import socket
import hashlib
import struct

host = "127.0.0.1"
port = 8080
BUFFER_SIZE = 1024
info = "TestMetainfo"
peer_name = "TestPeer1"
connected_peers = [] # list of peer name currently connected to client

def big_send():
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect((host, port))
    print("client connected to server")
    clientsocket.send("test\n"*1000)
    pass

def recvall(sock, size):
    data = ''
    while len(data) < size:
        msg = sock.recv(size - len(data))
        if not msg:
            return None
        data += msg
    return data

def recv_pwp_message(sock):
    msg_len = recvall(sock, 4)
    msg_len = (struct.unpack("!i", msg_len))[0]
    msg = recvall(sock, msg_len)
    msg_id = bytearray(msg[0])[0]
    return (msg_id, msg[1:])


serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# mark the socket so we can rebind quickly to this port number
# after the socket is closed
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# bind the socket to the local loopback IP address and special port
serversocket.bind((host, port))
# start listening with a backlog of 5 connections
serversocket.listen(5)


(clientsocket, address) = serversocket.accept()
out = recv_pwp(clientsocket)
print `out`
