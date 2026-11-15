# 📑 DocCheck: Intelligent Document Understanding and Information Verification

> **Project Domain:** Document Intelligence & Advanced Prompt Engineering  
> **Course / Project Level:** 20-Mark College Prompt Engineering Demonstration  
> **Powered by:** Python 3.12, Streamlit, Google Gemini Flash (`google-genai` SDK), PyMuPDF, python-docx, and ReportLab.

---

## 📖 1. Project Introduction

**DocCheck** is an intelligent, zero-hallucination document intelligence and verification platform. It allows users to upload digital documents (PDF, DOCX, and TXT), extracts critical structured business entities, and performs multi-stage cross-examination to uncover:
1. **Missing Expected Information:** Mandatory contractual or transactional fields omitted from invoices, agreements, or resumes.
2. **Internal Inconsistencies:** Conflicting dates, contradictory monetary figures, or mismatched terms across different pages or sections.
3. **Potentially Unsupported Claims:** Unsubstantiated claims, deliverables, or promises that lack supporting definitions or evidence in the source document.

DocCheck is built from the ground up to demonstrate rigorous prompt engineering principles, ensuring that every extracted value and flagged issue cites an exact verbatim snippet from the document text.

---

## ✨ 2. Key Features

- **Multi-Format Document Ingestion:** Supports searchable **PDFs** (preserving per-page boundaries `--- Page X ---`), **Word DOCX** (paragraphs and tables), and plain **TXT** files.
- **Scanned PDF Detection:** Intelligently detects image-only PDFs with zero extractable text and informs the user that OCR is not yet implemented in this release.
- **Document Categorization & Schema Auditing:**
  - **Invoice:** Audits invoice number, vendor name, invoice date, total amount, due date, customer, line items.
  - **Resume:** Audits candidate full name, contact info, academic credentials, work history, skills.
  - **Agreement:** Audits parties involved, effective date, scope/obligations, duration/term, termination clauses, governing law.
  - **General Document:** Analyzes claims and expectations defined explicitly by the document's own contents without imposing an arbitrary checklist.
- **3-Stage Sequential Prompt Pipeline:**
  1. *Structured Extraction:* Extracts entities, dates, sums, and claims into deterministic JSON with exact verbatim evidence quotes.
  2. *Verification & Cross-Examination:* Compares extracted values against ground-truth page text to detect omissions, contradictions, and unsupported claims.
  3. *Self-Review & Calibration:* Refines findings, eliminates false alarms, and calculates a calibrated Document Integrity Score (0–100).
- **Interactive Educational Dashboard:** Dedicated "Prompt Engineering" section breaking down the theoretical basis and prompt code for Role, Contextual, Structured, Constraint-Based, and Multi-Step Prompting.
- **Exportable Audit Reports:**
  - One-click downloadable **PDF Audit Report** generated using ReportLab with executive summary, data tables, and severity badges.
  - One-click downloadable **Structured JSON** for automated downstream workflows.

---

## 🛠️ 3. Technology Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Core programming language |
| **Streamlit** | Modern, responsive web interface and interactive dashboard |
| **Google GenAI SDK (`google-genai`)** | Official SDK connecting to Google Gemini 2.5 Flash / 2.0 Flash |
| **PyMuPDF (`pymupdf`)** | High-performance PDF parsing with per-page marker preservation |
| **python-docx** | Extraction of paragraphs and tables from Microsoft Word (.docx) files |
| **ReportLab** | Clean programmatic PDF audit report generation |
| **python-dotenv** | Secure local environment variable management |
| **pytest** | Comprehensive unit test suite |

---

## 🏗️ 4. Project Architecture & Directory Structure

```text
DocCheck/
├── app.py                      # Main Streamlit web application & UI navigation
├── config.py                   # Centralized configuration, expected schemas, constants
├── requirements.txt            # Python dependencies
├── .env.example                # Template for Gemini API key and model configuration
├── .env                        # Local environment variables (git-ignored)
├── .gitignore                  # Git exclusions for secrets, caches, and temp files
├── README.md                   # Complete project documentation and guide
├── create_samples.py           # Generator script for test documents
├── modules/                    # Modular application logic
│   ├── __init__.py
│   ├── document_reader.py      # PDF, DOCX, TXT parsers & scanned PDF detection
│   ├── gemini_service.py       # Google GenAI client, error handling, JSON sanitation
│   ├── prompts.py              # Prompt builders (Role, Context, Constraints, Few-Shot)
│   ├── verification.py         # 3-stage pipeline orchestrator & issue normalizer
│   └── report_generator.py     # PDF & JSON report generation via ReportLab
├── sample_documents/           # Realistic sample files for testing and evaluation
│   ├── sample_invoice.pdf      # Clean 2-page invoice
│   ├── sample_agreement_with_issues.pdf # Contract with conflicting dates & missing terms
│   ├── sample_resume.docx      # Clean candidate resume
│   ├── sample_scanned_pdf.pdf  # Blank page simulating scanned document
│   └── sample_project_notes.txt# Architectural review notes
└── tests/                      # Automated unit test suite
    ├── __init__.py
    ├── test_document_reader.py # Tests for parser, format validation, scanned PDF error
    ├── test_gemini_service.py  # Tests for JSON parsing, auth checks, API error handling
    ├── test_verification.py    # Tests for prompt construction and pipeline execution
    └── test_report_generator.py# Tests for PDF and JSON report generation
```

