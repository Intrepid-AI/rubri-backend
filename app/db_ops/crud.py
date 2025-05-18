from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app import models
from app.api.v1.datamodels import DocumentType, RubricStatus, ChangeType
from app.logger import get_logger

logger = get_logger(__name__)

# Document operations
def create_document(
    db: Session,
    filename: str,
    original_filename: str,
    file_path: str,
    content_type: str,
    document_type: str,
    extracted_text: Optional[str] = None
) -> models.Document:
    """
    Create a new document record in the database.
    
    Args:
        db: Database session
        filename: Stored filename
        original_filename: Original filename
        file_path: Path to the stored file
        content_type: MIME type of the file
        document_type: Type of document (jd or resume)
        extracted_text: Extracted text from the document (optional)
        
    Returns:
        Created document record
    """
    db_document = models.Document(
        id=str(uuid.uuid4()),
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        content_type=content_type,
        document_type=document_type,
        extracted_text=extracted_text
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    logger.info(f"Created document record: {db_document.id}")
    return db_document

def get_document(db: Session, document_id: str) -> Optional[models.Document]:
    """
    Get a document by ID.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        Document record or None if not found
    """
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_document_by_type(
    db: Session, 
    document_id: str, 
    document_type: str
) -> Optional[models.Document]:
    """
    Get a document by ID and type.
    
    Args:
        db: Database session
        document_id: Document ID
        document_type: Document type (jd or resume)
        
    Returns:
        Document record or None if not found
    """
    return db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.document_type == document_type
    ).first()

def update_document_text(
    db: Session, 
    document_id: str, 
    extracted_text: str
) -> Optional[models.Document]:
    """
    Update the extracted text of a document.
    
    Args:
        db: Database session
        document_id: Document ID
        extracted_text: Extracted text to update
        
    Returns:
        Updated document record or None if not found
    """
    db_document = get_document(db, document_id)
    if db_document:
        db_document.extracted_text = extracted_text
        db.commit()
        db.refresh(db_document)
        logger.info(f"Updated extracted text for document: {document_id}")
        return db_document
    else:
        logger.error(f"Document not found: {document_id}")
        return None

# Rubric operations
def create_rubric(
    db: Session,
    title: str,
    description: Optional[str],
    content: Dict[str, Any],
    jd_document_id: Optional[str] = None,
    resume_document_id: Optional[str] = None,
    status: str = RubricStatus.DRAFT.value
) -> models.Rubric:
    """
    Create a new rubric record in the database.
    
    Args:
        db: Database session
        title: Rubric title
        description: Rubric description
        content: Rubric content as JSON
        jd_document_id: ID of the JD document (optional)
        resume_document_id: ID of the resume document (optional)
        status: Rubric status (default: draft)
        
    Returns:
        Created rubric record
    """
    db_rubric = models.Rubric(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        content=content,
        jd_document_id=jd_document_id,
        resume_document_id=resume_document_id,
        status=status
    )
    
    db.add(db_rubric)
    db.commit()
    db.refresh(db_rubric)
    
    # Create history record
    create_rubric_history(
        db=db,
        rubric_id=db_rubric.id,
        content=content,
        change_type=ChangeType.CREATED.value,
        change_description="Initial rubric creation"
    )
    
    logger.info(f"Created rubric record: {db_rubric.id}")
    return db_rubric

def get_rubric(db: Session, rubric_id: str) -> Optional[models.Rubric]:
    """
    Get a rubric by ID.
    
    Args:
        db: Database session
        rubric_id: Rubric ID
        
    Returns:
        Rubric record or None if not found
    """
    return db.query(models.Rubric).filter(models.Rubric.id == rubric_id).first()

def update_rubric(
    db: Session,
    rubric_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    change_description: str = "Manual update"
) -> Optional[models.Rubric]:
    """
    Update a rubric record.
    
    Args:
        db: Database session
        rubric_id: Rubric ID
        title: New title (optional)
        description: New description (optional)
        content: New content (optional)
        status: New status (optional)
        change_description: Description of the change
        
    Returns:
        Updated rubric record or None if not found
    """
    db_rubric = get_rubric(db, rubric_id)
    if not db_rubric:
        logger.error(f"Rubric not found: {rubric_id}")
        return None
    
    # Update fields if provided
    if title is not None:
        db_rubric.title = title
    
    if description is not None:
        db_rubric.description = description
    
    if content is not None:
        db_rubric.content = content
    
    if status is not None:
        db_rubric.status = status
    
    db_rubric.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_rubric)
    
    # Create history record if content was updated
    if content is not None:
        create_rubric_history(
            db=db,
            rubric_id=db_rubric.id,
            content=db_rubric.content,
            change_type=ChangeType.UPDATED.value,
            change_description=change_description
        )
    
    logger.info(f"Updated rubric record: {db_rubric.id}")
    return db_rubric

def update_rubric_via_chat(
    db: Session,
    rubric_id: str,
    content: Dict[str, Any],
    message: str
) -> Optional[models.Rubric]:
    """
    Update a rubric via chat.
    
    Args:
        db: Database session
        rubric_id: Rubric ID
        content: New content
        message: Chat message
        
    Returns:
        Updated rubric record or None if not found
    """
    db_rubric = get_rubric(db, rubric_id)
    if not db_rubric:
        logger.error(f"Rubric not found: {rubric_id}")
        return None
    
    # Update content
    db_rubric.content = content
    db_rubric.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_rubric)
    
    # Create history record
    create_rubric_history(
        db=db,
        rubric_id=db_rubric.id,
        content=content,
        change_type=ChangeType.CHAT.value,
        change_description=f"Updated via chat: {message}"
    )
    
    logger.info(f"Updated rubric via chat: {db_rubric.id}")
    return db_rubric

def list_rubrics(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    List rubrics with pagination and optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status (optional)
        
    Returns:
        Dictionary with items, total, page, and page_size
    """
    # Build query
    query = db.query(models.Rubric)
    
    # Apply filters
    if status:
        query = query.filter(models.Rubric.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    query = query.order_by(models.Rubric.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    # Execute query
    rubrics = query.all()
    
    return {
        "items": rubrics,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit
    }

# Rubric history operations
def create_rubric_history(
    db: Session,
    rubric_id: str,
    content: Dict[str, Any],
    change_type: str,
    change_description: Optional[str] = None
) -> models.RubricHistory:
    """
    Create a new rubric history record.
    
    Args:
        db: Database session
        rubric_id: Rubric ID
        content: Rubric content at the time of the change
        change_type: Type of change (created, updated, chat)
        change_description: Description of the change (optional)
        
    Returns:
        Created rubric history record
    """
    db_history = models.RubricHistory(
        id=str(uuid.uuid4()),
        rubric_id=rubric_id,
        content=content,
        change_type=change_type,
        change_description=change_description
    )
    
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    
    logger.info(f"Created rubric history record: {db_history.id}")
    return db_history

def get_rubric_history(
    db: Session,
    rubric_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[models.RubricHistory]:
    """
    Get history records for a rubric.
    
    Args:
        db: Database session
        rubric_id: Rubric ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of rubric history records
    """
    return db.query(models.RubricHistory).filter(
        models.RubricHistory.rubric_id == rubric_id
    ).order_by(
        models.RubricHistory.created_at.desc()
    ).offset(skip).limit(limit).all()

# Shared link operations
def create_shared_link(
    db: Session,
    rubric_id: str,
    expires_at: Optional[datetime] = None
) -> models.SharedLink:
    """
    Create a shared link for a rubric.
    
    Args:
        db: Database session
        rubric_id: Rubric ID
        expires_at: Expiration date (optional)
        
    Returns:
        Created shared link record
    """
    # Generate a token
    token = str(uuid.uuid4())
    
    db_link = models.SharedLink(
        id=str(uuid.uuid4()),
        rubric_id=rubric_id,
        token=token,
        expires_at=expires_at
    )
    
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    logger.info(f"Created shared link: {db_link.id}")
    return db_link

def get_shared_link(db: Session, token: str) -> Optional[models.SharedLink]:
    """
    Get a shared link by token.
    
    Args:
        db: Database session
        token: Shared link token
        
    Returns:
        Shared link record or None if not found
    """
    return db.query(models.SharedLink).filter(models.SharedLink.token == token).first()