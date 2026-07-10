"""
Home Loan Agent Evaluation Cases

This file contains journey-level evaluation cases for the home-loan agent.

Each case defines:
- input messages
- expected tool trajectory
- expected final response behaviour
- expected DB status
- expected business decision

These cases will later be used by:
- final response evaluation
- agent trajectory evaluation
- DB persistence evaluation
- regression evaluation
"""

from __future__ import annotations

from typing import Any


HOME_LOAN_EVAL_CASES: list[dict[str, Any]] = [
    {
        "case_id": "general_ltv_question",
        "description": "General LTV question should be answered directly without tools.",
        "category": "final_response_no_tool",
        "messages": [
            "What is LTV in a home loan?"
        ],
        "expected_tools": [],
        "expected_decision": None,
        "expected_db_status": None,
        "expected_assessment_saved": False,
        "expected_application_should_exist": False,
        "must_include": [
            "ltv",
            "loan",
            "property"
        ],
        "must_not_include": [
            "final approval",
            "guaranteed",
            "sanctioned",
            "pre-approved based on your application"
        ],
        "notes": (
            "This validates direct response behaviour. The agent should not call any backend "
            "tool for a general educational question."
        ),
    },

    {
        "case_id": "general_documents_question",
        "description": "General document question should be answered directly without starting application flow.",
        "category": "final_response_no_tool",
        "messages": [
            "What documents are required for a home loan?"
        ],
        "expected_tools": [],
        "expected_decision": None,
        "expected_db_status": None,
        "expected_assessment_saved": False,
        "expected_application_should_exist": False,
        "must_include": [
            "pan",
            "id proof",
            "address proof",
            "bank statement"
        ],
        "must_not_include": [
            "final approval",
            "guaranteed",
            "sanctioned",
            "your application has been assessed"
        ],
        "notes": (
            "This validates that general help questions do not trigger application state updates."
        ),
    },

    {
        "case_id": "strong_applicant_pre_approved",
        "description": "Strong applicant with complete documents should be pre-approved.",
        "category": "full_journey_positive",
        "messages": [
            (
                "I want to apply for a home loan of 56 lakhs. My monthly income is 4 lakhs, "
                "my credit score is 700, I currently pay 12000 EMI, I am 29 years old, "
                "I am salaried, and the property value is 2.3 crores in Delhi."
            ),
            (
                "I have PAN card available, ID proof available, and address proof available."
            ),
            (
                "I have submitted PAN card, ID proof, address proof, bank statement, "
                "property title deed, sale agreement, salary slips, Form 16, employment proof, "
                "builder NOC and approved building plan."
            ),
        ],
        "expected_tools": [
            "update_application_state_tool",
            "update_application_state_tool",
            "update_application_state_tool",
            "check_application_readiness_tool",
            "run_home_loan_assessment_tool",
        ],
        "expected_decision": "pre_approved",
        "expected_db_status": "assessed",
        "expected_assessment_saved": True,
        "expected_application_should_exist": True,
        "expected_application_fields": {
            "loan_amount": 5600000,
            "monthly_income": 400000,
            "credit_score": 700,
            "existing_emi": 12000,
            "age": 29,
            "employment_type": "salaried",
            "property_value": 23000000,
            "property_location": "Delhi",
        },
        "must_include": [
            "initial",
            "assessment"
        ],
        "must_not_include": [
            "final approval",
            "guaranteed",
            "sanctioned"
        ],
        "notes": (
            "This is the main happy-path journey. It checks tool usage, assessment, "
            "DB persistence, and safe final wording."
        ),
    },

    {
        "case_id": "weak_applicant_rejected",
        "description": "Weak applicant with high risk and incomplete documents should be rejected or high risk.",
        "category": "full_journey_negative",
        "messages": [
            (
                "I want to apply for a home loan of 90 lakhs. My monthly income is 1.2 lakhs, "
                "my credit score is 640, I currently pay 35000 EMI, I am 45 years old, "
                "I am self-employed, and the property value is 1 crore in Mumbai."
            ),
            (
                "I have PAN card available, ID proof available, and address proof available."
            ),
            (
                "I have submitted PAN card, ID proof, address proof and bank statement."
            ),
        ],
        "expected_tools": [
            "update_application_state_tool",
            "update_application_state_tool",
            "update_application_state_tool",
            "check_application_readiness_tool",
            "run_home_loan_assessment_tool",
        ],
        "expected_decision": "rejected",
        "expected_db_status": "assessed",
        "expected_assessment_saved": True,
        "expected_application_should_exist": True,
        "expected_application_fields": {
            "loan_amount": 9000000,
            "monthly_income": 120000,
            "credit_score": 640,
            "existing_emi": 35000,
            "age": 45,
            "employment_type": "self-employed",
            "property_value": 10000000,
            "property_location": "Mumbai",
        },
        "must_include": [
            "risk",
            "document"
        ],
        "must_not_include": [
            "final approval",
            "guaranteed",
            "sanctioned"
        ],
        "notes": (
            "This checks that the agent does not approve weak/high-risk applications "
            "and explains the reason safely."
        ),
    },

    {
        "case_id": "document_availability_not_submission",
        "description": "Document availability should not be treated as document submission.",
        "category": "document_handling",
        "messages": [
            (
                "I want to apply for a home loan of 56 lakhs. My monthly income is 4 lakhs, "
                "my credit score is 700, I currently pay 12000 EMI, I am 29 years old, "
                "I am salaried, and the property value is 2.3 crores in Delhi."
            ),
            (
                "I have PAN card available, ID proof available, and address proof available."
            ),
        ],
        "expected_tools": [
            "update_application_state_tool",
            "update_application_state_tool",
        ],
        "expected_decision": None,
        "expected_db_status": "in_progress",
        "expected_assessment_saved": False,
        "expected_application_should_exist": True,
        "must_include": [
            "submit"
        ],
        "must_not_include": [
            "pre-approved",
            "rejected",
            "final approval",
            "guaranteed",
            "sanctioned"
        ],
        "notes": (
            "This checks a key lending workflow rule: documents being available is not the "
            "same as documents being submitted. Assessment should not run yet."
        ),
    },

    {
        "case_id": "missing_documents_case",
        "description": "Applicant with incomplete submitted documents should receive missing document guidance.",
        "category": "missing_documents",
        "messages": [
            (
                "I want to apply for a home loan of 56 lakhs. My monthly income is 4 lakhs, "
                "my credit score is 700, I currently pay 12000 EMI, I am 29 years old, "
                "I am salaried, and the property value is 2.3 crores in Delhi."
            ),
            (
                "I have PAN card available, ID proof available, and address proof available."
            ),
            (
                "I have submitted only PAN card, ID proof, address proof and bank statement."
            ),
        ],
        "expected_tools": [
            "update_application_state_tool",
            "update_application_state_tool",
            "update_application_state_tool",
            "check_application_readiness_tool",
            "run_home_loan_assessment_tool",
        ],
        "expected_decision": "rejected",
        "expected_db_status": "assessed",
        "expected_assessment_saved": True,
        "expected_application_should_exist": True,
        "must_include": [
            "missing",
            "document"
        ],
        "must_not_include": [
            "final approval",
            "guaranteed",
            "sanctioned"
        ],
        "notes": (
            "This validates missing document detection and final response explanation."
        ),
    },

    {
        "case_id": "finish_conversation",
        "description": "Finish should close the conversation and update DB status.",
        "category": "close_conversation",
        "messages": [
            "finish"
        ],
        "expected_tools": [
            "close_conversation_tool"
        ],
        "expected_decision": None,
        "expected_db_status": "closed",
        "expected_assessment_saved": False,
        "expected_application_should_exist": True,
        "must_include": [
            "closed"
        ],
        "must_not_include": [
            "final approval",
            "guaranteed",
            "sanctioned"
        ],
        "notes": (
            "This checks that finish/done/close triggers close_conversation_tool "
            "and persists closed status."
        ),
    },
]


def get_eval_case(case_id: str) -> dict[str, Any]:
    """
    Return a single evaluation case by case_id.
    """
    for case in HOME_LOAN_EVAL_CASES:
        if case["case_id"] == case_id:
            return case

    raise ValueError(f"Unknown eval case_id: {case_id}")


def list_case_ids() -> list[str]:
    """
    Return all available evaluation case IDs.
    """
    return [case["case_id"] for case in HOME_LOAN_EVAL_CASES]


def print_eval_cases_summary() -> None:
    """
    Print a quick summary of available evaluation cases.
    """
    print(f"Total evaluation cases: {len(HOME_LOAN_EVAL_CASES)}")
    print("-" * 80)

    for case in HOME_LOAN_EVAL_CASES:
        print(f"{case['case_id']} | {case['category']} | {case['description']}")