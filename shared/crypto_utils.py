"""Shared cryptographic utilities."""

import secrets
import hashlib
from typing import Tuple


def generate_random_key(length: int = 32) -> str:
    """Generate a random key.

    Args:
        length: Key length in bytes

    Returns:
        Hex-encoded random key
    """
    return secrets.token_hex(length)


def generate_random_bytes(length: int = 32) -> bytes:
    """Generate random bytes.

    Args:
        length: Number of bytes

    Returns:
        Random bytes
    """
    return secrets.token_bytes(length)


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """Hash data using specified algorithm.

    Args:
        data: Data to hash
        algorithm: Hash algorithm (sha256, sha512)

    Returns:
        Hex-encoded hash
    """
    if algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal
    """
    return secrets.compare_digest(a, b)
