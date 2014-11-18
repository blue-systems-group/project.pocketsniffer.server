import os
import re
import contextlib
import datetime
import time
import StringIO
import gzip
import subprocess
import pipes

from django.db import models, transaction
from django.db.models import F, Sum
from django.conf import settings
from django.utils.timezone import now
from django.core.cache import cache
from django.template import Template, Context
from django.test.utils import compare_xml


from lxml import etree


from apps.backend.exceptions import LockTimeout, BackendValidationError,\
    EmptyState, BrokenState
from libs.common.xmlconversion import Converter
import libs.common.util as util
from libs.common import xmlconversion

class Device(models.Model):
  HASHEDID_LENGTH = 40
  HASHEDID_PATTERN = re.compile(r'[0-9a-f]{40}')
  
  SECUREID_LENGTH = 16
  SECUREID_PATTERN = re.compile(r'[0-9A-F]{16}')
  
  hashedID = models.CharField(max_length=HASHEDID_LENGTH, primary_key=True, unique=True)
  
  last_state = models.ForeignKey('State', null=True, blank=True, related_name='state_device')
  last_manifest = models.ForeignKey('Manifest', null=True, blank=True, related_name='manifest_device')
  last_upload = models.ForeignKey('Upload', null=True, blank=True, related_name='upload_device')
  
  state_count = models.IntegerField(default=0)
  manifest_count = models.IntegerField(default=0)
  upload_count = models.IntegerField(default=0)
  upload_bytes_count = models.BigIntegerField(default=0)
  
  def lock(self, **kwargs):
    return Device.do_lock(device=self, **kwargs)
  
  @classmethod
  @contextlib.contextmanager
  def do_lock(cls, device=None, **kwargs):
    acquired_lock = False
    try:
      return_device = Device.do_acquire_lock(device, **kwargs)
      if return_device == None:
        raise LockTimeout()
      acquired_lock = True
      yield return_device
    finally:
      if acquired_lock:
        Device.do_release_lock(device, **kwargs)
  
  def acquire_lock(self, **kwargs):
    return Device.do_acquire_lock(device=self, **kwargs)
  
  @classmethod
  def do_acquire_lock(cls, device=None, block=None, name=None, length=None, timeout=None, sleep=None):
    
    key = Device.generate_lock_key(device, name)    
    
    if block == None:
      block = settings.BACKEND_LOCK_DEFAULTS[name]['block']
      
    if length == None:
      length = settings.BACKEND_LOCK_DEFAULTS[name]['length']
  
    if timeout == None:
      timeout = settings.BACKEND_LOCK_DEFAULTS[name]['timeout']
    
    if sleep == None:
      sleep = settings.BACKEND_LOCK_DEFAULTS[name]['sleep']
      
    if not block:
      timeout = datetime.timedelta(seconds=0)
      
    start_time = now()
    
    while True:
      if cache.add(key, 1, length.seconds):
        if device != None:
          return Device.objects.get(hashedID=device.hashedID)
        else:
          return True
      if now() > start_time + timeout:
        return None
      else:
        time.sleep(sleep.seconds)
  
  def is_locked(self, **kwargs):
    return Device.do_is_locked(device=self, **kwargs)
  
  @classmethod
  def do_is_locked(cls, device=None, name=None):
    return cache.get(Device.generate_lock_key(device, name)) != None
   
  def release_lock(self, **kwargs):
    return Device.do_release_lock(device=self, **kwargs)
  
  @classmethod
  def do_release_lock(cls, device=None, name=None, **kwargs):
    was_locked = Device.do_is_locked(device=device, name=name)
    cache.delete(Device.generate_lock_key(device, name))
    return was_locked
  
  @classmethod
  def generate_lock_key(cls, device, name):
    if device == None and name == None:
      raise Exception()
    
    if device != None:
      key = device.hashedID
      if name != None:
        key += "_" + name
    else:
      key = name + "_lock"
    
    return key
        
  @classmethod
  def create(cls, hashedID):
    device = Device.objects.get_or_create(hashedID=hashedID)[0]
    return device
  
  def update_counts(self):
    with self.lock() as device:
      device.state_count = State.objects.filter(device=device).count()
      device.upload_count = Upload.objects.filter(device=device, disabled=False).count()
      device.upload_bytes_count = Upload.objects.filter(device=device, disabled=False).aggregate(Sum('bytes'))['bytes__sum']
      if device.upload_bytes_count == None:
        device.upload_bytes_count = 0
 
      device.save(update_fields=['state_count'])
  
  @classmethod
  def total_states(cls):
    return sum([device.state_count for device in Device.objects.all()])

  @classmethod
  def total_uploads(cls):
    return sum([device.upload_count for device in Device.objects.all()])
  
  @classmethod
  def total_upload_bytes(cls):
    return sum([device.upload_bytes_count for device in Device.objects.all()])
 
  @classmethod
  def reset_new_device(cls, sender, **kwargs):
    if kwargs['created']:
      kwargs['instance'].reset_logcat()
  
  class HashedIDConverter(Converter):
    @classmethod
    def from_xml(cls, value):
      return value.zfill(Device.HASHEDID_LENGTH)
  
  class DeviceConverter(Converter):
    @classmethod
    def from_xml(cls, value):
      return Device.create(value.zfill(Device.HASHEDID_LENGTH))


