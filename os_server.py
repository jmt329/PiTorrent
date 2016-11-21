import getopt
import socket
import sys
import time
import os
from threading import Lock, Condition, Thread


host = "127.0.0.1"
port = 8765
netid = "swc63"
# Instead, you can pass command-line arguments
# -h/--host [IP] -p/--port [PORT]
# to put your server on a different IP/port.

class ConnectionQueue:
  """Monitor to add connections to connection list"""

  def __init__(self):
    self.connections = []
    self.lock = Lock()
    self.numConnections = 0
    self.noConnections = Condition(self.lock)

  def getConnection(self):
    with self.lock:
      while self.numConnections == 0:
        self.noConnections.wait()
      self.numConnections -= 1
      return self.connections.pop(0)

  def addConnection(self, socket):
    with self.lock:
      self.numConnections += 1
      self.connections.append(socket)
      self.noConnections.notify()

class Worker(Thread):
  """Worker threads for handling clients"""

  def __init__(self, connectionQueue):
    Thread.__init__(self)
    self.connections = connectionQueue

  def run(self):
    # Get work to do and do it
    while True:
      # Get a connection
      sock = self.connections.getConnection()
      ct = ConnectionHandler(sock)
      ct.handle()

class ConnectionHandler:
  """Handles a single client request"""

  def __init__(self, sock):
    self.sock = sock
    self.state = "HELO?"
    self.lastMessageValid = True
    self.timeout = 10

  def send(self, message):
    self.sock.send(message.encode('utf-8'))

  def handle(self):
    try:
      while True:
        self.sock.close()
        return
    except socket.timeout:
      self.sock.close()
    except socket.error:
      self.sock.close()

def serverloop():
  """The main server loop"""

  serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # mark the socket so we can rebind quickly to this port number
  # after the socket is closed
  serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  # bind the socket to the local loopback IP address and special port
  serversocket.bind((host, port))
  # start listening with a backlog of 5 connections
  serversocket.listen(5)

  # Thread Pool
  threadPool = []
  # List of waiting connections
  connectionList = ConnectionQueue()

  for i in xrange(32):
    # Create the 32 consumer threads for the connections
    workerThread = Worker(connectionList)
    threadPool.append(workerThread)
    workerThread.start()

  while True:
    # accept a connection
    try:
      (clientsocket, address) = serversocket.accept()
      connectionList.addConnection(clientsocket)
    except:
      return

# DO NOT CHANGE BELOW THIS LINE

opts, args = getopt.getopt(sys.argv[1:], 'h:p:', ['host=', 'port='])

for k, v in opts:
    if k in ('-h', '--host'):
        host = v
    if k in ('-p', '--port'):
        port = int(v)

print("Server coming up on %s:%i" % (host, port))
serverloop()
