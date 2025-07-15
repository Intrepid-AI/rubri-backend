"""
Stream Manager with Redis Publishing

This is a simplified version of the stream manager that publishes events
to Redis instead of trying to communicate directly with WebSockets.

This solves the cross-process communication issue between Celery workers
and the FastAPI server.
"""

import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from threading import Lock
import logging

from app.services.qgen.streaming.redis_publisher import get_redis_publisher

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of streaming events."""
    AGENT_START = "agent_start"
    AGENT_PROGRESS = "agent_progress"
    AGENT_THINKING = "agent_thinking"
    AGENT_OUTPUT = "agent_output"
    AGENT_COMPLETE = "agent_complete"
    SKILL_FOUND = "skill_found"
    QUESTION_GENERATED = "question_generated"
    EVALUATION_RESULT = "evaluation_result"
    RESPONSE_GENERATED = "response_generated"
    SECTION_ASSEMBLED = "section_assembled"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Represents a streaming event."""
    event_type: StreamEventType
    agent_name: str
    data: Dict[str, Any]
    timestamp: float = None
    sequence_id: int = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "agent_name": self.agent_name,
            "data": self.data,
            "timestamp": self.timestamp,
            "sequence_id": self.sequence_id
        }


class StreamManager:
    """
    Simplified stream manager that publishes events to Redis.
    
    This version removes all the complex buffering and retry logic since
    Redis pub/sub handles message delivery.
    """
    
    def __init__(self, task_id: str, websocket_enabled: bool = True):
        self.task_id = task_id
        self.websocket_enabled = websocket_enabled
        self._sequence_counter = 0
        self._sequence_lock = Lock()
        self._callbacks: List[Callable[[StreamEvent], None]] = []
        
        # Get Redis publisher singleton
        if self.websocket_enabled:
            self._publisher = get_redis_publisher()
        else:
            self._publisher = None
    
    def _get_next_sequence_id(self) -> int:
        """Get next sequence ID for event ordering."""
        with self._sequence_lock:
            self._sequence_counter += 1
            return self._sequence_counter
    
    def emit_event_sync(self, event: StreamEvent) -> None:
        """
        Emit a streaming event synchronously (for Celery context).
        
        This is the main method used by agents to send events.
        """
        # Assign sequence ID
        event.sequence_id = self._get_next_sequence_id()
        
        # Execute local callbacks (for testing, logging, etc.)
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in stream callback: {e}")
        
        # Publish to Redis if enabled
        if self.websocket_enabled and self._publisher:
            try:
                success = self._publisher.publish_event(self.task_id, event.to_dict())
                if success:
                    logger.debug(f"✅ Event published to Redis: {event.event_type} - {event.agent_name}")
                else:
                    logger.warning(f"⚠️ Failed to publish event to Redis: {event.event_type}")
            except Exception as e:
                logger.error(f"❌ Error publishing to Redis: {e}")
    
    async def emit_event(self, event: StreamEvent) -> None:
        """
        Async wrapper for emit_event_sync.
        
        Maintains compatibility with async code.
        """
        self.emit_event_sync(event)
    
    def add_callback(self, callback: Callable[[StreamEvent], None]) -> None:
        """Add a callback for stream events."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[StreamEvent], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # Agent helper methods for common event types
    
    def emit_agent_start_sync(self, agent_name: str, description: str = None) -> None:
        """Emit agent start event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_START,
            agent_name=agent_name,
            data={
                "description": description or f"{agent_name} is starting...",
                "status": "started"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_agent_start(self, agent_name: str, description: str = None) -> None:
        """Emit agent start event."""
        self.emit_agent_start_sync(agent_name, description)
    
    def emit_agent_thinking_sync(self, agent_name: str, thought: str) -> None:
        """Emit agent thinking event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_THINKING,
            agent_name=agent_name,
            data={
                "thought": thought,
                "status": "thinking"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_agent_thinking(self, agent_name: str, thought: str) -> None:
        """Emit agent thinking event."""
        self.emit_agent_thinking_sync(agent_name, thought)
    
    def emit_agent_output_sync(self, agent_name: str, output: Dict[str, Any], 
                              chunk: bool = False) -> None:
        """Emit agent output event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_OUTPUT,
            agent_name=agent_name,
            data={
                "output": output,
                "is_chunk": chunk,
                "status": "processing"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_agent_output(self, agent_name: str, output: Dict[str, Any], 
                               chunk: bool = False) -> None:
        """Emit agent output event."""
        self.emit_agent_output_sync(agent_name, output, chunk)
    
    def emit_agent_progress_sync(self, agent_name: str, progress: int, 
                                message: str = None) -> None:
        """Emit agent progress event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_PROGRESS,
            agent_name=agent_name,
            data={
                "progress": progress,
                "message": message,
                "status": "in_progress"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_agent_progress(self, agent_name: str, progress: int, 
                                 message: str = None) -> None:
        """Emit agent progress event."""
        self.emit_agent_progress_sync(agent_name, progress, message)
    
    def emit_skill_found_sync(self, skill: Dict[str, Any]) -> None:
        """Emit skill found event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.SKILL_FOUND,
            agent_name="SkillExtractionAgent",
            data={
                "skill": skill,
                "status": "skill_extracted"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_skill_found(self, skill: Dict[str, Any]) -> None:
        """Emit skill found event."""
        self.emit_skill_found_sync(skill)
    
    def emit_question_generated_sync(self, question: Dict[str, Any], 
                                    question_number: int, total_questions: int) -> None:
        """Emit question generated event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.QUESTION_GENERATED,
            agent_name="QuestionGenerationAgent",
            data={
                "question": question,
                "question_number": question_number,
                "total_questions": total_questions,
                "status": "question_generated"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_question_generated(self, question: Dict[str, Any], 
                                    question_number: int, total_questions: int) -> None:
        """Emit question generated event."""
        self.emit_question_generated_sync(question, question_number, total_questions)
    
    def emit_evaluation_result_sync(self, question_id: str, evaluation: Dict[str, Any]) -> None:
        """Emit evaluation result event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.EVALUATION_RESULT,
            agent_name="QuestionEvaluationAgent",
            data={
                "question_id": question_id,
                "evaluation": evaluation,
                "status": "question_evaluated"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_evaluation_result(self, question_id: str, evaluation: Dict[str, Any]) -> None:
        """Emit evaluation result event."""
        self.emit_evaluation_result_sync(question_id, evaluation)
    
    def emit_response_generated_sync(self, question_id: str, response: Dict[str, Any]) -> None:
        """Emit response generated event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.RESPONSE_GENERATED,
            agent_name="ExpectedResponseAgent",
            data={
                "question_id": question_id,
                "response": response,
                "status": "response_generated"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_response_generated(self, question_id: str, response: Dict[str, Any]) -> None:
        """Emit response generated event."""
        self.emit_response_generated_sync(question_id, response)
    
    def emit_section_assembled_sync(self, section_name: str, content: str) -> None:
        """Emit section assembled event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.SECTION_ASSEMBLED,
            agent_name="ReportAssemblyAgent",
            data={
                "section_name": section_name,
                "content": content,
                "status": "section_assembled"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_section_assembled(self, section_name: str, content: str) -> None:
        """Emit section assembled event."""
        self.emit_section_assembled_sync(section_name, content)
    
    def emit_agent_complete_sync(self, agent_name: str, summary: str = None) -> None:
        """Emit agent completion event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_COMPLETE,
            agent_name=agent_name,
            data={
                "summary": summary or f"{agent_name} completed successfully",
                "status": "completed"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_agent_complete(self, agent_name: str, summary: str = None) -> None:
        """Emit agent completion event."""
        self.emit_agent_complete_sync(agent_name, summary)
    
    def emit_error_sync(self, agent_name: str, error: str, details: Dict[str, Any] = None) -> None:
        """Emit error event synchronously."""
        event = StreamEvent(
            event_type=StreamEventType.ERROR,
            agent_name=agent_name,
            data={
                "error": error,
                "details": details or {},
                "status": "error"
            }
        )
        self.emit_event_sync(event)
    
    async def emit_error(self, agent_name: str, error: str, details: Dict[str, Any] = None) -> None:
        """Emit error event."""
        self.emit_error_sync(agent_name, error, details)
    
    # Compatibility methods (no-ops in Redis version)
    
    async def flush(self) -> None:
        """Compatibility method - no buffering in Redis version."""
        pass
    
    async def close(self) -> None:
        """Compatibility method - Redis publisher manages its own connection."""
        pass