# Clear Ballot — v1 Scope

Nonpartisan guide to the King County, WA ballot for the **November 3, 2026 general election**. A voter enters their address and gets the state measures, US House race, legislative district races, and WA Supreme Court races they will see, explained in plain English with every claim cited to a source.

This document is the full brief for the build session. It was produced from IDEA.md after a scoping discussion; decisions below are settled. Facts marked **verified** were checked live on 2026-10-17.

## Timing

WA mailed ballots around Oct 16, 2026. Election day is Nov 3 (ballots must be postmarked or in a drop box by 8pm). The site needs to be live and useful within days. Session 1 (this scope) must end with a deployed site, even if most candidate pages are still drafts.

## Decisions (settled)

| Topic | Decision |
|---|---|
| Jurisdiction | King County, WA only. Nov 3, 2026 general election only. |
| Contests in scope | 3 statewide initiatives; US House (CDs 1, 7, 8, 9); all WA legislative contests in LDs within King County; 5 WA Supreme Court positions. |
| Contests out of scope | County offices (Assessor, Director of Elections, Prosecuting Attorney, County Council), Court of Appeals, Superior/District/Municipal court judges, city/school/fire/special district measures and offices. Do not build data models that block adding these later, but do not ingest them. |
| Product form | Static site. Address lookup runs client-side via a geocoder; no database, no accounts, no server state. One tiny serverless function is allowed only as a CORS proxy for the geocoder. |
| Stack | Python 3.12 (`uv`) for ingestion/validation scripts; Astro for the site (content collections with zod schemas); deploy to Cloudflare Pages (free tier) with a Pages Function for the geocoder proxy. Vercel is an acceptable fallback. |
| Content authorship | The agent in the Claude Code session authors all explanatory content directly into content files, reading from fetched source documents in `sources/`. No LLM API calls from scripts. No API-credit spend. |
| Nonpartisanship rule | Every sentence of explanatory prose must carry a citation to a source on the allowlist. "Impacts" are drawn only from cited analyses (fiscal impact statements, legislative staff analyses, official arguments, reporting). The agent never infers impacts from general knowledge. |
| Candidate pages | Full editorial profile per candidate (background, positions by issue, affiliations/endorsements, funding, record), every sentence cited. Sam reviews all of them. |
| Voting records | Fixed bill shortlist with a published rule (see Content Rules). Plus each incumbent's sponsored bills. |
| Review gate | Content files carry `status: draft \| reviewed`. Everything builds and publishes, including candidate editorial prose, as soon as it exists. Draft items show a prominent "Unreviewed draft" banner; the banner is the only gate. Sam reviews via PR diffs and flips status. |
| Liability posture | Allowlisted sources + mandatory citations + draft banner + visible "Report an error" link + public corrections log + disclaimer. |
| Hosting cost | Free. |
| Sessions | Session 1: scaffold, ingestion, site, address lookup, the 3 measures fully written and reviewed-ready, candidate pages as structured cards with data filled in and prose sections stubbed. Sessions 2+: candidate editorial prose in batches by district. |

## Ballot inventory (verified from the King County sample ballot PDF)

Source: `https://cdn.kingcounty.gov/-/media/king-county/depts/elections/current-election/2026/11/sample-ballot.pdf` (the hash/rev query params may change; the page linking it is `https://kingcounty.gov/en/dept/elections/election-information/2026/november-general`).

**Statewide initiatives (3):**
- IL26-001 — Initiative to the Legislature; concerns parental rights relating to their children in public school. Would repeal amendments to a statute listing certain rights of parents/guardians and re-enact the law as originally enacted by a prior Initiative to the Legislature (I-2081).
- IP26-645 — Initiative to the People; concerns state and local taxes. Would repeal a 9.9% tax on annual individual income over $1,000,000, prohibit taxes measured by individual income, and define "income." Ballot summary states it would decrease funding for K-12, higher education, and human services.
- IL26-638 — Initiative to the Legislature; concerns participation in athletics at K-12 schools. Would prohibit students defined as "biologically male" from competing in certain school athletic activities intended for female students; requires verification of biological sex by healthcare providers.

**US House (4 contests, 8 candidates):** CD 1 (DelBene D, Silva R), CD 7 (Jayapal D, Sheth R), CD 8 (Schrier D, Meline R), CD 9 (Smith D, Basler R).

