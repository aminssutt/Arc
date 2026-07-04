# VULTRONRETRIEVER BRIEF — what it is and how the corpus must be shaped

> Fetched from the HF model cards (huggingface.co/collections/vultr/vultronretriever),
> Sat morning. Hand to vgtray (retriever owner). This drives how /data gets indexed —
> and it contains a pitch line the judges will love.

## What it actually is

- **Late-interaction (ColBERT-style) VISUAL document retriever.** Input = document PAGE
  IMAGES (RGB) + text queries. No text extraction needed — layout, tables, charts,
  schematics are retrieved AS SEEN.
- Three sizes, all **Apache 2.0**: `VultronRetrieverPrime-Qwen3.5-8B` (top),
  `Core-Qwen3.5-4.5B`, `Flash-Qwen3.5-0.8B`.
- Mechanics: pages encode at up to **1792 visual tokens**, one **320-dim vector per
  token**; query-page scoring = **MaxSim** (`score_multi_vector`). Index ~8× smaller than
  2560-dim single-vector alternatives.
- Pipeline per model card: render pages → `ColQwen3_5Processor`
  (`max_num_visual_tokens=1792`) → store per-token vectors → MaxSim at query time.
  Queries via `processor.process_queries()`; vLLM serving appends 10 `<|endoftext|>`
  augmentation tokens per query.
- Languages: EN, FR, DE, ES, IT, PT. **French documents are in-distribution** — French
  public telecom/energy docs are fair game for the corpus.

## 🎯 The pitch line (verified, cite the model card)

ViDoRe V3: 64.26 mean nDCG@10, **ranks #1 on the Energy and Industrial tasks** (among
others). Arc grounds a telecom **site-energy** fault agent in **industrial** documents —
we are using this retriever exactly where it is strongest, and we can SAY that with the
benchmark citation. Judges include the team that built it.

## Consequences for corpus prep (my lane — already aligned)

1. **Everything becomes page images.** The fetch-at-build script renders every corpus PDF
   to page PNGs (150–200 DPI is plenty for 1792 visual tokens; verify once empirically).
2. **Tables/schematics/alarm matrices are premium pages** — the manifest's `visual_value`
   field scores exactly this. Index the alarm-table and wiring-diagram pages even if the
   prose around them is skipped.
3. **Page-level citations for free:** retrieval returns pages → the report cites
   (doc, page) → the demo's "schematic lights up on citation" beat maps 1:1 to what the
   retriever actually returned. Honest and spectacular.
4. **Index budget:** late-interaction indexes are per-token — keep the corpus curated
   (target 300–800 HIGH-VALUE pages, not 10k pages of prose). The manifest is a
   curation, not a crawl.
5. Ask at the Vultr workshop (their retriever team is on site):
   - Is VultronRetriever served through Serverless Inference directly, or do we self-host
     the Flash/Core model? (Details page says "use these via Vultr Serverless Inference".)
   - Max pages / rate limits per index call; batch embedding endpoint?
   - Is `score_multi_vector` server-side, or do we run scoring locally over stored vectors?

## Model-size call (recommendation)

Index with **Prime-8B** if it's served/affordable ($300×5 credits); fall back to
**Flash-0.8B locally** for iteration speed and re-embed the final corpus with Prime
Saturday evening. Decide after the workshop answers.
