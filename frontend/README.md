# Course Creator Frontend

This is the frontend application for the Course Creator, built with Next.js and TypeScript.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
Create a `.env.local` file in the frontend directory with the following content:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEV_TOKEN=dev-token-12345
NEXT_PUBLIC_DEV_MODE=true

# Auth0 Configuration (for production)
NEXT_PUBLIC_AUTH0_DOMAIN=your-auth0-domain.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-auth0-client-id
NEXT_PUBLIC_AUTH0_AUDIENCE=your-auth0-api-audience
NEXT_PUBLIC_AUTH0_REDIRECT_URI=http://localhost:3000
```

## Development Mode

By default, the application runs in development mode (`NEXT_PUBLIC_DEV_MODE=true`), which:
- Uses a mock user for authentication
- Bypasses Auth0 configuration
- Uses the development token for API calls

## Production Mode

To use real Auth0 authentication:

1. Set `NEXT_PUBLIC_DEV_MODE=false`
2. Configure the Auth0 environment variables with your Auth0 application credentials
3. Ensure your Auth0 application is configured with the correct callback URLs

## Running the Application

```bash
npm run dev
```

Or use the Makefile from the root directory:

```bash
make run-frontend
```

## Features

- **Authentication**: Auth0 integration with development mode fallback
- **Course Management**: Create, view, and manage courses
- **Real-time Updates**: Track course generation progress
- **Responsive Design**: Works on desktop and mobile devices

## Authentication Flow

1. **Development Mode**: Automatically logs in with a mock user
2. **Production Mode**: Redirects to Auth0 for authentication
3. **Token Management**: Automatically handles JWT tokens for API calls
4. **Session Management**: Maintains authentication state across page reloads
