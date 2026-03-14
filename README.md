# Pendo Backend

Dating/discovery platform API built with Flask, PostgreSQL, and Firebase.

## Tech Stack

- **Framework:** Flask 3.x
- **Database:** PostgreSQL 16
- **ORM:** SQLAlchemy 2.0 + Alembic (Flask-Migrate)
- **Auth:** Firebase (phone OTP / Google OAuth) + JWT
- **Storage:** Firebase Cloud Storage
- **Reverse Proxy:** Traefik (TLS via Let's Encrypt)

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `POST /api/v1/auth/verify` | Exchange Firebase ID token for JWT pair |
| `POST /api/v1/auth/refresh` | Refresh access token |
| `GET /api/v1/users/me` | Get authenticated user profile |
| `PUT /api/v1/users/me` | Update user profile |
| `GET /api/v1/discover` | Discover nearby users (paginated) |
| `POST /api/v1/swipes` | Create a swipe (like/dislike/super_like) |
| `GET /health` | Health check (API + database status) |

## Local Development (Docker)

### Prerequisites

- Docker & Docker Compose
- Traefik running on `traefik-public` network
- `firebase_service_account.json` in project root
- `.env` file in project root

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `FIREBASE_STORAGE_BUCKET` | Firebase storage bucket name |
| `FLASK_APP` | Entry point (`run.py`) |
| `FLASK_ENV` | `development` or `production` |

### Run

```bash
# Build and start all services (backend + postgres + seed)
docker compose up -d --build

# Check logs
docker logs pendo-backend
docker logs pendo-seed

# Re-run migrations and seed
docker compose run --rm pendo-seed
```

### Database Access

```bash
# Interactive psql shell
docker exec -it pendo-db psql -U pendo -d pendo

# One-off query
docker exec pendo-db psql -U pendo -d pendo -c "SELECT count(*) FROM users;"
```

### Services

| Container | Description | Network |
|-----------|-------------|---------|
| `pendo-backend` | Flask API on port 5000 | traefik-public, pendo-internal |
| `pendo-db` | PostgreSQL 16 | pendo-internal |
| `pendo-seed` | Runs migrations + seeds DB | pendo-internal |

### Traefik Routing

Dev environment is routed via `pendo-dev.ruthwestlimited.com` with automatic TLS.

## Project Structure

```
├── app/
│   ├── config/         # App configuration
│   ├── extensions/     # DB, JWT, Socket.IO
│   ├── models/         # SQLAlchemy models
│   ├── routes/         # API blueprints
│   ├── schemas/        # Validation schemas
│   ├── services/       # Business logic
│   └── utils/          # Firebase utilities
├── migrations/         # Alembic migrations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── seed_test_users.py
└── run.py              # Entry point
```
