from __future__ import absolute_import

import os
import sys
import socket
import json
import logging
import threading
from jsonschema import validate
from dateutil import parser

from django.conf import settings

from apps.controller.models import AccessPoint, ScanResult, Station, Traffic, Latency, Throughput
from lib.common.utils import recv_all, freq_to_channel

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
    REPLY_SCHEMA = json.loads(f.read())



logger = logging.getLogger('backend')

def import_ap_list():
  for mac, ip in settings.AP_LIST:
    if AccessPoint.objects.filter(MAC=mac).exists():
      logger.debug("AP %s (%s) already exists." % (mac, ip))
      continue

    logger.info("Creating AP %s (%s)." % (mac, ip))
    AccessPoint(MAC=mac, IP=ip, sniffer_ap=True).save()


class HandlerThread(threading.Thread):

  def __init__(self, conn, ap):
    super(HandlerThread, self).__init__()
    self.conn = conn
    self.ap = ap


  def handle_ap_status(self, reply):
    ap_status = reply['apStatus']

    for band in ['band2g', 'band5g']:
      if ap_status[band]['enabled']:
        config = ap_status[band]
        if AccessPoint.objects.filter(BSSID=config['BSSID']).exists():
          ap = AccessPoint.objects.get(BSSID=config['BSSID'])
        else:
          if AccessPoint.objects.filter(MAC=ap_status['MAC'], BSSID=None).exists():
            ap = AccessPoint.objects.get(MAC=ap_status['MAC'])
          else:
            ap = AccessPoint(BSSID=config['BSSID'])

        for attr in ['MAC', 'IP']:
          setattr(ap, attr, ap_status[attr])
        for attr in ['BSSID', 'SSID', 'channel', 'noise', 'enabled']:
          setattr(ap, attr, config[attr])
        ap.tx_power = config['txPower']
        ap.last_status_update = parser.parse(ap_status['timestamp'])
        ap.save()

    for band, channels in [('band2g', range(1, 12)), ('band5g', range(36, 166))]:
      if not ap_status[band]['enabled']:
        try:
          ap = AccessPoint.objects.filter(MAC=['MAC'], enabled=True, channel__in=channels)[0]
          ap.enabled = False
          ap.last_status_update = parser.parse(ap_status['timestamp'])
          ap.save()
        except:
          pass


  def handle_ap_scan(self, reply):
    for scan_result in reply['apScan']:
      ap, unused = AccessPoint.objects.get_or_create(BSSID=scan_result['MAC'])
      ScanResult.objects.filter(myself_ap=ap).all().delete()
      for entry in scan_result['resultList']:
        neighbor_ap, unused = AccessPoint.objects.get_or_create(BSSID=entry['BSSID'])
        neighbor_ap.SSID = entry['SSID']
        neighbor_ap.channel = freq_to_channel(entry['frequency'])
        neighbor_ap.client_num = entry.get('stationCount', None)
        neighbor_ap.load = entry.get('bssLoad', None)
        neighbor_ap.save()

        ScanResult(myself_ap=ap, neighbor=neighbor_ap, signal=entry['RSSI'], timestamp=parser.parse(scan_result['timestamp'])).save()


  def handle_station_dump(self, reply):
    station_dump = reply['stationDump']
    for band, channels in [('band2g', settings.BAND2G_CHANNELS), ('band5g', settings.BAND5G_CHANNELS)]:
      if not AccessPoint.objects.filter(MAC=station_dump['MAC'], channel__in=channels).exists():
        logger.error("Access point %s at %s does not exist." % (station_dump['MAC'], band))
        continue
      ap = AccessPoint.objects.get(MAC=station_dump['MAC'], channel__in=channels)
      for station in station_dump[band]:
        sta, unused = Station.objects.get_or_create(MAC=station['MAC'])
        for attr, key in [('IP', 'IP'), ('inactive_time', 'inactiveTime'), ('rx_bytes', 'rxBytes'), ('rx_packets', 'rxPackets'),\
            ('tx_bytes', 'txBytes'), ('tx_packets', 'txPackets'), ('tx_fails', 'txFailures'), ('tx_retries', 'txRetries'),\
            ('signal_avg', 'avgSignal'), ('tx_bitrate', 'txBitrate'), ('rx_bitrate', 'rxBitrate')]:
          setattr(sta, attr, station.get(key, None))
        sta.sniffer_station = True
        sta.associate_with = ap
        sta.last_updated = parser.parse(station_dump['timestamp'])
        sta.save()



  def handle_phonelab_device(self, reply):
    for mac in reply['phonelabDevice']:
      sta, unused = Station.objects.get_or_create(MAC=mac)
      sta.phonelab_station = True
      sta.save()


  def handle_client_scan(self, reply):
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


  def handle_client_traffic(self, reply):
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


  def handle_client_latency(self, reply):
    for latency in reply['clientLatency']:
      if not Station.objects.filter(MAC=latency['MAC']).exists():
        logger.error("Station %s does not exist." % (latency['MAC']))
        continue
      sta = Station.objects.get(MAC=latency['MAC'])
      l = Latency(station=sta, timestamp=parser.parse(latency['timestamp']))
      for attr, key in [('host', 'host'), ('packet_transmitted', 'packetTransmitted'), ('packet_received', 'packetReceived'),\
          ('min_rtt', 'minRTT'), ('max_rtt', 'maxRTT'), ('avg_rtt', 'avgRTT'), ('std_dev', 'stdDev')]:
        setattr(l, attr, latency[key])
      l.save()


  def handle_client_throughput(self, reply):
    for throughput in reply['clientThroughput']:
      if not Station.objects.filter(MAC=throughput['MAC']).exists():
        logger.error("Station %s does not exist." % (throughput['MAC']))
        continue
      sta = Station.objects.get(MAC=throughput['MAC'])
      t = Throughput(station=sta, timestamp=parser.parse(throughput['timestamp']))
      for attr, key in [('url', 'url'), ('success', 'success'), ('file_size', 'fileSize'),\
          ('duration', 'duration'), ('throughput', 'throughput')]:
        setattr(t, attr, throughput[key])
      t.save()




  HANDLER_MAPPING = {
      'apStatus': 'handle_ap_status',
      'apScan': 'handle_ap_scan',
      'stationDump': 'handle_station_dump',
      'phonelabDevice': 'handle_phonelab_device',
      'clientScan': 'handle_client_scan',
      'clientTraffic': 'handle_client_traffic',
      'clientLatency': 'handle_client_latency',
      'clientThroughput': 'handle_client_throughput',
      }

  def run(self):
    logger.debug("Handler thread running.")
    try:
      reply = json.loads(recv_all(self.conn))
    except:
      logger.exception("Failed to read reply from %s" % (self.ap))
      return

    try:
      validate(reply, REPLY_SCHEMA)
    except:
      logger.exception("Failed to validate reply.")
      logger.debug(json.dumps(reply))
      return

    logger.debug("Got reply from %s" % (self.ap))
    for t, handler in HandlerThread.HANDLER_MAPPING.items():
      try:
        if reply['request'].get(t, False):
          getattr(self, handler, None)(reply)
      except:
        logger.exception("Failed to handle %s" % (t))


def collect(request, **kwargs):
  sniffer_aps = AccessPoint.objects.filter(sniffer_ap=True).exclude(IP=None)
  logger.debug("%d sniffer aps (with ip_addr) found." % (len(sniffer_aps)))
  if 'limit_aps' in kwargs:
    sniffer_aps = sniffer_aps.filter(MAC__in=kwargs['limit_aps'])
    logger.debug("Restricting to %d aps." % (len(sniffer_aps)))

  msg = json.dumps(request)
  
  logger.debug("Request msg: %s" % (msg))
  handler_threads = []
  for ap in sniffer_aps:
    try:
      logger.debug("Sending to %s:%s" % (ap.IP, settings.PUBLIC_TCP_PORT))
      conn = socket.create_connection((ap.IP, settings.PUBLIC_TCP_PORT))
      conn.sendall(msg)
      conn.shutdown(socket.SHUT_WR)
      t = HandlerThread(conn, ap)
      t.start()
      handler_threads.append(t)
    except:
      logger.exception("Failed to send msg to %s" % (ap))

  logger.debug("Waiting for responses.")
  try:
    for t in handler_threads:
      t.join()
  except KeyboardInterrupt:
    sys.exit()
