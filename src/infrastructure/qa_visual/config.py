"""QA Visual configuration with spike conditions C1-C5 built in.

C1: thinking:{type:"disabled"} always in QA loops (fast + deterministic).
C2: max_tokens >= 4000 required when thinking is ON.
C3: Browser User-Agent on direct HTTP calls to the provider gateway.
C4: Model id monitored (exp -> GA) via env, never hardcoded in callers.
C5: Pricing snapshot 2026-08-22 ($0.22/$0.66 per 1M tokens, off-peak).

The API key is read ONLY from the environment (OPENCODE_GO_API_KEY),
never stored in this repository.
"""

import os

from pydantic import BaseModel, Field, model_validator

DEFAULT_MODEL = "deepseek-v4-flash-vision-exp"
DEFAULT_GATEWAY_URL = "https://opencode.ai/zen/go/v1/chat/completions"
# C3: browser UA required to avoid Cloudflare 1010 rejections.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# C5: pricing pinned on 2026-08-22 (off-peak rates, USD per 1M tokens).
PRICING_INPUT_PER_1M_USD = 0.22
PRICING_OUTPUT_PER_1M_USD = 0.66
PRICING_SNAPSHOT_DATE = "2026-08-22"

DEFAULT_SCORE_THRESHOLD = 80
DEFAULT_MAX_TOKENS = 4000
DEFAULT_REPORTS_DIR = "reports/qa-visual"


class QAVisualConfig(BaseModel):
    """Configuration for the QA Visual module."""

    model: str = Field(default=DEFAULT_MODEL, description="Vision model id (C4: overridable)")
    gateway_url: str = Field(default=DEFAULT_GATEWAY_URL)
    user_agent: str = Field(default=BROWSER_USER_AGENT)
    api_key: str | None = Field(default=None, description="From env only, never committed")

    # C1: thinking disabled by default for QA loops.
    thinking_enabled: bool = Field(default=False)
    # C2: >= 4000 when thinking is ON.
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=1)

    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    request_timeout_s: float = Field(default=120.0, gt=0)

    score_threshold: int = Field(default=DEFAULT_SCORE_THRESHOLD, ge=0, le=100)

    # C5: pricing pin for cost tracking per analysis.
    cost_input_per_1m_usd: float = PRICING_INPUT_PER_1M_USD
    cost_output_per_1m_usd: float = PRICING_OUTPUT_PER_1M_USD
    pricing_snapshot_date: str = PRICING_SNAPSHOT_DATE

    reports_dir: str = Field(default=DEFAULT_REPORTS_DIR)
    degradation_alert_points: int = Field(
        default=10, ge=1, description="Score drop that triggers a trend alert"
    )

    @model_validator(mode="after")
    def _validate_thinking_tokens(self) -> "QAVisualConfig":
        """C2: thinking ON requires max_tokens >= 4000 for complete JSON."""
        if self.thinking_enabled and self.max_tokens < 4000:
            raise ValueError(
                "thinking_enabled=True requires max_tokens >= 4000 (spike condition C2)"
            )
        return self

    def calculate_cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Compute analysis cost from token usage with pinned pricing (C5)."""
        return (
            prompt_tokens * self.cost_input_per_1m_usd
            + completion_tokens * self.cost_output_per_1m_usd
        ) / 1_000_000

    @classmethod
    def from_env(cls) -> "QAVisualConfig":
        """Build config from environment variables with safe fallbacks."""
        threshold_raw = os.environ.get("QA_VISUAL_THRESHOLD_SCORE", "")
        try:
            threshold = int(threshold_raw) if threshold_raw else DEFAULT_SCORE_THRESHOLD
        except ValueError:
            threshold = DEFAULT_SCORE_THRESHOLD

        return cls(
            model=os.environ.get("QA_VISUAL_MODEL", DEFAULT_MODEL),
            gateway_url=os.environ.get("QA_VISUAL_GATEWAY_URL", DEFAULT_GATEWAY_URL),
            api_key=os.environ.get("OPENCODE_GO_API_KEY"),
            score_threshold=threshold,
            reports_dir=os.environ.get("QA_VISUAL_REPORTS_DIR", DEFAULT_REPORTS_DIR),
        )
