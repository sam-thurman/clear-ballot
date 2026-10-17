"""Fetch the SOS Statewide Voters' Pamphlet PDFs (King County editions) and
extract the measure sections and candidate statements into sources/.

Outputs:
  sources/pamphlet/wa-voters-pamphlet-2026-edition-NN-*.pdf / .txt   (raw, cached)
  sources/measures/<measure-id>.txt       full pamphlet section per measure
  sources/measures/<measure-id>-text.txt  the measure's legal text pages
  sources/candidates/<slug>.txt           the candidate's pamphlet entry
  data/pamphlet.json                      per-candidate: edition, page, url, website, email

Usage:
    uv run python -m clearballot.pamphlet
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx
from pypdf import PdfReader

from .ballot import slugify
from .paths import DATA, SOURCES

PDF_INDEX = (
    "https://www.sos.wa.gov/elections/data-research/election-data-and-maps/"
    "election-results-and-voters-pamphlets/2026-general-election-voters-guide/2026-voters-pamphlet-pdfs"
)
EDITIONS = {
    "edition-04-king-seattle": "https://www.sos.wa.gov/sites/default/files/2026-10/Voters%20Pamphlet%202026%20-%20Edition%2004%C2%A0-%20King%20-%20Seattle.pdf",
    "edition-05-king-north-eastside": "https://www.sos.wa.gov/sites/default/files/2026-10/Voters%20Pamphlet%202026%20-%20Edition%2005%C2%A0-%20King%20-%20North%20and%20Eastside.pdf",
    "edition-06-king-south-southeast": "https://www.sos.wa.gov/sites/default/files/2026-10/Voters%20Pamphlet%202026%20-%20Edition%2006%20-%20King%20-%20South%20and%20Southeast.pdf",
}
PAMPHLET_DIR = SOURCES / "pamphlet"
MEASURES_DIR = SOURCES / "measures"
CANDIDATES_DIR = SOURCES / "candidates"

RE_MEASURE_HDR = re.compile(r"^Initiative Measure (I[LP]\d{2}-\d{3})$")
RE_CONTEST_HDR = re.compile(
    r"^(United States Representative|State Senator|State Representative|Supreme Court Justice) \| (.+?) \| (.+)$"
)
RE_PARTY = re.compile(r"^\((Prefers .+?|Nonpartisan|States No Party Preference)\)$")
RE_URL = re.compile(r"(?:https?://)?(?:www\.)?[A-Za-z0-9][A-Za-z0-9.-]+\.(?:com|org|net|us|vote|info|me|io|co)\b(?:/[^\s;]*)?", re.I)
RE_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
BODY_STARTS = ("Elected Experience", "Legal/Judicial Experience")
BANNERS = (
    "Use a drop box!",
    "If you need to return your ballot by mail",
)


def fetch_editions() -> dict[str, Path]:
    PAMPHLET_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, url in EDITIONS.items():
        pdf = PAMPHLET_DIR / f"wa-voters-pamphlet-2026-{name}.pdf"
        if not pdf.exists():
            r = httpx.get(url, follow_redirects=True, timeout=120)
            r.raise_for_status()
            pdf.write_bytes(r.content)
            print(f"downloaded {name}: {len(r.content)} bytes")
        txt = pdf.with_suffix(".txt")
        if not txt.exists():
            reader = PdfReader(str(pdf))
            parts = []
            for i, page in enumerate(reader.pages):
                parts.append(f"=== PAGE {i + 1} ===\n{page.extract_text() or ''}")
            txt.write_text("\n".join(parts))
        out[name] = txt
    return out


def pages_of(txt: Path) -> list[list[str]]:
    """Return a list of pages; each page is a list of stripped non-empty lines (page number line removed)."""
    chunks = txt.read_text().split("=== PAGE ")[1:]
    pages = []
    for ch in chunks:
        _, _, body = ch.partition(" ===\n")
        lines = [l.strip() for l in body.splitlines()]
        lines = [l for l in lines if l]
        # First line is usually the page number, sometimes glued to a heading ("65Initiative ...").
        if lines and re.fullmatch(r"\d+", lines[0]):
            lines = lines[1:]
        elif lines:
            lines[0] = re.sub(r"^\d+(?=[A-Z])", "", lines[0])
        pages.append(lines)
    return pages


def extract_measures(pages: list[list[str]], measure_numbers: list[str]) -> dict[str, dict]:
    """Return {number: {"pages": [1-based], "text": str, "legal_text_pages": [...], "legal_text": str}}."""
    starts: dict[str, int] = {}
    for idx, lines in enumerate(pages):
        for k in range(len(lines) - 1):
            hm = RE_MEASURE_HDR.match(lines[k])
            if hm and lines[k + 1].startswith(f"Initiative Measure No. {hm.group(1)} concerns"):
                starts.setdefault(hm.group(1), idx)
    # Measure sections end where the next measure starts or where the candidates begin ("Congress" page).
    end_of_measures = next(
        (i for i, lines in enumerate(pages) if any(l == "Congress" for l in lines[:4]) and i > min(starts.values())),
        len(pages),
    )
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    result = {}
    for k, (num, s) in enumerate(ordered):
        e = ordered[k + 1][1] if k + 1 < len(ordered) else end_of_measures
        result[num] = {"pages": list(range(s + 1, e + 1)), "text": "\n\n".join("\n".join(pages[i]) for i in range(s, e))}
    # Legal text: the pages after "How do I read measure text?"
    legal_start = next((i for i, lines in enumerate(pages) if lines and lines[0].startswith("How do I read measure text?")), None)
    if legal_start is not None:
        legal_end = next(
            (i for i in range(legal_start + 1, len(pages)) if pages[i] and pages[i][0].startswith("County Elections Offices")),
            len(pages),
        )
        legal = "\n\n".join(f"[page {i + 1}]\n" + "\n".join(pages[i]) for i in range(legal_start, legal_end))
        for num in result:
            result[num]["legal_text_pages"] = list(range(legal_start + 1, legal_end + 1))
            result[num]["legal_text"] = legal
    for num in measure_numbers:
        if num not in result:
            print(f"WARNING: measure {num} not found in pamphlet", file=sys.stderr)
    return result


def _is_name_line(line: str) -> bool:
    """True for the short name fragments printed above a candidate's party line."""
    if line in BODY_STARTS or line == "Unopposed" or RE_PARTY.match(line):
        return False
    if line.startswith("Contact") or any(ch in line for ch in "@;:/") or re.search(r"\d", line):
        return False
    if "www" in line.lower() or RE_URL.search(line) or len(line.split()) > 4 or line.endswith((",", ";")):
        return False
    return True


