# main.py

import os

# ---------------------------------------------------------
# Opik local Docker configuration
# IMPORTANT:
# Set these BEFORE importing graph.py because graph.py imports
# LLM nodes and creates Opik/LangChain tracers.
# ---------------------------------------------------------

PROJECT_NAME = "home-loan-langgraph"
OPIK_LOCAL_URL = "http://localhost:5293/api"

os.environ["OPIK_BASE_URL"] = OPIK_LOCAL_URL
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import opik
from opik.integrations.langchain import OpikTracer

from graph import build_home_loan_graph
from services.document_service import generate_required_documents


# ---------------------------------------------------------
# Opik tracer
# ---------------------------------------------------------

opik_tracer = OpikTracer(project_name=PROJECT_NAME)


# ---------------------------------------------------------
# Input helper functions
# ---------------------------------------------------------

def get_string_input(prompt: str, default: str = "") -> str:
    """
    Reads a text value from the user.
    Uses the supplied default when the user submits an empty value.
    """

    value = input(prompt).strip()
    return value if value else default


def get_int_input(prompt: str, default: int = 0) -> int:
    """
    Reads a whole number safely.
    Prevents the application from crashing on blank or invalid input.
    """

    while True:
        value = input(prompt).strip()

        if value == "":
            return default

        try:
            return int(value)
        except ValueError:
            print("Please enter a valid whole number.")


def get_float_input(prompt: str, default: float = 0.0) -> float:
    """
    Reads a numeric value safely.
    Prevents the application from crashing on blank or invalid input.
    """

    while True:
        value = input(prompt).strip()

        if value == "":
            return default

        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")


def get_choice_input(
    prompt: str,
    valid_choices: list[str],
    default: str | None = None,
) -> str:
    """
    Reads a fixed-choice value safely.

    This prevents spelling mistakes such as 'alaried' being treated
    as a self-employed applicant.
    """

    options = "/".join(valid_choices)

    while True:
        default_text = f" [default: {default}]" if default else ""
        value = input(f"{prompt} ({options}){default_text}: ").strip().lower()

        if value == "" and default:
            return default

        if value in valid_choices:
            return value

        print(f"Please enter one of: {options}")


def ask_yes_no(prompt: str) -> bool:
    """
    Accepts only yes/no answers.
    """

    while True:
        value = input(f"{prompt} (yes/no): ").strip().lower()

        if value in ["yes", "y"]:
            return True

        if value in ["no", "n"]:
            return False

        print("Please answer yes or no.")


# ---------------------------------------------------------
# Document input
# ---------------------------------------------------------

def collect_submitted_documents(
    employment_type: str,
    property_type: str,
) -> list[str]:
    """
    Generates the required document checklist dynamically,
    then asks the applicant which documents have been submitted.
    """

    required_documents = generate_required_documents(
        employment_type=employment_type,
        property_type=property_type,
    )

    submitted_documents: list[str] = []

    print("\n--- DOCUMENT CHECKLIST ---")
    print("Please answer whether the applicant has submitted each document:")

    for document in required_documents:
        if ask_yes_no(f"Has the applicant submitted {document}?"):
            submitted_documents.append(document)

    return submitted_documents


# ---------------------------------------------------------
# Application input
# ---------------------------------------------------------

def get_user_application() -> dict:
    """
    Collects a complete home-loan application through terminal input.
    """

    print("\n==============================")
    print(" HOME LOAN APPLICATION JOURNEY")
    print("==============================")

    # -----------------------------------------------------
    # Customer profile
    # -----------------------------------------------------

    print("\n--- CUSTOMER PROFILE ---")

    name = get_string_input("Applicant name: ", "Test User")
    age = get_int_input("Age: ")

    employment_type = get_choice_input(
        "Employment type",
        ["salaried", "self-employed"],
        
    )

    monthly_income = get_float_input("Monthly income: ")
    work_experience_years = get_float_input("Work experience in years: ")
    credit_score = get_int_input("Credit score: ")
    existing_emi = get_float_input("Existing EMI amount: ")

    # -----------------------------------------------------
    # Loan requirement
    # -----------------------------------------------------

    print("\n--- LOAN REQUIREMENT ---")

    loan_amount = get_float_input("Requested loan amount: ")
    interest_rate = get_float_input("Interest rate, example 8.5: ", 8.5)
    tenure_years = get_int_input("Tenure in years: ", 20)

    loan_purpose = get_choice_input(
        "Loan purpose",
        ["purchase", "construction", "refinance"],
        
    )

    # -----------------------------------------------------
    # Property details
    # -----------------------------------------------------

    print("\n--- PROPERTY DETAILS ---")

    property_value = get_float_input("Property value: ")

    property_type = get_choice_input(
        "Property type",
        ["apartment", "flat", "house", "plot"],
       
    )

    property_location = get_string_input(
        "Property location: ",
        "Not provided",
    )

    property_age = get_int_input("Property age in years: ", 0)

    construction_status = get_choice_input(
        "Construction status",
        ["ready_to_move", "under_construction"],
        
    )

    legal_clearance_status = get_choice_input(
        "Legal clearance status",
        ["clear", "pending", "issue"],
        
    )

    valuation_status = get_choice_input(
        "Valuation status",
        ["clear", "pending", "issue"],
        
    )

   

    submitted_documents = collect_submitted_documents(
        employment_type=employment_type,
        property_type=property_type,
    )

    # -----------------------------------------------------
    # Initial LangGraph state
    # -----------------------------------------------------

    application = {
        # Customer profile
        "name": name,
        "age": age,
        "employment_type": employment_type,
        "monthly_income": monthly_income,
        "work_experience_years": work_experience_years,
        "credit_score": credit_score,
        "existing_emi": existing_emi,

        # Loan requirement
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "tenure_years": tenure_years,
        "loan_purpose": loan_purpose,

        # Property details
        "property_value": property_value,
        "property_type": property_type,
        "property_location": property_location,
        "property_age": property_age,
        "construction_status": construction_status,
        "legal_clearance_status": legal_clearance_status,
        "valuation_status": valuation_status,

        # Documents
        "submitted_documents": submitted_documents,
        "required_documents": [],
        "missing_documents": [],
        "document_status": "",

        # Calculated financial values
        "proposed_emi": 0.0,
        "ltv_ratio": 0.0,
        "dti_ratio": 0.0,
        "foir_ratio": 0.0,

        "max_affordable_new_emi": 0.0,
        "max_eligible_loan": 0.0,
        "loan_amount_gap": 0.0,

        # Decision fields
        "risk_level": "",
        "underwriting_status": "",
        "decision": "",
        "decision_reasons": [],

        # Phase 3A deterministic analysis fields
        "risk_flags": [],
        "positive_factors": [],
        "recommended_actions": [],

        # LLM-generated outputs
        "customer_explanation": "",
        "officer_summary": "",
    }

    return application


