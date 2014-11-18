import traceback

from django.conf.urls import patterns, url
from django.conf import settings
from django.http.response import Http404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from apps.backend.models import State, Manifest, Upload

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'

@csrf_exempt
def manifest_from_request(request, version, hashedID):
  hashedID = hashedID.zfill(40)
  if version == None:
    version = settings.BACKEND_DEFAULT_CLIENT_VERSION
  
  try:
    state = State.create(request, version=version, hashedID=hashedID)
    state.save()
  except:
    if settings.DEBUG:
      traceback.print_exc()
    raise Http404
    
  try:
    manifest = Manifest.create(version, hashedID)
  except:
    if settings.DEBUG:
      traceback.print_exc()
    raise Http404
  
  manifest.save()

  xml = manifest.xml
  if not xml.startswith(XML_DECLARATION) :
    xml = "%s%s" % (XML_DECLARATION, xml)
  
  return HttpResponse(xml, content_type='application/xml')


@csrf_exempt
def upload_from_request(request, version, hashedID, packagename, filename):
  hashedID = hashedID.zfill(40)
  try:
    upload = Upload.create(request, version, hashedID, packagename, filename)
    upload.save()
  except:
    if settings.DEBUG:
      traceback.print_exc()
    raise Http404
  
  return HttpResponse()
 


urlpatterns = patterns('',
    url(r'^manifest(?:/(?P<version>[0-9\.]+){1})?/(?P<hashedID>[a-f0-9]{38,40})', manifest_from_request),
    url(r'^uploader(?:/(?P<version>[0-9\.]+){1})?/(?P<hashedID>[a-f0-9]{38,40})(?:/(?P<packagename>\S+?){1})?/(?P<filename>\S+)$', upload_from_request),
)
