"""Acceptance tests for the sample ballot parser (SCOPE.md, Session 1 item 1)."""
import json

import pytest

from clearballot.ballot import DEFAULT_PDF, extract_lines, parse
from clearballot.paths import DATA


@pytest.fixture(scope="module")
def parsed():
    if not DEFAULT_PDF.exists():
        pytest.skip("sample ballot PDF not downloaded")
    return parse(extract_lines(DEFAULT_PDF))


def test_counts(parsed):
    measures, contests, candidates = parsed
    by_type = {}
    for c in contests:
        by_type[c.district_type] = by_type.get(c.district_type, 0) + 1
    assert len(measures) == 3
    assert by_type["cd"] == 4
    assert by_type["statewide"] == 5
    # LD count is derived from the PDF; this pins the value found on 2026-10-17
    # so a changed PDF (or a parser regression) is noticed.
    assert by_type["ld"] == 46
    assert len(contests) == 55
    assert len(candidates) == 101


def test_measure_numbers(parsed):
    measures, _, _ = parsed
    assert [m.ballot_number for m in measures] == ["IP26-645", "IL26-001", "IL26-638"]
    assert all(m.ballot_title.endswith("Should this measure be enacted into law?") for m in measures)


def test_lds_in_scope(parsed):
    _, contests, _ = parsed
    lds = sorted({c.district_number for c in contests if c.district_type == "ld"})
    assert lds == [1, 5, 11, 12, 30, 31, 32, 33, 34, 36, 37, 41, 43, 45, 46, 47, 48]
    for c in contests:
        if c.district_type == "ld":
            assert c.district_id == f"53{c.district_number:03d}"
        elif c.district_type == "cd":
            assert c.district_id == f"53{c.district_number:02d}"
        else:
            assert c.district_id == "statewide"


def test_spot_check_named_candidates(parsed):
    _, contests, candidates = parsed
    by_slug = {c.slug: c for c in candidates}

    jayapal = by_slug["candidate-pramila-jayapal"]
    assert jayapal.name == "Pramila Jayapal"
    assert jayapal.contest == "contest-us-house-cd-7"
    assert jayapal.party_preference == "Prefers Democratic Party"

    fitzgibbon = by_slug["candidate-joe-fitzgibbon"]
    assert fitzgibbon.contest == "contest-ld-34-rep-pos-2"
    assert fitzgibbon.party_preference == "Prefers Democratic Party"

    stephens = by_slug["candidate-debra-l-stephens"]
    assert stephens.name == "Debra L. Stephens"
    assert stephens.contest == "contest-supreme-court-pos-7"
    assert stephens.party_preference is None


def test_term_notes(parsed):
    _, contests, _ = parsed
    by_id = {c.id: c for c in contests}
    assert by_id["contest-ld-5-rep-pos-1"].term_note == "short and full term"
    assert by_id["contest-supreme-court-pos-1"].term_note == "unexpired 2-year term"
    assert by_id["contest-supreme-court-pos-5"].term_note == "unexpired 2-year term"
    assert by_id["contest-supreme-court-pos-3"].term_note is None


def test_no_out_of_scope_contests(parsed):
    _, contests, candidates = parsed
    names = {c.name for c in candidates}
    # County offices, lower courts, and city races must not leak in.
    assert "Leesa Manion" not in names
    assert "Julie Wise" not in names
    assert "Jan Trasen" not in names
    assert not any("Council" in c.office or "Judge" in c.office for c in contests)


def test_contest_candidate_integrity(parsed):
    _, contests, candidates = parsed
    slugs = [c.slug for c in candidates]
    assert len(slugs) == len(set(slugs))
    referenced = [s for c in contests for s in c.candidates]
    assert sorted(referenced) == sorted(slugs)


def test_written_json_matches_parse(parsed):
    measures, contests, candidates = parsed
    if not (DATA / "contests.json").exists():
        pytest.skip("data/contests.json not generated")
    data = json.loads((DATA / "contests.json").read_text())
    assert [c["id"] for c in data["contests"]] == [c.id for c in contests]
    cands = json.loads((DATA / "candidates.json").read_text())
    assert [c["slug"] for c in cands] == [c.slug for c in candidates]
