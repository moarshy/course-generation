# Naptha Course Creator

A monorepo for an AI-powered course creation platform with human-in-the-loop capabilities for DevRels.

## Architecture

- **Backend**: FastAPI-based API server
- **Worker**: Celery-based task worker using Redis
- **Frontend**: React application built with Vite
- **Database**: Redis for task queue and caching

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd course-creator
   ```

2. **Install dependencies**
   ```bash
   make install-backend
   make install-worker
   make install-frontend
   ```

3. **Start development environment**
   ```bash
   make dev-up
   ```

4. **Run services** (in separate terminals)
   ```bash
   # Terminal 1: Backend
   make run-backend

   # Terminal 2: Worker
   make run-worker

   # Terminal 3: Frontend
   make run-frontend
   ```

### Available Commands

Run `make help` to see all available commands.

### Services

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Redis**: localhost:6379

## Development

The project is set up as a monorepo with three main services:

1. **Backend** (`/backend`): FastAPI application handling API requests
2. **Worker** (`/worker`): Celery worker for background tasks
3. **Frontend** (`/frontend`): React application for the user interface

Each service can be developed independently while sharing the Redis instance for task queuing.

## Next Steps

This is a minimal setup. You can now add features incrementally:

- Database models and migrations
- Authentication and authorization
- Course generation logic
- AI integration
- Advanced UI components
- Testing setup 