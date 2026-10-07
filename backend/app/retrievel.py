"""Policy loading (Phase 1). Search/ranking is added in Phase 4."""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .config import POLICY_DIR

CURRENT = "CURRENT"
SUPERSEDED = "SUPERSEDED"


@dataclass
class Section:
    heading: str
    text: str


@dataclass
class Document:
    id: str
    version: str
    effective: date
    status: str                      # CURRENT | SUPERSEDED
    title: str
    text: str
    sections: list[Section] = field(default_factory=list)
    superseded_by: str | None = None          # e.g. "KB-02"
    superseded_by_version: str | None = None  # e.g. "v3"

    @property
    def label(self) -> str:
        return f"{self.id} {self.version}"


def _header(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"missing header '{key}'")
    return m.group(1).strip()


def _split_sections(text: str) -> list[Section]:
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return [Section(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def parse_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    try:
        title = re.search(r"^#\s+KB-\d+:\s*(.+)$", text, re.MULTILINE).group(1).strip()
        doc_id = _header(text, "Document ID")
        version = _header(text, "Version")
        effective = datetime.strptime(_header(text, "Effective date"), "%d %b %Y").date()
        raw_status = _header(text, "Status")
    except (AttributeError, ValueError) as e:
        raise ValueError(f"{path.name}: bad or missing metadata ({e})") from e

    status, sup_by, sup_ver = CURRENT, None, None
    if raw_status.upper().startswith("SUPERSEDED"):
        status = SUPERSEDED
        m = re.search(r"(KB-\d+)\s*(v\d+)?", raw_status)
        if m:
            sup_by, sup_ver = m.group(1), m.group(2)
    elif raw_status.upper() != CURRENT:
        raise ValueError(f"{path.name}: unknown status '{raw_status}'")

    return Document(doc_id, version, effective, status, title, text,
                    _split_sections(text), sup_by, sup_ver)


def load_documents(policy_dir: Path = POLICY_DIR) -> list[Document]:
    docs = [parse_document(p) for p in sorted(policy_dir.glob("KB-*.md"))]
    if not docs:
        raise FileNotFoundError(f"no KB-*.md files in {policy_dir}")
    return docs