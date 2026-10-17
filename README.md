# Clear Ballot

A nonpartisan, plain-English, fully cited guide to the King County, WA ballot for the
**November 3, 2026 general election**. A voter enters their address and sees the three state
initiatives, their U.S. House race, their state legislative races, and the five state Supreme Court
races, each explained from official documents with every sentence cited.

Scope and decisions: [SCOPE.md](SCOPE.md). Content rules and the voting-record shortlist:
[content/pages/methodology.md](content/pages/methodology.md).

## Layout

```
allowlist.json           citation domain allowlist (validator + methodology page)
pipeline/                Python 3.12 (uv): ingestion + validation
  clearballot/
    ballot.py            sample ballot PDF -> data/contests.json, candidates.json, districts.json
    pamphlet.py          SOS Voters' Pamphlet PDFs -> sources/measures, sources/candidates, data/pamphlet.json
    geocode.py           Census geocoder test harness (what the site does in the browser)
    pdc.py               PDC finance for state/judicial candidates + measure committees -> data/finance/
    fec.py               OpenFEC finance for the 8 US House candidates -> data/finance/
    wa_leg.py            legislators, sponsored bills, shortlist votes -> data/records/, data/bill_shortlist.json
    congress.py          US House incumbents, sponsored bills, shortlist votes -> data/federal.json
    courts.py            sitting Supreme Court justices -> data/justices.json
    build_content.py     data -> content/contests/*.md, content/candidates/*.md (frontmatter; bodies stubbed)
    validate.py          content validator (uv run validate)
  tests/
sources/                 fetched raw documents (committed so reviews are reproducible)
data/                    generated structured JSON (committed)
content/                 authored content: measures/, contests/, candidates/, pages/
site/                    Astro site; reads ../content via the glob loader's `base` option
  functions/api/geocode.ts   Cloudflare Pages Function: CORS proxy + 24h cache for the Census geocoder
  scripts/check-banner.mjs   post-build gate: every draft page shows the banner, every page has Report-an-error
.github/workflows/validate.yml   tests + validator + astro build on PRs and main
```

## Setup

```sh
cd pipeline && uv sync            # Python deps
cd ../site && npm ci              # Astro + wrangler
cp .env.example .env              # then add DATA_GOV_API_KEY (api.data.gov; used for OpenFEC and Congress.gov)
```

## Running ingestion

Run from `pipeline/`. Each step is idempotent and writes only its own outputs. Order matters for the first run.

```sh
uv run python -m clearballot.ballot          # parse the sample ballot (downloads nothing; see below to re-fetch)
uv run python -m clearballot.pamphlet        # fetch the 3 King County pamphlet editions, extract measures + statements
uv run python -m clearballot.courts          # sitting justices
uv run python -m clearballot.wa_leg          # ~20s: members, sponsored bills, shortlist roll calls
uv run python -m clearballot.pdc             # ~60s: PDC summaries + top contributors (Socrata; no key needed)
uv run python -m clearballot.fec             # needs DATA_GOV_API_KEY; writes finance: null with a note if missing
uv run python -m clearballot.congress        # needs DATA_GOV_API_KEY; ~10s
uv run python -m clearballot.build_content   # refresh contest/candidate frontmatter; keeps bodies, status, reviews
uv run validate                              # must pass before committing content
uv run pytest -q                             # parser/validator tests (one test calls the live Census geocoder)
```

