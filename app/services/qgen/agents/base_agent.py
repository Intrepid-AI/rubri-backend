"""
Base Agent Class for Multi-Agent Technical Interview System
Integrated with Rubri Backend LLM Client
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from app.services.qgen.models.schemas import LLMConfig, LLMProvider, AgentResult, MultiAgentInterviewState
from app.logger import get_logger
from app.llm_client_ops import LLM_Client_Ops

if TYPE_CHECKING:
    from app.services.qgen.streaming.stream_manager import StreamManager

class LLMFactory:
    """Factory for creating LLM instances using Rubri's LLM client."""
    
    logger = get_logger(__name__)
    
    @staticmethod
    def create_llm(config: LLMConfig):
        """Create an LLM instance using Rubri's LLM_Client_Ops."""
        LLMFactory.logger.info(f"Creating LLM instance with provider: {config.provider.value}, model: {config.model}")
        
        try:
            # Map qgen provider names to rubri provider names
            provider_mapping = {
                LLMProvider.OPENAI: "openai",
                LLMProvider.GEMINI: "gemini", 
                LLMProvider.GROQ: "groq",
                LLMProvider.AZURE_OPENAI: "azure_openai",
                LLMProvider.PORTKEY: "portkey"
            }
            
            rubri_provider = provider_mapping.get(config.provider)
            if not rubri_provider:
                raise ValueError(f"Unsupported LLM provider: {config.provider}")
            
            # Create LLM client using Rubri's client
            llm_client_ops = LLM_Client_Ops(provider_name=rubri_provider)
            
            if not llm_client_ops.health_check():
                raise Exception("LLM health check failed")
            
            LLMFactory.logger.info(f"Successfully created LLM client: {config.model}")
            return llm_client_ops.llm_client
            
        except Exception as e:
            LLMFactory.logger.error(f"Failed to create LLM instance: {str(e)}")
            raise

