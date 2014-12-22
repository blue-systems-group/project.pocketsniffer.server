import logging
import json
import os

from django.conf.urls import patterns, url
from django.http.response import Http404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse


from jsonschema import validate

from apps.controller.models import AccessPoint

logger = logging.getLogger('controller')

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'schemas')
with open(os.path.join(SCHEMA_DIR, 'heartbeat.json')) as f:
    HEARTBEAT_SCHEMA = json.loads(f.read())



@csrf_exempt
def heartbeat_from_request(request):
  logger.debug("Handling request.")

  try:
    heartbeat = json.loads(request.read())
  except:
    logger.exception("Failed to parse heartbeat.")
    raise Http404

  try:
    validate(heartbeat, HEARTBEAT_SCHEMA)
  except:
    logger.exception("Failed to validate heartbeat.")
    logger.debug(json.dumps(heartbeat))
    raise Http404

  
  AccessPoint.handle_ap_status(heartbeat['apStatus'])
  AccessPoint.handle_station_dump(heartbeat['stationDump'])
  AccessPoint.handle_ap_scan(heartbeat['apScan'])
  return HttpResponse()


urlpatterns = patterns('',
    url(r'^heartbeat/ap$', heartbeat_from_request),
)
