"""VultronRetriever — the single retrieval client for Arc (issues #5, #25).

Every retrieving agent (Correlation, Root-Cause, Remediation) grounds its
reasoning through this module. It wraps Vultr Serverless Inference's Vector
Store API and returns exactly the frozen ``RetrievedRef`` / ``Citation`` shapes
from ``contracts.agent_interface`` — never redefined here.

Vultr Vector Store API (discovered live against https://api.vultrinference.com,
2026-07-04; base path ``/v1/vector_store``):

    POST   /v1/vector_store                      {name}            -> {collection:{id,name,created}}
    GET    /v1/vector_store                                        -> {collections:[...]}
    GET    /v1/vector_store/{cid}                                  -> {collection:{...}}
    DELETE /v1/vector_store/{cid}                                  -> 204
    POST   /v1/vector_store/{cid}/items          {content,description} -> {item:{id,content,description,created}}
    GET    /v1/vector_store/{cid}/items                            -> {items:[{id,created,description}]}   (no content)
    GET    /v1/vector_store/{cid}/items/{iid}                      -> {item:{id,content,description,created}}
    DELETE /v1/vector_store/{cid}/items/{iid}                      -> 204
    POST   /v1/vector_store/{cid}/search         {input}           -> {results:[{id,created,content}], usage}

Behaviours that shaped this client (verified, not assumed):

* Collection ``id`` is *derived from the name* (sanitized + truncated to ~14
  chars), so the id returned by create must be reused; we never assume id==name.
* An item carries one free-form metadata string, ``description``. We pack our
  citation metadata into it as compact JSON: ``{"doc_id","section","title",
  "hash"}``. ``hash`` is a content fingerprint used for idempotency.
* ``/search`` returns results **ordered by relevance** but with only ``id`` and
  ``content`` — no ``description`` and no numeric score. So:
    - we resolve doc_id/section by joining search ids against the collection's
      item list (``GET /items`` returns description), cached in-process;
    - ``top_k`` is enforced client-side (the API ignores it);
    - ``RetrievedRef.score`` is left ``None`` (the API exposes no score; per the
      frozen contract score is optional).

Embedding model: the VultronRetriever family (``VultronRetrieverFlash-0.8B`` /
``Core-4.5B`` / ``Prime-8B`` on ``/v1/models``) powers ``/search`` server-side.
The Vector Store API selects/hosts it for the account; a ``model`` field on
collection-create is accepted but not honoured per-collection in this API
surface, so this client does not pin a model at the collection level. Callers
who need a specific tier use the chat/embeddings endpoints (owned by vultr.py).

Idempotency (AC #25): keyed on ``(doc_id, section)`` — the citation granularity.
Re-ingesting an unchanged chunk is a no-op (content ``hash`` matches → skip);
re-ingesting changed content replaces the old item (delete + insert). The Vultr
API assigns random UUIDs and offers no native upsert, so this delete-then-insert
on change is the upsert strategy.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from contracts.agent_interface import Citation, RetrievedRef

__all__ = ["VultronRetriever", "Retriever", "IngestSummary", "CollectionCollisionError"]

DEFAULT_BASE_URL = "https://api.vultrinference.com"
_VECTOR_STORE = "/v1/vector_store"

logger = logging.getLogger(__name__)

# The Vultr vector-store API derives a collection's id from its name, TRUNCATED
# to this many characters. Two names sharing this prefix map to the SAME id.
_ID_PREFIX_LEN = 14
_ON_COLLISION_MODES = ("suffix", "reuse", "error")


class CollectionCollisionError(RuntimeError):
    """Raised when a collection name collides (first 14 chars) with another and
    the caller asked for ``on_collision="error"`` (or a reuse target could not be
    resolved)."""

    def __init__(self, name: str, prior: str | None, detail: str = "") -> None:
        self.name = name
        self.prior = prior
        msg = (
            f"Collection name {name!r} collides on the first {_ID_PREFIX_LEN} "
            f"chars with existing collection {prior!r} (Vultr truncates collection "
            f"ids to {_ID_PREFIX_LEN} chars)."
        )
        super().__init__(f"{msg} {detail}".strip())


def _short_hash(name: str) -> str:
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]


def _disambiguated_name(name: str) -> str:
    """A collision-free variant of ``name`` whose FIRST 14 chars are unique.

    A plain suffix would not help: the id is truncated to 14 chars, so a colliding
    name (which by definition shares those 14 chars) must be disambiguated *within*
    them. We keep a readable base prefix and place a 6-char sha1 of the full name
    right after it: ``<name[:7]>-<hash6>`` (14 chars, deterministic per full name).
    """
    return f"{name[:7]}-{_short_hash(name)}"


class IngestSummary(dict):
    """Result of an ingest run: created / replaced / skipped chunk counts.

    A plain dict subclass so it stays JSON-serializable while giving callers
    attribute access (``summary.created``) for readability.
    """

    @property
    def created(self) -> int:
        return self.get("created", 0)

    @property
    def replaced(self) -> int:
        return self.get("replaced", 0)

    @property
    def skipped(self) -> int:
        return self.get("skipped", 0)

    @property
    def total(self) -> int:
        return self.created + self.replaced + self.skipped


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _pack_metadata(doc_id: str, section: str, title: str, content: str) -> str:
    return json.dumps(
        {"doc_id": doc_id, "section": section, "title": title, "hash": _content_hash(content)},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _unpack_metadata(description: str | None) -> dict[str, str]:
    """Parse an item description back into metadata; tolerant of legacy strings."""
    if not description:
        return {"doc_id": "", "section": "", "title": "", "hash": ""}
    try:
        data = json.loads(description)
        if isinstance(data, dict):
            return {
                "doc_id": str(data.get("doc_id", "")),
                "section": str(data.get("section", "")),
                "title": str(data.get("title", "")),
                "hash": str(data.get("hash", "")),
            }
    except (json.JSONDecodeError, TypeError):
        pass
    # Legacy / non-JSON description: treat the whole string as the section.
    return {"doc_id": "", "section": description, "title": "", "hash": ""}


class VultronRetriever:
    """Async retrieval client over one Vultr vector-store collection.

    Typical use::

        async with VultronRetriever("arc_telecom_corpus") as r:
            await r.ingest_manifest("agents/common/fixtures/manifest.json")
            refs = await r.query("rectifier undervoltage", top_k=3)
            citations = VultronRetriever.to_citations(refs)

    The client is safe to construct without network access; the collection is
    created lazily on first ingest/query (or explicitly via ``ensure_collection``).
    """

    def __init__(
        self,
        collection: str,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
        on_collision: str = "suffix",
    ) -> None:
        if on_collision not in _ON_COLLISION_MODES:
            raise ValueError(
                f"on_collision must be one of {_ON_COLLISION_MODES}, got {on_collision!r}."
            )
        self.collection_name = collection
        self._on_collision = on_collision
        self._base_url = base_url.rstrip("/")
        api_key = api_key or os.environ.get("VULTR_INFERENCE_API_KEY")
        if not api_key and client is None:
            raise ValueError(
                "No Vultr API key: pass api_key= or set VULTR_INFERENCE_API_KEY "
                "(or inject a preconfigured client=)."
            )
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        self._collection_id: str | None = None
        # In-process cache: item id -> parsed metadata, for the search join.
        self._meta_cache: dict[str, dict[str, str]] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    async def __aenter__(self) -> "VultronRetriever":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Collection management (get-or-create)
    # ------------------------------------------------------------------ #
    async def ensure_collection(self, *, on_collision: str | None = None) -> str:
        """Return the collection id, creating the collection if absent.

        Idempotent: an existing collection is matched by exact name (the API
        derives the id from the name, so we read the id it returns rather than
        assume id == name).

        Collision guard (issue #102): the API truncates a collection id to its
        first 14 chars, so two DIFFERENT names sharing that prefix map to the same
        id and would silently read/write the same collection. When creating a new
        name whose derived id already belongs to a different-named collection this
        method logs a loud warning and resolves per ``on_collision`` (constructor
        default, overridable per call):

        - ``"suffix"`` (default): create a disambiguated name whose first 14 chars
          are unique (``<name[:7]>-<hash6>``); this instance then owns it.
        - ``"reuse"``: return the colliding collection's id (intended for a shared
          collection such as the demo corpus).
        - ``"error"``: raise :class:`CollectionCollisionError`.

        **Team convention:** collection names must be unique within their first 14
        characters; ``arcdemo`` is reserved for THE shared demo corpus.
        """
        if self._collection_id is not None:
            return self._collection_id
        mode = on_collision or self._on_collision
        if mode not in _ON_COLLISION_MODES:
            raise ValueError(f"on_collision must be one of {_ON_COLLISION_MODES}, got {mode!r}.")

        name = self.collection_name
        existing = await self._list_collections()          # name -> id
        if name in existing:                               # exact-name reuse
            self._collection_id = existing[name]
            return self._collection_id

        self._collection_id = await self._create_guarded(name, existing, mode)
        return self._collection_id

    async def _list_collections(self) -> dict[str, str]:
        """Return {name: id} for every collection on the account."""
        resp = await self._client.get(_VECTOR_STORE)
        resp.raise_for_status()
        return {c["name"]: c["id"] for c in resp.json().get("collections", [])}

    async def _create_guarded(self, name: str, existing: dict[str, str], mode: str) -> str:
        """Create ``name``, detecting a shared-14-char-prefix collision either way
        the API surfaces it: a silent alias (create returns a pre-existing id) or a
        hard duplicate-name rejection."""
        by_id = {cid: nm for nm, cid in existing.items()}
        resp = await self._client.post(_VECTOR_STORE, json={"name": name})
        if resp.status_code < 400:
            cid = resp.json()["collection"]["id"]
            prior = by_id.get(cid)
            if prior is not None and prior != name:        # silent collision
                return await self._resolve_collision(name, prior, cid, mode)
            return cid
        if self._is_duplicate_name(resp):                  # hard duplicate (real API)
            prior = by_id.get(name[:_ID_PREFIX_LEN])
            return await self._resolve_collision(name, prior, None, mode)
        resp.raise_for_status()
        raise RuntimeError("unreachable")  # pragma: no cover

    @staticmethod
    def _is_duplicate_name(resp: httpx.Response) -> bool:
        if resp.status_code not in (400, 409, 422):
            return False
        try:
            msg = str(resp.json().get("message", ""))
        except (json.JSONDecodeError, ValueError):
            msg = resp.text
        return "duplicate" in msg.lower()

    async def _resolve_collision(
        self, name: str, prior: str | None, colliding_id: str | None, mode: str
    ) -> str:
        logger.warning(
            "Collection name %r collides on the first %d chars with existing "
            "collection %r (Vultr truncates collection ids to %d chars). "
            "Resolving with on_collision=%r.",
            name, _ID_PREFIX_LEN, prior or "<unknown>", _ID_PREFIX_LEN, mode,
        )
        if mode == "error":
            raise CollectionCollisionError(name, prior)
        if mode == "reuse":
            if colliding_id is not None:
                return colliding_id
            if prior is not None:
                cols = await self._list_collections()
                if prior in cols:
                    return cols[prior]
            raise CollectionCollisionError(
                name, prior, "on_collision='reuse' but the colliding id could not be resolved."
            )
        # mode == "suffix": create a disambiguated collection this instance owns.
        disamb = _disambiguated_name(name)
        resp = await self._client.post(_VECTOR_STORE, json={"name": disamb})
        resp.raise_for_status()
        cid = resp.json()["collection"]["id"]
        logger.warning("Disambiguated colliding name %r -> %r (id %r).", name, disamb, cid)
        self.collection_name = disamb
        return cid

    async def delete_collection(self) -> None:
        """Delete the collection (best-effort; used for smoke cleanup)."""
        cid = await self.ensure_collection()
        resp = await self._client.delete(f"{_VECTOR_STORE}/{cid}")
        if resp.status_code not in (204, 404):
            resp.raise_for_status()
        self._collection_id = None
        self._meta_cache.clear()

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #
    async def _existing_index(self, cid: str) -> dict[tuple[str, str], dict[str, str]]:
        """Map (doc_id, section) -> {item_id, hash} for the whole collection.

        Backed by ``GET /items`` (returns id + description, no content). Also
        refreshes the id->metadata cache used by the search join.
        """
        resp = await self._client.get(f"{_VECTOR_STORE}/{cid}/items")
        resp.raise_for_status()
        index: dict[tuple[str, str], dict[str, str]] = {}
        self._meta_cache.clear()
        for item in resp.json().get("items", []):
            meta = _unpack_metadata(item.get("description"))
            self._meta_cache[item["id"]] = meta
            index[(meta["doc_id"], meta["section"])] = {
                "item_id": item["id"],
                "hash": meta["hash"],
            }
        return index

    async def _insert_item(self, cid: str, content: str, description: str) -> str:
        resp = await self._client.post(
            f"{_VECTOR_STORE}/{cid}/items",
            json={"content": content, "description": description},
        )
        resp.raise_for_status()
        item_id = resp.json()["item"]["id"]
        self._meta_cache[item_id] = _unpack_metadata(description)
        return item_id

    async def _delete_item(self, cid: str, item_id: str) -> None:
        resp = await self._client.delete(f"{_VECTOR_STORE}/{cid}/items/{item_id}")
        if resp.status_code not in (204, 404):
            resp.raise_for_status()
        self._meta_cache.pop(item_id, None)

    async def ingest_document(
        self,
        doc_id: str,
        title: str,
        section: str,
        text: str,
        *,
        _index: dict[tuple[str, str], dict[str, str]] | None = None,
    ) -> str:
        """Upsert one chunk (a ``(doc_id, section)`` pair) into the collection.

        Returns the item id. Idempotent on ``(doc_id, section)``:
          * unchanged content (hash match) -> no-op, returns the existing id;
          * changed content -> old item deleted, new one inserted;
          * new pair -> inserted.

        ``_index`` is an internal optimisation so ``ingest_manifest`` fetches the
        existing-item list once instead of per chunk.
        """
        cid = await self.ensure_collection()
        index = _index if _index is not None else await self._existing_index(cid)

        key = (doc_id, section)
        description = _pack_metadata(doc_id, section, title, text)
        new_hash = _content_hash(text)

        existing = index.get(key)
        if existing is not None:
            if existing["hash"] == new_hash:
                return existing["item_id"]  # unchanged -> idempotent no-op
            await self._delete_item(cid, existing["item_id"])

        item_id = await self._insert_item(cid, text, description)
        index[key] = {"item_id": item_id, "hash": new_hash}
        return item_id

    async def ingest_manifest(self, path: str | Path) -> IngestSummary:
        """Ingest a corpus manifest: JSON list of
        ``{doc_id, title, section, path_or_text}``.

        ``path_or_text`` is read as a file if it resolves (absolute, or relative
        to the manifest's own directory); otherwise it is used as literal text.
        This keeps fixtures self-contained and does not depend on ``/data``.

        Returns an :class:`IngestSummary` with created / replaced / skipped counts.
        """
        manifest_path = Path(path)
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError(f"Manifest {manifest_path} must be a JSON list of chunk objects.")

        cid = await self.ensure_collection()
        index = await self._existing_index(cid)
        summary = IngestSummary(created=0, replaced=0, skipped=0)

        for raw in entries:
            doc_id = raw["doc_id"]
            title = raw.get("title", "")
            section = raw.get("section", "")
            text = self._resolve_text(raw["path_or_text"], manifest_path.parent)

            key = (doc_id, section)
            existed = key in index
            before_hash = index.get(key, {}).get("hash")
            await self.ingest_document(doc_id, title, section, text, _index=index)
            after_hash = _content_hash(text)

            if not existed:
                summary["created"] += 1
            elif before_hash == after_hash:
                summary["skipped"] += 1
            else:
                summary["replaced"] += 1

        return summary

    @staticmethod
    def _resolve_text(path_or_text: str, base_dir: Path) -> str:
        """Return file contents if ``path_or_text`` is an existing file, else the
        string itself (literal chunk text)."""
        candidate = Path(path_or_text)
        for p in (candidate, base_dir / candidate):
            if p.is_file():
                return p.read_text(encoding="utf-8")
        return path_or_text

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #
    async def query(self, text: str, top_k: int = 5) -> list[RetrievedRef]:
        """Retrieve the ``top_k`` most relevant chunks for ``text``.

        Returns frozen-contract ``RetrievedRef`` objects. ``top_k`` is enforced
        client-side (the API returns the full relevance-ordered set). doc_id /
        section are joined from the item metadata cache; if a returned id is not
        cached (e.g. a fresh process querying a pre-existing collection) the item
        list is refreshed once and the join retried.
        """
        if top_k <= 0:
            return []
        cid = await self.ensure_collection()

        resp = await self._client.post(
            f"{_VECTOR_STORE}/{cid}/search",
            json={"input": text},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])[:top_k]

        # Cold/stale cache: refresh the id->metadata map once if any id is unknown.
        if any(r["id"] not in self._meta_cache for r in results):
            await self._existing_index(cid)

        refs: list[RetrievedRef] = []
        for r in results:
            meta = self._meta_cache.get(r["id"], _unpack_metadata(None))
            refs.append(
                RetrievedRef(
                    doc_id=meta["doc_id"],
                    section=meta["section"],
                    snippet=r.get("content", ""),
                    score=None,  # Vultr search is rank-ordered; it exposes no numeric score.
                )
            )
        return refs

    # ------------------------------------------------------------------ #
    # Citation helper
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_citations(refs: list[RetrievedRef]) -> list[Citation]:
        """Project retrieved refs onto the frozen ``Citation`` trail shape."""
        return [
            Citation(doc_id=ref.doc_id, section=ref.section, snippet=ref.snippet)
            for ref in refs
        ]


# Alias: the module is imported as ``Retriever`` in some call sites, and as the
# fully-named ``VultronRetriever`` elsewhere. Both point to the same class.
Retriever = VultronRetriever
