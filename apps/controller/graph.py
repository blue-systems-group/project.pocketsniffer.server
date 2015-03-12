import os
import logging
import json
from collections import Counter
from datetime import datetime as dt
import numpy as np
from django.conf import settings
import itertools

from matplotlib.artist import setp

from libs.common.graph import Figure
from apps.controller.models import MeasurementHistory, ThroughputResult, AlgorithmHistory

FIGURE_DIR = os.path.join(os.path.dirname(__file__), 'graph')


logger = logging.getLogger('controller')

ALGORITHMS = ['RandomAssignment', 'WeightedGraphColor', 'TerminalCount', 'TrafficAware']
MEASUREMENT_NAME = {
    'iperf_udp': 'UDP_Uplink',
    'iperf_tcp': 'TCP_Uplink',
    'iperf_udp_downlink': 'UDP_Downlink',
    'iperf_tcp_downlink': 'TCP_Downlink',
    }


class ThroughputFigure(Figure):


  def __init__(self, **kwargs):
    super(ThroughputFigure, self).__init__(basedir=FIGURE_DIR)

  def get_individual_throughputs(self, throughput_result_query):
    return list(throughput_result_query.values_list('bw', flat=True))

  def get_bss_throughputs(self, throughput_result_query):
    return [sum(throughput_result_query.values_list('bw', flat=True))]

  def get_data(self, bss, measurement):
    data = dict((a, dict((n, []) for n in range(1, self.max_client_num+1))) for a in ALGORITHMS)
    used_counts = dict((a, 0) for a in ALGORITHMS)
    ignore_counts = dict((a, 0) for a in ALGORITHMS)

    for begin, end in self.periods:
      measurement_history_query = MeasurementHistory.objects.filter(begin1__gte=begin, begin1__lte=end, measurement=measurement)
      for algo in ALGORITHMS:
        for measurement_history in measurement_history_query.filter(algo=algo).order_by('begin1'):
          throughput_result_query = ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2)
          active_client_num = throughput_result_query.count()

          if measurement_history.client_num is not None and active_client_num != measurement_history.client_num:
            ignore_counts[algo] += 1
            continue

          if bss:
            new_data = self.get_bss_throughputs(throughput_result_query)
          else:
            new_data = self.get_individual_throughputs(throughput_result_query)

          data[algo][active_client_num].extend(new_data)
          used_counts[algo] += len(new_data)

    print '================================================================='
    print '%s %s %s %s' % ('BSS' if bss else 'Individual', self.placement, measurement, 'Jamming' if self.jamming else '')
    print '-----------------------------------------------------------------'
    for algo in ALGORITHMS:
      all_cases = list(itertools.chain.from_iterable(data[algo].values()))
      percentiles = ['%.2f' % (f) for f in [np.percentile(all_cases, n) for n in [10, 50, 90]]]
      print "[%20s] %20s [%d used, %d ignored] [%s]" % (algo, [len(data[algo][n]) for n in range(1, self.max_client_num+1)], used_counts[algo], ignore_counts[algo], percentiles)
    print '================================================================='

    return data


  def filename(self, bss, measurement):
    return '%s_%s_%s%s' % ('BSS' if bss else 'Individual', MEASUREMENT_NAME[measurement], self.placement, '_Jamming' if self.jamming else '')

  def ylabel(self, bss, measurement):
    return self.escape('%s %s Throughput' % ('BSS' if bss else 'Individual', MEASUREMENT_NAME[measurement].replace('_', ' ')))


  def plot(self):
    legend_fig = self.fig
    legend_ax = legend_fig.add_subplot(111)
    legend_ax.set_axis_off()

    for bss, measurement in itertools.product([True, False], self.measurements):
      data = self.get_data(bss=bss, measurement=measurement)

      legend_lines = []

      self.add_figure()
      ax = self.add_subplot(111)
      ax.axvline(x=self.max_client_num+1, linewidth=1, color='k')

      if bss:
        total_width = 0.75
      else:
        total_width = 0.6
      width = total_width/len(data)

      COLORS = ['r', 'k', 'b', 'g']

      for offset, algo, color in zip(range(0, len(data)), ALGORITHMS, COLORS):

        X = np.arange(1, self.max_client_num+1)
        Y = [data[algo][n] for n in range(1, self.max_client_num+1)]
        if bss:
          X = np.append(X, [self.max_client_num+2])
          Y.append(list(itertools.chain.from_iterable(Y)))

        if algo.startswith('TrafficAware'):
          label = 'TrafficAware'
        else:
          label = algo

        if bss:
          lines = ax.boxplot(Y, positions=X-total_width/2+offset*width+width/2, widths=0.6*width, sym='', whis=[10,90], patch_artist=True)
        else:
          lines = ax.boxplot(Y, positions=X-total_width/2+offset*width+width/2, widths=0.6*width, sym='', whis=[10,90], patch_artist=True)

        for line in ['whiskers', 'caps', 'fliers']:
          for l in lines[line]:
            l.set_visible(True)

        color = self.color

        for l in ['boxes', 'whiskers', 'caps', 'medians']:
          setp(lines[l], linewidth=1, color=color, linestyle='solid')
        setp(lines['medians'], color='w', linewidth=1)

        ax.set_xlim([total_width/2, max(X)+1])
        ax.set_xticks([x for x in X])

        l, = ax.plot([1,1], '-', color=color, linewidth=3, label=label)
        legend_lines.append(l)

        if bss:
          ax.set_xticklabels([str(i) for i in range(1, self.max_client_num+1)] + [self.escape('All cases')])
        else:
          ax.set_xticklabels([str(i) for i in range(1, self.max_client_num+1)])

      l = legend_ax.legend(legend_lines, ALGORITHMS, loc='center', ncol=len(ALGORITHMS), fontsize=10)
      l.get_frame().set_linewidth(0)
      legend_fig.savefig(os.path.join(FIGURE_DIR, 'legend.pdf'), bbox_inches='tight')

      for l in legend_lines:
        l.set_visible(False)

      ax.set_xlabel('\\textbf{Active Client Number}')
      ax.set_ylabel('\\textbf{%s} (Mbps)' % (self.ylabel(bss, measurement)))

      """
      if bss:
        ax.set_ylim(top=35)
      else:
        ax.set_ylim(top=25)
      """

      ax.get_xaxis().tick_bottom()  
      ax.get_yaxis().tick_left()

      self.thin_border(ax)
      self.save(self.filename(bss, measurement))



