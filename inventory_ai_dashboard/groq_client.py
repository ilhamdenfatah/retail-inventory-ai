"""
groq_client.py
Handles all Groq API calls. Takes a system prompt and message, returns the response as a string.
"""

import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")


def get_groq_client() -> Groq:
    """Initialize and return a Groq client using the API key from .env"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Make sure it's set in your .env file as: GROQ_API_KEY=your_key_here"
        )
    return Groq(api_key=api_key)


def ask_groq(
    system_prompt: str,
    user_message: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.3,
) -> str:
    """Send a single message to Groq and return the response text."""
    client = get_groq_client()

    chat_completion = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return chat_completion.choices[0].message.content


def ask_groq_with_history(
    system_prompt: str,
    conversation_history: list[dict],
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.3,
) -> str:
    """Send a full conversation history to Groq. Used for the Layer 2 Q&A chat."""
    client = get_groq_client()

    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    chat_completion = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )

    return chat_completion.choices[0].message.content

if __name__ == "__main__":
    from data_context import load_data, build_ai_context
    df = load_data()
    ctx = build_ai_context(df)

    response = ask_groq(
        system_prompt=f"You are an inventory analyst. Here is the data:\n\n{ctx}",
        user_message="Which store is at highest risk and why?"
    )
    print("✅ Groq response:")
    print(response)