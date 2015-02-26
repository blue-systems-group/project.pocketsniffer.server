from __future__ import absolute_import

import os
import logging
import socket
import time
import json
import random
from jsonschema import validate
from django.conf import settings

from celery import shared_task


from apps.controller.measure import ap_clean_up, do_measurement, MEASUREMENT_DURATION
from apps.controller.models import Traffic
from libs.common.util import get_iface_addr, recv_all

logger = logging.getLogger('controller')

MEASUREMENT_TASK_ID_FILE = '/tmp/measurement_task_id'
SERVER_TASK_ID_FILE = '/tmp/server_task_id'

HANDLER_MAPPING = {
    'clientTraffic': Traffic.handle_client_traffic,
    }

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'reply.json')) as f:
  REPLY_SCHEMA = json.loads(f.read())
 

@shared_task(bind=True)
def trigger_measurement(self, *args, **kwargs):
  logger.debug("Staring measurements, args = %s, kwargs = %s." % (str(args), str(kwargs)))

  with open(MEASUREMENT_TASK_ID_FILE, 'w') as f:
    print >>f, self.request.id

  min_interval = int(kwargs.get('min_interval', 0))
  max_interval = int(kwargs.get('max_interval', MEASUREMENT_DURATION))

  logger.debug("Interval range [%d, %d]" % (min_interval, max_interval))

  while True:
    ap_clean_up()
    do_measurement(**kwargs)

    if kwargs.get('oneshot', False):
      break

    interval = random.randint(min_interval, max_interval)
    time.sleep(interval)


@shared_task(bind=True)
def server_task(self, *args, **kwargs):
  public_ip = get_iface_addr(settings.PUBLIC_IFACE)
  logger.debug("Starting server thread on %s." % (public_ip))

  with open(SERVER_TASK_ID_FILE, 'w') as f:
    print >>f, self.request.id

  server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server_sock.bind((public_ip, settings.PUBLIC_TCP_PORT))
  server_sock.listen(settings.PUBLIC_BACKLOG)

  while True:
    conn, addr = server_sock.accept()
    content = recv_all(conn)

    try:
      reply = json.loads(content)
    except:
      logger.exception("Failed to read reply from %s: %s" % (str(addr), str(content)))
      continue

    try:
      validate(reply, REPLY_SCHEMA)
    except:
      logger.exception("Failed to validate reply.")
      logger.debug(json.dumps(reply))
      return

    logger.debug("Got reply from %s: %s" % (str(addr), json.dumps(reply)))

    for t, handler in HANDLER_MAPPING.items():
      try:
        if reply['request'].get(t, False):
          handler(reply[t])
      except:
        logger.exception("Failed to handle %s" % (t))
