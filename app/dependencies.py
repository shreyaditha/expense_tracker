"""
dependencies.py
---------------
FastAPI dependency functions that can be injected into any route.

FastAPI's Depends() system is one of its killer features:
  - You declare what a route needs (db session, current user, etc.)
  - FastAPI resolves and injects them automatically
  - It also handles cleanup (e.g. closing the DB session) via generators

Usage in a route:
    @router.get("/something")
    def my_route(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import decode_access_token
from app import models

# HTTPBearer parses "Authorization: Bearer <token>" from request headers
bearer_scheme = HTTPBearer()


def get_db():
    """
    Yield a database session for the duration of a request.
    The `finally` block ensures the session is always closed,
    even if an exception occurs — preventing connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Verify the JWT token from the Authorization header and return the User.
    Raise 401 if the token is missing, expired, or invalid.
    Raise 404 if the user no longer exists in the database.
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    return user
