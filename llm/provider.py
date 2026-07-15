"""LLM provider configuration and initialization.

This module provides a centralized way to configure and instantiate
the language model used throughout the application, ensuring
consistent settings such as temperature and model choice.

Provider selection
------------------
The active provider is controlled by the ``LLM_PROVIDER`` environment
variable (default: ``"nvidia"``).

nvidia (default)
    Uses ``langchain-nvidia-ai-endpoints`` (``ChatNVIDIA``).
    Requires ``NVIDIA_API_KEY``.
    Default model: ``deepseek-ai/deepseek-v3`` — strong tool/function calling
    and strict JSON schema adherence, eliminating the enum-confusion issues
    seen with some Groq-hosted models.

groq (fallback)
    Uses ``langchain-groq`` (``ChatGroq``).
    Requires ``GROQ_API_KEY``.
    Default model: ``llama-3.3-70b-versatile``.
    Note: some Groq-hosted models have known issues with strict enum values
    in structured output.  Prefer the NVIDIA provider for production use.

Model overrides
---------------
The active model can be overridden per-call via the ``model_name`` argument
to :func:`get_llm`, or globally via the ``NVIDIA_MODEL`` / ``GROQ_MODEL``
environment variables.
"""

import os
from typing import Optional, Union

from langchain_core.language_models.chat_models import BaseChatModel

# ---------------------------------------------------------------------------
# Provider defaults
# ---------------------------------------------------------------------------

_NVIDIA_DEFAULT_MODEL = "z-ai/glm-5.2"
_GROQ_DEFAULT_MODEL   = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def get_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    provider: Optional[str] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    seed: Optional[int] = None,
) -> BaseChatModel:
    """Initialize and return a chat model instance.

    The provider is chosen from the ``provider`` argument (highest priority),
    then the ``LLM_PROVIDER`` environment variable, then ``"nvidia"`` as the
    hard-coded default.

    Args:
        model_name: Optional model identifier override.  When ``None`` the
            provider-specific default model is used (``NVIDIA_MODEL`` /
            ``GROQ_MODEL`` env vars are checked first).
        temperature: Sampling temperature.  Defaults to ``0.0`` for
            deterministic, reproducible structured-output calls.
        provider: Optional provider override (``"nvidia"`` or ``"groq"``).  When
            ``None`` the ``LLM_PROVIDER`` environment variable is used, falling
            back to ``"nvidia"``.
        top_p: Nucleus-sampling probability mass (NVIDIA only).  ``None`` uses
            the model's server-side default.
        max_tokens: Maximum tokens in the completion (NVIDIA only).  ``None``
            uses the model's server-side default.
        seed: Fixed random seed for reproducible sampling (NVIDIA only).  ``None``
            leaves sampling non-deterministic.

    Returns:
        A :class:`~langchain_core.language_models.chat_models.BaseChatModel`
        instance ready to use with LangChain chains.

    Raises:
        ValueError: If the required API key for the selected provider is not
            set in the environment.
        ValueError: If an unsupported provider name is given.

    Example::

        from llm.provider import get_llm

        llm = get_llm()                                     # NVIDIA, GLM-5.2
        llm = get_llm(provider="groq")                      # Groq, Llama-3.3-70b
        llm = get_llm(top_p=1, max_tokens=16384, seed=42)   # GLM-5.2 with fixed seed
    """
    resolved_provider = (
        provider
        or os.getenv("LLM_PROVIDER", "nvidia")
    ).lower().strip()

    if resolved_provider == "nvidia":
        return _build_nvidia_llm(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
        )
    elif resolved_provider == "groq":
        return _build_groq_llm(model_name=model_name, temperature=temperature)
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{resolved_provider}'. "
            "Set LLM_PROVIDER to 'nvidia' or 'groq'."
        )


# ---------------------------------------------------------------------------
# Provider-specific builders
# ---------------------------------------------------------------------------


def _build_nvidia_llm(
    model_name: Optional[str],
    temperature: float,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    seed: Optional[int] = None,
) -> BaseChatModel:
    """Build a ChatNVIDIA instance.

    Args:
        model_name: Model identifier override.  Falls back to ``NVIDIA_MODEL``
            env var, then :data:`_NVIDIA_DEFAULT_MODEL`.
        temperature: Sampling temperature.
        top_p: Nucleus-sampling probability mass.  Omitted when ``None``.
        max_tokens: Maximum completion tokens.  Omitted when ``None``.
        seed: Fixed random seed for reproducible outputs.  Omitted when ``None``.

    Returns:
        Initialized :class:`~langchain_nvidia_ai_endpoints.ChatNVIDIA`.

    Raises:
        ValueError: If ``NVIDIA_API_KEY`` is not set.
    """
    from langchain_nvidia_ai_endpoints import ChatNVIDIA  # noqa: PLC0415

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError(
            "NVIDIA_API_KEY environment variable is not set. "
            "Get a free key at https://build.nvidia.com and add it to your .env file."
        )

    model = model_name or os.getenv("NVIDIA_MODEL", _NVIDIA_DEFAULT_MODEL)

    # Build kwargs — only include optional params when explicitly provided
    # so the model's server-side defaults are respected when they are None.
    kwargs: dict = dict(
        api_key=api_key,
        model=model,
        temperature=temperature,
    )
    if top_p is not None:
        kwargs["top_p"] = top_p
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if seed is not None:
        kwargs["seed"] = seed

    return ChatNVIDIA(**kwargs)


def _build_groq_llm(
    model_name: Optional[str],
    temperature: float,
) -> BaseChatModel:
    """Build a ChatGroq instance.

    Args:
        model_name: Model identifier override.  Falls back to ``GROQ_MODEL``
            env var, then :data:`_GROQ_DEFAULT_MODEL`.
        temperature: Sampling temperature.

    Returns:
        Initialized :class:`~langchain_groq.ChatGroq`.

    Raises:
        ValueError: If ``GROQ_API_KEY`` is not set.
    """
    from langchain_groq import ChatGroq  # noqa: PLC0415

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is not set. "
            "Please check your .env file or environment configuration."
        )

    model = model_name or os.getenv("GROQ_MODEL", _GROQ_DEFAULT_MODEL)

    return ChatGroq(
        api_key=api_key,
        model_name=model,
        temperature=temperature,
    )


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("Initializing LLM...")
    try:
        llm = get_llm()
        print(f"Provider : {os.getenv('LLM_PROVIDER', 'nvidia')}")
        print(f"Model    : {getattr(llm, 'model', getattr(llm, 'model_name', 'unknown'))}")
        print("Testing completion...")
        response = llm.invoke("Reply with exactly one word: Ready")
        print("Response:", response.content)
    except Exception as e:
        print(f"Error: {e}")
