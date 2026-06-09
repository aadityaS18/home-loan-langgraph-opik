"""HOME LOAN AGENT SETUP USING LANGCHAIN create_agent
File creates agent and registers all available tools
PostgreSQL checkpointing will be added in the next phase"""


from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from agent.system_prompt import HOME_LOAN_AGENT_SYSTEM_PROMPT

from tools.financial_tools import (

    calculate_emi_tool,
    calculate_ltv_tool,
    calculate_dti_tool,
    
   
    estimate_max_eligible_loan_tool,
)

from tools.verification_tools import(

    verify_kyc_tool,
    verify_cibil_tool,
)

from tools.document_tools import(

    get_required_documents_tool,
    find_missing_documents_tool,
)

from tools.underwriting_tools import run_initial_assessment_tool

def build_home_loan_agent():
    """Build home-loan agent using local Ollama model and tools"""

    model=ChatOllama(model="llama3.2:3b",
                     temperature=0,
                     num_predict=250,)
    
    tools=[

        calculate_emi_tool,
        calculate_ltv_tool,
        calculate_dti_tool,
        estimate_max_eligible_loan_tool,
        get_required_documents_tool,
        find_missing_documents_tool,
        verify_kyc_tool,
        verify_cibil_tool,
        run_initial_assessment_tool,
    ]




    agent=create_agent(

        model=model,
        tools=tools,
        system_prompt=HOME_LOAN_AGENT_SYSTEM_PROMPT,
    )


    return agent

