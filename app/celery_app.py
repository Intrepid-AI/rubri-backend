from celery import Celery
import os
from app.db_ops.db_config import load_app_config

# Load app configuration
app_config = load_app_config()

# Get Redis URL from environment or config
redis_url = os.getenv('REDIS_URL', app_config.get('redis', {}).get('url', 'redis://localhost:6379/0'))

# Create Celery app
celery_app = Celery(
    "rubri_backend",
    broker=redis_url,
    backend=redis_url,
    include=[
        'app.tasks.question_generation_tasks',
        'app.tasks.email_tasks'
    ]
)

# Configure Celery
celery_app.conf.update(
    result_expires=3600,  # Results expire after 1 hour
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_send_events=True,
    worker_send_task_events=True,
    result_extended=True,
    task_routes={
        'question_generation_tasks.*': {'queue': 'questions'},
        'email_tasks.*': {'queue': 'emails'}
    }
)

# Auto-discover tasks
celery_app.autodiscover_tasks()