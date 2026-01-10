"""
LLM Provider implementations for Escalation Engine

Supports multiple LLM providers:
- Bot: Rule-based, deterministic responses (free)
- Brain: Local LLM via Ollama (low cost)
- Human: Cloud LLMs via OpenAI, Anthropic, etc (higher cost)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .core import DecisionSource, DecisionContext, DecisionResult
from .config import LLMProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider"""
    content: str
    confidence: float
    tokens_used: int = 0
    cost: float = 0.0
    provider: str = ""
    model: str = ""
    time_taken_ms: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.name = config.name

    @abstractmethod
    async def decide(self, context: DecisionContext, **kwargs) -> LLMResponse:
        """
        Make a decision based on the context

        Args:
            context: Decision context
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with decision
        """
        pass

    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for a given number of tokens"""
        pass


class BotProvider(LLMProvider):
    """
    Bot provider - rule-based, deterministic decisions

    Fast, free, but limited to predefined rules.
    """

    def __init__(self, config: Optional[LLMProviderConfig] = None, rules: Optional[Dict[str, Any]] = None):
        if config is None:
            config = LLMProviderConfig(
                name="bot",
                provider_type="bot",
                cost_per_1k_tokens=0.0,
            )
        super().__init__(config)
        self.rules = rules or {}

    def add_rule(self, situation_type: str, handler: callable) -> None:
        """Add a rule handler for a situation type"""
        self.rules[situation_type] = handler

    async def decide(self, context: DecisionContext, **kwargs) -> LLMResponse:
        """Make a rule-based decision"""
        import time

        start_time = time.time()

        # Check for custom rule handler
        handler = kwargs.get(f"handler_{context.situation_type}") or self.rules.get(context.situation_type)

        if handler:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(context)
            else:
                result = handler(context)
        else:
            # Default rule-based logic
            result = self._default_handler(context)

        time_taken = (time.time() - start_time) * 1000

        return LLMResponse(
            content=result.get("action", "Proceed with default action"),
            confidence=result.get("confidence", 0.8),
            tokens_used=0,
            cost=0.0,
            provider=self.name,
            model="rule-based",
            time_taken_ms=time_taken,
            metadata=result.get("metadata", {}),
        )

    def _default_handler(self, context: DecisionContext) -> Dict[str, Any]:
        """Default rule-based decision logic"""
        # Extract action from description
        description = context.situation_description.lower()

        # Simple keyword-based decision
        if any(word in description for word in ["attack", "fight", "combat"]):
            return {"action": "Engage in combat", "confidence": 0.85}
        elif any(word in description for word in ["talk", "speak", "negotiate"]):
            return {"action": "Initiate dialogue", "confidence": 0.8}
        elif any(word in description for word in ["run", "flee", "escape"]):
            return {"action": "Retreat to safety", "confidence": 0.9}
        elif any(word in description for word in ["help", "assist", "support"]):
            return {"action": "Provide assistance", "confidence": 0.85}
        else:
            return {"action": "Assess and proceed cautiously", "confidence": 0.7}

    def estimate_cost(self, tokens: int) -> float:
        """Bot decisions are free"""
        return 0.0


class BrainProvider(LLMProvider):
    """
    Brain provider - local LLM via Ollama

    Low cost, good for nuanced decisions.
    """

    def __init__(self, config: Optional[LLMProviderConfig] = None):
        if config is None:
            config = LLMProviderConfig(
                name="brain",
                provider_type="ollama",
                base_url="http://localhost:11434",
                model="llama2",
                cost_per_1k_tokens=0.0,
            )
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy load the Ollama client"""
        if self._client is None:
            try:
                from ollama import Client
                self._client = Client(host=self.config.base_url)
            except ImportError:
                logger.warning("ollama package not installed, using mock responses")
                self._client = None
        return self._client

    async def decide(self, context: DecisionContext, **kwargs) -> LLMResponse:
        """Make a decision using local LLM"""
        import time

        start_time = time.time()
        client = self._get_client()

        prompt = self._build_prompt(context, kwargs)

        try:
            if client:
                response = await asyncio.to_thread(
                    client.generate,
                    model=self.config.model,
                    prompt=prompt,
                )
                content = response.get("response", "")
                tokens_used = response.get("eval_count", 0)
                confidence = self._extract_confidence(content)
            else:
                # Mock response when Ollama not available
                content = f"Considering: {context.situation_description}. Proceed with informed action."
                tokens_used = len(content.split()) * 1.3  # Rough estimate
                confidence = 0.7

        except Exception as e:
            logger.error(f"Brain provider error: {e}")
            content = f"Error: Unable to process. Defaulting to cautious approach."
            tokens_used = 0
            confidence = 0.5

        time_taken = (time.time() - start_time) * 1000
        cost = self.estimate_cost(int(tokens_used))

        return LLMResponse(
            content=content,
            confidence=confidence,
            tokens_used=int(tokens_used),
            cost=cost,
            provider=self.name,
            model=self.config.model,
            time_taken_ms=time_taken,
        )

    def _build_prompt(self, context: DecisionContext, kwargs: Dict) -> str:
        """Build prompt for the LLM"""
        system_prompt = kwargs.get("system_prompt", "You are a helpful assistant making decisions.")

        prompt = f"""{system_prompt}

Situation Type: {context.situation_type}
Description: {context.situation_description}
Stakes: {context.stakes:.2f} (0=trivial, 1=critical)

Please provide:
1. A clear action to take
2. Your confidence level (0-1)

Respond in format: ACTION: [action] CONFIDENCE: [0-1]"""
        return prompt

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence from response"""
        import re
        match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 0.7  # Default

    def estimate_cost(self, tokens: int) -> float:
        """Local LLM is essentially free"""
        return self.config.cost_per_1k_tokens * (tokens / 1000)


class HumanProvider(LLMProvider):
    """
    Human provider - cloud LLM via API

    Higher cost, best for critical decisions.
    Supports OpenAI, Anthropic, and compatible APIs.
    """

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        self._async_client = None
        self._sync_client = None

    def _get_clients(self):
        """Lazy load API clients"""
        provider_type = self.config.provider_type.lower()

        if provider_type == "openai":
            try:
                from openai import AsyncOpenAI, OpenAI
                if self._async_client is None:
                    self._async_client = AsyncOpenAI(api_key=self.config.api_key)
                if self._sync_client is None:
                    self._sync_client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                logger.warning("openai package not installed")
        elif provider_type == "anthropic":
            try:
                from anthropic import AsyncAnthropic, Anthropic
                if self._async_client is None:
                    self._async_client = AsyncAnthropic(api_key=self.config.api_key)
                if self._sync_client is None:
                    self._sync_client = Anthropic(api_key=self.config.api_key)
            except ImportError:
                logger.warning("anthropic package not installed")

        return self._async_client, self._sync_client

    async def decide(self, context: DecisionContext, **kwargs) -> LLMResponse:
        """Make a decision using cloud LLM API"""
        import time

        start_time = time.time()
        async_client, _ = self._get_clients()

        prompt = self._build_prompt(context, kwargs)

        try:
            if self.config.provider_type.lower() == "openai" and async_client:
                response = await async_client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": kwargs.get("system_prompt", "You are a helpful assistant.")},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                confidence = self._extract_confidence(content)

            elif self.config.provider_type.lower() == "anthropic" and async_client:
                response = await async_client.messages.create(
                    model=self.config.model,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                    system=kwargs.get("system_prompt", "You are a helpful assistant."),
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.content[0].text
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                confidence = self._extract_confidence(content)

            else:
                # Mock response when provider not available
                content = f"Analyzing: {context.situation_description}. Recommended action: Carefully evaluate and proceed."
                tokens_used = 500
                confidence = 0.85

        except Exception as e:
            logger.error(f"Human provider error: {e}")
            content = f"Error: Unable to process. Please review manually."
            tokens_used = 0
            confidence = 0.5

        time_taken = (time.time() - start_time) * 1000
        cost = self.estimate_cost(tokens_used)

        return LLMResponse(
            content=content,
            confidence=confidence,
            tokens_used=tokens_used,
            cost=cost,
            provider=self.name,
            model=self.config.model,
            time_taken_ms=time_taken,
        )

    def _build_prompt(self, context: DecisionContext, kwargs: Dict) -> str:
        """Build prompt for the LLM"""
        return f"""Situation Type: {context.situation_type}
