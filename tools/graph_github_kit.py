"""Generate a visual dependency graph for the Sol .github "kit".

Scans:
- .github/agents (agent YAML front matter handoffs + markdown references)
- .github/instructions
- .github/prompts
- .github/skills

Outputs:
- Mermaid diagram markdown (default: .github/kit_graph.md)
- Graphviz DOT (default: .github/kit_graph.dot)
- Standalone HTML viewer (default: .github/kit_graph.html)

No external dependencies.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Node:
    node_id: str
    label: str
    kind: str  # agent|instruction|prompt|skill|file|unknown|external-agent
    href: str | None = None


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    label: str


_RE_MD_GH_REF = re.compile(
    r"(?P<path>\.?\.?/?\.github/[A-Za-z0-9_./\-]+?\.md)", re.IGNORECASE
)


def _sanitize_id(raw: str) -> str:
    # Mermaid node IDs: keep them simple and stable.
    # Graphviz is looser, so Mermaid is the constraint.
    return re.sub(r"[^A-Za-z0-9_]", "_", raw)


def _rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _split_front_matter(text: str) -> tuple[str | None, str]:
    # Supports standard triple-dash YAML front matter at top of file.
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text

    for i in range(1, min(len(lines), 4000)):
        if lines[i].strip() == "---":
            yaml_text = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            return yaml_text, body

    # If malformed, treat as no front matter.
    return None, text


def _parse_agent_yaml_minimal(yaml_text: str) -> tuple[str | None, list[str]]:
    """Extract agent name and handoff targets from agent YAML.

    We intentionally avoid a YAML dependency; this parser is tailored to the
    structure in .github/agents/*.agent.md.
    """

    agent_name: str | None = None
    handoff_targets: list[str] = []

    lines = yaml_text.splitlines()
    for line in lines:
        m = re.match(r"^name:\s*(.+?)\s*$", line)
        if m:
            agent_name = m.group(1).strip().strip('"')

    # Parse handoffs list entries:
    # handoffs:
    #   - label: X
    #     agent: sol-lab-master
    in_handoffs = False
    for line in lines:
        if re.match(r"^handoffs:\s*$", line):
            in_handoffs = True
            continue
        if in_handoffs and re.match(r"^[A-Za-z0-9_\-]+:\s*", line):
            # Next top-level key ends handoffs.
            in_handoffs = False
        if not in_handoffs:
            continue

        m = re.match(r"^\s*agent:\s*(.+?)\s*$", line)
        if m:
            target = m.group(1).strip().strip('"')
            if target:
                handoff_targets.append(target)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for t in handoff_targets:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    return agent_name, deduped


def _extract_github_md_refs(text: str) -> list[str]:
    refs: list[str] = []
    for m in _RE_MD_GH_REF.finditer(text):
        p = m.group("path")
        if not p:
            continue
        p = p.replace("\\", "/")
        # Normalize leading ./ or ../
        while p.startswith("./"):
            p = p[2:]
        # We only keep references that point at .github/... (not ../.github)
        idx = p.lower().find(".github/")
        p = p[idx:]
        refs.append(p)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _kind_for_path(rel: str) -> str:
    if rel.startswith(".github/agents/"):
        return "agent"
    if rel.startswith(".github/instructions/"):
        return "instruction"
    if rel.startswith(".github/prompts/"):
        return "prompt"
    if rel.startswith(".github/skills/") and rel.endswith("/skill.md"):
        return "skill"
    if rel.startswith(".github/skills/"):
        return "file"
    return "file"


def _iter_md_files(gh_root: Path) -> Iterable[Path]:
    for p in gh_root.rglob("*.md"):
        # Skip obvious junk/hidden.
        if "/.venv/" in p.as_posix():
            continue
        yield p


def build_graph(sol_root: Path) -> tuple[dict[str, Node], list[Edge]]:
    gh_root = sol_root / ".github"
    if not gh_root.exists():
        raise FileNotFoundError(f"Missing .github folder at: {gh_root}")

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    # First pass: create nodes for all markdown files.
    for path in _iter_md_files(gh_root):
        rel = _rel_posix(path, sol_root)
        kind = _kind_for_path(rel)
        node_id = _sanitize_id(f"file::{rel}")
        nodes[rel] = Node(node_id=node_id, label=rel, kind=kind, href=rel)

    # Agents: map agent-name => relpath
    agent_name_to_rel: dict[str, str] = {}
    for rel, node in list(nodes.items()):
        if not rel.startswith(".github/agents/"):
            continue
        text = (sol_root / rel).read_text(encoding="utf-8")
        yaml_text, body = _split_front_matter(text)
        if not yaml_text:
            continue
        agent_name, _handoffs = _parse_agent_yaml_minimal(yaml_text)
        if agent_name:
            agent_name_to_rel[agent_name] = rel
            # Relabel agent nodes to be more readable.
            nodes[rel] = Node(
                node_id=_sanitize_id(f"agent::{agent_name}"),
                label=agent_name,
                kind="agent",
                href=rel,
            )

    # Second pass: parse references + handoffs.
    for rel, node in list(nodes.items()):
        path = sol_root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Ignore non-utf8.
            continue

        yaml_text, body = _split_front_matter(text)

        # Markdown refs
        for ref in _extract_github_md_refs(body):
            dst_rel = ref
            if dst_rel not in nodes:
                # Create unknown target node if ref doesn't exist.
                nodes[dst_rel] = Node(
                    node_id=_sanitize_id(f"missing::{dst_rel}"),
                    label=f"MISSING: {dst_rel}",
                    kind="unknown",
                    href=None,
                )
            edges.append(Edge(src=node.node_id, dst=nodes[dst_rel].node_id, label="refs"))

        # Agent handoffs
        if rel.startswith(".github/agents/") and yaml_text:
            agent_name, handoffs = _parse_agent_yaml_minimal(yaml_text)
            if agent_name:
                src_id = nodes[rel].node_id
                for target_name in handoffs:
                    if target_name in agent_name_to_rel:
                        dst_id = nodes[agent_name_to_rel[target_name]].node_id
                    else:
                        ext_key = f"external-agent::{target_name}"
                        if ext_key not in nodes:
                            nodes[ext_key] = Node(
                                node_id=_sanitize_id(ext_key),
                                label=target_name,
                                kind="external-agent",
                                href=None,
                            )
                        dst_id = nodes[ext_key].node_id
                    edges.append(Edge(src=src_id, dst=dst_id, label="handoff"))

    # Deduplicate edges
    uniq: set[tuple[str, str, str]] = set()
    deduped: list[Edge] = []
    for e in edges:
        key = (e.src, e.dst, e.label)
        if key in uniq:
            continue
        uniq.add(key)
        deduped.append(e)

    return nodes, deduped


def render_mermaid(nodes: dict[str, Node], edges: list[Edge], title: str) -> str:
    out: list[str] = []
    out.append(f"# {title}\n")
    out.append("This file is generated by `tools/graph_github_kit.py`.\n")
    out.append("```mermaid")
    out.extend(render_mermaid_diagram(nodes, edges))
    out.append("```")

    out.append("\n## Legend")
    out.append("- Solid arrow: agent handoff")
    out.append("- Dotted arrow: markdown reference")

    counts: dict[str, int] = {}
    for n in nodes.values():
        counts[n.kind] = counts.get(n.kind, 0) + 1
    out.append("\n## Stats")
    out.append("- Nodes: " + ", ".join(f"{k}={counts.get(k, 0)}" for k in counts))
    out.append(f"- Edges: {len(edges)}")

    return "\n".join(out) + "\n"


def render_mermaid_diagram(nodes: dict[str, Node], edges: list[Edge]) -> list[str]:
    """Return Mermaid diagram lines (no markdown fences)."""

    kind_order = ["agent", "instruction", "prompt", "skill", "file", "external-agent", "unknown"]
    by_kind: dict[str, list[Node]] = {k: [] for k in kind_order}
    for node in nodes.values():
        by_kind.setdefault(node.kind, []).append(node)

    def node_decl(n: Node) -> str:
        safe_label = n.label.replace('"', "'")
        return f"  {n.node_id}[\"{safe_label}\"]"

    out: list[str] = []
    out.append("graph TD")

    for kind in kind_order:
        group = sorted(by_kind.get(kind, []), key=lambda n: n.label.lower())
        if not group:
            continue
        label = {
            "agent": "Agents",
            "instruction": "Instructions",
            "prompt": "Prompts",
            "skill": "Skills",
            "file": "Other Files",
            "external-agent": "External Agents",
            "unknown": "Missing Targets",
        }.get(kind, kind)
        out.append(f"  subgraph {label}")
        for n in group:
            out.append(node_decl(n))
        out.append("  end")

    for e in sorted(edges, key=lambda x: (x.label, x.src, x.dst)):
        if e.label == "handoff":
            out.append(f"  {e.src} -->|handoff| {e.dst}")
        else:
            out.append(f"  {e.src} -.->|refs| {e.dst}")

    out.append("\n  classDef agent fill:#1f77b4,stroke:#0b3d62,color:#fff;")
    out.append("  classDef instruction fill:#2ca02c,stroke:#145214,color:#fff;")
    out.append("  classDef prompt fill:#ff7f0e,stroke:#8a4b08,color:#fff;")
    out.append("  classDef skill fill:#9467bd,stroke:#4b2c6f,color:#fff;")
    out.append("  classDef file fill:#e7e7e7,stroke:#999,color:#111;")
    out.append("  classDef external_agent fill:#17becf,stroke:#0b5b60,color:#fff;")
    out.append("  classDef unknown fill:#d62728,stroke:#6d1414,color:#fff;")

    for n in nodes.values():
        cls = n.kind.replace("-", "_")
        out.append(f"  class {n.node_id} {cls};")

    return out


def render_html(nodes: dict[str, Node], edges: list[Edge], title: str) -> str:
    diagram = "\n".join(render_mermaid_diagram(nodes, edges))
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{safe_title}</title>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; }}
      header {{ padding: 12px 16px; border-bottom: 1px solid #ddd; background: #fafafa; }}
      main {{ padding: 16px; }}
      .hint {{ color: #555; font-size: 13px; }}
      .mermaid {{ overflow-x: auto; }}
    </style>
  </head>
  <body>
    <header>
      <div><strong>{safe_title}</strong></div>
      <div class=\"hint\">Generated by <code>tools/graph_github_kit.py</code>. Solid arrows = handoffs; dotted = refs.</div>
    </header>
    <main>
      <pre class=\"mermaid\">
{diagram}
      </pre>
    </main>
    <script type=\"module\">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
  </body>
</html>
"""


def render_dot(nodes: dict[str, Node], edges: list[Edge], title: str) -> str:
    def dot_label(n: Node) -> str:
        return n.label.replace('"', "\\\"")

    out: list[str] = []
    out.append("digraph github_kit {")
    out.append('  graph [rankdir=LR, labelloc="t", label="' + title.replace('"', "\\\"") + '"];')
    out.append("  node [shape=box, fontname=Helvetica];")

    color = {
        "agent": "#1f77b4",
        "instruction": "#2ca02c",
        "prompt": "#ff7f0e",
        "skill": "#9467bd",
        "file": "#e7e7e7",
        "external-agent": "#17becf",
        "unknown": "#d62728",
    }

    for n in sorted(nodes.values(), key=lambda x: x.label.lower()):
        fill = color.get(n.kind, "#ffffff")
        font = "#111111" if n.kind in {"file"} else "#ffffff"
        out.append(
            f'  {n.node_id} [label="{dot_label(n)}", style=filled, fillcolor="{fill}", fontcolor="{font}"];'
        )

    for e in edges:
        style = "solid" if e.label == "handoff" else "dashed"
        elabel = "handoff" if e.label == "handoff" else "refs"
        out.append(f'  {e.src} -> {e.dst} [label="{elabel}", style="{style}"];')

    out.append("}")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate graph of Sol .github agents/instructions/prompts/skills")
    parser.add_argument(
        "--root",
        default=None,
        help="Sol repo root (defaults to parent of this script's folder)",
    )
    parser.add_argument(
        "--out-md",
        default=".github/kit_graph.md",
        help="Output Mermaid markdown path, relative to root",
    )
    parser.add_argument(
        "--out-dot",
        default=".github/kit_graph.dot",
        help="Output Graphviz DOT path, relative to root",
    )
    parser.add_argument(
        "--out-html",
        default=".github/kit_graph.html",
        help="Output standalone HTML viewer path, relative to root",
    )
    parser.add_argument(
        "--title",
        default="Sol .github Kit Graph",
        help="Graph title",
    )
    args = parser.parse_args()

    sol_root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]

    nodes, edges = build_graph(sol_root)

    md_path = sol_root / args.out_md
    dot_path = sol_root / args.out_dot
    html_path = sol_root / args.out_html

    md_path.write_text(render_mermaid(nodes, edges, args.title), encoding="utf-8")
    dot_path.write_text(render_dot(nodes, edges, args.title), encoding="utf-8")
    html_path.write_text(render_html(nodes, edges, args.title), encoding="utf-8")

    print(f"Wrote Mermaid: {md_path}")
    print(f"Wrote DOT:     {dot_path}")
    print(f"Wrote HTML:    {html_path}")
    print(f"Nodes: {len(nodes)}  Edges: {len(edges)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
