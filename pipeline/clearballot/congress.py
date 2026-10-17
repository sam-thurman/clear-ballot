"""Congress.gov records for the US House incumbents: sponsored bills (119th Congress) and
House roll-call votes on the federal shortlist.

Federal shortlist rule: see RULE below (published on the methodology page).

Needs DATA_GOV_API_KEY (works for api.congress.gov). Missing key -> no records written, exit 0.

Outputs:
  data/federal.json                 {candidates: {slug: {incumbent, current_office, bioguide, record, sources}}}
  data/bill_shortlist_federal.json  the shortlist with the rule text

Usage:
    uv run python -m clearballot.congress
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import date

import httpx

from .ballot import slugify
from .env import load_env
from .paths import DATA, SOURCES

API = "https://api.congress.gov/v3"
CONGRESS = 119
MEMBER_PAGE = "https://www.congress.gov/member/{slug}/{bioguide}"
BILL_PAGE = "https://www.congress.gov/bill/{congress}/{type_slug}/{number}"
BILL_PREFIX = {"HR": "H.R.", "S": "S.", "HJRES": "H.J.Res.", "SJRES": "S.J.Res.", "HRES": "H.Res.", "SRES": "S.Res.", "HCONRES": "H.Con.Res.", "SCONRES": "S.Con.Res."}
TYPE_SLUG = {"HR": "house-bill", "S": "senate-bill", "HJRES": "house-joint-resolution", "SJRES": "senate-joint-resolution", "HRES": "house-resolution", "HCONRES": "house-concurrent-resolution", "SCONRES": "senate-concurrent-resolution"}
# A public law is on the shortlist if any of its titles matches this: appropriations acts (full-year,
# continuing, consolidated) and budget reconciliation acts. "authorize appropriations" (e.g. the NDAA) does not match.
TITLE_RULE = re.compile(r"\bappropriations act\b|^(an act |an original bill )?making .*appropriations|provide for reconciliation", re.I)
PASSAGE_QUESTIONS = ("On Passage", "On Motion to Concur", "On Agreeing to the Conference Report", "On Motion to Suspend the Rules and Pass", "On Motion to Suspend the Rules and Concur", "On Motion to Suspend the Rules and Agree", "On Agreeing to the Senate Amendment")

RULE = (
    "For US House members we show the final-passage House roll-call votes on the appropriations and "
    "budget-reconciliation measures enacted during the 119th Congress (2025-26). The list is built "
    "automatically from the Congress.gov public-law list: a law qualifies if any of its titles contains "
    "'Appropriations Act', begins 'Making ... appropriations', or says 'provide for reconciliation'. "
    "Bills that merely authorize appropriations (such as the defense authorization act) do not qualify. "
    "For each, we take the last passage-type House vote (passage, concurrence in the Senate amendment, or "
    "agreeing to the conference report), as recorded by the Clerk of the House, with a link to the roll "
    "call. Any bill a candidate cites by number in their own Voters' Pamphlet statement is added. "
    "Sponsored bills are every measure the member introduced in the 119th Congress."
)


class CongressClient(httpx.Client):
    def get(self, url, **kw):  # type: ignore[override]
        for attempt in range(6):
            r = super().get(url, **kw)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Congress.gov {r.status_code} for {url}")
            return r
        raise RuntimeError(f"Congress.gov rate limit persisted for {url}")


def paginate(c: httpx.Client, path: str, key: str, params: dict | None = None, page_size: int = 250, max_pages: int = 40) -> list[dict]:
    """Offset-based pagination (the API's `next` links are unreliable: they can return short pages past `count`)."""
    out: list[dict] = []
    offset = 0
    for _ in range(max_pages):
        d = c.get(path, params={"limit": page_size, "offset": offset, **(params or {})}).json()
        rows = d.get(key, [])
        out.extend(rows)
        count = (d.get("pagination") or {}).get("count")
        offset += page_size
        if not rows or (count is not None and offset >= count):
            break
    return out


def current_wa_members(c: httpx.Client) -> list[dict]:
    return paginate(c, "/member/WA", "members", {"currentMember": "true"})


def shortlist_laws(c: httpx.Client) -> list[dict]:
    laws = paginate(c, f"/law/{CONGRESS}", "bills")
    out = []
    seen = set()
    for b in laws:
        key = (b["type"], str(b["number"]))
        if key in seen:
            continue
        seen.add(key)
        title = b.get("title") or ""
        # The list carries the short title only ("One Big Beautiful Bill Act"); check every title
        # (official titles read "An Act to provide for reconciliation..." / "Making appropriations...").
        titles = [title] + [t.get("title", "") for t in c.get(f"/bill/{CONGRESS}/{b['type'].lower()}/{b['number']}/titles", params={"limit": 250}).json().get("titles", [])]
        if any(TITLE_RULE.search(t or "") for t in titles):
            out.append({"type": b["type"], "number": str(b["number"]), "title": title, "laws": b.get("laws", []), "url": BILL_PAGE.format(congress=CONGRESS, type_slug=TYPE_SLUG.get(b["type"], b["type"].lower()), number=b["number"])})
    return out


def house_votes_index(c: httpx.Client) -> list[dict]:
    return paginate(c, f"/house-vote/{CONGRESS}", "houseRollCallVotes")


def vote_detail(c: httpx.Client, session: int, roll: int) -> dict:
    r = c.get(f"/house-vote/{CONGRESS}/{session}/{roll}")
    return r.json()["houseRollCallVote"]


def vote_members(c: httpx.Client, session: int, roll: int) -> dict[str, str]:
    # This endpoint returns every member in one response and ignores limit/offset.
    d = c.get(f"/house-vote/{CONGRESS}/{session}/{roll}/members", params={"limit": 250}).json()
    rows = (d.get("houseRollCallVoteMemberVotes") or {}).get("results", [])
    return {m["bioguideID"]: m.get("voteCast") for m in rows}


def sponsored(c: httpx.Client, bioguide: str) -> list[dict]:
    rows = paginate(c, f"/member/{bioguide}/sponsored-legislation", "sponsoredLegislation")
    out = []
    for b in rows:
        if b.get("congress") != CONGRESS or not b.get("number"):
            continue
        t = b.get("type", "")
        out.append(
            {
                "bill_id": f"{BILL_PREFIX.get(t, t)} {b['number']}",
                "title": b.get("title"),
                "status": (b.get("latestAction") or {}).get("text"),
                "status_date": (b.get("latestAction") or {}).get("actionDate"),
                "introduced": b.get("introducedDate"),
                "url": BILL_PAGE.format(congress=CONGRESS, type_slug=TYPE_SLUG.get(t, t.lower()), number=b["number"]),
            }
        )
    return out


def pamphlet_cited_bills(slug: str) -> list[str]:
    p = SOURCES / "candidates" / f"{slug}.txt"
    if not p.exists():
        return []
    return sorted(set(m.group(0) for m in re.finditer(r"\bH\.?\s?R\.?\s?\d{1,5}\b|\bS\.\s?\d{1,5}\b", p.read_text())))


def main() -> int:
    load_env()
    key = os.environ.get("DATA_GOV_API_KEY", "").strip()
    today = date.today().isoformat()
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    by_contest = {c["id"]: c for c in contests["contests"]}
    federal = [cand for cand in candidates if by_contest[cand["contest"]]["district_type"] == "cd"]
    if not key:
        print("DATA_GOV_API_KEY is not set; skipping Congress.gov. Federal incumbency/record will be null.", file=sys.stderr)
        return 0

    with CongressClient(base_url=API, params={"api_key": key, "format": "json"}, headers={"User-Agent": "clear-ballot/0.1"}, timeout=60) as c:
        members = current_wa_members(c)
        by_district = {str(m.get("district")): m for m in members if m.get("district")}

        print("building federal shortlist from public laws...")
        laws = shortlist_laws(c)
        votes_index = house_votes_index(c)
        shortlist = []
        for law in laws:
            cands = [v for v in votes_index if v.get("legislationType") == law["type"] and str(v.get("legislationNumber")) == law["number"]]
            chosen = None
            for v in sorted(cands, key=lambda v: (v["sessionNumber"], v["rollCallNumber"])):
                d = vote_detail(c, v["sessionNumber"], v["rollCallNumber"])
                q = d.get("voteQuestion") or ""
                if any(q.startswith(p) for p in PASSAGE_QUESTIONS):
                    chosen = {**v, "question": q, "result": d.get("result"), "date": (d.get("startDate") or "")[:10]}
            shortlist.append({**law, "law_numbers": [l.get("number") for l in law["laws"]], "house_vote": chosen})
            print(f"  {law['type']} {law['number']}: {law['title'][:70]} -> roll {chosen['rollCallNumber'] if chosen else None}")
        (DATA / "bill_shortlist_federal.json").write_text(json.dumps({"rule": RULE, "congress": CONGRESS, "as_of": today, "bills": shortlist}, indent=2, ensure_ascii=False) + "\n")

        vote_cache: dict[tuple, dict[str, str]] = {}
        out = {}
        for cand in federal:
            contest = by_contest[cand["contest"]]
            m = by_district.get(str(contest["district_number"]))
            toks = slugify(cand["name"]).split("-")
            is_member = bool(m) and slugify(m["name"]).split("-")[0] == toks[-1]  # API name is "Last, First"
            entry = {"incumbent": is_member, "current_office": None, "bioguide": None, "website": None, "record": None, "sources": []}
            if is_member:
                bio = m["bioguideId"]
                entry["bioguide"] = bio
                entry["current_office"] = f"U.S. Representative, Washington's {contest['district_number']}{'st' if contest['district_number']==1 else 'th'} Congressional District"
                member_url = MEMBER_PAGE.format(slug=slugify(cand["name"]), bioguide=bio)
                entry["sources"].append({"id": "congress-member", "title": f"Congress.gov member page: {m['name']}", "url": member_url, "publisher": "Library of Congress (Congress.gov)", "accessed": today, "kind": "legislative"})
                sp = sponsored(c, bio)
                votes = []
                for b in shortlist:
                    hv = b["house_vote"]
                    rec = {"bill_id": f"{BILL_PREFIX.get(b['type'], b['type'])} {b['number']}", "title": b["title"], "category": "federal", "vote": None, "chamber": "House", "date": None, "url": b["url"], "roll_call_url": None, "question": None}
                    if hv:
                        k = (hv["sessionNumber"], hv["rollCallNumber"])
                        if k not in vote_cache:
                            vote_cache[k] = vote_members(c, *k)
                        cast = (vote_cache[k].get(bio) or "").lower()
                        rec.update({"vote": {"yea": "yea", "aye": "yea", "nay": "nay", "no": "nay", "not voting": "absent", "present": "present"}.get(cast, cast or "not recorded"), "date": hv["date"], "roll_call_url": hv.get("sourceDataURL"), "question": hv["question"]})
                    votes.append(rec)
                cited = pamphlet_cited_bills(cand["slug"])
                entry["record"] = {"as_of": today, "sponsored_bills_url": f"https://www.congress.gov/member/{slugify(cand['name'])}/{bio}?q=%7B%22sponsorship%22%3A%22sponsored%22%2C%22congress%22%3A%22{CONGRESS}%22%7D", "sponsored_bills": sp, "shortlist_votes": votes, "pamphlet_cited_bills": cited}
                entry["sources"].append({"id": "congress-sponsored", "title": f"Sponsored legislation, {CONGRESS}th Congress: {m['name']}", "url": entry["record"]["sponsored_bills_url"], "publisher": "Library of Congress (Congress.gov)", "accessed": today, "kind": "legislative"})
                print(f"  {cand['slug']}: {bio}, {len(sp)} sponsored bills, votes {[v['vote'] for v in votes]}, pamphlet-cited {cited}")
            else:
                print(f"  {cand['slug']}: not a current member")
            out[cand["slug"]] = entry
        (DATA / "federal.json").write_text(json.dumps({"congress": CONGRESS, "as_of": today, "source": f"{API}/member/WA", "candidates": out}, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
