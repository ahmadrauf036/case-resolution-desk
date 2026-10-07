from datetime import date

from app.retrievel import CURRENT, SUPERSEDED, load_documents


def _by_id():
    return {d.id: d for d in load_documents()}


def test_loads_all_five_with_metadata():
    docs = _by_id()
    assert set(docs) == {"KB-01", "KB-02", "KB-03", "KB-04", "KB-05"}
    assert docs["KB-01"].version == "v2" and docs["KB-01"].effective == date(2026, 9, 1)
    assert docs["KB-02"].version == "v3" and docs["KB-02"].effective == date(2026, 10, 1)
    assert docs["KB-04"].version == "v1"


def test_kb05_is_superseded_by_kb02_v3():
    kb05 = _by_id()["KB-05"]
    assert kb05.status == SUPERSEDED
    assert (kb05.superseded_by, kb05.superseded_by_version) == ("KB-02", "v3")
    assert all(d.status == CURRENT for d in load_documents() if d.id != "KB-05")


def test_sections_parsed():
    assert all(len(d.sections) >= 5 for d in load_documents())