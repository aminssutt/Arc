"""Unit tests for VultronRetriever (issue #25) -- fully network-mocked.

The Vultr Vector Store API is faked with ``httpx.MockTransport``: a stateful
in-process double (``FakeVultr``) implements exactly the endpoints the client
touches and records every request, so behaviour is asserted without a single
real HTTP call. The retriever always runs against an injected client, so no
API key is ever needed.

Coverage map (issue #25 acceptance criteria):
1. ``ensure_collection`` reuses the id the API returns (a truncated id != name),
   for both the create path and the reuse-existing path.
2. Ingest idempotency on ``(doc_id, section)``: unchanged -> skip, changed ->
   delete+insert, new -> insert.
3. ``query`` enforces ``top_k`` client-side and joins doc_id/section via the item
   cache -- warm cache (no refresh) and cold cache (lazy refresh).
4. ``query`` returns frozen-contract ``RetrievedRef`` and ``to_citations`` yields
   valid ``Citation`` objects.
5. ``ingest_manifest`` resolves ``path_or_text`` as a file AND as literal text.
"""

from __future__ import annotations

import json
import logging
import re

import httpx
import pytest

from contracts.agent_interface import Citation, RetrievedRef
from agents.common.retriever import CollectionCollisionError, IngestSummary, VultronRetriever

BASE_URL = "https://fake.vultr"


# --------------------------------------------------------------------------- #
# In-process fake of the Vultr Vector Store API
# --------------------------------------------------------------------------- #
class FakeVultr:
    """Stateful double for the ``/v1/vector_store`` API surface.

    Stores collections and items in memory, records ``(method, path)`` for every
    request, and returns responses shaped like the real API (notably: ``GET
    /items`` omits ``content``; ``/search`` returns rank-ordered id+content with
    no score). Search rank order == item insertion order (deterministic).
    """

    def __init__(self) -> None:
        self.collections: dict[str, str] = {}          # name -> collection id
        self.items: dict[str, dict[str, dict]] = {}    # cid -> {item_id: {content, description}}
        self.calls: list[tuple[str, str]] = []         # (method, path) audit log
        self._item_seq = 0

    # -- helpers used by tests -------------------------------------------- #
    @staticmethod
    def derive_cid(name: str) -> str:
        """Mimic 'id derived from name, sanitized + truncated' (id != name)."""
        slug = re.sub(r"[^a-z0-9]", "", name.lower())
        return "vsc" + slug[:11]

    def seed_collection(self, name: str) -> str:
        cid = self.derive_cid(name)
        self.collections[name] = cid
        self.items.setdefault(cid, {})
        return cid

    def item_contents(self) -> list[str]:
        return [it["content"] for items in self.items.values() for it in items.values()]

    def count(self, method: str, *, endswith: str | None = None, contains: str | None = None) -> int:
        n = 0
        for m, p in self.calls:
            if m != method:
                continue
            if endswith is not None and not p.endswith(endswith):
                continue
            if contains is not None and contains not in p:
                continue
            n += 1
        return n

    # -- the MockTransport handler ---------------------------------------- #
    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.method
        path = request.url.path
        self.calls.append((method, path))
        parts = path.strip("/").split("/")  # e.g. ['v1','vector_store', cid, 'items', iid]
        body = json.loads(request.content) if request.content else {}

        # /v1/vector_store  (list / create)
        if parts == ["v1", "vector_store"]:
            if method == "GET":
                cols = [
                    {"id": cid, "name": name, "created": "2026-07-04T00:00:00Z"}
                    for name, cid in self.collections.items()
                ]
                return httpx.Response(200, json={"collections": cols})
            if method == "POST":
                name = body["name"]
                cid = self.collections.get(name) or self.seed_collection(name)
                return httpx.Response(
                    200,
                    json={"collection": {"id": cid, "name": name, "created": "2026-07-04T00:00:00Z"}},
                )

        # /v1/vector_store/{cid}
        if len(parts) == 3 and parts[:2] == ["v1", "vector_store"]:
            cid = parts[2]
            if method == "GET":
                name = next((n for n, c in self.collections.items() if c == cid), None)
                if name is None:
                    return httpx.Response(404, json={"error": "not found"})
                return httpx.Response(200, json={"collection": {"id": cid, "name": name}})
            if method == "DELETE":
                self.items.pop(cid, None)
                self.collections = {n: c for n, c in self.collections.items() if c != cid}
                return httpx.Response(204)

        # /v1/vector_store/{cid}/items  (list / insert)
        if len(parts) == 4 and parts[3] == "items":
            cid = parts[2]
            store = self.items.setdefault(cid, {})
            if method == "GET":
                # NB: real API omits content on the list endpoint.
                items = [
                    {"id": iid, "created": "2026-07-04T00:00:00Z", "description": it["description"]}
                    for iid, it in store.items()
                ]
                return httpx.Response(200, json={"items": items})
            if method == "POST":
                self._item_seq += 1
                iid = f"item-{self._item_seq:04d}"
                store[iid] = {"content": body["content"], "description": body["description"]}
                return httpx.Response(
                    200,
                    json={"item": {"id": iid, "content": body["content"],
                                   "description": body["description"], "created": "2026-07-04T00:00:00Z"}},
                )

        # /v1/vector_store/{cid}/items/{iid}
        if len(parts) == 5 and parts[3] == "items":
            cid, iid = parts[2], parts[4]
            store = self.items.setdefault(cid, {})
            if method == "GET":
                it = store.get(iid)
                if it is None:
                    return httpx.Response(404, json={"error": "not found"})
                return httpx.Response(200, json={"item": {"id": iid, **it, "created": "2026-07-04T00:00:00Z"}})
            if method == "DELETE":
                store.pop(iid, None)
                return httpx.Response(204)

        # /v1/vector_store/{cid}/search
        if len(parts) == 4 and parts[3] == "search":
            cid = parts[2]
            store = self.items.get(cid, {})
            results = [
                {"id": iid, "created": "2026-07-04T00:00:00Z", "content": it["content"]}
                for iid, it in store.items()  # insertion order == rank order
            ]
            return httpx.Response(200, json={"results": results, "usage": {"tokens": 0}})

        return httpx.Response(500, json={"error": f"unhandled {method} {path}"})


