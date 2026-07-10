import opik 
@opik.track(name="calculate_emi")



def calculate_emi(loan_amount:float,annual_interest_rate:float,tenure_years:int)->float:
    monthly_rate=annual_interest_rate/(12 *100)
    total_months=tenure_years*12

    if monthly_rate==0:
        return loan_amount/total_months
    

    emi=loan_amount*monthly_rate*((1+monthly_rate)**total_months)/(((1+monthly_rate)**total_months)-1)
    return round(emi,2)