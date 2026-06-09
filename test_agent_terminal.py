"""
Terminal test for the agentic home-loan flow.

This version prints:
- Assistant messages
- Tool calls requested by the agent
- Tool outputs returned to the agent

Use this before adding PostgreSQL and UI, so we can confirm that the agent
is actually calling the financial, KYC, CIBIL, document and underwriting tools.
"""

from agent.home_loan_agent import build_home_loan_agent


def print_message(message):
    """
    Pretty-print LangChain/LangGraph messages returned by the agent.
    """

    message_type = getattr(message, "type", "unknown")
    content = getattr(message, "content", "")

    # Assistant messages can contain tool calls.
    if message_type == "ai":
        tool_calls = getattr(message, "tool_calls", None)

        if content:
            print("\nAgent:", content)

        if tool_calls:
            print("\n--- TOOL CALLS REQUESTED ---")
            for tool_call in tool_calls:
                print(f"Tool: {tool_call.get('name')}")
                print(f"Args: {tool_call.get('args')}")

    # Tool output messages show results from tools.
    elif message_type == "tool":
        tool_name = getattr(message, "name", "unknown_tool")
        print("\n--- TOOL OUTPUT ---")
        print(f"Tool: {tool_name}")
        print(f"Output: {content}")

    # Human/user messages.
    elif message_type == "human":
        print("\nUser:", content)

    # Fallback for any other message type.
    else:
        if content:
            print(f"\n{message_type.upper()}:", content)


def main():
    agent = build_home_loan_agent()

    print("\nHome Loan Agent Terminal Test")
    print("Type 'exit' to stop.")
    print("This test prints tool calls and tool outputs.\n")

    conversation_messages = []

    while True:
        user_message = input("You: ").strip()

        if user_message.lower() in {"exit", "quit"}:
            break

        conversation_messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        response = agent.invoke(
            {
                "messages": conversation_messages,
            }
        )

        messages = response["messages"]

        print("\n================ AGENT TRACE ================")
        for message in messages:
            print_message(message)
        print("============================================\n")

        # Keep the returned conversation messages for the next turn.
        conversation_messages = messages


if __name__ == "__main__":
    main()
    