def parse_candidate_page(lines: list[str]) -> list[dict] | None:
    """Parse one candidate page into [{office, district, term, name, party, body}].

    Returns None if the page is not a candidate page. Two layouts occur:
    (a) both candidate name/party headers first, then both bodies in column order;
    (b) header, body, header, body. Bodies are assigned to headers in order.
    """
    lines = [l for l in lines if not any(l.startswith(b) for b in BANNERS) and l not in ("continue", "end")]
    if not lines:
        return None
    hdr = RE_CONTEST_HDR.match(lines[0])
    if not hdr:
        return None
    office, district, term = hdr.groups()
    rest = lines[1:]
    # Federal layout: first name printed at the top, last name + party after the body.
    first_name_prefix = None
    if len(rest) >= 2 and _is_name_line(rest[0]) and rest[1] in BODY_STARTS:
        first_name_prefix = rest.pop(0)

    # Pass 1: find party lines and the 1-3 short name lines before each.
    header_spans: list[tuple[int, int, str, str]] = []  # (name_start, party_idx, name, party)
    for i, l in enumerate(rest):
        pm = RE_PARTY.match(l)
        if not pm:
            continue
        j = i - 1
        name_lines: list[str] = []
        while j >= 0 and len(name_lines) < 3:
            cand = rest[j]
            if not _is_name_line(cand):
                break
            name_lines.insert(0, cand)
            j -= 1
        name = " ".join(name_lines).strip()
        if first_name_prefix and len(name_lines) == 1:
            name = f"{first_name_prefix} {name}".strip()
        header_spans.append((j + 1, i, name, pm.group(1)))
    header_idx = {k for (s, e, _, _) in header_spans for k in range(s, e + 1)}

    # Pass 2: collect bodies from the remaining lines.
    bodies: list[list[str]] = []
    cur: list[str] | None = None
    for i, l in enumerate(rest):
        if i in header_idx:
            continue
        if l in BODY_STARTS:
            cur = [l]
            bodies.append(cur)
        elif l.startswith("No information submitted") and cur is None:
            bodies.append([l])
        elif cur is not None:
            cur.append(l)

    out = []
    for k, (_, _, name, party) in enumerate(header_spans):
        body = bodies[k] if k < len(bodies) else []
        out.append({"office": office, "district": district, "term": term, "name": name, "party": party, "body": "\n".join(body)})
    return out




