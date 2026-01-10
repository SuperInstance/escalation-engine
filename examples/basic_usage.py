"""
Basic Usage Example for Escalation Engine

This example demonstrates the core functionality of routing decisions
through Bot, Brain, and Human tiers.
"""

from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
)


def main():
    # Initialize the engine
    engine = EscalationEngine()

    print("=" * 60)
    print("Escalation Engine - Basic Usage Example")
    print("=" * 60)
    print()

    # Example 1: Routine decision -> Bot
    print("Example 1: Routine Decision (Expected: BOT)")
    print("-" * 40)

    context1 = DecisionContext(
        character_id="user_123",
        situation_type="faq",
        situation_description="Customer asks about password reset",
        stakes=0.2,  # Low stakes
        urgency_ms=2000,
        similar_decisions_count=100,  # Seen many times
    )

    decision1 = engine.route_decision(context1)
    print(f"  Situation: {context1.situation_description}")
    print(f"  Route to: {decision1.source.value}")
    print(f"  Reason: {decision1.reason}")
    print(f"  Confidence required: {decision1.confidence_required}")
    print()

    # Example 2: Novel situation -> Brain
    print("Example 2: Novel Situation (Expected: BRAIN)")
    print("-" * 40)

    context2 = DecisionContext(
        character_id="user_456",
        situation_type="support",
        situation_description="Customer reports unusual integration error with legacy system",
        stakes=0.6,  # Medium stakes
        urgency_ms=5000,
        similar_decisions_count=0,  # Never seen before
    )

    decision2 = engine.route_decision(context2)
    print(f"  Situation: {context2.situation_description}")
    print(f"  Route to: {decision2.source.value}")
    print(f"  Reason: {decision2.reason}")
    print(f"  Confidence required: {decision2.confidence_required}")
    print()

    # Example 3: Critical situation -> Human
    print("Example 3: Critical Situation (Expected: HUMAN)")
    print("-" * 40)

    context3 = DecisionContext(
        character_id="user_789",
        situation_type="security",
        situation_description="Customer reports unauthorized account access",
        stakes=0.95,  # Very high stakes
        urgency_ms=100,  # Time critical
    )

    decision3 = engine.route_decision(context3)
    print(f"  Situation: {context3.situation_description}")
    print(f"  Route to: {decision3.source.value}")
    print(f"  Reason: {decision3.reason}")
    print(f"  Confidence required: {decision3.confidence_required}")
    print()

    # Example 4: Recording decisions and outcomes
    print("Example 4: Recording Decisions and Learning")
    print("-" * 40)

    # Simulate a bot decision
    result = DecisionResult(
        decision_id="dec_001",
        source=DecisionSource.BOT,
        action="Provided password reset instructions",
        confidence=0.85,
        time_taken_ms=5.0,
        cost_estimate=0.0,
        metadata={"character_id": "user_123"},
    )

    engine.record_decision(result)
    print(f"  Recorded decision: {result.decision_id}")

    # Record the outcome
    engine.record_outcome("dec_001", success=True)
    print(f"  Recorded outcome: success=True")

    # Check updated stats
    stats = engine.get_global_stats()
    print(f"  Total decisions: {stats['total_decisions']}")
    print(f"  Bot decisions: {stats['bot_decisions']}")
    print()

    # Example 5: Character-specific stats
    print("Example 5: Character Statistics")
    print("-" * 40)

    char_stats = engine.get_character_stats("user_123")
    print(f"  Character: user_123")
    print(f"  Total decisions: {char_stats['total_decisions']}")
    print(f"  Success rate: {char_stats['success_rate']:.1%}")
    print()


if __name__ == "__main__":
    main()
