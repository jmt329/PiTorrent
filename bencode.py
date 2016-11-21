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

# helper function that takes in a string s and returns the first key value pair
# and the rest of the string in the form (key, value, rest)
def dict_helper(s):
    pass

# returns the dictionary encoded in d
def decode_dict(d):
    decoded_d = {}
    d = d[1:-1] # get rid of surrounding d and e
    while(len(d) != 0):
        (key, value, d) = dict_helper(d)
        decoded_d[key] = value
    return decoded_d
