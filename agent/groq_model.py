"""
LLM provider setup.

Default provider:
- Ollama local model for development/testing.

Fallback provider:
- Groq hosted model for cloud/demo usage.

Environment variables:
MODEL_PROVIDER=ollama or groq
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://host.docker.internal:11434
GROQ_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=your_key
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama


load_dotenv()


@lru_cache(maxsize=1)
def get_groq_llm():
    """
    Backward-compatible function name.

    Even though the function is called get_groq_llm,
    it can now return either:
    - ChatOllama
    - ChatGroq

    This avoids changing imports in the rest of the project.
    """

    model_provider = os.getenv("MODEL_PROVIDER", "ollama").lower().strip()

    if model_provider == "ollama":
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://host.docker.internal:11434",
        )

        return ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=0.1,
            format="json",
        )

    if model_provider == "groq":
        groq_api_key = os.getenv("GROQ_API_KEY")
        groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        if not groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. Add it to .env or switch MODEL_PROVIDER=ollama."
            )

        return ChatGroq(
            groq_api_key=groq_api_key,
            model_name=groq_model,
            temperature=0.1,
        )

    raise ValueError(
        f"Unsupported MODEL_PROVIDER={model_provider}. Use 'ollama' or 'groq'."
    )


def get_llm():
    """
    Cleaner alias for future use.
    """
    return get_groq_llm()