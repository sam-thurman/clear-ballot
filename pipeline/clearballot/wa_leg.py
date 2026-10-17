"""WA Legislature records for state legislative candidates.

Produces, for every ballot candidate who is a current member of the Legislature:
  data/records/<slug>.json  {member, sponsored_bills, shortlist_votes}
and data/bill_shortlist.json (the published voting-record shortlist with the rule text),
plus data/legislators.json (ballot candidate -> member match, incumbent flag).

Sources (all leg.wa.gov):
  SponsorService.asmx/GetSponsors?biennium=2025-26           members with Id/Name/Party/District/Agency
  LegislationService.asmx/GetLegislation?biennium=&billNumber=  bill titles/status
  LegislationService.asmx/GetRollCalls?biennium=&billNumber=    roll calls with per-member votes
  app.leg.wa.gov/bi/report/BillsBySponsor?...primarybills      prime-sponsored bills (HTML report)

Usage:
    uv run python -m clearballot.wa_leg
"""
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date

import httpx

from .ballot import slugify
from .paths import DATA

BIENNIUM = "2025-26"
WS = "https://wslwebservices.leg.wa.gov"
NS = "{http://WSLWebServices.leg.wa.gov/}"
BILL_PAGE = "https://app.leg.wa.gov/billsummary?BillNumber={n}&Year={y}"
SPONSOR_REPORT = (
    "https://app.leg.wa.gov/bi/report/BillsBySponsor?{chamber}SponsorId={id}&biennium={b}"
    "&billsBySponsorReportType=primarybills&hasCompanionBills=false&sponsorType={chamber}"
)

SHORTLIST_RULE = (
    "For state legislators we show votes on a fixed shortlist, chosen by a rule published before any "
    "votes were looked up: (a) the bills the three 2026 initiatives respond to: the 2025 bill that "
    "amended the parental-rights statute created by Initiative 2081 (IL26-001), the 2026 bill that "
    "created the tax on income over $1 million (IP26-645), and the 2025-26 bills on K-12 athletics "
    "eligibility (IL26-638); (b) the 2025-27 operating budget and the major revenue bills passed "
    "alongside it; (c) the 2026 supplemental operating budget. Votes shown are the final passage "
    "vote in each chamber (the last 'final passage' roll call, which is the vote on the version that "
    "became law), as recorded by the Legislature, with a link to the bill page. Bills that never "
    "received a floor vote are listed with no votes. Sponsored bills are every bill the legislator "
    "was prime sponsor of in the 2025-26 biennium."
)

# (bill number, year of the bill page, category, note)
SHORTLIST = [
    (1296, 2025, "a", "Amended RCW 28A.605.005, the parental-rights statute enacted by Initiative 2081. IL26-001 would repeal these amendments."),
    (6346, 2026, "a", "Created the 9.9% tax on individual income over $1,000,000. IP26-645 would repeal it."),
    (1699, 2025, "a", "Would have barred 'biologically male' students from girls' interscholastic sports; same title as IL26-638. Died in House Education Committee; no floor vote."),
    (5097, 2025, "a", "Girls' interscholastic athletics eligibility. Died in Senate Early Learning & K-12 Committee; no floor vote."),
    (5012, 2025, "a", "Organization of interscholastic athletics. Died in Senate Early Learning & K-12 Committee; no floor vote."),
    (5167, 2025, "b", "2025-27 biennial operating budget."),
    (5813, 2025, "b", "Revenue: capital gains and estate tax changes (education legacy trust account)."),
    (5814, 2025, "b", "Revenue: extended sales tax to certain services and other excise tax changes."),
    (2081, 2025, "b", "Revenue: business and occupation tax surcharges and rates."),
    (5794, 2025, "b", "Revenue: repeal of certain tax preferences."),
    (2077, 2025, "b", "Revenue: tax on certain zero-emission vehicle credit sales."),
    (5998, 2026, "c", "2026 supplemental operating budget."),
]

CLIENT = httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "clear-ballot/0.1 (+github.com/sam-thurman/clear-ballot)"})


def xml_get(path: str, **params) -> ET.Element:
    r = CLIENT.get(f"{WS}/{path}", params=params)
    r.raise_for_status()
    return ET.fromstring(r.content)


