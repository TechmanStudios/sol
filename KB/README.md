# KB — Knowledge Base Directory

This directory holds the background knowledge files that the Sol hippocampus
indexes and retrieves from during experiment cycles.

**The KB files are intentionally excluded from the public repository.**
They contain proprietary or personal knowledge that is specific to each
deployment.  When you fork this repo you need to supply your own knowledge
files to give the Sol manifold something to reason over.

---

## Quick start for forkers

1. **Copy or rename `sample_kb.md`** (or place any `.md` file here) with your
   own knowledge content.

2. **Point the config at your file.**  Edit
   `tools/sol-hippocampus/config.json` and set `kb_index.kb_path` to the
   relative path from the repo root, e.g.:

   ```json
   "kb_index": {
       "kb_path": "KB/my_knowledge_base.md",
       ...
   }
   ```

   You can also pass a custom path at runtime:

   ```python
   from kb_index import KBIndex
   idx = KBIndex(kb_path="KB/my_knowledge_base.md")
   ```

3. **Run the indexer** to build `data/kb_index.json`:

   ```bash
   python tools/sol-hippocampus/kb_index.py
   ```

   The index is rebuilt automatically whenever the KB file changes (SHA-256
   check), so you can update your KB freely.

---

## File format

The KB file must be **Markdown** with `##` top-level section headers.
Each `##` section becomes a separate retrieval unit (chunk).  You can include
as many or as few sections as you like — the BM25 indexer handles both small
and large files.

See [`sample_kb.md`](sample_kb.md) for a minimal working example that you can
use to test the pipeline end-to-end.

---

## What happens when the KB is absent?

The Sol hippocampus degrades gracefully:

- `KBIndex` will **not raise an error** if the file is missing; it simply
  marks itself as unbuilt and returns empty results.
- The retrieval layer logs a notice and continues without KB enrichment.
- All tests use synthetic inline content, so the test suite passes with no
  KB file present.

You only need to supply a KB file if you want gap-enrichment and hypothesis
augmentation to draw on background knowledge.
