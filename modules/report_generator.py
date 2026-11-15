"""DocCheck Report Generator Module

Generates downloadable PDF audit reports using ReportLab and JSON export files.
Formats document summary, extracted entities, verification issues, evidence, and limitations.
"""

import io
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from modules.verification import AnalysisResult


def generate_json_report(analysis_result: AnalysisResult) -> str:
    """Generates a formatted JSON string of the complete analysis results."""
    import json
    return json.dumps(analysis_result.to_dict(), indent=2)


def generate_pdf_report(analysis_result: AnalysisResult) -> bytes:
    """Generates a professional multi-page PDF verification report using ReportLab.

    Args:
        analysis_result: The AnalysisResult object.

    Returns:
        Raw bytes of the generated PDF document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom brand styles
    primary_color = colors.HexColor("#1E3A8A")     # Deep blue
    secondary_color = colors.HexColor("#2563EB")   # Bright blue
    text_dark = colors.HexColor("#1E293B")         # Charcoal slate
    text_muted = colors.HexColor("#64748B")        # Slate gray
    bg_light = colors.HexColor("#F8FAFC")          # Off white / light gray
    border_color = colors.HexColor("#CBD5E1")

    # Severity colors
    color_high = colors.HexColor("#DC2626")        # Red
    color_medium = colors.HexColor("#D97706")      # Amber
    color_low = colors.HexColor("#2563EB")         # Blue

    title_style = ParagraphStyle(
        "DocCheckTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        alignment=TA_LEFT,
    )

    subtitle_style = ParagraphStyle(
        "DocCheckSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=text_muted,
        alignment=TA_LEFT,
    )

    h2_style = ParagraphStyle(
        "DocCheckH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "DocCheckBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )

    body_bold = ParagraphStyle(
        "DocCheckBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    table_header = ParagraphStyle(
        "DocCheckTH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
    )

    table_cell = ParagraphStyle(
        "DocCheckTC",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=text_dark,
    )

    table_cell_code = ParagraphStyle(
        "DocCheckTCCode",
        parent=table_cell,
        fontName="Courier",
        fontSize=8,
        textColor=colors.HexColor("#0F172A"),
    )

    table_cell_evidence = ParagraphStyle(
        "DocCheckTCEvidence",
        parent=table_cell,
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=colors.HexColor("#334155"),
    )

    notice_style = ParagraphStyle(
        "DocCheckNotice",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=text_muted,
    )

    story = []

    # --------------------------------------------------------------------------
    # HEADER & TITLE BLOCK
    # --------------------------------------------------------------------------
    now_str = datetime.now().strftime("%B %d, %Y - %H:%M:%S")

    header_table_data = [
        [
            Paragraph("<b>DocCheck</b> | Document Audit & Verification Report", title_style),
            Paragraph(f"<b>Generated:</b> {now_str}<br/><b>Model:</b> {analysis_result.model_used}", subtitle_style),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[340, 192])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=12))

    # --------------------------------------------------------------------------
    # AUDIT METRICS CARD
    # --------------------------------------------------------------------------
    score_color = color_high if analysis_result.integrity_score < 70 else (
        color_medium if analysis_result.integrity_score < 90 else colors.HexColor("#16A34A")
    )

    summary_table_data = [
        [
            Paragraph("<b>Document File:</b>", body_style),
            Paragraph(analysis_result.filename, body_bold),
            Paragraph("<b>Document Category:</b>", body_style),
            Paragraph(analysis_result.document_type, body_bold),
        ],
        [
            Paragraph("<b>Integrity Score:</b>", body_style),
            Paragraph(f"<font color='{score_color.hexval()}'><b>{analysis_result.integrity_score} / 100</b></font>", body_bold),
            Paragraph("<b>Audit Status:</b>", body_style),
            Paragraph(f"<b>{analysis_result.status_label}</b>", body_bold),
        ],
        [
            Paragraph("<b>Flagged Issues:</b>", body_style),
            Paragraph(
                f"<font color='{color_high.hexval()}'>High: {analysis_result.high_issues_count}</font> | "
                f"<font color='{color_medium.hexval()}'>Med: {analysis_result.medium_issues_count}</font> | "
                f"<font color='{color_low.hexval()}'>Low: {analysis_result.low_issues_count}</font>",
                body_style
            ),
            Paragraph("<b>Analysis Time:</b>", body_style),
            Paragraph(f"{analysis_result.processing_time_seconds:.2f} seconds", body_style),
        ]
    ]

    card_table = Table(summary_table_data, colWidths=[100, 166, 110, 156])
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 12))

    # --------------------------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------------------------
    story.append(Paragraph("1. Executive Document Summary", h2_style))
    summary_text = analysis_result.summary or "No summary available."
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # --------------------------------------------------------------------------
    # EXTRACTED FIELDS TABLE
    # --------------------------------------------------------------------------
    story.append(Paragraph("2. Key Extracted Information & Entities", h2_style))

    extracted_data = analysis_result.extracted_data or {}
    type_specific_fields = extracted_data.get("type_specific_fields", [])
    key_entities = extracted_data.get("key_entities", {})

    fields_rows = [
        [
            Paragraph("Field / Entity", table_header),
            Paragraph("Extracted Value", table_header),
            Paragraph("Evidence in Document", table_header),
            Paragraph("Page", table_header),
        ]
    ]

    # Add domain-specific fields
    if isinstance(type_specific_fields, list):
        for f in type_specific_fields:
            if not isinstance(f, dict):
                continue
            label = f.get("field_label") or f.get("field_key", "Field")
            val = str(f.get("value") or "Not Found")
            ev = str(f.get("evidence") or "None")
            pg = str(f.get("page_number") or "-")
            fields_rows.append([
                Paragraph(f"<b>{label}</b>", table_cell),
                Paragraph(val, table_cell_code),
                Paragraph(f'"{ev}"', table_cell_evidence),
                Paragraph(pg, table_cell),
            ])

    # Add entities (Names, Dates, Amounts)
    for category_name, items in [
        ("Entity", key_entities.get("names_and_organizations", [])),
        ("Date", key_entities.get("important_dates", [])),
        ("Amount / Number", key_entities.get("amounts_and_numbers", [])),
    ]:
        if isinstance(items, list):
            for item in items[:4]:  # Show top items
                if not isinstance(item, dict):
                    continue
                name_or_val = item.get("name") or item.get("date_text") or item.get("amount_or_number") or "N/A"
                desc = item.get("category") or item.get("significance") or item.get("description") or category_name
                ev = str(item.get("evidence") or "N/A")
                pg = str(item.get("page_number") or "-")
                fields_rows.append([
                    Paragraph(f"<b>{desc}</b>", table_cell),
                    Paragraph(str(name_or_val), table_cell_code),
                    Paragraph(f'"{ev}"', table_cell_evidence),
                    Paragraph(pg, table_cell),
                ])

    if len(fields_rows) > 1:
        fields_table = Table(fields_rows, colWidths=[120, 140, 232, 40])
        fields_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(fields_table)
    else:
        story.append(Paragraph("No specific structured fields extracted.", body_style))

    story.append(Spacer(1, 12))

    # --------------------------------------------------------------------------
    # VERIFICATION ISSUES & AUDIT FINDINGS
    # --------------------------------------------------------------------------
    story.append(Paragraph("3. Verification Issues & Audit Findings", h2_style))

    if analysis_result.all_issues:
        issues_rows = [
            [
                Paragraph("Severity", table_header),
                Paragraph("Type & Item", table_header),
                Paragraph("Description & Explanation", table_header),
                Paragraph("Supporting Evidence", table_header),
            ]
        ]

        for issue in analysis_result.all_issues:
            sev = issue.severity.capitalize()
            sev_color_tag = (
                f"<font color='{color_high.hexval()}'><b>HIGH</b></font>" if sev == "High" else (
                    f"<font color='{color_medium.hexval()}'><b>MEDIUM</b></font>" if sev == "Medium" else (
                        f"<font color='{color_low.hexval()}'><b>LOW</b></font>"
                    )
                )
            )

            type_label = (
                "Missing Field" if issue.issue_type == "missing_field" else (
                    "Inconsistency" if issue.issue_type == "inconsistency" else "Potentially Unsupported"
                )
            )

            pg_str = f" (Page {issue.page_number})" if issue.page_number else ""
            desc_text = f"<b>{issue.description}</b><br/>{issue.explanation}"

            issues_rows.append([
                Paragraph(sev_color_tag, table_cell),
                Paragraph(f"<b>{type_label}</b><br/>{issue.field_or_claim}{pg_str}", table_cell),
                Paragraph(desc_text, table_cell),
                Paragraph(f'"{issue.supporting_evidence}"', table_cell_evidence),
            ])

        issues_table = Table(issues_rows, colWidths=[60, 120, 212, 140])
        issues_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(issues_table)
    else:
        story.append(Paragraph(
            "<b>No verification issues detected.</b> The document was found to be internally consistent, "
            "with all expected mandatory fields present and supported by verbatim evidence.",
            body_style,
        ))

    story.append(Spacer(1, 14))

    # --------------------------------------------------------------------------
    # SYSTEM LIMITATIONS & LEGAL DISCLAIMER
    # --------------------------------------------------------------------------
    story.append(KeepTogether([
        Paragraph("4. Verification Scope & Limitations Notice", h2_style),
        Paragraph(
            "<b>Important Scope and Boundaries:</b> DocCheck performs heuristic document cross-examination "
            "and consistency auditing strictly against the text present within the uploaded document. "
            "A claim flagged as 'potentially unsupported' indicates a lack of corroborating evidence inside "
            "this document; it does not determine real-world factual accuracy. DocCheck is designed as an "
            "educational and diagnostic prompt engineering tool and should not replace qualified human legal, "
            "financial, or compliance review.",
            notice_style,
        ),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=6),
        Paragraph(
            "DocCheck Document Intelligence Engine | College Prompt Engineering Project",
            subtitle_style,
        ),
    ]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

