from __future__ import annotations

from datetime import date
from pathlib import Path

SOL_ROOT = Path(r"G:\docs\TechmanStudios\sol")
SOL_RESEARCH_DIR = SOL_ROOT / "solResearch"
ARCHIVE_MD_DIR = SOL_ROOT / "solArchive" / "MD"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def ensure_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))


def append_file(out_parts: list[str], path: Path) -> None:
    ensure_exists(path)
    content = read_text(path)
    out_parts.append("\n\n---\n\n")
    out_parts.append(f"# BEGIN FILE: {path.name}\n")
    out_parts.append(content)
    if not content.endswith("\n"):
        out_parts.append("\n")
    out_parts.append(f"# END FILE: {path.name}\n")


def main() -> None:
    # Chronological progression by date/version as present in solResearch folder.
    dashboard_reports = [
        "SOL_Dashboard_Chat_Report_2025-12-15.md",
        "SOL_Dashboard_Chat_Report_2025-12-16.md",
        "SOL_Dashboard_Chat_Report_2025-12-17.md",
        "SOL_Dashboard_Chat_Report_2025-12-18.md",
        "SOL_Dashboard_Chat_Report_2025-12-21.md",
        "SOL_qFoamInspection_CSV_to_TXT_Report_2025-12-22.md",
        "SOL_qFoamInspection_Damping_Sweep_Analysis_Report_2025-12-23.md",
        "SOL_Dashboard_Chat_Report_2025-12-24.md",
        "SOL_Dashboard_Chat_Report_2026-01-02.md",
        "SOL_Dashboard_Chat_Report_2026-01-02_v3-5_Physics-Vorticity-Memory.md",
        "SOL_Dashboard_Chat_Report_2026-01-03_v3-5_Leaders-Solver-Fallback.md",
        "SOL_Dashboard_Chat_Report_2026-01-11_v3-7_CapLaw-Invariants-Baseline-Interop.md",
        "SOL_Dashboard_Chat_Report_2026-01-15_v3-6_Phase-3-8-CapLaw-Harness-Split.md",
    ]

    rd_files: list[str] = []
    for i in range(0, 31):
        rd_files.append(f"rd{i}.md")
        if i == 1:
            rd_files.append("rd1_1.md")

    out_parts: list[str] = []
    out_parts.append("# SOL — Full Research Master (Dashboard Chat Reports + rd0–rd30)\n")
    out_parts.append(f"Generated: {date.today().isoformat()}\n")
    out_parts.append(
        "This file is a verbatim consolidation: it includes the full contents of each source file below, in order. "
        "No source content has been summarized or shortened; only file boundary markers have been added.\n"
    )

    out_parts.append("\n## Part A — SOL Dashboard chat reports (verbatim)\n")
    for name in dashboard_reports:
        append_file(out_parts, SOL_RESEARCH_DIR / name)

    out_parts.append("\n## Part B — solArchive MD rd0–rd30 (verbatim)\n")
    for name in rd_files:
        append_file(out_parts, ARCHIVE_MD_DIR / name)

    out_path = SOL_RESEARCH_DIR / "sol_fullResearch_rd0_rd30.md"
    out_path.write_text("".join(out_parts), encoding="utf-8", errors="strict")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
