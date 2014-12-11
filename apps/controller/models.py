from django.db import models


MAX_SSID_LENGTH = 64
BSSID_LENGTH = 17


class AccessPoint(models.Model):

  SSID = models.CharField(max_length=MAX_SSID_LENGTH, blank=True, null=True, default=None, db_index=True)
  BSSID = models.CharField(max_length=BSSID_LENGTH, primary_key=True)
  frequency = models.IntegerField(db_index=True)
  client_num = models.IntegerField(db_index=True, null=True)
  load = models.FloatField(null=True)


  is_sniffer_ap = models.BooleanField(default=False)
  tx_power_dbm = models.IntegerField(null=True)

  neighbor_aps = models.ManyToManyField('self', through='NeighborAP', through_fields=('myself', 'neighbor'), symmetrical=False)


class NeighborAP(models.Model):
  myself = models.ForeignKey(AccessPoint, related_name='myself')
  neighbor = models.ForeignKey(AccessPoint, related_name='neighbor')
  signal = models.IntegerField(null=True)
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
