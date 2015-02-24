import logging
import random


from django.conf import settings

from apps.controller.models import AccessPoint, ScanResult, Station, Traffic, AlgorithmHistory
import measure

logger = logging.getLogger('controller')

 


class Algorithm(object):

  def get_new_channel(self, ap):
    pass


  def run(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)

    for ap in AccessPoint.objects.filter(sniffer_ap=True, channel__in=settings.BAND2G_CHANNELS):
      new_channel = self.get_new_channel(ap)
      if new_channel != ap.channel:
        measure.Request({'action': 'apConfig', 'band2g': {'channel': new_channel}}).send(ap.BSSID)

      history = AlgorithmHistory(algo=self.__class__.__name__, ap=ap)
      history.channel_dwell_time = kwargs.get('channel_dwell_time', None)
      history.channel_before = ap.channel
      history.channel_after = new_channel
      history.save()




class NoAssignment(Algorithm):

  def get_new_channel(self, ap):
    return ap.channel



class RandomAssignment(Algorithm):

  def get_new_channel(self, ap):
    return random.choice(settings.BAND2G_CHANNELS)



class WeightedGraphColor(Algorithm):

  def get_new_channel(self, ap):
    H = dict((c, max([self.Ifactor(ap, neighbor)*self.weight(ap, neighbor) for neighbor in ap.neighbor_aps.all()])) for c in settings.BAND2G_CHANNELS)
    logger.debug("[%s] H index: %s" % (ap.BSSID, str(H)))
    return min(settings.BAND2G_CHANNELS, key=lambda t: H[t])


  def Ifactor(self, ap1, ap2):
    if ap1.channel == ap2.channel:
      return 1
    else:
      return 0


  def weight(self, ap1, ap2):
    client_num = 0
    overhear_num = 0

    for sta in Station.objects.filter(associate_with=ap1):
      client_num += 1
      if ScanResult.objects.filter(last_updated__gte=self.begin, myself_station=sta, neighbor=ap2).exists():
        overhear_num += 1

    if client_num == 0:
      return 0
    else:
      return float(overhear_num) / client_num


class TrafficAware(Algorithm):

  def get_new_channel(self, ap):
    active_stas = Station.objects.filter(sniffer_station=True, associate_with=ap, neighbor_station_isnull=True).all()
    H = dict((c, sum([tfc.packets for tfc in Traffic.objects.filter(last_updated__gte=self.begin, for_device__in=active_stas, channel=c)])) for c in settings.BAND2G_CHANNELS)
    return min(settings.BAND2G_CHANNELS, key=lambda t: H[t])
