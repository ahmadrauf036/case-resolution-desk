"""Policy loading (Phase 1). Search/ranking is added in Phase 4."""
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .config import POLICY_DIR
from .models import CaseInput, CheckResult, RuleResult, SourceRef

CURRENT = "CURRENT"
SUPERSEDED = "SUPERSEDED"


@dataclass
class Section:
    heading: str
    text: str


@dataclass
class Document:
    id: str
    version: str
    effective: date
    status: str                      # CURRENT | SUPERSEDED
    title: str
    text: str
    sections: list[Section] = field(default_factory=list)
    superseded_by: str | None = None          # e.g. "KB-02"
    superseded_by_version: str | None = None  # e.g. "v3"

    @property
    def label(self) -> str:
        return f"{self.id} {self.version}"


def _header(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"missing header '{key}'")
    return m.group(1).strip()


def _split_sections(text: str) -> list[Section]:
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return [Section(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def parse_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    try:
        title = re.search(r"^#\s+KB-\d+:\s*(.+)$", text, re.MULTILINE).group(1).strip()
        doc_id = _header(text, "Document ID")
        version = _header(text, "Version")
        effective = datetime.strptime(_header(text, "Effective date"), "%d %b %Y").date()
        raw_status = _header(text, "Status")
    except (AttributeError, ValueError) as e:
        raise ValueError(f"{path.name}: bad or missing metadata ({e})") from e

    status, sup_by, sup_ver = CURRENT, None, None
    if raw_status.upper().startswith("SUPERSEDED"):
        status = SUPERSEDED
        m = re.search(r"(KB-\d+)\s*(v\d+)?", raw_status)
        if m:
            sup_by, sup_ver = m.group(1), m.group(2)
    elif raw_status.upper() != CURRENT:
        raise ValueError(f"{path.name}: unknown status '{raw_status}'")

    return Document(doc_id, version, effective, status, title, text,
                    _split_sections(text), sup_by, sup_ver)


def load_documents(policy_dir: Path = POLICY_DIR) -> list[Document]:
    docs = [parse_document(p) for p in sorted(policy_dir.glob("KB-*.md"))]
    if not docs:
        raise FileNotFoundError(f"no KB-*.md files in {policy_dir}")
    return docs

# =====================================================================
# Phase 4: version-aware retrieval
# =====================================================================
_STOP = frozenset(
    "a an and are as at be by can for from has have how i if in is it me my of on or the to was we "
    "what when who will with you your do does this that than then so".split()
)
MIN_DISCOVERY_SCORE = 0.25   # question-only matches below this are ignored
MIN_EXTRA_SCORE = 0.25       # extra TF-IDF section per document

_OLD_POLICY_RE = re.compile(
    r"\b60\b|old(er)?\s+(policy|rule|score|handout)|previous|archive|superseded|colleague|"
    r"18:00|6\s*pm|earlier cohort", re.I)


def _tokens(text: str) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9]+", text.lower()):
        if t in _STOP:
            continue
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]                      # crude plural stemming
        out.append(t)
    return out


@dataclass
class _Entry:
    doc: Document
    section: Section
    vec: dict[str, float]


