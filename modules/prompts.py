"""DocCheck Prompts Module

Implements dedicated prompt engineering templates demonstrating:
- Role Prompting (Persona definition)
- Contextual Prompting (Document ground-truth grounding)
- Structured Output Prompting (Strict JSON schemas)
- Constraint-Based Prompting (Zero-hallucination, verbatim evidence requirements)
- Few-Shot Prompting (Exemplars of expected reasoning and extraction)
- Multi-Step Verification & Self-Refinement
"""

import json
from typing import List, Dict, Any
from config import EXPECTED_FIELDS_BY_TYPE, DOC_TYPE_GENERAL


# ==============================================================================
# Prompt Educational Metadata (For the Prompt Engineering Dashboard Tab)
# ==============================================================================
PROMPT_ENGINEERING_CONCEPTS = {
    "role_prompting": {
        "title": "1. Role Prompting",
        "description": (
            "Instructs the LLM to adopt a specific professional persona (e.g., Senior Document Intelligence Auditor). "
            "This anchors the vocabulary, precision level, and analytical rigor of the output."
        ),
        "code_snippet": (
            "You are DocCheck Extraction Engine, an expert AI document intelligence auditor specializing "
            "in zero-hallucination structured extraction and precision verification."
        ),
    },
    "contextual_prompting": {
        "title": "2. Contextual Prompting",
        "description": (
            "Feeds the target document text into the prompt with clear page boundary delimiters (e.g., `--- Page X ---`). "
            "This strictly restricts the AI's knowledge horizon to the provided text only."
        ),
        "code_snippet": (
            "DOCUMENT CONTEXT:\n"
            "The following text is the exact content extracted from the user's document. "
            "Page boundaries are marked with '--- Page X ---'. Base all answers solely on this context."
        ),
    },
    "constraint_prompting": {
        "title": "3. Constraint-Based Prompting (Zero Hallucination)",
        "description": (
            "Imposes negative constraints and strict boundary rules: do not guess, do not invent values, "
            "require verbatim evidence citations for every extracted claim, and mark missing info as null."
        ),
        "code_snippet": (
            "- ZERO HALLUCINATION RULE: Never invent, extrapolate, or assume any information.\n"
            "- EVIDENCE REQUIREMENT: Every value must cite an exact verbatim substring from the document.\n"
            "- NOT FOUND: If a field is not explicitly present, return null. Never guess."
        ),
    },
    "structured_prompting": {
        "title": "4. Structured Output Prompting",
        "description": (
            "Demands a standardized, deterministic JSON schema matching a machine-readable format. "
            "Combined with response_mime_type='application/json', this eliminates conversational filler."
        ),
        "code_snippet": (
            "Respond ONLY with a valid JSON object matching the schema below. "
            "Do NOT wrap in markdown formatting or add explanatory text outside the JSON."
        ),
    },
    "few_shot_prompting": {
        "title": "5. Few-Shot Prompting (Exemplars)",
        "description": (
            "Provides an in-context example showing the model how to extract evidence, parse dates, "
            "and format missing fields without hallucinations."
        ),
        "code_snippet": (
            "Example Input: 'Agreement executed March 10, 2024 between Apex Corp and Beta LLC.'\n"
            "Example Output: {\"field\": \"effective_date\", \"value\": \"March 10, 2024\", "
            "\"evidence\": \"Agreement executed March 10, 2024\", \"page_number\": 1}"
        ),
    },
    "multistep_verification": {
        "title": "6. Multi-Step Prompting & Self-Refinement",
        "description": (
            "Separates the workflow into discrete sequential reasoning passes: "
            "(1) Structured Extraction -> (2) Verification & Audit -> (3) Self-Review. "
            "Prevents cognitive overload and dramatically improves accuracy on college benchmarks."
        ),
        "code_snippet": (
            "Pipeline:\n"
            "Step 1: Extract entities, fields, and claims with verbatim quotes.\n"
            "Step 2: Cross-examine document for missing fields, contradictions, and unsupported claims.\n"
            "Step 3: Self-review to correct weak extractions and eliminate false alarms."
        ),
    },
}


