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
from apps.controller.algorithms import NoAssignment, RandomAssignment, WeightedGraphColor, TrafficAware, TerminalCount
from libs.common.util import recv_all


logger = logging.getLogger('controller')

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
    REPLY_SCHEMA = json.loads(f.read())
 

MEASUREMENT_DURATION = 10
CHANNEL_DWELL_TIME = 5
MEASUREMENTS = {
    # "latency": {'action': 'collect', 'clientLatency': True, 'pingArgs': '-i 0.2 -s 1232 -w %d 192.168.1.1' % (MEASUREMENT_DURATION)},
    # "iperf_tcp": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    # "iperf_udp": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -u -b 72M -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    "iperf_tcp_downlink": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-s -i 1 -p %s -f m -P 1' % ('%d')},
    "iperf_udp_downlink": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-s -i 1 -u -p %s -f m -P 1' % ('%d')},
    }


ALGORITHMS = [
    # NoAssignment(),
    RandomAssignment(),
    WeightedGraphColor(),
    TerminalCount(),
    TrafficAware(),
    # TrafficAware(weight={'packets': 1, 'retry_packets': 0, 'corrupted_packets': 0}),
    # TrafficAware(weight={'packets': 0, 'retry_packets': 1, 'corrupted_packets': 0}),
    # TrafficAware(weight={'packets': 0, 'retry_packets': 0, 'corrupted_packets': 1}),
    ]

MAX_CLIENT_NUM = 4


DEFAULT_REPEAT = len(MEASUREMENTS) * len(ALGORITHMS) * MAX_CLIENT_NUM * 20


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
      conn.settimeout(settings.READ_TIMEOUT_SEC)
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

    if self['action'] in ['apConfig', 'clientReassoc', 'clientReboot']:
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
        conn = socket.create_connection((ap.IP, settings.PUBLIC_TCP_PORT), timeout=settings.CONNECTION_TIMEOUT_SEC)
        conn.sendall(msg)
        conn.shutdown(socket.SHUT_WR)
        if block:
          t = threading.Thread(target=self.handle_reply, args=(conn,))
          t.start()
          handler_threads.append(t)
        else:
          conn.close()
      except socket.timeout:
        logger.debug("%s is dead." % (ap.BSSID))
      except:
        logger.exception("Failed to send msg to %s" % (ap.BSSID))

    for t in handler_threads:
      t.join()

  def broadcast(self, **kwargs):
    aps = AccessPoint.objects.filter(sniffer_ap=True).values_list('BSSID', flat=True)
    self.send(*aps, **kwargs)


""" Get AP-client association map. """
def get_stations(need_sniffer=False, enforce_association=False):
  now = dt.now()

  Request({'action': 'collect', 'apStatus': True, 'stationDump': True, 'phonelabDevice': True, 'nearbyDevices': True}).broadcast()

  stations = dict()

  if not need_sniffer:
    for sta in Station.objects.filter(sniffer_station=True, last_updated__gte=now):
      BSSID = sta.associate_with.BSSID
      if BSSID not in stations:
        stations[BSSID] = []
      stations[BSSID].append(sta.MAC)
  else:
    for active_sta in Station.objects.filter(sniffer_station=True, neighbor_station__isnull=True, last_updated__gte=now):
      try:
        passive_sta = Station.objects.filter(neighbor_station=active_sta, last_updated__gte=now)[0]
      except:
        logger.debug("No passive device for station %s" % (active_sta.MAC))
        continue

      if enforce_association and passive_sta.associate_with != active_sta.associate_with:
        logger.debug("Force %s reassociate with %s" % (passive_sta.MAC, active_sta.associate_with.BSSID))
        Request({'action': 'clientReassoc', 'clients': [passive_sta.MAC], 'newBSSID': active_sta.associate_with.BSSID}).send(passive_sta.associate_with.BSSID)

      BSSID = active_sta.associate_with.BSSID
      if BSSID not in stations:
        stations[BSSID] = []
      stations[BSSID].append((active_sta.MAC, passive_sta.MAC))

  logger.debug("Stations found: %s" % (str(stations)))
  return stations


