"""Identify which Supreme Court candidates are sitting justices, from the court's own bios index.

Source: https://www.courts.wa.gov/appellate_trial_courts/supreme/bios/
Output: data/justices.json  {slug: {incumbent, current_office, sources}}

Usage:
    uv run python -m clearballot.courts
"""
from __future__ import annotations

import html
import json
import re
from datetime import date

import httpx

from .ballot import slugify
from .paths import DATA

BIOS_INDEX = "https://www.courts.wa.gov/appellate_trial_courts/supreme/bios/"


def sitting_justices() -> list[dict]:
    # courts.wa.gov serves a stub page to the default python-httpx user agent.
    r = httpx.get(BIOS_INDEX, follow_redirects=True, timeout=60, headers={"User-Agent": "Mozilla/5.0 (compatible; clear-ballot/0.1)"})
    r.raise_for_status()
    out = []
    for a in re.finditer(r'<a[^>]*href="([^"]*fileID=[^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", a.group(2)))).strip()
        if not label:
            continue
        title = "Chief Justice" if label.upper().startswith("CHIEF JUSTICE") else ("Associate Chief Justice" if label.upper().startswith("ASSOCIATE CHIEF") else "Justice")
        name = re.sub(r"^(ASSOCIATE CHIEF JUSTICE|CHIEF JUSTICE|JUSTICE)\s+", "", label, flags=re.I).strip()
        out.append({"name": name, "title": title, "url": "https://www.courts.wa.gov" + html.unescape(a.group(1))})
    return out


def main() -> int:
    contests = json.loads((DATA / "contests.json").read_text())
    candidates = json.loads((DATA / "candidates.json").read_text())
    by_contest = {c["id"]: c for c in contests["contests"]}
    today = date.today().isoformat()
    justices = sitting_justices()
    print(f"{len(justices)} sitting justices listed at {BIOS_INDEX}")
    result = {}
    for cand in candidates:
        contest = by_contest[cand["contest"]]
        if contest["district_type"] != "statewide":
            continue
        toks = slugify(cand["name"]).split("-")
        first, last = toks[0], toks[-1]
        hit = None
        for j in justices:
            jt = slugify(j["name"]).split("-")
            if jt[-1] == last and jt[0].startswith(first[:3]):
                hit = j
        if hit:
            result[cand["slug"]] = {
                "incumbent": True,
                "current_office": f"{hit['title']}, Washington Supreme Court",
                "website": None,
                "sources": [
                    {
                        "id": "courts-bio",
                        "title": f"Washington Supreme Court biography: {hit['title']} {hit['name']}",
                        "url": hit["url"],
                        "publisher": "Washington State Courts",
                        "accessed": today,
                        "kind": "official",
                    }
                ],
            }
            print(f"  {cand['slug']}: sitting {hit['title']}")
        else:
            result[cand["slug"]] = {"incumbent": False, "current_office": None, "website": None, "sources": []}
    (DATA / "justices.json").write_text(json.dumps({"source": BIOS_INDEX, "as_of": today, "candidates": result}, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
