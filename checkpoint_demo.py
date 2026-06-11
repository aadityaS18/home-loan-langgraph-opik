"""
PostgreSQL checkpointing demo for the Home Loan Origination project.


"""

import os
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/home_loan",
)


class LoanJourneyState(TypedDict, total=False):
    """State for a simple step-by-step home loan journey."""

    applicant_name: str
    monthly_income: float
    loan_amount: float
    property_value: float
    current_step: str
    messages: list[str]


def collect_applicant_name(state: LoanJourneyState) -> LoanJourneyState:
    """Collect applicant name."""

    messages = state.get("messages", []).copy()

    if not state.get("applicant_name"):
        messages.append("Applicant name is missing.")
        return {
            **state,
            "current_step": "collect_applicant_name",
            "messages": messages,
        }

    messages.append(f"Applicant name collected: {state['applicant_name']}")

    return {
        **state,
        "current_step": "collect_income",
        "messages": messages,
    }


def collect_income(state: LoanJourneyState) -> LoanJourneyState:
    """Collect monthly income."""

    messages = state.get("messages", []).copy()

    if "monthly_income" not in state:
        messages.append("Monthly income is missing.")
        return {
            **state,
            "current_step": "collect_income",
            "messages": messages,
        }

    messages.append(f"Monthly income collected: {state['monthly_income']}")

    return {
        **state,
        "current_step": "collect_loan_amount",
        "messages": messages,
    }


def collect_loan_amount(state: LoanJourneyState) -> LoanJourneyState:
    """Collect requested loan amount."""

    messages = state.get("messages", []).copy()

    if "loan_amount" not in state:
        messages.append("Requested loan amount is missing.")
        return {
            **state,
            "current_step": "collect_loan_amount",
            "messages": messages,
        }

    messages.append(f"Requested loan amount collected: {state['loan_amount']}")

    return {
        **state,
        "current_step": "collect_property_value",
        "messages": messages,
    }


def collect_property_value(state: LoanJourneyState) -> LoanJourneyState:
    """Collect property value."""

    messages = state.get("messages", []).copy()

    if "property_value" not in state:
        messages.append("Property value is missing.")
        return {
            **state,
            "current_step": "collect_property_value",
            "messages": messages,
        }

    messages.append(f"Property value collected: {state['property_value']}")

    return {
        **state,
        "current_step": "ready_for_assessment",
        "messages": messages,
    }


def route_after_name(state: LoanJourneyState) -> str:
    """Route after applicant name step."""

    if not state.get("applicant_name"):
        return END

    return "collect_income"


def route_after_income(state: LoanJourneyState) -> str:
    """Route after income step."""

    if "monthly_income" not in state:
        return END

    return "collect_loan_amount"


def route_after_loan_amount(state: LoanJourneyState) -> str:
    """Route after loan amount step."""

    if "loan_amount" not in state:
        return END

    return "collect_property_value"


def route_after_property_value(state: LoanJourneyState) -> str:
    """Route after property value step."""

    return END


def build_workflow():
    """Build a small LangGraph workflow without compiling it yet."""

    workflow = StateGraph(LoanJourneyState)

    workflow.add_node("collect_applicant_name", collect_applicant_name)
    workflow.add_node("collect_income", collect_income)
    workflow.add_node("collect_loan_amount", collect_loan_amount)
    workflow.add_node("collect_property_value", collect_property_value)

    workflow.set_entry_point("collect_applicant_name")

    workflow.add_conditional_edges(
        "collect_applicant_name",
        route_after_name,
        {
            "collect_income": "collect_income",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "collect_income",
        route_after_income,
        {
            "collect_loan_amount": "collect_loan_amount",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "collect_loan_amount",
        route_after_loan_amount,
        {
            "collect_property_value": "collect_property_value",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "collect_property_value",
        route_after_property_value,
        {
            END: END,
        },
    )

    return workflow

def print_state(title: str, state):
    """Print workflow state."""

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if isinstance(state, dict):
        values = state
    elif hasattr(state, "values") and isinstance(state.values, dict):
        values = state.values
    else:
        values = {}

    print("Current step:", values.get("current_step"))
    print("Applicant name:", values.get("applicant_name"))
    print("Monthly income:", values.get("monthly_income"))
    print("Loan amount:", values.get("loan_amount"))
    print("Property value:", values.get("property_value"))

    print("\nMessages:")
    for message in values.get("messages", []):
        print("-", message)


def main():
    """Run checkpointing demo."""

    thread_id = "loan-demo-thread-001"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    print("\nPostgreSQL checkpointing demo started.")
    print(f"Thread ID: {thread_id}")

    workflow = build_workflow()

    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        # Creates checkpoint tables if they do not already exist.
        checkpointer.setup()

        graph = workflow.compile(checkpointer=checkpointer)

        state_1 = graph.invoke(
            {
                "applicant_name": "Aaditya",
                "messages": [],
            },
            config=config,
        )

        print_state("After step 1: applicant name collected", state_1)

        saved_state_1 = graph.get_state(config)
        print_state("Saved checkpoint after step 1", saved_state_1)

        state_2 = graph.invoke(
            {
                **saved_state_1.values,
                "monthly_income": 120000.0,
            },
            config=config,
        )

        print_state("After step 2: income collected", state_2)

        saved_state_2 = graph.get_state(config)
        print_state("Saved checkpoint after step 2", saved_state_2)

        state_3 = graph.invoke(
            {
                **saved_state_2.values,
                "loan_amount": 4000000.0,
            },
            config=config,
        )

        print_state("After step 3: loan amount collected", state_3)

        saved_state_3 = graph.get_state(config)
        print_state("Saved checkpoint after step 3", saved_state_3)

        state_4 = graph.invoke(
            {
                **saved_state_3.values,
                "property_value": 7000000.0,
            },
            config=config,
        )

        print_state("After step 4: property value collected", state_4)

        saved_state_4 = graph.get_state(config)
        print_state("Final saved checkpoint", saved_state_4)

    print("\nCheckpointing demo completed.")
    print("The workflow state was saved and resumed using PostgreSQL.")


if __name__ == "__main__":
    main()