Description: {context.situation_description}
Stakes: {context.stakes:.2f} (0=trivial, 1=critical)
Urgency: {context.urgency_ms}ms available

Character Status:
- HP: {context.character_hp_ratio:.1%}
- Resources: {context.available_resources}

Recent Context:
- Similar situations seen: {context.similar_decisions_count}
- Recent failures: {context.recent_failures}

Please provide:
1. A clear, specific action to take
2. Your confidence level (0-1)
3. Brief rationale

Respond in format:
ACTION: [action]
CONFIDENCE: [0-1]
RATIONALE: [brief explanation]"""

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence from response"""
        import re
        match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 0.85  # Default for human-level decisions

    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on tokens and provider pricing"""
        return self.config.cost_per_1k_tokens * (tokens / 1000)


def create_provider(source: DecisionSource, config: Optional[LLMProviderConfig] = None) -> LLMProvider:
    """
    Factory function to create a provider based on decision source

    Args:
        source: Decision source (BOT, BRAIN, HUMAN)
        config: Provider configuration

    Returns:
        LLMProvider instance
    """
    if source == DecisionSource.BOT:
        return BotProvider(config)
    elif source == DecisionSource.BRAIN:
        return BrainProvider(config)
    elif source == DecisionSource.HUMAN:
        if config is None:
            # Default to OpenAI if no config provided
            config = LLMProviderConfig(
                name="human",
                provider_type="openai",
                model="gpt-3.5-turbo",
                cost_per_1k_tokens=0.002,
            )
        return HumanProvider(config)
    else:
        raise ValueError(f"Unknown decision source: {source}")
