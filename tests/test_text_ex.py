import os
import io
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.text_ex import Text_Extractor

# Define minimal valid byte sequences for signature detection
PDF_SIG = b'%PDF-1.4\n%\x8d\x94\xfa\xc6\n'
DOCX_SIG = b'PK\x03\x04' + b'\x00' * 26 # Minimal PKZIP header
DOC_SIG = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1' + b'\x00' * 8 # OLE Compound File signature

class TestTextExtractor:
    """Test suite for the Text_Extractor class."""
    @pytest.fixture
    def extractor(self):
        """Create a Text_Extractor instance for testing."""
        return Text_Extractor(max_file_size_mb=1)  # Small size for testing
    
    @pytest.fixture
    def sample_text(self):
        """Sample text content for testing."""
        return "This is a sample text for testing purposes."
    
    # --- Fixtures for different file types ---

    @pytest.fixture
    def sample_text_file(self, tmp_path, sample_text):
        """Create a temporary text file for testing."""
        file_path = tmp_path / "sample.txt"
        file_path.write_text(sample_text, encoding='utf-8')
        return file_path

    @pytest.fixture
    def sample_pdf_file(self, tmp_path):
        """Create a temporary (dummy) PDF file for path testing."""
        file_path = tmp_path / "sample.pdf"
        file_path.write_bytes(PDF_SIG + b'dummy pdf content')
        return file_path

    @pytest.fixture
    def sample_docx_file(self, tmp_path):
        """Create a temporary (dummy) DOCX file for path testing."""
        file_path = tmp_path / "sample.docx"
        file_path.write_bytes(DOCX_SIG + b'dummy docx content')
        return file_path

    @pytest.fixture
    def sample_doc_file(self, tmp_path):
        """Create a temporary (dummy) DOC file for path testing."""
        file_path = tmp_path / "sample.doc"
        file_path.write_bytes(DOC_SIG + b'dummy doc content')
        return file_path

    @pytest.fixture
    def sample_md_file(self, tmp_path):
        """Create a temporary Markdown file for testing."""
        file_path = tmp_path / "sample.md"
        md_content = "# Header\n\nThis is *markdown* text with a [link](http://example.com)."
        file_path.write_text(md_content, encoding='utf-8')
        return file_path

    # --- Test File Validation and Size Checks ---

    def test_extract_text_file_not_found(self, extractor):
        """Test extracting from a non-existent file path."""
        with pytest.raises(FileNotFoundError):
            extractor.extract_text("non_existent_file.txt")

    def test_extract_text_file_too_large_path(self, extractor, tmp_path):
        """Test extracting from a file path exceeding size limit."""
        large_file = tmp_path / "large.bin"
        with open(large_file, 'wb') as f:
            f.write(b'0' * (extractor.max_file_size + 1))
        with pytest.raises(ValueError):
            extractor.extract_text(str(large_file))

    def test_extract_text_bytes_too_large(self, extractor):
        """Test extracting from bytes exceeding size limit."""
        large_bytes = b'0' * (extractor.max_file_size + 1)
        with pytest.raises(ValueError, match="File too large"):
            extractor.extract_text(large_bytes)

    def test_extract_text_file_permission_denied(self, extractor, tmp_path):
        """Test extracting from a file with no read permissions."""
        unreadable_file = tmp_path / "unreadable.txt"
        unreadable_file.write_text("content")
        original_mode = unreadable_file.stat().st_mode
        
        try:
            unreadable_file.chmod(0o000) # No read permission
            with pytest.raises(PermissionError, match="Cannot read file:"):
                extractor.extract_text(str(unreadable_file))
        finally:
            unreadable_file.chmod(original_mode) # Restore permissions

    def test_extract_text_path_is_directory(self, extractor, tmp_path):
        """Test providing a directory path instead of a file."""
        dir_path = tmp_path / "a_directory"
        dir_path.mkdir()
        with pytest.raises(ValueError, match="Not a file:"):
            extractor.extract_text(str(dir_path))

    # --- Test Text Extraction (TXT) ---

    def test_extract_text_from_txt_path(self, extractor, sample_text_file, sample_text):
        """Test extracting text from a text file path."""
        extracted_text = extractor.extract_text(str(sample_text_file))
        assert extracted_text == sample_text

    def test_extract_text_from_txt_path_object(self, extractor, sample_text_file, sample_text):
        """Test extracting text from a text file Path object."""
        extracted_text = extractor.extract_text(sample_text_file)
        assert extracted_text == sample_text

    def test_extract_text_from_txt_bytes(self, extractor, sample_text):
        """Test extracting text from text bytes."""
        text_bytes = sample_text.encode('utf-8')
        extracted_text = extractor.extract_text(text_bytes, mime_type='text/plain') # Specify mime for bytes
        assert extracted_text == sample_text

    def test_extract_text_from_txt_bytes_no_mime(self, extractor, sample_text):
        """Test extracting text from text bytes relying on heuristic detection."""
        text_bytes = sample_text.encode('utf-8')
        extracted_text = extractor.extract_text(text_bytes) # No mime_type
        assert extracted_text == sample_text

    def test_extract_text_from_txt_file_like(self, extractor, sample_text):
        """Test extracting text from a text file-like object."""
        text_bytes = sample_text.encode('utf-8')
        bytes_io = io.BytesIO(text_bytes)
        extracted_text = extractor.extract_text(bytes_io, mime_type='text/plain') # Specify mime for file-like
        assert extracted_text == sample_text

    def test_extract_text_from_txt_latin1(self, extractor):
        """Test fallback to latin-1 encoding for text."""
        latin1_text = "This contains ümlauts."
        latin1_bytes = latin1_text.encode('latin-1')
        # Should decode correctly with latin-1 after utf-8 fails
        extracted_text = extractor.extract_text(latin1_bytes, mime_type='text/plain')
        assert extracted_text == latin1_text

    def test_extract_text_from_empty_txt_file(self, extractor, tmp_path):
        """Test extracting from an empty text file (path)."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        assert extractor.extract_text(str(empty_file)) == ""

    def test_extract_text_from_empty_txt_bytes(self, extractor):
        """Test extracting from empty text bytes."""
        assert extractor.extract_text(b"", mime_type='text/plain') == ""

    def test_extract_text_from_whitespace_only_txt_file(self, extractor, tmp_path):
        ws_file = tmp_path / "whitespace.txt"
        ws_file.write_text("   \n\n\t  ")
        assert extractor.extract_text(str(ws_file)) == "   \n\n\t  "

    # --- Test PDF Extraction ---

    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_path(self, mock_pdf_open, extractor, sample_pdf_file):
        """Test extracting text from a PDF file path."""
        # Mock the PDF extraction
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content.   Extra spaces. \n\n\nMore newlines."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content."
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page, mock_page2]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        extracted_text = extractor.extract_text(str(sample_pdf_file))
        # Check content joining and whitespace cleanup
        expected_text = "Page 1 content. Extra spaces. \n\nMore newlines.\n\nPage 2 content."
        assert extracted_text == expected_text
        mock_pdf_open.assert_called_once()
        # Check that pdfplumber was opened with a file object from the path
        assert isinstance(mock_pdf_open.call_args[0][0], io.BytesIO) # It reads the file into BytesIO internally now

    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_path_object(self, mock_pdf_open, extractor, sample_pdf_file):
        """Test extracting text from a PDF file Path object."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF Path object content"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        extracted_text = extractor.extract_text(sample_pdf_file) # Pass Path object
        assert extracted_text == "PDF Path object content"
        mock_pdf_open.assert_called_once()
        assert isinstance(mock_pdf_open.call_args[0][0], io.BytesIO)


    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_bytes(self, mock_pdf_open, extractor):
        """Test extracting text from PDF bytes."""
        # Mock the PDF extraction
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF bytes content"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        pdf_bytes = PDF_SIG + b"dummy pdf bytes"
        extracted_text = extractor.extract_text(pdf_bytes) # Rely on signature detection
        assert extracted_text == "PDF bytes content"
        mock_pdf_open.assert_called_once()
        assert isinstance(mock_pdf_open.call_args[0][0], io.BytesIO)

    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_file_like(self, mock_pdf_open, extractor):
        """Test extracting text from a PDF file-like object."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF file-like content"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        pdf_bytes = PDF_SIG + b"dummy pdf file-like bytes"
        bytes_io = io.BytesIO(pdf_bytes)
        extracted_text = extractor.extract_text(bytes_io, mime_type='application/pdf')
        assert extracted_text == "PDF file-like content"
        mock_pdf_open.assert_called_once()

    @patch('pdfplumber.open', side_effect=Exception("Encrypted file"))
    def test_extract_text_from_encrypted_pdf(self, mock_pdf_open, extractor):
        """Test handling of encrypted PDFs."""
        pdf_bytes = PDF_SIG + b"encrypted data"
        with pytest.raises(ValueError, match="Encrypted PDFs are not supported"):
            extractor.extract_text(pdf_bytes)

    @patch('pdfplumber.open')
    def test_extract_text_from_empty_pdf_path(self, mock_pdf_open, extractor, tmp_path):
        """Test extracting from an empty PDF file (path)."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [] # No pages
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        empty_pdf_file = tmp_path / "empty.pdf"
        empty_pdf_file.write_bytes(PDF_SIG) # Minimal valid PDF start
        assert extractor.extract_text(str(empty_pdf_file)) == ""
        mock_pdf_open.assert_called_once()

    @patch('pdfplumber.open')
    def test_extract_text_from_empty_pdf_bytes(self, mock_pdf_open, extractor):
        """Test extracting from empty PDF bytes."""
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        empty_pdf_bytes = PDF_SIG 
        assert extractor.extract_text(empty_pdf_bytes) == "" # Relies on signature
        mock_pdf_open.assert_called_once()

    # --- Test DOCX Extraction ---

    @patch('docx.Document')
    def test_extract_text_from_docx_path(self, mock_document, extractor, sample_docx_file):
        """Test extracting text from a DOCX file path."""
        # Mock the DOCX extraction
        mock_para1 = MagicMock()
        mock_para1.text = "DOCX paragraph 1"
        mock_para2 = MagicMock()
        mock_para2.text = "DOCX paragraph 2"
        mock_document.return_value.paragraphs = [mock_para1, mock_para2]

        extracted_text = extractor.extract_text(str(sample_docx_file))
        assert extracted_text == "DOCX paragraph 1\n\nDOCX paragraph 2"
        mock_document.assert_called_once()
        # Check that Document was called with a BytesIO object after reading the file
        assert isinstance(mock_document.call_args[0][0], io.BytesIO)

    @patch('docx.Document')
    def test_extract_text_from_docx_path_object(self, mock_document, extractor, sample_docx_file):
        """Test extracting text from a DOCX file Path object."""
        mock_para = MagicMock()
        mock_para.text = "DOCX Path object content"
        mock_document.return_value.paragraphs = [mock_para]

        extracted_text = extractor.extract_text(sample_docx_file) # Pass Path object
        assert extracted_text == "DOCX Path object content"
        mock_document.assert_called_once()
        assert isinstance(mock_document.call_args[0][0], io.BytesIO)


    @patch('docx.Document')
    def test_extract_text_from_docx_bytes(self, mock_document, extractor):
        """Test extracting text from DOCX bytes."""
        # Mock the DOCX extraction
        mock_para = MagicMock()
        mock_para.text = "DOCX bytes content"
        mock_document.return_value.paragraphs = [mock_para]

        docx_bytes = DOCX_SIG + b"dummy docx bytes"
        extracted_text = extractor.extract_text(docx_bytes) # Rely on signature detection
        assert extracted_text == "DOCX bytes content"
        # Check that Document was called with a BytesIO object
        assert isinstance(mock_document.call_args[0][0], io.BytesIO)

    @patch('docx.Document')
    def test_extract_text_from_docx_file_like(self, mock_document, extractor):
        """Test extracting text from a DOCX file-like object."""
        mock_para = MagicMock()
        mock_para.text = "DOCX file-like content"
        mock_document.return_value.paragraphs = [mock_para]

        docx_bytes = DOCX_SIG + b"dummy docx file-like bytes"
        bytes_io = io.BytesIO(docx_bytes)
        extracted_text = extractor.extract_text(bytes_io, mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        assert extracted_text == "DOCX file-like content"
        mock_document.assert_called_once()

    @patch('docx.Document')
    def test_extract_text_from_empty_docx_path(self, mock_document, extractor, tmp_path):
        """Test extracting from an empty DOCX file (path)."""
        mock_document.return_value.paragraphs = []
        
        empty_docx_file = tmp_path / "empty.docx"
        empty_docx_file.write_bytes(DOCX_SIG) # Minimal valid DOCX start
        assert extractor.extract_text(str(empty_docx_file)) == ""
        mock_document.assert_called_once()

    @patch('docx.Document')
    def test_extract_text_from_empty_docx_bytes(self, mock_document, extractor):
        """Test extracting from empty DOCX bytes."""
        mock_document.return_value.paragraphs = []
        
        empty_docx_bytes = DOCX_SIG
        assert extractor.extract_text(empty_docx_bytes) == "" # Relies on signature
        mock_document.assert_called_once()

    # --- Test DOC Extraction ---

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.text_ex.process') # Patch where it's used
    @patch('os.unlink')
    def test_extract_text_from_doc_path(self, mock_unlink, mock_textract, mock_tempfile, extractor, sample_doc_file):
        """Test extracting text from a DOC file path using textract."""
        mock_textract.return_value = b"DOC content from textract"
        # Mock NamedTemporaryFile to simulate writing and return a path
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/fake_doc_file.doc"
        mock_temp_file_obj.write = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        # Patch os.path.exists to return True for the temp file path
        import os
        from unittest.mock import patch as patch_exists
        with patch_exists('os.path.exists', return_value=True):
            extracted_text = extractor.extract_text(str(sample_doc_file))

        assert extracted_text == "DOC content from textract"
        mock_tempfile.assert_called_once_with(suffix='.doc', delete=False)
        mock_temp_file_obj.write.assert_called_once_with(sample_doc_file.read_bytes())
        mock_textract.assert_called_once_with("/tmp/fake_doc_file.doc")
        mock_unlink.assert_called_once_with("/tmp/fake_doc_file.doc")

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.text_ex.process')
    @patch('os.unlink')
    def test_extract_text_from_doc_path_object(self, mock_unlink, mock_textract, mock_tempfile, extractor, sample_doc_file):
        """Test extracting text from a DOC file Path object."""
        mock_textract.return_value = b"DOC Path object content"
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/fake_doc_path_obj.doc"
        mock_temp_file_obj.write = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        import os
        from unittest.mock import patch as patch_exists
        with patch_exists('os.path.exists', return_value=True):
            extracted_text = extractor.extract_text(sample_doc_file) # Pass Path object

        assert extracted_text == "DOC Path object content"
        mock_tempfile.assert_called_once_with(suffix='.doc', delete=False)
        mock_temp_file_obj.write.assert_called_once_with(sample_doc_file.read_bytes())
        mock_textract.assert_called_once_with("/tmp/fake_doc_path_obj.doc")
        mock_unlink.assert_called_once_with("/tmp/fake_doc_path_obj.doc")

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.text_ex.process') # Patch where it's used
    @patch('os.unlink')
    def test_extract_text_from_doc_bytes(self, mock_unlink, mock_textract, mock_tempfile, extractor):
        """Test extracting text from DOC bytes using textract."""
        doc_bytes = DOC_SIG + b"dummy doc bytes"
        mock_textract.return_value = b"DOC bytes content from textract"
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/fake_doc_bytes.doc"
        mock_temp_file_obj.write = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        # Patch os.path.exists to return True for the temp file path
        import os
        from unittest.mock import patch as patch_exists
        with patch_exists('os.path.exists', return_value=True):
            extracted_text = extractor.extract_text(doc_bytes) # Rely on signature detection

        assert extracted_text == "DOC bytes content from textract"
        mock_tempfile.assert_called_once_with(suffix='.doc', delete=False)
        mock_temp_file_obj.write.assert_called_once_with(doc_bytes)
        mock_textract.assert_called_once_with("/tmp/fake_doc_bytes.doc")
        mock_unlink.assert_called_once_with("/tmp/fake_doc_bytes.doc")

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.text_ex.process')
    @patch('os.unlink')
    def test_extract_text_from_doc_file_like(self, mock_unlink, mock_textract, mock_tempfile, extractor):
        """Test extracting text from a DOC file-like object."""
        doc_bytes = DOC_SIG + b"dummy doc file-like bytes"
        mock_textract.return_value = b"DOC file-like content"
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/fake_doc_file_like.doc"
        mock_temp_file_obj.write = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        bytes_io = io.BytesIO(doc_bytes)
        extracted_text = extractor.extract_text(bytes_io, mime_type='application/msword')
        
        assert extracted_text == "DOC file-like content"
        mock_tempfile.assert_called_once_with(suffix='.doc', delete=False)
        mock_temp_file_obj.write.assert_called_once_with(doc_bytes)
        mock_textract.assert_called_once_with("/tmp/fake_doc_file_like.doc")
        mock_unlink.assert_called_once_with("/tmp/fake_doc_file_like.doc")

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.text_ex.process')
    @patch('os.unlink')
    def test_extract_text_from_empty_doc_path(self, mock_unlink, mock_textract, mock_tempfile, extractor, tmp_path):
        """Test extracting from an empty DOC file (path)."""
        mock_textract.return_value = b"" # Empty content
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/empty_doc.doc"
        mock_temp_file_obj.write = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        empty_doc_file = tmp_path / "empty.doc"
        empty_doc_file.write_bytes(DOC_SIG) # Minimal valid DOC start
        
        assert extractor.extract_text(str(empty_doc_file)) == ""
        mock_textract.assert_called_once()

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.text_ex.process')
    @patch('os.unlink')
    def test_extract_text_from_empty_doc_bytes(self, mock_unlink, mock_textract, mock_tempfile, extractor):
        """Test extracting from empty DOC bytes."""
        mock_textract.return_value = b""
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/empty_doc_bytes.doc"
        mock_temp_file_obj.write = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        empty_doc_bytes = DOC_SIG
        assert extractor.extract_text(empty_doc_bytes) == "" # Relies on signature
        mock_textract.assert_called_once()

    # --- Test Markdown Extraction ---

    def test_extract_text_from_md_path(self, extractor, sample_md_file):
        """Test extracting text from a Markdown file path."""
        extracted_text = extractor.extract_text(str(sample_md_file))
        # Check that markdown syntax is stripped
        assert "Header" in extracted_text
        assert "This is markdown text with a link." in extracted_text # Exact output depends on stripper

    def test_extract_text_from_md_path_object(self, extractor, sample_md_file):
        """Test extracting text from a Markdown file Path object."""
        extracted_text = extractor.extract_text(sample_md_file) # Pass Path object
        assert "Header" in extracted_text
        assert "This is markdown text with a link." in extracted_text

    def test_extract_text_from_md_bytes(self, extractor):
        """Test extracting text from Markdown bytes."""
        md_bytes = b"# Title\n\nSome **bold** and `code` text."
        extracted_text = extractor.extract_text(md_bytes) # Rely on heuristic detection
        assert "Title" in extracted_text
        assert "Some bold and code text." in extracted_text

    def test_extract_text_from_md_file_like(self, extractor):
        """Test extracting text from a Markdown file-like object."""
        md_bytes = b"### SubHeader\n\nMore *italic* text."
        bytes_io = io.BytesIO(md_bytes)
        extracted_text = extractor.extract_text(bytes_io, mime_type='text/markdown')
        assert "SubHeader" in extracted_text
        assert "More italic text." in extracted_text

    def test_extract_text_from_md_latin1(self, extractor):
        latin1_md_text = "# Ümlauts\n\nSome *text* with `code`."
        latin1_md_bytes = latin1_md_text.encode('latin-1')
        extracted_text = extractor.extract_text(latin1_md_bytes, mime_type='text/markdown')
        assert "Ümlauts" in extracted_text and "Some text with code" in extracted_text

    # --- Test Unsupported Types and Edge Cases ---

    def test_extract_text_unsupported_extension(self, extractor, tmp_path):
        """Test extracting text from unsupported file types."""
        other_file = tmp_path / "sample.xyz"
        other_file.write_text("Unknown content")
        with pytest.raises(ValueError, match="Unsupported file type: .xyz"):
            extractor.extract_text(str(other_file))

    def test_extract_text_unsupported_bytes(self, extractor):
        """Test extracting text from unsupported bytes."""
        unknown_bytes = b'\x00\x01\x02\x03\x04\x05' # Binary data, no known signature
        with pytest.raises(ValueError, match="Could not determine file type"):
            extractor.extract_text(unknown_bytes)

    def test_extract_text_mime_override(self, extractor, sample_text):
        """Test overriding MIME type detection."""
        text_bytes = sample_text.encode('utf-8')
        # Pretend it's a PDF, should use the text handler anyway if mime is text/*
        extracted_text = extractor.extract_text(text_bytes, mime_type='text/something')
        assert extracted_text == sample_text

        # Pretend it's PDF, but it's actually text bytes - should fail in PDF handler
        with patch('pdfplumber.open', side_effect=Exception("PDF error")):
             with pytest.raises(ValueError, match="Failed to extract text from PDF"):
                 extractor.extract_text(text_bytes, mime_type='application/pdf')

    def test_extract_text_unsupported_source_type(self, extractor):
        """Test providing an unsupported source type to extract_text."""
        with pytest.raises(ValueError, match="Unsupported source type: <class 'int'>"):
            extractor.extract_text(12345)

    def test_extract_text_file_like_invalid_read_type(self, extractor):
        """Test file-like object that returns non-str/bytes on read()."""
        class InvalidFileLike:
            def read(self):
                return 123 # Not str or bytes
        
        with pytest.raises(ValueError, match="File-like object must return bytes or str when read"):
            extractor.extract_text(InvalidFileLike())

    def test_extract_text_file_like_returns_str(self, extractor, sample_text):
        """Test file-like object that returns str on read()."""
        class StrFileLike:
            def read(self):
                return sample_text
        
        # When mime_type is not specified, and it's a string, it should be treated as text/plain
        extracted = extractor.extract_text(StrFileLike()) 
        assert extracted == sample_text

        # Explicitly
        extracted_explicit_mime = extractor.extract_text(StrFileLike(), mime_type='text/plain')
        assert extracted_explicit_mime == sample_text

    def test_extract_text_explicitly_unsupported_mime_type(self, extractor):
        """Test providing an explicitly unsupported MIME type."""
        some_bytes = b"data"
        with pytest.raises(ValueError, match="Unsupported MIME type: application/zip"):
            extractor.extract_text(some_bytes, mime_type="application/zip")
