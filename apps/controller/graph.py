import os
import logging
import json
from collections import Counter
from datetime import datetime as dt
import numpy as np
import itertools

from matplotlib.artist import setp

from libs.common.graph import Figure
from apps.controller.models import MeasurementHistory, ThroughputResult, AlgorithmHistory

FIGURE_DIR = os.path.join(os.path.dirname(__file__), 'graph')


logger = logging.getLogger('controller')

class ThroughputFigure(Figure):

  MEASUREMENT_NAME = {
      'iperf_udp': 'UDP_Uplink',
      'iperf_tcp': 'TCP_Uplink',
      'iperf_udp_downlink': 'UDP_Downlink',
      'iperf_tcp_downlink': 'TCP_Downlink',
      }

  def __init__(self, **kwargs):
    super(ThroughputFigure, self).__init__(basedir=FIGURE_DIR)

  def get_individual_throughputs(self, throughput_result_query):
    return list(throughput_result_query.values_list('bw', flat=True))

  def get_bss_throughputs(self, throughput_result_query):
    return [sum(throughput_result_query.values_list('bw', flat=True))]

  def get_data(self, bss, measurement):
    measurement_history_query = MeasurementHistory.objects.filter(begin1__gte=self.begin, begin1__lte=self.end, measurement=measurement)
    algorithms = set(measurement_history_query.values_list('algo', flat=True))
    data = dict((a, dict((n, []) for n in range(1, self.max_client_num+1))) for a in algorithms)

    client_mismatch = dict((a, 0) for a in algorithms)

    for algo in algorithms:
      for measurement_history in measurement_history_query.filter(algo=algo).order_by('begin1'):
        station_map = json.loads(measurement_history.station_map)

        if any([algo.startswith(s) for s in ['TerminalCount', 'TrafficAware']]):
          for ap, stas in station_map.items():
            station_map[ap] = list(itertools.chain.from_iterable(stas))

        for ap, stas in station_map.items():
          throughput_result_query = ThroughputResult.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2, station__MAC__in=stas)
          active_client_num = throughput_result_query.count()
          if active_client_num == 0:
            continue

          if measurement_history.client_num is not None and active_client_num != measurement_history.client_num:
            client_mismatch[algo] += 1
            continue

          if bss:
            data[algo][active_client_num].extend(self.get_bss_throughputs(throughput_result_query))
          else:
            data[algo][active_client_num].extend(self.get_individual_throughputs(throughput_result_query))

          algo_history_query = AlgorithmHistory.objects.filter(last_updated__gte=measurement_history.begin1, last_updated__lte=measurement_history.end2)
          assert algo_history_query.count() == 1

    return data


  def report(self, data):
    print('====================================================================')
    for algo, v in data.items():
      if algo.startswith('Traffic'):
          algo = 'TrafficAware'
      print('%20s: %s' % (algo, str(dict((n, len(v[n])/n) for n in range(1, self.max_client_num+1)))))
    print('====================================================================')


  def filename(self, bss, measurement):
    return '%s_%s_%s-[%s]' % ('BSS' if bss else 'Individual', ThroughputFigure.MEASUREMENT_NAME[measurement], self.placement, str(self.begin))

  def ylabel(self, bss, measurement):
    return self.escape('%s %s Throughput' % ('BSS' if bss else 'Individual', ThroughputFigure.MEASUREMENT_NAME[measurement].replace('_', ' ')))


  def plot(self):
    X = np.arange(1, self.max_client_num+1)
    X = np.append(X, [self.max_client_num+2])

    for bss, measurement in itertools.product([True, False], self.measurements):
      print('Plotting %s with bss = %s' % (measurement, bss))

      data = self.get_data(bss=bss, measurement=measurement)

      legend_lines = []

      self.add_figure()
      ax = self.add_subplot(111)
      ax.axvline(x=self.max_client_num+1, linewidth=1, color='k')

      total_width = 0.6
      width = total_width/len(data)

      for offset, algo in zip(range(0, len(data)), sorted(data.keys())):
        Y = [data[algo][n] for n in range(1, self.max_client_num+1)]
        Y.append(list(itertools.chain.from_iterable(Y)))

        if algo.startswith('TrafficAware'):
          label = 'TrafficAware'
        else:
          label = algo

        color = self.color

        lines = ax.boxplot(Y, positions=X-total_width/2+offset*width+width/2, widths=0.8*width, sym='', patch_artist=True)

        for l in ['boxes', 'whiskers', 'caps', 'medians']:
          setp(lines[l], linewidth=0.8, color=color, linestyle='solid')
        setp(lines['boxes'], facecolor='w')
        setp(lines['whiskers'], linewidth=0.4)

        ax.set_xlim([total_width/2, max(X)+1])
        ax.set_xticks([x for x in X])

        l, = ax.plot([1,1], '-', color=color, linewidth=1.5, label=label)
        legend_lines.append(l)

        ax.set_xticklabels([str(i) for i in range(1, self.max_client_num+1)] + [self.escape('All cases')])

      ax.legend(loc='upper left', bbox_to_anchor=(0.05, 1.2), ncol=len(data.keys())/2,  **self.legend_kwargs)

      for l in legend_lines:
        l.set_visible(False)

      ax.set_xlabel('\\textbf{Active Client Number}')
      ax.set_ylabel('\\textbf{%s} (Mbps)' % (self.ylabel(bss, measurement)))
      self.save(self.filename(bss, measurement))

      self.report(data)


EXPERIMENTS = [
    {
      'begin': dt(2015, 3, 2, 23, 4),
      'end': dt(2015, 3, 3, 5, 16),
      'measurements': ['iperf_udp', 'iperf_tcp'],
      'placement': 'static',
      'description': 'TCP/UDP uplink, singal AP, 1-4 clients, static placement',
      'max_client_num': 4,
      'plot': False,
      },
    {
      'begin': dt(2015, 3, 4, 4, 19),
      'end': dt(2016, 3, 4, 14, 46),
      'measurements': ['iperf_tcp_downlink', 'iperf_udp_downlink'],
      'placement': 'static',
      'description': 'TCP downlink, singal AP, 1-4 clients, static placement',
      'max_client_num': 4,
      'plot': False,
      },
    {
      'begin': dt(2015, 3, 5, 5, 30),
      'end': dt(2016, 3, 8, 14, 46),
      'measurements': ['iperf_tcp_downlink', 'iperf_udp_downlink'],
      'placement': 'static',
      'description': 'TCP downlink, singal AP, 1-4 clients, static placement. RTS enabled on router',
      'max_client_num': 4,
      'plot': True,
      },
 
    ]


def do_plot():
  for exp in EXPERIMENTS:
    if not exp['plot']:
      continue
    del exp['plot']
    f= ThroughputFigure()
    for k, v in exp.items():
      setattr(f, k, v)
    f.plot()
