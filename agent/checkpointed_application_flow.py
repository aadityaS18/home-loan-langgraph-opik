"""
Checkpointed home loan application journey.

Purpose:
- Save in-progress application state using LangGraph PostgreSQL checkpointing.
- Allow an applicant journey to be resumed using a thread_id.
- This is separate from final submitted application records stored in:
  applications, assessment_results and status_history.

Use case:
- Applicant starts application.
- Applicant fills details step by step.
- Each step is checkpointed in PostgreSQL.
- Applicant can resume later using the same thread_id.
"""

import os
from typing import Any, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/home_loan",
)


class CheckpointedLoanState(TypedDict, total=False):
    """State for an in-progress home loan application."""

    thread_id: str
    applicant_details: dict[str, Any]
    loan_details: dict[str, Any]
    property_details: dict[str, Any]
    document_details: dict[str, Any]
    current_step: str
    completed_steps: list[str]
    messages: list[str]


def _append_message(state: CheckpointedLoanState, message: str) -> list[str]:
    """Append a message to state without mutating original list."""

    messages = state.get("messages", []).copy()
    messages.append(message)
    return messages


def _append_completed_step(
    state: CheckpointedLoanState,
    step_name: str,
) -> list[str]:
    """Append completed step once."""

    completed_steps = state.get("completed_steps", []).copy()

    if step_name not in completed_steps:
        completed_steps.append(step_name)

    return completed_steps


def applicant_details_node(
    state: CheckpointedLoanState,
) -> CheckpointedLoanState:
    """Validate and save applicant details step."""

    if not state.get("applicant_details"):
        return {
            **state,
            "current_step": "applicant_details",
            "messages": _append_message(
                state,
                "Applicant details are pending.",
            ),
        }

    return {
        **state,
        "current_step": "loan_details",
        "completed_steps": _append_completed_step(state, "applicant_details"),
        "messages": _append_message(
            state,
            "Applicant details saved.",
        ),
    }


def loan_details_node(state: CheckpointedLoanState) -> CheckpointedLoanState:
    """Validate and save loan details step."""

    if not state.get("loan_details"):
        return {
            **state,
            "current_step": "loan_details",
            "messages": _append_message(
                state,
                "Loan details are pending.",
            ),
        }

    return {
        **state,
        "current_step": "property_details",
        "completed_steps": _append_completed_step(state, "loan_details"),
        "messages": _append_message(
            state,
            "Loan details saved.",
        ),
    }


def property_details_node(state: CheckpointedLoanState) -> CheckpointedLoanState:
    """Validate and save property details step."""

    if not state.get("property_details"):
        return {
            **state,
            "current_step": "property_details",
            "messages": _append_message(
                state,
                "Property details are pending.",
            ),
        }

    return {
        **state,
        "current_step": "document_details",
        "completed_steps": _append_completed_step(state, "property_details"),
        "messages": _append_message(
            state,
            "Property details saved.",
        ),
    }


def document_details_node(state: CheckpointedLoanState) -> CheckpointedLoanState:
    """Validate and save document details step."""

    if not state.get("document_details"):
        return {
            **state,
            "current_step": "document_details",
            "messages": _append_message(
                state,
                "Document details are pending.",
            ),
        }

    return {
        **state,
        "current_step": "ready_for_submission",
        "completed_steps": _append_completed_step(state, "document_details"),
        "messages": _append_message(
            state,
            "Document details saved. Application is ready for submission.",
        ),
    }


def route_after_applicant_details(state: CheckpointedLoanState) -> str:
    """Route after applicant details step."""

    if not state.get("applicant_details"):
        return END

    return "loan_details"


def route_after_loan_details(state: CheckpointedLoanState) -> str:
    """Route after loan details step."""

    if not state.get("loan_details"):
        return END

    return "property_details"


def route_after_property_details(state: CheckpointedLoanState) -> str:
    """Route after property details step."""

    if not state.get("property_details"):
        return END

    return "document_details"


