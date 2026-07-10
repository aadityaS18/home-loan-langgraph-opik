"""
Streamlit UI for Agent-Driven Home Loan Origination.

Important:
- UI does not control the loan flow.
- UI only sends user message + Application ID/thread ID.
- Agent decides whether to answer, update state, call tools, run assessment, or close conversation.
"""

import os
from typing import Any

import opik
import streamlit as st
from dotenv import load_dotenv

from agent.conversation_store import load_conversation_state
from agent.tool_calling_loan_agent import create_thread_id, run_agentic_loan_turn


load_dotenv()

OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


st.set_page_config(
    page_title="Agent-Driven Home Loan Origination",
    page_icon="🏠",
    layout="wide",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main {
            background-color: #f8fafc;
        }

        .metric-card {
            padding: 1rem;
            border-radius: 0.75rem;
            background: white;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
            margin-bottom: 0.75rem;
        }

        .metric-label {
            color: #6b7280;
            font-size: 0.85rem;
            margin-bottom: 0.25rem;
        }

        .metric-value {
            color: #111827;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .section-card {
            padding: 1.25rem;
            border-radius: 0.9rem;
            background: white;
            border: 1px solid #e5e7eb;
            margin-bottom: 1rem;
        }

        .small-muted {
            color: #6b7280;
            font-size: 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def create_empty_ui_state(thread_id: str) -> dict[str, Any]:
    return {
        "thread_id": thread_id,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "Hi, I can help with home loan questions or start a loan "
                    "application. You can ask me something like 'what documents "
                    "are required?' or tell me if you want to start a home loan application."
                ),
            }
        ],
        "application": {},
        "missing_fields": [],
        "assessment_result": None,
        "is_ready_for_assessment": False,
        "conversation_closed": False,
        "last_agent_action": "",
        "tool_trace": [],
    }


def initialize_session_state() -> None:
    if "thread_id" not in st.session_state:
        thread_id = create_thread_id()
        st.session_state.thread_id = thread_id
        st.session_state.loan_state = create_empty_ui_state(thread_id)

    if "loan_state" not in st.session_state:
        st.session_state.loan_state = create_empty_ui_state(st.session_state.thread_id)


