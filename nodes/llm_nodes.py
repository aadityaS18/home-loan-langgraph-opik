# nodes/llm_nodes.py

import opik
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from opik.integrations.langchain import OpikTracer

from state import HomeLoanState
from prompts.explanation_prompt import EXPLANATION_PROMPT
from prompts.officer_summary_prompt import OFFICER_SUMMARY_PROMPT


PROJECT_NAME = "home-loan-langgraph"

# Traces the LangChain + Ollama calls in local Opik.
opik_tracer = OpikTracer(project_name=PROJECT_NAME)

# Local free LLM running through Ollama.
# It explains results only; it does not make loan decisions.
llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    num_predict=400,
)


@opik.track(
    name="generate_customer_explanation",
    project_name=PROJECT_NAME,
)
def generate_customer_explanation(state: HomeLoanState):
    """
    Generates a customer-facing explanation.

    The deterministic rule engine already made the decision.
    Ollama only explains the supplied facts and recommendations.
    """

    prompt = ChatPromptTemplate.from_template(EXPLANATION_PROMPT)
    chain = prompt | llm

    response = chain.invoke(
        {
            # Decision details
            "name": state["name"],
            "decision": state["decision"],
            "risk_level": state["risk_level"],

            "decision_reasons": "\n".join(
                f"- {reason}" for reason in state["decision_reasons"]
            )
            if state["decision_reasons"]
            else "- None",

            "positive_factors": "\n".join(
                f"- {factor}" for factor in state["positive_factors"]
            )
            if state["positive_factors"]
            else "- None",

            "risk_flags": "\n".join(
                f"- {flag}" for flag in state["risk_flags"]
            )
            if state["risk_flags"]
            else "- None",

            "recommended_actions": "\n".join(
                f"- {action}" for action in state["recommended_actions"]
            )
            if state["recommended_actions"]
            else "- None",

            # Existing financial metrics
            "loan_amount": state["loan_amount"],
            "proposed_emi": state["proposed_emi"],
            "ltv_ratio": state["ltv_ratio"],
            "dti_ratio": state["dti_ratio"],
            "foir_ratio": state["foir_ratio"],

            # Phase 4 affordability estimation
            "max_affordable_new_emi": state["max_affordable_new_emi"],
            "max_eligible_loan": state["max_eligible_loan"],
            "loan_amount_gap": state["loan_amount_gap"],

            # Documents
            "missing_documents": ", ".join(state["missing_documents"])
            if state["missing_documents"]
            else "None",
        },
        config={"callbacks": [opik_tracer]},
    )

    state["customer_explanation"] = response.content
    return state


@opik.track(
    name="generate_officer_summary",
    project_name=PROJECT_NAME,
)
def generate_officer_summary(state: HomeLoanState):
    """
    Generates an internal summary for a loan officer.

    The LLM must format supplied underwriting facts only.
    It must not calculate or reinterpret the decision independently.
    """

    prompt = ChatPromptTemplate.from_template(OFFICER_SUMMARY_PROMPT)
    chain = prompt | llm

    response = chain.invoke(
        {
            # Applicant details
            "name": state["name"],
            "age": state["age"],
            "employment_type": state["employment_type"],
            "monthly_income": state["monthly_income"],
            "work_experience_years": state["work_experience_years"],
            "credit_score": state["credit_score"],
            "existing_emi": state["existing_emi"],

            # Loan details
            "loan_amount": state["loan_amount"],
            "interest_rate": state["interest_rate"],
            "tenure_years": state["tenure_years"],
            "loan_purpose": state["loan_purpose"],

            # Property details
            "property_value": state["property_value"],
            "property_type": state["property_type"],
            "property_location": state["property_location"],
            "property_age": state["property_age"],
            "construction_status": state["construction_status"],
            "legal_clearance_status": state["legal_clearance_status"],
            "valuation_status": state["valuation_status"],

            # Financial metrics
            "proposed_emi": state["proposed_emi"],
            "ltv_ratio": state["ltv_ratio"],
            "dti_ratio": state["dti_ratio"],
            "foir_ratio": state["foir_ratio"],

            # Phase 4 affordability estimation
            "max_affordable_new_emi": state["max_affordable_new_emi"],
            "max_eligible_loan": state["max_eligible_loan"],
            "loan_amount_gap": state["loan_amount_gap"],

            # Document status
            "document_status": state["document_status"],
            "missing_documents": ", ".join(state["missing_documents"])
            if state["missing_documents"]
            else "None",

            # Underwriting assessment
            "decision": state["decision"],
            "risk_level": state["risk_level"],

            "decision_reasons": "\n".join(
                f"- {reason}" for reason in state["decision_reasons"]
            )
            if state["decision_reasons"]
            else "- None",

            "positive_factors": "\n".join(
                f"- {factor}" for factor in state["positive_factors"]
            )
            if state["positive_factors"]
            else "- None",

            "risk_flags": "\n".join(
                f"- {flag}" for flag in state["risk_flags"]
            )
            if state["risk_flags"]
            else "- None",

            "recommended_actions": "\n".join(
                f"- {action}" for action in state["recommended_actions"]
            )
            if state["recommended_actions"]
            else "- None",
        },
        config={"callbacks": [opik_tracer]},
    )

    state["officer_summary"] = response.content
    return state


