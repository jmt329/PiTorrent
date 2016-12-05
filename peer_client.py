import socket
import hashlib

host = "127.0.0.1"
port = 8765
BUFFER_SIZE = 1024
info = "TestMetainfo"
peer_name = "TestPeer1"
connected_peers = [] # list of peer name currently connected to client

def make_handshake():
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

def send_handshake(hs):
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect((host, port))
    print("client connected to server")
    clientsocket.send(hs)

def check_handshake(hs):
    hs = bytearray(hs)
    if(hs[0] != 19):
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
    if(hs[48:] in connected_peers or hs[48:] == peer_name):
        print "Same name as current peer"
        return False
    return True

def init_handshake():
    # first assemble string of bytes
    hs = make_handshake()
    # send handshake
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect((host, port))
    print("client connected to server")
    clientsocket.send(hs)
    # check recived handshake
    remote_hs = clientsocket.recv(BUFFER_SIZE)
    if(not remote_hs or not check_handshake(remote_hs)):
        print "closing socket"
        clientsocket.close()
    else:
        print "Handshake done"

init_handshake()
