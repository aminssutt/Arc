"""Tests for the citation resolver (drill-down Level 1)."""

import json
import pathlib

import pytest

from agents.orchestration.citations import (
    enrich_citations,
    load_sources,
    resolve_citation,
    resolve_report_citations,
)

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY_FILE = ROOT / "data" / "corpus_sources.json"

# Inline registry -> unit tests do not depend on the real data file.
SOURCES = {
    "S1": {"doc_id": "S1", "title": "ETSI EN 300 132-2", "publisher": "ETSI", "family": "PWR",
           "rights": "fetch-at-build", "url": "https://etsi.org/en_30013202.pdf",
           "local_path": "corpus/standards/s1.pdf"},
    "V8": {"doc_id": "V8", "title": "LibreNMS eltek-webpower.yaml", "publisher": "LibreNMS", "family": "PWR",
           "rights": "commit", "url": "https://raw.githubusercontent.com/librenms/eltek-webpower.yaml",
           "local_path": None},
    "S10": {"doc_id": "S10", "title": "M.3100", "publisher": "ITU-T", "family": "ALL",
            "rights": "link-only", "url": None, "local_path": None},
}


# --------------------------------------------------------------------------- #
# resolve_citation
# --------------------------------------------------------------------------- #
def test_resolves_known_doc_to_openable_link():
    r = resolve_citation({"doc_id": "S1", "section": "4.2"}, SOURCES)
    assert r["openable"] is True
    assert r["url"] == "https://etsi.org/en_30013202.pdf"
    assert r["title"] == "ETSI EN 300 132-2"
    assert r["section"] == "4.2"
    assert r["unresolved"] is False


def test_pdf_page_anchor_added():
    r = resolve_citation({"doc_id": "S1", "section": "4.2", "page": 12}, SOURCES)
    assert r["open_url"] == "https://etsi.org/en_30013202.pdf#page=12"
    assert r["page"] == 12


def test_registry_page_hint_fills_page_when_citation_has_none():
    src = {"V2": {"doc_id": "V2", "title": "Eltek", "publisher": "Eltek", "family": "PWR",
                  "rights": "fetch-at-build", "url": "https://x/guide.pdf", "local_path": None,
                  "page_hint": "p24"}}
    r = resolve_citation({"doc_id": "V2", "section": "3.2"}, src)
    assert r["page"] == 24 and r["open_url"].endswith("#page=24")
    # explicit citation page wins over the hint
    r2 = resolve_citation({"doc_id": "V2", "section": "3.2", "page": 5}, src)
    assert r2["page"] == 5


def test_non_pdf_url_gets_no_page_anchor():
    r = resolve_citation({"doc_id": "V8", "section": "OID map", "page": 3}, SOURCES)
    assert r["open_url"] == "https://raw.githubusercontent.com/librenms/eltek-webpower.yaml"


def test_event_shape_claim_is_used_as_anchor():
    # After the orchestrator's _event_citation, section becomes "claim".
    r = resolve_citation({"doc_id": "S1", "claim": "voltage envelope", "title": "ETSI"}, SOURCES)
    assert r["section"] == "voltage envelope"
    assert r["openable"] is True


def test_link_only_doc_without_url_is_not_openable():
    r = resolve_citation({"doc_id": "S10", "section": "x"}, SOURCES)
    assert r["openable"] is False and r["url"] is None
    assert r["unresolved"] is False   # known doc, just no fetchable URL


def test_unknown_doc_is_unresolved_but_still_rendered():
    r = resolve_citation({"doc_id": "NOPE", "section": "x"}, SOURCES)
    assert r["openable"] is False and r["unresolved"] is True
    assert r["title"] == "NOPE"       # still shows something in the report


def test_report_citations_dedup():
    cites = [{"doc_id": "S1", "section": "4.2"}, {"doc_id": "S1", "section": "4.2"},
             {"doc_id": "V8", "section": "OID map"}]
    out = resolve_report_citations(cites, SOURCES)
    assert len(out) == 2


def test_enrich_preserves_claim_and_omits_null_page():
    # Backend path: keep doc_id + claim (event-required), add openable fields,
    # and DROP page when unknown (event schema types page as integer).
    known = enrich_citations([{"doc_id": "S1", "claim": "voltage envelope"}], SOURCES)[0]
    assert known["claim"] == "voltage envelope"      # preserved
    assert known["doc_id"] == "S1" and known["openable"] is True and known["url"]
    assert "page" not in known                       # S1 has no page_hint here -> omitted, not null

    unknown = enrich_citations([{"doc_id": "NOPE", "claim": "x"}], SOURCES)[0]
    assert unknown["claim"] == "x" and unknown["openable"] is False
    assert "page" not in unknown


