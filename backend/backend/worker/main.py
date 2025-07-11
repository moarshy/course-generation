import os
import logging
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import tasks to register them with Celery
from backend.worker.tasks import app as celery_app

# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
app = Celery(
    "naptha_course_creator",
    broker=redis_url,
    backend=redis_url
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@app.task
def hello():
    return "Hello from Naptha Course Creator Worker!"

if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    # Start the worker with proper arguments
    celery_app.start([
        'worker',
        '--loglevel=info',
        '--concurrency=1',
        '--pool=solo'  # Use solo pool for better compatibility
    ]) 