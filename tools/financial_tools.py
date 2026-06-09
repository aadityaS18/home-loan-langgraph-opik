"""
Financial tools for the home-loan agent.

These tools wrap deterministic calculation services so the agent can call
them instead of calculating financial values by itself.
"""

from langchain_core.tools import tool

from services.emi_calculator import calculate_emi
from services.ltv_calculator import calculate_ltv
from services.dti_calculator import calculate_dti
from services.eligibility_calculator import calculate_max_eligible_loan


@tool
def calculate_emi_tool(
    loan_amount: float,
    annual_interest_rate: float,
    tenure_years: int,
) -> dict:
    """Calculate the estimated monthly EMI for a requested home loan."""
    emi = calculate_emi(
        loan_amount=loan_amount,
        annual_interest_rate=annual_interest_rate,
        tenure_years=tenure_years,
    )

    return {
        "loan_amount": loan_amount,
        "annual_interest_rate": annual_interest_rate,
        "tenure_years": tenure_years,
        "proposed_emi": emi,
    }


@tool
def calculate_ltv_tool(
    loan_amount: float,
    property_value: float,
) -> dict:
    """Calculate the loan-to-value ratio for a requested loan and property value."""
    ltv_ratio = calculate_ltv(
        loan_amount=loan_amount,
        property_value=property_value,
    )

    return {
        "loan_amount": loan_amount,
        "property_value": property_value,
        "ltv_ratio": ltv_ratio,
    }


@tool
def calculate_dti_tool(
    existing_emi: float,
    proposed_emi: float,
    monthly_income: float,
) -> dict:
    """Calculate DTI and FOIR using existing EMI, proposed EMI and monthly income."""
    dti_ratio = calculate_dti(
        existing_emi=existing_emi,
        proposed_emi=proposed_emi,
        monthly_income=monthly_income,
    )

    return {
        "existing_emi": existing_emi,
        "proposed_emi": proposed_emi,
        "monthly_income": monthly_income,
        "dti_ratio": dti_ratio,
        "foir_ratio": dti_ratio,
    }


@tool
def estimate_max_eligible_loan_tool(
    monthly_income: float,
    existing_emi: float,
    annual_interest_rate: float,
    tenure_years: int,
) -> dict:
    """Estimate maximum affordable EMI and maximum eligible loan amount."""
    result = calculate_max_eligible_loan(
        monthly_income=monthly_income,
        existing_emi=existing_emi,
        annual_interest_rate=annual_interest_rate,
        tenure_years=tenure_years,
    )

    return result