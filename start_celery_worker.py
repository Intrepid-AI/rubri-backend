#!/usr/bin/env python3
"""
Celery worker startup script for Rubri Backend
"""

import sys
import os

# Add the current directory to Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app

if __name__ == "__main__":
    # Start Celery worker
    celery_app.start(argv=[
        'celery',
        'worker',
        '--app=app.celery_app:celery_app',
        '--loglevel=info',
        '--concurrency=4',
        '--queues=questions,emails',
        '--hostname=worker@%h'
    ])