class PolicyIndex:
    """Section-level TF-IDF index plus rule-driven citation selection."""

    def __init__(self, docs: list[Document]):
        self.docs = {d.id: d for d in docs}
        pairs = [(d, s) for d in docs for s in d.sections]
        toks = [_tokens(f"{s.heading} {s.text}") for _, s in pairs]
        df = Counter(t for ts in toks for t in set(ts))
        n = len(pairs)
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self._entries = [_Entry(d, s, self._vec(ts)) for (d, s), ts in zip(pairs, toks)]

    def _vec(self, tokens: list[str]) -> dict[str, float]:
        v = {t: c * self._idf[t] for t, c in Counter(tokens).items() if t in self._idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def search(self, query: str, allowed_ids=None) -> list[tuple[float, _Entry]]:
        q = self._vec(_tokens(query))
        scored = []
        for e in self._entries:
            if allowed_ids is not None and e.doc.id not in allowed_ids:
                continue
            scored.append((sum(w * e.vec.get(t, 0.0) for t, w in q.items()), e))
        scored.sort(key=lambda x: -x[0])
        return scored

    # ---- version guard ----
    def is_effective(self, doc: Document, on: date) -> bool:
        """Effective for the case date: started, and not yet replaced."""
        if doc.effective > on:
            return False
        if doc.status == SUPERSEDED:
            sup = self.docs.get(doc.superseded_by or "")
            return bool(sup) and on < sup.effective
        return True

    @staticmethod
    def old_policy_signal(inp: CaseInput) -> bool:
        if _OLD_POLICY_RE.search(inp.question):
            return True
        return inp.capstone_score is not None and 60 <= inp.capstone_score < 70

    # ---- rule-driven sections (deterministic citations) ----
    @staticmethod
    def _forced(inp: CaseInput, rule: RuleResult, conflict: bool) -> dict[str, list[str]]:
        res = {c.rule: c.result for c in rule.checks}
        att_ses_fail = CheckResult.FAIL in (res["attendance"], res["sessions"])
        state = rule.deadline.extension_state
        f: dict[str, list[str]] = {}

        k1 = ["Certificate requirements"]
        if att_ses_fail and (inp.note_offered or inp.note_verified):
            k1.append("Medical absence and evidence")
        if res["sessions"] == CheckResult.FAIL:
            k1.append("Makeup sessions")
        if CheckResult.UNKNOWN in (res["attendance"], res["sessions"]):
            k1.append("Attendance values")
        f["KB-01"] = k1

        k2 = ["Published deadline and pass score"]
        if state != "not_requested" or inp.extension_requested:
            k2 += ["Permitted extension", "Meaning of one business day"]
        if state == "late_request":
            k2.append("After-deadline requests")
        if state == "pending" or (inp.extension_approved and not inp.extension_requested):
            k2.append("Approval evidence")
        if conflict:
            k2.append("Version conflict")
        f["KB-02"] = k2

        if rule.hold:
            f["KB-03"] = ["Submission on hold", "Required learner action"]
        elif inp.submission_safe is not None:
            f["KB-03"] = ["Secrets must remain private"]

        k4 = [rule.suggested_status.value, "Minimum case note"]
        if rule.needs_approval and rule.missing_facts:
            k4.append("Multiple blockers")
        f["KB-04"] = k4
        return f

    def retrieve(self, inp: CaseInput, rule: RuleResult) -> list[SourceRef]:
        on = inp.case_date
        effective = {d.id for d in self.docs.values() if self.is_effective(d, on)}
        conflict = self.old_policy_signal(inp)
        forced = self._forced(inp, rule, conflict)

        order = [i for i in [*rule.policy_ids, "KB-04"] if i in effective]
        chosen: dict[str, list[str]] = {i: list(forced.get(i, [])) for i in order}

        # TF-IDF discovery from the question alone (e.g. fees -> KB-04 "outside the policies")
        for score, e in self.search(inp.question, effective)[:3]:
            if score >= MIN_DISCOVERY_SCORE:
                if e.doc.id not in chosen:
                    order.append(e.doc.id)
                    chosen[e.doc.id] = []
                if e.section.heading not in chosen[e.doc.id]:
                    chosen[e.doc.id].append(e.section.heading)

        # one extra best-matching section per document, from the full case context
        context = " ".join([
            inp.question, *rule.needs_approval, *rule.missing_facts, *rule.warnings,
            *[c.detail for c in rule.checks if c.result != CheckResult.PASS]])
        for doc_id in order:
            for score, e in self.search(context, {doc_id}):
                if score >= MIN_EXTRA_SCORE and e.section.heading not in chosen[doc_id]:
                    chosen[doc_id].append(e.section.heading)
                    break

        refs = []
        for doc_id in order:
            doc = self.docs[doc_id]
            secs = [s for s in doc.sections if s.heading in chosen[doc_id]]   # document order
            refs.append(self._ref(doc, secs, "evidence"))

        if conflict:
            for doc in self.docs.values():
                if doc.status != SUPERSEDED or doc.id in order:
                    continue
                sup = self.docs.get(doc.superseded_by or "")
                if not sup or sup.id not in effective:
                    continue
                heads = ["Archive notice", "Historical pass score"]
                if re.search(r"colleague|passed|cohort", inp.question, re.I):
                    heads.append("Learner claims")
                if re.search(r"deadline|due|18:00|6\s*pm", inp.question, re.I):
                    heads.append("Historical deadline time")
                secs = [s for s in doc.sections if s.heading in heads]
                refs.append(self._ref(doc, secs, "superseded"))
        return refs

    def _ref(self, doc: Document, secs: list[Section], role: str) -> SourceRef:
        body = "\n\n".join(f"[{s.heading}] {s.text}" for s in secs)
        sup_label = None
        if role == "superseded":
            sup = self.docs[doc.superseded_by]
            sup_label = sup.label
            body = (f"SUPERSEDED by {sup.label}. Historical only; not valid for cases on or after "
                    f"{sup.effective.day} {sup.effective:%b %Y}.\n\n" + body)
        return SourceRef(id=doc.id, version=doc.version, effective=doc.effective, status=doc.status,
                         role=role, snippet=body, superseded_by=sup_label)