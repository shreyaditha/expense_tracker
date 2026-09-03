"""
main.py
-------
FastAPI application entry point.

This file:
  1. Creates the FastAPI app instance
  2. Creates all DB tables on startup
  3. Registers all routers (groups, expenses, auth, balances)
  4. Adds CORS middleware (useful when connecting a frontend later)

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, groups, expenses, balances

# ---------------------------------------------------------------------------
# Create all tables
# SQLAlchemy reads all models (imported via the routers) and creates any
# missing tables. Safe to call on every startup — it won't drop existing data.
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Expense Splitter API",
    description=(
        "A Splitwise-style API for tracking shared expenses.\n\n"
        "**Getting started:**\n"
        "1. Register an account at `POST /auth/register`\n"
        "2. Log in at `POST /auth/login` to get your Bearer token\n"
        "3. Click **Authorize** (🔒) above and paste your token\n"
        "4. Create a group, add members, add expenses, and check balances!"
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allows browser-based frontends to call this API
# In production, replace "*" with your actual frontend URL
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# Each router is a mini-application with its own routes and prefix
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(balances.router)


# ---------------------------------------------------------------------------
# Root endpoint — health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    """API health check. Returns a welcome message."""
    return {
        "message": "Expense Splitter API is running!",
        "docs": "/docs",
        "redoc": "/redoc",
    }
