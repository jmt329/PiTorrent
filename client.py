#!/usr/bin/python

import requests
import sys
import hashlib
import bencode

info_hash = bytearray()

# TODO: Send HTTP request to tracker
def tracker_request(ip_addr, port, metainfo_obj):
  # TODO fill with legitimate information
  payload = {
      'info_hash' : str(info_hash), 
      'peer_id' : str(0), 
      'port' : str(8080),
      'uploaded' : str(0),
      'downloaded' : str(0),
      'left' : str(0)
      }
  req_addr = "http://" + ip_addr + ":" + str(port)
  r = requests.get(req_addr, params=payload)
  return r.text

# TODO: Take in metainfo file, parse it for relevant info

# TODO: Spawn threads to handle Peer connections and downloading


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print "Error: must provide metainfo file of extension .pt"
    sys.exit()
  mi_filename = sys.argv[1]
  if not mi_filename.endswith(".pt"):
    print "Error: must provide metainfo file of extension .pt"
    sys.exit()
  meta_info = {}
  with open(mi_filename, 'rb') as f:
    meta_info = bencode.bdecode(f.read())
  # Read file and create info_hash 
  info_hash = hashlib.sha1()
  info_hash.update(bencode.bencode(meta_info['info']))
  info_hash = bytearray(info_hash.digest())
  text = tracker_request("0.0.0.0", 8080, None)
  print text
