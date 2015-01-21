
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
from django.db.models import Q

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
    self.last_request = None


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
      for_devices = json.dumps(traffic['forDevices'])
      for entry in traffic['traffics']:
        src, created = Station.objects.get_or_create(MAC=entry['src'])
        if created:
          src.save()

        tfc = Traffic(hear_by=origin_sta, for_devices=for_devices, src=src)
        tfc.begin = parser.parse(entry['begin'])
        tfc.end = parser.parse(entry['end'])
        tfc.timestamp = parser.parse(traffic['timestamp'])
        tfc.channel = entry['channel']
        tfc.packets = entry['packets']
        tfc.retry_packets = entry['retryPackets']
        tfc.avg_rssi = entry['avgRSSI']
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

    logger.debug("Got reply from %s: %s" % (ap.BSSID, json.dumps(reply)))

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
          handler(reply)
      except:
        logger.exception("Failed to handle %s" % (t))


  def send_request(self, request, **kwargs):
    """Collect information necessary to run this algorithm."""
    sniffer_aps = AccessPoint.objects.filter(sniffer_ap=True).exclude(IP=None)
    logger.debug("%d sniffer aps (with ip_addr) found." % (len(sniffer_aps)))
    if 'limit_aps' in kwargs:
      sniffer_aps = sniffer_aps.filter(BSSID__in=kwargs['limit_aps'])
      logger.debug("Restricting to %d aps." % (len(sniffer_aps)))

    sniffer_aps = sniffer_aps.distinct('IP')

    self.last_request = dt.now()
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


  def disable(self, band):
    if band == 'band2g':
      channels = settings.BAND2G_CHANNELS
    elif band == 'band5g':
      channels = settings.BAND5G_CHANNELS
    else:
      logger.error("Invalid band %s" % (band))
      return

    for ap in AccessPoint.objects.filter(sniffer_ap=True, enabled=True, channel__in=channels):
      logger.debug("Disabling %s of %s (%s)." % (band, ap.MAC, ap.IP))
      self.send_request({'action': 'apConfig', band:{'enable':False}}, limit_aps=[ap.BSSID])


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

      self.trigger(Algorithm.TRIGGER_REASON_REQUEST, request=request, ip=addr[0])
      self.last_trigger = dt.now()

    try:
      logger.debug("Closing server socket.")
      server_sock.close()
    except:
      pass
        


class StaticAssignment(Algorithm):

  def __init__(self, *args, **kwargs):
    super(StaticAssignment, self).__init__(*args, **kwargs)

    self.ap_channels = dict()


  def trigger(self, reason, **kwargs):
    if reason == Algorithm.TRIGGER_REASON_REQUEST:
      logger.debug("Ignoring channel assignment request from ap.")
      return

    logger.debug("Collecting AP status.")
    self.send_request({'action': 'collect', 'apStatus': True})


    for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
      if ap.BSSID in self.ap_channels and ap.channel == self.ap_channels[ap.BSSID]:
        continue
      request = {'action': 'apConfig', 'band2g':{'enable': True}}
      if ap.BSSID not in self.ap_channels:
        self.ap_channels[ap.BSSID] = random.choice(settings.BAND2G_CHANNELS)
      logger.debug("Assign channel %d to %s (%s)" % (self.ap_channels[ap.BSSID], ap.BSSID, ap.IP))
      request['band2g']['channel'] = self.ap_channels[ap.BSSID]
      self.send_request(request, limit_aps=[ap.BSSID])


class RandomAssignment(Algorithm):

  def trigger(self, reason, **kwargs):
    logger.debug("Collecting AP status.")
    self.send_request({'action': 'collect', 'apStatus': True})

    for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
      request = {'action': 'apConfig', 'band2g':{'enable': True}}
      request['band2g']['channel'] = random.choice(settings.BAND2G_CHANNELS)
      logger.debug("Assign channel %d to %s (%s)" % (request['band2g']['channel'], ap.BSSID, ap.IP))
      self.send_request(request, limit_aps=[ap.BSSID])


