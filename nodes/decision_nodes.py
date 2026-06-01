# nodes/decision_nodes.py

import opik

from state import HomeLoanState
from services.rule_engine import run_underwriting_rules


@opik.track(name="underwriting_decision")
def underwriting_decision(state: HomeLoanState):
    """
    Runs deterministic underwriting rules and stores all decision facts.

    The rule engine returns:
    - final decision
    - overall risk level
    - decision reasons
    - risk flags
    - positive factors
    - recommended actions
    """

    (
        decision,
        risk_level,
        decision_reasons,
        risk_flags,
        positive_factors,
        recommended_actions,
    ) = run_underwriting_rules(state)

    state["decision"] = decision
    state["risk_level"] = risk_level
    state["decision_reasons"] = decision_reasons
    state["risk_flags"] = risk_flags
    state["positive_factors"] = positive_factors
    state["recommended_actions"] = recommended_actions
    state["underwriting_status"] = decision

    return state


@opik.track(name="decision_router")
def decision_router(state: HomeLoanState):
    """
    Routes the application to the correct response path.
    """

    if state["decision"] == "pre_approved":
        return "generate_loan_offer"

    if state["decision"] == "needs_documents":
        return "request_missing_documents"

    if state["decision"] == "manual_review":
        return "manual_review_response"

    return "rejected_response"