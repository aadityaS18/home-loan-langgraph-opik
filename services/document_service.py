# services/document_service.py

import opik


@opik.track(name="generate_required_documents")
def generate_required_documents(employment_type: str, property_type: str) -> list[str]:
    """
    Generates a document checklist based on employment type and property type.
    """

    common_docs = [
        "id_proof",
        "address_proof",
        "pan_card",
        "bank_statement",
        "property_title_deed",
        "sale_agreement",
    ]

    if employment_type.lower() == "salaried":
        income_docs = [
            "salary_slips",
            "form_16",
            "employment_proof",
        ]
    else:
        income_docs = [
            "itr_returns",
            "business_proof",
            "profit_loss_statement",
        ]

    if property_type.lower() in ["apartment", "flat"]:
        property_docs = [
            "builder_noc",
            "approved_building_plan",
        ]
    else:
        property_docs = [
            "land_record",
            "property_tax_receipt",
        ]

    return common_docs + income_docs + property_docs


@opik.track(name="find_missing_documents")
def find_missing_documents(required_documents: list[str], submitted_documents: list[str]) -> list[str]:
    """
    Returns documents that are required but not submitted.
    """

    return [doc for doc in required_documents if doc not in submitted_documents]
