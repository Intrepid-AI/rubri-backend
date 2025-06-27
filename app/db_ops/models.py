from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db_ops.database import Base
from app.logger import get_logger

logger = get_logger(__name__)

def generate_uuid():
    """Generate a UUID string for primary keys"""
    return str(uuid.uuid4())

class Document(Base):
    """
    Document model for storing uploaded files metadata and extracted text.
    
    This model stores information about uploaded job descriptions and resumes,
    including the file path, content type, and extracted text.
    """
    __tablename__ = "documents"
    
    doc_id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False)
    document_type = Column(String(20), nullable=False)  # 'jd' or 'resume'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    extracted_text = Column(Text, nullable=True)
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('filename', name='uq_document_filename'),
    )
    
    def __repr__(self):
        return f"<Document(id='{self.doc_id}', type='{self.document_type}', filename='{self.filename}')>"

class Rubric(Base):
    """
    Rubric model for storing evaluation rubrics.
    
    This model stores the rubric content, metadata, and references to the
    job description and resume documents used to generate the rubric.
    """
    __tablename__ = "rubrics"
    
    rubric_id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    jd_document_id = Column(String(36), ForeignKey("documents.doc_id"), nullable=True)
    resume_document_id = Column(String(36), ForeignKey("documents.doc_id"), nullable=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    jd_document = relationship("Document", foreign_keys=[jd_document_id])
    resume_document = relationship("Document", foreign_keys=[resume_document_id])
    history = relationship("RubricHistory", back_populates="rubric", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Rubric(id='{self.rubric_id}', title='{self.title}', status='{self.status}')>"

class RubricHistory(Base):
    """
    RubricHistory model for tracking changes to rubrics.
    
    This model stores the history of changes made to rubrics, including
    the content at each change point and the type of change.
    """
    __tablename__ = "rubric_history"
    
    rubhis_id = Column(String(36), primary_key=True, default=generate_uuid)
    rubric_id = Column(String(36), ForeignKey("rubrics.rubric_id"), nullable=False)
    content = Column(JSON, nullable=False)
    change_type = Column(String(20), nullable=False)  # 'created', 'updated', 'chat'
    change_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    rubric = relationship("Rubric", back_populates="history")
    
    def __repr__(self):
        return f"<RubricHistory(id='{self.rubhis_id}', rubric_id='{self.rubric_id}', change_type='{self.change_type}')>"

class SharedLink(Base):
    """
    SharedLink model for storing shareable links to rubrics.
    
    This model stores tokens for accessing rubrics without authentication,
    with optional expiration dates.
    """
    __tablename__ = "shared_links"
    
    link_id = Column(String(36), primary_key=True, default=generate_uuid)
    rubric_id = Column(String(36), ForeignKey("rubrics.rubric_id"), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    rubric = relationship("Rubric")
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('token', name='uq_shared_link_token'),
    )
    
    def __repr__(self):
        return f"<SharedLink(id='{self.link_id}', rubric_id='{self.rubric_id}', token='{self.token}')>"