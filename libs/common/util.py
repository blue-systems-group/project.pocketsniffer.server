import os, gzip, StringIO, logging, datetime, time, stat
from django.conf import settings
import grp
import re
import subprocess

logger = logging.getLogger('backend')

def recursive_create_directory(path, dirmod=0o2770):
  
  current_dir, make_dirs = os.path.dirname(path), []
  
  while True:
    if os.path.exists(current_dir):
      assert os.path.isdir(current_dir), "what should be a directory is not"
      break
    else:
      make_dirs.append(current_dir)
      current_dir = os.path.dirname(current_dir)
  
  make_dirs = reversed(make_dirs)
  for make_dir in make_dirs:
    os.mkdir(make_dir)
    os.chown(make_dir, os.stat(make_dir).st_uid, grp.getgrnam(settings.GROUP).gr_gid)
    os.chmod(make_dir, dirmod)

def set_path_mod(path, filemod=0o0440):
  os.chmod(path, filemod)
  os.chown(path, os.stat(path).st_uid, grp.getgrnam(settings.GROUP).gr_gid)
  
def stream_to_file(stream, path,
                   append=False, overwrite=True, dirmod=0o2770, filemod=0o0440, compressed=False):
  
  if not overwrite and os.path.exists(path):
    raise Exception("not overwriting existing file")
  
  recursive_create_directory(path, dirmod)
      
  if append == True:
    if compressed == True:
      f = gzip.open(path, 'ab')
    else:
      f = open(path, 'ab')
  else:
    if compressed == True:
      f = gzip.open(path, 'wb')
    else:
      f = open(path, 'wb')
      
  stream.seek(0)
  print >>f, stream.read().encode('utf-8')
  stream.seek(0)
  f.close()
  
  set_path_mod(path)

def unzip_stream(stream):
  string_buffer = StringIO.StringIO(stream.read())
  stream.length = string_buffer.len
  string_buffer.seek(0)
  return gzip.GzipFile(fileobj=string_buffer)

def received_file_relative_path(filename, received_time):
  try:
    name, extension = filename.split(os.extsep, 1)
    extension = '.' + extension
  except ValueError:
    name, extension = filename, ''

  return os.path.join(received_time.strftime("%Y/%m/%d/"),
                      name + "_" + received_time.strftime("%H_%M_%S_%f") + extension)

def count_dir(directory, count_dirs=False, extension=None):
  count = 0
  for unused, dirnames, filenames in os.walk(directory):
    if count_dirs:
      count += len(dirnames)
    if extension == None:
      count += len(filenames)
    else:
      count += len([1 for filename in filenames if filename.endswith(extension)])
  return count

def count_lines(directory, extensions=None):
  all_files = []
  for root, unused, files in os.walk(directory):
    if extensions == None:
      all_files.extend([os.path.join(root, f) for f in files])
    else:
      all_files.extend([os.path.join(root, f) for f in files if any([f.endswith(extension) for extension in extensions])])
  return sum([sum(1 for unused in gzip.open(f)) for f in all_files if f.endswith('.gz')]) + sum([sum(1 for unused in open(f)) for f in all_files if not f.endswith('.gz')])

def unixtime_from_datetime(dt):
  return long((time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0)) * 1000.0)

def datetime_modulo(dt, td):
  unix_datetime = unixtime_from_datetime(dt) / 1000
  return datetime.datetime.fromtimestamp(unix_datetime - (unix_datetime % td.total_seconds())).replace(tzinfo=dt.tzinfo)


def recv_all(conn):
  content = []
  try:
    while True:
      data = conn.recv(settings.BUF_SIZE)
      if len(data) == 0:
        break
      content.append(data)
  except:
    pass

  return ''.join(content)

def freq_to_channel(freq):
  if freq < 2472:
    return (freq - 2412) / 5 + 1
  else:
    return (freq - 5180) / 5 + 36 

def channel_to_freq(chan):
  if chan <= 11:
    return 2412 + (chan-1)*5
  else:
    return 5180 + (chan-36)*5



INET_ADDR_PATTERN = re.compile(r"""inet\saddr:(?P<IP>[\d\.]{7,15})\s""", re.VERBOSE)
def get_iface_addr(iface):
  output = subprocess.check_output('ifconfig %s' % (iface), shell=True)
  match = INET_ADDR_PATTERN.search(output)
  return match.group('IP')
