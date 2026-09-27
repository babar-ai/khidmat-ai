"""
Code generation utilities for Khidmat AI.
"""

import secrets
import string


def generate_booking_code(length: int = 8) -> str:
    """
    Generates a secure, human-readable uppercase alphanumeric confirmation code.
    Example: 'XY4F9K2A'
    """
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))
