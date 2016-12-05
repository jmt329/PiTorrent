#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from urlparse import urlparse
import urllib
import bencode
import sys
import hashlib

PORT_NUMBER = 8080

info_hash = ""

response = {
    'interval': str(30),
    'peers': []
    }

b_response = ""

def peer_in_list(p_id):
    """ Takes a peer_id as a string and searches current peer list for this
    peer to see if it exists already. Returns True if in list, else False  """
    for peer in response['peers']:
        if peer['peer_id'] == p_id:
            return True
    return False

def is_valid_request(params):
    """ Takes a dictionary and verifies that it is a valid request and is
    requesting the correct info_hash """
    try:
        test = params['peer_id']
        test = params['port']
        test = params['uploaded']
        test = params['downloaded']
        test = params['left']
        test = bytearray(params['info_hash'])
        return test == info_hash
    except:
        return false
    

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
        
  #Handler for the GET requests
  def do_GET(self):
    global b_response, response
    self.send_response(200)
    self.send_header('Content-type','text/plain')
    self.end_headers()
    print self.path
    url = urllib.unquote(self.path)
    params = urlparse(url).query
    params = dict(x.split("=") for x in params.split("&"))
    ip,junk = self.client_address
    if not is_valid_request(params):
        self.send_response(500)
        return
    # Have a valid request, add peer to list if necessary and send bencoded 
    #   peerlist
    if not peer_in_list(params['peer_id']):
        new_peer = dict()
        new_peer['peer_id'] = params['peer_id']
        new_peer['ip'] = ip
        new_peer['port'] = params['port']
        response['peers'].append(new_peer)
        b_response = bencode.bencode(response)
    print response

    # TODO: Deal with timeout of peers
    
    # Send the html message
    #self.send_response(200, b_response)
    self.wfile.write(b_response)
    return

try:
  #Create a web server and define the handler to manage the
  #incoming request
  if len(sys.argv) < 2:
    print "Error: must provide metainfo file of extension .pt"
    sys.exit()
  mi_filename = sys.argv[1]
  if not mi_filename.endswith(".pt"):
    print "Error: must provide metainfo file of extension .pt"
    sys.exit()
  # Read file and create info_hash 
  # TODO: Should be hashing on "info" key of meta_info file
  meta_info = {}
  with open(mi_filename, 'rb') as f:
    meta_info = bencode.bdecode(f.read())
  # Read file and create info_hash 
  info_hash = hashlib.sha1()
  info_hash.update(bencode.bencode(meta_info['info']))
  info_hash = bytearray(info_hash.digest())

  server = HTTPServer(('', PORT_NUMBER), myHandler)
  sa = server.socket.getsockname()
  print sa[0]
  print 'Started httpserver on port ',PORT_NUMBER

  #Wait forever for incoming http requests
  server.serve_forever()

except KeyboardInterrupt:
  print '^C received, shutting down the web server'
  server.socket.close()
