"""
Core Escalation Engine implementation

Provides intelligent decision routing through three tiers:
- Bot (fast, deterministic, free)
- Brain (local LLM, personality-driven)
- Human (API LLM, critical decisions)
"""

import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DecisionSource(Enum):
    """Where the decision came from"""
    BOT = "bot"
    BRAIN = "brain"
    HUMAN = "human"
    OVERRIDE = "override"


class EscalationReason(Enum):
    """Why a decision was escalated"""
    LOW_CONFIDENCE = "low_confidence"
    HIGH_STAKES = "high_stakes"
    NOVEL_SITUATION = "novel_situation"
    TIME_CRITICAL = "time_critical"
    CONFLICTING_BOTS = "conflicting_bots"
    SAFETY_CONCERN = "safety_concern"
    CHARACTER_GROWTH = "character_growth"
    PLAYER_REQUEST = "player_request"
    COST_LIMIT = "cost_limit"


@dataclass
class EscalationThresholds:
    """Thresholds for escalation decisions"""
    # Confidence thresholds
    bot_min_confidence: float = 0.7        # Below this, escalate to brain
    brain_min_confidence: float = 0.5      # Below this, escalate to human

    # Stakes thresholds
    high_stakes_threshold: float = 0.7     # Above this = high stakes
    critical_stakes_threshold: float = 0.9 # Above this = critical

    # Urgency thresholds
    urgent_time_ms: int = 500             # Less than this = urgent
    critical_time_ms: int = 100           # Less than this = critical

    # Novelty detection
    novelty_threshold: float = 0.6        # Above this = novel situation

    # Safety margins
    hp_critical_threshold: float = 0.2    # Below this HP = critical
    resource_critical_threshold: float = 0.15  # Below this resources = critical

    # Learning settings
    confidence_boost_per_success: float = 0.05  # Increase confidence on success
    confidence_penalty_per_failure: float = 0.1  # Decrease on failure


@dataclass
class DecisionContext:
    """Context for a decision that needs routing"""
    # Core context
    character_id: str
    situation_type: str  # e.g., "combat", "social", "support", "planning"
    situation_description: str

    # Importance
    stakes: float = 0.5              # 0=trivial, 1=life-or-death
    urgency_ms: Optional[int] = None # Time available for decision

    # State
    character_hp_ratio: float = 1.0
    available_resources: Dict[str, int] = field(default_factory=dict)

    # History
    similar_decisions_count: int = 0  # How many times seen similar
    recent_failures: int = 0          # Recent failed decisions

    # Metadata
    timestamp: float = field(default_factory=time.time)
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationDecision:
    """Result of escalation routing"""
    source: DecisionSource
    reason: Optional[EscalationReason] = None
    confidence_required: float = 0.0
    time_budget_ms: Optional[int] = None
    allow_fallback: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "source": self.source.value,
            "reason": self.reason.value if self.reason else None,
            "confidence_required": self.confidence_required,
            "time_budget_ms": self.time_budget_ms,
            "allow_fallback": self.allow_fallback,
            "metadata": self.metadata,
        }


@dataclass
class DecisionResult:
    """Result of a routed decision"""
    decision_id: str
    source: DecisionSource
    action: str
    confidence: float
    time_taken_ms: float
    escalated_from: Optional[DecisionSource] = None
    escalation_reason: Optional[EscalationReason] = None
    success: Optional[bool] = None  # Set after outcome known
    metadata: Dict[str, Any] = field(default_factory=dict)
    cost_estimate: float = 0.0  # Estimated cost in USD

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "decision_id": self.decision_id,
            "source": self.source.value,
            "action": self.action,
            "confidence": self.confidence,
            "time_taken_ms": self.time_taken_ms,
            "escalated_from": self.escalated_from.value if self.escalated_from else None,
            "escalation_reason": self.escalation_reason.value if self.escalation_reason else None,
            "success": self.success,
            "metadata": self.metadata,
            "cost_estimate": self.cost_estimate,
        }