---

## 🔑 5. Gemini API Key Configuration

DocCheck strictly reads API credentials from the environment or secure UI input. **Never hardcode API keys.**

### Step 1: Obtain a Free Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **"Get API key"** and create a new key.

### Step 2: Configure `.env` File
In the project root directory, copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Open `.env` in any text editor and paste your key:
```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here...
GEMINI_MODEL=gemini-3.8-flash
```

*(Note: You can also enter or override your Gemini API key directly in the Streamlit application sidebar under the ⚙️ Settings section).*

---

## 🚀 6. Installation & Execution Guide

### Step 1: Clone or Navigate to Project Directory
```powershell
cd "e:\1 Trisha\1 MSRIT COLLEGE\5th sem\prompt\DocCheck"
```

### Step 2: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Automated Test Suite
Verify that all document parsers, JSON handlers, and pipeline mocks pass:
```powershell
pytest -v
```
*(All 17 tests should pass cleanly).*

### Step 4: Launch the Streamlit Web Application
```powershell
streamlit run app.py
```
DocCheck will launch in your default web browser at:
`http://localhost:8501`

---

## 🧠 7. Prompt Engineering Concepts Demonstrated

DocCheck was engineered to showcase six fundamental prompt engineering strategies evaluated in collegiate AI curricula:

### 1. Role Prompting
- **Concept:** Anchors the LLM in a specialized persona to govern tone, analytical rigor, and vocabulary.
- **Example:** `"You are DocCheck Extraction Engine, an expert AI document intelligence auditor specializing in zero-hallucination structured data extraction."`

### 2. Contextual Prompting
- **Concept:** Restricts the model's knowledge universe strictly to the supplied text.
- **Implementation:** Document text is injected with clear page boundary markers (`--- Page 1 ---`, `--- Page 2 ---`). The prompt instructs the model: *"Base all answers solely on the provided document text. Do not make external factual assumptions."*

### 3. Constraint-Based Prompting (Zero-Hallucination)
- **Concept:** Imposes negative guardrails and attribution requirements.
- **Implementation:** 
  - *Evidence Requirement:* Every extracted field, entity, or claim must provide the exact verbatim substring from the document.
  - *Not-Found Rule:* Missing information must return `null`. The model is strictly prohibited from guessing or fabricating dates or amounts.

### 4. Structured Output Prompting
- **Concept:** Directs the model to output valid, deterministic JSON schemas.
- **Implementation:** Combines schema instructions with Gemini's native `response_mime_type="application/json"`, eliminating conversational preamble or markdown backtick parsing issues.

### 5. Few-Shot In-Context Exemplars
- **Concept:** Provides input-output demonstrations to guide the model on date formatting, evidence snippet citation, and page attribution.

### 6. Multi-Step Verification & Self-Refinement
- **Concept:** Prevents cognitive overload by splitting the reasoning into three sequential stages:
  - **Stage 1 (Extraction):** What does the document say?
  - **Stage 2 (Verification):** What is missing, contradictory, or unsubstantiated?
  - **Stage 3 (Self-Review):** Are the extracted values backed by exact quotes? Calibrate confidence and eliminate false positives.

---

## ⚠️ 8. Known Limitations & Scope Boundaries

1. **Scanned PDFs & OCR:** This version extracts digital, searchable text layers. Scanned PDFs without an OCR layer are detected and rejected with a helpful warning message. OCR integration is planned for a future update.
2. **Scope of Verification:** DocCheck audits internal consistency and document-supported claims. Labeling a claim as "potentially unsupported" means it lacks proof *within the four corners of this document*; it does not imply factual falsehood in the real world.
3. **File Size Limit:** Recommended document size is capped at 10MB to maintain low latency and responsive UI feedback.

---

## 👨‍💻 9. College Demonstration Checklist

For a 20-mark evaluation demonstration:
- [x] **Test 1: Document Upload & Extraction**  
  Select `sample_invoice.pdf` or upload an invoice. Notice that the invoice number, vendor, date, and line items are extracted into a clean table with verbatim quotes and page numbers.
- [x] **Test 2: Detecting Discrepancies & Unsupported Claims**  
  Select `sample_agreement_with_issues.pdf`. Notice that DocCheck automatically flags:
  - *Inconsistency (High):* Effective Date (May 1, 2024) contradicts Commencement Date (July 1, 2024).
  - *Unsupported Claim (Medium):* "Guarantees 100% unhackable quantum-safe data protection" without cryptographic specification.
  - *Missing Field (Medium):* Termination conditions are missing from the contract.
- [x] **Test 3: Scanned PDF Handling**  
  Select `sample_scanned_pdf.pdf`. Observe the clear, helpful error message explaining that scanned PDFs lack digital text.
- [x] **Test 4: PDF & JSON Export**  
  Click "Download PDF Audit Report" to inspect the ReportLab-generated document complete with severity badges and executive summary.
- [x] **Test 5: Educational Prompt Engineering Inspector**  
  Navigate to "Prompt Engineering" in the sidebar to view theoretical explanations and inspect the actual dynamic prompts generated for the active document.

