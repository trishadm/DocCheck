"""Unit tests for Report Generator Module

Tests JSON and ReportLab PDF document compilation.
"""

import json
from modules.verification import AnalysisResult, VerificationIssue
from modules.report_generator import generate_json_report, generate_pdf_report


def create_mock_analysis_result() -> AnalysisResult:
    """Helper creating a populated AnalysisResult object."""
    issue = VerificationIssue(
        issue_type="inconsistency",
        field_or_claim="Effective Date",
        description="Conflicting dates found.",
        severity="High",
        supporting_evidence="Page 1 vs Page 2",
        page_number=1,
        explanation="Date conflicts void clarity.",
    )

    return AnalysisResult(
        filename="contract_test.pdf",
        document_type="Agreement",
        summary="Test agreement between Party A and Party B.",
        extracted_data={
            "type_specific_fields": [
                {
                    "field_key": "parties_involved",
                    "field_label": "Parties Involved",
                    "value": "Party A & Party B",
                    "evidence": "Agreement between Party A and Party B",
                    "page_number": 1,
                }
            ],
            "key_entities": {
                "names_and_organizations": [{"name": "Party A", "category": "Company", "page_number": 1}],
                "important_dates": [{"date_text": "May 1, 2024", "significance": "Execution", "page_number": 1}],
                "amounts_and_numbers": [{"amount_or_number": "$5,000", "description": "Deposit", "page_number": 1}],
            },
        },
        verification_data={"missing_fields": []},
        self_review_data={"review_summary": "Clean self-review"},
        all_issues=[issue],
        integrity_score=75,
        status_label="Action Required - High Discrepancies",
        processing_time_seconds=2.45,
        model_used="gemini-3.8-flash",
        high_issues_count=1,
    )


def test_generate_json_report():
    """Tests JSON export formatting."""
    result = create_mock_analysis_result()
    json_str = generate_json_report(result)

    assert isinstance(json_str, str)
    data = json.loads(json_str)
    assert data["filename"] == "contract_test.pdf"
    assert data["integrity_score"] == 75
    assert len(data["issues"]) == 1
    assert data["statistics"]["high_issues"] == 1


def test_generate_pdf_report():
    """Tests PDF generation using ReportLab."""
    result = create_mock_analysis_result()
    pdf_bytes = generate_pdf_report(result)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    # PDF magic bytes start with %PDF
    assert pdf_bytes.startswith(b"%PDF")

