"""FastAPI app: thin HTTP layer over app.pipeline."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, db, pipeline
from .models import CaseInput, CaseOut, CaseSummary, StatusUpdate
from .retrieval import PolicyIndex, load_documents

log = logging.getLogger("skillbridge")

# Fail fast at startup if a policy file is malformed.
DOCUMENTS = load_documents()
INDEX = PolicyIndex(DOCUMENTS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="SkillBridge Case Resolution Desk", lifespan=lifespan)


def _cors_origins() -> list[str]:
    """CORS_ORIGIN may be comma-separated; localhost and 127.0.0.1 are treated as the same dev host."""
    out: list[str] = []
    for o in config.CORS_ORIGIN.split(","):
        o = o.strip().rstrip("/")
        if not o:
            continue
        out.append(o)
        if "localhost" in o:
            out.append(o.replace("localhost", "127.0.0.1"))
        elif "127.0.0.1" in o:
            out.append(o.replace("127.0.0.1", "localhost"))
    return list(dict.fromkeys(out))


app.add_middleware(CORSMiddleware, allow_origins=_cors_origins(),
                   allow_methods=["*"], allow_headers=["*"])


# ---------- consistent, readable errors: {"detail": "<string>", "errors": [...]} ----------

@app.exception_handler(RequestValidationError)
async def validation_handler(_, exc: RequestValidationError):
    problems = []
    for e in exc.errors():
        loc = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path")]
        msg = str(e.get("msg", "Invalid value")).removeprefix("Value error, ")
        problems.append({"field": ".".join(loc) or "request", "message": msg})
    summary = "; ".join(f"{p['field']}: {p['message']}" for p in problems) or "Invalid request."
    return JSONResponse(status_code=422, content={"detail": summary, "errors": problems})


@app.exception_handler(Exception)
async def unhandled_handler(_, exc: Exception):
    log.exception("Unhandled error")   # stack trace stays in the server log only
    return JSONResponse(status_code=500, content={
        "detail": "Something went wrong on the server. Please try again.", "errors": []})


# ---------- routes ----------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "case_date": config.DEFAULT_CASE_DATE.isoformat(),
        "policies": [d.label for d in DOCUMENTS],
        "llm_configured": bool(config.GROQ_API_KEY),
    }


@app.post("/api/cases", response_model=CaseOut, status_code=201)
def create_case(inp: CaseInput):
    """Analyze and save a case. Returns 201 even if the LLM failed: the rule result and a
    rule-based explanation are always included, and `llm_error` is set when the fallback was used."""
    return pipeline.analyze(inp, INDEX)


@app.get("/api/cases", response_model=list[CaseSummary])
def list_cases():
    return db.list_cases()


@app.get("/api/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int):
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@app.patch("/api/cases/{case_id}/status", response_model=CaseOut)
def update_status(case_id: int, body: StatusUpdate):
    """Coordinator moves a case between the five KB-04 statuses. Only the status changes."""
    case = db.update_status(case_id, body.status)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case