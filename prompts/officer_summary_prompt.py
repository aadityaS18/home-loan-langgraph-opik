# prompts/officer_summary_prompt.py

OFFICER_SUMMARY_PROMPT = """
You are preparing an internal underwriting summary for a loan officer.

Use ONLY the facts provided below.
Do not calculate, infer, reinterpret, or change any values.
Do not recommend document collection as the only resolution when the decision is rejected due to income, DTI, credit, or other hard rejection reasons.

Applicant:
- Name: {name}
- Age: {age}
- Employment Type: {employment_type}
- Monthly Income: {monthly_income}
- Credit Score: {credit_score}
- Existing EMI: {existing_emi}

Loan:
- Requested Loan Amount: {loan_amount}
- Interest Rate: {interest_rate}
- Tenure: {tenure_years} years
- Purpose: {loan_purpose}

Property:
- Property Value: {property_value}
- Property Type: {property_type}
- Location: {property_location}
- Legal Clearance: {legal_clearance_status}
- Valuation Status: {valuation_status}

Financial Metrics:
- Proposed EMI: {proposed_emi}
- LTV Ratio: {ltv_ratio}%
- DTI Ratio: {dti_ratio}%
- FOIR Ratio: {foir_ratio}%
- Maximum Affordable New EMI: {max_affordable_new_emi}
- Estimated Maximum Eligible Loan: {max_eligible_loan}
- Requested Amount Above Estimate: {loan_amount_gap}

Assessment:
- Decision: {decision}
- Risk Level: {risk_level}

Decision Reasons:
{decision_reasons}

Positive Factors:
{positive_factors}

Risk Flags:
{risk_flags}

Missing Documents:
{missing_documents}

Recommended Actions:
{recommended_actions}

Rules:
- The decision and recommended actions are already determined by the rule engine.
- If the decision is rejected, state that the application cannot proceed under the current prototype assessment.
- Use the heading "Assessment Findings", not "hard rejection reasons".
- Do not describe missing documents or pending valuation as hard rejection reasons.
- Missing documents are pending items.
- Pending valuation or legal clearance are review items.
- Do not modify any numeric value.
- Keep the summary concise and factual.
- Treat the maximum eligible loan amount as a prototype estimate, not a final sanctioned amount.

Return exactly this structure:

Officer Summary:
...

Assessment Findings:
- ...

Positive Factors:
- ...

Pending Items:
- ...

Recommended Officer Action:
- Review the application in light of the assessment findings and positive factors.
- Address any pending items before making a final decision."""