class State(models.Model):
  FILENAME = 'state.xml.gz'

  XML_CONVERTERS = {'HashedID': Device.HashedIDConverter}
  XML_MAP = u"""
    <state>
      <ManifestService>
        <versionName>version_name</versionName>
        <versionCode xml_converter='Int'>version_code</versionCode>
      </ManifestService>
      <UploaderService>
        <lastUpload xml_converter='JavaTime'>last_upload</lastUpload>
        <uploadedBytes xml_converter='Int'>uploaded_bytes</uploadedBytes>
        <reasonNotUpload>reason_not_upload</reasonNotUpload>
      </UploaderService>
      <received>
        <time xml_converter='UNIXTime'>received_time</time>
        <ID xml_converter='HashedID'>received_ID</ID>
        <path>received_path</path>
        <name>received_name</name>
        <port>received_port</port>
        <version xml_default='1.0'>version</version>
      </received>
    </state>
  """
  
  # ManifestService
  version_name = models.DecimalField(max_digits=3, decimal_places=1, null=True)
  version_code = models.IntegerField(null=True)

  # UploaderService
  last_upload = models.DateTimeField(null=True)
  uploaded_bytes = models.BigIntegerField(null=True)
  reason_not_upload = models.CharField(max_length=1024, null=True, blank=True)

  # general
  received_time = models.DateTimeField(db_index=True)
  received_ID = models.CharField(max_length=40, null=True)
  version = models.CharField(max_length=10)

  device = models.ForeignKey('Device')
  
  class Meta:
    unique_together = (('device', 'received_time'),)
  
  @classmethod
  def basedir(cls):
    return os.path.join(settings.DATA_DIR, 'state')
  
  @property
  def filename(self):
    return os.path.join(self.basedir(),
                        self.device.hashedID,
                        util.received_file_relative_path(self.FILENAME, self.received_time))
  
  @property
  def exists(self):
    return os.path.exists(self.filename)
  
  @property
  def root(self):
    return etree.parse(self.filename, etree.XMLParser(remove_blank_text=True)).getroot()
  
  def __unicode__(self):
    return xmlconversion.to_xml(self)
   
  def save(self, *args, **kwargs):
    with transaction.commit_manually():
      try:
        super(State, self).save(*args, **kwargs)
      except:
        do_remove_linked_file(self.filename, self.basedir())
        transaction.rollback()
        raise
      else:
        transaction.commit()

  @classmethod
  def path_matches(cls, path):
    return re.match(r'^state', os.path.split(path)[1]) != None
  
  @classmethod
  def fix_xml(cls, content):
    content_string = re.sub(r'(?m)(\s*(</?root/?>|</?state/?>|<\?xml.*?\?>)\s*)', '', content.read())
    content_string = os.linesep.join([s for s in content_string.splitlines() if s])
    if content_string == "":
      raise EmptyState()
    return StringIO.StringIO("<state>" + content_string + "</state>")
  
  @classmethod
  def create(cls, request, unzip_file=True, add_received=True, version=None, hashedID=None):
    state = State()
    if unzip_file:
      content = util.unzip_stream(request)
    else:
      content = request
    root = root_from_file(State.fix_xml(content))
    
    if add_received:
      root = add_received_xml(request, hashedID, version, root)
    else:
      if len(root) == 1 and root[0].tag == 'received':
        raise EmptyState()
      
    try:
      xmlconversion.from_xml(state, root)
    except Exception:
      raise BrokenState()
    
    state.device = Device.create(state.received_ID)
    
    if os.path.exists(state.filename):
      raise BackendValidationError("state file already exists")
    else:
      write_canonical_xml(root, state.filename)
    
    try:
      state.full_clean()
    except:
      do_remove_linked_file(state.filename, state.basedir())
      raise
      
    return state
  
  @classmethod
  def import_file(cls, import_file):
    return State.create(open(import_file, 'rb'), unzip_file=False, add_received=False)
    
  @classmethod
  def set_last_state(cls, sender, **kwargs):
    if kwargs['created']:
      state = kwargs['instance']
      with state.device.lock() as device:
        if device.last_state == None or device.last_state.received_time < state.received_time:
          device.last_state = state
          device.save(update_fields=['last_state'])
  
  @classmethod
  def update_state_count(cls, sender, **kwargs):
    if kwargs['created']:
      state = kwargs['instance']
      with state.device.lock() as device:
        device.state_count += 1
        device.save(update_fields=['state_count'])
  