**WA Legislature:** LDs 1, 5, 11, 12, 30, 31, 32, 33, 34, 36, 37, 41, 43, 45, 46, 47, 48. Every LD has Representative Position 1 and Position 2 on the ballot; some also have State Senator. LD 5 Position 1 is a "short and full term" contest. Expect roughly 44 contests and 80 candidates; derive the exact list from the sample ballot, not from this estimate. Several LDs straddle county lines; the contest is still the same statewide contest and the candidate data is identical.

**WA Supreme Court (5 contests, 10 candidates):** Justice Position 1 (unexpired 2-year term), 3, 4, 5 (unexpired 2-year term), 7. Nonpartisan.

Total: 3 measures, ~53 contests, ~98 candidates.

## Data sources

### Allowlist (the only domains citations may point to)

Official / primary:
- `sos.wa.gov`, `voter.votewa.gov` — Statewide Voters' Pamphlet: measure explanatory statements, fiscal impact statements, official pro/con arguments and rebuttals, candidate statements. Online guide: `https://voter.votewa.gov/genericvoterguide.aspx`. PDFs listed at the "2026 Voters' Pamphlet PDFs" page under `https://www.sos.wa.gov/elections/data-research/election-data-and-maps/election-results-and-voters-pamphlets/2026-general-election-voters-guide`. Candidate filings: `https://voter.votewa.gov/CandidateList.aspx`.
- `kingcounty.gov`, `cdn.kingcounty.gov`, `info.kingcounty.gov` — sample ballot, local pamphlet, "who has filed."
- `ofm.wa.gov` — fiscal impact statements for initiatives.
- `leg.wa.gov`, `app.leg.wa.gov`, `lawfilesext.leg.wa.gov`, `wslwebservices.leg.wa.gov` — bills, bill reports (staff analyses), roll calls, sponsors, member records.
- `pdc.wa.gov`, `data.wa.gov` — state/legislative/judicial campaign finance.
- `fec.gov`, `api.open.fec.gov` — federal campaign finance.
- `congress.gov`, `api.congress.gov`, `clerk.house.gov` — federal votes and sponsored bills.
- `courts.wa.gov` — Supreme Court justice bios and opinions.
- The candidate's own campaign website and the official legislator/member page (cite as `candidate-site` with the URL; allowed only for the candidate's own stated positions and biography, and must be attributed as the candidate's claim).

Reporting (news sections only; no editorials, op-eds, or endorsements as fact):
- `seattletimes.com`, `cascadepbs.org` (Crosscut), `kuow.org`, `washingtonstatestandard.com`, `spokesman.com`, `apnews.com`, `publicola.com`, `thestranger.com` (news only), `ballotpedia.org`.

Endorsements: may be listed as "Endorsed by X" only when cited to the endorsing organization's own published endorsement page or the candidate's site, and must be labeled as self-reported when from the candidate's site.

Anything not on this list fails validation. Extending the list is a deliberate edit to `allowlist.json` with a commit message explaining why.

### Verified endpoints

- **Census Geocoder** (free, no key). Returns lat/lon plus the 120th Congressional District and 2026 State Legislative Districts (Upper and Lower) for a one-line address. Verified: `401 5th Ave Seattle WA 98104` → CD 9, LD 34.
  `https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress?address=<addr>&benchmark=Public_AR_Current&vintage=Current_Current&format=json`
  Geographies keys: `"120th Congressional Districts"` (field `GEOID` like `5309`), `"2026 State Legislative Districts - Lower"` (`GEOID` like `53034`). No `Access-Control-Allow-Origin` header was observed, so browsers need a proxy. Use a Cloudflare Pages Function at `/api/geocode` that forwards the request and adds CORS headers. Fallback plan if the proxy is a problem: ship LD and CD GeoJSON (OFM "Washington State Legislative Districts 2024" on geo.wa.gov, and the Census CD shapes) and do point-in-polygon in the browser with a third-party geocoder.
- **WA PDC contributions** (Socrata, free, no key for light use; app token optional). Verified query:
  `https://data.wa.gov/resource/kv7h-kjye.json?$limit=2&election_year=2026&jurisdiction_county=KING&$select=filer_name,office,legislative_district,party,amount,contributor_name`
  Returns rows with `filer_name`, `office`, `legislative_district`, `party`, `amount`, `contributor_name`, etc. Also use the PDC candidate summary endpoints and expenditures dataset as needed; the PDC candidate page pattern is `https://www.pdc.wa.gov/political-disclosure-reporting-data/browse-search-data/candidates/<id>`. Statewide judicial candidates file with the PDC too.
