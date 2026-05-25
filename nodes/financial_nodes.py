import opik 
from state import HomeLoanState
from services.emi_calculator import calculate_emi
from services.ltv_calculator import calculate_ltv
from services.dti_calculator import calculate_dti



@opik.track(name="calculate_financials_metrics")
def calculate_financial_metrics(state:HomeLoanState):

    proposed_emi=calculate_emi(

        loan_amount=state["loan_amount"],
        annual_interest_rate=state["interest_rate"],

        tenure_years=state["tenure_years"],

    )


    ltv_ratio=calculate_ltv(

        loan_amount=state["loan_amount"],
        property_value=state["property_value"]
        
    )


    
    dti_ratio = calculate_dti(
        existing_emi=state["existing_emi"],
        proposed_emi=proposed_emi,
        monthly_income=state["monthly_income"],
    )

    state["proposed_emi"] = proposed_emi
    state["ltv_ratio"] = ltv_ratio
    state["dti_ratio"] = dti_ratio
    state["foir_ratio"] = dti_ratio

    return state





