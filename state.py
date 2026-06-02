# File defines the shared memory of the workflow 

from typing import TypedDict,List 


# Class defines what data our home loan workflow will store

class HomeLoanState(TypedDict):
    name: str
    age: int
    employment_type: str
    monthly_income: float
    work_experience_years: float
    credit_score: int
    existing_emi: float

    # Loan requirement
    loan_amount: float
    interest_rate: float
    tenure_years: int
    loan_purpose: str

    # Property details
    property_value: float
    property_type: str
    property_location: str
    property_age: int
    construction_status: str
    legal_clearance_status: str
    valuation_status: str

    # Documents
    submitted_documents: List[str]
    required_documents: List[str]
    missing_documents: List[str]
    document_status: str

    # Calculated values
    proposed_emi: float
    ltv_ratio: float
    dti_ratio: float
    foir_ratio: float

    # Final decision
    risk_level: str
    underwriting_status: str
    decision: str
    decision_reasons: List[str]
    customer_explanation: str
    officer_summary: str

        # Decision fields
    risk_level: str
    underwriting_status: str
    decision: str
    decision_reasons: List[str]

    # Detailed decision analysis
    risk_flags: List[str]
    positive_factors: List[str]
    recommended_actions: List[str]

    # LLM-generated outputs
    customer_explanation: str
    officer_summary: str

    max_affordable_new_emi:float #Estimated EMI capacity remaining after existing EMI
    max_eligible_loan:float #Maximum eligible loan amount based on financial metrics
    loan_amount_gap:float

    