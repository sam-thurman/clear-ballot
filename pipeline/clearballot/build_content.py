"""Generate contest and candidate content files from data/ (frontmatter from data, body stubbed).

Idempotent: re-running refreshes data-driven frontmatter fields but preserves anything an
author or reviewer owns: status, reviewed_by, reviewed_at, endorsements, hand-added sources,
and the markdown body.

Usage:
    uv run python -m clearballot.build_content
"""
from __future__ import annotations

import json
import re
from datetime import date

import yaml

from .paths import CONTENT, DATA

SOS_OFFICES_URL = "https://www.sos.wa.gov/elections/candidates/information/descriptions-elected-offices"
SOS_OFFICES_SOURCE = {
    "id": "sos-offices",
    "title": "Descriptions of Elected Offices",
    "url": SOS_OFFICES_URL,
    "publisher": "Washington Secretary of State",
    "accessed": "2026-10-17",
    "kind": "official",
}
# Plain-English office notes; every sentence is drawn from sources/offices/sos-descriptions-of-elected-offices.txt.
OFFICE_NOTES = {
    "cd": (
        "The U.S. House of Representatives and the U.S. Senate share responsibility for declaring war, "
        "maintaining the armed forces, setting taxes, borrowing money, regulating commerce, and passing the "
        "laws and budgets that run the federal government.[^sos-offices] Representatives serve two-year terms, "
        "and all 435 seats are up for election in even-numbered years.[^sos-offices] A representative must be at "
        "least 25 years old, a U.S. citizen for at least seven years, and a resident of the state, but does not "
        "have to live in the district.[^sos-offices]"
    ),
    "senator": (
        "State legislators propose and pass state laws, set the state budget, and decide how taxes are collected "
        "to pay for state and local government.[^sos-offices] The state Senate has 49 members, one from each "
        "legislative district, elected to four-year terms, with about half the seats up for election every two "
        "years.[^sos-offices] The Senate's one exclusive duty is to confirm appointments made by the "
        "governor.[^sos-offices] Legislators must be registered voters of their district.[^sos-offices]"
    ),
    "rep": (
        "State legislators propose and pass state laws, set the state budget, and decide how taxes are collected "
        "to pay for state and local government.[^sos-offices] The state House of Representatives has 98 members, "
        "two from each legislative district, elected to two-year terms, so every House seat is up for election "
        "in even-numbered years.[^sos-offices] Legislators must be registered voters of their district.[^sos-offices]"
    ),
    "statewide": (
        "The Washington Supreme Court is the highest court in the state; its justices hear appeals and decide "
        "cases from the Courts of Appeals and other lower courts.[^sos-offices] Nine justices are elected "
        "statewide to six-year terms.[^sos-offices] Judges in Washington are nonpartisan, must be in good "
        "standing to practice law in the state, must be registered Washington voters, and may not make "
        "statements that appear to commit them on legal issues that could come before them in "
        "court.[^sos-offices]"
    ),
}
TODO = "<!-- TODO: session 2 -->"

CANDIDATE_SECTIONS = ["Background", "Positions", "Affiliations and endorsements", "Record", "Funding"]

AUTHOR_OWNED = {"status", "reviewed_by", "reviewed_at", "endorsements"}


class LiteralDumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


LiteralDumper.add_representer(str, _str_presenter)


def dump_frontmatter(fm: dict) -> str:
    return yaml.dump(fm, Dumper=LiteralDumper, sort_keys=False, allow_unicode=True, width=1000)


