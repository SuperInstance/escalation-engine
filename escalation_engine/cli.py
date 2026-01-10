"""
Command-line interface for Escalation Engine
"""

import argparse
import sys
import logging
from pathlib import Path

from .core import EscalationEngine, DecisionContext
from .config import load_config, save_config, Config
from .server import run_server

logger = logging.getLogger(__name__)


def cmd_route(args) -> int:
    """Route a decision from command line"""
    engine = EscalationEngine()

    context = DecisionContext(
        character_id=args.character_id,
        situation_type=args.situation_type,
        situation_description=args.description,
        stakes=args.stakes,
        urgency_ms=args.urgency,
        character_hp_ratio=args.hp_ratio,
    )

    decision = engine.route_decision(context)

    print(f"Source: {decision.source.value}")
    print(f"Reason: {decision.reason.value if decision.reason else 'N/A'}")
    print(f"Confidence Required: {decision.confidence_required}")
    print(f"Allow Fallback: {decision.allow_fallback}")

    return 0


def cmd_server(args) -> int:
    """Start the API server"""
    print(f"Starting Escalation Engine server on {args.host}:{args.port}")
    print(f"API documentation: http://{args.host}:{args.port}/docs")

    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
    )

    return 0


def cmd_config(args) -> int:
    """Generate or validate config"""
    if args.generate:
        config = Config()

        output_path = args.output or "escalation_config.yaml"
        save_config(config, output_path)
        print(f"Generated config at: {output_path}")
        return 0

    if args.validate:
        try:
            config = load_config(args.config)
            print(f"Config loaded successfully from: {args.config}")
            print(f"  - Learning enabled: {config.enable_learning}")
            print(f"  - Daily budget: ${config.cost_tracking.daily_budget}")
            print(f"  - LLM providers: {len(config.llm_providers)}")
            return 0
        except Exception as e:
            print(f"Config validation failed: {e}", file=sys.stderr)
            return 1

    return 0


def cmd_test(args) -> int:
    """Run test scenarios"""
    from .core import DecisionResult, DecisionSource

    print("Running Escalation Engine tests...\n")

    engine = EscalationEngine()

    # Pre-populate patterns so routine combat isn't flagged as novel
    engine.situation_patterns["warrior_1:combat"] = ["Goblin attacks"] * 10

    tests = [
        {
            "name": "Routine Combat",
            "context": DecisionContext(
                character_id="warrior_1",
                situation_type="combat",
                situation_description="Goblin attacks with sword",
                stakes=0.3,
                urgency_ms=1000,
                similar_decisions_count=10,
            ),
            "expected": DecisionSource.BOT,
        },
        {
            "name": "High Stakes Combat",
            "context": DecisionContext(
                character_id="warrior_1",
                situation_type="combat",
                situation_description="Dragon breathes fire at party",
                stakes=0.95,
                urgency_ms=500,
                similar_decisions_count=2,
            ),
            "expected": DecisionSource.HUMAN,
        },
        {
            "name": "Critical HP",
            "context": DecisionContext(
                character_id="warrior_1",
                situation_type="combat",
                situation_description="Enemy attacks while near death",
                stakes=0.5,
                character_hp_ratio=0.1,
            ),
            "expected": DecisionSource.HUMAN,
        },
        {
            "name": "Novel Social",
            "context": DecisionContext(
                character_id="bard_1",
                situation_type="social",
                situation_description="Queen asks about your political allegiance",
                stakes=0.7,
                similar_decisions_count=0,
            ),
            "expected": DecisionSource.BRAIN,
        },
    ]

    passed = 0
    failed = 0

    for test in tests:
        decision = engine.route_decision(test["context"])
        expected = test["expected"]

        status = "PASS" if decision.source == expected else "FAIL"
        if decision.source == expected:
            passed += 1
        else:
            failed += 1

        print(f"[{status}] {test['name']}")
        print(f"  Expected: {expected.value}, Got: {decision.source.value}")
        print(f"  Reason: {decision.reason.value if decision.reason else 'N/A'}")
        print()

    print(f"Results: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


def main() -> int:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="escalation-engine",
        description="Escalation Engine - Intelligent decision routing",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Route command
    route_parser = subparsers.add_parser("route", help="Route a decision")
    route_parser.add_argument("--character-id", required=True, help="Character/entity ID")
    route_parser.add_argument("--situation-type", required=True, help="Type of situation")
    route_parser.add_argument("--description", required=True, help="Situation description")
    route_parser.add_argument("--stakes", type=float, default=0.5, help="Stakes level (0-1)")
    route_parser.add_argument("--urgency", type=int, help="Urgency in milliseconds")
    route_parser.add_argument("--hp-ratio", type=float, default=1.0, help="HP ratio (0-1)")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start API server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--generate", action="store_true", help="Generate default config")
    config_parser.add_argument("--validate", action="store_true", help="Validate config file")
    config_parser.add_argument("--config", help="Config file path")
    config_parser.add_argument("--output", "-o", help="Output path for generated config")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run test scenarios")

    args = parser.parse_args()

    # Set up logging
    log_level = logging.WARNING
    if args.verbose >= 2:
        log_level = logging.DEBUG
    elif args.verbose == 1:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    # Execute command
    if args.command == "route":
        return cmd_route(args)
    elif args.command == "server":
        return cmd_server(args)
    elif args.command == "config":
        return cmd_config(args)
    elif args.command == "test":
        return cmd_test(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
