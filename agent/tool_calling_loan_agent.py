"""
Native create_agent based home loan origination agent.

Important:
- Uses create_agent native tool-calling.
- No custom JSON planner.
- No final_response tool/action.
- Direct answers are handled by create_agent default behaviour.
- Tools update:
  1. conversation state store
  2. PostgreSQL tables against application_id/thread_id
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, TypedDict

import opik
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agent.conversation_store import load_conversation_state, save_conversation_state
from agent.db_store import (
    mark_application_closed,
    save_assessment_result,
    save_tool_event,
    upsert_application_state,
)
from agent.groq_model import get_groq_llm
from agent.loan_tools import (
    check_application_readiness_tool as deterministic_check_readiness,
    close_conversation_tool as deterministic_close_conversation,
    run_home_loan_assessment_tool as deterministic_run_assessment,
    update_application_state_tool as deterministic_update_application,
)


load_dotenv()

OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


class AgenticLoanState(TypedDict, total=False):
    thread_id: str
    messages: list[dict[str, str]]
    application: dict[str, Any]
    missing_fields: list[str]
    assessment_result: dict[str, Any] | None
    is_ready_for_assessment: bool
    conversation_closed: bool
    last_agent_action: str
    tool_trace: list[dict[str, Any]]


class UpdateApplicationStateInput(BaseModel):
    loan_amount: int | None = Field(
        default=None,
        description="Loan amount in INR. Example: 56 lakhs = 5600000.",
    )
    monthly_income: int | None = Field(
        default=None,
        description="Monthly income in INR. Example: 4 lakhs = 400000.",
    )
    credit_score: int | None = Field(
        default=None,
        description="Applicant credit score.",
    )
    existing_emi: int | None = Field(
        default=None,
        description="Current monthly EMI obligations in INR.",
    )
    age: int | None = Field(
        default=None,
        description="Applicant age.",
    )
    employment_type: str | None = Field(
        default=None,
        description="Employment type, for example salaried or self-employed.",
    )
    property_value: int | None = Field(
        default=None,
        description="Property value in INR. Example: 2.3 crores = 23000000.",
    )
    property_location: str | None = Field(
        default=None,
        description="Property city/location.",
    )
    pan_available: bool | None = Field(
        default=None,
        description="Whether PAN card is available.",
    )
    id_proof_available: bool | None = Field(
        default=None,
        description="Whether ID proof is available.",
    )
    address_proof_available: bool | None = Field(
        default=None,
        description="Whether address proof is available.",
    )
    submitted_documents: list[str] | None = Field(
        default=None,
        description=(
            "Canonical submitted document IDs only. Use values like pan_card, "
            "id_proof, address_proof, bank_statement, property_title_deed, "
            "sale_agreement, salary_slips, form_16, employment_proof, "
            "builder_noc, approved_building_plan."
        ),
    )
    documents_confirmed: bool | None = Field(
        default=None,
        description=(
            "True only when user says documents were submitted, uploaded, "
            "provided, attached, sent, or shared."
        ),
    )


class EmptyToolInput(BaseModel):
    pass


def create_thread_id() -> str:
    return f"loan-thread-{uuid.uuid4().hex[:8]}"


def create_initial_agentic_state(thread_id: str) -> AgenticLoanState:
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


def safe_db_call(function_name: str, callback) -> None:
    try:
        callback()
    except Exception as error:
        print(f"[DB WARNING] {function_name} failed: {error}")


GENERAL_QUESTION_PATTERNS = [
    "what is ltv",
    "what does ltv",
    "what is foir",
    "what does foir",
    "what is emi",
    "how is emi",
    "what documents are required",
    "which documents are required",
    "documents required for a home loan",
    "home loan documents",
    "how does a home loan work",
    "what is a credit score",
]


def is_general_education_question(user_message: str, state: AgenticLoanState) -> bool:
    message = user_message.lower().strip()
    has_active_application = bool(state.get("application"))

    if has_active_application:
        return False

    return any(pattern in message for pattern in GENERAL_QUESTION_PATTERNS)


def direct_education_answer(user_message: str) -> str:
    message = user_message.lower().strip()

    if "document" in message:
        return (
            "Common documents required for a home loan usually include PAN card, "
            "ID proof, address proof, recent bank statements, income proof such as "
            "salary slips or Form 16, employment proof, and property documents such as "
            "property title deed, sale agreement, builder NOC, and approved building plan. "
            "The exact list can vary by lender and applicant type."
        )

    if "ltv" in message:
        return (
            "LTV stands for Loan-to-Value ratio. It compares the loan amount with the "
            "property value. For example, if a property is worth ₹1 crore and the lender "
            "offers ₹80 lakhs, the LTV is 80%. The remaining amount is usually paid as "
            "down payment."
        )

    if "foir" in message:
        return (
            "FOIR stands for Fixed Obligation to Income Ratio. It shows how much of your "
            "monthly income is already committed to EMIs and other fixed obligations. "
            "Lenders use it to judge whether you can afford a new loan EMI."
        )

    if "emi" in message:
        return (
            "EMI stands for Equated Monthly Instalment. It is the fixed monthly payment "
            "you make towards a loan, covering both principal and interest."
        )

    if "credit score" in message:
        return (
            "A credit score reflects your creditworthiness based on your repayment history, "
            "credit usage, and borrowing behaviour. A higher score usually improves home "
            "loan eligibility."
        )

    return (
        "I can answer general home loan questions directly. You can also tell me if you "
        "want to start a home loan application."
    )


def should_allow_assessment(state: AgenticLoanState) -> tuple[bool, list[str]]:
    application = state.get("application", {})

    required_fields = [
        "loan_amount",
        "monthly_income",
        "credit_score",
        "existing_emi",
        "age",
        "employment_type",
        "property_value",
        "property_location",
        "pan_available",
        "id_proof_available",
        "address_proof_available",
        "documents_confirmed",
    ]

    missing = []

    for field in required_fields:
        value = application.get(field)

        if field in {
            "pan_available",
            "id_proof_available",
            "address_proof_available",
            "documents_confirmed",
        }:
            if value is not True:
                missing.append(field)
        elif value in [None, ""]:
            missing.append(field)

    if not application.get("submitted_documents"):
        missing.append("submitted_documents")

    return len(missing) == 0, missing


def format_assessment_summary(result: dict[str, Any]) -> str:
    assessment = result["assessment"]
    financial = result["financial_metrics"]
    documents = result["documents"]
    kyc = result["kyc"]
    cibil = result["cibil"]

    decision_label = str(assessment["decision"]).replace("_", " ").title()
    risk_label = str(assessment["risk_level"]).replace("_", " ").title()
    document_status = str(documents["document_status"]).replace("_", " ").title()

    missing_documents = documents.get("missing_documents", [])

    if missing_documents:
        missing_docs_text = ", ".join(
            str(document).replace("_", " ").title()
            for document in missing_documents
        )
    else:
        missing_docs_text = "None"

    return (
        "I have completed the initial home loan assessment using affordability, "
        "credit, KYC and document checks.\n\n"
        f"Result: {decision_label}\n"
        f"Risk level: {risk_label}\n"
        f"Estimated EMI: ₹{financial['proposed_emi']:,.2f}\n"
        f"DTI ratio: {financial['dti_ratio']}%\n"
        f"FOIR ratio: {financial['foir_ratio']}%\n"
        f"LTV ratio: {financial['ltv_ratio']}%\n"
        f"KYC status: {kyc['kyc_status']}\n"
        f"CIBIL status: {cibil['cibil_status']}\n"
        f"Document status: {document_status}\n"
        f"Missing documents: {missing_docs_text}\n\n"
        "This is an initial eligibility assessment only, not a final loan sanction.\n\n"
        "You can ask me anything about this result, or type 'finish' to close the conversation."
    )


def build_system_prompt(state: AgenticLoanState) -> str:
    current_application = json.dumps(state.get("application", {}), indent=2)
    current_missing_fields = json.dumps(state.get("missing_fields", []), indent=2)

    assessment_result = (
        json.dumps(state.get("assessment_result"), indent=2)
        if state.get("assessment_result")
        else "No assessment result yet"
    )

    return f"""
