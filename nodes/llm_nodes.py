
import opik
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from opik.integrations.langchain import OpikTracer

from state import HomeLoanState
from prompts.explanation_prompt import EXPLANATION_PROMPT

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