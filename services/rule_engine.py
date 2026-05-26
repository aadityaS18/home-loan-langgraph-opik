# services/rule_engine.py

import opik


@opik.track(name="underwriting_rule_engine")
def run_underwriting_rules(state: dict) -> tuple[str, str, list[str]]:
    """
    Rule-based underwriting engine.

    It collects all relevant risk reasons instead of stopping at the first issue.
    """

    reasons = []
    hard_rejection = False
    manual_review = False
    needs_documents = False
    risk_level = "low"

    if state["age"] < 21:
        hard_rejection = True
        reasons.append("Applicant age is below the minimum requirement of 21.")

    if state["monthly_income"] < 30000:
        hard_rejection = True
        reasons.append("Monthly income is below the minimum requirement of 30000.")

    if state["credit_score"] < 650:
        hard_rejection = True
        reasons.append("Credit score is below the acceptable threshold of 650.")
    elif 650 <= state["credit_score"] < 700:
        manual_review = True
        reasons.append("Credit score is moderate and requires manual review.")

    if state["dti_ratio"] > 55:
        hard_rejection = True
        reasons.append("Debt-to-income ratio is too high.")
    elif 45 <= state["dti_ratio"] <= 55:
        manual_review = True
        reasons.append("Debt-to-income ratio requires manual review.")

    if state["ltv_ratio"] > 90:
        manual_review = True
        reasons.append("Loan-to-value ratio is above 90%.")

    if state["missing_documents"]:
        needs_documents = True
        reasons.append("Some required documents are missing.")

    if state["legal_clearance_status"].lower() != "clear":
        manual_review = True
        reasons.append("Property legal clearance is not fully clear.")

    if state["valuation_status"].lower() != "clear":
        manual_review = True
        reasons.append("Property valuation requires review.")

    if hard_rejection:
        decision = "rejected"
        risk_level = "high"
    elif needs_documents:
        decision = "needs_documents"
        risk_level = "medium"
    elif manual_review:
        decision = "manual_review"
        risk_level = "medium"
    else:
        decision = "pre_approved"
        risk_level = "low"
        reasons.append("Applicant meets the main home-loan eligibility criteria.")

    return decision, risk_level, reasons