class WeightedGraphColor(Algorithm):

  def __init__(self, *args, **kwargs):
    super(WeightedGraphColor, self).__init__(*args, **kwargs)
    self.coordinate = kwargs.get('coordinate', False)


  def Ifactor(self, ap1, ap2):
    if ap1.channel == ap2.channel:
      return 1
    else:
      return 0

  def weight(self, ap1, ap2):
    client_num = 0
    overhear_num = 0

    if self.coordinate and ap1.sniffer_ap and ap2.sniffer_ap:
      client_num = Station.objects.filter(Q(associate_with=ap1) | Q(associate_with=ap2)).count()
      for a, b in [(ap1, ap2), (ap2, ap1)]:
        for sta in Station.objects.filter(associate_with=a):
          if ScanResult.objects.filter(timestamp__gte=self.last_request, myself_station=sta, neighbor=b).exists():
            overhear_num += 1
    else:
      client_num = Station.objects.filter(associate_with=ap1).count()
      for sta in Station.objects.filter(associate_with=ap1):
        if ScanResult.objects.filter(timestamp__gte=self.last_request, myself_station=sta, neighbor=ap2).exists():
          overhear_num += 1

    if client_num == 0:
      return 0
    else:
      return float(overhear_num) / client_num


  def trigger(self, reason, **kwargs):
    if reason == Algorithm.TRIGGER_REASON_REQUEST:
      logger.debug("Ignoring channel assignment request from ap.")
      return

    self.send_request({'action': 'collect', 'apScan': True, 'clientScan': True})

    for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
      H = dict()
      for c in settings.BAND2G_CHANNELS:
        H[c] = 0
        for neighbor in ap.neighbor_aps:
          H[c] = max(H[c], self.Ifactor(ap, neighbor)*self.weight(ap, neighbor))
      c = min(settings.BAND2G_CHANNELS, key=lambda t: H[t])

      request = {'action': 'apConfig', 'band2g':{'enable': True}}
      request['band2g']['channel'] = c
      logger.debug("Assign channel %d to %s (%s)" % (c, ap.BSSID, ap.IP))
      self.send_request(request, limit_aps=[ap.BSSID])


class ConflictSet(Algorithm):
  pass


class OurAlgorithm(Algorithm):

  def trigger(self, reason, **kwargs):
    if reason == Algorithm.TRIGGER_REASON_TIMEOUT:
      logger.debug("Ignore periodic trigger.")
      return

    ip = kwargs['ip']
    try:
      ap = AccessPoint.objects.filter(sniffer_ap=True, enabled=True, channel__in=settings.BAND2G_CHANNELS, IP=ip)[0]
    except:
      logger.exception("No AP with ip %s found." % (ip))
      return

    request = kwargs['request']
    request['action'] = 'collect'
    request['clientTraffic'] = True
    request['trafficChannel'] = settings.BAND2G_CHANNELS
    request['channelDwellTime'] = 5

    self.send_request(request, limit_aps=[ap.BSSID])

    clients = [c.MAC for c in Station.objects.filter(associate_with=ap)]
    src_excludes = clients + [ap.BSSID]

    logger.debug("All clients: %s" % (str(clients)))
    logger.debug("Exclude stations: %s" % (str(src_excludes)))

    H = dict()
    for c in settings.BAND2G_CHANNELS:
      H[c] = {'packets': 0, 'retry_packets': 0}
      for t in Traffic.objects.filter(last_updated__gte=self.last_request, channel=c).exclude(src__MAC__in=src_excludes):
        H[c]['packets'] += t.packets
        H[c]['retry_packets'] += t.retry_packets
      logger.debug("%d (%d) packets on channel %d" % (H[c]['packets'], H[c]['retry_packets'], c))

    logger.debug("traffic map: %s" % (json.dumps(H)))
    c = min(settings.BAND2G_CHANNELS, key=lambda t: H[t]['packets'])

    if c != ap.channel and H[ap.channel]['packets'] > 1.2 * H[c]['packets']:
      request = {'action': 'apConfig', 'band2g':{'channel': c}}
      logger.debug("Assign channel %d to AP %s." % (c, ap.BSSID))
      self.send_request(request, limit_aps=[ap.BSSID])
