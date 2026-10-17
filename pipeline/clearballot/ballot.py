"""Parse the King County sample ballot PDF into data/contests.json and data/candidates.json.

Only in-scope contests are emitted: the statewide initiatives, US House, WA
Legislature, and WA Supreme Court. Everything else on the ballot (county
offices, lower courts, city/school/special-district measures) is skipped.

Usage:
    uv run python -m clearballot.ballot [--pdf PATH] [--url URL]

The default PDF path is sources/pamphlet/king-county-sample-ballot-2026-11.pdf.
Re-download from the King County Elections page if the URL hash rotates:
https://kingcounty.gov/en/dept/elections/election-information/2026/november-general
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from .paths import DATA, SOURCES

DEFAULT_PDF = SOURCES / "pamphlet" / "king-county-sample-ballot-2026-11.pdf"
DEFAULT_URL = (
    "https://cdn.kingcounty.gov/-/media/king-county/depts/elections/"
    "current-election/2026/11/sample-ballot.pdf"
)
ELECTION = {
    "name": "November 3, 2026 General Election",
    "date": "2026-11-03",
    "county": "King County, WA",
}
STATE_FIPS = "53"

RE_MEASURE = re.compile(r"^Initiative Measure No\. (I[LP]\d{2}-\d{3})$")
RE_CD = re.compile(r"^Congressional District No\. (\d+)$")
RE_LD = re.compile(r"^Legislative District No\. (\d+)$")
RE_REP_POS = re.compile(r"^Representative Position No\. (\d+)$")
RE_JUSTICE = re.compile(r"^Justice Position No\. (\d+)$")
RE_PARTY = re.compile(r"^\((.+)\)$")
RE_PAGE = re.compile(r"^=== PAGE (\d+) ===$")

# Lines that mean "the candidate list is over" when encountered in a list.
STOP_PREFIXES = (
    "Sample",
    "ELECTIONS OFFICE",
    "READ:",
    "Continue voting",
    "Initiative Measure",
    "United States Representative",
    "Legislative District",
    "Justice Position",
    "Judge Position",
    "Prosecuting Attorney",
    "Assessor",
    "Director of Elections",
    "Metropolitan King County",
    "Court of Appeals",
    "City of ",
    "State",
    "Federal",
    "County",
    "Northeast Electoral",
    "Shoreline Electoral",
    "Southeast Electoral",
    "Southwest Electoral",
    "West Electoral",
    "Seattle Municipal",
    "School",
    "Special Purpose",
    "End of Ballot",
)
TERM_NOTES = ("short and full term", "unexpired 2-year term", "unexpired 1-year term")


@dataclass
class Measure:
    id: str
    ballot_number: str
    measure_type: str
    ballot_title: str
    ballot_page: int


@dataclass
class Contest:
    id: str
    office: str
    title: str
    district_type: str  # statewide | cd | ld
    district_id: str  # e.g. 5309, 53034, statewide
    district_number: int | None
    partisan: bool
    term_note: str | None
    ballot_page: int
    candidates: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    slug: str
    name: str
    contest: str
    party_preference: str | None
    ballot_order: int


def slugify(text: str) -> str:
    s = text.lower()
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def extract_lines(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    for i, page in enumerate(reader.pages):
        lines.append(f"=== PAGE {i + 1} ===")
        text = page.extract_text() or ""
        for raw in text.splitlines():
            line = re.sub(r"\s+", " ", raw.replace("\t", " ")).strip()
            lines.append(line)
    return lines


def measure_type_for(number: str) -> str:
    return "Initiative to the People" if number.startswith("IP") else "Initiative to the Legislature"


def parse(lines: list[str]) -> tuple[list[Measure], list[Contest], list[Candidate]]:
    measures: list[Measure] = []
    contests: list[Contest] = []
    candidates: list[Candidate] = []
    page = 0
    i = 0
    n = len(lines)

    def is_stop(line: str) -> bool:
        return any(line.startswith(p) for p in STOP_PREFIXES) or RE_PAGE.match(line) is not None

    def read_candidates(start: int, partisan: bool) -> tuple[int, list[tuple[str, str | None]]]:
        """Read candidate lines starting at `start`. Returns (next_index, [(name, party)])."""
        j = start
        found: list[tuple[str, str | None]] = []
        while j < n:
            line = lines[j]
            if not line:
                j += 1
                continue
            if is_stop(line):
                break
            if partisan:
                m = RE_PARTY.match(line)
                if not m:
                    break
                party = m.group(1)
                j += 1
                while j < n and not lines[j]:
                    j += 1
                if j >= n or is_stop(lines[j]):
                    raise ValueError(f"party preference without a name near line {j}")
                found.append((lines[j], party))
                j += 1
            else:
                found.append((line, None))
                j += 1
        return j, found

    def read_header_tail(start: int) -> tuple[int, str | None, bool]:
        """After a contest title, consume optional term note, '<x> office', 'vote for one'."""
        j = start
        term_note = None
        partisan = False
        while j < n:
            line = lines[j]
            if line in TERM_NOTES:
                term_note = line
            elif line == "partisan office":
                partisan = True
            elif line == "nonpartisan office":
                partisan = False
            elif line == "vote for one":
                return j + 1, term_note, partisan
            elif line == "":
                pass
            else:
                raise ValueError(f"unexpected header line {j}: {line!r}")
            j += 1
        raise ValueError("ran off the end of the ballot inside a contest header")

    def add_contest(contest: Contest, found: list[tuple[str, str | None]]) -> None:
        for order, (name, party) in enumerate(found, start=1):
            slug = f"candidate-{slugify(name)}"
            if any(c.slug == slug for c in candidates):
                raise ValueError(f"duplicate candidate slug {slug}")
            candidates.append(Candidate(slug, name, contest.id, party, order))
            contest.candidates.append(slug)
        contests.append(contest)

    while i < n:
        line = lines[i]
        pm = RE_PAGE.match(line)
        if pm:
            page = int(pm.group(1))
            i += 1
            continue

        mm = RE_MEASURE.match(line)
        if mm and i + 1 < n:
            # The title line appears twice (box header, then the summary opener).
            # The second occurrence begins the summary text.
            number = mm.group(1)
            if any(m.ballot_number == number for m in measures):
                i += 1
                continue
            # Collect summary text starting at the second occurrence of the title
            # (the summary opener; "concerns ..." may be on the same or next line).
            j = i + 1
            while j < n and not lines[j].startswith(f"Initiative Measure No. {number}"):
                j += 1
            parts: list[str] = []
            while j < n and lines[j] != "Yes":
                if lines[j]:
                    parts.append(lines[j])
                j += 1
            title = " ".join(parts)
            measures.append(
                Measure(
                    id=f"measure-{number.lower()}",
                    ballot_number=number,
                    measure_type=measure_type_for(number),
                    ballot_title=title,
                    ballot_page=page,
                )
            )
            i = j
            continue

        if line == "United States Representative" and i + 1 < n:
            cm = RE_CD.match(lines[i + 1])
            if not cm:
                raise ValueError(f"US House header without district at line {i}")
            cd = int(cm.group(1))
            j, term_note, partisan = read_header_tail(i + 2)
            j, found = read_candidates(j, partisan)
            contest = Contest(
                id=f"contest-us-house-cd-{cd}",
                office="United States Representative",
                title=f"US Representative, Congressional District {cd}",
                district_type="cd",
                district_id=f"{STATE_FIPS}{cd:02d}",
                district_number=cd,
                partisan=partisan,
                term_note=term_note,
                ballot_page=page,
            )
            add_contest(contest, found)
            i = j
            continue

        lm = RE_LD.match(line)
        if lm and i + 1 < n:
            ld = int(lm.group(1))
            office_line = lines[i + 1]
            if office_line == "State Senator":
                office = "State Senator"
                cid = f"contest-ld-{ld}-senator"
                title = f"State Senator, Legislative District {ld}"
            else:
                rm = RE_REP_POS.match(office_line)
                if not rm:
                    raise ValueError(f"LD header with unknown office at line {i}: {office_line!r}")
                pos = int(rm.group(1))
                office = f"State Representative Position {pos}"
                cid = f"contest-ld-{ld}-rep-pos-{pos}"
                title = f"State Representative Position {pos}, Legislative District {ld}"
            j, term_note, partisan = read_header_tail(i + 2)
            j, found = read_candidates(j, partisan)
            contest = Contest(
                id=cid,
                office=office,
                title=title,
                district_type="ld",
                district_id=f"{STATE_FIPS}{ld:03d}",
                district_number=ld,
                partisan=partisan,
                term_note=term_note,
                ballot_page=page,
            )
            add_contest(contest, found)
            i = j
            continue

        jm = RE_JUSTICE.match(line)
        if jm:
            pos = int(jm.group(1))
            j, term_note, partisan = read_header_tail(i + 1)
            j, found = read_candidates(j, partisan)
            contest = Contest(
                id=f"contest-supreme-court-pos-{pos}",
                office=f"Supreme Court Justice Position {pos}",
                title=f"State Supreme Court Justice Position {pos}",
                district_type="statewide",
                district_id="statewide",
                district_number=None,
                partisan=partisan,
                term_note=term_note,
                ballot_page=page,
            )
            add_contest(contest, found)
            i = j
            continue

        i += 1

    return measures, contests, candidates


def write_outputs(
    measures: list[Measure],
    contests: list[Contest],
    candidates: list[Candidate],
    pdf_path: Path,
    out_dir: Path = DATA,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    source = {
        "title": "King County Elections sample ballot, November 3, 2026 General Election",
        "url": DEFAULT_URL,
        "local_path": str(pdf_path.relative_to(out_dir.parent)) if pdf_path.is_relative_to(out_dir.parent) else str(pdf_path),
        "parsed_at": date.today().isoformat(),
    }
    (out_dir / "contests.json").write_text(
        json.dumps(
            {
                "election": ELECTION,
                "source": source,
                "measures": [asdict(m) for m in measures],
                "contests": [asdict(c) for c in contests],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    (out_dir / "candidates.json").write_text(
        json.dumps([asdict(c) for c in candidates], indent=2, ensure_ascii=False) + "\n"
    )
    (out_dir / "districts.json").write_text(
        json.dumps(build_districts(measures, contests), indent=2, ensure_ascii=False) + "\n"
    )


def build_districts(measures: list[Measure], contests: list[Contest]) -> dict:
    """Map every in-scope district_id to the measures/contests a voter there sees.

    Keys are Census GEOIDs as returned by the Census geocoder ("120th Congressional
    Districts" -> 5309, "2026 State Legislative Districts - Lower" -> 53034) plus
    "statewide". Everyone in King County sees the statewide entry.
    """
    districts: dict[str, dict] = {
        "statewide": {
            "district_type": "statewide",
            "district_number": None,
            "name": "Statewide",
            "measures": [m.id for m in measures],
            "contests": [],
        }
    }
    for c in contests:
        entry = districts.setdefault(
            c.district_id,
            {
                "district_type": c.district_type,
                "district_number": c.district_number,
                "name": (
                    f"Congressional District {c.district_number}"
                    if c.district_type == "cd"
                    else f"Legislative District {c.district_number}"
                ),
                "measures": [],
                "contests": [],
            },
        )
        entry["contests"].append(c.id)
    return {
        "state_fips": STATE_FIPS,
        "county_geoid": "53033",
        "geocoder_keys": {
            "cd": "120th Congressional Districts",
            "ld": "2026 State Legislative Districts - Lower",
            "county": "Counties",
        },
        "districts": districts,
    }


def summarize(measures, contests, candidates) -> str:
    by_type: dict[str, int] = {}
    for c in contests:
        by_type[c.district_type] = by_type.get(c.district_type, 0) + 1
    lds = sorted({c.district_number for c in contests if c.district_type == "ld"})
    return (
        f"measures={len(measures)} contests={len(contests)} "
        f"(cd={by_type.get('cd', 0)}, ld={by_type.get('ld', 0)}, statewide={by_type.get('statewide', 0)}) "
        f"candidates={len(candidates)} LDs={lds}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="local sample ballot PDF")
    ap.add_argument("--url", default=None, help="download the PDF from this URL to --pdf first")
    args = ap.parse_args(argv)

    if args.url:
        import httpx

        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        r = httpx.get(args.url, follow_redirects=True, timeout=60)
        r.raise_for_status()
        args.pdf.write_bytes(r.content)
        print(f"downloaded {len(r.content)} bytes -> {args.pdf}")

    if not args.pdf.exists():
        print(f"sample ballot PDF not found at {args.pdf}; pass --url {DEFAULT_URL}", file=sys.stderr)
        return 2

    lines = extract_lines(args.pdf)
    (args.pdf.parent / "sample-ballot.txt").write_text("\n".join(lines) + "\n")
    measures, contests, candidates = parse(lines)
    write_outputs(measures, contests, candidates, args.pdf)
    print(summarize(measures, contests, candidates))
    print(f"wrote {DATA / 'contests.json'} and {DATA / 'candidates.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
