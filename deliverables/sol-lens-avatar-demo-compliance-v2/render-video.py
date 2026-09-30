from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1920
HEIGHT = 1080
FPS = 30


def run(command: list[str], capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=not capture, text=True, capture_output=capture)


def media_duration(ffmpeg: Path, path: Path) -> float:
    result = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(path)], text=True, capture_output=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not determine duration for {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size=size)


def make_title_overlay(title: str, target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    label_font = font(22, bold=True)
    label = title.upper()
    bounds = draw.textbbox((0, 0), label, font=label_font)
    box_w = bounds[2] - bounds[0] + 54
    x, y, box_h = 42, 92, 56
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=14, fill=(6, 12, 24, 232), outline=(234, 180, 82, 215), width=2)
    draw.text((x + 27, y + 14), label, font=label_font, fill=(246, 226, 184, 255))
    canvas.save(target)


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], max_width: int, text_font: ImageFont.FreeTypeFont, fill: tuple[int, int, int, int], gap: int = 12) -> int:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    x, y = xy
    line_height = text_font.size + gap
    for value in lines:
        draw.text((x, y), value, font=text_font, fill=fill)
        y += line_height
    return y


def make_evidence_capture(kind: str, target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (4, 9, 18, 255))
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((1020, -260, 2160, 820), fill=(24, 147, 190, 58))
    gdraw.ellipse((-350, 520, 850, 1450), fill=(226, 164, 63, 44))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(80)))
    draw = ImageDraw.Draw(canvas)
    cream = (245, 237, 217, 255)
    muted = (160, 174, 191, 255)
    cyan = (75, 201, 232, 255)
    gold = (238, 181, 77, 255)
    green = (100, 222, 166, 255)
    draw.text((150, 175), "AUTHENTIC BUILD WEEK EVIDENCE", font=font(23, True), fill=gold)

    if kind == "codex":
        draw.text((150, 225), "Codex turned feedback into tested product changes", font=font(47, True), fill=cream)
        commits = [
            ("c390ef9", "Packet-driven semantic graph"),
            ("e7d5200", "Focus demo on curated examples"),
            ("23181d8", "Guide judges through examples"),
            ("0e9e0d5", "Deterministic manifold replay"),
        ]
        y = 340
        for sha, message in commits:
            draw.rounded_rectangle((150, y, 1030, y + 92), radius=14, fill=(9, 18, 34, 238), outline=(46, 73, 98, 255), width=2)
            draw.text((180, y + 24), sha, font=font(25, True), fill=cyan)
            draw.text((365, y + 24), message, font=font(27), fill=cream)
            y += 112
        draw.rounded_rectangle((1120, 340, 1765, 790), radius=20, fill=(9, 18, 34, 238), outline=(234, 180, 82, 205), width=2)
        draw.text((1170, 390), "DECISIONS RETAINED", font=font(22, True), fill=gold)
        y = draw_wrapped(draw, "Replace unfamiliar JSON-first onboarding with seven one-click teaching packets.", (1170, 450), 520, font(28), cream)
        y = draw_wrapped(draw, "Keep experimental replay state separate from the authoritative court verdict.", (1170, y + 35), 520, font(28), cream)
        draw.rounded_rectangle((150, 850, 1765, 950), radius=18, fill=(10, 39, 31, 242), outline=(100, 222, 166, 215), width=2)
        draw.text((195, 880), "37 TESTS PASSED", font=font(31, True), fill=green)
        draw.text((555, 883), "validator · layout · fixtures · replay · UI", font=font(26), fill=cream)
    else:
        draw.text((150, 225), "GPT-5.6 powered the Codex development loop", font=font(47, True), fill=cream)
        inputs = ["BUILD GUIDE", "REPOSITORY", "TEST FAILURES", "UI FEEDBACK"]
        x = 150
        for item in inputs:
            draw.rounded_rectangle((x, 375, x + 350, 465), radius=16, fill=(9, 18, 34, 238), outline=(46, 73, 98, 255), width=2)
            bounds = draw.textbbox((0, 0), item, font=font(22, True))
            draw.text((x + (350 - (bounds[2] - bounds[0])) / 2, 406), item, font=font(22, True), fill=cyan)
            x += 390
        draw.line((330, 520, 1590, 520), fill=(75, 201, 232, 170), width=4)
        draw.polygon([(1580, 508), (1610, 520), (1580, 532)], fill=cyan)
        draw.rounded_rectangle((525, 585, 1395, 725), radius=22, fill=(20, 48, 66, 248), outline=(75, 201, 232, 235), width=3)
        draw.text((705, 617), "GPT-5.6 IN CODEX", font=font(39, True), fill=cream)
        draw.text((694, 671), "patches · tests · revisions", font=font(28), fill=muted)
        draw.rounded_rectangle((150, 820, 1765, 950), radius=18, fill=(46, 25, 18, 245), outline=(238, 181, 77, 220), width=2)
        draw.text((195, 850), "BOUNDARY", font=font(24, True), fill=gold)
        draw.text((390, 847), "Build-time model — no live GPT call in the deterministic browser evaluator", font=font(29), fill=cream)
        draw.text((390, 894), "Observable packet fields only · no hidden-reasoning claim", font=font(23), fill=muted)
    canvas.convert("RGB").save(target, quality=95)


