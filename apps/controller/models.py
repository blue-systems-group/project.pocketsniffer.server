import json

from django.db import models


MAX_SSID_LENGTH = 64
BSSID_LENGTH = 17

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
