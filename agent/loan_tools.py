"""
Deterministic tools for the agent-driven home loan application.

Important:
- These tools do backend work only.
- They do not decide the conversation flow.
- The agent decides when to call these tools.
"""

from typing import Any

from agent.controlled_assessment import run_controlled_home_loan_assessment


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


def normalize_submitted_documents(value: Any) -> list[str]:
    """
    Convert submitted documents into canonical document IDs expected by
    the controlled assessment tool.

    Example:
    "PAN card" -> "pan_card"
    "ID proof" -> "id_proof"
    "Builder NOC" -> "builder_noc"
    """

    if value is None:
        return []

    if isinstance(value, list):
        raw_documents = [
            str(document).strip()
            for document in value
            if str(document).strip()
        ]

    elif isinstance(value, str):
        text = value.strip()

        if not text:
            return []

        raw_documents: list[str] = []

        for separator in [",", ";", "\n"]:
            if separator in text:
                raw_documents = [
                    part.strip()
                    for part in text.split(separator)
                    if part.strip()
                ]
                break

        if not raw_documents:
            raw_documents = [text]

    else:
        raw_documents = [str(value).strip()]

    alias_map = {
        "pan": "pan_card",
        "pan card": "pan_card",
        "pancard": "pan_card",

        "id": "id_proof",
        "id proof": "id_proof",
        "identity proof": "id_proof",
        "aadhaar": "id_proof",
        "aadhar": "id_proof",
        "passport": "id_proof",
        "voter id": "id_proof",

        "address": "address_proof",
        "address proof": "address_proof",
        "utility bill": "address_proof",
        "electricity bill": "address_proof",

        "bank statement": "bank_statement",
        "bank statements": "bank_statement",

        "property title deed": "property_title_deed",
        "title deed": "property_title_deed",
        "property deed": "property_title_deed",

        "sale agreement": "sale_agreement",
        "agreement to sell": "sale_agreement",

        "salary slip": "salary_slips",
        "salary slips": "salary_slips",
        "payslip": "salary_slips",
        "payslips": "salary_slips",

        "form 16": "form_16",
        "form16": "form_16",

        "employment proof": "employment_proof",
        "employment letter": "employment_proof",
        "job proof": "employment_proof",

        "builder noc": "builder_noc",
        "noc": "builder_noc",

        "approved building plan": "approved_building_plan",
        "building plan": "approved_building_plan",
        "approved plan": "approved_building_plan",
    }

    canonical_documents: list[str] = []

    for document in raw_documents:
        cleaned = (
            document.lower()
            .replace(".", "")
            .replace(":", "")
            .replace("-", " ")
            .replace("_", " ")
            .replace(" and ", " ")
            .strip()
        )

        if cleaned in alias_map:
            canonical_documents.append(alias_map[cleaned])
            continue

        for alias, canonical_name in alias_map.items():
            if alias in cleaned:
                canonical_documents.append(canonical_name)

    unique_documents: list[str] = []

    for document in canonical_documents:
        if document not in unique_documents:
            unique_documents.append(document)

    return unique_documents


def normalize_application_fields(application: dict[str, Any]) -> dict[str, Any]:
    normalized = application.copy()

    if "submitted_documents" in normalized:
        normalized["submitted_documents"] = normalize_submitted_documents(
            normalized.get("submitted_documents")
        )

        if normalized["submitted_documents"]:
            normalized["documents_confirmed"] = True

    return normalized


def update_application_state_tool(
    current_application: dict[str, Any],
    extracted_fields: dict[str, Any],
) -> dict[str, Any]:
    updated_application = current_application.copy()
    updated_fields: dict[str, Any] = {}

    for key, value in extracted_fields.items():
        if value is not None and value != "":
            updated_application[key] = value
            updated_fields[key] = value

    updated_application = normalize_application_fields(updated_application)

    if "submitted_documents" in updated_fields:
        updated_fields["submitted_documents"] = normalize_submitted_documents(
            updated_fields["submitted_documents"]
        )
        updated_fields["documents_confirmed"] = True

    missing_fields = get_missing_fields(updated_application)

    return {
        "tool_name": "update_application_state_tool",
        "application": updated_application,
        "updated_fields": updated_fields,
        "ready_for_assessment": len(missing_fields) == 0,
        "missing_fields": missing_fields,
    }


def check_application_readiness_tool(
    application: dict[str, Any],
) -> dict[str, Any]:
    application = normalize_application_fields(application)
    missing_fields = get_missing_fields(application)

    return {
        "tool_name": "check_application_readiness_tool",
        "ready_for_assessment": len(missing_fields) == 0,
        "missing_fields": missing_fields,
    }


def build_application_for_assessment(application: dict[str, Any]) -> dict[str, Any]:
    application = normalize_application_fields(application)

    submitted_documents = normalize_submitted_documents(
        application.get("submitted_documents", [])
    )

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
        "submitted_documents": submitted_documents,
    }


def run_home_loan_assessment_tool(
    application: dict[str, Any],
) -> dict[str, Any]:
    application = normalize_application_fields(application)

    readiness = check_application_readiness_tool(application)

    if not readiness["ready_for_assessment"]:
        return {
            "tool_name": "run_home_loan_assessment_tool",
            "assessment_ran": False,
            "error": "Application is not ready for assessment.",
            "missing_fields": readiness["missing_fields"],
        }

    final_application = build_application_for_assessment(application)
    assessment_result = run_controlled_home_loan_assessment(final_application)

    return {
        "tool_name": "run_home_loan_assessment_tool",
        "assessment_ran": True,
        "application": final_application,
        "assessment_result": assessment_result,
    }


def close_conversation_tool() -> dict[str, Any]:
    return {
        "tool_name": "close_conversation_tool",
        "conversation_closed": True,
    }