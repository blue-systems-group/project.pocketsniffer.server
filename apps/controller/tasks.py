from __future__ import absolute_import

import socket
import json
import logging
import threading

from django.conf import settings
from celery import shared_task



from apps.backend.models import AccessPoint
from lib.common.utils import recv_all


logger = logging.getlogger('backend')

def import_ap_list():
  for wan_mac, wan_ip in settings.AP_LIST:
    if AccessPoint.object.exists(wan_mac=wan_mac):
      logger.debug("AP %s (%s) already exists." % (wan_mac, wan_ip))
      continue

    logger.info("Creating AP %s (%s)." % (wan_mac, wan_ip))
    AccessPoint(wan_ip=wan_ip, wan_mac=wan_mac, is_sniffer_ap=True).save()


class HandlerThread(threading.Thread):

  def __init__(self, conn, ap, request):
    super(HandlerThread, self).__init__()
    self.conn = conn
    self.ap = ap
    self.request = request


  def handle_collect(self, reply):
    if 'neighborAPs' in reply:
      for neighborAP in reply['neighborAPs']:
        if AccessPoint.object.exist(


  def handle_execute(self, reply):
    pass

  HANDLER_MAPPING = {
      'collect': handle_collect,
      'execute': handle_execute,
      }

  def run(self):
    try:
      self.conn.settimeout(settings.READ_TIMEOUT_SEC)
      reply = json.loads(recv_all(self.conn))
    except:
      logger.exception("Failed to read reply from %s" % (self.ap))
      return

    logger.debug("Got reply from %s" % (self.ap))
    getattr(self, HandlerThread.HANDLER_MAPPING[self.request['action']])(reply)




def collect(ap_scan=True, client_scan=True, client_traffic=False, **kwargs):
  request = {'action':'collect', 'client_scan':client_scan, 'client_traffic':client_traffic}
  if client_traffic and 'channel' in kwargs:
    request['channels'] = kwargs['channel']
  if 'clients' in kwargs:
    request['clients'] = kwargs['clients']


  sniffer_aps = AccessPoint.object.filter(is_sniffer_ap=True).exclude(wan_ip_addr=None)
  logger.debug("%d sniffer aps (with ip_addr) found." % (len(sniffer_aps)))
  if 'aps' in kwargs:
    sniffer_aps = sniffer_aps.filter(BSSID__in=kwargs['aps'])
    logger.debug("Restricting to %d aps." % (len(sniffer_aps)))

  msg = json.dumps(request)
  
  logger.debug("Request msg: %s" % (msg))
  handler_threads = []
  for ap in sniffer_aps:
    try:
      conn = socket.create_connection((ap.wan_ip, settings.PUBLIC_TCP_PORT), settings.CONNECTION_TIMEOUT_SEC*1000)
      conn.sendall(msg)
      t = HandlerThread(conn, ap, request)
      t.start()
      handler_threads.append(t)
    except:
      logger.exception("Failed to send msg to %s" % (ap))

  logger.debug("Waiting for responses.")
  for t in handler_threads:
    t.join()
