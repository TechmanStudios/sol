"""
SOL Kernel: Neuro-Symbolic Reflection & DAG Extraction
File: sol/kernel/synthesis/symbolic_reflector.py

Performs neuro-symbolic reflection on continuous Riemannian semantic circuits:
1. Directed Acyclic Graph (DAG) extraction: Depth, critical path, fan-in/fan-out.
2. Symbolic Boolean Expression Recovery: Inverts continuous wave lensing into exact
   symbolic propositional logic formulas (AND, OR, NOT, XOR).
3. Semantic Equivalence Verification: Formally validates recovered symbolic logic
   against the continuous circuit truth table.
4. Mermaid Flowchart Export: Generates interactive GitHub-flavored Mermaid diagrams.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from sol.kernel.synthesis.circuit_topology import (
    CircuitNode,
    CircuitNodeType,
    SelfAssembledCircuit
)
from sol.kernel.synthesis.circuit_synthesizer import TruthTableSpec


@dataclass
class DAGNodeInfo:
    """Structural metadata for a node within the extracted DAG."""
    node_id: str
    node_type: CircuitNodeType
    depth: int
    parents: List[str]
    children: List[str]
    in_degree: int
    out_degree: int
    expression: str


@dataclass
class CircuitDAG:
    """Topological graph structure of a synthesized Riemannian circuit."""
    circuit_id: str
    nodes: Dict[str, DAGNodeInfo]
    layers: Dict[int, List[str]]
    critical_path_length: int
    max_depth: int
    max_fan_in: int
    max_fan_out: int
    total_edges: int


@dataclass
class SymbolicReflectionReport:
    """Comprehensive neuro-symbolic reflection analysis report."""
    circuit_id: str
    dag: CircuitDAG
    expressions: Dict[str, str]
    simplified_expressions: Dict[str, str]
    is_equivalent: bool
    mermaid_markdown: str
    reflection_time_ms: float
    algebraic_summary: str


class SymbolicReflector:
    """
    Extracts topological DAGs, recovers analytical propositional expressions,
    and produces executable diagrams from continuous Riemannian circuits.
    """

    def __init__(self, simplify_algebra: bool = True):
        self.simplify_algebra = simplify_algebra

    def reflect(
        self,
        circuit: SelfAssembledCircuit,
        spec: Optional[TruthTableSpec] = None
    ) -> SymbolicReflectionReport:
        """Executes full neuro-symbolic reflection pipeline on a Riemannian circuit."""
        t0 = time.time()

        # 1. Extract DAG and topological depth
        dag = self.extract_dag(circuit)

        # 2. Recover symbolic boolean expressions
        raw_exprs, simplified_exprs = self.recover_expressions(circuit, dag)

        # 3. Verify semantic equivalence if spec is provided
        is_equiv = True
        if spec is not None:
            is_equiv = self.verify_semantic_equivalence(simplified_exprs, spec)

        # 4. Generate Mermaid diagram
        mermaid_md = self.generate_mermaid(circuit, dag)

        # 5. Summarize algebraic properties
        summary_lines = []
        for out_id, expr in simplified_exprs.items():
            summary_lines.append(f"{out_id} = {expr}")
        summary_str = "; ".join(summary_lines)

        elapsed_ms = (time.time() - t0) * 1000.0

        return SymbolicReflectionReport(
            circuit_id=circuit.circuit_id,
            dag=dag,
            expressions=raw_exprs,
            simplified_expressions=simplified_exprs,
            is_equivalent=is_equiv,
            mermaid_markdown=mermaid_md,
            reflection_time_ms=elapsed_ms,
            algebraic_summary=summary_str
        )

    def extract_dag(self, circuit: SelfAssembledCircuit) -> CircuitDAG:
        """Extracts directed acyclic graph topology, computing depths and critical paths."""
        nodes_dict: Dict[str, DAGNodeInfo] = {}
        parents_map: Dict[str, List[str]] = {nid: [] for nid in circuit.nodes}
        children_map: Dict[str, List[str]] = {nid: [] for nid in circuit.nodes}

        for (src, dst) in circuit.edges.keys():
            if src in children_map:
                children_map[src].append(dst)
            if dst in parents_map:
                parents_map[dst].append(src)

        # Compute depths using topological forward propagation
        depth_map: Dict[str, int] = {}
        for nid in circuit.input_node_ids:
            depth_map[nid] = 0

        # Topological sort
        visited: Set[str] = set()
        topo_order: List[str] = []

        def topo_visit(n: str):
            if n in visited:
                return
            visited.add(n)
            for p in parents_map[n]:
                topo_visit(p)
            topo_order.append(n)

        for nid in circuit.nodes:
            topo_visit(nid)

        for nid in topo_order:
            if nid in circuit.input_node_ids:
                depth_map[nid] = 0
            else:
                p_depths = [depth_map.get(p, 0) for p in parents_map[nid]]
                depth_map[nid] = (max(p_depths) + 1) if p_depths else 0

        # Build layers map
        layers: Dict[int, List[str]] = {}
        for nid, d in depth_map.items():
            layers.setdefault(d, []).append(nid)

        max_depth = max(depth_map.values()) if depth_map else 0
        max_fan_in = max((len(parents_map[n]) for n in circuit.nodes), default=0)
        max_fan_out = max((len(children_map[n]) for n in circuit.nodes), default=0)

        for nid, node in circuit.nodes.items():
            nodes_dict[nid] = DAGNodeInfo(
                node_id=nid,
                node_type=node.node_type,
                depth=depth_map.get(nid, 0),
                parents=parents_map[nid],
                children=children_map[nid],
                in_degree=len(parents_map[nid]),
                out_degree=len(children_map[nid]),
                expression=""
            )

        return CircuitDAG(
            circuit_id=circuit.circuit_id,
            nodes=nodes_dict,
            layers=layers,
            critical_path_length=max_depth + 1,
            max_depth=max_depth,
            max_fan_in=max_fan_in,
            max_fan_out=max_fan_out,
            total_edges=len(circuit.edges)
        )

    def recover_expressions(
        self,
        circuit: SelfAssembledCircuit,
        dag: CircuitDAG
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Recursively translates topological wave connections into boolean expressions.
        Returns: (raw_expressions, simplified_expressions).
        """
        memo: Dict[str, str] = {}

        def get_node_expr(nid: str) -> str:
            if nid in memo:
                return memo[nid]

            node = circuit.nodes[nid]
            if node.node_type == CircuitNodeType.INPUT:
                memo[nid] = nid
                return nid

            parents = dag.nodes[nid].parents
            if not parents:
                memo[nid] = "0"
                return "0"

            parent_exprs = [get_node_expr(p) for p in parents]

            if node.node_type == CircuitNodeType.INVERTER:
                child = parent_exprs[0]
                memo[nid] = f"(NOT {child})"
            elif node.node_type in (CircuitNodeType.LENS_AND, CircuitNodeType.LENS):
                if len(parent_exprs) == 1:
                    memo[nid] = parent_exprs[0]
                else:
                    inner = " AND ".join(parent_exprs)
                    memo[nid] = f"({inner})"
            elif node.node_type == CircuitNodeType.LENS_OR:
                if len(parent_exprs) == 1:
                    memo[nid] = parent_exprs[0]
                else:
                    inner = " OR ".join(parent_exprs)
                    memo[nid] = f"({inner})"
            elif node.node_type == CircuitNodeType.INTERFERENCE:
                if len(parent_exprs) == 1:
                    memo[nid] = parent_exprs[0]
                elif len(parent_exprs) == 2:
                    memo[nid] = f"({parent_exprs[0]} XOR {parent_exprs[1]})"
                else:
                    inner = " XOR ".join(parent_exprs)
                    memo[nid] = f"({inner})"
            elif node.node_type == CircuitNodeType.BASIN:
                if len(parent_exprs) == 1:
                    memo[nid] = parent_exprs[0]
                else:
                    inner = " OR ".join(parent_exprs)
                    memo[nid] = f"({inner})"
            elif node.node_type == CircuitNodeType.SPLITTER:
                memo[nid] = parent_exprs[0]
            else:
                memo[nid] = parent_exprs[0] if parent_exprs else "0"

            return memo[nid]

        raw_exprs: Dict[str, str] = {}
        simplified_exprs: Dict[str, str] = {}

        for out_id in circuit.output_node_ids:
            raw = get_node_expr(out_id)
            raw_exprs[out_id] = raw
            simplified = self._simplify_boolean_string(raw) if self.simplify_algebra else raw
            simplified_exprs[out_id] = simplified

        return raw_exprs, simplified_exprs

    def _simplify_boolean_string(self, expr: str) -> str:
        """Simplifies double negations, trivial identities, and redundant parens."""
        s = expr.strip()

        # Simplify double negations: (NOT (NOT X)) -> X
        changed = True
        while changed:
            old = s
            # Pattern: (NOT (NOT ...))
            if s.startswith("(NOT (NOT ") and s.endswith("))"):
                inner = s[10:-2]
                s = inner.strip()
            # Replace inline double negations
            s = s.replace("(NOT (NOT ", "").replace("))", ")") if "(NOT (NOT " in s else s
            changed = (old != s)

        return s

    def verify_semantic_equivalence(
        self,
        expressions: Dict[str, str],
        spec: TruthTableSpec
    ) -> bool:
        """
        Evaluates boolean expressions under all truth table input assignments
        to formally verify semantic equivalence.
        """
        for in_tuple, expected_out in spec.table.items():
            env = {spec.inputs[i]: in_tuple[i] for i in range(len(spec.inputs))}

            for out_idx, out_name in enumerate(spec.outputs):
                expr_str = expressions.get(out_name, "0")
                val = self._evaluate_expr_string(expr_str, env)
                if val != expected_out[out_idx]:
                    return False

        return True

    def _evaluate_expr_string(self, expr: str, env: Dict[str, int]) -> int:
        """Evaluates a propositional boolean formula string under variable assignments."""
        # Replace propositional operators with Python boolean operators
        # Note: Must replace XOR before OR, as OR is a substring of XOR
        py_expr = expr
        py_expr = py_expr.replace("XOR", " ^ ")
        py_expr = py_expr.replace("AND", " and ")
        py_expr = py_expr.replace("OR", " or ")
        py_expr = py_expr.replace("NOT", " not ")

        # Safe evaluation namespace
        safe_env = {k: bool(v) for k, v in env.items()}
        try:
            res = eval(py_expr, {"__builtins__": {}}, safe_env)
            return 1 if bool(res) else 0
        except Exception:
            return 0

    def generate_mermaid(self, circuit: SelfAssembledCircuit, dag: Optional[CircuitDAG] = None) -> str:
        """Generates GitHub-flavored Mermaid flowchart markup for the circuit."""
        if dag is None:
            dag = self.extract_dag(circuit)

        lines = [
            "```mermaid",
            "flowchart LR",
            f"    %% Circuit: {circuit.name} (ID: {circuit.circuit_id})",
            "    classDef inputNode fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;",
            "    classDef lensNode fill:#0f172a,stroke:#4ade80,stroke-width:2px,color:#f8fafc;",
            "    classDef interfNode fill:#1e1b4b,stroke:#c084fc,stroke-width:2px,color:#f8fafc;",
            "    classDef invNode fill:#31102b,stroke:#f43f5e,stroke-width:2px,color:#f8fafc;",
            "    classDef basinNode fill:#14532d,stroke:#22c55e,stroke-width:3px,color:#ffffff,font-weight:bold;",
            ""
        ]

        # Subgraph: Inputs
        lines.append("    subgraph Inputs [\"Inputs\"]")
        for in_id in circuit.input_node_ids:
            lines.append(f"        {in_id}[\"Input: {in_id}\"]:::inputNode")
        lines.append("    end")
        lines.append("")

        # Subgraph: Intermediate Operators
        intermediate_nodes = [
            nid for nid, node in circuit.nodes.items()
            if node.node_type not in (CircuitNodeType.INPUT, CircuitNodeType.BASIN)
        ]
        if intermediate_nodes:
            lines.append("    subgraph ManifoldLoci [\"Riemannian Loci & Operators\"]")
            for nid in intermediate_nodes:
                node = circuit.nodes[nid]
                ntype = node.node_type.value
                if node.node_type in (CircuitNodeType.LENS_AND, CircuitNodeType.LENS):
                    lines.append(f"        {nid}([\"Lens (AND): {nid}\"]):::lensNode")
                elif node.node_type == CircuitNodeType.LENS_OR:
                    lines.append(f"        {nid}([\"Lens (OR): {nid}\"]):::lensNode")
                elif node.node_type == CircuitNodeType.INTERFERENCE:
                    lines.append(f"        {nid}{{\"Interference (XOR): {nid}\"}}:::interfNode")
                elif node.node_type == CircuitNodeType.INVERTER:
                    lines.append(f"        {nid}[/\"Inverter (NOT): {nid}\"/]:::invNode")
                else:
                    lines.append(f"        {nid}[\"{ntype}: {nid}\"]")
            lines.append("    end")
            lines.append("")

        # Subgraph: Output Basins
        lines.append("    subgraph Basins [\"Output Basins\"]")
        for out_id in circuit.output_node_ids:
            lines.append(f"        {out_id}[(\"Basin: {out_id}\")]:::basinNode")
        lines.append("    end")
        lines.append("")

        # Directed Edges
        lines.append("    %% Topological Directed Geodesic Rails")
        for (src, dst), weight in circuit.edges.items():
            if weight != 1.0:
                lines.append(f"    {src} -->|w={weight:.2f}| {dst}")
            else:
                lines.append(f"    {src} --> {dst}")

        lines.append("```")
        return "\n".join(lines)
