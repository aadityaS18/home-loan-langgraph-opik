"""Home Loan Agent eval metrics 
Focus areas: 
1. Final response eval
2. Agent trajectory eval
3. Db=Backend persistence eval
4. Regression eval"""



from __future__ import annotations

from typing import Any 

def normalize_text(value: str| None)->str:
    """Normalize text for simple phrase matching """
    if not value:
        return ""
    return value.lower().strip()



def final_response_score(
    final_response: str,
    must_include: list[str] | None = None,
    must_not_include: list[str] | None = None,
) -> dict[str, Any]:
    """
    Score the final response.

    Checks:
    - Required phrases are present.
    - Unsafe phrases are absent.

    Returns score between 0 and 1.
    """
    must_include = must_include or []
    must_not_include = must_not_include or []

    response = normalize_text(final_response)

    missing_required_phrases = []
    for phrase in must_include:
        if normalize_text(phrase) not in response:
            missing_required_phrases.append(phrase)

    unsafe_phrases_found = []
    for phrase in must_not_include:
        if normalize_text(phrase) in response:
            unsafe_phrases_found.append(phrase)

    include_score = 1.0 if not missing_required_phrases else 0.0
    safety_score = 1.0 if not unsafe_phrases_found else 0.0

    score = (include_score + safety_score) / 2

    passed = score == 1.0

    return {
        "metric_name": "final_response",
        "score": score,
        "passed": passed,
        "missing_required_phrases": missing_required_phrases,
        "unsafe_phrases_found": unsafe_phrases_found,
    }


def extract_tool_names_from_trace(tool_trace: list[Any] | None) -> list[str]:
    """
    Extract tool names from state['tool_trace'].

    Supports common formats:
    - [{"tool_name": "..."}]
    - [{"name": "..."}]
    - [{"tool": "..."}]
    - ["tool_name"]
    """
    if not tool_trace:
        return []

    tool_names: list[str] = []

    for item in tool_trace:
        if isinstance(item, str):
            tool_names.append(item)
            continue

        if isinstance(item, dict):
            tool_name = (
                item.get("tool_name")
                or item.get("name")
                or item.get("tool")
                or item.get("action")
            )

            if tool_name:
                tool_names.append(str(tool_name))

    return tool_names


def trajectory_score(
    expected_tools: list[str],
    actual_tool_trace: list[Any] | None,
) -> dict[str, Any]:
    """
    Score agent trajectory.

    Checks whether the expected tool sequence matches the actual tool sequence.

    Scoring:
    - 1.0 = exact sequence match
    - 0.7 = same tools but order differs
    - 0.4 = expected tools are subset of actual tools but extra tools exist
    - 0.0 = missing important tools or wrong trajectory
    """
    actual_tools = extract_tool_names_from_trace(actual_tool_trace)

    if expected_tools == actual_tools:
        return {
            "metric_name": "agent_trajectory",
            "score": 1.0,
            "passed": True,
            "expected_tools": expected_tools,
            "actual_tools": actual_tools,
            "missing_tools": [],
            "extra_tools": [],
            "reason": "Exact tool sequence matched.",
        }

    expected_set = set(expected_tools)
    actual_set = set(actual_tools)

    missing_tools = list(expected_set - actual_set)
    extra_tools = list(actual_set - expected_set)

    if expected_set == actual_set:
        score = 0.7
        reason = "Correct tools were called, but order was different."
    elif expected_set.issubset(actual_set):
        score = 0.4
        reason = "Expected tools were called, but extra tools were also called."
    else:
        score = 0.0
        reason = "Missing required tools or wrong trajectory."

    return {
        "metric_name": "agent_trajectory",
        "score": score,
        "passed": score >= 0.7,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "missing_tools": missing_tools,
        "extra_tools": extra_tools,
        "reason": reason,
    }


