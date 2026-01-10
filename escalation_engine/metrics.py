"""
Metrics and cost tracking for Escalation Engine

Tracks decision patterns, costs, and performance metrics.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from .core import DecisionSource, DecisionResult, EscalationReason

logger = logging.getLogger(__name__)


@dataclass
class CostTracker:
    """Track costs associated with decisions"""
    total_cost: float = 0.0
    daily_cost: float = 0.0
    daily_budget: float = 10.0
    alert_threshold: float = 8.0
    cost_by_source: Dict[str, float] = field(default_factory=dict)
    cost_by_day: Dict[str, float] = field(default_factory=dict)

    # Source-specific costs
    cost_bot: float = 0.0
    cost_brain: float = 0.0
    cost_human: float = 0.02

    def __post_init__(self):
        self.cost_by_source = {
            DecisionSource.BOT.value: 0.0,
            DecisionSource.BRAIN.value: 0.0,
            DecisionSource.HUMAN.value: 0.0,
        }

    def record_cost(self, source: DecisionSource, cost: float) -> None:
        """Record a cost for a decision source"""
        self.total_cost += cost
        self.daily_cost += cost
        self.cost_by_source[source.value] = self.cost_by_source.get(source.value, 0.0) + cost

        # Track by day
        today = datetime.now().strftime("%Y-%m-%d")
        self.cost_by_day[today] = self.cost_by_day.get(today, 0.0) + cost

        # Check if we should alert
        if self.daily_cost >= self.alert_threshold:
            logger.warning(f"Cost alert: Daily cost ${self.daily_cost:.2f} exceeds threshold ${self.alert_threshold:.2f}")

    def check_budget(self, estimated_cost: float) -> bool:
        """Check if a decision is within budget"""
        return (self.daily_cost + estimated_cost) <= self.daily_budget

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary"""
        return {
            "total_cost": round(self.total_cost, 4),
            "daily_cost": round(self.daily_cost, 4),
            "daily_budget": self.daily_budget,
            "remaining_budget": round(self.daily_budget - self.daily_cost, 4),
            "budget_used_ratio": self.daily_cost / self.daily_budget if self.daily_budget > 0 else 0,
            "cost_by_source": {k: round(v, 4) for k, v in self.cost_by_source.items()},
            "cost_by_day": {k: round(v, 4) for k, v in self.cost_by_day.items()},
        }

    def reset_daily(self) -> None:
        """Reset daily tracking (call at start of new day)"""
        self.daily_cost = 0.0


@dataclass
class DecisionMetrics:
    """Metrics for a single decision"""
    timestamp: float
    source: DecisionSource
    escalation_reason: Optional[EscalationReason]
    confidence: float
    time_taken_ms: float
    success: Optional[bool]
    cost: float


@dataclass
class PerformanceMetrics:
    """Track performance metrics over time"""
    total_decisions: int = 0
    successful_decisions: int = 0
    failed_decisions: int = 0

    # Timing metrics
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    max_time_ms: float = 0.0
    min_time_ms: float = float('inf')

    # Confidence metrics
    total_confidence: float = 0.0
    avg_confidence: float = 0.0

    # Source breakdown
    decisions_by_source: Dict[str, int] = field(default_factory=lambda: {
        DecisionSource.BOT.value: 0,
        DecisionSource.BRAIN.value: 0,
        DecisionSource.HUMAN.value: 0,
    })

    # Escation metrics
    escalations: int = 0
    escalation_reasons: Dict[str, int] = field(default_factory=dict)

    # Recent decisions (last 100)
    recent_decisions: List[DecisionMetrics] = field(default_factory=list)

    def record_decision(
        self,
        source: DecisionSource,
        confidence: float,
        time_taken_ms: float,
        cost: float,
        escalation_reason: Optional[EscalationReason] = None,
        success: Optional[bool] = None
    ) -> None:
        """Record a decision"""
        self.total_decisions += 1
        self.decisions_by_source[source.value] += 1

        if success is True:
            self.successful_decisions += 1
        elif success is False:
            self.failed_decisions += 1

        # Timing
        self.total_time_ms += time_taken_ms
        self.avg_time_ms = self.total_time_ms / self.total_decisions
        self.max_time_ms = max(self.max_time_ms, time_taken_ms)
        self.min_time_ms = min(self.min_time_ms, time_taken_ms)

        # Confidence
        self.total_confidence += confidence
        self.avg_confidence = self.total_confidence / self.total_decisions

        # Escalation
        if escalation_reason:
            self.escalations += 1
            reason_str = escalation_reason.value
            self.escalation_reasons[reason_str] = self.escalation_reasons.get(reason_str, 0) + 1

        # Add to recent
        metric = DecisionMetrics(
            timestamp=time.time(),
            source=source,
            escalation_reason=escalation_reason,
            confidence=confidence,
            time_taken_ms=time_taken_ms,
            success=success,
            cost=cost
        )
        self.recent_decisions.append(metric)

        # Keep only last 100
        if len(self.recent_decisions) > 100:
            self.recent_decisions.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        success_rate = 0.0
        if self.successful_decisions + self.failed_decisions > 0:
            success_rate = self.successful_decisions / (self.successful_decisions + self.failed_decisions)

        return {
            "total_decisions": self.total_decisions,
            "success_rate": round(success_rate, 3),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2) if self.min_time_ms != float('inf') else 0,
            "max_time_ms": round(self.max_time_ms, 2),
            "avg_confidence": round(self.avg_confidence, 3),
            "decisions_by_source": self.decisions_by_source,
            "escalations": self.escalations,
            "escalation_rate": round(self.escalations / self.total_decisions, 3) if self.total_decisions > 0 else 0,
            "escalation_reasons": self.escalation_reasons,
        }


