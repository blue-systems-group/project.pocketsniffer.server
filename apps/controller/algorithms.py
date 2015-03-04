import logging
import json
import random


from django.conf import settings
from django.db.models import Q

from apps.controller.models import AccessPoint, ScanResult, Station, Traffic, AlgorithmHistory
import measure

logger = logging.getLogger('controller')

 


class Algorithm(object):

  def __init__(self, *args, **kwargs):
    self.need_scan_result = False
    self.need_traffic = False

  def get_new_channel(self, ap):
    pass

  @property
  def name(self):
    return self.__class__.__name__

  def run(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)

    if 'ap' in kwargs:
      target_aps = [kwargs['ap']]
    else:
      target_aps = AccessPoint.objects.filter(last_updated__gte=self.begin, sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS)


    for m in [ScanResult, AccessPoint, Station, Traffic]:
      logger.debug("%d new %s." % (m.objects.filter(last_updated__gte=self.begin).count(), m.__name__))

    for ap in target_aps:
      h_index, new_channel = self.get_new_channel(ap)
      if new_channel != ap.channel:
        logger.debug("Assign AP %s with new channel %d (was %d)" % (ap.BSSID, new_channel, ap.channel))
        measure.Request({'action': 'apConfig', 'band2g': {'channel': new_channel}}).send(ap.BSSID)
      else:
        logger.debug("AP %s stays on channel %d" % (ap.BSSID, ap.channel))

      history = AlgorithmHistory(algo=self.__class__.__name__, ap=ap)
      history.channel_dwell_time = kwargs.get('channel_dwell_time', None)
      history.channel_before = ap.channel
      history.channel_after = new_channel
      history.h_index = json.dumps(h_index)
      history.save()




class NoAssignment(Algorithm):

  def __init__(self, *args, **kwargs):
    super(NoAssignment, self).__init__(*args, **kwargs)
    self.need_scan_result = False
    self.need_traffic = False

  def get_new_channel(self, ap):
    return dict(), ap.channel


class RandomAssignment(Algorithm):

  def __init__(self, *args, **kwargs):
    super(RandomAssignment, self).__init__(*args, **kwargs)
    self.need_scan_result = False
    self.need_traffic = False


  def get_new_channel(self, ap):
    return dict(), random.choice(settings.BAND2G_CHANNELS)




class WeightedGraphColor(Algorithm):

  def __init__(self, *args, **kwargs):
    super(WeightedGraphColor, self).__init__(*args, **kwargs)
    self.need_scan_result = True
    self.need_traffic = False


  def get_new_channel(self, ap):

    logger.debug("%d neighbors" % (ScanResult.objects.filter(last_updated__gte=self.begin, myself_ap=ap).count()))

    H = dict()
    for c in settings.BAND2G_CHANNELS:
      h = []
      for neighbor_id in ScanResult.objects.filter(last_updated__gte=self.begin, myself_ap=ap).values_list('neighbor', flat=True):
        neighbor = AccessPoint.objects.get(id=neighbor_id)
        h.append(self.Ifactor(c, neighbor.channel)*self.weight(ap, neighbor))
      H[c] = max([0] + h)
    logger.debug("[%s] [%s] H index: %s" % (self.__class__.__name__, ap.BSSID, str(H)))
    min_h = min(H.values())
    candidates = [c for c in settings.BAND2G_CHANNELS if H[c] == min_h]
    return H, random.choice(candidates)


  def Ifactor(self, chan1, chan2):
    return 1 if chan1 == chan2 else 0


  def weight(self, ap1, ap2):
    client_num = 0
    overhear_num = 0

    for sta in Station.objects.filter(last_updated__gte=self.begin, sniffer_station=True, associate_with=ap1):
      client_num += 1
      if ScanResult.objects.filter(last_updated__gte=self.begin, myself_station=sta, neighbor=ap2).exists():
        overhear_num += 1

    if client_num == 0:
      return 0
    else:
      return float(overhear_num) / client_num


class TerminalCount(Algorithm):

  def __init__(self, *args, **kwargs):
    super(TerminalCount, self).__init__(*args, **kwargs)
    self.need_scan_result = True
    self.need_traffic = True

  def get_new_channel(self, ap):
    my_stas = Station.objects.filter(last_updated__gte=self.begin, sniffer_station=True, associate_with=ap, neighbor_station__isnull=True).all()

    H = dict()
    for c in settings.BAND2G_CHANNELS:
      terminals = set(Traffic.objects.filter(last_updated__gte=self.begin, for_device__in=my_stas, channel=c).exclude(src__in=[s.MAC for s in my_stas]).exclude(src=ap.BSSID).values_list('src', flat=True))
      terminals = terminals.union(ScanResult.objects.filter(last_updated__gte=self.begin, neighbor__channel=c).filter(Q(myself_ap=ap)|Q(myself_station__in=my_stas)).values_list('neighbor__BSSID', flat=True))
      H[c] = len(terminals)

    logger.debug("[%s] [%s] H index: %s" % (self.__class__.__name__, ap.BSSID, str(H)))
    return H, min(settings.BAND2G_CHANNELS, key=lambda t: H[t])


class TrafficAware(Algorithm):

  METRICS = ['packets', 'retry_packets', 'corrupted_packets']


  def __init__(self, *args, **kwargs):
    super(TrafficAware, self).__init__(*args, **kwargs)
    self.need_scan_result = False
    self.need_traffic = True

    self.weight = kwargs.get('weight', {'packets': 1, 'retry_packets': 0, 'corrupted_packets': 0})

  def get_new_channel(self, ap):
    my_stas = Station.objects.filter(last_updated__gte=self.begin, sniffer_station=True, associate_with=ap, neighbor_station__isnull=True).values_list('MAC', flat=True)
    H = dict()
    for c in settings.BAND2G_CHANNELS:
      H[c] = dict()
      for m in TrafficAware.METRICS:
        H[c][m] = sum(Traffic.objects.filter(last_updated__gte=self.begin, for_device__MAC__in=my_stas, channel=c).exclude(src__in=my_stas).exclude(src=ap.BSSID).values_list(m, flat=True))

    logger.debug("[%s] [%s] H index: %s" % (self.__class__.__name__, ap.BSSID, str(H)))

    max_c = dict((m, max([H[c][m] for c in settings.BAND2G_CHANNELS])) for m in TrafficAware.METRICS)
    for m in TrafficAware.METRICS:
      for c in settings.BAND2G_CHANNELS:
        if max_c[m] == 0:
          H[c][m] = 0
        else:
          H[c][m] = float(H[c][m]) / max_c[m]

    logger.debug("[%s] [%s] H index: %s" % (self.__class__.__name__, ap.BSSID, str(H)))
    return H, min(settings.BAND2G_CHANNELS, key=lambda c: sum([H[c][k]*v for k, v in self.weight.items()]))
