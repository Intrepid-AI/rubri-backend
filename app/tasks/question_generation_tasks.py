import time
from datetime import datetime
from typing import Dict, Any, Optional
from celery import current_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db_ops.database import get_db_session
from app.db_ops import crud
from app.db_ops.models import TaskStatus
from app.api.v1.datamodels import DocumentType
from app.logger import get_logger
from app.tasks.progress_tracker import ProgressTracker
from app.tasks.email_tasks import send_completion_email

logger = get_logger(__name__)

class QuestionGenerationProgressTracker(ProgressTracker):
    """Progress tracker specifically for question generation workflow"""
    
    def __init__(self, task_id: str, db: Session):
        super().__init__(task_id, db, total_steps=5)
        self.agent_steps = [
            "Extracting Skills",
            "Generating Questions", 
            "Evaluating Questions",
            "Creating Guidance",
            "Finalizing Report"
        ]
    
    def update_agent_progress(self, agent_name: str, progress_within_agent: int = 100):
        """Update progress based on agent completion"""
        logger.info(f"DEBUG: update_agent_progress called with agent_name={agent_name}, progress_within_agent={progress_within_agent}")
        
        agent_mapping = {
            "SkillExtractionAgent": 0,
            "QuestionGenerationAgent": 1,
            "QuestionEvaluationAgent": 2,
            "ExpectedResponseAgent": 3,
            "ReportAssemblyAgent": 4
        }
        
        step_index = agent_mapping.get(agent_name)
        if step_index is not None:
            # Calculate overall progress: each agent is 20% of total
            overall_progress = (step_index * 20) + (progress_within_agent * 20 // 100)
            current_step = self.agent_steps[step_index]
            
            logger.info(f"DEBUG: Calculated overall_progress={overall_progress}, current_step={current_step}, step_number={step_index + 1}")
            
            self.update_progress(
                progress=min(overall_progress, 100),
                current_step=current_step,
                step_number=step_index + 1
            )
        else:
            logger.warning(f"DEBUG: Unknown agent_name '{agent_name}' in agent_mapping")

@celery_app.task(bind=True, name="question_generation_tasks.generate_interview_questions_async")
def generate_interview_questions_async(
    self,
    jd_document_id: Optional[str] = None,
    resume_document_id: Optional[str] = None,
    position_title: str = "Technical Position",
    llm_provider: str = "openai",
    user_email: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async task for generating interview questions using multi-agent system
    """
    task_id = self.request.id
    logger.info(f"Starting async question generation task {task_id} for position: {position_title}")
    
    db = None
    progress_tracker = None
    
    try:
        # Get database session and progress tracker
        db = get_db_session()
        progress_tracker = QuestionGenerationProgressTracker(task_id, db)
        
        # Immediately update task status to in_progress (record already exists from API)
        logger.info(f"Updating task {task_id} status to in_progress")
        progress_tracker.update_status_to_in_progress()
        
        # Give a moment for the status update to be committed
        time.sleep(0.1)
        
        progress_tracker.update_progress(
            progress=5,
            current_step="Starting question generation..."
        )
        
        # Get documents and validate
        resume_document = None
        jd_document = None
        resume_text = ""
        jd_text = ""
        
        if jd_document_id:
            jd_document = crud.get_document_by_type(
                db=db,
                document_id=jd_document_id,
                document_type=DocumentType.JD.value
            )
            if not jd_document:
                error_msg = f"JD document with ID {jd_document_id} not found"
                logger.error(error_msg)
                progress_tracker.fail_task(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "task_id": task_id
                }
            jd_text = jd_document.extracted_text or ""
        
        if resume_document_id:
            resume_document = crud.get_document_by_type(
                db=db,
                document_id=resume_document_id,
                document_type=DocumentType.RESUME.value
            )
            if not resume_document:
                error_msg = f"Resume document with ID {resume_document_id} not found"
                logger.error(error_msg)
                progress_tracker.fail_task(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "task_id": task_id
                }
            resume_text = resume_document.extracted_text or ""
        
        if not resume_text and not jd_text:
            raise ValueError("At least one document (JD or Resume) must be provided with extracted text")
        
        # Import and create multi-agent system
        from app.services.qgen.orchestrator.multi_agent_system import create_technical_interview_system
        from app.services.qgen.models.schemas import LLMProvider
        
        provider_mapping = {
            "openai": LLMProvider.OPENAI,
            "gemini": LLMProvider.GEMINI,
            "groq": LLMProvider.GROQ,
            "azure_openai": LLMProvider.AZURE_OPENAI,
            "portkey": LLMProvider.PORTKEY
        }
        
        llm_provider_enum = provider_mapping.get(llm_provider, LLMProvider.OPENAI)
        
        # Create interview system with progress tracking
        interview_system = _create_interview_system_with_progress_tracking(
            llm_provider_enum,
            "gpt-4o-mini" if llm_provider_enum == LLMProvider.OPENAI else "gemini-2.0-flash-001",
            progress_tracker
        )
        
        # Generate interview questions
        logger.info(f"Starting multi-agent interview generation for task {task_id}")
        result = interview_system.generate_technical_interview(
            resume_text=resume_text,
            job_description=jd_text,
            position_title=position_title,
            thread_id=f"async_{task_id}"
        )
        
        # Store result in database if successful
        rubric_id = None
        if result["success"]:
            try:
                db_rubric = crud.create_rubric(
                    db=db,
                    title=f"Async Interview Questions: {position_title}",
                    description=f"Generated interview questions and evaluation for {position_title}",
                    content={
                        "type": "async_interview_questions",
                        "evaluation": result.get("evaluation_object"),
                        "formatted_report": result.get("formatted_report"),
                        "agent_performance": result.get("agent_performance"),
                        "processing_time": result.get("processing_time"),
                        "input_scenario": result.get("input_scenario")
                    },
                    jd_document_id=jd_document.doc_id if jd_document else None,
                    resume_document_id=resume_document.doc_id if resume_document else None,
                    status="completed"
                )
                result["rubric_id"] = db_rubric.rubric_id
                rubric_id = db_rubric.rubric_id
                logger.info(f"Created rubric {rubric_id} for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to store question generation result in database: {e}")
        
        # Mark task as completed
        progress_tracker.complete_task(
            result_data=result,
            rubric_id=rubric_id
        )
        
        # Send email notification if requested
        if user_email and result["success"]:
            try:
                send_completion_email.delay(
                    user_email=user_email,
                    task_id=task_id,
                    position_title=position_title,
                    rubric_id=rubric_id,
                    result_summary={
                        "questions_generated": result.get("questions_generated", 0),
                        "interview_duration_minutes": result.get("interview_duration_minutes", 0),
                        "skills_identified": result.get("skills_identified", 0)
                    }
                )
                logger.info(f"Queued completion email for task {task_id} to {user_email}")
            except Exception as e:
                logger.error(f"Failed to queue completion email for task {task_id}: {e}")
        
        logger.info(f"Async question generation task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Error in async question generation: {str(e)}"
        logger.error(f"Task {task_id} failed: {error_msg}")
        
        # Mark task as failed - handle case where progress_tracker might not be initialized
        if progress_tracker:
            try:
                progress_tracker.fail_task(error_msg)
                logger.info(f"Task {task_id} marked as failed in database")
            except Exception as fail_error:
                logger.error(f"Failed to update task {task_id} status to failed: {fail_error}")
        else:
            # If progress tracker wasn't initialized, try to update status directly
            logger.warning(f"Progress tracker not initialized for task {task_id}, attempting direct status update")
            if db:
                try:
                    from app.db_ops.models import TaskStatus
                    task_status = db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
                    if task_status:
                        task_status.status = "failed"
                        task_status.error_message = error_msg
                        task_status.completed_at = datetime.utcnow()
                        db.commit()
                        logger.info(f"Task {task_id} status updated to failed directly")
                except Exception as direct_fail_error:
                    logger.error(f"Failed to directly update task {task_id} status: {direct_fail_error}")
        
        return {
            "success": False,
            "error": error_msg,
            "task_id": task_id
        }
    finally:
        if db:
            db.close()

@celery_app.task(bind=True, name="question_generation_tasks.generate_quick_questions_async")
def generate_quick_questions_async(
    self,
    resume_text: Optional[str] = None,
    job_description: Optional[str] = None,
    position_title: str = "Technical Position",
    llm_provider: str = "openai",
    user_email: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async task for generating quick interview questions from text
    """
    task_id = self.request.id
    logger.info(f"Starting async quick question generation task {task_id} for position: {position_title}")
    
    db = None
    progress_tracker = None
    
    try:
        # Get database session and progress tracker
        db = get_db_session()
        progress_tracker = QuestionGenerationProgressTracker(task_id, db)
        
        # Immediately update task status to in_progress (record already exists from API)
        logger.info(f"Updating task {task_id} status to in_progress")
        progress_tracker.update_status_to_in_progress()
        
        # Give a moment for the status update to be committed
        time.sleep(0.1)
        
        progress_tracker.update_progress(
            progress=5,
            current_step="Starting quick question generation..."
        )
        
        # Validate input
        if not resume_text and not job_description:
            raise ValueError("Either resume_text or job_description (or both) must be provided")
        
        # Import and create multi-agent system
        from app.services.qgen.orchestrator.multi_agent_system import create_technical_interview_system
        from app.services.qgen.models.schemas import LLMProvider
        
        provider_mapping = {
            "openai": LLMProvider.OPENAI,
            "gemini": LLMProvider.GEMINI,
            "groq": LLMProvider.GROQ,
            "azure_openai": LLMProvider.AZURE_OPENAI,
            "portkey": LLMProvider.PORTKEY
        }
        
        llm_provider_enum = provider_mapping.get(llm_provider, LLMProvider.GEMINI)
        
        # Create interview system with progress tracking
        interview_system = _create_interview_system_with_progress_tracking(
            llm_provider_enum,
            "gpt-4o-mini" if llm_provider_enum == LLMProvider.OPENAI else "gemini-2.0-flash-001",
            progress_tracker
        )
        
        # Generate interview questions
        logger.info(f"Starting multi-agent quick interview generation for task {task_id}")
        result = interview_system.generate_technical_interview(
            resume_text=resume_text or "",
            job_description=job_description or "",
            position_title=position_title,
            thread_id=f"quick_async_{task_id}"
        )
        
        # Store result in database if successful
        rubric_id = None
        if result["success"]:
            try:
                db_rubric = crud.create_rubric(
                    db=db,
                    title=f"Async Quick Interview Questions: {position_title}",
                    description=f"Generated interview questions from direct text input for {position_title}",
                    content={
                        "type": "async_quick_interview_questions",
                        "evaluation": result.get("evaluation_object"),
                        "formatted_report": result.get("formatted_report"),
                        "agent_performance": result.get("agent_performance"),
                        "processing_time": result.get("processing_time"),
                        "input_scenario": result.get("input_scenario"),
                        "input_texts": {
                            "resume_text": resume_text,
                            "job_description": job_description
                        }
                    },
                    status="completed"
                )
                result["rubric_id"] = db_rubric.rubric_id
                rubric_id = db_rubric.rubric_id
                logger.info(f"Created rubric {rubric_id} for quick task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to store quick question generation result in database: {e}")
        
        # Mark task as completed
        progress_tracker.complete_task(
            result_data=result,
            rubric_id=rubric_id
        )
        
        # Send email notification if requested
        if user_email and result["success"]:
            try:
                send_completion_email.delay(
                    user_email=user_email,
                    task_id=task_id,
                    position_title=position_title,
                    rubric_id=rubric_id,
                    result_summary={
                        "questions_generated": result.get("questions_generated", 0),
                        "interview_duration_minutes": result.get("interview_duration_minutes", 0),
                        "skills_identified": result.get("skills_identified", 0)
                    }
                )
                logger.info(f"Queued completion email for quick task {task_id} to {user_email}")
            except Exception as e:
                logger.error(f"Failed to queue completion email for quick task {task_id}: {e}")
        
        logger.info(f"Async quick question generation task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Error in async quick question generation: {str(e)}"
        logger.error(f"Quick task {task_id} failed: {error_msg}")
        
        # Mark task as failed - handle case where progress_tracker might not be initialized
        if progress_tracker:
            try:
                progress_tracker.fail_task(error_msg)
                logger.info(f"Quick task {task_id} marked as failed in database")
            except Exception as fail_error:
                logger.error(f"Failed to update quick task {task_id} status to failed: {fail_error}")
        else:
            # If progress tracker wasn't initialized, try to update status directly
            logger.warning(f"Progress tracker not initialized for quick task {task_id}, attempting direct status update")
            if db:
                try:
                    from app.db_ops.models import TaskStatus
                    task_status = db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
                    if task_status:
                        task_status.status = "failed"
                        task_status.error_message = error_msg
                        task_status.completed_at = datetime.utcnow()
                        db.commit()
                        logger.info(f"Quick task {task_id} status updated to failed directly")
                except Exception as direct_fail_error:
                    logger.error(f"Failed to directly update quick task {task_id} status: {direct_fail_error}")
        
        return {
            "success": False,
            "error": error_msg,
            "task_id": task_id
        }
    finally:
        if db:
            db.close()

def _create_interview_system_with_progress_tracking(llm_provider, llm_model, progress_tracker):
    """
    Create interview system and integrate progress tracking from the start
    """
    logger.info("DEBUG: Creating interview system with integrated progress tracking")
    
    from app.services.qgen.orchestrator.multi_agent_system import _create_interview_system_with_progress_patching
    from app.services.qgen.models.schemas import LLMConfig
    
    # Create LLM config
    llm_config = LLMConfig(
        provider=llm_provider,
        model=llm_model,
        temperature=0.1
    )
    
    # Create the system with progress tracking integrated during initialization
    system = _create_interview_system_with_progress_patching(llm_config, progress_tracker)
    
    return system

def _patch_agents_with_progress_tracking(interview_system, progress_tracker):
    """
    Patch the agents to include progress tracking
    """
    logger.info("DEBUG: Patching agents with progress tracking")
    
    agents = [
        (interview_system.skill_extractor, "SkillExtractionAgent"),
        (interview_system.question_generator, "QuestionGenerationAgent"),
        (interview_system.question_evaluator, "QuestionEvaluationAgent"),
        (interview_system.response_generator, "ExpectedResponseAgent"),
        (interview_system.report_assembler, "ReportAssemblyAgent")
    ]
    
    for agent, agent_name in agents:
        logger.info(f"DEBUG: Patching {agent_name} execute method")
        original_execute = agent.execute
        
        def create_wrapped_execute(original_method, name):
            def wrapped_execute(state):
                logger.info(f"DEBUG: Starting agent: {name}")
                progress_tracker.update_agent_progress(name, 0)
                
                try:
                    result = original_method(state)
                    progress_tracker.update_agent_progress(name, 100)
                    logger.info(f"DEBUG: Completed agent: {name}")
                    return result
                except Exception as e:
                    logger.error(f"Agent {name} failed: {str(e)}")
                    raise
            
            return wrapped_execute
        
        # Replace the execute method
        agent.execute = create_wrapped_execute(original_execute, agent_name)
        logger.info(f"DEBUG: Successfully patched {agent_name}")
    
    logger.info("DEBUG: Finished patching all agents")

def _patch_interview_system_for_progress(interview_system, progress_tracker):
    """
    Patch the interview system to report progress via the progress tracker
    """
    logger.info("DEBUG: Starting to patch interview system for progress tracking")
    
    # Store original execute methods
    original_execute_methods = {}
    
    agents = [
        interview_system.skill_extractor,
        interview_system.question_generator,
        interview_system.question_evaluator,
        interview_system.response_generator,
        interview_system.report_assembler
    ]
    
    agent_names = [
        "SkillExtractionAgent",
        "QuestionGenerationAgent", 
        "QuestionEvaluationAgent",
        "ExpectedResponseAgent",
        "ReportAssemblyAgent"
    ]
    
    # Wrap each agent's execute method to report progress
    for agent, agent_name in zip(agents, agent_names):
        logger.info(f"DEBUG: Patching agent {agent_name}, original execute: {agent.execute}")
        original_execute = agent.execute
        
        def create_wrapped_execute(original_method, name):
            def wrapped_execute(state):
                logger.info(f"DEBUG: Starting agent: {name}")
                progress_tracker.update_agent_progress(name, 0)
                
                try:
                    result = original_method(state)
                    progress_tracker.update_agent_progress(name, 100)
                    logger.info(f"DEBUG: Completed agent: {name}")
                    return result
                except Exception as e:
                    logger.error(f"Agent {name} failed: {str(e)}")
                    raise
            
            return wrapped_execute
        
        agent.execute = create_wrapped_execute(original_execute, agent_name)
        logger.info(f"DEBUG: Patched agent {agent_name}, new execute: {agent.execute}")
    
    logger.info("DEBUG: Finished patching all agents for progress tracking")