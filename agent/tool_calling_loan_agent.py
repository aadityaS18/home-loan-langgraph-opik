"""
Tool-calling agent for home loan origination.

The agent decides:
- whether to answer directly
- whether to update application state
- whether to check readiness
- whether to run assessment
- whether to close conversation

The backend only executes tools selected by the agent.
"""

import json
import os
import uuid
from string import Template
from typing import Any, TypedDict

import opik
from dotenv import load_dotenv

from agent.conversation_store import load_conversation_state, save_conversation_state
from agent.groq_model import get_groq_llm
from agent.loan_tools import (
    check_application_readiness_tool,
    close_conversation_tool,
    run_home_loan_assessment_tool,
    update_application_state_tool,
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


def clean_json_response(raw_response: str) -> str:
    text = raw_response.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()

    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


def parse_agent_decision(raw_response: str) -> dict[str, Any]:
    try:
        cleaned = clean_json_response(raw_response)
        parsed = json.loads(cleaned)

        if not isinstance(parsed, dict):
            raise ValueError("Agent response is not a JSON object.")

        return parsed

    except Exception:
        return {
            "action": "final_response",
            "tool_args": {},
            "assistant_message": (
                "I understood your message, but I had trouble selecting the next tool. "
                "Could you please rephrase that?"
            ),
        }


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
            str(doc).replace("_", " ").title() for doc in missing_documents
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
        "Would you like to ask anything else about this result, or should I finish this conversation?"
    )


