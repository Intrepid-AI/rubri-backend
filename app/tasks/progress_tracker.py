from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Session
import json

from app.db_ops.models import TaskStatus
from app.logger import get_logger

if TYPE_CHECKING:
    from app.services.qgen.streaming.stream_manager import StreamEvent

logger = get_logger(__name__)

class ProgressTracker:
    """
    Utility class for tracking and updating task progress in the database
    """
    
    def __init__(self, task_id: str, db: Session = None, total_steps: int = 5):
        self.task_id = task_id
        self.db = db
        self.total_steps = total_steps
        self.logger = logger
        self._streaming_events: List[Dict[str, Any]] = []
        self._streaming_enabled = False
    
    def start_task(self, 
                   task_type: str,
                   position_title: Optional[str] = None,
                   user_email: Optional[str] = None,
                   user_id: Optional[str] = None,
                   request_data: Optional[Dict[str, Any]] = None):
        """Initialize task status in database"""
        try:
            task_status = TaskStatus(
                task_id=self.task_id,
                task_type=task_type,
                status="in_progress",
                progress=0,
                current_step="Initializing...",
                total_steps=self.total_steps,
                user_id=user_id,
                user_email=user_email,
                position_title=position_title,
                request_data=request_data,
                started_at=datetime.utcnow()
            )
            
            self.db.add(task_status)
            self.db.commit()
            self.db.flush()  # Force immediate write to database
            
            self.logger.info(f"Started tracking task {self.task_id} of type {task_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize task status for {self.task_id}: {e}")
            self.db.rollback()
    
    def update_status_to_in_progress(self):
        """Update task status from pending to in_progress"""
        try:
            task_status = self.db.query(TaskStatus).filter(
                TaskStatus.task_id == self.task_id
            ).first()
            
            if task_status:
                old_status = task_status.status
                task_status.status = "in_progress"
                task_status.started_at = datetime.utcnow()
                
                self.db.commit()
                self.logger.info(f"Task {self.task_id} status updated: {old_status} -> in_progress")
            else:
                self.logger.error(f"Task status not found for {self.task_id} when trying to update to in_progress")
                    
        except Exception as e:
            self.logger.error(f"Failed to update status for task {self.task_id}: {e}")
            self.db.rollback()
            raise
    
    def update_progress(self, 
                       progress: int,
                       current_step: str,
                       step_number: Optional[int] = None):
        """Update task progress"""
        self.logger.info(f"DEBUG: update_progress called with progress={progress}, current_step={current_step}, step_number={step_number}")
        
        try:
            task_status = self.db.query(TaskStatus).filter(
                TaskStatus.task_id == self.task_id
            ).first()
            
            if task_status:
                old_progress = task_status.progress
                task_status.progress = min(progress, 100)
                task_status.current_step = current_step
                
                # Ensure status is in_progress if not already completed/failed
                if task_status.status == "pending":
                    task_status.status = "in_progress"
                
                self.db.commit()
                self.logger.info(f"DEBUG: Task {self.task_id} progress updated: {old_progress}% -> {progress}% - {current_step}")
            else:
                self.logger.warning(f"Task status not found for {self.task_id}")
                    
        except Exception as e:
            self.logger.error(f"Failed to update progress for task {self.task_id}: {e}")
            self.db.rollback()
            # Don't raise - continue with task execution
    
    def complete_task(self, 
                     result_data: Optional[Dict[str, Any]] = None,
                     rubric_id: Optional[str] = None):
        """Mark task as completed"""
        try:
            task_status = self.db.query(TaskStatus).filter(
                TaskStatus.task_id == self.task_id
            ).first()
            
            if task_status:
                task_status.status = "completed"
                task_status.progress = 100
                task_status.current_step = "Completed"
                task_status.completed_at = datetime.utcnow()
                task_status.result_data = result_data
                task_status.rubric_id = rubric_id
                
                self.db.commit()
                self.logger.info(f"Task {self.task_id} completed successfully")
            else:
                self.logger.warning(f"Task status not found for {self.task_id}")
                    
        except Exception as e:
            self.logger.error(f"Failed to complete task {self.task_id}: {e}")
            self.db.rollback()
    
    def fail_task(self, error_message: str):
        """Mark task as failed"""
        try:
            task_status = self.db.query(TaskStatus).filter(
                TaskStatus.task_id == self.task_id
            ).first()
            
            if task_status:
                task_status.status = "failed"
                task_status.current_step = "Failed"
                task_status.completed_at = datetime.utcnow()
                task_status.error_message = error_message
                
                self.db.commit()
                self.logger.error(f"Task {self.task_id} failed: {error_message}")
            else:
                self.logger.warning(f"Task status not found for {self.task_id}")
                    
        except Exception as e:
            self.logger.error(f"Failed to mark task {self.task_id} as failed: {e}")
            self.db.rollback()
            # Don't raise - just log the original error
            self.logger.error(f"Original task failure: {error_message}")
    
    def get_status(self) -> Optional[TaskStatus]:
        """Get current task status"""
        try:
            return self.db.query(TaskStatus).filter(
                TaskStatus.task_id == self.task_id
            ).first()
        except Exception as e:
            self.logger.error(f"Failed to get status for task {self.task_id}: {e}")
            return None
    
    def enable_streaming(self):
        """Enable streaming event collection"""
        self._streaming_enabled = True
        self.logger.info(f"Streaming enabled for task {self.task_id}")
    
    def add_streaming_event(self, event: 'StreamEvent'):
        """Add a streaming event to the buffer"""
        if self._streaming_enabled:
            self._streaming_events.append(event.to_dict())
            
            # Also update progress in database if we have db access
            if self.db:
                self._update_streaming_data()
    
    def _update_streaming_data(self):
        """Update streaming data in database"""
        try:
            if not self.db:
                return
                
            task_status = self.db.query(TaskStatus).filter(
                TaskStatus.task_id == self.task_id
            ).first()
            
            if task_status:
                # Store streaming events in result_data
                if not task_status.result_data:
                    task_status.result_data = {}
                
                task_status.result_data['streaming_events'] = self._streaming_events[-100:]  # Keep last 100 events
                task_status.result_data['streaming_enabled'] = True
                
                self.db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update streaming data for task {self.task_id}: {e}")
            self.db.rollback()
    
    def get_streaming_events(self, since_sequence_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get streaming events, optionally since a specific sequence ID"""
        if since_sequence_id is None:
            return self._streaming_events.copy()
        
        # Filter events after the given sequence ID
        filtered_events = []
        for event in self._streaming_events:
            if event.get('sequence_id', 0) > since_sequence_id:
                filtered_events.append(event)
        
        return filtered_events
    
    def update_progress_with_stream(self, 
                                  progress: int,
                                  current_step: str,
                                  step_number: Optional[int] = None,
                                  streaming_data: Optional[Dict[str, Any]] = None):
        """Update task progress with optional streaming data"""
        self.update_progress(progress, current_step, step_number)
        
        if streaming_data and self.db:
            try:
                task_status = self.db.query(TaskStatus).filter(
                    TaskStatus.task_id == self.task_id
                ).first()
                
                if task_status:
                    if not task_status.result_data:
                        task_status.result_data = {}
                    
                    # Merge streaming data
                    task_status.result_data.update(streaming_data)
                    self.db.commit()
                    
            except Exception as e:
                self.logger.error(f"Failed to update streaming data: {e}")
                self.db.rollback()