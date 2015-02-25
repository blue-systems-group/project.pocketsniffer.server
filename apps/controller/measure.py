import os
import threading
import logging
import time
import socket
import json
import random
from datetime import datetime as dt, timedelta
from django.conf import settings
from jsonschema import validate


from apps.controller.models import Station, AccessPoint, ScanResult, Traffic, LatencyResult, ThroughputResult, MeasurementHistory
from apps.controller.algorithms import NoAssignment, RandomAssignment, WeightedGraphColor, TrafficAware
from lib.common.utils import recv_all


logger = logging.getLogger('controller')

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
    REPLY_SCHEMA = json.loads(f.read())
 


MEASUREMENT_DURATION = 30
MEASUREMENTS = {
    "latency": {'action': 'collect', 'clientLatency': True, 'pingArgs': '-i 0.2 -s 1232 -w %d 192.168.1.1' % (MEASUREMENT_DURATION)},
    "iperf_tcp": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    "iperf_udp": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -u -b 72M -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    }


ALGORITHMS = [
    NoAssignment(),
    RandomAssignment(),
    WeightedGraphColor(),
    TrafficAware(),
    ]


class Request(dict):

  HANDLER_MAPPING = {
      'apStatus': AccessPoint.handle_ap_status,
      'stationDump': AccessPoint.handle_station_dump,

      'phonelabDevice': Station.handle_phonelab_device,
      'nearbyDevices': Station.handle_neighbor_device,

      'apScan': ScanResult.handle_ap_scan,
      'clientScan': ScanResult.handle_client_scan,

      'clientTraffic': Traffic.handle_client_traffic,
      'clientLatency': LatencyResult.handle_client_latency,
      'clientThroughput': ThroughputResult.handle_client_throughput,
      }


  def handle_reply(self, conn):
    try:
      content = recv_all(conn)
      reply = json.loads(content)
    except:
      logger.exception("Failed to parse reply: %s" % (str(content)))
      return

    try:
      validate(reply, REPLY_SCHEMA)
    except:
      logger.exception("Failed to validate reply.")
      logger.debug(json.dumps(reply))
      return

    logger.debug("Got reply: %s" % (json.dumps(reply)))

    for t, handler in Request.HANDLER_MAPPING.items():
      try:
        if reply['request'].get(t, False):
          handler(reply[t])
      except:
        logger.exception("Failed to handle %s" % (t))


  def send(self, *aps, **kwargs):
    sniffer_aps = AccessPoint.objects.filter(sniffer_ap=True, BSSID__in=aps, channel__in=settings.BAND2G_CHANNELS).exclude(IP=None).distinct('IP')

    if self['action'] == 'apConfig' or self['action'] == 'clientReassoc':
      block = False
    elif self['action'] == 'collect' and self.get('clientTraffic', False):
      block = False
    else:
      block = True

    msg = json.dumps(self)
    logger.debug("Request msg: %s" % (msg))

    handler_threads = []

    for ap in sniffer_aps:
      try:
        logger.debug("Sending to %s:%s" % (ap.IP, settings.PUBLIC_TCP_PORT))
        conn = socket.create_connection((ap.IP, settings.PUBLIC_TCP_PORT))
        conn.sendall(msg)
        conn.shutdown(socket.SHUT_WR)
        if block:
          t = threading.Thread(target=self.handle_reply, args=(conn,))
          t.start()
          handler_threads.append(t)
        else:
          conn.close()
      except:
        logger.exception("Failed to send msg to %s" % (ap))

    for t in handler_threads:
      t.join()



  def broadcast(self, **kwargs):
    aps = AccessPoint.objects.filter(sniffer_ap=True).values_list('BSSID', flat=True)
    self.send(*aps, **kwargs)



def check_association():
  Request({'action': 'collect', 'stationDump': True}).broadcast()
  Request({'action': 'collect', 'nearbyDevices': True}).broadcast()

  active_stas = []
  passive_stas = []
  for active_sta in Station.objects.filter(sniffer_station=True, neighbor_station__isnull=True):
    ap = active_sta.associate_with

    try:
      passive_sta = Station.objects.filter(neighbor_station=active_sta)[0]
    except:
      logger.exception("No passive device for station %s" % (active_sta.MAC))
      continue
    
    if passive_sta.associate_with == ap:
      logger.debug("Passive device (%s) for active device (%s) associate with same AP (%s)" % (passive_sta.MAC, active_sta.MAC, ap.BSSID))
    else:
      logger.debug("Force passive device (%s) associate with AP (%s)" % (passive_sta.MAC, ap.BSSID))
      Request({'action': 'clientReassoc', 'clients': [passive_sta.MAC], 'newBSSID': ap.BSSID}).send(passive_sta.associate_with.BSSID)

    active_stas.append(active_sta.MAC)
    passive_stas.append(passive_sta.MAC)

  logger.debug("%d active stations (with passive device) found." % (len(active_stas)))
  return active_stas, passive_stas


def do_measurement():
  logger.debug("===================== MEASUREMENT START ===================== ")
  measurement_history = MeasurementHistory()

  algo = random.choice(ALGORITHMS)
  logger.debug("Choosed algorithm: %s" % (algo.__class__.__name__))
  measurement_history.algo = algo.__class__.__name__

  key = random.choice(MEASUREMENTS.keys())
  logger.debug("Choosed measurment: %s" % (key))
  measurement_history.measure = key


  logger.debug("Randomly assigning AP channels.")
  for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
    Request({'action': 'apConfig', 'band2g': {'channel': random.choice(settings.BAND2G_CHANNELS)}}).send(ap.BSSID)

  logger.debug("Check passive client association.")
  active_stas, passive_stas = check_association()

  if len(active_stas) == 0:
    logger.debug("No available active clients found.")
    logger.debug("===================== MEASUREMENT END    ===================== ")
    return

  channel_dwell_time = random.choice([1, 2, 5, 10])

  measure_request = Request(MEASUREMENTS[key])
  measure_request['clients'] = active_stas

  measurement_history.begin1 = dt.now()

  if isinstance(algo, TrafficAware):
    Request({'action': 'collect', 'clientTraffic': True, 'trafficChannel': settings.BAND2G_CHANNELS, 'channelDwellTime': channel_dwell_time, 'clients': active_stas}).broadcast()

  measure_request.broadcast()

  Request({'action': 'collect', 'apScan': True, 'clientScan': True, 'clients': active_stas}).broadcast()

  if isinstance(algo, TrafficAware):
    for active_sta in active_stas:
      logger.debug("Waiting for traffic statistics for %s." % (active_sta))
      while not Traffic.objects.filter(last_updated__gte=measurement_history.begin1, for_device__MAC=active_sta).exists():
        time.sleep(1)

  measurement_history.end1 = dt.now()

  algo.run(begin=measurement_history.begin1, end=measurement_history.end1, channel_dwell_time=channel_dwell_time)

  measurement_history.begin2 = dt.now()

  measure_request.broadcast()

  measurement_history.end2 = dt.now()

  measurement_history.save()
  logger.debug("===================== MEASUREMENT END    ===================== ")


def ap_clean_up():
  for ap in AccessPoint.objects.filter(sniffer_ap=True, last_updated__lte=dt.now()-timedelta(seconds=2*settings.AP_HEARTBEAT_INTERVAL)):
    logger.debug("AP %s is dead, delete it." % (ap.BSSID))
    ap.delete()