# ==============================================================================
# 1. Extraction Prompt Builder
# ==============================================================================
def build_extraction_prompt(doc_text: str, user_selected_type: str) -> str:
    """Builds the Stage 1 extraction prompt.

    Uses Role, Context, Constraints, and Structured Output definitions.
    """
    type_hint_instruction = ""
    if user_selected_type and user_selected_type != "Automatic detection":
        type_hint_instruction = (
            f"The user selected the document category as: '{user_selected_type}'. "
            f"Verify if this matches the text; if not, determine the true document type."
        )
    else:
        type_hint_instruction = (
            "Analyze the content and determine the specific document category "
            "(e.g., 'Invoice', 'Resume', 'Agreement', 'Report', 'Receipt', or 'General document')."
        )

    # Format expected fields if known
    expected_fields = EXPECTED_FIELDS_BY_TYPE.get(user_selected_type, [])
    expected_fields_json = json.dumps(expected_fields, indent=2)

    prompt = f"""You are DocCheck Extraction Engine, an expert AI document intelligence auditor specializing in zero-hallucination structured data extraction.

=== CONTEXT ===
You are given the text of a digital document below. Page boundaries are indicated with markers like `--- Page X ---`.
{type_hint_instruction}

=== CORE DIRECTIVES & CONSTRAINTS ===
1. ZERO HALLUCINATION: Extract only information that is explicitly stated in the document text. Never guess, infer, or fabricate data.
2. EVIDENCE CITATIONS: For every extracted entity, field, and claim, provide the EXACT VERBATIM SUBSTRING from the text as `evidence`, along with the `page_number` where it appears.
3. MISSING INFORMATION: If an expected field or entity is absent, return null for `value` and `evidence`. Do NOT leave fields out.
4. CLAIMS EXTRACTION: Extract key assertions, deliverable commitments, qualifications, warranties, or financial representations made in the document.
5. SUMMARY: Provide an objective, factual 2-3 sentence summary of the document.

=== EXPECTED FIELDS REFERENCE FOR THIS CATEGORY ===
{expected_fields_json if expected_fields else "General document: Extract all prominent domain-relevant fields explicitly present in the text."}

=== FEW-SHOT EXEMPLAR ===
Input Snippet: "--- Page 1 ---\nAcme Software Inc. Billed to: Horizon Media LLC. Total: $4,500.00. Payment terms: Net 30."
Expected Field Output:
{{
  "field_key": "total_amount",
  "field_label": "Total Amount",
  "value": "$4,500.00",
  "status": "Found",
  "evidence": "Total: $4,500.00",
  "page_number": 1
}}

=== REQUIRED JSON OUTPUT SCHEMA ===
Return ONLY a valid JSON object matching this exact structure:
{{
  "detected_document_type": "Invoice | Resume | Agreement | General document | <Other specific type>",
  "document_summary": "2-3 sentence objective overview of the document.",
  "key_entities": {{
    "names_and_organizations": [
      {{
        "name": "Name of person or company",
        "category": "Person | Organization | Vendor | Client | Employer | Educational Institution",
        "evidence": "exact quote from document",
        "page_number": 1
      }}
    ],
    "important_dates": [
      {{
        "date_text": "Date string as appears",
        "significance": "e.g., Issue Date, Effective Date, Expiration Date, Employment Period",
        "evidence": "exact quote from document",
        "page_number": 1
      }}
    ],
    "amounts_and_numbers": [
      {{
        "amount_or_number": "Numeric or currency value",
        "description": "What this amount or number represents",
        "evidence": "exact quote from document",
        "page_number": 1
      }}
    ]
  }},
  "type_specific_fields": [
    {{
      "field_key": "snake_case_key",
      "field_label": "Human Readable Label",
      "value": "Extracted value or null if not found",
      "status": "Found | Missing",
      "evidence": "exact quote from document or null",
      "page_number": 1
    }}
  ],
  "main_claims": [
    {{
      "claim": "Statement, commitment, deliverable, or assertion made in the document",
      "claimant_or_topic": "Who makes the claim or which topic it addresses",
      "stated_evidence": "exact quote from document",
      "page_number": 1
    }}
  ]
}}

=== TARGET DOCUMENT TEXT ===
{doc_text}
"""
    return prompt


