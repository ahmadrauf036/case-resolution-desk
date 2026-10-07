"""KB-04 case note: facts, policy IDs/versions used, unresolved items, next action."""
from .models import CaseInput, RuleResult, SourceRef


def _val(x, suffix: str = "") -> str:
    return "unknown" if x is None else f"{x:g}{suffix}"


def _decision(requested, approved) -> str:
    if requested is not True:
        return "not requested"
    return {True: "approved", False: "denied", None: "pending (no decision recorded)"}[approved]


def build_case_note(inp: CaseInput, rule: RuleResult, sources: list[SourceRef]) -> str:
    safe = {True: "safe", False: "SECRET FOUND (on hold)", None: "not checked"}[inp.submission_safe]
    note = ("not offered" if not inp.note_offered else
            "offered, verified" if inp.note_verified else "offered, not verified")
    makeup = {True: "approved", False: "denied", None: "no decision recorded"}[inp.makeup_approved]

    used = ", ".join(f"{s.id} {s.version}" for s in sources if s.role == "evidence")
    old = ", ".join(f"{s.id} {s.version}" for s in sources if s.role == "superseded")
    unresolved = [*rule.needs_approval, *rule.missing_facts]

    lines = [
        f"Case note: {inp.learner_name} ({inp.case_date.isoformat()})",
        f"Question: {inp.question[:300]}",
        f"Facts: attendance {_val(inp.attendance_pct, '%')}; live sessions {_val(inp.sessions)}; "
        f"capstone {_val(inp.capstone_score)}; submission {safe}; medical note {note}; "
        f"extension {_decision(inp.extension_requested, inp.extension_approved)}; makeup {makeup}.",
        f"Due date in force: {rule.deadline.effective_due:%a %d %b %Y %H:%M} PKT.",
        f"Outcome: {rule.eligibility.value}; suggested status: {rule.suggested_status.value}.",
        f"Policies used: {used}." + (f" Superseded, not used for the decision: {old}." if old else ""),
        "Unresolved: " + ("; ".join(unresolved) if unresolved else "none") + ".",
        f"Next action: {rule.next_action}",
    ]
    return "\n".join(lines)