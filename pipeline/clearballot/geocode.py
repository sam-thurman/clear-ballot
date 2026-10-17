"""Local test harness for the Census geocoder -> ballot lookup.

This mirrors what the site does in the browser (via the /api/geocode Pages
Function): geocode a one-line address, read the Congressional District and
State Legislative District (Lower) GEOIDs, and look them up in data/districts.json.

Usage:
    uv run python -m clearballot.geocode "401 5th Ave Seattle WA 98104" [more addresses...]
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import httpx

from .paths import DATA

GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
PARAMS = {"benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"}


@dataclass
class GeocodeResult:
    matched_address: str
    lat: float
    lon: float
    county_geoid: str | None
    cd: str | None
    ld: str | None


def geocode(address: str, timeout: float = 30.0) -> GeocodeResult | None:
    r = httpx.get(GEOCODER_URL, params={"address": address, **PARAMS}, timeout=timeout)
    r.raise_for_status()
    matches = r.json()["result"]["addressMatches"]
    if not matches:
        return None
    m = matches[0]
    g = m.get("geographies", {})
    keys = json.loads((DATA / "districts.json").read_text())["geocoder_keys"]

    def first_geoid(key: str) -> str | None:
        rows = g.get(key) or []
        return rows[0].get("GEOID") if rows else None

    return GeocodeResult(
        matched_address=m["matchedAddress"],
        lat=m["coordinates"]["y"],
        lon=m["coordinates"]["x"],
        county_geoid=first_geoid(keys["county"]),
        cd=first_geoid(keys["cd"]),
        ld=first_geoid(keys["ld"]),
    )


def ballot_for(result: GeocodeResult) -> dict:
    districts = json.loads((DATA / "districts.json").read_text())
    d = districts["districts"]
    in_county = result.county_geoid == districts["county_geoid"]
    out = {
        "in_king_county": in_county,
        "cd": result.cd,
        "ld": result.ld,
        "measures": d["statewide"]["measures"] if in_county else [],
        "contests": [],
    }
    if in_county:
        for key in (result.cd, result.ld):
            if key and key in d:
                out["contests"].extend(d[key]["contests"])
        out["contests"].extend(d["statewide"]["contests"])
    return out


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    rc = 0
    for addr in args:
        res = geocode(addr)
        if res is None:
            print(f"{addr!r}: no match")
            rc = 1
            continue
        b = ballot_for(res)
        print(f"{addr!r} -> {res.matched_address} ({res.lat:.5f}, {res.lon:.5f})")
        print(f"  county={res.county_geoid} in_king_county={b['in_king_county']} cd={res.cd} ld={res.ld}")
        print(f"  measures: {b['measures']}")
        print(f"  contests: {b['contests']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
