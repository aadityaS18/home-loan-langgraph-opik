#Edges define the order in which the nodes run.

#Trace: full application run 
#Spans:each workflow step

# graph.py

from langgraph.graph import StateGraph, END

from state import HomeLoanState

from nodes.financial_nodes import calculate_financial_metrics
from nodes.document_nodes import verify_documents
from nodes.decision_nodes import underwriting_decision, decision_router
from nodes.llm_nodes import generate_customer_explanation
from nodes.llm_nodes import generate_customer_explanation, generate_officer_summary

def build_home_loan_graph():
    """
    Builds the upgraded LangGraph home-loan journey workflow.
    """

    workflow = StateGraph(HomeLoanState)

    # Main workflow nodes
    workflow.add_node("calculate_financial_metrics", calculate_financial_metrics)
    workflow.add_node("verify_documents", verify_documents)
    workflow.add_node("underwriting_decision", underwriting_decision)

    # Final response nodes use the LLM explanation node
    workflow.add_node("generate_loan_offer", generate_customer_explanation)
    workflow.add_node("request_missing_documents", generate_customer_explanation)
    workflow.add_node("manual_review_response", generate_customer_explanation)
    workflow.add_node("rejected_response", generate_customer_explanation)
    workflow.add_node("generate_officer_summary", generate_officer_summary)
    # Starting point
    workflow.set_entry_point("calculate_financial_metrics")

    # Main flow
    workflow.add_edge("calculate_financial_metrics", "verify_documents")
    workflow.add_edge("verify_documents", "underwriting_decision")

    # Conditional decision routing
    workflow.add_conditional_edges(
        "underwriting_decision",
        decision_router,
        {
            "generate_loan_offer": "generate_loan_offer",
            "request_missing_documents": "request_missing_documents",
            "manual_review_response": "manual_review_response",
            "rejected_response": "rejected_response",
        },
    )

    # End points
    workflow.add_edge("generate_loan_offer", END)
    workflow.add_edge("request_missing_documents", END)
    workflow.add_edge("manual_review_response", END)
    workflow.add_edge("rejected_response", END)

    workflow.add_edge("generate_loan_offer", "generate_officer_summary")
    workflow.add_edge("request_missing_documents", "generate_officer_summary")
    workflow.add_edge("manual_review_response", "generate_officer_summary")
    workflow.add_edge("rejected_response", "generate_officer_summary")
    workflow.add_edge("generate_officer_summary", END)

    return workflow.compile()