import json
import logging

from dateutil import parser

from django.db import models
from django.conf import settings
from datetime import datetime as dt


from libs.common.util import freq_to_channel


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
  neighbor_aps = models.ManyToManyField('self', through='ScanResult', through_fields=('myself_ap', 'neighbor'), symmetrical=False)

  last_updated = models.DateTimeField(null=True, default=None, auto_now=True)

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
        ap.save()

    for band, channels in [('band2g', range(1, 12)), ('band5g', range(36, 166))]:
      if not ap_status[band]['enabled']:
        try:
          ap = AccessPoint.objects.filter(MAC=['MAC'], enabled=True, channel__in=channels)[0]
          ap.enabled = False
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
          try:
            setattr(sta, attr, station.get(key, None))
          except:
            pass
        sta.sniffer_station = True
        sta.associate_with = ap
        sta.save()



class Station(models.Model):

  MAC = models.CharField(max_length=BSSID_LENGTH, null=True, default=None)

  associate_with = models.ForeignKey(AccessPoint, related_name='associated_stations', null=True, default=None, on_delete=models.CASCADE)

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

  neighbor_station = models.ForeignKey('Station', null=True, default=None, on_delete=models.CASCADE)

  last_updated = models.DateTimeField(null=True, default=None, auto_now=True)


  @classmethod
  def handle_neighbor_device(cls, nearby_devices):
    for neighbor_info in nearby_devices:
      try:
        sta = Station.objects.get(MAC=neighbor_info['MAC'])
      except:
        logger.exception("Station %s not found." % (neighbor_info['MAC']))
        continue

      has_neighbor = False
      for neighbor in neighbor_info['neighbors']:
        if not neighbor['interested']:
          continue
        try:
          sta.neighbor_station = Station.objects.get(MAC=neighbor['MAC'])
          sta.save()
          has_neighbor = True
          break
        except:
          logger.exception("Station %s not found." % (neighbor['MAC']))
          continue

      if not has_neighbor:
        sta.neighbor_station = None
        sta.save()


  @classmethod
  def handle_phonelab_device(cls, reply):
    for mac in reply['phonelabDevice']:
      sta, unused = Station.objects.get_or_create(MAC=mac)
      sta.phonelab_station = True
      sta.save()



  def __repr__(self):
    d = {}
    for attr in ['MAC', 'sniffer_station', 'phonelab_station', 'neighbor_station']:
      d[attr] = getattr(self, attr, None)
    return json.dumps(d)



class ScanResult(models.Model):
  myself_ap = models.ForeignKey(AccessPoint, related_name='myself_ap', null=True, default=None, on_delete=models.CASCADE)
  myself_station = models.ForeignKey(Station, related_name='myself_station', null=True, default=None, on_delete=models.CASCADE)
  neighbor = models.ForeignKey(AccessPoint, related_name='neighbor', null=True, default=None, on_delete=models.CASCADE)
  signal = models.IntegerField(null=True, default=None)
  timestamp = models.DateTimeField(null=True, default=None)
  last_updated = models.DateTimeField(null=True, default=None, auto_now=True)

  @classmethod
  def handle_client_scan(cls, client_scan):
    for scan_result in client_scan:
      sta, unused = Station.objects.get_or_create(MAC=scan_result['MAC'])
      for entry in scan_result['resultList']:
        neighbor_ap, unused = AccessPoint.objects.get_or_create(BSSID=entry['BSSID'])
        neighbor_ap.SSID = entry['SSID']
        neighbor_ap.channel = freq_to_channel(entry['frequency'])
        neighbor_ap.client_num = entry.get('stationCount', None)
        neighbor_ap.load = entry.get('bssLoad', None)
        neighbor_ap.save()

        ScanResult(myself_station=sta, neighbor=neighbor_ap, signal=entry['RSSI'], timestamp=parser.parse(scan_result['timestamp'])).save()

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
  timestamp = models.DateTimeField(null=True, default=None)
  hear_by = models.ForeignKey(Station, related_name='heard_traffic', null=True, default=None, on_delete=models.CASCADE)
  for_device = models.ForeignKey(Station, related_name='for_device', null=True, default=None)
  src = models.ForeignKey(Station, null=True, default=None, on_delete=models.CASCADE)
  begin = models.DateTimeField(null=True, default=None)
  end = models.DateTimeField(null=True, default=None)
  packets = models.BigIntegerField(null=True, default=None)
  retry_packets = models.BigIntegerField(null=True, default=None)
  avg_rssi = models.IntegerField(null=True, default=None)
  channel = models.IntegerField(null=True, default=None)
  last_updated = models.DateTimeField(null=True, default=None, auto_now=True)

  @classmethod
  def handle_client_traffic(cls, client_traffic):
    for traffic in client_traffic:
      origin_sta, unused = Station.objects.get_or_create(MAC=traffic['MAC'])
      for_device = Station.objects.get(MAC=traffic['forDevice'])
      for entry in traffic['traffics']:
        src, created = Station.objects.get_or_create(MAC=entry['src'])
        if created:
          src.save()

        tfc = Traffic(hear_by=origin_sta, for_device=for_device, src=src)
        tfc.begin = parser.parse(entry['begin'])
        tfc.end = parser.parse(entry['end'])
        tfc.timestamp = parser.parse(traffic['timestamp'])
        tfc.channel = entry['channel']
        tfc.packets = entry['packets']
        tfc.retry_packets = entry['retryPackets']
        tfc.avg_rssi = entry['avgRSSI']
        tfc.save()



