import base64

def decrypt_config(encoded_str: str, key: str) -> str:
    try:
        raw_bytes = base64.b64decode(encoded_str)
        raw_str = raw_bytes.decode('utf-8')
        decoded = "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(raw_str))
        return decoded
    except Exception:
        return None
