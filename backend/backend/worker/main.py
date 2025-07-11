"""
Celery Worker Entry Point

This module starts the Celery worker for course generation tasks.
All task definitions are in backend.worker.tasks module.
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import the configured Celery app from tasks module
from backend.worker.tasks import app as celery_app

if __name__ == "__main__":
    logger.info("Starting Celery worker for course generation...")
    # Start the worker with proper arguments
    celery_app.start([
        'worker',
        '--loglevel=info',
        '--concurrency=1',
        '--pool=solo'  # Use solo pool for better compatibility
    ]) 