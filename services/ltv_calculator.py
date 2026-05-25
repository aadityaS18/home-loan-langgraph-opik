import opik

@opik.track(name="calculate_ltv")
def calculate_ltv(loan_amount:float,property_value:float)->float:
    if property_value<=0:
        return 0.0
    
    return round((loan_amount/property_value)*100,2)