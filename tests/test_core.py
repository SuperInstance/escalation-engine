"""
Tests for Escalation Engine core functionality
"""

import pytest
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationReason,
    EscalationThresholds,
)


class TestEscalationEngine:
    """Tests for EscalationEngine class"""

    def test_initialization(self):
        """Test engine initialization"""
        engine = EscalationEngine()
        assert engine is not None
        assert engine.stats["total_decisions"] == 0

    def test_route_bot_decision(self):
        """Test routing a routine decision to bot"""
        engine = EscalationEngine()

        # First, add some patterns so the situation isn't novel
        engine.situation_patterns[f"test_char:faq"] = ["Common question"] * 10

        context = DecisionContext(
            character_id="test_char",
            situation_type="faq",
            situation_description="Common question",
            stakes=0.2,
            similar_decisions_count=10,
        )

        decision = engine.route_decision(context)
        assert decision.source == DecisionSource.BOT

    def test_route_human_decision_critical(self):
        """Test routing a critical decision to human"""
        engine = EscalationEngine()

        context = DecisionContext(
            character_id="test_char",
            situation_type="security",
            situation_description="Critical security incident",
            stakes=0.95,
            urgency_ms=50,
        )

        decision = engine.route_decision(context)
        assert decision.source == DecisionSource.HUMAN
        assert decision.reason in [EscalationReason.HIGH_STAKES, EscalationReason.TIME_CRITICAL]

    def test_route_brain_decision_novel(self):
        """Test routing a novel decision to brain"""
        engine = EscalationEngine()

        context = DecisionContext(
            character_id="test_char",
            situation_type="novel_situation",
            situation_description="Never seen before situation",
            stakes=0.6,
            similar_decisions_count=0,
        )

        decision = engine.route_decision(context)
        assert decision.source == DecisionSource.BRAIN
        assert decision.reason == EscalationReason.NOVEL_SITUATION

    def test_critical_hp_override(self):
        """Test critical HP override routes to human"""
        engine = EscalationEngine()

        context = DecisionContext(
            character_id="test_char",
            situation_type="routine",
            situation_description="Routine situation",
            stakes=0.3,
            character_hp_ratio=0.15,  # Critical HP
        )

        decision = engine.route_decision(context)
        assert decision.source == DecisionSource.HUMAN
        assert decision.reason == EscalationReason.SAFETY_CONCERN

    def test_record_decision(self):
        """Test recording a decision"""
        engine = EscalationEngine()

        result = DecisionResult(
            decision_id="test_001",
            source=DecisionSource.BOT,
            action="Test action",
            confidence=0.8,
            time_taken_ms=10.0,
            metadata={"character_id": "test_char"},
        )

        engine.record_decision(result)

        assert engine.stats["total_decisions"] == 1
        assert engine.stats["bot_decisions"] == 1

    def test_record_outcome(self):
        """Test recording decision outcome"""
        engine = EscalationEngine()

        result = DecisionResult(
            decision_id="test_002",
            source=DecisionSource.BOT,
            action="Test action",
            confidence=0.8,
            time_taken_ms=10.0,
            metadata={"character_id": "test_char"},
        )

        engine.record_decision(result)
        engine.record_outcome("test_002", success=True)

        assert result.success is True

    def test_threshold_adjustment_on_success(self):
        """Test that successful outcomes lower thresholds"""
        engine = EscalationEngine()
        char_id = "test_char"

        initial_threshold = engine.get_thresholds(char_id).bot_min_confidence

        result = DecisionResult(
            decision_id="test_003",
            source=DecisionSource.BOT,
            action="Test action",
            confidence=0.8,
            time_taken_ms=10.0,
            metadata={"character_id": char_id},
        )

        engine.record_decision(result)
        engine.record_outcome("test_003", success=True)

        new_threshold = engine.get_thresholds(char_id).bot_min_confidence
        assert new_threshold < initial_threshold

    def test_threshold_adjustment_on_failure(self):
        """Test that failed outcomes raise thresholds"""
        engine = EscalationEngine()
        char_id = "test_char"

        initial_threshold = engine.get_thresholds(char_id).bot_min_confidence

        result = DecisionResult(
            decision_id="test_004",
            source=DecisionSource.BOT,
            action="Test action",
            confidence=0.8,
            time_taken_ms=10.0,
            metadata={"character_id": char_id},
        )

        engine.record_decision(result)
        engine.record_outcome("test_004", success=False)

        new_threshold = engine.get_thresholds(char_id).bot_min_confidence
        assert new_threshold > initial_threshold

    def test_character_stats(self):
        """Test getting character statistics"""
        engine = EscalationEngine()
        char_id = "test_char"

        # Record some decisions
        for i in range(5):
            result = DecisionResult(
                decision_id=f"test_{i}",
                source=DecisionSource.BOT,
                action=f"Action {i}",
                confidence=0.8,
                time_taken_ms=10.0,
                metadata={"character_id": char_id},
            )
            engine.record_decision(result)

        stats = engine.get_character_stats(char_id)
        assert stats["total_decisions"] == 5
        assert stats["bot_decisions"] == 5

    def test_custom_thresholds(self):
        """Test setting custom thresholds for a character"""
        engine = EscalationEngine()
        char_id = "test_char"

        custom_thresholds = EscalationThresholds(
            bot_min_confidence=0.5,
            brain_min_confidence=0.3,
            high_stakes_threshold=0.8,
        )

        engine.set_thresholds(char_id, custom_thresholds)

        retrieved = engine.get_thresholds(char_id)
        assert retrieved.bot_min_confidence == 0.5
        assert retrieved.brain_min_confidence == 0.3
        assert retrieved.high_stakes_threshold == 0.8

    def test_should_escalate_low_confidence(self):
        """Test escalation check for low confidence"""
        engine = EscalationEngine()

        context = DecisionContext(
            character_id="test_char",
            situation_type="test",
            situation_description="Test situation",
            stakes=0.5,
        )

        result = DecisionResult(
            decision_id="test_005",
            source=DecisionSource.BOT,
            action="Test action",
            confidence=0.5,  # Low confidence
            time_taken_ms=10.0,
        )

        should_esc, reason = engine.should_escalate(result, context)
        assert should_esc is True
        assert reason == EscalationReason.LOW_CONFIDENCE

    def test_should_not_escalate_human(self):
        """Test that human decisions don't escalate further"""
        engine = EscalationEngine()

        context = DecisionContext(
            character_id="test_char",
            situation_type="test",
            situation_description="Test situation",
            stakes=0.5,
        )

        result = DecisionResult(
            decision_id="test_006",
            source=DecisionSource.HUMAN,
            action="Test action",
            confidence=0.3,  # Even low confidence
            time_taken_ms=100.0,
        )

        should_esc, reason = engine.should_escalate(result, context)
        assert should_esc is False
        assert reason is None


class TestDecisionContext:
    """Tests for DecisionContext"""

    def test_decision_context_creation(self):
        """Test creating a decision context"""
        context = DecisionContext(
            character_id="char_1",
            situation_type="combat",
            situation_description="Goblin attack",
        )

        assert context.character_id == "char_1"
        assert context.situation_type == "combat"
        assert context.situation_description == "Goblin attack"
        assert context.stakes == 0.5  # Default
        assert context.character_hp_ratio == 1.0  # Default


class TestEscalationThresholds:
    """Tests for EscalationThresholds"""

    def test_default_thresholds(self):
        """Test default threshold values"""
        thresholds = EscalationThresholds()

        assert thresholds.bot_min_confidence == 0.7
        assert thresholds.brain_min_confidence == 0.5
        assert thresholds.high_stakes_threshold == 0.7
        assert thresholds.critical_stakes_threshold == 0.9
