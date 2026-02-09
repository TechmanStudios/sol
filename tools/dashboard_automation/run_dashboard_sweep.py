"""Run SOL dashboard JS experiments in Firefox Developer Edition.

This script drives the browser via Selenium, injects SOL experiment scripts,
executes them, and ensures CSV downloads land in solData/ for agent pickup.

Usage examples:
    python tools/dashboard_automation/run_dashboard_sweep.py --dashboard sol_dashboard_v3_7_2.html --firefox-dev
  python tools/dashboard_automation/run_dashboard_sweep.py --duration-min 30 --auto

Notes:
- Firefox (Dev Edition) cannot be forced by in-page JS to save to an arbitrary
  folder. The reliable approach is to set the browser profile download dir.
- If you run manually (no automation), set Firefox's Downloads folder to solData.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def _auto_detect_firefox_dev_binary() -> str:
    if os.name != "nt":
        return ""

    candidates = [
        r"C:\Program Files\Firefox Developer Edition\firefox.exe",
        r"C:\Program Files (x86)\Firefox Developer Edition\firefox.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:  # noqa: N802
        # Some browsers request /favicon.ico by default; avoid noisy 404 stack traces.
        if self.path.rstrip("/") == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        super().do_GET()


@dataclass(frozen=True)
class RunResult:
    summary_csv: Path
    trace_csv: Path


@dataclass(frozen=True)
class AutoMapResult:
    summary_csv: Path
    trace_csv: Path
    manifest_json: Path


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    message: str
    dashboard: str
    runs: int
    outputs: list[dict[str, str]]


def _start_server(root: Path, port: int) -> ThreadingHTTPServer:
    handler = lambda *a, **kw: _QuietHandler(*a, directory=str(root), **kw)  # type: ignore[misc]
    httpd: ThreadingHTTPServer = ThreadingHTTPServer(("127.0.0.1", port), handler)

    t = threading.Thread(target=httpd.serve_forever, name="sol-dashboard-http", daemon=True)
    t.start()
    return httpd


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _list_csv_files(folder: Path) -> set[Path]:
    return {p for p in folder.glob("*.csv") if p.is_file()}


def _list_download_files(folder: Path) -> set[Path]:
    out: set[Path] = set()
    for ext in ("*.csv", "*.json"):
        out |= {p for p in folder.glob(ext) if p.is_file()}
    return out


def _list_command_files(command_dir: Path) -> list[Path]:
    if not command_dir.exists():
        return []
    # Process oldest first for deterministic behavior.
    return sorted(
        [p for p in command_dir.glob("*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
    )


def _requeue_stale_processing_files(command_dir: Path, *, stale_s: float) -> int:
    """Move orphaned *.json.processing files back into the queue.

    Commands are "locked" for processing by renaming <name>.json -> <name>.json.processing.
    If the runner crashes after that rename, the command can be stranded forever.

    This function conservatively requeues only those processing files older than stale_s.
    """
    if stale_s <= 0 or not command_dir.exists():
        return 0

    now = time.time()
    moved = 0
    for processing in sorted(command_dir.glob("*.json.processing")):
        try:
            if not processing.is_file():
                continue
            age_s = now - processing.stat().st_mtime
            if age_s < stale_s:
                continue

            stem = processing.name
            if stem.endswith(".processing"):
                stem = stem[: -len(".processing")]
            if stem.endswith(".json"):
                stem = stem[: -len(".json")]

            stamp = time.strftime("%Y%m%d_%H%M%S")
            base = f"{stem}_requeued_{stamp}"
            candidate = command_dir / f"{base}.json"
            suffix_i = 1
            while candidate.exists():
                candidate = command_dir / f"{base}_{suffix_i}.json"
                suffix_i += 1

            processing.replace(candidate)
            moved += 1
            print(
                f"[run_dashboard_sweep] Requeued stale command: {processing.name} -> {candidate.name} (age={age_s:.0f}s)"
            )
        except Exception as e:
            print(f"[run_dashboard_sweep] Failed to requeue {processing.name}: {e}")
    return moved


def _wait_for_new_downloads(
    folder: Path,
    before: set[Path],
    expected_count: int,
    timeout_s: float,
) -> list[Path]:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        now = _list_csv_files(folder)
        new = sorted(now - before, key=lambda p: p.stat().st_mtime)

        # Firefox writes partial downloads as *.part
        partials = list(folder.glob("*.part"))
        if len(new) >= expected_count and not partials:
            return new

        time.sleep(0.25)

    now = _list_csv_files(folder)
    new = sorted(now - before, key=lambda p: p.stat().st_mtime)
    raise TimeoutError(
        f"Timed out waiting for {expected_count} CSV downloads in {folder}. "
        f"Got {len(new)} new CSV(s)."
    )


def _wait_for_new_files(
    folder: Path,
    before: set[Path],
    expected_count: int,
    timeout_s: float,
) -> list[Path]:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        now = _list_download_files(folder)
        new = sorted(now - before, key=lambda p: p.stat().st_mtime)

        partials = list(folder.glob("*.part"))
        if len(new) >= expected_count and not partials:
            return new

        time.sleep(0.25)

    now = _list_download_files(folder)
    new = sorted(now - before, key=lambda p: p.stat().st_mtime)
    raise TimeoutError(
        f"Timed out waiting for {expected_count} download(s) in {folder}. "
        f"Got {len(new)} new file(s)."
    )


def _build_sweep_params(
    out_prefix: str,
    overrides_json: str | None,
    overrides_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"outPrefix": out_prefix}
    if overrides_json:
        extra = json.loads(overrides_json)
        if not isinstance(extra, dict):
            raise ValueError("--params-json must be a JSON object")
        params.update(extra)
    if overrides_dict:
        params.update(overrides_dict)
    return params


def _run_sweep(driver: Any, params: dict[str, Any]) -> dict[str, Any]:
    # Avoid returning full trace arrays (can be huge). Return only counts.
    script = r"""
