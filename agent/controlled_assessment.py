"""
Controlled home-loan assessment runner.

This file runs the home-loan tools in the correct order instead of relying on
the local LLM to decide every tool call. The LLM can still be used for chat
and explanation, but the business-critical tool execution remains reliable.
"""

from tools.financial_tools import (
    calculate_emi_tool,
    calculate_ltv_tool,
    calculate_dti_tool,
    estimate_max_eligible_loan_tool,
)
from tools.verification_tools import (
    verify_kyc_tool,
    verify_cibil_tool,
)
from tools.document_tools import (
    get_required_documents_tool,
    find_missing_documents_tool,
)
from tools.underwriting_tools import run_initial_assessment_tool


def run_controlled_home_loan_assessment(application: dict) -> dict:
    """
    Run the full initial assessment in a fixed, reliable order.

    Expected application keys:
    - name
    - age
    - employment_type
    - monthly_income
    - work_experience_years
    - credit_score
    - existing_emi
    - loan_amount
    - interest_rate
    - tenure_years
    - loan_purpose
    - property_value
    - property_type
    - property_location
    - property_age
    - construction_status
    - legal_clearance_status
    - valuation_status
    - pan_available
    - id_proof_available
    - address_proof_available
    - submitted_documents
    """

    # 1. Mock KYC verification.
    kyc_result = verify_kyc_tool.invoke(
        {
            "pan_available": application["pan_available"],
            "id_proof_available": application["id_proof_available"],
            "address_proof_available": application["address_proof_available"],
        }
    )

    # 2. Mock CIBIL verification.
    cibil_result = verify_cibil_tool.invoke(
        {
            "credit_score": application["credit_score"],
        }
    )

    # 3. Financial calculations.
    emi_result = calculate_emi_tool.invoke(
        {
            "loan_amount": application["loan_amount"],
            "annual_interest_rate": application["interest_rate"],
            "tenure_years": application["tenure_years"],
        }
    )

    ltv_result = calculate_ltv_tool.invoke(
        {
            "loan_amount": application["loan_amount"],
            "property_value": application["property_value"],
        }
    )

    dti_result = calculate_dti_tool.invoke(
        {
            "existing_emi": application["existing_emi"],
            "proposed_emi": emi_result["proposed_emi"],
            "monthly_income": application["monthly_income"],
        }
    )

    eligibility_result = estimate_max_eligible_loan_tool.invoke(
        {
            "monthly_income": application["monthly_income"],
            "existing_emi": application["existing_emi"],
            "annual_interest_rate": application["interest_rate"],
            "tenure_years": application["tenure_years"],
        }
    )

    loan_amount_gap = max(
        round(application["loan_amount"] - eligibility_result["max_eligible_loan"], 2),
        0.0,
    )

    # 4. Document checklist.
    required_docs_result = get_required_documents_tool.invoke(
        {
            "employment_type": application["employment_type"],
            "property_type": application["property_type"],
        }
    )

    required_documents = required_docs_result["required_documents"]

    submitted_documents = application.get("submitted_documents", [])

    missing_docs_result = find_missing_documents_tool.invoke(
        {
            "required_documents": required_documents,
            "submitted_documents": submitted_documents,
        }
    )

    missing_documents = missing_docs_result["missing_documents"]
    document_status = missing_docs_result["document_status"]

    # 5. Underwriting assessment.
    assessment_result = run_initial_assessment_tool.invoke(
        {
            "name": application["name"],
            "age": application["age"],
            "employment_type": application["employment_type"],
            "monthly_income": application["monthly_income"],
            "work_experience_years": application["work_experience_years"],
            "credit_score": application["credit_score"],
            "existing_emi": application["existing_emi"],
            "loan_amount": application["loan_amount"],
            "interest_rate": application["interest_rate"],
            "tenure_years": application["tenure_years"],
            "loan_purpose": application["loan_purpose"],
            "property_value": application["property_value"],
            "property_type": application["property_type"],
            "property_location": application["property_location"],
            "property_age": application["property_age"],
            "construction_status": application["construction_status"],
            "legal_clearance_status": application["legal_clearance_status"],
            "valuation_status": application["valuation_status"],
            "required_documents": required_documents,
            "submitted_documents": submitted_documents,
            "missing_documents": missing_documents,
            "document_status": document_status,
            "proposed_emi": emi_result["proposed_emi"],
            "ltv_ratio": ltv_result["ltv_ratio"],
            "dti_ratio": dti_result["dti_ratio"],
            "foir_ratio": dti_result["foir_ratio"],
            "max_affordable_new_emi": eligibility_result["max_affordable_new_emi"],
            "max_eligible_loan": eligibility_result["max_eligible_loan"],
            "loan_amount_gap": loan_amount_gap,
        }
    )

    return {
        "application": application,
        "kyc": kyc_result,
        "cibil": cibil_result,
        "financial_metrics": {
            "proposed_emi": emi_result["proposed_emi"],
            "ltv_ratio": ltv_result["ltv_ratio"],
            "dti_ratio": dti_result["dti_ratio"],
            "foir_ratio": dti_result["foir_ratio"],
            "max_affordable_new_emi": eligibility_result["max_affordable_new_emi"],
            "max_eligible_loan": eligibility_result["max_eligible_loan"],
            "loan_amount_gap": loan_amount_gap,
        },
        "documents": {
            "required_documents": required_documents,
            "submitted_documents": submitted_documents,
            "missing_documents": missing_documents,
            "document_status": document_status,
        },
        "assessment": assessment_result,
    }