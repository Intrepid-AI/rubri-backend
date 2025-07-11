import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db_ops.database import get_db_session
from app.db_ops import crud
from app.logger import get_logger

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

# Global connection manager instance
connection_manager = ConnectionManager()