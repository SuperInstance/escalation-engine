"""
Tests for LLM provider implementations
"""

import pytest
from escalation_engine.core import DecisionContext, DecisionSource
from escalation_engine.providers import (
    BotProvider,
    BrainProvider,
    HumanProvider,
    create_provider,
    LLMProviderConfig,
)


class TestBotProvider:
    """Tests for BotProvider"""

    @pytest.mark.asyncio
    async def test_bot_provider_decision(self):
        """Test bot provider makes a decision"""
        config = LLMProviderConfig(
            name="test_bot",
            provider_type="bot",
        )
        provider = BotProvider(config)

        context = DecisionContext(
            character_id="test_char",
            situation_type="combat",
            situation_description="Enemy attacks",
        )

        response = await provider.decide(context)

        assert response.content is not None
        assert response.provider == "test_bot"
        assert response.cost == 0.0

    def test_bot_provider_cost(self):
        """Test bot provider estimates zero cost"""
        config = LLMProviderConfig(name="bot", provider_type="bot")
        provider = BotProvider(config)

        assert provider.estimate_cost(1000) == 0.0

    def test_bot_provider_custom_rule(self):
        """Test bot provider with custom rule"""
        provider = BotProvider()

        def custom_handler(context):
            return {"action": "Custom action", "confidence": 0.95}

        provider.add_rule("test_type", custom_handler)

        context = DecisionContext(
            character_id="test",
            situation_type="test_type",
            situation_description="Test",
        )

        # The handler should be registered
        assert "test_type" in provider.rules


class TestBrainProvider:
    """Tests for BrainProvider"""

    @pytest.mark.asyncio
    async def test_brain_provider_decision(self):
        """Test brain provider makes a decision"""
        config = LLMProviderConfig(
            name="test_brain",
            provider_type="ollama",
            base_url="http://localhost:11434",
            model="llama2",
        )
        provider = BrainProvider(config)

        context = DecisionContext(
            character_id="test_char",
            situation_type="support",
            situation_description="Customer needs help",
        )

        # Should return a response even without Ollama running
        response = await provider.decide(context)

        assert response.content is not None
        assert response.provider == "test_brain"

    def test_brain_provider_cost(self):
        """Test brain provider estimates cost"""
        config = LLMProviderConfig(
            name="brain",
            provider_type="ollama",
            cost_per_1k_tokens=0.001,
        )
        provider = BrainProvider(config)

        cost = provider.estimate_cost(500)
        assert cost == 0.0005  # 500/1000 * 0.001


class TestHumanProvider:
    """Tests for HumanProvider"""

    @pytest.mark.asyncio
    async def test_human_provider_decision(self):
        """Test human provider makes a decision"""
        config = LLMProviderConfig(
            name="test_human",
            provider_type="openai",
            model="gpt-3.5-turbo",
            cost_per_1k_tokens=0.002,
        )
        provider = HumanProvider(config)

        context = DecisionContext(
            character_id="test_char",
            situation_type="critical",
            situation_description="Critical situation",
            stakes=0.95,
        )

        # Should return a response even without API key
        response = await provider.decide(context)

        assert response.content is not None
        assert response.provider == "test_human"

    def test_human_provider_cost(self):
        """Test human provider estimates cost"""
        config = LLMProviderConfig(
            name="human",
            provider_type="openai",
            cost_per_1k_tokens=0.002,
        )
        provider = HumanProvider(config)

        cost = provider.estimate_cost(1000)
        assert cost == 0.002  # 1000/1000 * 0.002


class TestCreateProvider:
    """Tests for create_provider factory function"""

    def test_create_bot_provider(self):
        """Test creating a bot provider"""
        provider = create_provider(DecisionSource.BOT)
        assert isinstance(provider, BotProvider)

    def test_create_brain_provider(self):
        """Test creating a brain provider"""
        provider = create_provider(DecisionSource.BRAIN)
        assert isinstance(provider, BrainProvider)

    def test_create_human_provider(self):
        """Test creating a human provider"""
        config = LLMProviderConfig(
            name="human",
            provider_type="openai",
        )
        provider = create_provider(DecisionSource.HUMAN, config)
        assert isinstance(provider, HumanProvider)

    def test_create_unknown_provider(self):
        """Test creating provider with unknown source raises error"""
        with pytest.raises(ValueError):
            # Create a fake source
            from enum import Enum
            class FakeSource(Enum):
                FAKE = "fake"

            create_provider(FakeSource.FAKE)
