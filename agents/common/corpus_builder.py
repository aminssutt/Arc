"""Corpus chunking adapter — doc-level manifest -> retriever chunk rows (#80 / #54).

The corpus has two manifest shapes and this module is the single adapter between
them (both contracts stay intact):

* **doc-level** `corpus_manifest.json` (loader output, `data/schema.md` §7):
  `{doc_id, type, title, path, vendor, equipment_class, site_id, date, tags}`.
* **chunk-level** rows consumed by `VultronRetriever.ingest_manifest`:
  `{doc_id, title, section, path_or_text}`, citation granularity `(doc_id, section)`.

`build_chunks` explodes each document into per-section chunks: it splits on
markdown headers (`#`…`######`), `Section N — Title` headers, and numbered
headers (`3.2 Title`); with no headers it falls back to paragraph groups of
~1500 chars (`section = "part N"`). Oversized sections are sub-split the same
way (`section = "<heading> (part N)"`). `doc_id` and the document `title` are
preserved on every chunk.

Canonical `doc_id` namespace (S/V/O/I per `validation/DATA_MANIFEST.md`) is the
key across schema, corpus, retriever citations, and the frozen event stream — the
doc-level manifest must already carry canonical ids.

CLI::

    # list the chunks a manifest would produce, no network, no ingest
    python -m agents.common.corpus_builder --manifest <path> --dry-run

    # build chunks and ingest them into a Vultr collection (needs VULTR_INFERENCE_API_KEY)
    source .env
    python -m agents.common.corpus_builder --manifest <path> --collection arc_corpus
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

# Section is the citation pinpoint, so keep chunks readable but bounded.
MAX_SECTION_CHARS = 4000
TARGET_CHUNK_CHARS = 1500

# Heading detectors, tried in order per line.
_MD_HEADING = re.compile(r"^\s*#{1,6}\s+(?P<title>.+?)\s*$")
_SECTION_HEADING = re.compile(r"^\s*Section\s+(?P<num>[\w.\-]+)\s*[—:\-–]\s*(?P<title>.+?)\s*$", re.IGNORECASE)
_NUM_HEADING = re.compile(r"^\s*(?P<num>\d+(?:\.\d+)+)\s+(?P<title>\S.{0,80})$")


def _heading(line: str) -> str | None:
    """Return the normalized section title if ``line`` is a heading, else None."""
    m = _MD_HEADING.match(line)
    if m:
        return m.group("title").strip()
    m = _SECTION_HEADING.match(line)
    if m:
        return f"{m.group('num')} {m.group('title')}".strip()
    m = _NUM_HEADING.match(line)
    if m:
        return f"{m.group('num')} {m.group('title')}".strip()
    return None


def _split_paragraphs(text: str, target: int = TARGET_CHUNK_CHARS) -> list[str]:
    """Group blank-line-separated paragraphs into pieces up to ~``target`` chars."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    buf = ""
    for p in paras:
        if buf and len(buf) + len(p) + 2 > target:
            pieces.append(buf)
            buf = p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf:
        pieces.append(buf)
    return pieces or ([text.strip()] if text.strip() else [])


