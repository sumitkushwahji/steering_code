def compute_checksum(data):
    byte_arr = bytes.fromhex(data)
    checksum = 0
    for byte in byte_arr:
        checksum ^= byte
    return '{:#04x}'.format(checksum & 0xFF)