def split_markdown(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("no frontmatter")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def write_markdown(path, fm: dict, body: str) -> None:
    path.write_text(f"---\n{dump_frontmatter(fm)}---\n\n{body.lstrip()}")


def merge_existing(path, fm: dict, body: str, generated_source_ids: set[str]) -> tuple[dict, str]:
    """Keep author-owned frontmatter keys, extra sources, and the existing body."""
    if not path.exists():
        return fm, body
    old_fm, old_body = split_markdown(path.read_text())
    for k in AUTHOR_OWNED:
        if k in old_fm:
            fm[k] = old_fm[k]
    extra_sources = [s for s in old_fm.get("sources", []) if s.get("id") not in generated_source_ids]
    fm["sources"] = fm["sources"] + extra_sources
    return fm, (old_body if old_body.strip() else body)


def load_json(path):
    return json.loads(path.read_text()) if path.exists() else None


def build_contests(contests: dict, today: str) -> int:
    n = 0
    for c in contests["contests"]:
        path = CONTENT / "contests" / f"{c['id']}.md"
        fm = {
            "id": c["id"],
            "title": c["title"],
            "status": "draft",
            "reviewed_by": None,
            "reviewed_at": None,
            "updated_at": today,
            "office": c["office"],
            "district_type": c["district_type"],
            "district_id": c["district_id"],
            "district_number": c["district_number"],
            "partisan": c["partisan"],
            "term_note": c["term_note"],
            "candidates": c["candidates"],
            "ballot_page": c["ballot_page"],
            "sources": [
                {
                    "id": "kc-sample-ballot",
                    "title": contests["source"]["title"],
                    "url": contests["source"]["url"],
                    "publisher": "King County Elections",
                    "accessed": contests["source"]["parsed_at"],
                    "kind": "official",
                }
            ],
        }
        fm["sources"].append(SOS_OFFICES_SOURCE)
        kind = c["district_type"] if c["district_type"] != "ld" else ("senator" if c["office"] == "State Senator" else "rep")
        body = f"## About this office\n\n{OFFICE_NOTES[kind]}\n"
        fm, old_body = merge_existing(path, fm, body, {"kc-sample-ballot", "sos-offices"})
        # The office note is generated; replace a stub or an earlier generated note, keep anything else.
        if TODO in old_body or old_body.strip().startswith("## About this office"):
            old_body = body
        body = old_body
        write_markdown(path, fm, body)
        n += 1
    return n


def build_candidates(contests: dict, candidates: list[dict], today: str) -> int:
    pamphlet = load_json(DATA / "pamphlet.json") or {"candidates": {}}
    legislators = load_json(DATA / "legislators.json") or {"candidates": []}
    leg_by_slug = {m["slug"]: m for m in legislators["candidates"]}
    federal = load_json(DATA / "federal.json") or {"candidates": {}}
    justices = load_json(DATA / "justices.json") or {"candidates": {}}
    by_contest = {c["id"]: c for c in contests["contests"]}
    n = 0
    for cand in candidates:
        slug = cand["slug"]
        contest = by_contest[cand["contest"]]
        path = CONTENT / "candidates" / f"{slug}.md"
        pam = pamphlet["candidates"].get(slug) or {}
        fin = load_json(DATA / "finance" / f"{slug}.json")
        rec = load_json(DATA / "records" / f"{slug}.json")
        leg = leg_by_slug.get(slug)
        fed = federal["candidates"].get(slug)
        jus = justices["candidates"].get(slug)

        sources = [
            {
                "id": "kc-sample-ballot",
                "title": contests["source"]["title"],
                "url": contests["source"]["url"],
                "publisher": "King County Elections",
                "accessed": contests["source"]["parsed_at"],
                "kind": "official",
            }
        ]
        if pam:
            sources.append(
                {
                    "id": "sos-pamphlet",
                    "title": f"Voters' Pamphlet statement, {cand['name']} (2026 General Election, {pam['edition']}, page {pam['page']})",
                    "url": pam["url"],
                    "publisher": "Washington Secretary of State",
                    "accessed": "2026-10-17",
                    "kind": "official",
                }
            )
        incumbent = False
        current_office = None
        if leg and leg.get("member"):
            incumbent = leg["incumbent"]
            current_office = leg["current_office"]
            sources.append(
                {
                    "id": "leg-member",
                    "title": f"Legislator page: {leg['member']['name']}",
                    "url": leg["member"]["url"],
                    "publisher": "Washington State Legislature",
                    "accessed": legislators["as_of"],
                    "kind": "legislative",
                }
            )
        if fed:
            incumbent = fed.get("incumbent", False)
            current_office = fed.get("current_office")
            for s in fed.get("sources", []):
                sources.append(s)
        if jus:
            incumbent = jus.get("incumbent", False)
            current_office = jus.get("current_office")
            for s in jus.get("sources", []):
                sources.append(s)

        finance = None
        finance_checked = None
        if fin:
            finance_checked = fin.get("checked")
            if fin.get("finance"):
                f = fin["finance"]
                finance = {
                    "source": f["source"],
                    "filer_id": f.get("filer_id"),
                    "url": f.get("pdc_url") or f.get("url"),
                    "total_raised": f.get("total_raised"),
                    "total_spent": f.get("total_spent"),
                    "cash_on_hand": f.get("cash_on_hand"),
                    "as_of": f.get("as_of"),
                    "top_contributors": [
                        {k: v for k, v in tc.items() if k in ("name", "amount", "employer", "occupation")}
                        for tc in f.get("top_contributors", [])
                    ],
                    "small_donor_share": f.get("small_donor_share"),
                }
                sources.append(
                    {
                        "id": "finance",
                        "title": f"Campaign finance filings: {f.get('filer_name') or cand['name']}",
                        "url": finance["url"],
                        "publisher": "Washington Public Disclosure Commission" if f["source"] == "pdc" else "Federal Election Commission",
                        "accessed": f.get("as_of") or finance_checked,
                        "kind": "finance",
                    }
                )
        record = None
        if rec:
            record = {
                "as_of": rec["as_of"],
                "sponsored_bills_url": rec["sponsored_bills_source"],
                "sponsored_bills": [
                    {"bill_id": b["bill_id"], "title": b["title"], "status": b["status"], "url": b["url"]}
                    for b in rec["sponsored_bills"]
                ],
                "shortlist_votes": [
                    {"bill_id": v["bill_id"], "title": v["title"], "vote": v["vote"], "chamber": v["chamber"], "date": v["date"], "url": v["url"]}
                    for v in rec["shortlist_votes"]
                ],
            }
            sources.append(
                {
                    "id": "leg-sponsored",
                    "title": f"Bills by sponsor, 2025-26: {rec['member']['name']}",
                    "url": rec["sponsored_bills_source"],
                    "publisher": "Washington State Legislature",
                    "accessed": rec["as_of"],
                    "kind": "legislative",
                }
            )
        if fed and fed.get("record"):
            record = fed["record"]

        fm = {
            "id": slug,
            "title": cand["name"],
            "status": "draft",
            "reviewed_by": None,
            "reviewed_at": None,
            "updated_at": today,
            "name": cand["name"],
            "contest": cand["contest"],
            "party_preference": cand["party_preference"],
            "incumbent": incumbent,
            "current_office": current_office,
            "website": pam.get("website") or (fed or {}).get("website") or (jus or {}).get("website"),
            "pamphlet_statement_url": pam.get("url"),
            "pamphlet_statement_submitted": (not pam.get("no_statement")) if pam else None,
            "finance": finance,
            "finance_checked": finance_checked,
            "record": record,
            "endorsements": [],
            "sources": sources,
        }
        generated_ids = {s["id"] for s in sources}
        body = "\n".join(f"## {sec}\n\n{TODO}\n" for sec in CANDIDATE_SECTIONS)
        fm, body = merge_existing(path, fm, body, generated_ids)
        write_markdown(path, fm, body)
        n += 1
    return n


def main() -> int:
    today = date.today().isoformat()
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    (CONTENT / "contests").mkdir(parents=True, exist_ok=True)
    (CONTENT / "candidates").mkdir(parents=True, exist_ok=True)
    nc = build_contests(contests, today)
    nk = build_candidates(contests, candidates, today)
    print(f"wrote {nc} contest files and {nk} candidate files under {CONTENT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
