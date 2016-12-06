#!/usr/bin/python
from threading import Lock, Condition, Thread
import math

class FileBuilder:
  """Monitor to handle file operations concurrently"""

  def __init__(self, file_name, file_size, piece_size, new_file=True):
    self.lock = Lock()
    self.bytes_written = 0
    self.file_size = file_size
    self.file_name = file_name
    self.total_pieces = int(math.ceil(float(file_size) / float(piece_size)))
    self.pieces_written = [0]*self.total_pieces
    self.piece_size = piece_size
    if new_file:
        with open(self.file_name, 'wb') as f:
            f.seek(self.file_size-1)
            f.write('\0')

  # offset in bytes
  def writePiece(self, piece_buffer, current_piece):
    with self.lock:
        if (current_piece != self.total_pieces - 1):
            if (len(piece_buffer) != self.piece_size):
                return
        else:
            if (len(piece_buffer) != \
                    (self.file_size - self.piece_size*(self.total_pieces-1))):
                return
        if (not self.pieces_written[current_piece]):
            # piece has not been written to yet
            with open(self.file_name, 'rb+') as f:
                f.seek(current_piece*self.piece_size)
                f.write(piece_buffer)
            self.bytes_written += len(piece_buffer)
            self.pieces_written[current_piece] = 1

  def readPiece(self, piece_number):
    with self.lock:
        if (self.pieces_written[piece_number]):
            out = ""
            with open(self.file_name, 'rb+') as f:
                f.seek(piece_number*self.piece_size)
                if (piece_number != self.total_pieces - 1):
                    out = f.read(self.piece_size)
                else:
                    out = f.read(self.file_size - \
                            self.piece_size*(self.total_pieces-1))
            print out
            return
        print "Piece not written yet"


