"""
Groq-powered LLM utilities for the agent-driven loan chatbot.

This file handles:
1. Intent classification
2. Field extraction
3. Dynamic agent response generation

The LLM does NOT approve or reject the loan.
Final loan decisions still come from deterministic tools.
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
    "voter id": "id_proof",
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


INTENT_PROMPT = """
You are an intent classifier for a home loan chatbot.

Classify the user message into exactly one intent:

- general_question
  The user is asking about home loans, documents, EMI, LTV, eligibility, process, interest rate, etc.
  They are not necessarily applying.

- application_data
  The user is providing information for their loan application.

- correction
  The user is correcting or updating a previous answer.

- assessment_request
  The user is asking to calculate, check eligibility, run assessment, proceed, continue, or tell final result.

- resume_request
  The user wants to continue or resume an old application.

Important:
- "I want to apply for a home loan" is application_data.
- "sure", "yes proceed", "run assessment", "check eligibility" is assessment_request.
- "what documents are required?" is general_question.
- "what is LTV?" is general_question.

Return JSON only:
{
  "intent": "...",
  "confidence": 0.0,
  "reason": "short reason"
}
"""


EXTRACTION_PROMPT = """
You are an information extraction assistant for a conversational home loan application.

Extract only fields clearly provided by the user.
Return valid JSON only.
Do not guess.
Do not explain.
Do not make loan decisions.

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

Strict extraction rules:
- Extract only what the user explicitly provided.
- Do not assume or infer document availability.
- Do not set pan_available, id_proof_available, or address_proof_available unless the user clearly says they have or do not have those documents.
- Do not set submitted_documents unless the user clearly says submitted, uploaded, provided, attached, shared, sent, or given documents.
- Do not treat "I want to apply for a home loan" as confirmation of PAN, ID proof, address proof, or submitted documents.
- Do not infer loan_amount, income, documents, or credit score from general home-loan questions.
- "Documents available" and "documents submitted" are different.
- If user says documents are available, do not mark submitted_documents.
- If user says documents are submitted/uploaded/provided, then extract submitted_documents.

Money normalization:
- 35 lakhs -> 3500000
- 35 lakh -> 3500000
- 85k -> 85000
- 1 crore -> 10000000

Important money field rule:
- If the user says income, salary, monthly income, or earnings, extract monthly_income.
- If the user says loan amount, borrow, looking for loan, applying for loan, or want loan, extract loan_amount.
- If the user says existing EMI, current EMI, or currently pay EMI, extract existing_emi.
- If the user says property value, house value, flat value, or property price, extract property_value.
- Do not infer loan_amount from income.
- Do not infer monthly_income from loan_amount.

Employment normalization:
- salaried -> "salaried"
- self employed / business / self-employed -> "self-employed"

Boolean normalization:
Only extract these if the user explicitly refers to the document or if the current missing field is specifically asking about it:
- pan_available
- id_proof_available
- address_proof_available

Examples:
User: I have PAN card
JSON: {"pan_available": true}

User: I do not have ID proof
JSON: {"id_proof_available": false}

User: yes
Context missing field: pan_available
JSON: {"pan_available": true}

User: I want to apply for a home loan
JSON: {}

Document extraction:
If the user lists submitted/uploaded/provided documents, return submitted_documents as canonical names.

If the user says they have NOT submitted some documents, do NOT include those documents in submitted_documents.

Canonical document names:
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

Example:
User:
I submitted PAN card, ID proof and bank statement but I have not submitted builder NOC.

JSON:
{
  "submitted_documents": ["pan_card", "id_proof", "bank_statement"],
  "documents_confirmed": true
}

Example:
User:
I have PAN card available.

JSON:
{
  "pan_available": true
}

Do NOT return submitted_documents for that example.

If user says none/no documents submitted:
{
  "submitted_documents": [],
  "documents_confirmed": true
}

Return JSON only.
"""


AGENT_RESPONSE_PROMPT = """
You are a professional home loan assistant and loan origination agent.

You are not a fixed form.
You must understand the user's intent before deciding what to do.

You can:
- Answer general home-loan questions.
- Explain required documents.
- Explain EMI, LTV, DTI, FOIR, eligibility, and the home-loan process.
- Help start a home-loan application when the user wants to apply.
- Ask the next best question only when the user is applying or continuing an application.
- Acknowledge corrections.
- Continue an existing application.

