"""PDC (Washington Public Disclosure Commission) campaign finance for state legislative
and Supreme Court candidates, plus committee totals for the three ballot measures.

Sources (data.wa.gov Socrata, no key needed for light use):
  3h9x-7bvm  Campaign Finance Summary        (per-candidacy totals: contributions, expenditures, ...)
  kv7h-kjye  Contributions to Candidates and Political Committees (itemized; used for top contributors)

Outputs:
  data/finance/<slug>.json        per candidate (or {"finance": null, ...} when no filing matched)
  data/finance/measures.json      committees registered for/against each initiative, totals, top contributors

Usage:
    uv run python -m clearballot.pdc
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

import httpx

from .ballot import slugify
from .paths import DATA

SUMMARY = "https://data.wa.gov/resource/3h9x-7bvm.json"
CONTRIBUTIONS = "https://data.wa.gov/resource/kv7h-kjye.json"
PDC_CANDIDATE_PAGE = "https://www.pdc.wa.gov/political-disclosure-reporting-data/browse-search-data/candidates/{id}"
PDC_COMMITTEE_PAGE = "https://www.pdc.wa.gov/political-disclosure-reporting-data/browse-search-data/committees/{id}"
ELECTION_YEAR = "2026"
# "small donor share" = share of contribution dollars from itemized gifts of $100 or less, plus the
# lump sums filers report as "SMALL CONTRIBUTIONS" (unitemized gifts of $25 or less).
SMALL_DONOR_MAX = 100.0

MEASURE_COMMITTEE_PATTERNS = {
    # measure id -> substrings that identify the measure in the committee's ballot_number field
    "measure-ip26-645": ["645"],
    "measure-il26-001": ["001"],
    "measure-il26-638": ["638"],
}

HEADERS = {"User-Agent": "clear-ballot/0.1 (+github.com/sam-thurman/clear-ballot)"}
if os.environ.get("SOCRATA_APP_TOKEN"):
    HEADERS["X-App-Token"] = os.environ["SOCRATA_APP_TOKEN"]
CLIENT = httpx.Client(timeout=120, headers=HEADERS)


def soda(url: str, **params) -> list[dict]:
    r = CLIENT.get(url, params={f"${k}": v for k, v in params.items()})
    r.raise_for_status()
    return r.json()


def candidate_summaries() -> list[dict]:
    where = (
        f"election_year='{ELECTION_YEAR}' AND ("
        "office like 'STATE REPRESENTATIVE%' OR office like 'STATE SENATOR%'"
        " OR office like 'STATE SUPREME COURT%')"
        # No county filter: several King County legislative districts straddle county lines and the
        # PDC files the candidacy under whichever county the jurisdiction is keyed to (e.g. LD 12 -> Chelan).
    )
    return soda(SUMMARY, where=where, limit=1000)


def name_tokens(name: str) -> list[str]:
    return slugify(name).split("-")


def match_summary(cand: dict, contest: dict, rows: list[dict]) -> dict | None:
    """Match a ballot candidate to a PDC candidacy by office, district/position, and name."""
    toks = name_tokens(cand["name"])
    first, last = toks[0], toks[-1]
    if contest["district_type"] == "ld":
        want_office = "STATE SENATOR" if contest["office"] == "State Senator" else "STATE REPRESENTATIVE"
        want_district = f"{contest['district_number']:02d}"
        want_position = None if want_office == "STATE SENATOR" else contest["office"].rsplit(" ", 1)[-1]
    else:
        want_office = "STATE SUPREME COURT JUSTICE"
        want_district = None
        want_position = contest["office"].rsplit(" ", 1)[-1]
    hits = []
    for r in rows:
        if not r.get("office", "").startswith(want_office):
            continue
        if want_district and r.get("legislative_district", "").zfill(2) != want_district:
            continue
        ftoks = name_tokens(r.get("filer_name", ""))
        if last not in ftoks or first not in ftoks:
            continue
        hits.append(r)
    if not hits:
        return None
    # Prefer the candidacy for the right position, on the general ballot, most recently updated.
    def rank(r):
        return (
            str(r.get("position", "")) == str(want_position),
            r.get("on_general_election_ballot") is True,
            r.get("active_candidate") is True,
            r.get("updated_at", ""),
        )
    hits.sort(key=rank, reverse=True)
    return hits[0]


def top_contributors(filer_id: str, n: int = 5) -> tuple[list[dict], float, float]:
    """Return (top contributors, total contribution dollars, small-donor dollars) for a filer in this cycle."""
    rows = soda(
        CONTRIBUTIONS,
        select="contributor_name,contributor_employer_name,contributor_occupation,sum(amount) as total,count(*) as n",
        where=f"election_year={ELECTION_YEAR} AND filer_id='{filer_id}' AND amount > 0",
        group="contributor_name,contributor_employer_name,contributor_occupation",
        order="total DESC",
        limit=n,
    )
    totals = soda(
        CONTRIBUTIONS,
        select="sum(amount) as total",
        where=f"election_year={ELECTION_YEAR} AND filer_id='{filer_id}' AND amount > 0",
    )
    small = soda(
        CONTRIBUTIONS,
        select="sum(amount) as total",
        where=(
            f"election_year={ELECTION_YEAR} AND filer_id='{filer_id}' AND amount > 0 AND "
            f"(amount <= {SMALL_DONOR_MAX} OR upper(contributor_name) = 'SMALL CONTRIBUTIONS')"
        ),
    )
    top = [
        {
            "name": r.get("contributor_name"),
            "amount": round(float(r.get("total") or 0), 2),
            "count": int(r.get("n") or 0),
            "employer": r.get("contributor_employer_name") or None,
            "occupation": r.get("contributor_occupation") or None,
        }
        for r in rows
    ]
    total = float((totals[0].get("total") if totals else 0) or 0)
    small_total = float((small[0].get("total") if small else 0) or 0)
    return top, total, small_total


def finance_from_summary(s: dict, today: str) -> dict:
    filer_id = s["filer_id"]
    top, total, small_total = top_contributors(filer_id)
    contributions = float(s.get("contributions_amount") or 0)
    return {
        "source": "pdc",
        "filer_id": filer_id,
        "filer_name": s.get("filer_name"),
        "pdc_url": PDC_CANDIDATE_PAGE.format(id=s["person_id"]) if s.get("person_id") else (s.get("url") or {}).get("url"),
        "registration_url": (s.get("url") or {}).get("url"),
        "total_raised": round(contributions, 2),
        "total_spent": round(float(s.get("expenditures_amount") or 0), 2),
        "carryforward": round(float(s.get("carryforward_amount") or 0), 2),
        "loans": round(float(s.get("loans_amount") or 0), 2),
        "debts": round(float(s.get("debts_amount") or 0), 2),
        "cash_on_hand": None,  # not published in the PDC summary dataset; see methodology
        "independent_expenditures_for": round(float(s.get("independent_expenditures_for_amount") or 0), 2),
        "independent_expenditures_against": round(float(s.get("independent_expenditures_against_amount") or 0), 2),
        "as_of": (s.get("updated_at") or today)[:10],
        "top_contributors": top,
        "small_donor_share": round(small_total / total, 3) if total > 0 else None,
        "small_donor_max": SMALL_DONOR_MAX,
        "reporting_option": s.get("reporting_option"),
    }


def measure_committees(today: str) -> dict:
    rows = soda(
        CONTRIBUTIONS,
        select="filer_id,filer_name,committee_id,ballot_number,for_or_against,sum(amount) as total,count(*) as n",
        where=f"election_year={ELECTION_YEAR} AND type='Political Committee' AND ballot_number IS NOT NULL AND amount > 0",
        group="filer_id,filer_name,committee_id,ballot_number,for_or_against",
        order="total DESC",
        limit=2000,
    )
    out = {}
    for mid, pats in MEASURE_COMMITTEE_PATTERNS.items():
        committees = []
        seen = set()
        for r in rows:
            bn = r.get("ballot_number") or ""
            if not any(p in bn for p in pats):
                continue
            if r["filer_id"] in seen:
                continue
            seen.add(r["filer_id"])
            top, total, small_total = top_contributors(r["filer_id"], n=5)
            committees.append(
                {
                    "filer_id": r["filer_id"],
                    "name": r["filer_name"],
                    "ballot_number": bn,
                    "for_or_against": r.get("for_or_against"),
                    "total_contributions": round(total, 2),
                    "contribution_count": int(r.get("n") or 0),
                    "top_contributors": top,
                    "pdc_url": PDC_COMMITTEE_PAGE.format(id=r["committee_id"]) if r.get("committee_id") else None,
                }
            )
        committees.sort(key=lambda c: -c["total_contributions"])
        out[mid] = committees
    return {"as_of": today, "source": CONTRIBUTIONS, "note": "Committees whose PDC registration lists this measure number; multi-measure committees appear under each measure. Totals are all positive contributions (cash and in-kind) reported for the 2026 cycle.", "measures": out}


def main() -> int:
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    by_contest = {c["id"]: c for c in contests["contests"]}
    today = date.today().isoformat()
    out_dir = DATA / "finance"
    out_dir.mkdir(exist_ok=True)

    print("fetching PDC candidate summaries...")
    rows = candidate_summaries()
    print(f"  {len(rows)} candidacies (King County legislative + Supreme Court)")
    matched = 0
    for cand in candidates:
        contest = by_contest[cand["contest"]]
        if contest["district_type"] == "cd":
            continue  # federal: see fec.py
        s = match_summary(cand, contest, rows)
        if s is None:
            rec = {"slug": cand["slug"], "finance": None, "checked": today, "note": f"No PDC candidate filing matched for {cand['name']} ({contest['title']}) as of {today}."}
            print(f"  {cand['slug']}: no filing")
        else:
            rec = {"slug": cand["slug"], "finance": finance_from_summary(s, today), "checked": today}
            matched += 1
            print(f"  {cand['slug']}: {s['filer_id']} raised ${rec['finance']['total_raised']:,.0f}")
        (out_dir / f"{cand['slug']}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    print(f"matched {matched} candidates to PDC filings")

    print("fetching measure committees...")
    mc = measure_committees(today)
    (out_dir / "measures.json").write_text(json.dumps(mc, indent=2, ensure_ascii=False) + "\n")
    for mid, cs in mc["measures"].items():
        print(f"  {mid}: {len(cs)} committees; top: {[(c['name'], c['for_or_against'], c['total_contributions']) for c in cs[:3]]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
