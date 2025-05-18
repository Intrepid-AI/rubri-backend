from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid

# Enum Models
class DocumentType(str, Enum):
    """Enum for document types"""
    JD = "jd"
    RESUME = "resume"

class RubricStatus(str, Enum):
    """Enum for rubric statuses"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ChangeType(str, Enum):
    """Enum for history change types"""
    CREATED = "created"
    UPDATED = "updated"
    CHAT = "chat"

# Base Models
class DocumentBase(BaseModel):
    """Base model for document metadata"""
    document_type: DocumentType
    
    class Config:
        orm_mode = True

class RubricBase(BaseModel):
    """Base model for rubric data"""
    title: str
    description: Optional[str] = None
    
    class Config:
        orm_mode = True

class RubricHistoryBase(BaseModel):
    """Base model for rubric history entries"""
    change_type: ChangeType
    change_description: Optional[str] = None
    
    class Config:
        orm_mode = True

# Request Models
class DocumentCreate(BaseModel):
    """Model for creating a new document"""
    document_type: DocumentType
    file_path: Optional[str] = None
    text_content: Optional[str] = None
    
    class Config:
        orm_mode = True

class TextUpload(BaseModel):
    """Model for uploading text content"""
    text: str
    document_type: DocumentType

class RubricCreate(RubricBase):
    """Model for creating a new rubric"""
    jd_document_id: Optional[str] = None
    resume_document_id: Optional[str] = None
    
    @validator('jd_document_id', 'resume_document_id', pre=True)
    def validate_uuid(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError('Invalid UUID format')
        return v

class RubricUpdate(BaseModel):
    """Model for updating an existing rubric"""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    status: Optional[RubricStatus] = None

class RubricChatRequest(BaseModel):
    """Model for chat-based rubric updates"""
    rubric_id: str
    message: str
    
    @validator('rubric_id', pre=True)
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid UUID format')
        return v

# Response Models
class DocumentResponse(DocumentBase):
    """Response model for document data"""
    id: str
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
    id: str
    jd_document_id: Optional[str] = None
    resume_document_id: Optional[str] = None
    content: Dict[str, Any]
    status: RubricStatus
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

# Legacy models for backward compatibility
class DocumentRead(BaseModel):
    """Legacy model for reading documents"""
    id: int
    file_path: str
    text_content: str
    
    class Config:
        orm_mode = True

class RubricRead(BaseModel):
    """Legacy model for reading rubrics"""
    id: int
    document_id: int
    rubric_content: str
    
    class Config:
        orm_mode = True

class RubricHistoryRead(BaseModel):
    """Legacy model for reading rubric history"""
    id: int
    rubric_id: int
    rubric_content: str
    
    class Config:
        orm_mode = True