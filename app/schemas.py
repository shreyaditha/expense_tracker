"""
schemas.py
----------
Pydantic schemas for request validation and response serialisation.

Convention used here:
  - <Model>Create  →  body of POST requests (input)
  - <Model>Update  →  body of PUT requests  (input, all fields optional)
  - <Model>Out     →  what the API returns   (output)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ===========================================================================
# Auth / User
# ===========================================================================

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===========================================================================
# Group
# ===========================================================================

class GroupCreate(BaseModel):
    name: str
    description: str = ""


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Group Member
# ===========================================================================

class AddMemberRequest(BaseModel):
    user_id: int


class GroupMemberOut(BaseModel):
    id: int
    group_id: int
    user_id: int
    joined_at: datetime
    user: UserOut

    model_config = {"from_attributes": True}


# ===========================================================================
# Expense
# ===========================================================================

class SplitInput(BaseModel):
    """
    Optional per-user split amounts.
    If provided, share_amount is the exact amount this user owes.
    """
    user_id: int
    share_amount: float


class ExpenseCreate(BaseModel):
    title: str
    amount: float
    description: str = ""

    # If splits is empty → divide equally among all group members
    splits: list[SplitInput] = []

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be positive")
        return round(v, 2)


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


class SplitOut(BaseModel):
    id: int
    user_id: int
    share_amount: float
    user: UserOut

    model_config = {"from_attributes": True}


class ExpenseOut(BaseModel):
    id: int
    group_id: int
    paid_by: int
    title: str
    amount: float
    description: str
    created_at: datetime
    splits: list[SplitOut]
    paid_by_user: UserOut

    model_config = {"from_attributes": True}


# ===========================================================================
# Balances  (computed — not backed by a single DB table)
# ===========================================================================

class UserBalance(BaseModel):
    """Net balance for one user in a group. Positive = owed money, Negative = owes money."""
    user_id: int
    full_name: str
    email: str
    net_balance: float   # positive → is owed this amount; negative → owes this amount


class Settlement(BaseModel):
    """A single simplified payment that clears debt."""
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: float        # how much `from_user` should pay `to_user`


class BalanceSummary(BaseModel):
    group_id: int
    group_name: str
    balances: list[UserBalance]
    settlements: list[Settlement]