Important rules:
- If the user is only asking a general home-loan question, answer the question only.
- Do not force the user into an application flow after a general question.
- Do not ask for personal financial details unless the user wants to apply, check eligibility, or continue an existing application.
- If the user asks a general question, you may softly offer help, but do not ask application questions.
- If the user provides application information, then continue the application naturally.
- Ask only one focused next question during the application flow.
- Do not ask a hardcoded list of questions.
- Do not approve or reject the loan yourself.
- Final decision comes only from the tool-based assessment.
- Never say a field has been updated unless it exists in the current application state.
- Do not print the raw JSON application state to the user.
- Do not claim PAN, ID proof, address proof, or submitted documents are confirmed unless they are present in the current application state.
- "Documents available" and "documents submitted" are different.
- If documents are only available, ask later which documents have been submitted/uploaded.
- Do not repeatedly ask for a field that is already present in the current application state.
- If assessment_ready is true, tell the user that the assessment can proceed.

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
"""


def clean_json_response(content: str) -> dict[str, Any]:
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
            return parsed
    except json.JSONDecodeError:
        return {}

    return {}


def parse_money_value(text: str) -> float | None:
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
    clean_text = text.lower().strip()

    yes_terms = [
        "yes",
        "y",
        "true",
        "available",
        "i have",
        "have it",
        "have that",
        "uploaded",
        "submitted",
        "present",
        "with me",
        "all available",
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

    if clean_text in yes_terms:
        return True

    if clean_text in no_terms:
        return False

    if any(term in clean_text for term in yes_terms):
        return True

    if any(term in clean_text for term in no_terms):
        return False

    return None


def extract_document_names(raw_text: str) -> list[str]:
    documents: list[str] = []

    for phrase, canonical_name in DOCUMENT_ALIASES.items():
        if phrase in raw_text and canonical_name not in documents:
            documents.append(canonical_name)

    for canonical_name in CANONICAL_DOCUMENTS:
        if canonical_name in raw_text and canonical_name not in documents:
            documents.append(canonical_name)

    return documents


def extract_negative_documents(raw_text: str) -> list[str]:
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
        "none submitted",
        "no documents submitted",
    ]

    if raw_text in no_document_phrases:
        return []

    all_documents = extract_document_names(raw_text)
    negative_documents = extract_negative_documents(raw_text)

    return [
        document
        for document in all_documents
        if document not in negative_documents
    ]


def infer_money_field_from_text(
    user_message: str,
    current_missing_fields: list[str],
) -> str | None:
    text = user_message.lower().strip()

    income_keywords = [
        "monthly income",
        "income",
        "salary",
        "earn",
        "earning",
        "per month",
        "monthly salary",
    ]

    loan_keywords = [
        "loan amount",
        "home loan",
        "borrow",
        "borrowing",
        "looking for",
        "need loan",
        "want loan",
        "want a loan",
        "loan of",
        "applying for home-loan",
        "applying for home loan",
    ]

    existing_emi_keywords = [
        "existing emi",
        "current emi",
        "currently pay",
        "pay emi",
        "emi currently",
        "old emi",
        "car loan",
        "credit card",
    ]

    property_keywords = [
        "property value",
        "property price",
        "house value",
        "flat value",
        "home value",
        "property is worth",
        "worth",
    ]

    if any(keyword in text for keyword in income_keywords):
        return "monthly_income"

    if any(keyword in text for keyword in existing_emi_keywords):
        return "existing_emi"

    if any(keyword in text for keyword in property_keywords):
        return "property_value"

    if any(keyword in text for keyword in loan_keywords):
        return "loan_amount"

    if current_missing_fields:
        first_missing = current_missing_fields[0]

        if first_missing in [
            "loan_amount",
            "monthly_income",
            "existing_emi",
            "property_value",
            "interest_rate",
        ]:
            return first_missing

    return None


def fallback_extract(
    user_message: str,
    current_missing_fields: list[str],
) -> dict[str, Any]:
    text = user_message.lower().strip()
    extracted: dict[str, Any] = {}

    if not current_missing_fields:
        return extracted

    money_value = parse_money_value(text)

    if money_value is not None:
        money_field = infer_money_field_from_text(
            user_message=user_message,
            current_missing_fields=current_missing_fields,
        )

        if money_field is not None:
            extracted[money_field] = money_value

    if "credit score" in text or (
        "credit_score" in current_missing_fields and re.fullmatch(r"\d{3}", text)
    ):
        score_match = re.search(r"\b([3-8]\d{2}|900)\b", text)

        if score_match:
            extracted["credit_score"] = int(score_match.group(1))

    if "age" in text or "years old" in text or "yrs" in text or (
        "age" in current_missing_fields and re.fullmatch(r"\d{2}", text)
    ):
        age_match = re.search(r"\b(1[8-9]|[2-6]\d|7[0-5])\b", text)

        if age_match:
            extracted["age"] = int(age_match.group(1))

    if "salaried" in text:
        extracted["employment_type"] = "salaried"
    elif "self employed" in text or "self-employed" in text or "business" in text:
        extracted["employment_type"] = "self-employed"

    if "property_location" in current_missing_fields:
        location_keywords = ["in ", "located", "location", "city"]

        if any(keyword in text for keyword in location_keywords):
            extracted["property_location"] = user_message.strip()

        elif len(user_message.strip().split()) <= 4 and not money_value:
            extracted["property_location"] = user_message.strip()

    yes_no_fields = [
        "pan_available",
        "id_proof_available",
        "address_proof_available",
    ]

    for field in yes_no_fields:
        if field in current_missing_fields:
            bool_value = normalize_boolean_from_text(text)

            if bool_value is not None:
                extracted[field] = bool_value
                break

    if "documents_confirmed" in current_missing_fields:
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

        if any(keyword in text for keyword in submission_keywords):
            extracted["submitted_documents"] = normalize_documents_from_text(
                user_message
            )
            extracted["documents_confirmed"] = True

    return extracted


@opik.track(
    name="groq_classify_user_intent",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def classify_user_intent_with_groq(
    user_message: str,
    application: dict[str, Any],
    missing_fields: list[str],
) -> dict[str, Any]:
    llm = get_groq_llm()

    prompt = f"""
