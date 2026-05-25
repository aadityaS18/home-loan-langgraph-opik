import opik


@opik.track(name="underwriting_rule_engine")

def run_underwriting_rules(state:dict)->tuple[str,str,list[str]]:
    reasons=[]
    decision="pre_approved"
    risk_level="low"

    if state["age"]<21:
        return "rejected","high",["Application age is belowminimum requirement."]
    
    if state["monthly_income"]<30000:
        return "rejected","high" ,["Monthly income is below minimum requirement."]
    
    if state["credit_score"]<650:
        return "rejected","high",["Credit score is below acceptable threshold"]
    
    if state["dti_ratio"]>50:
        return "rejected","high",["Debt to income ratio is high"]
    
    if state["ltv_ratio"]>90:
        decision="manual_review"
        risk_level="high"

        reasons.append("Loan-to-value ratio is above 90%")

    if 45 <=state["dti_ratio"]<=55:
        decision="manual_review"
        risk_level="medium"
        reasons.append("Debt-to-income ratio requires manual review")


    if 650 <= state["credit_score"] < 700:
        decision = "manual_review"
        risk_level = "medium"
        reasons.append("Credit score is moderate and requires review.")

    if state["missing_documents"]:
        decision = "needs_documents"
        risk_level = "medium"
        reasons.append("Some required documents are missing.")

    if state["legal_clearance_status"].lower()!="clear":
        decision="manual_review"
        risk_level="high" 
        reasons.append("Property legal clearance is not fully cleared.")      

    if state["valuation_status"].lower() != "clear":
        decision = "manual_review"
        risk_level = "medium"
        reasons.append("Property valuation requires review.")

    if not reasons:
        reasons.append("Applicant meets the main home-loan eligibility criteria.")   


    return decision,risk_level,reasons


