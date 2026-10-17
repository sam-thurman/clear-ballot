"""Unit tests for the content validator rules."""
import textwrap

from clearballot.validate import Report, body_sentences, check_body, check_fields, check_sources, MEASURE

HOSTS = {"sos.wa.gov", "seattletimes.com"}
SOURCES = {
    "sos": {"id": "sos", "kind": "official", "url": "https://www.sos.wa.gov/x"},
    "news": {"id": "news", "kind": "news", "url": "https://www.seattletimes.com/x"},
}


def errors(body: str, sources=SOURCES) -> list[str]:
    rep = Report()
    check_body("t.md", textwrap.dedent(body), sources, rep)
    return rep.errors


def test_cited_sentences_pass():
    assert errors("## What it does\n\nIt repeals the tax.[^sos] It also defines income.[^sos]\n") == []


def test_uncited_sentence_fails():
    errs = errors("## What it does\n\nIt repeals the tax. It also defines income.[^sos]\n")
    assert len(errs) == 1 and "without a trailing" in errs[0]


def test_unknown_citation_fails():
    errs = errors("## What it does\n\nIt repeals the tax.[^nope]\n")
    assert any("not in sources" in e for e in errs)


def test_news_in_fiscal_impact_fails():
    errs = errors("## Fiscal impact\n\nRevenue falls by $11 billion.[^news]\n")
    assert any("news source" in e for e in errs)
    assert errors("## Arguments for\n\nRevenue falls by $11 billion.[^news]\n") == []


def test_exempt_lines():
    body = "## Section\n\n<!-- TODO: session 2 -->\n\n> Quoted text here.[^sos]\n\n- bullet item.[^sos]\n\n[^sos]: footnote definition line\n"
    assert errors(body) == []
    assert list(body_sentences("## H\n\n<!-- TODO -->\n")) == []


def test_sentence_split_counts():
    sents = [s for _, _, s in body_sentences("## H\n\nOne here.[^a] Two here?[^a] Three![^a]\n")]
    assert len(sents) == 3


def test_reviewed_requires_reviewer():
    rep = Report()
    fm = {"id": "x", "title": "x", "status": "reviewed", "reviewed_by": None, "reviewed_at": None, "updated_at": "2026-10-17", "sources": [],
          "ballot_number": "x", "measure_type": "x", "ballot_title": "x", "yes_means": "x", "no_means": "x"}
    check_fields("t.md", fm, MEASURE, rep)
    assert any("requires reviewed_by" in e for e in rep.errors)


def test_allowlist_host():
    rep = Report()
    fm = {"sources": [
        {"id": "ok", "kind": "official", "url": "https://voter.votewa.gov/x", "title": "t", "publisher": "p", "accessed": "d"},
        {"id": "bad", "kind": "news", "url": "https://example.com/x", "title": "t", "publisher": "p", "accessed": "d"},
        {"id": "site", "kind": "candidate-site", "url": "https://example.com/x", "title": "t", "publisher": "p", "accessed": "d"},
    ]}
    check_sources("t.md", fm, {"votewa.gov"}, rep)
    assert len(rep.errors) == 1 and "'bad'" in rep.errors[0]


def test_abbreviations_do_not_split():
    from clearballot.validate import split_sentences
    assert split_sentences("U.S. Rep. Smith voted no.[^a] The No. 5 seat is open.[^a]") == ["U.S. Rep. Smith voted no.[^a]", "The No. 5 seat is open.[^a]"]
    assert split_sentences("It costs $11.4 billion over five years.[^a]") == ["It costs $11.4 billion over five years.[^a]"]
    assert split_sentences('He said "no."[^a] She agreed.[^a]') == ['He said "no."[^a]', "She agreed.[^a]"]
