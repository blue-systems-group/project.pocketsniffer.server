import json

from django.db import models


MAX_SSID_LENGTH = 64
BSSID_LENGTH = 17


class AccessPoint(models.Model):

  BSSID_2g = models.CharField(max_length=BSSID_LENGTH)
  BSSID_5g = models.CharField(max_length=BSSID_LENGTH)

  SSID_2g = models.CharField(max_length=MAX_SSID_LENGTH, blank=True, null=True, default=None, db_index=True)
  SSID_5g = models.CharField(max_length=MAX_SSID_LENGTH, blank=True, null=True, default=None, db_index=True)

  chan_2g = models.IntegerField(db_index=True)
  chan_5g = models.IntegerField(db_index=True)

  client_num_2g = models.IntegerField(db_index=True, null=True)
  client_num_5g = models.IntegerField(db_index=True, null=True)

  load_2g = models.FloatField(null=True)
  load_5g = models.FloatField(null=True)

  is_sniffer_ap = models.BooleanField(default=False)

  tx_power_dbm_2g = models.IntegerField(null=True)
  tx_power_dbm_5g = models.IntegerField(null=True)

  wan_mac = models.CharField(max_length=BSSID_LENGTH)
  wan_ip_addr = models.CharField(max_length=128, null=True)

  neighbor_aps = models.ManyToManyField('self', through='NeighborAP', through_fields=('myself', 'neighbor'), symmetrical=False)


  def __repr__(self):
    d = {}
    for attr in ['SSID', 'BSSID', 'wan_mac', 'wan_ip', 'is_sniffer_ap']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)



class NeighborAP(models.Model):
  myself = models.ForeignKey(AccessPoint, related_name='myself')
  neighbor = models.ForeignKey(AccessPoint, related_name='neighbor')
  signal_2g = models.IntegerField(null=True)
  signal_5g = models.IntegerField(null=True)
  last_updated = models.DateTimeField(auto_now=True)



class Station(models.Model):
  mac = models.CharField(max_length=BSSID_LENGTH, primary_key=True)

  is_sniffer_client = models.BooleanField(default=False)

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

  associcated_ap = models.ForeignKey(AccessPoint, related_name='associated_stations')

  scanned_aps = models.ManyToManyField(AccessPoint, through='ScanResult', through_fields=('station', 'ap'), symmetrical=False, related_name='nearby_stations')

  def __repr__(self):
    d = {}
    for attr in ['mac', 'is_sniffer_ap']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)



class ScanResult(models.Model):
  station = models.ForeignKey(Station)
  ap = models.ForeignKey(AccessPoint)
  signal = models.IntegerField(null=True)
  last_updated = models.DateTimeField(auto_now=True)


class Traffic(models.Model):
  station = models.ForeignKey(Station)
  ap = models.ForeignKey(AccessPoint)
  begin = models.DateTimeField(null=True)
  end = models.DateTimeField(null=True)
  tx_bytes = models.BigIntegerField(null=True)
  rx_bytes = models.BigIntegerField(null=True)
  last_updated = models.DateTimeField(auto_now=True)
