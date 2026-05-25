import opik

from state import HomeLoanState
from services.rule_engine import run_underwriting_rules



@opik.track(name="underwritting_decision")

def underwrtiting_decision(state:HomeLoanState):
    """
    Langgraph node: Runs rule-based underwriting and updates final decison fields """


    decision,risk_level,resons=run_underwriting_rules(state)


    state["decision"]=decision
    state["risk_level"]=risk_level
    state["decision_reasons"]=reasons
    state["underwriting_status"]=decision

    return state


@opik.track(name="decision_router")




def decision_router(state:HomeLoanState):

    """Langgraph conditional router:
    sends workflow to the correct final node"""


    if state["decision"]=="pre_approved":
        return "generate_loan_offer"
    
    if state["decision"]=="needs_documents":
        return "request_missing_documets"
    
    if state["decision"]=="rejected":
        return "rejected_response"

    if state["decision"]=="needs_review":
        return "review_application"
    
    return "manual_review_response"