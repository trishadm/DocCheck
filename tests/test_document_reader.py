"""Unit tests for Document Reader Module

Tests file type validation, text extraction, page markers, and error detection
such as empty files and scanned PDFs.
"""

import os
import pytest
from modules.document_reader import (
    read_document,
    validate_file_metadata,
    UnsupportedFileTypeError,
    EmptyDocumentError,
    ScannedPdfError,
    DocumentReaderError,
)

SAMPLE_DIR = "sample_documents"


def test_validate_file_metadata():
    """Tests file metadata validation logic."""
    # Valid formats
    assert validate_file_metadata("contract.pdf", 1024) == ".pdf"
    assert validate_file_metadata("resume.docx", 2048) == ".docx"
    assert validate_file_metadata("notes.txt", 512) == ".txt"

    # Unsupported format
    with pytest.raises(UnsupportedFileTypeError):
        validate_file_metadata("image.jpg", 1024)

    # Empty filename
    with pytest.raises(UnsupportedFileTypeError):
        validate_file_metadata("", 1024)

    # Empty file (0 bytes)
    with pytest.raises(EmptyDocumentError):
        validate_file_metadata("empty.pdf", 0)

    # Exceeding size limit
    with pytest.raises(DocumentReaderError):
        validate_file_metadata("large.pdf", 11 * 1024 * 1024)


def test_pdf_extraction_with_page_markers():
    """Tests PDF reading and preservation of page markers."""
    pdf_path = os.path.join(SAMPLE_DIR, "sample_invoice.pdf")
    assert os.path.exists(pdf_path), "sample_invoice.pdf must exist"

    with open(pdf_path, "rb") as f:
        doc_content = read_document(f.read(), "sample_invoice.pdf")

    assert doc_content.file_type == "pdf"
    assert doc_content.total_pages == 2
    assert "--- Page 1 ---" in doc_content.raw_text
    assert "--- Page 2 ---" in doc_content.raw_text
    assert "INV-2024-8842" in doc_content.raw_text
    assert doc_content.word_count > 0


def test_docx_extraction():
    """Tests DOCX reading."""
    docx_path = os.path.join(SAMPLE_DIR, "sample_resume.docx")
    assert os.path.exists(docx_path), "sample_resume.docx must exist"

    with open(docx_path, "rb") as f:
        doc_content = read_document(f.read(), "sample_resume.docx")

    assert doc_content.file_type == "docx"
    assert "Alex Morgan" in doc_content.raw_text
    assert "Python" in doc_content.raw_text
    assert doc_content.word_count > 20


def test_txt_extraction():
    """Tests plain text file reading."""
    txt_path = os.path.join(SAMPLE_DIR, "sample_project_notes.txt")
    assert os.path.exists(txt_path), "sample_project_notes.txt must exist"

    with open(txt_path, "rb") as f:
        doc_content = read_document(f.read(), "sample_project_notes.txt")

    assert doc_content.file_type == "txt"
    assert "Project Phoenix" in doc_content.raw_text
    assert doc_content.word_count > 10


def test_scanned_pdf_detection():
    """Tests that a PDF with zero extractable text raises ScannedPdfError."""
    scanned_path = os.path.join(SAMPLE_DIR, "sample_scanned_pdf.pdf")
    assert os.path.exists(scanned_path), "sample_scanned_pdf.pdf must exist"

    with open(scanned_path, "rb") as f:
        with pytest.raises(ScannedPdfError) as exc_info:
            read_document(f.read(), "sample_scanned_pdf.pdf")

    assert "scanned document" in str(exc_info.value).lower()

