# Naptha Course Creator

A monorepo for an AI-powered course creation platform.

## Quick Setup

### 1. Environment Variables

Create `.env` files:

**Frontend** (`frontend/.env`):
```
VITE_AUTH0_DOMAIN=
VITE_AUTH0_CLIENT_ID=
VITE_AUTH0_AUDIENCE=
VITE_API_BASE_URL=http://localhost:8000/api
```

**Backend** (`backend/.env`):
```
AUTH0_DOMAIN=
AUTH0_AUDIENCE=
AUTH0_CLIENT_ID=
AUTH0_ALGORITHMS=["RS256"]
AUTH0_ISSUER=
REDIS_URL=redis://localhost:6379/0
```

### 2. Start Redis

```bash
make dev-up
```

### 3. Run Services (in separate terminals)

```bash
# Terminal 1: Backend
make run-backend

# Terminal 2: Worker  
make run-worker

# Terminal 3: Frontend
make run-frontend
```

### Access

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs 