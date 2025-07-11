from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.db_ops import models
from app.api.v1.datamodels import DocumentType, ChangeType
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
        doc_id=str(uuid.uuid4()),
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
    
    logger.info(f"Created document record: {db_document.doc_id}")
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
    return db.query(models.Document).filter(models.Document.doc_id == document_id).first()

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
        models.Document.doc_id == document_id
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
    content: Dict[str, Any],
    title: str,
    description: Optional[str] = None,
    jd_document_id: Optional[str] = None,
    resume_document_id: Optional[str] = None,
    status: str = "draft"
) -> models.Rubric:
    """
    Create a new rubric record in the database.
    
    Args:
        db: Database session
        content: Rubric content as JSON
        title: Rubric title
        description: Rubric description (optional)
        jd_document_id: ID of the JD document (optional)
        resume_document_id: ID of the resume document (optional)
        status: Rubric status (default: draft)
        
    Returns:
        Created rubric record
    """
    db_rubric = models.Rubric(
        rubric_id=str(uuid.uuid4()),
        title=title,
        description=description,
        status=status,
        content=content,
        jd_document_id=jd_document_id,
        resume_document_id=resume_document_id,
    )
    
    db.add(db_rubric)
    db.commit()
    db.refresh(db_rubric)
    
    # Create history record
    create_rubric_history(
        db=db,
        rubric_id=db_rubric.rubric_id,
        content=content,
        change_type=ChangeType.CREATED.value
    )
    
    logger.info(f"Created rubric record: {db_rubric.rubric_id}")
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
    return db.query(models.Rubric).filter(models.Rubric.rubric_id == rubric_id).first()

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
            rubric_id=db_rubric.rubric_id,
            content=db_rubric.content,
            change_type=ChangeType.UPDATED.value
        )
    
    logger.info(f"Updated rubric record: {db_rubric.rubric_id}")
    return db_rubric

def update_rubric_via_chat(
    db: Session,
    rubric_id: str,
    content: Dict[str, Any]
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
        rubric_id=db_rubric.rubric_id,
        content=content,
        change_type=ChangeType.CHAT.value
    )
    
    logger.info(f"Updated rubric via chat: {db_rubric.rubric_id}")
    return db_rubric

def list_rubrics(
    db: Session,
    skip: int = 0,
    limit: int = 100
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
        rubhis_id=str(uuid.uuid4()),
        rubric_id=rubric_id,
        content=content,
        change_type=change_type
    )
    
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    
    logger.info(f"Created rubric history record: {db_history.rubhis_id}")
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
        link_id=str(uuid.uuid4()),
        rubric_id=rubric_id,
        token=token,
        expires_at=expires_at
    )
    
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    logger.info(f"Created shared link: {db_link.link_id}")
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

# Task Status operations
def create_task_status(
    db: Session,
    task_id: str,
    task_type: str,
    position_title: Optional[str] = None,
    user_email: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None
) -> models.TaskStatus:
    """
    Create a new task status record.
    
    Args:
        db: Database session
        task_id: Unique task ID
        task_type: Type of task (question_generation, etc.)
        position_title: Position title (optional)
        user_email: User email for notifications (optional)
        request_data: Original request data (optional)
        
    Returns:
        Created task status record
    """
    db_task = models.TaskStatus(
        task_id=task_id,
        task_type=task_type,
        status="pending",
        progress=0,
        position_title=position_title,
        user_email=user_email,
        request_data=request_data
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    logger.info(f"Created task status record: {task_id}")
    return db_task

def get_task_status(db: Session, task_id: str) -> Optional[models.TaskStatus]:
    """
    Get task status by task ID.
    
    Args:
        db: Database session
        task_id: Task ID
        
    Returns:
        Task status record or None if not found
    """
    return db.query(models.TaskStatus).filter(models.TaskStatus.task_id == task_id).first()

def update_task_status(
    db: Session,
    task_id: str,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    result_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    rubric_id: Optional[str] = None
) -> Optional[models.TaskStatus]:
    """
    Update task status.
    
    Args:
        db: Database session
        task_id: Task ID
        status: New status (optional)
        progress: Progress percentage 0-100 (optional)
        current_step: Current processing step (optional)
        result_data: Task results (optional)
        error_message: Error message if failed (optional)
        rubric_id: Associated rubric ID (optional)
        
    Returns:
        Updated task status record or None if not found
    """
    db_task = get_task_status(db, task_id)
    if not db_task:
        logger.error(f"Task status not found: {task_id}")
        return None
    
    if status is not None:
        db_task.status = status
        
        # Set timestamps based on status
        if status == "in_progress" and not db_task.started_at:
            db_task.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            db_task.completed_at = datetime.utcnow()
    
    if progress is not None:
        db_task.progress = min(progress, 100)
    
    if current_step is not None:
        db_task.current_step = current_step
    
    if result_data is not None:
        db_task.result_data = result_data
    
    if error_message is not None:
        db_task.error_message = error_message
    
    if rubric_id is not None:
        db_task.rubric_id = rubric_id
    
    db.commit()
    db.refresh(db_task)
    
    logger.info(f"Updated task status: {task_id}")
    return db_task

def list_task_statuses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    task_type: Optional[str] = None
) -> List[models.TaskStatus]:
    """
    List task statuses with optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status (optional)
        task_type: Filter by task type (optional)
        
    Returns:
        List of task status records
    """
    query = db.query(models.TaskStatus)
    
    if status:
        query = query.filter(models.TaskStatus.status == status)
    
    if task_type:
        query = query.filter(models.TaskStatus.task_type == task_type)
    
    return query.order_by(
        models.TaskStatus.created_at.desc()
    ).offset(skip).limit(limit).all()

# User operations
def create_user(
    db: Session,
    google_id: str,
    email: str,
    name: str,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    picture_url: Optional[str] = None
) -> models.User:
    """
    Create a new user record.
    
    Args:
        db: Database session
        google_id: Google account ID
        email: User's email address
        name: User's full name
        given_name: User's first name (optional)
        family_name: User's last name (optional)
        picture_url: User's profile picture URL (optional)
        
    Returns:
        Created user record
    """
    db_user = models.User(
        user_id=str(uuid.uuid4()),
        google_id=google_id,
        email=email,
        name=name,
        given_name=given_name,
        family_name=family_name,
        picture_url=picture_url,
        last_login_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Created user record: {db_user.user_id} ({email})")
    return db_user

def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    """
    Get user by user ID.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        User record or None if not found
    """
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """
    Get user by email address.
    
    Args:
        db: Database session
        email: Email address
        
    Returns:
        User record or None if not found
    """
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_google_id(db: Session, google_id: str) -> Optional[models.User]:
    """
    Get user by Google ID.
    
    Args:
        db: Database session
        google_id: Google account ID
        
    Returns:
        User record or None if not found
    """
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def update_user_login_time(db: Session, user_id: str) -> Optional[models.User]:
    """
    Update user's last login time.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Updated user record or None if not found
    """
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"Updated login time for user: {user_id}")
    return user

