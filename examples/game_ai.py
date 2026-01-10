"""
Game AI Example - D&D Character Decision Making

Demonstrates using Escalation Engine for game AI decisions,
where characters need to balance speed, intelligence, and drama.
"""

from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationThresholds,
)


class DnDCharacter:
    """Represents a D&D character with AI decision making"""

    def __init__(self, name, character_class, engine: EscalationEngine):
        self.name = name
        self.character_class = character_class
        self.engine = engine
        self.hp = 100
        self.max_hp = 100
        self.level = 1
        self.spell_slots = 3
        self.gold = 50

        # Class-specific thresholds
        self._setup_thresholds()

    def _setup_thresholds(self):
        """Set up character-specific escalation thresholds"""

        if self.character_class == "Fighter":
            # Fighters are confident in combat, use bot more
            self.engine.set_thresholds(
                self.name,
                EscalationThresholds(
                    bot_min_confidence=0.6,  # Lower threshold, more bot usage
                    brain_min_confidence=0.4,
                    high_stakes_threshold=0.8,  # Higher threshold for high stakes
                )
            )
        elif self.character_class == "Wizard":
            # Wizards are more cautious, escalate earlier
            self.engine.set_thresholds(
                self.name,
                EscalationThresholds(
                    bot_min_confidence=0.8,  # Higher threshold, more brain/human
                    brain_min_confidence=0.6,
                    high_stakes_threshold=0.6,  # Lower threshold, escalate sooner
                )
            )
        elif self.character_class == "Bard":
            # Bards are creative, prefer brain (personality-driven)
            self.engine.set_thresholds(
                self.name,
                EscalationThresholds(
                    bot_min_confidence=0.9,  # Very high threshold, avoid bot
                    brain_min_confidence=0.5,
                    high_stakes_threshold=0.7,
                )
            )

    @property
    def hp_ratio(self):
        return self.hp / self.max_hp

    def make_decision(self, situation_type, description, stakes=0.5, urgency_ms=None):
        """Make a decision based on the situation"""

        context = DecisionContext(
            character_id=self.name,
            situation_type=situation_type,
            situation_description=description,
            stakes=stakes,
            urgency_ms=urgency_ms,
            character_hp_ratio=self.hp_ratio,
            available_resources={
                "spell_slots": self.spell_slots,
                "gold": self.gold,
            },
        )

        decision = self.engine.route_decision(context)

        return decision

    def take_damage(self, amount):
        """Take damage"""
        self.hp = max(0, self.hp - amount)
        print(f"  {self.name} takes {amount} damage! HP: {self.hp}/{self.max_hp}")

    def cast_spell(self):
        """Cast a spell"""
        if self.spell_slots > 0:
            self.spell_slots -= 1
            return True
        return False


