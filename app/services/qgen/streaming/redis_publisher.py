"""
Redis Event Publisher for Cross-Process Streaming

This module enables Celery workers to publish streaming events to Redis,
which are then consumed by the FastAPI server and forwarded to WebSocket clients.

Architecture:
    Celery Worker -> RedisEventPublisher -> Redis Pub/Sub -> FastAPI Server

Example Usage:
    publisher = RedisEventPublisher()
    publisher.publish_event("task_123", {
        "event_type": "skill_found",
        "data": {"skill": "Python"}
    })
"""

import json
import redis
from typing import Dict, Any, Optional
from app.logger import get_logger

logger = get_logger(__name__)


class RedisEventPublisher:
    """
    Publishes streaming events to Redis for cross-process communication.
    
    This class is used by Celery workers to send real-time events that
    will be consumed by the FastAPI server and forwarded to WebSocket clients.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis publisher.
        
        Args:
            redis_url: Redis connection URL. If not provided, uses default localhost:6379
        """
        # Use the same Redis instance as Celery for consistency
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._redis_client = None
        self._connection_retries = 3
        
    @property
    def redis_client(self):
        """Lazy Redis client initialization with connection retry."""
        if self._redis_client is None:
            retries = 0
            while retries < self._connection_retries:
                try:
                    self._redis_client = redis.from_url(
                        self.redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_keepalive=True,
                        socket_keepalive_options={}
                    )
                    # Test connection
                    self._redis_client.ping()
                    logger.info(f"✅ Redis publisher connected to {self.redis_url}")
                    break
                except redis.ConnectionError as e:
                    retries += 1
                    logger.error(f"❌ Redis connection attempt {retries}/{self._connection_retries} failed: {e}")
                    if retries >= self._connection_retries:
                        raise
        return self._redis_client
    
    def publish_event(self, task_id: str, event_data: Dict[str, Any]) -> bool:
        """
        Publish streaming event to Redis channel.
        
        Args:
            task_id: Task ID to publish event for
            event_data: Event data dictionary containing event_type, agent_name, data, etc.
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        channel = f"stream:task:{task_id}"
        
        try:
            # Ensure event_data is JSON serializable
            message = json.dumps(event_data)
            
            # Publish to Redis channel
            subscribers = self.redis_client.publish(channel, message)
            
            logger.info(
                f"📡 Published event to Redis - Channel: {channel}, "
                f"Type: {event_data.get('event_type', 'unknown')}, "
                f"Subscribers: {subscribers}"
            )
            
            return True
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"❌ Redis connection error while publishing: {e}")
            # Reset client to force reconnection on next attempt
            self._redis_client = None
            return False
            
        except Exception as e:
            logger.error(f"❌ Error publishing event to Redis: {e}")
            return False
    
    def publish_batch(self, task_id: str, events: list) -> bool:
        """
        Publish multiple events as a batch.
        
        Args:
            task_id: Task ID to publish events for
            events: List of event dictionaries
            
        Returns:
            bool: True if all events published successfully
        """
        if not events:
            return True
            
        # Publish batch as a single message for efficiency
        batch_event = {
            "type": "batch",
            "events": events
        }
        
        return self.publish_event(task_id, batch_event)
    
    def close(self):
        """Close Redis connection."""
        if self._redis_client:
            try:
                self._redis_client.close()
                logger.info("🔌 Redis publisher connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._redis_client = None


# Singleton instance for reuse across Celery tasks
_publisher_instance = None


def get_redis_publisher() -> RedisEventPublisher:
    """
    Get singleton Redis publisher instance.
    
    This ensures we reuse connections across multiple task executions.
    """
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = RedisEventPublisher()
    return _publisher_instance