# Clear Ballot — candidate page authoring brief (session 2)

You are writing the editorial body of candidate pages for Clear Ballot, a nonpartisan, fully cited guide to the King County, WA ballot for the November 3, 2026 general election. Repo: `/Users/sam/Personal Projects/repos/clear-ballot`. Work only on the candidate slugs assigned to you. Do NOT run any git commands, do NOT run `build_content.py`, do NOT edit files for other candidates, and do NOT edit anything under `site/`, `data/`, or `pipeline/`. The parent agent commits and opens PRs.

## What already exists for each candidate

- `content/candidates/<slug>.md` — frontmatter is already populated (name, contest, party_preference, incumbent, current_office, website, pamphlet_statement_url, finance, record, sources). The body has five stub sections, each containing `<!-- TODO: session 2 -->`.
- `sources/candidates/<slug>.txt` — the candidate's statement from the state Voters' Pamphlet, with page link. This is your primary source. Its source id in frontmatter is `sos-pamphlet`.
- `data/finance/<slug>.json` — full finance record (PDC or FEC). Summarized in frontmatter `finance` (source id `finance`).
- `data/records/<slug>.json` (state incumbents) or `data/federal.json` (US House incumbents) — sponsored bills and shortlist votes. Summarized in frontmatter `record` (source ids `leg-sponsored` / `congress-sponsored`; member page `leg-member` / `congress-member`).
- `data/justices.json` — sitting Supreme Court justices with a `courts-bio` source (courts.wa.gov biography URL).
- `allowlist.json` — the only domains that may be cited (official, finance, legislative, news). `candidate-site` and `endorsement` kinds may be any https host.
- The content rules are in `content/pages/methodology.md`. Read it once.

## Gathering sources (save everything you use)

1. Read `sources/candidates/<slug>.txt`.
2. Fetch the candidate's website (the `website` field in frontmatter). Use `curl -sL -A "Mozilla/5.0 (Macintosh) clear-ballot/0.1" <url>` and extract readable text (strip tags with Python). Also try obvious subpages: `/about`, `/issues`, `/priorities`, `/endorsements`, `/meet-<first>` if the homepage links to them. Save the text to `sources/candidates/<slug>-site.txt` with a header: `SOURCE: <page title>`, `URL: <url>`, `RETRIEVED: 2026-10-17`. One file per page is fine (`<slug>-site-issues.txt` etc.). If the site is unreachable or blocked, record that in your final report and do not guess its content.
3. For incumbents, open the official member page URL already in frontmatter (`leg-member` / `congress-member` / `courts-bio`); fetch and save it as `sources/candidates/<slug>-official.txt`. For courts.wa.gov use the Mozilla user agent or it serves a stub.
4. News (optional, use sparingly): `web_search` with `site:` restricted to allowlisted news domains (seattletimes.com, kuow.org, cascadepbs.org, washingtonstatestandard.com, spokesman.com, apnews.com, publicola.com, thestranger.com, ballotpedia.org). Only news sections: skip URLs containing `/opinion/`, `/editorial`, `/endorse`. washingtonstatestandard.com blocks scripted fetches; skip it unless the article is in its RSS feed (`https://washingtonstatestandard.com/feed/`). Save any article you cite to `sources/candidates/<slug>-news-<n>.txt` with SOURCE/URL/PUBLISHED/RETRIEVED header. Use news only for (a) facts about the candidate's background or record, (b) the candidate's own quoted statements. Never use an opponent's or advocacy group's characterization.
5. Ballotpedia is allowlisted (kind `news`) and is useful for biography facts; cite it as "according to Ballotpedia".

## Writing the body

Replace each `<!-- TODO: session 2 -->` with prose. Keep the five headings in this exact order and wording:

```
## Background
## Positions
## Affiliations and endorsements
## Record
## Funding
```

Rules (the validator enforces 1–3; the reviewer enforces the rest):

