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

import json
import os
import uuid
from typing import Any, TypedDict

import opik
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool

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
    """
    DB writes should not crash the chat flow.
    If PostgreSQL has an issue, the app still continues using conversation state.
    """

    try:
        callback()
    except Exception as error:
        print(f"[DB WARNING] {function_name} failed: {error}")


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

The UI only sends the user message and Application ID.
You decide whether to answer directly, collect details, call tools, run assessment,
explain the result, or close the conversation.

Important design rule:
- Direct answers are handled by your default assistant behaviour.
- There is no final_response tool.
- Only call backend tools when an external or deterministic action is needed.

Current Application ID:
{state.get("thread_id")}

Current application state:
{current_application}

Current missing fields:
{current_missing_fields}

Current assessment result:
{assessment_result}

Your registered tools are:

1. update_application_state_tool
Use when the user provides application details such as loan amount, income,
credit score, EMI, age, employment type, property value, property location,
KYC availability, or submitted documents.

2. check_application_readiness_tool
Use when you need to check whether the application has all required fields
before assessment.

3. run_home_loan_assessment_tool
Use only when the application is ready for assessment.

4. close_conversation_tool
Use when the user says finish, done, close, end, no thanks, or says they have
no more questions.

Conversation rules:
- General home-loan questions should be answered directly without calling a tool.
- After assessment, answer follow-up questions directly unless the user changes application details.
- If the user changes details after assessment, call update_application_state_tool.
- Do not behave like a fixed finite state machine.
- Do not ask for fields already present unless the user wants to correct them.
- Ask natural follow-up questions based on the current application state.
- Do not treat "documents available" as "documents submitted".
- Only submitted/uploaded/provided/attached/sent/shared documents count as submitted documents.
- If application details are complete, check readiness and then run assessment.
- After running assessment, explain the assessment summary to the user.

Required application fields before assessment:
- loan_amount
- monthly_income
- credit_score
- existing_emi
- age
- employment_type
- property_value
- property_location
- pan_available
- id_proof_available
- address_proof_available
- documents_confirmed

Supported extracted fields:
- loan_amount
- monthly_income
- credit_score
- existing_emi
- age
- employment_type
- property_value
- property_location
- pan_available
- id_proof_available
- address_proof_available
- submitted_documents
- documents_confirmed

Money normalization:
- 56 lakhs = 5600000
- 4 lakhs = 400000
- 2.3 crores = 23000000
- 90 lakhs = 9000000
- 1.2 lakhs = 120000
- 1 crore = 10000000

Document availability rules:
- "I have PAN card available" means pan_available true.
- "I have ID proof available" means id_proof_available true.
- "I have address proof available" means address_proof_available true.
- "I have all documents available" means availability only, not submitted.

Document submission rules:
- If user says they submitted/uploaded/provided/attached/sent/shared documents,
  call update_application_state_tool.
- submitted_documents must be a list.
- Also set documents_confirmed true.
- Use canonical document names:
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

Examples of direct answer behaviour:
- User asks "What is LTV?" -> answer directly, no tool.
- User asks "What documents are required?" -> answer directly, no tool.
- User asks "Can you explain this result?" after assessment -> answer directly, no tool.

Examples of tool behaviour:
- User gives loan amount/income/credit score/property details -> call update_application_state_tool.
- User gives PAN/ID/address proof availability -> call update_application_state_tool.
- User submits documents -> call update_application_state_tool.
- Application looks complete -> call check_application_readiness_tool.
- Readiness is true -> call run_home_loan_assessment_tool.
- User says finish/done/close -> call close_conversation_tool.
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


def persist_application_state(
    state: AgenticLoanState,
    status: str,
) -> None:
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


def create_home_loan_agent(state: AgenticLoanState):
    """
    Creates a native create_agent instance with tools bound to the current
    Application ID/thread state.

    The agent decides when to call tools.
    The tools update state and persist to PostgreSQL against application_id.
    """

    @tool
    def update_application_state_tool(extracted_fields: dict[str, Any]) -> str:
        """
        Update the current loan application state using extracted user-provided fields.

        Use this tool when the user provides loan details, property details,
        KYC availability, or submitted documents.
        """

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
            "tool_args": {
                "extracted_fields": extracted_fields,
            },
            "tool_result": result,
        }

        state.setdefault("tool_trace", []).append(trace_item)

        save_conversation_state(state["thread_id"], state)

        persist_application_state(
            state=state,
            status="in_progress",
        )

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
        )

    @tool
    def check_application_readiness_tool() -> str:
        """
        Check whether the current application has all required fields before assessment.

        Use this tool before running the final home loan assessment.
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

        persist_application_state(
            state=state,
            status="in_progress",
        )

        persist_tool_event(
            state=state,
            tool_name="check_application_readiness_tool",
            tool_args={},
            tool_result=result,
        )

        return json.dumps(result, indent=2)

    @tool
    def run_home_loan_assessment_tool() -> str:
        """
        Run the deterministic home loan assessment after the application is complete.

        This checks EMI, DTI, FOIR, LTV, KYC, CIBIL/credit score,
        document completeness, risk level, and final loan decision.
        """

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

        return json.dumps(result, indent=2)

    @tool
    def close_conversation_tool() -> str:
        """
        Close the current home loan conversation/application thread.

        Use this when the user says finish, done, close, end, no thanks,
        or says they have no more questions.
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

        return json.dumps(result, indent=2)

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

    if not assistant_message:
        if state.get("assessment_result"):
            assistant_message = format_assessment_summary(state["assessment_result"])
        elif state.get("missing_fields"):
            next_missing = state["missing_fields"][0].replace("_", " ")
            assistant_message = f"Please provide your {next_missing} so I can continue."
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