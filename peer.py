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


class PeerList:

  def __init__(self, lst=[]):
    self.connected = lst
    self.lock = Lock()
    self.noPeers = Condition(self.lock)

  def add(self, c):
    with self.lock:
      self.connected.append(c)

  def remove(self, c):
    with self.lock:
      self.connected.remove(c)

  def contains(self, c):
    with self.lock:
      return c in self.connected

  def get_peer(self):
    with self.lock:
      while(len(self.connected) == 0):
        self.noPeers.wait()
      return self.connected.pop()

  def update(self, new_lst):
    with self.lock:
      self.connected = new_lst

  # connected must be list of dicts
  def contains_key(self, key, e):
    with self.lock:
      for p in self.connected:
        if(p[key] == e):
          return True
      return False

  # returns true if sha1(e) is in connected['key']
  def contains_hashed_key(self, key, e):
    e_sha1 = hashlib.sha1()
    e_sha1.update(e)
    hashed = e_sha1.digest()
    with self.lock:
      for p in self.connected:
        if(str(p[key]) == hashed):
          return True
      return False

  # returns a list of peer_ids
  def peer_ids(self):
    with self.lock:
      peer_id = []
      for p in self.connected:
        if(type(p) == bytearray):
          return self.connected
        peer_id.append(p['peer_id'])
      return peer_id

class Seeder(Thread):
  """Seeder threads for handling clients requesting pieces"""

  def __init__(self, connectionQueue, seeding_to, potential_peers):
    Thread.__init__(self)
    self.connections = connectionQueue
    self.seeding_to = seeding_to
    self.potential_peers = potential_peers

  def run(self):
    # Get work to do and do it
    while True:
      # Get a connection
      sock = self.connections.getConnection()
      ct = ConnectionHandler(sock, self.seeding_to, self.potential_peers)
      ct.handle()

class Requester(Thread):
  """Requester threads for requesting pieces from other clients"""

  def __init__(self, potential_peers, requesting_from):
    Thread.__init__(self)
    self.potential_peers = potential_peers # peers from server
    self.requesting_from = requesting_from

  def run(self):
    # Get work to do and do it
    while True:
      peer = self.potential_peers.get_peer()
      # make hash of peer_id
      id_sha1 = hashlib.sha1()
      id_sha1.update(peer['peer_id'])
      if(peer['peer_id'] != my_peer_id and \
         not self.requesting_from.contains(id_sha1.digest())):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((peer['ip'], int(peer['port'])))
        rh = RequestHandler(sock, self.requesting_from, self.potential_peers)
        rh.handle()

class Handler:

  def __init__(self, sock, connected_peers, potential_peers):
    self.sock = sock
    self.connected_peers = connected_peers
    self.potential_peers = potential_peers

  def send(self, message):
    self.sock.send(message)

  def recv(self):
    return self.sock.recv(BUFFER_SIZE)

  # returns True if handshake is valid otherwise false
  # handshake is valid if it is properly formatted and from a valid peer
  def check_handshake(self, hs):
    hs = bytearray(hs)
    # check name length
    if(int(hs[0]) != 19):
      print "Wrong name length"
      return False
    # check protcol
    if(hs[1:20] != "BitTorrent protocol"):
      print "Wrong protocol"
      return False
    # check info hash
    meta_sha1 = hashlib.sha1()
    meta_sha1.update(bencode.bencode(info['info']))
    info_hash = bytearray(meta_sha1.digest())
    if(hs[28:48] != info_hash):
      print "Wrong info hash"
      return False
    # get peer_id
    name_sha1 = hashlib.sha1()
    name_sha1.update(my_peer_id)
    name_hash = bytearray(name_sha1.digest())
    # update potential_peers from tracker
    vp = get_peers_from_tracker()
    valid_peers = PeerList(vp)

    # # check connected_peers and close connections if no longer a potential peer
    # cp = self.connected_peers.peer_ids()
    # pp = self.potential_peers.peer_ids()
    # for c in cp:
    #   if(c not in pp):
    #     self.connected_peers.remove(c)

    # check if peer is valid
    # not already connected to peer, peer_id is not mine, and in list from tracker
    if(self.connected_peers.contains(hs[48:]) or (hs[48:] == name_hash) or \
       (valid_peers.contains_hashed_key('peer_id', hs[48:]))):
      print "Same name as current peer"
      return False
    # valid peer so add to connected list
    self.connected_peers.add(hs[48:])
    # if we did not know about this peer, add it to potential_peers
    if(not self.potential_peers.contains_key('peer_id', hs[48:])):
      for p in vp:
        id_sha1 = hashlib.sha1()
        id_sha1.update(p['peer_id'])
        if(id_sha1.digest() == hs[48:]):
          self.potential_peers.add(p)

    #print "In check_handshake: connected_peers = " + str(self.connected_peers.peer_ids())
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

  def __init__(self, sock, requesting_from, potential_peers):
    Handler.__init__(self, sock, requesting_from, potential_peers)
    self.state = "NOT_CONNECTED"
    self.timeout = 10

  def init_handshake(self):
    # first assemble string of bytes
    hs = self.make_handshake()
    # send handshake
    print "Sending Handshake"
    self.send(hs)
    # check recived handshake
    remote_hs = self.recv()
    if(not remote_hs or not self.check_handshake(remote_hs)):
        print "closing socket"
        self.sock.close()
        return False
    else:
        print "Handshake done"
        return True

  def handle(self):
    try:
      while True:
        print("RequestHandler: got connection")
        if(self.state == "NOT_CONNECTED"):
          if(self.init_handshake()):
            self.state = "REQUESTING"
        return
    except socket.timeout:
      self.sock.close()
    except socket.error:
      self.sock.close()


class ConnectionHandler(Handler):
  """Handles a single client request"""

  def __init__(self, sock, seeding_to, potential_peers):
    Handler.__init__(self, sock, seeding_to, potential_peers)
    self.state = "NOT_CONNECTED"
    self.timeout = 10

  def handle(self):
    try:
      while True:
        print("ConnectionHandler: got connection")
        if(self.state == "NOT_CONNECTED"):
          self.recv_handshake()
        self.sock.close()
        return
    except socket.timeout:
      self.sock.close()
    except socket.error:
      self.sock.close()

def get_peers_from_tracker():
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
    return r_d['peers']

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
  seeding_to = PeerList()
  requesting_from = PeerList()
  potential_peers = PeerList(get_peers_from_tracker())

  for i in xrange(8):
    # Create the 8 seeder threads for requesting connections
    seederThread    = Seeder(connectionList, seeding_to, potential_peers)
    requesterThread = Requester(potential_peers, requesting_from)
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
