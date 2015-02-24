import os
from django.core.management.base import BaseCommand, CommandError

from apps.controller.tasks import trigger_measurement, MEASUREMENT_TASK_ID_FILE
from celery.task.control import revoke

class Command(BaseCommand):
  args = '<start|stop|restart> [min_interval=??] [max_interval=??]'

  def handle(self, *args, **options):

    if len(args) < 1:
      raise CommandError("No action.")

    action = args[0]

    if action not in ['start', 'stop', 'restart']:
      raise CommandError("Unknown action: %s" % (action))

    try:
      with open(MEASUREMENT_TASK_ID_FILE, 'r') as f:
        task_id = f.read().strip()
    except:
      task_id = None

    if task_id is not None:
      self.stdout.write("Found ongoing task %s" % (task_id))

    if action == 'stop' and task_id is None:
      raise CommandError("No previous measurement task found.")

    if action == 'start' and task_id is not None:
      self.stdout.write("Measurement task is already running.")
      return

    try:
      os.remove(MEASUREMENT_TASK_ID_FILE)
    except:
      pass

    if action == 'stop' or (action == 'restart' and task_id is not None):
      self.stdout.write("Revoking task %s" % (task_id))
      revoke(task_id, terminate=True, signal='SIGKILL')

      if action == 'stop':
        self.stdout.write("Stopped measurement task.")
        return


    kwargs = dict(tuple(p.split('=')) for p in args if '=' in p)
    args = [a for a in args if '=' not in a]

    trigger_measurement.delay(*args, **kwargs)
