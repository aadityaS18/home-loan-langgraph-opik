"""
Test the controlled home-loan assessment runner.

This confirms that all tools work in the correct order without depending on
the LLM to choose tools perfectly.
"""

from pprint import pprint

from agent.controlled_assessment import run_controlled_home_loan_assessment


BASE_DOCUMENTS = [
    "id_proof",
    "address_proof",
    "pan_card",
    "bank_statement",
    "property_title_deed",
    "sale_agreement",
    "salary_slips",
    "form_16",
    "employment_proof",
    "builder_noc",
    "approved_building_plan",
]


APPROVED_CASE = {
    "name": "Aryan",
    "age": 35,
    "employment_type": "salaried",
    "monthly_income": 150000,
    "work_experience_years": 8,
    "credit_score": 780,
    "existing_emi": 5000,
    "loan_amount": 3000000,
    "interest_rate": 8.5,
    "tenure_years": 20,
    "loan_purpose": "purchase",
    "property_value": 6000000,
    "property_type": "apartment",
    "property_location": "Bangalore",
    "property_age": 4,
    "construction_status": "ready_to_move",
    "legal_clearance_status": "clear",
    "valuation_status": "clear",
    "pan_available": True,
    "id_proof_available": True,
    "address_proof_available": True,
    "submitted_documents": BASE_DOCUMENTS,
}


REJECTED_CASE = {
    "name": "Rahul",
    "age": 32,
    "employment_type": "salaried",
    "monthly_income": 70000,
    "work_experience_years": 5,
    "credit_score": 730,
    "existing_emi": 10000,
    "loan_amount": 6000000,
    "interest_rate": 8.5,
    "tenure_years": 20,
    "loan_purpose": "purchase",
    "property_value": 7500000,
    "property_type": "apartment",
    "property_location": "Noida",
    "property_age": 3,
    "construction_status": "ready_to_move",
    "legal_clearance_status": "clear",
    "valuation_status": "clear",
    "pan_available": True,
    "id_proof_available": True,
    "address_proof_available": True,
    "submitted_documents": BASE_DOCUMENTS,
}


def run_case(case_name: str, application: dict):
    print(f"\n================ {case_name} ================")
    result = run_controlled_home_loan_assessment(application)

    print("\nDecision:", result["assessment"]["decision"])
    print("Risk Level:", result["assessment"]["risk_level"])
    print("KYC:", result["kyc"]["kyc_status"])
    print("CIBIL:", result["cibil"]["cibil_status"])
    print("Document Status:", result["documents"]["document_status"])

    print("\nFinancial Metrics:")
    pprint(result["financial_metrics"])

    print("\nDecision Reasons:")
    pprint(result["assessment"]["decision_reasons"])

    print("\nRisk Flags:")
    pprint(result["assessment"]["risk_flags"])

    print("\nRecommended Actions:")
    pprint(result["assessment"]["recommended_actions"])


if __name__ == "__main__":
    run_case("APPROVED CASE", APPROVED_CASE)
    run_case("REJECTED CASE", REJECTED_CASE)