# Arc — The Corpus

Arc's diagnoses are only as trustworthy as their citations. The corpus is a small,
deliberately curated set of **10 real telecom documents** — vendor manuals,
standards, maintenance logs, an SLA, and a spare-price listing — that ground every
load-bearing claim. Its design is what makes the pivot honest: the *same* corpus
supports two opposite conclusions depending on the field ground truth.

## The 10 documents

Defined in `data/corpus_manifest.json`; source files under `data/corpus/`. The
`.pdf` paths are plain-text markdown, served as text (no PDF parsing).

| doc_id | Title | Role in the pipeline |
|---|---|---|
| **V4** | Vertiv NetSure 2100 −48VDC manual | Rectifier alarm signature — grounds the **initial** genuine diagnosis |
| **V6** | ELTEK-DISTRIBUTED-MIB (SNMP trap OIDs) | Trap / alarm-code detection semantics (initial) |
| **S1** | ETSI EN 300 132-2 — −48V DC power interface | The −48V DC voltage envelope (−40.5 … −57.0 V) |
| **FIST-3-6** | FIST 3-6 Storage Battery Maintenance | Battery float/discharge, time-to-LVD urgency |
| **TM-5-693** | TM 5-693 UPS Selection/Maintenance | Symptom/fix matrices — remediation procedure |
| **UFC-3-540-07** | UFC 3-540-07 Generator O&M / electrical safety | DC plant lockout / PPE — cited **safety** steps |
| **O1** | Lumen Service Level Agreement | SLA clock (TTR), credits — cost/urgency |
| **O5** | TelExpress Eaton APR48-3G listing (spare price) | Real spare price (USD 769.04) — Cost/Inventory grounding |
| **S2** | ETSI ES 202 336-2 — DC power monitoring model | Measurement-point / sensing fault — grounds the **pivot** |
| **V2** | Eltek Smartpack2 Master Controller guide | Supervision module / alarm-limit — grounds the **pivot** |

Each document carries an `equipment_class` and `tags` that mark its scenario role:
`confirm-scenario` (V4, FIST-3-6) vs. `pivot-scenario` (S2, V2), `false-undervoltage`
(S2, V2), `alarm-signature` (V4). These are documentation aids — retrieval is by
content similarity, not by tag filter.

## Manifest structure: `path` vs. inline `text`

`data/corpus_manifest.json` is the **doc-level** manifest (loader output,
`data/schema.md` §7). Each entry:

```json
{ "doc_id": "V4", "type": "ran_manual", "title": "Vertiv NetSure 2100 -48VDC manual",
  "path": "corpus/vendor/v4_netsure2100.pdf", "vendor": "Vertiv",
  "equipment_class": "rectifier", "site_id": null, "date": "2019-01-01",
  "tags": ["dc_plant","rectifier","-48v","alarm-signature","confirm-scenario"] }
```

A document's content is resolved one of two ways:

- **`path`** — a file under `data/corpus/` (V4, V6, S1, FIST-3-6, TM-5-693,
  UFC-3-540-07, O1, S2, V2).
- **Inline `text`** — the content lives in the manifest and `path` is `null`. Only
  **O5** uses this: it is a link-only vendor spare listing whose whole payload is
  the APR48-3G price line the Cost/Inventory agent uses. The citations endpoint
  serves it with `source_path:"(inline)"`.

A separate registry, `data/corpus_sources.json`, is the human **rights/sourcing**
table (`doc_id → title, publisher, family, rights, url, local_path, page_hint,
aliases`). It is consumed by the citation resolver (`agents/orchestration/citations.py`,
`enrich_citations`) to turn a citation into an *openable* link (with a `#page=`
anchor when a page hint exists). It also carries `aliases` so the manifest's
`FIST-3-6` / `UFC-3-540-07` resolve to the registry's `O2` / `O4` entries.

## Chunking by section

The doc-level manifest and the retriever's **chunk-level** manifest are two
different shapes; `agents/common/corpus_builder.py` is the single adapter between
them. `build_chunks` explodes each document into per-section chunks
(`{doc_id, title, section, path_or_text}`), and the citation granularity is
`(doc_id, section)`:

- Splits on markdown headers (`#`…`######`), `Section N — Title` headers, and
  numbered headers (`3.2 Title`).
- With no headers, falls back to paragraph groups of ~1500 chars
  (`section = "part N"`).
- A section over 4000 chars is sub-split the same way
  (`section = "<heading> (part N)"`); a short preamble folds into the first
  section so no text is dropped.
- `doc_id` and the document `title` are preserved on every chunk.

The chunk rows are ingested by `VultronRetriever.ingest_manifest` (SHA-256
idempotent, see [VULTR.md](VULTR.md)); at query time each hit returns as a
`RetrievedRef {doc_id, section, snippet, page?}`, and the section is the citation
pinpoint that `GET /api/citations/{doc_id}?claim=…` re-opens.

## The bidirectional grounding — the money shot

The corpus is split so that the **same set of documents grounds two opposite
diagnoses**, and *which one wins is decided by the field measurement, not by a
script*.

**Initial diagnosis — a genuine undervoltage.** The telemetry is coherent: a
rectifier `module_status = fail` together with the busbar `dc_voltage_v` sagging.
Per Root-Cause's discriminant rule, coherent telemetry with **no contradicting
field measurement** points to a **real physical cause**. The diagnosis grounds in:

- **V4** — the Vertiv rectifier-lost alarm signature (the cause),
- **V6** — the Eltek trap semantics (the detection),
- **S1** — the −48V DC voltage envelope (what "undervoltage" means).

The sensing-fault documents (S2, V2) are in the corpus the whole time but are
**not** ranked top here — the evidence for a *misreading* is absent.

**The pivot — a sensing / measurement-path fault.** The technician measures the
busbar and reads a **healthy** float magnitude (e.g. −53.9 V) that *contradicts*
the −45.0 V telemetry undervoltage. Now, and only now, the discriminant condition
is met: the bus is field-verified healthy while the alarm persists, so the fault
is in the measurement/supervision path. The re-diagnosis grounds in:

- **S2** — the ETSI DC power monitoring model (measurement-point failure),
- **V2** — the Eltek Smartpack2 supervision/alarm-limit behavior (the sensing card).

**Why this is the core of the demo.** Nothing about the pivot is hard-coded. The
corpus contains the evidence for *both* conclusions; the field measurement,
interpreted in magnitudes by `Orchestrator._interpret_measurements`
(field-truth-over-telemetry, see [ARCHITECTURE.md](ARCHITECTURE.md)), is what
makes S2/V2 the grounded answer instead of V4/V6. A jury sees the system reach one
cited conclusion, get contradicted by a real measurement, and re-reason to the
*opposite* cited conclusion from the same evidence base — honest,
evidence-conditioned reasoning rather than a canned path. The two seeded scenarios
(`data/scenarios/run_confirm_signals.jsonl`, `run_pivot_signals.jsonl`) drive
exactly these two runs deterministically.

## Doc-id namespace

The canonical `doc_id` namespace is **S/V/O** (per `validation/DATA_MANIFEST.md`):
`S*` standards, `V*` vendor, `O*` operator/other, plus the maintenance-log codes
`FIST-3-6` / `TM-5-693` / `UFC-3-540-07`. This is the primary key the frozen event
fixtures already cite, so the corpus manifest and every retriever fixture re-adopt
it — otherwise a citation would not resolve to a document on click. The full
resolvable set surfaced by the citations endpoint is `V4, S1, V6, FIST-3-6,
TM-5-693, UFC-3-540-07, O1, O5, S2, V2`.
