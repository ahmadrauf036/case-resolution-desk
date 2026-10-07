import httpx
import pytest

from app import config, llm
from app.db import get_case, init_db, insert_case
from app.models import CaseInput
from app.notes import build_case_note
from app.retrieval import PolicyIndex, load_documents
from app.rules import evaluate

KEY = "gsk_test_SECRET123"
INDEX = PolicyIndex(load_documents())


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", KEY)


def setup(**kw):
    kw.setdefault("learner_name", "T")
    kw.setdefault("question", "Am I eligible?")
    inp = CaseInput(**kw)
    rule = evaluate(inp)
    return inp, rule, INDEX.retrieve(inp, rule)


NADIA = dict(learner_name="Nadia", attendance_pct=76, sessions=2, note_offered=True, extension_requested=True,
             question="Can I still get a certificate? I have a medical note and want an extension.")
SARA = dict(learner_name="Sara", attendance_pct=85, sessions=3, capstone_score=65,
            question="A colleague said the passing score is 60. Am I certified?")


def client_returning(content=None, status=200, raises=None, seen=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        if raises:
            raise raises
        if status != 200:
            return httpx.Response(status, json={"error": {"message": f"boom {KEY}"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
    return httpx.Client(transport=httpx.MockTransport(handler))


GOOD = ("Recommendation: Nadia is not eligible on the current record [KB-01 v2]. "
        "Why: attendance 76% and 2 sessions are below the minimums. "
        "Pending: no extension has been approved yet [KB-02 v3]. Next action: ask the mentor.")


def test_success_returns_llm_text_and_sends_grounded_request():
    seen = []
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning(GOOD, seen=seen))
    assert out.used_llm and out.error is None and out.answer == GOOD
    req = seen[0]
    assert req.headers["authorization"] == f"Bearer {KEY}"
    body = req.content.decode()
    assert "RULE RESULT" in body and "INELIGIBLE" in body and "KB-01" in body


@pytest.mark.parametrize("status,word", [(429, "rate-limited"), (401, "credentials"), (500, "problems"), (404, "model")])
def test_provider_errors_give_safe_message_and_fallback(status, word):
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning(status=status))
    assert not out.used_llm and word in out.error
    assert KEY not in out.error and KEY not in out.answer and "Traceback" not in out.error
    assert "rule-based" in out.answer and "Not eligible" in out.answer


@pytest.mark.parametrize("exc", [httpx.ReadTimeout("t"), httpx.ConnectError("c")])
def test_timeout_and_network_errors_fall_back(exc):
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning(raises=exc))
    assert out.error and "rule-based" in out.answer


def test_missing_key_makes_no_http_call(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    seen = []
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning(GOOD, seen=seen))
    assert not seen and "not configured" in out.error


def test_unreadable_response_falls_back():
    inp, rule, src = setup(**NADIA)
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="not json")))
    assert "unreadable" in llm.explain(inp, rule, src, bad).error


@pytest.mark.parametrize("bad_text", [
    "Recommendation: Nadia is eligible for a certificate [KB-01 v2].",
    "Recommendation: not eligible. The extension has been approved [KB-02 v3].",
    "Recommendation: not eligible [KB-09 v1].",
    "Recommendation: not eligible [KB-01 v7].",
    "Recommendation: the makeup session has been approved [KB-01 v2].",
])
def test_inconsistent_llm_output_is_rejected(bad_text):
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning(bad_text))
    assert not out.used_llm and "consistency check" in out.error
    assert "rule-based" in out.answer


def test_old_60_rule_must_be_marked_superseded():
    inp, rule, src = setup(**SARA)
    out = llm.explain(inp, rule, src, client_returning("Recommendation: 60 is the passing score [KB-02 v3]."))
    assert not out.used_llm
    ok = ("Recommendation: not certified; the pass mark is 70 [KB-02 v3]. The 60-point rule in KB-05 v1 "
          "is superseded and does not apply.")
    assert llm.explain(inp, rule, src, client_returning(ok)).used_llm


def test_missing_citation_gets_sources_line_appended():
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning("Recommendation: not eligible on the current record."))
    assert out.used_llm and "Sources: KB-01 v2" in out.answer


def test_fallback_for_sara_explains_superseded_rule():
    inp, rule, src = setup(**SARA)
    text = llm.fallback_explanation(inp, rule, src)
    assert "pass mark of 70" in text and "KB-05 v1 is superseded by KB-02 v3" in text
    assert "17:00 PKT" in text


def test_case_is_still_saved_when_provider_fails(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    inp, rule, src = setup(**NADIA)
    out = llm.explain(inp, rule, src, client_returning(status=429))
    saved = insert_case(inp, rule, src, build_case_note(inp, rule, src), out.answer, out.error, path=db)
    loaded = get_case(saved.id, db)
    assert "rate-limited" in loaded.llm_error and loaded.rule_result.eligibility.value == "INELIGIBLE"