You are an agent-driven home loan origination assistant.

CRITICAL TOOL POLICY:

GENERAL EDUCATION QUESTIONS:
If user asks a general question like:
- What is LTV?
- What documents are required for a home loan?
- What is FOIR?
- What is EMI?
- What is a credit score?

Then answer directly.
Do NOT call tools.
Do NOT update application state.
Do NOT check readiness.
Do NOT run assessment.
Do NOT create DB records.

APPLICATION UPDATE:
Only call update_application_state_tool when user provides applicant-specific details:
loan amount, income, credit score, EMI, age, employment type, property value,
property location, document availability, or submitted/uploaded documents.

ASSESSMENT RULE:
Never run assessment after only financial/property details.
Only run assessment after:
1. financial details are collected,
2. property details are collected,
3. PAN/ID/address proof availability is collected,
4. submitted/uploaded documents are collected,
5. check_application_readiness_tool confirms readiness.

DOCUMENT RULE:
Document availability is not document submission.
"I have PAN card available" means availability only.
Only submitted/uploaded/provided/attached/sent/shared means submitted.

For document availability only:
- call update_application_state_tool
- ask which documents have been submitted/uploaded
- do not run assessment

For submitted documents:
- call update_application_state_tool
- send only submitted_documents and documents_confirmed unless user explicitly corrects other fields
- use canonical document IDs only

