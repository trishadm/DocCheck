"""DocCheck Configuration Module

Manages environment variables, model choices, document schemas, and system-wide
constants for the DocCheck intelligent document verification system.
"""

import os
from typing import Dict, List
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

# ==============================================================================
# Gemini API Configuration
# ==============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

# Currently supported and recommended Gemini models for fast, high-quality reasoning
SUPPORTED_MODELS = [
    "gemini-3.8-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
]

# ==============================================================================
# File Upload Constraints
# ==============================================================================
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"]
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
]

# ==============================================================================
# Document Types & Expected Field Schemas
# ==============================================================================
DOC_TYPE_AUTO = "Automatic detection"
DOC_TYPE_INVOICE = "Invoice"
DOC_TYPE_RESUME = "Resume"
DOC_TYPE_AGREEMENT = "Agreement"
DOC_TYPE_GENERAL = "General document"

DOC_TYPES = [
    DOC_TYPE_AUTO,
    DOC_TYPE_INVOICE,
    DOC_TYPE_RESUME,
    DOC_TYPE_AGREEMENT,
    DOC_TYPE_GENERAL,
]

# Expected fields per document type used to detect missing critical information
EXPECTED_FIELDS_BY_TYPE: Dict[str, List[Dict[str, str]]] = {
    DOC_TYPE_INVOICE: [
        {"key": "invoice_number", "label": "Invoice Number", "severity": "High"},
        {"key": "vendor_name", "label": "Vendor / Supplier Name", "severity": "High"},
        {"key": "invoice_date", "label": "Invoice Date", "severity": "High"},
        {"key": "total_amount", "label": "Total Amount", "severity": "High"},
        {"key": "due_date", "label": "Due Date / Payment Terms", "severity": "Medium"},
        {"key": "customer_name", "label": "Billed To / Customer Name", "severity": "Medium"},
        {"key": "line_items", "label": "Line Items / Itemized Services", "severity": "Medium"},
    ],
    DOC_TYPE_RESUME: [
        {"key": "candidate_name", "label": "Candidate Full Name", "severity": "High"},
        {"key": "contact_details", "label": "Contact Info (Email / Phone)", "severity": "High"},
        {"key": "education", "label": "Education / Academic Credentials", "severity": "High"},
        {"key": "skills", "label": "Skills / Core Competencies", "severity": "Medium"},
        {"key": "work_experience", "label": "Work Experience / Employment History", "severity": "Medium"},
    ],
    DOC_TYPE_AGREEMENT: [
        {"key": "parties_involved", "label": "Parties Involved", "severity": "High"},
        {"key": "effective_date", "label": "Effective Date / Execution Date", "severity": "High"},
        {"key": "obligations_and_scope", "label": "Obligations and Scope of Work", "severity": "High"},
        {"key": "duration_or_term", "label": "Term / Duration of Agreement", "severity": "Medium"},
        {"key": "termination_conditions", "label": "Termination Conditions", "severity": "Medium"},
        {"key": "governing_law", "label": "Governing Law / Jurisdiction", "severity": "Low"},
    ],
    DOC_TYPE_GENERAL: [],  # Dynamic: driven by the content of the document itself
}

# ==============================================================================
# UI Styling & Branding
# ==============================================================================
APP_TITLE = "DocCheck"
APP_SUBTITLE = "Intelligent Document Understanding & Information Verification"
APP_VERSION = "1.0.0"
COMPANY_OR_COLLEGE = "College Prompt Engineering Demonstration"

