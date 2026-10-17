---
id: methodology
title: Methodology
status: draft
reviewed_by: null
reviewed_at: null
updated_at: '2026-10-17'
sources:
  - id: kc-ballot
    title: King County Elections sample ballot, November 3, 2026 General Election
    url: https://cdn.kingcounty.gov/-/media/king-county/depts/elections/current-election/2026/11/sample-ballot.pdf
    publisher: King County Elections
    accessed: '2026-10-17'
    kind: official
---

## What this site is

Clear Ballot is a nonpartisan, volunteer-made guide to the King County, Washington ballot for the November 3, 2026 general election. It explains the three statewide initiatives, the four U.S. House races, the state legislative races in districts that touch King County, and the five state Supreme Court races. It does not cover county offices, lower courts, or city, school, or special-district measures. It does not endorse anyone or anything.

The contest and candidate list comes from the King County sample ballot.[^kc-ballot] Your address is turned into districts by the [U.S. Census Bureau's geocoder](https://geocoding.geo.census.gov/geocoder/), which returns the Congressional district and state legislative district for a street address. The address is sent only to the Census Bureau through a small relay (needed because browsers cannot call the geocoder directly), is cached briefly at the relay to reduce load on a federal service, and is never stored by this site.

## Content rules

These rules apply to everything written here. A validator program checks rules 2, 4, and 6 on every change before the site can be published.

1. **Plain English.** Any legal or fiscal term is defined on first use. The target is a reading level a 9th grader can follow.
2. **Every sentence cites a source on the allowlist.** There are no uncited sentences in the measure or candidate pages. Citations appear as numbered footnotes; the full list of sources for each page is at the bottom of the page, and every source used on the site is listed on the [Sources](/sources) page.
3. **Arguments for and against** are summarized from the official Voters' Pamphlet arguments and are attributed to the people who wrote them. The site never says which side is right.
4. **Impacts** appear only when a cited fiscal impact statement, legislative staff analysis, court filing, or news report describes them. Reporting is cited as "reported by X"; it is not presented as this site's own finding. News sources are never used in the "Fiscal impact" section of a measure page.
5. **Candidate positions** come from the candidate's own pamphlet statement, website, public votes, sponsored bills, or quoted statements in cited reporting. Characterizations from opponents or advocacy groups are excluded.
6. **Funding figures** come from Public Disclosure Commission (state candidates and committees) and Federal Election Commission (U.S. House candidates) filings and show the "as of" date. Top contributors are listed as filed; employer and occupation are shown when filed. For state filers, "small-donor share" is the share of contribution dollars from gifts of $100 or less plus the lump sums campaigns report as "small contributions" (unitemized gifts of $25 or less). For federal filers it is the share of receipts reported as unitemized individual contributions ($200 or less). The PDC's open data does not publish cash on hand, so it is shown only for federal candidates.
7. **Voting records** follow a fixed shortlist rule, described below, so that the bills shown were chosen before any vote was looked up. Votes are shown as filed, with a link to the roll call. Sponsored bills are listed in full for the current term.
8. **Corrections.** Anyone, including candidates, may report an error using the "Report an error" link at the bottom of every page, which opens a GitHub issue pre-filled with the page address. Corrections are logged publicly on the [Corrections](/corrections) page with the date and the change.
9. **Nonpartisan.** This site is not affiliated with any campaign, committee, or party, and does not endorse.

## Review status

Every page is built from a content file that carries a status of `draft` or `reviewed`. Pages publish as soon as they exist so the information is available before ballots are due. A page that has not yet been checked by a human reviewer shows a prominent "Unreviewed draft" banner at the top. The banner is removed only when a named reviewer records their review in the content file. Candidate pages were generated with their structured data (party preference, finance, record) filled in from the sources above and their narrative sections still to be written; those sections say "Not yet written" until they are.

## Voting record shortlist

For state legislators, the shortlist is: (a) the bills the three 2026 initiatives respond to; (b) the 2025-27 operating budget and the major revenue bills passed with it; and (c) the 2026 supplemental operating budget. The vote shown is the final passage vote in each chamber (the last "final passage" roll call, which is the vote on the version that became law). Bills that never received a floor vote are listed with no vote. "Not recorded" means the chamber held the vote but the legislator is not on the roll call, most often because they were not yet a member.

| Category | Bill | What it is |
|---|---|---|
| (a) | [ESHB 1296 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=1296&Year=2025) | Amended the parental-rights statute created by Initiative 2081; IL26-001 would repeal these amendments |
| (a) | [ESSB 6346 (2026)](https://app.leg.wa.gov/billsummary?BillNumber=6346&Year=2026) | Created the 9.9% tax on income over $1 million; IP26-645 would repeal it |
| (a) | [HB 1699 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=1699&Year=2025) | Girls' interscholastic sports eligibility (same title as IL26-638); died in committee, no floor vote |
| (a) | [SB 5097 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=5097&Year=2025) | Girls' interscholastic athletics; died in committee, no floor vote |
| (a) | [SB 5012 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=5012&Year=2025) | Organization of interscholastic athletics; died in committee, no floor vote |
| (b) | [ESSB 5167 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=5167&Year=2025) | 2025-27 operating budget |
| (b) | [ESSB 5813 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=5813&Year=2025) | Revenue: capital gains and estate tax changes |
| (b) | [ESSB 5814 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=5814&Year=2025) | Revenue: sales tax on certain services and other excise tax changes |
| (b) | [ESHB 2081 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=2081&Year=2025) | Revenue: business and occupation tax surcharges and rates |
| (b) | [ESSB 5794 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=5794&Year=2025) | Revenue: repeal of certain tax preferences |
| (b) | [SHB 2077 (2025)](https://app.leg.wa.gov/billsummary?BillNumber=2077&Year=2025) | Revenue: tax on certain zero-emission vehicle credit sales |
| (c) | [ESSB 5998 (2026)](https://app.leg.wa.gov/billsummary?BillNumber=5998&Year=2026) | 2026 supplemental operating budget |

For U.S. House members, the shortlist is the final-passage House votes on the appropriations and budget-reconciliation measures enacted during the 119th Congress (2025-26). The list is built automatically from the Congress.gov public-law list: a law qualifies if any of its titles contains "Appropriations Act," begins "Making … appropriations," or says "provide for reconciliation." Bills that merely authorize appropriations, such as the defense authorization act, do not qualify. For each, the vote shown is the last passage-type House vote (passage, concurrence in the Senate amendment, or agreeing to the conference report). Any bill a candidate cites by number in their own pamphlet statement is added. As of October 17, 2026 the list is:

| Bill | Public law | House vote shown |
|---|---|---|
| [H.R. 1968](https://www.congress.gov/bill/119/house-bill/1968), Full-Year Continuing Appropriations and Extensions Act, 2025 | 119-4 | March 11, 2025 |
| [H.R. 1](https://www.congress.gov/bill/119/house-bill/1), reconciliation act (H. Con. Res. 14) | 119-21 | July 3, 2025 |
| [H.R. 5371](https://www.congress.gov/bill/119/house-bill/5371), Continuing Appropriations, Agriculture, Legislative Branch, Military Construction and Veterans Affairs, and Extensions Act, 2026 | 119-37 | November 12, 2025 |
| [H.R. 6938](https://www.congress.gov/bill/119/house-bill/6938), Commerce, Justice, Science; Energy and Water; Interior and Environment Appropriations Act, 2026 | 119-74 | January 8, 2026 |
| [H.R. 7148](https://www.congress.gov/bill/119/house-bill/7148), Consolidated Appropriations Act, 2026 | 119-75 | February 3, 2026 |
| [H.R. 7147](https://www.congress.gov/bill/119/house-bill/7147), Homeland Security and Further Additional Continuing Appropriations Act, 2026 | 119-86 | January 22, 2026 |
| [S. 2](https://www.congress.gov/bill/119/senate-bill/2), Secure America Act (reconciliation, S. Con. Res. 33) | 119-98 | June 9, 2026 |
| [H.R. 6500](https://www.congress.gov/bill/119/house-bill/6500), Continuing Appropriations and Extensions Act, 2027 | 119-103 | September 1, 2026 |

## Sources allowlist

Citations may only point to these publishers. Adding a publisher is a deliberate, logged change.

- **Official and primary:** Washington Secretary of State and VoteWA (Voters' Pamphlet, measure documents, candidate filings); King County Elections (sample ballot, local pamphlet); Office of Financial Management (fiscal impact statements); Washington State Legislature (bills, bill reports, roll calls, members); Washington Public Disclosure Commission and data.wa.gov (state campaign finance); Federal Election Commission (federal campaign finance); Congress.gov and the Clerk of the House (federal votes and bills); Washington State Courts (Supreme Court biographies and opinions); a candidate's own campaign website or official member page, cited only for the candidate's own stated positions and biography and attributed as the candidate's claim.
- **Reporting (news sections only; no editorials, op-eds, or endorsements as fact):** The Seattle Times, Cascade PBS, KUOW, Washington State Standard, The Spokesman-Review, Associated Press, PubliCola, The Stranger (news only), Ballotpedia.
- **Endorsements** may be listed as "Endorsed by X" only when cited to the endorsing organization's own published endorsement page or the candidate's site, and must be labeled as self-reported when from the candidate's site.

## How it is built

The site is a static website generated from plain-text content files. Python scripts fetch the source documents listed above into a public repository, parse the sample ballot, and fill in structured data; the explanatory prose is written by hand from those documents. The validator runs on every change. The code, the content files, and the fetched source documents are public at [github.com/sam-thurman/clear-ballot](https://github.com/sam-thurman/clear-ballot).
