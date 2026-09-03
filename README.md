# 💸 Expense Splitter API

A **Splitwise-inspired REST API** built with FastAPI — track shared expenses between friends, calculate who owes whom, and settle up with the minimum number of transactions.

Built as a learning project to explore FastAPI's core concepts: routing, dependency injection, JWT authentication, SQLAlchemy ORM, and non-trivial computed responses.

---

## ✨ Features

- 🔐 **JWT Authentication** — register, log in, and access protected routes
- 👥 **Groups** — create groups, invite friends, manage membership
- 💳 **Expenses** — add expenses with automatic equal split or custom per-person amounts
- 📊 **Smart Balances** — computed net balances (not just DB reads)
- 🔁 **Debt Simplification** — greedy algorithm to minimize the number of payments needed
- 📖 **Auto-generated docs** — Swagger UI at `/docs`, ReDoc at `/redoc`

---

## 🗂️ Project Structure

```
expense_tracker_fast_api/
├── app/
│   ├── main.py           # App entry point — creates app, registers routers
│   ├── database.py       # SQLAlchemy engine & session factory
│   ├── models.py         # ORM models: User, Group, GroupMember, Expense, ExpenseSplit
│   ├── schemas.py        # Pydantic schemas for request/response validation
│   ├── auth.py           # JWT creation/verification + bcrypt password hashing
│   ├── dependencies.py   # Reusable FastAPI dependencies (get_db, get_current_user)
│   └── routers/
│       ├── auth.py       # POST /auth/register  POST /auth/login  GET /auth/me
│       ├── groups.py     # CRUD for groups + membership management
│       ├── expenses.py   # CRUD for expenses with split logic
│       └── balances.py   # GET /groups/{id}/balances  ← the interesting computed endpoint
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone and install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/expense-splitter-api.git
cd expense-splitter-api

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be live at **http://localhost:8000**

### 3. Explore the docs

Open **http://localhost:8000/docs** in your browser to get the full interactive Swagger UI.

---

## 🔑 Authentication Flow

```
POST /auth/register    →  create account
POST /auth/login       →  get JWT token
                          (use token as: Authorization: Bearer <token>)
GET  /auth/me          →  verify token / get your profile
```

In Swagger UI, click the **🔒 Authorize** button and paste your token.

---

## 📋 API Endpoints

### Auth
| Method | Endpoint | Auth? | Description |
|--------|----------|-------|-------------|
| POST | `/auth/register` | ❌ | Create a new account |
| POST | `/auth/login` | ❌ | Log in, receive JWT token |
| GET | `/auth/me` | ✅ | Get current user profile |

### Groups
| Method | Endpoint | Auth? | Description |
|--------|----------|-------|-------------|
| POST | `/groups/` | ✅ | Create a group (you become creator + member) |
| GET | `/groups/` | ✅ | List groups you're a member of |
| GET | `/groups/{id}` | ✅ | Get group details |
| PUT | `/groups/{id}` | ✅ | Update group (creator only) |
| DELETE | `/groups/{id}` | ✅ | Delete group (creator only) |
| GET | `/groups/{id}/members` | ✅ | List members |
| POST | `/groups/{id}/members` | ✅ | Add a member |
| DELETE | `/groups/{id}/members/{user_id}` | ✅ | Remove a member (creator only) |

### Expenses
| Method | Endpoint | Auth? | Description |
|--------|----------|-------|-------------|
| POST | `/groups/{id}/expenses` | ✅ | Add an expense (equal or custom split) |
| GET | `/groups/{id}/expenses` | ✅ | List expenses in a group |
| GET | `/expenses/{id}` | ✅ | Get a single expense |
| PUT | `/expenses/{id}` | ✅ | Update expense (expense owner only) |
| DELETE | `/expenses/{id}` | ✅ | Delete expense |

### Balances ⭐
| Method | Endpoint | Auth? | Description |
|--------|----------|-------|-------------|
| GET | `/groups/{id}/balances` | ✅ | Net balances + simplified settlements |

---

## 🧮 How Balance Calculation Works

For every expense in the group:

```
net[payer]        += expense.amount          # they fronted the money
net[each_member]  -= their split share       # they owe their portion
```

**Example:**
- Alice pays £90 for dinner — split equally among Alice, Bob, Carol (£30 each)
- Bob pays £60 for taxi — split equally (£20 each)

| User | Paid | Owes | Net |
|------|------|------|-----|
| Alice | £90 | £30+£20 = £50 | **+£40** |
| Bob | £60 | £30+£20 = £50 | **+£10** |
| Carol | £0 | £30+£20 = £50 | **−£50** |

**Simplified settlements** (greedy algorithm — minimal transactions):
- Carol → Alice: £40
- Carol → Bob: £10

---

## 🏗️ Data Models

```
User ──────────────────────────────────────────────────────
  id, email, full_name, hashed_password, created_at

Group ─────────────────────────────────────────────────────
  id, name, description, created_by (FK→User), created_at

GroupMember  (User ↔ Group many-to-many) ─────────────────
  id, group_id (FK→Group), user_id (FK→User), joined_at

Expense ───────────────────────────────────────────────────
  id, group_id (FK→Group), paid_by (FK→User),
  title, amount, description, created_at

ExpenseSplit ──────────────────────────────────────────────
  id, expense_id (FK→Expense), user_id (FK→User), share_amount
```

---

## 🗄️ Database

Uses **SQLite** by default — zero config, file-based (`expense_tracker.db` is auto-created).

To switch to **PostgreSQL**:
1. `pip install psycopg2-binary`
2. Change one line in `app/database.py`:
   ```python
   DATABASE_URL = "postgresql://user:password@localhost/dbname"
   ```
   And remove the `connect_args` from `create_engine()`.

---

## 🧠 Key FastAPI Concepts Used

| Concept | Where to find it |
|---------|-----------------|
| **Dependency Injection** | `app/dependencies.py` — `get_db`, `get_current_user` |
| **Pydantic Validation** | `app/schemas.py` — request/response models with validators |
| **SQLAlchemy ORM** | `app/models.py` — relationships, cascade deletes |
| **JWT Auth** | `app/auth.py` — token creation & decoding |
| **Router organisation** | `app/routers/` — each domain has its own file |
| **Computed responses** | `app/routers/balances.py` — logic beyond simple DB reads |
| **HTTP status codes** | `status_code=201` for creates, `204` for deletes |

---

## 📦 Tech Stack

| | |
|-|-|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **ORM** | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) |
| **Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Auth** | [python-jose](https://github.com/mpdavis/python-jose) (JWT) + [passlib](https://passlib.readthedocs.io/) (bcrypt) |
| **Database** | SQLite (dev) / PostgreSQL (prod-ready) |
| **Server** | [Uvicorn](https://www.uvicorn.org/) |

---

## 📝 License

MIT — free to use, modify, and share.
