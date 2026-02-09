#!/usr/bin/env python3
"""
SOL Hippocampus --- Knowledge Base Indexer

Pure-Python BM25 inverted index over the ThothStream Knowledge Base.
Zero external dependencies.  Chunks the KB at section boundaries,
tokenises each chunk, and builds a cached index that can be queried
by the retrieval module during gap-enrichment.

The index is persisted to ``data/kb_index.json`` and is automatically
rebuilt whenever the KB file's SHA-256 changes.

Usage (standalone):
    from kb_index import KBIndex
    idx = KBIndex()           # loads or builds
    hits = idx.query("Metatron spiral phi", top_k=5)
    for h in hits:
        print(h.score, h.section, h.text[:120])
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent

_KB_PATH = _SOL_ROOT / "KB" / "ThothStream_Knowledgebase.md"
_INDEX_PATH = _SOL_ROOT / "data" / "kb_index.json"
_CONFIG_PATH = _THIS_DIR / "config.json"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Stop-words (minimal set -- keeps index lean without external data)
# ---------------------------------------------------------------------------
_STOP_WORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "can", "could",
    "this", "that", "these", "those", "i", "we", "you", "he", "she",
    "they", "me", "him", "her", "us", "them", "my", "our", "your",
    "his", "their", "which", "who", "whom", "what", "where", "when",
    "how", "if", "not", "no", "nor", "so", "as", "than", "too", "very",
    "just", "about", "also", "then", "more", "only", "all", "each",
    "every", "any", "some", "such",
}


# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_'\-]{2,}")


def tokenise(text: str) -> list[str]:
    """Lowercase token list, stop-words removed."""
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOP_WORDS and len(t) < 40
    ]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class KBChunk:
    """A passage from the knowledge base."""
    chunk_id: int
    section: str          # top-level source label (e.g. "NumisOMgpt.txt")
    line_start: int       # 1-based line in KB file
    line_end: int
    text: str             # raw passage text (trimmed)
    tokens: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "section": self.section,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "text": self.text[:2000],     # cap stored text for index size
            "token_count": len(self.tokens),
        }


@dataclass
class KBHit:
    """A scored search result."""
    chunk_id: int
    section: str
    line_start: int
    line_end: int
    text: str
    score: float
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "section": self.section,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "score": round(self.score, 4),
            "matched_terms": self.matched_terms,
            "snippet": self.text[:300],
        }


# ---------------------------------------------------------------------------
# BM25 parameters
# ---------------------------------------------------------------------------
_BM25_K1 = 1.2
_BM25_B = 0.75


# ---------------------------------------------------------------------------
# KBIndex
# ---------------------------------------------------------------------------

class KBIndex:
    """
    Pure-Python BM25 inverted index over the ThothStream Knowledge Base.

    Build pipeline:
        1. Read KB markdown
        2. Split at ``## `` headers into sections
        3. Subdivide large sections into ~CHUNK_MAX_LINES chunks
        4. Tokenise each chunk
        5. Build inverted index (term -> [(chunk_id, tf)])
        6. Compute IDF for every term
        7. Persist to JSON

    Query:
        Tokenise query -> BM25 score each chunk -> return top_k
    """

    CHUNK_MAX_LINES = 500    # target lines per chunk
    CHUNK_MIN_LINES = 20     # discard tiny residual chunks

    def __init__(self, *, kb_path: Path | None = None,
                 index_path: Path | None = None,
                 auto_build: bool = True):
        self.kb_path = Path(kb_path or _KB_PATH)
        self.index_path = Path(index_path or _INDEX_PATH)

        # Index data
        self._chunks: list[dict] = []           # chunk metadata (no full tokens)
        self._chunk_texts: list[str] = []        # full text per chunk
        self._chunk_token_counts: list[int] = [] # doc lengths
        self._inv_index: dict[str, list[tuple[int, int]]] = {}  # term -> [(cid, tf)]
        self._idf: dict[str, float] = {}
        self._avg_dl: float = 0.0
        self._kb_sha256: str = ""
        self._n_chunks: int = 0
        self._built = False

        if auto_build:
            if self._load_cached():
                self._built = True
            elif self.kb_path.exists():
                self.build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """
        Build the index from the KB file.

        Returns a summary dict with chunk count, term count, file hash.
        """
        raw_lines = self._read_kb()
        self._kb_sha256 = self._hash_kb()
        chunks = self._chunk_lines(raw_lines)
        self._build_inverted_index(chunks)
        self._save()
        self._built = True
        return {
            "kb_sha256": self._kb_sha256,
            "chunks": self._n_chunks,
            "terms": len(self._inv_index),
            "avg_doc_len": round(self._avg_dl, 1),
            "index_path": str(self.index_path),
        }

    def _read_kb(self) -> list[str]:
        with open(self.kb_path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()

    def _hash_kb(self) -> str:
        h = hashlib.sha256()
        with open(self.kb_path, "rb") as f:
            for block in iter(lambda: f.read(1 << 16), b""):
                h.update(block)
        return h.hexdigest()

    def _chunk_lines(self, lines: list[str]) -> list[KBChunk]:
        """Split the KB into chunks at ## boundaries, subdivide large ones."""
        sections: list[tuple[str, int, int]] = []   # (section_label, start, end)
        current_section = "preamble"
        current_start = 0

        for i, line in enumerate(lines):
            if line.startswith("## "):
                if i > current_start:
                    sections.append((current_section, current_start, i))
                current_section = line.strip().lstrip("# ").strip()
                current_start = i

        # Last section
        if current_start < len(lines):
            sections.append((current_section, current_start, len(lines)))

        # Subdivide large sections
        chunks: list[KBChunk] = []
        cid = 0
        for section_label, sec_start, sec_end in sections:
            sec_len = sec_end - sec_start
            if sec_len <= self.CHUNK_MAX_LINES:
                text = "".join(lines[sec_start:sec_end]).strip()
                if text and sec_len >= self.CHUNK_MIN_LINES:
                    toks = tokenise(text)
                    chunks.append(KBChunk(
                        chunk_id=cid,
                        section=section_label,
                        line_start=sec_start + 1,  # 1-based
                        line_end=sec_end,
                        text=text,
                        tokens=toks,
                    ))
                    cid += 1
            else:
                # Split into sub-chunks
                pos = sec_start
                while pos < sec_end:
                    end = min(pos + self.CHUNK_MAX_LINES, sec_end)
                    # Try to break at a blank line
                    if end < sec_end:
                        for back in range(min(50, end - pos)):
                            if lines[end - back - 1].strip() == "":
                                end = end - back
                                break
                    text = "".join(lines[pos:end]).strip()
                    if text and (end - pos) >= self.CHUNK_MIN_LINES:
                        toks = tokenise(text)
                        chunks.append(KBChunk(
                            chunk_id=cid,
                            section=section_label,
                            line_start=pos + 1,
                            line_end=end,
                            text=text,
                            tokens=toks,
                        ))
                        cid += 1
                    pos = end

        return chunks

    def _build_inverted_index(self, chunks: list[KBChunk]):
        """Build BM25 inverted index from chunks."""
        self._n_chunks = len(chunks)
        self._chunks = [c.to_dict() for c in chunks]
        self._chunk_texts = [c.text for c in chunks]
        self._chunk_token_counts = [len(c.tokens) for c in chunks]

        # Build raw inverted index: term -> [(chunk_id, tf)]
        inv: dict[str, list[tuple[int, int]]] = {}
        for c in chunks:
            tf_map: dict[str, int] = {}
            for t in c.tokens:
                tf_map[t] = tf_map.get(t, 0) + 1
            for term, count in tf_map.items():
                inv.setdefault(term, []).append((c.chunk_id, count))

        self._inv_index = inv

        # IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        N = self._n_chunks
        self._idf = {}
        for term, postings in inv.items():
            df = len(postings)
            self._idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

        # Average document length
        total_tokens = sum(self._chunk_token_counts)
        self._avg_dl = total_tokens / N if N > 0 else 1.0

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, query_text: str, top_k: int = 5) -> list[KBHit]:
        """
        BM25 ranked retrieval.

        Returns up to ``top_k`` KBHit objects sorted by descending score.
        """
        if not self._built:
            return []

        q_tokens = tokenise(query_text)
        if not q_tokens:
            return []

        scores: dict[int, float] = {}
        matched_terms: dict[int, list[str]] = {}

        for qt in q_tokens:
            if qt not in self._inv_index:
                continue
            idf = self._idf.get(qt, 0.0)
            for cid, tf in self._inv_index[qt]:
                dl = self._chunk_token_counts[cid]
                # BM25 score component
                numerator = tf * (_BM25_K1 + 1)
                denominator = tf + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / self._avg_dl)
                score = idf * (numerator / denominator)
                scores[cid] = scores.get(cid, 0.0) + score
                matched_terms.setdefault(cid, [])
                if qt not in matched_terms[cid]:
                    matched_terms[cid].append(qt)

        # Sort and take top_k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        hits = []
        for cid, score in ranked:
            meta = self._chunks[cid]
            hits.append(KBHit(
                chunk_id=cid,
                section=meta["section"],
                line_start=meta["line_start"],
                line_end=meta["line_end"],
                text=self._chunk_texts[cid][:2000],
                score=score,
                matched_terms=matched_terms.get(cid, []),
            ))
        return hits

    def query_by_tags(self, tags: list[str], top_k: int = 5) -> list[KBHit]:
        """
        Query using a list of tags/keywords (joins them into a query).
        """
        return self.query(" ".join(tags), top_k=top_k)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self):
        """Persist index to JSON."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert inv_index for JSON (keys must be strings)
        inv_serial = {term: postings for term, postings in self._inv_index.items()}

        data = {
            "version": 1,
            "kb_sha256": self._kb_sha256,
            "n_chunks": self._n_chunks,
            "avg_dl": self._avg_dl,
            "chunks": self._chunks,
            "chunk_texts": [t[:2000] for t in self._chunk_texts],
            "chunk_token_counts": self._chunk_token_counts,
            "inv_index": inv_serial,
            "idf": self._idf,
        }
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _load_cached(self) -> bool:
        """
        Load cached index if it exists and KB hash matches.
        Returns True on success.
        """
        if not self.index_path.exists() or not self.kb_path.exists():
            return False

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        if data.get("version") != 1:
            return False

        # Check KB hash
        current_hash = self._hash_kb()
        if data.get("kb_sha256") != current_hash:
            return False

        # Restore
        self._kb_sha256 = data["kb_sha256"]
        self._n_chunks = data["n_chunks"]
        self._avg_dl = data["avg_dl"]
        self._chunks = data["chunks"]
        self._chunk_texts = data["chunk_texts"]
        self._chunk_token_counts = data["chunk_token_counts"]
        # Restore inv_index (JSON stores lists of lists, convert to tuples)
        self._inv_index = {
            term: [(p[0], p[1]) for p in postings]
            for term, postings in data["inv_index"].items()
        }
        self._idf = data["idf"]
        return True

    # ------------------------------------------------------------------
    # Info / status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return index statistics."""
        if not self._built:
            return {"built": False, "kb_exists": self.kb_path.exists()}

        # Top terms by document frequency
        top_terms = sorted(
            ((t, len(p)) for t, p in self._inv_index.items()),
            key=lambda x: x[1],
            reverse=True,
        )[:20]

        # Section breakdown
        section_counts: dict[str, int] = {}
        for c in self._chunks:
            sec = c["section"]
            section_counts[sec] = section_counts.get(sec, 0) + 1

        return {
            "built": True,
            "kb_sha256": self._kb_sha256[:16] + "...",
            "chunks": self._n_chunks,
            "unique_terms": len(self._inv_index),
            "avg_doc_length": round(self._avg_dl, 1),
            "index_file_exists": self.index_path.exists(),
            "top_terms": [(t, df) for t, df in top_terms],
            "sections": section_counts,
        }

    def needs_rebuild(self) -> bool:
        """Check if the index needs rebuilding."""
        if not self._built:
            return True
        if not self.kb_path.exists():
            return False
        return self._hash_kb() != self._kb_sha256


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_cached_index: KBIndex | None = None


def get_kb_index(*, force_rebuild: bool = False) -> KBIndex:
    """
    Get or create the singleton KB index.

    Uses a module-level cache so repeated calls in the same process
    re-use the loaded index.
    """
    global _cached_index
    if _cached_index is not None and not force_rebuild:
        return _cached_index
    idx = KBIndex(auto_build=True)
    if force_rebuild and idx._built:
        idx.build()
    _cached_index = idx
    return idx


if __name__ == "__main__":
    # Quick self-test
    idx = KBIndex()
    info = idx.status()
    print(f"KB Index: {info['chunks']} chunks, {info['unique_terms']} terms")
    if idx._built:
        hits = idx.query("Metatron spiral phi sacred geometry", top_k=3)
        for h in hits:
            print(f"  [{h.score:.2f}] {h.section} (L{h.line_start}-{h.line_end})")
            print(f"    {h.text[:120]}...")
