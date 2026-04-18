# Escalation Engine - Complete Documentation

**Intelligent Decision Routing for Cost-Optimized LLM Usage**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Advanced Topics](#advanced-topics)

---

## Overview

### What is Escalation Engine?

Escalation Engine is a Python library that intelligently routes decisions through three tiers to achieve 40x cost reduction while maintaining quality:

1. **Bot** - Fast, deterministic, rule-based (free)
2. **Brain** - Local LLM for nuanced decisions (low cost)
3. **Human** - API LLM for critical decisions (higher cost)

### Key Benefits

- **40x Cost Reduction**: Route routine decisions to free rules
- **Quality Maintained**: Critical decisions still get LLM treatment
- **Fast Response**: Bot decisions in <10ms
- **Learning System**: Adapts thresholds based on outcomes
- **Multi-Provider**: OpenAI, Anthropic, Ollama support

### Use Cases

- Customer support automation
- Game character AI
- Content moderation
- Data analysis workflows
- Any system with varying decision complexity

---

## Architecture

### Decision Flow

```
                    Decision Request
                           |
                           v
                 +---------------------+
                 |  Escalation Engine  |
                 |  - Analyze stakes   |
                 |  - Check novelty    |
                 |  - Evaluate urgency |
                 +----------+----------+
                            |
           +----------------+----------------+
           |                |                |
           v                v                v
    +------------+   +------------+   +------------+
    |   BOT      |   |   BRAIN    |   |   HUMAN    |
    | (Rules)    |   | (Local LLM)|   | (API LLM)  |
    | Free       |   | Low Cost   |   | High Cost  |
    | <10ms      |   | 100-500ms  |   | 500-2000ms |
    +------------+   +------------+   +------------+
```

### Routing Matrix

| Situation | Novel? | Stakes | Urgent | Route To | Confidence |
|-----------|--------|--------|--------|----------|------------|
| Routine | No | Low | Any | Bot | 0.70 |
| Important | No | High | No | Brain | 0.60 |
| Critical | Any | Critical | Yes | Human | 0.90 |
| Novel | Yes | Any | No | Brain | 0.50 |
| Urgent | No | Any | Yes | Bot | 0.60 |

### Core Components

```
escalation_engine/
├── __init__.py           # Public API
├── core.py               # EscalationEngine implementation
├── config.py             # Configuration management
├── providers.py          # LLM provider abstraction
├── metrics.py            # Performance tracking
├── server.py             # FastAPI server
└── cli.py                # Command-line interface
```

---

## Installation

### From PyPI

```bash
pip install escalation-engine
```

### From Source

```bash
git clone https://github.com/ws-fabric/escalation-engine
cd escalation-engine
pip install -e .
```

### With Optional Dependencies

```bash
# With all LLM providers
pip install escalation-engine[all]

# Specific providers
pip install escalation-engine[openai,anthropic]
pip install escalation-engine[ollama]
```

### Verify Installation

```python
from escalation_engine import EscalationEngine

engine = EscalationEngine()
print(engine.get_stats())
# Output: {'total_decisions': 0, 'bot_decisions': 0, ...}
```

---

## API Reference

### EscalationEngine

Main class for decision routing.

```python
from escalation_engine import EscalationEngine, DecisionContext

engine = EscalationEngine()
```

#### Constructor

```python
EscalationEngine(
    config: Optional[Dict[str, Any]] = None,
    enable_learning: bool = True,
    enable_metrics: bool = True
)
```

**Parameters:**
- `config`: Optional configuration dictionary
- `enable_learning`: Enable threshold adjustment from outcomes
- `enable_metrics`: Track performance metrics

#### Methods

##### route_decision()

Route a decision to the appropriate source.

```python
route_decision(context: DecisionContext) -> EscalationDecision
```

**Parameters:**
- `context`: Decision context with stakes, urgency, situation details

**Returns:**
- `EscalationDecision`: Routing decision with source and requirements

**Example:**
```python
context = DecisionContext(
    character_id="user_123",
    situation_type="support",
    situation_description="User reports login issue",
    stakes=0.5,
    urgency_ms=5000
)

decision = engine.route_decision(context)
print(f"Route to: {decision.source.value}")
```

##### record_decision()

Record a routed decision for tracking.

```python
record_decision(result: DecisionResult) -> None
```

**Parameters:**
- `result`: The decision that was executed

##### record_outcome()

Record the outcome of a decision for learning.

```python
record_outcome(
    decision_id: str,
    success: bool,
    outcome_details: Optional[Dict[str, Any]] = None
) -> None
```

##### get_stats()

Get global or per-character statistics.

```python
get_stats(character_id: Optional[str] = None) -> Dict[str, Any]
```

**Returns:**
- Dictionary with decision counts, success rates, costs

##### set_thresholds()

Configure custom thresholds for a character.

```python
set_thresholds(
    character_id: str,
    thresholds: EscalationThresholds
) -> None
```

### DecisionContext

Context for a decision that needs routing.

```python
@dataclass
class DecisionContext:
    character_id: str                      # Required
    situation_type: str                    # Required
    situation_description: str             # Required
    stakes: float = 0.5                   # 0-1 importance
    urgency_ms: Optional[int] = None       # Time available
    character_hp_ratio: float = 1.0        # Health/resource status
    available_resources: Dict[str, int]    # Available resources
    similar_decisions_count: int = 0       # How many times seen
    recent_failures: int = 0               # Recent failures
    timestamp: float = field(default_factory=time.time)
```

### EscalationDecision

Result of routing a decision.

```python
@dataclass
class EscalationDecision:
    source: DecisionSource                 # BOT, BRAIN, HUMAN
    reason: Optional[EscalationReason]     # Why routed this way
    confidence_required: float             # Min confidence needed
    time_budget_ms: Optional[int]          # Time allowed
    allow_fallback: bool                   # Can escalate further
    metadata: Dict[str, Any]               # Additional data
```

### DecisionSource

Enum for where decisions come from.

```python
class DecisionSource(Enum):
    BOT = "bot"          # Rule-based, free
    BRAIN = "brain"      # Local LLM, low cost
    HUMAN = "human"      # API LLM, high cost
    OVERRIDE = "override"# Manual override
```

### EscalationReason

Enum for why a decision was routed.

```python
class EscalationReason(Enum):
    LOW_CONFIDENCE = "low_confidence"
    HIGH_STAKES = "high_stakes"
    NOVEL_SITUATION = "novel_situation"
    TIME_CRITICAL = "time_critical"
    CONFLICTING_BOTS = "conflicting_bots"
    SAFETY_CONCERN = "safety_concern"
    CHARACTER_GROWTH = "character_growth"
    PLAYER_REQUEST = "player_request"
    COST_LIMIT = "cost_limit"
```

### EscalationThresholds

Configure routing behavior per character.

```python
@dataclass
class EscalationThresholds:
    bot_min_confidence: float = 0.7        # Below this -> brain
    brain_min_confidence: float = 0.5      # Below this -> human
    high_stakes_threshold: float = 0.7     # Above this -> important
    critical_stakes_threshold: float = 0.9 # Above this -> human
    urgent_time_ms: int = 500              # Below this -> urgent
    critical_time_ms: int = 100            # Below this -> critical
    novelty_threshold: float = 0.6         # Above this -> novel
    hp_critical_threshold: float = 0.2     # Below this -> critical
```

---

## Usage Examples

### Basic Usage

```python
from escalation_engine import EscalationEngine, DecisionContext

# Initialize
engine = EscalationEngine()

# Create context
context = DecisionContext(
    character_id="user_123",
    situation_type="support",
    situation_description="User needs password reset",
    stakes=0.3,  # Low stakes
    urgency_ms=10000
)

# Route decision
decision = engine.route_decision(context)

print(f"Route: {decision.source.value}")
print(f"Confidence required: {decision.confidence_required}")
print(f"Reason: {decision.reason}")

# Output:
# Route: bot
# Confidence required: 0.7
# Reason: None (routine situation)
```

### High Stakes Situation

```python
context = DecisionContext(
    character_id="user_123",
    situation_type="support",
    situation_description="User reports account breach",
    stakes=0.9,  # Critical!
    urgency_ms=5000
)

decision = engine.route_decision(context)

print(f"Route: {decision.source.value}")
# Output: Route: human

print(f"Reason: {decision.reason.value}")
# Output: Reason: high_stakes
```

### Recording Outcomes (Learning)

```python
from escalation_engine import DecisionResult, DecisionSource

# Make a decision
result = DecisionResult(
    decision_id="dec_001",
    source=DecisionSource.BOT,
    action="Reset password via automated link",
    confidence=0.85,
    time_taken_ms=5.0
)

# Record the decision
engine.record_decision(result)

# Later, record the outcome
engine.record_outcome(
    decision_id="dec_001",
    success=True,
    outcome_details={"user_satisfied": True}
)

# Stats updated automatically
stats = engine.get_stats("user_123")
print(f"Success rate: {stats['success_rate']:.2%}")
```

### Custom Thresholds

```python
from escalation_engine import EscalationEngine, EscalationThresholds

engine = EscalationEngine()

# Set cautious thresholds for a new character
engine.set_thresholds(
    "new_character",
    EscalationThresholds(
        bot_min_confidence=0.5,      # Lower bar for bot
        brain_min_confidence=0.4,    # Lower bar for brain
        high_stakes_threshold=0.5,    # Consider more as high stakes
    )
)

# Set aggressive thresholds for an experienced character
engine.set_thresholds(
    "veteran_character",
    EscalationThresholds(
        bot_min_confidence=0.85,     # Higher bar for bot
        brain_min_confidence=0.7,    # Higher bar for brain
        high_stakes_threshold=0.9,   # Only very critical matters
    )
)
```

### With LLM Providers

```python
from escalation_engine import EscalationEngine
from escalation_engine.providers import OpenAIProvider, OllamaProvider

# Configure providers
engine = EscalationEngine(config={
    "llm_providers": {
        "openai": {
            "api_key": "sk-...",
            "model": "gpt-4",
            "cost_per_1k_tokens": 0.03
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "llama2",
            "cost_per_1k_tokens": 0.0
        }
    }
})

# Route and execute
decision = engine.route_decision(context)

if decision.source == DecisionSource.BRAIN:
    # Use local Ollama
    response = engine.providers["ollama"].generate(
        prompt=context.situation_description
    )
elif decision.source == DecisionSource.HUMAN:
    # Use OpenAI API
    response = engine.providers["openai"].generate(
        prompt=context.situation_description
    )
```

---

## Configuration

### File Configuration (YAML)

Create `escalation_config.yaml`:

```yaml
# Default thresholds for new characters
default_thresholds:
  bot_min_confidence: 0.7
  brain_min_confidence: 0.5
  high_stakes_threshold: 0.7
  critical_stakes_threshold: 0.9
  urgent_time_ms: 500
  critical_time_ms: 100
  novelty_threshold: 0.6
  hp_critical_threshold: 0.2

# LLM provider configuration
llm_providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    cost_per_1k_tokens: 0.03
    max_tokens: 500

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-opus-20240229"
    cost_per_1k_tokens: 0.015

  ollama:
    base_url: "http://localhost:11434"
    model: "llama2"
    cost_per_1k_tokens: 0.0

# Cost tracking
cost_tracking:
  enabled: true
  daily_budget: 10.0
  alert_threshold: 8.0

# Learning
learning:
  enabled: true
  confidence_boost_per_success: 0.05
  confidence_penalty_per_failure: 0.1
```

### Loading Configuration

```python
from escalation_engine import EscalationEngine

# From file
engine = EscalationEngine(config_path="escalation_config.yaml")

# From dictionary
engine = EscalationEngine(config={
    "default_thresholds": {
        "bot_min_confidence": 0.8
    },
    "cost_tracking": {
        "enabled": True,
        "daily_budget": 5.0
    }
})
```

### Environment Variables

```bash
# Required for OpenAI/Anthropic
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...

# Optional overrides
export ESCALATION_CONFIG_PATH=/path/to/config.yaml
export ESCALATION_DAILY_BUDGET=10.0
export OLLAMA_BASE_URL=http://localhost:11434
```

---

## Advanced Topics

### Custom Decision Sources

```python
from escalation_engine import DecisionSource, EscalationEngine
from escalation_engine.core import DecisionContext

class CustomDecisionSource:
    """Custom decision source implementation"""

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", "custom")

    def decide(self, context: DecisionContext) -> str:
        """Make a decision"""
        # Your custom logic here
        return f"Custom decision for {context.situation_type}"

    def get_confidence(self, context: DecisionContext) -> float:
        """Return confidence level"""
        return 0.8

# Register with engine
engine = EscalationEngine()
engine.register_source("custom", CustomDecisionSource({"name": "my_source"}))
```

### Metrics and Monitoring

```python
from escalation_engine import EscalationEngine

engine = EscalationEngine(enable_metrics=True)

# ... make decisions ...

# Get global stats
stats = engine.get_stats()
print(f"Total decisions: {stats['total_decisions']}")
print(f"Cost savings: {stats['cost_savings_percent']:.1f}%")

# Get per-character stats
char_stats = engine.get_stats("user_123")
print(f"Bot rate: {char_stats['bot_rate']:.1%}")
print(f"Success rate: {char_stats['success_rate']:.1%}")

# Export metrics
engine.export_metrics("metrics.json")
```

### FastAPI Server

Run the built-in API server:

```bash
uvicorn escalation_engine.server:app --reload
```

**Endpoints:**

- `POST /route` - Route a decision
- `POST /record` - Record a decision result
- `POST /outcome` - Record an outcome
- `GET /stats` - Get global statistics
- `GET /stats/{character_id}` - Get character statistics

**Example API Usage:**

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "user_123",
    "situation_type": "support",
    "situation_description": "Password reset request",
    "stakes": 0.3,
    "urgency_ms": 5000
  }'
