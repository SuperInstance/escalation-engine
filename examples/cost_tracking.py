"""
Cost Tracking Example

Demonstrates tracking costs and budget management with the Escalation Engine.
"""

import time
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
)
from escalation_engine.metrics import MetricsTracker


def simulate_day(tracker: MetricsTracker, engine: EscalationEngine, day: int):
    """Simulate a day of decisions"""

    print(f"\n{'='*70}")
    print(f"Day {day} - Processing Decisions")
    print('='*70)

    # Simulate various decisions throughout the day
    scenarios = [
        # Routine decisions (BOT)
        ("user_001", "faq", "Password reset question", 0.2, DecisionSource.BOT),
        ("user_002", "faq", "Shipping inquiry", 0.1, DecisionSource.BOT),
        ("user_003", "faq", "Account settings question", 0.1, DecisionSource.BOT),
        ("user_004", "faq", "Billing question", 0.2, DecisionSource.BOT),
        ("user_005", "faq", "Product availability", 0.1, DecisionSource.BOT),
        # Medium complexity (BRAIN)
        ("user_006", "support", "Integration help needed", 0.6, DecisionSource.BRAIN),
        ("user_007", "support", "API usage clarification", 0.5, DecisionSource.BRAIN),
        ("user_008", "support", "Feature explanation request", 0.6, DecisionSource.BRAIN),
        # High stakes (HUMAN)
        ("user_009", "security", "Reported unauthorized access", 0.95, DecisionSource.HUMAN),
        ("user_010", "billing", "Enterprise contract cancellation request", 0.9, DecisionSource.HUMAN),
    ]

    total_cost = 0.0

    for char_id, sit_type, desc, stakes, expected_source in scenarios:
        # Create context
        context = DecisionContext(
            character_id=char_id,
            situation_type=sit_type,
            situation_description=desc,
            stakes=stakes,
        )

        # Route decision
        decision = engine.route_decision(context)

        # Simulate execution
        time.sleep(0.01)  # Simulate processing time

        # Calculate cost
        cost = get_source_cost(decision.source)
        total_cost += cost

        # Record result
        result = DecisionResult(
            decision_id=f"{char_id}_{int(time.time())}",
            source=decision.source,
            action=f"Handle {sit_type} request",
            confidence=0.8,
            time_taken_ms=50,
            cost_estimate=cost,
            metadata={"situation_type": sit_type},
        )

        engine.record_decision(result)
        tracker.track_decision(result, char_id)

        # Print decision
        symbol = get_source_symbol(decision.source)
        print(f"{symbol} {desc:40s} -> {decision.source.value:6s} (${cost:.4f})")

    # Print summary
    cost_summary = tracker.cost_tracker.get_cost_summary()

    print(f"\nDay {day} Summary:")
    print(f"  Total decisions: {len(scenarios)}")
    print(f"  Daily cost: ${cost_summary['daily_cost']:.4f}")
    print(f"  Budget used: {cost_summary['budget_used_ratio']:.1%}")
    print(f"  Remaining budget: ${cost_summary['remaining_budget']:.4f}")

    if cost_summary['daily_cost'] > cost_summary['alert_threshold']:
        print(f"  WARNING: Exceeded alert threshold of ${cost_summary['alert_threshold']:.2f}!")


def get_source_cost(source: DecisionSource) -> float:
    """Get cost per decision for a source"""
    costs = {
        DecisionSource.BOT: 0.0,
        DecisionSource.BRAIN: 0.001,
        DecisionSource.HUMAN: 0.02,
    }
    return costs.get(source, 0.0)


def get_source_symbol(source: DecisionSource) -> str:
    """Get a visual symbol for the source"""
    symbols = {
        DecisionSource.BOT: "[BOT]",
        DecisionSource.BRAIN: "[BRAIN]",
        DecisionSource.HUMAN: "[HUMAN]",
    }
    return symbols.get(source, "[???]")


def main():
    """Run cost tracking demo"""

    print("="*70)
    print("Cost Tracking Demo - Escalation Engine")
    print("="*70)

    # Initialize with daily budget
    daily_budget = 5.0  # $5 per day

    print(f"\nConfiguration:")
    print(f"  Daily budget: ${daily_budget:.2f}")
    print(f"  Alert threshold: ${daily_budget * 0.8:.2f} (80%)")
    print(f"\nCost per decision:")
    print(f"  BOT:     $0.0000 (rules-based)")
    print(f"  BRAIN:   $0.0010 (local LLM)")
    print(f"  HUMAN:   $0.0200 (API LLM)")

    # Initialize
    engine = EscalationEngine()
    tracker = MetricsTracker(daily_budget=daily_budget)

    # Simulate 3 days
    for day in range(1, 4):
        simulate_day(tracker, engine, day)

        # Reset daily cost at start of new day
        if day < 3:
            tracker.cost_tracker.reset_daily()

    # Final summary
    print(f"\n{'='*70}")
    print("Final Summary - 3 Day Period")
    print('='*70)

    summary = tracker.get_summary()

    print(f"\nCost Breakdown:")
    cost_by_source = summary['cost']['cost_by_source']
    for source, cost in cost_by_source.items():
        pct = (cost / summary['cost']['total_cost'] * 100) if summary['cost']['total_cost'] > 0 else 0
        print(f"  {source.upper():8s}: ${cost:.4f} ({pct:.1f}%)")

    print(f"\nPerformance:")
    perf = summary['performance']
    print(f"  Total decisions: {perf['total_decisions']}")
    print(f"  Avg confidence: {perf['avg_confidence']:.2f}")
    print(f"  Avg time: {perf['avg_time_ms']:.1f}ms")
    print(f"  Success rate: {perf['success_rate']:.1%}")

    print(f"\nSituation Patterns:")
    for situation, sources in summary['situation_patterns'].items():
        total = sum(sources.values())
        print(f"  {situation:15s}: {total} decisions")
        for source, count in sources.items():
            print(f"    {source}: {count}")

    print(f"\nCost Comparison:")
    total_decisions = perf['total_decisions']
    baseline_cost = total_decisions * 0.02  # All decisions to HUMAN
    actual_cost = summary['cost']['total_cost']
    savings = baseline_cost - actual_cost
    reduction = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

    print(f"  Baseline (all HUMAN):  ${baseline_cost:.2f}")
    print(f"  Actual (with routing): ${actual_cost:.2f}")
    print(f"  Savings:               ${savings:.2f} ({reduction:.0f}% reduction)")
    print(f"  ROI:                   {reduction:.0f}x")


if __name__ == "__main__":
    main()