class EscalationEngine:
    """
    Escalation engine for intelligent decision routing

    Routes decisions through the optimal path:
    1. Try bot if appropriate
    2. Escalate to brain if bot uncertain
    3. Escalate to human if brain uncertain or critical
    4. Learn from outcomes to improve routing
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        enable_learning: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize escalation engine"""
        # Configuration
        self.config = config or {}
        self.enable_learning = enable_learning

        # Character-specific thresholds
        self.thresholds: Dict[str, EscalationThresholds] = {}

        # Decision history
        self.decision_history: List[DecisionResult] = []
        self.decisions_by_character: Dict[str, List[DecisionResult]] = {}

        # Pattern recognition for novelty detection
        self.situation_patterns: Dict[str, List[str]] = {}
        self.novel_situations: List[str] = []

        # Statistics
        self.stats = {
            "total_decisions": 0,
            "bot_decisions": 0,
            "brain_decisions": 0,
            "human_decisions": 0,
            "escalations": 0,
            "escalation_rate": 0.0,
            "avg_confidence": 0.0,
            "total_cost": 0.0,
        }

        # Callbacks for extensibility
        self._bot_handler: Optional[callable] = None
        self._brain_handler: Optional[callable] = None
        self._human_handler: Optional[callable] = None

        logger.info("EscalationEngine initialized")

    def get_thresholds(self, character_id: str) -> EscalationThresholds:
        """Get thresholds for a character, creating defaults if needed"""
        if character_id not in self.thresholds:
            self.thresholds[character_id] = EscalationThresholds()
        return self.thresholds[character_id]

    def set_thresholds(
        self,
        character_id: str,
        thresholds: EscalationThresholds
    ) -> None:
        """Set custom thresholds for a character"""
        self.thresholds[character_id] = thresholds
        logger.info(f"Updated thresholds for {character_id}")

    def set_handlers(
        self,
        bot_handler: Optional[callable] = None,
        brain_handler: Optional[callable] = None,
        human_handler: Optional[callable] = None
    ) -> None:
        """Set decision handlers for each source"""
        self._bot_handler = bot_handler
        self._brain_handler = brain_handler
        self._human_handler = human_handler

    def route_decision(
        self,
        context: DecisionContext
    ) -> EscalationDecision:
        """
        Route a decision to the appropriate source

        Args:
            context: Decision context

        Returns:
            EscalationDecision with routing information
        """
        start_time = time.time()

        character_id = context.character_id
        thresholds = self.get_thresholds(character_id)

        # Check for critical overrides first
        critical_override = self._check_critical_override(context, thresholds)
        if critical_override:
            return critical_override

        # Check if situation is novel
        is_novel = self._is_novel_situation(context, thresholds)

        # Check stakes level
        is_high_stakes = context.stakes >= thresholds.high_stakes_threshold
        is_critical_stakes = context.stakes >= thresholds.critical_stakes_threshold

        # Check urgency
        is_urgent = (context.urgency_ms is not None and
                    context.urgency_ms <= thresholds.urgent_time_ms)
        is_time_critical = (context.urgency_ms is not None and
                           context.urgency_ms <= thresholds.critical_time_ms)

        # Determine routing
        decision = None

        # Critical situations -> Human
        if is_critical_stakes or is_time_critical:
            decision = EscalationDecision(
                source=DecisionSource.HUMAN,
                reason=EscalationReason.HIGH_STAKES if is_critical_stakes else EscalationReason.TIME_CRITICAL,
                confidence_required=0.9,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )

        # Novel situations with high stakes -> Brain (or Human if very high)
        elif is_novel and is_high_stakes:
            decision = EscalationDecision(
                source=DecisionSource.BRAIN if not is_critical_stakes else DecisionSource.HUMAN,
                reason=EscalationReason.NOVEL_SITUATION,
                confidence_required=thresholds.brain_min_confidence,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )

        # Novel situations with low stakes -> Brain
        elif is_novel:
            decision = EscalationDecision(
                source=DecisionSource.BRAIN,
                reason=EscalationReason.NOVEL_SITUATION,
                confidence_required=thresholds.brain_min_confidence,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )

        # High stakes but familiar -> Brain
        elif is_high_stakes:
            decision = EscalationDecision(
                source=DecisionSource.BRAIN,
                reason=EscalationReason.HIGH_STAKES,
                confidence_required=thresholds.brain_min_confidence + 0.1,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )

        # Urgent but familiar -> Bot (fast response)
        elif is_urgent:
            decision = EscalationDecision(
                source=DecisionSource.BOT,
                reason=None,
                confidence_required=thresholds.bot_min_confidence - 0.1,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )

        # Routine situation -> Bot
        else:
            decision = EscalationDecision(
                source=DecisionSource.BOT,
                reason=None,
                confidence_required=thresholds.bot_min_confidence,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )

        # Add metadata
        decision.metadata = {
            "is_novel": is_novel,
            "is_high_stakes": is_high_stakes,
            "is_critical_stakes": is_critical_stakes,
            "is_urgent": is_urgent,
            "is_time_critical": is_time_critical,
            "routing_time_ms": (time.time() - start_time) * 1000
        }

        logger.debug(
            f"Routed {character_id} decision to {decision.source.value}: "
            f"stakes={context.stakes:.2f}, novel={is_novel}, urgent={is_urgent}"
        )

        return decision

    def _check_critical_override(
        self,
        context: DecisionContext,
        thresholds: EscalationThresholds
    ) -> Optional[EscalationDecision]:
        """Check for critical situations that override normal routing"""

        # Critical HP -> Human
        if context.character_hp_ratio <= thresholds.hp_critical_threshold:
            return EscalationDecision(
                source=DecisionSource.HUMAN,
                reason=EscalationReason.SAFETY_CONCERN,
                confidence_required=0.95,
                time_budget_ms=context.urgency_ms,
                allow_fallback=False,
                metadata={"critical_hp": True}
            )

        # Critical resources -> Human
        for resource, amount in context.available_resources.items():
            if resource in ["spell_slots", "hp_potions", "resurrection", "credits", "tokens"]:
                if amount <= 1:  # Last of critical resource
                    return EscalationDecision(
                        source=DecisionSource.HUMAN,
                        reason=EscalationReason.SAFETY_CONCERN,
                        confidence_required=0.95,
                        time_budget_ms=context.urgency_ms,
                        allow_fallback=False,
                        metadata={"critical_resource": resource}
                    )

        # Recent failures -> Brain or Human
        if context.recent_failures >= 3:
            return EscalationDecision(
                source=DecisionSource.BRAIN,
                reason=EscalationReason.LOW_CONFIDENCE,
                confidence_required=0.8,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True,
                metadata={"recent_failures": context.recent_failures}
            )

        return None

    def _is_novel_situation(
        self,
        context: DecisionContext,
        thresholds: EscalationThresholds
    ) -> bool:
        """Determine if situation is novel (unseen or rare)"""

        # Check if we've seen this situation type before
        situation_key = f"{context.character_id}:{context.situation_type}"

        if situation_key not in self.situation_patterns:
            self.situation_patterns[situation_key] = []

        patterns = self.situation_patterns[situation_key]

        # If we haven't seen many similar situations, it's novel
        if len(patterns) < 5:
            return True

        # Check if description is similar to known patterns
        description_lower = context.situation_description.lower()
        description_words = set(description_lower.split())

        max_similarity = 0.0
        for pattern in patterns:
            pattern_words = set(pattern.lower().split())
            if not pattern_words:
                continue

            common_words = description_words & pattern_words
            similarity = len(common_words) / len(pattern_words)
            max_similarity = max(max_similarity, similarity)

        # If max similarity is low, situation is novel
        is_novel = max_similarity < (1.0 - thresholds.novelty_threshold)

        # Store pattern if novel
        if is_novel or len(patterns) < 20:
            patterns.append(context.situation_description[:100])

        return is_novel

    def should_escalate(
        self,
        result: DecisionResult,
        context: DecisionContext
    ) -> Tuple[bool, Optional[EscalationReason]]:
        """
        Determine if a decision should be escalated to next level

        Args:
            result: The decision that was made
            context: Original decision context

        Returns:
            (should_escalate, reason)
        """
        thresholds = self.get_thresholds(context.character_id)

        # Already from human, can't escalate further
        if result.source == DecisionSource.HUMAN:
            return False, None

        # Check confidence
        if result.source == DecisionSource.BOT:
            if result.confidence < thresholds.bot_min_confidence:
                return True, EscalationReason.LOW_CONFIDENCE
        elif result.source == DecisionSource.BRAIN:
            if result.confidence < thresholds.brain_min_confidence:
                return True, EscalationReason.LOW_CONFIDENCE

        # Check if stakes warrant escalation
        if context.stakes >= thresholds.critical_stakes_threshold:
            if result.source == DecisionSource.BOT:
                return True, EscalationReason.HIGH_STAKES

        return False, None

    def record_decision(
        self,
        result: DecisionResult
    ) -> None:
        """
        Record a decision for history and learning

        Args:
            result: Decision result to record
        """
        # Add to history
        self.decision_history.append(result)

        # Add to character history
        char_id = result.metadata.get("character_id")
        if char_id:
            if char_id not in self.decisions_by_character:
                self.decisions_by_character[char_id] = []
            self.decisions_by_character[char_id].append(result)

        # Update stats
        self.stats["total_decisions"] += 1

        if result.source == DecisionSource.BOT:
            self.stats["bot_decisions"] += 1
        elif result.source == DecisionSource.BRAIN:
            self.stats["brain_decisions"] += 1
        elif result.source == DecisionSource.HUMAN:
            self.stats["human_decisions"] += 1

        if result.escalated_from is not None:
            self.stats["escalations"] += 1

        # Update rates
        if self.stats["total_decisions"] > 0:
            self.stats["escalation_rate"] = (
                self.stats["escalations"] / self.stats["total_decisions"]
            )

        # Track cost
        self.stats["total_cost"] += result.cost_estimate

        logger.debug(f"Recorded decision from {result.source.value}")

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        outcome_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record the outcome of a decision for learning

        Args:
            decision_id: ID of the decision
            success: Whether the decision was successful
            outcome_details: Optional detailed outcome information
        """
        if not self.enable_learning:
            return

        # Find the decision
        for result in self.decision_history:
            if result.decision_id == decision_id:
                result.success = success

                # Update character thresholds based on outcome
                char_id = result.metadata.get("character_id")
                if char_id:
                    self._update_thresholds(char_id, result, success)

                logger.debug(
                    f"Recorded outcome for {decision_id}: "
                    f"{'success' if success else 'failure'}"
                )
                return

        logger.warning(f"Decision {decision_id} not found for outcome recording")

    def _update_thresholds(
        self,
        character_id: str,
        result: DecisionResult,
        success: bool
    ) -> None:
        """Update character thresholds based on decision outcome"""
        thresholds = self.get_thresholds(character_id)

        # Adjust confidence thresholds based on success
        if result.source == DecisionSource.BOT:
            if success:
                thresholds.bot_min_confidence = max(
                    0.5,
                    thresholds.bot_min_confidence - thresholds.confidence_boost_per_success
                )
            else:
                thresholds.bot_min_confidence = min(
                    0.9,
                    thresholds.bot_min_confidence + thresholds.confidence_penalty_per_failure
                )

        elif result.source == DecisionSource.BRAIN:
            if success:
                thresholds.brain_min_confidence = max(
                    0.3,
                    thresholds.brain_min_confidence - thresholds.confidence_boost_per_success
                )
            else:
                thresholds.brain_min_confidence = min(
                    0.8,
                    thresholds.brain_min_confidence + thresholds.confidence_penalty_per_failure
                )

    def get_character_stats(
        self,
        character_id: str
    ) -> Dict[str, Any]:
        """Get decision statistics for a character"""
        if character_id not in self.decisions_by_character:
            return {"total_decisions": 0}

        decisions = self.decisions_by_character[character_id]

        bot_decisions = sum(1 for d in decisions if d.source == DecisionSource.BOT)
        brain_decisions = sum(1 for d in decisions if d.source == DecisionSource.BRAIN)
        human_decisions = sum(1 for d in decisions if d.source == DecisionSource.HUMAN)
        escalations = sum(1 for d in decisions if d.escalated_from is not None)

        successes = sum(1 for d in decisions if d.success is True)
        failures = sum(1 for d in decisions if d.success is False)

        if decisions:
            avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
            avg_time = sum(d.time_taken_ms for d in decisions) / len(decisions)
            total_cost = sum(d.cost_estimate for d in decisions)
        else:
            avg_confidence = 0.0
            avg_time = 0.0
            total_cost = 0.0

        return {
            "total_decisions": len(decisions),
            "bot_decisions": bot_decisions,
            "brain_decisions": brain_decisions,
            "human_decisions": human_decisions,
            "escalations": escalations,
            "escalation_rate": escalations / len(decisions) if decisions else 0,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / (successes + failures) if (successes + failures) > 0 else 0,
            "avg_confidence": avg_confidence,
            "avg_time_ms": avg_time,
            "total_cost": total_cost,
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global decision statistics"""
        stats = self.stats.copy()

        # Add computed stats
        if stats["total_decisions"] > 0:
            stats["avg_confidence"] = (
                sum(d.confidence for d in self.decision_history) / stats["total_decisions"]
            )
            stats["avg_time_ms"] = (
                sum(d.time_taken_ms for d in self.decision_history) / stats["total_decisions"]
            )

        # Calculate cost savings (assume all human = baseline)
        if stats["total_decisions"] > 0:
            baseline_cost = stats["total_decisions"] * 0.02  # $0.02 per decision baseline
            actual_cost = stats["total_cost"]
            stats["cost_savings"] = baseline_cost - actual_cost
            stats["cost_reduction_ratio"] = baseline_cost / actual_cost if actual_cost > 0 else float('inf')

        return stats

    def reset_stats(self) -> None:
        """Reset all statistics"""
        self.stats = {
            "total_decisions": 0,
            "bot_decisions": 0,
            "brain_decisions": 0,
            "human_decisions": 0,
            "escalations": 0,
            "escalation_rate": 0.0,
            "avg_confidence": 0.0,
            "total_cost": 0.0,
        }
        self.decision_history.clear()
        self.decisions_by_character.clear()

    def create_decision_id(self) -> str:
        """Create a unique decision ID"""
        return str(uuid.uuid4())
