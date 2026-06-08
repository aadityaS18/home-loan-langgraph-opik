"""
Test the controlled home-loan assessment runner.

This confirms that all tools work in the correct order without depending on
the LLM to choose tools perfectly.
"""

from pprint import pprint

from agent.controlled_assessment import run_controlled_home_loan_assessment


application = {
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
    "submitted_documents": [
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
    ],
}


if __name__ == "__main__":
    result = run_controlled_home_loan_assessment(application)
    pprint(result)