def make_avatar_stage(source: Path, target: Path) -> None:
    avatar = Image.open(source).convert("RGBA")
    avatar = avatar.resize((91, 166), Image.Resampling.NEAREST)
    stage = Image.new("RGBA", (150, 215), (0, 0, 0, 0))
    glow = Image.new("RGBA", stage.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((24, 22, 126, 198), fill=(38, 173, 222, 70))
    stage.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
    stage.alpha_composite(avatar, ((stage.width - avatar.width) // 2, 24))
    stage.save(target)


def make_cursor(target: Path, ring_target: Path) -> None:
    cursor = Image.new("RGBA", (54, 68), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cursor)
    points = [(6, 4), (8, 52), (20, 40), (29, 61), (38, 57), (29, 36), (47, 35)]
    draw.polygon(points, fill=(250, 250, 250, 255), outline=(3, 8, 15, 255))
    cursor.save(target)
    ring = Image.new("RGBA", (84, 84), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((9, 9, 75, 75), outline=(238, 181, 77, 235), width=7)
    rd.ellipse((25, 25, 59, 59), outline=(75, 201, 232, 180), width=4)
    ring.save(ring_target)


def make_composite_frame(capture: Path, title: Path, avatar: Path, side: str, target: Path) -> None:
    base = Image.open(capture).convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    base.alpha_composite(Image.open(title).convert("RGBA"))
    pet = Image.open(avatar).convert("RGBA")
    x = WIDTH - pet.width - 38 if side == "right" else 38
    y = HEIGHT - pet.height - 24
    base.alpha_composite(pet, (x, y))
    base.convert("RGB").save(target, quality=95)


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def sentence_chunks(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root.resolve()
    production = root / "production"
    captures = production / "captures"
    audio = production / "audio"
    work = production / "render"
    work.mkdir(parents=True, exist_ok=True)

    import imageio_ffmpeg
    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    timeline = json.loads((production / "timeline.json").read_text(encoding="utf-8-sig"))
    make_evidence_capture("codex", captures / "evidence-codex.png")
    make_evidence_capture("gpt", captures / "evidence-gpt.png")
    avatar_stage = work / "avatar-stage.png"
    cursor_stage = work / "cursor.png"
    click_ring = work / "click-ring.png"
    make_avatar_stage(production / "avatar.png", avatar_stage)
    make_cursor(cursor_stage, click_ring)

    segment_paths: list[Path] = []
    captions_out: list[tuple[float, float, str]] = []
    timeline_out: list[dict[str, object]] = []
    cursor_time = 0.0

    for index, segment in enumerate(timeline, start=1):
        speech_path = audio / segment["audio"]
        speech_duration = media_duration(ffmpeg, speech_path)
        duration = speech_duration + 1.08
        title_overlay = work / f"title-{index:02}.png"
        make_title_overlay(segment["title"], title_overlay)
        composite_frame = work / f"composite-{index:02}.png"
        make_composite_frame(captures / segment["capture"], title_overlay, avatar_stage, segment.get("side", "right"), composite_frame)
        output = work / f"segment-v2-{index:02}.mp4"
        segment_paths.append(output)
        x0, y0, x1, y1, click_fraction = segment["cursor"]
        click_time = max(1.0, duration * float(click_fraction))
        cx = f"{x0}+({x1}-{x0})*min(t/{click_time:.3f},1)"
        cy = f"{y0}+({y1}-{y0})*min(t/{click_time:.3f},1)"
        fade_out = max(0.4, duration - 0.35)
        filter_graph = (
            f"[0:v]scale={WIDTH}:{HEIGHT},fps={FPS}[bg];"
            f"[bg][2:v]overlay=x={x1}-42:y={y1}-42:enable='between(t,{click_time - 0.24:.3f},{click_time + 0.48:.3f})'[ringed];"
            f"[ringed][1:v]overlay=x='{cx}':y='{cy}':format=auto,"
            f"fade=t=in:st=0:d=0.28,fade=t=out:st={fade_out:.3f}:d=0.35,format=yuv420p,setsar=1[v];"
            "[3:a]adelay=380|380,loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=0.62[a]"
        )
        output_is_complete = False
        if output.exists():
            try:
                output_is_complete = abs(media_duration(ffmpeg, output) - duration) < 0.18
            except RuntimeError:
                output_is_complete = False
        if not output_is_complete:
            subprocess.run([
                str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning",
                "-loop", "1", "-framerate", str(FPS), "-i", str(composite_frame),
                "-loop", "1", "-framerate", str(FPS), "-i", str(cursor_stage),
                "-loop", "1", "-framerate", str(FPS), "-i", str(click_ring),
                "-i", str(speech_path), "-filter_complex", filter_graph,
                "-map", "[v]", "-map", "[a]", "-t", f"{duration:.3f}", "-r", str(FPS),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", str(output),
            ], check=True)

        chunks = sentence_chunks(segment["text"])
        start = cursor_time + 0.38
        total_words = sum(max(1, len(chunk.split())) for chunk in chunks)
        for chunk in chunks:
            end = start + speech_duration * max(1, len(chunk.split())) / total_words
            captions_out.append((start, end, chunk))
            start = end
        timeline_out.append({"id": segment["id"], "start": round(cursor_time, 3), "end": round(cursor_time + duration, 3), "speech_seconds": round(speech_duration, 3), "capture": segment["capture"]})
        cursor_time += duration

    concat_file = work / "segments.txt"
    concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in segment_paths), encoding="utf-8")
    joined = work / "joined.mp4"
    subprocess.run([str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(joined)], check=True)

    captions = root / "SOL-Lens-Build-Week-Compliant-Demo.en.srt"
    with captions.open("w", encoding="utf-8") as handle:
        for number, (start, end, text) in enumerate(captions_out, start=1):
            handle.write(f"{number}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n\n")
    final = root / "SOL-Lens-Build-Week-Compliant-Demo.mp4"
    subprocess.run([str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning", "-i", str(joined), "-i", str(captions), "-map", "0:v", "-map", "0:a", "-map", "1:0", "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-disposition:s:0", "default", "-movflags", "+faststart", str(final)], check=True)

    voice_metadata = json.loads((production / "voice-metadata.json").read_text(encoding="utf-8"))
    manifest = {
        "video": final.name,
        "captions": captions.name,
        "duration_seconds": round(cursor_time, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "voice": voice_metadata,
        "avatar": "user-supplied dAvatar_transparent.png",
        "segments": len(segment_paths),
        "timeline": timeline_out,
        "sha256": {"video": sha256(final), "avatar": sha256(production / "avatar.png")},
    }
    (root / "render-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
