# 💬 Real-Time Chat Application

A **production-style** Real-Time Chat Application built with **FastAPI**, **PostgreSQL**, **Redis**, and **WebSockets**. Designed to demonstrate backend engineering skills for internship and placement interviews.

---

## 🏗️ Architecture Overview

```
Browser (HTML + Bootstrap + JS)
        │
        ▼
  FastAPI Application (Python 3.12)
   ├── REST API endpoints (JWT protected)
   ├── WebSocket endpoint (/ws/{chat_id})
   └── Jinja2 HTML templates
        │
   ┌────┴──────────────────┐
   ▼                       ▼
PostgreSQL              Redis
(persistent storage)    (presence + pub/sub)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111 |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Cache/Presence | Redis 7 |
| Auth | JWT (python-jose) + bcrypt |
| Migrations | Alembic |
| Templates | Jinja2 + Bootstrap 5 |
| Container | Docker + Docker Compose |
| Logging | structlog |

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://www.docker.com/get-started) + Docker Compose

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd chatting-website
cp .env.example .env
# Edit .env if needed (default values work with Docker Compose)
```

### 2. Build and start all services

```bash
docker compose up --build
```

This starts:
- **FastAPI app** on `http://localhost:8000`
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`

Alembic migrations run automatically on startup.

### 3. Open in browser

- 🌐 **App**: http://localhost:8000
- 📖 **Swagger Docs**: http://localhost:8000/docs
- 📚 **ReDoc**: http://localhost:8000/redoc

---

## 📁 Project Structure

```
app/
├── main.py              # FastAPI app + frontend routes
├── database.py          # Async SQLAlchemy engine
├── config/
│   └── settings.py      # Pydantic Settings (env vars)
├── models/              # SQLAlchemy ORM models
│   ├── user.py
│   ├── chat.py          # Chat + ChatMember
│   ├── message.py
│   └── group.py
├── schemas/             # Pydantic validation schemas
├── auth/
│   ├── jwt_handler.py   # JWT create/decode
│   ├── password.py      # bcrypt hashing
│   └── dependencies.py  # get_current_user dependency
├── routers/             # FastAPI route handlers
│   ├── auth.py          # /auth/register, /login, /refresh
│   ├── users.py         # /users/
│   ├── chats.py         # /chats/
│   └── groups.py        # /groups/
├── services/            # Business logic (separated from routes)
├── websocket/
│   ├── connection_manager.py   # Room-based WebSocket pool
│   └── ws_router.py            # /ws/{chat_id} endpoint
├── redis/
│   └── redis_client.py  # Presence tracking + pub/sub
├── middleware/
│   └── logging_middleware.py
├── utils/
│   └── logger.py        # Structured logging
└── templates/           # Jinja2 HTML templates
    ├── base.html
    ├── login.html
    ├── register.html
    └── dashboard.html
```

---

## 🔑 API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login → get tokens |
| POST | `/auth/refresh` | Refresh access token |

### Users
| Method | Endpoint | Description |
|---|---|---|
| GET | `/users/me` | Get my profile |
| PATCH | `/users/me` | Update my profile |
| GET | `/users/` | List all users |
| GET | `/users/online` | Get online users (Redis) |
| GET | `/users/{id}` | Get any user's public profile |

### Chats
| Method | Endpoint | Description |
|---|---|---|
| POST | `/chats/` | Get or create private chat |
| GET | `/chats/` | List my chats |
| GET | `/chats/{id}/messages` | Paginated message history |
| GET | `/chats/{id}/members` | List chat members |

### Groups
| Method | Endpoint | Description |
|---|---|---|
| POST | `/groups/` | Create group |
| GET | `/groups/` | My groups |
| PATCH | `/groups/{id}` | Update group (admin only) |
| POST | `/groups/{id}/members` | Add member (admin) |
| DELETE | `/groups/{id}/members/{uid}` | Remove member (admin) |
| GET | `/groups/{id}/members` | List members |

### WebSocket
```
ws://localhost:8000/ws/{chat_id}?token=<access_token>
```

---

## 🔌 WebSocket Message Protocol

**Client → Server:**
```json
{ "type": "message", "content": "Hello World!" }
{ "type": "typing",  "is_typing": true }
{ "type": "ping" }
```

**Server → Client:**
```json
{ "type": "message", "id": "...", "sender_id": "...", "sender": "alice", "content": "Hello!", "timestamp": "..." }
{ "type": "typing",  "user_id": "...", "username": "alice", "is_typing": true }
{ "type": "user_joined", "user_id": "...", "username": "alice", "online_users": [...] }
{ "type": "user_left",   "user_id": "...", "username": "alice", "online_users": [...] }
{ "type": "pong" }
{ "type": "error", "detail": "..." }
```

---

## 🗄️ Database Schema

```
Users ──────────────────────────────────────────────
 id (UUID PK) | username | email | hashed_password
 is_active | created_at | last_seen

