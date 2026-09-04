import hashlib
import os


def compute_file_sha256(file_input) -> str:
    """
    Compute the SHA-256 hash of a file on disk or a file-like stream.
    Returns 64-character lowercase hex digest.
    """
    sha256_hash = hashlib.sha256()
    
    # If it's a file path string or os.PathLike
    if isinstance(file_input, (str, os.PathLike)):
        with open(file_input, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)
    else:
        # It's a file-like object / stream (e.g. Werkzeug FileStorage or BytesIO)
        pos = 0
        if hasattr(file_input, 'tell') and hasattr(file_input, 'seek'):
            pos = file_input.tell()
            file_input.seek(0)
            
        for chunk in iter(lambda: file_input.read(65536), b""):
            sha256_hash.update(chunk)
            
        if hasattr(file_input, 'seek'):
            file_input.seek(pos)
            
    return sha256_hash.hexdigest().lower()


def compute_bytes_sha256(data: bytes) -> str:
    """
    Compute the SHA-256 hash of raw bytes.
    """
    return hashlib.sha256(data).hexdigest().lower()


def hex_to_bytes32(hex_str: str) -> bytes:
    """
    Convert a 64-char hex string (with or without '0x' prefix) to 32 bytes for Solidity.
    """
    cleaned = hex_str[2:] if hex_str.startswith(('0x', '0X')) else hex_str
    if len(cleaned) != 64:
        raise ValueError(f"Hex string must be exactly 64 characters (32 bytes), got {len(cleaned)}")
    return bytes.fromhex(cleaned)


def bytes32_to_hex(b32) -> str:
    """
    Convert a 32-byte bytes/HexBytes object or hex string from Web3 to a 64-char lowercase hex string without '0x'.
    """
    if isinstance(b32, (bytes, bytearray)):
        return b32.hex().lower()
    elif isinstance(b32, str):
        cleaned = b32[2:] if b32.startswith(('0x', '0X')) else b32
        return cleaned.lower()
    elif hasattr(b32, 'hex'):
        return b32.hex().lower()
    return str(b32).lower()
