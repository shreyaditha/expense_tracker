"""
auth.py
-------
JWT token creation & verification + password hashing utilities.

How JWT auth works (short version):
  1. User POSTs email + password to /auth/login
  2. We verify the password, then create a signed JWT containing the user's id
  3. The client sends that token in every subsequent request as:
       Authorization: Bearer <token>
  4. Our `get_current_user` dependency (in dependencies.py) reads and verifies
     the token, returning the User object for use in route handlers
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Configuration
# Change SECRET_KEY to a long random string before deploying!
# Generate one with:  python -c "import secrets; print(secrets.token_hex(32))"
# ---------------------------------------------------------------------------
SECRET_KEY = "change-me-before-deploying-to-production-please"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# passlib context — bcrypt is the recommended hashing algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password. Always store the hash, never the plain text."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT containing the user's id in the `sub` claim.
    `sub` (subject) is the standard JWT claim for the principal (the user).
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),   # always a string in JWTs
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """
    Decode and verify a JWT.
    Returns the user_id (int) if valid, or None if expired / tampered.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        return int(user_id_str)
    except JWTError:
        return None
