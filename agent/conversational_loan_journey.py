"""
Conversational home loan journey.

Flow:
1. User replies naturally.
2. Groq extracts structured fields.
3. Application state is updated.
4. Agent asks the next missing question.
5. Document availability and submitted documents are collected conversationally.
6. Once all required fields are collected, the fixed home-loan assessment runs.
7. Final result is returned with EMI / DTI / FOIR / LTV / KYC / CIBIL / documents.
8. Opik traces extraction, state update and calculation.
"""

import os
from typing import Any, TypedDict

import opik
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from agent.controlled_assessment import run_controlled_home_loan_assessment
from agent.llm_extractor import extract_loan_fields_with_groq


load_dotenv()

OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


class LoanConversationState(TypedDict, total=False):
    thread_id: str
    messages: list[dict[str, str]]
    latest_user_message: str
    application: dict[str, Any]
    missing_fields: list[str]
    validation_errors: list[str]
    last_extracted_fields: dict[str, Any]
    assessment_result: dict[str, Any] | None
    is_ready_for_assessment: bool


REQUIRED_FIELDS = [
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


QUESTION_MAP = {
    "loan_amount": "What loan amount are you looking for?",
    "monthly_income": "What is your monthly income?",
    "credit_score": "What is your credit score?",
    "existing_emi": "How much existing EMI do you currently pay per month?",
    "age": "What is your age?",
    "employment_type": "Are you salaried or self-employed?",
    "property_value": "What is the estimated property value?",
    "property_location": "Where is the property located?",
    "pan_available": "Do you have a PAN card available?",
    "id_proof_available": "Do you have ID proof available?",
    "address_proof_available": "Do you have address proof available?",
    "documents_confirmed": (
        "Please tell me which documents you have already submitted. "
        "You can also mention anything not submitted. "
        "For example: 'I submitted PAN card, ID proof and bank statement, "
        "but I have not submitted builder NOC or approved building plan.' "
        "If you have not submitted any documents, say none."
    ),
}


DOCUMENT_ALIASES = {
    "pan": "pan_card",
    "pan card": "pan_card",
    "pancard": "pan_card",
    "id": "id_proof",
    "id proof": "id_proof",
    "identity proof": "id_proof",
    "aadhaar": "id_proof",
    "aadhar": "id_proof",
    "passport": "id_proof",
    "address": "address_proof",
    "address proof": "address_proof",
    "utility bill": "address_proof",
    "electricity bill": "address_proof",
    "bank statement": "bank_statement",
    "bank statements": "bank_statement",
    "property title": "property_title_deed",
    "property title deed": "property_title_deed",
    "title deed": "property_title_deed",
    "sale agreement": "sale_agreement",
    "salary slip": "salary_slips",
    "salary slips": "salary_slips",
    "form 16": "form_16",
    "form16": "form_16",
    "employment proof": "employment_proof",
    "builder noc": "builder_noc",
    "noc": "builder_noc",
    "approved building plan": "approved_building_plan",
    "building plan": "approved_building_plan",
}


CANONICAL_DOCUMENTS = {
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
}


def is_missing(value: Any) -> bool:
    """
    Check if a value should be treated as missing.

    Important:
    False is not missing because user may answer no to document availability.
    """

    return value is None or value == "" or value == []


def get_missing_fields(application: dict[str, Any]) -> list[str]:
    """Return all required fields still missing from application state."""

    missing_fields: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in application:
            missing_fields.append(field)
            continue

        value = application.get(field)

        if isinstance(value, bool):
            continue

        if is_missing(value):
            missing_fields.append(field)

    return missing_fields


def normalize_boolean(value: Any) -> bool | None:
    """Normalize yes/no answers."""

    if isinstance(value, bool):
        return value

    text = str(value).lower().strip()

    yes_values = [
        "yes",
        "y",
        "true",
        "available",
        "have",
        "i have",
        "uploaded",
        "submitted",
        "present",
    ]

    no_values = [
        "no",
        "n",
        "false",
        "not available",
        "missing",
        "dont have",
        "don't have",
        "do not have",
        "not uploaded",
        "not submitted",
    ]

    if text in yes_values:
        return True

    if text in no_values:
        return False

    if any(term in text for term in yes_values):
        return True

    if any(term in text for term in no_values):
        return False

    return None


def extract_document_names(raw_text: str) -> list[str]:
    """Extract all document names mentioned in text."""

    documents: list[str] = []

    for phrase, canonical_name in DOCUMENT_ALIASES.items():
        if phrase in raw_text and canonical_name not in documents:
            documents.append(canonical_name)

    for canonical_name in CANONICAL_DOCUMENTS:
        if canonical_name in raw_text and canonical_name not in documents:
            documents.append(canonical_name)

    return documents


def extract_negative_documents(raw_text: str) -> list[str]:
    """
    Extract documents that user says are not submitted.

    Example:
    'I submitted PAN card, but I have not submitted builder NOC'
    -> ['builder_noc']
    """

    negative_markers = [
        "i have not submitted",
        "i haven't submitted",
        "i havent submitted",
        "have not submitted",
        "haven't submitted",
        "havent submitted",
        "not submitted",
        "not uploaded",
        "missing",
        "dont have",
        "don't have",
        "do not have",
    ]

    negative_parts: list[str] = []

    for marker in negative_markers:
        if marker in raw_text:
            after_marker = raw_text.split(marker, 1)[1]

            stop_markers = [
                " but i submitted",
                " but submitted",
                " but i have submitted",
                ".",
                ";",
            ]

            for stop_marker in stop_markers:
                if stop_marker in after_marker:
                    after_marker = after_marker.split(stop_marker, 1)[0]

            negative_parts.append(after_marker)

    if not negative_parts:
        return []

    return extract_document_names(" ".join(negative_parts))


def normalize_documents(value: Any) -> list[str]:
    """
    Normalize document names into canonical document keys.

    If user mentions both submitted and not submitted documents,
    only submitted documents are kept.
    """

    if value is None:
        return []

    if isinstance(value, list):
        raw_text = " ".join(str(item).lower().strip() for item in value)
    else:
        raw_text = str(value).lower().strip()

    no_document_phrases = [
        "none",
        "nothing",
        "no documents",
        "no docs",
        "i have not submitted any documents",
        "i havent submitted any documents",
        "haven't submitted any documents",
        "not submitted any documents",
    ]

    if raw_text in no_document_phrases:
        return []

    all_mentioned_documents = extract_document_names(raw_text)
    negative_documents = extract_negative_documents(raw_text)

    submitted_documents = [
        document
        for document in all_mentioned_documents
        if document not in negative_documents
    ]

    return submitted_documents


def validate_and_normalize_fields(
    extracted: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Validate and normalize fields extracted by Groq."""

    valid: dict[str, Any] = {}
    errors: list[str] = []

    for field, value in extracted.items():
        try:
            if field in [
                "loan_amount",
                "monthly_income",
                "existing_emi",
                "property_value",
                "interest_rate",
            ]:
                numeric_value = float(value)

                if numeric_value < 0:
                    errors.append(f"{field} cannot be negative.")
                    continue

                valid[field] = numeric_value

            elif field in ["age", "credit_score", "tenure_years", "property_age"]:
                int_value = int(value)

                if field == "age" and not 18 <= int_value <= 75:
                    errors.append("Age should be between 18 and 75.")
                    continue

                if field == "credit_score" and not 300 <= int_value <= 900:
                    errors.append("Credit score should be between 300 and 900.")
                    continue

                if field == "tenure_years" and not 1 <= int_value <= 40:
                    errors.append("Tenure should be between 1 and 40 years.")
                    continue

                valid[field] = int_value

            elif field == "employment_type":
                text = str(value).lower().strip().replace("_", "-")

                if text not in ["salaried", "self-employed"]:
                    errors.append("Employment type should be salaried or self-employed.")
                    continue

                valid[field] = text

            elif field == "property_location":
                valid[field] = str(value).strip()

            elif field in [
                "pan_available",
                "id_proof_available",
                "address_proof_available",
            ]:
                bool_value = normalize_boolean(value)

                if bool_value is None:
                    errors.append(f"{field} should be answered as yes or no.")
                    continue

                valid[field] = bool_value

            elif field == "submitted_documents":
                valid["submitted_documents"] = normalize_documents(value)
                valid["documents_confirmed"] = True

            elif field == "documents_confirmed":
                bool_value = normalize_boolean(value)

                if bool_value is None:
                    valid["documents_confirmed"] = True
                else:
                    valid["documents_confirmed"] = bool_value

            else:
                valid[field] = value

        except (TypeError, ValueError):
            errors.append(f"Could not understand value for {field}.")

    if "submitted_documents" in valid:
        valid["documents_confirmed"] = True

    return valid, errors


@opik.track(
    name="conversational_extract_and_update_state",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def extract_and_update_state(state: LoanConversationState) -> LoanConversationState:
    """
    Extract user answer using Groq, validate it, and update application state.
    """

    messages = state.get("messages", [])
    application = state.get("application", {})
    latest_user_message = state.get("latest_user_message", "")

    messages.append(
        {
            "role": "user",
            "content": latest_user_message,
        }
    )

    current_missing = get_missing_fields(application)

    extracted = extract_loan_fields_with_groq(
        user_message=latest_user_message,
        current_application=application,
        current_missing_fields=current_missing,
    )

    valid_fields, validation_errors = validate_and_normalize_fields(extracted)

    application.update(valid_fields)

    missing_fields = get_missing_fields(application)

    return {
        **state,
        "messages": messages,
        "application": application,
        "missing_fields": missing_fields,
        "validation_errors": validation_errors,
        "last_extracted_fields": valid_fields,
        "is_ready_for_assessment": len(missing_fields) == 0,
    }


def decide_next_step(state: LoanConversationState) -> LoanConversationState:
    """Decide if the agent should ask another question or run calculation."""

    application = state.get("application", {})
    missing_fields = get_missing_fields(application)

    return {
        **state,
        "missing_fields": missing_fields,
        "is_ready_for_assessment": len(missing_fields) == 0,
    }


def ask_next_question(state: LoanConversationState) -> LoanConversationState:
    """Ask the next missing question."""

    messages = state.get("messages", [])
    missing_fields = state.get("missing_fields", [])
    validation_errors = state.get("validation_errors", [])
    last_extracted_fields = state.get("last_extracted_fields", {})

    if not missing_fields:
        assistant_message = (
            "Thanks. I have enough information now. I will calculate affordability."
        )
    else:
        if validation_errors:
            prefix = "I could not validate that answer. " + " ".join(validation_errors)
        elif not last_extracted_fields:
            prefix = "I could not clearly capture that detail."
        else:
            prefix = "Got it."

        next_field = missing_fields[0]
        question = QUESTION_MAP.get(next_field, f"Please provide {next_field}.")
        assistant_message = f"{prefix} {question}"

    messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
        }
    )

    return {
        **state,
        "messages": messages,
    }


def build_application_for_assessment(application: dict[str, Any]) -> dict[str, Any]:
    """
    Build the full application payload expected by the existing assessment flow.

    Document fields are not defaulted to uploaded.
    They come from the conversation.
    """

    return {
        "name": application.get("name", "Conversational Applicant"),
        "age": int(application["age"]),
        "employment_type": application["employment_type"],
        "monthly_income": float(application["monthly_income"]),
        "work_experience_years": float(application.get("work_experience_years", 5)),
        "credit_score": int(application["credit_score"]),
        "existing_emi": float(application["existing_emi"]),
        "loan_amount": float(application["loan_amount"]),
        "interest_rate": float(application.get("interest_rate", 8.5)),
        "tenure_years": int(application.get("tenure_years", 20)),
        "loan_purpose": application.get("loan_purpose", "purchase"),
        "property_value": float(application["property_value"]),
        "property_type": application.get("property_type", "apartment"),
        "property_location": application["property_location"],
        "property_age": int(application.get("property_age", 3)),
        "construction_status": application.get("construction_status", "ready_to_move"),
        "legal_clearance_status": application.get("legal_clearance_status", "clear"),
        "valuation_status": application.get("valuation_status", "clear"),
        "pan_available": bool(application["pan_available"]),
        "id_proof_available": bool(application["id_proof_available"]),
        "address_proof_available": bool(application["address_proof_available"]),
        "submitted_documents": application.get("submitted_documents", []),
    }


@opik.track(
    name="conversational_home_loan_calculation",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def run_assessment(state: LoanConversationState) -> LoanConversationState:
    """
    Run final home-loan assessment after all required fields are collected.
    """

    messages = state.get("messages", [])
    application = state.get("application", {})

    final_application = build_application_for_assessment(application)
    result = run_controlled_home_loan_assessment(final_application)

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
        missing_docs_text = ", ".join(missing_documents)
    else:
        missing_docs_text = "None"

    assistant_message = (
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
        "This is an initial eligibility assessment only, not a final loan sanction."
    )

    messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
        }
    )

    return {
        **state,
        "messages": messages,
        "application": final_application,
        "assessment_result": result,
        "is_ready_for_assessment": True,
        "missing_fields": [],
    }


def route_after_decision(state: LoanConversationState) -> str:
    """Route to assessment if all required fields are present."""

    missing_fields = state.get("missing_fields", [])

    if len(missing_fields) == 0:
        return "run_assessment"

    return "ask_next_question"


def build_conversational_loan_graph():
    """Build the LangGraph conversational home loan journey."""

    graph = StateGraph(LoanConversationState)

    graph.add_node("extract_and_update_state", extract_and_update_state)
    graph.add_node("decide_next_step", decide_next_step)
    graph.add_node("ask_next_question", ask_next_question)
    graph.add_node("run_assessment", run_assessment)

    graph.set_entry_point("extract_and_update_state")

    graph.add_edge("extract_and_update_state", "decide_next_step")

    graph.add_conditional_edges(
        "decide_next_step",
        route_after_decision,
        {
            "ask_next_question": "ask_next_question",
            "run_assessment": "run_assessment",
        },
    )

    graph.add_edge("ask_next_question", END)
    graph.add_edge("run_assessment", END)

    return graph.compile()





