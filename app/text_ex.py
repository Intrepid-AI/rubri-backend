import os
import re
import io
import logging
from typing import Optional, Dict, Any, Union, List, BinaryIO, Tuple
from pathlib import Path
import mimetypes
import pdfplumber
import docx
import markdown
import tempfile
# from textract import process

from app.logger import get_logger

LOGGER = get_logger(__name__)

class Text_Extractor:
    """
    A versatile text extraction class supporting multiple file formats.
    
    Supported formats:
    - PDF (.pdf)
    - Plain text (.txt)
    - Microsoft Word (.doc, .docx)
    - Markdown (.md)
    
    Usage:
        extractor = Text_Extractor(max_file_size_mb=10)
        
        # Extract from file path
        text = extractor.extract_text("path/to/file.pdf")
        
        # Extract from file bytes
        with open("document.docx", "rb") as f:
            bytes_data = f.read()
        text = extractor.extract_text(bytes_data)
        
        # Extract from file-like object
        with open("document.txt", "rb") as file_obj:
            text = extractor.extract_text(file_obj)
    """
    
    # Map of supported file extensions to friendly names
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'PDF',
        '.txt': 'Text',
        '.docx': 'Word Document',
        '.doc': 'Word Document (Legacy)',
        '.md': 'Markdown',
    }
    
    # Map of file signatures (magic numbers) to MIME types
    FILE_SIGNATURES = {
        b'%PDF': 'application/pdf',
        b'PK\x03\x04': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': 'application/msword',
    }
    
    # Map of MIME types to handlers and extensions
    MIME_HANDLERS = {
        'application/pdf': ('.pdf', '_extract_from_pdf_bytes'),
        'text/plain': ('.txt', '_extract_from_text_bytes'),
        'application/msword': ('.doc', '_extract_from_word_bytes'),
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 
            ('.docx', '_extract_from_word_bytes'),
        'text/markdown': ('.md', '_extract_from_markdown_bytes'),
    }
    
    # Maximum file size in bytes (default: 10MB)
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    def __init__(self, max_file_size_mb: int = 10, log_level: int = logging.INFO) -> None:
        """
        Initialize the Text_Extractor with configurable settings.
        
        Args:
            max_file_size_mb: Maximum allowed file size in megabytes
            log_level: Logging level (from the logging module)
        """
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert MB to bytes

        # Initialize mimetypes
        mimetypes.init()
        # Add common types that might be missing
        mimetypes.add_type('text/markdown', '.md')
        
        LOGGER.debug(f"Initialized Text_Extractor with {max_file_size_mb}MB max file size")
        
    
    def extract_text(self, source: Union[str, bytes, BinaryIO, Path], **kwargs) -> str:
        """
        Extract text from the given source (file path, bytes, or file-like object).
        
        Args:
            source: Path to a file, bytes data, or file-like object
            **kwargs: Additional options for specific extractors
                     - encoding: Text encoding for files (default: utf-8)
                     - mime_type: Override auto-detected MIME type
        
        Returns:
            Extracted text as a string
        
        Raises:
            ValueError: If the source is invalid or unsupported
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file can't be read due to permissions
        """
        try:
            # Handle various source types
            if isinstance(source, str):
                # Assume it's a file path
                source_path = Path(source)
                self._validate_file(source_path)
                
                # Determine file type and extract accordingly
                extension = source_path.suffix.lower()
                
                if extension not in self.SUPPORTED_EXTENSIONS and kwargs.get('mime_type') is None:
                    raise ValueError(
                        f"Unsupported file type: {extension}. "
                        f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS.keys())}"
                    )
                
                LOGGER.info(f"Extracting text from {self.SUPPORTED_EXTENSIONS.get(extension, 'Unknown')}: {source}")
                
                with open(source_path, 'rb') as f:
                    file_bytes = f.read()
                    return self._process_bytes(file_bytes, extension, **kwargs)
                    
            elif isinstance(source, bytes):
                # Handle raw bytes
                LOGGER.info("Extracting text from bytes data")
                return self._process_bytes(source, **kwargs)
                
            elif hasattr(source, 'read') and callable(source.read):
                # Handle file-like objects
                LOGGER.info("Extracting text from file-like object")
                # Read the entire content (this might not be ideal for very large files)
                file_content = source.read()
                
                # Convert to bytes if it's not already
                if not isinstance(file_content, bytes):
                    if isinstance(file_content, str):
                        file_content = file_content.encode('utf-8')
                    else:
                        raise ValueError("File-like object must return bytes or str when read")
                
                return self._process_bytes(file_content, **kwargs)
                
            elif isinstance(source, Path):
                # Handle Path objects
                self._validate_file(source)
                extension = source.suffix.lower()
                
                if extension not in self.SUPPORTED_EXTENSIONS and kwargs.get('mime_type') is None:
                    raise ValueError(
                        f"Unsupported file type: {extension}. "
                        f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS.keys())}"
                    )
                
                LOGGER.info(f"Extracting text from {self.SUPPORTED_EXTENSIONS.get(extension, 'Unknown')}: {source}")
                
                with open(source, 'rb') as f:
                    file_bytes = f.read()
                    return self._process_bytes(file_bytes, extension, **kwargs)
            
            else:
                raise ValueError(f"Unsupported source type: {type(source)}")
                
        except Exception as e:
            LOGGER.error(f"Error extracting text: {str(e)}")
            raise
    
    def _process_bytes(self, file_bytes: bytes, extension: str = None, **kwargs) -> str:
        """
        Process bytes data based on detected or provided MIME type.
        
        Args:
            file_bytes: The file content as bytes
            extension: File extension (optional, used as hint)
            **kwargs: Additional options for extractors
        
        Returns:
            Extracted text
        """
        # Check file size
        if len(file_bytes) > self.max_file_size:
            raise ValueError(
                f"File too large: {len(file_bytes) / (1024*1024):.2f}MB. "
                f"Maximum allowed size: {self.max_file_size / (1024*1024):.2f}MB"
            )
            
        # Determine MIME type
        # First check if user provided a mime_type
        mime_type = kwargs.get('mime_type')
        
        if not mime_type:
            # Try to detect from extension if provided
            if extension:
                mime_type = mimetypes.guess_type(f"file{extension}")[0]
                
            # If still not determined, use file signature detection
            if not mime_type:
                mime_type = self._detect_mime_from_bytes(file_bytes)
                
                if not mime_type:
                    # Fallback to basic text detection
                    if self._is_probably_text(file_bytes):
                        mime_type = 'text/plain'
                    else:
                        raise ValueError("Could not determine file type. Please specify mime_type.")
        
        LOGGER.info(f"Detected MIME type: {mime_type}")
        
        # Process based on MIME type
        if mime_type in self.MIME_HANDLERS:
            _, handler_name = self.MIME_HANDLERS[mime_type]
            handler = getattr(self, handler_name)
            return handler(file_bytes, **kwargs)
        elif mime_type.startswith('text/'):
            # Generic text handling
            return self._extract_from_text_bytes(file_bytes, **kwargs)
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
    
    def _detect_mime_from_bytes(self, file_bytes: bytes) -> Optional[str]:
        """
        Detect MIME type from file bytes using file signatures.
        
        Args:
            file_bytes: File content as bytes
            
        Returns:
            MIME type string or None if not detected
        """
        # Check for known file signatures (magic numbers)
        for signature, mime_type in self.FILE_SIGNATURES.items():
            if file_bytes.startswith(signature):
                return mime_type
                
        # Check for text-based formats
        if self._is_probably_text(file_bytes, check_chars=500):
            # Look for markdown indicators
            try:
                text_sample = file_bytes[:500].decode('utf-8', errors='ignore')
                if text_sample.startswith('# ') or re.search(r'^#{1,6}\s+\w+', text_sample, re.MULTILINE):
                    return 'text/markdown'
                else:
                    return 'text/plain'
            except Exception:
                pass
                
        return None
    
    def _is_probably_text(self, file_bytes: bytes, check_chars: int = 1000) -> bool:
        """
        Check if the byte data is likely to be text.
        
        Args:
            file_bytes: File content as bytes
            check_chars: Number of characters to check
            
        Returns:
            True if the data appears to be text, False otherwise
        """
        # Check if the file contains only ASCII characters
        sample = file_bytes[:check_chars]
        
        # Zero bytes often indicate binary file
        if b'\x00' in sample:
            return False
            
        # Check if mostly printable ASCII
        printable_ratio = sum(32 <= b <= 126 or b in (9, 10, 13) for b in sample) / len(sample)
        return printable_ratio > 0.7  # 70% printable characters is a reasonable threshold
    
    def _validate_file(self, file_path: Path) -> None:
        """
        Validate that the file exists, is readable, and isn't too large.
        
        Args:
            file_path: Path to the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file can't be read
            ValueError: If the file is too large
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Cannot read file: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large: {file_size / (1024*1024):.2f}MB. "
                f"Maximum allowed size: {self.max_file_size / (1024*1024):.2f}MB"
            )
    
    def _extract_from_text_bytes(self, file_bytes: bytes, encoding: str = 'utf-8', **kwargs) -> str:
        """
        Extract text from bytes of a text file.
        
        Args:
            file_bytes: Content of the text file as bytes
            encoding: Text encoding to use
            
        Returns:
            Text content as string
        """
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            LOGGER.warning(f"Failed to decode with {encoding}, trying with latin-1")
            return file_bytes.decode('latin-1')
    
    def _extract_from_pdf_bytes(self, file_bytes: bytes, **kwargs) -> str:
        """
        Extract text from PDF bytes using pdfplumber.
        
        Args:
            file_bytes: PDF content as bytes
            
        Returns:
            Extracted text with proper formatting
        """
        extracted_text = []
        
        with io.BytesIO(file_bytes) as pdf_file:
            try:
                # Open the PDF with pdfplumber
                with pdfplumber.open(pdf_file) as pdf:
                    # Check if the PDF is encrypted (pdfplumber will raise an error)
                    
                    # Extract text from each page
                    for page in pdf.pages:
                        # Extract text with pdfplumber's built-in text extraction
                        page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                        
                        if page_text:
                            extracted_text.append(page_text)
            except Exception as e:
                if "password" in str(e).lower() or "encrypted" in str(e).lower():
                    raise ValueError("Encrypted PDFs are not supported")
                else:
                    raise ValueError(f"Failed to extract text from PDF: {str(e)}")
        
        # Join all the extracted text with paragraph breaks
        full_text = "\n\n".join(extracted_text)
        
        # Clean up excessive whitespace
        # Replace multiple spaces with a single space
        full_text = re.sub(r' +', ' ', full_text)
        
        # Clean up excessive newlines (more than 2) with exactly 2 newlines (paragraph breaks)
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        
        return full_text.strip()
    
    def _extract_from_word_bytes(self, file_bytes: bytes, **kwargs) -> str:
        """
        Extract text from Word document bytes (.doc or .docx).
        
        Args:
            file_bytes: Word document content as bytes
            
        Returns:
            Extracted text
        """
        # Determine if it's a .docx based on file signature
        is_docx = file_bytes.startswith(b'PK\x03\x04')
        
        if is_docx:
            # Process DOCX
            with io.BytesIO(file_bytes) as docx_file:
                doc = docx.Document(docx_file)
                return '\n\n'.join(paragraph.text for paragraph in doc.paragraphs)
        else:
            # For .doc files, we need to use a different approach
            return self._process_doc_with_temp_file(file_bytes)
    
    def _process_doc_with_temp_file(self, file_bytes: bytes) -> str:
        """Process a legacy .doc file using available methods."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name
            
            process_doc = process(temp_path).decode('utf-8')
            os.unlink(temp_path)
            return process_doc
        
        except Exception as e:
            LOGGER.error(f"Error processing DOC with temp file: {str(e)}")
            raise ValueError(f"Failed to extract text from DOC: {str(e)}")
    
    def _extract_from_markdown_bytes(self, file_bytes: bytes, extensions: List[str] = None, 
                                    encoding: str = 'utf-8', **kwargs) -> str:
        """
        Extract text from Markdown bytes.
        
        Args:
            file_bytes: Markdown content as bytes
            extensions: List of markdown extensions to use
            encoding: File encoding
            
        Returns:
            Plain text extracted from the Markdown
        """
        # Decode bytes to string
        try:
            md_content = file_bytes.decode(encoding)
        except UnicodeDecodeError:
            LOGGER.warning(f"Failed to decode with {encoding}, trying with latin-1")
            md_content = file_bytes.decode('latin-1')
        
        # Convert markdown to plain text (simple approach)
        # Remove headers
        plain_text = re.sub(r'^#{1,6}\s+', '', md_content, flags=re.MULTILINE)
        
        # Remove emphasis markers
        plain_text = re.sub(r'[*_~`]', '', plain_text)
        
        # Remove link syntax but keep the text
        plain_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', plain_text)
        
        # Remove images
        plain_text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', plain_text)
        
        # Remove HTML tags if any
        plain_text = re.sub(r'<[^>]+>', '', plain_text)
        
        # Remove code blocks
        plain_text = re.sub(r'```[^`]*```', '', plain_text)
        
        # Remove inline code
        plain_text = re.sub(r'`[^`]+`', '', plain_text)
        
        # Remove blockquotes
        plain_text = re.sub(r'^>\s+', '', plain_text, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        plain_text = re.sub(r'\n{3,}', '\n\n', plain_text)
        plain_text = re.sub(r'\s+', ' ', plain_text)
        
        return plain_text.strip()
    

if __name__ == "__main__":

    # Initialize the extractor
    extractor = Text_Extractor(max_file_size_mb=20)

    # Example 1: From file path
    # text1 = extractor.extract_text("document.pdf")
    # print(text1)

    # Example 2: From bytes
    # with open("document.docx", "rb") as f:
    #     bytes_data = f.read()
    # text2 = extractor.extract_text(bytes_data)
    # print(text2)

    # Example 3: From file-like object
    # with open("document.txt", "rb") as file_obj:
    #     text3 = extractor.extract_text(file_obj)

    # print(text3)

    # # Example 5: With mime_type specified
    # text5 = extractor.extract_text(bytes_data, mime_type="application/pdf")

    # # Example 6: Extract and prepare for LangChain
    # chunks = extractor.extract_and_prepare_for_langchain("large_document.pdf", 
    #                                                 chunk_size=1500, 
    #                                                 chunk_overlap=150)