1. **Every sentence ends with one or more citation markers** like `[^sos-pamphlet]` or `[^site]`, placed after the period: `...in 2017.[^sos-pamphlet]` A bullet item is a sentence and needs its own citation. Headings and blank lines are exempt.
2. Every marker must match an `id` in the file's frontmatter `sources` list. Add new sources there (see below).
3. A `news` source may never be cited in a section headed "Fiscal impact" (not applicable here, but do not add such a heading).
4. **Plain English**, 9th-grade reading level, sentences of 35 words or fewer (the validator warns above 35; keep under). Define any legal or fiscal term on first use.
5. **Attribute the candidate's own claims as claims.** Pamphlet and website content is what the candidate says: "In the Voters' Pamphlet, X says…", "X's campaign website lists…", "X describes…". Do not restate a candidate's self-description as established fact. Official pages (legislature, Congress.gov, courts.wa.gov) and filings can be stated as fact.
6. **No characterizations from opponents or advocacy groups.** No endorsements from editorial boards. No adjectives of your own about the candidate ("experienced", "controversial", "popular"). Never say who should win or which side is right.
7. **Do not infer or fabricate.** If the sources do not say it, do not write it. If a section has little material, write two or three honest sentences and stop. "The candidate's website does not list positions on specific issues.[^site]" is a fine sentence.
8. Each section's content:
   - **Background**: biography facts. Education, work, prior offices, community roles, from the pamphlet ("Elected Experience", "Other Professional Experience", "Education", "Community Service"), the official page, and the site. 3–8 sentences.
   - **Positions**: a bulleted list, one bullet per issue, each bullet one or two sentences, each cited. Draw from the pamphlet "Statement" and the site's issues pages. Lead each bullet with the issue in bold, e.g. `- **Housing:** X says they will…[^site]`. For sitting judges, include the pamphlet statement's themes but note judicial candidates may not commit on legal issues (cite `sos-offices` if you add that source, or the pamphlet). 3–10 bullets.
   - **Affiliations and endorsements**: party preference as stated on the ballot (cite `kc-sample-ballot`), organizations the candidate belongs to or lists, and endorsements. Endorsements may only be listed if cited to the endorsing organization's own endorsement page (kind `endorsement`) or to the candidate's site/pamphlet, in which case say "self-reported" in the sentence. Also add them to frontmatter `endorsements` (see below). If there are many, list the first 8–10 and say the site lists more.
   - **Record**: for incumbents, a prose summary of the structured `record` in frontmatter: number of bills they prime-sponsored this term with two or three named examples (cite `leg-sponsored` / `congress-sponsored`), and how they voted on the shortlist bills (cite `leg-member` for state legislators, since the votes come from the legislature; for US House cite `congress-member`), naming each bill and vote. Keep it factual: "Voted yea on ESSB 6346, the bill creating the tax on income over $1 million." For non-incumbents: one or two sentences on what the pamphlet lists under "Elected Experience" (or that it lists none), cited to `sos-pamphlet`. For sitting justices: summarize the courts.wa.gov biography (appointment date, prior role), cite `courts-bio`; do not characterize their opinions.
   - **Funding**: prose summary of frontmatter `finance`: total raised and spent with the as-of date, the small-donor share with a one-phrase definition, and the top contributors by name (and employer/occupation if filed), all cited to `finance`. If `finance` is null, write: "No campaign finance filing was found as of <finance_checked>.[^kc-sample-ballot]" For US House candidates the source is the FEC and figures are through the coverage date; mention "according to FEC filings".

## Editing frontmatter

You may change ONLY these frontmatter keys: `sources` (append new entries; never remove or reorder existing ones) and `endorsements`. Everything else, including `status: draft`, stays as is.

Source entry format (YAML, under `sources:`):

```yaml
  - id: site
    title: "Campaign website: About"
    url: https://example.com/about
    publisher: "<Candidate name> campaign"
    accessed: '2026-10-17'
    kind: candidate-site
  - id: news-1
    title: "<article headline>"
    url: https://www.seattletimes.com/...
    publisher: The Seattle Times
    accessed: '2026-10-17'
    kind: news
  - id: endorse-1
    title: "<Org> 2026 endorsements"
    url: https://org.example/endorsements
    publisher: <Org>
    accessed: '2026-10-17'
    kind: endorsement
```

Use short ids: `site`, `site-issues`, `news-1`, `endorse-1`. Endorsement entries in frontmatter:

```yaml
endorsements:
  - org: Washington State Labor Council
    url: https://www.wslc.org/endorsements
    self_reported: true
```

`self_reported: true` when the only evidence is the candidate's own site or pamphlet; `false` only when `url` is the organization's own endorsement page that you fetched and saved.

Edit the markdown file with the `patch` tool or by rewriting it after reading it in full; keep YAML valid (quote strings containing `:` or starting with special characters).

## Validate before you finish

For each file: `cd "/Users/sam/Personal Projects/repos/clear-ballot/pipeline" && uv run validate ../content/candidates/<slug>.md` must print `0 errors`. Fix every error. Warnings about sentence length should be fixed too (split the sentence).

## Final report (your summary back to the parent)

For each slug: validator result, which source files you saved under `sources/candidates/`, the candidate website status (fetched / blocked / none), and anything you could not find. Flag any sentence you are unsure is supported by its source. Be brief.
