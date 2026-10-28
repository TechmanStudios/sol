from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from .gatekeeper import Gatekeeper
from .judge import Judge
from .memory_store import MemoryStore
from .models import Policy, RunResult, TaskSpec
from .runner import Runner
from .teacher import ReflectiveGeminiTeacher, Teacher


RUNTIME_MODE_PROFILES: dict[str, dict[str, dict]] = {
    "default": {
        "all": {},
        "anchor": {},
    },
    "fast": {
        "all": {
            "steps": 60,
            "reps": 1,
            "metrics_every": 10,
            "baseline": "fresh",
        },
        "anchor": {
            "steps": 100,
            "reps": 1,
            "metrics_every": 10,
            "baseline": "fresh",
        },
    },
    "full": {
        "all": {
            "steps": 220,
            "reps": 2,
            "metrics_every": 5,
            "baseline": "fresh",
        },
        "anchor": {
            "steps": 300,
            "reps": 3,
            "metrics_every": 5,
            "baseline": "fresh",
        },
    },
    "overnight": {
        "all": {
            "steps": 500,
            "reps": 3,
            "metrics_every": 5,
            "baseline": "fresh",
        },
        "anchor": {
            "steps": 900,
            "reps": 4,
            "metrics_every": 5,
            "baseline": "fresh",
        },
    },
}


def _load_tasks(task_file: Path) -> list[TaskSpec]:
    raw = json.loads(task_file.read_text(encoding="utf-8"))
    return [TaskSpec(**row) for row in raw]


def _apply_runtime_mode(tasks: list[TaskSpec], mode: str) -> list[TaskSpec]:
    profile = RUNTIME_MODE_PROFILES.get(mode, RUNTIME_MODE_PROFILES["default"])
    all_overrides = profile.get("all", {})
    anchor_overrides = profile.get("anchor", {})

    profiled_tasks: list[TaskSpec] = []
    for task in tasks:
        payload = dict(task.payload)
        runtime = dict(payload.get("runtime_overrides", {}))

        runtime.update(all_overrides)
        if task.anchor:
            runtime.update(anchor_overrides)

        payload["runtime_overrides"] = runtime
        profiled_tasks.append(
            TaskSpec(
                task_id=task.task_id,
                family=task.family,
                payload=payload,
                anchor=task.anchor,
            )
        )

    return profiled_tasks


def _eval_policy(policy: Policy, tasks: list[TaskSpec], runner: Runner) -> list[RunResult]:
    return [runner.run_task(policy, task) for task in tasks]


def _subset(results: list[RunResult], tasks: list[TaskSpec], anchor: bool) -> list[RunResult]:
    selected_ids = {t.task_id for t in tasks if t.anchor == anchor}
    return [r for r in results if r.task_id in selected_ids]


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def _write_task_diagnostics(gen_dir: Path, results: list[RunResult], prefix: str) -> list[str]:
    diag_dir = gen_dir / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for run in results:
        if run.run_snapshot is None:
            continue
        file_name = f"{prefix}_{_safe_name(run.task_id)}.json"
        out_path = diag_dir / file_name
        out_path.write_text(json.dumps(run.run_snapshot, indent=2), encoding="utf-8")
        written.append(str(out_path))

    return written


def _load_or_init_policy(path: Path, baseline_knobs: dict[str, float]) -> Policy:
    if path.exists():
        return Policy(**json.loads(path.read_text(encoding="utf-8")))
    policy = Policy(policy_id="policy-g000", generation=0, knobs=baseline_knobs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(policy), indent=2), encoding="utf-8")
    return policy


