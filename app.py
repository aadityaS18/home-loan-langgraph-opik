"""
Streamlit chatbot UI for Conversational Home Loan Origination.

Flow:
1. User chats naturally.
2. LangGraph extracts fields using Groq.
3. Application state updates.
4. Agent asks the next missing question.
5. Once complete, home loan assessment runs.
6. Opik traces every chat turn and calculation.
"""

import os
import re
import uuid
from html import escape
from typing import Any

from dotenv import load_dotenv

load_dotenv()

import opik
import streamlit as st

from agent.conversational_loan_journey import (
    REQUIRED_FIELDS,
    build_conversational_loan_graph,
)


OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


st.set_page_config(
    page_title="Home Loan Origination Chatbot",
    page_icon="🏠",
    layout="wide",
)


@st.cache_resource
def get_graph():
    """Build LangGraph once for Streamlit."""
    return build_conversational_loan_graph()


def create_thread_id() -> str:
    """Create a new conversation thread id."""
    return f"loan-thread-{uuid.uuid4().hex[:8]}"


def create_initial_state() -> dict[str, Any]:
    """Create initial chatbot state."""

    return {
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "Hi, I can help you start a home loan application. "
                    "What loan amount are you looking for?"
                ),
            }
        ],
        "application": {},
        "missing_fields": REQUIRED_FIELDS.copy(),
        "validation_errors": [],
        "last_extracted_fields": {},
        "assessment_result": None,
        "is_ready_for_assessment": False,
    }


def initialize_session_state() -> None:
    """Initialize Streamlit session state."""

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = create_thread_id()

    if "loan_state" not in st.session_state:
        st.session_state.loan_state = create_initial_state()


def reset_conversation() -> None:
    """Reset conversation state."""

    st.session_state.thread_id = create_thread_id()
    st.session_state.loan_state = create_initial_state()


