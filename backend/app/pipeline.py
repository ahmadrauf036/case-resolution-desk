"""validate (done by pydantic) -> evaluate -> retrieve -> explain -> note -> persist.

Kept free of FastAPI so the whole flow can be tested without HTTP.
"""
import logging

from . import db, llm, notes, rules
from .models import CaseInput, CaseOut
from .retrieval import PolicyIndex

log = logging.getLogger("skillbridge")


def analyze(inp: CaseInput, index: PolicyIndex, db_path: str | None = None) -> CaseOut:
    rule = rules.evaluate(inp)              # the decision comes from code only
    sources = index.retrieve(inp, rule)

    try:
        exp = llm.explain(inp, rule, sources)   # handles provider errors itself
    except Exception:                           # anything unexpected must not lose the case
        log.exception("Unexpected error in explanation step")
        exp = llm.Explanation(
            llm.fallback_explanation(inp, rule, sources),
            "The AI explanation failed unexpectedly. Showing the rule-based explanation instead.",
        )

    case_note = notes.build_case_note(inp, rule, sources)
    return db.insert_case(inp, rule, sources, case_note,
                          llm_answer=exp.answer, llm_error=exp.error, path=db_path)