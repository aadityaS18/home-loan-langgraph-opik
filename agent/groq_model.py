import os

from langchain_groq import ChatGroq


def get_groq_llm() -> ChatGroq:
    """Create Groq chat model."""

    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        max_retries=2,
    )