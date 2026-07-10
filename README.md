# Home Loan Journey using LangGraph

This project implements a simple home-loan application journey using LangGraph.

## Features

- Takes applicant details manually from terminal
- Checks basic eligibility based on age and income
- Checks EMI affordability
- Checks required documents
- Performs credit score based risk assessment
- Gives final result: approved, rejected, or needs documents

## Tech Stack

- Python
- LangGraph

## Workflow

User Input  
→ Collect User Details  
→ Check Eligibility  
→ Check Affordability  
→ Check Documents  
→ Risk Assessment  
→ Make Decision  
→ Final Response

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt



## Opik Cloud Tracing

This project uses Opik Cloud to trace the LangGraph home-loan workflow.

The complete loan application run is tracked as a parent trace:

- `run_home_loan_application`

Each LangGraph workflow step is tracked as a child span:

- `collect_user_details`
- `check_eligibility`
- `check_affordability`
- `check_documents`
- `risk_assessment`
- `make_decision`
- `route_decision`
- `approved_response`
- `missing_docs_response`
- `rejected_response`

To configure Opik Cloud:

```bash
opik configure