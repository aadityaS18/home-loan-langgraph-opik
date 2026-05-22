#Edges define the order in which the nodes run.

#Trace: full application run 
#Spans:each workflow step

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

    workflow = StateGraph(HomeLoanState)# over here this creates the langgraph worflow using homeloanstate

    # Add all nodes

    # over here each home-loan steo is added as a node.Edges define the flow between steps  and  to tell if application is rejected,accpted or missing documents
    workflow.add_node("collect_user_details", collect_user_details)
    workflow.add_node("check_eligibility", check_eligibility)# this tell when we use check_eleigibilty if theels functn to run it and checks if it seleigible
    workflow.add_node("check_affordability", check_affordability)
    workflow.add_node("check_documents", check_documents)
    workflow.add_node("risk_assessment", risk_assessment)
    workflow.add_node("make_decision", make_decision)

    # used here to add each step of home-loan journey into langgraph workflow
    workflow.add_node("approved_response", approved_response)
    workflow.add_node("missing_docs_response", missing_docs_response)
    workflow.add_node("rejected_response", rejected_response)

    # Starting point
    workflow.set_entry_point("collect_user_details")

    # is used to connect two nodes and define the order in which they run 
    workflow.add_edge("collect_user_details", "check_eligibility")#after checkeligible is complete it goes to the next check affordbility 
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






