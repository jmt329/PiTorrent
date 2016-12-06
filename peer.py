import getopt
import socket
import sys
import time
import os
import hashlib
import requests
import bencode
import sys
import struct
from file_monitor import FileBuilder
from time         import sleep
from PieceStatus  import PieceStatus
from PeerInfo     import PeerInfo
from bitarray     import bitarray
from threading    import Lock, Condition, Thread

my_host = "0.0.0.0"
my_port = 8080
BUFFER_SIZE = 4096
dest_file_name = ""
info_filename = ""
info = {}
my_peer_id = ""
seeder = False
peer_info = None
numPieces = 0
fixed_block_size = 4000
number_of_blocks = 0
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

  def __init__(self, connectionQueue, seeding_to, potential_peers, \
               piece_status, file_builder):
    Thread.__init__(self)
    self.connections     = connectionQueue
    self.seeding_to      = seeding_to
    self.potential_peers = potential_peers
    self.piece_status    = piece_status
    self.file_builder    = file_builder

  def run(self):
    # Get work to do and do it
    while True:
      # Get a connection
      sock = self.connections.getConnection()
      ct = ConnectionHandler(sock, self.seeding_to, self.potential_peers, \
                             self.piece_status, self.file_builder)
      ct.handle()

class Requester(Thread):
  """Requester threads for requesting pieces from other clients"""

  def __init__(self, potential_peers, requesting_from, piece_status, \
               file_builder):
    Thread.__init__(self)
    self.potential_peers = potential_peers # peers from server
    self.requesting_from = requesting_from
    self.piece_status    = piece_status
    self.file_builder    = file_builder

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
        rh = RequestHandler(sock, self.requesting_from, self.potential_peers, \
                            self.piece_status, self.file_builder)
        rh.handle()

class Handler:

  def __init__(self, sock, connected_peers, potential_peers, piece_status, \
               file_builder):
    self.sock = sock
    self.connected_peers = connected_peers
    self.potential_peers = potential_peers
    self.piece_status    = piece_status
    self.pid             = '' # peer id of successful connection
    self.file_builder    = file_builder

  def send(self, message):
    self.sock.sendall(message)

  def recv(self):
    return self.sock.recv(BUFFER_SIZE)

  def recvall(self, size):
    print "in recvall"
    data = ''
    while len(data) < size:
      msg = self.sock.recv(size - len(data))
      if not msg:
        return None
      data += msg
    return data

  def recv_pwp_message(self):
    print "in recv_pwp_message"
    msg_len = self.recvall(4)
    msg_len = (struct.unpack("!i", msg_len))[0]
    msg = self.recvall(msg_len)
    msg_id = bytearray(msg[0])[0]
    return (msg_id, msg[1:])

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
    # check if peer is valid
    # not already connected to peer, peer_id is not mine, and in list from tracker
    if(self.connected_peers.contains(hs[48:]) or (hs[48:] == name_hash) or \
       (valid_peers.contains_hashed_key('peer_id', hs[48:]))):
      print "Same name as current peer"
      return False
    # save pid and valid peer so add to connected list
    self.pid = hs[48:]
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
    hs = self.recvall(68)
    # check handshake
    if(not self.check_handshake(hs)):
      # not a valid handshake
      print "closing socket"
      self.sock.close()
      return False
    else:
      # send handshake back
      print "Sending handshake back"
      hs = self.make_handshake()
      self.send(hs)
      return True

  def send_pwp(self, messageID, payload):
    # Build peer wire message, expected payload as bytearray
    print "In send pwp"
    length = 1 + len(payload)
    message = bytearray()
    message.extend(struct.pack("!i", length))
    message.append(messageID)
    message.extend(payload)
    # Message built, send
    self.send(message)

  def recv_pwp(self):
    msg_id, payload = self.recv_pwp_message()
    if(payload == None):
      # connection is closed or something
      pass # TODO fail
    if(msg_id == 4):
      # Have
      return 4
    elif(msg_id == 5):
      # Bitfield
      bits = bitarray()
      bits.frombytes(payload)
      print numPieces
      self.recv_bitfield(bits[0:numPieces])
      return 5
    elif(msg_id == 6):
      # Request
      print "Got request"
      # TODO: send piece
      return 6
    elif(msg_id == 7):
      # Piece
      return (7, self.recv_piece(payload))

  def recv_piece(self, payload):
    piece_index = (struct.unpack("!i", payload[0:4]))[0]
    block_offset = (struct.unpack("!i", payload[4:8]))[0]
    block = payload[8:]
    return (piece_index, block_offset, block)

  def send_bitfield(self):
    bf = self.piece_status.get_bitfield()
    print "send_bitfield: len(bf) = " + str(len(bf))
    self.send_pwp(5, bf.tobytes())
    print "Sent bitfield"

  def recv_bitfield(self, bf):
    print "recieved bitfield: " + `bf`
    peer_info.add(self.pid, bf)
    print "recived bitfield"


