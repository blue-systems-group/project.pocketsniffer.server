
import os
import json
import logging
import socket
import random
import threading
import sys
from jsonschema import validate
from dateutil import parser
from datetime import datetime as dt


from django.conf import settings

from apps.controller.models import AccessPoint, ScanResult, Station, Traffic
from lib.common.utils import recv_all, freq_to_channel, get_iface_addr

logger = logging.getLogger('controller')

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'request.json')) as f:
    REQUEST_SCHEMA = json.loads(f.read())
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
    REPLY_SCHEMA = json.loads(f.read())
  


class Algorithm(object):

  TRIGGER_REASON_TIMEOUT = 1
  TRIGGER_REASON_REQUEST = 2

  def __init__(self, *args, **kwargs):
    super(Algorithm, self).__init__()
    self.intervalSec = 300
    self.last_trigger = None


  @classmethod
  def handle_phonelab_device(cls, reply):
    for mac in reply['phonelabDevice']:
      sta, unused = Station.objects.get_or_create(MAC=mac)
      sta.phonelab_station = True
      sta.save()


  @classmethod
  def handle_client_scan(cls, reply):
    for scan_result in reply['clientScan']:
      sta, unused = Station.objects.get_or_create(MAC=scan_result['MAC'])
      ScanResult.objects.filter(myself_station=sta).all().delete()
      for entry in scan_result['resultList']:
        neighbor_ap, unused = AccessPoint.objects.get_or_create(BSSID=entry['BSSID'])
        neighbor_ap.SSID = entry['SSID']
        neighbor_ap.channel = freq_to_channel(entry['frequency'])
        neighbor_ap.client_num = entry.get('stationCount', None)
        neighbor_ap.load = entry.get('bssLoad', None)
        neighbor_ap.save()

        ScanResult(myself_station=sta, neighbor=neighbor_ap, signal=entry['RSSI'], timestamp=parser.parse(scan_result['timestamp'])).save()


  @classmethod
  def handle_client_traffic(cls, reply):
    for traffic in reply['clientTraffic']:
      origin_sta, unused = Station.objects.get_or_create(MAC=traffic['MAC'])
      for entry in traffic['traffics']:
        uplink = None
        if not (Station.objects.filter(MAC__in=[entry['from'], entry['to']]).exists() or\
            AccessPoint.objects.filter(BSSID__in=[entry['from'], entry['to']]).exists()):
          logger.error("Station or AP missing. Ignore traffic %s --> %s" % (entry['from'], entry['to']))
          continue

        if AccessPoint.objects.filter(BSSID=entry['from']).exists():
          ap = AccessPoint.objects.get(BSSID=entry['from'])
          sta, unused = Station.objects.get_or_create(MAC=entry['to'])
          uplink = False
        elif AccessPoint.objects.filter(BSSID=entry['to']).exists():
          sta, unused = Station.objects.get_or_create(MAC=entry['from'])
          ap = AccessPoint.objects.get(BSSID=entry['to'])
          uplink = True
        elif Station.objects.filter(MAC=entry['from']).exists():
          sta = Station.objects.get(MAC=entry['from'])
          ap, unused = AccessPoint.objects.get_or_create(BSSID=entry['to'])
          uplink = True
        elif Station.objects.filter(MAC=entry['to']).exists():
          ap, unused = AccessPoint.objects.get_or_create(BSSID=entry['to'])
          sta = Station.objects.get(MAC=entry['to'])
          uplink = False

        if uplink is None:
          logger.debug("Can not determine uplink: %s --> %s" % (entry['from'], entry['to']))
          continue

        sta.associate_with = ap
        sta.save()

        tfc = Traffic(hear_by=origin_sta, from_station=sta, to_ap=ap)
        tfc.begin = parser.parse(entry['begin'])
        tfc.end = parser.parse(entry['end'])
        tfc.timestamp = parser.parse(traffic['timestamp'])
        tfc.channel = entry['channel']
        if uplink is True:
          tfc.tx_bytes = entry['txBytes']
          tfc.rx_bytes = entry['rxBytes']
          tfc.avg_tx_rssi = entry['avgTxRSSI']
          tfc.avg_rx_rssi = entry['avgRxRSSI']
        else:
          tfc.tx_bytes = entry['rxBytes']
          tfc.rx_bytes = entry['txBytes']
          tfc.avg_tx_rssi = entry['avgRxRSSI']
          tfc.avg_rx_rssi = entry['avgTxRSSI']
        tfc.save()


  @classmethod
  def handle_ap_reply(cls, conn, ap):

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

    logger.debug("Got reply from %s" % (ap.BSSID))

    HANDLER_MAPPING = {
        'apStatus': AccessPoint.handle_ap_status,
        'apScan': AccessPoint.handle_ap_scan,
        'stationDump': AccessPoint.handle_station_dump,
        'phonelabDevice': Algorithm.handle_phonelab_device,
        'clientScan': Algorithm.handle_client_scan,
        'clientTraffic': Algorithm.handle_client_traffic,
        }

    for t, handler in HANDLER_MAPPING.items():
      try:
        if reply['request'].get(t, False):
          handler(reply[t])
      except:
        logger.exception("Failed to handle %s" % (t))


  def send_request(self, request, **kwargs):
    """Collect information necessary to run this algorithm."""
    sniffer_aps = AccessPoint.objects.filter(sniffer_ap=True).exclude(IP=None)
    logger.debug("%d sniffer aps (with ip_addr) found." % (len(sniffer_aps)))
    if 'limit_aps' in kwargs:
      sniffer_aps = sniffer_aps.filter(BSSID__in=kwargs['limit_aps'])
      logger.debug("Restricting to %d aps." % (len(sniffer_aps)))

    msg = json.dumps(request)

    expect_reply = request['action'] == 'collect'
    
    logger.debug("Request msg: %s" % (msg))
    handler_threads = []
    for ap in sniffer_aps:
      try:
        logger.debug("Sending to %s:%s" % (ap.IP, settings.PUBLIC_TCP_PORT))
        conn = socket.create_connection((ap.IP, settings.PUBLIC_TCP_PORT))
        conn.sendall(msg)
        if expect_reply:
          conn.shutdown(socket.SHUT_WR)
          t = threading.Thread(target=Algorithm.handle_ap_reply, args=(conn, ap))
          t.start()
          handler_threads.append(t)
        else:
          conn.close()
      except:
        logger.exception("Failed to send msg to %s" % (ap))

    if expect_reply:
      logger.debug("Waiting for responses.")
      try:
        for t in handler_threads:
          t.join()
      except KeyboardInterrupt:
        sys.exit()
      except:
        logger.exception("Failed to collect information.")


  def trigger(self, reason, **kwargs):
    pass

  def run(self):
    try:
      public_ip = get_iface_addr(settings.PUBLIC_IFACE)
    except:
      logger.exception("Failed to get public ip.")
      return

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((public_ip, settings.PUBLIC_TCP_PORT))
    server_sock.settimeout(self.intervalSec)
    server_sock.listen(10)

    while True:
      try:
        conn, addr = server_sock.accept()
      except socket.timeout:
        self.trigger(Algorithm.TRIGGER_REASON_TIMEOUT)
        self.last_trigger = dt.now()
        continue
      except:
        logger.exception("Exiting.")
        break

      try:
        request = json.loads(recv_all(conn))
      except:
        logger.exception("Failed to read request.")
        continue

      try:
        validate(request, REQUEST_SCHEMA)
      except:
        logger.exception("Failed to validate request.")
        continue

      self.trigger(Algorithm.TRIGGER_REASON_REQUEST, request=request)
      self.last_trigger = dt.now()

    try:
      logger.debug("Closing server socket.")
      server_sock.close()
    except:
      pass
        


class StaticAssignment(Algorithm):

  def __init__(self, *args, **kwargs):
    super(StaticAssignment, self).__init__(*args, **kwargs)

    logger.debug("Collecting AP status.")
    request = {'action': 'collect', 'apStatus': True}
    self.send_request(request)


    self.send_request({'action': 'apConfig', 'band2g':{'enable':False}})

    for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND5G_CHANNELS):
      request = {'action': 'apConfig', 'band5g':{}}
      request['band5g']['enable'] = True
      request['band5g']['channel'] = random.choice(settings.BAND5G_CHANNELS)
      self.send_request(request, limit_aps=[ap.BSSID])


  def trigger(self, reason, **kwargs):
    pass



class RandomAssignment(Algorithm):

  def run(self):
    pass


class LCCS(Algorithm):
  pass


class WeightedGraphColor(Algorithm):
  pass

class ConflictSet(Algorithm):
  pass
