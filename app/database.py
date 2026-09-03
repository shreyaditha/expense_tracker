"""
database.py
-----------
Sets up the SQLAlchemy engine and session factory.

We use SQLite here for zero-config local development.
To switch to PostgreSQL, just change DATABASE_URL to:
    "postgresql://user:password@localhost/dbname"
and install psycopg2:  pip install psycopg2-binary
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# SQLite file will be created in the project root
DATABASE_URL = "sqlite:///./expense_tracker.db"

# connect_args is SQLite-specific: allows multi-thread access
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Each request gets its own Session from this factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class that all ORM models inherit from
class Base(DeclarativeBase):
    pass
