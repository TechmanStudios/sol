#!/usr/bin/env python3
"""
SOL Hippocampus — CLI

Unified command-line interface for the hippocampus subsystem:
dream cycles, memory queries, meta-learning, and compaction.

Usage:
    python cli.py dream              # Run a dream cycle
    python cli.py dream --sessions 3 # Replay top 3 sessions
    python cli.py dream --dry-run    # Show what would be replayed

    python cli.py query --param damping        # Query memory for damping
    python cli.py query --basin 82             # Query memory for node 82
    python cli.py query --novel damping        # Find untested damping values

    python cli.py meta                         # Print meta-learning report
    python cli.py meta --scores                # Template effectiveness
    python cli.py meta --cold                  # Under-explored regions

    python cli.py compact                      # Rebuild memory_graph.json
    python cli.py status                       # Memory stats

    python cli.py kb build                     # Build/rebuild KB index
    python cli.py kb query "Metatron spiral"   # Query the KB
    python cli.py kb status                    # KB index statistics
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))


def cmd_dream(args):
    from dream_cycle import DreamCycle
    dc = DreamCycle(max_sessions=args.sessions, dry_run=args.dry_run)
    result = dc.run()
    if args.json:
        print(json.dumps(result, indent=2))


def cmd_query(args):
    from retrieval import MemoryQuery
    mq = MemoryQuery()

    if args.param:
        findings = mq.query_parameter(args.param)
        if not findings:
            print(f"No memory findings for parameter '{args.param}'")
            return
        print(f"\nMemory findings for '{args.param}' ({len(findings)} results):")
        for f in findings:
            print(f"  {f.label} (conf={f.confidence:.2f}, tags={f.tags})")

    elif args.basin is not None:
        findings = mq.query_basin(args.basin)
        if not findings:
            print(f"No memory findings for basin node {args.basin}")
            return
        print(f"\nMemory findings for basin node {args.basin} ({len(findings)} results):")
        for f in findings:
            print(f"  {f.label} (conf={f.confidence:.2f}, tags={f.tags})")

    elif args.novel:
        novel = mq.query_novel_regions(args.novel)
        if not novel:
            print(f"No novel regions found for '{args.novel}' (or no prior data)")
            return
        print(f"\nNovel regions for '{args.novel}':")
        for v in novel:
            print(f"  {v}")

    elif args.history:
        parts = args.history.split(":")
        template = parts[0] if len(parts) > 0 else None
        gap_type = parts[1] if len(parts) > 1 else None
        history = mq.query_experiment_history(template=template, gap_type=gap_type)
        if not history:
            print("No experiment history found")
            return
        print(f"\nExperiment history ({len(history)} records):")
        for h in history:
            print(f"  {h.get('session_id')} | {h.get('template')} | "
                  f"score={h.get('insight_score', 0):.2f} | "
                  f"sanity={'PASS' if h.get('sanity_passed') else 'FAIL'}")

    else:
        print(mq.memory_summary())


def cmd_meta(args):
    from meta_learner import MetaLearner
    ml = MetaLearner()

    if args.scores:
        scores = ml.template_scores()
        if not scores:
            print("No template scores yet (need more observations)")
            return
        print("\nTemplate Effectiveness Scores (EMA):")
        for t, s in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(s * 20)
            print(f"  {t:<25} {s:.3f} {bar}")

    elif args.cold:
        cold = ml.cold_regions()
        if not cold:
            print("No under-explored regions found")
            return
        print("\nUnder-Explored Parameter Regions:")
        for c in cold:
            print(f"  {c['param']}: {c['sessions']} sessions, "
                  f"values={c['values_tested']}, "
                  f"avg_insight={c['avg_insight']}")

    elif args.gap_type:
        scores = ml.gap_type_scores()
        if not scores:
            print("No gap type scores yet")
            return
        print("\nGap Type Yield Scores (EMA):")
        for gt, s in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(s * 20)
            print(f"  {gt:<25} {s:.3f} {bar}")

    else:
        print(ml.report())


def cmd_compact(args):
    from memory_store import compact
    result = compact(force=args.force)
    if args.json:
        print(json.dumps(result.get("meta", {}), indent=2))


def cmd_status(args):
    from memory_store import memory_stats
    from memory_overlay import MemoryOverlay

    stats = memory_stats()
    overlay = MemoryOverlay()
    summary = overlay.summary()

    print(f"\n{'='*50}")
    print("SOL Hippocampus — Status")
    print(f"{'='*50}")
    print(f"\nCore manifold:")
    print(f"  Nodes: {summary['core_nodes']}")
    print(f"  Edges: {summary['core_edges']}")
    print(f"\nMemory overlay:")
    print(f"  Nodes: {stats['node_count']}")
    print(f"  Edges: {stats['edge_count']}")
    print(f"  Avg confidence: {stats['avg_confidence']:.3f}")
    print(f"  ID counter: {stats['id_counter']}")
    print(f"  Last compacted: {stats['last_compacted']}")
    print(f"  Trace files: {stats['trace_files']}")
    print(f"\nComposite manifold:")
    print(f"  Total nodes: {summary['total_nodes']}")
    print(f"  Total edges: {summary['total_edges']}")

    if args.json:
        print(json.dumps({**stats, **summary}, indent=2))


def cmd_kb(args):
    if args.kb_command == "build":
        from kb_index import KBIndex
        idx = KBIndex(auto_build=False)
        print("Building KB index...")
        result = idx.build()
        print(f"  Chunks:  {result['chunks']}")
        print(f"  Terms:   {result['terms']}")
        print(f"  Avg DL:  {result['avg_doc_len']}")
        print(f"  KB SHA:  {result['kb_sha256'][:16]}...")
        print(f"  Saved:   {result['index_path']}")
        if args.json:
            print(json.dumps(result, indent=2))

    elif args.kb_command == "query":
        query_text = " ".join(args.query_text)
        if not query_text:
            print("Usage: cli.py kb query <text>")
            return
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        hits = mq.query_kb(query_text, top_k=args.top_k)
        if not hits:
            print("No KB results (index may not be built yet)")
            return
        print(f"\nKB results for '{query_text}' ({len(hits)} hits):\n")
        for h in hits:
            print(f"  [{h['score']:.3f}] {h['section']} "
                  f"(L{h['line_start']}-{h['line_end']})")
            print(f"    Terms: {', '.join(h['matched_terms'][:8])}")
            print(f"    {h['snippet'][:200]}")
            print()
        if args.json:
            print(json.dumps(hits, indent=2))

    elif args.kb_command == "status":
        from retrieval import MemoryQuery
        mq = MemoryQuery()
        status = mq.kb_status()
        if not status.get("available"):
            print("KB index not available (run: cli.py kb build)")
            return
        print(f"\nKB Index Status:")
        print(f"  Chunks:       {status.get('chunks', '?')}")
        print(f"  Unique terms: {status.get('unique_terms', '?')}")
        print(f"  Avg doc len:  {status.get('avg_doc_length', '?')}")
        print(f"  Index cached: {status.get('index_file_exists', False)}")
        sections = status.get("sections", {})
        if sections:
            print(f"\n  Sections ({len(sections)}):")
            for sec, cnt in sorted(sections.items(), key=lambda x: x[1], reverse=True)[:15]:
                print(f"    {sec[:50]:<50} {cnt} chunks")
        if args.json:
            # Remove non-serializable top_terms tuples
            safe = {k: v for k, v in status.items() if k != "top_terms"}
            print(json.dumps(safe, indent=2, default=str))
    else:
        print("Usage: cli.py kb {build|query|status}")


def main():
    parser = argparse.ArgumentParser(
        description="SOL Hippocampus — Full Memory System",
        epilog="Dream cycles, retrieval, meta-learning, and memory compaction.",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # dream
    p_dream = sub.add_parser("dream", help="Run a dream cycle")
    p_dream.add_argument("--sessions", type=int, default=None,
                         help="Max sessions to replay")
    p_dream.add_argument("--dry-run", action="store_true",
                         help="Show what would be replayed")
    p_dream.add_argument("--json", action="store_true",
                         help="Output JSON summary")

    # query
    p_query = sub.add_parser("query", help="Query the memory layer")
    p_query.add_argument("--param", type=str, help="Query by parameter name")
    p_query.add_argument("--basin", type=int, help="Query by basin node ID")
    p_query.add_argument("--novel", type=str, help="Find untested values for a parameter")
    p_query.add_argument("--history", type=str,
                         help="Experiment history (format: template:gap_type)")

    # meta
    p_meta = sub.add_parser("meta", help="Meta-learning report")
    p_meta.add_argument("--scores", action="store_true",
                        help="Template effectiveness scores")
    p_meta.add_argument("--cold", action="store_true",
                        help="Under-explored regions")
    p_meta.add_argument("--gap-type", action="store_true",
                        help="Gap type yield scores")

    # compact
    p_compact = sub.add_parser("compact", help="Rebuild memory_graph.json from traces")
    p_compact.add_argument("--force", action="store_true",
                           help="Force rebuild even if up to date")
    p_compact.add_argument("--json", action="store_true",
                           help="Output JSON metadata")

    # status
    p_status = sub.add_parser("status", help="Memory system status")
    p_status.add_argument("--json", action="store_true",
                          help="Output JSON")

    # kb
    p_kb = sub.add_parser("kb", help="Knowledge base index operations")
    p_kb.add_argument("kb_command", choices=["build", "query", "status"],
                      help="KB subcommand")
    p_kb.add_argument("query_text", nargs="*", default=[],
                      help="Query text (for 'query' subcommand)")
    p_kb.add_argument("--top-k", type=int, default=5,
                      help="Number of results to return")
    p_kb.add_argument("--json", action="store_true",
                      help="Output JSON")

    args = parser.parse_args()

    commands = {
        "dream": cmd_dream,
        "query": cmd_query,
        "meta": cmd_meta,
        "compact": cmd_compact,
        "status": cmd_status,
        "kb": cmd_kb,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