Canonical document IDs:
pan_card
id_proof
address_proof
bank_statement
property_title_deed
sale_agreement
salary_slips
form_16
employment_proof
builder_noc
approved_building_plan
itr_returns
business_proof
profit_loss_statement

FINAL ANSWER RULE:
For assessment results, clearly say this is an initial eligibility assessment only,
not final sanction or guaranteed approval.

There is no final_response tool. Direct answers are your normal assistant output.

Current Application ID:
{state.get("thread_id")}

Current application state:
{current_application}

Current missing fields:
{current_missing_fields}

Current assessment result:
{assessment_result}

Registered tools:
1. update_application_state_tool
2. check_application_readiness_tool
3. run_home_loan_assessment_tool
4. close_conversation_tool

Money normalization:
56 lakhs = 5600000
4 lakhs = 400000
2.3 crores = 23000000
90 lakhs = 9000000
1.2 lakhs = 120000
1 crore = 10000000

Examples:
User: What documents are required for a home loan?
Correct: answer directly, no tool.

User: I want a loan of 56 lakhs, income 4 lakhs, credit score 700.
Correct: call update_application_state_tool, then ask for missing details/documents. Do not assess.

User: I have PAN card available, ID proof available, and address proof available.
Correct: call update_application_state_tool. Do not assess. Ask which documents are submitted/uploaded.

User: I have submitted PAN card, ID proof, address proof, bank statement, property title deed, sale agreement, salary slips, Form 16, employment proof, builder NOC and approved building plan.
Correct: call update_application_state_tool with submitted_documents and documents_confirmed=true.
Then call check_application_readiness_tool.
If ready, call run_home_loan_assessment_tool.

