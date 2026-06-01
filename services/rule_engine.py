# services/rule_engine.py

import opik


@opik.track(name="underwriting_rule_engine")
def run_underwriting_rules(
    state: dict,
) -> tuple[str, str, list[str], list[str], list[str], list[str]]:
    """
    Prototype underwriting rule engine.

    Important:
    - These thresholds are project/demo rules, not a specific bank policy.
    - The Python rule engine decides the assessment.
    - The LLM only explains the result later.

    Returns:
        decision
        risk_level
        decision_reasons
        risk_flags
        positive_factors
        recommended_actions
    """

    decision_reasons = []
    risk_flags = []
    positive_factors = []
    recommended_actions = []

    has_rejection_reason = False
    requires_manual_review = False
    requires_documents = False

    # ---------------------------------------------------------
    # Applicant eligibility checks
    # ---------------------------------------------------------

    if state["age"] < 21:
        has_rejection_reason = True
        reason = "Applicant age is below the minimum prototype requirement of 21 years."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Applicant can reconsider applying after meeting the minimum age requirement."
        )
    else:
        positive_factors.append("Applicant meets the minimum age requirement.")

    if state["monthly_income"] < 30000:
        has_rejection_reason = True
        reason = "Monthly income is below the prototype minimum requirement of 30000."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Consider applying with higher stable income or an eligible co-applicant."
        )
    else:
        positive_factors.append("Monthly income meets the minimum prototype requirement.")

    # ---------------------------------------------------------
    # Credit assessment
    # ---------------------------------------------------------

    if state["credit_score"] < 650:
        has_rejection_reason = True
        reason = "Credit score is below the acceptable prototype threshold of 650."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Improve credit profile before submitting a new application."
        )
    elif state["credit_score"] < 700:
        requires_manual_review = True
        reason = "Credit score is moderate and requires manual review."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Provide supporting income and repayment documents for review."
        )
    else:
        positive_factors.append("Credit score is within the acceptable range.")

    # ---------------------------------------------------------
    # Affordability assessment
    # ---------------------------------------------------------

    if state["dti_ratio"] > 55:
        has_rejection_reason = True
        reason = "Debt-to-income ratio is above the prototype limit of 55%."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Reduce existing obligations or request a lower loan amount."
        )
    elif state["dti_ratio"] >= 45:
        requires_manual_review = True
        reason = "Debt-to-income ratio is between 45% and 55% and requires review."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Consider a lower loan amount or longer tenure to reduce EMI burden."
        )
    else:
        positive_factors.append(
            f"DTI ratio of {state['dti_ratio']}% is within the prototype acceptable range."
        )

    # ---------------------------------------------------------
    # Property financing assessment
    # ---------------------------------------------------------

    if state["ltv_ratio"] > 90:
        requires_manual_review = True
        reason = "Loan-to-value ratio is above 90% and requires review."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Consider increasing the down payment to reduce the LTV ratio."
        )
    else:
        positive_factors.append(
            f"LTV ratio of {state['ltv_ratio']}% is within the prototype acceptable range."
        )

    # ---------------------------------------------------------
    # Document assessment
    # ---------------------------------------------------------

    if state["missing_documents"]:
        requires_documents = True
        missing_docs_text = ", ".join(state["missing_documents"])
        reason = f"Required documents are missing: {missing_docs_text}."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            f"Submit the missing documents: {missing_docs_text}."
        )
    else:
        positive_factors.append("All required documents have been submitted.")

    # ---------------------------------------------------------
    # Property verification assessment
    # ---------------------------------------------------------

    if state["legal_clearance_status"].lower() != "clear":
        requires_manual_review = True
        reason = "Property legal clearance is not marked as clear."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Complete property legal verification before proceeding."
        )
    else:
        positive_factors.append("Property legal clearance is marked as clear.")

    if state["valuation_status"].lower() != "clear":
        requires_manual_review = True
        reason = "Property valuation status is not marked as clear."
        decision_reasons.append(reason)
        risk_flags.append(reason)
        recommended_actions.append(
            "Complete property valuation review before proceeding."
        )
    else:
        positive_factors.append("Property valuation status is marked as clear.")

    # ---------------------------------------------------------
    # Final decision priority
    # ---------------------------------------------------------

    if has_rejection_reason:
        decision = "rejected"
        risk_level = "high"
    elif requires_documents:
        decision = "needs_documents"
        risk_level = "medium"
    elif requires_manual_review:
        decision = "manual_review"
        risk_level = "medium"
    else:
        decision = "pre_approved"
        risk_level = "low"
        decision_reasons.append(
            "Applicant meets the current prototype pre-approval criteria."
        )
        recommended_actions.append(
            "Proceed to detailed verification and final lender review."
        )

    return (
        decision,
        risk_level,
        decision_reasons,
        risk_flags,
        positive_factors,
        recommended_actions,
    )