def build_agent_prompt(
    state: AgenticLoanState,
    user_message: str,
    previous_tool_result: dict[str, Any] | None,
) -> str:
    recent_messages = state.get("messages", [])[-10:]

    current_thread_id = state.get("thread_id")
    current_application = json.dumps(state.get("application", {}), indent=2)
    current_missing_fields = json.dumps(state.get("missing_fields", []), indent=2)

    assessment_result = (
        json.dumps(state.get("assessment_result"), indent=2)
        if state.get("assessment_result")
        else "No assessment result yet"
    )

    previous_tool_result_text = (
        json.dumps(previous_tool_result, indent=2)
        if previous_tool_result
        else "No tool has been called yet in this turn."
    )

    prompt_template = Template(
        """
You are an agent-driven home loan origination assistant.

The conversation flow must be agent-driven.
Do not rely on a fixed question map.
Do not behave like a finite state machine.

You can decide to call tools. The backend will only execute the tool you choose.

Available actions:
1. update_application_state_tool
2. check_application_readiness_tool
3. run_home_loan_assessment_tool
4. close_conversation_tool
5. final_response

Tool descriptions:
- update_application_state_tool:
  Use when the user provides application details.
  Extract only details explicitly mentioned by the user.

- check_application_readiness_tool:
  Use when you need to know whether enough application information exists.

- run_home_loan_assessment_tool:
  Use only after readiness confirms the application is complete.

- close_conversation_tool:
  Use when assessment is complete and user says finish, done, close, end, no thanks, or nothing else.

- final_response:
  Use when you want to answer the user directly.

Important rules:
- You must decide the next action.
- The backend should not decide the next question.
- Ask natural follow-up questions based on current state and tool results.
- Do not ask for fields already present in the application unless user wants to correct them.
- Do not treat "documents available" as "documents submitted".
- Only set documents_confirmed true when user says submitted/uploaded/provided/attached/sent/shared documents.
- General home-loan questions should be answered directly.
- After assessment, answer follow-up questions about the result.
- Do not run the assessment again unless the user changes application details.
- Do not say "What would you like to do next?" during application collection.

After tool result rules:
- If previous_tool_result is from update_application_state_tool, respond naturally to the user.
- Mention the updated field briefly.
- Then ask the next useful application question based on missing_fields.
- Do not ask for a field that is already present in Current application state.
- If missing_fields is empty, call run_home_loan_assessment_tool.
- If previous_tool_result shows assessment_ran true, respond with the assessment summary.
- If previous_tool_result shows application is not ready, ask naturally for one important missing detail.

Post-assessment correction rule:
- If assessment_result already exists and user provides corrected or additional application details/documents, call update_application_state_tool.
- After updating, call check_application_readiness_tool.
- If ready_for_assessment is true, call run_home_loan_assessment_tool again.
- Do not just say it might be a technical issue.

Supported application fields:
loan_amount, monthly_income, credit_score, existing_emi, age,
employment_type, property_value, property_location,
pan_available, id_proof_available, address_proof_available,
submitted_documents, documents_confirmed

Money normalization:
- 45 lakhs = 4500000
- 56 lakhs = 5600000
- 5 lakhs = 500000
- 4 lakhs = 400000
- 2.3 crores = 23000000

Document availability rules:
- "I have PAN card available" means pan_available true.
- "I have ID proof available" means id_proof_available true.
- "I have address proof available" means address_proof_available true.
- "I have all documents available" means availability only, not submitted.

Document submission rules:
- If user says they submitted/uploaded/provided documents, submitted_documents MUST be a JSON list.
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

Current thread ID:
$current_thread_id

Current application state:
$current_application

Current missing fields from last tool check:
$current_missing_fields

Assessment result:
$assessment_result

Conversation closed:
$conversation_closed

Recent conversation:
$recent_conversation

Latest user message:
$user_message

Previous tool result:
$previous_tool_result_text

Return ONLY valid JSON in this exact structure:
{
  "action": "one of: update_application_state_tool, check_application_readiness_tool, run_home_loan_assessment_tool, close_conversation_tool, final_response",
  "tool_args": {
    "extracted_fields": {}
  },
  "assistant_message": "message to show user if action is final_response or close_conversation_tool"
}

Example:
User says: "What documents are required?"
Return:
{
  "action": "final_response",
  "tool_args": {},
  "assistant_message": "For a home loan, lenders usually ask for PAN card, identity proof, address proof, income proof, bank statements, and property documents such as sale agreement and title documents."
}

Example:
User says: "I want a loan of 45 lakhs"
Return:
{
  "action": "update_application_state_tool",
  "tool_args": {
    "extracted_fields": {
      "loan_amount": 4500000
    }
  },
  "assistant_message": ""
}

Example:
Previous tool result:
{
  "tool_name": "update_application_state_tool",
  "updated_fields": {
    "loan_amount": 4500000
  },
  "missing_fields": ["monthly_income", "credit_score"]
}

Return:
{
  "action": "final_response",
  "tool_args": {},
  "assistant_message": "I have noted the loan amount as ₹45,00,000. What is your monthly income?"
}

Example:
Previous tool result:
{
  "tool_name": "check_application_readiness_tool",
  "ready_for_assessment": true,
  "missing_fields": []
}

Return:
{
  "action": "run_home_loan_assessment_tool",
  "tool_args": {},
  "assistant_message": ""
}

Example:
User says: "I have submitted PAN card, ID proof, address proof, bank statement, property title deed and salary slips"

Return:
{
  "action": "update_application_state_tool",
  "tool_args": {
    "extracted_fields": {
      "submitted_documents": [
        "pan_card",
        "id_proof",
        "address_proof",
        "bank_statement",
        "property_title_deed",
        "salary_slips"
      ],
      "documents_confirmed": true
    }
  },
  "assistant_message": ""
}
"""
    )

    return prompt_template.safe_substitute(
        current_thread_id=current_thread_id,
        current_application=current_application,
        current_missing_fields=current_missing_fields,
        assessment_result=assessment_result,
        conversation_closed=state.get("conversation_closed", False),
        recent_conversation=json.dumps(recent_messages, indent=2),
        user_message=user_message,
        previous_tool_result_text=previous_tool_result_text,
    )


