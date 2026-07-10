"""
Agent-driven conversational home loan journey.

"""

import os
import uuid
from typing import Any, TypedDict

import opik
from dotenv import load_dotenv

from agent.controlled_assessment import run_controlled_home_loan_assessment
from agent.conversation_store import load_conversation_state, save_conversation_state
from agent.llm_extractor import (
    classify_user_intent_with_groq,
    extract_loan_fields_with_groq,
    generate_agent_response_with_groq,
)


load_dotenv()

OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


class LoanConversationState(TypedDict, total=False):
    thread_id: str
    messages: list[dict[str, str]]
    application: dict[str, Any]
    missing_fields: list[str]
    validation_errors: list[str]
    last_extracted_fields: dict[str, Any]
    last_intent: str
    assessment_result: dict[str, Any] | None
    is_ready_for_assessment: bool
    conversation_closed: bool


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


def create_thread_id() -> str:
    return f"loan-thread-{uuid.uuid4().hex[:8]}"


def create_initial_conversation_state(thread_id: str) -> LoanConversationState:
    return {
        "thread_id": thread_id,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "Hi, I can help with home loan questions or start a loan "
                    "application. You can ask me something like "
                    "'what documents are required?' or tell me if you want to "
                    "start a home loan application."
                ),
            }
        ],
        "application": {},
        "missing_fields": REQUIRED_FIELDS.copy(),
        "validation_errors": [],
        "last_extracted_fields": {},
        "last_intent": "",
        "assessment_result": None,
        "is_ready_for_assessment": False,
        "conversation_closed": False,
    }


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def get_missing_fields(application: dict[str, Any]) -> list[str]:
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
    if isinstance(value, bool):
        return value

    text = str(value).lower().strip()

    yes_terms = [
        "yes",
        "y",
        "true",
        "available",
        "have",
        "i have",
        "uploaded",
        "submitted",
        "present",
        "with me",
    ]

    no_terms = [
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
        "not with me",
    ]

    if text in yes_terms:
        return True

    if text in no_terms:
        return False

    if any(term in text for term in yes_terms):
        return True

    if any(term in text for term in no_terms):
        return False

    return None