class RequestHandler(Handler):
  """Makes a request to a single client"""

  def __init__(self, sock, requesting_from, potential_peers, piece_status, \
               file_builder):
    Handler.__init__(self, sock, requesting_from, potential_peers, piece_status, \
                     file_builder)
    self.state = "NOT_CONNECTED"

  def init_handshake(self):
    # first assemble string of bytes
    hs = self.make_handshake()
    # send handshake
    print "Sending Handshake"
    self.send(hs)
    # check recived handshake
    remote_hs = self.recvall(68)
    if(not remote_hs or not self.check_handshake(remote_hs)):
        print "closing socket"
        self.sock.close()
        return False
    else:
        print "Handshake done"
        return True

  def req_piece(self, p):
    print "in req_piece"
    piece_acc = ""
    for bo in xrange(0, fixed_block_size*number_of_blocks, fixed_block_size):
      payload = bytearray()
      payload.extend(struct.pack("!i", p))
      payload.extend(struct.pack("!i", bo))
      payload.extend(struct.pack("!i", fixed_block_size))
      self.send_pwp(6, payload)
      # wait for block
      block[1][2] = self.recv_pwp()
      piece_acc += block
      print "sent req for block offset: " + str(bo)
    # TODO validate piece (maybe)
    self.file_builder.writePiece(piece_acc, p)
    self.piece_status.finished_piece(p)
    self.peer_info.broadcast(p)

  def handle(self):
    try:
      while True:
        #print("RequestHandler: got connection")
        if(self.state == "NOT_CONNECTED"):
          if(self.init_handshake()):

            self.send_bitfield()
            print "sent bitfield in handle"
            if(self.recv_pwp() == 5):
              print "pwp 5"
              self.state = "REQ"
            else:
              print "something went wrong in RequestHandler"
        elif(self.state == "REQ"):
          # send out have
          p = self.piece_status.get_piece()
          if(p == None or peer_info.check_piece(self.pid, p) == 0):
            continue
          else:
            self.req_piece(p)
          # check if done and move state
          if(self.piece_status.is_done()):
            self.state = "DONE"

          # if peer doesn't have any pieces I need: wait on CV for file to finish
          # or sender to get a new piece
          # once full piece is downloaded and verified, broadcast HAVE
          # if file finishes: close connection, move to state NOT_CONNECTED
          pass
    except socket.timeout:
      self.sock.close()
    except socket.error:
      self.sock.close()


class ConnectionHandler(Handler):
  """Handles a single client request"""

  def __init__(self, sock, seeding_to, potential_peers, piece_status, \
               file_builder):
    Handler.__init__(self, sock, seeding_to, potential_peers, piece_status, \
                     file_builder)
    self.state = "NOT_CONNECTED"
    self.timeout = 10

  def handle(self):
    try:
      while True:
        if(self.state == "NOT_CONNECTED"):
          if(self.recv_handshake()):
            sleep(.1)
            # sent back handshake
            self.send_bitfield()
            if(self.recv_pwp() == 5):
              self.state = "RESP"
              print "pwp 5"
            else:
              print "Something went wrong in ConnectionHandler"
        if(self.state == "RESP"):
          print "In state RESP"
          print "piece_status: " + str(self.piece_status.pieces)
          # read from port
          self.recv_pwp()
          # if Have, update
          # if data, save
          pass
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
  connectionList  = ConnectionQueue()
  seeding_to      = PeerList()
  requesting_from = PeerList()
  potential_peers = PeerList(get_peers_from_tracker())
  global numPieces
  numPieces       = len(info['info']['pieces'])/20
  global number_of_blocks
  number_of_blocks = (info['info']['piece_length']/fixed_block_size) + \
                     (not (not (info['info']['piece_length']%fixed_block_size)))
  piece_status    = PieceStatus(numPieces, seeder)
  global peer_info
  peer_info       = PeerInfo(numPieces)
  file_builder = FileBuilder(dest_file_name, info['info']['length'], \
                             info['info']['piece_length'])

  for i in xrange(8):
    # Create the 8 seeder threads for requesting connections
    seederThread    = Seeder(connectionList, seeding_to, potential_peers, \
                             piece_status, file_builder)
    requesterThread = Requester(potential_peers, requesting_from, \
                                piece_status, file_builder)
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

opts, args = getopt.getopt(sys.argv[1:], 'h:p:m:i:s:n:', \
                           ['host=', 'port=', 'metainfo=', \
                            'peer_id=', 'seeder=', 'name='])

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
    if k in ('-s', '--seeder'):
      seeder = v
    if k in ('-n', '--name'):
      dest_file_name = v

print("Server coming up on %s:%i" % (my_host, my_port))
serverloop()
