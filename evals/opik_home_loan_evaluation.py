

import os
from typing import Any

import opik
from dotenv import load_dotenv
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import base_metric, score_result

try:
    from services.tracing_service import run_traced_home_loan_assessment as run_assessment
except ImportError:
    from agent.controlled_assessment import run_controlled_home_loan_assessment as run_assessment


load_dotenv()

PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-origination")
DATASET_NAME = "home-loan-evaluation-scenarios"


def get_item_value(item: Any, key: str) -> Any:
    """Handle both Opik DatasetItem objects and plain dictionaries."""
    if hasattr(item, "input"):
        return item.input[key]
    return item[key]


class DecisionMatchMetric(base_metric.BaseMetric):
    def __init__(self):
        super().__init__(name="decision_match")

    def score(
        self,
        output: dict[str, Any],
        expected_decision: str,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        actual = output.get("decision")
        passed = actual == expected_decision

        return score_result.ScoreResult(
            name=self.name,
            value=1.0 if passed else 0.0,
            reason=f"Expected decision={expected_decision}, actual decision={actual}",
        )


class RiskLevelMatchMetric(base_metric.BaseMetric):
    def __init__(self):
        super().__init__(name="risk_level_match")

    def score(
        self,
        output: dict[str, Any],
        expected_risk_level: str,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        actual = output.get("risk_level")
        passed = actual == expected_risk_level

        return score_result.ScoreResult(
            name=self.name,
            value=1.0 if passed else 0.0,
            reason=f"Expected risk={expected_risk_level}, actual risk={actual}",
        )


class DocumentStatusMatchMetric(base_metric.BaseMetric):
    def __init__(self):
        super().__init__(name="document_status_match")

    def score(
        self,
        output: dict[str, Any],
        expected_document_status: str,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        actual = output.get("document_status")
        passed = actual == expected_document_status

        return score_result.ScoreResult(
            name=self.name,
            value=1.0 if passed else 0.0,
            reason=f"Expected document_status={expected_document_status}, actual={actual}",
        )


EVALUATION_CASES = [
    {
        "scenario": "eligible_salaried_applicant",
        "application": {
            "name": "Eligible Applicant",
            "age": 35,
            "employment_type": "salaried",
            "monthly_income": 150000.0,
            "work_experience_years": 8.0,
            "credit_score": 780,
            "existing_emi": 5000.0,
            "loan_amount": 3000000.0,
            "interest_rate": 8.5,
            "tenure_years": 20,
            "loan_purpose": "purchase",
            "property_value": 6000000.0,
            "property_type": "apartment",
            "property_location": "Bangalore",
            "property_age": 4,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
            "pan_available": True,
            "id_proof_available": True,
            "address_proof_available": True,
            "submitted_documents": [
                "id_proof",
                "address_proof",
                "pan_card",
                "bank_statement",
                "property_title_deed",
                "sale_agreement",
                "salary_slips",
                "form_16",
                "employment_proof",
                "builder_noc",
                "approved_building_plan",
            ],
        },
        "expected_decision": "pre_approved",
        "expected_risk_level": "low",
        "expected_document_status": "complete",
    },
    {
        "scenario": "low_credit_score_applicant",
        "application": {
            "name": "Low Credit Applicant",
            "age": 31,
            "employment_type": "salaried",
            "monthly_income": 120000.0,
            "work_experience_years": 5.0,
            "credit_score": 590,
            "existing_emi": 8000.0,
            "loan_amount": 2500000.0,
            "interest_rate": 9.0,
            "tenure_years": 20,
            "loan_purpose": "purchase",
            "property_value": 5000000.0,
            "property_type": "apartment",
            "property_location": "Delhi",
            "property_age": 3,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
            "pan_available": True,
            "id_proof_available": True,
            "address_proof_available": True,
            "submitted_documents": [
                "id_proof",
                "address_proof",
                "pan_card",
                "bank_statement",
                "property_title_deed",
                "sale_agreement",
                "salary_slips",
                "form_16",
                "employment_proof",
            ],
        },
        "expected_decision": "rejected",
        "expected_risk_level": "high",
        "expected_document_status": "complete",
    },
    {
        "scenario": "missing_documents_applicant",
        "application": {
            "name": "Missing Docs Applicant",
            "age": 40,
            "employment_type": "self_employed",
            "monthly_income": 180000.0,
            "work_experience_years": 10.0,
            "credit_score": 750,
            "existing_emi": 10000.0,
            "loan_amount": 3500000.0,
            "interest_rate": 8.8,
            "tenure_years": 20,
            "loan_purpose": "purchase",
            "property_value": 7000000.0,
            "property_type": "apartment",
            "property_location": "Mumbai",
            "property_age": 2,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
            "pan_available": True,
            "id_proof_available": True,
            "address_proof_available": True,
            "submitted_documents": [
                "id_proof",
                "address_proof",
                "pan_card",
                "bank_statement",
            ],
        },
        "expected_decision": "manual_review",
        "expected_risk_level": "medium",
        "expected_document_status": "missing_documents",
    },
    {
        "scenario": "high_affordability_risk_applicant",
        "application": {
            "name": "High DTI Applicant",
            "age": 37,
            "employment_type": "salaried",
            "monthly_income": 70000.0,
            "work_experience_years": 6.0,
            "credit_score": 720,
            "existing_emi": 30000.0,
            "loan_amount": 4500000.0,
            "interest_rate": 9.2,
            "tenure_years": 15,
            "loan_purpose": "purchase",
            "property_value": 6000000.0,
            "property_type": "apartment",
            "property_location": "Noida",
            "property_age": 5,
            "construction_status": "ready_to_move",
            "legal_clearance_status": "clear",
            "valuation_status": "clear",
            "pan_available": True,
            "id_proof_available": True,
            "address_proof_available": True,
            "submitted_documents": [
                "id_proof",
                "address_proof",
                "pan_card",
                "bank_statement",
                "property_title_deed",
                "sale_agreement",
                "salary_slips",
                "form_16",
                "employment_proof",
            ],
        },
        "expected_decision": "rejected",
        "expected_risk_level": "high",
        "expected_document_status": "complete",
    },
]


def build_dataset():
    client = Opik()

    try:
        dataset = client.get_or_create_dataset(
            name=DATASET_NAME,
            description="Home loan business-rule evaluation scenarios",
            project_name=PROJECT_NAME,
        )
    except TypeError:
        dataset = client.get_or_create_dataset(
            DATASET_NAME,
            "Home loan business-rule evaluation scenarios",
            PROJECT_NAME,
        )

    dataset.insert(EVALUATION_CASES)
    return dataset


@opik.track(name="home_loan_evaluation_task", project_name=PROJECT_NAME)
def evaluation_task(item: Any) -> dict[str, Any]:
    application = get_item_value(item, "application")
    result = run_assessment(application)

    assessment = result.get("assessment", result)
    documents = result.get("documents", result)

    output = {
        "decision": assessment.get("decision"),
        "risk_level": assessment.get("risk_level"),
        "document_status": documents.get("document_status")
        or assessment.get("document_status"),
    }

    return {"output": output}


def main():
    opik.configure(use_local=os.getenv("OPIK_USE_LOCAL", "true").lower() == "true")

    dataset = build_dataset()
    
result = evaluate(
    dataset=dataset,
    task=evaluation_task,
    scoring_metrics=[
        DecisionMatchMetric(),
        RiskLevelMatchMetric(),
        DocumentStatusMatchMetric(),
    ],
    experiment_name="home-loan-rule-evaluation",
    project_name=PROJECT_NAME,
)

print("Opik evaluation complete.")
print(result)

if __name__ == "__main__":
    main()