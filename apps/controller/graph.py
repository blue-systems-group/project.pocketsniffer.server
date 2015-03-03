import os
import json
from collections import Counter
from datetime import datetime as dt
from itertools import chain
import numpy as np

from matplotlib.artist import setp

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
# BEGIN = dt(2015, 03, 02, 23, 04); END = dt(2015, 3, 3, 2, 06) # UDP uplink, single # # AP, 1-4 clients
# BEGIN = dt(2015, 03, 03, 2, 19); END = dt(2015, 3, 3, 5, 16) # TCP uplink, single AP, 1-4 clients
BEGIN = dt(2015, 3, 3, 20, 38); END = dt(2016, 3, 3, 2, 06) # TCP downlink, single AP, 1-4 clients


MAX_CLIENT_NUM = 4
IGNORE_NO_CHAN_SWITCH = False

class ThroughputComaprisonFigure(Figure):

  def __init__(self):
    super(ThroughputComaprisonFigure, self).__init__(basedir=FIGURE_DIR)

  def get_data(self):
    measurement_history_query = MeasurementHistory.objects.filter(begin1__gte=BEGIN, begin1__lte=END)
    algorithms = set(measurement_history_query.values_list('algo', flat=True))
    data = dict((a, dict((n, []) for n in range(1, MAX_CLIENT_NUM+1))) for a in algorithms)

    for algo in algorithms:
      for measurement_history in measurement_history_query.filter(measurement=self.measurement, algo=algo).order_by('begin1'):
        station_map = json.loads(measurement_history.station_map)

        if algo in ['TerminalCount', 'TrafficAware'] or algo.startswith('Traffic'):
          for ap, stas in station_map.items():
            station_map[ap] = list(chain.from_iterable(stas))

        for ap, stas in station_map.items():
          throughput_result_query = ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2, station__MAC__in=stas)
          active_client_num = throughput_result_query.count()
          if active_client_num == 0:
            continue

          self.collect_one_ap(data[algo][active_client_num], throughput_result_query)

    return data


  def plot(self):
    data = self.get_data()
    total_width = 0.8
    width = total_width/len(data)

    X = np.arange(1, MAX_CLIENT_NUM+1)
    X = np.append(X, [MAX_CLIENT_NUM+2])
    print X

    legend_lines = []

    ax = self.add_subplot(111)
    ax.axvline(x=MAX_CLIENT_NUM+1, linewidth=1, color='k')

    for offset, algo in zip(range(0, len(data)), sorted(data.keys())):
      Y = [data[algo][n] for n in range(1, MAX_CLIENT_NUM+1)]
      Y.append(list(chain.from_iterable(Y)))
      print [len(l) for l in Y]

      if algo.startswith('TrafficAware'):
        label = 'TrafficAware'
      else:
        label = algo

      lines = ax.boxplot(Y, positions=X-total_width/2+offset*width+width/2, widths=0.6*width, whis=100, patch_artist=True)

      color = self.color

      for l in ['boxes', 'whiskers', 'caps', 'medians']:
        setp(lines[l], linewidth=0.8, color=color, linestyle='solid')
      setp(lines['boxes'], facecolor='w')

      ax.set_xlim([total_width/2, max(X)+total_width])
      ax.set_xticks([x for x in X])

      l, = ax.plot([1,1], '-', color=color, label=label)
      legend_lines.append(l)

      ax.set_xticklabels([str(i) for i in range(1, MAX_CLIENT_NUM+1)] + [self.escape('all_cases')])

    ax.legend(loc='upper left', bbox_to_anchor=(0.05, 1.2), ncol=len(data.keys())/2,  **self.legend_kwargs)

    for l in legend_lines:
      l.set_visible(False)

    ax.set_xlabel('\\textbf{Active Client Number}')
    ax.set_ylabel('\\textbf{%s} (Mbps)' % (self.ylabel))
    self.save()


