"""
app/auth/password.py
--------------------
Password hashing and verification using bcrypt via passlib.

Why bcrypt?
- Designed specifically for passwords (slow by design).
- Includes a built-in salt, so identical passwords produce different hashes.
- Industry standard — used by Django, Spring Security, etc.
"""

from passlib.context import CryptContext

# CryptContext handles algorithm versioning — if you ever switch from bcrypt,
# you can add the new scheme and it will auto-upgrade on next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password.
    Returns a bcrypt hash string like: $2b$12$...
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plain-text password against its stored bcrypt hash.
    Returns True if they match, False otherwise.
    
    Uses constant-time comparison internally to prevent timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)
