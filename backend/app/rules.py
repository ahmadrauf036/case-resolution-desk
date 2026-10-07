"""Deterministic business rules. Pure functions: no I/O, no LLM, no randomness.

The LLM may explain these results but can never change them.
"""
from datetime import date, datetime, time, timedelta, timezone

from .models import (
    CaseInput, CaseStatus, Check, CheckResult, DeadlineInfo, Eligibility,
    ExtensionState, RuleResult,
)

PKT = timezone(timedelta(hours=5))

ATTENDANCE_MIN = 80.0                       # KB-01
SESSIONS_MIN = 3                            # KB-01
CAPSTONE_MIN = 70.0                         # KB-02 v3
MAKEUP_WINDOW_DAYS = 7                      # KB-01
DEADLINE = datetime(2026, 10, 9, 17, 0, tzinfo=PKT)   # KB-02 v3
CAPSTONE_POLICY_EFFECTIVE = date(2026, 10, 1)
CASE_TIME = time(11, 0)                     # assumed time of day of a case (PKT)


# ---------- helpers ----------

def add_business_days(dt: datetime, n: int) -> datetime:
    """Mon-Fri are business days, no holidays (KB-02)."""
    while n > 0:
        dt += timedelta(days=1)
        if dt.weekday() < 5:
            n -= 1
    return dt


def case_datetime(d: date) -> datetime:
    return datetime.combine(d, CASE_TIME, tzinfo=PKT)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%a %d %b %Y %H:%M PKT")


# ---------- individual checks ----------

def check_attendance(v: float | None) -> Check:
    base = dict(rule="attendance", label="Attendance at least 80%", source="KB-01")
    if v is None:
        return Check(**base, result=CheckResult.UNKNOWN,
                     detail="Attendance is not recorded; it is kept unknown, not assumed.")
    if v >= ATTENDANCE_MIN:
        return Check(**base, result=CheckResult.PASS, detail=f"Recorded {v:g}% meets the 80% minimum.")
    return Check(**base, result=CheckResult.FAIL,
                 detail=f"Recorded {v:g}% is below the 80% minimum (no rounding up).")


def check_sessions(v: int | None) -> Check:
    base = dict(rule="sessions", label="At least 3 live sessions", source="KB-01")
    if v is None:
        return Check(**base, result=CheckResult.UNKNOWN,
                     detail="Live-session count is not recorded; it is kept unknown, not assumed.")
    if v >= SESSIONS_MIN:
        return Check(**base, result=CheckResult.PASS, detail=f"{v} live sessions meets the minimum of 3.")
    return Check(**base, result=CheckResult.FAIL,
                 detail=f"{v} live session(s) is below the minimum of 3.")


def check_capstone(v: float | None) -> Check:
    base = dict(rule="capstone", label="Capstone score at least 70/100", source="KB-02")
    if v is None:
        return Check(**base, result=CheckResult.UNKNOWN,
                     detail="No capstone score recorded, so a pass is not confirmed.")
    if v >= CAPSTONE_MIN:
        return Check(**base, result=CheckResult.PASS, detail=f"Score {v:g} meets the pass mark of 70.")
    extra = " The superseded 60-point rule does not apply." if v >= 60 else ""
    return Check(**base, result=CheckResult.FAIL,
                 detail=f"Score {v:g} is below the current pass mark of 70.{extra}")


def check_submission(safe: bool | None) -> Check:
    base = dict(rule="submission", label="Submission safe to review", source="KB-03")
    if safe is None:
        return Check(**base, result=CheckResult.UNKNOWN,
                     detail="Submission has not been checked for secrets yet.")
    if safe:
        return Check(**base, result=CheckResult.PASS, detail="No secrets reported in the submission.")
    return Check(**base, result=CheckResult.FAIL,
                 detail="A secret was found in the submission. It is on hold until a clean replacement is confirmed.")


# ---------- deadline / extension ----------

def extension_state(inp: CaseInput, now: datetime) -> ExtensionState:
    if inp.extension_requested is not True:
        return "not_requested"
    if now >= DEADLINE:
        return "late_request"          # no automatic path; needs human review
    if inp.extension_approved is True:
        return "approved"
    if inp.extension_approved is False:
        return "denied"
    return "pending"


def deadline_info(inp: CaseInput, now: datetime) -> DeadlineInfo:
    state = extension_state(inp, now)
    extended = add_business_days(DEADLINE, 1)
    effective = extended if state == "approved" else DEADLINE
    before = now < DEADLINE
    notes = {
        "not_requested": (
            f"No extension requested. The standard due date {_fmt(DEADLINE)} applies. "
            "A request must be made before that time and approved by a mentor."
            if before else
            f"No extension requested and the deadline {_fmt(DEADLINE)} has passed; the standard due date applies."),
        "pending": (f"Extension requested but not approved. The standard due date {_fmt(DEADLINE)} "
                    "stays in force until a mentor records approval."),
        "approved": f"Mentor-approved extension recorded. Individual due date is {_fmt(extended)}.",
        "denied": f"Extension was denied. The standard due date {_fmt(DEADLINE)} applies.",
        "late_request": (f"The request was made at or after the deadline {_fmt(DEADLINE)}. KB-02 gives no "
                         "automatic extension; refer for human review without promising acceptance."),
    }
    return DeadlineInfo(
        standard_due=DEADLINE, effective_due=effective, extension_state=state,
        can_still_request=before and state == "not_requested",
        is_past_due=now >= effective, note=notes[state],
    )


# ---------- main entry point ----------