class ThroughputBarFigure(ThroughputFigure):


  def __init__(self, **kwargs):
    super(ThroughputBarFigure, self).__init__(basedir=FIGURE_DIR)


  def plot(self):
    legend_fig = self.fig
    legend_ax = legend_fig.add_subplot(111)
    legend_ax.set_axis_off()

    for bss, measurement in itertools.product([True, False], self.measurements):
      data = self.get_data(bss=bss, measurement=measurement)

      legend_lines = []

      self.add_figure()
      ax = self.add_subplot(111)
      ax.axvline(x=self.max_client_num+1, linewidth=1, color='k')

      if bss:
        total_width = 0.75
      else:
        total_width = 0.6
      width = total_width/len(data)

      for offset, algo in zip(range(0, len(data)), ALGORITHMS):

        X = np.arange(1, self.max_client_num+1)
        Y = [data[algo][n] for n in range(1, self.max_client_num+1)]
        if bss:
          X = np.append(X, [self.max_client_num+2])
          Y.append(list(itertools.chain.from_iterable(Y)))

        if algo.startswith('TrafficAware'):
          label = 'TrafficAware'
        else:
          label = algo

        color = self.color
        hatch = None

        left = X-total_width/2+offset*width
        height = [np.median(y) for y in Y]
        ax.bar(left, height, 0.8*width, color=color, linewidth=0, hatch=hatch, label=algo)

        ax.set_xlim([total_width/2, max(X)+1])
        ax.set_xticks([x for x in X])

        l, = ax.bar(0, 1,  color=color, linewidth=0, hatch=hatch, label=label)
        legend_lines.append(l)

        if bss:
          ax.set_xticklabels([str(i) for i in range(1, self.max_client_num+1)] + [self.escape('All cases')])
        else:
          ax.set_xticklabels([str(i) for i in range(1, self.max_client_num+1)])

      l = legend_ax.legend(legend_lines, ALGORITHMS, loc='center', ncol=len(ALGORITHMS), fontsize=10)
      l.get_frame().set_linewidth(0)
      legend_fig.savefig(os.path.join(FIGURE_DIR, 'legend.pdf'), bbox_inches='tight')

      for l in legend_lines:
        l.set_visible(False)

      ax.set_xlabel('\\textbf{Active Client Number}')
      ax.set_ylabel('\\textbf{%s} (Mbps)' % (self.ylabel(bss, measurement)))

      if bss:
        ax.set_ylim(top=35)
      else:
        ax.set_ylim(top=25)

      ax.get_xaxis().tick_bottom()  
      ax.get_yaxis().tick_left()

      self.thin_border(ax)
      self.save(self.filename(bss, measurement))