def get_members() -> list[dict]:
    root = xml_get("SponsorService.asmx/GetSponsors", biennium=BIENNIUM)
    out = []
    for m in root:
        out.append({c.tag[len(NS):]: (c.text or "").strip() for c in m})
    return out


def get_legislation(bill_number: int) -> dict | None:
    root = xml_get("LegislationService.asmx/GetLegislation", biennium=BIENNIUM, billNumber=bill_number)
    legs = root.findall(NS + "Legislation")
    if not legs:
        return None
    # Several versions are returned (original, substitute, engrossed...). Take the most advanced.
    def rank(l):
        return (int(l.findtext(NS + "SubstituteVersion") or 0), int(l.findtext(NS + "EngrossedVersion") or 0))
    leg = max(legs, key=rank)
    cs = leg.find(NS + "CurrentStatus")
    return {
        "bill_id": leg.findtext(NS + "BillId"),
        "bill_number": bill_number,
        "title": leg.findtext(NS + "LongDescription"),
        "short_title": leg.findtext(NS + "ShortDescription"),
        "status": cs.findtext(NS + "Status") if cs is not None else None,
        "history": cs.findtext(NS + "HistoryLine") if cs is not None else None,
        "introduced": (leg.findtext(NS + "IntroducedDate") or "")[:10],
    }


def get_final_passage_votes(bill_number: int) -> dict:
    """Return {"House": {...}, "Senate": {...}} for the last final-passage roll call in each chamber."""
    root = xml_get("LegislationService.asmx/GetRollCalls", biennium=BIENNIUM, billNumber=bill_number)
    chosen: dict[str, dict] = {}
    for rc in root.findall(NS + "RollCall"):
        motion = (rc.findtext(NS + "Motion") or "").strip()
        if "final passage" not in motion.lower():
            continue
        agency = rc.findtext(NS + "Agency")
        entry = {
            "agency": agency,
            "motion": motion,
            "date": (rc.findtext(NS + "VoteDate") or "")[:10],
            "sequence": rc.findtext(NS + "SequenceNumber"),
            "yea": int(rc.find(NS + "YeaVotes").findtext(NS + "Count") or 0),
            "nay": int(rc.find(NS + "NayVotes").findtext(NS + "Count") or 0),
            "absent": int(rc.find(NS + "AbsentVotes").findtext(NS + "Count") or 0),
            "excused": int(rc.find(NS + "ExcusedVotes").findtext(NS + "Count") or 0),
            "votes": {},
        }
        for v in rc.find(NS + "Votes"):
            mid = v.findtext(NS + "MemberId")
            vote = (v.findtext(NS + "VOte") or v.findtext(NS + "Vote") or "").strip().lower()
            entry["votes"][mid] = vote
        prev = chosen.get(agency)
        # keep the latest final passage vote per chamber
        if prev is None or (entry["date"], int(entry["sequence"] or 0)) >= (prev["date"], int(prev["sequence"] or 0)):
            chosen[agency] = entry
    return chosen


def get_sponsored_bills(member_id: str, chamber: str) -> list[dict]:
    url = SPONSOR_REPORT.format(chamber=chamber, id=member_id, b=BIENNIUM)
    r = CLIENT.get(url)
    r.raise_for_status()
    rows = re.findall(r"<tr.*?</tr>", r.text, re.S)
    bills = []
    for row in rows:
        cells = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        links = re.findall(r'href="(https://app\.leg\.wa\.gov/billsummary\?[^"]+)"', row)
        if len(cells) < 9 or not links or cells[1] == "Bill":
            continue
        bills.append(
            {
                "bill_id": cells[1],
                "title": cells[4],
                "status": cells[5],
                "status_date": cells[7],
                "url": html.unescape(links[0]),
            }
        )
    return bills


