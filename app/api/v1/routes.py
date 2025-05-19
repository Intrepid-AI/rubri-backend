from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.api.v1.datamodels import (
    DocumentType, DocumentResponse, TextUpload,
    RubricCreate, RubricUpdate, RubricResponse, RubricChatRequest,
    RubricListResponse, ExportLinkResponse, ErrorResponse
)

from app.constants import Constants
from app.logger import get_logger
from app.db_ops.database import get_db
from app.db_ops import crud
from app.services.file_upload_ops import _process_file_upload, _process_text_upload
from app.services.llm_rubric_ops import RubricGenerator

# Initialize router
router = APIRouter()

# Initialize logger
logger = get_logger(__name__)

# Upload Routes
@router.post("/upload/file/jd", response_model=DocumentResponse, tags=["Upload"])
async def upload_jd_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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

@router.post("/rubric/chat", response_model=RubricResponse, tags=["Rubric"])
async def chat_with_rubric(
    chat_request: RubricChatRequest,
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

@router.get("/rubric/list", response_model=RubricListResponse, tags=["Rubric"])
async def list_rubrics(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
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