def evaluate(inp: CaseInput) -> RuleResult:
    now = case_datetime(inp.case_date)
    checks = [
        check_attendance(inp.attendance_pct),
        check_sessions(inp.sessions),
        check_capstone(inp.capstone_score),
        check_submission(inp.submission_safe),
    ]
    by = {c.rule: c for c in checks}
    deadline = deadline_info(inp, now)

    hold = inp.submission_safe is False
    any_fail = any(c.result == CheckResult.FAIL for c in checks)
    any_unknown = any(c.result == CheckResult.UNKNOWN for c in checks)

    if hold:
        eligibility = Eligibility.ON_HOLD
    elif any_fail:
        eligibility = Eligibility.INELIGIBLE
    elif any_unknown:
        eligibility = Eligibility.PENDING
    else:
        eligibility = Eligibility.ELIGIBLE

    needs_approval: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []

    if inp.case_date < CAPSTONE_POLICY_EFFECTIVE:
        warnings.append("Case date is before 1 Oct 2026. This pack only keeps the old score and cutoff; "
                        "it is not a full historical record.")

    # Unknown scored facts
    if by["attendance"].result == CheckResult.UNKNOWN:
        missing.append("Recorded attendance percentage")
    if by["sessions"].result == CheckResult.UNKNOWN:
        missing.append("Number of live sessions attended")
    if by["capstone"].result == CheckResult.UNKNOWN:
        missing.append("Capstone score")
    if by["submission"].result == CheckResult.UNKNOWN and eligibility != Eligibility.INELIGIBLE:
        missing.append("Confirmation that the submission is safe to review (secret check)")

    # Secret on hold (KB-03)
    if hold:
        missing.append("Clean replacement submission (secret removed, key rotated) confirmed safe by the coordinator")

    # Attendance / session gaps and the medical note (KB-01)
    att_fail = by["attendance"].result == CheckResult.FAIL
    ses_fail = by["sessions"].result == CheckResult.FAIL
    if att_fail or ses_fail:
        if inp.note_verified is True:
            missing.append("Coordinator to record the corrected attendance/session figures; "
                           "until then the existing record applies")
        elif inp.note_offered is True:
            missing.append("Coordinator verification of the medical note (a note alone does not waive any requirement)")

    # Makeup path (KB-01): only one missed session can be made up
    if ses_fail:
        gap = SESSIONS_MIN - (inp.sessions or 0)
        if gap > 1:
            warnings.append(f"The learner is {gap} sessions short; KB-01 allows only one missed live session "
                            "to be made up.")
        elif inp.makeup_approved is False:
            warnings.append("The makeup session was denied by the mentor.")
        else:
            window_end = None
            if inp.missed_session_date:
                window_end = inp.missed_session_date + timedelta(days=MAKEUP_WINDOW_DAYS)
            if window_end and inp.case_date > window_end:
                warnings.append(f"The 7-day makeup window ended on {window_end.isoformat()}; "
                                "the makeup option no longer applies.")
            elif inp.makeup_approved is True:
                missing.append("Approved makeup session must actually be completed and recorded "
                               "(the session count does not change until then)")
            else:
                needs_approval.append("Mentor approval for one makeup live session (KB-01), "
                                      "within 7 calendar days of the missed session")
                if inp.missed_session_date is None:
                    missing.append("Date of the missed live session (to check the 7-day makeup window)")

    # Extension (KB-02)
    if deadline.extension_state == "pending":
        needs_approval.append("Mentor decision on the one-business-day extension (KB-02); "
                              "the standard due date stays in force until approved")
    elif deadline.extension_state == "late_request":
        needs_approval.append("Human review of an extension requested at or after the deadline (KB-02); "
                              "acceptance is not promised")
    if inp.extension_approved is True and inp.extension_requested is not True:
        missing.append("Evidence the extension was requested before the deadline (KB-02 requires both request and approval)")

    # Status (KB-04): one displayed status; both blockers stay visible in the lists
    if hold:
        status = CaseStatus.WAITING_LEARNER
    elif needs_approval:
        status = CaseStatus.WAITING_MENTOR
    elif missing:
        status = CaseStatus.WAITING_LEARNER
    else:
        status = CaseStatus.READY_FOR_REVIEW

    # Next actions
    actions: list[str] = []
    if hold:
        actions.append("Ask the learner to remove the secret, revoke/rotate the exposed key, and send a clean "
                       "replacement; do not issue a pass decision until the coordinator confirms it is safe.")
    for item in needs_approval:
        actions.append(f"Mentor action needed: {item}.")
    if missing and not hold:
        actions.append("Obtain: " + "; ".join(missing) + ".")
    unmet = [c.label for c in checks if c.result == CheckResult.FAIL and c.rule != "submission"]
    if eligibility == Eligibility.INELIGIBLE:
        actions.append("On the current record the certificate cannot be issued (unmet: "
                       + ", ".join(unmet) + "). Refer any dispute to the coordinator.")
    if eligibility == Eligibility.ELIGIBLE and not actions:
        actions.append("Send to a human reviewer to confirm the result; this tool does not issue certificates.")
    if eligibility == Eligibility.PENDING and not actions:
        actions.append("Complete the missing checks and re-run the analysis.")

    policy_ids = ["KB-01", "KB-02"]
    if inp.submission_safe is not None:
        policy_ids.append("KB-03")

    return RuleResult(
        eligibility=eligibility, checks=checks, missing_facts=missing, needs_approval=needs_approval,
        hold=hold, suggested_status=status, next_action=actions[0], next_actions=actions,
        warnings=warnings, deadline=deadline, policy_ids=policy_ids,
    )