@dataclass
class MetricsTracker:
    """Main metrics tracker combining cost and performance"""

    def __init__(self, daily_budget: float = 10.0):
        self.cost_tracker = CostTracker(daily_budget=daily_budget)
        self.performance = PerformanceMetrics()
        self.character_metrics: Dict[str, PerformanceMetrics] = {}

        # Time-based tracking
        self.metrics_by_hour: Dict[str, int] = defaultdict(int)
        self.metrics_by_day: Dict[str, int] = defaultdict(int)

        # Decision patterns
        self.situation_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def track_decision(
        self,
        result: DecisionResult,
        character_id: Optional[str] = None
    ) -> None:
        """Track a decision result"""
        # Update cost
        self.cost_tracker.record_cost(result.source, result.cost_estimate)

        # Update global performance
        self.performance.record_decision(
            source=result.source,
            confidence=result.confidence,
            time_taken_ms=result.time_taken_ms,
            cost=result.cost_estimate,
            escalation_reason=result.escalation_reason,
            success=result.success
        )

        # Update character-specific metrics
        if character_id:
            if character_id not in self.character_metrics:
                self.character_metrics[character_id] = PerformanceMetrics()

            self.character_metrics[character_id].record_decision(
                source=result.source,
                confidence=result.confidence,
                time_taken_ms=result.time_taken_ms,
                cost=result.cost_estimate,
                escalation_reason=result.escalation_reason,
                success=result.success
            )

        # Time-based tracking
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d %H:00")
        day_key = now.strftime("%Y-%m-%d")
        self.metrics_by_hour[hour_key] += 1
        self.metrics_by_day[day_key] += 1

        # Situation patterns
        situation_type = result.metadata.get("situation_type", "unknown")
        self.situation_patterns[situation_type][result.source.value] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary"""
        return {
            "cost": self.cost_tracker.get_cost_summary(),
            "performance": self.performance.get_summary(),
            "character_count": len(self.character_metrics),
            "decisions_by_hour": dict(list(self.metrics_by_hour.items())[-24]),  # Last 24 hours
            "decisions_by_day": dict(list(self.metrics_by_day.items())[-7]),  # Last 7 days
            "situation_patterns": {k: dict(v) for k, v in self.situation_patterns.items()},
        }

    def get_character_summary(self, character_id: str) -> Dict[str, Any]:
        """Get metrics for a specific character"""
        if character_id not in self.character_metrics:
            return {"error": "Character not found"}

        return self.character_metrics[character_id].get_summary()

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis"""
        return {
            "summary": self.get_summary(),
            "cost": self.cost_tracker.get_cost_summary(),
            "performance": self.performance.get_summary(),
            "characters": {
                char_id: metrics.get_summary()
                for char_id, metrics in self.character_metrics.items()
            },
            "timestamp": datetime.now().isoformat(),
        }

    def reset(self) -> None:
        """Reset all metrics"""
        self.cost_tracker = CostTracker(daily_budget=self.cost_tracker.daily_budget)
        self.performance = PerformanceMetrics()
        self.character_metrics.clear()
        self.metrics_by_hour.clear()
        self.metrics_by_day.clear()
        self.situation_patterns.clear()
