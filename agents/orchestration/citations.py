"""Citation resolver -- turn a report's citation into an OPENABLE source link.

Owner: aminssutt. Feature: citation drill-down (Level 1).

The action report carries a citation trail: each entry pinpoints a source by
``doc_id`` + ``section`` (and, when captured, ``page``). This module joins that
against the corpus **source registry** (``data/corpus_sources.json``: doc_id ->
title + publisher + URL + local_path + rights) so the control-room / iOS report
can render every claim as a clickable link that opens the exact document (at the
page anchor when a page is known).

Pure and offline: no LLM, no network. It does not fetch documents; it produces
the metadata a viewer needs. Wiring the enriched citations into the
``action_report_ready`` event (backend) and the click-through viewer (frontend)
are coordinated follow-ups; this is the resolvable-source contract they consume.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

_PAGE_HINT_RE = re.compile(r"\d+")

_DEFAULT_REGISTRY = pathlib.Path(__file__).resolve().parents[2] / "data" / "corpus_sources.json"


def load_sources(path: str | pathlib.Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the corpus source registry as ``doc_id -> entry``.

    Returns an empty map if the registry file is absent (feature degrades to
    "unresolved" citations rather than crashing).
    """
    p = pathlib.Path(path) if path else _DEFAULT_REGISTRY
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for e in data:
        if not isinstance(e, dict) or not e.get("doc_id"):
            continue
        index[e["doc_id"]] = e
        # alternative doc_ids seen in citations (e.g. the ingested corpus names a
        # doc "UFC-3-540-07" while the manifest codes it "O4") resolve to the same
        # entry -- avoids a real citation reading as unresolved.
        for alias in e.get("aliases") or []:
            index.setdefault(alias, e)
    return index


def _page_of(citation: dict[str, Any]) -> int | None:
    page = citation.get("page")
    # `type(...) is int` excludes bool (a subclass of int) -> no "#page=True".
    return page if type(page) is int and page > 0 else None


def _parse_page_hint(hint: Any) -> int | None:
    """Extract the first page number from a registry hint ('p24', 'pp16/20')."""
    if not isinstance(hint, str):
        return None
    m = _PAGE_HINT_RE.search(hint)
    return int(m.group()) if m else None


def _open_url(url: str | None, page: int | None) -> str | None:
    """Add a PDF page anchor so the viewer jumps to the exact page."""
    if not url:
        return None
    if page:
        path = url.split("?", 1)[0].split("#", 1)[0]  # tolerate query/fragment
        if path.lower().endswith(".pdf"):
            return f"{url}#page={page}"
    return url


def resolve_citation(citation: dict[str, Any], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Enrich one citation into a viewer-ready, openable record.

    Accepts either the agent shape (``{doc_id, section, snippet}``) or the event
    shape (``{doc_id, title, page, claim}``). ``openable`` is False when the
    doc_id is unknown or has no URL -- the report still shows the source, just
    without a working link.
    """
    doc_id = citation.get("doc_id", "")
    anchor = citation.get("section") or citation.get("claim") or ""
    snippet = citation.get("snippet")
    page = _page_of(citation)

    src = sources.get(doc_id)
    if src is None:
        return {
            "doc_id": doc_id, "title": citation.get("title") or doc_id,
            "publisher": None, "family": None, "rights": None,
            "url": None, "open_url": None, "local_path": None,
            "section": anchor, "snippet": snippet, "page": page,
            "openable": False, "unresolved": True,
        }

    # Fall back to the registry's page hint when the citation carries no page.
    if page is None:
        page = _parse_page_hint(src.get("page_hint"))

    url = src.get("url")
    return {
        "doc_id": doc_id,
        "title": src.get("title") or citation.get("title") or doc_id,
        "publisher": src.get("publisher"),
        "family": src.get("family"),
        "rights": src.get("rights"),
        "url": url,
        "open_url": _open_url(url, page),
        "local_path": src.get("local_path"),
        "section": anchor,
        "snippet": snippet,
        "page": page,
        "openable": bool(url),
        "unresolved": False,
    }


def enrich_citations(
    citations: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge resolver fields ONTO each citation, preserving its original keys.

    Use this at report-assembly time: the frozen event schema requires each
    citation to keep ``doc_id`` + ``claim``, so we merge (``{**original,
    **resolved}``) rather than replace -- the resolver adds ``title`` / ``url`` /
    ``open_url`` / ``page`` / ``openable`` while ``claim`` survives. Order is
    preserved and nothing is dropped (no dedup; the caller already deduped).
    """
    src = sources if sources is not None else load_sources()
    out: list[dict[str, Any]] = []
    for c in citations:
        merged = {**c, **resolve_citation(c, src)}
        # The event schema types `page` as integer; omit the key when unknown
        # (a null `page` would violate the frozen contract). Viewer treats a
        # missing page as "no page".
        if merged.get("page") is None:
            merged.pop("page", None)
        out.append(merged)
    return out


def resolve_report_citations(
    citations: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Enrich a report's whole citation trail; dedups by (doc_id, section, page)."""
    src = sources if sources is not None else load_sources()
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int | None]] = set()
    for c in citations:
        resolved = resolve_citation(c, src)
        key = (resolved["doc_id"], resolved["section"], resolved["page"])
        if key in seen:
            continue
        seen.add(key)
        out.append(resolved)
    return out
