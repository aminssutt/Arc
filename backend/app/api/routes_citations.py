"""GET /api/citations/{doc_id}?claim=... (DEMO.1) — open a cited source.

Resolves a citation against data/corpus_manifest.json (title/path) and the
data/corpus/ files (created in parallel by the corpus lane — READ ONLY here).
Returns ``{doc_id, title, section, snippet, source_path}``. A doc_id absent from
the manifest, or whose source file is not present yet, returns a clean 404.
"""
import json
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_SNIPPET_RADIUS = 160
_HEADER_RE = re.compile(r"^\s*(#{1,6}\s+.+|section\s+\S.+|\d+(\.\d+)*\s+\S.+)$", re.IGNORECASE)


def _load_manifest(data_dir: Path) -> list[dict]:
    try:
        return json.loads((data_dir / "corpus_manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return []


def _resolve_file(data_dir: Path, rel_path: str | None) -> Path | None:
    """Locate the source file. The corpus lane may materialise text (.txt/.md)
    where the manifest names a .pdf, so probe those siblings too."""
    if not rel_path:
        return None
    base = data_dir / rel_path
    candidates = [base, base.with_suffix(".txt"), base.with_suffix(".md"),
                  (data_dir / "corpus") / Path(rel_path).name]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _extract(text: str, claim: str) -> tuple[str, str]:
    """Best-effort (section, snippet) around the claim; header-aware."""
    lowered = text.lower()
    idx = lowered.find(claim.lower().strip()) if claim.strip() else -1
    if idx < 0 and claim.strip():
        for term in sorted(claim.split(), key=len, reverse=True):
            if len(term) >= 4:
                found = lowered.find(term.lower())
                if found >= 0:
                    idx = found
                    break
    if idx < 0:
        idx = 0
    start, end = max(0, idx - _SNIPPET_RADIUS), min(len(text), idx + _SNIPPET_RADIUS)
    snippet = text[start:end].strip()
    section = ""
    for line in text[:idx].splitlines()[::-1]:
        if _HEADER_RE.match(line):
            section = line.lstrip("#").strip()
            break
    return section, snippet


@router.get("/api/citations/{doc_id}")
async def get_citation(doc_id: str, request: Request):
    claim = request.query_params.get("claim", "")
    data_dir = request.app.state.settings.data_dir
    entry = next((d for d in _load_manifest(data_dir) if d.get("doc_id") == doc_id), None)
    if entry is None:
        return JSONResponse(status_code=404, content={"detail": f"unknown doc_id '{doc_id}'"})
    # Content resolution order: inline manifest `text` (e.g. O5, link-only spare
    # listing) first, then the on-disk source. The .pdf paths are plain markdown
    # text — served as text, no PDF parsing.
    text, source_path = "", entry.get("path")
    inline = entry.get("text")
    if isinstance(inline, str) and inline.strip():
        text = inline
        source_path = entry.get("path") or "(inline)"
    else:
        src = _resolve_file(data_dir, entry.get("path"))
        if src is None:
            return JSONResponse(status_code=404, content={
                "detail": f"source for '{doc_id}' not materialised yet",
                "doc_id": doc_id, "title": entry.get("title", "")})
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            text = ""
        source_path = entry.get("path") or str(src)

    section, snippet = _extract(text, claim) if text.strip() else ("", "")
    return JSONResponse(status_code=200, content={
        "doc_id": doc_id,
        "title": entry.get("title", ""),
        "section": section,
        "snippet": snippet,
        "source_path": source_path,
    })