""" One experiment run """
def do_measurement(**kwargs):
  logger.debug("================ MEASUREMENT BEGIN =====================")

  history = MeasurementHistory()
  history.begin1 = dt.now()

  algo = kwargs.get('algo', random.choice(ALGORITHMS))
  measurement = kwargs.get('measurement', random.choice(MEASUREMENTS.keys()))

  station_map = get_stations(algo.need_traffic, enforce_association=True)
  client_num = kwargs.get('client_num', random.randint(1, MAX_CLIENT_NUM))
  eligible_aps = [ap for ap, stas in station_map.items() if len(stas) >= client_num]
  if len(eligible_aps) == 0:
    logger.debug("No eligible APs! Aborting.")
    return

  ap = AccessPoint.objects.get(BSSID=kwargs.get('ap', random.choice(eligible_aps)))

  all_stations = station_map[ap.BSSID]
  if len(all_stations) > client_num:
    all_stations = random.sample(all_stations, client_num)

  if algo.need_traffic:
    active_stas = [t[0] for t in all_stations]
    passive_stas = [t[1] for t in all_stations]
  else:
    active_stas = all_stations
    passive_stas = None

  history.ap = ap
  history.algo = algo.name
  history.measurement = measurement
  history.station_map = json.dumps(station_map)
  history.client_num = len(active_stas)
  history.active_stas = json.dumps(active_stas)
  history.passive_stas = json.dumps(passive_stas)


  logger.debug("=======================================================")
  logger.debug("Algorithm: %s" % (history.algo))
  logger.debug("Measurment: %s" % (history.measurement))
  logger.debug("AP: %s" % (ap.BSSID))
  logger.debug("Client number: %d" % (len(active_stas)))
  logger.debug("Active clients: %s" % (str(active_stas)))
  logger.debug("=======================================================")

  if algo.need_traffic:
    if passive_stas is None:
      logger.debug("No passive stas. Aborting.")
      return
    Request({'action': 'collect', 'clientTraffic': True, 'trafficChannel': settings.BAND2G_CHANNELS, 'channelDwellTime': CHANNEL_DWELL_TIME, 'clients': active_stas}).send(ap.BSSID)
    time.sleep(CHANNEL_DWELL_TIME*len(settings.BAND2G_CHANNELS))
    for sta in passive_stas:
      logger.debug("Waiting for traffic statistics from %s" % (sta))
      for unused in range(0, 20):
        if Traffic.objects.filter(last_updated__gte=history.begin1, hear_by__MAC=sta).exists():
          break
        time.sleep(1)
    if not Traffic.objects.filter(last_updated__gte=history.begin1, hear_by__MAC__in=passive_stas).exists():
      logger.debug("No traffic statistics for any active device.")
      logger.debug("===================== MEASUREMENT END    ===================== ")
      return

  if algo.need_scan_result:
    Request({'action': 'collect', 'apScan': True, 'clientScan': True, 'clients': active_stas}).send(ap.BSSID)

  algo.run(begin=history.begin1, ap=ap)

  measure_request = Request(MEASUREMENTS[measurement])
  measure_request['clients'] = active_stas
  measure_request.send(ap.BSSID)

  history.end2 = dt.now()
  history.save()
  logger.debug("===================== MEASUREMENT END    ===================== ")



def ap_measurement(**kwargs):
    repeat = kwargs.get('repeat', DEFAULT_REPEAT)
    for unused in range(0, repeat):
      logger.debug("================ Run #: %d / %d  =====================" % (unused, repeat))
      do_measurement()



def reboot_clients():
  Request({'action': 'clientReboot', 'clients': list(Station.objects.filter(sniffer_station=True).values_list('MAC', flat=True))}).broadcast()
  time.sleep(60)
