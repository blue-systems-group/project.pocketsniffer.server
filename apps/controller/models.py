import json
import logging

from dateutil import parser

from django.db import models
from django.conf import settings


from lib.common.utils import freq_to_channel


MAX_SSID_LENGTH = 64
BSSID_LENGTH = 17

logger = logging.getLogger('controller')

class AccessPoint(models.Model):

  BSSID = models.CharField(max_length=BSSID_LENGTH, null=True, default=None)
  SSID = models.CharField(max_length=MAX_SSID_LENGTH, null=True, default=None)
  channel = models.IntegerField(null=True, default=None)
  client_num = models.IntegerField(null=True, default=None)
  load = models.FloatField(null=True, default=None)

  sniffer_ap = models.BooleanField(default=False)
  MAC = models.CharField(max_length=BSSID_LENGTH, null=True, default=None)
  IP  = models.CharField(null=True, max_length=128, default=None)
  tx_power = models.IntegerField(null=True, default=None)
  noise = models.IntegerField(null=True, default=None)
  enabled = models.BooleanField(default=True)
  last_status_update = models.DateTimeField(null=True, default=None)
  neighbor_aps = models.ManyToManyField('self', through='ScanResult', through_fields=('myself_ap', 'neighbor'), symmetrical=False)

  def __repr__(self):
    d = {}
    for attr in ['MAC', 'IP', 'SSID', 'BSSID', 'channel']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)

  @classmethod
  def handle_ap_status(cls, ap_status):
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

        ap.sniffer_ap = True
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


  @classmethod
  def handle_station_dump(cls, station_dump):
    for band, channels in [('band2g', settings.BAND2G_CHANNELS), ('band5g', settings.BAND5G_CHANNELS)]:
      if not AccessPoint.objects.filter(MAC=station_dump['MAC'], channel__in=channels).exists():
        logger.warn("Access point %s at %s does not exist." % (station_dump['MAC'], band))
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


  @classmethod
  def handle_ap_scan(cls, ap_scan):
    for scan_result in ap_scan:
      ap, unused = AccessPoint.objects.get_or_create(BSSID=scan_result['MAC'])
      for entry in scan_result['resultList']:
        neighbor_ap, unused = AccessPoint.objects.get_or_create(BSSID=entry['BSSID'])
        neighbor_ap.SSID = entry['SSID']
        neighbor_ap.channel = freq_to_channel(entry['frequency'])
        neighbor_ap.client_num = entry.get('stationCount', None)
        neighbor_ap.load = entry.get('bssLoad', None)
        neighbor_ap.save()

        ScanResult(myself_ap=ap, neighbor=neighbor_ap, signal=entry['RSSI'], timestamp=parser.parse(scan_result['timestamp'])).save()



class Station(models.Model):

  MAC = models.CharField(max_length=BSSID_LENGTH, null=True, default=None)

  associate_with = models.ForeignKey(AccessPoint, related_name='associated_stations', null=True, default=None)
  traffics = models.ManyToManyField(AccessPoint, related_name='station_traffic', through='Traffic', through_fields=('from_station', 'to_ap'), symmetrical=False)

  sniffer_station = models.BooleanField(default=False)
  phonelab_station = models.BooleanField(default=False)
  scan_results = models.ManyToManyField(AccessPoint, related_name='visible_stations', through='ScanResult', through_fields=('myself_station', 'neighbor'), symmetrical=False)

  IP = models.CharField(max_length=128, null=True, default=None)

  inactive_time = models.IntegerField(null=True, default=None)
  rx_bytes = models.BigIntegerField(null=True, default=None)
  rx_packets = models.BigIntegerField(null=True, default=None)
  tx_bytes = models.BigIntegerField(null=True, default=None)
  tx_packets = models.BigIntegerField(null=True, default=None)
  tx_retries = models.BigIntegerField(null=True, default=None)
  tx_fails = models.BigIntegerField(null=True, default=None)
  signal_avg = models.IntegerField(null=True, default=None)
  tx_bitrate = models.IntegerField(null=True, default=None)
  rx_bitrate = models.IntegerField(null=True, default=None)

  last_updated = models.DateTimeField(null=True, default=None)

  def __repr__(self):
    d = {}
    for attr in ['MAC', 'sniffer_station', 'phonelab_station']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)


class ScanResult(models.Model):
  myself_ap = models.ForeignKey(AccessPoint, related_name='myself_ap', null=True, default=None)
  myself_station = models.ForeignKey(Station, related_name='myself_station', null=True, default=None)
  neighbor = models.ForeignKey(AccessPoint, related_name='neighbor', null=True, default=None)
  signal = models.IntegerField(null=True, default=None)
  timestamp = models.DateTimeField(null=True, default=None)

  def __repr__(self):
    d = {}
    if self.myself_ap is not None:
      d['performed_by_ap'] = self.myself_ap.BSSID
    elif self.myself_station is not None:
      d['performed_by_station'] = self.myself_station.MAC
    d['neighbor'] = self.neighbor.BSSID
    d['signal'] = self.signal
    return json.dumps(d)




class Traffic(models.Model):
  hear_by = models.ForeignKey(Station, related_name='heard_traffic', null=True, default=None)
  for_sta = models.ForeignKey(Station, related_name='for_sta', null=True, default=None)
  from_station = models.ForeignKey(Station, null=True, default=None)
  to_ap = models.ForeignKey(AccessPoint, null=True, default=None)
  begin = models.DateTimeField(null=True, default=None)
  end = models.DateTimeField(null=True, default=None)
  tx_bytes = models.BigIntegerField(null=True, default=None)
  rx_bytes = models.BigIntegerField(null=True, default=None)
  avg_tx_rssi = models.IntegerField(null=True, default=None)
  avg_rx_rssi = models.IntegerField(null=True, default=None)
  channel = models.IntegerField(null=True, default=None)
  timestamp = models.DateTimeField(null=True, default=None)

  def __repr__(self):
    d = {}
    for attr in ['MAC', 'sniffer_station', 'phonelab_station']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)




class Latency(models.Model):
  station = models.ForeignKey(Station, null=True, default=None)
  timestamp = models.DateTimeField(null=True, default=None)
  host = models.CharField(max_length=128, null=True, default=None)
  packet_transmitted = models.IntegerField(null=True, default=None)
  packet_received = models.IntegerField(null=True, default=None)
  min_rtt = models.FloatField(null=True, default=None)
  max_rtt = models.FloatField(null=True, default=None)
  avg_rtt = models.FloatField(null=True, default=None)
  std_dev = models.FloatField(null=True, default=None)


class Throughput(models.Model):
  station = models.ForeignKey(Station, null=True, default=None)
  timestamp = models.DateTimeField(null=True, default=None)
  url = models.CharField(max_length=512, null=True, default=None)
  success = models.BooleanField(default=False)
  file_size = models.IntegerField(null=True, default=None)
  duration = models.IntegerField(null=True, default=None)
  throughput = models.FloatField(null=True, default=None)



class AlgorithmHistory(models.Model):
  algo = models.CharField(max_length=128)
  begin = models.DateTimeField(null=True, default=None)
  end = models.DateTimeField(null=True, default=None)
  celery_task_id = models.CharField(max_length=512, null=True, default=None)


class APConfigHistory(models.Model):
  timestamp = models.DateTimeField()
  ap = models.ForeignKey(AccessPoint)
  channel = models.IntegerField(null=True, default=None)
  txpower = models.IntegerField(null=True, default=None)