@opik.track(
    name="agentic_loan_agent_decision",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def ask_agent_for_next_action(
    state: AgenticLoanState,
    user_message: str,
    previous_tool_result: dict[str, Any] | None,
) -> dict[str, Any]:
    llm = get_groq_llm()
    prompt = build_agent_prompt(state, user_message, previous_tool_result)
    response = llm.invoke(prompt)
    raw_response = getattr(response, "content", str(response))
    return parse_agent_decision(raw_response)


def execute_agent_tool(
    action: str,
    tool_args: dict[str, Any],
    state: AgenticLoanState,
) -> tuple[AgenticLoanState, dict[str, Any]]:
    application = state.get("application", {})

    if action == "update_application_state_tool":
        extracted_fields = tool_args.get("extracted_fields", {})

        result = update_application_state_tool(
            current_application=application,
            extracted_fields=extracted_fields,
        )

        state["application"] = result["application"]
        state["missing_fields"] = result.get("missing_fields", [])
        state["is_ready_for_assessment"] = result.get("ready_for_assessment", False)

        return state, result

    if action == "check_application_readiness_tool":
        result = check_application_readiness_tool(
            application=state.get("application", {})
        )

        state["missing_fields"] = result["missing_fields"]
        state["is_ready_for_assessment"] = result["ready_for_assessment"]

        return state, result

    if action == "run_home_loan_assessment_tool":
        result = run_home_loan_assessment_tool(
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

        return state, result

    if action == "close_conversation_tool":
        result = close_conversation_tool()
        state["conversation_closed"] = True
        return state, result

    return state, {
        "tool_name": "unknown",
        "error": f"Unknown action: {action}",
    }


def build_safe_fallback_message(state: AgenticLoanState) -> str:
    missing_fields = state.get("missing_fields", [])

    if state.get("assessment_result"):
        return (
            "The assessment is complete. You can ask me about the result, FOIR, LTV, "
            "EMI, risk level, documents, or type 'finish' to close this conversation."
        )

    if missing_fields:
        next_field = missing_fields[0].replace("_", " ")

        friendly_questions = {
            "loan amount": "What loan amount are you looking for?",
            "monthly income": "What is your monthly income?",
            "credit score": "What is your credit score?",
            "existing emi": "What is your current monthly EMI for existing loans?",
            "age": "What is your age?",
            "employment type": "Are you salaried or self-employed?",
            "property value": "What is the value of the property?",
            "property location": "Where is the property located?",
            "pan available": "Do you have your PAN card available?",
            "id proof available": "Do you have an ID proof available?",
            "address proof available": "Do you have an address proof available?",
            "documents confirmed": (
                "Which documents have you submitted or uploaded for this application?"
            ),
        }

        return friendly_questions.get(
            next_field,
            f"To continue, please provide: {next_field}.",
        )

    return (
        "I have updated your application details. I can now check whether the "
        "application is ready for assessment."
    )


@opik.track(
    name="agentic_loan_turn",
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

    messages = state.get("messages", [])
    tool_trace = state.get("tool_trace", [])

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    state["messages"] = messages
    state["tool_trace"] = tool_trace

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

    previous_tool_result: dict[str, Any] | None = None
    assistant_message = ""

    for _ in range(6):
        decision = ask_agent_for_next_action(
            state=state,
            user_message=user_message,
            previous_tool_result=previous_tool_result,
        )

        action = decision.get("action", "final_response")
        tool_args = decision.get("tool_args", {}) or {}

        state["last_agent_action"] = action

        if action == "final_response":
            assistant_message = decision.get("assistant_message", "").strip()

            if not assistant_message:
                assistant_message = build_safe_fallback_message(state)

            break

        state, tool_result = execute_agent_tool(
            action=action,
            tool_args=tool_args,
            state=state,
        )

        tool_trace.append(
            {
                "action": action,
                "tool_args": tool_args,
                "tool_result": tool_result,
            }
        )

        state["tool_trace"] = tool_trace
        previous_tool_result = tool_result

        if action == "close_conversation_tool":
            assistant_message = decision.get("assistant_message", "").strip()

            if not assistant_message:
                assistant_message = (
                    "Got it. I’ll close this home loan conversation now. "
                    "You can start a new application or resume another Application ID from the sidebar."
                )

            break

        if action == "run_home_loan_assessment_tool" and tool_result.get("assessment_ran"):
            assistant_message = tool_result.get("assessment_summary", "")

            if not assistant_message:
                assistant_message = (
                    "I have completed the initial home loan assessment. "
                    "You can ask me about the result or type 'finish' to close."
                )

            break

    if not assistant_message:
        assistant_message = build_safe_fallback_message(state)

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