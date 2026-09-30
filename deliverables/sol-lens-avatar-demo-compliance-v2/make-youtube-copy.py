from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PRODUCTION = ROOT / "production"
SOURCE = ROOT / "SOL-Lens-Build-Week-Compliant-Demo.mp4"
SRT = ROOT / "SOL-Lens-Build-Week-YouTube-Captions.en.srt"
ASS = PRODUCTION / "youtube-captions.ass"
OUTPUT = ROOT / "SOL-Lens-Build-Week-YouTube-Upload.mp4"
MANIFEST = ROOT / "youtube-upload-manifest.json"


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def ass_timestamp(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"


def phrase_chunks(text: str, max_words: int = 7, max_chars: int = 48) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and (len(current) >= max_words or len(candidate) > max_chars):
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    if len(chunks) > 1 and len(chunks[-1].split()) < 4:
        chunks[-2] = f"{chunks[-2]} {chunks[-1]}"
        chunks.pop()
    return chunks


def wrap_ass(text: str, limit: int = 36) -> str:
    if len(text) <= limit:
        return text
    words = text.split()
    midpoint = len(text) / 2
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - midpoint))
    return " ".join(words[:best]) + r"\N" + " ".join(words[best:])


def build_cues() -> list[tuple[float, float, str]]:
    timeline = json.loads((PRODUCTION / "timeline.json").read_text(encoding="utf-8"))
    rendered = json.loads((ROOT / "render-manifest.json").read_text(encoding="utf-8"))["timeline"]
    timing = {item["id"]: item for item in rendered}
    cues: list[tuple[float, float, str]] = []
    for segment in timeline:
        chunks = phrase_chunks(segment["text"])
        total_words = sum(len(chunk.split()) for chunk in chunks)
        start = float(timing[segment["id"]]["start"]) + 0.38
        speech_seconds = float(timing[segment["id"]]["speech_seconds"])
        for chunk in chunks:
            duration = speech_seconds * len(chunk.split()) / total_words
            end = start + duration
            cues.append((start, end, chunk))
            start = end
    return cues


def write_captions(cues: list[tuple[float, float, str]]) -> None:
    with SRT.open("w", encoding="utf-8") as handle:
        for index, (start, end, text) in enumerate(cues, start=1):
            handle.write(f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}\n\n")

    header = """[Script Info]
Title: SOL Lens YouTube captions
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,Segoe UI,25,&H00FFFFFF,&H000000FF,&H00000000,&H78000000,0,0,0,0,100,100,0,0,3,1,0,2,60,60,34,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [header]
    for start, end, text in cues:
        safe = wrap_ass(text).replace("{", r"\{").replace("}", r"\}")
        lines.append(f"Dialogue: 0,{ass_timestamp(start)},{ass_timestamp(end)},Caption,,0,0,0,,{safe}\n")
    ASS.write_text("".join(lines), encoding="utf-8-sig")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    import imageio_ffmpeg

    cues = build_cues()
    write_captions(cues)
    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    subprocess.run(
        [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(SOURCE),
            "-map", "0:v:0", "-map", "0:a:0",
            "-vf", "ass=production/youtube-captions.ass",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "copy",
            "-movflags", "+faststart", str(OUTPUT),
        ],
        cwd=ROOT,
        check=True,
    )
    manifest = {
        "video": OUTPUT.name,
        "source_video": SOURCE.name,
        "captions": SRT.name,
        "caption_mode": "burned-in; no separate subtitle stream",
        "caption_style": {
            "font": "Segoe UI",
            "font_size": 25,
            "target_maximum_words_per_cue": 7,
            "actual_maximum_words_per_cue": max(len(text.split()) for _, _, text in cues),
            "minimum_cue_seconds": round(min(end - start for start, end, _ in cues), 3),
            "maximum_lines": 2,
            "bottom_margin": 34,
        },
        "cue_count": len(cues),
        "sha256": sha256(OUTPUT),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
