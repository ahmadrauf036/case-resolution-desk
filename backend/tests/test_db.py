import pytest

from app.db import get_case, init_db, insert_case, list_cases, update_status
from app.models import CaseInput, CaseStatus, Eligibility
from app.notes import build_case_note
from app.retrieval import PolicyIndex, load_documents
from app.rules import evaluate


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def save(db, **kw):
    kw.setdefault("learner_name", "Nadia")
    kw.setdefault("question", "Am I eligible?")
    inp = CaseInput(**kw)
    rule = evaluate(inp)
    sources = PolicyIndex(load_documents()).retrieve(inp, rule)
    return insert_case(inp, rule, sources, build_case_note(inp, rule, sources), path=db)


def test_roundtrip_preserves_everything(db):
    saved = save(db, attendance_pct=76, sessions=2, extension_requested=True)
    loaded = get_case(saved.id, db)
    assert loaded.input.attendance_pct == 76
    assert loaded.rule_result.eligibility == Eligibility.INELIGIBLE
    assert loaded.status == CaseStatus.WAITING_MENTOR
    assert {s.id for s in loaded.sources} >= {"KB-01", "KB-02"}
    assert loaded.llm_answer is None and loaded.llm_error is None


def test_list_is_newest_first_and_missing_case_is_none(db):
    a = save(db, learner_name="First")
    b = save(db, learner_name="Second")
    assert [c.id for c in list_cases(db)] == [b.id, a.id]
    assert get_case(999, db) is None


def test_status_update_persists(db):
    saved = save(db)
    assert update_status(saved.id, CaseStatus.CLOSED, db).status == CaseStatus.CLOSED
    assert get_case(saved.id, db).status == CaseStatus.CLOSED
    assert update_status(999, CaseStatus.OPEN, db) is None


def test_case_note_contains_kb04_elements(db):
    note = save(db, attendance_pct=76, sessions=2, note_offered=True, extension_requested=True).case_note
    for part in ["Facts:", "Policies used: KB-01 v2", "Unresolved:", "Next action:", "medical note offered, not verified"]:
        assert part in note