def validate_and_normalize_fields(
    extracted: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
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

            elif field in ["property_location", "name", "property_type"]:
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
                if isinstance(value, list):
                    valid["submitted_documents"] = [
                        str(document).strip()
                        for document in value
                        if str(document).strip()
                    ]
                else:
                    valid["submitted_documents"] = []

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


def build_application_for_assessment(application: dict[str, Any]) -> dict[str, Any]:
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


def format_assessment_message(result: dict[str, Any]) -> str:
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
            str(doc).replace("_", " ").title()
            for doc in missing_documents
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


def has_application_started(application: dict[str, Any]) -> bool:
    application_start_fields = [
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
        "submitted_documents",
        "documents_confirmed",
    ]

    return any(field in application for field in application_start_fields)


def should_extract_for_intent(intent: str) -> bool:
    return intent in [
        "application_data",
        "correction",
        "assessment_request",
    ]


def should_run_assessment(
    intent: str,
    assessment_ready: bool,
    assessment_already_done: bool,
) -> bool:
    if assessment_already_done:
        return False

    return assessment_ready and intent in [
        "application_data",
        "correction",
        "assessment_request",
    ]


def user_explicitly_mentions_document_availability(
    user_message: str,
    field: str,
) -> bool:
    text = user_message.lower()

    field_keywords = {
        "pan_available": ["pan", "pan card", "pancard"],
        "id_proof_available": [
            "id proof",
            "identity proof",
            "aadhaar",
            "aadhar",
            "passport",
            "voter id",
            "id",
        ],
        "address_proof_available": [
            "address proof",
            "utility bill",
            "electricity bill",
            "aadhaar",
            "aadhar",
            "passport",
            "voter id",
            "address",
        ],
    }

    availability_keywords = [
        "yes",
        "no",
        "have",
        "don't have",
        "dont have",
        "do not have",
        "available",
        "not available",
        "missing",
        "with me",
        "not with me",
    ]

    doc_keywords = field_keywords.get(field, [])

    return any(keyword in text for keyword in doc_keywords) and any(
        keyword in text for keyword in availability_keywords
    )


def user_explicitly_mentions_document_submission(user_message: str) -> bool:
    text = user_message.lower().strip()

    submission_keywords = [
        "submitted",
        "uploaded",
        "provided",
        "attached",
        "sent",
        "shared",
        "given",
        "i submitted",
        "i have submitted",
        "i uploaded",
        "i have uploaded",
        "i provided",
        "i have provided",
        "documents submitted",
        "docs submitted",
        "uploaded documents",
        "submitted documents",
        "none submitted",
        "no documents submitted",
    ]

    return any(keyword in text for keyword in submission_keywords)


def apply_contextual_document_availability(
    user_message: str,
    extracted: dict[str, Any],
    missing_fields_before: list[str],
) -> dict[str, Any]:
    text = user_message.lower().strip()

    current_expected_field = (
        missing_fields_before[0] if missing_fields_before else None
    )

    positive_phrases = [
        "yes",
        "yea",
        "yeah",
        "yep",
        "i have",
        "have that",
        "i have that",
        "available",
        "with me",
        "i have all",
        "all available",
        "all the documents",
        "all documents",
        "all docs",
    ]

    negative_phrases = [
        "no",
        "not available",
        "don't have",
        "dont have",
        "do not have",
        "missing",
        "not with me",
    ]

    is_positive = any(phrase in text for phrase in positive_phrases)
    is_negative = any(phrase in text for phrase in negative_phrases)

    if is_positive and (
        "all documents" in text
        or "all the documents" in text
        or "all available" in text
        or "all docs" in text
    ):
        extracted["pan_available"] = True
        extracted["id_proof_available"] = True
        extracted["address_proof_available"] = True
        return extracted

    if current_expected_field in [
        "pan_available",
        "id_proof_available",
        "address_proof_available",
    ]:
        if is_positive:
            extracted[current_expected_field] = True
        elif is_negative:
            extracted[current_expected_field] = False

    if is_positive:
        if "pan" in text or "pan card" in text or "pancard" in text:
            extracted["pan_available"] = True

        if (
            "id proof" in text
            or "identity proof" in text
            or "passport" in text
            or "voter id" in text
            or "aadhaar" in text
            or "aadhar" in text
        ):
            extracted["id_proof_available"] = True

        if (
            "address proof" in text
            or "utility bill" in text
            or "electricity bill" in text
            or (
                current_expected_field == "address_proof_available"
                and (
                    "passport" in text
                    or "voter id" in text
                    or "aadhaar" in text
                    or "aadhar" in text
                    or "i have that" in text
                    or "have that" in text
                    or "yes" in text
                )
            )
        ):
            extracted["address_proof_available"] = True

    return extracted


def is_finish_conversation_message(user_message: str) -> bool:
    text = user_message.lower().strip()

    finish_phrases = [
        "finish",
        "end",
        "close",
        "stop",
        "done",
        "no thanks",
        "no thank you",
        "that's all",
        "thats all",
        "nothing else",
        "no more questions",
    ]

    return any(phrase in text for phrase in finish_phrases)


@opik.track(
    name="agent_driven_home_loan_calculation",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def run_assessment_for_state(state: LoanConversationState) -> LoanConversationState:
    application = state.get("application", {})
    messages = state.get("messages", [])

    final_application = build_application_for_assessment(application)
    result = run_controlled_home_loan_assessment(final_application)

    messages.append(
        {
            "role": "assistant",
            "content": format_assessment_message(result),
        }
    )

    return {
        **state,
        "messages": messages,
        "application": final_application,
        "assessment_result": result,
        "missing_fields": [],
        "is_ready_for_assessment": True,
        "conversation_closed": False,
    }


@opik.track(
    name="agent_driven_conversational_turn",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def run_conversational_loan_turn(
    thread_id: str,
    user_message: str,
) -> dict[str, Any]:
    saved_state = load_conversation_state(thread_id)

    if saved_state:
        state: LoanConversationState = saved_state
    else:
        state = create_initial_conversation_state(thread_id)

    messages = state.get("messages", [])
    application = state.get("application", {})

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    if state.get("assessment_result") is not None and is_finish_conversation_message(
        user_message
    ):
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "Got it. I’ll close this home loan conversation now. "
                    "You can start a new application or resume another Application ID from the sidebar."
                ),
            }
        )

        state = {
            **state,
            "messages": messages,
            "conversation_closed": True,
        }

        save_conversation_state(thread_id, state)

        return {
            "thread_id": thread_id,
            "assistant_message": messages[-1]["content"],
            "messages": state.get("messages", []),
            "application": state.get("application", {}),
            "missing_fields": state.get("missing_fields", []),
            "assessment_result": state.get("assessment_result"),
            "is_ready_for_assessment": state.get("is_ready_for_assessment", False),
            "state": state,
        }

    missing_fields_before = get_missing_fields(application)

    intent_result = classify_user_intent_with_groq(
        user_message=user_message,
        application=application,
        missing_fields=missing_fields_before,
    )

    intent = intent_result.get("intent", "application_data")
    assessment_already_done = state.get("assessment_result") is not None

    if assessment_already_done and intent not in ["correction", "application_data"]:
        intent = "general_question"

    extracted: dict[str, Any] = {}
    validation_errors: list[str] = []

    if should_extract_for_intent(intent) and not assessment_already_done:
        extracted_raw = extract_loan_fields_with_groq(
            user_message=user_message,
            current_application=application,
            current_missing_fields=missing_fields_before,
        )

        extracted, validation_errors = validate_and_normalize_fields(extracted_raw)

        extracted = apply_contextual_document_availability(
            user_message=user_message,
            extracted=extracted,
            missing_fields_before=missing_fields_before,
        )

        document_availability_fields = [
            "pan_available",
            "id_proof_available",
            "address_proof_available",
        ]

        for field in document_availability_fields:
            if field in extracted:
                explicitly_mentioned = user_explicitly_mentions_document_availability(
                    user_message=user_message,
                    field=field,
                )

                text = user_message.lower().strip()

                current_expected_field = (
                    missing_fields_before[0] if missing_fields_before else None
                )

                contextual_positive_answer = any(
                    phrase in text
                    for phrase in [
                        "yes",
                        "yea",
                        "yeah",
                        "yep",
                        "i have",
                        "have that",
                        "i have that",
                        "available",
                        "with me",
                    ]
                )

                all_documents_answer = any(
                    phrase in text
                    for phrase in [
                        "all documents",
                        "all the documents",
                        "all docs",
                        "all available",
                    ]
                )

                allow_contextual_answer = (
                    contextual_positive_answer and current_expected_field == field
                )

                allow_all_documents_answer = all_documents_answer and field in [
                    "pan_available",
                    "id_proof_available",
                    "address_proof_available",
                ]

                if not (
                    explicitly_mentioned
                    or allow_contextual_answer
                    or allow_all_documents_answer
                ):
                    extracted.pop(field, None)

        if "submitted_documents" in extracted or "documents_confirmed" in extracted:
            if not user_explicitly_mentions_document_submission(user_message):
                extracted.pop("submitted_documents", None)
                extracted.pop("documents_confirmed", None)

        application.update(extracted)

    missing_fields_after = get_missing_fields(application)
    assessment_ready = len(missing_fields_after) == 0
    application_started = has_application_started(application)

    state = {
        **state,
        "messages": messages,
        "application": application,
        "missing_fields": missing_fields_after,
        "validation_errors": validation_errors,
        "last_extracted_fields": extracted,
        "last_intent": intent,
        "is_ready_for_assessment": assessment_ready,
        "conversation_closed": state.get("conversation_closed", False),
    }

    assessment_already_done = state.get("assessment_result") is not None

    if should_run_assessment(
        intent=intent,
        assessment_ready=assessment_ready,
        assessment_already_done=assessment_already_done,
    ):
        state = run_assessment_for_state(state)

    else:
        should_continue_application = (
            intent in ["application_data", "correction", "assessment_request"]
            or application_started
        )

        if intent == "general_question" and not application_started:
            should_continue_application = False

        if assessment_already_done:
            should_continue_application = False

        next_field_to_ask = missing_fields_after[0] if missing_fields_after else None

        if assessment_already_done:
            next_field_to_ask = None

        assistant_message = generate_agent_response_with_groq(
            user_message=user_message,
            intent=intent,
            application=application,
            missing_fields=missing_fields_after,
            validation_errors=validation_errors,
            last_extracted_fields=extracted,
            assessment_ready=assessment_ready,
            should_continue_application=should_continue_application,
            next_field_to_ask=next_field_to_ask,
        )

        state["messages"].append(
            {
                "role": "assistant",
                "content": assistant_message,
            }
        )

    save_conversation_state(thread_id, state)

    latest_assistant_message = ""

    for message in reversed(state.get("messages", [])):
        if message.get("role") == "assistant":
            latest_assistant_message = message.get("content", "")
            break

    return {
        "thread_id": thread_id,
        "assistant_message": latest_assistant_message,
        "messages": state.get("messages", []),
        "application": state.get("application", {}),
        "missing_fields": state.get("missing_fields", []),
        "assessment_result": state.get("assessment_result"),
        "is_ready_for_assessment": state.get("is_ready_for_assessment", False),
        "state": state,
    }





