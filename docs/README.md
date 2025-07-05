# Naptha Course Creator Documentation

Welcome to the documentation for the Naptha Course Creator platform. This documentation provides comprehensive guides for developers working with the system.

## 📚 Available Documentation

### [Authentication Flow](./authentication-flow.md)
Comprehensive guide covering:
- Auth0 integration setup
- Signup and signin flow diagrams
- Backend JWT verification process
- API endpoint documentation
- Security best practices
- Troubleshooting guide

## 🏗️ Architecture Overview

The Naptha Course Creator is built as a monorepo with:

- **Frontend**: React + Vite + Auth0 React SDK
- **Backend**: FastAPI + Redis + Auth0 JWT verification
- **Worker**: Celery for background tasks
- **Database**: Redis for user data and session storage

## 🚀 Quick Start

1. **Setup Environment**
   ```bash
   make install
   ```

2. **Start Development Services**
   ```bash
   make dev-up
   ```

3. **Access Services**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 🔧 Development

### Project Structure
```
course-creator/
├── backend/        # FastAPI backend
├── frontend/       # React frontend
├── worker/         # Celery worker
├── docs/          # Documentation
└── docker-compose.yml
```

### Available Commands
```bash
make help          # Show all available commands
make dev-up        # Start development environment
make dev-down      # Stop development environment
make install       # Install dependencies
make clean         # Clean up containers and volumes
```

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Auth0 React SDK](https://auth0.com/docs/quickstart/spa/react)
- [Redis Documentation](https://redis.io/docs/)
- [Celery Documentation](https://docs.celeryq.dev/)

## 🤝 Contributing

When adding new features or making changes:

1. Update relevant documentation
2. Add appropriate tests
3. Follow the existing code style
4. Update this documentation index if needed

## 📝 Documentation Guidelines

- Use clear, concise language
- Include code examples where helpful
- Add sequence diagrams for complex flows
- Keep troubleshooting sections up to date
- Include environment configuration details 