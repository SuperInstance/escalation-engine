"""
Learning System Example

Demonstrates the adaptive learning capabilities of the Escalation Engine,
where thresholds adjust based on decision outcomes.
"""

from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationThresholds,
)


def print_thresholds(engine: EscalationEngine, character_id: str):
    """Print current thresholds for a character"""
    thresholds = engine.get_thresholds(character_id)
    print(f"  Bot min confidence:    {thresholds.bot_min_confidence:.3f}")
    print(f"  Brain min confidence:  {thresholds.brain_min_confidence:.3f}")
    print(f"  High stakes threshold: {thresholds.high_stakes_threshold:.3f}")


def simulate_learning_cycle(engine: EscalationEngine, character_id: str, iterations: int):
    """Simulate a learning cycle for a character"""

    print(f"\n{'='*70}")
    print(f"Learning Simulation: {character_id}")
    print('='*70)

    print(f"\nInitial Thresholds:")
    print_thresholds(engine, character_id)

    decisions_made = 0

    for i in range(iterations):
        print(f"\n--- Iteration {i+1} ---")

        # Create a context
        context = DecisionContext(
            character_id=character_id,
            situation_type="test_situation",
            situation_description=f"Test situation {i+1}",
            stakes=0.5,
        )

        # Route decision
        decision = engine.route_decision(context)

        # Simulate a decision result
        # For this demo, we'll simulate success that improves over time
        simulated_confidence = 0.6 + (i * 0.05)  # Improving confidence

        result = DecisionResult(
            decision_id=f"{character_id}_dec_{i}",
            source=decision.source,
            action=f"Test action {i+1}",
            confidence=min(simulated_confidence, 0.95),
            time_taken_ms=50,
            cost_estimate=0.0,
            metadata={"character_id": character_id, "situation_type": "test_situation"},
        )

        engine.record_decision(result)

        # Record outcome (alternating success/failure, mostly success)
        success = i % 4 != 0  # 75% success rate
        engine.record_outcome(result.decision_id, success=success)

        print(f"  Routed to: {decision.source.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Outcome: {'SUCCESS' if success else 'FAILURE'}")

        decisions_made += 1

        # Show updated thresholds every 5 iterations
        if (i + 1) % 5 == 0:
            print(f"\n  Updated Thresholds after {i+1} decisions:")
            print_thresholds(engine, character_id)

    # Final stats
    print(f"\n{'='*70}")
    print(f"Final Statistics for {character_id}")
    print('='*70)

    stats = engine.get_character_stats(character_id)
    final_thresholds = engine.get_thresholds(character_id)

    print(f"\nDecisions: {stats['total_decisions']}")
    print(f"  Bot: {stats['bot_decisions']}")
    print(f"  Brain: {stats['brain_decisions']}")
    print(f"  Human: {stats['human_decisions']}")

    print(f"\nOutcomes:")
    print(f"  Successes: {stats['successes']}")
    print(f"  Failures: {stats['failures']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")

    print(f"\nFinal Thresholds:")
    print_thresholds(engine, character_id)

    # Calculate threshold changes
    initial_bot = 0.7  # Default
    initial_brain = 0.5  # Default
    bot_change = final_thresholds.bot_min_confidence - initial_bot
    brain_change = final_thresholds.brain_min_confidence - initial_brain

    print(f"\nThreshold Adjustments:")
    print(f"  Bot threshold: {bot_change:+.3f} ({'lowered' if bot_change < 0 else 'raised'})")
    print(f"  Brain threshold: {brain_change:+.3f} ({'lowered' if brain_change < 0 else 'raised'})")

    return stats


def compare_characters(engine: EscalationEngine):
    """Compare two characters with different learning outcomes"""

    print(f"\n{'='*70}")
    print("Character Comparison")
    print('='*70)

    # Reliable character - mostly successful decisions
    print("\nCharacter A (Reliable):")
    reliable_stats = simulate_learning_cycle(engine, "char_reliable", 20)

    # Reset for next character
    engine.decision_history.clear()
    engine.decisions_by_character.clear()

    # Struggling character - many failed decisions
    print(f"\n{'='*70}")
    print("\nCharacter B (Struggling):")

    # Set fresh thresholds
    engine.thresholds["char_struggling"] = EscalationThresholds()

    struggling_stats = simulate_learning_cycle(engine, "char_struggling", 20)

    # Compare
    print(f"\n{'='*70}")
    print("Comparison Summary")
    print('='*70)

    print(f"\n{'Metric':<25} {'Reliable':>15} {'Struggling':>15}")
    print("-" * 55)
    print(f"{'Total decisions':<25} {reliable_stats['total_decisions']:>15} {struggling_stats['total_decisions']:>15}")
    print(f"{'Bot decisions':<25} {reliable_stats['bot_decisions']:>15} {struggling_stats['bot_decisions']:>15}")
    print(f"{'Brain decisions':<25} {reliable_stats['brain_decisions']:>15} {struggling_stats['brain_decisions']:>15}")
    print(f"{'Success rate':<25} {reliable_stats['success_rate']:>14.1%} {struggling_stats['success_rate']:>14.1%}")

    reliable_thresholds = engine.get_thresholds("char_reliable")
    struggling_thresholds = engine.get_thresholds("char_struggling")

    print(f"\n{'Final Thresholds':<25} {'Reliable':>15} {'Struggling':>15}")
    print("-" * 55)
    print(f"{'Bot min confidence':<25} {reliable_thresholds.bot_min_confidence:>15.3f} {struggling_thresholds.bot_min_confidence:>15.3f}")
    print(f"{'Brain min confidence':<25} {reliable_thresholds.brain_min_confidence:>15.3f} {struggling_thresholds.brain_min_confidence:>15.3f}")

    print("\nInterpretation:")
    if reliable_thresholds.bot_min_confidence < struggling_thresholds.bot_min_confidence:
        print("  Reliable character has LOWER bot threshold (trusts bots more)")
    if struggling_thresholds.bot_min_confidence > 0.7:
        print("  Struggling character has RAISED bot threshold (more cautious)")


def main():
    """Run the learning system demo"""

    print("="*70)
    print("Learning System Demo - Escalation Engine")
    print("="*70)

    print("\nThe Escalation Engine learns from decision outcomes to adapt")
    print("thresholds for each character/entity.")
    print("\nLearning Rules:")
    print("  - Success: Lower thresholds (trust the source more)")
    print("  - Failure: Raise thresholds (trust the source less)")

    # Initialize engine
    engine = EscalationEngine()

    # Run comparison
    compare_characters(engine)

    print(f"\n{'='*70}")
    print("Key Takeaway")
    print('='*70)
    print("\nEach character develops personalized escalation thresholds")
    print("based on their unique experience and outcomes.")
    print("\nA reliable character can automate more (lower thresholds),")
    print("while a struggling one gets more human oversight (higher thresholds).")


if __name__ == "__main__":
    main()