class ChannelBreakdownFigure(Figure):

  def __init__(self):
    super(ChannelBreakdownFigure, self).__init__(basedir=FIGURE_DIR)

  @property
  def filename(self):
    return '%s_%s%s' % (self.__class__.__name__, self.placement, '_Jamming' if self.jamming else '')
  

  def get_data(self):
    data = dict((algo, dict((c, 0) for c in settings.BAND2G_CHANNELS)) for algo in ALGORITHMS)

    for begin, end in self.periods:
      history_query = AlgorithmHistory.objects.filter(last_updated__gte=begin, last_updated__lte=end)
      for entry in history_query:
        data[entry.algo][entry.channel_after] += 1

    return data


  def plot(self):
    data = self.get_data()

    print '================================================'
    print self.filename
    for algo in ALGORITHMS:
      X = data[algo].values()
      index = float(sum(X)**2)/len(X)/sum([x**2 for x in X])
      print '%s: %.2f' % (algo, index)
    print '================================================'






class CorrectnessFigure(Figure):

  def __init__(self):
    super(CorrectnessFigure, self).__init__(basedir=FIGURE_DIR)

  @property
  def filename(self):
    return '%s_%s%s' % (self.__class__.__name__, self.placement, '_Jamming' if self.jamming else '')


  def get_data(self):

    data = dict((algo, {'correct': 0, 'wrong': 0}) for algo in ALGORITHMS)

    for begin, end in self.periods:
      measurement_history = MeasurementHistory.objects.filter(begin1__gte=begin, begin1__lte=end)
      algo_history = AlgorithmHistory.objects.filter(last_updated__gte=begin, last_updated__lte=end)

      for m_history in measurement_history:
        a_history = algo_history.filter(last_updated__gte=m_history.begin1, last_updated__lte=m_history.end2)
        if len(a_history) != 1:
          print "Algo mismatch: measurment id = %d" % (m_history.id)
          continue

        a_history = a_history[0]

        if a_history.channel_after == m_history.jamming_channel:
          data[a_history.algo]['wrong'] += 1
        else:
          data[a_history.algo]['correct'] += 1

    return data

  def plot(self):
    if not self.jamming:
      return

    
    data = self.get_data()

    print '================================================'
    print self.filename
    for algo in ALGORITHMS:
      ratio = float(data[algo]['correct'])/sum(data[algo].values())*100
      print '%s: %.2f%%' % (algo, ratio)
    print '================================================'



EXPERIMENTS = [
     {
       'periods': [(dt(2015, 3, 7, 0, 33), dt(2015, 3, 8, 5, 49)), (dt(2015, 3, 9, 22, 40), dt(2015, 3, 10, 14, 36))],
      'measurements': ['iperf_tcp', 'iperf_udp', 'iperf_tcp_downlink', 'iperf_udp_downlink'],
      'placement': 'Static',
      'jamming': True,
      'description': 'TCP downlink, singal AP, 1-4 clients, static placement. Random jamming channel.',
      'max_client_num': 4,
      'plot': True,
      },
     {
       'periods': [(dt(2015, 3, 8, 5, 57), dt(2015, 3, 9, 11, 19)), (dt(2015,3,10,22,26), dt(2015,3,11,13,55))],
      'measurements': ['iperf_tcp', 'iperf_udp', 'iperf_tcp_downlink', 'iperf_udp_downlink'],
      'placement': 'Static',
      'jamming': False,
      'description': 'TCP downlink, singal AP, 1-4 clients, static placement. No jamming.',
      'max_client_num': 4,
      'plot': True,
      },
     {
       'periods': [(dt(2015, 3, 10, 14, 41), dt(2015, 3, 10, 21, 24))],
      'measurements': ['iperf_tcp', 'iperf_tcp_downlink'],
      'placement': 'Mobile',
      'jamming': False,
      'max_client_num': 2,
      'plot': True,
      },
     {
       'periods': [(dt(2015, 3, 11, 14, 11), dt(2015, 3, 11, 18, 45)), (dt(2015,3,11,19,3), dt(2015,3,11,20,11))],
      'measurements': ['iperf_tcp', 'iperf_tcp_downlink'],
      'placement': 'Mobile',
      'jamming': True,
      'max_client_num': 2,
      'plot': True,
      },
 
    ]



FIGURES = [
    ThroughputFigure,
    ChannelBreakdownFigure,
    CorrectnessFigure,
    ]


def do_plot():
  for exp in EXPERIMENTS:
    if not exp['plot']:
      continue
    del exp['plot']
    for Fig in FIGURES:
      f= Fig()
      for k, v in exp.items():
        setattr(f, k, v)
      f.plot()
