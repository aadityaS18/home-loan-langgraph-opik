"""
Mock verification tools for the home-loan agent.

These tools simulate KYC and CIBIL checks for prototype development.
They are not real external integrations.
"""

from langchain_core.tools import tool


@tool
def verify_kyc_tool(
    pan_available: bool,
    id_proof_available: bool,
    address_proof_available: bool,
) -> dict:
    """
    Mock KYC verification.

    Returns verified only when PAN, ID proof and address proof are available.
    """

    missing_items = []

    if not pan_available:
        missing_items.append("pan_card")

    if not id_proof_available:
        missing_items.append("id_proof")

    if not address_proof_available:
        missing_items.append("address_proof")

    if missing_items:
        return {
            "kyc_status": "pending",
            "verified": False,
            "missing_items": missing_items,
            "reason": "Mock KYC check pending because required identity documents are missing.",
        }

    return {
        "kyc_status": "verified",
        "verified": True,
        "missing_items": [],
        "reason": "Mock KYC check passed.",
    }


@tool
def verify_cibil_tool(credit_score: int) -> dict:
    """
    Mock CIBIL verification using the supplied credit score.

    This is not a live CIBIL integration.
    """

    if credit_score >= 700:
        return {
            "cibil_status": "acceptable",
            "score": credit_score,
            "risk_band": "low",
            "reason": "Credit score is acceptable under the prototype rule.",
        }

    if credit_score >= 650:
        return {
            "cibil_status": "review_required",
            "score": credit_score,
            "risk_band": "medium",
            "reason": "Credit score requires manual review under the prototype rule.",
        }

    return {
        "cibil_status": "high_risk",
        "score": credit_score,
        "risk_band": "high",
        "reason": "Credit score is below the acceptable prototype threshold.",
    }