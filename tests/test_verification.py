"""Unit tests for Prompts & Verification Pipeline Module

Tests prompt construction and end-to-end multi-stage verification orchestration.
"""

import pytest
from unittest.mock import patch

from config import EXPECTED_FIELDS_BY_TYPE
from modules.prompts import (
    build_extraction_prompt,
    build_verification_prompt,
    build_self_review_prompt,
)
from modules.verification import run_document_analysis, AnalysisResult


def test_build_extraction_prompt():
    """Tests Stage 1 extraction prompt structure."""
    doc_text = "--- Page 1 ---\nInvoice INV-100 from Acme Corp. Total: $500."
    prompt = build_extraction_prompt(doc_text, "Invoice")

    assert "DocCheck Extraction Engine" in prompt
    assert "ZERO HALLUCINATION" in prompt
    assert "Invoice" in prompt
    assert doc_text in prompt
    assert "invoice_number" in prompt


def test_build_verification_prompt():
    """Tests Stage 2 verification prompt structure."""
    doc_text = "--- Page 1 ---\nAgreement executed May 1, 2024."
    extracted = {"detected_document_type": "Agreement"}
    expected = EXPECTED_FIELDS_BY_TYPE["Agreement"]

    prompt = build_verification_prompt(doc_text, extracted, "Agreement", expected)

    assert "DocCheck Verification Engine" in prompt
    assert "MISSING CRITICAL INFORMATION" in prompt
    assert "POTENTIALLY UNSUPPORTED CLAIMS" in prompt
    assert "parties_involved" in prompt
    assert doc_text in prompt


def test_build_self_review_prompt():
    """Tests Stage 3 self-review prompt structure."""
    doc_text = "--- Page 1 ---\nSample text"
    extracted = {"detected_document_type": "General document"}
    verified = {"missing_fields": []}

    prompt = build_self_review_prompt(doc_text, extracted, verified)

    assert "DocCheck Quality Reviewer" in prompt
    assert "integrity_score" in prompt
    assert doc_text in prompt


@patch("modules.verification.generate_structured_json")
def test_run_document_analysis_pipeline(mock_generate_json):
    """Tests full 3-stage pipeline orchestration with mocked Gemini responses."""
    # Stage 1: Extraction response
    stage1_response = {
        "detected_document_type": "Invoice",
        "document_summary": "Apex Cloud invoice INV-2024-8842",
        "key_entities": {
            "names_and_organizations": [{"name": "Apex Cloud", "category": "Vendor", "page_number": 1}],
            "important_dates": [{"date_text": "October 15, 2024", "significance": "Invoice Date", "page_number": 1}],
            "amounts_and_numbers": [{"amount_or_number": "$12,475.00", "description": "Total", "page_number": 1}],
        },
        "type_specific_fields": [
            {"field_key": "total_amount", "field_label": "Total Amount", "value": "$12,475.00", "evidence": "TOTAL: $12,475.00", "page_number": 1}
        ],
        "main_claims": [
            {"claim": "Late payments incur 1.5% fee", "stated_evidence": "1.5% monthly late fee", "page_number": 2}
        ],
    }

    # Stage 2: Verification response
    stage2_response = {
        "audit_summary": "Document audited with 1 minor issue.",
        "missing_fields": [],
        "inconsistencies": [],
        "unsupported_claims": [
            {
                "issue_type": "unsupported_claim",
                "field_or_claim": "Quantum Safe Encryption",
                "description": "Lacks technical specification in text.",
                "severity": "Medium",
                "supporting_evidence": "guarantees 100% quantum-safe",
                "page_number": 1,
                "explanation": "No encryption algorithms or key lengths defined.",
            }
        ],
    }

    # Stage 3: Self-review response
    stage3_response = {
        "review_summary": "Audited with calibrated confidence.",
        "integrity_score": 88,
        "status": "Verified with Notices",
        "corrections_applied": [],
        "consolidated_issues": [
            {
                "issue_type": "unsupported_claim",
                "field_or_claim": "Quantum Safe Encryption",
                "description": "Lacks technical specification in text.",
                "severity": "Medium",
                "supporting_evidence": "guarantees 100% quantum-safe",
                "page_number": 1,
                "explanation": "No encryption algorithms or key lengths defined.",
            }
        ],
    }

    mock_generate_json.side_effect = [stage1_response, stage2_response, stage3_response]

    result = run_document_analysis(
        doc_text="--- Page 1 ---\nSample Invoice Content",
        filename="test_invoice.pdf",
        user_selected_type="Invoice",
        model_name="gemini-3.8-flash",
        api_key="fake-test-key",
    )

    assert isinstance(result, AnalysisResult)
    assert result.filename == "test_invoice.pdf"
    assert result.document_type == "Invoice"
    assert result.integrity_score == 88
    assert result.status_label == "Verified with Notices"
    assert len(result.all_issues) == 1
    assert result.medium_issues_count == 1
    assert result.all_issues[0].issue_type == "unsupported_claim"
    assert mock_generate_json.call_count == 3

