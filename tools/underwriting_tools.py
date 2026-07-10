"""
Underwriting tools for the home-loan agent.

This wraps the existing deterministic rule engine so the agent can request
an initial assessment without making the decision itself.
"""

from langchain_core.tools import tool

from services.rule_engine import run_underwriting_rules


@tool
def run_initial_assessment_tool(
    name: str,
    age: int,
    employment_type: str,
    monthly_income: float,
    work_experience_years: float,
    credit_score: int,
    existing_emi: float,
    loan_amount: float,
    interest_rate: float,
    tenure_years: int,
    loan_purpose: str,
    property_value: float,
    property_type: str,
    property_location: str,
    property_age: int,
    construction_status: str,
    legal_clearance_status: str,
    valuation_status: str,
    required_documents: list[str],
    submitted_documents: list[str],
    missing_documents: list[str],
    document_status: str,
    proposed_emi: float,
    ltv_ratio: float,
    dti_ratio: float,
    foir_ratio: float,
    max_affordable_new_emi: float,
    max_eligible_loan: float,
    loan_amount_gap: float,
) -> dict:
    """
    Run the deterministic prototype underwriting assessment.

    The agent must call this tool before giving an approval/rejection result.
    """

    state = {
        "name": name,
        "age": age,
        "employment_type": employment_type,
        "monthly_income": monthly_income,
        "work_experience_years": work_experience_years,
        "credit_score": credit_score,
        "existing_emi": existing_emi,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "tenure_years": tenure_years,
        "loan_purpose": loan_purpose,
        "property_value": property_value,
        "property_type": property_type,
        "property_location": property_location,
        "property_age": property_age,
        "construction_status": construction_status,
        "legal_clearance_status": legal_clearance_status,
        "valuation_status": valuation_status,
        "required_documents": required_documents,
        "submitted_documents": submitted_documents,
        "missing_documents": missing_documents,
        "document_status": document_status,
        "proposed_emi": proposed_emi,
        "ltv_ratio": ltv_ratio,
        "dti_ratio": dti_ratio,
        "foir_ratio": foir_ratio,
        "max_affordable_new_emi": max_affordable_new_emi,
        "max_eligible_loan": max_eligible_loan,
        "loan_amount_gap": loan_amount_gap,
    }

    (
        decision,
        risk_level,
        decision_reasons,
        risk_flags,
        positive_factors,
        recommended_actions,
    ) = run_underwriting_rules(state)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "decision_reasons": decision_reasons,
        "risk_flags": risk_flags,
        "positive_factors": positive_factors,
        "recommended_actions": recommended_actions,
        "underwriting_status": decision,
    }