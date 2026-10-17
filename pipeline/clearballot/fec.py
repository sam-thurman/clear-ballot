"""OpenFEC campaign finance for the US House candidates.

Needs DATA_GOV_API_KEY (api.data.gov) in the environment or ../.env. If the key is
missing, writes {"finance": null, "note": "missing key"} for each federal candidate
and exits 0, so the rest of the pipeline still runs.

Outputs data/finance/<slug>.json for the federal candidates (same shape as pdc.py output).

Usage:
    uv run python -m clearballot.fec
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import date

import httpx

from .ballot import slugify
from .env import load_env
from .paths import DATA

API = "https://api.open.fec.gov/v1"
CYCLE = 2026
FEC_CANDIDATE_PAGE = "https://www.fec.gov/data/candidate/{id}/?cycle={cycle}"
SMALL_DONOR_NOTE = "share of total receipts reported as unitemized individual contributions (gifts of $200 or less)"


class FecClient(httpx.Client):
    """httpx client with the api key, polite retry on 429, and key-free error messages."""

    def get(self, url, **kw):  # type: ignore[override]
        for attempt in range(6):
            r = super().get(url, **kw)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"OpenFEC {r.status_code} for {url}")
            return r
        raise RuntimeError(f"OpenFEC rate limit persisted for {url}")


def client(key: str) -> httpx.Client:
    return FecClient(base_url=API, params={"api_key": key}, headers={"User-Agent": "clear-ballot/0.1"}, timeout=60)


def find_candidate(c: httpx.Client, name: str, district: int) -> dict | None:
    r = c.get("/candidates/", params={"state": "WA", "office": "H", "cycle": CYCLE, "district": f"{district:02d}", "per_page": 100})
    toks = slugify(name).split("-")
    first, last = toks[0], toks[-1]
    hits = []
    for cand in r.json()["results"]:
        ftoks = slugify(cand["name"]).split("-")
        if last in ftoks and (first in ftoks or any(t.startswith(first) for t in ftoks)):
            hits.append(cand)
    if not hits:
        return None
    # Prefer active statutory candidates (candidate_status C) over prior-cycle or not-yet-qualified records.
    hits.sort(key=lambda x: (x.get("candidate_status") == "C", x.get("incumbent_challenge") == "I"), reverse=True)
    return hits[0]


def totals(c: httpx.Client, candidate_id: str) -> dict | None:
    r = c.get(f"/candidate/{candidate_id}/totals/", params={"cycle": CYCLE, "election_full": "true"})
    res = r.json()["results"]
    full = res[0] if res else None
    r2 = c.get(f"/candidate/{candidate_id}/totals/", params={"cycle": CYCLE})
    r2.raise_for_status()
    res2 = r2.json()["results"]
    period = res2[0] if res2 else None
    if not full and not period:
        return None
    t = full or period
    return {
        "receipts": t.get("receipts"),
        "disbursements": t.get("disbursements"),
        "cash_on_hand": (period or {}).get("last_cash_on_hand_end_period") or (period or {}).get("cash_on_hand_end_period"),
        "coverage_end_date": (t.get("coverage_end_date") or "")[:10],
        "individual_contributions": t.get("individual_contributions"),
        "individual_unitemized_contributions": t.get("individual_unitemized_contributions"),
        "other_political_committee_contributions": t.get("other_political_committee_contributions"),
        "last_report": t.get("last_report_type_full"),
    }


def principal_committee(c: httpx.Client, candidate_id: str) -> str | None:
    r = c.get(f"/candidate/{candidate_id}/committees/", params={"cycle": CYCLE})
    for com in r.json()["results"]:
        if com.get("designation") == "P":
            return com["committee_id"]
    res = r.json()["results"]
    return res[0]["committee_id"] if res else None


def top_contributors(c: httpx.Client, committee_id: str, n: int = 5) -> list[dict]:
    """Aggregate the 100 largest itemized receipts by contributor name (+ employer)."""
    r = c.get(
        "/schedules/schedule_a/",
        params={
            "committee_id": committee_id,
            "two_year_transaction_period": CYCLE,
            "sort": "-contribution_receipt_amount",
            "per_page": 100,
        },
    )
    agg: dict[tuple, dict] = {}
    for row in r.json()["results"]:
        name = row.get("contributor_name") or "(unnamed)"
        # Skip conduit roll-ups (ActBlue/WinRed totals) and memo entries, which double-count
        # the earmarked gifts already itemized under the real donor's name.
        if row.get("memo_code") == "X" or "CONDUIT" in (row.get("contributor_occupation") or "").upper() or name.strip().upper() in ("ACTBLUE", "WINRED"):
            continue
        key = (name.strip().upper(), (row.get("contributor_employer") or "").strip().upper())
        a = agg.setdefault(key, {"name": name.strip(), "amount": 0.0, "count": 0, "employer": row.get("contributor_employer") or None, "occupation": row.get("contributor_occupation") or None})
        a["amount"] += float(row.get("contribution_receipt_amount") or 0)
        a["count"] += 1
    out = sorted(agg.values(), key=lambda x: -x["amount"])[:n]
    for o in out:
        o["amount"] = round(o["amount"], 2)
    return out


def main() -> int:
    load_env()
    key = os.environ.get("DATA_GOV_API_KEY", "").strip()
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    by_contest = {c["id"]: c for c in contests["contests"]}
    today = date.today().isoformat()
    out_dir = DATA / "finance"
    out_dir.mkdir(exist_ok=True)
    federal = [cand for cand in candidates if by_contest[cand["contest"]]["district_type"] == "cd"]

    if not key:
        print("DATA_GOV_API_KEY is not set (put it in .env). Writing finance: null for the 8 federal candidates.", file=sys.stderr)
        for cand in federal:
            (out_dir / f"{cand['slug']}.json").write_text(
                json.dumps({"slug": cand["slug"], "finance": None, "checked": today, "note": "OpenFEC not queried: DATA_GOV_API_KEY missing."}, indent=2) + "\n"
            )
        return 0

    with client(key) as c:
        for cand in federal:
            contest = by_contest[cand["contest"]]
            fc = find_candidate(c, cand["name"], contest["district_number"])
            if not fc:
                rec = {"slug": cand["slug"], "finance": None, "checked": today, "note": f"No FEC candidate record matched for {cand['name']} (WA-{contest['district_number']}) as of {today}."}
                print(f"  {cand['slug']}: no FEC candidate record")
            else:
                t = totals(c, fc["candidate_id"])
                com = principal_committee(c, fc["candidate_id"])
                top = top_contributors(c, com) if com else []
                if t is None:
                    rec = {"slug": cand["slug"], "finance": None, "checked": today, "fec_candidate_id": fc["candidate_id"], "note": f"FEC candidate {fc['candidate_id']} has no financial totals filed for the {CYCLE} cycle as of {today}."}
                    print(f"  {cand['slug']}: {fc['candidate_id']} no totals filed")
                else:
                    receipts = float(t["receipts"] or 0)
                    unitemized = float(t["individual_unitemized_contributions"] or 0)
                    rec = {
                        "slug": cand["slug"],
                        "checked": today,
                        "finance": {
                            "source": "fec",
                            "filer_id": fc["candidate_id"],
                            "filer_name": fc["name"],
                            "committee_id": com,
                            "pdc_url": FEC_CANDIDATE_PAGE.format(id=fc["candidate_id"], cycle=CYCLE),
                            "total_raised": round(receipts, 2),
                            "total_spent": round(float(t["disbursements"] or 0), 2),
                            "cash_on_hand": round(float(t["cash_on_hand"]), 2) if t["cash_on_hand"] is not None else None,
                            "as_of": t["coverage_end_date"] or today,
                            "last_report": t["last_report"],
                            "top_contributors": top,
                            "top_contributors_note": "aggregated from the 100 largest itemized receipts to the principal campaign committee, excluding conduit (ActBlue/WinRed) roll-ups and memo entries",
                            "small_donor_share": round(unitemized / receipts, 3) if receipts > 0 else None,
                            "small_donor_note": SMALL_DONOR_NOTE,
                            "incumbent_challenge": fc.get("incumbent_challenge"),
                        },
                    }
                    print(f"  {cand['slug']}: {fc['candidate_id']} raised ${receipts:,.0f} through {t['coverage_end_date']}")
            (out_dir / f"{cand['slug']}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
