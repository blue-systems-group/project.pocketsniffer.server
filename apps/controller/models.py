import json

from django.db import models


MAX_SSID_LENGTH = 64
BSSID_LENGTH = 17

class AccessPoint(models.Model):

  MAC = models.CharField(max_length=BSSID_LENGTH)
  BSSID = models.CharField(max_length=BSSID_LENGTH)
  SSID = models.CharField(max_length=MAX_SSID_LENGTH)
  channel = models.IntegerField()
  client_num = models.IntegerField(null=True)
  load = models.FloatField(null=True)

  sniffer_ap = models.BooleanField(default=False)
  tx_power = models.IntegerField(null=True)
  neighbor_aps = models.ManyToManyField('self', through='ScanResult', through_fields=('myself_ap', 'neighbor'), symmetrical=False)

  def __repr__(self):
    d = {}
    for attr in ['MAC', 'SSID', 'BSSID', 'channel']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)


class Station(models.Model):

  MAC = models.CharField(max_length=BSSID_LENGTH)

  associate_with = models.ForeignKey(AccessPoint, related_name='associated_stations')
  traffics = models.ManyToManyField(AccessPoint, related_name='station_traffic', through='Traffic', through_fields=('station', 'ap'), symmetrical=False)

  sniffer_station = models.BooleanField(default=False)
  scan_results = models.ManyToManyField(AccessPoint, related_name='visible_stations', through='ScanResult', through_fields=('myself_station', 'neighbor'), symmetrical=False)

  inactive_time = models.IntegerField(null=True)
  rx_bytes = models.BigIntegerField(null=True)
  rx_packets = models.BigIntegerField(null=True)
  tx_bytes = models.BigIntegerField(null=True)
  tx_packets = models.BigIntegerField(null=True)
  tx_retries = models.BigIntegerField(null=True)
  tx_fails = models.BigIntegerField(null=True)
  signal_avg = models.IntegerField(null=True)
  tx_bitrate_mbps = models.IntegerField(null=True)
  tx_bitrate_mbps = models.IntegerField(null=True)


class ScanResult(models.Model):
  myself_ap = models.ForeignKey(AccessPoint, related_name='myself_ap')
  myself_station = models.ForeignKey(Station, related_name='myself_station')
  neighbor = models.ForeignKey(AccessPoint, related_name='neighbor')
  signal = models.IntegerField(null=True)
  last_updated = models.DateTimeField(auto_now=True)


class Traffic(models.Model):
  hear_by = models.ForeignKey(Station, related_name='heard_traffic')
  station = models.ForeignKey(Station)
  ap = models.ForeignKey(AccessPoint)
  begin = models.DateTimeField(null=True)
  end = models.DateTimeField(null=True)
  tx_bytes = models.BigIntegerField(null=True)
  rx_bytes = models.BigIntegerField(null=True)
  avg_signal = models.IntegerField(null=True)
  last_updated = models.DateTimeField(auto_now=True)
