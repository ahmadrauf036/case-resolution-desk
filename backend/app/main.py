from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from retrievel import load_documents

app = FastAPI(title="SkillBridge Case Resolution Desk")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.CORS_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fail fast at startup if a policy file is malformed.
DOCUMENTS = load_documents()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "case_date": config.DEFAULT_CASE_DATE.isoformat(),
        "policies": [d.label for d in DOCUMENTS],
        "llm_configured": bool(config.GROQ_API_KEY),
    }