```

**Response:**
```json
{
  "source": "bot",
  "reason": null,
  "confidence_required": 0.7,
  "time_budget_ms": 5000,
  "allow_fallback": true,
  "metadata": {
    "is_novel": false,
    "is_high_stakes": false,
    "routing_time_ms": 1.2
  }
}
```

### Cost Analysis

```python
from escalation_engine import EscalationEngine

engine = EscalationEngine()

# Simulate 1000 decisions
for i in range(1000):
    context = DecisionContext(
        character_id=f"user_{i % 100}",
        situation_type="support",
        situation_description=f"Query {i}",
        stakes=0.3 + (i % 10) * 0.07
    )
    decision = engine.route_decision(context)
    # Track which routes were taken

# Analyze costs
stats = engine.get_stats()
print(f"Bot decisions: {stats['bot_decisions']} (free)")
print(f"Brain decisions: {stats['brain_decisions']} (local)")
print(f"Human decisions: {stats['human_decisions']} (${stats['total_cost']:.2f})")
print(f"Cost without escalation: ${1000 * 0.02:.2f}")
print(f"Savings: ${1000 * 0.02 - stats['total_cost']:.2f} ({(1 - stats['total_cost']/(1000 * 0.02)) * 100:.0f}%)")
```

---

## Testing

```python
import pytest
from escalation_engine import EscalationEngine, DecisionContext, DecisionSource

def test_low_stakes_bot_routing():
    engine = EscalationEngine()

    context = DecisionContext(
        character_id="test",
        situation_type="support",
        situation_description="FAQ question",
        stakes=0.3
    )

    decision = engine.route_decision(context)
    assert decision.source == DecisionSource.BOT

def test_high_stakes_human_routing():
    engine = EscalationEngine()

    context = DecisionContext(
        character_id="test",
        situation_type="support",
        situation_description="Account breach",
        stakes=0.95
    )

    decision = engine.route_decision(context)
    assert decision.source == DecisionSource.HUMAN

def test_novel_situation_brain_routing():
    engine = EscalationEngine()

    context = DecisionContext(
        character_id="test",
        situation_type="support",
        situation_description="Unique issue never seen",
        stakes=0.5,
        similar_decisions_count=0  # Never seen
    )

    decision = engine.route_decision(context)
    assert decision.source == DecisionSource.BRAIN
```

---

**Package Version:** 1.0.0
**Documentation Version:** 1.0.0
**Last Updated:** 2025-01-10
