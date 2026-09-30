"""Generate long-form omnibus sweep command JSON batches for the SOL dashboard runner.

This creates a *staged* batch of command JSON files compatible with:
  tools/dashboard_automation/run_dashboard_sweep.py --watch-commands

By default it writes into a timestamped staging folder under:
  solData/testResults/omnibus_batches/<STAMP>/command_queue/

Use --enqueue to write directly into:
  solData/testResults/command_queue/

Notes
- Dashboard implementation is ground truth for runnable knobs.
- SOL_mathFoundation PDF is treated as a theoretical superset; symbols not
  represented in the dashboard are flagged in the manifest.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


# ----------------------------
# Dashboard config extraction
# ----------------------------


def _strip_js_comments(text: str) -> str:
    # Minimal comment stripping used only for locating the config block; the
    # parser below is comment-aware.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


class _JsObjParser:
    def __init__(self, src: str):
        self.src = src
        self.i = 0

    def _peek(self) -> str:
        return self.src[self.i : self.i + 1]

    def _advance(self, n: int = 1) -> None:
        self.i += n

    def _eof(self) -> bool:
        return self.i >= len(self.src)

    def _skip_ws_and_comments(self) -> None:
        while not self._eof():
            ch = self._peek()
            if ch and ch.isspace():
                self._advance(1)
                continue

            if self.src.startswith("//", self.i):
                j = self.src.find("\n", self.i)
                self.i = len(self.src) if j == -1 else j + 1
                continue

            if self.src.startswith("/*", self.i):
                j = self.src.find("*/", self.i + 2)
                if j == -1:
                    self.i = len(self.src)
                else:
                    self.i = j + 2
                continue

            break

    def _expect(self, s: str) -> None:
        self._skip_ws_and_comments()
        if not self.src.startswith(s, self.i):
            near = self.src[self.i : self.i + 50]
            raise ValueError(f"Expected {s!r} at {self.i}; near: {near!r}")
        self._advance(len(s))

    def _parse_string(self) -> str:
        self._skip_ws_and_comments()
        q = self._peek()
        if q not in ('"', "'"):
            raise ValueError("Expected string")
        self._advance(1)
        out = []
        while not self._eof():
            ch = self._peek()
            if ch == "\\":
                self._advance(1)
                if self._eof():
                    break
                out.append(self._peek())
                self._advance(1)
                continue
            if ch == q:
                self._advance(1)
                return "".join(out)
            out.append(ch)
            self._advance(1)
        raise ValueError("Unterminated string")

    def _parse_identifier(self) -> str:
        self._skip_ws_and_comments()
        m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", self.src[self.i :])
        if not m:
            near = self.src[self.i : self.i + 50]
            raise ValueError(f"Expected identifier at {self.i}; near: {near!r}")
        ident = m.group(0)
        self._advance(len(ident))
        return ident

    def _parse_number_or_word(self) -> Any:
        self._skip_ws_and_comments()
        # Number
        m = re.match(r"-?(?:\d+\.\d+|\d+)(?:[eE][+-]?\d+)?", self.src[self.i :])
        if m:
            token = m.group(0)
            self._advance(len(token))
            try:
                if "." in token or "e" in token.lower():
                    return float(token)
                return int(token)
            except Exception:
                return token

        # Word literals
        word = self._parse_identifier()
        if word == "true":
            return True
        if word == "false":
            return False
        if word == "null":
            return None
        # For non-JSON words (e.g. Infinity) keep as token.
        return word

    def parse_value(self) -> Any:
        self._skip_ws_and_comments()
        ch = self._peek()
        if ch == "{":
            return self.parse_object()
        if ch == "[":
            return self.parse_array()
        if ch in ('"', "'"):
            return self._parse_string()
        return self._parse_number_or_word()

    def parse_array(self) -> list[Any]:
        self._expect("[")
        arr: list[Any] = []
        while True:
            self._skip_ws_and_comments()
            if self._peek() == "]":
                self._advance(1)
                return arr
            arr.append(self.parse_value())
            self._skip_ws_and_comments()
            if self._peek() == ",":
                self._advance(1)
                continue
            if self._peek() == "]":
                self._advance(1)
                return arr
            near = self.src[self.i : self.i + 50]
            raise ValueError(f"Expected ',' or ']' in array; near: {near!r}")

    def parse_object(self) -> dict[str, Any]:
        self._expect("{")
        obj: dict[str, Any] = {}
        while True:
            self._skip_ws_and_comments()
            if self._peek() == "}":
                self._advance(1)
                return obj

            # Key
            ch = self._peek()
            if ch in ('"', "'"):
                key = self._parse_string()
            else:
                key = self._parse_identifier()

            self._skip_ws_and_comments()
            self._expect(":")
            value = self.parse_value()
            obj[key] = value

            self._skip_ws_and_comments()
            if self._peek() == ",":
                self._advance(1)
                continue
            if self._peek() == "}":
                self._advance(1)
                return obj
            near = self.src[self.i : self.i + 50]
            raise ValueError(f"Expected ',' or '}}' in object; near: {near!r}")


def _extract_app_config(dashboard_html: str) -> dict[str, Any]:
    # Find "config: { ... }" inside "const App = { ... }".
    # We parse only the object literal for config.
    anchor = "config:"
    idx = dashboard_html.find(anchor)
    if idx == -1:
        raise ValueError("Could not find 'config:' in dashboard HTML")

    # Find the first '{' after config:
    brace_start = dashboard_html.find("{", idx)
    if brace_start == -1:
        raise ValueError("Could not find '{' starting config object")

    # Slice a manageable window starting at brace_start and let the parser
    # consume the first full object.
    window = dashboard_html[brace_start:]
    parser = _JsObjParser(window)
    config = parser.parse_object()
    if not isinstance(config, dict):
        raise ValueError("Parsed config is not an object")
    return config


def _iter_leaf_paths(obj: Any, prefix: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_leaf_paths(v, prefix + (str(k),))
        return
    if isinstance(obj, list):
        # Arrays are not swept (usually metadata like derivedKeys).
        yield prefix, obj
        return
    yield prefix, obj


def _set_nested(d: dict[str, Any], path: Iterable[str], value: Any) -> dict[str, Any]:
    cur = d
    parts = list(path)
    for key in parts[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[parts[-1]] = value
    return d


# ----------------------------
# Math foundation extraction
# ----------------------------


@dataclass(frozen=True)
class TheoryInventory:
    pdf_path: str
    symbols: list[str]
    raw_hits: dict[str, int]


_GREEK_RE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")


def _extract_theory_symbols_from_pdf(pdf_path: Path, max_pages: int = 12) -> TheoryInventory:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    hits: dict[str, int] = {}
    for pi in range(min(doc.page_count, max_pages)):
        text = doc.load_page(pi).get_text("text")  # type: ignore[attr-defined]
        for ch in _GREEK_RE.findall(text):
            hits[ch] = hits.get(ch, 0) + 1

    # Also pick up a few conventional Latin variable names often used in the doc.
    # This is intentionally conservative (we don't want a giant noisy list).
    latin_candidates = ["u", "rho", "psi", "phi", "v", "p", "dt", "t", "M", "g"]
    for pi in range(min(doc.page_count, max_pages)):
        text = doc.load_page(pi).get_text("text")  # type: ignore[attr-defined]
        lower = text.lower()
        for tok in latin_candidates:
            if tok.lower() in lower:
                hits[tok] = hits.get(tok, 0) + lower.count(tok.lower())

    symbols = sorted(hits.keys(), key=lambda k: (-hits[k], str(k)))
    return TheoryInventory(pdf_path=str(pdf_path), symbols=symbols, raw_hits=hits)


def _map_theory_symbol_to_impl(symbol: str) -> str | None:
    # Very small, explicit mapping. Everything else is treated as theory-only.
    mapping = {
        "ρ": "rho",
        "v": "edgeFlux",
        "φ": "p",
        "ψ": "psi",
        "rho": "rho",
        "phi": "p",
        "psi": "psi",
        "p": "p",
        "dt": "dt",
    }
    return mapping.get(symbol)


# ----------------------------
# Omnibus plan generation
# ----------------------------


@dataclass(frozen=True)
class SweepSpec:
    path: tuple[str, ...]
    default: Any
    values: list[Any]
    reason: str


def _is_sweepable_config(path: tuple[str, ...], value: Any) -> bool:
    if not path:
        return False

    # Skip viz-only knobs (presentation).
    if path[0] in {"viz"}:
        return False

    # Skip obvious metadata strings.
    if path[-1] in {"notes"}:
        return False

    # Skip arrays by default.
    if isinstance(value, list):
        return False

    # Skip color-ish strings.
    if isinstance(value, str) and value.startswith("#"):
        return False

    return isinstance(value, (int, float, bool, str)) or value is None


def _value_candidates(path: tuple[str, ...], default: Any) -> list[Any]:
    # Enum overrides (based on dashboard comments).
    joined = ".".join(path)
    if joined.endswith("capLaw.lawFamily"):
        return ["linear", "power", "hybrid"]
    if joined.endswith("capLaw.proxy"):
        return ["degree", "condSum", "hybrid"]
    if joined.endswith("capLaw.writeTo"):
        return ["semanticMass", "semanticMass0", "both"]

    if isinstance(default, bool):
        return [False, True]

    if isinstance(default, (int, float)):
        d = float(default)
        # Conservative multiplicative sweep.
        if d == 0:
            return [0, 0.05, 0.1, 0.2]
        # Keep sign.
        if d > 0:
            return [round(d * 0.5, 6), default, round(d * 1.5, 6)]
        return [round(d * 1.5, 6), default, round(d * 0.5, 6)]

    if default is None:
        # For null placeholders (e.g., capLaw.k0), leave unswept.
        return []

    if isinstance(default, str):
        # Most strings are labels/colors; only sweep known enums above.
        return []

    return []


def _build_sweep_specs(app_config: dict[str, Any]) -> list[SweepSpec]:
    specs: list[SweepSpec] = []
    for path, value in _iter_leaf_paths(app_config):
        if not _is_sweepable_config(path, value):
            continue
        values = _value_candidates(path, value)
        if not values:
            continue
        specs.append(SweepSpec(path=path, default=value, values=values, reason="dashboard.config"))
    return specs


def _make_command(
    *,
    dashboard: str,
    out_prefix: str,
    params: dict[str, Any],
    dashboard_config: dict[str, Any] | None,
    meta: dict[str, Any],
    runs: int = 1,
    timeout_s: float = 900.0,
) -> dict[str, Any]:
    cmd: dict[str, Any] = {
        "kind": "sol.dashboard.sweep.v1",
        "dashboard": dashboard,
        "outPrefix": out_prefix,
        "runs": runs,
        "timeoutS": timeout_s,
        "params": params,
        "meta": meta,
    }
    if dashboard_config:
        cmd["dashboardConfig"] = dashboard_config
    return cmd


def _make_ab_ba_pair(
    *,
    dashboard: str,
    base_out_prefix: str,
    base_params: dict[str, Any],
    a_overrides: dict[str, Any] | None,
    b_overrides: dict[str, Any] | None,
    meta_common: dict[str, Any],
    timeout_s: float,
) -> list[dict[str, Any]]:
    a_params = {**base_params, **(a_overrides or {})}
    b_params = {**base_params, **(b_overrides or {})}

    ab = _make_command(
        dashboard=dashboard,
        out_prefix=f"{base_out_prefix}_AB",
        params=a_params,
        dashboard_config=None,
        meta={**meta_common, "order": "A_then_B", "arm": "A"},
        timeout_s=timeout_s,
    )
    ab2 = _make_command(
        dashboard=dashboard,
        out_prefix=f"{base_out_prefix}_AB__B",
        params=b_params,
        dashboard_config=None,
        meta={**meta_common, "order": "A_then_B", "arm": "B"},
        timeout_s=timeout_s,
    )

    ba = _make_command(
        dashboard=dashboard,
        out_prefix=f"{base_out_prefix}_BA",
        params=b_params,
        dashboard_config=None,
        meta={**meta_common, "order": "B_then_A", "arm": "B"},
        timeout_s=timeout_s,
    )
    ba2 = _make_command(
        dashboard=dashboard,
        out_prefix=f"{base_out_prefix}_BA__A",
        params=a_params,
        dashboard_config=None,
        meta={**meta_common, "order": "B_then_A", "arm": "A"},
        timeout_s=timeout_s,
    )

    return [ab, ab2, ba, ba2]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True)
class BatchPaths:
    root: Path
    queue: Path
    manifest: Path


def _resolve_batch_paths(sol_root: Path, enqueue: bool) -> BatchPaths:
    test_results = sol_root / "solData" / "testResults"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if enqueue:
        queue = test_results / "command_queue"
        root = queue
    else:
        root = test_results / "omnibus_batches" / stamp
        queue = root / "command_queue"

    manifest = root / f"omnibus_manifest_{stamp}.json"
    return BatchPaths(root=root, queue=queue, manifest=manifest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard",
        default="sol_dashboard_v3_7_2.html",
        help="Dashboard HTML under sol/ (canonical target for command generation).",
    )
    ap.add_argument(
        "--pdf",
        default="SOL_mathFoundation_v1.pdf",
        help="Math foundation PDF used to extract theoretical symbols.",
    )
    ap.add_argument(
        "--enqueue",
        action="store_true",
        help="Write commands directly into solData/testResults/command_queue (will run if watcher is active).",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=60,
        help="Max number of command files to generate (safety cap).",
    )
    ap.add_argument(
        "--phases",
        default="A,B,C,D",
        help=(
            "Comma-separated phases to generate (any of A,B,C,D). "
            "Note: generation order is A, C, B, D so Phase C isn't starved by large Phase B."
        ),
    )
    ap.add_argument(
        "--steps",
        type=int,
        default=4000,
        help="Default steps per run (template baseline).",
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=900.0,
        help="Timeout per run (seconds).",
    )

    args = ap.parse_args()

    sol_root = Path(__file__).resolve().parents[2]
    dashboard_path = (sol_root / args.dashboard).resolve()
    if not dashboard_path.exists():
        raise FileNotFoundError(f"Dashboard not found: {dashboard_path}")

    # Extract dashboard config.
    html = dashboard_path.read_text(encoding="utf-8")
    app_config = _extract_app_config(html)
    specs = _build_sweep_specs(app_config)

    # Extract theory inventory.
    pdf_path = (sol_root / args.pdf).resolve()
    theory: TheoryInventory | None = None
    if pdf_path.exists():
        theory = _extract_theory_symbols_from_pdf(pdf_path)

    batch = _resolve_batch_paths(sol_root, enqueue=bool(args.enqueue))

    # Harness defaults (these are *mechanismTraceSweep* params).
    base_params: dict[str, Any] = {
        "steps": int(args.steps),
        "dts": [0.12, 0.16],
        "dampings": [2, 4, 6],
        "modes": ["pulse100"],
        "pressSliderVal": 200,
        "injectAmount": 10,
        "targetId": 64,
        "probeIds": [64, 82, 79],
        "guardrail": {"type": "none"},
    }

    generated: list[dict[str, Any]] = []
    commands_written: list[str] = []

    # Phase A: baseline harness sanity (dt/damp/pressure/inject).
    phase_a: list[dict[str, Any]] = []
    phase_a.append(
        _make_command(
            dashboard=args.dashboard,
            out_prefix="omnibus_A_sanity_default",
            params={**base_params},
            dashboard_config=None,
            meta={"phase": "A", "purpose": "harness_sanity", "source": "template"},
            timeout_s=float(args.timeout_s),
        )
    )
    phase_a.append(
        _make_command(
            dashboard=args.dashboard,
            out_prefix="omnibus_A_sanity_noinject",
            params={**base_params, "injectAmount": 0},
            dashboard_config=None,
            meta={"phase": "A", "purpose": "harness_sanity", "source": "template", "knob": "injectAmount"},
            timeout_s=float(args.timeout_s),
        )
    )

    # Phase B: dashboard config single-knob sweeps.
    phase_b: list[dict[str, Any]] = []
    for spec in specs:
        path_str = ".".join(spec.path)
        for v in spec.values:
            cfg: dict[str, Any] = {}
            _set_nested(cfg, spec.path, v)

            phase_b.append(
                _make_command(
                    dashboard=args.dashboard,
                    out_prefix=f"omnibus_B_cfg_{path_str.replace('.', '_')}_{str(v).replace('.', 'p')}",
                    params={**base_params},
                    dashboard_config=cfg,
                    meta={
                        "phase": "B",
                        "purpose": "single_knob",
                        "source": "dashboard",
                        "dashboardConfigPath": path_str,
                        "default": spec.default,
                        "value": v,
                    },
                    timeout_s=float(args.timeout_s),
                )
            )

    # Phase C: reserved for interactions (template only; user can expand).
    # Phase C: counterbalanced interaction probes (AB/BA)
    # These live in sweep params (guardrail + bleed), not App.config. This makes them
    # runnable even when the dashboard UI doesn't expose a knob.
    phase_c: list[dict[str, Any]] = []

    # Define treatments B against a shared baseline A.
    baseline_a: dict[str, Any] = {
        "guardrail": {"type": "none"},
    }

    treatments: list[dict[str, Any]] = [
        {
            "id": "pLeak",
            "label": "adaptive_damping_pLeak",
            "overrides": {
                "guardrail": {"type": "pLeak", "gain": 6.0, "meanPSoft": 0.003, "meanPSpan": 0.01}
            },
        },
        {
            "id": "rhoLeak",
            "label": "adaptive_damping_rhoLeak",
            "overrides": {
                "guardrail": {"type": "rhoLeak", "gain": 6.0, "rhoSumSoft": 3.0, "rhoSumSpan": 8.0}
            },
        },
        {
            "id": "bleed_pMaxNode",
            "label": "bleed_rho_at_pMaxNode",
            "overrides": {
                "guardrail": {
                    "type": "none",
                    "bleed": {
                        "type": "pMax",
                        "applyTo": "rho",
                        "scope": "pMaxNode",
                        "bleedMax": 0.03,
                        "pMaxSoft": 2.0,
                        "pMaxSpan": 6.0,
                    },
                }
            },
        },
        {
            "id": "bleed_rhoSum_topKp",
            "label": "bleed_rho_topKp_by_rhoSum",
            "overrides": {
                "guardrail": {
                    "type": "none",
                    "bleed": {
                        "type": "rhoSum",
                        "applyTo": "rho",
                        "scope": "topKp",
                        "k": 3,
                        "bleedMax": 0.02,
                        "rhoSumSoft": 10,
                        "rhoSumSpan": 20,
                    },
                }
            },
        },
        {
            "id": "combo_pLeak_plus_bleed",
            "label": "pLeak_plus_bleed_p",
            "overrides": {
                "guardrail": {
                    "type": "pLeak",
                    "gain": 6.0,
                    "meanPSoft": 0.003,
                    "meanPSpan": 0.01,
                    "bleed": {
                        "type": "p",
                        "applyTo": "p",
                        "scope": "global",
                        "bleedMax": 0.02,
                        "meanPSoft": 0.003,
                        "meanPSpan": 0.02,
                    },
                }
            },
        },
    ]

    for t in treatments:
        pair_id = f"omnibus_C_{t['id']}"
        phase_c.extend(
            _make_ab_ba_pair(
                dashboard=args.dashboard,
                base_out_prefix=pair_id,
                base_params=base_params,
                a_overrides=baseline_a,
                b_overrides=t["overrides"],
                meta_common={
                    "phase": "C",
                    "purpose": "counterbalanced_pair",
                    "source": "harness",
                    "pairId": pair_id,
                    "treatment": t["label"],
                },
                timeout_s=float(args.timeout_s),
            )
        )

    # Phase D: long-run endurance template.
    phase_d: list[dict[str, Any]] = [
        _make_command(
            dashboard=args.dashboard,
            out_prefix="omnibus_D_endurance_template",
            params={**base_params, "steps": max(int(args.steps), 20000)},
            dashboard_config=None,
            meta={"phase": "D", "purpose": "endurance_template", "source": "template"},
            timeout_s=float(max(args.timeout_s, 2400.0)),
        )
    ]

    want_phases = {p.strip().upper() for p in str(args.phases).split(",") if p.strip()}

    # Order matters: keep Phase C early so --limit small batches include it.
    ordered: list[tuple[str, list[dict[str, Any]]]] = [
        ("A", phase_a),
        ("C", phase_c),
        ("B", phase_b),
        ("D", phase_d),
    ]

    generated: list[dict[str, Any]] = []
    for key, items in ordered:
        if key in want_phases:
            generated.extend(items)

    # Apply safety cap.
    if args.limit > 0:
        generated = generated[: int(args.limit)]

    # Write commands.
    for idx, cmd in enumerate(generated, start=1):
        fname = f"{idx:04d}_{cmd['outPrefix']}.json"
        _write_json(batch.queue / fname, cmd)
        commands_written.append(str((batch.queue / fname).resolve()))

    # Manifest.
    theory_map: list[dict[str, Any]] = []
    if theory:
        for sym in theory.symbols:
            mapped = _map_theory_symbol_to_impl(sym)
            theory_map.append(
                {
                    "symbol": sym,
                    "hits": theory.raw_hits.get(sym, 0),
                    "mappedTo": mapped,
                    "presentInDashboardConfig": mapped in {".".join(p) for p, _ in _iter_leaf_paths(app_config)} if mapped else False,
                }
            )

    manifest = {
        "generatedAt": datetime.now().isoformat(),
        "dashboard": args.dashboard,
        "pdf": str(pdf_path) if pdf_path.exists() else None,
        "commandQueue": str(batch.queue.resolve()),
        "commandCount": len(commands_written),
        "phases": sorted(want_phases),
        "phaseOrder": [k for k, _ in ordered if k in want_phases],
        "harnessDefaults": base_params,
        "dashboardConfigSweepSpecs": [
            {
                "path": ".".join(s.path),
                "default": s.default,
                "values": s.values,
                "reason": s.reason,
            }
            for s in specs
        ],
        "phaseCDesign": {
            "baselineA": baseline_a,
            "treatments": treatments,
            "note": "Phase C is AB/BA counterbalanced pairs over harness params (guardrail/bleed).",
        },
        "theoryInventory": dataclasses.asdict(theory) if theory else None,
        "theoryMapping": theory_map,
    }
    _write_json(batch.manifest, manifest)

    print(f"Wrote {len(commands_written)} command file(s) to: {batch.queue}")
    print(f"Wrote manifest: {batch.manifest}")
    if not args.enqueue:
        print("(Staged batch; move files into solData/testResults/command_queue when ready.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
