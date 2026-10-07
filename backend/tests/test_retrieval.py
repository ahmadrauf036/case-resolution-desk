from datetime import date

import pytest

from app.models import CaseInput
from app.retrieval import PolicyIndex, load_documents
from app.rules import evaluate


@pytest.fixture(scope="module")
def index():
    return PolicyIndex(load_documents())


def run(index, **kw):
    kw.setdefault("learner_name", "T")
    kw.setdefault("question", "Am I eligible?")
    inp = CaseInput(**kw)
    return index.retrieve(inp, evaluate(inp))


def ids(refs, role):
    return {r.id for r in refs if r.role == role}


NADIA = dict(question="Can I still get a certificate? I missed a session, I have a medical note, "
                      "and I want to submit my capstone one day late.",
             attendance_pct=76, sessions=2, note_offered=True, extension_requested=True)
HAMZA = dict(attendance_pct=82, sessions=3, capstone_score=78, submission_safe=False)
SARA = dict(question="A colleague said the passing score is 60. Am I certified?",
            attendance_pct=85, sessions=3, capstone_score=65)


@pytest.mark.parametrize("case", [NADIA, HAMZA, SARA, {}])
def test_superseded_kb05_is_never_evidence(index, case):
    assert "KB-05" not in ids(run(index, **case), "evidence")


def test_sara_gets_current_kb02_and_superseded_kb05(index):
    refs = run(index, **SARA)
    assert "KB-02" in ids(refs, "evidence")
    kb05 = next(r for r in refs if r.id == "KB-05")
    assert kb05.role == "superseded" and kb05.superseded_by == "KB-02 v3"
    assert kb05.snippet.startswith("SUPERSEDED by KB-02 v3")
    kb02 = next(r for r in refs if r.id == "KB-02")
    assert kb02.version == "v3" and "17:00 PKT" in kb02.snippet


def test_old_policy_phrase_alone_triggers_superseded_note(index):
    refs = run(index, question="My handout says 60 is enough to pass")
    assert ids(refs, "superseded") == {"KB-05"}


def test_nadia_cites_kb01_kb02_and_workflow_not_kb05(index):
    refs = run(index, **NADIA)
    assert {"KB-01", "KB-02", "KB-04"} <= ids(refs, "evidence")
    assert not ids(refs, "superseded")
    kb01 = next(r for r in refs if r.id == "KB-01")
    assert "Makeup sessions" in kb01.snippet and "Medical absence" in kb01.snippet


def test_hamza_cites_submission_hold(index):
    kb03 = next(r for r in run(index, **HAMZA) if r.id == "KB-03")
    assert "Submission on hold" in kb03.snippet


def test_policy_not_yet_effective_is_excluded(index):
    refs = run(index, case_date=date(2026, 9, 15))
    assert "KB-02" not in ids(refs, "evidence")     # effective 1 Oct 2026


def test_question_outside_policies_surfaces_kb04_note(index):
    kb04 = next(r for r in run(index, question="Do I have to pay fees or get a stipend?") if r.id == "KB-04")
    assert "Answer outside the policies" in kb04.snippet