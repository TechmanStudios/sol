"""sol_compile.py

Compile a Markdown knowledge base into a concept-keyword graph for SOL.

Design goals:
- Pure Python (stdlib only)
- Deterministic output
- Focused on "semantic sculpture" rather than QA

Output JSON schema:
{
  "rawNodes": [{"id": 1, "label": "numisom", "group": "spirit"}, ...],
  "rawEdges": [{"from": 1, "to": 2}, ...],
  "meta": { ... }
}

"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from stopwords import STOPWORDS


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)\s*$")
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9']+")

# Proper-noun phrase extraction is intentionally heuristic.
# We want esoteric/proper nouns (e.g., "Temple Doors", "New Earth Star", "Numis'OM")
# to appear as concept nodes more often than generic nouns (e.g., "world", "life").
_PROPER_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+")

# Terms that are "too generic" for semantic sculpture; we penalize rather than hard-remove.
_GENERIC_TERMS = {
    'world','life','body','energy','form','human','planet','people','time','thing','things',
    'light','way','place','part','parts','work','works','year','years','day','days',
    'man','men','woman','women','child','children',
}

_PROPER_EXCLUDE = {
    # common heading / boilerplate / sentence-start artifacts
    'introduction','about','contents','section','chapter','figure','table','note','notes',
    'please','example','examples','volume','issue','page','pages',
}

# Single-word esoteric names to preserve even if they look "generic" by frequency.
_ESOTERIC_SINGLETON_WHITELIST = {
    'thoth','metatron','christ','christos','isis','osiris','horus','anubis','ra','set',
    'merkabah','merkhaba','shamballah','numis\'om','numis\'om',"numis'om",
    'altheria','orion','venus','ark','grail',
}


@dataclass(frozen=True)
class Doc:
    """A unit of co-occurrence (roughly: a section)."""

    source: str
    heading_path: str
    text: str


def iter_docs_from_markdown(md: str, default_source: str = "ThothStream") -> Iterator[Doc]:
    """Split markdown into section docs using headings.

    Strategy:
    - Each heading starts a new doc
    - Doc includes everything until next heading of same-or-higher level

    This keeps co-occurrence local enough to be meaningful.
    """

    lines = md.splitlines()

    current_source = default_source
    heading_stack: list[tuple[int, str]] = []
    buffer: list[str] = []

    def flush() -> Doc | None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        buffer = []
        if not text:
            return None
        path = " > ".join([h for _, h in heading_stack]) if heading_stack else "(root)"
        return Doc(source=current_source, heading_path=path, text=text)

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            doc = flush()
            if doc:
                yield doc

            level = len(m.group(1))
            heading = m.group(2).strip()

            # Heuristic: if the heading looks like a filename from the export, treat it as the doc source.
            if heading.lower().endswith(('.txt', '.pdf', '.rtf', '.md')):
                current_source = heading

            # Maintain a heading stack
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading))
            continue

        buffer.append(line)

    doc = flush()
    if doc:
        yield doc


def iter_docs_from_plaintext(text: str, *, source: str) -> Iterator[Doc]:
    """Split plaintext into co-occurrence docs.

    For raw text files, headings aren't reliable, so we:
    - split into blocks on blank lines
    - merge blocks into ~800-2000 char chunks

    This keeps co-occurrence local without exploding doc count.
    """

    lines = text.splitlines()
    blocks: list[str] = []
    current: list[str] = []

    def flush_block() -> None:
        nonlocal current
        if current:
            blocks.append("\n".join(current).strip())
            current = []

    for line in lines:
        if not line.strip():
            flush_block()
            continue
        current.append(line)
    flush_block()

    buf: list[str] = []
    buf_len = 0
    target_min = 800
    target_max = 2200

    def flush_doc() -> Doc | None:
        nonlocal buf, buf_len
        txt = "\n\n".join([b for b in buf if b]).strip()
        buf = []
        buf_len = 0
        if not txt:
            return None
        return Doc(source=source, heading_path="(root)", text=txt)

    for b in blocks:
        if not b:
            continue
        if buf_len + len(b) > target_max and buf_len >= target_min:
            d = flush_doc()
            if d:
                yield d
        buf.append(b)
        buf_len += len(b)

    d = flush_doc()
    if d:
        yield d


def iter_docs_from_path(input_path: Path) -> Iterator[Doc]:
    """Yield Docs from a single file or all files in a directory."""

    if input_path.is_dir():
        # Deterministic ordering
        for p in sorted(input_path.rglob('*')):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {'.md', '.txt', '.rtf'}:
                continue
            yield from iter_docs_from_path(p)
        return

    suffix = input_path.suffix.lower()
    text = input_path.read_text(encoding='utf-8', errors='replace')
    if suffix == '.md':
        yield from iter_docs_from_markdown(text, default_source=str(input_path.name))
    else:
        yield from iter_docs_from_plaintext(text, source=str(input_path.name))


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = [t for t in _WORD_RE.findall(text) if len(t) >= 3]

    # Normalize a few common variants without being aggressive.
    normed: list[str] = []
    for t in tokens:
        if t.endswith("'s"):
            t = t[:-2]
        if t in STOPWORDS:
            continue
        normed.append(t)
    return normed


def extract_proper_phrases(text: str, *, max_len_words: int = 4) -> list[str]:
    """Extract Title-Case / ALL-CAPS phrases from the original-cased text.

    Output is normalized to lowercase phrases (space-joined), suitable for concept labels.

    Heuristic rules:
    - Words starting with uppercase letter count as "proper".
    - Allow small connector words inside a phrase ("of", "the", "and", ...).
    - Keep phrases length 1..max_len_words, preferring multi-word phrases via TF-IDF boost later.
    """

    connector = {'of', 'the', 'and', 'or', 'to', 'in', 'for', 'on', 'at', 'with', 'from'}

    words = _PROPER_WORD_RE.findall(text)
    phrases: list[list[str]] = []
    current: list[str] = []

    def is_proper_word(w: str) -> bool:
        # Treat ALL-CAPS as proper (e.g., "NES"), and allow internal apostrophes.
        return (len(w) >= 3 and w.isupper()) or (len(w) >= 3 and w[0].isupper())

    for w in words:
        wl = w.lower()
        if is_proper_word(w):
            current.append(wl)
            continue

        # Allow connectors inside a phrase (but not start the phrase)
        if current and wl in connector:
            current.append(wl)
            continue

        if current:
            phrases.append(current)
            current = []

    if current:
        phrases.append(current)

    out: list[str] = []
    for p in phrases:
        # Split long runs into sliding windows so we can capture multi-word names.
        # Example: "Illumined Assembly of the Christos Merkabah" -> windows.
        tokens = [t for t in p if t != "'"]
        if not tokens:
            continue

        # Remove leading/trailing connectors
        while tokens and tokens[0] in connector:
            tokens = tokens[1:]
        while tokens and tokens[-1] in connector:
            tokens = tokens[:-1]
        if not tokens:
            continue

        for L in range(1, max_len_words + 1):
            if len(tokens) < L:
                break
            for i in range(0, len(tokens) - L + 1):
                phrase = " ".join(tokens[i : i + L]).strip()
                if not phrase:
                    continue
                if phrase in STOPWORDS:
                    continue
                if phrase in _PROPER_EXCLUDE:
                    continue
                # Avoid phrases that are only connectors
                if all(t in connector for t in phrase.split()):
                    continue
                out.append(phrase)

    return out


def extract_concepts(docs: Iterable[Doc], *, max_nodes: int, min_df: int, max_df_ratio: float) -> tuple[list[str], dict[str, int], list[set[str]]]:
    """Extract concept keywords.

    Returns:
    - concepts: ordered list of concept strings
    - df: document frequency per concept
    - doc_terms: list of per-doc term sets (restricted later to chosen concepts)

    Approach:
    - Build document frequency (df) over unigrams + bigrams
    - Filter by df range
    - Rank by TF-IDF mass across docs
    """

    per_doc_tokens: list[list[str]] = []
    per_doc_termset: list[set[str]] = []
    per_doc_proper: list[list[str]] = []

    df = Counter()
    proper_vocab = set()

    for doc in docs:
        toks = tokenize(doc.text)
        per_doc_tokens.append(toks)

        # Build candidates: unigrams + bigrams
        cands: list[str] = []
        cands.extend(toks)
        for a, b in zip(toks, toks[1:]):
            if a in STOPWORDS or b in STOPWORDS:
                continue
            # Avoid ultra-common glue bigrams by requiring both tokens to be distinct-ish
            if a == b:
                continue
            cands.append(f"{a} {b}")

        # Proper noun phrases (from original-cased text)
        proper = extract_proper_phrases(doc.text)
        per_doc_proper.append(proper)
        proper_vocab.update(proper)
        cands.extend(proper)

        termset = set(cands)
        per_doc_termset.append(termset)
        df.update(termset)

    doc_count = len(per_doc_termset)
    if doc_count == 0:
        return [], {}, []

    max_df = max(2, int(doc_count * max_df_ratio))

    # Filter by df
    # Allow low-DF proper nouns (df>=1) but still keep very-high DF terms out.
    allowed = {
        t
        for t, d in df.items()
        if (d <= max_df) and (d >= min_df or (t in proper_vocab and d >= 1))
    }

    # Compute TF-IDF mass per term
    tfidf_mass: dict[str, float] = defaultdict(float)
    # Weighting knobs (sculpture-oriented):
    # - emphasize multi-word proper noun phrases
    # - keep single-word esoteric names
    proper_boost = 2.6
    proper_phrase_boost = 3.4
    generic_penalty = 0.22
    unigram_nonproper_penalty = 0.70
    high_df_unigram_penalty = 0.40

    for toks, termset, proper_list in zip(per_doc_tokens, per_doc_termset, per_doc_proper):
        # term frequency from candidates
        # Count unigrams & bigrams in this doc
        tf = Counter()
        tf.update([t for t in toks if t in allowed])
        for a, b in zip(toks, toks[1:]):
            bg = f"{a} {b}"
            if bg in allowed:
                tf[bg] += 1

        # Proper phrases present in this doc (count once each; boost via multiplier below)
        for p in proper_list:
            if p in allowed:
                tf[p] += 1

        for term, f in tf.items():
            d = df[term]
            idf = math.log((doc_count + 1) / (d + 1)) + 1.0

            score = f * idf

            is_phrase = (' ' in term)

            # Prefer phrases (often names) vs generic unigrams
            if is_phrase:
                score *= 1.35
            else:
                # Reduce generic single-word dominance unless it is a proper noun / whitelisted
                if term not in proper_vocab and term not in _ESOTERIC_SINGLETON_WHITELIST:
                    score *= unigram_nonproper_penalty

            # Penalize known generic terms
            if term in _GENERIC_TERMS and term not in _ESOTERIC_SINGLETON_WHITELIST:
                score *= generic_penalty

            # Penalize very-high DF unigrams (too "background English")
            if (not is_phrase) and term not in _ESOTERIC_SINGLETON_WHITELIST and d > int(doc_count * 0.16):
                score *= high_df_unigram_penalty

            # Boost proper nouns (detected from original casing)
            if term in proper_vocab:
                score *= (proper_phrase_boost if is_phrase else proper_boost)

            # Always boost whitelisted esoteric singletons a bit
            if (not is_phrase) and term in _ESOTERIC_SINGLETON_WHITELIST:
                score *= 1.8

            tfidf_mass[term] += score

    concepts = [t for t, _ in sorted(tfidf_mass.items(), key=lambda kv: kv[1], reverse=True)[:max_nodes]]
    concept_set = set(concepts)

    restricted_doc_terms: list[set[str]] = [s.intersection(concept_set) for s in per_doc_termset]

    return concepts, dict(df), restricted_doc_terms


def classify_group(term: str) -> str:
    """Map a concept keyword to a coarse group for coloring/mode field."""

    t = term.lower()

    spirit_markers = {
        'thoth','metatron','merkabah','merkhaba','ascension','portal','stargate','temple','archetype',
        'soul','spirit','christ','christos','shamballah','akashic','etheric','new earth','vibration',
        'numisom','numis\'om','venus','guardian','radiant','illumined',
    }
    tech_markers = {
        'python','code','coding','algorithm','hardware','software','network','graph','matrix','data','model',
        'tensor','system','signal','compute','machine','neural','embedding','llm','api',
    }

    # Exact / substring hits
    for m in spirit_markers:
        if m in t:
            return 'spirit'
    for m in tech_markers:
        if m in t:
            return 'tech'

    return 'bridge'


def build_edges(doc_terms: list[set[str]], concepts: list[str], *, topk_edges: int, min_cooc: int) -> list[tuple[str, str, float]]:
    """Build edges via document-level co-occurrence.

    Edge weight uses a PMI-like score over docs:
      pmi = log( (c_ij * N) / (c_i * c_j) )

    Then we keep top-k neighbors per node.
    """

    N = len(doc_terms)
    if N == 0:
        return []

    # counts
    c_i = Counter()
    c_ij = Counter()

    for termset in doc_terms:
        terms = sorted(termset)
        c_i.update(terms)
        for i in range(len(terms)):
            for j in range(i + 1, len(terms)):
                c_ij[(terms[i], terms[j])] += 1

    # compute scores
    scores_by_node: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (a, b), cij in c_ij.items():
        if cij < min_cooc:
            continue
        ci = c_i[a]
        cj = c_i[b]
        if ci == 0 or cj == 0:
            continue
        pmi = math.log((cij * N) / (ci * cj))
        # Clamp negatives away; we only want positively-associated structure
        if pmi <= 0:
            continue
        scores_by_node[a].append((b, pmi))
        scores_by_node[b].append((a, pmi))

    # keep top-k per node, then dedupe undirected edges
    keep = set()
    for a in concepts:
        neigh = scores_by_node.get(a)
        if not neigh:
            continue
        neigh.sort(key=lambda x: x[1], reverse=True)
        for b, _ in neigh[:topk_edges]:
            lo, hi = (a, b) if a < b else (b, a)
            keep.add((lo, hi))

    # compute final weights for kept edges
    edges: list[tuple[str, str, float]] = []
    for lo, hi in sorted(keep):
        cij = c_ij.get((lo, hi)) or c_ij.get((hi, lo)) or 0
        if cij < min_cooc:
            continue
        ci = c_i[lo]
        cj = c_i[hi]
        pmi = math.log((cij * N) / (ci * cj))
        edges.append((lo, hi, max(0.0, pmi)))

    return edges


def compile_input_to_graph(input_path: Path, *, max_nodes: int, topk_edges: int) -> dict:
    docs = list(iter_docs_from_path(input_path))

    # Tuning knobs (safe defaults)
    concepts, df, doc_terms = extract_concepts(
        docs,
        max_nodes=max_nodes,
        min_df=2,
        max_df_ratio=0.25,
    )

    edges_scored = build_edges(doc_terms, concepts, topk_edges=topk_edges, min_cooc=2)

    # Map concepts to ids
    node_id = {c: i + 1 for i, c in enumerate(concepts)}

    rawNodes = [{"id": node_id[c], "label": c, "group": classify_group(c)} for c in concepts]

    rawEdges = [{"from": node_id[a], "to": node_id[b]} for (a, b, _w) in edges_scored]

    return {
        "rawNodes": rawNodes,
        "rawEdges": rawEdges,
        "meta": {
            "input": str(input_path).replace('\\\\', '/'),
            "docCount": len(docs),
            "maxNodes": max_nodes,
            "topKEdges": topk_edges,
            "nodeCount": len(rawNodes),
            "edgeCount": len(rawEdges),
            "notes": "Edges are undirected co-occurrence links scored by positive PMI over heading sections."
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compile markdown knowledge base into a SOL concept graph (JSON).")
    ap.add_argument("--input", required=True, help="Path to input markdown file OR a directory of source files")
    ap.add_argument("--out", required=True, help="Path to output json file")
    ap.add_argument("--max-nodes", type=int, default=120, help="Max concept nodes to keep")
    ap.add_argument("--topk-edges", type=int, default=6, help="Top-k neighbors per node")

    args = ap.parse_args(argv)

    input_path = Path(args.input)
    out_path = Path(args.out)

    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    graph = compile_input_to_graph(input_path, max_nodes=args.max_nodes, topk_edges=args.topk_edges)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"Wrote: {out_path} (nodes={graph['meta']['nodeCount']}, edges={graph['meta']['edgeCount']}, docs={graph['meta']['docCount']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