def run_generation_loop(
    config: dict,
    generations: int,
    out_dir: Path,
    mode: str = "default",
    use_reflective_teacher: bool = False,
    live: bool = False,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    active_policy_path = out_dir / "policy_current.json"

    task_file_path = Path(config["task_file"])
    if not task_file_path.exists():
        sol_root = Path(__file__).resolve().parents[3]
        alt_path = sol_root / config["task_file"]
        if alt_path.exists():
            task_file_path = alt_path

    tasks = _apply_runtime_mode(_load_tasks(task_file_path), mode)
    baseline_knobs = dict(config["baseline_knobs"])

    runner = Runner()
    judge = Judge(config["judge_weights"])
    knob_bounds = {k: tuple(v) for k, v in config["knob_bounds"].items()}
    is_reflective = bool(
        use_reflective_teacher
        or config.get("use_reflective_teacher")
        or config.get("teacher_mode") == "reflective"
    )
    is_live = bool(live or config.get("live", False))
    if is_reflective:
        reflective_default_bounds = {
            "damping": (0.5, 2.0),
            "c_press": (0.05, 0.2),
            "psi_diffusion": (0.01, 0.06),
            "cap_threshold": (0.20, 0.50),
        }
        reflective_default_baseline = {
            "damping": 1.0,
            "c_press": 0.1,
            "psi_diffusion": 0.05,
            "cap_threshold": 0.45,
        }
        for rk, rbounds in reflective_default_bounds.items():
            if rk not in knob_bounds:
                knob_bounds[rk] = rbounds
        for rk, rval in reflective_default_baseline.items():
            if rk not in baseline_knobs:
                baseline_knobs[rk] = rval
        teacher: Teacher = ReflectiveGeminiTeacher(
            knob_bounds=knob_bounds,
            step_scale=config.get("teacher_step_scale", 0.15),
            model=config.get("teacher_model", "gemini-4-argon"),
            live=is_live,
        )
    else:
        teacher = Teacher(knob_bounds, config.get("teacher_step_scale", 0.15))
    gatekeeper = Gatekeeper(
        min_anchor_delta=config.get("min_anchor_delta", 0.01),
        max_full_regression=config.get("max_full_regression", 0.0),
    )

    policy = _load_or_init_policy(active_policy_path, baseline_knobs)
    prev_interaction_id: str | None = None

    for generation in range(policy.generation + 1, policy.generation + generations + 1):
        gen_dir = out_dir / f"gen_{generation:03d}"
        if gen_dir.exists():
            shutil.rmtree(gen_dir)
        memory = MemoryStore(gen_dir)

        baseline_results = _eval_policy(policy, tasks, runner)
        baseline_full = judge.score(policy.policy_id, baseline_results)
        baseline_anchor = judge.score(policy.policy_id, _subset(baseline_results, tasks, anchor=True))

        reflective_spec_dict: dict | None = None
        if isinstance(teacher, ReflectiveGeminiTeacher):
            proposal, r_spec = teacher.propose_reflective(
                baseline=policy,
                generation=generation,
                previous_interaction_id=prev_interaction_id,
            )
            prev_interaction_id = r_spec.interaction_id
            reflective_spec_dict = r_spec.to_dict()
        else:
            proposal = teacher.propose(policy, generation)

        candidate_results = _eval_policy(proposal.candidate, tasks, runner)
        candidate_full = judge.score(proposal.candidate.policy_id, candidate_results)
        candidate_anchor = judge.score(proposal.candidate.policy_id, _subset(candidate_results, tasks, anchor=True))

        baseline_diag_files = _write_task_diagnostics(gen_dir, baseline_results, "baseline")
        candidate_diag_files = _write_task_diagnostics(gen_dir, candidate_results, "candidate")

        decision = gatekeeper.decide(baseline_full, candidate_full, baseline_anchor, candidate_anchor)

        memory.append_event("baseline_policy", asdict(policy))
        memory.append_event("run_mode", {
            "mode": mode,
            "runtime_profile": RUNTIME_MODE_PROFILES.get(mode, RUNTIME_MODE_PROFILES["default"]),
        })
        proposal_event = {
            "proposal_id": proposal.proposal_id,
            "parent_policy_id": proposal.parent_policy_id,
            "candidate": asdict(proposal.candidate),
            "rationale": proposal.rationale,
        }
        if reflective_spec_dict is not None:
            proposal_event["reflective_spec"] = reflective_spec_dict
        memory.append_event("proposal", proposal_event)
        memory.append_event("scores", {
            "baseline_full": asdict(baseline_full),
            "baseline_anchor": asdict(baseline_anchor),
            "candidate_full": asdict(candidate_full),
            "candidate_anchor": asdict(candidate_anchor),
        })
        memory.append_event("gate_decision", asdict(decision))
        memory.append_event("diagnostics", {
            "baseline": baseline_diag_files,
            "candidate": candidate_diag_files,
        })

        summary = {
            "generation": generation,
            "mode": mode,
            "baseline_policy_id": policy.policy_id,
            "candidate_policy_id": proposal.candidate.policy_id,
            "accepted": decision.accepted,
            "reason": decision.reason,
            "delta_anchor": decision.delta_anchor_score,
            "delta_full": decision.delta_full_score,
            "baseline_anchor_score": baseline_anchor.aggregate,
            "candidate_anchor_score": candidate_anchor.aggregate,
            "baseline_full_score": baseline_full.aggregate,
            "candidate_full_score": candidate_full.aggregate,
        }
        if reflective_spec_dict is not None:
            summary["reflective_spec"] = reflective_spec_dict
        (gen_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        if decision.accepted:
            policy = proposal.candidate
            active_policy_path.write_text(json.dumps(asdict(policy), indent=2), encoding="utf-8")

    return active_policy_path
