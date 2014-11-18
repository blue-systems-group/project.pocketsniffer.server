import re, StringIO
from lxml import etree
from datetime import datetime, timedelta
from django.utils.timezone import utc
  
class Converter(object):
  @classmethod
  def to_xml(cls, value):
    return str(value)
  @classmethod
  def from_xml(cls, value):
    return value
  @classmethod
  def from_xml_element(cls, element):
    pass

class ConversionException(Exception):
  pass  

class String(Converter):
  pass

class Unicode(Converter):
  @classmethod
  def from_xml(cls, value):
    return unicode(value)
  
class Float(Converter):
  @classmethod
  def from_xml(cls, value):
    return float(value)

class Int(Converter):
  @classmethod
  def from_xml(cls, value):
    return int(value)
  
class Long(Converter):
  @classmethod
  def from_xml(cls, value):
    return long(value)
  
class Boolean(Converter):
  @classmethod    
  def to_xml(cls, value):
    if value == True:
      return "true"
    elif value == False:
      return "false"
    else:
      raise ConversionException("could not convert boolean to xml")
    
  @classmethod
  def from_xml(cls, field):
    if field == "true":
      return True
    elif field == "false":
      return False
    else:
      raise ConversionException("could not convert boolean from xml")

class UNIXTime(Converter):
  
  @classmethod
  def from_xml(cls, field):
    return (datetime.utcfromtimestamp(long(field) / 1000).replace(tzinfo=utc) + \
            timedelta(milliseconds=long(field) % 1000))

class JavaTime(Converter):
  PATTERN = re.compile("""(?x)(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+
                              (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\.(?P<microsecond>\d{1,6})""")

  @classmethod
  def from_xml(cls, field):
    match = JavaTime.PATTERN.match(field)
    assert match, "pattern did not match javatime"
    return datetime(int(match.group('year')),
                    int(match.group('month')),
                    int(match.group('day')),
                    int(match.group('hour')),
                    int(match.group('minute')),
                    int(match.group('second')),
                    int(match.group('microsecond').ljust(6, '0'))).replace(tzinfo=utc)

class FlexTime(Converter):
  
  @classmethod
  def from_xml(cls, field):
    try:
      return UNIXTime.from_xml(field)
    except ValueError:
      return JavaTime.from_xml(field)
    
def to_xml(obj, xml_map=None):
  pass
    
def from_xml(obj, root, xml_map=None, converters={}):
  if xml_map == None:
    xml_map = obj.XML_MAP
  map_tree = etree.parse(StringIO.StringIO(xml_map), parser=etree.XMLParser(encoding='utf-8'))
  if len(converters) == 0:
    try:
      converters = obj.XML_CONVERTERS
    except:
      pass 
  for element in [e for e in map_tree.getroot().getiterator() if e.text and e.text.strip() != ""]:
    converter_name = element.get('xml_converter', 'String')
    if converters.has_key(converter_name):
      converter = converters[converter_name]
    else:
      converter = eval(converter_name)
    xml_value = None
    xml_element = None
    try:
      xml_element = root.xpath(map_tree.getpath(element))[0]
      xml_value = xml_element.text
    except :
      pass
    if xml_value == None:
      xml_value = element.get('xml_default')

    value = converter.from_xml(xml_value)
    if value is not None :
      setattr(obj, element.text, value)
    else :
      setattr(obj, element.text, converter.from_xml_element(xml_element))
