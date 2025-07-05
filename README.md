# Naptha Course Creator

A monorepo for an AI-powered course creation platform with Auth0 authentication and human-in-the-loop capabilities for DevRels.

## Architecture

- **Backend**: FastAPI-based API server with Auth0 JWT verification
- **Worker**: Celery-based task worker using Redis
- **Frontend**: React application with Auth0 authentication
- **Database**: Redis for user data and task queue

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Auth0 account configured

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd course-creator
   ```

2. **Setup environment variables**
   ```bash
   make setup-env
   ```
   
   Then update the `.env` files with your actual Auth0 credentials:
   - `frontend/.env` - Frontend Auth0 config
   - `backend/.env` - Backend Auth0 config
   - `worker/.env` - Redis config

3. **Install dependencies**
   ```bash
   make install-backend
   make install-worker
   make install-frontend
   ```

4. **Start development environment**
   ```bash
   make dev-up
   ```

5. **Run services** (in separate terminals)
   ```bash
   # Terminal 1: Backend
   make run-backend

   # Terminal 2: Worker
   make run-worker

   # Terminal 3: Frontend
   make run-frontend
   ```

### Auth0 Configuration

The application uses the following Auth0 settings:

- **Domain**: `naptha-ai.us.auth0.com`
- **Client ID**: `vQW0OJXbL51c3EEqHAxwDPB7kCJQfX42`
- **API Audience**: `https://naptha-ai.us.auth0.com/api/v2/`
- **Algorithms**: `["RS256"]`
- **Issuer**: `https://naptha-ai.us.auth0.com/`

Make sure your Auth0 application is configured with:
- Application Type: Single Page Application
- Allowed Callback URLs: `http://localhost:3000`
- Allowed Logout URLs: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`

### Available Commands

Run `make help` to see all available commands.

### Services

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Backend API Docs**: http://localhost:8000/docs
- **Redis**: localhost:6379

## Features

### Authentication
- **Sign Up**: Create new accounts via Auth0
- **Login**: Authenticate existing users
- **Logout**: Secure session termination
- **User Sync**: Automatic user data synchronization between frontend and backend
- **JWT Verification**: Secure API endpoints with Auth0 JWT tokens

### User Management
- User data stored in Redis key-value store
- Automatic user creation/update on login
- Email-based user indexing
- Profile information management

### API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check with Redis status
- `POST /api/users/sync` - Sync user from Auth0 (authenticated)
- `GET /api/users/me` - Get current user info (authenticated)
- `GET /api/users/{auth0_id}` - Get user by ID (authenticated)

## Development

The project is set up as a monorepo with three main services:

1. **Backend** (`/backend`): FastAPI application with Auth0 JWT verification
2. **Worker** (`/worker`): Celery worker for background tasks
3. **Frontend** (`/frontend`): React application with Auth0 authentication

### User Data Flow

1. User signs up/logs in via Auth0 on frontend
2. Frontend receives JWT token and user profile
3. Frontend automatically syncs user data to backend
4. Backend validates JWT and stores user in Redis
5. Subsequent API calls use JWT for authentication

### Redis Schema

```
user:{auth0_id} -> JSON user object
user_email:{email} -> auth0_id
```

## Next Steps

This setup provides a solid foundation with authentication. You can now add:

- Course creation and management
- AI-powered content generation
- Human review workflows
- Advanced user roles and permissions
- Course analytics and reporting 