def db_persistence_score(
    expected_application_should_exist: bool,
    expected_db_status: str | None,
    expected_assessment_saved: bool,
    db_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Score DB persistence.

    db_snapshot will later come from PostgreSQL and should look like:

    {
        "application_exists": True,
        "status": "assessed",
        "assessment_exists": True,
        "tool_event_count": 5
    }
    """
    if db_snapshot is None:
        db_snapshot = {
            "application_exists": False,
            "status": None,
            "assessment_exists": False,
            "tool_event_count": 0,
        }

    application_exists = bool(db_snapshot.get("application_exists"))
    actual_status = db_snapshot.get("status")
    assessment_exists = bool(db_snapshot.get("assessment_exists"))

    failures = []

    if expected_application_should_exist != application_exists:
        failures.append(
            f"application_exists expected {expected_application_should_exist}, got {application_exists}"
        )

    if expected_db_status is not None and actual_status != expected_db_status:
        failures.append(
            f"status expected {expected_db_status}, got {actual_status}"
        )

    if expected_assessment_saved != assessment_exists:
        failures.append(
            f"assessment_exists expected {expected_assessment_saved}, got {assessment_exists}"
        )

    passed = len(failures) == 0
    score = 1.0 if passed else 0.0

    return {
        "metric_name": "db_persistence",
        "score": score,
        "passed": passed,
        "failures": failures,
        "db_snapshot": db_snapshot,
    }


def overall_regression_score(
    final_response_eval: dict[str, Any],
    trajectory_eval: dict[str, Any],
    db_eval: dict[str, Any],
) -> dict[str, Any]:
    """
    Combine all scores into one regression score.

    Weights:
    - Agent trajectory: 40%
    - DB persistence: 35%
    - Final response: 25%
    """
    final_score = float(final_response_eval["score"])
    trajectory = float(trajectory_eval["score"])
    db_score = float(db_eval["score"])

    weighted_score = (
        (trajectory * 0.40)
        + (db_score * 0.35)
        + (final_score * 0.25)
    )

    passed = (
        final_response_eval["passed"]
        and trajectory_eval["passed"]
        and db_eval["passed"]
    )

    return {
        "metric_name": "overall_regression",
        "score": round(weighted_score, 3),
        "passed": passed,
        "component_scores": {
            "final_response": final_score,
            "agent_trajectory": trajectory,
            "db_persistence": db_score,
        },
    }


def evaluate_case_result(
    case: dict[str, Any],
    final_response: str,
    actual_tool_trace: list[Any] | None,
    db_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Evaluate one complete test case result.

    This is the main helper used by the evaluation runner.
    """
    final_response_eval = final_response_score(
        final_response=final_response,
        must_include=case.get("must_include", []),
        must_not_include=case.get("must_not_include", []),
    )

    trajectory_eval = trajectory_score(
        expected_tools=case.get("expected_tools", []),
        actual_tool_trace=actual_tool_trace,
    )

    db_eval = db_persistence_score(
        expected_application_should_exist=case.get("expected_application_should_exist", False),
        expected_db_status=case.get("expected_db_status"),
        expected_assessment_saved=case.get("expected_assessment_saved", False),
        db_snapshot=db_snapshot,
    )

    overall_eval = overall_regression_score(
        final_response_eval=final_response_eval,
        trajectory_eval=trajectory_eval,
        db_eval=db_eval,
    )

    return {
        "case_id": case["case_id"],
        "description": case["description"],
        "final_response_eval": final_response_eval,
        "trajectory_eval": trajectory_eval,
        "db_eval": db_eval,
        "overall_eval": overall_eval,
    }


def print_evaluation_result(result: dict[str, Any]) -> None:
    """
    Pretty print one evaluation result.
    """
    print("=" * 100)
    print(f"Case: {result['case_id']}")
    print(f"Description: {result['description']}")
    print("-" * 100)

    print(
        f"Final response: "
        f"{result['final_response_eval']['score']} | "
        f"Passed: {result['final_response_eval']['passed']}"
    )

    print(
        f"Trajectory: "
        f"{result['trajectory_eval']['score']} | "
        f"Passed: {result['trajectory_eval']['passed']}"
    )

    print(
        f"DB persistence: "
        f"{result['db_eval']['score']} | "
        f"Passed: {result['db_eval']['passed']}"
    )

    print(
        f"Overall regression: "
        f"{result['overall_eval']['score']} | "
        f"Passed: {result['overall_eval']['passed']}"
    )

    if result["trajectory_eval"].get("reason"):
        print(f"Trajectory reason: {result['trajectory_eval']['reason']}")

    if result["db_eval"].get("failures"):
        print(f"DB failures: {result['db_eval']['failures']}")

    if result["final_response_eval"].get("missing_required_phrases"):
        print(
            "Missing required phrases: "
            f"{result['final_response_eval']['missing_required_phrases']}"
        )

    if result["final_response_eval"].get("unsafe_phrases_found"):
        print(
            "Unsafe phrases found: "
            f"{result['final_response_eval']['unsafe_phrases_found']}"
        )