const params = arguments[0];
const done = arguments[arguments.length - 1];
(async () => {
  try {
    if (!window.solMechanismTraceSweepV1) {
      throw new Error('solMechanismTraceSweepV1 not installed');
    }
        const api = window.solMechanismTraceSweepV1;
        const fn = (typeof api.run === 'function')
            ? api.run
            : (typeof api.mechanismTraceSweep === 'function')
                ? api.mechanismTraceSweep
                : null;
        if (!fn) {
            throw new Error('solMechanismTraceSweepV1 has no run() or mechanismTraceSweep()');
        }
        const out = await fn.call(api, params);
    const summaryCount = Array.isArray(out?.summaryRows) ? out.summaryRows.length : null;
    const traceCount = Array.isArray(out?.traceRows) ? out.traceRows.length : null;
    done({ ok: true, summaryCount, traceCount });
  } catch (e) {
    done({ ok: false, error: (e && e.message) ? e.message : String(e) });
  }
})();
"""
    return driver.execute_async_script(script, params)


def _install_script_tag(driver: Any, *, src: str, element_id: str) -> None:
        driver.execute_script(
                """
(function(src, id) {
    if (document.getElementById(id)) return;
    const s = document.createElement('script');
    s.id = id;
    s.src = src + '?ts=' + Date.now();
    document.head.appendChild(s);
})(arguments[0], arguments[1]);
""",
                src,
                element_id,
        )


def _run_auto_map_plan(driver: Any, plan: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("_run_auto_map_plan no longer supports execute_async_script. Use _run_auto_map_plan_job().")


def _run_auto_map_plan_job(driver: Any, plan: dict[str, Any], *, timeout_s: float) -> dict[str, Any]:
    job_key = f"__solAutoMapPlanJob__{int(time.time() * 1000)}__{os.getpid()}"

    start_script = r"""
const plan = arguments[0];
const jobKey = arguments[1];

if (!window.solAutoMap) throw new Error('solAutoMap not installed');
if (typeof window.solAutoMap.runPlan !== 'function') throw new Error('solAutoMap.runPlan not available');

window[jobKey] = {
  done: false,
  ok: false,
  error: null,
  summaryCount: null,
  traceCount: null,
  planName: String(plan?.planName || '')
};

Promise.resolve()
  .then(() => window.solAutoMap.runPlan(plan))
  .then((out) => {
    const summaryCount = Array.isArray(out?.summaryRows) ? out.summaryRows.length : null;
    const traceCount = Array.isArray(out?.traceRows) ? out.traceRows.length : null;
    window[jobKey].done = true;
    window[jobKey].ok = true;
    window[jobKey].summaryCount = summaryCount;
    window[jobKey].traceCount = traceCount;
  })
  .catch((e) => {
    window[jobKey].done = true;
    window[jobKey].ok = false;
    window[jobKey].error = (e && e.message) ? e.message : String(e);
  });

return true;
"""

    poll_script = r"""
const jobKey = arguments[0];
const s = window[jobKey];
if (!s) return { done: true, ok: false, error: 'job state missing' };
return {
  done: !!s.done,
  ok: !!s.ok,
  error: s.error || null,
  summaryCount: (s.summaryCount ?? null),
  traceCount: (s.traceCount ?? null),
  planName: s.planName || ''
};
"""

    cleanup_script = r"""
const jobKey = arguments[0];
try { delete window[jobKey]; } catch (_) {}
return true;
"""

    driver.execute_script(start_script, plan, job_key)

    t0 = time.time()
    last = None
    try:
        while time.time() - t0 < float(timeout_s):
            last = driver.execute_script(poll_script, job_key)
            if isinstance(last, dict) and last.get("done"):
                return last
            time.sleep(1.0)
    finally:
        try:
            driver.execute_script(cleanup_script, job_key)
        except Exception:
            pass

    raise TimeoutError(f"Timed out waiting for solAutoMap.runPlan to complete after {timeout_s}s")


def _run_auto_map_master(driver: Any, master_plan: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(
            "_run_auto_map_master no longer supports execute_async_script. Use _run_auto_map_master_job()."
        )


def _run_auto_map_master_job(driver: Any, master_plan: dict[str, Any], *, timeout_s: float) -> dict[str, Any]:
    job_key = f"__solAutoMapMasterJob__{int(time.time() * 1000)}__{os.getpid()}"

    start_script = r"""
const masterPlan = arguments[0];
const jobKey = arguments[1];

if (!window.solAutoMap) throw new Error('solAutoMap not installed');
if (typeof window.solAutoMap.runMaster !== 'function') throw new Error('solAutoMap.runMaster not available');

window[jobKey] = {
  done: false,
  ok: false,
  error: null,
  summaryCount: null,
  traceCount: null,
  masterName: String(masterPlan?.masterName || masterPlan?.planName || '')
};

Promise.resolve()
  .then(() => window.solAutoMap.runMaster(masterPlan))
  .then((out) => {
    const summaryCount = Array.isArray(out?.masterSummaryRows) ? out.masterSummaryRows.length : null;
    const traceCount = Array.isArray(out?.masterTraceRows) ? out.masterTraceRows.length : null;
    window[jobKey].done = true;
    window[jobKey].ok = true;
    window[jobKey].summaryCount = summaryCount;
    window[jobKey].traceCount = traceCount;
  })
  .catch((e) => {
    window[jobKey].done = true;
    window[jobKey].ok = false;
    window[jobKey].error = (e && e.message) ? e.message : String(e);
  });

return true;
"""

    poll_script = r"""
const jobKey = arguments[0];
const s = window[jobKey];
if (!s) return { done: true, ok: false, error: 'job state missing' };
return {
  done: !!s.done,
  ok: !!s.ok,
  error: s.error || null,
  summaryCount: (s.summaryCount ?? null),
  traceCount: (s.traceCount ?? null),
  masterName: s.masterName || ''
};
"""

    cleanup_script = r"""
