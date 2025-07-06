.PHONY: help dev-up dev-down install-backend install-worker install-frontend setup-env

help: ## Show this help message
	@echo "Naptha Course Creator - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup-env: ## Setup environment files
	@echo "Setting up environment files..."
	@cp .env.example .env 2>/dev/null || echo ".env already exists"
	@cp frontend/.env.example frontend/.env 2>/dev/null || echo "frontend/.env already exists"
	@echo "Environment files created. Please update them with your actual values."

dev-up: ## Start development environment
	@echo "Starting Naptha Course Creator development environment..."
	@echo "1. Starting services with Docker Compose..."
	docker-compose up -d
	@echo "2. Services started successfully!"
	@echo ""
	@echo "Services running:"
	@echo "  Redis:    localhost:6379"
	@echo "  Backend:  localhost:8000"
	@echo "  Worker:   Running in background"
	@echo ""
	@echo "To start frontend: cd frontend && npm run dev"
	@echo "To view logs: docker-compose logs -f"

dev-down: ## Stop development environment
	@echo "Stopping development environment..."
	docker-compose down

install-backend: ## Install backend dependencies
	@echo "Installing backend dependencies..."
	pip install -e backend/

install-frontend: ## Install frontend dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies

run-backend: ## Run backend server
	@echo "Starting backend server..."
	cd backend && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Run celery worker
	@echo "Starting celery worker..."
	cd backend && celery -A worker.tasks worker --loglevel=info

run-frontend: ## Run frontend server
	@echo "Starting frontend server..."
	cd frontend && npm run dev

logs: ## View Docker Compose logs
	@echo "Viewing service logs..."
	docker-compose logs -f

build: ## Build Docker images
	@echo "Building Docker images..."
	docker-compose build

clean: ## Clean up Docker resources
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f 