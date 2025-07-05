from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

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
    print("Welcome to Naptha Course Creator Worker")
    app.start() 