def chunk_document(text: str, *, doc_id: str, title: str) -> list[dict[str, str]]:
    """Explode one document's text into chunk rows ``{doc_id,title,section,path_or_text}``."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []  # (section_title, body_lines)
    preamble: list[str] = []
    current: tuple[str, list[str]] | None = None

    for line in lines:
        h = _heading(line)
        if h is not None:
            if current is not None:
                sections.append(current)
            current = (h, [])
        elif current is None:
            preamble.append(line)
        else:
            current[1].append(line)
    if current is not None:
        sections.append(current)

    # No headings at all -> paragraph-group fallback.
    if not sections:
        pieces = _split_paragraphs(text)
        if len(pieces) == 1:
            return [{"doc_id": doc_id, "title": title, "section": "part 1",
                     "path_or_text": pieces[0]}]
        return [
            {"doc_id": doc_id, "title": title, "section": f"part {i}", "path_or_text": piece}
            for i, piece in enumerate(pieces, 1)
        ]

    # Fold a short preamble (typically the doc title line) into the first section
    # so no text is dropped; keep a substantial preamble as its own chunk.
    pre_text = "\n".join(preamble).strip()
    rows: list[dict[str, str]] = []
    if pre_text and len(pre_text) >= 200:
        rows.append({"doc_id": doc_id, "title": title, "section": "Introduction",
                     "path_or_text": pre_text})
        pre_text = ""

    for idx, (sec_title, body) in enumerate(sections):
        content = "\n".join(body).strip()
        if idx == 0 and pre_text:
            content = f"{pre_text}\n\n{content}".strip()
        if not content:
            continue
        if len(content) <= MAX_SECTION_CHARS:
            rows.append({"doc_id": doc_id, "title": title, "section": sec_title,
                         "path_or_text": content})
        else:
            for k, piece in enumerate(_split_paragraphs(content), 1):
                rows.append({"doc_id": doc_id, "title": title,
                             "section": f"{sec_title} (part {k})", "path_or_text": piece})
    return rows


def _resolve_doc_text(entry: dict[str, Any], base_dir: Path) -> str:
    """Load a doc-level entry's text: inline ``text``/``path_or_text``, else read ``path``."""
    if entry.get("text"):
        return str(entry["text"])
    if entry.get("path_or_text") and "\n" in str(entry["path_or_text"]):
        return str(entry["path_or_text"])
    raw_path = entry.get("path") or entry.get("path_or_text")
    if not raw_path:
        raise ValueError(f"corpus entry {entry.get('doc_id')!r} has neither 'path' nor inline text")
    candidate = Path(raw_path)
    for p in (candidate, base_dir / candidate, base_dir / "corpus" / candidate):
        if p.is_file():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"corpus entry {entry.get('doc_id')!r}: path {raw_path!r} not found "
        f"(looked relative to {base_dir})"
    )


def build_chunks(manifest_path: str | Path) -> list[dict[str, str]]:
    """Read a doc-level corpus manifest and return chunk-level rows for the retriever."""
    manifest_path = Path(manifest_path)
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError(f"{manifest_path} must be a JSON list of document objects")
    rows: list[dict[str, str]] = []
    for entry in entries:
        doc_id = entry["doc_id"]
        title = entry.get("title", "")
        text = _resolve_doc_text(entry, manifest_path.parent)
        rows.extend(chunk_document(text, doc_id=doc_id, title=title))
    return rows


def _print_dry_run(rows: list[dict[str, str]]) -> None:
    by_doc: dict[str, int] = {}
    for r in rows:
        by_doc[r["doc_id"]] = by_doc.get(r["doc_id"], 0) + 1
    print(f"[dry-run] {len(rows)} chunk(s) from {len(by_doc)} document(s):\n")
    for r in rows:
        preview = " ".join(r["path_or_text"].split())[:80]
        print(f"  {r['doc_id']:<16} | {r['section']:<40} | {len(r['path_or_text']):>5} ch | {preview}…")
    print("\nper-document chunk counts:")
    for doc_id, n in by_doc.items():
        print(f"  {doc_id}: {n}")


async def _ingest(rows: list[dict[str, str]], collection: str) -> None:
    from agents.common.retriever import VultronRetriever

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(rows, fh)
        tmp = fh.name
    try:
        async with VultronRetriever(collection) as retriever:
            summary = await retriever.ingest_manifest(tmp)
        print(f"[ingest] collection={collection!r} created={summary.created} "
              f"replaced={summary.replaced} skipped={summary.skipped} total={summary.total}")
    finally:
        Path(tmp).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agents.common.corpus_builder", description=__doc__)
    parser.add_argument("--manifest", required=True, help="path to a doc-level corpus_manifest.json")
    parser.add_argument("--dry-run", action="store_true", help="list chunks without ingesting (no network)")
    parser.add_argument("--collection", default="arc_corpus", help="target Vultr collection (ingest mode)")
    args = parser.parse_args(argv)

    rows = build_chunks(args.manifest)
    if args.dry_run:
        _print_dry_run(rows)
        return 0
    asyncio.run(_ingest(rows, args.collection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