def simulate_combat():
    """Simulate a D&D combat encounter"""

    print("=" * 70)
    print("D&D Combat Simulation - Escalation Engine Demo")
    print("=" * 70)
    print()

    # Create engine
    engine = EscalationEngine()

    # Create party
    fighter = DnDCharacter("Thorin", "Fighter", engine)
    wizard = DnDCharacter("Elara", "Wizard", engine)
    bard = DnDCharacter("Felix", "Bard", engine)

    party = [fighter, wizard, bard]

    print("Adventuring Party:")
    for char in party:
        print(f"  {char.name} the {char.character_class}")
    print()

    # Combat encounter
    print("Encounter: A goblin raiding party appears!")
    print("-" * 70)

    # Round 1: Routine combat
    print("\nRound 1: Routine goblin combat")
    print()

    for char in party:
        decision = char.make_decision(
            situation_type="combat",
            description="Goblin with rusty sword attacks",
            stakes=0.3,
            urgency_ms=2000,
        )

        print(f"{char.name} ({char.character_class}):")
        print(f"  Decision source: {decision.source.value}")
        print(f"  Action: {get_action_description(decision)}")

        # Record result
        result = DecisionResult(
            decision_id=f"{char.name}_round1",
            source=decision.source,
            action="Attack",
            confidence=0.8,
            time_taken_ms=50,
            cost_estimate=get_cost(decision.source),
            metadata={"character_id": char.name},
        )
        engine.record_decision(result)

    # Round 2: Critical situation!
    print("\nRound 2: A goblin boss appears and casts fireball!")
    print("-" * 70)

    # Wizard takes heavy damage
    wizard.take_damage(75)

    for char in party:
        # High stakes, time critical
        decision = char.make_decision(
            situation_type="combat",
            description="Goblin boss casts powerful fireball at party",
            stakes=0.9,
            urgency_ms=100,
        )

        print(f"{char.name} ({char.character_class}, HP: {char.hp}/{char.max_hp}):")
        print(f"  Decision source: {decision.source.value}")
        print(f"  Reason: {decision.reason.value if decision.reason else 'N/A'}")
        print(f"  Action: {get_action_description(decision)}")

        # Record result
        result = DecisionResult(
            decision_id=f"{char.name}_round2",
            source=decision.source,
            action="Defensive maneuver",
            confidence=0.7,
            time_taken_ms=200,
            cost_estimate=get_cost(decision.source),
            metadata={"character_id": char.name},
        )
        engine.record_decision(result)

    # Social encounter
    print("\nSocial Encounter: The captured goblin wants to negotiate")
    print("-" * 70)

    for char in party:
        # Bard handles social
        if char == bard:
            decision = char.make_decision(
                situation_type="social",
                description="Goblin offers information about the dragon in exchange for freedom",
                stakes=0.7,
            )

            print(f"{char.name} ({char.character_class}):")
            print(f"  Decision source: {decision.source.value}")
            print(f"  Action: {get_action_description(decision)}")

            result = DecisionResult(
                decision_id=f"{char.name}_social",
                source=decision.source,
                action="Negotiate",
                confidence=0.75,
                time_taken_ms=500,
                cost_estimate=get_cost(decision.source),
                metadata={"character_id": char.name},
            )
            engine.record_decision(result)

    # Show statistics
    print("\n" + "=" * 70)
    print("Adventure Statistics")
    print("=" * 70)

    global_stats = engine.get_global_stats()
    print(f"\nTotal decisions: {global_stats['total_decisions']}")
    print(f"  Bot (Rules):     {global_stats['bot_decisions']:2d} - Fast, mechanical")
    print(f"  Brain (Local LLM): {global_stats['brain_decisions']:2d} - Smart, nuanced")
    print(f"  Human (API LLM):  {global_stats['human_decisions']:2d} - Critical, creative")
    print(f"\nEscalations: {global_stats['escalations']}")
    print(f"Total cost estimate: ${global_stats['total_cost']:.4f}")

    print("\nCharacter Breakdown:")
    for char in party:
        char_stats = engine.get_character_stats(char.name)
        print(f"\n{char.name} ({char.character_class}):")
        print(f"  Decisions: {char_stats['total_decisions']}")
        print(f"  Bot: {char_stats['bot_decisions']}, Brain: {char_stats['brain_decisions']}, Human: {char_stats['human_decisions']}")


def get_action_description(decision):
    """Get a narrative description of the action based on decision source"""

    actions = {
        DecisionSource.BOT: [
            "Attacks with practiced precision",
            "Follows established combat pattern",
            "Executes standard maneuver",
            "Uses class ability",
        ],
        DecisionSource.BRAIN: [
            "Assesses the situation and responds thoughtfully",
            "Adapts strategy based on context",
            "Makes a tactical decision",
            "Weighes options carefully",
        ],
        DecisionSource.HUMAN: [
            "Rises to the occasion with exceptional insight",
            "Makes a dramatic, story-defining choice",
            "Acts with remarkable creativity",
            "Delivers a memorable moment",
        ],
    }

    import random
    return random.choice(actions.get(decision.source, ["Takes action"]))


def get_cost(source):
    """Get cost estimate for a decision source"""

    costs = {
        DecisionSource.BOT: 0.0,
        DecisionSource.BRAIN: 0.001,
        DecisionSource.HUMAN: 0.02,
    }
    return costs.get(source, 0.0)


if __name__ == "__main__":
    simulate_combat()
