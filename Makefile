.PHONY: help dev-up dev-down install-backend install-worker install-frontend setup-env

help: ## Show this help message
	@echo "Naptha Course Creator - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup-env: ## Setup environment files
	@echo "Setting up environment files..."
	@cp backend/.env.example backend/.env 2>/dev/null || echo "backend/.env already exists"
	@cp worker/.env.example worker/.env 2>/dev/null || echo "worker/.env already exists"
	@cp frontend/.env.example frontend/.env 2>/dev/null || echo "frontend/.env already exists"
	@echo "Environment files created. Please update them with your actual values."

dev-up: ## Start development environment
	@echo "Starting Naptha Course Creator development environment..."
	@echo "1. Starting Redis..."
	docker-compose up -d redis
	@echo "2. Redis started successfully!"
	@echo ""
	@echo "Make sure to run 'make setup-env' first to set up your environment variables."
	@echo ""
	@echo "Now you can start the services manually:"
	@echo "  Backend:  cd backend && uvicorn app.main:app --reload --port 8000"
	@echo "  Worker:   cd worker && celery -A app.main worker --loglevel=info"
	@echo "  Frontend: cd frontend && npm run dev"
	@echo ""
	@echo "Or use the individual commands:"
	@echo "  make run-backend"
	@echo "  make run-worker"
	@echo "  make run-frontend"

dev-down: ## Stop development environment
	@echo "Stopping development environment..."
	docker-compose down

install-backend: ## Install backend dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt

install-worker: ## Install worker dependencies
	@echo "Installing worker dependencies..."
	cd worker && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

install: install-backend install-worker install-frontend ## Install all dependencies

run-backend: ## Run backend server
	@echo "Starting backend server..."
	cd backend && uvicorn app.main:app --reload --port 8000

run-worker: ## Run celery worker
	@echo "Starting celery worker..."
	cd worker && celery -A app.main worker --loglevel=info

run-frontend: ## Run frontend server
	@echo "Starting frontend server..."
	cd frontend && npm run dev 