

import opik

from state import HomeLoanState
from services.document_service import generate_required_documents, find_missing_documents


@opik.track(name="verify_documents")
def verify_documents(state: HomeLoanState):
    """
    LangGraph node:
    Generates required documents and checks missing documents.
    """

    required_docs = generate_required_documents(
        employment_type=state["employment_type"],
        property_type=state["property_type"],
    )

    missing_docs = find_missing_documents(
        required_documents=required_docs,
        submitted_documents=state["submitted_documents"],
    )

    state["required_documents"] = required_docs
    state["missing_documents"] = missing_docs

    if missing_docs:
        state["document_status"] = "incomplete"
    else:
        state["document_status"] = "complete"

    return state       