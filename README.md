# Expense Splitter API

A production-style RESTful API built with FastAPI and SQLAlchemy to track shared group expenses, compute user net balances, and generate minimal debt settlement schedules (similar to Splitwise).

---

## Overview

When groups of people share costs (trips, rent, dining, events), tracking who paid what and calculating who owes whom becomes complex. This project provides a complete backend solution with:

- User authentication using JWT tokens and bcrypt password hashing.
- Group management with role-based member control.
- Flexible expense logging supporting equal distribution and custom itemized splits.
- Real-time balance evaluation and a greedy debt simplification algorithm to settle debts in the minimum number of transactions.
- Interactive documentation auto-generated via OpenAPI (Swagger UI and ReDoc).

---

## Architecture and Technology Stack

- **Web Framework:** FastAPI (ASGI based on Starlette)
- **Data Validation:** Pydantic v2
- **ORM / Database Layer:** SQLAlchemy 2.0 with SQLite (configurable to PostgreSQL)
- **Security:** JSON Web Tokens (python-jose), Password Hashing (bcrypt)
- **ASGI Server:** Uvicorn

---

## Directory Structure

```text
expense_tracker_fast_api/
|-- app/
|   |-- __init__.py
|   |-- main.py              # Application initialization, middleware, router setup
|   |-- database.py          # Database engine and session factory
|   |-- models.py            # SQLAlchemy database tables and relationships
|   |-- schemas.py           # Pydantic request and response schemas
|   |-- auth.py              # JWT encoding/decoding and bcrypt utilities
|   |-- dependencies.py      # Dependency injection (get_db, get_current_user)
|   `-- routers/
|       |-- __init__.py
|       |-- auth.py          # Authentication routes (register, login, me)
|       |-- groups.py        # Group CRUD and membership management
|       |-- expenses.py      # Expense creation and split recording
|       `-- balances.py      # Balance calculation and debt simplification
|-- requirements.txt         # Project dependencies
|-- .gitignore               # Ignored files and directories
`-- README.md                # Project documentation
```

---

## Database Models

The relational structure consists of five entities:

1. **User (`users`)**
   - `id`: Primary key integer.
   - `email`: Unique string identifier for authentication.
   - `full_name`: Display name.
   - `hashed_password`: Salted bcrypt hash.
   - `created_at`: Timestamp.

2. **Group (`groups`)**
   - `id`: Primary key integer.
   - `name`: Name of the group.
   - `description`: Group description or notes.
   - `created_by`: Foreign key pointing to `users.id`.
   - `created_at`: Timestamp.

3. **GroupMember (`group_members`)**
   - Association table enforcing a many-to-many relationship between `users` and `groups`.
   - Constrained by a unique constraint on `(group_id, user_id)`.

4. **Expense (`expenses`)**
   - `id`: Primary key integer.
   - `group_id`: Foreign key pointing to `groups.id`.
   - `paid_by`: Foreign key pointing to `users.id` (the person who fronted payment).
   - `title`: Short label describing the expense.
   - `amount`: Total amount paid.
   - `description`: Optional notes.
   - `created_at`: Timestamp.

5. **ExpenseSplit (`expense_splits`)**
   - `id`: Primary key integer.
   - `expense_id`: Foreign key pointing to `expenses.id`.
   - `user_id`: Foreign key pointing to `users.id` (the participant who owes a portion).
   - `share_amount`: Exact monetary value owed by the participant.

---

## Setup and Installation

### Prerequisites

- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- pip package manager
- virtualenv (optional but recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/expense-splitter-api.git
cd expense-splitter-api
```

### 2. Create and Activate a Virtual Environment

On Windows (Command Prompt / PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\activate
```

On Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://127.0.0.1:8000`.

---

## Interactive Documentation

Once the server is running, visit:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

Use the Swagger UI interface to test requests directly in your browser. Click the **Authorize** button at the top right to pass Bearer tokens to protected endpoints.

---

## API Specification

### Authentication

#### Register a User
- **POST** `/auth/register`
- **Body:**
```json
{
  "email": "alex@example.com",
  "full_name": "Alex Mercer",
  "password": "securepassword123"
}
```
- **Response (201 Created):**
```json
{
  "id": 1,
  "email": "alex@example.com",
  "full_name": "Alex Mercer",
  "created_at": "2026-09-03T09:15:00"
}
```

#### Log In
- **POST** `/auth/login`
- **Body:**
```json
{
  "email": "alex@example.com",
  "password": "securepassword123"
}
```
- **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

#### Get Current Profile
- **GET** `/auth/me`
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):** Current user object.

---

### Groups

All group routes require authentication.

