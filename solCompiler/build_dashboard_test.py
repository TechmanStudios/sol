from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]

    ap = argparse.ArgumentParser(description='Build a SOL dashboard HTML with an inlined concept graph JSON.')
    ap.add_argument('--template', default=str(root / 'sol_dashboard_refactored.html'), help='Path to HTML template')
    ap.add_argument('--graph', default=str(root / 'solCompiler' / 'output' / 'ts_concepts_graph.json'), help='Path to compiled graph JSON')
    ap.add_argument('--out', default=str(root / 'sol_dashboard_test.html'), help='Output HTML path')
    ap.add_argument('--title', default='SOL Dashboard Test | Concept Graph', help='HTML <title>')
    args = ap.parse_args(argv)

    template_path = Path(args.template)
    graph_path = Path(args.graph)
    out_path = Path(args.out)

    html = template_path.read_text(encoding='utf-8')
    graph = json.loads(graph_path.read_text(encoding='utf-8'))

    raw_nodes = graph['rawNodes']
    raw_edges = graph['rawEdges']

    nodes_js = json.dumps(raw_nodes, ensure_ascii=False, indent=12)
    edges_js = json.dumps(raw_edges, ensure_ascii=False, indent=12)

    pat_nodes = re.compile(r"(const\s+rawNodes\s*=\s*)\[(?:.|\n)*?\](\s*;)")
    pat_edges = re.compile(r"(const\s+rawEdges\s*=\s*)\[(?:.|\n)*?\](\s*;)")

    if not pat_nodes.search(html) or not pat_edges.search(html):
        raise SystemExit('Could not find rawNodes/rawEdges blocks in template')

    html = pat_nodes.sub(lambda m: m.group(1) + nodes_js + m.group(2), html, count=1)
    html = pat_edges.sub(lambda m: m.group(1) + edges_js + m.group(2), html, count=1)

    # Disable all-to-all background edges for readability on a dense concept graph.
    html = re.sub(r"const\s+USE_ALL_TO_ALL_EDGES\s*=\s*true\s*;", "const USE_ALL_TO_ALL_EDGES = false;", html)

    # Retitle
    html = re.sub(r"<title>[^<]*</title>", f"<title>{args.title}</title>", html, count=1)

    out_path.write_text(html, encoding='utf-8')
    print(f"Wrote: {out_path}")
    print(f"Graph: nodes={len(raw_nodes)} edges={len(raw_edges)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
