import os
import logging
import time
import socket
import json
import random
from datetime import datetime as dt, timedelta
from django.conf import settings


from apps.controller.models import Station, AccessPoint, MeasurementHistory
from apps.controller.algorithms import NoAssignment, RandomAssignment, WeightedGraphColor, TrafficAware


logger = logging.getLogger('controller')

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
    REPLY_SCHEMA = json.loads(f.read())
 


MEASUREMENT_DURATION = 30
MEASUREMENTS = {
    "Latency": {'action': 'collect', 'clientLatency': True, 'pingArgs': '-i 0.2 -s 1232 -w %d 192.168.1.1' % (MEASUREMENT_DURATION)},
    "TCP Throughput": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    "UDP Throughput": {'action': 'collect', 'clientThroughput': True, 'iperfArgs': '-c 192.168.1.1 -i 1 -t %d -u -b 50M -p %s -f m' % (MEASUREMENT_DURATION, '%d')},
    }


ALGORITHMS = [
    NoAssignment(),
    RandomAssignment(),
    WeightedGraphColor(),
    TrafficAware(),
    ]



class Request(dict):

  def send(self, *aps):
    sniffer_aps = AccessPoint.objects.filter(sniffer_ap=True, BSSID__in=aps, channel__in=settings.BAND2G_CHANNELS).exclude(IP=None).distinct('IP')

    msg = json.dumps(self)
    logger.debug("Request msg: %s" % (msg))

    for ap in sniffer_aps:
      try:
        logger.debug("Sending to %s:%s" % (ap.IP, settings.PUBLIC_TCP_PORT))
        conn = socket.create_connection((ap.IP, settings.PUBLIC_TCP_PORT))
        conn.sendall(msg)
        conn.shutdown(socket.SHUT_WR)
        conn.close()
      except:
        logger.exception("Failed to send msg to %s" % (ap))

    delay = 0

    if self['action'] == 'apConfig':
      delay = 5
    elif self['action'] == 'clientReassoc':
      delay = 10
    elif self['action'] == 'collect':
      if any([self.get(k, False) for k in ['phonelabDevice', 'clientScan', 'nearbyDevice']]):
        delay = 10
      elif any([self.get(k, False) for k in ['apStatus', 'apScan', 'stationDump']]):
        delay = 5

    if delay > 0:
      time.sleep(delay)


  def broadcast(self):
    aps = AccessPoint.objects.filter(sniffer_ap=True).values_list('BSSID', flat=True)
    self.send(*aps)



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

  for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
    Request({'action': 'apConfig', 'band2g': {'channel': random.choice(settings.BAND2G_CHANNELS)}}).send(ap.BSSID)

  active_stas, passive_stas = check_association()

  if len(active_stas) == 0:
    logger.debug("No available active clients found.")
    logger.debug("===================== MEASUREMENT END    ===================== ")
    return

  channel_dwell_time = random.choice([1, 2, 5, 10])

  key = random.choice(MEASUREMENTS.keys())
  measure_request = Request(MEASUREMENTS[key])
  measure_request['clients'] = active_stas

  measurement_history = MeasurementHistory()
  measurement_history.begin1 = dt.now()

  Request({'action': 'collect', 'clientTraffic': True, 'trafficChannel': settings.BAND2G_CHANNELS, 'channelDwellTime': channel_dwell_time, 'clients': active_stas}).broadcast()
  measure_request.broadcast()
  time.sleep(MEASUREMENT_DURATION+10)

  Request({'action': 'collect', 'apScan': True}).broadcast()
  Request({'action': 'collect', 'clientScan': True, 'clients': active_stas}).broadcast()

  measurement_history.end1 = dt.now()

  random.choice(ALGORITHMS).run(begin=measurement_history.begin1, end=measurement_history.end1, channel_dwell_time=channel_dwell_time)

  measurement_history.begin2 = dt.now()

  measure_request.broadcast()
  time.sleep(MEASUREMENT_DURATION+10)

  measurement_history.end2 = dt.now()

  measurement_history.save()
  logger.debug("===================== MEASUREMENT END    ===================== ")


def ap_clean_up():
  for ap in AccessPoint.objects.filter(sniffer_ap=True, last_updated__lte=dt.now()-timedelta(seconds=2*settings.AP_HEARTBEAT_INTERVAL)):
    logger.debug("AP %s is dead, delete it." % (ap.BSSID))
    ap.delete()
