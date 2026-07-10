"""
Document tools for the home-loan agent.
"""

from langchain_core.tools import tool

from services.document_service import generate_required_documents, find_missing_documents


@tool
def get_required_documents_tool(
    employment_type: str,
    property_type: str,
) -> dict:
    """Return required documents based on employment type and property type."""
    required_documents = generate_required_documents(
        employment_type=employment_type,
        property_type=property_type,
    )

    return {
        "employment_type": employment_type,
        "property_type": property_type,
        "required_documents": required_documents,
    }


@tool
def find_missing_documents_tool(
    required_documents: list[str],
    submitted_documents: list[str],
) -> dict:
    """Return documents missing from the submitted document list."""
    missing_documents = find_missing_documents(
        required_documents=required_documents,
        submitted_documents=submitted_documents,
    )

    return {
        "required_documents": required_documents,
        "submitted_documents": submitted_documents,
        "missing_documents": missing_documents,
        "document_status": "complete" if not missing_documents else "incomplete",
    }