class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, agent_name: str, llm_config: LLMConfig, 
                 structured_output_model: type = None, 
                 stream_manager: Optional['StreamManager'] = None):
        self.agent_name = agent_name
        self.llm_config = llm_config
        self.logger = get_logger(f"{__name__}.{agent_name}")
        self.stream_manager = stream_manager
        self._streaming_enabled = stream_manager is not None
        
        self.logger.info(f"Initializing {agent_name} agent")
        self.llm = LLMFactory.create_llm(llm_config)
        if structured_output_model is not None:
            self.llm = self.llm.with_structured_output(structured_output_model)
            self.logger.info(f"Agent {agent_name} configured with structured output: {structured_output_model.__name__}")
        
        self.logger.info(f"Successfully initialized {agent_name} agent (streaming: {self._streaming_enabled})")
    
    @abstractmethod
    def execute(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Execute the agent's logic. Must be implemented by subclasses."""
        raise NotImplementedError(f"{self.agent_name} must implement execute method")
    
    async def _stream_start(self, description: str = None) -> None:
        """Emit agent start event if streaming is enabled."""
        if self._streaming_enabled and self.stream_manager:
            await self.stream_manager.emit_agent_start(self.agent_name, description)
    
    async def _stream_thinking(self, thought: str) -> None:
        """Emit agent thinking event if streaming is enabled."""
        if self._streaming_enabled and self.stream_manager:
            await self.stream_manager.emit_agent_thinking(self.agent_name, thought)
    
    async def _stream_output(self, output: Dict[str, Any], chunk: bool = False) -> None:
        """Emit agent output event if streaming is enabled."""
        if self._streaming_enabled and self.stream_manager:
            await self.stream_manager.emit_agent_output(self.agent_name, output, chunk)
    
    async def _stream_complete(self, summary: str = None) -> None:
        """Emit agent completion event if streaming is enabled."""
        if self._streaming_enabled and self.stream_manager:
            await self.stream_manager.emit_agent_complete(self.agent_name, summary)
    
    async def _stream_error(self, error: str, details: Dict[str, Any] = None) -> None:
        """Emit error event if streaming is enabled."""
        if self._streaming_enabled and self.stream_manager:
            await self.stream_manager.emit_error(self.agent_name, error, details)
    
    def _ensure_async_context(self, coro):
        """Ensure coroutine runs in async context."""
        try:
            # For Celery workers, we need to run in a thread pool
            import threading
            import concurrent.futures
            
            def run_in_thread():
                try:
                    # Create new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(coro)
                    new_loop.close()
                    return result
                except Exception as e:
                    self.logger.error(f"Failed to run streaming event in thread: {e}")
                    return None
            
            # Run in thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=1.0)  # 1 second timeout
                
        except Exception as e:
            self.logger.error(f"Failed to ensure async context: {e}")
            return None
    
    def stream_start_sync(self, description: str = None) -> None:
        """Synchronous wrapper for streaming start event."""
        if self._streaming_enabled:
            self.logger.info(f"🔥 STREAM START: {self.agent_name} - {description}")
            self._ensure_async_context(self._stream_start(description))
        else:
            self.logger.warning(f"Streaming not enabled for {self.agent_name}")
    
    def stream_thinking_sync(self, thought: str) -> None:
        """Synchronous wrapper for streaming thinking event."""
        if self._streaming_enabled:
            self.logger.info(f"🔥 STREAM THINKING: {self.agent_name} - {thought[:50]}...")
            self._ensure_async_context(self._stream_thinking(thought))
    
    def stream_output_sync(self, output: Dict[str, Any], chunk: bool = False) -> None:
        """Synchronous wrapper for streaming output event."""
        if self._streaming_enabled:
            self._ensure_async_context(self._stream_output(output, chunk))
    
    def stream_complete_sync(self, summary: str = None) -> None:
        """Synchronous wrapper for streaming completion event."""
        if self._streaming_enabled:
            self._ensure_async_context(self._stream_complete(summary))
    
    def stream_error_sync(self, error: str, details: Dict[str, Any] = None) -> None:
        """Synchronous wrapper for streaming error event."""
        if self._streaming_enabled:
            self._ensure_async_context(self._stream_error(error, details))
    
    def _record_result(self, state: MultiAgentInterviewState, 
                      success: bool, output_data: Dict[str, Any] = None, 
                      error_message: str = None, execution_time: float = 0.0):
        """Record agent execution result in the state."""
        result = AgentResult(
            agent_name=self.agent_name,
            execution_time=execution_time,
            success=success,
            output_data=output_data or {},
            error_message=error_message,
            metadata={
                "llm_provider": self.llm_config.provider.value,
                "llm_model": self.llm_config.model,
                "timestamp": time.time()
            }
        )
        state["agent_results"].append(result)
        state["current_agent"] = self.agent_name if success else None
    
    def _log_info(self, message: str, state: MultiAgentInterviewState = None):
        """Log informational message."""
        self.logger.info(message)
        
        if state:
            from langchain_core.messages import AIMessage
            state["messages"].append(AIMessage(content=f"[{self.agent_name}] {message}"))
        
        # Emit as thinking event if streaming
        self.stream_thinking_sync(message)
    
    def _log_error(self, error: str, state: MultiAgentInterviewState = None):
        """Log error message."""
        self.logger.error(error)
        
        if state:
            state["errors"].append(f"[{self.agent_name}] ERROR: {error}")
        
        # Emit as error event if streaming
        self.stream_error_sync(error)
    
    def _log_success(self, message: str, state: MultiAgentInterviewState = None):
        """Log success message."""
        self.logger.info(message)
        
        if state:
            from langchain_core.messages import AIMessage
            state["messages"].append(AIMessage(content=f"[{self.agent_name}] SUCCESS: {message}"))
    
    def _validate_input(self, state: MultiAgentInterviewState, required_fields: list) -> bool:
        """Validate that required fields are present in state."""
        missing_fields = []
        
        for field in required_fields:
            if field not in state or not state[field]:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            self._log_error(error_msg, state)
            return False
        
        return True
    
    def _safe_execute(self, state: MultiAgentInterviewState, 
                     execution_func, required_fields: list = None) -> MultiAgentInterviewState:
        """Safely execute agent logic with error handling and timing."""
        self.logger.info(f"Starting execution of {self.agent_name}")
        start_time = time.time()
        
        # Emit streaming start event
        self.stream_start_sync(f"{self.agent_name} is starting...")
        
        try:
            # Validate inputs if required
            if required_fields:
                self.logger.info(f"Validating required fields: {required_fields}")
                if not self._validate_input(state, required_fields):
                    raise ValueError(f"Input validation failed for {self.agent_name}")
                self.logger.info("Input validation passed")
            
            # Execute the main logic
            self.logger.info(f"Executing main logic for {self.agent_name}")
            result_state = execution_func(state)
            
            # Record successful execution
            execution_time = time.time() - start_time
            self.logger.info(f"Agent {self.agent_name} completed successfully in {execution_time:.2f}s")
            
            self._record_result(
                result_state,
                success=True,
                execution_time=execution_time
            )
            
            # Emit streaming complete event
            self.stream_complete_sync(f"{self.agent_name} completed successfully")
            
            return result_state
            
        except Exception as e:
            # Record failed execution
            execution_time = time.time() - start_time
            error_message = f"{self.agent_name} execution failed: {str(e)}"
            
            self.logger.error(f"Agent {self.agent_name} failed after {execution_time:.2f}s: {str(e)}")
            self._log_error(error_message, state)
            self._record_result(
                state,
                success=False,
                error_message=error_message,
                execution_time=execution_time
            )
            
            return state

class AgentMetrics:
    """Utility class for tracking agent performance metrics."""
    
    @staticmethod
    def calculate_total_execution_time(agent_results: list) -> float:
        """Calculate total execution time across all agents."""
        return sum(result.execution_time for result in agent_results)
    
    @staticmethod
    def get_agent_success_rate(agent_results: list) -> float:
        """Calculate success rate across all agents."""
        if not agent_results:
            return 0.0
        
        successful = sum(1 for result in agent_results if result.success)
        return successful / len(agent_results)
    
    @staticmethod
    def get_slowest_agent(agent_results: list) -> str:
        """Get the name of the slowest executing agent."""
        if not agent_results:
            return "None"
        
        slowest = max(agent_results, key=lambda r: r.execution_time)
        return slowest.agent_name
    
    @staticmethod
    def generate_performance_summary(agent_results: list) -> Dict[str, Any]:
        """Generate comprehensive performance summary."""
        if not agent_results:
            return {"total_agents": 0, "all_successful": False}
        
        return {
            "total_agents": len(agent_results),
            "successful_agents": sum(1 for r in agent_results if r.success),
            "failed_agents": sum(1 for r in agent_results if not r.success),
            "total_execution_time": AgentMetrics.calculate_total_execution_time(agent_results),
            "average_execution_time": AgentMetrics.calculate_total_execution_time(agent_results) / len(agent_results),
            "success_rate": AgentMetrics.get_agent_success_rate(agent_results),
            "slowest_agent": AgentMetrics.get_slowest_agent(agent_results),
            "all_successful": all(r.success for r in agent_results),
            "agent_details": [
                {
                    "name": r.agent_name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "error": r.error_message if not r.success else None
                }
                for r in agent_results
            ]
        }

def create_agent_with_retry(agent_class, llm_config: LLMConfig, 
                          stream_manager: Optional['StreamManager'] = None,
                          max_retries: int = 3):
    """Create an agent with retry logic for LLM initialization."""
    for attempt in range(max_retries):
        try:
            return agent_class(llm_config, stream_manager=stream_manager)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Attempt {attempt + 1} failed, retrying... Error: {e}")
            time.sleep(1)  # Brief delay before retry

def validate_agent_chain(agents: list, state: MultiAgentInterviewState) -> bool:
    """Validate that a chain of agents can process the given state."""
    current_state = state.copy()
    
    for agent in agents:
        try:
            # Dry run validation (don't actually execute)
            required_fields = getattr(agent, 'required_fields', [])
            if required_fields:
                missing = [field for field in required_fields if field not in current_state]
                if missing:
                    print(f"Agent {agent.agent_name} missing required fields: {missing}")
                    return False
        except Exception as e:
            print(f"Validation failed for agent {agent.agent_name}: {e}")
            return False
    
    return True