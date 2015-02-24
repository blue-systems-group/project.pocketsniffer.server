import os
from django.core.management.base import BaseCommand, CommandError

from apps.controller.tasks import server_task, SERVER_TASK_ID_FILE
from celery.task.control import revoke

class Command(BaseCommand):
  args = '<start|stop|restart>'

  def handle(self, *args, **options):

    if len(args) < 1:
      raise CommandError("No action.")

    action = args[0]

    if action not in ['start', 'stop', 'restart']:
      raise CommandError("Unknown action: %s" % (action))

    try:
      with open(SERVER_TASK_ID_FILE, 'r') as f:
        task_id = f.read().strip()
    except:
      task_id = None

    if task_id is not None:
      self.stdout.write("Found ongoing task %s" % (task_id))

    if action == 'stop' and task_id is None:
      raise CommandError("No previous server task found.")

    if action == 'start' and task_id is not None:
      self.stdout.write("Server task is already running.")
      return

    try:
      os.remove(SERVER_TASK_ID_FILE)
    except:
      pass

    if action == 'stop' or (action == 'restart' and task_id is not None):
      self.stdout.write("Revoking task %s" % (task_id))
      revoke(task_id, terminate=True, signal='SIGKILL')

      if action == 'stop':
        self.stdout.write("Stopped server task.")
        return


    kwargs = dict(tuple(p.split('=')) for p in args if '=' in p)
    args = [a for a in args if '=' not in a]

    server_task.delay(*args, **kwargs)
