import os
from collections import Counter
from datetime import datetime as dt
import numpy as np

from libs.common.graph import Figure
from apps.controller.models import MeasurementHistory, ThroughputResult, LatencyResult

FIGURE_DIR = os.path.join(os.path.dirname(__file__), 'graph')

ALGORITHMS = [
    'NoAssignment',
    # 'RandomAssignment',
    'WeightedGraphColor',
    'TerminalCount',
    'TrafficAware',
    ]

# BEGIN = dt(2015, 2, 27, 03, 50); END = dt(2015, 2, 27, 14, 33)
# BEGIN = dt(2015, 2, 27, 14, 33); END = dt(2015, 2, 27, 16, 38)
# BEGIN = dt(2015, 2, 27, 16, 38); END = dt(2015, 2, 27, 18, 57)
# BEGIN = dt(2015, 2, 27, 18, 57); END = dt(2015, 2, 27, 22, 34)
# BEGIN = dt(2015, 2, 28, 04, 16); END = dt(2016, 2, 27, 22, 34)
BEGIN = dt(2015, 2, 28, 19, 21); END = dt(2016, 2, 27, 22, 34)

class ThroughputFigure(Figure):

  def __init__(self):
    super(ThroughputFigure, self).__init__(basedir=FIGURE_DIR)
    self.measurement = 'iperf_tcp'
    self.xlabel = 'TCP Throughput Improvement'


  def plot(self):
    data = dict((a, []) for a in ALGORITHMS)

    sta_num = []

    for algo in ALGORITHMS:
      for history in MeasurementHistory.objects.filter(measurement=self.measurement, algo=algo, begin1__gte=BEGIN, begin1__lte=END).order_by('begin1'):
        sta_num.append(ThroughputResult.objects.filter(last_updated__gte=history.begin1, last_updated__lte=history.end1).count())
        for sta in ThroughputResult.objects.filter(last_updated__gte=history.begin1, last_updated__lte=history.end1).values_list('station', flat=True):
          before_bw = ThroughputResult.objects.filter(last_updated__gte=history.begin1, last_updated__lte=history.end1, station=sta).values_list('bw', flat=True)
          after_bw =  ThroughputResult.objects.filter(last_updated__gte=history.begin2, last_updated__lte=history.end2, station=sta).values_list('bw', flat=True)
          assert len(before_bw) == 1
          if len(after_bw) == 0:
            continue
          before_bw, after_bw = before_bw[0], after_bw[0]
          if before_bw > 0:
            data[algo].append(round((after_bw-before_bw)/before_bw, 2))

      print "%d measurments for algo %s" % (len(data[algo]), algo)

    print "Sta number: %s" % (str(Counter(sta_num)))

    MAX = max([0] + [max(data[a]) for a in ALGORITHMS if len(data[a]) > 0])
    print "Max improvement is %f" % (MAX)

    ax = self.add_subplot(111)
    X = [round(x, 2) for x in np.arange(-1, MAX, 0.01)]
    for algo in ALGORITHMS:
      count = Counter(data[algo])
      PDF = [count.get(x, 0) for x in X]
      self.plot_cdf(ax, X, PDF, color=self.color, marker=self.marker, label=algo)

    ax.legend(loc='best', **self.legend_kwargs)
    ax.set_xlim([-1, 2])

    if self.xlabel is not None:
      ax.set_xlabel('\\textbf{%s}' % (self.xlabel))

    self.save()


class TCPThroughputFigure(ThroughputFigure):

  def __init__(self):
    super(TCPThroughputFigure, self).__init__()
    self.measurement = 'iperf_tcp'
    self.xlabel = 'TCP Throughput Improvement'


class UDPThroughputFigure(ThroughputFigure):

  def __init__(self):
    super(UDPThroughputFigure, self).__init__()
    self.measurement = 'iperf_udp'
    self.xlabel = 'UDP Throughput Improvement'


class LatencyFigure(Figure):

  def __init__(self):
    super(LatencyFigure, self).__init__(basedir=FIGURE_DIR)
    self.measurement = 'latency'


  def plot(self):
    data = dict((a, []) for a in ALGORITHMS)

    for algo in ALGORITHMS:
      for history in MeasurementHistory.objects.filter(measurement=self.measurement, algo=algo, begin1__gte=BEGIN, begin1__lte=END).order_by('begin1'):
        for sta in LatencyResult.objects.filter(last_updated__gte=history.begin1, last_updated__lte=history.end1).values_list('station', flat=True):
          before_latency = LatencyResult.objects.filter(last_updated__gte=history.begin1, last_updated__lte=history.end1, station=sta).values_list(self.attr, flat=True)
          after_latency =  LatencyResult.objects.filter(last_updated__gte=history.begin2, last_updated__lte=history.end2, station=sta).values_list(self.attr, flat=True)
          assert len(before_latency) == 1
          if len(after_latency) == 0:
            continue
          before_latency, after_latency = before_latency[0], after_latency[0]
          if before_latency > 0:
            data[algo].append(round((before_latency-after_latency)/before_latency, 2))

      print "%d measurments for algo %s" % (len(data[algo]), algo)

    MIN = min([min(data[a]) for a in ALGORITHMS if len(data[a]) > 0])
    print "Min improvement is %f" % (MIN)

    ax = self.add_subplot(111)
    X = [round(x, 2) for x in np.arange(MIN, 1, 0.01)]
    for algo in ALGORITHMS:
      count = Counter(data[algo])
      PDF = [count.get(x, 0) for x in X]
      self.plot_cdf(ax, X, PDF, color=self.color, marker=self.marker, label=algo)

    ax.legend(loc='best', **self.legend_kwargs)
    ax.set_xlim([-2, 1])

    if self.xlabel is not None:
      ax.set_xlabel('\\textbf{%s}' % (self.xlabel))

    self.save()


class RTTFigure(LatencyFigure):

  def __init__(self):
    super(RTTFigure, self).__init__()
    self.attr = 'avg_rtt'
    self.xlabel = 'RTT Improvement'


class JitterFigure(LatencyFigure):

  def __init__(self):
    super(JitterFigure, self).__init__()
    self.attr = 'std_dev'
    self.xlabel = 'Jitter Improvement'




ALL_FIGURES = [
    TCPThroughputFigure,
    UDPThroughputFigure,
    RTTFigure,
    JitterFigure,
    ]