def test_dedup_keeps_distinct_pages_same_doc_section():
    cites = [{"doc_id": "S1", "section": "4.2", "page": 3},
             {"doc_id": "S1", "section": "4.2", "page": 7}]
    out = resolve_report_citations(cites, SOURCES)
    assert {c["page"] for c in out} == {3, 7}   # page is part of the dedup key


# --------------------------------------------------------------------------- #
# Edge cases (QA M1/L1) — the "never crash" guarantees, pinned
# --------------------------------------------------------------------------- #
def test_empty_citation_degrades_gracefully():
    r = resolve_citation({}, SOURCES)
    assert r["openable"] is False and r["unresolved"] is True
    assert r["open_url"] is None and r["section"] == ""


def test_missing_section_and_claim_anchor_is_empty():
    assert resolve_citation({"doc_id": "S1"}, SOURCES)["section"] == ""


@pytest.mark.parametrize("bad_page", ["12", 12.0, 0, -1, True])
def test_invalid_page_never_produces_anchor(bad_page):
    r = resolve_citation({"doc_id": "S1", "section": "x", "page": bad_page}, SOURCES)
    assert "#page=" not in (r["open_url"] or "")
    assert r["page"] is None


def test_open_url_is_none_when_not_openable():
    assert resolve_citation({"doc_id": "S10", "section": "x"}, SOURCES)["open_url"] is None   # url None
    assert resolve_citation({"doc_id": "NOPE", "section": "x"}, SOURCES)["open_url"] is None   # unknown


def test_malformed_registry_does_not_crash(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "a list"}', encoding="utf-8")
    assert load_sources(bad) == {}
    bad.write_text("{ this is not json", encoding="utf-8")
    assert load_sources(bad) == {}


# --------------------------------------------------------------------------- #
# Alias resolution (corpus doc_id != manifest code-ID)
# --------------------------------------------------------------------------- #
def test_alias_resolves_to_canonical_entry():
    src = {"O4": {"doc_id": "O4", "title": "UFC 3-540-07", "publisher": "WBDG", "family": "PWR",
                  "rights": "commit", "url": "https://wbdg.org/ufc.pdf", "local_path": None,
                  "aliases": ["UFC-3-540-07"]}}
    r = resolve_citation({"doc_id": "UFC-3-540-07", "section": "2", "page": 24}, load_sources_from(src))
    assert r["doc_id"] == "UFC-3-540-07"      # keeps the cited id
    assert r["openable"] and r["title"] == "UFC 3-540-07"
    assert r["open_url"] == "https://wbdg.org/ufc.pdf#page=24"


def load_sources_from(mapping):
    # helper: write a temp registry and load it (exercises the alias indexing)
    import json as _json
    import tempfile
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    _json.dump(list(mapping.values()), f)
    f.close()
    return load_sources(f.name)


# --------------------------------------------------------------------------- #
# Integration: the REAL registry (produced from DATA_MANIFEST)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not REGISTRY_FILE.is_file(), reason="corpus_sources.json not present")
def test_real_registry_is_well_formed():
    sources = load_sources()
    assert sources, "registry loaded empty"
    for doc_id, e in sources.items():
        # doc_id is the entry's own id OR one of its aliases (index holds both).
        assert doc_id == e.get("doc_id") or doc_id in (e.get("aliases") or [])
        assert e.get("title"), f"{doc_id} missing title"
        assert e.get("rights") in {"commit", "fetch-at-build", "link-only"}, f"{doc_id} bad rights"


@pytest.mark.skipif(not REGISTRY_FILE.is_file(), reason="corpus_sources.json not present")
def test_demo_citations_resolve_to_openable_sources():
    sources = load_sources()
    # The energy demo run cites the Eltek/rectifier + DC-plant sources.
    for doc_id in ("V2", "V4", "S1"):
        if doc_id in sources:
            r = resolve_citation({"doc_id": doc_id, "section": "demo"}, sources)
            assert r["openable"], f"{doc_id} should resolve to an openable URL"