Re-download the sample ballot if King County rotates the URL hash:
`uv run python -m clearballot.ballot --url "https://cdn.kingcounty.gov/-/media/king-county/depts/elections/current-election/2026/11/sample-ballot.pdf"`
(the page that links it: https://kingcounty.gov/en/dept/elections/election-information/2026/november-general).
`uv run python -m clearballot.geocode "450 110th Ave NE Bellevue WA 98004"` prints what the site would show for an address.

## Authoring a candidate page

Candidate files live at `content/candidates/<slug>.md`. The frontmatter (party preference, incumbency,
finance, record, sources) is generated from `data/` by `build_content.py`; do not hand-edit those keys,
re-run the generator instead. Author the body sections, in this order: **Background**, **Positions**,
**Affiliations and endorsements**, **Record** (incumbents), **Funding**.

Rules the validator enforces (`uv run validate content/candidates/<slug>.md`):

- Every sentence ends with one or more `[^source-id]` markers that match an entry in `sources`.
- Every source URL is on a host in `allowlist.json`, except `kind: candidate-site` and `kind: endorsement`,
  which may be any https host but must be attributed in the prose ("The candidate says…").
- A `news` source is never cited in a section whose heading starts with "Fiscal impact".
- Headings, list markers, blockquote markers, and `<!-- TODO -->` lines are exempt; empty sections are allowed.
- Sentences over 35 words produce a warning. Aim for a 9th-grade reading level.

Add hand-written sources to the `sources` list with a stable `id`; the generator preserves any source id it
did not create, and preserves `status`, `reviewed_by`, `reviewed_at`, and `endorsements`.
Raw pamphlet statements for every candidate are in `sources/candidates/<slug>.txt` (page-linked).

## Reviewing and flipping status

Every content file has `status: draft | reviewed`. Draft pages publish with an "Unreviewed draft" banner;
the banner is the only gate. To review:

1. Open the PR (or the file) and check each sentence against its cited source.
2. Set `status: reviewed`, `reviewed_by: <your handle>`, `reviewed_at: YYYY-MM-DD`.
3. `uv run validate` (fails if a reviewed file lacks reviewer/date) and `cd site && npm run build`
   (fails if a reviewed page still shows the banner or a draft page does not).

Corrections go in `content/pages/corrections.md` with the date, the page, and the change. "Report an error"
links open a pre-filled GitHub issue labeled `error-report`.

## Running the site locally

```sh
cd site
npm run dev                 # Astro dev server (no geocode function; the address form will fall back to browse)
npm run build               # astro build + banner check -> dist/
npm run preview             # wrangler pages dev dist -> http://127.0.0.1:8788 with /api/geocode working
```

Markdown citations are rendered by `site/src/remark-sources-footnotes.mjs`, which turns `[^id]` markers plus
the frontmatter `sources` into numbered footnotes. The site uses Astro's unified (remark) processor explicitly
for this (see `astro.config.mjs`).

## Deploying (Cloudflare Pages, free plan)

Not yet deployed. Two options:

**Git integration (recommended):** Cloudflare dashboard → Workers & Pages → Create → Pages → connect the
GitHub repo. Settings: root directory `site`, build command `npm run build`, output directory `dist`,
production branch `main`. Pages picks up `site/functions/api/geocode.ts` automatically. No environment
variables are needed for the site (the API keys are only used by the Python ingestion, locally).

**CLI:** `cd site && npx wrangler login && npm run build && npx wrangler pages deploy dist --project-name clear-ballot`.

After the first deploy, set `site` in `site/astro.config.mjs` to the real URL (it is used for the
"Report an error" page link) and rebuild. Vercel also works (static output + an equivalent serverless
function at `api/geocode`), but the Pages Function would need porting.

## Session 2 plan

Candidate editorial prose, in batches by district, each batch a PR that Sam reviews via the diff:

1. US House (CDs 1, 7, 8, 9): 8 candidates. Start with `content/candidates/candidate-suzan-delbene.md`.
2. Supreme Court (Positions 1, 3, 4, 5, 7): 10 candidates.
3. Legislative districts in numeric order: LD 1, 5, 11, 12, 30, 31, 32, 33, 34, 36, 37, 41, 43, 45, 46, 47, 48.

For each candidate: read `sources/candidates/<slug>.txt` (pamphlet statement), the candidate's website
(cite as `kind: candidate-site`, attributed), the structured `finance` and `record` already in frontmatter,
and allowlisted reporting; write the five body sections; run `uv run validate`; open a PR.
Also outstanding from session 1: the contest pages' "About this office" note (cite the SOS "Descriptions
of Elected Offices" page), and tightening long sentences flagged by the validator on the measure pages.

Exact next command for session 2:

```sh
cd pipeline && uv run validate ../content/candidates/candidate-suzan-delbene.md
```
