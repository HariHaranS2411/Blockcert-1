import io
import pytest
from app.blockchain.hashing import compute_file_sha256, compute_bytes_sha256, hex_to_bytes32, bytes32_to_hex


def test_bytes_hashing():
    data = b"BlockCert Official Certificate Document Data"
    hash_hex = compute_bytes_sha256(data)
    assert len(hash_hex) == 64
    # Deterministic check
    assert hash_hex == compute_bytes_sha256(data)


def test_file_stream_hashing():
    content = b"Sample Certificate Content for Alex Johnson"
    stream = io.BytesIO(content)
    hash1 = compute_file_sha256(stream)
    hash2 = compute_bytes_sha256(content)
    assert hash1 == hash2


def test_single_byte_tamper_changes_hash():
    original = b"Standard Degree Certificate - B.S. Computer Science"
    tampered = b"Standard Degree Certificate - B.S. Computer Science."
    
    hash_orig = compute_bytes_sha256(original)
    hash_tamp = compute_bytes_sha256(tampered)
    
    assert hash_orig != hash_tamp


def test_bytes32_conversions():
    hex_str = "a" * 64
    b32 = hex_to_bytes32(hex_str)
    assert len(b32) == 32
    assert bytes32_to_hex(b32) == hex_str

    # Test with 0x prefix
    b32_prefixed = hex_to_bytes32("0x" + hex_str)
    assert b32_prefixed == b32
