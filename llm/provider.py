"""LLM provider configuration and initialization.

This module provides a centralized way to configure and instantiate
the language model used throughout the application, ensuring
consistent settings such as temperature and model choice.
"""

import os
from typing import Optional
from langchain_groq import ChatGroq

# Default model can be overridden by environment variable
DEFAULT_MODEL = "groq/compound"

def get_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatGroq:
    """Initialize and return a ChatGroq instance.
    
    Args:
        model_name: Optional override for the model to use.
            Defaults to GROQ_MODEL environment variable or DEFAULT_MODEL.
        temperature: Sampling temperature. Defaults to 0.0 for deterministic output.
        
    Returns:
        ChatGroq: An initialized LangChain ChatGroq model instance.
        
    Raises:
        ValueError: If GROQ_API_KEY is not found in the environment.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is not set. "
            "Please check your .env file or environment configuration."
        )
        
    model = model_name or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    
    return ChatGroq(
        api_key=api_key,
        model_name=model,
        temperature=temperature
    )

if __name__ == "__main__":
    from dotenv import load_dotenv
    # Load environment variables from the .env file in the root
    load_dotenv()
    
    print("Initializing LLM...")
    try:
        llm = get_llm()
        print(f"Success! Initialized model: {llm.model_name}")
        print("Testing completion...")
        response = llm.invoke("Hi! Are you working?")
        print("Response:", response.content)
    except Exception as e:
        print(f"Error: {e}")
