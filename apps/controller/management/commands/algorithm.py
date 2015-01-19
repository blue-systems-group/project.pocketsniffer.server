from datetime import datetime as dt

from django.core.management.base import BaseCommand, CommandError

from celery.task.control import revoke

from apps.controller.algorithms import StaticAssignment, RandomAssignment, WeightedGraphColor, OurAlgorithm
from apps.controller.tasks import run_algorithm
from apps.controller.models import AlgorithmHistory

ALGORITHM_MAPPING = dict((a.__name__, a) for a in [StaticAssignment, RandomAssignment, WeightedGraphColor, OurAlgorithm])

class Command(BaseCommand):
  args = '<algo> <action> [options]'
  help = 'Start/stop algorithm.'

  def handle(self, *args, **options):
    if len(args) < 2:
      raise CommandError("No algorithms or actions given.")

    algo, action = args[0], args[1]

    if algo not in ALGORITHM_MAPPING:
      raise CommandError("No such algorithm: %s" % (algo))

    if action not in ['start', 'stop', 'restart']:
      raise CommandError("Unknown action: %s" % (action))

    history = AlgorithmHistory.objects.filter(algo=algo, end=None)


    if action == 'stop' and not history.exists():
      raise CommandError("No previous %s instance found." % (algo))

    if action == 'start' and history.exists():
      self.stdout.write("Algorithm %s is already running." % (algo))
      return

    if action == 'stop' or (action == 'restart' and history.exists()):
      history = history[0]
      revoke(history.celery_task_id, terminate=True)
      history.end = dt.now()
      history.save()

      if action == 'stop':
        self.stdout.write("%s terminated." % (algo))
        return

    self.stdout.write("Starting %s." % (algo))
    run_algorithm.delay(ALGORITHM_MAPPING[algo], *(args[2:]), **options)
