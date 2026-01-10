"""
Configuration management for Escalation Engine

Supports YAML and JSON configuration files with environment variable interpolation.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

import yaml

logger = logging.getLogger(__name__)


def _substitute_env_vars(value: str) -> str:
    """Substitute environment variables in strings like ${VAR_NAME}"""
    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        var_name = match.group(1)
        # Check for default value syntax ${VAR:-default}
        if ':-' in var_name:
            var_name, default = var_name.split(':-', 1)
            return os.environ.get(var_name, default)
        return os.environ.get(var_name, match.group(0))

    return pattern.sub(replacer, value)


def _substitute_env_recursive(data: Any) -> Any:
    """Recursively substitute environment variables in data structures"""
    if isinstance(data, str):
        return _substitute_env_vars(data)
    elif isinstance(data, dict):
        return {k: _substitute_env_recursive(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_recursive(item) for item in data]
    return data


@dataclass
class ThresholdsConfig:
    """Configuration for escalation thresholds"""
    bot_min_confidence: float = 0.7
    brain_min_confidence: float = 0.5
    high_stakes_threshold: float = 0.7
    critical_stakes_threshold: float = 0.9
    urgent_time_ms: int = 500
    critical_time_ms: int = 100
    novelty_threshold: float = 0.6
    hp_critical_threshold: float = 0.2
    resource_critical_threshold: float = 0.15
    confidence_boost_per_success: float = 0.05
    confidence_penalty_per_failure: float = 0.1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThresholdsConfig':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider"""
    name: str
    provider_type: str  # "openai", "anthropic", "ollama"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    cost_per_1k_tokens: float = 0.0
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout_ms: int = 30000
    enabled: bool = True

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'LLMProviderConfig':
        """Create from dictionary"""
        provider_type = data.get("provider_type", name)
        return cls(
            name=name,
            provider_type=provider_type,
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            model=data.get("model", "gpt-3.5-turbo"),
            cost_per_1k_tokens=data.get("cost_per_1k_tokens", 0.0),
            max_tokens=data.get("max_tokens", 1000),
            temperature=data.get("temperature", 0.7),
            timeout_ms=data.get("timeout_ms", 30000),
            enabled=data.get("enabled", True),
        )


@dataclass
class CostTrackingConfig:
    """Configuration for cost tracking"""
    enabled: bool = True
    daily_budget: float = 10.0
    alert_threshold: float = 8.0
    cost_bot: float = 0.0
    cost_brain: float = 0.0
    cost_human: float = 0.02


@dataclass
class Config:
    """Main configuration for Escalation Engine"""
    default_thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    llm_providers: Dict[str, LLMProviderConfig] = field(default_factory=dict)
    cost_tracking: CostTrackingConfig = field(default_factory=CostTrackingConfig)
    enable_learning: bool = True
    enable_metrics: bool = True
    log_level: str = "INFO"

    # Character-specific overrides
    character_thresholds: Dict[str, ThresholdsConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create from dictionary"""
        config = cls()

        # Parse default thresholds
        if "default_thresholds" in data:
            config.default_thresholds = ThresholdsConfig.from_dict(data["default_thresholds"])

        # Parse LLM providers
        if "llm_providers" in data:
            for name, provider_data in data["llm_providers"].items():
                config.llm_providers[name] = LLMProviderConfig.from_dict(name, provider_data)

        # Parse cost tracking
        if "cost_tracking" in data:
            cost_data = data["cost_tracking"]
            config.cost_tracking = CostTrackingConfig(
                enabled=cost_data.get("enabled", True),
                daily_budget=cost_data.get("daily_budget", 10.0),
                alert_threshold=cost_data.get("alert_threshold", 8.0),
                cost_bot=cost_data.get("cost_bot", 0.0),
                cost_brain=cost_data.get("cost_brain", 0.0),
                cost_human=cost_data.get("cost_human", 0.02),
            )

        # Parse settings
        config.enable_learning = data.get("enable_learning", True)
        config.enable_metrics = data.get("enable_metrics", True)
        config.log_level = data.get("log_level", "INFO")

        # Parse character thresholds
        if "character_thresholds" in data:
            for char_id, thresh_data in data["character_thresholds"].items():
                config.character_thresholds[char_id] = ThresholdsConfig.from_dict(thresh_data)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "default_thresholds": {
                "bot_min_confidence": self.default_thresholds.bot_min_confidence,
                "brain_min_confidence": self.default_thresholds.brain_min_confidence,
                "high_stakes_threshold": self.default_thresholds.high_stakes_threshold,
                "critical_stakes_threshold": self.default_thresholds.critical_stakes_threshold,
                "urgent_time_ms": self.default_thresholds.urgent_time_ms,
                "critical_time_ms": self.default_thresholds.critical_time_ms,
                "novelty_threshold": self.default_thresholds.novelty_threshold,
            },
            "llm_providers": {
                name: {
                    "provider_type": p.provider_type,
                    "model": p.model,
                    "cost_per_1k_tokens": p.cost_per_1k_tokens,
                    "enabled": p.enabled,
                }
                for name, p in self.llm_providers.items()
            },
            "cost_tracking": {
                "enabled": self.cost_tracking.enabled,
                "daily_budget": self.cost_tracking.daily_budget,
                "alert_threshold": self.cost_tracking.alert_threshold,
            },
            "enable_learning": self.enable_learning,
            "enable_metrics": self.enable_metrics,
            "log_level": self.log_level,
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from a file

    Args:
        config_path: Path to YAML or JSON config file

    Returns:
        Config object
    """
    if config_path is None:
        # Check default locations
        default_paths = [
            "escalation_config.yaml",
            "escalation_config.yml",
            "escalation_config.json",
            os.path.expanduser("~/.escalation-engine/config.yaml"),
            "/etc/escalation-engine/config.yaml",
        ]

        for path in default_paths:
            if os.path.exists(path):
                config_path = path
                break
        else:
            # Return default config
            logger.info("No config file found, using defaults")
            return Config()

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load based on extension
    suffix = config_file.suffix.lower()
    with open(config_file, "r") as f:
        if suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(f)
        elif suffix == ".json":
            import json
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file type: {suffix}")

    # Substitute environment variables
    data = _substitute_env_recursive(data)

    # Parse config
    config = Config.from_dict(data)
    logger.info(f"Loaded configuration from {config_path}")
    return config


def save_config(config: Config, config_path: str) -> None:
    """
    Save configuration to a file

    Args:
        config: Config object to save
        config_path: Path to save the config file
    """
    config_file = Path(config_path)
    suffix = config_file.suffix.lower()

    data = config.to_dict()

    with open(config_file, "w") as f:
        if suffix in [".yaml", ".yml"]:
            yaml.dump(data, f, default_flow_style=False)
        elif suffix == ".json":
            import json
            json.dump(data, f, indent=2)
        else:
            raise ValueError(f"Unsupported config file type: {suffix}")

    logger.info(f"Saved configuration to {config_path}")
