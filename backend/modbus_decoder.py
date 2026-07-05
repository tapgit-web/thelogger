import struct

def decode_int(h, l):
    raw = struct.pack(">HH", h, l)
    int_value = struct.unpack(">i", raw)[0]
    return int_value

def decode_float(h, l):
    raw = struct.pack(">HH", h, l)
    return struct.unpack(">f", raw)[0]

def decode_uint(h, l):
    raw = struct.pack(">HH", h, l)
    return struct.unpack(">I", raw)[0]

def decode_int16(h):
    raw = struct.pack(">H", h)
    return struct.unpack(">h", raw)[0]

def decode_uint16(h):
    return h

def decode_bcd(h, l):
    s = f"{h:04x}{l:04x}"
    try:
        return int(s)
    except:
        return 0
