"""Model registry for OpenRouter API routing.

Maps agent roles to models with fallback chains for cost control and reliability.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class AgentRole(Enum):
    """Agent roles in the Karpathy validation loop."""

    ORCHESTRATOR = "orchestrator"
    IMPLEMENTER = "implementer"
    DEBUGGER = "debugger"
    TEST_EXECUTOR = "test_executor"
    UI_ARCHITECT = "ui_architect"


@dataclass
class ModelConfig:
    """Configuration for a single model on OpenRouter."""

    model_id: str  # Full OpenRouter model ID (e.g., "anthropic/claude-sonnet-4.5")
    context_length: int
    is_free: bool
    provider: str  # e.g., "anthropic", "openai", "nvidia", "poolside"
    description: str = ""


# Model registry: all available models
MODELS = {
    # Paid tier - high quality orchestration and implementation
    "claude-sonnet-4.5": ModelConfig(
        model_id="anthropic/claude-sonnet-5",
        context_length=200000,
        is_free=False,
        provider="anthropic",
        description="Claude Sonnet 4.5 - highest quality for orchestration and complex coding",
    ),
    "claude-opus-4.6": ModelConfig(
        model_id="anthropic/claude-opus-4.6",
        context_length=200000,
        is_free=False,
        provider="anthropic",
        description="Claude Opus 4.6 - premium orchestration tier, authorized for Architect/Orchestrator role only",
    ),
    "gpt-4o": ModelConfig(
        model_id="openai/gpt-4o",
        context_length=128000,
        is_free=False,
        provider="openai",
        description="GPT-4o - strong reasoning for code review and debugging",
    ),
    # Free tier - code generation
    "poolside-laguna-s": ModelConfig(
        model_id="poolside/laguna-s-2.1:free",
        context_length=262144,
        is_free=True,
        provider="poolside",
        description="Poolside Laguna S - free coding model, primary free implementer",
    ),
    "poolside-laguna-xs": ModelConfig(
        model_id="poolside/laguna-xs-2.1:free",
        context_length=262144,
        is_free=True,
        provider="poolside",
        description="Poolside Laguna XS - free coding model, fallback",
    ),
    "cohere-north-mini": ModelConfig(
        model_id="cohere/north-mini-code:free",
        context_length=256000,
        is_free=True,
        provider="cohere",
        description="Cohere North Mini - free coding model",
    ),
    # Frontier tier - advanced/complex build tasks (e.g. UI + dashboard design),
    # authorized on top of the standard cost-discipline default
    "kimi-k3": ModelConfig(
        model_id="moonshotai/kimi-k3",
        context_length=1048576,
        is_free=False,
        provider="moonshotai",
        description="Kimi K3 - frontier reasoning/coding model, large context",
    ),
    "glm-5.3": ModelConfig(
        model_id="z-ai/glm-5.3",
        context_length=1310720,
        is_free=False,
        provider="z-ai",
        description="GLM 5.3 - frontier reasoning/coding model, large context",
    ),
    "gpt-6-astra": ModelConfig(
        model_id="openai/gpt-6-astra",
        context_length=1050000,
        is_free=False,
        provider="openai",
        description="GPT-6 Astra - frontier OpenAI model",
    ),
    "openrouter-auto": ModelConfig(
        model_id="openrouter/auto",
        context_length=2000000,
        is_free=False,
        provider="openrouter",
        description="OpenRouter auto-router - dynamically selects a capable model per request",
    ),
    # Free tier - reasoning and debugging
    "nemotron-ultra": ModelConfig(
        model_id="nvidia/nemotron-3-ultra-550b-a55b:free",
        context_length=1000000,
        is_free=True,
        provider="nvidia",
        description="Nemotron 3 Ultra 550B - massive context, strong reasoning",
    ),
    "nemotron-lightning": ModelConfig(
        model_id="nvidia/nemotron-3.5-lightning:free",
        context_length=1000000,
        is_free=True,
        provider="nvidia",
        description="Nemotron 3.5 Lightning - fast inference, large context",
    ),
    "nemotron-super": ModelConfig(
        model_id="nvidia/nemotron-3-super-120b-a12b:free",
        context_length=262144,
        is_free=True,
        provider="nvidia",
        description="Nemotron 3 Super 120B - balanced free model",
    ),
}


# Role-based routing: ordered fallback chains
# Primary models are paid for quality, fallbacks use free tier for cost control
ROLE_ROUTING = {
    AgentRole.ORCHESTRATOR: [
        "claude-sonnet-4.5",  # Primary: default orchestration model per cost-discipline policy
        "gpt-4o",             # Fallback: strong reasoning if Sonnet unavailable
        # NOTE: claude-opus-4.6 intentionally excluded from automatic routing.
        # Per the routing matrix, Opus is an exception-only escalation for
        # security-critical or architecturally-deadlocked cases, requiring a
        # logged justification — never a silent default/fallback pick.
    ],
    AgentRole.IMPLEMENTER: [
        "poolside-laguna-s",  # Primary: free-tier default per cost-discipline policy
        "poolside-laguna-xs",  # Free fallback: smaller coding model
        "cohere-north-mini",  # Free fallback 2: general coding
    ],
    AgentRole.DEBUGGER: [
        "gpt-4o",  # Primary: strong reasoning for bug detection
        "nemotron-ultra",  # Free fallback: 1M context, strong reasoning
        "nemotron-lightning",  # Free fallback 2: fast, large context
        "nemotron-super",  # Free fallback 3: balanced
    ],
    AgentRole.TEST_EXECUTOR: [
        "poolside-laguna-s",  # Free tier acceptable for test generation
        "poolside-laguna-xs",
        "cohere-north-mini",
    ],
    AgentRole.UI_ARCHITECT: [
        "kimi-k3",  # Primary: frontier model for advanced UI/dashboard design
        "glm-5.3",  # Fallback 1: frontier alternative
        "gpt-6-astra",  # Fallback 2: frontier alternative
        "openrouter-auto",  # Fallback 3: let OpenRouter pick a capable model
    ],
}


def get_model_for_role(role: AgentRole, attempt: int = 0) -> str:
    """Get the appropriate model ID for a role, advancing through fallbacks on retries.

    Args:
        role: The agent role needing a model
        attempt: Retry attempt number (0 = first try, 1+ = fallbacks)

    Returns:
        OpenRouter model ID string (e.g., "anthropic/claude-sonnet-4.5")

    Raises:
        IndexError: If attempt exceeds available fallbacks
    """
    fallback_chain = ROLE_ROUTING.get(role, [])

    if not fallback_chain:
        raise ValueError(f"No models configured for role: {role}")

    if attempt >= len(fallback_chain):
        # Exhausted all fallbacks - return the last one and let caller handle failure
        return MODELS[fallback_chain[-1]].model_id

    model_key = fallback_chain[attempt]
    return MODELS[model_key].model_id


def get_model_info(model_key: str) -> Optional[ModelConfig]:
    """Get full model configuration by key.

    Args:
        model_key: Friendly model key (e.g., "claude-sonnet-4.5")

    Returns:
        ModelConfig if found, None otherwise
    """
    return MODELS.get(model_key)
