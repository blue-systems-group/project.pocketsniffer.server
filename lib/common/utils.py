
from django.conf import settings

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