- **WA Legislature web services** (SOAP-style GET endpoints returning XML, free). Verified: `https://wslwebservices.leg.wa.gov/SponsorService.asmx/GetSponsors?biennium=2025-26` returns members with `Id`, `Name`, `Party`, `District`, `Agency`. Related services: `LegislationService.asmx` (`GetLegislationByYear`, `GetLegislation`), `RollCallService.asmx` (`GetRollCalls?biennium=&billNumber=`), `CommitteeService.asmx`. Bill pages: `https://app.leg.wa.gov/billsummary?BillNumber=<n>&Year=<y>`. Bill reports (staff analyses) are linked from the bill summary page.
- **King County sample ballot PDF** — text layer extracts cleanly; it is the authoritative contest/candidate list for King County.

### Needs a free key (register during session, store in `.env`, never commit)
- **OpenFEC** `https://api.open.fec.gov/v1/` — federal candidate totals and top contributors. Key from api.data.gov.
- **Congress.gov API** `https://api.congress.gov/v3/` — sponsored legislation and member info for the four US House incumbents. House roll call votes come from `clerk.house.gov` XML (no key).

If Sam has not supplied keys, build the ingestion with the key read from env, write a clear "missing key" message, and continue; do not fabricate data.

## Repository layout

```
clear-ballot/
  SCOPE.md                 # this file
  README.md                # what it is, how to run, how to review content
  allowlist.json           # citation domain allowlist
  pipeline/                # Python (uv project)
    pyproject.toml
    clearballot/
      ballot.py            # parse sample ballot PDF -> contests + candidates JSON
      geocode.py           # local test harness for the Census geocoder
      pdc.py               # PDC contributions summaries per candidate
      fec.py               # OpenFEC summaries for federal candidates
      wa_leg.py            # members, sponsored bills, roll calls on the shortlist
      congress.py          # federal sponsored bills + House roll calls on shortlist
      pamphlet.py          # fetch pamphlet PDFs/HTML into sources/, extract text
      validate.py          # content validator (see below)
    tests/
  sources/                 # fetched raw documents, committed (small text/PDF) so reviews are reproducible
    pamphlet/ measures/ bills/ candidates/
  data/                    # generated structured JSON, committed
    contests.json candidates.json finance/ records/ bill_shortlist.json
  content/                 # authored content (markdown + frontmatter), committed
    measures/<id>.md
    contests/<id>.md
    candidates/<slug>.md
    pages/methodology.md pages/corrections.md pages/about.md
  site/                    # Astro
    src/content/config.ts  # zod schemas mirroring content/ frontmatter
    src/pages/ ...
    functions/api/geocode.ts   # Cloudflare Pages Function CORS proxy
  .github/workflows/validate.yml  # runs validate.py + astro build on PRs
```

Astro's content collections should read directly from `content/` (symlink or configured path) so there is one copy of each file.

## Content model

All content files are markdown with YAML frontmatter. IDs are stable slugs derived from the ballot (`measure-ip26-645`, `contest-us-house-cd-7`, `contest-ld-34-rep-pos-1`, `candidate-pramila-jayapal`).

**Common frontmatter:** `id`, `title`, `status: draft|reviewed`, `reviewed_by`, `reviewed_at`, `updated_at`, `sources: [{id, title, url, publisher, accessed, kind: official|finance|legislative|news|candidate-site|endorsement}]`.

**Measure** body sections, in order: *What it does* (plain English, 3-6 sentences), *What changes if it passes / if it fails*, *Fiscal impact* (from OFM statement), *Arguments for* and *Arguments against* (summarized from the official pamphlet arguments and rebuttals, attributed to the committees that wrote them), *Impacts you may not be thinking about* (only items with a cited analysis or reporting), *Who is funding each side* (PDC committee totals and top contributors), *Related*: the bills or prior initiatives it responds to, with links. Frontmatter adds `ballot_number`, `measure_type`, `ballot_title` (verbatim), `yes_means`, `no_means`.

**Contest** frontmatter: `office`, `district_type: statewide|cd|ld`, `district_id` (e.g. `5309`, `53034`, or `statewide`), `partisan: bool`, `term_note` (e.g. "short and full term", "unexpired 2-year term"), `candidates: [slugs]`. Body optional: a short note on what the office does, cited to the SOS "Descriptions of Elected Offices" page.

