#!/usr/bin/python

import requests

# TODO: Send HTTP request to tracker
def tracker_request(ip_addr, port, metainfo_obj):
  # TODO fill with legitimate information
  payload = {
      'info_hash' : str(0), 
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
  text = tracker_request("0.0.0.0", 8080, None)
  print text
