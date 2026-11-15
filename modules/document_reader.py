"""DocCheck Document Reader Module

Extracts text from PDF, DOCX, and TXT documents.
Preserves page markers for PDFs and detects scanned PDFs without extractable text.
"""

import io
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # PyMuPDF fallback
import docx  # python-docx

from config import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS


class DocumentReaderError(Exception):
    """Base exception for document reader errors."""
    pass


class UnsupportedFileTypeError(DocumentReaderError):
    """Raised when an uploaded file format is not supported."""
    pass


class EmptyDocumentError(DocumentReaderError):
    """Raised when an uploaded document contains no content or 0 bytes."""
    pass


class ScannedPdfError(DocumentReaderError):
    """Raised when a PDF contains pages but no extractable text (e.g., scanned images)."""
    pass


class DocumentCorruptedError(DocumentReaderError):
    """Raised when a file cannot be parsed due to corruption."""
    pass


@dataclass
class DocumentContent:
    """Holds structured extraction results from an uploaded document."""
    filename: str
    file_type: str  # 'pdf', 'docx', 'txt'
    raw_text: str  # Full text including page boundaries
    pages: List[Dict[str, Union[int, str]]] = field(default_factory=list)
    total_pages: int = 1
    char_count: int = 0
    word_count: int = 0
    is_scanned_pdf: bool = False
    preview: str = ""

    def get_page_text(self, page_number: int) -> Optional[str]:
        """Returns the text for a specific 1-indexed page number."""
        for p in self.pages:
            if p.get("page_number") == page_number:
                return str(p.get("text", ""))
        return None


def validate_file_metadata(filename: str, file_size_bytes: int) -> str:
    """Validates the file extension and size constraints.

    Returns:
        The normalized file extension (e.g., '.pdf').
    """
    if not filename or not filename.strip():
        raise UnsupportedFileTypeError("Document filename cannot be empty.")

    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file format '{ext}'. Allowed formats are: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise DocumentReaderError(
            f"File size exceeds the {MAX_FILE_SIZE_MB}MB limit ({file_size_bytes / (1024*1024):.1f}MB)."
        )

    if file_size_bytes == 0:
        raise EmptyDocumentError("The uploaded file is empty (0 bytes).")

    return ext


def extract_from_pdf(file_bytes: bytes, filename: str) -> DocumentContent:
    """Extracts text from a PDF file preserving per-page markers.

    Detects scanned PDFs (no text layer) and raises ScannedPdfError.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise DocumentCorruptedError(f"Failed to open PDF document '{filename}': {str(e)}")

    total_pages = len(doc)
    if total_pages == 0:
        raise EmptyDocumentError(f"PDF document '{filename}' contains 0 pages.")

    pages_data: List[Dict[str, Union[int, str]]] = []
    combined_text_parts: List[str] = []
    total_chars = 0

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc.load_page(page_idx)
        # Extract text with clean layout
        page_text = page.get_text("text").strip()

        pages_data.append({
            "page_number": page_num,
            "text": page_text
        })

        if page_text:
            combined_text_parts.append(f"--- Page {page_num} ---\n{page_text}\n")
            total_chars += len(page_text)
        else:
            combined_text_parts.append(f"--- Page {page_num} ---\n[No extractable text on this page]\n")

    full_text = "\n".join(combined_text_parts).strip()

    # If the PDF has pages but virtually no text across all pages, it is a scanned PDF
    if total_chars < 15:
        raise ScannedPdfError(
            f"No extractable text was found in '{filename}'. This appears to be a scanned document "
            "or an image-only PDF. DocCheck currently does not perform Optical Character Recognition (OCR). "
            "Please upload a document with searchable digital text."
        )

    word_count = len(full_text.split())
    preview = full_text[:1200] + ("..." if len(full_text) > 1200 else "")

    return DocumentContent(
        filename=filename,
        file_type="pdf",
        raw_text=full_text,
        pages=pages_data,
        total_pages=total_pages,
        char_count=total_chars,
        word_count=word_count,
        preview=preview,
    )


def extract_from_docx(file_bytes: bytes, filename: str) -> DocumentContent:
    """Extracts text from a DOCX file including paragraphs and tables."""
    try:
        doc_stream = io.BytesIO(file_bytes)
        doc = docx.Document(doc_stream)
    except Exception as e:
        raise DocumentCorruptedError(f"Failed to open DOCX document '{filename}': {str(e)}")

    text_parts: List[str] = []

    # 1. Extract paragraphs
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            text_parts.append(txt)

    # 2. Extract tables (important for invoices, agreements, and resumes)
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                # Join row cells with pipe separator
                text_parts.append(" | ".join(row_cells))

    full_text = "\n".join(text_parts).strip()

    if not full_text:
        raise EmptyDocumentError(f"DOCX document '{filename}' contains no readable text or content.")

    # Format into page-marked text representation (single section for docx)
    formatted_text = f"--- Page 1 ---\n{full_text}"
    word_count = len(full_text.split())
    preview = full_text[:1200] + ("..." if len(full_text) > 1200 else "")

    return DocumentContent(
        filename=filename,
        file_type="docx",
        raw_text=formatted_text,
        pages=[{"page_number": 1, "text": full_text}],
        total_pages=1,
        char_count=len(full_text),
        word_count=word_count,
        preview=preview,
    )


def extract_from_txt(file_bytes: bytes, filename: str) -> DocumentContent:
    """Extracts text from a plain TXT file with multi-encoding fallback."""
    # Try UTF-8 first, fallback to Latin-1
    try:
        full_text = file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        try:
            full_text = file_bytes.decode("latin-1").strip()
        except Exception as e:
            raise DocumentCorruptedError(f"Could not decode text file '{filename}': {str(e)}")

    if not full_text:
        raise EmptyDocumentError(f"Text file '{filename}' is empty.")

    formatted_text = f"--- Page 1 ---\n{full_text}"
    word_count = len(full_text.split())
    preview = full_text[:1200] + ("..." if len(full_text) > 1200 else "")

    return DocumentContent(
        filename=filename,
        file_type="txt",
        raw_text=formatted_text,
        pages=[{"page_number": 1, "text": full_text}],
        total_pages=1,
        char_count=len(full_text),
        word_count=word_count,
        preview=preview,
    )


def read_document(file_input: Union[bytes, io.BytesIO], filename: str) -> DocumentContent:
    """Unified entry point to read and parse an uploaded document.

    Args:
        file_input: Raw bytes or BytesIO stream of the file.
        filename: Name of the file including extension.

    Returns:
        DocumentContent object with extracted text, page markers, and statistics.
    """
    if isinstance(file_input, io.BytesIO):
        file_bytes = file_input.getvalue()
    elif isinstance(file_input, bytes):
        file_bytes = file_input
    elif hasattr(file_input, "read"):
        file_bytes = file_input.read()
    else:
        raise DocumentReaderError(f"Unsupported file input type: {type(file_input)}")

    ext = validate_file_metadata(filename, len(file_bytes))

    if ext == ".pdf":
        return extract_from_pdf(file_bytes, filename)
    elif ext == ".docx":
        return extract_from_docx(file_bytes, filename)
    elif ext == ".txt":
        return extract_from_txt(file_bytes, filename)
    else:
        raise UnsupportedFileTypeError(f"Unsupported format '{ext}'.")
