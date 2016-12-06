from threading import Lock
from bitarray  import bitarray

class PieceStatus:
    """ Keeps track if pieces have been downloaded or if they are currently being
    requested """

    def __init__(self, numPieces, haveFile=False):
        self.pieces = [0] * numPieces # initally nothing is downloaded
        if(haveFile):
            # peer is coming in as seeder
            self.pieces = [2] * numPieces
        self.lock = Lock()

    # returns an empty piece number that has not been downloaded and is not
    # currently being downloaded
    # if no empty pieces exist, return None
    def get_piece(self):
        with self.lock:
            try:
                p = self.pieces.index(0)
                self.pieces[p] = 1
            except ValueError:
                p = None
            return p

    # maks piece pieceNum as completed and verified
    def finished_piece(self, pieceNum):
        with self.lock:
            self.pieces[pieceNum] = 2

    # returns the bitarray representing the bitfield
    def get_bitfield(self):
        with self.lock:
            bf = bitarray(len(self.pieces))
            for i in xrange(len(self.pieces)):
                if(self.pieces[i] == 2):
                    bf[i] = 1
                else:
                    bf[i] = 0
            return bf

    # updates pieces with bitfield
    def update(self, bitfield):
        for i in xrange(len(bitfield)):
            if(bitfield[i] == 0):
                self.pieces[i] = 0
            else:
                self.pieces[i] = 2

    def check_piece(self, piece_idx):
        return self.pieces[piece_idx] == 2
