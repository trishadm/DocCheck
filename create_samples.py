"""Script to generate realistic sample documents (PDF, DOCX, TXT)

Used for testing and demonstration during college presentations.
"""

import os
import fitz  # PyMuPDF
import docx  # python-docx

SAMPLE_DIR = "sample_documents"
os.makedirs(SAMPLE_DIR, exist_ok=True)


def create_sample_invoice_pdf():
    """Creates a clean sample invoice PDF with 2 pages."""
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    text_p1 = """
INVOICE
Apex Cloud Solutions LLC
100 Innovation Boulevard, Suite 400
Austin, TX 78701
Contact: billing@apexcloud.io | (512) 555-0199

INVOICE DETAILS:
Invoice Number: INV-2024-8842
Invoice Date: October 15, 2024
Due Date: November 15, 2024
Payment Terms: Net 30 Days

BILLED TO:
Nexus Financial Systems Inc.
Attn: Accounts Payable
450 Market Street, 12th Floor
San Francisco, CA 94105

SERVICES & CHARGES:
------------------------------------------------------------------------------------------
Item   Description                          Hours/Qty    Rate         Total
------------------------------------------------------------------------------------------
1.     Cloud Architecture Assessment        40 hrs       $150.00      $6,000.00
2.     API Security Hardening               25 hrs       $175.00      $4,375.00
3.     Database Index Optimization           15 hrs       $140.00      $2,100.00
------------------------------------------------------------------------------------------
Subtotal:                                                             $12,475.00
Tax (0% - B2B Exempt):                                                    $0.00
TOTAL DUE:                                                            $12,475.00
"""
    page1.insert_text((50, 60), text_p1, fontsize=10)

    # Page 2
    page2 = doc.new_page()
    text_p2 = """
Apex Cloud Solutions LLC - Payment Instructions & Policies

BANK WIRE TRANSFER DETAILS:
Bank Name: Silicon Valley Commercial Bank
Routing Transit Number (ABA): 121000358
Account Number: 9844-3211-0023
Account Holder: Apex Cloud Solutions LLC
SWIFT / BIC Code: SVCBUS6S

TERMS AND CONDITIONS:
1. Late Payments: Invoices unpaid after 30 days are subject to a 1.5% monthly late fee.
2. Deliverable Acceptance: Client has 14 calendar days from invoice date to dispute any charge.
3. Support Contact: For questions regarding this invoice, contact accounts@apexcloud.io.

Thank you for your business!
"""
    page2.insert_text((50, 60), text_p2, fontsize=10)

    filepath = os.path.join(SAMPLE_DIR, "sample_invoice.pdf")
    doc.save(filepath)
    doc.close()
    print(f"Created {filepath}")


def create_sample_agreement_pdf():
    """Creates an agreement PDF with intentional discrepancies and unsupported claims."""
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    text_p1 = """
MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is entered into as of May 1, 2024 ("Effective Date"),
by and between:

Client: Global Logistics Network Inc. ("Client"), a Delaware corporation having its principal
place of business at 800 Harbor Way, Seattle, WA 98101.
AND
Provider: CyberShield Defense Corp. ("Provider"), an Ohio corporation having its principal
place of business at 220 Tech Park Lane, Columbus, OH 43215.

RECITALS:
WHEREAS, Client desires to retain Provider to furnish enterprise cybersecurity monitoring services; and
WHEREAS, Provider represents that it possesses the requisite expertise, tools, and proprietary algorithms.

SECTION 1: SCOPE OF SERVICES
Provider shall deliver 24/7 continuous threat telemetry and managed intrusion detection.
Provider guarantees 100% unhackable quantum-safe data protection across all client workloads,
ensuring zero data breaches occur under any circumstances.
"""
    page1.insert_text((50, 60), text_p1, fontsize=10)

    # Page 2
    page2 = doc.new_page()
    text_p2 = """
SECTION 2: TERM AND COMMENCEMENT
Notwithstanding anything to the contrary, the initial term of this Agreement shall commence on
July 1, 2024 ("Commencement Date") and shall continue for an initial period of twelve (12) months.

SECTION 3: COMPENSATION AND BILLING
Client agrees to pay Provider a monthly recurring retainer fee of $8,500.00 payable in advance.
Provider shall invoice Client on the first business day of each calendar month.

SECTION 4: GOVERNING LAW
This Agreement shall be construed and governed in accordance with the laws of the State of Washington,
without regard to conflict of law principles.

[NOTE: Notice that Section on Termination Conditions is completely missing!]
"""
    page2.insert_text((50, 60), text_p2, fontsize=10)

    filepath = os.path.join(SAMPLE_DIR, "sample_agreement_with_issues.pdf")
    doc.save(filepath)
    doc.close()
    print(f"Created {filepath}")


