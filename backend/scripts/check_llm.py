"""Confirm your Groq key and model work. Prints no secrets."""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402

if not config.GROQ_API_KEY:
    sys.exit("GROQ_API_KEY is empty. Set it in .env")

try:
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        json={"model": config.GROQ_MODEL, "max_tokens": 20,
              "messages": [{"role": "user", "content": "Reply with the word: ready"}]},
        timeout=15,
    )
except httpx.HTTPError as e:
    sys.exit(f"Network error: {type(e).__name__}")

print("HTTP", r.status_code)
print(r.json()["choices"][0]["message"]["content"] if r.status_code == 200
      else "Failed: check key, model ID and rate limits in Groq docs.")