const jobKey = arguments[0];
try { delete window[jobKey]; } catch (_) {}
return true;
"""

    driver.execute_script(start_script, master_plan, job_key)

    t0 = time.time()
    last = None
    try:
        while time.time() - t0 < float(timeout_s):
            last = driver.execute_script(poll_script, job_key)
            if isinstance(last, dict) and last.get("done"):
                return last
            time.sleep(2.0)
    finally:
        try:
            driver.execute_script(cleanup_script, job_key)
        except Exception:
            pass

    raise TimeoutError(f"Timed out waiting for solAutoMap.runMaster to complete after {timeout_s}s")


def _apply_dashboard_config(driver: Any, dashboard_config: dict[str, Any]) -> None:
    if not dashboard_config:
        return

    script = r"""
const cfg = arguments[0];

function isPlainObject(x) {
    return !!x && typeof x === 'object' && !Array.isArray(x);
}

function deepMerge(target, source) {
    if (!isPlainObject(target) || !isPlainObject(source)) return;
    for (const [k, v] of Object.entries(source)) {
        if (isPlainObject(v)) {
            if (!isPlainObject(target[k])) target[k] = {};
            deepMerge(target[k], v);
        } else {
            target[k] = v;
        }
    }
}

const app = window.SOLDashboard;
if (!app || !app.config) {
    throw new Error('SOLDashboard.config not available (dashboard not ready)');
}

deepMerge(app.config, cfg);
return true;
"""

    driver.execute_script(script, dashboard_config)


def _parse_float_pair_csv(raw: str) -> tuple[float, float]:
        parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
        if len(parts) != 2:
                raise ValueError("Expected two comma-separated floats")
        return float(parts[0]), float(parts[1])


def _probe_damping_quantization(
        driver: Any,
        *,
        dt: float,
        damping_a: float,
        damping_b: float,
        node_id: int,
        rho0: float,
) -> dict[str, Any]:
        script = r"""
const dt = arguments[0];
const a = arguments[1];
const b = arguments[2];
const nodeId = arguments[3];
const rho0 = arguments[4];

