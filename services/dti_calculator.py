import opik

@opik.track(nam="calculate_dti")

def calculate_dti(existing_emi:float,proposed_emi:float,monthly_income:float)->float:
    if monthly_income<=0:
        return 100.0
    
    total_debt=existing_emi+proposed_emi

    return round((total_debt/monthly_income)*100,2)

