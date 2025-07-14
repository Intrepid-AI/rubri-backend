from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from app.api.v1.datamodels import (
    DocumentType, DocumentResponse, TextUpload,
    RubricCreate, RubricUpdate, RubricResponse, RubricChatRequest,
    RubricListResponse, ExportLinkResponse, ErrorResponse,
    QuestionGenerationCreate, QuestionGenerationResponse, QuickQuestionRequest,
    AsyncQuestionGenerationRequest, AsyncQuickQuestionRequest,
    TaskStatusResponse, TaskInitiationResponse, TaskStatusEnum
)

from app.constants import Constants
from app.logger import get_logger
from app.db_ops.database import get_db
from app.db_ops import crud
from app.db_ops.models import TaskStatus
from app.db_ops.db_config import load_app_config
from app.services.file_upload_ops import _process_file_upload, _process_text_upload
# from app.services.llm_rubric_ops import RubricGenerator
from app.services.mock_response_service import mock_response_service
from app.auth.dependencies import get_optional_user, require_auth
from app.api.v1.auth_routes import router as auth_router

# Initialize router
router = APIRouter()

# Include auth routes
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Initialize logger
logger = get_logger(__name__)

# Upload Routes
@router.post("/upload/file/jd", response_model=DocumentResponse, tags=["Upload"])
async def upload_jd_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Upload a job description file (PDF, Text, Word)
    
    This endpoint allows uploading a job description document in various formats.
    The text will be extracted from the document in the background.
    """
    return await _process_file_upload(
        file=file,
        document_type=DocumentType.JD,
        background_tasks=background_tasks,
        db=db
    )

@router.post("/upload/file/resume", response_model=DocumentResponse, tags=["Upload"])
async def upload_resume_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Upload a resume file (PDF, Text, Word)
    
    This endpoint allows uploading a resume document in various formats.
    The text will be extracted from the document in the background.
    """
    return await _process_file_upload(
        file=file,
        document_type=DocumentType.RESUME,
        background_tasks=background_tasks,
        db=db
    )

