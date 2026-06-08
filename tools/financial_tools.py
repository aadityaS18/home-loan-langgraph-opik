"""
Financial Tools  for home-loan agent.
"""

from langchain_core.tools import tool
from services.emi_calculator import calculate_emi
from services.ltv_calculator import calculate_ltv

from services.dti_calculator import calculate_dti
from services.eligibility_calculator import calculate_max_eligible_loan


@tool

def calculate_emi_tool(
    loan_amount:float,annual_interest_rate:float,
    tenure_years:int,

) ->dict:
    

    emi=calculate_emi(
        loan_amount=loan_amount,
        annual_interest_rate=annual_interest_rate,
        tenure_years=tenure_years,
    )

    return {

        "loan_amount": loan_amount,
        "annual_interest_rate":annual_interest_rate,
        "tenure_years":tenure_years,
        "proposed_emi":emi,
    }


@tool
def calculate_ltv_tool(
    existing_emi:float,
    proposed_emi:float,
    monthly_income:float,

)->dict:
    

    dtv_ratio=calculate_dti(
        existing_emi=existing_emi,
        proposed_emi=proposed_emi,
        monthly_income=monthly_income
    )

    return{

        "existing_emi":existing_emi,
        "proposed_emi":proposed_emi,
        "monthly_income":monthly_income,
        "dti_ratio":dtv_ratio,
        "foir_ratio":dtv_ratio,
    }


@tool

def estimate_max_eligible_loan_tool(

    monthly_income:float,
    existing_emi:float,
    annual_interest_rate:float,
    tenure_years:int,
    
)->dict:
    
    result=calculate_max_eligible_loan(

        monthly_income=monthly_income,
        existing_emi=existing_emi,
        annual_interest_rate=annual_interest_rate,
        tenure_years=tenure_years
    )

    return result