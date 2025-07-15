"""
Redis Event Subscriber for WebSocket Streaming

This module enables the FastAPI server to subscribe to Redis channels and
forward streaming events to WebSocket clients.

Architecture:
    Redis Pub/Sub -> RedisEventSubscriber -> WebSocket Manager -> WebSocket Clients

Example Usage:
    subscriber = await get_redis_subscriber()
    await subscriber.subscribe_to_task("task_123")
"""

import asyncio
import json
import redis.asyncio as aioredis
from typing import Dict, Any, Optional, Set
from app.logger import get_logger

logger = get_logger(__name__)


class RedisEventSubscriber:
    """
    Subscribes to Redis channels and forwards events to WebSocket clients.
    
    This class runs in the FastAPI server process and bridges the gap between
    Redis pub/sub and WebSocket connections.
    """
    
    def __init__(self, websocket_manager, redis_url: Optional[str] = None):
        """
        Initialize Redis subscriber.
        
        Args:
            websocket_manager: The WebSocket connection manager instance
            redis_url: Redis connection URL. If not provided, uses default localhost:6379
        """
        self.websocket_manager = websocket_manager
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._redis_client = None
        self._pubsub = None
        self._subscriptions: Dict[str, asyncio.Task] = {}
        self._running = False
        
    async def start(self):
        """Initialize Redis connection and pubsub."""
        try:
            self._redis_client = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                auto_close_connection_pool=False
            )
            self._pubsub = self._redis_client.pubsub()
            self._running = True
            logger.info(f"✅ Redis subscriber connected to {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect Redis subscriber: {e}")
            raise
    
    async def stop(self):
        """Stop all subscriptions and close connections."""
        self._running = False
        
        # Cancel all subscription tasks
        for task_id, task in list(self._subscriptions.items()):
            await self.unsubscribe_from_task(task_id)
        
        # Close pubsub and Redis connection
        if self._pubsub:
            await self._pubsub.close()
            
        if self._redis_client:
            await self._redis_client.close()
            
        logger.info("🔌 Redis subscriber stopped")
    
    async def subscribe_to_task(self, task_id: str):
        """
        Subscribe to events for a specific task.
        
        Args:
            task_id: Task ID to subscribe to
        """
        if task_id in self._subscriptions:
            logger.info(f"Already subscribed to task {task_id}")
            return
            
        channel = f"stream:task:{task_id}"
        
        try:
            # Subscribe to the channel
            await self._pubsub.subscribe(channel)
            
            # Create a task to handle messages for this channel
            subscription_task = asyncio.create_task(
                self._handle_channel_messages(task_id, channel)
            )
            self._subscriptions[task_id] = subscription_task
            
            logger.info(f"📡 Subscribed to Redis channel: {channel}")
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to channel {channel}: {e}")
            raise
    
    async def unsubscribe_from_task(self, task_id: str):
        """
        Unsubscribe from events for a specific task.
        
        Args:
            task_id: Task ID to unsubscribe from
        """
        if task_id not in self._subscriptions:
            return
            
        channel = f"stream:task:{task_id}"
        
        try:
            # Cancel the subscription task
            task = self._subscriptions.pop(task_id)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Unsubscribe from the channel
            await self._pubsub.unsubscribe(channel)
            
            logger.info(f"📡 Unsubscribed from Redis channel: {channel}")
            
        except Exception as e:
            logger.error(f"❌ Error unsubscribing from channel {channel}: {e}")
    
    async def _handle_channel_messages(self, task_id: str, channel: str):
        """
        Handle messages from a specific Redis channel.
        
        Args:
            task_id: Task ID for this channel
            channel: Redis channel name
        """
        logger.info(f"🎧 Starting message handler for channel: {channel}")
        
        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                    
                # Skip non-message types (subscribe confirmations, etc.)
                if message['type'] != 'message':
                    continue
                
                try:
                    # Parse the message data
                    event_data = json.loads(message['data'])
                    
                    # Handle batch events
                    if event_data.get('type') == 'batch':
                        events = event_data.get('events', [])
                        logger.info(f"📦 Received batch of {len(events)} events for task {task_id}")
                        
                        # Forward batch to WebSocket
                        await self.websocket_manager.send_streaming_batch(task_id, events)
                    else:
                        # Forward single event to WebSocket
                        logger.info(
                            f"📨 Received event for task {task_id}: "
                            f"{event_data.get('event_type', 'unknown')} - "
                            f"{event_data.get('agent_name', 'unknown')}"
                        )
                        await self.websocket_manager.send_streaming_event(task_id, event_data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in message: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    
        except asyncio.CancelledError:
            logger.info(f"🛑 Message handler cancelled for channel: {channel}")
            raise
        except Exception as e:
            logger.error(f"❌ Fatal error in message handler for channel {channel}: {e}")
            # Remove from subscriptions on fatal error
            self._subscriptions.pop(task_id, None)
    
    def get_active_subscriptions(self) -> Set[str]:
        """Get set of task IDs with active subscriptions."""
        return set(self._subscriptions.keys())
    
    def is_subscribed_to_task(self, task_id: str) -> bool:
        """Check if subscribed to a specific task."""
        return task_id in self._subscriptions


# Global subscriber instance
_subscriber_instance = None


async def get_redis_subscriber(websocket_manager) -> RedisEventSubscriber:
    """
    Get or create singleton Redis subscriber instance.
    
    Args:
        websocket_manager: WebSocket connection manager instance
        
    Returns:
        RedisEventSubscriber instance
    """
    global _subscriber_instance
    
    if _subscriber_instance is None:
        _subscriber_instance = RedisEventSubscriber(websocket_manager)
        await _subscriber_instance.start()
        
    return _subscriber_instance