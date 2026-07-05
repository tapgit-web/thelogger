import struct

def decode_int16(h: int) -> int:
    return struct.unpack(">h", struct.pack(">H", h))[0]

def decode_uint16(h: int) -> int:
    return h

def decode_int32(h: int, l: int) -> int:
    return struct.unpack(">i", struct.pack(">HH", h, l))[0]

def decode_uint32(h: int, l: int) -> int:
    return struct.unpack(">I", struct.pack(">HH", h, l))[0]

def decode_float32(h: int, l: int) -> float:
    return struct.unpack(">f", struct.pack(">HH", h, l))[0]

def decode_bcd(h: int, l: int) -> int:
    try:
        s = f"{h:04x}{l:04x}"
        return int(s)
    except Exception:
        return 0