| Method | Route | Description |
|---|---|---|
| `POST` | `/groups/` | Create a new group (creator is automatically added as a member) |
| `GET` | `/groups/` | List all groups the authenticated user belongs to |
| `GET` | `/groups/{group_id}` | Retrieve details of a specific group |
| `PUT` | `/groups/{group_id}` | Update group details (creator only) |
| `DELETE` | `/groups/{group_id}` | Delete group and all associated records (creator only) |
| `GET` | `/groups/{group_id}/members` | List members of a group |
| `POST` | `/groups/{group_id}/members` | Add a registered user to the group by user_id |
| `DELETE` | `/groups/{group_id}/members/{user_id}` | Remove a member from the group (creator only) |

---

### Expenses

| Method | Route | Description |
|---|---|---|
| `POST` | `/groups/{group_id}/expenses` | Record an expense for the group |
| `GET` | `/groups/{group_id}/expenses` | Retrieve all expenses for the group |
| `GET` | `/expenses/{expense_id}` | Retrieve a single expense by ID |
| `PUT` | `/expenses/{expense_id}` | Update expense title/amount (payer only) |
| `DELETE` | `/expenses/{expense_id}` | Delete an expense (payer or group creator) |

#### Expense Creation Modes

1. **Equal Split:** Omit the `splits` array (or send `[]`). The system divides `amount` evenly across all current members of the group.
```json
{
  "title": "Dinner",
  "amount": 90.00,
  "description": "Team meal",
  "splits": []
}
```

2. **Custom Split:** Specify each participant's share explicitly. The sum of `share_amount` values must equal the total `amount`.
```json
{
  "title": "Grocery Run",
  "amount": 100.00,
  "description": "Shared pantry supplies",
  "splits": [
    {"user_id": 1, "share_amount": 60.00},
    {"user_id": 2, "share_amount": 40.00}
  ]
}
```

---

### Balances and Settlements

- **GET** `/groups/{group_id}/balances`

Computes the net financial standing of every member in the group and produces a minimal list of debt settlement transactions.

#### Example Response
```json
{
  "group_id": 1,
  "group_name": "Vacation Group",
  "balances": [
    {
      "user_id": 1,
      "full_name": "Alice",
      "email": "alice@example.com",
      "net_balance": 40.0
    },
    {
      "user_id": 2,
      "full_name": "Bob",
      "email": "bob@example.com",
      "net_balance": 10.0
    },
    {
      "user_id": 3,
      "full_name": "Carol",
      "email": "carol@example.com",
      "net_balance": -50.0
    }
  ],
  "settlements": [
    {
      "from_user_id": 3,
      "from_user_name": "Carol",
      "to_user_id": 1,
      "to_user_name": "Alice",
      "amount": 40.0
    },
    {
      "from_user_id": 3,
      "from_user_name": "Carol",
      "to_user_id": 2,
      "to_user_name": "Bob",
      "amount": 10.0
    }
  ]
}
```

---

## Balance and Settlement Algorithm

### Net Balance Calculation
For each user $u$ in group $G$:

$$\text{Net Balance}(u) = \sum \text{Paid by } u - \sum \text{Owed by } u \text{ in splits}$$

- If $\text{Net Balance}(u) > 0$, user $u$ is a **creditor** (is owed money).
- If $\text{Net Balance}(u) < 0$, user $u$ is a **debtor** (owes money).
- If $\text{Net Balance}(u) = 0$, user $u$ is settled.

The sum of all net balances across any group always equals zero.

### Greedy Debt Simplification
To avoid unnecessary cross-payments, a greedy two-pointer algorithm resolves debts:

1. Separate users into creditors ($C$) and debtors ($D$).
2. Sort creditors descending by credit amount.
3. Sort debtors descending by absolute debt amount.
4. Set settlement amount $S = \min(\text{credit}_i, \text{debt}_j)$.
5. Generate a settlement from debtor $j$ to creditor $i$ for amount $S$.
6. Deduct $S$ from both balances. Advance pointer for whichever party reaches zero balance.
7. Repeat until all balances are zero.

This algorithm reduces the number of transactions to at most $N - 1$, where $N$ is the number of participants.

---

## Switching to PostgreSQL

SQLite is enabled by default for zero-configuration setup. To switch to PostgreSQL in production:

1. Install `psycopg2-binary`:
   ```bash
   pip install psycopg2-binary
   ```
2. Update `DATABASE_URL` in `app/database.py`:
   ```python
   DATABASE_URL = "postgresql://username:password@localhost:5432/dbname"
   ```
3. Remove the `connect_args={"check_same_thread": False}` parameter from `create_engine`.

---

## License

This project is open-source and available under the MIT License.