class Manifest(models.Model):
  FILENAME = 'manifest.xml.gz'
  
  MANIFEST_HASHEDID_REPLACE_STRING = '__hashedID__'
  MANIFEST_VERSION_REPLACE_STRING = '__version__'
  
  class Meta:
    unique_together = (('device', 'retrieved_time'),)
  
  device = models.ForeignKey('Device')
  retrieved_time = models.DateTimeField()
  version = models.CharField(max_length=10)
  
  @classmethod
  def basedir(cls):
    return os.path.join(settings.DATA_DIR, 'manifests')

  @property
  def filename(self):
    return os.path.join(self.basedir(),
                        self.device.hashedID,
                        util.received_file_relative_path(self.FILENAME, self.retrieved_time))
    
  @property
  def exists(self):
    return os.path.exists(self.filename)
  
  @property
  def root(self):
    return etree.parse(gzip.open(self.filename)).getroot()
  
  @property
  def xml(self):
    xml = StringIO.StringIO()
    etree.parse(self.filename, etree.XMLParser(remove_blank_text=True)).write_c14n(xml)
    return xml.getvalue()
  
  def save(self, *args, **kwargs):
    with transaction.commit_manually():
      try:
        super(Manifest, self).save(*args, **kwargs)
      except:
        do_remove_linked_file(self.filename, self.basedir())
        transaction.rollback()
        raise
      else:
        transaction.commit()

  @classmethod
  def make_context(cls, device, request=None) :
    ctx = Context()
    return ctx
    
  @classmethod
  def create(cls, version, hashedID, request=None):
    filename = os.path.join(settings.MANIFEST_DIR, version, 'manifest.xml')
    
    if hashedID != None:
      device = Device.create(hashedID)
    else:
      device = None
      
    template = Template(open(filename, 'rb').read())
    
    if hashedID != None:
      ctx = Manifest.make_context(device=device, request=None)
    else:
      ctx = Manifest.make_context(device=None, request=request)

    xml = template.render(ctx)
    root =  etree.fromstring(StringIO.StringIO(xml.decode('utf-8')).getvalue().encode('utf-8'),
                          parser=etree.XMLParser(encoding='utf-8'))
    if device == None:
      return_string = StringIO.StringIO()
      etree.ElementTree(root).write_c14n(return_string)
      return return_string.getvalue()
    
    if device.last_manifest and device.last_manifest.exists and compare_xml(root, device.last_manifest.root):
      return device.last_manifest
    else:
      manifest = Manifest(device=Device.create(hashedID),
                          version=version,
                          retrieved_time=now())
      

      if os.path.exists(manifest.filename):
        raise BackendValidationError("manifest file already exists")
      else:
        write_canonical_xml(root, manifest.filename)
        
      try:
        manifest.full_clean()
      except:
        do_remove_linked_file(manifest.filename, manifest.basedir())
        raise
    
      return manifest
  
  @classmethod
  def set_last_manifest(cls, sender, **kwargs):
    if not kwargs['created']:
      return
    manifest = kwargs['instance']
    with manifest.device.lock() as device:
      if device.last_manifest == None or device.last_manifest.retrieved_time < manifest.retrieved_time:
        device.last_manifest = manifest
        device.save(update_fields=['last_manifest'])
  
  @classmethod
  def update_manifest_count(cls, sender, **kwargs):
    if kwargs['created']:
      manifest = kwargs['instance']
      device = manifest.device
      
      device.manifest_count = F('manifest_count') + 1
      device.save(update_fields=['manifest_count'])
  

def do_remove_linked_file(filename, basedir):
  if filename != None:
    try:
      os.unlink(filename)
    except OSError:
      pass
    current_dir = os.path.dirname(filename)
    while True:
      if not current_dir or current_dir == basedir:
        break
      try:
        os.rmdir(current_dir)
      except OSError:
        break
      current_dir = os.path.dirname(current_dir)