@opik.track(
    name="streamlit_conversational_chat_turn",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def process_chat_turn(
    user_message: str,
    current_state: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    """Process one chat turn through LangGraph and log it to Opik."""

    graph = get_graph()

    state = {
        **current_state,
        "latest_user_message": user_message,
        "thread_id": thread_id,
    }

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    return graph.invoke(state, config=config)


def inject_css() -> None:
    """Inject custom CSS for cleaner result cards."""

    st.markdown(
        """
        <style>
            .result-banner {
                padding: 22px 26px;
                border-radius: 18px;
                border: 1px solid rgba(255,255,255,0.14);
                background: linear-gradient(135deg, rgba(31,41,55,0.95), rgba(17,24,39,0.95));
                margin-top: 24px;
                margin-bottom: 20px;
            }

            .result-title {
                font-size: 34px;
                font-weight: 800;
                margin-bottom: 8px;
            }

            .result-subtitle {
                font-size: 16px;
                opacity: 0.85;
            }

            .loan-card {
                min-height: 132px;
                padding: 18px 20px;
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.12);
                background: rgba(31,41,55,0.75);
                margin-bottom: 12px;
            }

            .loan-card-title {
                font-size: 14px;
                font-weight: 600;
                opacity: 0.78;
                margin-bottom: 10px;
            }

            .loan-card-value {
                font-size: 25px;
                font-weight: 800;
                line-height: 1.15;
                word-break: normal;
                white-space: normal;
            }

            .loan-card-subtitle {
                font-size: 13px;
                opacity: 0.72;
                margin-top: 8px;
            }

            .status-good {
                border-left: 6px solid #22c55e;
            }

            .status-review {
                border-left: 6px solid #f59e0b;
            }

            .status-bad {
                border-left: 6px solid #ef4444;
            }

            .number-card {
                border-left: 6px solid #3b82f6;
            }

            .pill {
                display: inline-block;
                padding: 8px 13px;
                border-radius: 999px;
                margin: 5px 7px 5px 0;
                background: rgba(245,158,11,0.16);
                border: 1px solid rgba(245,158,11,0.45);
                font-weight: 700;
                font-size: 15px;
            }

            .next-step-box {
                padding: 14px 18px;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.10);
                background: rgba(31,41,55,0.55);
                margin-bottom: 10px;
            }

            .small-muted {
                font-size: 13px;
                opacity: 0.7;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_status(value: Any) -> str:
    """Convert snake_case values into readable labels."""

    if value is None:
        return "N/A"

    return str(value).replace("_", " ").title()


def format_money(value: Any) -> str:
    """Format money safely."""

    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def format_percent(value: Any) -> str:
    """Format percentage safely."""

    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_document_name(document: Any) -> str:
    """Format document key into readable document name."""

    document_map = {
        "pan_card": "PAN Card",
        "id_proof": "ID Proof",
        "address_proof": "Address Proof",
        "bank_statement": "Bank Statement",
        "property_title_deed": "Property Title Deed",
        "sale_agreement": "Sale Agreement",
        "salary_slips": "Salary Slips",
        "form_16": "Form 16",
        "employment_proof": "Employment Proof",
        "builder_noc": "Builder NOC",
        "approved_building_plan": "Approved Building Plan",
    }

    return document_map.get(str(document), str(document).replace("_", " ").title())


def format_action_text(action: Any) -> str:
    """Clean backend recommended action text for UI display."""

    text = str(action)

    document_keys = [
        "pan_card",
        "id_proof",
        "address_proof",
        "bank_statement",
        "property_title_deed",
        "sale_agreement",
        "salary_slips",
        "form_16",
        "employment_proof",
        "builder_noc",
        "approved_building_plan",
    ]

    for document_key in document_keys:
        text = text.replace(document_key, format_document_name(document_key))

    def replace_amount(match: re.Match) -> str:
        raw_number = match.group(1)

        try:
            return f"approximately {format_money(float(raw_number))}"
        except ValueError:
            return match.group(0)

    text = re.sub(
        r"approximately\s+([0-9]+(?:\.[0-9]+)?)",
        replace_amount,
        text,
        flags=re.IGNORECASE,
    )

    return text


def get_status_class(value: Any) -> str:
    """Map value to UI style class."""

    text = str(value).lower()

    if any(
        word in text
        for word in [
            "approved",
            "eligible",
            "verified",
            "complete",
            "excellent",
            "acceptable",
            "low",
        ]
    ):
        return "status-good"

    if any(
        word in text
        for word in [
            "reject",
            "poor",
            "high",
            "incomplete",
            "missing",
        ]
    ):
        return "status-bad"

    return "status-review"


def render_badge_card(title: str, value: Any, subtitle: str = "") -> None:
    """Render status card without st.metric truncation."""

    readable_value = format_status(value)
    css_class = get_status_class(value)

    st.markdown(
        f"""
        <div class="loan-card {css_class}">
            <div class="loan-card-title">{escape(title)}</div>
            <div class="loan-card-value">{escape(readable_value)}</div>
            <div class="loan-card-subtitle">{escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_number_card(title: str, value: str, subtitle: str = "") -> None:
    """Render numeric result card."""

    st.markdown(
        f"""
        <div class="loan-card number-card">
            <div class="loan-card-title">{escape(title)}</div>
            <div class="loan-card-value">{escape(value)}</div>
            <div class="loan-card-subtitle">{escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render sidebar showing state and tracing info."""

    state = st.session_state.loan_state
    application = state.get("application", {})
    missing_fields = state.get("missing_fields", [])

    with st.sidebar:
        st.header("Conversation State")

        st.caption("Thread ID")
        st.code(st.session_state.thread_id)

        if st.button("Reset Conversation"):
            reset_conversation()
            st.rerun()

        st.divider()

        st.subheader("Collected Details")

        if application:
            st.json(application)
        else:
            st.info("No details collected yet.")

        st.subheader("Missing Fields")

        if missing_fields:
            for field in missing_fields:
                st.write(f"- {field}")
        else:
            st.success("No missing fields. Ready for assessment.")

        st.divider()

        total_fields = len(REQUIRED_FIELDS)
        collected_fields = total_fields - len(missing_fields)
        progress = collected_fields / total_fields if total_fields else 0

        st.subheader("Application Progress")
        st.progress(progress)
        st.caption(f"{collected_fields}/{total_fields} required fields collected")

        st.divider()

        st.subheader("Opik Trace Names")
        st.code("streamlit_conversational_chat_turn")
        st.code("groq_extract_loan_fields")
        st.code("conversational_extract_and_update_state")
        st.code("conversational_home_loan_calculation")


def render_chat_messages() -> None:
    """Render chatbot messages."""

    messages = st.session_state.loan_state.get("messages", [])

    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")

        with st.chat_message(role):
            st.write(content)


def render_assessment_result() -> None:
    """Render final home-loan assessment in clean dashboard format."""

    result = st.session_state.loan_state.get("assessment_result")

    if not result:
        return

    assessment = result.get("assessment", {})
    financial = result.get("financial_metrics", {})
    documents = result.get("documents", {})
    kyc = result.get("kyc", {})
    cibil = result.get("cibil", {})

    decision = assessment.get("decision", "N/A")
    risk_level = assessment.get("risk_level", "N/A")

    st.divider()

    st.markdown(
        """
        <div class="result-banner">
            <div class="result-title">Loan Eligibility Result</div>
            <div class="result-subtitle">
                Initial assessment completed using EMI, DTI, FOIR, LTV, KYC, CIBIL and document checks.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_badge_card("Decision", decision, "Initial loan outcome")

    with c2:
        render_badge_card("Risk Level", risk_level, "Underwriting risk")

    with c3:
        render_badge_card(
            "KYC Status",
            kyc.get("kyc_status", "N/A"),
            "Identity verification",
        )

    with c4:
        render_badge_card(
            "CIBIL Status",
            cibil.get("cibil_status", "N/A"),
            "Credit profile",
        )

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        render_number_card(
            "Estimated EMI",
            format_money(financial.get("proposed_emi")),
            "Monthly repayment",
        )

    with f2:
        render_number_card(
            "DTI Ratio",
            format_percent(financial.get("dti_ratio")),
            "Existing debt burden",
        )

    with f3:
        render_number_card(
            "FOIR Ratio",
            format_percent(financial.get("foir_ratio")),
            "Total obligation ratio",
        )

    with f4:
        render_number_card(
            "LTV Ratio",
            format_percent(financial.get("ltv_ratio")),
            "Loan vs property value",
        )

    st.subheader("Why this decision was made")

    reasons = assessment.get("decision_reasons", [])

    if reasons:
        for reason in reasons:
            st.write(f"- {format_action_text(reason)}")
    else:
        st.success("Applicant meets the initial eligibility criteria.")

    st.subheader("Risk Flags")

    flags = assessment.get("risk_flags", [])

    if flags:
        for flag in flags:
            st.write(f"- {format_action_text(flag)}")
    else:
        st.success("No major risk flags found.")

    st.subheader("Document Review")

    document_status = documents.get("document_status", "N/A")
    missing_documents = documents.get("missing_documents", [])

    st.write(f"**Document Status:** {format_status(document_status)}")

    if missing_documents:
        pills = "".join(
            f'<span class="pill">{escape(format_document_name(doc))}</span>'
            for doc in missing_documents
        )

        st.markdown(pills, unsafe_allow_html=True)
    else:
        st.success("No missing documents.")

    st.subheader("Recommended Next Steps")

    recommended_actions = assessment.get("recommended_actions", [])
    clean_actions: list[str] = []

    if missing_documents:
        readable_missing_docs = ", ".join(
            format_document_name(doc) for doc in missing_documents
        )

        clean_actions.append(
            f"Ask the applicant to submit the missing documents: {readable_missing_docs}."
        )
        clean_actions.append(
            "Re-run document verification once the missing documents are uploaded."
        )

    for action in recommended_actions:
        action_text = format_action_text(action)

        # Avoid duplicate raw missing-document messages from backend
        if "missing documents" in action_text.lower():
            continue

        if action_text not in clean_actions:
            clean_actions.append(action_text)

    if clean_actions:
        for action in clean_actions:
            st.markdown(
                f"""
                <div class="next-step-box">
                    {escape(action)}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.write("- Proceed to loan officer review.")

    st.info(
        "This is an initial eligibility assessment only. "
        "It is not a final loan sanction or disbursement decision."
    )


def main() -> None:
    """Main Streamlit app."""

    initialize_session_state()
    inject_css()

    st.title("🏠 Conversational Home Loan Origination")

    st.caption(
        "The agent asks for loan details step by step, extracts answers using Groq, "
        "updates application state, and calculates EMI, DTI, FOIR, LTV and eligibility "
        "once enough information is collected."
    )

    render_sidebar()
    render_chat_messages()
    render_assessment_result()

    result_exists = st.session_state.loan_state.get("assessment_result") is not None

    if result_exists:
        st.success(
            "Assessment is complete. Reset the conversation from the sidebar to start a new application."
        )
        return

    user_message = st.chat_input("Type your reply here...")

    if user_message:
        with st.spinner("Agent is processing your response..."):
            try:
                new_state = process_chat_turn(
                    user_message=user_message,
                    current_state=st.session_state.loan_state,
                    thread_id=st.session_state.thread_id,
                )

                st.session_state.loan_state = new_state
                st.rerun()

            except Exception as exc:
                st.error("Something went wrong while processing this message.")
                st.exception(exc)


if __name__ == "__main__":
    main()