Chats ───────────────────────────────────────────────
 id (UUID PK) | type (private/group) | created_at

ChatMembers (junction table) ────────────────────────
 id | user_id → Users | chat_id → Chats | joined_at

Messages ────────────────────────────────────────────
 id (UUID PK) | sender_id → Users | chat_id → Chats
 content | is_read | delivered | created_at

Groups ──────────────────────────────────────────────
 id (UUID PK) | name | description
 admin_id → Users | chat_id → Chats | created_at
```

---

## 🔐 JWT Authentication Flow

```
1. POST /auth/register → User created in DB
2. POST /auth/login    → Verify password → Issue tokens:
                           access_token  (30 min)
                           refresh_token (7 days)
3. API Request → Authorization: Bearer <access_token>
                 → get_current_user dependency decodes JWT
                 → Returns user object or 401
4. Token expires → POST /auth/refresh with refresh_token
                    → New access_token issued
```

---

## 🟢 Redis Presence Tracking

```python
# On WebSocket connect:
SADD online_users <user_id>

# On WebSocket disconnect:
SREM online_users <user_id>

# Check who's online:
SMEMBERS online_users

# Typing indicator via Pub/Sub:
PUBLISH typing:<chat_id> "<user_id>:1"   # typing
PUBLISH typing:<chat_id> "<user_id>:0"   # stopped
```

---

## 🧪 Running Tests

```bash
# Inside the Docker container
docker compose exec app pytest tests/ -v

# Or locally (requires DB + Redis running)
pytest tests/ -v
```

---

## 🧠 Interview Q&A

**Q: Why WebSockets instead of polling?**
> Polling sends an HTTP request every N seconds even when there's nothing new — wasteful. WebSockets maintain a persistent TCP connection; the server *pushes* messages immediately, with zero extra requests. This reduces latency from seconds to milliseconds and cuts server load dramatically.

**Q: Why Redis for presence tracking?**
> PostgreSQL is great for persistent data but slow for high-frequency reads like "is this user online?". Redis is in-memory, so reads are ~100μs vs ~5ms for Postgres. A Redis Set (`SADD/SMEMBERS`) is the perfect data structure for a group of online users.

**Q: Why PostgreSQL over MongoDB?**
> Messages have clear relationships (User → Message → Chat). PostgreSQL enforces these with foreign keys, guarantees ACID transactions, and supports complex joins (e.g., "messages with sender usernames"). MongoDB's flexibility isn't needed here and would lose data integrity guarantees.

**Q: How would you scale to millions of messages?**
> 1. **Pagination** already implemented (OFFSET/LIMIT, upgrade to cursor-based for scale).
> 2. **Read replicas** for PostgreSQL — route SELECT queries to replicas.
> 3. **Horizontal app scaling** — Redis Pub/Sub already enables broadcasting across multiple FastAPI instances.
> 4. **Message partitioning** — partition the messages table by chat_id or date.
> 5. **CDN** for static assets, **object storage** for file attachments.

**Q: How is the WebSocket secured?**
> The JWT access token is passed as a query parameter (`?token=...`) on the WebSocket handshake URL. The `get_current_user_ws` dependency decodes it before accepting the connection. If invalid, the connection is closed with code 4003.

---

## 🐳 Docker Services

| Service | Image | Port |
|---|---|---|
| app | Custom (Python 3.12) | 8000 |
| db | postgres:16-alpine | 5432 |
| redis | redis:7-alpine | 6379 |

---

## 📝 Development Commands

```bash
# Start all services
docker compose up --build

# View logs
docker compose logs -f app

# Run Alembic migration
docker compose exec app alembic revision --autogenerate -m "description"
docker compose exec app alembic upgrade head

# Open Redis CLI
docker compose exec redis redis-cli

# Check online users in Redis
docker compose exec redis redis-cli SMEMBERS online_users

# Stop everything
docker compose down

# Stop and remove volumes (fresh start)
docker compose down -v
```
