# main.py




# workflow User enters details
   #   ↓
#collect_user_details
 #     ↓
#check_eligibility
 #     ↓
#check_affordability
 #     ↓
##check_documents
  #    ↓
#risk_assessment
 #     ↓
#make_decision
 #     ↓
#route_decision
 #  /        |          \
#approved  missing docs  rejected

from graph import build_home_loan_graph
import opik
from opik import track

opik.configure(
    project_name="home-loan-langgraph"# connects the project to opik cloud under home-loan-langgraph 
)

@track(name="run_home_loan_application")# this tracks one complete home-loan application run as parent trace
def run_home_loan_application(app,application):
    """Parent trace for one full home-loan application run."""
    return app.invoke(application)


def get_documents_from_user():
    """
    This function asks the user which documents they have submitted.
    It returns a list of selected documents.
    """

    documents = []

    print("\nAnswer yes/no for each document:")

    id_proof = input("Do you have ID proof? ").lower()
    if id_proof == "yes":
        documents.append("id_proof")

    income_proof = input("Do you have income proof? ").lower()
    if income_proof == "yes":
        documents.append("income_proof")

    bank_statement = input("Do you have bank statement? ").lower()
    if bank_statement == "yes":
        documents.append("bank_statement")

    property_documents = input("Do you have property documents? ").lower()
    if property_documents == "yes":
        documents.append("property_documents")

    return documents



def get_int_input(prompt):
    """
    Keeps asking until the user enters a valid number.
    If user presses Enter without typing anything, it uses 0.
    """

    while True:
        value = input(prompt)

        if value == "":
            return 0

        try:
            return int(value)
        except ValueError:
            print("Please enter a valid number.")


def get_user_application():
    """
    This function manually takes home loan application details
    from the user through terminal input.
    """

    print("\n--- ENTER HOME LOAN APPLICATION DETAILS ---")

    name = input("Enter applicant name: ")
    age = get_int_input("Enter age: ")
    income = get_int_input("Enter monthly income: ")
    employment_type = input("Enter employment type, for example salaried/self-employed: ")
    loan_amount = get_int_input("Enter requested loan amount: ")
    credit_score = get_int_input("Enter credit score: ")
    existing_emi = get_int_input("Enter existing EMI amount: ")

    documents = get_documents_from_user()

    application = {
        "name": name,
        "age": age,
        "income": income,
        "employment_type": employment_type,
        "loan_amount": loan_amount,
        "credit_score": credit_score,
        "existing_emi": existing_emi,

        # Documents entered manually
        "documents": documents,

        # These start empty and are filled by LangGraph
        "eligibility_status": "",
        "risk_status": "",
        "decision": "",
        "message": ""
    }

    return application


def print_result(result):
    """
    Prints final home loan result in a clean format.
    """

    print("\n--- HOME LOAN RESULT ---")
    print("Name:", result["name"])
    print("Age:", result["age"])
    print("Income:", result["income"])
    print("Employment Type:", result["employment_type"])
    print("Loan Amount:", result["loan_amount"])
    print("Credit Score:", result["credit_score"])
    print("Existing EMI:", result["existing_emi"])
    print("Documents:", result["documents"])
    print("Eligibility:", result["eligibility_status"])
    print("Risk:", result["risk_status"])
    print("Decision:", result["decision"])
    print("Message:", result["message"])


def main():
    """
    Main function to run multiple home loan applications.
    """

    # Build LangGraph workflow only once
    app = build_home_loan_graph()

    while True:
        # Take one application manually
        application = get_user_application()

        # Run application through LangGraph
        result = run_home_loan_application(app, application)

        # Print result
        print_result(result)

        # Ask if user wants to check another application
        again = input("\nDo you want to check another loan application? yes/no: ").lower()

        if again != "yes":
            print("\nThank you. Home loan checking finished.")
            break


if __name__ == "__main__":
    main()


