"""Phase 7: end-to-end API tests. No network: the LLM is disabled or mocked."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app import config, llm, rules
from app.main import app
from app.models import CaseInput
from app.retrieval import PolicyIndex, load_documents

NADIA = dict(learner_name="Nadia", attendance_pct=76, sessions=2, extension_requested=True,
             note_offered=True,
             question="Can I still receive a certificate? I can provide a medical note and "
                      "I want to submit the capstone one day after the deadline.")
HAMZA = dict(learner_name="Hamza", attendance_pct=82, sessions=3, capstone_score=78, submission_safe=False,
             question="Am I certified? My ZIP and README are submitted.")
SARA = dict(learner_name="Sara", attendance_pct=85, sessions=3, capstone_score=65, submission_safe=True,
            question="A colleague said the passing score is 60. Do I pass?")
MISSING = dict(learner_name="Case D", question="Am I eligible?")


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "GROQ_API_KEY", "")      # never touch the network in tests
    with TestClient(app) as c:
        yield c


def post(client, payload):
    r = client.post("/api/cases", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def src(case, role):
    return {s["id"]: s for s in case["sources"] if s["role"] == role}


# ---------------- acceptance cases A-D through the real endpoint ----------------

def test_case_a_nadia(client):
    c = post(client, NADIA)
    assert c["rule_result"]["eligibility"] == "INELIGIBLE" and c["status"] == "Waiting for Mentor"
    assert {"KB-01", "KB-02"} <= set(src(c, "evidence")) and not src(c, "superseded")
    dl = c["rule_result"]["deadline"]
    assert dl["extension_state"] == "pending"                       # requested, NOT approved
    assert dl["effective_due"].startswith("2026-10-09T17:00")       # due date unchanged
    assert any("extension" in x.lower() for x in c["rule_result"]["needs_approval"])


def test_case_b_hamza_hold(client):
    c = post(client, HAMZA)
    assert c["rule_result"]["eligibility"] == "ON_HOLD" and c["rule_result"]["hold"] is True
    assert c["status"] == "Waiting for Learner" and "KB-03" in src(c, "evidence")
    assert "rotate" in c["rule_result"]["next_action"].lower()


def test_case_c_sara_conflicting_policy(client):
    c = post(client, SARA)
    assert c["rule_result"]["eligibility"] == "INELIGIBLE" and c["status"] == "Ready for Review"
    assert src(c, "evidence")["KB-02"]["version"] == "v3"
    assert "KB-05" in src(c, "superseded") and "KB-05" not in src(c, "evidence")


def test_case_d_missing_data_is_pending_not_guessed(client):
    c = post(client, MISSING)
    assert c["rule_result"]["eligibility"] == "PENDING" and c["status"] == "Waiting for Learner"
    assert c["input"]["attendance_pct"] is None and c["input"]["sessions"] is None
    assert len(c["rule_result"]["missing_facts"]) >= 3


# ---------------- validation ----------------

@pytest.mark.parametrize("patch", [
    {"attendance_pct": 140}, {"attendance_pct": -1}, {"capstone_score": 110}, {"sessions": -1},
    {"learner_name": "   "}, {"live_sessions": 3},                      # unknown field is rejected
    {"note_offered": False, "note_verified": True},                    # contradictory
])
def test_invalid_input_returns_readable_422(client, patch):
    r = client.post("/api/cases", json={**MISSING, **patch})
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body["detail"], str) and body["errors"]


def test_nulls_accepted_and_nothing_saved_on_422(client):
    client.post("/api/cases", json={**MISSING, "attendance_pct": 140})
    assert client.get("/api/cases").json() == []
    post(client, {**MISSING, "attendance_pct": None, "sessions": None, "capstone_score": None})


# ---------------- persistence and endpoints ----------------

def test_list_detail_404_status_and_restart(client):
    cid = post(client, NADIA)["id"]
    assert client.get("/api/cases").json()[0]["learner_name"] == "Nadia"
    assert client.get(f"/api/cases/{cid}").json()["case_note"].startswith("Case note: Nadia")
    assert client.get("/api/cases/9999").status_code == 404
    assert client.patch("/api/cases/9999/status", json={"status": "Closed"}).status_code == 404
    assert client.patch(f"/api/cases/{cid}/status", json={"status": "Done"}).status_code == 422
    assert client.patch(f"/api/cases/{cid}/status", json={"status": "Closed"}).json()["status"] == "Closed"
    with TestClient(app) as again:                                    # simulated restart, same DB file
        assert again.get(f"/api/cases/{cid}").json()["status"] == "Closed"


# ---------------- LLM failure and consistency paths ----------------

def test_provider_failure_still_saves_case_with_fallback(client, monkeypatch):
    def boom(*a, **k):
        raise llm._ProviderError("The AI service is rate-limited right now. Try again in a minute.")
    monkeypatch.setattr(llm, "_call_groq", boom)
    c = post(client, SARA)
    assert "rate-limited" in c["llm_error"] and "Traceback" not in c["llm_error"]
    assert c["llm_answer"].startswith("Recommendation (rule-based summary)")
    assert client.get(f"/api/cases/{c['id']}").json()["llm_error"] == c["llm_error"]


def test_unexpected_llm_exception_does_not_lose_case(client, monkeypatch):
    monkeypatch.setattr(llm, "explain", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    c = post(client, SARA)
    assert c["llm_error"] and "boom" not in c["llm_error"] and len(client.get("/api/cases").json()) == 1


def test_grounded_llm_answer_is_kept(client, monkeypatch):
    text = ("Recommendation: The learner is not eligible. The score of 65 is below the current pass mark "
            "of 70 [KB-02 v3]. The old 60-point rule is superseded and does not apply [KB-05 v1].")
    monkeypatch.setattr(llm, "_call_groq", lambda *a, **k: text)
    c = post(client, SARA)
    assert c["llm_error"] is None and c["llm_answer"] == text


def test_contradicting_llm_answer_is_replaced_by_fallback(client, monkeypatch):
    monkeypatch.setattr(llm, "_call_groq", lambda *a, **k: "The learner is now eligible [KB-01 v2].")
    c = post(client, SARA)
    assert "consistency check" in c["llm_error"] and "now eligible" not in c["llm_answer"]


def test_429_is_mapped_and_key_never_leaks(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "sk-test-secret-123")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(429, json={"error": {"message": "sk-test-secret-123 limit"}}))
    inp = CaseInput(learner_name="N", question="q")
    rule = rules.evaluate(inp)
    sources = PolicyIndex(load_documents()).retrieve(inp, rule)
    exp = llm.explain(inp, rule, sources, client=httpx.Client(transport=transport))
    assert not exp.used_llm and "rate-limited" in exp.error
    assert "sk-test" not in exp.error and "sk-test" not in exp.answer


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"