class MeasurementHistory(models.Model):
  begin1 = models.DateTimeField(null=True, default=None)
  end1 = models.DateTimeField(null=True, default=None)

  begin2 = models.DateTimeField(null=True, default=None)
  end2 = models.DateTimeField(null=True, default=None)

  measurement = models.CharField(max_length=128, null=True, default=None)
  algo = models.CharField(max_length=128, null=True, default=None)

  def __repr__(self):
    return json.dumps({'begin': str(self.begin1), 'end': str(self.end2), 'algo': str(self.algo), 'measurement': str(self.measurement)})



class AlgorithmHistory(models.Model):
  last_updated = models.DateTimeField(null=True, auto_now=True, auto_now_add=True)
  algo = models.CharField(max_length=128, null=True, default=None)
  ap = models.ForeignKey(AccessPoint, null=True, default=None, on_delete=models.CASCADE)
  channel_dwell_time = models.IntegerField(null=True, default=None)
  channel_before = models.IntegerField(null=True, default=None)
  channel_after = models.IntegerField(null=True, default=None)

  def __repr__(self):
    return json.dumps({'algorithm': self.algo, 'ap': self.ap.BSSID, 'before': self.channel_before, 'after': self.channel_after})



class LatencyResult(models.Model):

  timestamp = models.DateTimeField(null=True, default=None)
  station = models.ForeignKey(Station, on_delete=models.CASCADE)
  pingArgs = models.CharField(max_length=128, null=True, default=None)
  packet_transmitted = models.IntegerField(default=0)
  packet_received = models.IntegerField(default=0)
  min_rtt = models.FloatField(default=0)
  max_rtt = models.FloatField(default=0)
  avg_rtt = models.FloatField(default=0)
  std_dev = models.FloatField(default=0)

  last_updated = models.DateTimeField(null=True, auto_now=True, auto_now_add=True)


  @classmethod
  def handle_client_latency(cls, client_latency):
    for entry in client_latency:
      r = LatencyResult()
      r.timestamp = parser.parse(entry['timestamp'])
      r.station = Station.objects.get(MAC=entry['MAC'])
      r.pingArgs = entry['pingArgs']

      for attr, key in [('packet_transmitted', 'packetTransmitted'), ('packet_received', 'packetReceived')]:
        setattr(r, attr, int(entry[key]))

      for attr, key in [('min_rtt', 'minRTT'), ('max_rtt', 'maxRTT'), ('avg_rtt', 'avgRTT'), ('std_dev', 'stdDev')]:
        setattr(r, attr, float(entry[key]))

      r.save()

  def __repr__(self):
    return json.dumps({'timestamp': str(self.timestamp), 'station': self.station.MAC, 'avg_rtt': self.avg_rtt})


class ThroughputResult(models.Model):

  timestamp = models.DateTimeField(null=True, default=None)
  station = models.ForeignKey(Station, on_delete=models.CASCADE)
  iperfArgs = models.CharField(max_length=128, null=True, default=None)
  all_bw = models.TextField(null=True, default=None)
  bw = models.FloatField(default=0)

  last_updated = models.DateTimeField(null=True, auto_now=True, auto_now_add=True)

  @classmethod
  def handle_client_throughput(cls, client_throughput):
    for entry in client_throughput:
      r = ThroughputResult()
      r.timestamp = parser.parse(entry['timestamp'])
      r.station = Station.objects.get(MAC=entry['MAC'])
      r.iperfArgs = entry['iperfArgs']

      r.all_bw = json.dumps(entry['bandwidths'])
      r.bw = float(entry['overallBandwidth'])

      r.save()

  def __repr__(self):
    return json.dumps({'timestamp': str(self.timestamp), 'station': self.station.MAC, 'bw': self.bw})



def cleanup_all():
  for m in [AccessPoint, Station, ScanResult, ThroughputResult, LatencyResult, Traffic, MeasurementHistory, AlgorithmHistory]:
    print "Deleting %s" % (str(m))
    m.objects.all().delete()
