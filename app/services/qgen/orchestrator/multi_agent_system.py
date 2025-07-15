from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
import time
from typing import Literal, Optional, TYPE_CHECKING
from app.services.qgen.models.schemas import (
    LLMConfig, LLMProvider, MultiAgentInterviewState, ProcessingStage,
    create_initial_state
)
from app.services.qgen.agents.skill_extraction_agent import SkillExtractionAgent
from app.services.qgen.agents.question_generation_agent import QuestionGenerationAgent
from app.services.qgen.agents.question_evaluation_agent import QuestionEvaluationAgent
from app.services.qgen.agents.expected_response_agent import ExpectedResponseAgent
from app.services.qgen.agents.report_assembly_agent import ReportAssemblyAgent
from app.services.qgen.utils.report_formatter import format_final_report
from app.logger import get_logger

if TYPE_CHECKING:
    from app.services.qgen.streaming.stream_manager import StreamManager

class MultiAgentTechnicalInterviewSystem:
    """
    Complete Multi-Agent Technical Interview System
    
    Orchestrates 5 specialized agents:
    1. SkillExtractionAgent - Extracts technical skills from resume/JD
    2. QuestionGenerationAgent - Creates deep technical questions  
    3. QuestionEvaluationAgent - Evaluates question quality
    4. ExpectedResponseAgent - Generates interviewer guidance
    5. ReportAssemblyAgent - Creates final comprehensive report
    """
    
    def __init__(self, llm_config: LLMConfig, stream_manager: Optional['StreamManager'] = None):
        self.llm_config = llm_config
        self.stream_manager = stream_manager
        self.memory = MemorySaver()
        self.logger = get_logger(__name__)
        
        self.logger.info("Initializing Multi-Agent Technical Interview System")
        self.logger.info(f"LLM Configuration: Provider={llm_config.provider.value}, Model={llm_config.model}, Temperature={llm_config.temperature}")
        self.logger.info(f"Streaming enabled: {stream_manager is not None}")
        
        # Initialize all agents with streaming support
        self.logger.info("Initializing all agents...")
        self.skill_extractor = SkillExtractionAgent(llm_config, stream_manager)
        self.question_generator = QuestionGenerationAgent(llm_config, stream_manager)
        self.question_evaluator = QuestionEvaluationAgent(llm_config, stream_manager)
        self.response_generator = ExpectedResponseAgent(llm_config, stream_manager)
        self.report_assembler = ReportAssemblyAgent(llm_config, stream_manager)
        self.logger.info("All agents initialized successfully")
        
        # Build workflow
        self.logger.info("Building multi-agent workflow...")
        self.workflow = self._build_workflow()
        self.agent = self.workflow.compile(checkpointer=self.memory)
        self.logger.info("Multi-Agent Technical Interview System initialized successfully")
    
    def _build_workflow(self) -> StateGraph:
        """Build the complete multi-agent workflow."""
        
        self.logger.info("Building multi-agent workflow with 5 agents")
        workflow = StateGraph(MultiAgentInterviewState)
        
        # Add all agent nodes
        workflow.add_node("extract_skills", self.skill_extractor.execute)
        workflow.add_node("generate_questions", self.question_generator.execute)
        workflow.add_node("evaluate_questions", self.question_evaluator.execute)
        workflow.add_node("generate_responses", self.response_generator.execute)
        workflow.add_node("assemble_report", self.report_assembler.execute)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.add_edge(START, "extract_skills")
        self.logger.info("Workflow entry point set to skill extraction")
        
        # Define workflow transitions
        self.logger.info("Setting up workflow transitions and conditional routing")
        workflow.add_conditional_edges(
            "extract_skills",
            self._route_from_skill_extraction,
            {
                "generate_questions": "generate_questions",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_questions", 
            self._route_from_question_generation,
            {
                "evaluate_questions": "evaluate_questions",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "evaluate_questions",
            self._route_from_question_evaluation,
            {
                "generate_responses": "generate_responses",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_responses",
            self._route_from_response_generation,
            {
                "assemble_report": "assemble_report",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "assemble_report",
            self._route_from_report_assembly,
            {
                "complete": END,
                "error": "handle_error"
            }
        )
        
        # Error handling leads to END
        workflow.add_edge("handle_error", END)
        self.logger.info("Multi-agent workflow built successfully with error handling")
        
        return workflow
    
    def _route_from_skill_extraction(self, state: MultiAgentInterviewState) -> str:
        """Route after skill extraction."""
        stage = state["processing_stage"]
        self.logger.info(f"Routing from skill extraction, current stage: {stage}")
        
        if stage == ProcessingStage.ERROR:
            self.logger.error("Skill extraction failed, routing to error handler")
            return "error"
        elif stage == ProcessingStage.SKILLS_EXTRACTED:
            self.logger.info("Skill extraction successful, routing to question generation")
            return "generate_questions"
        else:
            self.logger.error(f"Unexpected processing stage after skill extraction: {stage}")
            return "error"
    
    def _route_from_question_generation(self, state: MultiAgentInterviewState) -> str:
        """Route after question generation."""
        stage = state["processing_stage"]
        self.logger.info(f"Routing from question generation, current stage: {stage}")
        
        if stage == ProcessingStage.ERROR:
            self.logger.error("Question generation failed, routing to error handler")
            return "error"
        elif stage == ProcessingStage.QUESTIONS_GENERATED:
            self.logger.info("Question generation successful, routing to question evaluation")
            return "evaluate_questions"
        else:
            self.logger.error(f"Unexpected processing stage after question generation: {stage}")
            return "error"
    
    def _route_from_question_evaluation(self, state: MultiAgentInterviewState) -> str:
        """Route after question evaluation."""
        stage = state["processing_stage"]
        self.logger.info(f"Routing from question evaluation, current stage: {stage}")
        
        if stage == ProcessingStage.ERROR:
            self.logger.error("Question evaluation failed, routing to error handler")
            return "error"
        elif stage == ProcessingStage.QUESTIONS_EVALUATED:
            self.logger.info("Question evaluation successful, routing to expected response generation")
            return "generate_responses"
        else:
            self.logger.error(f"Unexpected processing stage after question evaluation: {stage}")
            return "error"
    
    def _route_from_response_generation(self, state: MultiAgentInterviewState) -> str:
        """Route after response generation."""
        stage = state["processing_stage"]
        self.logger.info(f"Routing from response generation, current stage: {stage}")
        
        if stage == ProcessingStage.ERROR:
            self.logger.error("Expected response generation failed, routing to error handler")
            return "error"
        elif stage == ProcessingStage.RESPONSES_GENERATED:
            self.logger.info("Expected response generation successful, routing to report assembly")
            return "assemble_report"
        else:
            self.logger.error(f"Unexpected processing stage after response generation: {stage}")
            return "error"
    
    def _route_from_report_assembly(self, state: MultiAgentInterviewState) -> str:
        """Route after report assembly."""
        stage = state["processing_stage"]
        self.logger.info(f"Routing from report assembly, current stage: {stage}")
        
        if stage == ProcessingStage.ERROR:
            self.logger.error("Report assembly failed, routing to error handler")
            return "error"
        elif stage == ProcessingStage.COMPLETED:
            self.logger.info("Report assembly completed successfully, workflow complete")
            return "complete"
        else:
            self.logger.error(f"Unexpected processing stage after report assembly: {stage}")
            return "error"
    
    def _handle_error(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Handle errors that occur during processing."""
        errors = state.get("errors", [])
        
        self.logger.error(f"Multi-agent workflow encountered {len(errors)} errors:")
        for i, error in enumerate(errors, 1):
            self.logger.error(f"  Error {i}: {error}")
        
        error_message = "❌ Multi-agent interview generation failed:\n"
        for i, error in enumerate(errors, 1):
            error_message += f"  {i}. {error}\n"
        
        error_message += "\nPlease check your inputs and try again."
        
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content=error_message))
        state["processing_stage"] = ProcessingStage.ERROR
        
        self.logger.error("Multi-agent workflow terminated due to errors")
        return state
    
    def generate_technical_interview(self, 
                                   resume_text: str = "",
                                   job_description: str = "",
                                   position_title: str = "Technical Position",
                                   thread_id: str = "default") -> dict:
        """
        Main method to generate complete technical interview evaluation.
        
        Args:
            resume_text: Candidate's resume (optional)
            job_description: Job description (optional) 
            position_title: Position title
            thread_id: Unique thread ID for tracking
            
        Returns:
            Complete interview evaluation results
        """
        
        self.logger.info(f"Starting technical interview generation for position: {position_title}")
        self.logger.info(f"Thread ID: {thread_id}")
        self.logger.info(f"Resume text length: {len(resume_text)} characters")
        self.logger.info(f"Job description length: {len(job_description)} characters")
        
        start_time = time.time()
        
        try:
            # Create initial state
            self.logger.info("Creating initial state for multi-agent workflow")
            initial_state = create_initial_state(
                resume_text=resume_text,
                job_description=job_description,
                position_title=position_title,
                llm_provider=self.llm_config.provider,
                llm_model=self.llm_config.model
            )
            self.logger.info(f"Initial state created with input scenario: {initial_state['input_scenario']}")
            
            # Add initial message
            initial_state["messages"] = [
                HumanMessage(content=f"Generate comprehensive technical interview evaluation for {position_title}")
            ]
            
            # Execute multi-agent workflow
            self.logger.info("Executing multi-agent workflow...")
            result = self.agent.invoke(initial_state, config={"thread_id": thread_id})
            
            total_time = time.time() - start_time
            
            # Process results
            final_stage = result["processing_stage"]
            self.logger.info(f"Multi-agent workflow completed with stage: {final_stage}")
            self.logger.info(f"Total processing time: {total_time:.2f} seconds")
            
            if final_stage == ProcessingStage.COMPLETED:
                self.logger.info("Multi-agent workflow completed successfully")
                return self._create_success_response(result, total_time)
            else:
                self.logger.error(f"Multi-agent workflow failed at stage: {final_stage}")
                return self._create_error_response(result, total_time)
                
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"System error during multi-agent workflow: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Workflow failed after {total_time:.2f} seconds")
            
            return {
                "success": False,
                "error": error_msg,
                "processing_time": total_time,
                "stage_reached": "initialization"
            }
    
    def _create_success_response(self, result: MultiAgentInterviewState, total_time: float) -> dict:
        """Create success response with all results."""
        
        evaluation = result["final_evaluation"]
        agent_results = result["agent_results"]
        
        self.logger.info(f"Creating success response for candidate: {evaluation.candidate_name}")
        self.logger.info(f"Total skills identified: {evaluation.total_skills_identified}")
        self.logger.info(f"Total questions generated: {evaluation.total_questions}")
        self.logger.info(f"Estimated interview duration: {evaluation.estimated_interview_duration} minutes")
        
        # Calculate agent performance
        agent_performance = {}
        for agent_result in agent_results:
            agent_performance[agent_result.agent_name] = {
                "success": agent_result.success,
                "execution_time": agent_result.execution_time,
                "output_data": agent_result.output_data
            }
        
        # Generate formatted report
        self.logger.info("Generating formatted report...")
        formatted_report = format_final_report(evaluation)
        self.logger.info(f"Generated formatted report with {len(formatted_report)} characters")
        
        return {
            "success": True,
            "processing_time": total_time,
            "candidate_name": evaluation.candidate_name,
            "position_title": evaluation.position_title,
            "input_scenario": evaluation.input_scenario.value,
            
            # Core results
            "skills_identified": evaluation.total_skills_identified,
            "categories_covered": len(evaluation.skill_categories),
            "questions_generated": evaluation.total_questions,
            "interview_duration_minutes": evaluation.estimated_interview_duration,
            "sections_created": len(evaluation.interview_sections),
            
            # Insights
            "key_strengths": evaluation.key_strengths,
            "potential_concerns": evaluation.potential_concerns,
            "focus_areas": evaluation.recommended_focus_areas,
            "overall_recommendation": evaluation.overall_recommendation,
            
            # Complete data
            "formatted_report": formatted_report,
            "evaluation_object": evaluation.model_dump(mode='json') if evaluation else None,
            "agent_performance": agent_performance,
            
            # Processing details
            "messages": [msg.content for msg in result["messages"]],
            "workflow_success": True
        }
    
    def _create_error_response(self, result: MultiAgentInterviewState, total_time: float) -> dict:
        """Create error response with diagnostic information."""
        
        errors = result.get("errors", [])
        agent_results = result.get("agent_results", [])
        
        self.logger.error(f"Creating error response with {len(errors)} errors")
        for i, error in enumerate(errors, 1):
            self.logger.error(f"Error {i}: {error}")
        
        # Find where the workflow failed
        last_successful_agent = None
        failed_agent = None
        
        for agent_result in agent_results:
            if agent_result.success:
                last_successful_agent = agent_result.agent_name
                self.logger.info(f"Agent {agent_result.agent_name} completed successfully")
            else:
                failed_agent = agent_result.agent_name
                self.logger.error(f"Agent {agent_result.agent_name} failed: {agent_result.error_message}")
                break
        
        self.logger.info(f"Last successful agent: {last_successful_agent}")
        self.logger.error(f"Failed agent: {failed_agent}")
        
        return {
            "success": False,
            "processing_time": total_time,
            "stage_reached": result.get("processing_stage", "unknown"),
            "last_successful_agent": last_successful_agent,
            "failed_agent": failed_agent,
            "errors": errors,
            "messages": [msg.content for msg in result.get("messages", [])],
            "partial_results": {
                "skills_extracted": len(result.get("extracted_skills", [])),
                "questions_generated": len(result.get("generated_questions", [])),
                "questions_approved": len(result.get("approved_questions", []))
            }
        }

# Factory function for easy instantiation
def create_technical_interview_system(llm_provider: LLMProvider = LLMProvider.OPENAI,
                                     llm_model: str = "gpt-4.1",
                                     temperature: float = 0.1) -> MultiAgentTechnicalInterviewSystem:
    """
    Factory function to create a technical interview system.
    
    Args:
        llm_provider: LLM provider (OpenAI, Gemini, Groq, etc.)
        llm_model: Model name (e.g., "gpt-4o-mini", "gemini-2.0-flash-001")
        temperature: Model temperature for generation
        
    Returns:
        Configured multi-agent system
    """
    
    logger = get_logger(__name__)
    logger.info(f"Creating technical interview system with provider: {llm_provider.value}, model: {llm_model}, temperature: {temperature}")
    
    llm_config = LLMConfig(
        provider=llm_provider,
        model=llm_model,
        temperature=temperature
    )
    
    system = MultiAgentTechnicalInterviewSystem(llm_config)
    logger.info("Technical interview system created successfully")
    return system

def _create_interview_system_with_progress_patching(llm_config, progress_tracker, stream_manager=None):
    """
    Create interview system with progress tracking and streaming integrated during initialization
    """
    logger = get_logger(__name__)
    logger.info("Creating interview system with progress tracking and streaming integration")
    
    # Create system with modified initialization that includes progress patching and streaming
    system = ProgressTrackingMultiAgentSystem(llm_config, progress_tracker, stream_manager)
    logger.info("Progress-tracking and streaming interview system created successfully")
    return system

class ProgressTrackingMultiAgentSystem(MultiAgentTechnicalInterviewSystem):
    """
    Modified MultiAgentTechnicalInterviewSystem that integrates progress tracking
    during initialization, before workflow compilation
    """
    
    def __init__(self, llm_config, progress_tracker, stream_manager=None):
        self.progress_tracker = progress_tracker
        self.stream_manager = stream_manager
        self.llm_config = llm_config
        self.memory = MemorySaver()
        self.logger = get_logger(__name__)
        
        self.logger.info("Initializing Multi-Agent Technical Interview System with Progress Tracking and Streaming")
        self.logger.info(f"LLM Configuration: Provider={llm_config.provider.value}, Model={llm_config.model}, Temperature={llm_config.temperature}")
        self.logger.info(f"Streaming enabled: {stream_manager is not None}")
        
        # Initialize all agents with streaming support
        self.logger.info("Initializing all agents...")
        self.skill_extractor = SkillExtractionAgent(llm_config, stream_manager)
        self.question_generator = QuestionGenerationAgent(llm_config, stream_manager)
        self.question_evaluator = QuestionEvaluationAgent(llm_config, stream_manager)
        self.response_generator = ExpectedResponseAgent(llm_config, stream_manager)
        self.report_assembler = ReportAssemblyAgent(llm_config, stream_manager)
        self.logger.info("All agents initialized successfully")
        
        # PATCH AGENTS BEFORE WORKFLOW BUILDING
        self.logger.info("Patching agents for progress tracking BEFORE workflow compilation")
        self._patch_agents_for_progress()
        
        # Build workflow (now with patched agents)
        self.logger.info("Building multi-agent workflow...")
        self.workflow = self._build_workflow()
        self.agent = self.workflow.compile(checkpointer=self.memory)
        self.logger.info("Multi-Agent Technical Interview System with Progress Tracking initialized successfully")
    
    def _patch_agents_for_progress(self):
        """Patch agents to include progress tracking before workflow compilation"""
        agents = [
            (self.skill_extractor, "SkillExtractionAgent"),
            (self.question_generator, "QuestionGenerationAgent"),
            (self.question_evaluator, "QuestionEvaluationAgent"),
            (self.response_generator, "ExpectedResponseAgent"),
            (self.report_assembler, "ReportAssemblyAgent")
        ]
        
        for agent, agent_name in agents:
            self.logger.info(f"DEBUG: Patching {agent_name} execute method BEFORE workflow compilation")
            original_execute = agent.execute
            
            def create_wrapped_execute(original_method, name):
                def wrapped_execute(state):
                    self.logger.info(f"DEBUG: Starting agent: {name}")
                    self.progress_tracker.update_agent_progress(name, 0)
                    
                    try:
                        result = original_method(state)
                        self.progress_tracker.update_agent_progress(name, 100)
                        self.logger.info(f"DEBUG: Completed agent: {name}")
                        return result
                    except Exception as e:
                        self.logger.error(f"Agent {name} failed: {str(e)}")
                        raise
                
                return wrapped_execute
            
            # Replace the execute method BEFORE workflow uses it
            agent.execute = create_wrapped_execute(original_execute, agent_name)
            self.logger.info(f"DEBUG: Successfully patched {agent_name} BEFORE workflow compilation")
        
        self.logger.info("DEBUG: Finished patching all agents BEFORE workflow compilation")
    
    def _build_workflow(self) -> StateGraph:
        """Build the complete multi-agent workflow with lambda functions to support progress tracking."""
        
        self.logger.info("Building multi-agent workflow with 5 agents (with lambda functions for progress tracking)")
        workflow = StateGraph(MultiAgentInterviewState)
        
        # Add all agent nodes using lambda functions to call current method references
        self.logger.info("DEBUG: Adding workflow nodes with lambda functions for progress tracking")
        workflow.add_node("extract_skills", lambda state: self.skill_extractor.execute(state))
        workflow.add_node("generate_questions", lambda state: self.question_generator.execute(state))
        workflow.add_node("evaluate_questions", lambda state: self.question_evaluator.execute(state))
        workflow.add_node("generate_responses", lambda state: self.response_generator.execute(state))
        workflow.add_node("assemble_report", lambda state: self.report_assembler.execute(state))
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.add_edge(START, "extract_skills")
        self.logger.info("Workflow entry point set to skill extraction")
        
        # Define workflow transitions
        self.logger.info("Setting up workflow transitions and conditional routing")
        workflow.add_conditional_edges(
            "extract_skills",
            self._route_from_skill_extraction,
            {
                "generate_questions": "generate_questions",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_questions", 
            self._route_from_question_generation,
            {
                "evaluate_questions": "evaluate_questions",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "evaluate_questions",
            self._route_from_question_evaluation,
            {
                "generate_responses": "generate_responses",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_responses",
            self._route_from_response_generation,
            {
                "assemble_report": "assemble_report",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "assemble_report",
            self._route_from_report_assembly,
            {
                "complete": END,
                "error": "handle_error"
            }
        )
        
        # Error handling leads to END
        workflow.add_edge("handle_error", END)
        self.logger.info("Multi-agent workflow built successfully with lambda functions for progress tracking")
        
        return workflow