@router.post("/upload/text/jd", response_model=DocumentResponse, tags=["Upload"])
async def upload_jd_text(
    text_upload: TextUpload,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Upload job description as plain text
    
    This endpoint allows uploading a job description as plain text.
    """
    return await _process_text_upload(
        text=text_upload.text,
        document_type=DocumentType.JD,
        db=db
    )

@router.post("/upload/text/resume", response_model=DocumentResponse, tags=["Upload"])
async def upload_resume_text(
    text_upload: TextUpload,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Upload resume as plain text
    
    This endpoint allows uploading a resume as plain text.
    """
    return await _process_text_upload(
        text=text_upload.text,
        document_type=DocumentType.RESUME,
        db=db
    )

# Rubric Routes
@router.post("/rubric/create", tags=["Rubric"])
async def create_rubric(
    rubric_create: RubricCreate,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new rubric based on JD and/or resume
    
    This endpoint generates an evaluation rubric based on the provided
    job description and/or resume documents.
    """

    resume_document = None
    
    if not rubric_create.jd_document_id:
        raise HTTPException(
            status_code=400,
            detail="JD document ID must be provided"
            )
    
    jd_document = crud.get_document_by_type(
        db=db,
        document_id=rubric_create.jd_document_id,
        document_type=DocumentType.JD.value
    )
        
    if not jd_document:
        raise HTTPException(
            status_code=404,
            detail=f"JD document with ID {rubric_create.jd_document_id} not found"
        )
    
    if rubric_create.resume_document_id:
        resume_document = crud.get_document_by_type(
            db=db,
            document_id=rubric_create.resume_document_id,
            document_type=DocumentType.RESUME.value
        )
        
        if not resume_document:
            raise HTTPException(
                status_code=404,
                detail=f"Resume document with ID {rubric_create.resume_document_id} not found"
            )
    
    # Extract text from documents
    jd_text = jd_document.extracted_text
    resume_text = resume_document.extracted_text if resume_document else None
    
    rubric_generator = RubricGenerator(db=db)
    dict_result_rubric = rubric_generator.generate_rubric(jd_text=jd_text, 
                                                          resume_text=resume_text)


    # TODO: Generate rubric using LLM
    # For now, create a mock rubric
    # mock_content = {
    #     "title": f"Evaluation Rubric for {rubric_create.title}",
    #     "sections": [
    #         {
    #             "name": "Technical Skills",
    #             "items": [
    #                 {
    #                     "skill": "Example Skill",
    #                     "description": "Description of the skill",
    #                     "scoring_criteria": {
    #                         "1": "Poor - Description",
    #                         "2": "Below Average - Description",
    #                         "3": "Average - Description",
    #                         "4": "Above Average - Description",
    #                         "5": "Excellent - Description"
    #                     },
    #                     "sample_questions": [
    #                         "Example question 1?",
    #                         "Example question 2?"
    #                     ]
    #                 }
    #             ]
    #         }
    #     ]
    # }
    
    # Create rubric record using CRUD operation
    # db_rubric = crud.create_rubric(
    #     db=db,
    #     title=rubric_create.title,
    #     description=rubric_create.description,
    #     content=mock_content,
    #     jd_document_id=jd_document.id if jd_document else None,
    #     resume_document_id=resume_document.id if resume_document else None,
    #     status=RubricStatus.DRAFT.value
    # )
    import pprint
    pprint.pprint(dict_result_rubric, indent=2)
    return dict_result_rubric


# Question Generation Routes
@router.post("/questions/generate", response_model=QuestionGenerationResponse, tags=["Questions"])
async def generate_interview_questions(
    question_request: QuestionGenerationCreate,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive interview questions using multi-agent system
    
    This endpoint uses the uploaded documents to generate a complete
    interview evaluation with technical questions, expected responses,
    and interviewer guidance.
    """
    try:
        # Check if mock responses are enabled in development
        app_config = load_app_config()
        use_mock_responses = app_config.get("development", {}).get("use_mock_responses", False)
        
        if use_mock_responses:
            logger.info("Using mock response for development")
            
            # Determine input scenario based on provided documents
            input_scenario = "mock"
            if question_request.jd_document_id and question_request.resume_document_id:
                input_scenario = "both"
            elif question_request.jd_document_id:
                input_scenario = "jd_only"
            elif question_request.resume_document_id:
                input_scenario = "resume_only"
            
            # Get mock response
            mock_result = mock_response_service.get_mock_question_response(
                position_title=question_request.position_title,
                input_scenario=input_scenario,
                jd_document_id=question_request.jd_document_id,
                resume_document_id=question_request.resume_document_id
            )
            
            # Store mock result in database if successful
            if mock_result.get("success", True):
                try:
                    # Get documents for database storage (if they exist)
                    resume_document = None
                    jd_document = None
                    
                    if question_request.jd_document_id:
                        jd_document = crud.get_document_by_type(
                            db=db,
                            document_id=question_request.jd_document_id,
                            document_type=DocumentType.JD.value
                        )
                    
                    if question_request.resume_document_id:
                        resume_document = crud.get_document_by_type(
                            db=db,
                            document_id=question_request.resume_document_id,
                            document_type=DocumentType.RESUME.value
                        )
                    
                    # Create rubric record with mock results
                    db_rubric = crud.create_rubric(
                        db=db,
                        title=f"Mock Interview Questions: {question_request.position_title}",
                        description=f"Mock generated interview questions for development: {question_request.position_title}",
                        content={
                            "type": "mock_interview_questions",
                            "evaluation": mock_result.get("evaluation_object"),
                            "formatted_report": mock_result.get("formatted_report"),
                            "agent_performance": mock_result.get("agent_performance"),
                            "processing_time": mock_result.get("processing_time"),
                            "input_scenario": mock_result.get("input_scenario")
                        },
                        jd_document_id=jd_document.doc_id if jd_document else None,
                        resume_document_id=resume_document.doc_id if resume_document else None,
                        status="completed"
                    )
                    mock_result["rubric_id"] = db_rubric.rubric_id
                except Exception as e:
                    logger.warning(f"Failed to store mock question generation result in database: {e}")
            
            return QuestionGenerationResponse(**mock_result)
        
        # Continue with normal processing if mock responses are disabled
        # Import here to avoid circular imports
        from app.services.qgen.orchestrator.multi_agent_system import create_technical_interview_system
        from app.services.qgen.models.schemas import LLMProvider
        
        # Get documents
        resume_document = None
        jd_document = None
        resume_text = ""
        jd_text = ""
        
        if question_request.jd_document_id:
            jd_document = crud.get_document_by_type(
                db=db,
                document_id=question_request.jd_document_id,
                document_type=DocumentType.JD.value
            )
            if not jd_document:
                raise HTTPException(
                    status_code=404,
                    detail=f"JD document with ID {question_request.jd_document_id} not found"
                )
            jd_text = jd_document.extracted_text or ""
        
        if question_request.resume_document_id:
            resume_document = crud.get_document_by_type(
                db=db,
                document_id=question_request.resume_document_id,
                document_type=DocumentType.RESUME.value
            )
            if not resume_document:
                raise HTTPException(
                    status_code=404,
                    detail=f"Resume document with ID {question_request.resume_document_id} not found"
                )
            resume_text = resume_document.extracted_text or ""
        
        if not resume_text and not jd_text:
            raise HTTPException(
                status_code=400,
                detail="At least one document (JD or Resume) must be provided with extracted text"
            )
        
        # Map LLM provider
        provider_mapping = {
            "openai": LLMProvider.OPENAI,
            "gemini": LLMProvider.GEMINI,
            "groq": LLMProvider.GROQ,
            "azure_openai": LLMProvider.AZURE_OPENAI,
            "portkey": LLMProvider.PORTKEY
        }
        
        llm_provider = provider_mapping.get(question_request.llm_provider, LLMProvider.OPENAI)
        
        # Create multi-agent system
        interview_system = create_technical_interview_system(
            llm_provider=llm_provider,
            llm_model="gpt-4.1" if llm_provider == LLMProvider.OPENAI else "gemini-2.0-flash-001"
        )
        
        # Generate interview questions
        result = interview_system.generate_technical_interview(
            resume_text=resume_text,
            job_description=jd_text,
            position_title=question_request.position_title,
            thread_id=f"api_{question_request.jd_document_id or question_request.resume_document_id}"
        )
        
        # Store result in database if successful
        if result["success"]:
            try:
                # Create rubric record with question generation results
                db_rubric = crud.create_rubric(
                    db=db,
                    title=f"Interview Questions: {question_request.position_title}",
                    description=f"Generated interview questions and evaluation for {question_request.position_title}",
                    content={
                        "type": "interview_questions",
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
            except Exception as e:
                logger.warning(f"Failed to store question generation result in database: {e}")
        
        return QuestionGenerationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error generating interview questions: {str(e)}")
        return QuestionGenerationResponse(
            success=False,
            processing_time=0,
            position_title=question_request.position_title,
            input_scenario="error",
            error=str(e)
        )





@router.post("/questions/generate/quick", response_model=QuestionGenerationResponse, tags=["Questions"])
async def generate_quick_questions(
    quick_request: QuickQuestionRequest,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate interview questions from raw text (without uploading files)
    
    This endpoint allows direct text input for quick question generation
    without requiring file uploads.
    """
    try:
        # Check if mock responses are enabled in development
        app_config = load_app_config()
        use_mock_responses = app_config.get("development", {}).get("use_mock_responses", False)
        
        if use_mock_responses:
            logger.info("Using mock response for quick question generation in development")
            
            # Determine input scenario based on provided text
            input_scenario = "quick_mock"
            if quick_request.resume_text and quick_request.job_description:
                input_scenario = "quick_both"
            elif quick_request.job_description:
                input_scenario = "quick_jd_only"
            elif quick_request.resume_text:
                input_scenario = "quick_resume_only"
            
            # Get mock response
            mock_result = mock_response_service.get_mock_question_response(
                position_title=quick_request.position_title,
                input_scenario=input_scenario
            )
            
            # Store mock result in database if successful
            if mock_result.get("success", True):
                try:
                    # Create rubric record with mock results
                    db_rubric = crud.create_rubric(
                        db=db,
                        title=f"Mock Quick Interview Questions: {quick_request.position_title}",
                        description=f"Mock generated interview questions from direct text input for development: {quick_request.position_title}",
                        content={
                            "type": "mock_quick_interview_questions",
                            "evaluation": mock_result.get("evaluation_object"),
                            "formatted_report": mock_result.get("formatted_report"),
                            "agent_performance": mock_result.get("agent_performance"),
                            "processing_time": mock_result.get("processing_time"),
                            "input_scenario": mock_result.get("input_scenario"),
                            "input_texts": {
                                "resume_text": quick_request.resume_text,
                                "job_description": quick_request.job_description
                            }
                        },
                        status="completed"
                    )
                    mock_result["rubric_id"] = db_rubric.rubric_id
                except Exception as e:
                    logger.warning(f"Failed to store mock quick question generation result in database: {e}")
            
            return QuestionGenerationResponse(**mock_result)
        
        # Continue with normal processing if mock responses are disabled
        # Import here to avoid circular imports
        from app.services.qgen.orchestrator.multi_agent_system import create_technical_interview_system
        from app.services.qgen.models.schemas import LLMProvider
        
        # Validate input
        if not quick_request.resume_text and not quick_request.job_description:
            raise HTTPException(
                status_code=400,
                detail="Either resume_text or job_description (or both) must be provided"
            )
        
        # Map LLM provider
        provider_mapping = {
            "openai": LLMProvider.OPENAI,
            "gemini": LLMProvider.GEMINI,
            "groq": LLMProvider.GROQ,
            "azure_openai": LLMProvider.AZURE_OPENAI,
            "portkey": LLMProvider.PORTKEY
        }
        
        llm_provider = provider_mapping.get(quick_request.llm_provider, LLMProvider.GEMINI)
        
        # Create multi-agent system
        interview_system = create_technical_interview_system(
            llm_provider=llm_provider,
            llm_model="gpt-4o-mini" if llm_provider == LLMProvider.OPENAI else "gemini-2.0-flash-001"
        )
        
        # Generate interview questions
        result = interview_system.generate_technical_interview(
            resume_text=quick_request.resume_text or "",
            job_description=quick_request.job_description or "",
            position_title=quick_request.position_title,
            thread_id=f"quick_{hash(str(quick_request.resume_text) + str(quick_request.job_description)) % 10000}"
        )
        
        # Store result in database if successful
        if result["success"]:
            try:
                # Create rubric record with question generation results
                db_rubric = crud.create_rubric(
                    db=db,
                    title=f"Quick Interview Questions: {quick_request.position_title}",
                    description=f"Generated interview questions from direct text input for {quick_request.position_title}",
                    content={
                        "type": "quick_interview_questions",
                        "evaluation": result.get("evaluation_object"),
                        "formatted_report": result.get("formatted_report"),
                        "agent_performance": result.get("agent_performance"),
                        "processing_time": result.get("processing_time"),
                        "input_scenario": result.get("input_scenario"),
                        "input_texts": {
                            "resume_text": quick_request.resume_text,
                            "job_description": quick_request.job_description
                        }
                    },
                    status="completed"
                )
                result["rubric_id"] = db_rubric.rubric_id
            except Exception as e:
                logger.warning(f"Failed to store quick question generation result in database: {e}")
        
        return QuestionGenerationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error generating quick interview questions: {str(e)}")
        return QuestionGenerationResponse(
            success=False,
            processing_time=0,
            position_title=quick_request.position_title,
            input_scenario="error",
            error=str(e)
        )

@router.post("/rubric/chat", response_model=RubricResponse, tags=["Rubric"])
async def chat_with_rubric(
    chat_request: RubricChatRequest,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update rubric through chat with LLM
    
    This endpoint allows updating a rubric through a chat-like interaction
    with an LLM. The user can provide feedback or requests, and the LLM
    will update the rubric accordingly.
    """
    # Retrieve the rubric
    db_rubric = crud.get_rubric(db, chat_request.rubric_id)
    
    if not db_rubric:
        raise HTTPException(
            status_code=404,
            detail=f"Rubric with ID {chat_request.rubric_id} not found"
        )
    
    # TODO: Update rubric using LLM
    # For now, just update the rubric with a mock change
    current_content = db_rubric.content
    
    # Make a simple change to the content
    if "sections" in current_content and len(current_content["sections"]) > 0:
        section = current_content["sections"][0]
        if "items" in section and len(section["items"]) > 0:
            item = section["items"][0]
            item["description"] = f"Updated based on chat: {chat_request.message}"
    
    # Update the rubric using CRUD operation
    updated_rubric = crud.update_rubric_via_chat(
        db=db,
        rubric_id=chat_request.rubric_id,
        content=current_content
    )
    
    return updated_rubric

@router.put("/rubric/edit/{rubric_id}", response_model=RubricResponse, tags=["Rubric"])
async def edit_rubric(
    rubric_update: RubricUpdate,
    rubric_id: str = Path(..., description="The ID of the rubric to edit"),
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Edit rubric directly
    
    This endpoint allows direct editing of a rubric's content and metadata.
    """
    # Update the rubric using CRUD operation
    updated_rubric = crud.update_rubric(
        db=db,
        rubric_id=rubric_id,
        content=rubric_update.content,
        status=rubric_update.status.value if rubric_update.status else None,
        change_description="Manual edit"
    )
    
    if not updated_rubric:
        raise HTTPException(
            status_code=404,
            detail=f"Rubric with ID {rubric_id} not found"
        )
    
    return updated_rubric

@router.get("/rubric/export/link/{rubric_id}", response_model=ExportLinkResponse, tags=["Rubric"])
async def export_rubric_link(
    rubric_id: str = Path(..., description="The ID of the rubric to export"),
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate shareable link for rubric
    
    This endpoint generates a shareable link for a rubric that can be
    accessed without authentication.
    """
    # Check if rubric exists
    db_rubric = crud.get_rubric(db, rubric_id)
    
    if not db_rubric:
        raise HTTPException(
            status_code=404,
            detail=f"Rubric with ID {rubric_id} not found"
        )
    
    # Create a shared link using CRUD operation
    expires_at = datetime.utcnow().replace(hour=23, minute=59, second=59)
    db_link = crud.create_shared_link(
        db=db,
        rubric_id=rubric_id,
        expires_at=expires_at
    )
    
    # Generate the link
    link = f"/shared/rubric/{rubric_id}?token={db_link.token}"
    
    return {
        "link": link,
        "expires_at": expires_at
    }

@router.get("/rubric/export/pdf/{rubric_id}", tags=["Rubric"])
async def export_rubric_pdf(
    rubric_id: str = Path(..., description="The ID of the rubric to export"),
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Export rubric as PDF
    
    This endpoint generates a PDF version of a rubric and returns it
    as a downloadable file.
    """
    # Check if rubric exists
    db_rubric = crud.get_rubric(db, rubric_id)
    
    if not db_rubric:
        raise HTTPException(
            status_code=404,
            detail=f"Rubric with ID {rubric_id} not found"
        )
    
    # TODO: Generate PDF
    # For now, return a mock response
    return JSONResponse(
        content={"detail": "PDF export not implemented yet"},
        status_code=501
    )

# Async Question Generation Routes
@router.post("/questions/generate/async", response_model=TaskInitiationResponse, tags=["Questions"])
async def start_async_question_generation(
    question_request: AsyncQuestionGenerationRequest,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Start async interview question generation with real-time progress updates
    
    This endpoint starts a background task for comprehensive interview question generation.
    Returns a task ID that can be used to track progress via WebSocket connection.
    """
    try:
        # Import Celery task
        from app.tasks.question_generation_tasks import generate_interview_questions_async
        
        # Validate documents exist if provided
        if question_request.jd_document_id:
            jd_document = crud.get_document_by_type(
                db=db,
                document_id=question_request.jd_document_id,
                document_type=DocumentType.JD.value
            )
            if not jd_document:
                raise HTTPException(
                    status_code=404,
                    detail=f"JD document with ID {question_request.jd_document_id} not found"
                )
        
        if question_request.resume_document_id:
            resume_document = crud.get_document_by_type(
                db=db,
                document_id=question_request.resume_document_id,
                document_type=DocumentType.RESUME.value
            )
            if not resume_document:
                raise HTTPException(
                    status_code=404,
                    detail=f"Resume document with ID {question_request.resume_document_id} not found"
                )
        
        if not question_request.jd_document_id and not question_request.resume_document_id:
            raise HTTPException(
                status_code=400,
                detail="At least one document (JD or Resume) must be provided"
            )
        
        # Determine user email for notifications
        user_email = None
        user_id = None
        if current_user:
            user_id = current_user.user_id
            # Use authenticated user's email if notifications are enabled
            if current_user.email_notifications_enabled == "true":
                user_email = current_user.email
                logger.info(f"Using authenticated user email for notifications: {user_email}")
        elif question_request.user_email:
            # Fallback to provided email if user not authenticated
            user_email = question_request.user_email
            logger.info(f"Using provided email for notifications: {user_email}")
        
        # Generate task ID and create database record BEFORE starting Celery task
        task_id = str(uuid.uuid4())
        
        # Create task status record in database immediately
        task_status = TaskStatus(
            task_id=task_id,
            task_type="question_generation",
            status="pending",
            progress=0,
            current_step="Initializing...",
            total_steps=5,
            user_id=user_id,
            user_email=user_email,
            position_title=question_request.position_title,
            request_data={
                "jd_document_id": question_request.jd_document_id,
                "resume_document_id": question_request.resume_document_id,
                "llm_provider": question_request.llm_provider
            },
            started_at=datetime.utcnow()
        )
        
        db.add(task_status)
        db.commit()
        db.refresh(task_status)  # Ensure the object is fully synchronized
        
        logger.info(f"Created task record in database for task {task_id} with status: {task_status.status}")
        
        # Start async task with pre-generated task ID
        task = generate_interview_questions_async.apply_async(
            args=[
                question_request.jd_document_id,
                question_request.resume_document_id,
                question_request.position_title,
                question_request.llm_provider,
                user_email,
                user_id
            ],
            task_id=task_id
        )
        
        logger.info(f"Started async question generation task {task.id} for position: {question_request.position_title}")
        
        return TaskInitiationResponse(
            task_id=task.id,
            status=TaskStatusEnum.PENDING,
            message=f"Interview question generation started for {question_request.position_title}",
            estimated_duration_minutes=15,
            websocket_endpoint=f"/ws/progress/{task.id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting async question generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start question generation: {str(e)}"
        )

@router.post("/questions/generate/quick/async", response_model=TaskInitiationResponse, tags=["Questions"])
async def start_async_quick_question_generation(
    quick_request: AsyncQuickQuestionRequest,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Start async quick question generation from text with real-time progress updates
    
    This endpoint starts a background task for quick interview question generation
    from raw text input without requiring file uploads.
    """
    try:
        # Import Celery task
        from app.tasks.question_generation_tasks import generate_quick_questions_async
        
        # Validate input
        if not quick_request.resume_text and not quick_request.job_description:
            raise HTTPException(
                status_code=400,
                detail="Either resume_text or job_description (or both) must be provided"
            )
        
        # Determine user email for notifications
        user_email = None
        user_id = None
        if current_user:
            user_id = current_user.user_id
            # Use authenticated user's email if notifications are enabled
            if current_user.email_notifications_enabled == "true":
                user_email = current_user.email
                logger.info(f"Using authenticated user email for notifications: {user_email}")
        elif quick_request.user_email:
            # Fallback to provided email if user not authenticated
            user_email = quick_request.user_email
            logger.info(f"Using provided email for notifications: {user_email}")
        
        # Generate task ID and create database record BEFORE starting Celery task
        task_id = str(uuid.uuid4())
        
        # Create task status record in database immediately
        task_status = TaskStatus(
            task_id=task_id,
            task_type="quick_question_generation",
            status="pending",
            progress=0,
            current_step="Initializing...",
            total_steps=5,
            user_id=user_id,
            user_email=user_email,
            position_title=quick_request.position_title,
            request_data={
                "resume_text": quick_request.resume_text,
                "job_description": quick_request.job_description,
                "llm_provider": quick_request.llm_provider
            },
            started_at=datetime.utcnow()
        )
        
        db.add(task_status)
        db.commit()
        db.refresh(task_status)  # Ensure the object is fully synchronized
        
        logger.info(f"Created task record in database for task {task_id} with status: {task_status.status}")
        
        # Start async task with pre-generated task ID
        task = generate_quick_questions_async.apply_async(
            args=[
                quick_request.resume_text,
                quick_request.job_description,
                quick_request.position_title,
                quick_request.llm_provider,
                user_email,
                user_id
            ],
            task_id=task_id
        )
        
        logger.info(f"Started async quick question generation task {task.id} for position: {quick_request.position_title}")
        
        return TaskInitiationResponse(
            task_id=task.id,
            status=TaskStatusEnum.PENDING,
            message=f"Quick interview question generation started for {quick_request.position_title}",
            estimated_duration_minutes=10,
            websocket_endpoint=f"/ws/progress/{task.id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting async quick question generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start quick question generation: {str(e)}"
        )

@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse, tags=["Tasks"])
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the current status of an async task
    
    This endpoint returns the current progress and status of a background task.
    """
    task_status = crud.get_task_status(db, task_id)
    
    if not task_status:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )
    
    return TaskStatusResponse(
        task_id=task_status.task_id,
        task_type=task_status.task_type,
        status=TaskStatusEnum(task_status.status),
        progress=task_status.progress,
        current_step=task_status.current_step,
        total_steps=task_status.total_steps,
        position_title=task_status.position_title,
        started_at=task_status.started_at,
        completed_at=task_status.completed_at,
        created_at=task_status.created_at,
        result_data=task_status.result_data,
        error_message=task_status.error_message,
        rubric_id=task_status.rubric_id
    )

@router.get("/tasks", tags=["Tasks"])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of tasks to return"),
    db: Session = Depends(get_db)
):
    """
    List async tasks with optional filtering
    
    This endpoint returns a list of background tasks with their current status.
    """
    tasks = crud.list_task_statuses(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        task_type=task_type
    )
    
    return {
        "items": [
            TaskStatusResponse(
                task_id=task.task_id,
                task_type=task.task_type,
                status=TaskStatusEnum(task.status),
                progress=task.progress,
                current_step=task.current_step,
                total_steps=task.total_steps,
                position_title=task.position_title,
                started_at=task.started_at,
                completed_at=task.completed_at,
                created_at=task.created_at,
                result_data=task.result_data,
                error_message=task.error_message,
                rubric_id=task.rubric_id
            ) for task in tasks
        ],
        "total": len(tasks),
        "skip": skip,
        "limit": limit
    }

@router.get("/rubric/list", response_model=RubricListResponse, tags=["Rubric"])
async def list_rubrics(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    List all rubrics
    
    This endpoint returns a paginated list of rubrics with optional filtering.
    """
    # Calculate skip value for pagination
    skip = (page - 1) * page_size
    
    # Get rubrics using CRUD operation
    result = crud.list_rubrics(
        db=db,
        skip=skip,
        limit=page_size
    )
    
    return result