def match_candidates(members: list[dict], candidates: list[dict], contests: dict) -> list[dict]:
    """Match each state-legislative ballot candidate to a current member (same district, same name)."""
    by_contest = {c["id"]: c for c in contests["contests"]}
    out = []
    for cand in candidates:
        contest = by_contest[cand["contest"]]
        if contest["district_type"] != "ld":
            continue
        ld = str(contest["district_number"])
        toks = slugify(cand["name"]).split("-")
        first, last = toks[0], toks[-1]
        hits = []
        for m in members:
            if m["District"] != ld:
                continue
            mt = slugify(m["Name"]).split("-")
            if mt[-1] == last and mt[0] == first:
                hits.append(m)
        if not hits:
            out.append({"slug": cand["slug"], "member": None, "incumbent": False, "current_office": None})
            continue
        seeking_senate = contest["office"] == "State Senator"
        # Prefer the chamber matching the seat sought; a person listed in both chambers
        # (appointed from House to Senate) is treated as holding the later seat (Senate).
        senate = [m for m in hits if m["Agency"] == "Senate"]
        house = [m for m in hits if m["Agency"] == "House"]
        current = (senate or house)[0]
        chamber = current["Agency"]
        office = f"State {'Senator' if chamber == 'Senate' else 'Representative'}, Legislative District {ld}"
        incumbent = (chamber == "Senate") == seeking_senate
        out.append(
            {
                "slug": cand["slug"],
                "member": {"id": current["Id"], "name": current["Name"], "party": current["Party"], "district": ld, "chamber": chamber,
                           "url": f"https://leg.wa.gov/legislators/member/{current['Id']}"},
                "incumbent": incumbent,
                "current_office": office,
            }
        )
    return out


def main() -> int:
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    today = date.today().isoformat()

    print("fetching members...")
    members = get_members()
    matches = match_candidates(members, candidates, contests)
    (DATA / "legislators.json").write_text(json.dumps({"biennium": BIENNIUM, "source": f"{WS}/SponsorService.asmx/GetSponsors?biennium={BIENNIUM}", "as_of": today, "candidates": matches}, indent=2, ensure_ascii=False) + "\n")
    current = [m for m in matches if m["member"]]
    print(f"matched {len(current)} of {len(matches)} state legislative candidates to current members; incumbents for seat sought: {sum(1 for m in current if m['incumbent'])}")

    print("fetching shortlist bills and roll calls...")
    shortlist = []
    rollcalls: dict[int, dict] = {}
    for n, year, cat, note in SHORTLIST:
        leg = get_legislation(n)
        if leg is None:
            print(f"  WARNING: bill {n} not found", file=sys.stderr)
            continue
        rc = get_final_passage_votes(n)
        rollcalls[n] = rc
        shortlist.append(
            {
                **leg,
                "category": cat,
                "note": note,
                "url": BILL_PAGE.format(n=n, y=year),
                "final_passage": {
                    ch: {k: v for k, v in e.items() if k != "votes"} for ch, e in rc.items()
                },
            }
        )
        print(f"  {leg['bill_id']}: {leg['short_title']} [{leg['status']}] final passage in {sorted(rc)}")
    (DATA / "bill_shortlist.json").write_text(
        json.dumps({"rule": SHORTLIST_RULE, "biennium": BIENNIUM, "as_of": today, "bills": shortlist}, indent=2, ensure_ascii=False) + "\n"
    )

    print("fetching sponsored bills per member...")
    (DATA / "records").mkdir(exist_ok=True)
    for m in current:
        mem = m["member"]
        sponsored = get_sponsored_bills(mem["id"], mem["chamber"])
        votes = []
        for b in shortlist:
            rc = rollcalls[b["bill_number"]]
            vote = None
            chamber = None
            for ch in ("Senate", "House"):
                if ch in rc and mem["id"] in rc[ch]["votes"]:
                    vote, chamber = rc[ch]["votes"][mem["id"]], ch
                    break
            votes.append(
                {
                    "bill_id": b["bill_id"],
                    "title": b["title"],
                    "category": b["category"],
                    # "not recorded": the chamber held a final passage vote but this member is not on the roll call
                    # (most often because they were not yet a member). None: the bill never had a floor vote.
                    "vote": vote if vote in ("yea", "nay", "absent", "excused") else (None if not rc else "not recorded"),
                    "chamber": chamber,
                    "date": rc[chamber]["date"] if chamber else None,
                    "url": b["url"],
                }
            )
        rec = {
            "slug": m["slug"],
            "member": mem,
            "as_of": today,
            "sponsored_bills_source": SPONSOR_REPORT.format(chamber=mem["chamber"], id=mem["id"], b=BIENNIUM),
            "sponsored_bills": sponsored,
            "shortlist_votes": votes,
        }
        (DATA / "records" / f"{m['slug']}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        print(f"  {m['slug']}: {len(sponsored)} sponsored bills; votes: {[v['vote'] for v in votes]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