try {
    const app = window.SOLDashboard;
    if (!app || !app.state || !app.state.physics) {
        return { ok: false, error: 'SOLDashboard.state.physics not available' };
    }

    const slider = (app.dom && app.dom.dampSlider) || document.getElementById('dampSlider');
    const sliderInfo = slider ? {
        step: slider.step,
        min: slider.min,
        max: slider.max,
        value: slider.value,
        valueAsNumber: slider.valueAsNumber
    } : null;

    function setAndRead(val) {
        if (!slider) return null;
        slider.value = String(val);
        return {
            set: String(val),
            afterValue: slider.value,
            afterNumber: slider.valueAsNumber
        };
    }

    const setA = setAndRead(a);
    const setB = setAndRead(b);

    function dampingOnlyStep(damp) {
        if (!app.sim || typeof app.sim.createPhysics !== 'function') {
            throw new Error('SOLDashboard.sim.createPhysics not available');
        }
        const p = app.sim.createPhysics();

        // Isolate damping: ensure p=0 by using c_press=0.
        for (const n of (p.nodes || [])) {
            n.rho = 0;
            n.p = 0;
            n.isStellar = false;
            n.isConstellation = false;
        }
        const target = (p.nodeById && p.nodeById.get(nodeId)) || (p.nodes && p.nodes[0]);
        if (!target) throw new Error('No nodes available for probe');
        target.rho = rho0;
        p.step(dt, 0, damp);
        return {
            damp,
            rhoAfter: target.rho
        };
    }

    const outA = dampingOnlyStep(a);
    const outB = dampingOnlyStep(b);
    return {
        ok: true,
        sliderInfo,
        sliderSetA: setA,
        sliderSetB: setB,
        dampingOnly: {
            dt,
            nodeId,
            rho0,
            a: outA,
            b: outB,
            rhoDiff_b_minus_a: (outB.rhoAfter - outA.rhoAfter)
        }
    };
} catch (e) {
    return { ok: false, error: (e && e.message) ? e.message : String(e) };
}
"""
        return driver.execute_script(script, float(dt), float(damping_a), float(damping_b), int(node_id), float(rho0))


def _load_command(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Command JSON must be an object")
    return data


def _normalize_dashboard_path(sol_root: Path, dashboard: str) -> Path:
    p = (sol_root / dashboard).resolve()
    try:
        p.relative_to(sol_root)
    except Exception as e:
        raise ValueError(f"Dashboard must live under {sol_root}: {dashboard}") from e
    if not p.exists():
        raise FileNotFoundError(f"Dashboard not found: {p}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard",
        default="sol_dashboard_v3_7_2.html",
        help="Dashboard HTML file under the sol/ folder (served over localhost).",
    )
    ap.add_argument(
        "--download-dir",
        default=str(Path(__file__).resolve().parents[2] / "solData" / "testResults"),
        help="Where CSV downloads should land (default: solData/testResults/).",
    )
    ap.add_argument(
        "--firefox-binary",
        default=os.environ.get("FIREFOX_BINARY") or "",
        help="Path to Firefox binary. Use for Firefox Developer Edition.",
    )
    ap.add_argument(
        "--firefox-dev",
        action="store_true",
        help="Convenience flag: uses FIREFOX_DEV_EXE env var if set.",
    )
    ap.add_argument(
        "--headless",
        action="store_true",
        help="Run Firefox headless (useful for unattended runs).",
    )
    ap.add_argument(
        "--out-prefix",
        default="sol_mechSweep",
        help="CSV filename prefix.",
    )
    ap.add_argument(
        "--params-json",
        default="",
        help='JSON object merged into sweep params. Example: {"steps":2000}',
    )
    ap.add_argument(
        "--duration-min",
        type=float,
        default=0.0,
        help="If >0, keep running sweeps until this many minutes elapse.",
    )
    ap.add_argument(
        "--auto",
        action="store_true",
        help="If set, run immediately (non-interactive).",
    )
    ap.add_argument(
        "--browser-retries",
        type=int,
        default=2,
        help="Retries per run when the browser connection drops (e.g., WinError 10054).",
    )

    ap.add_argument(
        "--watch-commands",
        action="store_true",
        help=(
            "Watch a folder for JSON command files and execute them. "
            "This is the recommended mode for agent-driven runs."
        ),
    )
    ap.add_argument(
        "--run-command-dir",
        default="",
        help=(
            "Process all *.json command files found in a folder once, then exit. "
            "Uses one Firefox session (recommended for staged batches like Phase C)."
        ),
    )
    ap.add_argument(
        "--command-file",
        default="",
        help=(
            "Run a single command JSON file then exit. "
            "The file will be archived to command_done and a result JSON written to command_results."
        ),
    )
    ap.add_argument(
        "--command-dir",
        default="",
        help="Folder to watch for command JSON files (default: <download-dir>/command_queue).",
    )
    ap.add_argument(
        "--command-done-dir",
        default="",
        help="Where to move processed commands (default: <download-dir>/command_done).",
    )
    ap.add_argument(
        "--command-results-dir",
        default="",
        help="Where to write command results JSON (default: <download-dir>/command_results).",
    )
    ap.add_argument(
        "--poll-s",
        type=float,
        default=1.0,
        help="Polling interval for --watch-commands.",
    )
    ap.add_argument(
        "--requeue-stale-processing-s",
        type=float,
        default=3600.0,
        help=(
            "On startup, move orphaned *.json.processing files back into the command queue if their last-write time is older "
            "than this many seconds (default: 3600). Set to 0 to disable."
        ),
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=600.0,
        help="Timeout for a single sweep + downloads.",
    )

    ap.add_argument(
        "--auto-map-pack",
        default="",
        help=(
            "Optional: path to SOL Auto Mapper pack JS (sol_auto_mapper_pack.js). "
            "Used by sol.dashboard.auto_map.v1 commands when packPath is not provided."
        ),
    )

    ap.add_argument(
        "--startup-timeout-s",
        type=float,
        default=180.0,
        help="Timeout for initial dashboard load + JS injection (seconds).",
    )

    ap.add_argument(
        "--probe-damping-quantization",
        action="store_true",
        help=(
            "Run a small diagnostic after the dashboard loads to check whether the UI damping slider "
            "snaps/quantizes values and whether physics.step is sensitive to tiny damping differences."
        ),
    )
    ap.add_argument(
        "--probe-only",
        action="store_true",
        help="Exit immediately after running any requested probes (no sweeps / no command processing).",
    )
    ap.add_argument(
        "--probe-damping-values",
        default="1.869131155,1.86913118",
        help="Comma-separated damping pair to probe (A,B).",
    )
    ap.add_argument(
        "--probe-dt",
        type=float,
        default=0.16,
        help="dt used for probe step.",
    )
    ap.add_argument(
        "--probe-node-id",
        type=int,
        default=64,
        help="Node id used for damping-only probe (on a fresh physics instance).",
    )
    ap.add_argument(
        "--probe-rho0",
        type=float,
        default=1_000_000.0,
        help="Initial rho used for damping-only probe.",
    )

    args = ap.parse_args()

    sol_root = Path(__file__).resolve().parents[2]
    dashboard_path = _normalize_dashboard_path(sol_root, args.dashboard)

    download_dir = Path(args.download_dir).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    command_dir = Path(args.command_dir).resolve() if args.command_dir else (download_dir / "command_queue")
    command_done_dir = (
        Path(args.command_done_dir).resolve() if args.command_done_dir else (download_dir / "command_done")
    )
    command_results_dir = (
        Path(args.command_results_dir).resolve() if args.command_results_dir else (download_dir / "command_results")
    )
    if args.watch_commands or args.command_file or args.run_command_dir:
        command_dir.mkdir(parents=True, exist_ok=True)
        command_done_dir.mkdir(parents=True, exist_ok=True)
        command_results_dir.mkdir(parents=True, exist_ok=True)

    # Recover stranded commands from prior crashes (only in queue-processing modes).
    if args.watch_commands or args.run_command_dir:
        _requeue_stale_processing_files(command_dir, stale_s=float(args.requeue_stale_processing_s))

    firefox_binary = args.firefox_binary
    if args.firefox_dev:
        firefox_binary = os.environ.get("FIREFOX_DEV_EXE", firefox_binary)
        if not firefox_binary:
            firefox_binary = _auto_detect_firefox_dev_binary()
        if not firefox_binary:
            raise SystemExit(
                "--firefox-dev was set but Firefox Developer Edition was not found. "
                "Set env var FIREFOX_DEV_EXE to your Dev Edition firefox.exe, or pass --firefox-binary."
            )

    # Lazy import so reading this file doesn't require selenium.
    from selenium import webdriver
    from selenium.webdriver.common.by import By  # noqa: F401
    from selenium.common.exceptions import WebDriverException, TimeoutException
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.support.ui import WebDriverWait

    port = _find_free_port()
    httpd = _start_server(sol_root, port)

    try:
        def dashboard_url(dashboard_path_: Path) -> str:
            return (
                f"http://127.0.0.1:{port}/{dashboard_path_.relative_to(sol_root).as_posix()}"
                "?automation=1"
            )

        def asset_url(asset_path_: Path) -> str:
            return f"http://127.0.0.1:{port}/{asset_path_.relative_to(sol_root).as_posix()}"

        url = dashboard_url(dashboard_path)

        options = Options()
        if firefox_binary:
            options.binary_location = firefox_binary
        if args.headless:
            options.add_argument("-headless")

        # Force downloads into solData.
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", str(download_dir))
        options.set_preference("browser.download.useDownloadDir", True)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.manager.focusWhenStarting", False)
        options.set_preference("browser.download.alwaysOpenPanel", False)
        options.set_preference("browser.download.panel.shown", False)
        options.set_preference("pdfjs.disabled", True)

        # Avoid download prompts for CSV.
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk",
            ",".join(
                [
                    "text/csv",
                    "application/csv",
                    "application/octet-stream",
                    "application/json",
                    "text/plain",
                ]
            ),
        )
        options.set_preference("browser.helperApps.neverAsk.openFile", "")

        # Some dashboard dependencies can be heavy (e.g., vis-network). If the host
        # machine is under load, Firefox can abort long-running scripts.
        # Increase the limit to reduce flakiness during automation.
        # 0 disables the timeout.
        options.set_preference("dom.max_script_run_time", 0)
        options.set_preference("dom.max_chrome_script_run_time", 0)

        geckodriver_log = download_dir / "geckodriver.log"
        service = Service(log_output=str(geckodriver_log))

        def _start_driver():
            try:
                return webdriver.Firefox(options=options, service=service)
            except WebDriverException as e:
                raise SystemExit(
                    "Failed to start Firefox WebDriver. Common causes: Firefox binary path invalid, "
                    "Firefox not installed, or geckodriver/firefox mismatch. "
                    f"Binary={firefox_binary!r}. geckodriver_log={geckodriver_log}. Error={e}"
                )

        def _is_transient_browser_error(e: BaseException) -> bool:
            msg = str(e)[:4000]
            needles = [
                "WinError 10054",
                "ConnectionResetError",
                "forcibly closed by the remote host",
                "disconnected",
                "Failed to decode response",
                "invalid session id",
            ]
            return any(n in msg for n in needles) or isinstance(e, WebDriverException)

        driver = _start_driver()

        try:
            wait = WebDriverWait(driver, 60)

            def ensure_dashboard_ready(dashboard_path_: Path) -> None:
                try:
                    driver.get(dashboard_url(dashboard_path_))

                    # In WebDriver sessions, DOMContentLoaded timing can be flaky if the
                    # page is still settling. App.init is idempotent (dashboard sets
                    # window.__SOL_INIT_DONE__), so it's safe to invoke explicitly.
                    try:
                        driver.execute_script(
                            """