class Upload(models.Model):
  
  class Meta:
    unique_together = (('device', 'received_time'),)
   
  device = models.ForeignKey('Device')
  received_time = models.DateTimeField()
  version = models.CharField(max_length=10)
  bytes = models.IntegerField()
  packagename = models.CharField(max_length=256, null=True, blank=True)
  upload_filename = models.CharField(max_length=128)
  disabled = models.BooleanField(default=False)
  compressed = models.BooleanField(default=False)

  @classmethod
  def basedir(cls):
    return os.path.join(settings.DATA_DIR, 'upload')
  
  @property
  def filename(self):
    base_filename = os.path.join(self.basedir(),
                                 self.device.hashedID,
                                 util.received_file_relative_path(self.upload_filename, self.received_time))
    if self.compressed:
      return base_filename + '.gz'
    else:
      return base_filename
    
  @property
  def exists(self):
    return os.path.exists(self.filename)
  
  def compress(self, save=True):
    if self.compressed:
      return True
    else:
      try:
        subprocess.check_call("gzip %s" % (pipes.quote(self.filename),), shell=True)
      except:
        raise
      else:
        self.compressed = True
        if save:
          self.save(update_fields=['compressed'])
        return True
  
  def fix_compressed(self):
    if not self.exists:
      if self.compressed == True:
        self.compressed = False
      else:
        self.compressed = True
      if self.exists:
        self.save()
      else:
        raise Exception("could not fix upload file compression state")
        
  def decompress(self):
    if not self.exists:
      self.fix_compressed()
      
    if not self.compressed:
      return True
    else:
      try:
        subprocess.check_call("gunzip %s" % (pipes.quote(self.filename),), shell=True)
      except Exception, e:
        print e
        raise
      else:
        self.compressed = False
        self.save(update_fields=['compressed'])
        return True
      
  def clean(self):
    if not self.exists:
      raise BackendValidationError("file does not exist")
   
  def save(self, *args, **kwargs):
    with transaction.commit_manually():
      try:
        super(Upload, self).save(*args, **kwargs)
      except:
        do_remove_linked_file(self.filename, self.basedir())
        transaction.rollback()
        raise
      else:
        transaction.commit()
      
  @classmethod
  def path_matches(cls, path):
    return any([re.match(r'^log', os.path.split(path)[1]) != None],)
  
  @classmethod
  def create(cls, request, version, hashedID, packagename, filename):
    upload = Upload(device=Device.create(hashedID), version=version, received_time=now(),
                    packagename=packagename, upload_filename=filename, logcat_processing_done=False)
    
    content = util.unzip_stream(request).read().decode('utf-8', errors='ignore')
    upload.bytes = len(content)
    
    if os.path.exists(upload.filename):
      raise BackendValidationError("upload file already exists")
    else:
      util.stream_to_file(StringIO.StringIO(content), upload.filename)
    
    try:
      upload.full_clean()
      upload.compress(save=False)
    except:
      do_remove_linked_file(upload.filename, upload.basedir())
      raise
    
    return upload

  @classmethod
  def set_last_upload(cls, sender, **kwargs):
    if kwargs['created']:
      upload = kwargs['instance']
      with upload.device.lock(name='upload') as device:
        if device.last_upload == None or device.last_upload.received_time < upload.received_time:
          device.last_upload = upload
          device.save(update_fields=['last_upload'])
  
  @classmethod
  def update_upload_counts(cls, sender, **kwargs):
    if kwargs['created']:
      upload = kwargs['instance']
      device = upload.device
      
      device.upload_count = F('upload_count') + 1
      device.upload_bytes_count = F('upload_bytes_count') + upload.bytes
      device.save(update_fields=['upload_count', 'upload_bytes_count'])
       
      
  class ConvertPath(Converter):
    @classmethod
    def from_xml(cls, field):
      try:
        return os.path.basename(field)
      except:
        return None

 

def root_from_file(request):
  return etree.fromstring(StringIO.StringIO(request.read().decode('utf-8')).getvalue().encode('utf-8'),
                          parser=etree.XMLParser(encoding='utf-8'))
 
def add_received_xml(request, ID, version, root):
  received_xml = """
    <received>
      <time>%lu</time>
      <ID>%s</ID>
      <path>%s</path>
      <name>%s</name>
      <port>%s</port>
      <version>%s</version>
    </received>""" % (int(time.time() * 1000), ID, request.path,
                      request.META['SERVER_NAME'], request.META['SERVER_PORT'], version)
  root.append(etree.fromstring(received_xml))
  return root

def write_canonical_xml(root, filename, mode=0440):  
  xml_string = StringIO.StringIO()
  etree.ElementTree(root).write_c14n(xml_string)
  util.stream_to_file(xml_string, filename, compressed=True)



