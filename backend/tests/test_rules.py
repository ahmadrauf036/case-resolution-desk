from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.models import CaseInput, CaseStatus, CheckResult, Eligibility
from app.rules import DEADLINE, PKT, add_business_days, evaluate


def make(**kw):
    kw.setdefault("learner_name", "Test")
    kw.setdefault("question", "Am I eligible?")
    return CaseInput(**kw)


def result_of(res, rule):
    return next(c.result for c in res.checks if c.rule == rule)


# ---- 1. Thresholds -------------------------------------------------------
@pytest.mark.parametrize("field,value,rule,expected", [
    ("capstone_score", 69, "capstone", CheckResult.FAIL),
    ("capstone_score", 70, "capstone", CheckResult.PASS),
    ("attendance_pct", 79.9, "attendance", CheckResult.FAIL),
    ("attendance_pct", 80, "attendance", CheckResult.PASS),
    ("sessions", 2, "sessions", CheckResult.FAIL),
    ("sessions", 3, "sessions", CheckResult.PASS),
])
def test_thresholds(field, value, rule, expected):
    assert result_of(evaluate(make(**{field: value})), rule) == expected


# ---- 2. Unknowns and approvals ------------------------------------------
def test_unknown_attendance_is_pending_never_eligible():
    res = evaluate(make(sessions=3, capstone_score=80, submission_safe=True))
    assert res.eligibility == Eligibility.PENDING
    assert "Recorded attendance percentage" in res.missing_facts


def test_all_pass_and_safe_is_eligible_for_review():
    res = evaluate(make(attendance_pct=82, sessions=3, capstone_score=78, submission_safe=True))
    assert res.eligibility == Eligibility.ELIGIBLE
    assert res.suggested_status == CaseStatus.READY_FOR_REVIEW


def test_all_pass_but_submission_unchecked_is_pending():
    res = evaluate(make(attendance_pct=82, sessions=3, capstone_score=78))
    assert res.eligibility == Eligibility.PENDING


def test_extension_requested_but_not_approved_keeps_standard_due_date():
    res = evaluate(make(extension_requested=True))
    assert res.deadline.extension_state == "pending"
    assert res.deadline.effective_due == DEADLINE
    assert any("extension" in n.lower() for n in res.needs_approval)
    assert res.suggested_status == CaseStatus.WAITING_MENTOR


def test_approved_extension_moves_due_date_to_monday():
    res = evaluate(make(extension_requested=True, extension_approved=True))
    assert res.deadline.effective_due == datetime(2026, 10, 12, 17, 0, tzinfo=PKT)
    assert res.deadline.effective_due.weekday() == 0  # Monday


def test_approval_without_a_request_is_not_honoured():
    res = evaluate(make(extension_approved=True))
    assert res.deadline.effective_due == DEADLINE
    assert any("requested before the deadline" in m for m in res.missing_facts)


def test_late_extension_request_goes_to_human_review():
    res = evaluate(make(extension_requested=True, case_date=date(2026, 10, 10)))
    assert res.deadline.extension_state == "late_request"
    assert res.deadline.effective_due == DEADLINE


def test_makeup_approval_does_not_raise_session_count():
    res = evaluate(make(attendance_pct=85, sessions=2, makeup_approved=True,
                        capstone_score=80, submission_safe=True))
    assert res.eligibility == Eligibility.INELIGIBLE
    assert not res.needs_approval
    assert any("completed and recorded" in m for m in res.missing_facts)


def test_business_day_math():
    assert add_business_days(DEADLINE, 1).date() == date(2026, 10, 12)


# ---- 3. Acceptance cases A-D --------------------------------------------
def test_case_a_nadia():
    res = evaluate(make(learner_name="Nadia", attendance_pct=76, sessions=2, note_offered=True,
                        note_verified=False, extension_requested=True))
    assert res.eligibility == Eligibility.INELIGIBLE
    assert result_of(res, "attendance") == CheckResult.FAIL
    assert result_of(res, "sessions") == CheckResult.FAIL
    assert result_of(res, "capstone") == CheckResult.UNKNOWN
    assert res.suggested_status == CaseStatus.WAITING_MENTOR
    assert len(res.needs_approval) == 2            # makeup + extension
    assert res.deadline.extension_state == "pending"
    assert res.deadline.effective_due == DEADLINE
    assert any("medical note" in m for m in res.missing_facts)
    assert {"KB-01", "KB-02"} <= set(res.policy_ids)


def test_case_b_hamza_hold():
    res = evaluate(make(learner_name="Hamza", attendance_pct=82, sessions=3,
                        capstone_score=78, submission_safe=False))
    assert res.eligibility == Eligibility.ON_HOLD and res.hold
    assert res.suggested_status == CaseStatus.WAITING_LEARNER
    assert "KB-03" in res.policy_ids
    assert "rotate" in res.next_action


def test_case_c_sara_old_threshold_rejected():
    res = evaluate(make(learner_name="Sara", attendance_pct=85, sessions=3,
                        capstone_score=65, extension_requested=False))
    assert res.eligibility == Eligibility.INELIGIBLE
    assert result_of(res, "capstone") == CheckResult.FAIL
    assert "70" in next(c.detail for c in res.checks if c.rule == "capstone")
    assert res.deadline.standard_due == DEADLINE


def test_case_d_missing_data():
    res = evaluate(make())
    assert res.eligibility == Eligibility.PENDING
    assert res.suggested_status == CaseStatus.WAITING_LEARNER
    assert len(res.missing_facts) >= 3
    assert all(c.result == CheckResult.UNKNOWN for c in res.checks)


# ---- 4. Validation -------------------------------------------------------
@pytest.mark.parametrize("kw", [
    {"attendance_pct": 140}, {"attendance_pct": -1}, {"capstone_score": 110},
    {"sessions": -1}, {"sessions": 2.5},
])
def test_impossible_numbers_rejected(kw):
    with pytest.raises(ValidationError):
        make(**kw)