try {
  if (window.SOLDashboard && typeof window.SOLDashboard.init === 'function') {
    window.SOLDashboard.init();
  }
} catch (e) {
  try { window.__SOL_INIT_ERROR__ = String(e && (e.stack || e)); } catch (_) {}
}
"""
                        )
                    except WebDriverException:
                        # If the browser is mid-navigation, just rely on the wait below.
                        pass

                    def _probe(d):
                        return d.execute_script(
                            """
return {
  readyState: document.readyState,
  hasApp: !!window.SOLDashboard,
  initDone: !!window.__SOL_INIT_DONE__,
  initError: (window.__SOL_INIT_ERROR__ || null),
  hasPhysics: !!(window.SOLDashboard
    && window.SOLDashboard.state
    && window.SOLDashboard.state.physics
    && Array.isArray(window.SOLDashboard.state.physics.nodes)
    && typeof window.SOLDashboard.state.physics.step === 'function')
};
"""
                        )

                    def _wait_for_physics(d):
                        try:
                            p = _probe(d) or {}
                        except WebDriverException:
                            return False
                        if p.get("initError"):
                            raise RuntimeError(f"Dashboard App.init failed: {p.get('initError')}")
                        return bool(p.get("hasPhysics"))

                    try:
                        WebDriverWait(driver, float(args.startup_timeout_s)).until(_wait_for_physics)
                    except TimeoutException:
                        try:
                            p = _probe(driver) or {}
                        except WebDriverException as e:
                            p = {"probeError": str(e)}
                        raise RuntimeError(
                            "Timed out waiting for SOLDashboard physics to initialize. "
                            f"probe={p} url={dashboard_url(dashboard_path_)}"
                        )

                    # Load the sweep harness as a script tag from our local server.
                    # This is more reliable than pushing a large script payload via
                    # execute_script (which can be flaky in some Marionette sessions).
                    harness_src = asset_url(sol_root / "solEngine" / "mechanismTraceSweep_v1.js")
                    driver.execute_script(
                        """
