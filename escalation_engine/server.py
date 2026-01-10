"""
FastAPI server for Escalation Engine

Provides a REST API for decision routing and metrics.
"""

import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

from .core import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationReason,
)
from .config import load_config
from .metrics import MetricsTracker

logger = logging.getLogger(__name__)


# Global engine instance
_engine: Optional[EscalationEngine] = None
_metrics: Optional[MetricsTracker] = None


def get_engine() -> EscalationEngine:
    """Get the global engine instance"""
    global _engine
    if _engine is None:
        _engine = EscalationEngine()
    return _engine


def get_metrics() -> MetricsTracker:
    """Get the global metrics tracker"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsTracker()
    return _metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    global _engine, _metrics

    try:
        config = load_config()
        _engine = EscalationEngine(
            enable_learning=config.enable_learning,
            enable_metrics=config.enable_metrics,
        )
        _metrics = MetricsTracker(daily_budget=config.cost_tracking.daily_budget)

        # Apply config thresholds
        for char_id, thresh_config in config.character_thresholds.items():
            from .core import EscalationThresholds
            _engine.set_thresholds(char_id, EscalationThresholds(
                bot_min_confidence=thresh_config.bot_min_confidence,
                brain_min_confidence=thresh_config.brain_min_confidence,
                high_stakes_threshold=thresh_config.high_stakes_threshold,
                critical_stakes_threshold=thresh_config.critical_stakes_threshold,
            ))

        logger.info("Escalation Engine server started")
    except Exception as e:
        logger.warning(f"Could not load config: {e}. Using defaults.")
        _engine = EscalationEngine()
        _metrics = MetricsTracker()

    yield

    # Shutdown
    logger.info("Escalation Engine server stopped")


# Pydantic models for API
class DecisionContextRequest(BaseModel):
    """Request model for decision routing"""
    character_id: str = Field(..., description="ID of the character/entity making the decision")
    situation_type: str = Field(..., description="Type of situation (e.g., 'combat', 'social')")
    situation_description: str = Field(..., description="Free-form description of the situation")
    stakes: float = Field(default=0.5, ge=0, le=1, description="Stakes level (0=trivial, 1=critical)")
    urgency_ms: Optional[int] = Field(default=None, description="Time available in milliseconds")
    character_hp_ratio: float = Field(default=1.0, ge=0, le=1, description="Character health ratio")
    available_resources: Dict[str, int] = Field(default_factory=dict, description="Available resources")
    similar_decisions_count: int = Field(default=0, ge=0, description="Number of similar decisions seen")
    recent_failures: int = Field(default=0, ge=0, description="Number of recent failures")
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class DecisionResponse(BaseModel):
    """Response model for decision routing"""
    source: str
    reason: Optional[str]
    confidence_required: float
    time_budget_ms: Optional[int]
    allow_fallback: bool
    metadata: Dict[str, Any]


class DecisionRecordRequest(BaseModel):
    """Request model for recording a decision"""
    decision_id: str
    source: str
    action: str
    confidence: float
    time_taken_ms: float
    escalated_from: Optional[str] = None
    escalation_reason: Optional[str] = None
    success: Optional[bool] = None
    cost_estimate: float = 0.0
    character_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutcomeRequest(BaseModel):
    """Request model for recording an outcome"""
    decision_id: str
    success: bool
    outcome_details: Optional[Dict[str, Any]] = None


# Create FastAPI app
app = FastAPI(
    title="Escalation Engine API",
    description="Intelligent decision routing for cost-optimized LLM usage",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "name": "Escalation Engine API",
        "version": "1.0.0",
        "description": "Intelligent decision routing for cost-optimized LLM usage",
        "endpoints": {
            "route": "POST /route - Route a decision",
            "record": "POST /record - Record a decision result",
            "outcome": "POST /outcome - Record an outcome",
            "stats": "GET /stats - Get global statistics",
            "stats_character": "GET /stats/{character_id} - Get character statistics",
            "metrics": "GET /metrics - Get detailed metrics",
        }
    }


@app.get("/health", tags=["Health"])
async def health() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/route", response_model=DecisionResponse, tags=["Decisions"])
async def route_decision(request: DecisionContextRequest) -> DecisionResponse:
    """
    Route a decision to the appropriate source (Bot, Brain, or Human)

    Returns the recommended source and routing metadata.
    """
    engine = get_engine()

    context = DecisionContext(
        character_id=request.character_id,
        situation_type=request.situation_type,
        situation_description=request.situation_description,
        stakes=request.stakes,
        urgency_ms=request.urgency_ms,
        character_hp_ratio=request.character_hp_ratio,
        available_resources=request.available_resources,
        similar_decisions_count=request.similar_decisions_count,
        recent_failures=request.recent_failures,
        custom_data=request.custom_data,
    )

    decision = engine.route_decision(context)

    return DecisionResponse(
        source=decision.source.value,
        reason=decision.reason.value if decision.reason else None,
        confidence_required=decision.confidence_required,
        time_budget_ms=decision.time_budget_ms,
        allow_fallback=decision.allow_fallback,
        metadata=decision.metadata,
    )


@app.post("/record", tags=["Decisions"])
async def record_decision(request: DecisionRecordRequest) -> Dict[str, Any]:
    """
    Record a decision result for tracking and learning

    Use this after executing a decision to track outcomes.
    """
    engine = get_engine()
    metrics = get_metrics()

    # Parse source and reason
    try:
        source = DecisionSource(request.source)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source: {request.source}"
        )

    escalated_from = None
    if request.escalated_from:
        try:
            escalated_from = DecisionSource(request.escalated_from)
        except ValueError:
            pass

    escalation_reason = None
    if request.escalation_reason:
        try:
            escalation_reason = EscalationReason(request.escalation_reason)
        except ValueError:
            pass

    result = DecisionResult(
        decision_id=request.decision_id,
        source=source,
        action=request.action,
        confidence=request.confidence,
        time_taken_ms=request.time_taken_ms,
        escalated_from=escalated_from,
        escalation_reason=escalation_reason,
        success=request.success,
        cost_estimate=request.cost_estimate,
        metadata=request.metadata or {"character_id": request.character_id},
    )

    engine.record_decision(result)

    # Track metrics
    metrics.track_decision(result, request.character_id)

    return {
        "status": "recorded",
        "decision_id": request.decision_id,
        "stats": engine.get_global_stats(),
    }


@app.post("/outcome", tags=["Decisions"])
async def record_outcome(request: OutcomeRequest) -> Dict[str, Any]:
    """
    Record the outcome of a decision for learning

    Call this after you know whether a decision was successful.
    """
    engine = get_engine()

    engine.record_outcome(
        decision_id=request.decision_id,
        success=request.success,
        outcome_details=request.outcome_details,
    )

    return {
        "status": "recorded",
        "decision_id": request.decision_id,
    }


@app.get("/stats", tags=["Statistics"])
async def get_global_stats() -> Dict[str, Any]:
    """Get global decision statistics"""
    engine = get_engine()
    return engine.get_global_stats()


@app.get("/stats/{character_id}", tags=["Statistics"])
async def get_character_stats(character_id: str) -> Dict[str, Any]:
    """Get decision statistics for a specific character"""
    engine = get_engine()
    return engine.get_character_stats(character_id)


@app.get("/metrics", tags=["Metrics"])
async def get_metrics() -> Dict[str, Any]:
    """Get detailed metrics including costs and performance"""
    metrics = get_metrics()
    return metrics.export_metrics()


@app.get("/metrics/character/{character_id}", tags=["Metrics"])
async def get_character_metrics(character_id: str) -> Dict[str, Any]:
    """Get detailed metrics for a specific character"""
    metrics = get_metrics()
    return metrics.get_character_summary(character_id)


@app.post("/reset", tags=["Administration"])
async def reset_stats() -> Dict[str, str]:
    """Reset all statistics (requires confirmation)"""
    engine = get_engine()
    global _metrics
    _metrics = MetricsTracker()
    engine.reset_stats()
    return {"status": "reset"}


def run_server(host: str = "0.0.0.0", port: int = 8000, **kwargs) -> None:
    """Run the FastAPI server"""
    uvicorn.run(
        "escalation_engine.server:app",
        host=host,
        port=port,
        **kwargs
    )


if __name__ == "__main__":
    run_server()