def create_sample_resume_docx():
    """Creates a sample resume in DOCX format."""
    doc = docx.Document()
    doc.add_heading("Alex Morgan", level=0)
    doc.add_paragraph("Email: alex.morgan@email.com | Phone: +1 (555) 321-7654 | Location: Austin, TX | LinkedIn: linkedin.com/in/alexmorgan-dev")

    doc.add_heading("Professional Summary", level=1)
    doc.add_paragraph(
        "Senior Software Engineer with 6+ years of experience designing high-throughput distributed systems, "
        "microservices, and machine learning pipelines. Proven track record in reducing cloud infrastructure costs by 35%."
    )

    doc.add_heading("Core Technical Skills", level=1)
    doc.add_paragraph("Languages: Python, Go, TypeScript, SQL\nFrameworks: FastAPI, PyTorch, Streamlit, Docker, Kubernetes\nCloud & Data: AWS (ECS, S3, DynamoDB), PostgreSQL, Redis, Apache Kafka")

    doc.add_heading("Professional Work Experience", level=1)
    p1 = doc.add_paragraph()
    p1.add_run("Lead Backend Engineer | CloudScale Inc. (Austin, TX)\n").bold = True
    p1.add_run("June 2021 - Present\n")
    p1.add_run("- Architected multi-tenant real-time streaming pipeline processing 50M events daily.\n- Spearheaded transition to Kubernetes microservices, cutting server latency by 42%.")

    p2 = doc.add_paragraph()
    p2.add_run("Software Engineer | DataCraft Labs (Boston, MA)\n").bold = True
    p2.add_run("July 2018 - May 2021\n")
    p2.add_run("- Built RESTful APIs and ETL pipelines in Python for healthcare analytics.\n- Implemented OAuth2 authentication and automated CI/CD test pipelines.")

    doc.add_heading("Education", level=1)
    p3 = doc.add_paragraph()
    p3.add_run("Bachelor of Science in Computer Science\n").bold = True
    p3.add_run("University of Texas at Austin | Graduated May 2018 | GPA: 3.85 / 4.0")

    filepath = os.path.join(SAMPLE_DIR, "sample_resume.docx")
    doc.save(filepath)
    print(f"Created {filepath}")


def create_sample_scanned_pdf():
    """Creates a PDF with zero extractable text (simulating a scanned image without OCR)."""
    doc = fitz.open()
    # Add a blank page with no text
    doc.new_page()
    filepath = os.path.join(SAMPLE_DIR, "sample_scanned_pdf.pdf")
    doc.save(filepath)
    doc.close()
    print(f"Created {filepath}")


def create_sample_txt():
    """Creates a sample general notes document in TXT."""
    content = """Project Phoenix: Quarterly System Architecture Review
Date of Review: September 28, 2024
Author: System Architecture Board (Lead: Dr. Marcus Vance)

Executive Summary:
Project Phoenix represents our next-generation document processing infrastructure.
The system is slated for pilot deployment across 3 regional branches on November 10, 2024.

Key Architecture Decisions:
1. Microservice Framework: All backend endpoints will migrate to Python FastAPI.
2. Document Parsing: PyMuPDF will handle PDF rasterization and text extraction with page preservation.
3. LLM Integration: Google Gemini 2.5 Flash will be utilized for high-throughput zero-hallucination structured extraction.

Key Milestones:
- Milestone 1: Core Parsing Engine Completed - October 15, 2024
- Milestone 2: Verification Engine Integration - October 30, 2024
- Milestone 3: Production Rollout - November 10, 2024

Open Questions & Risk Assessment:
- Document Security: End-to-end encryption must be validated by the Compliance Officer prior to pilot launch.
- Scanned PDF Handling: Currently, scanned PDFs require a digital text layer; OCR roadmap is deferred to v2.0.
"""
    filepath = os.path.join(SAMPLE_DIR, "sample_project_notes.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created {filepath}")


if __name__ == "__main__":
    create_sample_invoice_pdf()
    create_sample_agreement_pdf()
    create_sample_resume_docx()
    create_sample_scanned_pdf()
    create_sample_txt()
    print("All sample files generated successfully!")