Current application:
{json.dumps(application, indent=2)}

Missing fields:
{missing_fields}

User message:
{user_message}

Return JSON only.
"""

    response = llm.invoke(
        [
            ("system", INTENT_PROMPT),
            ("human", prompt),
        ]
    )

    parsed = clean_json_response(response.content)

    intent = parsed.get("intent", "application_data")

    if intent not in [
        "general_question",
        "application_data",
        "correction",
        "assessment_request",
        "resume_request",
    ]:
        intent = "application_data"

    return {
        "intent": intent,
        "confidence": parsed.get("confidence", 0.5),
        "reason": parsed.get("reason", ""),
    }


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
    llm = get_groq_llm()

    prompt = f"""
Current application state:
{json.dumps(current_application, indent=2)}

Current missing fields:
{current_missing_fields}

Most likely missing field being answered:
{current_missing_fields[0] if current_missing_fields else "None"}

User message:
{user_message}

Return JSON only.
"""

    response = llm.invoke(
        [
            ("system", EXTRACTION_PROMPT),
            ("human", prompt),
        ]
    )

    llm_extracted = clean_json_response(response.content)
    fallback_extracted = fallback_extract(user_message, current_missing_fields)

    extracted = {
        **llm_extracted,
        **fallback_extracted,
    }

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


@opik.track(
    name="groq_generate_agent_response",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def generate_agent_response_with_groq(
    user_message: str,
    intent: str,
    application: dict[str, Any],
    missing_fields: list[str],
    validation_errors: list[str],
    last_extracted_fields: dict[str, Any],
    assessment_ready: bool,
    should_continue_application: bool,
    next_field_to_ask: str | None,
) -> str:
    llm = get_groq_llm()

    prompt = f"""
Intent:
{intent}

Current application:
{json.dumps(application, indent=2)}

Missing fields:
{missing_fields}

Next field to ask:
{next_field_to_ask}

Validation errors:
{validation_errors}

Fields extracted from latest user message:
{json.dumps(last_extracted_fields, indent=2)}

Assessment ready:
{assessment_ready}

Should continue application flow:
{should_continue_application}

Latest user message:
{user_message}

Generate the assistant response.

Important behavior:
- If intent is general_question and should_continue_application is false:
  answer the user's home-loan question only.
  Do NOT ask for income, loan amount, credit score, documents, EMI, or any application detail.
  You may end with a soft optional line like:
  "I can also help you check eligibility when you are ready to apply."

- If intent is general_question and should_continue_application is true:
  answer the question first.
  Then gently offer to continue the existing application.
  Do not force the next application question unless the user clearly wants to continue.

- If intent is application_data, correction, or assessment_request:
  acknowledge only the information that exists in Current application.
  If fields are missing, ask one natural next question.



Post-assessment behavior:
- If assessment is already complete and the user asks a follow-up question, answer it normally.
- Do not ask application collection questions again unless the user clearly wants to change details.
- If user asks what to do next, explain the next steps from the assessment result.
- If user says finish, end, done, or no thanks, the backend will close the conversation.  

Important next-question rule:
- If should_continue_application is true and assessment_ready is false, ask ONLY for Next field to ask.
- Do not ask for any field that already exists in Current application.
- Do not ask for monthly_income if monthly_income already exists.
- Do not ask for loan_amount if loan_amount already exists.
- Do not ask for age if age already exists.
- Do not ask for credit_score if credit_score already exists.
- Do not ask for existing_emi if existing_emi already exists.
- Do not choose a different missing field yourself.
- Use Missing fields only to understand progress.
- The only field you may ask next is Next field to ask.
- If Next field to ask is None and assessment_ready is true, tell the user assessment can proceed.

Document rules:
- Do not claim PAN, ID proof, address proof, or submitted documents are confirmed unless they exist in Current application.
- "Documents available" and "documents submitted" are different.
- If documents are only available, ask which documents have been submitted/uploaded only when Next field to ask is documents_confirmed.
- If Next field to ask is documents_confirmed, ask the user which documents have been submitted/uploaded for this application.
- Do not say assessment can proceed until documents_confirmed exists in Current application.
- Availability of PAN/ID/address proof is not enough for assessment. Submitted/uploaded document list is still required.

Style rules:
- Do not print raw JSON.
- Do not use a rigid form style.
- Do not ask for all details at once.
- Do not approve or reject the loan yourself.
- Final decision comes only from the tool-based assessment.
"""

    response = llm.invoke(
        [
            ("system", AGENT_RESPONSE_PROMPT),
            ("human", prompt),
        ]
    )

    return response.content.strip()