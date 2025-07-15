"""
Stream manager for handling real-time agent updates.

This version uses Redis pub/sub for cross-process communication between
Celery workers and the FastAPI server.
"""

# Import everything from the Redis implementation
from .stream_manager_redis import (
    StreamEventType,
    StreamEvent,
    StreamManager
)

# The Redis implementation is now the default
# All the complex buffering and retry logic has been removed
# since Redis handles message delivery between processes

__all__ = [
    "StreamEventType",
    "StreamEvent", 
    "StreamManager"
]