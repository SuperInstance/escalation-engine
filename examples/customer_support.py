"""
Customer Support Automation Example

Demonstrates using Escalation Engine for a customer support system
that intelligently routes inquiries to reduce LLM costs.
"""

import asyncio
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    create_provider,
)
from escalation_engine.config import LLMProviderConfig


# Custom bot handlers for common support scenarios
def handle_password_reset(context):
    """Handle password reset - fully automated"""
    return {
        "action": "Send password reset email with security verification",
        "confidence": 0.95,
        "metadata": {"category": "account", "automated": True}
    }


def handle_refund_request(context):
    """Handle refund request - check amount first"""
    # Extract amount from custom_data if available
    amount = context.custom_data.get("refund_amount", 0)

    if amount < 50:
        return {
            "action": "Auto-approve refund under $50",
            "confidence": 0.9,
            "metadata": {"category": "billing", "auto_approved": True}
        }
    else:
        return {
            "action": "Flag for manual review - amount exceeds threshold",
            "confidence": 0.7,
            "metadata": {"category": "billing", "requires_review": True}
        }


def handle_faq(context):
    """Handle FAQ with knowledge base lookup"""
    keywords = context.situation_description.lower()

    if "shipping" in keywords:
        return {
            "action": "Provide shipping policy information",
            "confidence": 0.9,
        }
    elif "return" in keywords:
        return {
            "action": "Provide return policy information",
            "confidence": 0.9,
        }
    else:
        return {
            "action": "Search knowledge base for relevant articles",
            "confidence": 0.75,
        }


async def process_inquiry(engine: EscalationEngine, inquiry: dict) -> dict:
    """
    Process a customer inquiry through the escalation engine

    Args:
        engine: EscalationEngine instance
        inquiry: Dictionary with inquiry details

    Returns:
        Response dictionary with action and metadata
    """

    # Create decision context
    context = DecisionContext(
        character_id=inquiry["customer_id"],
        situation_type=inquiry["category"],
        situation_description=inquiry["message"],
        stakes=inquiry.get("stakes", 0.5),
        urgency_ms=inquiry.get("urgency_ms", 5000),
        custom_data=inquiry.get("custom_data", {}),
    )

    # Route the decision
    decision = engine.route_decision(context)

    # Execute based on source
    if decision.source == DecisionSource.BOT:
        # Use rule-based handler
        handler = None
        if context.situation_type == "password_reset":
            handler = handle_password_reset
        elif context.situation_type == "refund":
            handler = handle_refund_request
        elif context.situation_type == "faq":
            handler = handle_faq

        if handler:
            result = handler(context)
        else:
            result = {
                "action": "Provide standard response template",
                "confidence": 0.7,
            }

        response = {
            "action": result["action"],
            "confidence": result["confidence"],
            "source": "bot",
            "cost": 0.0,
            "metadata": result.get("metadata", {}),
        }

    elif decision.source == DecisionSource.BRAIN:
        # Use local LLM (simulated here)
        response = {
            "action": f"Draft personalized response: '{context.situation_description[:50]}...'",
            "confidence": 0.8,
            "source": "brain",
            "cost": 0.001,
        }

    else:  # HUMAN
        # Escalate to human agent (or use API LLM)
        response = {
            "action": "Escalate to senior agent for review",
            "confidence": 0.95,
            "source": "human",
            "cost": 0.02,
            "escalation_reason": decision.reason.value if decision.reason else None,
        }

    # Record the decision
    result = DecisionResult(
        decision_id=inquiry.get("inquiry_id", "unknown"),
        source=decision.source,
        action=response["action"],
        confidence=response["confidence"],
        time_taken_ms=10.0,
        cost_estimate=response["cost"],
        metadata={"category": context.situation_type},
    )

    engine.record_decision(result)

    return response


async def main():
    """Run customer support demo"""

    print("=" * 70)
    print("Customer Support Automation - Escalation Engine Demo")
    print("=" * 70)
    print()

    # Initialize engine
    engine = EscalationEngine()

    # Sample inquiries
    inquiries = [
        {
            "inquiry_id": "INC-001",
            "customer_id": "cust_12345",
            "category": "password_reset",
            "message": "I can't log into my account, forgot password",
            "stakes": 0.3,
            "urgency_ms": 2000,
            "custom_data": {"attempts": 3},
        },
        {
            "inquiry_id": "INC-002",
            "customer_id": "cust_67890",
            "category": "refund",
            "message": "I'd like a refund for my recent purchase",
            "stakes": 0.6,
            "custom_data": {"refund_amount": 25},
        },
        {
            "inquiry_id": "INC-003",
            "customer_id": "cust_11111",
            "category": "refund",
            "message": "Requesting full refund for enterprise subscription",
            "stakes": 0.9,
            "custom_data": {"refund_amount": 5000},
        },
        {
            "inquiry_id": "INC-004",
            "customer_id": "cust_22222",
            "category": "technical_issue",
            "message": "System crashed after recent update, losing production data",
            "stakes": 0.95,
            "urgency_ms": 100,
        },
        {
            "inquiry_id": "INC-005",
            "customer_id": "cust_33333",
            "category": "faq",
            "message": "What are your shipping options?",
            "stakes": 0.1,
        },
    ]

    total_cost = 0.0

    for inquiry in inquiries:
        print(f"Inquiry: {inquiry['inquiry_id']}")
        print(f"  Category: {inquiry['category']}")
        print(f"  Message: {inquiry['message'][:60]}{'...' if len(inquiry['message']) > 60 else ''}")

        response = await process_inquiry(engine, inquiry)

        print(f"  Routed to: {response['source'].upper()}")
        print(f"  Action: {response['action'][:60]}{'...' if len(response['action']) > 60 else ''}")
        print(f"  Cost: ${response['cost']:.4f}")
        print()

        total_cost += response["cost"]

    # Show statistics
    print("-" * 70)
    print("Summary Statistics")
    print("-" * 70)

    stats = engine.get_global_stats()

    print(f"Total inquiries: {stats['total_decisions']}")
    print(f"  Bot handled: {stats['bot_decisions']} (${0:.2f})")
    print(f"  Brain handled: {stats['brain_decisions']} (${stats['brain_decisions'] * 0.001:.2f})")
    print(f"  Human handled: {stats['human_decisions']} (${stats['human_decisions'] * 0.02:.2f})")
    print(f"Total cost: ${total_cost:.4f}")
    print()

    # Show cost savings
    baseline_cost = stats['total_decisions'] * 0.02  # All human
    savings = baseline_cost - total_cost
    reduction = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

    print(f"Baseline cost (all human): ${baseline_cost:.2f}")
    print(f"Actual cost (with routing): ${total_cost:.2f}")
    print(f"Savings: ${savings:.2f} ({reduction:.0f}% reduction)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
