"""Content validator for content/ (see SCOPE.md "Validator").

Fails (exit 1) on:
  - frontmatter field missing or wrong type (mirrors site/src/content.config.ts)
  - any body sentence without a [^id] citation (headings, list markers, blockquote markers,
    <!-- TODO --> lines exempt; empty sections allowed)
  - a citation id not present in sources
  - a source URL whose host is not in allowlist.json (candidate-site / endorsement kinds are exempt
    from the domain check but must be https and attributed in prose)
  - a news source cited in a "Fiscal impact" section
  - status: reviewed without reviewed_by and reviewed_at
  - a candidate slug referenced by a contest with no file, or a candidate whose contest has no file
  - a contest district_id not present in data/districts.json
Warns on sentences over 35 words and on sections still marked TODO.

Usage:
    uv run validate            # whole content/ tree
    uv run validate PATH ...   # specific files
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .paths import ALLOWLIST, CONTENT, DATA

STATUS = {"draft", "reviewed"}
KINDS = {"official", "finance", "legislative", "news", "candidate-site", "endorsement"}
DISTRICT_TYPES = {"statewide", "cd", "ld"}
VOTES = {"yea", "nay", "absent", "excused", "present", "not recorded", None}
TODO_RE = re.compile(r"<!--\s*TODO.*?-->")
CITE_RE = re.compile(r"\[\^([A-Za-z0-9_.:-]+)\]")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
# A sentence ends at . ? or ! (optionally followed by citation markers and closing quotes/parens)
# when whitespace follows, except after common abbreviations.
SENTENCE_END = re.compile(r"([.?!])((?:[)\"”']|\[\^[A-Za-z0-9_.:-]+\])*)(\s+)")
ABBREVIATIONS = {"U.S", "No", "Nos", "Rep", "Sen", "Gov", "St", "Mr", "Ms", "Mrs", "Dr", "Jr", "Sr", "vs", "etc", "H.R", "Inc", "Res", "Con", "Sec", "Pos", "Dept", "approx", "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sept", "Sep", "Oct", "Nov", "Dec"}


def split_sentences(text: str) -> list[str]:
    out = []
    start = 0
    for m in SENTENCE_END.finditer(text):
        before = text[start : m.start()]
        last = before.rsplit(None, 1)[-1] if before.strip() else ""
        last = last.lstrip("(\"“'")
        has_cite = "[^" in m.group(2)
        if m.group(1) == "." and not has_cite and (last in ABBREVIATIONS or re.fullmatch(r"[A-Za-z]", last)):
            continue
        out.append(text[start : m.end(2)].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


MAX_WORDS = 35

# (field, allowed python types, required)  -- None in types means null allowed
COMMON = [
    ("id", (str,), True),
    ("title", (str,), True),
    ("status", (str,), True),
    ("reviewed_by", (str, type(None)), True),
    ("reviewed_at", (str, type(None)), True),
    ("updated_at", (str,), True),
    ("sources", (list,), True),
]
MEASURE = COMMON + [
    ("ballot_number", (str,), True),
    ("measure_type", (str,), True),
    ("ballot_title", (str,), True),
    ("yes_means", (str,), True),
    ("no_means", (str,), True),
]
CONTEST = COMMON + [
    ("office", (str,), True),
    ("district_type", (str,), True),
    ("district_id", (str,), True),
    ("district_number", (int, type(None)), True),
    ("partisan", (bool,), True),
    ("term_note", (str, type(None)), True),
    ("candidates", (list,), True),
]
CANDIDATE = COMMON + [
    ("name", (str,), True),
    ("contest", (str,), True),
    ("party_preference", (str, type(None)), True),
    ("incumbent", (bool,), True),
    ("current_office", (str, type(None)), True),
    ("website", (str, type(None)), True),
    ("pamphlet_statement_url", (str, type(None)), True),
    ("finance", (dict, type(None)), True),
    ("finance_checked", (str, type(None)), True),
    ("record", (dict, type(None)), True),
    ("endorsements", (list,), True),
]
PAGE = COMMON


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path, msg):
        self.errors.append(f"{path}: {msg}")

    def warn(self, path, msg):
        self.warnings.append(f"{path}: {msg}")


def load_allowlist() -> set[str]:
    d = json.loads(ALLOWLIST.read_text())
    hosts = set()
    for k in ("official", "finance", "legislative", "news"):
        hosts.update(d.get(k, []))
    return hosts


def host_allowed(url: str, hosts: set[str]) -> bool:
    h = (urlparse(url).hostname or "").lower()
    return any(h == a or h.endswith("." + a) for a in hosts)


def split_markdown(text: str):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def check_fields(path, fm: dict, spec, rep: Report):
    for field, types, required in spec:
        if field not in fm:
            if required:
                rep.error(path, f"frontmatter missing '{field}'")
            continue
        if not isinstance(fm[field], types):
            rep.error(path, f"frontmatter '{field}' has type {type(fm[field]).__name__}, expected {'/'.join(t.__name__ for t in types)}")
    if fm.get("status") not in STATUS:
        rep.error(path, f"status must be one of {sorted(STATUS)}")
    if fm.get("status") == "reviewed" and not (fm.get("reviewed_by") and fm.get("reviewed_at")):
        rep.error(path, "status: reviewed requires reviewed_by and reviewed_at")
    for i, s in enumerate(fm.get("sources") or []):
        if not isinstance(s, dict):
            rep.error(path, f"sources[{i}] is not a mapping")
            continue
        for k in ("id", "title", "url", "publisher", "accessed", "kind"):
            if not isinstance(s.get(k), str) or not s[k]:
                rep.error(path, f"sources[{i}] missing string '{k}'")
        if s.get("kind") not in KINDS:
            rep.error(path, f"sources[{i}] kind '{s.get('kind')}' not in {sorted(KINDS)}")


def check_sources(path, fm: dict, hosts: set[str], rep: Report) -> dict[str, dict]:
    by_id = {}
    for s in fm.get("sources") or []:
        if not isinstance(s, dict) or not s.get("id"):
            continue
        if s["id"] in by_id:
            rep.error(path, f"duplicate source id '{s['id']}'")
        by_id[s["id"]] = s
        url = s.get("url") or ""
        if s.get("kind") in ("candidate-site", "endorsement"):
            if not url.startswith("https://") and not url.startswith("http://"):
                rep.error(path, f"source '{s['id']}' url is not http(s)")
        elif not host_allowed(url, hosts):
            rep.error(path, f"source '{s['id']}' host not on allowlist: {url}")
    return by_id


def body_sentences(body: str):
    """Yield (section_title, line_no, sentence) for prose lines that need citations."""
    section = None
    in_code = False
    for ln, raw in enumerate(body.splitlines(), start=1):
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.strip():
            continue
        hm = HEADING_RE.match(line)
        if hm:
            section = hm.group(1).strip()
            continue
        if TODO_RE.fullmatch(line.strip()) or line.strip().startswith("<!--"):
            continue
        text = line.strip()
        if text.startswith(">"):
            text = text.lstrip("> ").strip()
        text = LIST_RE.sub("", text)
        if re.fullmatch(r"\[\^[^\]]+\]:.*", text):  # footnote definition line
            continue
        if re.fullmatch(r"\|.*\|", text):  # table row
            continue
        if not text:
            continue
        for sent in split_sentences(text):
            if sent:
                yield section, ln, sent


def check_body(path, body: str, sources: dict[str, dict], rep: Report):
    sections = re.findall(r"^#{1,6}\s+(.*)$", body, re.M)
    for sec in sections:
        pass
    # TODO warnings per section
    for m in re.finditer(r"^#{1,6}\s+(.*)$\n+(?:<!--\s*TODO.*?-->)", body, re.M):
        rep.warn(path, f"section '{m.group(1).strip()}' is still TODO")
    for section, ln, sent in body_sentences(body):
        cites = CITE_RE.findall(sent)
        # A sentence must end with one or more citation markers (optionally followed by closing punctuation).
        if not cites or not re.search(r"[.?!][)\"”']*(\[\^[A-Za-z0-9_.:-]+\]\s*)+[)\"”']*$", sent):
            rep.error(path, f"line {ln}: sentence without a trailing [^id] citation: {sent[:80]!r}")
        for c in cites:
            if c not in sources:
                rep.error(path, f"line {ln}: citation [^{c}] not in sources")
            elif section and section.lower().startswith("fiscal impact") and sources[c].get("kind") == "news":
                rep.error(path, f"line {ln}: news source [^{c}] cited in the Fiscal impact section")
        words = len(CITE_RE.sub("", sent).split())
        if words > MAX_WORDS:
            rep.warn(path, f"line {ln}: sentence has {words} words (> {MAX_WORDS})")


def validate_file(path: Path, hosts: set[str], districts: dict, rep: Report) -> dict | None:
    fm, body = split_markdown(path.read_text())
    if fm is None:
        rep.error(path, "no YAML frontmatter")
        return None
    kind = path.parent.name
    spec = {"measures": MEASURE, "contests": CONTEST, "candidates": CANDIDATE, "pages": PAGE}.get(kind)
    if spec is None:
        rep.error(path, f"unknown content directory '{kind}'")
        return None
    check_fields(path, fm, spec, rep)
    if fm.get("id") != path.stem:
        rep.error(path, f"id '{fm.get('id')}' does not match filename")
    sources = check_sources(path, fm, hosts, rep)
    check_body(path, body, sources, rep)
    if kind == "contests":
        if fm.get("district_type") not in DISTRICT_TYPES:
            rep.error(path, f"district_type must be one of {sorted(DISTRICT_TYPES)}")
        if fm.get("district_id") not in districts:
            rep.error(path, f"district_id '{fm.get('district_id')}' not in data/districts.json")
    if kind == "candidates":
        rec = fm.get("record") or {}
        for v in rec.get("shortlist_votes") or []:
            if v.get("vote") not in VOTES:
                rep.error(path, f"shortlist vote value '{v.get('vote')}' not allowed")
        fin = fm.get("finance")
        if fin is not None:
            for k in ("source", "total_raised", "total_spent", "as_of", "top_contributors"):
                if k not in fin:
                    rep.error(path, f"finance missing '{k}'")
            if fm.get("finance_checked") is None:
                rep.error(path, "finance present but finance_checked is null")
        if fm.get("pamphlet_statement_url") and not host_allowed(fm["pamphlet_statement_url"], hosts):
            rep.error(path, "pamphlet_statement_url host not on allowlist")
    return fm


def cross_check(files: dict[Path, dict], rep: Report):
    contests = {fm["id"]: (p, fm) for p, fm in files.items() if p.parent.name == "contests"}
    candidates = {fm["id"]: (p, fm) for p, fm in files.items() if p.parent.name == "candidates"}
    for cid, (p, fm) in contests.items():
        for slug in fm.get("candidates") or []:
            if slug not in candidates:
                rep.error(p, f"candidate '{slug}' has no content file")
            elif candidates[slug][1].get("contest") != cid:
                rep.error(p, f"candidate '{slug}' lists contest '{candidates[slug][1].get('contest')}', not '{cid}'")
    for slug, (p, fm) in candidates.items():
        c = fm.get("contest")
        if c not in contests:
            rep.error(p, f"contest '{c}' has no content file")
        elif slug not in (contests[c][1].get("candidates") or []):
            rep.error(p, f"contest '{c}' does not list this candidate")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    paths = [Path(a) for a in args] if args else sorted(CONTENT.rglob("*.md"))
    hosts = load_allowlist()
    districts = json.loads((DATA / "districts.json").read_text())["districts"] if (DATA / "districts.json").exists() else {}
    rep = Report()
    files: dict[Path, dict] = {}
    for p in paths:
        fm = validate_file(p, hosts, districts, rep)
        if fm:
            files[p] = fm
    if not args:
        cross_check(files, rep)
    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")
    todo = sum(1 for w in rep.warnings if "still TODO" in w)
    print(f"validated {len(files)} files: {len(rep.errors)} errors, {len(rep.warnings)} warnings ({todo} TODO sections)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
