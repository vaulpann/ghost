from pydantic import BaseModel


class AuditRequest(BaseModel):
    audit_id: str
    package_name: str
    registry: str  # npm, pypi, github
    version: str
    tarball_url: str | None = None
    callback_url: str | None = None


class AuditStatusResponse(BaseModel):
    audit_id: str
    status: str  # accepted, downloading, discovery, validation, complete, failed
    progress: str | None = None
    error: str | None = None


class DiscoveryFinding(BaseModel):
    category: str
    subcategory: str | None = None
    severity: str
    title: str
    description: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    attack_vector: str | None = None
    impact: str | None = None
    cwe_id: str | None = None
    confidence: float = 0.5


class ValidatedVulnerability(BaseModel):
    original_index: int
    validated: bool
    confidence: float
    reasoning: str
    severity_adjusted: str | None = None
    poc_code: str | None = None
    poc_description: str | None = None
    cvss_score: float | None = None
    remediation: str | None = None


class AuditResult(BaseModel):
    audit_id: str
    status: str
    discovery_findings: list[DiscoveryFinding] = []
    validated_vulnerabilities: list[ValidatedVulnerability] = []
    rejected_indices: list[int] = []
    discovery_model: str | None = None
    discovery_tokens_used: int | None = None
    discovery_duration_secs: float | None = None
    validation_model: str | None = None
    validation_tokens_used: int | None = None
    validation_duration_secs: float | None = None
    total_cost_usd: float | None = None
    source_size_bytes: int | None = None
    source_file_count: int | None = None
    error: str | None = None
