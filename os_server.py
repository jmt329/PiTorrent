import getopt
import socket
import sys
import time
import os
import hashlib
from threading import Lock, Condition, Thread

host = "127.0.0.1"
port = 8765
BUFFER_SIZE = 1024
info = "TestMetainfo"
peer_name = "TestPeer2"
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


class ConnectedPeers:

  def __init__(self):
    self.connected = []
    self.lock = Lock()

  def add(self, c):
    with self.lock:
      self.connected.append(c)

  def contains(self, c):
    with self.lock:
      return c in self.connected


class Worker(Thread):
  """Worker threads for handling clients"""

  def __init__(self, connectionQueue, peer_list):
    Thread.__init__(self)
    self.connections = connectionQueue
    self.peer_list = peer_list

  def run(self):
    # Get work to do and do it
    while True:
      # Get a connection
      sock = self.connections.getConnection()
      ct = ConnectionHandler(sock, self.peer_list)
      ct.handle()

class ConnectionHandler:
  """Handles a single client request"""

  def __init__(self, sock, peer_list):
    self.sock = sock
    self.state = "NOT_CONNECTED"
    self.timeout = 10
    self.peer_list = peer_list

  def send(self, message):
    self.sock.send(message)

  def recv(self):
    return self.sock.recv(BUFFER_SIZE)

  def check_handshake(self, hs):
    hs = bytearray(hs)
    if(int(hs[0]) != 19):
      print "Wrong name length"
      return False
    if(hs[1:20] != "BitTorrent protocol"):
      print "Wrong protocol"
      return False
    meta_sha1 = hashlib.sha1()
    meta_sha1.update(info)
    info_hash = bytearray(meta_sha1.digest())
    if(hs[28:48] != info_hash):
      print "Wrong info hash"
      return False
    name_sha1 = hashlib.sha1()
    name_sha1.update(peer_name)
    name_hash = bytearray(name_sha1.digest())
    if(self.peer_list.contains(hs[48:]) or (hs[48:] == name_hash)):
      print "Same name as current peer"
      return False
    self.peer_list.add(hs[48:])
    return True

  def make_handshake(self):
    nameLength = bytearray(1)
    nameLength[0] = 19
    protocolName = bytearray("BitTorrent protocol")
    reserved = bytearray(8)
    meta_sha1 = hashlib.sha1()
    meta_sha1.update(info)
    info_hash = bytearray(meta_sha1.digest())
    name_sha1 = hashlib.sha1()
    name_sha1.update(peer_name)
    name_hash = bytearray(name_sha1.digest())
    return nameLength + protocolName + reserved + info_hash + name_hash

  def recv_handshake(self):
    hs = self.recv()
    # check handshake
    if(not self.check_handshake(hs)):
      # not a valid handshake
      print "closing socket"
      self.sock.close()
    else:
      # send handshake back
      print "Sending handshake back"
      hs = self.make_handshake()
      self.send(hs)

  def handle(self):
    try:
      while True:
        print("server got connection")
        if(self.state == "NOT_CONNECTED"):
          self.recv_handshake()
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
  peer_list = ConnectedPeers()

  for i in xrange(32):
    # Create the 32 consumer threads for the connections
    workerThread = Worker(connectionList, peer_list)
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
