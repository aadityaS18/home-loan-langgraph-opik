#This file contains actual home-loan journey 

#Nodes are the individual steps of the loan journey. Each node is a Python function.

from state import HomeLoanState


# Node 1: Collect user details

def collect_user_details(state:HomeLoanState):
    """
    This is the first step.
    In. real app,details would come from a form or chatbot
    Here, we just confirm that the user details are received.
    """
    state["message"]=f"User details collected for {state["name"]}."

    return state



# Node 2:Check basic eligibility 


def check_eligibility(state:HomeLoanState):
    """
    This step check basic rules:
    -User should be at least 21 years old 
    - Monthly income should be at least 30,000
    """

    if state["age"]<21:
        state["eligibility_status"]="rejected"
        state["message"]="Applicant age is below 21"

    elif state["income"]<30000:
        state["eligibility_status"]="rejected"
        state["message"]="Monthly income is below the minimum requirement "

    else:
        state["eligibility_status"]="eligible"
        state["message"]="Basic eligibility check passed."

    return state 



# Node 3: Check EMI affordibilty 


def check_affordability(state: HomeLoanState):
    """
    Checks whether the applicant can afford another EMI.
    If the applicant is already rejected, do not overwrite the message.
    """

    # Stop here if already rejected in eligibility
    if state["eligibility_status"] == "rejected":
        return state

    max_allowed_emi = state["income"] * 0.40
    remaining_capacity = max_allowed_emi - state["existing_emi"]

    if remaining_capacity <= 0:
        state["eligibility_status"] = "rejected"
        state["message"] = "Existing EMI burden is too high."
    else:
        state["message"] = f"Applicant can afford extra EMI up to {remaining_capacity}."

    return state


# Node 4:Check doucments

def check_documents(state: HomeLoanState):
    """
    Checks whether all required home-loan documents are submitted.
    If the applicant is already rejected, do not overwrite the message.
    """

    # Stop here if already rejected
    if state["eligibility_status"] == "rejected":
        return state

    required_docs = [
        "id_proof",
        "income_proof",
        "bank_statement",
        "property_documents"
    ]

    missing_docs = []

    for doc in required_docs:
        if doc not in state["documents"]:
            missing_docs.append(doc)

    if missing_docs:
        state["decision"] = "needs_documents"
        state["message"] = "Missing documents: " + ", ".join(missing_docs)
    else:
        state["message"] = "All required documents are submitted."

    return state


# Node5 :Risk Assessment

def risk_assessment(state: HomeLoanState):
    """
    Checks risk level using credit score.
    If already rejected or documents are missing, do not overwrite the message.
    """

    # Stop here if already rejected or documents are missing
    if state["eligibility_status"] == "rejected" or state["decision"] == "needs_documents":
        return state

    if state["credit_score"] < 650:
        state["risk_status"] = "high"
        state["message"] = "Credit score is too low."

    elif state["credit_score"] < 720:
        state["risk_status"] = "medium"
        state["message"] = "Medium risk profile."

    else:
        state["risk_status"] = "low"
        state["message"] = "Low risk profile."

    return state


# node 6: Final decison 

def make_decision(state:HomeLoanState):

    """
    This step makes final decision.

    Possible decisons
    -approved
    - rejected
    - needs_documents
    """

    if state["eligibility_status"]=="rejected":
        state["decision"]="rejected"

    elif state["decision"]== "needs_documents":
        state["decision"]="needs_documents"

    elif state["risk_status"]=="high":
        state["decision"]="rejected"

    else:
        state["decision"]="approved"

    return state        



# Approved response 

def approved_response(state:HomeLoanState):
    """
    This response is shown if the application is approved.
    """

    state["message"] = (
        f"Congratulations {state['name']}, your home loan application "
        f"is approved for initial review. Requested amount: {state['loan_amount']}."
    )

    return state


# Missing documents response

def missing_docs_response(state:HomeLoanState):
    """
    This response is shown if some documents are missing"""

    state["message"]=(
        f"Hi {state['name']}, your application is currently on hold. "
        f"{state['message']}"

    )

    return state





def rejected_response(state: HomeLoanState):
    """
    This response is shown if the application is rejected.
    """

    state["message"] = (
        f"Sorry {state['name']}, your home loan application cannot proceed. "
        f"Reason: {state['message']}"
    )

    return state





def route_decision(state: HomeLoanState):
    """
    This function tells LangGraph which final node to go to.

    If decision is approved:
        go to approved_response

    If documents are missing:
        go to missing_docs_response

    Otherwise:
        go to rejected_response
    """

    if state["decision"] == "approved":
        return "approved_response"

    elif state["decision"] == "needs_documents":
        return "missing_docs_response"

    else:
        return "rejected_response"





  
    

    
