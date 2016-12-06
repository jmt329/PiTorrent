#!/usr/bin/python
from threading import Lock, Condition, Thread
import math
from PieceStatus import PieceStatus

class Peer:
  """Inner class representing a single peer"""
  def __init__(self, peer_id, num_pieces):
    self.lock = Lock()
    self.peer_id = peer_id
    self.broadcast = []
    self.num_pieces = num_pieces
    self.pieces = PieceStatus(self.num_pieces)

  def add_broadcast(self, bc):
    with self.lock:
      self.broadcast.append(bc)

  def get_broadcast(self):
    with self.lock:
      if (len(self.broadcast) == 0):
        return None
      return self.broadcast.pop()

  def get_id(self):
    return self.peer_id

  def update(self, bitfield):
    with self.lock:
      self.pieces.update(bitfield)

  def finished_piece(self, piece_idx):
    with self.lock:
      self.pieces.finished_piece(piece_idx)

  def check_piece(self, piece_idx):
    with self.lock:
      self.pieces.check_piece(piece_idx)

class PeerInfo:
  """Monitor to handle the information a peer has about all other peers"""

  def __init__(self, num_pieces):
    self.lock = Lock()
    self.peers = []
    self.num_pieces = num_pieces

  def add(self, peer_id, bitfield):
    with self.lock:
      p = Peer(peer_id, self.num_pieces)
      p.update(bitfield)
      self.peers.append(p)

  def broadcast(self, piece_idx):
    for p in self.peers:
      p.add_broadcast(piece_idx)

  def update(self, peer_id, piece_idx):
    for p in self.peers:
      if (p.get_id() == peer_id):
        p.finished_piece(piece_idx)

  def get_broadcast(self, peer_id):
    for p in self.peers:
      if (p.get_id() == peer_id):
        return p.get_broadcast()

  def check_piece(self, peer_id, piece_idx):
    for p in self.peers:
      if (p.get_id() == peer_id):
        return p.check_piece(piece_idx)
