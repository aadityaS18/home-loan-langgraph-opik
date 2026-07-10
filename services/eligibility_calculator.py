import opik 

# Maximum Eligible Loan Calculation Service


@opik.track(name="calculate_max_eligible_loan")

def calculate_max_eligible_loan(

    monthly_income:float,
    existing_emi:float,
    annual_interest_rate:float,
    tenure_years:int,
    max_foir_percent:float=45.0,


)-> dict[str,float]:
    
    """
    Estimates the applicant's maximum eligible loan amount.

    Prototype assumption:
    Total EMI obligations should remain within 45% of monthly income.

    This is only a project/demo estimate and is not a bank sanction amount.
    """




    if monthly_income <= 0 or tenure_years<=0:
        return{
            "max_affordable_new_emi": 0,
            "max_eligible_loan":0,

        }
    

    max_total_emi=monthly_income*(max_foir_percent/100) # maximum total EMI allowed under the prototype Foir Assumptuon 

    max_affordable_new_emi=max_total_emi-existing_emi # remaining emi capacity after ecisting obligations

    if max_affordable_new_emi<=0:
        return {
            "max_affordable_new_emi":0,
            "max_eligible_loan":0,
        }
    
    monthly_rate=annual_interest_rate/(12*100)
    total_months=tenure_years*12

    # if we want a zero interest scenario

    if monthly_rate ==0:
        max_eligible_loan=max_affordable_new_emi*total_months
    else:
        # Principal = EMI * ((1+r)^n - 1) / (r * (1+r)^n)Estimates the applicant's maximum eligible loan amount.

      max_eligible_loan = (
            max_affordable_new_emi
            * (((1 + monthly_rate) ** total_months) - 1)
            / (monthly_rate * ((1 + monthly_rate) ** total_months))
        )

    return{
        "max_affordable_new_emi": round(max_affordable_new_emi),
        "max_eligible_loan": round(max_eligible_loan, 2)
    }

