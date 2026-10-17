"""Acceptance test for districts.json + the Census geocoder (SCOPE.md, Session 1 item 2).

Network test: it calls the live Census geocoder. Both expected results were
cross-checked on 2026-10-17 against the WA Legislature District Finder
(https://app.leg.wa.gov/DistrictFinder/).
"""
import json

import httpx
import pytest

from clearballot.geocode import ballot_for, geocode
from clearballot.paths import DATA

CASES = [
    # (address, expected cd, expected ld, expected US House contest, expected LD contests)
    (
        "401 5th Ave Seattle WA 98104",  # King County Courthouse, Seattle
        "5309",
        "53034",
        "contest-us-house-cd-9",
        ["contest-ld-34-senator", "contest-ld-34-rep-pos-1", "contest-ld-34-rep-pos-2"],
    ),
    (
        "450 110th Ave NE Bellevue WA 98004",  # Bellevue City Hall, Eastside
        "5301",
        "53048",
        "contest-us-house-cd-1",
        ["contest-ld-48-senator", "contest-ld-48-rep-pos-1", "contest-ld-48-rep-pos-2"],
    ),
]


def test_districts_json_covers_every_contest():
    contests = json.loads((DATA / "contests.json").read_text())
    districts = json.loads((DATA / "districts.json").read_text())["districts"]
    seen = {cid for d in districts.values() for cid in d["contests"]}
    assert seen == {c["id"] for c in contests["contests"]}
    assert districts["statewide"]["measures"] == [m["id"] for m in contests["measures"]]
    for c in contests["contests"]:
        assert c["district_id"] in districts


@pytest.mark.parametrize("address,cd,ld,house,ld_contests", CASES)
def test_geocode_resolves_to_correct_contests(address, cd, ld, house, ld_contests):
    try:
        res = geocode(address)
    except httpx.HTTPError as e:  # pragma: no cover
        pytest.skip(f"geocoder unreachable: {e}")
    assert res is not None, address
    assert res.cd == cd
    assert res.ld == ld
    b = ballot_for(res)
    assert b["in_king_county"]
    assert len(b["measures"]) == 3
    assert house in b["contests"]
    for c in ld_contests:
        assert c in b["contests"]
    assert sum(1 for c in b["contests"] if c.startswith("contest-supreme-court-")) == 5
