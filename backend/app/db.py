"""SQLite persistence (stdlib only). One short-lived connection per call."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from . import config
from .models import (
    CaseInput, CaseOut, CaseStatus, CaseSummary, Eligibility, RuleResult, SourceRef,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_name     TEXT NOT NULL,
    question         TEXT NOT NULL,
    inputs_json      TEXT NOT NULL,
    rule_result_json TEXT NOT NULL,
    sources_json     TEXT NOT NULL,
    llm_answer       TEXT,
    llm_error        TEXT,
    eligibility      TEXT NOT NULL,
    status           TEXT NOT NULL,
    next_action      TEXT NOT NULL,
    case_note        TEXT NOT NULL,
    created_at       TEXT NOT NULL
)
"""


def _connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str | None = None) -> None:
    with closing(_connect(path)) as conn, conn:
        conn.execute(SCHEMA)


def _to_case(row: sqlite3.Row) -> CaseOut:
    return CaseOut(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        input=CaseInput.model_validate_json(row["inputs_json"]),
        rule_result=RuleResult.model_validate_json(row["rule_result_json"]),
        sources=[SourceRef.model_validate(s) for s in json.loads(row["sources_json"])],
        llm_answer=row["llm_answer"],
        llm_error=row["llm_error"],
        status=CaseStatus(row["status"]),
        case_note=row["case_note"],
    )


def insert_case(inp: CaseInput, rule: RuleResult, sources: list[SourceRef], case_note: str,
                llm_answer: str | None = None, llm_error: str | None = None,
                path: str | None = None) -> CaseOut:
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute(
            """INSERT INTO cases (learner_name, question, inputs_json, rule_result_json, sources_json,
                                  llm_answer, llm_error, eligibility, status, next_action, case_note, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (inp.learner_name, inp.question, inp.model_dump_json(), rule.model_dump_json(),
             json.dumps([s.model_dump(mode="json") for s in sources]),
             llm_answer, llm_error, rule.eligibility.value, rule.suggested_status.value,
             rule.next_action, case_note, datetime.now(timezone.utc).isoformat()),
        )
        case_id = cur.lastrowid
    return get_case(case_id, path)


def get_case(case_id: int, path: str | None = None) -> CaseOut | None:
    with closing(_connect(path)) as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return _to_case(row) if row else None


def list_cases(path: str | None = None) -> list[CaseSummary]:
    with closing(_connect(path)) as conn:
        rows = conn.execute(
            "SELECT id, created_at, learner_name, eligibility, status FROM cases ORDER BY id DESC"
        ).fetchall()
    return [CaseSummary(id=r["id"], created_at=datetime.fromisoformat(r["created_at"]),
                        learner_name=r["learner_name"], eligibility=Eligibility(r["eligibility"]),
                        status=CaseStatus(r["status"])) for r in rows]


def update_status(case_id: int, status: CaseStatus, path: str | None = None) -> CaseOut | None:
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute("UPDATE cases SET status = ? WHERE id = ?", (status.value, case_id))
        if cur.rowcount == 0:
            return None
    return get_case(case_id, path)