# ==============================================================================
# 2. Verification Prompt Builder
# ==============================================================================
def build_verification_prompt(
    doc_text: str,
    extracted_data: Dict[str, Any],
    document_type: str,
    expected_fields: List[Dict[str, str]],
) -> str:
    """Builds the Stage 2 verification prompt.

    Detects missing fields, internal contradictions, and potentially unsupported claims.
    """
    extracted_summary = json.dumps(extracted_data, indent=2)
    expected_fields_json = json.dumps(expected_fields, indent=2)

    prompt = f"""You are DocCheck Verification Engine, a meticulous document auditor and factual consistency checker.

=== OBJECTIVE ===
Cross-examine the extracted information and the source document text to detect:
1. MISSING CRITICAL INFORMATION: Important fields expected for document category '{document_type}' that are absent.
2. INTERNAL INCONSISTENCIES: Contradictory dates, conflicting financial figures, name mismatches, or conflicting terms across pages or sections.
3. POTENTIALLY UNSUPPORTED CLAIMS: Statements, credentials, metrics, or assertions that lack adequate backing, corroboration, or definitions in the document text itself.

=== CRITICAL AUDIT GUIDELINES ===
- BOUNDARY RULE: Compare information ONLY against the uploaded document text. Do NOT verify against external world knowledge or make external factual assumptions.
- FAIRNESS RULE: A claim lacking supporting evidence in this document is NOT automatically false in the real world. You must explicitly label it as "potentially unsupported" within the scope of this document.
- SEVERITY LEVELS:
  * High: Missing critical contractual/financial terms, direct numerical or date contradictions, significant unverifiable commitments.
  * Medium: Missing operational details (e.g., due date when payment terms are cited, undefined scope items), ambiguities.
  * Low: Minor formatting inconsistencies, non-critical missing optional fields.

=== EXPECTED FIELDS CHECKLIST FOR CATEGORY '{document_type}' ===
{expected_fields_json if expected_fields else "General document: Audit only expectations explicitly created by the document's own text."}

=== PREVIOUSLY EXTRACTED INFORMATION ===
{extracted_summary}

=== SOURCE DOCUMENT TEXT (GROUND TRUTH) ===
{doc_text}

=== REQUIRED JSON OUTPUT SCHEMA ===
Return ONLY a valid JSON object matching this structure:
{{
  "audit_summary": "Concise summary of the audit findings, highlighting major risks or confirming document consistency.",
  "missing_fields": [
    {{
      "issue_type": "missing_field",
      "field_or_claim": "Name of missing field",
      "description": "Clear explanation of what is missing and why it matters",
      "severity": "High | Medium | Low",
      "supporting_evidence": "N/A - Not found in document text",
      "page_number": null,
      "explanation": "Why this field is expected for this document category"
    }}
  ],
  "inconsistencies": [
    {{
      "issue_type": "inconsistency",
      "field_or_claim": "The conflicting element (e.g., 'Due Date vs Effective Date')",
      "description": "Specific details of the contradiction",
      "severity": "High | Medium | Low",
      "supporting_evidence": "Quote 1 from Page X vs Quote 2 from Page Y",
      "page_number": 1,
      "explanation": "Why these two statements or figures cannot both be true simultaneously"
    }}
  ],
  "unsupported_claims": [
    {{
      "issue_type": "unsupported_claim",
      "field_or_claim": "The assertion or claim in question",
      "description": "Explanation of why this claim lacks sufficient internal substantiation",
      "severity": "High | Medium | Low",
      "supporting_evidence": "Exact quote from text where claim is made",
      "page_number": 1,
      "explanation": "What supporting proof or definitions are absent from the document"
    }}
  ]
}}
"""
    return prompt


# ==============================================================================
# 3. Self-Review Prompt Builder
# ==============================================================================
def build_self_review_prompt(
    doc_text: str,
    extracted_data: Dict[str, Any],
    verification_data: Dict[str, Any],
) -> str:
    """Builds the Stage 3 self-review prompt.

    Audits the extraction and verification to eliminate hallucinations and calibrate confidence.
    """
    extracted_json = json.dumps(extracted_data, indent=2)
    verification_json = json.dumps(verification_data, indent=2)

    prompt = f"""You are DocCheck Quality Reviewer, acting as the final self-reflection and calibration layer.

=== TASK ===
Review the Stage 1 Extractions and Stage 2 Verification findings against the source document.
1. Check that all extracted values are genuinely supported by exact verbatim quotes from the text.
2. Correct any extraction where the model may have hallucinated or over-extrapolated.
3. Validate that flagged issues are genuine problems and eliminate any false positives.
4. Calculate an overall Document Integrity Score (0 to 100) and assign an audit status.

=== INPUT DATA ===
1. Extracted Data:
{extracted_json}

2. Verification Issues:
{verification_json}

3. Source Document Text:
{doc_text}

=== REQUIRED JSON OUTPUT SCHEMA ===
Return ONLY a valid JSON object matching this structure:
{{
  "review_summary": "Summary of the final self-review pass and quality assessment.",
  "integrity_score": 85,
  "status": "Verified - Clean | Verified with Notices | Action Required - High Discrepancies",
  "corrections_applied": [
    {{
      "target_field": "Field or claim modified",
      "original_value": "Previous extraction or finding",
      "corrected_value": "Corrected value or 'Retracted' if false alarm",
      "reason": "Detailed justification based on text"
    }}
  ],
  "consolidated_issues": [
    {{
      "issue_type": "missing_field | inconsistency | unsupported_claim",
      "field_or_claim": "Target item",
      "description": "Concise description of the verified issue",
      "severity": "High | Medium | Low",
      "supporting_evidence": "Verbatim quote or 'N/A - Not in text'",
      "page_number": 1,
      "explanation": "Root cause explanation"
    }}
  ]
}}
"""
    return prompt

