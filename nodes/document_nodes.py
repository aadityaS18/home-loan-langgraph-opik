
"""
Document Verification Node

This LangGraph node handles the document-checking stage of the home-loan
journey.

The required document checklist is generated dynamically based on:
- Employment type of the applicant.
- Type of property being financed.

For example:
- A salaried applicant may require salary slips and Form 16.
- A self-employed applicant may require ITR returns and business proof.
- An apartment may require builder-related documents.
- A plot may require land-related documents.

The node compares the required documents with the submitted documents and
stores the missing-document result in the shared workflow state.

Inputs read from state:
- employment_type
- property_type
- submitted_documents

Outputs added to state:
- required_documents
- missing_documents
- document_status
"""


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