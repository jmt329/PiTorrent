#!/usr/bin/python

import sys
import hashlib
import bencode

PIECE_SIZE = 256000 # 256 kB fixed piece size

if len(sys.argv) < 3:
  print "Error: must provide file and server name"
  sys.exit()
filename = sys.argv[1]
# Read file
meta_info = {
    'announce' : sys.argv[2],
    'info' : {}
    }
length = 0
pieces = ""
with open(filename, 'rb') as f:
  piece = f.read(PIECE_SIZE)
  length += len(piece)
  while piece != "":
    # hash each piece with sha1 and store in meta_info
    h = hashlib.sha1()
    h.update(piece)
    # Hacky fix to solve http server get errors
    pieces += str(h.digest()).replace('&','S')
    piece = f.read(PIECE_SIZE)
    length += len(piece)

meta_info['info'] = {
    'length' : length,
    'name' : filename,
    'piece_length' : PIECE_SIZE,
    'pieces' : pieces
    }
# Bencode and store to a file with same filename, new extension ".pt"
b_meta_info = bencode.bencode(meta_info)

with open(filename + ".pt", 'wb') as f:
  f.write(b_meta_info)
