"""
Escalation Engine - Intelligent Decision Routing

A standalone tool for routing decisions through multiple tiers:
- Bot (mechanical, free)
- Brain (local LLM, low cost)
- Human (API LLM, higher cost)

Provides 40x cost reduction through intelligent routing based on:
- Confidence levels
- Stakes assessment
- Novelty detection
- Time constraints
- Historical performance
"""

__version__ = "1.0.0"
__author__ = "Casey"
__license__ = "MIT"

# Core exports
from escalation_engine.core import (
    EscalationEngine,
    DecisionSource,
    EscalationReason,
    EscalationThresholds,
    DecisionContext,
    EscalationDecision,
    DecisionResult,
)

# Configuration exports
from escalation_engine.config import (
    Config,
    ThresholdsConfig,
    LLMProviderConfig,
    load_config,
)

# LLM provider exports
from escalation_engine.providers import (
    LLMProvider,
    BotProvider,
    BrainProvider,
    HumanProvider,
    create_provider,
)

# Metrics exports
from escalation_engine.metrics import (
    MetricsTracker,
    CostTracker,
    PerformanceMetrics,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core
    "EscalationEngine",
    "DecisionSource",
    "EscalationReason",
    "EscalationThresholds",
    "DecisionContext",
    "EscalationDecision",
    "DecisionResult",
    # Configuration
    "Config",
    "ThresholdsConfig",
    "LLMProviderConfig",
    "load_config",
    # Providers
    "LLMProvider",
    "BotProvider",
    "BrainProvider",
    "HumanProvider",
    "create_provider",
    # Metrics
    "MetricsTracker",
    "CostTracker",
    "PerformanceMetrics",
]
