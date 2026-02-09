# solCompiler

Pure-Python utilities to compile longform text/markdown into a SOL dashboard graph.

## Goal

- Input: a large markdown knowledge base (e.g. `KB/ThothStream_Knowledgebase.md`)
- Output: a compact semantic *concept keyword* graph you can paste into the SOL dashboard (`rawNodes` / `rawEdges`).

This first version focuses on **semantic sculpture** (how activation flows), not “answering”.

## Quick start

From `g:\docs\TechmanStudios\sol`:

```powershell
python .\solCompiler\sol_compile.py --input .\KB\ThothStream_Knowledgebase.md --out .\solCompiler\output\ts_concepts_graph.json --max-nodes 120 --topk-edges 6
```

The output JSON contains:

- `rawNodes`: `{ id, label, group }`
- `rawEdges`: `{ from, to }`
- `meta`: settings + stats

## Paste into the dashboard

Open `sol_dashboard_refactored.html` and replace the `rawNodes` and `rawEdges` arrays in `App.data` with the generated arrays.

(If you want, I can also add an optional “Load JSON” file input later, but this keeps the dashboard single-file.)