@opik.track(
    name="streamlit_agent_tool_calling_chat_turn",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def process_chat_turn(
    user_message: str,
    thread_id: str,
) -> dict[str, Any]:
    return run_agentic_loan_turn(
        thread_id=thread_id,
        user_message=user_message,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Application Session")

        st.caption("Use this Application ID to resume the same conversation later.")

        current_thread_id = st.session_state.thread_id

        st.text_input(
            "Current Application ID",
            value=current_thread_id,
            disabled=True,
        )

        st.divider()

        if st.button("Start New Application", use_container_width=True):
            new_thread_id = create_thread_id()
            st.session_state.thread_id = new_thread_id
            st.session_state.loan_state = create_empty_ui_state(new_thread_id)
            st.rerun()

        st.subheader("Resume Application")

        resume_thread_id = st.text_input(
            "Enter Application ID",
            placeholder="loan-thread-xxxxxxxx",
        )

        if st.button("Resume", use_container_width=True):
            if not resume_thread_id.strip():
                st.warning("Please enter an Application ID.")
            else:
                saved_state = load_conversation_state(resume_thread_id.strip())

                if saved_state:
                    st.session_state.thread_id = resume_thread_id.strip()
                    st.session_state.loan_state = saved_state
                    st.success("Application resumed.")
                    st.rerun()
                else:
                    st.error("No saved conversation found for this Application ID.")

        st.divider()

        state = st.session_state.loan_state
        application = state.get("application", {})
        missing_fields = state.get("missing_fields", [])
        assessment_result = state.get("assessment_result")
        conversation_closed = state.get("conversation_closed", False)

        st.subheader("Agent State")

        st.write("Last agent action:")
        st.code(state.get("last_agent_action", "None") or "None")

        if conversation_closed:
            st.info("Conversation closed")

        if assessment_result:
            st.success("Assessment completed")

        st.subheader("Collected Application Data")

        if application:
            st.json(application)
        else:
            st.caption("No application details collected yet.")

        st.subheader("Missing Fields")

        if missing_fields:
            st.write(missing_fields)
        else:
            st.caption("No missing fields currently reported by the tool.")

        st.subheader("Tool Trace")

        tool_trace = state.get("tool_trace", [])

        if tool_trace:
            for index, item in enumerate(tool_trace[-5:], start=1):
                with st.expander(f"Tool call {index}: {item.get('action', 'unknown')}"):
                    st.json(item)
        else:
            st.caption("No tools called yet.")


def render_chat_messages() -> None:
    messages = st.session_state.loan_state.get("messages", [])

    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")

        with st.chat_message(role):
            st.markdown(content)


def get_nested_value(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def render_metric_card(label: str, value: Any, help_text: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="small-muted">{help_text or ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_assessment_result() -> None:
    result = st.session_state.loan_state.get("assessment_result")

    if not result:
        return

    st.divider()

    st.subheader("Loan Eligibility Result")

    st.caption(
        "Initial assessment completed using EMI, DTI, FOIR, LTV, KYC, CIBIL and document checks."
    )

    assessment = result.get("assessment", {})
    financial = result.get("financial_metrics", {})
    documents = result.get("documents", {})
    kyc = result.get("kyc", {})
    cibil = result.get("cibil", {})

    decision = str(assessment.get("decision", "unknown")).replace("_", " ").title()
    risk_level = str(assessment.get("risk_level", "unknown")).replace("_", " ").title()

    kyc_status = str(kyc.get("kyc_status", "unknown")).replace("_", " ").title()
    cibil_status = str(cibil.get("cibil_status", "unknown")).replace("_", " ").title()
    document_status = str(documents.get("document_status", "unknown")).replace(
        "_", " "
    ).title()

    proposed_emi = financial.get("proposed_emi", 0)
    dti_ratio = financial.get("dti_ratio", 0)
    foir_ratio = financial.get("foir_ratio", 0)
    ltv_ratio = financial.get("ltv_ratio", 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Decision", decision, "Initial loan outcome")

    with col2:
        render_metric_card("Risk Level", risk_level, "Underwriting risk")

    with col3:
        render_metric_card("KYC Status", kyc_status, "Identity verification")

    with col4:
        render_metric_card("CIBIL Status", cibil_status, "Credit profile")

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        render_metric_card(
            "Estimated EMI",
            f"₹{float(proposed_emi):,.2f}",
            "Monthly repayment",
        )

    with col6:
        render_metric_card(
            "DTI Ratio",
            f"{dti_ratio}%",
            "Existing debt burden",
        )

    with col7:
        render_metric_card(
            "FOIR Ratio",
            f"{foir_ratio}%",
            "Total obligation ratio",
        )

    with col8:
        render_metric_card(
            "LTV Ratio",
            f"{ltv_ratio}%",
            "Loan vs property value",
        )

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Why this decision was made")

    reasons = assessment.get("decision_reasons", [])

    if reasons:
        for reason in reasons:
            st.write(f"- {reason}")
    else:
        st.write("Applicant meets the current prototype assessment criteria.")

    risk_flags = assessment.get("risk_flags", [])

    st.subheader("Risk Flags")

    if risk_flags:
        for flag in risk_flags:
            st.warning(str(flag).replace("_", " ").title())
    else:
        st.success("No major risk flags found.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Document Review")

    st.write(f"Document Status: **{document_status}**")

    missing_documents = documents.get("missing_documents", [])

    if missing_documents:
        st.warning("Missing documents:")
        for document in missing_documents:
            st.write(f"- {str(document).replace('_', ' ').title()}")
    else:
        st.success("No missing documents.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Recommended Next Steps")

    next_steps = assessment.get("recommended_next_steps", [])

    if next_steps:
        for step in next_steps:
            st.write(f"- {step}")
    else:
        st.write("Proceed to detailed verification and final lender review.")

    st.caption(
        "This is an initial eligibility assessment only. "
        "It is not a final loan sanction or disbursement decision."
    )

    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    initialize_session_state()
    inject_css()

    st.title("🏠 Agent-Driven Home Loan Origination")

    st.caption(
        "The UI only sends a message and Application ID. "
        "The agent decides whether to answer a question, collect details, "
        "call tools, run the assessment, or close the conversation."
    )

    render_sidebar()
    render_chat_messages()
    render_assessment_result()

    result_exists = st.session_state.loan_state.get("assessment_result") is not None
    conversation_closed = st.session_state.loan_state.get("conversation_closed", False)

    if result_exists and not conversation_closed:
        st.success(
            "Assessment is complete. You can still ask follow-up questions, "
            "ask about the result, or type 'finish' to close this conversation."
        )

    if conversation_closed:
        st.success(
            "This conversation is closed. Start a new application or resume another "
            "Application ID from the sidebar."
        )
        return

    user_message = st.chat_input(
        "Ask a home-loan question, continue the application, or type 'finish'..."
    )

    if user_message:
        with st.spinner("Agent is thinking and deciding whether to call tools..."):
            try:
                result = process_chat_turn(
                    user_message=user_message,
                    thread_id=st.session_state.thread_id,
                )

                st.session_state.loan_state = result["state"]
                st.rerun()

            except Exception as exc:
                st.error("Something went wrong while processing this message.")
                st.exception(exc)


if __name__ == "__main__":
    main()