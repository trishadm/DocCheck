"""DocCheck Verification & Analysis Orchestrator

Coordinates the multi-stage document intelligence pipeline:
  Stage 1: Structured Extraction (Entities, domain fields, claims, summary)
  Stage 2: Factual Verification (Missing fields, contradictions, unsupported claims)
  Stage 3: Self-Review & Calibration (Audit extractions, calibrate confidence, eliminate false alarms)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from config import EXPECTED_FIELDS_BY_TYPE, DOC_TYPE_GENERAL, DOC_TYPE_AUTO
from modules.prompts import (
    build_extraction_prompt,
    build_verification_prompt,
    build_self_review_prompt,
)
from modules.gemini_service import generate_structured_json


@dataclass
class VerificationIssue:
    """Represents an issue detected during document verification."""
    issue_type: str  # 'missing_field', 'inconsistency', 'unsupported_claim'
    field_or_claim: str
    description: str
    severity: str  # 'High', 'Medium', 'Low'
    supporting_evidence: str
    page_number: Optional[int]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "field_or_claim": self.field_or_claim,
            "description": self.description,
            "severity": self.severity,
            "supporting_evidence": self.supporting_evidence,
            "page_number": self.page_number,
            "explanation": self.explanation,
        }


@dataclass
class AnalysisResult:
    """Encapsulates the complete result of the 3-stage DocCheck analysis."""
    filename: str
    document_type: str
    summary: str
    extracted_data: Dict[str, Any]
    verification_data: Dict[str, Any]
    self_review_data: Dict[str, Any]
    all_issues: List[VerificationIssue] = field(default_factory=list)
    integrity_score: int = 100
    status_label: str = "Verified"
    processing_time_seconds: float = 0.0
    model_used: str = ""

    # Stats counters
    high_issues_count: int = 0
    medium_issues_count: int = 0
    low_issues_count: int = 0
    missing_fields_count: int = 0
    inconsistencies_count: int = 0
    unsupported_claims_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "document_type": self.document_type,
            "summary": self.summary,
            "integrity_score": self.integrity_score,
            "status_label": self.status_label,
            "processing_time_seconds": round(self.processing_time_seconds, 2),
            "model_used": self.model_used,
            "statistics": {
                "high_issues": self.high_issues_count,
                "medium_issues": self.medium_issues_count,
                "low_issues": self.low_issues_count,
                "missing_fields": self.missing_fields_count,
                "inconsistencies": self.inconsistencies_count,
                "unsupported_claims": self.unsupported_claims_count,
            },
            "extracted_data": self.extracted_data,
            "issues": [issue.to_dict() for issue in self.all_issues],
            "self_review": self.self_review_data,
        }


def run_document_analysis(
    doc_text: str,
    filename: str,
    user_selected_type: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> AnalysisResult:
    """Executes the full 3-stage Document Understanding and Verification pipeline.

    Args:
        doc_text: Text extracted from document with page markers.
        filename: Original file name.
        user_selected_type: User-specified document category.
        model_name: Gemini model name.
        api_key: Optional Gemini API key.
        progress_callback: Optional callback(stage_num, stage_title, percentage) for UI progress.

    Returns:
        AnalysisResult object containing all extracted data, issues, and audit scores.
    """
    start_time = time.time()

    # --------------------------------------------------------------------------
    # STAGE 1: AI Document Understanding & Structured Extraction
    # --------------------------------------------------------------------------
    if progress_callback:
        progress_callback(1, "Stage 1/3: Extracting structured data and entities...", 0.25)

    extraction_prompt = build_extraction_prompt(doc_text, user_selected_type)
    extracted_data = generate_structured_json(
        prompt=extraction_prompt,
        model_name=model_name,
        api_key=api_key,
        temperature=0.1,
    )

    detected_type = extracted_data.get("detected_document_type", "General document")
    effective_doc_type = detected_type if user_selected_type == DOC_TYPE_AUTO else user_selected_type
    summary = extracted_data.get("document_summary", "Summary not available.")

    # Determine expected fields for verification
    expected_fields = EXPECTED_FIELDS_BY_TYPE.get(effective_doc_type, [])

    # --------------------------------------------------------------------------
    # STAGE 2: Information Verification & Factual Cross-Examination
    # --------------------------------------------------------------------------
    if progress_callback:
        progress_callback(2, "Stage 2/3: Cross-examining text for inconsistencies and claims...", 0.60)

    verification_prompt = build_verification_prompt(
        doc_text=doc_text,
        extracted_data=extracted_data,
        document_type=effective_doc_type,
        expected_fields=expected_fields,
    )
    verification_data = generate_structured_json(
        prompt=verification_prompt,
        model_name=model_name,
        api_key=api_key,
        temperature=0.1,
    )

    # --------------------------------------------------------------------------
    # STAGE 3: Self-Review & Integrity Calibration
    # --------------------------------------------------------------------------
    if progress_callback:
        progress_callback(3, "Stage 3/3: Running self-review and confidence calibration...", 0.90)

    self_review_prompt = build_self_review_prompt(
        doc_text=doc_text,
        extracted_data=extracted_data,
        verification_data=verification_data,
    )
    self_review_data = generate_structured_json(
        prompt=self_review_prompt,
        model_name=model_name,
        api_key=api_key,
        temperature=0.1,
    )

    # --------------------------------------------------------------------------
    # CONSOLIDATE AND NORMALIZE ISSUES
    # --------------------------------------------------------------------------
    issues_list: List[VerificationIssue] = []

    # Use consolidated issues from self-review if available, otherwise fallback to stage 2
    raw_issues = self_review_data.get("consolidated_issues")
    if not raw_issues or not isinstance(raw_issues, list) or len(raw_issues) == 0:
        # Merge issues from stage 2
        raw_issues = []
        raw_issues.extend(verification_data.get("missing_fields", []))
        raw_issues.extend(verification_data.get("inconsistencies", []))
        raw_issues.extend(verification_data.get("unsupported_claims", []))

    high_count = 0
    medium_count = 0
    low_count = 0
    missing_count = 0
    inconsist_count = 0
    unsupported_count = 0

    for raw in raw_issues:
        if not isinstance(raw, dict):
            continue

        raw_type = str(raw.get("issue_type", "unsupported_claim")).lower()
        if "missing" in raw_type:
            norm_type = "missing_field"
            missing_count += 1
        elif "inconsist" in raw_type or "conflict" in raw_type:
            norm_type = "inconsistency"
            inconsist_count += 1
        else:
            norm_type = "unsupported_claim"
            unsupported_count += 1

        raw_sev = str(raw.get("severity", "Medium")).capitalize()
        if raw_sev not in ["High", "Medium", "Low"]:
            raw_sev = "Medium"

        if raw_sev == "High":
            high_count += 1
        elif raw_sev == "Medium":
            medium_count += 1
        else:
            low_count += 1

        # Extract page number safely
        pg = raw.get("page_number")
        page_num: Optional[int] = None
        if isinstance(pg, int):
            page_num = pg
        elif isinstance(pg, str) and pg.isdigit():
            page_num = int(pg)

        issue = VerificationIssue(
            issue_type=norm_type,
            field_or_claim=str(raw.get("field_or_claim", "Unknown")),
            description=str(raw.get("description", "")),
            severity=raw_sev,
            supporting_evidence=str(raw.get("supporting_evidence", "N/A")),
            page_number=page_num,
            explanation=str(raw.get("explanation", "")),
        )
        issues_list.append(issue)

    # --------------------------------------------------------------------------
    # SCORE AND STATUS DETERMINATION
    # --------------------------------------------------------------------------
    integrity_score = self_review_data.get("integrity_score")
    if not isinstance(integrity_score, int):
        # Heuristic calculation if model didn't return an integer
        penalty = (high_count * 20) + (medium_count * 10) + (low_count * 3)
        integrity_score = max(0, 100 - penalty)

    if high_count > 0 or integrity_score < 70:
        status_label = "Action Required - High Discrepancies"
    elif medium_count > 0 or integrity_score < 90:
        status_label = "Verified with Notices"
    else:
        status_label = "Verified - Clean"

    total_time = time.time() - start_time

    if progress_callback:
        progress_callback(3, "Analysis completed successfully!", 1.0)

    from modules.gemini_service import get_effective_model
    used_model = get_effective_model(model_name)

    return AnalysisResult(
        filename=filename,
        document_type=effective_doc_type,
        summary=summary,
        extracted_data=extracted_data,
        verification_data=verification_data,
        self_review_data=self_review_data,
        all_issues=issues_list,
        integrity_score=integrity_score,
        status_label=status_label,
        processing_time_seconds=total_time,
        model_used=used_model,
        high_issues_count=high_count,
        medium_issues_count=medium_count,
        low_issues_count=low_count,
        missing_fields_count=missing_count,
        inconsistencies_count=inconsist_count,
        unsupported_claims_count=unsupported_count,
    )

