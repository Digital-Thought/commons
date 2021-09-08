import base64


def to_base64_string(bytes_data: bytes) -> str:
    return to_base64_bytes(bytes_data).decode('ascii')


def to_base64_bytes(bytes_data: bytes) -> bytes:
    return base64.b64encode(bytes_data)
