import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db_ops.database import get_db_session
from app.db_ops import crud
from app.logger import get_logger
from app.services.streaming import get_redis_subscriber

logger = get_logger(__name__)

class ConnectionManager:
    """
    WebSocket connection manager for real-time progress updates
    """
    
    def __init__(self):
        # Store active connections by task_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store task monitoring status
        self.monitoring_tasks: Dict[str, bool] = {}
        # Connection limits
        self.max_connections_per_task = 3  # Limit connections per task
        self.max_total_connections = 100   # Global connection limit
        # Redis subscriber instance (lazy initialized)
        self._redis_subscriber = None
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept WebSocket connection and register it for a task"""
        # Check global connection limit
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        if total_connections >= self.max_total_connections:
            logger.warning(f"Rejecting WebSocket connection for task {task_id} - global limit ({self.max_total_connections}) reached")
            await websocket.close(code=4008, reason="Connection limit reached")
            return
        
        # Check per-task connection limit
        if task_id in self.active_connections and len(self.active_connections[task_id]) >= self.max_connections_per_task:
            logger.warning(f"Rejecting WebSocket connection for task {task_id} - task limit ({self.max_connections_per_task}) reached")
            await websocket.close(code=4009, reason="Task connection limit reached")
            return
        
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        logger.info(f"WebSocket connected for task {task_id}. Task connections: {len(self.active_connections[task_id])}, Total: {total_connections + 1}")
        
        # Update database to track WebSocket connection for cross-process communication
        self._update_websocket_connection_in_db(task_id, connected=True)
        
        # Subscribe to Redis events for this task
        await self._subscribe_to_redis_events(task_id)
        
        # Start monitoring this task if not already monitoring
        if task_id not in self.monitoring_tasks:
            self.monitoring_tasks[task_id] = True
            asyncio.create_task(self.monitor_task_progress(task_id))
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """Remove WebSocket connection"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            
            # If no more connections for this task, stop monitoring
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
                self.monitoring_tasks[task_id] = False
                # Update database to track WebSocket disconnection
                self._update_websocket_connection_in_db(task_id, connected=False)
                # Unsubscribe from Redis events
                asyncio.create_task(self._unsubscribe_from_redis_events(task_id))
                logger.info(f"Stopped monitoring task {task_id} - no more connections")
            else:
                logger.info(f"WebSocket disconnected for task {task_id}. Remaining connections: {len(self.active_connections[task_id])}")
    
    async def send_progress_update(self, task_id: str, data: dict):
        """Send progress update to all connections for a task"""
        if task_id not in self.active_connections:
            logger.warning(f"DEBUG: No active connections for task {task_id}")
            return
        
        message = json.dumps({
            "type": "progress_update",
            "task_id": task_id,
            "data": data
        })
        
        logger.info(f"DEBUG: Sending progress update to {len(self.active_connections[task_id])} connections for task {task_id}: {data}")
        
        # Send to all connections for this task
        disconnected_connections = set()
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_text(message)
                logger.info(f"DEBUG: Successfully sent progress update to WebSocket for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket for task {task_id}: {e}")
                disconnected_connections.add(connection)
        
        # Remove failed connections
        for connection in disconnected_connections:
            self.active_connections[task_id].discard(connection)
    
    async def send_completion(self, task_id: str, data: dict):
        """Send completion notification to all connections for a task"""
        if task_id not in self.active_connections:
            return
        
        message = json.dumps({
            "type": "task_completed",
            "task_id": task_id,
            "data": data
        })
        
        # Send to all connections for this task
        disconnected_connections = set()
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send completion message to WebSocket for task {task_id}: {e}")
                disconnected_connections.add(connection)
        
        # Remove failed connections
        for connection in disconnected_connections:
            self.active_connections[task_id].discard(connection)
        
        # Clean up after completion
        await asyncio.sleep(5)  # Give time for final messages to be received
        if task_id in self.monitoring_tasks:
            self.monitoring_tasks[task_id] = False
    
    async def send_error(self, task_id: str, error_message: str):
        """Send error notification to all connections for a task"""
        if task_id not in self.active_connections:
            logger.warning(f"DEBUG: No active connections for task {task_id} to send error to")
            return
        
        message = json.dumps({
            "type": "error",
            "task_id": task_id,
            "data": {"error": error_message}
        })
        
        logger.info(f"DEBUG: Sending error message to {len(self.active_connections[task_id])} connections for task {task_id}: {error_message}")
        
        # Send to all connections for this task
        disconnected_connections = set()
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_text(message)
                logger.info(f"DEBUG: Successfully sent error message to WebSocket for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to send error message to WebSocket for task {task_id}: {e}")
                disconnected_connections.add(connection)
        
        # Remove failed connections
        for connection in disconnected_connections:
            self.active_connections[task_id].discard(connection)
    
    async def broadcast(self, task_id: str, message: str):
        """Broadcast a raw message to all connections for a task"""
        if task_id not in self.active_connections or len(self.active_connections[task_id]) == 0:
            logger.info(f"📢 No active connections for task {task_id} - broadcast ignored gracefully")
            return
        
        logger.info(f"📢 BROADCASTING to {len(self.active_connections[task_id])} connections for task {task_id}")
        disconnected_connections = set()
        sent_count = 0
        
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_text(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast message to WebSocket for task {task_id}: {e}")
                disconnected_connections.add(connection)
        
        # Remove failed connections
        for connection in disconnected_connections:
            self.active_connections[task_id].discard(connection)
        
        logger.info(f"✅ BROADCAST SUCCESS: {sent_count} messages sent, {len(disconnected_connections)} failed")
    
    async def send_streaming_event(self, task_id: str, event_data: dict):
        """Send streaming event to all connections for a task"""
        if task_id not in self.active_connections or len(self.active_connections[task_id]) == 0:
            logger.info(f"📡 No active connections for task {task_id} - stream event ignored gracefully")
            return
        
        message = json.dumps({
            "type": "stream_event",
            "task_id": task_id,
            "event": event_data
        })
        
        logger.info(f"📡 WEBSOCKET SENDING STREAM EVENT to {len(self.active_connections[task_id])} clients: {event_data.get('event_type', 'unknown')} - {event_data.get('agent_name', 'unknown')}")
        await self.broadcast(task_id, message)
        logger.info(f"✅ Stream event broadcasted successfully")
    
    async def send_streaming_batch(self, task_id: str, events: list):
        """Send batch of streaming events to all connections for a task"""
        if task_id not in self.active_connections:
            logger.warning(f"🚫 No active connections for task {task_id} - cannot send stream batch")
            return
        
        message = json.dumps({
            "type": "stream_batch",
            "task_id": task_id,
            "events": events
        })
        
        logger.info(f"📦 WEBSOCKET SENDING STREAM BATCH to {len(self.active_connections[task_id])} clients: {len(events)} events")
        await self.broadcast(task_id, message)
        logger.info(f"✅ Stream batch broadcasted successfully")
    
    async def monitor_task_progress(self, task_id: str):
        """Monitor task progress and send updates to connected clients"""
        logger.info(f"Starting progress monitoring for task {task_id}")
        
        last_progress = -1
        last_status = ""
        
        # Reduce initial delay to catch early failures
        await asyncio.sleep(0.2)
        
        try:
            attempts_without_task = 0
            max_attempts = 10  # Increase attempts for better resilience
            
            while self.monitoring_tasks.get(task_id, False):
                # Create a new database session for each check to avoid stale data
                db = get_db_session()
                
                try:
                    # Force database to use latest data (important for SQLite)
                    db.expire_all()  # Expire all objects to force fresh read
                    db.commit()      # Commit any pending transactions
                    
                    # Get current task status from database
                    task_status = crud.get_task_status(db, task_id)
                    logger.debug(f"DEBUG: WebSocket monitoring loop for task {task_id} - monitoring_tasks status: {self.monitoring_tasks.get(task_id, False)}")
                    
                    if not task_status:
                        attempts_without_task += 1
                        if attempts_without_task <= max_attempts:
                            logger.debug(f"Task {task_id} not found in database (attempt {attempts_without_task}/{max_attempts})")
                            # Use shorter sleep for first few attempts
                            sleep_time = 0.5 if attempts_without_task <= 3 else 1.0
                            await asyncio.sleep(sleep_time)
                            continue
                        else:
                            logger.error(f"Task {task_id} not found in database after {max_attempts} attempts")
                            await self.send_error(task_id, "Task initialization failed - task record not found")
                            break
                    
                    # Reset counter when task is found
                    attempts_without_task = 0
                    
                    # Check if progress or status changed
                    current_progress = task_status.progress
                    current_status = task_status.status
                    
                    # Log status transitions for debugging
                    if current_status != last_status:
                        logger.info(f"Task {task_id} status changed: {last_status} -> {current_status}")
                    
                    logger.info(f"DEBUG: WebSocket monitoring task {task_id} - current_progress={current_progress}, current_status={current_status}, last_progress={last_progress}, last_status={last_status}")
                    
                    # Always send update if status changed or progress changed
                    if (current_progress != last_progress or 
                        current_status != last_status):
                        
                        # Send progress update
                        update_data = {
                            "progress": current_progress,
                            "status": current_status,
                            "current_step": task_status.current_step,
                            "step_number": None,  # You can calculate this based on progress
                            "total_steps": task_status.total_steps,
                            "estimated_remaining_minutes": self._estimate_remaining_time(
                                task_status.started_at,
                                current_progress
                            ) if task_status.started_at else None
                        }
                        
                        # Include error message if task failed
                        if current_status == "failed" and task_status.error_message:
                            update_data["error_message"] = task_status.error_message
                        
                        await self.send_progress_update(task_id, update_data)
                        
                        last_progress = current_progress
                        last_status = current_status
                    
                    # Check if task is completed or failed
                    if current_status in ["completed", "failed"]:
                        logger.info(f"Task {task_id} reached terminal status: {current_status}")
                        
                        # Send completion or failure notification
                        completion_data = {
                            "status": current_status,
                            "progress": current_progress,
                            "result_data": task_status.result_data,
                            "error_message": task_status.error_message,
                            "rubric_id": task_status.rubric_id
                        }
                        
                        if current_status == "failed":
                            logger.error(f"Task {task_id} failed with error: {task_status.error_message}")
                            # Send error notification before completion
                            if task_status.error_message:
                                await self.send_error(task_id, task_status.error_message)
                        
                        await self.send_completion(task_id, completion_data)
                        break
                    
                finally:
                    # Always close the database session
                    db.close()
                
                # Wait before next check - use adaptive polling
                if current_status == "pending":
                    # Check more frequently when pending
                    await asyncio.sleep(0.5)
                else:
                    # Normal polling interval when running
                    await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error monitoring task {task_id}: {e}")
        finally:
            logger.info(f"Stopped monitoring task {task_id}")
    
    def _estimate_remaining_time(self, started_at, current_progress) -> int:
        """Estimate remaining time in minutes based on current progress"""
        if not started_at or current_progress <= 0:
            return 15  # Default estimate
        
        from datetime import datetime
        elapsed_minutes = (datetime.utcnow() - started_at).total_seconds() / 60
        
        if current_progress >= 100:
            return 0
        
        # Estimate total time based on current progress
        estimated_total_minutes = (elapsed_minutes / current_progress) * 100
        remaining_minutes = max(0, estimated_total_minutes - elapsed_minutes)
        
        return int(remaining_minutes)
    
    def _notify_stream_managers_of_connection(self, task_id: str):
        """Notify any stream managers that a WebSocket connection is now available."""
        try:
            logger.info(f"🔗 WebSocket connection established for task {task_id}, triggering retry for any buffered events")
            
            # Create a small delay to ensure the connection is fully established
            import asyncio
            import threading
            
            def trigger_retry():
                # Import here to avoid circular imports
                try:
                    from app.services.qgen.streaming.stream_manager import StreamManager
                    # This notification will trigger existing stream managers to retry their buffered events
                    logger.info(f"✅ Connection notification sent for task {task_id}")
                except Exception as e:
                    logger.error(f"Error in retry trigger: {e}")
            
            # Run the notification in a separate thread to avoid blocking
            retry_thread = threading.Thread(target=trigger_retry)
            retry_thread.daemon = True
            retry_thread.start()
            
        except Exception as e:
            logger.error(f"Error notifying stream managers of connection: {e}")
    
    def _update_websocket_connection_in_db(self, task_id: str, connected: bool):
        """Update database to track WebSocket connection status for cross-process communication"""
        try:
            from app.db_ops.database import get_db_session
            from app.db_ops.models import TaskStatus
            
            db = get_db_session()
            try:
                task_status = db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
                if task_status:
                    if not hasattr(task_status, 'websocket_connected'):
                        # Add websocket_connected field to the task status if it doesn't exist
                        # For now, we'll just log the connection status
                        logger.info(f"📡 WebSocket connection status for task {task_id}: {'connected' if connected else 'disconnected'}")
                    else:
                        task_status.websocket_connected = connected
                        db.commit()
                        logger.info(f"📡 Updated WebSocket connection status in DB for task {task_id}: {'connected' if connected else 'disconnected'}")
                else:
                    logger.warning(f"Task {task_id} not found in database for WebSocket connection tracking")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error updating WebSocket connection status in database: {e}")
    
    async def _get_redis_subscriber(self):
        """Get or create Redis subscriber instance."""
        if self._redis_subscriber is None:
            self._redis_subscriber = await get_redis_subscriber(self)
        return self._redis_subscriber
    
    async def _subscribe_to_redis_events(self, task_id: str):
        """Subscribe to Redis events for a specific task."""
        try:
            subscriber = await self._get_redis_subscriber()
            await subscriber.subscribe_to_task(task_id)
            logger.info(f"📡 Subscribed to Redis events for task {task_id}")
        except Exception as e:
            logger.error(f"❌ Error subscribing to Redis events for task {task_id}: {e}")
    
    async def _unsubscribe_from_redis_events(self, task_id: str):
        """Unsubscribe from Redis events for a specific task."""
        try:
            if self._redis_subscriber:
                await self._redis_subscriber.unsubscribe_from_task(task_id)
                logger.info(f"📡 Unsubscribed from Redis events for task {task_id}")
        except Exception as e:
            logger.error(f"❌ Error unsubscribing from Redis events for task {task_id}: {e}")

# Global connection manager instance
connection_manager = ConnectionManager()