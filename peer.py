import getopt
import socket
import sys
import time
import os
import hashlib
import requests
import bencode
import sys
from threading import Lock, Condition, Thread

my_host = "0.0.0.0"
my_port = 8080
BUFFER_SIZE = 1024
info_filename = ""
info = {}
my_peer_id = ""
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

  def __init__(self, lst=[]):
    self.connected = lst
    self.lock = Lock()
    self.noPeers = Condition(self.lock)

  def add(self, c):
    with self.lock:
      self.connected.append(c)

  def contains(self, c):
    with self.lock:
      return c in self.connected

  def get_peer(self):
    with self.lock:
      while(len(self.connected) == 0):
        self.noPeers.wait()
      return self.connected.pop()


class Seeder(Thread):
  """Seeder threads for handling clients requesting pieces"""

  def __init__(self, connectionQueue, connected_list):
    Thread.__init__(self)
    self.connections = connectionQueue
    self.connected_list = connected_list

  def run(self):
    # Get work to do and do it
    while True:
      # Get a connection
      sock = self.connections.getConnection()
      ct = ConnectionHandler(sock, self.connected_list)
      ct.handle()

class Requester(Thread):
  """Requester threads for requesting pieces from other clients"""

  def __init__(self, peer_list, connected_peers):
    Thread.__init__(self)
    self.peer_list = peer_list # peers from server
    self.connected_peers = connected_peers

  def run(self):
    # Get work to do and do it
    while True:
      peer = self.peer_list.get_peer()
      if(peer['peer_id'] != my_peer_id):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((peer['ip'], int(peer['port'])))
        rh = RequestHandler(sock, self.connected_peers)
        rh.handle()

class Handler:

  def __init__(self, sock, connected_list):
    self.sock = sock
    self.connected_list = connected_list

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
    meta_sha1.update(bencode.bencode(info['info']))
    info_hash = bytearray(meta_sha1.digest())
    if(hs[28:48] != info_hash):
      print "Wrong info hash"
      return False
    name_sha1 = hashlib.sha1()
    name_sha1.update(my_peer_id)
    name_hash = bytearray(name_sha1.digest())
    if(self.connected_list.contains(hs[48:]) or (hs[48:] == name_hash)):
      print "Same name as current peer"
      return False
    self.connected_list.add(hs[48:])
    return True

  def make_handshake(self):
    nameLength = bytearray(1)
    nameLength[0] = 19
    protocolName = bytearray("BitTorrent protocol")
    reserved = bytearray(8)
    meta_sha1 = hashlib.sha1()
    meta_sha1.update(bencode.bencode(info['info']))
    info_hash = bytearray(meta_sha1.digest())
    name_sha1 = hashlib.sha1()
    name_sha1.update(my_peer_id)
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

class RequestHandler(Handler):
  """Makes a request to a single client"""

  def __init__(self, sock, connected_peers):
    Handler.__init__(self, sock, connected_peers)
    self.state = "NOT_CONNECTED"
    self.timeout = 10

  def init_handshake(self):
    # first assemble string of bytes
    hs = self.make_handshake()
    # send handshake
    self.send(hs)
    # check recived handshake
    remote_hs = self.recv()
    if(not remote_hs or not self.check_handshake(remote_hs)):
        print "closing socket"
        clientsocket.close()
    else:
        print "Handshake done"

  def handle(self):
    try:
      while True:
        print("got connection")
        if(self.state == "NOT_CONNECTED"):
          self.init_handshake()
          self.sock.close()
        return
    except socket.timeout:
      self.sock.close()
    except socket.error:
      self.sock.close()



class ConnectionHandler(Handler):
  """Handles a single client request"""

  def __init__(self, sock, connected_list):
    Handler.__init__(self, sock, connected_list)
    self.state = "NOT_CONNECTED"
    self.timeout = 10

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

def get_peers():
    info_sha1 = hashlib.sha1()
    info_sha1.update(bencode.bencode(info['info']))
    info_hash = str(bytearray(info_sha1.digest()))
    payload = {
      'info_hash'  : info_hash,
      'peer_id'    : my_peer_id,
      'port'       : my_port,
      'uploaded'   : str(0),
      'downloaded' : str(0),
      'left'       : str(info['info']['length'])
    }
    server_url = "http://" + info['announce']
    r = requests.get(server_url, params=payload)
    r_d = bencode.bdecode(r.text)
    return ConnectedPeers(r_d['peers'])

def serverloop():
  """The main server loop"""

  serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # mark the socket so we can rebind quickly to this port number
  # after the socket is closed
  serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  # bind the socket to the local loopback IP address and special port
  serversocket.bind((my_host, my_port))
  # start listening with a backlog of 5 connections
  serversocket.listen(5)

  # Thread Pool
  seederThreadPool    = []
  requesterThreadPool = []
  # List of waiting connections
  connectionList = ConnectionQueue()
  connected_list = ConnectedPeers()

  potential_peers = get_peers()
  for i in xrange(8):
    # Create the 8 seeder threads for requesting connections
    seederThread    = Seeder(connectionList, connected_list)
    requesterThread = Requester(potential_peers, connected_list)
    seederThreadPool.append(seederThread)
    requesterThreadPool.append(requesterThread)
    seederThread.start()
    requesterThread.start()

  while True:
    # accept a connection
    try:
      (clientsocket, address) = serversocket.accept()
      connectionList.addConnection(clientsocket)
    except:
      return

# DO NOT CHANGE BELOW THIS LINE

opts, args = getopt.getopt(sys.argv[1:], 'h:p:m:i:', \
                           ['host=', 'port=', 'metainfo=', 'peer_id='])

for k, v in opts:
    if k in ('-h', '--host'):
      my_host = v
    if k in ('-p', '--port'):
      my_port = int(v)
    if k in ('-m', '--metainfo'):
      info_filename = v
      with open(info_filename, 'rb') as f:
        info = bencode.bdecode(f.read())
    if k in ('-i', '--peer_id'):
      my_peer_id = v


print("Server coming up on %s:%i" % (my_host, my_port))
serverloop()
