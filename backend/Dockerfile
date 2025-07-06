FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy backend package files
COPY backend/ ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -e ./backend/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set working directory to backend package
WORKDIR /app/backend

# Default command (can be overridden)
CMD ["python", "-m", "backend.main"] 