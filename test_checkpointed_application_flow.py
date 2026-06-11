"""
Test checkpointed application journey.

Run:
    python test_checkpointed_application_flow.py
"""

from pprint import pprint

from agent.checkpointed_application_flow import (
    get_application_progress,
    is_ready_for_submission,
    save_applicant_details,
    save_document_details,
    save_loan_details,
    save_property_details,
    start_application_thread,
)


def print_progress(title: str, state: dict):
    """Print checkpointed application progress."""

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("Thread ID:", state.get("thread_id"))
    print("Current Step:", state.get("current_step"))
    print("Completed Steps:", state.get("completed_steps"))
    print("Ready For Submission:", is_ready_for_submission(state))
    print("\nMessages:")
    for message in state.get("messages", []):
        print("-", message)


def main():
    """Run checkpointed application flow test."""

    thread_id = "loan-application-thread-001"

    state = start_application_thread(thread_id)
    print_progress("Initial application thread", state)

    state = save_applicant_details(
        thread_id,
        {
            "name": "Sample Applicant",
            "age": 35,
            "employment_type": "salaried",
            "monthly_income": 150000.0,
            "work_experience_years": 8.0,
            "credit_score": 780,
            "existing_emi": 5000.0,
        },
    )
    print_progress("After applicant details", state)

    state = save_loan_details(
        thread_id,
        {
            "loan_amount": 3000000.0,
            "interest_rate": 8.5,
            "tenure_years": 20,
            "loan_purpose": "purchase",
        },
    )
    print_progress("After loan details", state)

    state = save_property_details(
        thread_id,
        {
            "property_value": 6000000.0,
            "property_type": "apartment",
            "property_location": "Bangalore",
            "property_age": 4,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
        },
    )
    print_progress("After property details", state)

    state = save_document_details(
        thread_id,
        {
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
        },
    )
    print_progress("After document details", state)

    saved_state = get_application_progress(thread_id)
    print_progress("Saved progress loaded from PostgreSQL checkpoint", saved_state)

    print("\nFull saved state:")
    pprint(saved_state)


if __name__ == "__main__":
    main()