# Escalation Engine

**Intelligent decision routing for 40x cost reduction through smart LLM usage**

The Escalation Engine intelligently routes decisions through three tiers:

1. **Bot** - Fast, deterministic, rule-based (free)
2. **Brain** - Local LLM for nuanced decisions (low cost)
3. **Human** - API LLM for critical decisions (higher cost)

## Features

- **Confidence-based escalation** - Route based on decision confidence
- **Context-aware routing** - Consider stakes, urgency, novelty
- **Cost tracking** - Monitor and optimize spending
- **Performance metrics** - Track success rates and decision patterns
- **Fallback logic** - Automatic escalation when confidence drops
- **Learning system** - Adapt thresholds based on outcomes
- **Multi-provider support** - Works with OpenAI, Anthropic, Ollama, and more
- **FastAPI integration** - Ready for web service deployment
- **Configuration file support** - YAML/JSON config

## Installation

```bash
pip install escalation-engine
```

## Quick Start

```python
from escalation_engine import EscalationEngine, DecisionContext

# Initialize the engine
engine = EscalationEngine()

# Create a decision context
context = DecisionContext(
    character_id="user_123",
    situation_type="customer_support",
    situation_description="User reports billing issue",
    stakes=0.7,  # High stakes
    urgency_ms=5000  # 5 seconds to respond
)

# Route the decision
decision = engine.route_decision(context)

print(f"Route to: {decision.source}")  # BOT, BRAIN, or HUMAN
print(f"Reason: {decision.reason}")
print(f"Confidence required: {decision.confidence_required}")
```

## How It Works

```
                    ┌─────────────────────────────────────┐
                    │       Decision Request              │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │     Escalation Engine               │
                    │  - Analyze stakes                   │
                    │  - Check novelty                    │
                    │  - Evaluate urgency                 │
                    │  - Review history                   │
                    └───────┬───────────────┬─────────────┘
                            │               │
                    ┌───────▼───────┐   ┌──▼─────────────┐
                    │   CRITICAL?   │   │   ROUTINE?     │
                    │   Time < 100ms│   │   Seen before  │
                    └───────┬───────┘   └──┬─────────────┘
                            │               │
                     HUMAN  │           BOT │
                    (API LLM)│        (Rules)│
                            │               │
                            └───┬───────┬───┘
                                │       │
                        ┌───────▼───┐   │
                        │  BRAIN    ◄───┘  (Local LLM)
                        │ (Ollama)  │       - Novel situations
                        └───────────┘       - Medium stakes
                                            - Low confidence
```

## Configuration

Create an `escalation_config.yaml`:

```yaml
# escalation_config.yaml
default_thresholds:
  bot_min_confidence: 0.7
  brain_min_confidence: 0.5
  high_stakes_threshold: 0.7
  critical_stakes_threshold: 0.9
  urgent_time_ms: 500
  critical_time_ms: 100

llm_providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    cost_per_1k_tokens: 0.03

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-opus-20240229"
    cost_per_1k_tokens: 0.015

  ollama:
    base_url: "http://localhost:11434"
    model: "llama2"
    cost_per_1k_tokens: 0.0

cost_tracking:
  enabled: true
  daily_budget: 10.0
  alert_threshold: 8.0
```

Use the configuration:

```python
from escalation_engine import EscalationEngine

engine = EscalationEngine(config_path="escalation_config.yaml")
```

## Decision Sources

### Bot (Rule-based)
- **Use when:** Routine decisions, high familiarity, time-sensitive
- **Cost:** Free
- **Speed:** < 10ms
- **Example:** Password reset, FAQ answers

### Brain (Local LLM)
- **Use when:** Novel situations, medium stakes, some ambiguity
- **Cost:** Minimal (local compute)
- **Speed:** 100-500ms
- **Example:** Customer inquiry with unique context

### Human (API LLM)
- **Use when:** Critical stakes, low confidence, safety concerns
- **Cost:** $0.01-0.10 per decision
- **Speed:** 500-2000ms
- **Example:** Legal questions, medical advice, account closure

## Cost Savings

Traditional approach: All decisions to API LLM
- 1000 decisions/day × $0.02 = **$20/day**

Escalation Engine approach:
- 700 Bot decisions × $0 = $0
- 250 Brain decisions × $0 = $0
- 50 Human decisions × $0.02 = $1
- **Total: $1/day = 40x reduction**

## API Reference

### EscalationEngine

```python
class EscalationEngine:
    def __init__(self, config_path: Optional[str] = None)
    def route_decision(self, context: DecisionContext) -> EscalationDecision
    def should_escalate(self, result: DecisionResult, context: DecisionContext) -> Tuple[bool, EscalationReason]
    def record_decision(self, result: DecisionResult) -> None
    def record_outcome(self, decision_id: str, success: bool) -> None
    def get_stats(self) -> Dict[str, Any]
```

### DecisionContext

```python
@dataclass
class DecisionContext:
    character_id: str              # Entity making the decision
    situation_type: str            # Type of situation
    situation_description: str     # Free-form description
    stakes: float = 0.5           # 0=trivial, 1=critical
    urgency_ms: Optional[int] = None
    character_hp_ratio: float = 1.0  # Health/resource status
    available_resources: Dict[str, int] = field(default_factory=dict)
    similar_decisions_count: int = 0
    recent_failures: int = 0
```

### EscalationDecision

```python
@dataclass
class EscalationDecision:
    source: DecisionSource          # BOT, BRAIN, HUMAN
    reason: Optional[EscalationReason]
    confidence_required: float
    time_budget_ms: Optional[int]
    allow_fallback: bool
    metadata: Dict[str, Any]
```

## FastAPI Server

Run the built-in FastAPI server:

```bash
uvicorn escalation_engine.server:app --reload
```

The server exposes:

- `POST /route` - Route a decision
- `POST /record` - Record a decision result
- `POST /outcome` - Record an outcome
- `GET /stats` - Get statistics
- `GET /stats/{character_id}` - Get character statistics

### Example API Request

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "user_123",
    "situation_type": "support",
    "situation_description": "Customer wants refund",
    "stakes": 0.8,
    "urgency_ms": 3000
  }'
```

Response:

```json
{
  "source": "brain",
  "reason": "high_stakes",
  "confidence_required": 0.6,
  "time_budget_ms": 3000,
  "allow_fallback": true,
  "metadata": {
    "is_novel": false,
    "is_high_stakes": true,
    "is_critical_stakes": false,
    "is_urgent": false
  }
}
```

## Examples

See the `examples/` directory for complete examples:

- `basic_usage.py` - Simple routing example
- `customer_support.py` - Customer support automation
- `game_ai.py` - Game character AI decisions
- `cost_tracking.py` - Cost monitoring and alerts
- `learning_system.py` - Adaptive thresholds

## Publishing to PyPI

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI (test first)
twine upload --repository testpypi dist/*
twine upload dist/*
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines.

## Credits

Originally developed as part of DMLog - extracted and enhanced as a standalone tool.
