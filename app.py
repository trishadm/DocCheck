"""DocCheck - Intelligent Document Understanding & Information Verification

A Streamlit web application demonstrating advanced prompt engineering for:
- Zero-hallucination structured document extraction
- Cross-examination and factual verification
- Self-review and integrity calibration
"""

import os
import io
import json
import streamlit as st
import pandas as pd

import config
from modules.document_reader import (
    read_document,
    DocumentContent,
    ScannedPdfError,
    EmptyDocumentError,
    UnsupportedFileTypeError,
    DocumentReaderError,
)
from modules.gemini_service import (
    test_gemini_connection,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiServiceError,
    GeminiUnavailableError,
    get_effective_api_key,
    get_effective_model,
)
from modules.verification import run_document_analysis, AnalysisResult
from modules.prompts import (
    PROMPT_ENGINEERING_CONCEPTS,
    build_extraction_prompt,
    build_verification_prompt,
    build_self_review_prompt,
)
from modules.report_generator import generate_pdf_report, generate_json_report

# ==============================================================================
# STREAMLIT PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title=f"{config.APP_TITLE} | Intelligent Document Verification",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Light Theme CSS with Blue Accents and Rounded Cards
CUSTOM_CSS = """
<style>
    /* Global Styles */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Card Styles */
    .doccheck-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .doccheck-card-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 8px;
    }
    
    /* Severity Badges */
    .badge-high {
        background-color: #FEF2F2;
        color: #DC2626;
        border: 1px solid #FECACA;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
    }
    .badge-medium {
        background-color: #FFFBEB;
        color: #D97706;
        border: 1px solid #FDE68A;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
    }
    .badge-low {
        background-color: #EFF6FF;
        color: #2563EB;
        border: 1px solid #BFDBFE;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
    }
    
    /* Score Metric Box */
    .metric-box {
        text-align: center;
        padding: 16px;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Status Pills */
    .status-clean {
        background-color: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 700;
    }
    .status-warning {
        background-color: #FFFBEB;
        color: #D97706;
        border: 1px solid #FDE68A;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 700;
    }
    .status-danger {
        background-color: #FEF2F2;
        color: #DC2626;
        border: 1px solid #FECACA;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 700;
    }
    
    /* Evidence Quote Block */
    .evidence-quote {
        background-color: #F1F5F9;
        border-left: 4px solid #2563EB;
        padding: 10px 14px;
        font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace;
        font-size: 0.85rem;
        color: #1E293B;
        border-radius: 0 8px 8px 0;
        margin: 6px 0;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = "Dashboard"

if "custom_api_key" not in st.session_state:
    st.session_state.custom_api_key = config.GEMINI_API_KEY


# ==============================================================================
# SIDEBAR NAVIGATION & CONFIGURATION
# ==============================================================================
with st.sidebar:
    st.title("📑 DocCheck")
    st.caption("Document Intelligence & Verification")

    st.markdown("---")

    # Main Navigation
    nav_options = [
        "Dashboard",
        "Analyze Document",
        "Analysis Results",
        "Prompt Engineering",
    ]
    selected_nav = st.radio(
        "Navigation",
        options=nav_options,
        index=nav_options.index(st.session_state.nav_choice)
        if st.session_state.nav_choice in nav_options
        else 0,
        key="sidebar_nav",
    )
    st.session_state.nav_choice = selected_nav

    st.markdown("---")

    # Configuration Section
    st.subheader("⚙️ Settings & Credentials")

    # Model Selection
    selected_model = st.selectbox(
        "Gemini Flash Model",
        options=config.SUPPORTED_MODELS,
        index=0,
        help="Select a fast, reasoning-capable model. Configurable via GEMINI_MODEL.",
    )

    # API Key Input
    has_env_key = bool(config.GEMINI_API_KEY)
    key_placeholder = "••••••••••••••••••••" if has_env_key else "Paste Gemini API Key"
    
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.custom_api_key if not has_env_key else "",
        type="password",
        placeholder=key_placeholder,
        help="Get a free API key at https://aistudio.google.com/",
    )

    # Effective API key determination
    effective_key = api_key_input.strip() if api_key_input.strip() else config.GEMINI_API_KEY
    st.session_state.custom_api_key = effective_key

    if effective_key:
        st.success("✓ API Key configured", icon="🔑")
    else:
        st.warning("⚠️ No API Key found (.env or sidebar)", icon="⚠️")

    # Test Connection Button
    if st.button("Test Gemini Connection", use_container_width=True):
        with st.spinner("Testing API connection..."):
            test_res = test_gemini_connection(api_key=effective_key, model_name=selected_model)
            if test_res["success"]:
                st.success(f"Connected! Model: {test_res['model']}")
            else:
                st.error(f"Connection Failed: {test_res['message']}")

    st.markdown("---")
    st.markdown(
        "<div style='font-size: 0.75rem; color: #64748B; text-align: center;'>"
        "DocCheck v1.0 • College Prompt Engineering Project<br/>"
        "Powered by Google Gemini 3.8 Flash</div>",
        unsafe_allow_html=True,
    )


# ==============================================================================
# VIEW 1: DASHBOARD
# ==============================================================================
if st.session_state.nav_choice == "Dashboard":
    st.title("📑 DocCheck: Intelligent Document Understanding")
    st.markdown(
        "**DocCheck** combines **structured prompt engineering** and **LLM self-verification** "
        "to extract key information from digital documents, audit missing fields, detect internal contradictions, "
        "and flag potentially unsupported claims without hallucination."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Key Value Props (Cards)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div class="doccheck-card">
                <div class="doccheck-card-header">🎯 Structured Extraction</div>
                <p style="font-size: 0.9rem; color: #475569;">
                    Extracts entities, key dates, monetary sums, and document summaries into standardized JSON schemas with verbatim text evidence citations.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        col2.markdown(
            """
            <div class="doccheck-card">
                <div class="doccheck-card-header">🔍 Inconsistency & Gap Audit</div>
                <p style="font-size: 0.9rem; color: #475569;">
                    Evaluates invoices, resumes, contracts, and general files against expected field checklists, uncovering conflicting dates or amounts.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        col3.markdown(
            """
            <div class="doccheck-card">
                <div class="doccheck-card-header">🛡️ Zero-Hallucination Review</div>
                <p style="font-size: 0.9rem; color: #475569;">
                    Applies a 3-stage prompt pipeline (Extract &rarr; Verify &rarr; Self-Review) ensuring every assertion links back to ground-truth page text.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Session Statistics
    st.subheader("📊 Session Statistics")
    history_count = len(st.session_state.analysis_history)
    m1, m2, m3, m4 = st.columns(4)

    total_issues = sum(item.get("issues_count", 0) for item in st.session_state.analysis_history)
    clean_docs = sum(1 for item in st.session_state.analysis_history if item.get("status") == "Verified - Clean")

    with m1:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-value">{history_count}</div>
                <div class="metric-label">Documents Analyzed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-value">{clean_docs}</div>
                <div class="metric-label">Clean Documents</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-value">{total_issues}</div>
                <div class="metric-label">Total Issues Flagged</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        active_model = selected_model
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-value" style="font-size: 1.25rem; padding-top: 10px;">{active_model}</div>
                <div class="metric-label">Active Gemini Model</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Call to action & Recent Documents
    left_c, right_c = st.columns([1.5, 1])

    with left_c:
        st.subheader("🚀 Quick Start")
        st.info(
            "Ready to audit a document? Jump to **Analyze Document** to upload your own PDF, DOCX, or TXT file, "
            "or load one of the built-in college sample documents.",
            icon="💡",
        )
        if st.button("Go to Analyze Document ➡️", type="primary"):
            st.session_state.nav_choice = "Analyze Document"
            st.rerun()

    with right_c:
        st.subheader("🕒 Recent Analysis")
        if st.session_state.analysis_history:
            recent_df = pd.DataFrame(st.session_state.analysis_history)[
                ["filename", "doc_type", "score", "status"]
            ]
            st.dataframe(recent_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No documents analyzed in this session yet. Upload a document to see results here.")


# ==============================================================================
# VIEW 2: ANALYZE DOCUMENT
# ==============================================================================
elif st.session_state.nav_choice == "Analyze Document":
    st.title("📄 Upload & Analyze Document")
    st.markdown("Upload a PDF, DOCX, or TXT file to inspect extracted text and initiate multi-stage AI verification.")

    upload_col, preset_col = st.columns([1.6, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "Choose a document (Max 10MB)",
            type=["pdf", "docx", "txt"],
            help="Upload PDF, Word DOCX, or plain text file with selectable text.",
        )

    with preset_col:
        st.markdown("**Or load a sample document:**")
        sample_choice = st.selectbox(
            "Sample College Test Documents",
            options=[
                "None (Use Uploaded File)",
                "sample_invoice.pdf (Valid Invoice)",
                "sample_agreement_with_issues.pdf (Discrepancies & Gaps)",
                "sample_resume.docx (Alex Morgan Resume)",
                "sample_scanned_pdf.pdf (Scanned PDF Test)",
                "sample_project_notes.txt (System Notes)",
            ],
            index=0,
        )

    # Document Category Selector
    doc_type_choice = st.selectbox(
        "Document Category",
        options=config.DOC_TYPES,
        index=0,
        help="Select a type to enforce specific expected fields, or choose Automatic detection.",
    )

    # Handle document loading
    loaded_content: DocumentContent = None
    read_error = None

    if sample_choice != "None (Use Uploaded File)":
        sample_filename = sample_choice.split(" ")[0]
        sample_path = os.path.join("sample_documents", sample_filename)
        if os.path.exists(sample_path):
            try:
                with open(sample_path, "rb") as f:
                    file_bytes = f.read()
                loaded_content = read_document(file_bytes, sample_filename)
            except Exception as e:
                read_error = e
    elif uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            loaded_content = read_document(file_bytes, uploaded_file.name)
        except Exception as e:
            read_error = e

    # Error handling for document reading
    if read_error:
        if isinstance(read_error, ScannedPdfError):
            st.error(f"❌ Scanned PDF Detected: {str(read_error)}", icon="⚠️")
        elif isinstance(read_error, EmptyDocumentError):
            st.error(f"❌ Empty Document: {str(read_error)}", icon="⚠️")
        elif isinstance(read_error, UnsupportedFileTypeError):
            st.error(f"❌ Unsupported Format: {str(read_error)}", icon="⚠️")
        else:
            st.error(f"❌ Document Parsing Error: {str(read_error)}", icon="⚠️")
        st.session_state.current_doc = None

    elif loaded_content:
        st.session_state.current_doc = loaded_content
        st.success(f"✓ Document loaded successfully: **{loaded_content.filename}**")

        # Document Metadata Badges
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("File Type", loaded_content.file_type.upper())
        b2.metric("Page Count", loaded_content.total_pages)
        b3.metric("Word Count", f"{loaded_content.word_count:,}")
        b4.metric("Character Count", f"{loaded_content.char_count:,}")

        # Text Preview Collapsible
        with st.expander("📖 Extracted Document Text Preview (with page markers)", expanded=True):
            st.text_area(
                "Document Text",
                value=loaded_content.raw_text,
                height=220,
                disabled=True,
            )

        # Analysis Trigger
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🚀 Run DocCheck Analysis", type="primary", use_container_width=True)

        if analyze_button:
            if not effective_key:
                st.error(
                    "❌ Google Gemini API Key is missing! Please enter your API key in the sidebar "
                    "or add it to your `.env` file (`GEMINI_API_KEY=...`).",
                    icon="🔑",
                )
            else:
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def update_progress(stage_num: int, message: str, percentage: float):
                    progress_bar.progress(percentage)
                    status_text.info(f"⏳ {message}")

                try:
                    result = run_document_analysis(
                        doc_text=loaded_content.raw_text,
                        filename=loaded_content.filename,
                        user_selected_type=doc_type_choice,
                        model_name=selected_model,
                        api_key=effective_key,
                        progress_callback=update_progress,
                    )
                    st.session_state.analysis_result = result

                    # Append to session history
                    st.session_state.analysis_history.append({
                        "filename": result.filename,
                        "doc_type": result.document_type,
                        "score": result.integrity_score,
                        "status": result.status_label,
                        "issues_count": len(result.all_issues),
                    })

                    status_text.success("🎉 Analysis complete! Navigating to Analysis Results...")
                    st.session_state.nav_choice = "Analysis Results"
                    st.rerun()

                except GeminiAuthError as e:
                    status_text.empty()
                    st.error(f"❌ Gemini Authentication Error: {str(e)}", icon="🔑")
                except GeminiUnavailableError as e:
                    status_text.empty()
                    st.error(f"❌ Gemini Temporary Demand Spike (503): {str(e)}", icon="⏳")
                except GeminiQuotaError as e:
                    status_text.empty()
                    st.error(f"❌ Gemini Quota / Rate Limit Error: {str(e)}", icon="⏳")
                except GeminiServiceError as e:
                    status_text.empty()
                    st.error(f"❌ Gemini Service Error: {str(e)}", icon="⚠️")
                except Exception as e:
                    status_text.empty()
                    st.error(f"❌ Unexpected Error: {str(e)}", icon="⚠️")


# ==============================================================================
# VIEW 3: ANALYSIS RESULTS
# ==============================================================================
elif st.session_state.nav_choice == "Analysis Results":
    result: AnalysisResult = st.session_state.analysis_result

    if not result:
        st.warning("⚠️ No analysis has been performed yet.", icon="ℹ️")
        st.info("Please navigate to **Analyze Document** to upload a document and run the audit.")
        if st.button("Go to Analyze Document"):
            st.session_state.nav_choice = "Analyze Document"
            st.rerun()
    else:
        st.title(f"📊 Audit Results: {result.filename}")

        # Top Banner with Integrity Score & Status
        status_css_class = "status-clean" if result.integrity_score >= 90 else (
            "status-warning" if result.integrity_score >= 70 else "status-danger"
        )

        st.markdown(
            f"""
            <div class="doccheck-card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1.3rem; font-weight: 700; color: #1E3A8A;">Status: </span>
                    <span class="{status_css_class}">{result.status_label}</span>
                    <div style="color: #64748B; font-size: 0.85rem; margin-top: 6px;">
                        Document Category: <b>{result.document_type}</b> • Analyzed in <b>{result.processing_time_seconds:.2f}s</b> using <b>{result.model_used}</b>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 2.2rem; font-weight: 800; color: #1E3A8A;">{result.integrity_score}<span style="font-size: 1.1rem; color: #94A3B8;"> / 100</span></div>
                    <div style="font-size: 0.75rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Integrity Score</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Analysis Results Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Overview",
            "🔍 Extracted Information",
            "⚠️ Verification Issues",
            "📌 Evidence Citations",
        ])

        # ----------------------------------------------------------------------
        # TAB 1: OVERVIEW
        # ----------------------------------------------------------------------
        with tab1:
            st.subheader("1. Executive Document Summary")
            st.markdown(f"> {result.summary}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("2. Audit Statistics")

            oc1, oc2, oc3, oc4 = st.columns(4)
            oc1.metric("High Severity", result.high_issues_count, delta="Immediate Attention" if result.high_issues_count > 0 else "Clear", delta_color="inverse")
            oc2.metric("Medium Severity", result.medium_issues_count)
            oc3.metric("Low Severity", result.low_issues_count)
            oc4.metric("Total Issues", len(result.all_issues))

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("3. Self-Review & Integrity Calibration")
            review_data = result.self_review_data or {}
            st.write(review_data.get("review_summary", "Self-review completed."))

            corrections = review_data.get("corrections_applied", [])
            if corrections:
                st.markdown("**Self-Corrections Applied During Review:**")
                for c in corrections:
                    st.info(
                        f"**{c.get('target_field', 'Field')}**: Changed from `'{c.get('original_value')}'` to "
                        f"`'{c.get('corrected_value')}'` — *{c.get('reason')}*"
                    )

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("4. Export Audit Reports")
            r_col1, r_col2 = st.columns(2)

            with r_col1:
                pdf_bytes = generate_pdf_report(result)
                st.download_button(
                    label="📄 Download PDF Audit Report",
                    data=pdf_bytes,
                    file_name=f"DocCheck_Report_{result.filename}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            with r_col2:
                json_str = generate_json_report(result)
                st.download_button(
                    label="💾 Download Structured JSON Data",
                    data=json_str,
                    file_name=f"DocCheck_Data_{result.filename}.json",
                    mime="application/json",
                    use_container_width=True,
                )

        # ----------------------------------------------------------------------
        # TAB 2: EXTRACTED INFORMATION
        # ----------------------------------------------------------------------
        with tab2:
            st.subheader("Domain-Specific Extracted Fields")
            type_fields = result.extracted_data.get("type_specific_fields", [])

            if type_fields:
                formatted_fields = []
                for f in type_fields:
                    val = f.get("value")
                    val_str = str(val) if val is not None else "Not Found"
                    formatted_fields.append({
                        "Field Label": f.get("field_label", f.get("field_key", "Field")),
                        "Extracted Value": val_str,
                        "Status": f.get("status", "Found" if val else "Missing"),
                        "Page": f.get("page_number", "-"),
                        "Evidence Snippet": f.get("evidence", "None"),
                    })
                st.dataframe(pd.DataFrame(formatted_fields), use_container_width=True, hide_index=True)
            else:
                st.info("No domain-specific expected fields defined for this document category.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Key Entities & Numerical Figures")
            entities = result.extracted_data.get("key_entities", {})

            ent_col1, ent_col2, ent_col3 = st.columns(3)

            with ent_col1:
                st.markdown("##### 👥 Names & Organizations")
                names = entities.get("names_and_organizations", [])
                if names:
                    for n in names:
                        pg_str = f" (Pg {n.get('page_number')})" if n.get("page_number") else ""
                        st.markdown(f"• **{n.get('name')}** - *{n.get('category')}*{pg_str}")
                else:
                    st.caption("None extracted.")

            with ent_col2:
                st.markdown("##### 📅 Important Dates")
                dates = entities.get("important_dates", [])
                if dates:
                    for d in dates:
                        pg_str = f" (Pg {d.get('page_number')})" if d.get("page_number") else ""
                        st.markdown(f"• **{d.get('date_text')}** - *{d.get('significance')}*{pg_str}")
                else:
                    st.caption("None extracted.")

            with ent_col3:
                st.markdown("##### 💰 Amounts & Numbers")
                amounts = entities.get("amounts_and_numbers", [])
                if amounts:
                    for a in amounts:
                        pg_str = f" (Pg {a.get('page_number')})" if a.get("page_number") else ""
                        st.markdown(f"• **{a.get('amount_or_number')}** - *{a.get('description')}*{pg_str}")
                else:
                    st.caption("None extracted.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Key Document Claims & Commitments")
            claims = result.extracted_data.get("main_claims", [])
            if claims:
                for idx, c in enumerate(claims, 1):
                    pg_str = f" (Page {c.get('page_number')})" if c.get("page_number") else ""
                    st.markdown(f"**{idx}. {c.get('claim')}**{pg_str}")
                    st.markdown(f"<div class='evidence-quote'>Evidence: \"{c.get('stated_evidence')}\"</div>", unsafe_allow_html=True)
            else:
                st.caption("No explicit major claims extracted.")

        # ----------------------------------------------------------------------
        # TAB 3: VERIFICATION ISSUES
        # ----------------------------------------------------------------------
        with tab3:
            st.subheader("Audited Discrepancies, Missing Fields & Potential Gaps")
            st.markdown(
                "> **Disclaimer on Potentially Unsupported Claims:** A claim lacking supporting evidence "
                "within this document is not automatically false in the real world. It is strictly labeled "
                "as *potentially unsupported* relative to the uploaded document text."
            )

            if not result.all_issues:
                st.success("🎉 No issues detected! The document satisfies all expected criteria and shows internal consistency.")
            else:
                # Severity Filter
                sev_filter = st.radio(
                    "Filter by Severity",
                    options=["All", "High", "Medium", "Low"],
                    horizontal=True,
                )

                filtered_issues = [
                    i for i in result.all_issues
                    if sev_filter == "All" or i.severity == sev_filter
                ]

                st.write(f"Showing **{len(filtered_issues)}** issues:")

                for issue in filtered_issues:
                    badge_class = f"badge-{issue.severity.lower()}"
                    type_label = (
                        "Missing Expected Field" if issue.issue_type == "missing_field" else (
                            "Internal Inconsistency" if issue.issue_type == "inconsistency" else "Potentially Unsupported Claim"
                        )
                    )
                    pg_display = f"• Page {issue.page_number}" if issue.page_number else ""

                    st.markdown(
                        f"""
                        <div class="doccheck-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span class="{badge_class}">{issue.severity.upper()} SEVERITY</span>
                                <span style="font-size: 0.85rem; color: #64748B; font-weight: 600;">{type_label} {pg_display}</span>
                            </div>
                            <div style="font-weight: 700; font-size: 1.05rem; color: #1E293B; margin-bottom: 4px;">
                                {issue.field_or_claim}
                            </div>
                            <div style="font-size: 0.9rem; color: #334155; margin-bottom: 6px;">
                                {issue.description}
                            </div>
                            <div style="font-size: 0.85rem; color: #64748B; font-style: italic;">
                                <b>Explanation:</b> {issue.explanation}
                            </div>
                            <div class="evidence-quote">
                                <b>Document Evidence:</b> "{issue.supporting_evidence}"
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # ----------------------------------------------------------------------
        # TAB 4: EVIDENCE CITATIONS
        # ----------------------------------------------------------------------
        with tab4:
            st.subheader("Verbatim Evidence Citations & Ground-Truth Text")
            st.markdown(
                "Every extraction and flagged issue in DocCheck is strictly paired with an exact verbatim substring "
                "from the document, proving zero-hallucination compliance."
            )

            # Evidence Explorer Table
            evidence_rows = []
            for issue in result.all_issues:
                evidence_rows.append({
                    "Context": f"Issue: {issue.field_or_claim}",
                    "Severity": issue.severity,
                    "Page": issue.page_number or "-",
                    "Verbatim Quote": issue.supporting_evidence,
                })

            for f in result.extracted_data.get("type_specific_fields", []):
                if f.get("evidence"):
                    evidence_rows.append({
                        "Context": f"Field: {f.get('field_label', f.get('field_key'))}",
                        "Severity": "N/A (Extracted)",
                        "Page": f.get("page_number") or "-",
                        "Verbatim Quote": f.get("evidence"),
                    })

            if evidence_rows:
                st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)
            else:
                st.caption("No evidence citations available.")

            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("📄 Full Ground-Truth Text with Page Markers"):
                if st.session_state.current_doc:
                    st.text_area(
                        "Source Document Text",
                        value=st.session_state.current_doc.raw_text,
                        height=350,
                        disabled=True,
                    )


# ==============================================================================
# VIEW 4: PROMPT ENGINEERING (EDUCATIONAL COLLEGE SECTION)
# ==============================================================================
elif st.session_state.nav_choice == "Prompt Engineering":
    st.title("🎓 Prompt Engineering Architecture & Concepts")
    st.markdown(
        "This section documents the theoretical concepts and exact prompt design techniques implemented "
        "in DocCheck for academic evaluation in a **20-Mark Prompt Engineering Course**."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Concept Accordions
    for key, concept in PROMPT_ENGINEERING_CONCEPTS.items():
        with st.expander(f"📌 {concept['title']}", expanded=True):
            st.markdown(f"**Theoretical Basis:** {concept['description']}")
            st.markdown("**Implementation Prompt Segment:**")
            st.code(concept["code_snippet"], language="markdown")

    st.markdown("---")
    st.subheader("🔍 Live Dynamic Prompt Inspector")
    st.markdown(
        "Inspect the exact dynamic prompts generated by DocCheck for the currently loaded document. "
        "Notice how role directives, context markers, negative constraints, and JSON schemas combine."
    )

    sample_text = (
        st.session_state.current_doc.raw_text
        if st.session_state.current_doc
        else "--- Page 1 ---\nSample Document Text for Prompt Demonstration..."
    )

    p_stage = st.selectbox(
        "Select Pipeline Stage to Inspect Prompt",
        options=[
            "Stage 1: Structured Extraction Prompt",
            "Stage 2: Verification & Audit Prompt",
            "Stage 3: Self-Review & Refinement Prompt",
        ],
    )

    if p_stage.startswith("Stage 1"):
        inspected_prompt = build_extraction_prompt(sample_text, "Automatic detection")
        st.code(inspected_prompt, language="markdown")
    elif p_stage.startswith("Stage 2"):
        dummy_extract = {
            "detected_document_type": "Invoice",
            "document_summary": "Apex Cloud invoice INV-2024-8842 for cloud services.",
            "type_specific_fields": [
                {"field_key": "total_amount", "value": "$12,475.00", "evidence": "TOTAL DUE: $12,475.00", "page_number": 1}
            ],
        }
        inspected_prompt = build_verification_prompt(sample_text, dummy_extract, "Invoice", config.EXPECTED_FIELDS_BY_TYPE["Invoice"])
        st.code(inspected_prompt, language="markdown")
    else:
        dummy_extract = {"detected_document_type": "Agreement"}
        dummy_verif = {"missing_fields": [{"field_or_claim": "Termination Conditions", "severity": "Medium"}]}
        inspected_prompt = build_self_review_prompt(sample_text, dummy_extract, dummy_verif)
        st.code(inspected_prompt, language="markdown")

