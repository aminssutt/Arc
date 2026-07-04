# Citation drill-down — resolvable sources for the action report

**Owner:** aminssutt · **Feature:** "every claim resolves" made clickable.

When the action report is generated (end of the validation flow), each cited
source resolves to the **exact technical document** it came from — so a NOC
engineer can click a citation and open the real manual/standard (at the page,
when known). Sources come from the corpus RAG over the company's telecom
technical documents.

## The three pieces (and who owns them)

| # | Piece | Status | Owner |
|---|---|---|---|
| Registry | `data/corpus_sources.json` — `doc_id → {title, publisher, family, url, local_path, rights, page_hint}` | ✅ this feature | aminssutt |
| Resolver | `agents/orchestration/citations.py` — `resolve_report_citations(citations)` → viewer-ready records | ✅ this feature | aminssutt |
| Viewer wiring | render each citation as a link → open `open_url` (PDF `#page=N`) | ⏳ follow-up | daniwavy (web #50 / iOS) |
| Event enrichment | attach resolved citations to `action_report_ready.data.report.citations` | ⏳ follow-up | simerugby (backend) — schema `data` is open |

## Resolved citation record (the contract the viewer consumes)
```json
{
  "doc_id": "S1",
  "title": "ETSI EN 300 132-2 — -48V DC power interface",
  "publisher": "ETSI", "family": "PWR", "rights": "fetch-at-build",
  "url": "https://www.etsi.org/.../en_30013202v020801p.pdf",
  "open_url": "https://www.etsi.org/.../en_30013202v020801p.pdf#page=12",
  "local_path": "corpus/standards/s1_en300132-2.pdf",
  "section": "4.2 voltage envelope",
  "snippet": "…normal -48V input range −40.5 to −57.0 VDC…",
  "page": 12,
  "openable": true,
  "unresolved": false
}
```
- **`open_url`** is what the click opens (page anchor for PDFs). Falls back to `url`.
- **`openable: false`** → render the source (title + section) but no working link
  (`link-only` docs with no fetchable URL, or an unknown `doc_id`).
- Accepts both citation shapes: agent `{doc_id, section, snippet}` and event
  `{doc_id, title, page, claim}` (claim is used as the anchor).

## Levels
- **L1 (this PR):** resolve to the document + section, openable link, page anchor
  when a page is present. Deterministic, offline, no contract change.
- **L2 (follow-up):** capture the **exact page** per chunk at ingestion (retriever
  + corpus, vgtray) and add `page` to the frozen `Citation`/`RetrievedRef`
  (small contract PR) so every citation carries a real page.
- **L3 (follow-up):** highlight the exact snippet on the page (PDF.js text layer).

## Registry coverage & honest gaps
`data/corpus_sources.json` = **35 sources**, **32 with a real URL** (openable),
**3 `link-only` with no fetchable URL** (`S10` M.3100, `V9` Nokia AirScale, `O5`
Eaton listing) → rendered as sources but not clickable (`openable: false`). Zero
fabricated URLs.

**Aliases:** the ingested corpus can name a doc differently from the manifest
code-ID (e.g. it cites `UFC-3-540-07`, the manifest codes it `O4`). The registry
entry carries an `aliases` list and the loader indexes those too, so a real
citation never reads as unresolved. Current aliases: `O4 ← UFC-3-540-07`,
`O2 ← FIST-3-6`.

## Note on standards vs manuals
Standards (ETSI/ITU/3GPP) are cited by **clause/section** ("§4.2"), not always a
page — for those the `section` is the anchor. Manuals/reports (Vertiv, FCC) use
`page`. The resolver carries both; the viewer prefers `page` when present, else
shows `section`.

## Usage
```python
from agents.orchestration.citations import resolve_report_citations
enriched = resolve_report_citations(report["citations"])   # loads data/corpus_sources.json
```
