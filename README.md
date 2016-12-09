# PiTorrent

An implementation of a subset of the BitTorrent Protocol (BTP) v1.0

To use:

  You must have the following packages installed using pip:
  
  bencode
  
  bitarray
  
  requests

  To make a metainfo file (pitorrent file, *.pt):
    
    python make_metainfo_file.py < file_to_seed > < tracker_server_name >

  To make start the tracker server:
    
    python http_server.py <.pt_file>

  To open a client:
    
    python peer.py -p <port_number_to_use> -n < name_of_file > -m < .pt_file > -s < True if seeder, else false > -i < client name >


