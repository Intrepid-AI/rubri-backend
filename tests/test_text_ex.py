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

    @patch('pdfplumber.open', side_effect=Exception("Encrypted file"))
    def test_extract_text_from_encrypted_pdf(self, mock_pdf_open, extractor):
        """Test handling of encrypted PDFs."""
        pdf_bytes = PDF_SIG + b"encrypted data"
        with pytest.raises(ValueError, match="Encrypted PDFs are not supported"):
            extractor.extract_text(pdf_bytes)

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

    # --- Test Markdown Extraction ---

    def test_extract_text_from_md_path(self, extractor, sample_md_file):
        """Test extracting text from a Markdown file path."""
        extracted_text = extractor.extract_text(str(sample_md_file))
        # Check that markdown syntax is stripped
        assert extracted_text == "Header This is markdown text with a link."

    def test_extract_text_from_md_bytes(self, extractor):
        """Test extracting text from Markdown bytes."""
        md_bytes = b"# Title\n\nSome **bold** and `code` text."
        extracted_text = extractor.extract_text(md_bytes) # Rely on heuristic detection
        assert extracted_text == "Title Some bold and code text."

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
