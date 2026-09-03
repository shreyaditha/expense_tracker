"""
models.py
---------
All SQLAlchemy ORM models live here.

Relationships at a glance:
  User  <──M:M──>  Group        (via GroupMember)
  Group <──1:M──>  Expense
  Expense <──1:M──> ExpenseSplit
  ExpenseSplit references a User (who owes their share)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey,
    DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Reverse relationships
    group_memberships = relationship("GroupMember", back_populates="user")
    expenses_paid = relationship("Expense", back_populates="paid_by_user")
    expense_splits = relationship("ExpenseSplit", back_populates="user")


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------
class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="group", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# GroupMember  (association table with extra data)
# ---------------------------------------------------------------------------
class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=utcnow)

    # Prevent the same user being added to the same group twice
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)

    group = relationship("Group", back_populates="expenses")
    paid_by_user = relationship("User", back_populates="expenses_paid")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# ExpenseSplit  — who owes how much for a given expense
# ---------------------------------------------------------------------------
class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    share_amount = Column(Float, nullable=False)   # how much this user owes

    expense = relationship("Expense", back_populates="splits")
    user = relationship("User", back_populates="expense_splits")
