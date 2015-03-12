import os
import sys
import logging
import traceback
import matplotlib
import numpy as np
from itertools import cycle
matplotlib.use('Agg')
from matplotlib import pyplot as plt, rc

tableau10 = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189)]
for i in range(0, len(tableau10)):
  r, g, b = tableau10[i]
  tableau10[i] = (r/255.0, g/255.0, b/255.0)



def pool_worker(f):
  def wrapper(*args, **kwargs):
    try:
      f(*args, **kwargs)
    except:
      raise Exception("".join(traceback.format_exception(*sys.exc_info())))
  return wrapper


class Figure(object):

  def __init__(self, basedir=os.path.realpath(__file__), width=4, height=3):
    try:
      os.makedirs(basedir)
    except:
      pass

    self.basedir = basedir
    self.width = width
    self.height = height
    self.legend_kwargs = {'numpoints': 1, 'markerscale': 1.5, 'fontsize': 'small'}
    self.plot_kwargs = {'linewidth': 0.3, 'markersize': 3, 'markeredgewidth': 0}

    self.add_figure()

    logging.basicConfig(format='[%(asctime)s] %(levelname)s [%(filename)32s:%(lineno)4d] %(message)s', level=logging.DEBUG)
    self.logger = logging.getLogger('Figure')


  

  @property
  def marker(self):
    return next(self.markers)

  @property
  def color(self):
    return next(self.colors)

  @property
  def hatch(self):
    return next(self.hatches)

  def add_figure(self):
    self.fig = plt.figure()
    self.markers = cycle('osD^')
    self.colors = cycle(tableau10)
    self.set_font()
    self.hatches = cycle(['/', '\\', '-', '|', '.', 'o', '*'])



  def add_subplot(self, *args, **kwargs):
    return self.fig.add_subplot(*args, **kwargs)

  def set_font(self):
    rc('font', **{'family': 'serif', 'serif': ['Times'], 'size':'9'})
    rc('text', usetex=True)

  def save(self, name=None, extension='.pdf', **kwargs):
    if name is None:
      name = self.__class__.__name__

    self.fig.set_size_inches(self.width, self.height)
    path = os.path.join(self.basedir, name + extension)
    self.fig.savefig(path, bbox_inches='tight', **kwargs)


  def plot(self, *args, **kwargs):
    self.logger.error("plot for %s is not implemented." % (self.__class__.__name__))

  def thin_border(self, ax, lw=0.5):
    for axis in ['top', 'bottom', 'left', 'right']:
      ax.spines[axis].set_linewidth(lw)

  def plot_cdf(self, ax, x, y, limit=None, lw=0.2, color='r', marker='*', label=None):
    cdf = np.divide(np.cumsum(y).astype(float), sum(y)).tolist()
    if limit is None:
      limit = len(cdf)
    x = x[:limit]
    ax.plot(x, cdf[:limit], '-' + color + marker, linewidth=lw, markersize=3, markeredgewidth=0, label=label)

    # ax.set_xlim([min(x), max(x)])
    ax.set_yticks(np.arange(0, 1.01, 0.1))
    ax.set_ylabel('\\textbf{CDF}')
    ax.grid(True)

    self.thin_border(ax)

  def escape(self, s):
    for special in ['_', '&']:
      s = ('\\'+special).join(s.split(special))
    return s
