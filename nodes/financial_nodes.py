# nodes/financial_nodes.py

import opik

from state import HomeLoanState
from services.emi_calculator import calculate_emi
from services.ltv_calculator import calculate_ltv
from services.dti_calculator import calculate_dti
from services.eligibility_calculator import calculate_max_eligible_loan


@opik.track(name="calculate_financial_metrics")
def calculate_financial_metrics(state: HomeLoanState):
    """
    Calculates all financial metrics required by the underwriting engine:
    - proposed EMI
    - LTV ratio
    - DTI / FOIR ratio
    - estimated maximum eligible loan
    - requested loan amount gap
    """

    proposed_emi = calculate_emi(
        loan_amount=state["loan_amount"],
        annual_interest_rate=state["interest_rate"],
        tenure_years=state["tenure_years"],
    )

    ltv_ratio = calculate_ltv(
        loan_amount=state["loan_amount"],
        property_value=state["property_value"],
    )

    dti_ratio = calculate_dti(
        existing_emi=state["existing_emi"],
        proposed_emi=proposed_emi,
        monthly_income=state["monthly_income"],
    )

    eligibility_estimate = calculate_max_eligible_loan(
        monthly_income=state["monthly_income"],
        existing_emi=state["existing_emi"],
        annual_interest_rate=state["interest_rate"],
        tenure_years=state["tenure_years"],
    )

    max_affordable_new_emi = eligibility_estimate["max_affordable_new_emi"]
    max_eligible_loan = eligibility_estimate["max_eligible_loan"]

    loan_amount_gap = max(
        round(state["loan_amount"] - max_eligible_loan, 2),
        0.0,
    )

    # Return new state values to LangGraph.
    return {
        "proposed_emi": proposed_emi,
        "ltv_ratio": ltv_ratio,
        "dti_ratio": dti_ratio,
        "foir_ratio": dti_ratio,
        "max_affordable_new_emi": max_affordable_new_emi,
        "max_eligible_loan": max_eligible_loan,
        "loan_amount_gap": loan_amount_gap,
    }





