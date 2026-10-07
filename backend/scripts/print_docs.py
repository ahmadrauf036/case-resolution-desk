"""Phase 1 check: print every policy with its parsed metadata."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.retrievel import load_documents  # noqa: E402

for d in load_documents():
    extra = f" -> replaced by {d.superseded_by} {d.superseded_by_version}" if d.superseded_by else ""
    print(f"{d.id} | {d.version} | {d.effective} | {d.status}{extra} | {len(d.sections)} sections | {d.title}")