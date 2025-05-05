import os
import uuid
import shutil
from datetime import datetime

from fastapi import UploadFile, BackgroundTasks

from app.logger import get_logger
from app.constants import Constants

from sqlalchemy.orm import Session

from app.api.v1.datamodels import DocumentType
from app.db_ops import crud
from app.text_ex import Text_Extractor
from app.utils import Directory_Structure

LOGGER = get_logger(__name__)

dir_struct = Directory_Structure()
text_extractor = Text_Extractor(max_file_size_mb=20)

# Helper functions
async def _process_file_upload(
    file: UploadFile,
    document_type: DocumentType,
    background_tasks: BackgroundTasks,
    db: Session
):
    """Process file upload and extract text"""
    # Check file extension
    file_name = os.path.splitext(file.filename)[0]
    file_ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    
    # Create directory for storing files
    today_dir = dir_struct()
    doc_type_dir = Constants.JD.value if document_type == DocumentType.JD else Constants.RESUME_PATH.value
    save_dir = os.path.join(today_dir, doc_type_dir)
    os.makedirs(save_dir, exist_ok=True)
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    unique_filename = f"{unique_id}_{file_name}.{file_ext}"
    file_path = os.path.join(save_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create document record using CRUD operation
    db_document = crud.create_document(
        db=db,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        content_type=file.content_type or f"application/{file_ext}",
        document_type=document_type.value
    )
    
    # Extract text in background
    background_tasks.add_task(
        _extract_text_from_file,
        file_path=file_path,
        document_id=db_document.id,
        db=db
    )
    
    return db_document

async def _process_text_upload(
    text: str,
    document_type: DocumentType,
    db: Session
):
    """Process text upload"""
    # Create directory for storing files
    today_dir = dir_struct()
    doc_type_dir = Constants.JD.value if document_type == DocumentType.JD else Constants.RESUME_PATH.value
    save_dir = os.path.join(today_dir, doc_type_dir)
    os.makedirs(save_dir, exist_ok=True)
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    unique_filename = f"{unique_id}.txt"
    file_path = os.path.join(save_dir, unique_filename)
    
    # Save text to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    # Create document record using CRUD operation
    db_document = crud.create_document(
        db=db,
        filename=unique_filename,
        original_filename=unique_filename,
        file_path=file_path,
        content_type="text/plain",
        document_type=document_type.value,
        extracted_text=text
    )
    
    return db_document

def _extract_text_from_file(file_path: str, document_id: str, db: Session):
    """Extract text from file and update document record"""
    try:
        # Extract text
        extracted_text = text_extractor.extract_text(file_path)
        
        # Update document record using CRUD operation
        crud.update_document_text(db, document_id, extracted_text)
        LOGGER.info(f"Text extracted and saved for document {document_id}")
    except Exception as e:
        LOGGER.error(f"Error extracting text from file {file_path}: {str(e)}")
