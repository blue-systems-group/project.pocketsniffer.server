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
 

MEASUREMENT_DURATION = 20
CHANNEL_DWELL_TIME = 5
MEASUREMENTS = {
    # "latency": {'action': 'collect', 'clientLatency': True, 'pingArgs': '-i 0.2 -s 1232 -w %d 192.168.1.1' % (MEASUREMENT_DURATION)},
    # "iperf_tcp_uplink": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    "iperf_tcp_downlink": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-s -i 1 -p %s -f m -P 1' % ('%d')},
    # "iperf_udp_uplink": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -u -b 72M -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    # "iperf_udp_downlink": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-s -i 1 -u -p %s -f m -P 1' % ('%d')},
    }


ALGORITHMS = [
    # NoAssignment(),
    RandomAssignment(),
    WeightedGraphColor(),
    TerminalCount(),
    TrafficAware(weight={'packets': 0.4, 'retry_packets': 0.2, 'corrupted_packets': 0.4}),
    # TrafficAware(weight={'packets': 1, 'retry_packets': 0, 'corrupted_packets': 0}),
    # TrafficAware(weight={'packets': 0, 'retry_packets': 1, 'corrupted_packets': 0}),
    # TrafficAware(weight={'packets': 0, 'retry_packets': 0, 'corrupted_packets': 1}),
    ]

MAX_CLIENT_NUM = 4


DEFAULT_REPEAT = len(MEASUREMENTS) * len(ALGORITHMS) * MAX_CLIENT_NUM * 10


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



class APMeasurementThread(threading.Thread):

  def __init__(self, ap, **kwargs):
    super(APMeasurementThread, self).__init__()
    self.ap = ap
    self.repeat = kwargs.get('repeat', DEFAULT_REPEAT)


  def do_measurement(self, algo, measurement, limit_client=None):
    measurement_history = MeasurementHistory()
    measurement_history.begin1 = dt.now()

    station_map = get_stations(algo.need_traffic, enforce_association=True)
    all_stations = station_map[self.ap.BSSID]
    if len(all_stations) == 0:
      logger.debug("No stations found for AP %s." % (self.ap.BSSID))
      return

    if limit_client is not None:
      if not algo.need_traffic:
        all_stations = [t for t in all_stations if t.startswith(limit_client)]
      else:
        for t1, t2 in all_stations:
          if t1.startswith(limit_client):
            all_stations = (t1, t2)
            break

    client_num = random.randint(1, min(len(all_stations), MAX_CLIENT_NUM))
    all_stations = random.sample(all_stations, client_num)

    measurement_history.ap = self.ap
    measurement_history.algo = algo.name
    measurement_history.measurement = measurement
    measurement_history.station_map = json.dumps(station_map)
    measurement_history.client_num = client_num

    if algo.need_traffic:
      active_stas = [t[0] for t in all_stations]
      passive_stas = [t[1] for t in all_stations]
    else:
      active_stas = all_stations

    logger.debug("================ MEASUREMENT BEGIN =====================")
    logger.debug("Algorithm: %s" % (algo.name))
    logger.debug("Measurment: %s" % (measurement))
    logger.debug("Client number: %d" % (client_num))
    logger.debug("Active clients: %s" % (str(active_stas)))


    if algo.need_traffic:
      Request({'action': 'collect', 'clientTraffic': True, 'trafficChannel': settings.BAND2G_CHANNELS, 'channelDwellTime': CHANNEL_DWELL_TIME, 'clients': active_stas}).send(self.ap.BSSID)
      time.sleep(CHANNEL_DWELL_TIME*len(settings.BAND2G_CHANNELS))
      for sta in passive_stas:
        logger.debug("Waiting for traffic statistics from %s" % (sta))
        for unused in range(0, 20):
          if Traffic.objects.filter(last_updated__gte=measurement_history.begin1, hear_by__MAC=sta).exists():
            break
          time.sleep(1)
      if not Traffic.objects.filter(last_updated__gte=measurement_history.begin1, hear_by__MAC__in=passive_stas).exists():
        logger.debug("No traffic statistics for any active device.")
        logger.debug("===================== MEASUREMENT END    ===================== ")
        return

    if algo.need_scan_result:
      Request({'action': 'collect', 'apScan': True, 'clientScan': True, 'clients': active_stas}).send(self.ap.BSSID)

    algo.run(begin=measurement_history.begin1, ap=self.ap)

    measure_request = Request(MEASUREMENTS[measurement])
    measure_request['clients'] = active_stas
    measure_request.send(self.ap.BSSID)

    measurement_history.end2 = dt.now()
    measurement_history.save()
    logger.debug("===================== MEASUREMENT END    ===================== ")


  def run(self):
    for unused in range(0, self.repeat):
      logger.debug("================ Run #: %d / %d  =====================" % (unused, self.repeat))
      algo = random.choice(ALGORITHMS)
      measurement = random.choice(MEASUREMENTS.keys())
      self.do_measurement(algo, measurement)
      time.sleep(random.randint(1, MEASUREMENT_DURATION))


def ap_measurement(**kwargs):
  station_map = get_stations(need_sniffer=True)
  threads = []
  for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS, BSSID__in=station_map.keys()):
    t = APMeasurementThread(ap, **kwargs)
    t.start()
    threads.append(t)
  return threads


def reboot_clients():
  Request({'action': 'clientReboot', 'clients': list(Station.objects.filter(sniffer_station=True).values_list('MAC', flat=True))}).broadcast()
  time.sleep(60)
