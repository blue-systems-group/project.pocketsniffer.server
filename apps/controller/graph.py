import os
import json
from collections import Counter
from datetime import datetime as dt
from itertools import chain
import numpy as np

from libs.common.graph import Figure
from apps.controller.models import MeasurementHistory, ThroughputResult

FIGURE_DIR = os.path.join(os.path.dirname(__file__), 'graph')

ALGORITHMS = [
    # 'NoAssignment',
    'RandomAssignment',
    'WeightedGraphColor',
    'TerminalCount',
    'TrafficAware',
    ]

# BEGIN = dt(2015, 2, 27, 03, 50); END = dt(2015, 2, 27, 14, 33)
# BEGIN = dt(2015, 2, 27, 14, 33); END = dt(2015, 2, 27, 16, 38)
# BEGIN = dt(2015, 2, 27, 16, 38); END = dt(2015, 2, 27, 18, 57)
# BEGIN = dt(2015, 2, 27, 18, 57); END = dt(2015, 2, 28, 04, 16)
# BEGIN = dt(2015, 2, 28, 04, 16); END = dt(2015, 2, 28, 19, 21)
# BEGIN = dt(2015, 2, 28, 19, 21); END = dt(2015, 3, 01, 02, 57)
# BEGIN = dt(2015, 03, 01, 02, 59); END = dt(2015, 03, 01, 17, 8)
# BEGIN = dt(2015, 03, 1, 22, 46); END = dt(2015, 3, 2, 0, 22) # UDP+TCP, 2 AP, 1-4 # clinets
# BEGIN = dt(2015, 03, 02, 2, 34); END = dt(2015, 3, 2, 4, 20)
# BEGIN = dt(2015, 03, 02, 5, 00); END = dt(2015, 3, 2, 6, 13) 
BEGIN = dt(2015, 03, 02, 23, 04); END = dt(2015, 3, 3, 2, 06) # UDP, single # # AP, 1-4 clients
# BEGIN = dt(2015, 03, 03, 2, 19); END = dt(2016, 3, 3, 2, 06) # TCP, single AP, 1-4 clients


MAX_CLIENT_NUM = 4
IGNORE_NO_CHAN_SWITCH = False

class ThroughputFigure(Figure):

  def __init__(self):
    super(ThroughputFigure, self).__init__(basedir=FIGURE_DIR)

  def plot(self):
    for n in range(1, MAX_CLIENT_NUM+1) + [None]:
      print "%s: %s clients." % (self.__class__.__name__, str(n) if n is not None else 'all' )
      data = self.get_data(client_num=n)

      for algo, bws in data.items():
        data[algo] = [round(b, 1) for b in bws]

      self.add_figure()
      ax = self.add_subplot(111)
      labels = []
      for algo in sorted(data.keys()):
        try:
          X = [round(x, 1) for x in np.arange(0, int(max(data[algo]))+1, 0.1)]
        except:
          print "No data for %s" % (algo)
          continue
        count = Counter(data[algo])
        PDF = [count.get(x, 0) for x in X]
        if algo.startswith('TrafficAware'):
          label = self.escape('TrafficAware')
        else:
          label = self.escape(algo)
        self.plot_cdf(ax, X, PDF, color=self.color, marker=self.marker, label=label)
        labels.append(label)

      ax.legend(loc='best', **self.legend_kwargs)

      if self.xlabel is not None:
        ax.set_xlabel('\\textbf{%s} (Mbps)' % (self.xlabel))

      if n is not None:
        self.save('%s-%d-clients' % (self.__class__.__name__, n))
      else:
        self.save('%s-all-cases' % (self.__class__.__name__))


class IndividualThroughputFigure(ThroughputFigure):

  def get_data(self, client_num):
    query = MeasurementHistory.objects.filter(begin1__gte=BEGIN, begin1__lte=END)
    algorithms = set(query.values_list('algo', flat=True))
    data = dict((a, []) for a in algorithms)

    for algo in algorithms:
      for measurement_history in query.filter(measurement=self.measurement, algo=algo).order_by('begin1'):
        active_client_num = ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2).count()

        if client_num is not None and active_client_num != client_num:
          continue

        for all_bw in ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2).values_list('all_bw', flat=True):
          data[algo].extend(json.loads(all_bw))

      print "%d bw for algo %s" % (len(data[algo]), algo)

    return data



class BSSThroughputFigure(ThroughputFigure):

  def get_data(self, client_num):
    query = MeasurementHistory.objects.filter(begin1__gte=BEGIN, begin1__lte=END)
    algorithms = set(query.values_list('algo', flat=True))
    data = dict((a, []) for a in algorithms)

    for algo in algorithms:
      for measurement_history in query.filter(measurement=self.measurement, algo=algo).order_by('begin1'):
        active_client_num = ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2).count()

        if client_num is not None and active_client_num != client_num:
          continue

        station_map = json.loads(measurement_history.station_map)

        if algo in ['TerminalCount', 'TrafficAware'] or algo.startswith('Traffic'):
          for ap, stas in station_map.items():
            station_map[ap] = list(chain.from_iterable(stas))

        for ap, stas in station_map.items():
          l = []
          for all_bw in ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2, station__MAC__in=stas).values_list('all_bw', flat=True):
            l.append(json.loads(all_bw))
          data[algo].extend([sum(x) for x in zip(*l)])

      print "%d bw for algo %s" % (len(data[algo]), algo)

    return data


class UDPIndividualThroughputFigure(IndividualThroughputFigure):

  def __init__(self):
    super(UDPIndividualThroughputFigure, self).__init__()
    self.measurement = 'iperf_udp'
    self.xlabel = 'Individual UDP Throughput'


class TCPIndividualThroughputFigure(IndividualThroughputFigure):

  def __init__(self):
    super(TCPIndividualThroughputFigure, self).__init__()
    self.measurement = 'iperf_tcp'
    self.xlabel = 'Individual TCP Throughput'


class UDPBSSThroughputFigure(BSSThroughputFigure):

  def __init__(self):
    super(UDPBSSThroughputFigure, self).__init__()
    self.measurement = 'iperf_udp'
    self.xlabel = 'BSS UDP Throughput'


class TCPBSSThroughputFigure(BSSThroughputFigure):

  def __init__(self):
    super(TCPBSSThroughputFigure, self).__init__()
    self.measurement = 'iperf_tcp'
    self.xlabel = 'BSS TCP Throughput'



class ThroughputImprovementFigure(Figure):

  def __init__(self):
    super(ThroughputImprovementFigure, self).__init__(basedir=FIGURE_DIR)
    self.measurement = 'iperf_tcp'
    self.xlabel = 'TCP Throughput Improvement'

  def get_improvements(self):
    pass

  def plot(self):
    data = self.get_improvements()

    MAX = max(chain.from_iterable(data.values()))
    print "Max improvement is %f" % (MAX)

    ax = self.add_subplot(111)
    X = [round(x, 2) for x in np.arange(-1, MAX, 0.01)]
    for algo in ALGORITHMS:
      count = Counter(data[algo])
      PDF = [count.get(x, 0) for x in X]
      self.plot_cdf(ax, X, PDF, color=self.color, marker=self.marker, label=algo)

    ax.legend(loc='best', **self.legend_kwargs)
    ax.set_xlim([-1, 1])

    if self.xlabel is not None:
      ax.set_xlabel('\\textbf{%s}' % (self.xlabel))

    self.save()


ALL_FIGURES = [
    UDPIndividualThroughputFigure,
    UDPBSSThroughputFigure,
    #TCPIndividualThroughputFigure,
    #TCPBSSThroughputFigure,
    ]
