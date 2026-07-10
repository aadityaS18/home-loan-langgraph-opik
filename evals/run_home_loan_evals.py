"""
Run Home Loan Agent Evaluations

Run all:
    export MODEL_PROVIDER=groq
    export GROQ_MODEL=llama-3.1-8b-instant
    export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/home_loan
    python evals/run_home_loan_evals.py

Run one:
    export EVAL_CASE_ID=general_documents_question
    python evals/run_home_loan_evals.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import opik
from opik import opik_context
import psycopg2
from psycopg2.extras import RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agent.tool_calling_loan_agent import run_agentic_loan_turn
from evals.home_loan_eval_cases import HOME_LOAN_EVAL_CASES
from evals.home_loan_metrics import evaluate_case_result, print_evaluation_result


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/home_loan",
)

OPIK_PROJECT_NAME = os.getenv("OPIK_PROJECT_NAME", "home-loan-langgraph")


def create_eval_application_id(case_id: str) -> str:
    unique_id = str(uuid.uuid4())[:8]
    return f"eval-{case_id}-{unique_id}"


def extract_final_response(result: dict[str, Any]) -> str:
    possible_keys = [
        "assistant_message",
        "response",
        "assistant_response",
        "agent_response",
        "final_response",
        "answer",
        "message",
        "output",
        "reply",
        "assistant_reply",
    ]

    for key in possible_keys:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    state = result.get("state")
    if isinstance(state, dict):
        for key in possible_keys:
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    messages = result.get("messages")
    if isinstance(messages, list) and messages:
        last_message = messages[-1]

        if isinstance(last_message, dict):
            value = (
                last_message.get("content")
                or last_message.get("text")
                or last_message.get("message")
            )
            if isinstance(value, str) and value.strip():
                return value.strip()

        if hasattr(last_message, "content"):
            value = getattr(last_message, "content")
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def get_db_snapshot(application_id: str) -> dict[str, Any]:
    snapshot = {
        "application_exists": False,
        "status": None,
        "assessment_exists": False,
        "tool_event_count": 0,
        "application_data": None,
        "assessment_result": None,
    }

    try:
        with psycopg2.connect(DATABASE_URL) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT application_id, status, application_data
                    FROM loan_applications
                    WHERE application_id = %s;
                    """,
                    (application_id,),
                )
                application_row = cursor.fetchone()

                if application_row:
                    snapshot["application_exists"] = True
                    snapshot["status"] = application_row.get("status")
                    snapshot["application_data"] = application_row.get("application_data")

                cursor.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM loan_tool_events
                    WHERE application_id = %s;
                    """,
                    (application_id,),
                )
                tool_event_row = cursor.fetchone()

                if tool_event_row:
                    snapshot["tool_event_count"] = int(tool_event_row["count"])

                cursor.execute(
                    """
                    SELECT assessment_result
                    FROM loan_assessments
                    WHERE application_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """,
                    (application_id,),
                )
                assessment_row = cursor.fetchone()

                if assessment_row:
                    snapshot["assessment_exists"] = True
                    snapshot["assessment_result"] = assessment_row.get("assessment_result")

    except Exception as error:
        print(f"[DB WARNING] Could not read DB snapshot for {application_id}: {error}")

    return snapshot


def extract_actual_tool_trace(final_state: dict[str, Any] | None) -> list[Any]:
    if not final_state:
        return []

    return final_state.get("tool_trace", [])


def safe_reason(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    return json.dumps(value, default=str)[:1000]


def log_opik_feedback_scores(evaluation_result: dict[str, Any]) -> None:
    """
    Add evaluation scores to the current Opik trace.

    These scores appear in the Opik "Feedback scores" tab.
    """
    final_response_eval = evaluation_result["final_response_eval"]
    trajectory_eval = evaluation_result["trajectory_eval"]
    db_eval = evaluation_result["db_eval"]
    overall_eval = evaluation_result["overall_eval"]

    feedback_scores = [
        {
            "name": "final_response_score",
            "value": float(final_response_eval["score"]),
            "reason": safe_reason(
                {
                    "passed": final_response_eval["passed"],
                    "missing_required_phrases": final_response_eval.get(
                        "missing_required_phrases",
                        [],
                    ),
                    "unsafe_phrases_found": final_response_eval.get(
                        "unsafe_phrases_found",
                        [],
                    ),
                }
            ),
        },
        {
            "name": "agent_trajectory_score",
            "value": float(trajectory_eval["score"]),
            "reason": safe_reason(
                {
                    "passed": trajectory_eval["passed"],
                    "expected_tools": trajectory_eval.get("expected_tools", []),
                    "actual_tools": trajectory_eval.get("actual_tools", []),
                    "reason": trajectory_eval.get("reason", ""),
                }
            ),
        },
        {
            "name": "db_persistence_score",
            "value": float(db_eval["score"]),
            "reason": safe_reason(
                {
                    "passed": db_eval["passed"],
                    "failures": db_eval.get("failures", []),
                    "status": db_eval.get("db_snapshot", {}).get("status"),
                    "assessment_exists": db_eval.get("db_snapshot", {}).get(
                        "assessment_exists"
                    ),
                    "tool_event_count": db_eval.get("db_snapshot", {}).get(
                        "tool_event_count"
                    ),
                }
            ),
        },
        {
            "name": "overall_regression_score",
            "value": float(overall_eval["score"]),
            "reason": safe_reason(
                {
                    "passed": overall_eval["passed"],
                    "component_scores": overall_eval.get("component_scores", {}),
                }
            ),
        },
    ]

    metadata = {
        "case_id": evaluation_result["case_id"],
        "application_id": evaluation_result.get("application_id"),
        "description": evaluation_result.get("description"),
        "final_response_passed": final_response_eval["passed"],
        "trajectory_passed": trajectory_eval["passed"],
        "db_passed": db_eval["passed"],
        "overall_passed": overall_eval["passed"],
    }

    try:
        opik_context.update_current_trace(
            feedback_scores=feedback_scores,
            metadata=metadata,
            tags=[
                "home-loan-eval",
                evaluation_result["case_id"],
                "passed" if overall_eval["passed"] else "failed",
            ],
        )

        print("[OPIK] Feedback scores logged to current trace.")

    except TypeError:
        # Some Opik versions may not support tags/metadata in this exact call.
        try:
            opik_context.update_current_trace(
                feedback_scores=feedback_scores,
            )
            opik_context.update_current_trace(
                metadata=metadata,
            )

            print("[OPIK] Feedback scores logged to current trace.")

        except Exception as error:
            print(f"[OPIK WARNING] Could not log feedback scores: {error}")

    except Exception as error:
        print(f"[OPIK WARNING] Could not log feedback scores: {error}")


@opik.track(
    name="home_loan_eval_case",
    project_name=OPIK_PROJECT_NAME,
    flush=True,
)
def run_single_eval_case(case: dict[str, Any]) -> dict[str, Any]:
    application_id = create_eval_application_id(case["case_id"])

    print("\n" + "#" * 100)
    print(f"Running case: {case['case_id']}")
    print(f"Application ID: {application_id}")
    print("#" * 100)

    final_response = ""
    final_state: dict[str, Any] | None = None

    for turn_number, message in enumerate(case["messages"], start=1):
        print(f"\nUser turn {turn_number}: {message}")

        try:
            result = run_agentic_loan_turn(
                thread_id=application_id,
                user_message=message,
            )

            print(f"Result keys: {list(result.keys())}")

            final_response = extract_final_response(result)
            final_state = result.get("state", {})

            if final_response:
                print(f"Agent response {turn_number}: {final_response[:700]}")
            else:
                print("Agent response could not be extracted.")
                print(str(result)[:1000])

        except Exception as error:
            print(f"[EVAL ERROR] Case {case['case_id']} failed on turn {turn_number}: {error}")

            final_response = f"EVAL_ERROR: {str(error)}"
            final_state = final_state or {}
            break

    actual_tool_trace = extract_actual_tool_trace(final_state)
    db_snapshot = get_db_snapshot(application_id)

    evaluation_result = evaluate_case_result(
        case=case,
        final_response=final_response,
        actual_tool_trace=actual_tool_trace,
        db_snapshot=db_snapshot,
    )

    evaluation_result["application_id"] = application_id
    evaluation_result["final_response"] = final_response
    evaluation_result["actual_tool_trace"] = actual_tool_trace
    evaluation_result["db_snapshot"] = db_snapshot

    log_opik_feedback_scores(evaluation_result)

    print_evaluation_result(evaluation_result)

    return evaluation_result


def print_final_summary(results: list[dict[str, Any]]) -> None:
    total_cases = len(results)
    passed_cases = sum(1 for result in results if result["overall_eval"]["passed"])
    failed_cases = total_cases - passed_cases

    average_score = (
        sum(float(result["overall_eval"]["score"]) for result in results) / total_cases
        if total_cases
        else 0.0
    )

    print("\n" + "=" * 100)
    print("HOME LOAN AGENT EVALUATION SUMMARY")
    print("=" * 100)
    print(f"Total cases: {total_cases}")
    print(f"Passed cases: {passed_cases}")
    print(f"Failed cases: {failed_cases}")
    print(f"Average regression score: {round(average_score, 3)}")
    print("-" * 100)

    for result in results:
        status = "PASS" if result["overall_eval"]["passed"] else "FAIL"
        print(
            f"{status} | "
            f"{result['case_id']} | "
            f"score={result['overall_eval']['score']} | "
            f"application_id={result['application_id']}"
        )

    print("=" * 100)

    if failed_cases > 0:
        print("\nFailed cases:")
        for result in results:
            if not result["overall_eval"]["passed"]:
                print(f"- {result['case_id']}")
                print(f"  Final response: {result['final_response_eval']}")
                print(f"  Trajectory: {result['trajectory_eval']}")
                print(f"  DB: {result['db_eval']}")


def save_results_to_json(results: list[dict[str, Any]]) -> None:
    os.makedirs("evals/results", exist_ok=True)

    output_path = "evals/results/latest_home_loan_eval_results.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, default=str)

    print(f"\nSaved eval results to: {output_path}")


def main() -> None:
    print("Starting Home Loan Agent Evaluations...")
    print(f"Using DATABASE_URL: {DATABASE_URL}")
    print(f"Using OPIK_PROJECT_NAME: {OPIK_PROJECT_NAME}")

    case_filter = os.getenv("EVAL_CASE_ID")

    cases_to_run = HOME_LOAN_EVAL_CASES

    if case_filter:
        cases_to_run = [
            case for case in HOME_LOAN_EVAL_CASES
            if case["case_id"] == case_filter
        ]

        if not cases_to_run:
            raise ValueError(f"No eval case found for EVAL_CASE_ID={case_filter}")

    results: list[dict[str, Any]] = []

    for case in cases_to_run:
        result = run_single_eval_case(case)
        results.append(result)

    print_final_summary(results)
    save_results_to_json(results)


if __name__ == "__main__":
    main()