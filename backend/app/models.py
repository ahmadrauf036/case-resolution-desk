"""Request/response contract. Strict validation lives here."""
from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import config


class CheckResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class Eligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"   # on the current record
    PENDING = "PENDING"         # unresolved facts, nothing confirmed failing
    ON_HOLD = "ON_HOLD"         # unsafe submission (KB-03)


class CaseStatus(str, Enum):    # KB-04 workflow statuses
    OPEN = "Open"
    WAITING_LEARNER = "Waiting for Learner"
    WAITING_MENTOR = "Waiting for Mentor"
    READY_FOR_REVIEW = "Ready for Review"
    CLOSED = "Closed"


ExtensionState = Literal[
    "not_requested", "pending", "approved", "denied", "late_request"
]


class CaseInput(BaseModel):
    """What the coordinator enters. None always means 'unknown / not recorded'."""

    # forbid: a misspelled field (e.g. "live_sessions") is an error, not a silent "unknown"
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    learner_name: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)

    attendance_pct: Optional[float] = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    sessions: Optional[int] = Field(default=None, ge=0, le=100)
    capstone_score: Optional[float] = Field(default=None, ge=0, le=100, allow_inf_nan=False)

    # True = safe, False = secret found, None = not checked yet
    submission_safe: Optional[bool] = None

    # Extension: None = no decision recorded, True = approved, False = denied
    extension_requested: Optional[bool] = None
    extension_approved: Optional[bool] = None

    # Makeup session: None = no decision recorded, True = approved, False = denied
    makeup_approved: Optional[bool] = None
    missed_session_date: Optional[date] = None

    # Medical note: offered by the learner / verified by the coordinator
    note_offered: Optional[bool] = None
    note_verified: Optional[bool] = None

    case_date: date = Field(default_factory=lambda: config.DEFAULT_CASE_DATE)

    @model_validator(mode="after")
    def _note_consistency(self):
        if self.note_verified is True and self.note_offered is not True:
            raise ValueError("note_verified cannot be true unless note_offered is true")
        return self


class SourceRef(BaseModel):
    id: str
    version: str
    effective: date
    status: str                              # CURRENT | SUPERSEDED
    role: Literal["evidence", "superseded"]
    snippet: str
    superseded_by: Optional[str] = None      # e.g. "KB-02 v3" (superseded sources only)


class Check(BaseModel):
    rule: str                 # attendance | sessions | capstone | submission
    label: str
    result: CheckResult
    detail: str
    source: str               # policy ID, e.g. "KB-01"


class DeadlineInfo(BaseModel):
    standard_due: datetime
    effective_due: datetime
    extension_state: ExtensionState
    can_still_request: bool
    is_past_due: bool
    note: str


class RuleResult(BaseModel):
    eligibility: Eligibility
    checks: list[Check]
    missing_facts: list[str]
    needs_approval: list[str]
    hold: bool
    suggested_status: CaseStatus
    next_action: str
    next_actions: list[str]
    warnings: list[str]
    deadline: DeadlineInfo
    policy_ids: list[str]


class CaseOut(BaseModel):
    id: int
    created_at: datetime
    input: CaseInput
    rule_result: RuleResult
    sources: list[SourceRef]
    llm_answer: Optional[str] = None   # LLM text, or the rule-based fallback when llm_error is set
    llm_error: Optional[str] = None    # non-null => the fallback explanation was used
    status: CaseStatus
    case_note: str


class CaseSummary(BaseModel):
    id: int
    created_at: datetime
    learner_name: str
    eligibility: Eligibility
    status: CaseStatus


class StatusUpdate(BaseModel):
    status: CaseStatus