# bencode.py
# Functions relevant to bencoding in BTP/1.0
# Author: James Talmage
# Date: 11/10/2016

###############################################################################
# ENCODING
###############################################################################

# returns the encoded format of t
# t must be a dictionary, list, integer or string
def bencode_any(t):
    if(type(t) == dict):
        return bencode_dict(t)
    elif(type(t) == list):
        return bencode_list(t)
    elif(type(t) == int):
        return bencode_int(t)
    elif(type(t) == str):
        return bencode_str(t)
    else:
        raise TypeError("input mist be dictionar, list, integer or string")

# returns the encoded integer i
def bencode_int(i):
    assert(type(i) == int)
    return 'i' + str(i) + 'e'

# returns the encoded string s
def bencode_str(s):
    assert(type(s) == str)
    length = len(s)
    return str(length) + ':' + s

# returns the encoded dictionary d
def bencode_dict(d):
    b_dict = 'd'
    assert(type(d) == dict)
    for key in sorted(d.keys()):
        b_dict += bencode_str(str(key)) + bencode_any(d[key])
    return b_dict + 'e'

# returns the encoded list l
# the list can only contain a dictionary, list, integer or string
def bencode_list(l):
    assert(type(l) == list)
    b_list = 'l'
    for e in l:
        b_list += bencode_any(e)
    return b_list + 'e'


###############################################################################
# DECODING
###############################################################################

# returns what has been encoded in string b
# b is a valid bencoded string
# returns a dictionary, list, integer, or string
def decode(b):
    assert(type(b) == str)
    if(b[0] == 'd'):
        return decode_dict(b)
    elif(b[0] == 'l'):
        return decode_list(b)
    elif(b[0] == 'i'):
        return decode_int(b)
    elif(b[0].isdigit()):
        return decode_str(b)

# returns int encoded in b
def decode_int(b):
    return int(b[1:-1])

# returns str encoded at the beginning b, drops the rest of b
def decode_str(b):
    length, string = b.split(':', 1)
    length = int(length)
    return string[0:length]

def decode_list(b):
    elements = b[1:-1]
    lst = []
    while(len(elements) != 0):
        if(elements[0] == 'i'):
            # e is first int, elements contain the rest of the elements
            e, elements = elements.split('e', 1)
            lst.append(decode(e+'e'))
        elif(elements[0] == 'd' or elements[0] == 'l'):
            pass
        else:
            # must be a string
            e = decode_str(elements)
            lst.append(e)
            elements = elements[elements.find(e)+len(e):]
    return lst

def decode_dict(b):
    pass