**Candidate** frontmatter: `name`, `contest`, `party_preference` (verbatim from ballot, e.g. "Prefers Democratic Party"; null for nonpartisan), `incumbent: bool`, `current_office`, `website`, `pamphlet_statement_url`, `finance: {source, total_raised, total_spent, cash_on_hand, as_of, top_contributors: [{name, amount}], small_donor_share}`, `record: {sponsored_bills: [...], shortlist_votes: [{bill_id, title, vote: yea|nay|absent|excused, url}]}` (incumbents only), `endorsements: [{org, url, self_reported: bool}]`.
Body sections: *Background* (bio facts), *Positions* (by issue, each bullet cited; the candidate's own statements are attributed as such), *Affiliations and endorsements*, *Record* (prose summary of the structured record, incumbents only), *Funding* (prose summary of the structured finance). Session 1 ships every candidate with frontmatter populated from data and body sections present but containing only a `<!-- TODO: session 2 -->` marker; status `draft`.

**Citations in body text:** every sentence ends with one or more `[^src-id]` markers referencing `sources[].id`. A paragraph that is a direct quote uses a blockquote with the citation after it. The validator enforces this.

## Content rules (publish these on the Methodology page)

1. Plain English. Define any legal or fiscal term on first use. Target a reading level a 9th grader can follow.
2. Every sentence cites a source on the allowlist. No uncited sentences anywhere in measure or candidate bodies.
3. Arguments for and against are summarized from the official pamphlet arguments and attributed to their authors. The site never states which side is correct.
4. Impacts appear only when a cited fiscal statement, legislative staff analysis, court filing, or news report describes them. Reporting is cited as "reported by X"; it is not presented as the site's own finding.
5. Candidate positions come from the candidate's pamphlet statement, website, public votes, sponsored bills, or quoted statements in cited reporting. Characterizations from opponents or advocacy groups are excluded.
6. Funding figures come from PDC and FEC filings and show the "as of" date. Top contributors are listed as filed; employer and occupation are shown when filed.
7. Voting record shortlist rule: for state legislators, (a) the bills the three initiatives respond to (the 2025 parental-rights amendments to I-2081, the 2025 legislation creating the tax on income over $1M, and the bill(s) on K-12 athletics eligibility — identify exact bill numbers from leg.wa.gov and the SOS measure text during ingestion), (b) the 2025-27 operating budget and its major revenue bills, (c) the 2026 supplemental budget. For US House members, the comparable list is the final passage votes on the FY2026 appropriations/reconciliation packages and any bill cited in their own pamphlet statement. The rule and the resulting list are published; votes are shown as filed with a link to the roll call. Sponsored bills are listed in full for the current biennium.
8. Candidates may request corrections via the "Report an error" link. Corrections are logged publicly with date and change.
9. The site is nonpartisan, is not affiliated with any campaign, committee, or party, and does not endorse.

## Validator (`pipeline/clearballot/validate.py`)

Runs in CI on every PR and locally via `uv run validate`. Fails the build on:
- a frontmatter field missing or wrong type (mirror the Astro zod schema)
- any body sentence without a `[^id]` citation (sentence split on `.`, `?`, `!` followed by whitespace; headings, list markers, blockquote markers, and `<!-- TODO -->` lines are exempt; an empty section is allowed)
- a citation id not present in `sources`
- a source URL whose host is not in `allowlist.json`
- a `news` source used in a *Fiscal impact* section
- `status: reviewed` without `reviewed_by` and `reviewed_at`
- a candidate slug referenced by a contest that has no file, or vice versa
- a contest `district_id` not present in `data/districts.json`

Also warns (no fail) on sentences over 35 words and on sections that are still TODO.

## Site

Pages:
- `/` — address input (one line, "street, city, zip"), a short "what this is" paragraph, link to Methodology. On submit: call `/api/geocode`, read CD and LD GEOIDs, render the voter's ballot: measures, US House contest, LD contests, Supreme Court contests, each as a card linking to the detail page. Store nothing; put the district ids in the URL (`/ballot?cd=5309&ld=53034`) so the result is shareable and bookmarkable. If geocoding fails or the address is outside King County, say so and offer the browse-by-district fallback.
- `/ballot?cd=&ld=` — the rendered ballot for those districts, also reachable without geocoding.
- `/browse` — all contests grouped: measures, US House by CD, Legislature by LD, Supreme Court.
- `/measures/<id>`, `/contests/<id>`, `/candidates/<slug>` — detail pages. Candidate pages show the structured card (party preference, incumbent, finance summary with chart-free table, record table) above the prose.
- `/methodology`, `/corrections`, `/about`, `/sources` (every source used, grouped by publisher).

Every page: footer disclaimer ("Nonpartisan, volunteer-made, not affiliated with any campaign. Report an error."), "Report an error" linking to a pre-filled GitHub issue template that includes the page URL. Draft items show a top-of-page banner: "Unreviewed draft. This page was drafted from the sources listed below and has not yet been checked by a human reviewer." Build fails if the banner component is not wired to `status`.

Design: mobile-first, readable, fast. System font stack, no framework beyond Astro and minimal CSS. No analytics in v1. No tracking. Respect `prefers-color-scheme`.

Also link out, not replicate: King County Elections ballot status and drop box finder, VoteWA registration.

## Session 1 deliverables and acceptance

Done means all of the following are true and demonstrated with real command output:

1. `uv run python -m clearballot.ballot` parses the King County sample ballot PDF into `data/contests.json` and `data/candidates.json` covering exactly the in-scope contests; a test asserts the counts (3 measures, 4 CD contests, 5 Supreme Court contests, and the LD contest count derived from the PDF) and spot-checks three named candidates.
2. `data/districts.json` maps every in-scope `district_id` to its contests; the geocoder result for at least two real King County addresses (one Seattle, one Eastside, e.g. a Bellevue or Redmond civic address) resolves to the correct contests.
3. Pamphlet text for all 3 measures (explanatory statement, fiscal impact statement, arguments for/against, rebuttals) is fetched into `sources/measures/` and the three measure content files are complete in every section, pass the validator, and are `status: draft` awaiting Sam's review.
4. PDC finance frontmatter is populated for every state legislative and Supreme Court candidate who has a PDC filing; FEC for the 8 federal candidates if a key is available. Candidates with no filing show `finance: null` and the page says "No campaign finance filing found as of <date>."
5. For every incumbent state legislator: sponsored bills for 2025-26 and votes on the shortlist, in frontmatter, with links. `data/bill_shortlist.json` lists the shortlist with the rule text.
6. Every candidate has a content file with populated frontmatter, stubbed body, `status: draft`.
7. Validator passes on the whole `content/` tree. CI workflow runs validator and `astro build`.
8. The site is deployed on Cloudflare Pages (or Vercel) on a free plan at a URL Sam can open; address lookup works there end to end; Methodology, Corrections, About, Sources pages exist; the draft banner appears on draft pages; the Report-an-error link opens a prefilled issue.
9. README documents: how to run ingestion, how to author a candidate page, how to review and flip `status`, how to deploy, and the session 2 plan (candidate prose by district, suggested batch order: CDs first, then Supreme Court, then LDs by number).
10. Everything is committed on `main` with clear commit messages. No secrets committed. `.env.example` lists the keys.

Report at the end: what is deployed (URL), what is verified by running it, what is stubbed, what blocked (missing keys, source pages that changed shape), and the exact next command for session 2.

## Working agreements for the build session

- Do not fabricate any data, quote, figure, or source. If a source cannot be fetched, leave the field null and record the failure in the final report.
- Do not call any paid LLM API. Author content in-session.
- Give brief progress updates at natural checkpoints (scaffold done, ingestion done, measures written, deployed).
- Ask Sam only for things that cannot be recovered from the repo or the web: API keys, Cloudflare/Vercel account login, a GitHub repo to push to, the domain if any.
- Prefer boring, well-documented choices. Fewer dependencies.
- Keep the ballot inventory derived from the PDF, not hardcoded from this document; this document's inventory is for cross-checking.

## Known risks

- The sample ballot PDF URL carries a hash and may rotate; the parser should accept a local path and the README should say where to re-download.
- The SOS online voters' guide is an ASP.NET app; scraping may need the election id and per-race URLs. The PDF pamphlet is the fallback and has a clean text layer.
- The Census geocoder has no published rate limit but is a federal service; the proxy should cache responses briefly and the UI should degrade to browse-by-district if it is down.
- The exact bill numbers behind the three initiatives must be confirmed during ingestion. Do not guess.
- Full editorial candidate profiles are the largest review burden and the largest liability surface. They publish as soon as written, under the draft banner, by Sam's decision. The draft banner is not optional and must be visually unmissable on candidate pages.
- Astro content collections reading outside `src/` requires either a symlink or the `glob` loader with a custom base; pick one and document it.
