"""Pydantic models for structured LLM output in each analysis pass."""

from pydantic import BaseModel, Field


class TriageResult(BaseModel):
    """Output from Pass 1: Triage (GPT-4o-mini)"""
    verdict: str = Field(description="SUSPICIOUS or BENIGN")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the verdict")
    reasoning: str = Field(description="1-2 sentence explanation of the verdict")
    signals: list[str] = Field(
        default_factory=list,
        description="List of detected threat signals, e.g. ['new_network_call', 'obfuscated_code', 'install_script_change']",
    )


class Evidence(BaseModel):
    """Code evidence supporting a finding."""
    file_path: str
    line_start: int
    line_end: int
    snippet: str = Field(description="The relevant code snippet")
    explanation: str = Field(description="Why this code is concerning")


class DeepFinding(BaseModel):
    """A single security finding from Pass 2."""
    category: str = Field(description="Finding category (e.g., 'network_call', 'obfuscation', 'install_script')")
    severity: str = Field(description="info, low, medium, high, or critical")
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Detailed explanation of the finding")
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    mitre_technique: str | None = Field(default=None, description="MITRE ATT&CK technique ID if applicable")
    remediation: str | None = Field(default=None, description="Suggested remediation steps")


class DeepAnalysisResult(BaseModel):
    """Output from Pass 2: Deep Analysis (GPT-4o)"""
    findings: list[DeepFinding] = Field(default_factory=list)
    benign_changes_summary: str = Field(description="Summary of non-suspicious changes in the diff")
    attack_narrative: str | None = Field(
        default=None,
        description="If findings suggest a coordinated attack, describe the attack chain",
    )


class SynthesisResult(BaseModel):
    """Output from Pass 3: Synthesis (GPT-4o)"""
    risk_score: float = Field(ge=0.0, le=10.0, description="Overall risk score")
    risk_level: str = Field(description="none, low, medium, high, or critical")
    summary: str = Field(description="2-3 sentence executive summary")
    detailed_report: str = Field(description="Full Markdown-formatted analysis report")
    recommended_action: str = Field(
        description="One of: no_action, monitor, review_manually, block_update, alert_immediately"
    )
    false_positive_likelihood: float = Field(
        ge=0.0, le=1.0,
        description="Estimated probability that the findings are false positives",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization, e.g. ['data-exfiltration', 'npm', 'critical-package']",
    )
