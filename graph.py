#Edges define the order in which the nodes run.

from langgraph.graph import StateGraph, END

from state import HomeLoanState

from nodes import (
    collect_user_details,
    check_eligibility,
    check_affordability,
    check_documents,
    risk_assessment,
    make_decision,
    approved_response,
    missing_docs_response,
    rejected_response,
    route_decision,
)


def build_home_loan_graph():
    """
    Builds the LangGraph workflow for the home loan journey.
    """

    workflow = StateGraph(HomeLoanState)

    # Add all nodes
    workflow.add_node("collect_user_details", collect_user_details)
    workflow.add_node("check_eligibility", check_eligibility)
    workflow.add_node("check_affordability", check_affordability)
    workflow.add_node("check_documents", check_documents)
    workflow.add_node("risk_assessment", risk_assessment)
    workflow.add_node("make_decision", make_decision)

    # Add final response nodes
    workflow.add_node("approved_response", approved_response)
    workflow.add_node("missing_docs_response", missing_docs_response)
    workflow.add_node("rejected_response", rejected_response)

    # Starting point
    workflow.set_entry_point("collect_user_details")

    # Normal flow
    workflow.add_edge("collect_user_details", "check_eligibility")
    workflow.add_edge("check_eligibility", "check_affordability")
    workflow.add_edge("check_affordability", "check_documents")
    workflow.add_edge("check_documents", "risk_assessment")
    workflow.add_edge("risk_assessment", "make_decision")

    # Conditional routing after decision
    workflow.add_conditional_edges(
        "make_decision",
        route_decision,
        {
            "approved_response": "approved_response",
            "missing_docs_response": "missing_docs_response",
            "rejected_response": "rejected_response",
        },
    )

    # End points
    workflow.add_edge("approved_response", END)
    workflow.add_edge("missing_docs_response", END)
    workflow.add_edge("rejected_response", END)

    return workflow.compile()