def update_user_preferences(
    db: Session,
    user_id: str,
    email_notifications_enabled: Optional[bool] = None,
    preferred_llm_provider: Optional[str] = None
) -> Optional[models.User]:
    """
    Update user preferences.
    
    Args:
        db: Database session
        user_id: User ID
        email_notifications_enabled: Email notification preference
        preferred_llm_provider: Preferred LLM provider
        
    Returns:
        Updated user record or None if not found
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if email_notifications_enabled is not None:
        user.email_notifications_enabled = "true" if email_notifications_enabled else "false"
    
    if preferred_llm_provider is not None:
        user.preferred_llm_provider = preferred_llm_provider
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated preferences for user: {user_id}")
    return user

# User Session operations
def create_user_session(
    db: Session,
    user_id: str,
    access_token_hash: str,
    refresh_token_hash: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> models.UserSession:
    """
    Create a new user session.
    
    Args:
        db: Database session
        user_id: User ID
        access_token_hash: Hashed access token
        refresh_token_hash: Hashed refresh token (optional)
        expires_at: Session expiration time
        user_agent: User agent string
        ip_address: Client IP address
        
    Returns:
        Created session record
    """
    if not expires_at:
        expires_at = datetime.utcnow() + timedelta(hours=24)
    
    db_session = models.UserSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        access_token_hash=access_token_hash,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    logger.info(f"Created session for user: {user_id}")
    return db_session

def get_user_session_by_token_hash(db: Session, token_hash: str) -> Optional[models.UserSession]:
    """
    Get user session by token hash.
    
    Args:
        db: Database session
        token_hash: Hashed access token
        
    Returns:
        Session record or None if not found
    """
    return db.query(models.UserSession).filter(
        models.UserSession.access_token_hash == token_hash,
        models.UserSession.expires_at > datetime.utcnow()
    ).first()

def update_user_session_last_accessed(db: Session, session_id: str):
    """
    Update session last accessed time.
    
    Args:
        db: Database session
        session_id: Session ID
    """
    session = db.query(models.UserSession).filter(
        models.UserSession.session_id == session_id
    ).first()
    
    if session:
        session.last_accessed_at = datetime.utcnow()
        db.commit()

def delete_user_session(db: Session, session_id: str) -> bool:
    """
    Delete a user session (logout).
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        True if session was deleted, False otherwise
    """
    session = db.query(models.UserSession).filter(
        models.UserSession.session_id == session_id
    ).first()
    
    if session:
        db.delete(session)
        db.commit()
        logger.info(f"Deleted session: {session_id}")
        return True
    
    return False

def delete_expired_sessions(db: Session) -> int:
    """
    Delete all expired sessions.
    
    Args:
        db: Database session
        
    Returns:
        Number of sessions deleted
    """
    expired_sessions = db.query(models.UserSession).filter(
        models.UserSession.expires_at <= datetime.utcnow()
    ).all()
    
    count = len(expired_sessions)
    for session in expired_sessions:
        db.delete(session)
    
    db.commit()
    
    if count > 0:
        logger.info(f"Deleted {count} expired sessions")
    
    return count

if __name__ == "__main__":
    from app.db_ops.database import SessionLocal
    import pprint
    from uuid import uuid4

    db = SessionLocal()
    pp = pprint.PrettyPrinter(indent=2)

    print("--- Testing Document Creation ---")
    doc = create_document(
        db=db,
        filename=uuid4().hex + "testfile.txt",
        original_filename="original_testfile.txt",
        file_path="/tmp/testfile.txt",
        content_type="text/plain",
        document_type="jd",
        extracted_text="Sample extracted text."
    )
    pp.pprint(doc.__dict__)

    print("--- Testing Get Document ---")
    fetched_doc = get_document(db, doc.doc_id)
    pp.pprint(fetched_doc.__dict__ if fetched_doc else None)

    print("--- Testing Rubric Creation ---")
    rubric = create_rubric(
        db=db,
        title="Test Rubric",
        description="Test rubric description",
        content={"criteria": ["Skill A", "Skill B"]},
        jd_document_id=doc.doc_id
    )
    pp.pprint(rubric.__dict__)

    print("--- Testing Get Rubric ---")
    fetched_rubric = get_rubric(db, rubric.rubric_id)
    pp.pprint(fetched_rubric.__dict__ if fetched_rubric else None)

    print("--- Testing Update Rubric ---")
    updated_rubric = update_rubric(
        db=db,
        rubric_id=rubric.rubric_id,
        content={"criteria": ["Skill A", "Skill B", "Skill C"]},
        change_description="Added Skill C"
    )
    pp.pprint(updated_rubric.__dict__ if updated_rubric else None)

    print("--- Testing Update Rubric (No Content Change) ---")
    updated_rubric_no_content = update_rubric(
        db=db,
        rubric_id=rubric.rubric_id,
        content=None,
        change_description="No content change"
    )
    pp.pprint(updated_rubric_no_content.__dict__ if updated_rubric_no_content else None)

    print("--- Testing Update Rubric via Chat ---")
    chat_updated_rubric = update_rubric_via_chat(
        db=db,
        rubric_id=rubric.rubric_id,
        content={"criteria": ["Skill A", "Skill B", "Skill C", "Skill D"]}
    )
    pp.pprint(chat_updated_rubric.__dict__ if chat_updated_rubric else None)

    print("--- Testing List Rubrics ---")
    rubric_list = list_rubrics(db=db, skip=0, limit=10)
    pp.pprint(rubric_list)

    print("--- Testing Get Rubric History ---")
    rubric_history = get_rubric_history(db=db, rubric_id=rubric.rubric_id, skip=0, limit=10)
    for rh in rubric_history:
        pp.pprint(rh.__dict__)

    print("--- Testing Create Shared Link ---")
    shared_link = create_shared_link(db=db, rubric_id=rubric.rubric_id)
    pp.pprint(shared_link.__dict__)

    print("--- Testing Get Shared Link ---")
    fetched_link = get_shared_link(db=db, token=shared_link.token)
    pp.pprint(fetched_link.__dict__ if fetched_link else None)

    db.close()