# File defines the shared memory of the workflow 

from typing import TypedDict,List 


# Class defines what data our home loan workflow will store

class HomeLoanState(TypedDict):
    name:str
    age:int
    income:float
    employment_type:str


    # Loan-related info
    loan_amount:int
    credit_score:int
    existing_emi:int


    documents:List[str]

    # Fields will be updated by different workflow steps

    eligibility_status:str
    risk_status:str
    decision:str
    message:str
    