(function(src) {
  const id = '__sol_mech_trace_sweep_v1__';
  if (document.getElementById(id)) return;
  const s = document.createElement('script');
  s.id = id;
  s.src = src + '?ts=' + Date.now();
  document.head.appendChild(s);
})(arguments[0]);
""",
                        harness_src,
                    )
                    WebDriverWait(driver, float(args.startup_timeout_s)).until(
                        lambda d: d.execute_script("return !!window.solMechanismTraceSweepV1")
                    )
                except WebDriverException as e:
                    raise RuntimeError(
                        "Browser connection dropped while loading dashboard or injecting sweep JS. "
                        f"Binary={firefox_binary!r}. url={dashboard_url(dashboard_path_)}. "
                        f"geckodriver_log={geckodriver_log}. Error={e}"
                    )

            ensure_dashboard_ready(dashboard_path)

            if args.probe_damping_quantization:
                try:
                    a, b = _parse_float_pair_csv(str(args.probe_damping_values))
                    report = _probe_damping_quantization(
                        driver,
                        dt=float(args.probe_dt),
                        damping_a=float(a),
                        damping_b=float(b),
                        node_id=int(args.probe_node_id),
                        rho0=float(args.probe_rho0),
                    )
                    print("\n=== DAMPING QUANTIZATION PROBE ===")
                    print(json.dumps(report, indent=2, sort_keys=True))
                    print("=== END PROBE ===\n")
                except Exception as e:
                    print("\n=== DAMPING QUANTIZATION PROBE (FAILED) ===")
                    print(str(e))
                    print("=== END PROBE ===\n")

            if args.probe_only:
                return 0

            def do_one_run(params: dict[str, Any], timeout_s: float) -> RunResult:
                before = _list_csv_files(download_dir)

                # Browser connection can drop transiently during long batches.
                # Retry by restarting the WebDriver and re-injecting the harness.
                retries = max(0, int(args.browser_retries))
                last_err: Exception | None = None
                nonlocal driver
                for attempt in range(retries + 1):
                    try:
                        out = _run_sweep(driver, params)
                        if not out.get("ok"):
                            raise RuntimeError(out.get("error") or "Unknown sweep error")
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        if attempt >= retries or not _is_transient_browser_error(e):
                            raise
                        print(f"[run_dashboard_sweep] Browser dropped; restarting WebDriver (attempt {attempt+1}/{retries})")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = _start_driver()
                        ensure_dashboard_ready(dashboard_path)

                new_csvs = _wait_for_new_downloads(
                    download_dir,
                    before,
                    expected_count=2,
                    timeout_s=timeout_s,
                )

                # Heuristic: file names end with *_summary_* and *_trace_*
                summary = next((p for p in new_csvs if "_summary_" in p.name), None)
                trace = next((p for p in new_csvs if "_trace_" in p.name), None)

                if not summary or not trace:
                    # Fall back to ordering.
                    if len(new_csvs) >= 2:
                        summary, trace = new_csvs[-2], new_csvs[-1]
                    else:
                        raise RuntimeError("Expected two CSV downloads (summary+trace), but did not find them")

                return RunResult(summary_csv=summary, trace_csv=trace)

            def run_command(cmd_path: Path) -> CommandResult:
                nonlocal driver
                processing = cmd_path.with_suffix(cmd_path.suffix + ".processing")
                try:
                    cmd_path.replace(processing)
                except Exception:
                    # Another process might have grabbed it.
                    return CommandResult(ok=False, message="Could not lock command file", dashboard="", runs=0, outputs=[])

                try:
                    cmd = _load_command(processing)
                    kind = str(cmd.get("kind") or "")
                    if kind and kind not in {
                        "sol.dashboard.sweep.v1",
                        "sol.dashboard.auto_map.v1",
                        "sol.dashboard.auto_map_master.v1",
                        "sol.dashboard.smoke.v1",
                    }:
                        raise ValueError(f"Unsupported command kind: {kind}")

                    dashboard = str(cmd.get("dashboard") or args.dashboard)
                    dashboard_p = _normalize_dashboard_path(sol_root, dashboard)
                    ensure_dashboard_ready(dashboard_p)

                    out_prefix = str(cmd.get("outPrefix") or args.out_prefix)
                    params_overrides = cmd.get("params")
                    if params_overrides is not None and not isinstance(params_overrides, dict):
                        raise ValueError("Command field 'params' must be an object")

                    dashboard_cfg = cmd.get("dashboardConfig")
                    if dashboard_cfg is not None and not isinstance(dashboard_cfg, dict):
                        raise ValueError("Command field 'dashboardConfig' must be an object")

                    runs = int(cmd.get("runs") or 1)
                    if runs < 1:
                        raise ValueError("Command field 'runs' must be >= 1")

                    timeout_s = float(cmd.get("timeoutS") or args.timeout_s)

                    outputs: list[dict[str, str]] = []

                                        if kind == "sol.dashboard.smoke.v1":
                                                # UI-neutral smoke test: validate that the dashboard booted,
                                                # physics is present, and step() executes a few times.
                                                smoke = cmd.get("smoke")
                                                if smoke is not None and not isinstance(smoke, dict):
                                                        raise ValueError("Command field 'smoke' must be an object for sol.dashboard.smoke.v1")
                                                smoke = smoke or {}

                                                steps = int(smoke.get("steps") or 3)
                                                steps = max(1, min(steps, 5000))
                                                dt = float(smoke.get("dt") or 0.12)
                                                press_c = float(smoke.get("pressureC") or 20.0)
                                                damping = float(smoke.get("damping") or 4.0)

                                                if dashboard_cfg:
                                                        _apply_dashboard_config(driver, dashboard_cfg)

                                                # One run == one smoke execution + report.
                                                for _ in range(runs):
                                                        report = driver.execute_script(
                                                                """
function safe(x){ return (Number.isFinite(x) ? x : 0); }

try {
    if (window.SOLDashboard && typeof window.SOLDashboard.init === 'function') {
        window.SOLDashboard.init();
    }
} catch (e) {
    try { window.__SOL_INIT_ERROR__ = String(e && (e.stack || e)); } catch (_) {}
}

const err = (window.__SOL_INIT_ERROR__ || null);
if (err) return { ok:false, stage:'init', error: String(err) };

const phy = window.SOLDashboard && window.SOLDashboard.state && window.SOLDashboard.state.physics;
if (!phy || !Array.isArray(phy.nodes) || !Array.isArray(phy.edges) || typeof phy.step !== 'function') {
    return { ok:false, stage:'probe', error:'physics not ready', hasSOLDashboard:!!window.SOLDashboard };
}

// Best-effort stepping (supports historical step signatures).
function stepOnce(dt, pressC, damping) {
    try { phy.step(dt, pressC, damping); return true; } catch (e) {}
    try { phy.step(dt); return true; } catch (e) {}
    try { phy.step(); return true; } catch (e) {}
    return false;
}

let okSteps = 0;
for (let i = 0; i < arguments[0]; i++) {
    if (!stepOnce(arguments[1], arguments[2], arguments[3])) {
        return { ok:false, stage:'step', error:'physics.step failed', i };
    }
    okSteps++;
}

let rhoSum = 0;
let rhoMax = -Infinity;
for (const n of phy.nodes) {
    const r = safe(n && n.rho);
    rhoSum += r;
    if (r > rhoMax) rhoMax = r;
}

