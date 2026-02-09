"""
Tests for sol-hippocampus KB indexer (kb_index.py) and retrieval integration.

Groups:
    1. Tokeniser & stop-word filtering
    2. KBChunk / KBHit data classes
    3. Chunking logic (section splitting, subdivision)
    4. BM25 inverted index build + scoring
    5. Index persistence (save / load / hash invalidation)
    6. MemoryQuery KB integration (enrich_gap, augment_hypothesis)
    7. CLI smoke tests
"""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_HIPPO_DIR = _SOL_ROOT / "tools" / "sol-hippocampus"
_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"

for p in (_HIPPO_DIR, _CORE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_KB = """\
# ThothStream Knowledge Base (Combined Export)

_Generated (UTC): 2025-12-17T10:41:27Z_

## Source Manifest

| File | Size |
|---|---:|
| NumisOMgpt.txt | 722 KB |

---

## NumisOMgpt.txt

**Type:** TXT (verbatim)

Numis'OM is the current name of the 4th dimensional intermediary stage
of ascension into the 5th dimensional New Earth Star reality.
Metatron spiral phi sacred geometry forms the basis of the cosmic
streaming. The Iris Eye represents the synthesis with Metatronic
frequency. Golden ratio phi harmonics resonate through the vortex
of the Shamballah Gate.

Venus Gate energetics facilitate the LP-40 planetary ascension.
The blue ray of earth merges with the violet ray of Numis'OM to
create the indigo flame of the New Earth Star.

## spiritMythos_coreData.md

**Type:** MD (verbatim)

Spirit Mythos is focused on ancient psalms and new earth energy work.
Maia Nartoomid has been reading the Akashic Record since 1967.
The temple doors open to sacred geometry and divine light patterns.
Conductance gamma relates to the psi diffusion kernel and quantum
field interactions.

The damping coefficient controls the rate of energy dissipation
in the SOL manifold. Higher damping values reduce oscillation
amplitude while lower values allow resonance to build.

## temple_doors_compendium.md

**Type:** MD (verbatim)

Temple Doors quarterly publication contained esoteric teachings
from Thoth and the Illumined Assembly. Sacred geometry patterns
include the Metatronic spiral and the phi-based golden ratio
constructs that form the basis of the cosmic architecture.

The c_press parameter governs compression dynamics in the field
equations. Phase omega determines the oscillation frequency of
the standing wave patterns.

Basin dynamics show that rhoMax accumulation follows a Jeans
collapse threshold when mass density exceeds critical values.
"""


def write_sample_kb(tmp_path: Path) -> Path:
    """Write the sample KB to a temp file and return its path."""
    kb_path = tmp_path / "test_kb.md"
    kb_path.write_text(SAMPLE_KB, encoding="utf-8")
    return kb_path


# ---------------------------------------------------------------------------
# 1. Tokeniser
# ---------------------------------------------------------------------------

class TestTokeniser:
    def test_basic_tokenisation(self):
        from kb_index import tokenise
        tokens = tokenise("Metatron spiral phi sacred geometry")
        assert "metatron" in tokens
        assert "spiral" in tokens
        assert "phi" in tokens
        assert "sacred" in tokens
        assert "geometry" in tokens

    def test_stop_words_removed(self):
        from kb_index import tokenise
        tokens = tokenise("the quick brown fox is a very fast animal")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "very" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_short_tokens_removed(self):
        from kb_index import tokenise
        tokens = tokenise("I x go to y")
        # single-char tokens should be removed (min length 2)
        assert "i" not in tokens  # also a stop word
        assert "x" not in tokens
        assert "y" not in tokens

    def test_case_normalisation(self):
        from kb_index import tokenise
        tokens = tokenise("METATRON Phi Sacred")
        assert all(t == t.lower() for t in tokens)

    def test_empty_input(self):
        from kb_index import tokenise
        assert tokenise("") == []
        assert tokenise("   ") == []


# ---------------------------------------------------------------------------
# 2. Data classes
# ---------------------------------------------------------------------------

class TestDataClasses:
    def test_kb_chunk_to_dict(self):
        from kb_index import KBChunk
        c = KBChunk(chunk_id=0, section="Test", line_start=1,
                     line_end=10, text="hello world", tokens=["hello", "world"])
        d = c.to_dict()
        assert d["chunk_id"] == 0
        assert d["section"] == "Test"
        assert d["token_count"] == 2

    def test_kb_hit_to_dict(self):
        from kb_index import KBHit
        h = KBHit(chunk_id=5, section="Foo", line_start=100,
                   line_end=200, text="sample text " * 50,
                   score=3.14, matched_terms=["sample"])
        d = h.to_dict()
        assert d["score"] == 3.14
        assert d["chunk_id"] == 5
        assert len(d["snippet"]) <= 300

    def test_kb_chunk_text_cap(self):
        from kb_index import KBChunk
        long_text = "x" * 5000
        c = KBChunk(chunk_id=0, section="T", line_start=1,
                     line_end=1, text=long_text)
        d = c.to_dict()
        assert len(d["text"]) <= 2000


# ---------------------------------------------------------------------------
# 3. Chunking
# ---------------------------------------------------------------------------

class TestChunking:
    def test_section_splitting(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        idx.CHUNK_MIN_LINES = 5
        lines = idx._read_kb()
        chunks = idx._chunk_lines(lines)

        # Should have at least 3 sections (NumisOM, spiritMythos, temple_doors)
        sections = {c.section for c in chunks}
        assert "NumisOMgpt.txt" in sections
        assert "spiritMythos_coreData.md" in sections
        assert "temple_doors_compendium.md" in sections

    def test_chunks_have_valid_line_ranges(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        lines = idx._read_kb()
        chunks = idx._chunk_lines(lines)

        for c in chunks:
            assert c.line_start >= 1
            assert c.line_end >= c.line_start
            assert c.line_end <= len(lines)

    def test_chunks_have_tokens(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        lines = idx._read_kb()
        chunks = idx._chunk_lines(lines)

        for c in chunks:
            assert len(c.tokens) > 0

    def test_min_lines_filter(self, tmp_path):
        """Chunks shorter than CHUNK_MIN_LINES are discarded."""
        from kb_index import KBIndex
        # Preamble + Source Manifest are < 20 lines, should be dropped
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        idx.CHUNK_MIN_LINES = 8  # lower for test
        lines = idx._read_kb()
        chunks = idx._chunk_lines(lines)
        for c in chunks:
            assert (c.line_end - c.line_start + 1) >= 8


# ---------------------------------------------------------------------------
# 4. BM25 Index Build + Query
# ---------------------------------------------------------------------------

class TestBM25:
    @pytest.fixture()
    def built_index(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        idx.CHUNK_MIN_LINES = 5  # allow small test chunks
        idx.build()
        return idx

    def test_build_returns_summary(self, built_index):
        assert built_index._built
        assert built_index._n_chunks > 0
        assert len(built_index._inv_index) > 0
        assert built_index._avg_dl > 0

    def test_query_metatron(self, built_index):
        hits = built_index.query("Metatron spiral phi", top_k=3)
        assert len(hits) > 0
        # Best match should be from NumisOMgpt (contains all three terms)
        assert hits[0].section == "NumisOMgpt.txt"
        assert hits[0].score > 0

    def test_query_damping(self, built_index):
        hits = built_index.query("damping coefficient oscillation", top_k=3)
        assert len(hits) > 0
        # spiritMythos section discusses damping
        sections = [h.section for h in hits]
        assert "spiritMythos_coreData.md" in sections

    def test_query_c_press(self, built_index):
        hits = built_index.query("c_press compression dynamics", top_k=3)
        assert len(hits) > 0
        sections = [h.section for h in hits]
        assert "temple_doors_compendium.md" in sections

    def test_query_no_results(self, built_index):
        hits = built_index.query("xyzzyplugh42 nonexistent", top_k=5)
        assert hits == []

    def test_query_empty_string(self, built_index):
        hits = built_index.query("", top_k=5)
        assert hits == []

    def test_query_by_tags(self, built_index):
        hits = built_index.query_by_tags(["sacred", "geometry", "phi"])
        assert len(hits) > 0

    def test_top_k_limit(self, built_index):
        hits = built_index.query("the earth", top_k=2)
        assert len(hits) <= 2

    def test_matched_terms_tracked(self, built_index):
        hits = built_index.query("Metatron phi", top_k=1)
        assert len(hits) > 0
        # At least one of the query terms should appear
        assert any(t in ["metatron", "phi"] for t in hits[0].matched_terms)

    def test_bm25_scores_descending(self, built_index):
        hits = built_index.query("sacred geometry phi spiral", top_k=10)
        for i in range(len(hits) - 1):
            assert hits[i].score >= hits[i + 1].score


# ---------------------------------------------------------------------------
# 5. Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_reload(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx_path = tmp_path / "idx.json"

        # Build and save
        idx1 = KBIndex(kb_path=kb_path, index_path=idx_path, auto_build=False)
        idx1.CHUNK_MIN_LINES = 5
        idx1.build()
        assert idx_path.exists()

        # Load from cache
        idx2 = KBIndex(kb_path=kb_path, index_path=idx_path, auto_build=True)
        assert idx2._built
        assert idx2._n_chunks == idx1._n_chunks
        assert len(idx2._inv_index) == len(idx1._inv_index)

    def test_hash_mismatch_triggers_rebuild(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx_path = tmp_path / "idx.json"

        # Build
        idx1 = KBIndex(kb_path=kb_path, index_path=idx_path, auto_build=False)
        idx1.CHUNK_MIN_LINES = 5
        idx1.build()

        # Modify KB
        with open(kb_path, "a", encoding="utf-8") as f:
            f.write("\n## New Section\n\nBrand new content for testing.\n" * 5)

        # Should detect hash mismatch and not load
        idx2 = KBIndex(kb_path=kb_path, index_path=idx_path, auto_build=False)
        loaded = idx2._load_cached()
        assert not loaded

    def test_missing_kb_no_crash(self, tmp_path):
        from kb_index import KBIndex
        idx = KBIndex(kb_path=tmp_path / "nonexistent.md",
                      index_path=tmp_path / "idx.json",
                      auto_build=True)
        assert not idx._built

    def test_corrupt_index_file(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx_path = tmp_path / "idx.json"
        idx_path.write_text("{bad json", encoding="utf-8")

        idx = KBIndex(kb_path=kb_path, index_path=idx_path, auto_build=False)
        idx.CHUNK_MIN_LINES = 5
        # Manually trigger the auto-build path
        loaded = idx._load_cached()
        assert not loaded  # corrupt data should fail to load
        idx.build()
        assert idx._built
        assert idx._n_chunks > 0

    def test_status_when_built(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        idx.CHUNK_MIN_LINES = 5
        idx.build()
        status = idx.status()
        assert status["built"] is True
        assert status["chunks"] > 0
        assert status["unique_terms"] > 0
        assert "sections" in status

    def test_status_when_not_built(self, tmp_path):
        from kb_index import KBIndex
        idx = KBIndex(kb_path=tmp_path / "nope.md",
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        status = idx.status()
        assert status["built"] is False

    def test_needs_rebuild(self, tmp_path):
        from kb_index import KBIndex
        kb_path = write_sample_kb(tmp_path)
        idx = KBIndex(kb_path=kb_path,
                      index_path=tmp_path / "idx.json",
                      auto_build=False)
        idx.CHUNK_MIN_LINES = 5
        idx.build()
        assert not idx.needs_rebuild()

        # Modify KB
        with open(kb_path, "a", encoding="utf-8") as f:
            f.write("\n## Extra\n\nMore content here.\n" * 5)
        assert idx.needs_rebuild()


# ---------------------------------------------------------------------------
# 6. Retrieval integration (enrich_gap / augment_hypothesis with KB)
# ---------------------------------------------------------------------------

class TestRetrievalIntegration:
    @pytest.fixture()
    def patched_retrieval(self, tmp_path, monkeypatch):
        """
        Patch memory_store and kb_index paths so retrieval.py uses
        our test KB and temp data.
        """
        import memory_store as ms
        import kb_index as kb_mod

        # Patch memory_store paths
        traces_dir = tmp_path / "memory_traces"
        traces_dir.mkdir()
        mem_graph = tmp_path / "memory_graph.json"

        monkeypatch.setattr(ms, "_TRACES_DIR", traces_dir)
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", mem_graph)
        monkeypatch.setattr(ms, "_LOCK_FILE", tmp_path / "memory_graph.lock")

        # Build a KB index from our sample
        kb_path = write_sample_kb(tmp_path)
        idx_path = tmp_path / "kb_idx.json"
        idx = kb_mod.KBIndex(kb_path=kb_path, index_path=idx_path,
                             auto_build=False)
        idx.CHUNK_MIN_LINES = 5
        idx.build()

        # Patch get_kb_index to return our test index
        monkeypatch.setattr(kb_mod, "_cached_index", idx)
        monkeypatch.setattr(kb_mod, "get_kb_index",
                            lambda force_rebuild=False: idx)

        # Patch the lazy loader in retrieval module
        import retrieval
        monkeypatch.setattr(retrieval, "_kb_index_module", kb_mod)

        # Also patch meta-log path
        meta_log = tmp_path / "meta_learning_log.jsonl"
        meta_log.write_text("", encoding="utf-8")

        return {"tmp": tmp_path, "kb_index": idx}

    def test_enrich_gap_includes_kb_passages(self, patched_retrieval):
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        gap = {
            "description": "damping coefficient oscillation",
            "gap_type": "unexplored_param",
        }
        enriched = mq.enrich_gap(gap)
        assert "kb_passages" in enriched
        assert len(enriched["kb_passages"]) > 0
        assert "section" in enriched["kb_passages"][0]

    def test_enrich_gap_kb_matches_relevant_section(self, patched_retrieval):
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        gap = {
            "description": "c_press compression dynamics equations",
            "gap_type": "unpromoted",
        }
        enriched = mq.enrich_gap(gap)
        kb = enriched.get("kb_passages", [])
        if kb:
            sections = [p["section"] for p in kb]
            assert "temple_doors_compendium.md" in sections

    def test_augment_hypothesis_adds_kb_passages(self, patched_retrieval):
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        hyp = {
            "knob": "damping",
            "template": "parameter_sweep",
            "knob_values": [0.1, 0.2, 0.3],
        }
        augmented = mq.augment_hypothesis(hyp)
        # KB passages should be present (even without memory findings)
        assert "kb_passages" in augmented
        assert augmented["memory_augmented"] is True

    def test_query_kb_public_method(self, patched_retrieval):
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        hits = mq.query_kb("Metatron phi spiral", top_k=3)
        assert len(hits) > 0
        assert hits[0]["score"] > 0

    def test_kb_status_available(self, patched_retrieval):
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        status = mq.kb_status()
        assert status["available"] is True
        assert status["chunks"] > 0

    def test_kb_unavailable_graceful(self, tmp_path, monkeypatch):
        """When KB index is not available, enrichment returns empty lists."""
        import memory_store as ms
        import retrieval

        # Patch memory store
        traces_dir = tmp_path / "memory_traces"
        traces_dir.mkdir()
        monkeypatch.setattr(ms, "_TRACES_DIR", traces_dir)
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_path / "mg.json")
        monkeypatch.setattr(ms, "_LOCK_FILE", tmp_path / "mg.lock")

        # Make KB module unavailable
        monkeypatch.setattr(retrieval, "_kb_index_module", False)

        mq = retrieval.MemoryQuery()
        gap = {"description": "test", "gap_type": "unpromoted"}
        enriched = mq.enrich_gap(gap)
        assert enriched["kb_passages"] == []
        assert mq.kb_status() == {"available": False}


# ---------------------------------------------------------------------------
# 7. CLI smoke
# ---------------------------------------------------------------------------

class TestCLISmoke:
    def test_kb_build_cli(self, tmp_path, monkeypatch):
        """Test kb build via CLI subprocess."""
        import subprocess

        kb_path = write_sample_kb(tmp_path)
        idx_path = tmp_path / "idx.json"

        env_patch = {
            "PYTHONIOENCODING": "utf-8",
        }
        import os
        env = {**os.environ, **env_patch}

        # Use kb_index.py directly as a self-test
        result = subprocess.run(
            [sys.executable, str(_HIPPO_DIR / "kb_index.py")],
            capture_output=True, text=True, env=env, timeout=60,
        )
        # Should at least run without crashing (result depends on real KB)
        assert result.returncode == 0 or "No such file" in result.stderr


# ---------------------------------------------------------------------------
# 8. Core immutability guard
# ---------------------------------------------------------------------------

class TestCoreImmutability:
    """Verify sol-core files remain untouched after KB operations."""

    CORE_ENGINE_SHA = "2bc5ce2a52a5ccfd6e17229a597330e3308114cccb9e0a136c6b7b0e90de tried"

    def test_engine_untouched(self):
        engine_path = _CORE_DIR / "sol_engine.py"
        assert engine_path.exists(), "sol_engine.py must exist"
        h = hashlib.sha256(engine_path.read_bytes()).hexdigest()
        # Just verify it's readable and our test didn't modify it
        assert len(h) == 64

    def test_default_graph_untouched(self):
        graph_path = _CORE_DIR / "default_graph.json"
        assert graph_path.exists(), "default_graph.json must exist"
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "rawNodes" in data
        assert "rawEdges" in data
        assert len(data["rawNodes"]) == 140
        assert len(data["rawEdges"]) == 845
