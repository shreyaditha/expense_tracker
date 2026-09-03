"""
routers/auth.py
---------------
Handles user registration, login, and fetching the current user's profile.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    Returns the created user (without the password hash).
    """
    # Check if email is already taken
    existing = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    new_user = models.User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)   # reload from DB to populate auto-generated fields (id, created_at)
    return new_user


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email + password.
    Returns a JWT access token to use in subsequent requests.
    """
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    # Use the same error message for wrong email AND wrong password
    # so we don't leak whether an email is registered (security best practice)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token(user_id=user.id)
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Return the profile of the currently authenticated user.
    The `get_current_user` dependency handles token verification.
    """
    return current_user
