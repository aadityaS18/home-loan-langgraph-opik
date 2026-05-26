
import opik
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from opik.integrations.langchain import OpikTracer

from state import HomeLoanState
from prompts.explanation_prompt import EXPLANATION_PROMPT
from prompts.officer_summary_prompt import OFFICER_SUMMARY_PROMPT

opik_tracer=OpikTracer(project_name="home-loan-langgraph")

llm=ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    num_predict=250

)

@opik.track(name="generate_customer_explanation")

def generate_customer_explanation(state:HomeLoanState):
    """
    LangGraph +Langchain node using local Ollama model
    
    The rule engine makes the loan decision.
    The LLM only explains the decision"""

    prompt = ChatPromptTemplate.from_template(EXPLANATION_PROMPT)
    chain = prompt | llm

    response=chain.invoke(

        {
            "name": state["name"],
            "decision": state["decision"],
            "risk_level": state["risk_level"],
            "decision_reasons": ", ".join(state["decision_reasons"]),
            "proposed_emi": state["proposed_emi"],
            "ltv_ratio": state["ltv_ratio"],
            "dti_ratio": state["dti_ratio"],
            "foir_ratio": state["foir_ratio"],
            "missing_documents": ", ".join(state["missing_documents"])
            if state["missing_documents"]
            else "None",


        },
        config={"callbacks":[opik_tracer]}
    )

    state["customer_explanation"]=response.content

    return state





@opik.track(name="generate_officer_summary")

def generate_officer_summary(state:HomeLoanState):
    """Generates an internal loan officer summary using Ollama"""
    
    prompt=ChatPromptTemplate.from_template(OFFICER_SUMMARY_PROMPT)
    chain=prompt | llm

    response=chain.invoke(
        {

            "name": state["name"],
            "age": state["age"],
            "employment_type": state["employment_type"],
            "monthly_income": state["monthly_income"],
            "work_experience_years": state["work_experience_years"],
            "credit_score": state["credit_score"],
            "existing_emi": state["existing_emi"],
            "loan_amount": state["loan_amount"],
            "interest_rate": state["interest_rate"],
            "tenure_years": state["tenure_years"],
            "loan_purpose": state["loan_purpose"],
            "property_value": state["property_value"],
            "property_type": state["property_type"],
            "property_location": state["property_location"],
            "property_age": state["property_age"],
            "construction_status": state["construction_status"],
            "legal_clearance_status": state["legal_clearance_status"],
            "valuation_status": state["valuation_status"],
            "proposed_emi": state["proposed_emi"],
            "ltv_ratio": state["ltv_ratio"],
            "dti_ratio": state["dti_ratio"],
            "foir_ratio": state["foir_ratio"],
            "document_status": state["document_status"],
            "missing_documents": ", ".join(state["missing_documents"]) if state["missing_documents"] else "None",
            "decision": state["decision"],
            "risk_level": state["risk_level"],
            "decision_reasons": ", ".join(state["decision_reasons"]),
        },
        config={"callbacks":[opik_tracer]},
    )

    state["officer_summary"]=response.content

    return state