from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import edge_tts


VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+8%"
PITCH = "+1Hz"


SEGMENTS = [
    {
        "id": "01-hook",
        "title": "WHY AGENT EVIDENCE",
        "capture": "01-opening.png",
        "side": "right",
        "cursor": [285, 610, 285, 680, 0.72],
        "text": "Agent migrations are often approved from polished final answers. That can hide weak evidence, broken constraints, or unresolved contradictions. SOL Lens makes the observable workflow inspectable before a team promotes it.",
        "speech": "Agent migrations are often approved from polished final answers. That can hide weak evidence, broken constraints, or unresolved contradictions. S O L Lens makes the observable workflow inspectable before a team promotes it.",
    },
    {
        "id": "02-product-delta",
        "title": "PRODUCT + BUILD WEEK DELTA",
        "capture": "01-opening.png",
        "side": "right",
        "cursor": [1380, 70, 1660, 70, 0.70],
        "text": "SOL Lens is a developer workbench for engineering teams comparing reference and candidate agents. It builds on earlier SOL Engine research; during Build Week, I turned that foundation into this runnable packet workbench, deterministic court, teaching gallery, and replay module.",
        "speech": "S O L Lens is a developer workbench for engineering teams comparing reference and candidate agents. It builds on earlier S O L Engine research; during Build Week, I turned that foundation into this runnable packet workbench, deterministic court, teaching gallery, and replay module.",
    },
    {
        "id": "03-one-click-fixtures",
        "title": "START WITHOUT JSON",
        "capture": "02-gallery.png",
        "side": "right",
        "cursor": [285, 680, 285, 930, 0.60],
        "text": "I can start without authoring JSON. These seven browser-local fixtures cover grounded answers, tool fan-out, self-correction, handoffs, conflict, and program-scale traces, while using the same validator and scoring path as an imported packet.",
        "speech": "I can start without authoring J S O N. These seven browser-local fixtures cover grounded answers, tool fan-out, self-correction, handoffs, conflict, and program-scale traces, while using the same validator and scoring path as an imported packet.",
    },
    {
        "id": "04-core-workflow",
        "title": "VALIDATE + SCORE + DECIDE",
        "capture": "04-grounded-graph.png",
        "side": "left",
        "cursor": [980, 370, 1760, 875, 0.70],
        "text": "A Logon is one observable step: a request, tool result, check, contradiction, or output. Typed edges preserve how those steps support or constrain one another. SOL Lens validates the packet, lays out the graph, scores evidence, coherence, and contradiction, then applies explicit gates. This grounded trace moves from HOLD to PROMOTE.",
        "speech": "A low-gon is one observable step: a request, tool result, check, contradiction, or output. Typed edges preserve how those steps support or constrain one another. S O L Lens validates the packet, lays out the graph, scores evidence, coherence, and contradiction, then applies explicit gates. This grounded trace moves from hold to promote.",
    },
    {
        "id": "05-conflict",
        "title": "CONFLICT BECOMES VISIBLE",
        "capture": "06-conflict-verdict.png",
        "side": "left",
        "cursor": [285, 680, 1765, 860, 0.72],
        "text": "Now I load the conflicting-sources fixture. Its candidate contradiction score reaches point two four, so the same court moves from PROMOTE to QUARANTINE. That is the product's value: a busy-looking agent cannot hide a weak evidence structure behind a polished answer.",
        "speech": "Now I load the conflicting-sources fixture. Its candidate contradiction score reaches point two four, so the same court moves from promote to quarantine. That is the product's value: a busy-looking agent cannot hide a weak evidence structure behind a polished answer.",
    },
    {
        "id": "06-replay-proof",
        "title": "PROOF + MANIFOLD REPLAY",
        "capture": "08-manifold-step3.png",
        "side": "right",
        "cursor": [1725, 930, 1390, 165, 0.68],
        "text": "The proof packet preserves the authoritative deterministic result. Manifold Replay separately visualizes density, pressure, conductance, and edge flux. Three Step clicks change the telemetry, but this experimental layer never rewrites the QUARANTINE verdict.",
        "speech": "The proof packet preserves the authoritative deterministic result. Manifold Replay separately visualizes density, pressure, conductance, and edge flux. Three Step clicks change the telemetry, but this experimental layer never rewrites the quarantine verdict.",
    },
    {
        "id": "07-codex-story",
        "title": "HOW CODEX CHANGED THE BUILD",
        "capture": "evidence-codex.png",
        "side": "right",
        "cursor": [420, 790, 1370, 800, 0.74],
        "text": "During Build Week, I used Codex to implement the versioned packet validator, deterministic graph layout, seven fixtures, replay engine, and thirty-seven-test suite. The first judge flow assumed unfamiliar JSON, so I retained the product decision to replace it with one-click teaching packets. I also kept replay state separate from the court so an experimental visualization cannot change the decision.",
        "speech": "During Build Week, I used Codex to implement the versioned packet validator, deterministic graph layout, seven fixtures, replay engine, and thirty-seven-test suite. The first judge flow assumed unfamiliar J S O N, so I retained the product decision to replace it with one-click teaching packets. I also kept replay state separate from the court so an experimental visualization cannot change the decision.",
    },
    {
        "id": "08-gpt-boundary",
        "title": "GPT-5.6 ROLE + BOUNDARY",
        "capture": "evidence-gpt.png",
        "side": "right",
        "cursor": [450, 765, 1420, 765, 0.72],
        "text": "GPT-5.6 powered those Codex build sessions. It received the build guide, repository, test failures, and interface feedback, then helped produce patches, tests, and revisions. It is a build-time development model here, not a live evaluator; this submitted browser app remains deterministic.",
        "speech": "G P T five point six powered those Codex build sessions. It received the build guide, repository, test failures, and interface feedback, then helped produce patches, tests, and revisions. It is a build-time development model here, not a live evaluator; this submitted browser app remains deterministic.",
    },
    {
        "id": "09-close",
        "title": "VISIBLE. DETERMINISTIC. REVIEWABLE.",
        "capture": "09-manifold-reset.png",
        "side": "left",
        "cursor": [1390, 165, 1690, 930, 0.72],
        "text": "For engineering teams, that means migration decisions backed by portable evidence instead of final-answer vibes: visible, deterministic, and independently reviewable before a workflow reaches production.",
        "speech": "For engineering teams, that means migration decisions backed by portable evidence instead of final-answer vibes: visible, deterministic, and independently reviewable before a workflow reaches production.",
    },
]


async def synthesize(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    timeline = []
    for segment in SEGMENTS:
        target = output / f"{segment['id']}.mp3"
        communicate = edge_tts.Communicate(
            segment["speech"], voice=VOICE, rate=RATE, pitch=PITCH, volume="+0%"
        )
        await communicate.save(str(target))
        item = {key: value for key, value in segment.items() if key != "speech"}
        item["audio"] = target.name
        timeline.append(item)

    timeline_path = output.parent / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    metadata = {
        "provider": "Microsoft Edge neural speech service",
        "voice": VOICE,
        "rate": RATE,
        "pitch": PITCH,
        "note": "Andrew HD is installed for Windows Narrator but is not exposed to the legacy System.Speech WAV exporter; this render uses Microsoft's exportable Andrew neural voice and records the exact identifier.",
    }
    (output.parent / "voice-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "production" / "audio")
    args = parser.parse_args()
    asyncio.run(synthesize(args.output.resolve()))


if __name__ == "__main__":
    main()