def contact_info(body: str) -> tuple[str | None, str | None]:
    idx = body.find("\nContact")
    if idx < 0:
        return None, None
    tail = body[idx:]
    email = RE_EMAIL.search(tail)
    # remove emails before scanning for urls
    no_email = RE_EMAIL.sub(" ", tail)
    url = None
    for m in RE_URL.finditer(no_email):
        u = m.group(0)
        if "@" in u:
            continue
        url = u if u.lower().startswith("http") else f"https://{u}"
        break
    return url, (email.group(0) if email else None)


def main() -> int:
    editions = fetch_editions()
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    measure_numbers = [m["ballot_number"] for m in contests["measures"]]
    MEASURES_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    # Measures come from edition 04 (identical statewide sections in every edition).
    first = next(iter(editions))
    pages = pages_of(editions[first])
    measures = extract_measures(pages, measure_numbers)
    pdf_url = EDITIONS[first]
    for num, m in measures.items():
        mid = f"measure-{num.lower()}"
        header = (
            f"SOURCE: Washington State Voters' Pamphlet, 2026 General Election, Edition 04 (King - Seattle)\n"
            f"URL: {pdf_url}\nPAGES: {m['pages'][0]}-{m['pages'][-1]}\nPUBLISHER: Washington Secretary of State\n"
            f"RETRIEVED: 2026-10-17\n\n"
        )
        (MEASURES_DIR / f"{mid}.txt").write_text(header + m["text"] + "\n")
        if "legal_text" in m:
            (MEASURES_DIR / f"{mid}-legal-text.txt").write_text(
                header.replace(f"PAGES: {m['pages'][0]}-{m['pages'][-1]}", f"PAGES: {m['legal_text_pages'][0]}-{m['legal_text_pages'][-1]}")
                + m["legal_text"]
                + "\n"
            )
        print(f"{mid}: pamphlet pages {m['pages']}")

    # Candidates: scan every edition; keep the first page a candidate appears on.
    by_slug = {c["slug"]: c for c in candidates}
    found: dict[str, dict] = {}
    unmatched = []
    for ed, txt in editions.items():
        for pno, lines in enumerate(pages_of(txt), start=1):
            parsed = parse_candidate_page(lines)
            if not parsed:
                continue
            for entry in parsed:
                slug = f"candidate-{slugify(entry['name'])}"
                if slug not in by_slug:
                    # try last-name + first-token match
                    toks = slugify(entry["name"]).split("-")
                    cands = [s for s in by_slug if s.endswith("-" + toks[-1]) and s.startswith("candidate-" + toks[0])]
                    if len(cands) == 1:
                        slug = cands[0]
                    else:
                        unmatched.append((ed, pno, entry["name"], entry["office"], entry["district"]))
                        continue
                if slug in found:
                    continue
                website, email = contact_info(entry["body"])
                url = f"{EDITIONS[ed]}#page={pno}"
                found[slug] = {
                    "edition": ed,
                    "page": pno,
                    "url": url,
                    "pamphlet_name": entry["name"],
                    "party": entry["party"],
                    "website": website,
                    "email": email,
                    "no_statement": not any(
                        ln and ln not in BODY_STARTS and not ln.startswith("No information submitted")
                        and ln not in ("Other Professional Experience", "Education", "Community Service", "Statement", "Contact")
                        for ln in entry["body"].splitlines()
                    ),
                }
                (CANDIDATES_DIR / f"{slug}.txt").write_text(
                    f"SOURCE: Washington State Voters' Pamphlet, 2026 General Election, {ed}\nURL: {url}\nPAGE: {pno}\n"
                    f"PUBLISHER: Washington Secretary of State\nRETRIEVED: 2026-10-17\n"
                    f"CONTEST: {entry['office']} | {entry['district']} | {entry['term']}\n"
                    f"CANDIDATE: {entry['name']} ({entry['party']})\n\n{entry['body']}\n"
                )
    missing = [s for s in by_slug if s not in found]
    (DATA / "pamphlet.json").write_text(json.dumps({"index_url": PDF_INDEX, "editions": EDITIONS, "candidates": found}, indent=2, ensure_ascii=False) + "\n")
    print(f"candidate statements: {len(found)}/{len(by_slug)} matched")
    if unmatched:
        print("unmatched pamphlet names (not on the King County ballot or name mismatch):")
        for u in unmatched:
            print("  ", u)
    if missing:
        print("ballot candidates with no pamphlet entry found:", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
