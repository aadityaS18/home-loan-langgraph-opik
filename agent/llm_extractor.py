"""
Groq-based LLM extractor for conversational home loan journey.

Purpose:
- Convert natural user replies into structured application fields.
- Example:
    "around 35 lakhs" -> {"loan_amount": 3500000}
    "85k per month" -> {"monthly_income": 85000}
    "yes" when asked for PAN -> {"pan_available": true}
    "PAN card and bank statement only" -> {"submitted_documents": ["pan_card", "bank_statement"], "documents_confirmed": true}

The LLM extracts fields only. It does not make loan decisions.
"""

import json
import os
import re
from typing import Any

import opik
from dotenv import load_dotenv

from agent.groq_model import get_groq_llm


load_dotenv()

OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


SUPPORTED_FIELDS = {
    "name",
    "age",
    "employment_type",
    "monthly_income",
    "credit_score",
    "existing_emi",
    "loan_amount",
    "interest_rate",
    "tenure_years",
    "property_value",
    "property_type",
    "property_location",
    "pan_available",
    "id_proof_available",
    "address_proof_available",
    "submitted_documents",
    "documents_confirmed",
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


EXTRACTION_SYSTEM_PROMPT = """
You are an information extraction assistant for a conversational home loan application.

Your task:
- Extract only fields clearly provided by the user.
- Return valid JSON only.
- Do not return markdown.
- Do not guess values.
- Do not make loan decisions.
- Do not explain anything.

Supported fields:
- name
- age
- employment_type
- monthly_income
- credit_score
- existing_emi
- loan_amount
- interest_rate
- tenure_years
- property_value
- property_type
- property_location
- pan_available
- id_proof_available
- address_proof_available
- submitted_documents
- documents_confirmed

Money normalization:
- 35 lakhs -> 3500000
- 35 lakh -> 3500000
- 85k -> 85000
- 1 crore -> 10000000

Employment normalization:
- salaried -> "salaried"
- self employed / business / self-employed -> "self-employed"

Boolean normalization:
- yes / I have / available / uploaded / submitted -> true
- no / not available / missing / don't have / not uploaded -> false

Document extraction:
If user says documents they submitted, return submitted_documents as a list using these canonical names:
- pan_card
- id_proof
- address_proof
- bank_statement
- property_title_deed
- sale_agreement
- salary_slips
- form_16
- employment_proof
- builder_noc
- approved_building_plan

If user says no documents / none / nothing submitted, return:
{
  "submitted_documents": [],
  "documents_confirmed": true
}

Examples:
User: Around 35 lakhs
JSON:
{"loan_amount": 3500000}

User: 85k per month
JSON:
{"monthly_income": 85000}

User: yes
Context missing field: pan_available
JSON:
{"pan_available": true}

User: no
Context missing field: id_proof_available
JSON:
{"id_proof_available": false}

User: PAN card and bank statement only
JSON:
{"submitted_documents": ["pan_card", "bank_statement"], "documents_confirmed": true}

Return JSON only.
"""


def clean_json_response(content: str) -> dict[str, Any]:
    """Parse JSON even if the model accidentally returns markdown fences."""

    text = content.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return {
                key: value
                for key, value in parsed.items()
                if key in SUPPORTED_FIELDS
            }

    except json.JSONDecodeError:
        return {}

    return {}


def parse_money_value(text: str) -> float | None:
    """Parse money values like 35 lakhs, 85k, 1 crore, 3500000."""

    clean_text = text.lower().replace(",", "")

    crore_match = re.search(r"(\d+(\.\d+)?)\s*(crore|crores|cr)", clean_text)
    if crore_match:
        return float(crore_match.group(1)) * 10000000

    lakh_match = re.search(r"(\d+(\.\d+)?)\s*(lakh|lakhs|lac|lacs)", clean_text)
    if lakh_match:
        return float(lakh_match.group(1)) * 100000

    k_match = re.search(r"(\d+(\.\d+)?)\s*k", clean_text)
    if k_match:
        return float(k_match.group(1)) * 1000

    number_match = re.search(r"\b\d{4,}\b", clean_text)
    if number_match:
        return float(number_match.group(0))

    return None


def normalize_boolean_from_text(text: str) -> bool | None:
    """Normalize yes/no answers from free text."""

    clean_text = text.lower().strip()

    yes_terms = [
        "yes",
        "y",
        "true",
        "available",
        "i have",
        "have it",
        "uploaded",
        "submitted",
        "present",
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
    ]

    if clean_text in yes_terms:
        return True

    if clean_text in no_terms:
        return False

    if any(term in clean_text for term in yes_terms):
        return True

    if any(term in clean_text for term in no_terms):
        return False

    return None

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
    """Extract documents that user says are not submitted."""

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


def normalize_documents_from_text(value: Any) -> list[str]:
    """
    Normalize document names from user answer.

    If user says both submitted and not submitted documents,
    only keep submitted documents.
    """

    if value is None:
        return []

    if isinstance(value, list):
        documents: list[str] = []

        for item in value:
            item_text = str(item).lower().strip()

            if item_text in CANONICAL_DOCUMENTS and item_text not in documents:
                documents.append(item_text)

            for phrase, canonical_name in DOCUMENT_ALIASES.items():
                if phrase in item_text and canonical_name not in documents:
                    documents.append(canonical_name)

        return documents

    raw_text = str(value).lower()

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

    if raw_text.strip() in no_document_phrases:
        return []

    all_mentioned_documents = extract_document_names(raw_text)
    negative_documents = extract_negative_documents(raw_text)

    submitted_documents = [
        document
        for document in all_mentioned_documents
        if document not in negative_documents
    ]

    return submitted_documents


def fallback_extract(
    user_message: str,
    current_missing_fields: list[str],
) -> dict[str, Any]:
    """
    Rule-based fallback for common short replies.

    This also corrects common LLM extraction mistakes like:
    "85k" should be 85000, not 500000.
    """

    text = user_message.lower().strip()
    extracted: dict[str, Any] = {}

    if not current_missing_fields:
        return extracted

    next_field = current_missing_fields[0]

    if next_field in [
        "loan_amount",
        "monthly_income",
        "existing_emi",
        "property_value",
        "interest_rate",
    ]:
        money_value = parse_money_value(text)

        if money_value is not None:
            extracted[next_field] = money_value

    if next_field == "credit_score":
        score_match = re.search(r"\b([3-8]\d{2}|900)\b", text)

        if score_match:
            extracted["credit_score"] = int(score_match.group(1))

    if next_field == "age":
        age_match = re.search(r"\b(1[8-9]|[2-6]\d|7[0-5])\b", text)

        if age_match:
            extracted["age"] = int(age_match.group(1))

    if next_field == "tenure_years":
        tenure_match = re.search(r"\b([1-9]|[1-3]\d|40)\b", text)

        if tenure_match:
            extracted["tenure_years"] = int(tenure_match.group(1))

    if next_field == "employment_type":
        if "salaried" in text:
            extracted["employment_type"] = "salaried"
        elif "self employed" in text or "self-employed" in text or "business" in text:
            extracted["employment_type"] = "self-employed"

    if next_field == "property_location":
        extracted["property_location"] = user_message.strip()

    if next_field in [
        "pan_available",
        "id_proof_available",
        "address_proof_available",
    ]:
        bool_value = normalize_boolean_from_text(text)

        if bool_value is not None:
            extracted[next_field] = bool_value

    if next_field == "documents_confirmed":
        submitted_documents = normalize_documents_from_text(user_message)

        extracted["submitted_documents"] = submitted_documents
        extracted["documents_confirmed"] = True

    return extracted


@opik.track(
    name="groq_extract_loan_fields",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def extract_loan_fields_with_groq(
    user_message: str,
    current_application: dict[str, Any],
    current_missing_fields: list[str],
) -> dict[str, Any]:
    """
    Use Groq to extract structured loan application fields from natural language.
    """

    llm = get_groq_llm()

    prompt = f"""
Current application state:
{json.dumps(current_application, indent=2)}

Current missing fields in order:
{current_missing_fields}

Most likely field being answered:
{current_missing_fields[0] if current_missing_fields else "None"}

User message:
{user_message}

Return JSON only.
"""

    response = llm.invoke(
        [
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("human", prompt),
        ]
    )

    llm_extracted = clean_json_response(response.content)
    fallback_extracted = fallback_extract(user_message, current_missing_fields)

    # Fallback overrides LLM for the immediate asked field.
    # This avoids common mistakes for short answers like "85k", "yes", "no", "760".
    extracted = {
        **llm_extracted,
        **fallback_extracted,
    }

    # If submitted_documents came as text/list from LLM, normalize it.
    if "submitted_documents" in extracted:
        extracted["submitted_documents"] = normalize_documents_from_text(
            extracted["submitted_documents"]
        )
        extracted["documents_confirmed"] = True

    return {
        key: value
        for key, value in extracted.items()
        if key in SUPPORTED_FIELDS
    }