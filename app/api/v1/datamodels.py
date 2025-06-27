from pydantic import BaseModel, Field, validator, UUID4
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid

# Enum Models
class DocumentType(str, Enum):
    """Enum for document types"""
    JD = "jd"
    RESUME = "resume"

class ChangeType(str, Enum):
    """Enum for history change types"""
    CREATED = "created"
    UPDATED = "updated" 
    CHAT = "chat"

class RubricStatus(str, Enum):
    """Enum for rubric status"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"

# Base Models
class DocumentBase(BaseModel):
    """Base model for document metadata"""
    document_type: DocumentType
    
    class Config:
        orm_mode = True

class RubricBase(BaseModel):
    """Base model for rubric data"""
    
    class Config:
        orm_mode = True

class RubricHistoryBase(BaseModel):
    """Base model for rubric history entries"""
    change_type: ChangeType
    change_description: Optional[str] = None
    
    class Config:
        orm_mode = True

# Request Models

class TextUpload(BaseModel):
    """Model for uploading text content"""
    text: str
    document_type: DocumentType

class RubricCreate(RubricBase):
    """Model for creating a new rubric"""
    title: str
    description: Optional[str] = None
    jd_document_id: Optional[UUID4] = None
    resume_document_id: Optional[UUID4] = None
    
class RubricUpdate(BaseModel):
    """Model for updating an existing rubric"""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    status: Optional[RubricStatus] = None

class RubricChatRequest(BaseModel):
    """Model for chat-based rubric updates"""
    rubric_id: UUID4
    message: str

# Response Models
class DocumentResponse(DocumentBase):
    """Response model for document data"""
    doc_id: str
    original_filename: str
    
    class Config:
        orm_mode = True

class RubricHistoryResponse(RubricHistoryBase):
    """Response model for rubric history data"""
    id: str
    rubric_id: str
    content: Dict[str, Any]
    created_at: datetime
    
    class Config:
        orm_mode = True

class RubricResponse(RubricBase):
    """Response model for rubric data"""
    rubric_id: str
    title: str
    description: Optional[str] = None
    status: str
    jd_document_id: Optional[str] = None
    resume_document_id: Optional[str] = None
    content: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    jd_document: Optional[DocumentResponse] = None
    resume_document: Optional[DocumentResponse] = None
    
    class Config:
        orm_mode = True

class RubricListResponse(BaseModel):
    """Response model for listing rubrics"""
    items: List[RubricResponse]
    total: int
    page: int
    page_size: int
    
    class Config:
        orm_mode = True

class ExportLinkResponse(BaseModel):
    """Response model for export link"""
    link: str
    expires_at: Optional[datetime] = None

# Error Models
class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str
    status_code: int = 400
    
class ValidationErrorDetail(BaseModel):
    """Validation error detail"""
    loc: List[str]
    msg: str
    type: str

class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    detail: List[ValidationErrorDetail]
    status_code: int = 422

# Question Generation Models
class QuestionGenerationCreate(BaseModel):
    """Model for creating interview questions"""
    jd_document_id: Optional[str] = None
    resume_document_id: Optional[str] = None
    position_title: str = Field(..., description="Position title for the interview")
    llm_provider: Optional[str] = Field("openai", description="LLM provider to use")
    
class QuestionGenerationResponse(BaseModel):
    """Response model for question generation"""
    success: bool
    rubric_id: Optional[str] = None
    processing_time: float
    candidate_name: Optional[str] = None
    position_title: str
    input_scenario: str
    skills_identified: Optional[int] = None
    categories_covered: Optional[int] = None
    questions_generated: Optional[int] = None
    interview_duration_minutes: Optional[int] = None
    sections_created: Optional[int] = None
    key_strengths: Optional[List[str]] = None
    potential_concerns: Optional[List[str]] = None
    focus_areas: Optional[List[str]] = None
    overall_recommendation: Optional[str] = None
    formatted_report: Optional[str] = None
    evaluation_object: Optional[Dict[str, Any]] = None
    agent_performance: Optional[Dict[str, Any]] = None
    messages: Optional[List[str]] = None
    workflow_success: Optional[bool] = None
    error: Optional[str] = None

class QuickQuestionRequest(BaseModel):
    """Model for quick question generation from text"""
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    position_title: str = Field(..., description="Position title")
    llm_provider: Optional[str] = Field("openai", description="LLM provider to use")