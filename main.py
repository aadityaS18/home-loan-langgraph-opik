# main.py
import os
import opik
from opik.integrations.langchain import OpikTracer

from graph import build_home_loan_graph


os.environ.setdefault("OPIK_BASE_URL", "http://localhost:5293/api")
os.environ.setdefault("OPIK_PROJECT_NAME", "home-loan-langgraph")

opik_tracer = OpikTracer(project_name="home-loan-langgraph")

@opik.track(name="home-loan-journey", project_name="home-loan-langgraph")
def run_home_loan_application(app, application):
    return app.invoke(
        application,
        config={"callbacks": [opik_tracer]},
    )

from graph import build_home_loan_graph
from services.document_service import generate_required_documents


#opik.configure(
    #use_local=True,
   # project_name="home-loan-langgraph",
#)

#opik_tracer = OpikTracer(project_name="home-loan-langgraph")


def get_string_input(prompt: str, default: str = "") -> str:
    value = input(prompt).strip()
    return value if value else default


def get_int_input(prompt: str, default: int = 0) -> int:
    while True:
        value = input(prompt).strip()

        if value == "":
            return default

        try:
            return int(value)
        except ValueError:
            print("Please enter a valid whole number.")


def get_float_input(prompt: str, default: float = 0.0) -> float:
    while True:
        value = input(prompt).strip()

        if value == "":
            return default

        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")


def ask_yes_no(prompt: str) -> bool:
    while True:
        value = input(prompt + " (yes/no): ").strip().lower()

        if value in ["yes", "y"]:
            return True

        if value in ["no", "n"]:
            return False

        print("Please answer yes or no.")


def collect_submitted_documents(employment_type: str, property_type: str) -> list[str]:
    """
    Generates required documents based on applicant/property type,
    then asks the user which documents are submitted.
    """

    required_documents = generate_required_documents(
        employment_type=employment_type,
        property_type=property_type,
    )

    submitted_documents = []

    print("\n--- DOCUMENT CHECKLIST ---")
    print("Please answer whether the applicant has submitted each document:")

    for document in required_documents:
        has_document = ask_yes_no(f"Has the applicant submitted {document}?")
        if has_document:
            submitted_documents.append(document)

    return submitted_documents


def get_user_application() -> dict:
    """
    Collects a realistic home-loan application from terminal input.
    """

    print("\n==============================")
    print(" HOME LOAN APPLICATION JOURNEY")
    print("==============================")

    print("\n--- CUSTOMER PROFILE ---")
    name = get_string_input("Applicant name: ", "Test User")
    age = get_int_input("Age: ")
    employment_type = get_string_input("Employment type (salaried/self-employed): ", "salaried")
    monthly_income = get_float_input("Monthly income: ")
    work_experience_years = get_float_input("Work experience in years: ")
    credit_score = get_int_input("Credit score: ")
    existing_emi = get_float_input("Existing EMI amount: ")

    print("\n--- LOAN REQUIREMENT ---")
    loan_amount = get_float_input("Requested loan amount: ")
    interest_rate = get_float_input("Interest rate, example 8.5: ", 8.5)
    tenure_years = get_int_input("Tenure in years: ", 20)
    loan_purpose = get_string_input("Loan purpose (purchase/construction/refinance): ", "purchase")

    print("\n--- PROPERTY DETAILS ---")
    property_value = get_float_input("Property value: ")
    property_type = get_string_input("Property type (apartment/flat/house/plot): ", "apartment")
    property_location = get_string_input("Property location: ", "Not provided")
    property_age = get_int_input("Property age in years: ", 0)
    construction_status = get_string_input("Construction status (ready_to_move/under_construction): ", "ready_to_move")
    legal_clearance_status = get_string_input("Legal clearance status (clear/pending/issue): ", "clear")
    valuation_status = get_string_input("Valuation status (clear/pending/issue): ", "clear")

    submitted_documents = collect_submitted_documents(
        employment_type=employment_type,
        property_type=property_type,
    )

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
        "proposed_emi": 0,
        "ltv_ratio": 0,
        "dti_ratio": 0,
        "foir_ratio": 0,

        # Decision fields
        "risk_level": "",
        "underwriting_status": "",
        "decision": "",
        "decision_reasons": [],

        # LLM-generated outputs
        "customer_explanation": "",
        "officer_summary": "",
    }

    return application


@opik.track(name="home_loan_journey")
def run_home_loan_application(app, application):
    """
    Parent trace for the full home-loan journey.
    Uses OpikTracer for LangGraph/LangChain callback tracing.
    """

    return app.invoke(
        application,
        config={"callbacks": [opik_tracer]},
    )


def print_result(result: dict):
    print("\n==============================")
    print(" HOME LOAN RESULT")
    print("==============================")

    print("Applicant:", result["name"])
    print("Decision:", result["decision"])
    print("Risk Level:", result["risk_level"])
    print("Underwriting Status:", result["underwriting_status"])

    print("\n--- FINANCIAL METRICS ---")
    print("Proposed EMI:", result["proposed_emi"])
    print("LTV Ratio:", str(result["ltv_ratio"]) + "%")
    print("DTI Ratio:", str(result["dti_ratio"]) + "%")
    print("FOIR Ratio:", str(result["foir_ratio"]) + "%")

    print("\n--- DOCUMENT STATUS ---")
    print("Document Status:", result["document_status"])
    print("Missing Documents:", result["missing_documents"])

    print("\n--- DECISION REASONS ---")
    for reason in result["decision_reasons"]:
        print("-", reason)

    print("\n--- AI CUSTOMER EXPLANATION ---")
    print(result["customer_explanation"])


    print("\n--- OFFICER SUMMARY ---")
    print(result["officer_summary"])


def main():
    app = build_home_loan_graph()

    while True:
        application = get_user_application()
        result = run_home_loan_application(app, application)
        print_result(result)

        another = ask_yes_no("\nDo you want to check another application?")
        if not another:
            break

    opik_tracer.flush()
    print("\nFinished home-loan journey.")


if __name__ == "__main__":
    main()