def route_after_document_details(state: CheckpointedLoanState) -> str:
    """Route after document details step."""

    return END


def build_checkpointed_application_workflow():
    """Build the LangGraph workflow for checkpointed application progress."""

    workflow = StateGraph(CheckpointedLoanState)

    workflow.add_node("applicant_details", applicant_details_node)
    workflow.add_node("loan_details", loan_details_node)
    workflow.add_node("property_details", property_details_node)
    workflow.add_node("document_details", document_details_node)

    workflow.set_entry_point("applicant_details")

    workflow.add_conditional_edges(
        "applicant_details",
        route_after_applicant_details,
        {
            "loan_details": "loan_details",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "loan_details",
        route_after_loan_details,
        {
            "property_details": "property_details",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "property_details",
        route_after_property_details,
        {
            "document_details": "document_details",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "document_details",
        route_after_document_details,
        {
            END: END,
        },
    )

    return workflow


def get_thread_config(thread_id: str) -> dict:
    """Return LangGraph config for a thread."""

    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


def _run_checkpointed_update(
    thread_id: str,
    update: dict[str, Any],
) -> CheckpointedLoanState:
    """
    Run one checkpointed update for the given thread.

    This loads existing checkpoint state, merges the new update,
    runs the graph, and saves the updated state back to PostgreSQL.
    """

    workflow = build_checkpointed_application_workflow()
    config = get_thread_config(thread_id)

    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        checkpointer.setup()
        graph = workflow.compile(checkpointer=checkpointer)

        existing_state = graph.get_state(config)

        if existing_state and existing_state.values:
            current_values = dict(existing_state.values)
        else:
            current_values = {
                "thread_id": thread_id,
                "completed_steps": [],
                "messages": [],
                "current_step": "applicant_details",
            }

        merged_state = {
            **current_values,
            **update,
            "thread_id": thread_id,
        }

        result = graph.invoke(merged_state, config=config)

    return result


def start_application_thread(thread_id: str) -> CheckpointedLoanState:
    """Start or resume a checkpointed application thread."""

    return _run_checkpointed_update(
        thread_id=thread_id,
        update={},
    )


def save_applicant_details(
    thread_id: str,
    applicant_details: dict[str, Any],
) -> CheckpointedLoanState:
    """Save applicant details into checkpointed state."""

    return _run_checkpointed_update(
        thread_id=thread_id,
        update={
            "applicant_details": applicant_details,
        },
    )


def save_loan_details(
    thread_id: str,
    loan_details: dict[str, Any],
) -> CheckpointedLoanState:
    """Save loan details into checkpointed state."""

    return _run_checkpointed_update(
        thread_id=thread_id,
        update={
            "loan_details": loan_details,
        },
    )


def save_property_details(
    thread_id: str,
    property_details: dict[str, Any],
) -> CheckpointedLoanState:
    """Save property details into checkpointed state."""

    return _run_checkpointed_update(
        thread_id=thread_id,
        update={
            "property_details": property_details,
        },
    )


def save_document_details(
    thread_id: str,
    document_details: dict[str, Any],
) -> CheckpointedLoanState:
    """Save document details into checkpointed state."""

    return _run_checkpointed_update(
        thread_id=thread_id,
        update={
            "document_details": document_details,
        },
    )


def get_application_progress(thread_id: str) -> CheckpointedLoanState:
    """Return saved checkpoint state for a thread."""

    workflow = build_checkpointed_application_workflow()
    config = get_thread_config(thread_id)

    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        checkpointer.setup()
        graph = workflow.compile(checkpointer=checkpointer)
        existing_state = graph.get_state(config)

        if existing_state and existing_state.values:
            return dict(existing_state.values)

    return {
        "thread_id": thread_id,
        "completed_steps": [],
        "messages": [],
        "current_step": "not_started",
    }


def is_ready_for_submission(state: CheckpointedLoanState) -> bool:
    """Return whether the checkpointed application is ready for final submission."""

    return state.get("current_step") == "ready_for_submission"