User: finish
Correct: call close_conversation_tool.
"""


def extract_message_content(message: Any) -> str:
    content = getattr(message, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    text_parts.append(str(text))
            else:
                text_parts.append(str(item))

        return "\n".join(text_parts)

    if isinstance(message, dict):
        return str(message.get("content", ""))

    return str(message)


def get_last_assistant_message(agent_result: dict[str, Any]) -> str:
    messages = agent_result.get("messages", [])

    for message in reversed(messages):
        message_type = getattr(message, "type", None)

        if message_type == "ai":
            content = extract_message_content(message)
            if content:
                return content

        if isinstance(message, dict):
            role = message.get("role")
            if role in {"assistant", "ai"}:
                content = str(message.get("content", ""))
                if content:
                    return content

    return ""


def persist_application_state(state: AgenticLoanState, status: str) -> None:
    safe_db_call(
        "upsert_application_state",
        lambda: upsert_application_state(
            application_id=state["thread_id"],
            application_data=state.get("application", {}),
            missing_fields=state.get("missing_fields", []),
            is_ready_for_assessment=state.get("is_ready_for_assessment", False),
            status=status,
        ),
    )


def persist_tool_event(
    state: AgenticLoanState,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> None:
    safe_db_call(
        "save_tool_event",
        lambda: save_tool_event(
            application_id=state["thread_id"],
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
        ),
    )


def clean_extracted_fields(raw_fields: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in raw_fields.items()
        if value is not None
    }


def create_home_loan_agent(state: AgenticLoanState):
    @tool(args_schema=UpdateApplicationStateInput)
    def update_application_state_tool(
        loan_amount: int | None = None,
        monthly_income: int | None = None,
        credit_score: int | None = None,
        existing_emi: int | None = None,
        age: int | None = None,
        employment_type: str | None = None,
        property_value: int | None = None,
        property_location: str | None = None,
        pan_available: bool | None = None,
        id_proof_available: bool | None = None,
        address_proof_available: bool | None = None,
        submitted_documents: list[str] | None = None,
        documents_confirmed: bool | None = None,
    ) -> str:
        """
        Update application state with applicant-specific fields.
        """
        extracted_fields = clean_extracted_fields(
            {
                "loan_amount": loan_amount,
                "monthly_income": monthly_income,
                "credit_score": credit_score,
                "existing_emi": existing_emi,
                "age": age,
                "employment_type": employment_type,
                "property_value": property_value,
                "property_location": property_location,
                "pan_available": pan_available,
                "id_proof_available": id_proof_available,
                "address_proof_available": address_proof_available,
                "submitted_documents": submitted_documents,
                "documents_confirmed": documents_confirmed,
            }
        )

        result = deterministic_update_application(
            current_application=state.get("application", {}),
            extracted_fields=extracted_fields,
        )

        state["application"] = result["application"]
        state["missing_fields"] = result.get("missing_fields", [])
        state["is_ready_for_assessment"] = result.get("ready_for_assessment", False)
        state["last_agent_action"] = "update_application_state_tool"

        trace_item = {
            "action": "update_application_state_tool",
            "tool_args": {"extracted_fields": extracted_fields},
            "tool_result": result,
        }

        state.setdefault("tool_trace", []).append(trace_item)
        save_conversation_state(state["thread_id"], state)

        persist_application_state(state=state, status="in_progress")

        persist_tool_event(
            state=state,
            tool_name="update_application_state_tool",
            tool_args={"extracted_fields": extracted_fields},
            tool_result=result,
        )

        return json.dumps(
            {
                "tool_name": "update_application_state_tool",
                "updated_fields": result.get("updated_fields", {}),
                "ready_for_assessment": result.get("ready_for_assessment", False),
                "missing_fields": result.get("missing_fields", []),
                "application": result.get("application", {}),
            },
            indent=2,
            default=str,
        )

    @tool(args_schema=EmptyToolInput)
    def check_application_readiness_tool() -> str:
        """
        Check whether current application is ready for assessment.
        """
        result = deterministic_check_readiness(
            application=state.get("application", {})
        )

        state["missing_fields"] = result.get("missing_fields", [])
        state["is_ready_for_assessment"] = result.get("ready_for_assessment", False)
        state["last_agent_action"] = "check_application_readiness_tool"

        trace_item = {
            "action": "check_application_readiness_tool",
            "tool_args": {},
            "tool_result": result,
        }

        state.setdefault("tool_trace", []).append(trace_item)
        save_conversation_state(state["thread_id"], state)

        persist_application_state(state=state, status="in_progress")

        persist_tool_event(
            state=state,
            tool_name="check_application_readiness_tool",
            tool_args={},
            tool_result=result,
        )

        return json.dumps(result, indent=2, default=str)

    @tool(args_schema=EmptyToolInput)
    def run_home_loan_assessment_tool() -> str:
        """
        Run deterministic assessment only after application is complete.
        """
        can_assess, missing_for_assessment = should_allow_assessment(state)

        if not can_assess:
            result = {
                "assessment_ran": False,
                "ready_for_assessment": False,
                "missing_fields": missing_for_assessment,
                "message": (
                    "Assessment cannot be run yet. Required applicant details, "
                    "document availability, and submitted documents must be collected first."
                ),
            }

            state["missing_fields"] = missing_for_assessment
            state["is_ready_for_assessment"] = False
            state["last_agent_action"] = "run_home_loan_assessment_tool_blocked"

            trace_item = {
                "action": "run_home_loan_assessment_tool",
                "tool_args": {},
                "tool_result": result,
            }

            state.setdefault("tool_trace", []).append(trace_item)
            save_conversation_state(state["thread_id"], state)

            persist_application_state(state=state, status="in_progress")

            persist_tool_event(
                state=state,
                tool_name="run_home_loan_assessment_tool",
                tool_args={},
                tool_result=result,
            )

            return json.dumps(result, indent=2, default=str)

        result = deterministic_run_assessment(
            application=state.get("application", {})
        )

        if result.get("assessment_ran"):
            state["application"] = result["application"]
            state["assessment_result"] = result["assessment_result"]
            state["missing_fields"] = []
            state["is_ready_for_assessment"] = True

            result["assessment_summary"] = format_assessment_summary(
                result["assessment_result"]
            )
        else:
            state["missing_fields"] = result.get("missing_fields", [])
            state["is_ready_for_assessment"] = False

        state["last_agent_action"] = "run_home_loan_assessment_tool"

        trace_item = {
            "action": "run_home_loan_assessment_tool",
            "tool_args": {},
            "tool_result": result,
        }

        state.setdefault("tool_trace", []).append(trace_item)
        save_conversation_state(state["thread_id"], state)

        persist_application_state(
            state=state,
            status="assessed" if result.get("assessment_ran") else "in_progress",
        )

        if result.get("assessment_ran"):
            safe_db_call(
                "save_assessment_result",
                lambda: save_assessment_result(
                    application_id=state["thread_id"],
                    assessment_result=result["assessment_result"],
                ),
            )

        persist_tool_event(
            state=state,
            tool_name="run_home_loan_assessment_tool",
            tool_args={},
            tool_result=result,
        )

        return json.dumps(result, indent=2, default=str)

    @tool(args_schema=EmptyToolInput)
    def close_conversation_tool() -> str:
        """
        Close the current conversation/application.
        """
        result = deterministic_close_conversation()

        state["conversation_closed"] = True
        state["last_agent_action"] = "close_conversation_tool"

        trace_item = {
            "action": "close_conversation_tool",
            "tool_args": {},
            "tool_result": result,
        }

        state.setdefault("tool_trace", []).append(trace_item)
        save_conversation_state(state["thread_id"], state)

        safe_db_call(
            "mark_application_closed",
            lambda: mark_application_closed(
                application_id=state["thread_id"],
            ),
        )

        persist_tool_event(
            state=state,
            tool_name="close_conversation_tool",
            tool_args={},
            tool_result=result,
        )

        return json.dumps(result, indent=2, default=str)

    tools = [
        update_application_state_tool,
        check_application_readiness_tool,
        run_home_loan_assessment_tool,
        close_conversation_tool,
    ]

    return create_agent(
        model=get_groq_llm(),
        tools=tools,
        system_prompt=build_system_prompt(state),
    )


@opik.track(
    name="create_agent_loan_turn",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def run_agentic_loan_turn(
    thread_id: str,
    user_message: str,
) -> dict[str, Any]:
    saved_state = load_conversation_state(thread_id)

    if saved_state:
        state: AgenticLoanState = saved_state
    else:
        state = create_initial_agentic_state(thread_id)

    state.setdefault("thread_id", thread_id)
    state.setdefault("messages", [])
    state.setdefault("application", {})
    state.setdefault("missing_fields", [])
    state.setdefault("assessment_result", None)
    state.setdefault("is_ready_for_assessment", False)
    state.setdefault("conversation_closed", False)
    state.setdefault("tool_trace", [])
    state.setdefault("last_agent_action", "")

    messages = state.get("messages", [])

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    state["messages"] = messages

    if is_general_education_question(user_message, state):
        assistant_message = direct_education_answer(user_message)

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message,
            }
        )

        state["messages"] = messages
        state["last_agent_action"] = "direct_response"
        save_conversation_state(thread_id, state)

        return {
            "thread_id": thread_id,
            "assistant_message": assistant_message,
            "messages": state.get("messages", []),
            "application": state.get("application", {}),
            "missing_fields": state.get("missing_fields", []),
            "assessment_result": state.get("assessment_result"),
            "is_ready_for_assessment": state.get("is_ready_for_assessment", False),
            "state": state,
        }

    if state.get("conversation_closed"):
        assistant_message = (
            "This conversation is already closed. You can start a new application "
            "or resume another Application ID from the sidebar."
        )

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message,
            }
        )

        state["messages"] = messages
        save_conversation_state(thread_id, state)

        return {
            "thread_id": thread_id,
            "assistant_message": assistant_message,
            "messages": state.get("messages", []),
            "application": state.get("application", {}),
            "missing_fields": state.get("missing_fields", []),
            "assessment_result": state.get("assessment_result"),
            "is_ready_for_assessment": state.get("is_ready_for_assessment", False),
            "state": state,
        }

    tool_trace_before = len(state.get("tool_trace", []))

    agent = create_home_loan_agent(state)

    agent_input_messages = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in state.get("messages", [])
        if message.get("role") in {"user", "assistant"}
    ]

    agent_result = agent.invoke(
        {
            "messages": agent_input_messages,
        }
    )

    assistant_message = get_last_assistant_message(agent_result)

    tool_trace_after = len(state.get("tool_trace", []))

    if tool_trace_after == tool_trace_before:
        state["last_agent_action"] = "direct_response"

    # IMPORTANT FIX:
    # After assessment runs, always return the deterministic assessment summary.
    # This prevents weak applicant cases from returning only a short disclaimer.
    if (
        state.get("assessment_result")
        and state.get("last_agent_action") == "run_home_loan_assessment_tool"
    ):
        assistant_message = format_assessment_summary(state["assessment_result"])

    elif not assistant_message:
        if state.get("assessment_result"):
            assistant_message = format_assessment_summary(state["assessment_result"])
        elif state.get("missing_fields"):
            missing_text = ", ".join(
                field.replace("_", " ")
                for field in state.get("missing_fields", [])[:5]
            )
            assistant_message = (
                f"I still need the following details before I can continue: {missing_text}. "
                "Please provide them when ready."
            )
        else:
            assistant_message = (
                "I have updated your home loan application. Please provide the next "
                "required detail so I can continue."
            )

    messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
        }
    )

    state["messages"] = messages
    save_conversation_state(thread_id, state)

    return {
        "thread_id": thread_id,
        "assistant_message": assistant_message,
        "messages": state.get("messages", []),
        "application": state.get("application", {}),
        "missing_fields": state.get("missing_fields", []),
        "assessment_result": state.get("assessment_result"),
        "is_ready_for_assessment": state.get("is_ready_for_assessment", False),
        "state": state,
    }