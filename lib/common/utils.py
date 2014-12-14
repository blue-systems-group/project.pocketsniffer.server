
from django.conf import settings

def recv_all(conn):
  content = []
  while True:
    data = conn.recv(settings.BUF_SIZE)
    if len(data) == 0:
      break
    content.append(data)

  return ''.join(content)