def fake_client(fake: FakeVultr) -> httpx.AsyncClient:
    """An AsyncClient wired to a FakeVultr via MockTransport (no real sockets)."""
    return httpx.AsyncClient(transport=httpx.MockTransport(fake.handler), base_url=BASE_URL)


# --------------------------------------------------------------------------- #
# 1. ensure_collection reuses the API-returned id (truncated id != name)
# --------------------------------------------------------------------------- #
class TestEnsureCollection:
    @pytest.mark.asyncio
    async def test_creates_and_returns_derived_id_not_the_name(self) -> None:
        # Arrange -- empty backend, so the collection must be created.
        fake = FakeVultr()
        name = "arc_telecom_corpus"
        async with fake_client(fake) as client:
            r = VultronRetriever(name, client=client)
            # Act
            cid = await r.ensure_collection()
        # Assert -- the id is the truncated one the API returned, never the name.
        assert cid == FakeVultr.derive_cid(name)
        assert cid != name
        assert fake.count("POST", endswith="/vector_store") == 1  # created once

    @pytest.mark.asyncio
    async def test_reuses_existing_collection_id_without_creating(self) -> None:
        # Arrange -- the collection already exists on the backend.
        fake = FakeVultr()
        name = "arc_telecom_corpus"
        seeded = fake.seed_collection(name)
        async with fake_client(fake) as client:
            r = VultronRetriever(name, client=client)
            fake.calls.clear()
            # Act
            cid = await r.ensure_collection()
        # Assert -- matched by name, id reused, no create issued.
        assert cid == seeded
        assert cid != name
        assert fake.count("POST", endswith="/vector_store") == 0

    @pytest.mark.asyncio
    async def test_second_call_is_cached_no_extra_request(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("arc_telecom_corpus", client=client)
            first = await r.ensure_collection()
            fake.calls.clear()
            second = await r.ensure_collection()
        assert first == second
        assert fake.calls == []  # served from the in-process cache


# --------------------------------------------------------------------------- #
# 2. Ingest idempotency on (doc_id, section)
# --------------------------------------------------------------------------- #
class TestIngestIdempotency:
    @pytest.mark.asyncio
    async def test_new_pair_is_inserted(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            item_id = await r.ingest_document("DOC", "Intro", "1.0 Overview", "content v1")
        assert item_id  # got an id back
        assert fake.count("POST", endswith="/items") == 1
        assert fake.count("DELETE", contains="/items/") == 0
        assert fake.item_contents() == ["content v1"]

    @pytest.mark.asyncio
    async def test_unchanged_content_is_a_no_op_skip(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            first = await r.ingest_document("DOC", "Intro", "1.0 Overview", "content v1")
            fake.calls.clear()
            # Act -- re-ingest identical content.
            second = await r.ingest_document("DOC", "Intro", "1.0 Overview", "content v1")
        # Assert -- same id, no write of any kind.
        assert second == first
        assert fake.count("POST", endswith="/items") == 0
        assert fake.count("DELETE", contains="/items/") == 0
        assert fake.item_contents() == ["content v1"]

    @pytest.mark.asyncio
    async def test_changed_content_deletes_then_inserts(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            first = await r.ingest_document("DOC", "Intro", "1.0 Overview", "content v1")
            fake.calls.clear()
            # Act -- same (doc_id, section), different content.
            second = await r.ingest_document("DOC", "Intro", "1.0 Overview", "content v2")
        # Assert -- old item deleted, new item inserted, only the new content remains.
        assert second != first
        assert fake.count("DELETE", contains="/items/") == 1
        assert fake.count("POST", endswith="/items") == 1
        assert fake.item_contents() == ["content v2"]


# --------------------------------------------------------------------------- #
# 3 & 4. query: client-side top_k, cache join, contract types
# --------------------------------------------------------------------------- #
class TestQuery:
    @staticmethod
    async def _ingest_five(r: VultronRetriever) -> None:
        for i in range(5):
            await r.ingest_document("DOC", "Runbook", f"{i}.0 Section {i}", f"chunk body {i}")

    @pytest.mark.asyncio
    async def test_top_k_is_enforced_client_side(self) -> None:
        # Arrange -- 5 chunks ingested; API would return all 5 on search.
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            await self._ingest_five(r)
            # Act
            refs = await r.query("anything", top_k=2)
        # Assert -- truncated to 2, rank order preserved (first two inserted).
        assert len(refs) == 2
        assert [ref.section for ref in refs] == ["0.0 Section 0", "1.0 Section 1"]

    @pytest.mark.asyncio
    async def test_top_k_zero_or_negative_short_circuits(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            await self._ingest_five(r)
            fake.calls.clear()
            assert await r.query("x", top_k=0) == []
            assert await r.query("x", top_k=-3) == []
        # No search request should have gone out.
        assert fake.count("POST", endswith="/search") == 0

    @pytest.mark.asyncio
    async def test_warm_cache_join_uses_cache_without_refetch(self) -> None:
        # Arrange -- same instance ingested, so its item cache is warm.
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            await self._ingest_five(r)
            fake.calls.clear()
            # Act
            refs = await r.query("anything", top_k=3)
        # Assert -- doc_id/section resolved from cache; no GET /items refresh needed.
        assert [ref.doc_id for ref in refs] == ["DOC", "DOC", "DOC"]
        assert refs[0].section == "0.0 Section 0"
        assert fake.count("GET", endswith="/items") == 0

    @pytest.mark.asyncio
    async def test_cold_cache_triggers_lazy_refresh(self) -> None:
        # Arrange -- retriever A populates the backend...
        fake = FakeVultr()
        async with fake_client(fake) as client_a:
            await self._ingest_five(VultronRetriever("c", client=client_a))
        # ...retriever B is a fresh process/instance: its item cache is cold.
        async with fake_client(fake) as client_b:
            r_b = VultronRetriever("c", client=client_b)
            fake.calls.clear()
            # Act
            refs = await r_b.query("anything", top_k=2)
        # Assert -- ids were unknown, so a single GET /items refresh happened,
        # and the join still resolved doc_id/section.
        assert fake.count("GET", endswith="/items") == 1
        assert all(ref.doc_id == "DOC" for ref in refs)
        assert refs[0].section == "0.0 Section 0"

    @pytest.mark.asyncio
    async def test_query_returns_frozen_contract_refs(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            await self._ingest_five(r)
            refs = await r.query("anything", top_k=2)
        assert refs and all(isinstance(ref, RetrievedRef) for ref in refs)
        # Vultr search exposes no numeric score -> contract's optional score is None.
        assert all(ref.score is None for ref in refs)
        assert refs[0].snippet == "chunk body 0"

    @pytest.mark.asyncio
    async def test_to_citations_projects_valid_citations(self) -> None:
        fake = FakeVultr()
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            await self._ingest_five(r)
            refs = await r.query("anything", top_k=2)
        citations = VultronRetriever.to_citations(refs)
        assert len(citations) == len(refs)
        assert all(isinstance(c, Citation) for c in citations)
        assert citations[0].doc_id == refs[0].doc_id
        assert citations[0].section == refs[0].section
        assert citations[0].snippet == refs[0].snippet


# --------------------------------------------------------------------------- #
# 5. ingest_manifest: file mode AND literal-text mode
# --------------------------------------------------------------------------- #
class TestIngestManifest:
    FILE_CONTENT = "Rectifier module A tripped on overtemperature.\nDC plant on reserve."
    LITERAL_TEXT = "Battery reserve depleted after 45 minutes on the -48V DC plant."

    def _write_manifest(self, tmp_path):
        (tmp_path / "rectifier.txt").write_text(self.FILE_CONTENT, encoding="utf-8")
        manifest = [
            {"doc_id": "RUNBOOK-DC", "title": "DC Power", "section": "3.1 Rectifier",
             "path_or_text": "rectifier.txt"},          # resolves relative to manifest dir
            {"doc_id": "RUNBOOK-DC", "title": "DC Power", "section": "3.2 Battery",
             "path_or_text": self.LITERAL_TEXT},          # not a file -> literal text
        ]
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    @pytest.mark.asyncio
    async def test_reads_file_entry_and_literal_entry(self, tmp_path) -> None:
        # Arrange
        fake = FakeVultr()
        manifest_path = self._write_manifest(tmp_path)
        # Act
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            summary = await r.ingest_manifest(manifest_path)
        # Assert -- both new; file entry stored the file's bytes, literal entry the string.
        assert isinstance(summary, IngestSummary)
        assert (summary.created, summary.replaced, summary.skipped) == (2, 0, 0)
        assert set(fake.item_contents()) == {self.FILE_CONTENT, self.LITERAL_TEXT}

    @pytest.mark.asyncio
    async def test_re_ingesting_same_manifest_skips_everything(self, tmp_path) -> None:
        fake = FakeVultr()
        manifest_path = self._write_manifest(tmp_path)
        async with fake_client(fake) as client:
            r = VultronRetriever("c", client=client)
            await r.ingest_manifest(manifest_path)
            # Act -- second identical ingest is a full no-op.
            summary = await r.ingest_manifest(manifest_path)
        assert (summary.created, summary.replaced, summary.skipped) == (0, 0, 2)
        # Still exactly two items, unchanged.
        assert set(fake.item_contents()) == {self.FILE_CONTENT, self.LITERAL_TEXT}


# --------------------------------------------------------------------------- #
# 6. Collection prefix-collision guard (issue #102)
# --------------------------------------------------------------------------- #
class FakeVultrStrict(FakeVultr):
    """Models the REAL API: a create whose derived id already belongs to a
    different-named collection is REJECTED with 422 'Duplicate collection name'
    (rather than silently aliasing, which the base FakeVultr does)."""

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/vector_store":
            self.calls.append(("POST", request.url.path))
            name = json.loads(request.content)["name"]
            cid = self.derive_cid(name)
            owner = next((n for n, c in self.collections.items() if c == cid), None)
            if owner is not None and owner != name:
                return httpx.Response(422, json={
                    "message": "Duplicate collection name found, please provide a unique name"})
            self.collections[name] = cid
            self.items.setdefault(cid, {})
            return httpx.Response(200, json={"collection": {"id": cid, "name": name}})
        return super().handler(request)


# Two distinct names that share their first 14 chars -> same truncated id.
NAME_A = "arc_remediation_smoke"
NAME_B = "arc_remediation_probe"


class TestCollectionCollisionGuard:
    def test_shared_prefix_is_the_root_cause(self) -> None:
        # Different names, identical derived id -> the collision the guard fixes.
        assert NAME_A[:14] == NAME_B[:14]
        assert FakeVultr.derive_cid(NAME_A) == FakeVultr.derive_cid(NAME_B)

    @pytest.mark.asyncio
    async def test_suffix_mode_disambiguates_and_warns(self, caplog) -> None:
        # Arrange -- collection A already exists on the backend.
        fake = FakeVultr()
        cid_a = fake.seed_collection(NAME_A)
        async with fake_client(fake) as client:
            r_b = VultronRetriever(NAME_B, client=client, on_collision="suffix")
            with caplog.at_level(logging.WARNING, logger="agents.common.retriever"):
                cid_b = await r_b.ensure_collection()
        # Assert -- B got a DISTINCT id, its name was disambiguated, warning logged.
        assert cid_b != cid_a
        assert r_b.collection_name != NAME_B
        assert r_b.collection_name.startswith(NAME_B[:7])
        assert "collide" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_suffix_mode_against_real_api_duplicate_422(self, caplog) -> None:
        # The real API rejects the colliding create with 422; the guard still
        # disambiguates to a distinct collection.
        fake = FakeVultrStrict()
        cid_a = fake.seed_collection(NAME_A)
        async with fake_client(fake) as client:
            r_b = VultronRetriever(NAME_B, client=client, on_collision="suffix")
            with caplog.at_level(logging.WARNING, logger="agents.common.retriever"):
                cid_b = await r_b.ensure_collection()
        assert cid_b != cid_a
        assert r_b.collection_name != NAME_B
        assert "collide" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_reuse_mode_returns_the_colliding_id(self, caplog) -> None:
        fake = FakeVultr()
        cid_a = fake.seed_collection(NAME_A)
        async with fake_client(fake) as client:
            r_b = VultronRetriever(NAME_B, client=client, on_collision="reuse")
            with caplog.at_level(logging.WARNING, logger="agents.common.retriever"):
                cid_b = await r_b.ensure_collection()
        # Deliberate share (e.g. arcdemo corpus): B reuses A's collection id.
        assert cid_b == cid_a
        assert "collide" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_error_mode_raises(self) -> None:
        fake = FakeVultr()
        fake.seed_collection(NAME_A)
        async with fake_client(fake) as client:
            r_b = VultronRetriever(NAME_B, client=client, on_collision="error")
            with pytest.raises(CollectionCollisionError):
                await r_b.ensure_collection()

    @pytest.mark.asyncio
    async def test_no_collision_creates_normally_without_warning(self, caplog) -> None:
        # Compat: a unique name is unaffected by the guard (call-site behaviour).
        fake = FakeVultr()
        fake.seed_collection(NAME_A)
        async with fake_client(fake) as client:
            r = VultronRetriever("arc_unique_corpus_x", client=client)  # default suffix
            with caplog.at_level(logging.WARNING, logger="agents.common.retriever"):
                cid = await r.ensure_collection()
        assert cid == FakeVultr.derive_cid("arc_unique_corpus_x")
        assert r.collection_name == "arc_unique_corpus_x"  # name untouched
        assert "collide" not in caplog.text.lower()

    def test_invalid_on_collision_mode_rejected(self) -> None:
        # Validated eagerly in __init__, before any client work.
        with pytest.raises(ValueError):
            VultronRetriever(NAME_A, api_key="x", on_collision="bogus")