# ---------------------------------------------------------
# Home-loan workflow execution
# ---------------------------------------------------------

@opik.track(
    name="home_loan_journey",
    project_name=PROJECT_NAME,
)
def run_home_loan_application(app, application: dict) -> dict:
    """
    Parent Opik trace for one complete home-loan application.

    The compiled LangGraph workflow runs inside this parent trace.
    OpikTracer captures LangGraph/LangChain execution details.
    """

    return app.invoke(
        application,
        config={"callbacks": [opik_tracer]},
    )


# ---------------------------------------------------------
# Result display
# ---------------------------------------------------------

def print_result(result: dict) -> None:
    """
    Prints the complete loan assessment result.
    """

    print("\n==============================")
    print(" HOME LOAN RESULT")
    print("==============================")

    print("Applicant:", result["name"])
    print("Decision:", result["decision"])
    print("Risk Level:", result["risk_level"])
    print("Underwriting Status:", result["underwriting_status"])

    print("\n--- FINANCIAL METRICS ---")
    print("Requested Loan Amount:", result["loan_amount"])
    print("Proposed EMI:", result["proposed_emi"])
    print("LTV Ratio:", f'{result["ltv_ratio"]}%')
    print("DTI Ratio:", f'{result["dti_ratio"]}%')
    print("FOIR Ratio:", f'{result["foir_ratio"]}%')

    print("\n--- ESTIMATED LOAN ELIGIBILITY ---")
    print("Maximum Affordable New EMI:", result["max_affordable_new_emi"])
    print("Estimated Maximum Eligible Loan:", result["max_eligible_loan"])

    if result["loan_amount_gap"] > 0:
        print("Requested Amount Above Estimate:", result["loan_amount_gap"])
    else:
        print("Requested loan amount is within the estimated affordability limit.")

    print("\n--- DOCUMENT STATUS ---")
    print("Document Status:", result["document_status"])
    print("Missing Documents:", result["missing_documents"])

    print("\n--- DECISION REASONS ---")
    if result["decision_reasons"]:
        for reason in result["decision_reasons"]:
            print("-", reason)
    else:
        print("- None")

    print("\n--- POSITIVE FACTORS ---")
    if result["positive_factors"]:
        for factor in result["positive_factors"]:
            print("-", factor)
    else:
        print("- None")

    print("\n--- RISK FLAGS ---")
    if result["risk_flags"]:
        for flag in result["risk_flags"]:
            print("-", flag)
    else:
        print("- None")

    print("\n--- RECOMMENDED ACTIONS ---")
    if result["recommended_actions"]:
        for action in result["recommended_actions"]:
            print("-", action)
    else:
        print("- None")

    print("\n--- AI CUSTOMER EXPLANATION ---")
    print(result["customer_explanation"])

    print("\n--- OFFICER SUMMARY (EXPERIMENTAL - UNDER REFINEMENT) ---")
    print(result["officer_summary"])




def main() -> None:
    """
    Starts the interactive home-loan journey application.
    """

    app = build_home_loan_graph()

    while True:
        application = get_user_application()
        result = run_home_loan_application(app, application)

        print_result(result)

        if not ask_yes_no("\nDo you want to check another application?"):
            break

    
    opik_tracer.flush()

    print("\nFinished home-loan journey.")


if __name__ == "__main__":
    main()