class IndividualThroughputComaprisonFigure(ThroughputComaprisonFigure):

  def collect_one_ap(self, l, query):
    l.extend(query.values_list('bw', flat=True))


class BSSThroughputComaprisonFigure(ThroughputComaprisonFigure):

  def collect_one_ap(self, l, query):
    l.append(sum(query.values_list('bw', flat=True)))


class UDPIndividualThroughputComparisonFigure(IndividualThroughputComaprisonFigure):

  def __init__(self):
    super(UDPIndividualThroughputComparisonFigure, self).__init__()
    self.measurement = 'iperf_udp'
    self.ylabel = 'Individual UDP Throughput'


class UDPBSSThroughputComparisonFigure(BSSThroughputComaprisonFigure):

  def __init__(self):
    super(UDPBSSThroughputComparisonFigure, self).__init__()
    self.measurement = 'iperf_udp'
    self.ylabel = 'BSS UDP Throughput'

class TCPUplinkIndividualThroughputComparisonFigure(IndividualThroughputComaprisonFigure):

  def __init__(self):
    super(TCPUplinkIndividualThroughputComparisonFigure, self).__init__()
    self.measurement = 'iperf_tcp'
    self.ylabel = 'Individual TCP Throughput'


class TCPBSSUplinkThroughputComparisonFigure(BSSThroughputComaprisonFigure):

  def __init__(self):
    super(TCPBSSUplinkThroughputComparisonFigure, self).__init__()
    self.measurement = 'iperf_tcp'
    self.ylabel = 'BSS TCP Throughput'

class TCPDownlinkIndividualThroughputComparisonFigure(IndividualThroughputComaprisonFigure):

  def __init__(self):
    super(TCPDownlinkIndividualThroughputComparisonFigure, self).__init__()
    self.measurement = 'iperf_tcp_downlink'
    self.ylabel = 'Individual TCP Downlink Throughput'


class TCPBSSDownlinkThroughputComparisonFigure(BSSThroughputComaprisonFigure):

  def __init__(self):
    super(TCPBSSDownlinkThroughputComparisonFigure, self).__init__()
    self.measurement = 'iperf_tcp_downlink'
    self.ylabel = 'BSS TCP Downlink Throughput'













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
    measurement_history_query = MeasurementHistory.objects.filter(begin1__gte=BEGIN, begin1__lte=END)
    algorithms = set(measurement_history_query.values_list('algo', flat=True))
    data = dict((a, []) for a in algorithms)

    for algo in algorithms:
      for measurement_history in measurement_history_query.filter(measurement=self.measurement, algo=algo).order_by('begin1'):
        active_client_num = ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2).count()

        if client_num is not None and active_client_num != client_num:
          continue

        for all_bw in ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2).values_list('all_bw', flat=True):
          data[algo].extend(json.loads(all_bw))

      print "%d bw for algo %s" % (len(data[algo]), algo)

    return data



class BSSThroughputFigure(ThroughputFigure):

  def get_data(self, client_num):
    measurement_history_query = MeasurementHistory.objects.filter(begin1__gte=BEGIN, begin1__lte=END)
    algorithms = set(measurement_history_query.values_list('algo', flat=True))
    data = dict((a, []) for a in algorithms)

    for algo in algorithms:
      for measurement_history in measurement_history_query.filter(measurement=self.measurement, algo=algo).order_by('begin1'):
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
    # UDPIndividualThroughputComparisonFigure,
    # UDPBSSThroughputComparisonFigure,
    # TCPUplinkIndividualThroughputComparisonFigure,
    # TCPBSSUplinkThroughputComparisonFigure,
    TCPDownlinkIndividualThroughputComparisonFigure,
    TCPBSSDownlinkThroughputComparisonFigure,
    # UDPIndividualThroughputFigure,
    # UDPBSSThroughputFigure,
    #TCPIndividualThroughputFigure,
    #TCPBSSThroughputFigure,
    ]