return {
    ok: true,
    stage: 'done',
    nodes: phy.nodes.length,
    edges: phy.edges.length,
    okSteps,
    rhoSum,
    rhoMax
};
""",
                                                                steps,
                                                                dt,
                                                                press_c,
                                                                damping,
                                                        )

                                                        if not isinstance(report, dict) or not report.get("ok"):
                                                                raise RuntimeError(f"Smoke failed: {report}")

                                                        outputs.append(
                                                                {
                                                                        "nodes": str(report.get("nodes")),
                                                                        "edges": str(report.get("edges")),
                                                                        "okSteps": str(report.get("okSteps")),
                                                                        "rhoSum": str(report.get("rhoSum")),
                                                                        "rhoMax": str(report.get("rhoMax")),
                                                                }
                                                        )

                                                return CommandResult(ok=True, message="ok", dashboard=dashboard, runs=runs, outputs=outputs)

                    if kind == "sol.dashboard.auto_map.v1":
                        plan = cmd.get("plan")
                        if not isinstance(plan, dict):
                            raise ValueError("Command field 'plan' must be an object for sol.dashboard.auto_map.v1")

                        pack_path_raw = str(cmd.get("packPath") or args.auto_map_pack or "").strip()
                        if not pack_path_raw:
                            raise ValueError(
                                "sol.dashboard.auto_map.v1 requires packPath (or pass --auto-map-pack to run_dashboard_sweep.py)"
                            )
                        pack_path = Path(pack_path_raw).resolve()
                        if not pack_path.exists():
                            raise FileNotFoundError(f"Auto mapper pack not found: {pack_path}")

                        # Serve the pack via the existing localhost server by copying it into solData.
                        auto_assets = (download_dir / "_automation_assets")
                        auto_assets.mkdir(parents=True, exist_ok=True)
                        served_pack = auto_assets / "sol_auto_mapper_pack.js"
                        try:
                            served_pack.write_text(_read_text(pack_path), encoding="utf-8")
                        except Exception as e:
                            raise RuntimeError(f"Failed to stage auto mapper pack: {e}")

                        pack_src = asset_url(served_pack)
                        def ensure_auto_map_ready() -> None:
                            _install_script_tag(driver, src=pack_src, element_id="__sol_auto_mapper_pack__")
                            WebDriverWait(driver, float(args.startup_timeout_s)).until(
                                lambda d: d.execute_script("return !!window.solAutoMap")
                            )
                            if dashboard_cfg:
                                _apply_dashboard_config(driver, dashboard_cfg)

                        ensure_auto_map_ready()

                        retries = max(0, int(args.browser_retries))
                        for _run_idx in range(runs):
                            for attempt in range(retries + 1):
                                try:
                                    before = _list_download_files(download_dir)
                                    out = _run_auto_map_plan_job(driver, plan, timeout_s=timeout_s)
                                    if not out.get("ok"):
                                        raise RuntimeError(out.get("error") or "Unknown auto-map error")

                                    new_files = _wait_for_new_files(
                                        download_dir,
                                        before,
                                        expected_count=3,
                                        timeout_s=timeout_s,
                                    )
                                    break
                                except Exception as e:
                                    if attempt >= retries or not _is_transient_browser_error(e):
                                        raise
                                    print(
                                        f"[run_dashboard_sweep] Browser dropped during auto-map; restarting WebDriver (attempt {attempt+1}/{retries})"
                                    )
                                    try:
                                        driver.quit()
                                    except Exception:
                                        pass
                                    driver = _start_driver()
                                    ensure_dashboard_ready(dashboard_p)
                                    ensure_auto_map_ready()

                            summary = next(
                                (p for p in new_files if p.suffix.lower() == ".csv" and "__summary" in p.name),
                                None,
                            )
                            trace = next(
                                (p for p in new_files if p.suffix.lower() == ".csv" and "__trace" in p.name),
                                None,
                            )
                            manifest = next(
                                (p for p in new_files if p.suffix.lower() == ".json" and "__manifest" in p.name),
                                None,
                            )

                            if not summary or not trace or not manifest:
                                raise RuntimeError(
                                    "Expected 3 downloads (summary.csv, trace.csv, manifest.json) but did not find all artifacts. "
                                    f"got={[p.name for p in new_files]}"
                                )

                            outputs.append(
                                {
                                    "summaryCsv": summary.name,
                                    "traceCsv": trace.name,
                                    "manifestJson": manifest.name,
                                }
                            )

                        return CommandResult(ok=True, message="ok", dashboard=dashboard, runs=runs, outputs=outputs)

                    if kind == "sol.dashboard.auto_map_master.v1":
                        master_plan = cmd.get("masterPlan") or cmd.get("plan")
                        if not isinstance(master_plan, dict):
                            raise ValueError(
                                "Command field 'masterPlan' (or 'plan') must be an object for sol.dashboard.auto_map_master.v1"
                            )

                        sweeps = master_plan.get("sweeps")
                        if not isinstance(sweeps, list) or not sweeps:
                            raise ValueError("masterPlan.sweeps must be a non-empty array")

                        pack_path_raw = str(cmd.get("packPath") or args.auto_map_pack or "").strip()
                        if not pack_path_raw:
                            raise ValueError(
                                "sol.dashboard.auto_map_master.v1 requires packPath (or pass --auto-map-pack to run_dashboard_sweep.py)"
                            )
                        pack_path = Path(pack_path_raw).resolve()
                        if not pack_path.exists():
                            raise FileNotFoundError(f"Auto mapper pack not found: {pack_path}")

                        auto_assets = (download_dir / "_automation_assets")
                        auto_assets.mkdir(parents=True, exist_ok=True)
                        served_pack = auto_assets / "sol_auto_mapper_pack.js"
                        try:
                            served_pack.write_text(_read_text(pack_path), encoding="utf-8")
                        except Exception as e:
                            raise RuntimeError(f"Failed to stage auto mapper pack: {e}")

                        pack_src = asset_url(served_pack)
                        def ensure_auto_map_ready() -> None:
                            _install_script_tag(driver, src=pack_src, element_id="__sol_auto_mapper_pack__")
                            WebDriverWait(driver, float(args.startup_timeout_s)).until(
                                lambda d: d.execute_script("return !!window.solAutoMap")
                            )
                            if dashboard_cfg:
                                _apply_dashboard_config(driver, dashboard_cfg)

                        ensure_auto_map_ready()

                        expected_files = 3 * (len(sweeps) + 1)

                        retries = max(0, int(args.browser_retries))
                        last_err: Exception | None = None
                        new_files: list[Path] | None = None
                        for attempt in range(retries + 1):
                            try:
                                before = _list_download_files(download_dir)
                                out = _run_auto_map_master_job(driver, master_plan, timeout_s=timeout_s)
                                if not out.get("ok"):
                                    raise RuntimeError(out.get("error") or "Unknown auto-map master error")

                                new_files = _wait_for_new_files(
                                    download_dir,
                                    before,
                                    expected_count=expected_files,
                                    timeout_s=timeout_s,
                                )
                                last_err = None
                                break
                            except Exception as e:
                                last_err = e
                                if attempt >= retries or not _is_transient_browser_error(e):
                                    raise
                                print(
                                    f"[run_dashboard_sweep] Browser dropped during auto-map master; restarting WebDriver (attempt {attempt+1}/{retries})"
                                )
                                try:
                                    driver.quit()
                                except Exception:
                                    pass
                                driver = _start_driver()
                                ensure_dashboard_ready(dashboard_p)
                                ensure_auto_map_ready()

                        if new_files is None:
                            raise RuntimeError(str(last_err) if last_err else "auto-map master failed")

                        outputs.append(
                            {
                                "downloadCount": str(len(new_files)),
                                "files": ";".join([p.name for p in new_files]),
                            }
                        )

                        return CommandResult(ok=True, message="ok", dashboard=dashboard, runs=1, outputs=outputs)

                    for _ in range(runs):
                        params = _build_sweep_params(out_prefix, None, overrides_dict=params_overrides)

                        if dashboard_cfg:
                            _apply_dashboard_config(driver, dashboard_cfg)

                        rr = do_one_run(params, timeout_s=timeout_s)
                        outputs.append(
                            {
                                "summaryCsv": rr.summary_csv.name,
                                "traceCsv": rr.trace_csv.name,
                            }
                        )

                    return CommandResult(ok=True, message="ok", dashboard=dashboard, runs=runs, outputs=outputs)

                except Exception as e:
                    return CommandResult(ok=False, message=str(e), dashboard=str(cmd.get("dashboard") or ""), runs=0, outputs=[])

                finally:
                    # Archive processed command (keep record).
                    done_name = processing.name.replace(".processing", "")
                    dest = command_done_dir / done_name
                    try:
                        if processing.exists():
                            processing.replace(dest)
                    except Exception:
                        pass

            if args.command_file:
                cmd_path = Path(args.command_file).resolve()
                res = run_command(cmd_path)
                stamp = time.strftime("%Y%m%d_%H%M%S")
                result_path = command_results_dir / f"{cmd_path.stem}_result_{stamp}.json"
                _write_json(
                    result_path,
                    {
                        "ok": res.ok,
                        "message": res.message,
                        "dashboard": res.dashboard,
                        "runs": res.runs,
                        "outputs": res.outputs,
                    },
                )
                print(f"Processed {cmd_path.name} -> {result_path.name}")

            elif args.run_command_dir:
                run_dir = Path(args.run_command_dir).resolve()
                if not run_dir.exists():
                    raise SystemExit(f"--run-command-dir not found: {run_dir}")

                ran = 0
                failed = 0
                for cmd_path in _list_command_files(run_dir):
                    res = run_command(cmd_path)
                    stamp = time.strftime("%Y%m%d_%H%M%S")
                    result_path = command_results_dir / f"{cmd_path.stem}_result_{stamp}.json"
                    _write_json(
                        result_path,
                        {
                            "ok": res.ok,
                            "message": res.message,
                            "dashboard": res.dashboard,
                            "runs": res.runs,
                            "outputs": res.outputs,
                        },
                    )
                    ran += 1
                    if not res.ok:
                        failed += 1
                    print(f"Processed {cmd_path.name} -> {result_path.name}")

                print(f"Batch complete. commands={ran} failed={failed}")

            elif args.watch_commands:
                print(f"Command queue mode. Watching: {command_dir}")
                print(f"Downloads: {download_dir}")
                print("Drop a JSON file into command_queue to trigger a run.")

                t_end = time.time() + (args.duration_min * 60.0) if args.duration_min > 0 else None
                while True:
                    for cmd_path in _list_command_files(command_dir):
                        res = run_command(cmd_path)
                        stamp = time.strftime("%Y%m%d_%H%M%S")
                        result_path = command_results_dir / f"{cmd_path.stem}_result_{stamp}.json"
                        _write_json(
                            result_path,
                            {
                                "ok": res.ok,
                                "message": res.message,
                                "dashboard": res.dashboard,
                                "runs": res.runs,
                                "outputs": res.outputs,
                            },
                        )
                        print(f"Processed {cmd_path.name} -> {result_path.name}")

                    if t_end is not None and time.time() >= t_end:
                        print("Watch window elapsed; exiting.")
                        break

                    time.sleep(max(0.1, float(args.poll_s)))

            elif args.auto or args.duration_min > 0:
                t_end = time.time() + (args.duration_min * 60.0) if args.duration_min > 0 else None
                run_idx = 0
                while True:
                    run_idx += 1
                    params = _build_sweep_params(args.out_prefix, args.params_json or None)
                    rr = do_one_run(params, timeout_s=args.timeout_s)
                    print(f"Run {run_idx}: {rr.summary_csv.name} ; {rr.trace_csv.name}")
                    if t_end is None:
                        break
                    if time.time() >= t_end:
                        break
            else:
                print("Interactive mode. Commands: run | quit")
                while True:
                    cmd = input("> ").strip().lower()
                    if cmd in {"q", "quit", "exit"}:
                        break
                    if cmd in {"run", "r"}:
                        params = _build_sweep_params(args.out_prefix, args.params_json or None)
                        rr = do_one_run(params, timeout_s=args.timeout_s)
                        print(f"OK: {rr.summary_csv.name} ; {rr.trace_csv.name}")
                        continue
                    print("Unknown command. Try: run | quit")

        finally:
            try:
                driver.quit()
            except Exception:
                pass

    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
