from __future__ import absolute_import

import os
import logging
import socket
import sys
import json
import threading
import random
import time
from datetime import datetime as dt
from jsonschema import validate
from django.conf import settings

from celery import shared_task


from apps.controller.models import Station, AccessPoint, ScanResult, Traffic, LatencyResult, ThroughputResult, MeasurementHistory
from apps.controller.algorithms import NoAssignment, RandomAssignment, WeightedGraphColor, TrafficAware

from lib.common.utils import recv_all

logger = logging.getLogger('controller')

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'request.json')) as f:
    REQUEST_SCHEMA = json.loads(f.read())
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
    REPLY_SCHEMA = json.loads(f.read())
 

MEASUREMENT_TASK_ID_FILE = '/tmp/measurement_task_id'

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


  def send(self, *aps):
    sniffer_aps = AccessPoint.objects.filter(sniffer_ap=True, BSSID__in=aps, channel__in=settings.BAND2G_CHANNELS).exclude(IP=None).distinct('IP')

    msg = json.dumps(self)
    logger.debug("Request msg: %s" % (msg))

    expect_reply = self['action'] == 'collect'
    
    handler_threads = []
    for ap in sniffer_aps:
      try:
        logger.debug("Sending to %s:%s" % (ap.IP, settings.PUBLIC_TCP_PORT))
        conn = socket.create_connection((ap.IP, settings.PUBLIC_TCP_PORT))
        conn.sendall(msg)
        if expect_reply:
          conn.shutdown(socket.SHUT_WR)
          t = threading.Thread(target=self.handle_ap_reply, args=(conn, ap))
          t.start()
          handler_threads.append(t)
        else:
          conn.close()
      except:
        logger.exception("Failed to send msg to %s" % (ap))

    if expect_reply:
      logger.debug("Waiting for %d responses." % (len(handler_threads)))
      try:
        for t in handler_threads:
          t.join()
      except KeyboardInterrupt:
        sys.exit()
      except:
        logger.exception("Failed to collect information.")


  def send_async(self, *aps):
    t = threading.Thread(target=self.send, args=aps)
    t.start()
    return t
  

  def broadcast(self):
    aps = AccessPoint.objects.filter(sniffer_ap=True).values_list('BSSID', flat=True)
    self.send(*aps)


  def broadcast_async(self):
    aps = AccessPoint.objects.filter(sniffer_ap=True).values_list('BSSID', flat=True)
    self.send_async(*aps)


  def handle_ap_reply(self, conn, ap):
    logger.debug("Handler thread running, ap = %s (%s)." % (ap.BSSID, ap.IP))
    try:
      reply = json.loads(recv_all(conn))
    except:
      logger.exception("Failed to read reply from %s" % (ap.BSSID))
      return

    try:
      validate(reply, REPLY_SCHEMA)
    except:
      logger.exception("Failed to validate reply.")
      logger.debug(json.dumps(reply))
      return

    logger.debug("Got reply from %s: %s" % (ap.BSSID, json.dumps(reply)))


    for t, handler in Request.HANDLER_MAPPING.items():
      try:
        if reply['request'].get(t, False):
          handler(reply[t])
      except:
        logger.exception("Failed to handle %s" % (t))



def check_association():
  Request({'action': 'collect', 'stationDump': True}).broadcast()
  Request({'action': 'collect', 'nearbyDevices': True}).broadcast()

  active_stas = []
  for active_sta in Station.objects.fitler(sniffer_ap=True, neighbor_station__isnull=True):
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

    active_stas.append(active_sta)

  logger.debug("%d active stations (with passive device) found." % (len(active_stas)))
  return active_stas


def do_measurement():
  for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
    Request({'action': 'apConfig', 'band2g': {'channel': random.choice(settings.BAND2G_CHANNELS)}}).send(ap.BSSID)

  active_stas = check_association(ap)

  channel_dwell_time = random.choice([1, 2, 5, 10])

  key = random.choice(MEASUREMENTS.keys())
  measure_request = Request(MEASUREMENTS(key))
  measure_request['clients'] = [s.MAC for s in active_stas]

  measurement_history = MeasurementHistory()
  measurement_history.begin1 = dt.now()

  Request({'action': 'collect', 'clientTraffic': True, 'trafficChannel': settings.BAND2G_CHANNELS, 'channelDwellTime': channel_dwell_time, 'clients': [s.MAC for s in active_stas]}).broadcast_async()
  measure_request.broadcast()
  Request({'action': 'collect', 'apScan': True, 'clientScan': True, 'clients': [s.MAC for s in active_stas]}).broadcast()

  measurement_history.end1 = dt.now()

  random.choice(ALGORITHMS).run(begin=measurement_history.begin1, end=measurement_history.end1, channel_dwell_time=channel_dwell_time)

  measurement_history.begin2 = dt.now()
  measure_request.broadcast()
  measurement_history.end2 = dt.now()

  measurement_history.save()


@shared_task(bind=True)
def trigger_measurement(self, *args, **kwargs):
  logger.debug("Staring measurements, args = %s, kwargs = %s." % (str(args), str(kwargs)))

  with open(MEASUREMENT_TASK_ID_FILE, 'w') as f:
    print >>f, self.request.id

  min_interval = int(kwargs.get('min_interval', int(MEASUREMENT_DURATION)))
  max_interval = int(kwargs.get('max_interval', int(2*MEASUREMENT_DURATION)))

  logger.debug("Interval range [%d, %d]" % (min_interval, max_interval))

  while True:
    do_measurement()

    interval = random.randint(min_interval, max_interval)
    time.sleep(interval)
