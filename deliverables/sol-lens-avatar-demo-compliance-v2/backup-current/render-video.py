from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1920
HEIGHT = 1080
FPS = 30


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size=size)


def make_title_overlay(title: str, target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    label_font = font(23, bold=True)
    label = title.upper()
    bounds = draw.textbbox((0, 0), label, font=label_font)
    box_w = bounds[2] - bounds[0] + 56
    box_h = 58
    x, y = 42, 94
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=14, fill=(6, 12, 24, 225), outline=(234, 180, 82, 210), width=2)
    draw.text((x + 28, y + 14), label, font=label_font, fill=(246, 226, 184, 255))
    canvas.save(target)


def make_avatar_stage(source: Path, target: Path) -> None:
    avatar = Image.open(source).convert("RGBA")
    avatar = avatar.resize((avatar.width * 2, avatar.height * 2), Image.Resampling.NEAREST)
    stage = Image.new("RGBA", (286, 420), (0, 0, 0, 0))
    glow = Image.new("RGBA", stage.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((36, 36, 250, 370), fill=(38, 173, 222, 72))
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    stage.alpha_composite(glow)
    x = (stage.width - avatar.width) // 2
    y = (stage.height - avatar.height) // 2 - 4
    stage.alpha_composite(avatar, (x, y))
    stage.save(target)


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def sentence_chunks(text: str) -> list[str]:
    pieces = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    return pieces or [text.strip()]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--ffmpeg", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    production = root / "production"
    captures = production / "captures"
    audio = production / "audio"
    work = production / "render"
    work.mkdir(parents=True, exist_ok=True)

    if args.ffmpeg:
        ffmpeg = args.ffmpeg.resolve()
    else:
        import imageio_ffmpeg
        ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())

    timeline = json.loads((production / "timeline.json").read_text(encoding="utf-8-sig"))
    avatar_stage = work / "avatar-stage.png"
    make_avatar_stage(production / "avatar.png", avatar_stage)

    segment_paths: list[Path] = []
    caption_entries: list[tuple[float, float, str]] = []
    cursor = 0.0

    for index, segment in enumerate(timeline, start=1):
        speech_path = audio / segment["audio"]
        speech_duration = wav_duration(speech_path)
        duration = speech_duration + 0.9
        title_overlay = work / f"title-{index:02}.png"
        make_title_overlay(segment["title"], title_overlay)
        output = work / f"segment-{index:02}.mp4"
        segment_paths.append(output)

        fade_out = max(0.4, duration - 0.38)
        pet_x = "W-w-46" if segment.get("side") == "right" else "46"
        filter_graph = (
            f"[0:v]scale={WIDTH}:{HEIGHT},"
            "zoompan=z='min(zoom+0.00010,1.03)':"
            "x='min(max(iw/2-iw/zoom/2,0),iw-iw/zoom)':"
            "y='min(max(ih/2-ih/zoom/2,0),ih-ih/zoom)':"
            f"d=1:s={WIDTH}x{HEIGHT}:fps={FPS}[bg];"
            "[bg][1:v]overlay=0:0:format=auto[titled];"
            f"[titled][2:v]overlay=x={pet_x}:y=H-h-34+6*sin(2*PI*t/2.3):format=auto,"
            f"fade=t=in:st=0:d=0.32,fade=t=out:st={fade_out:.3f}:d=0.38,format=yuv420p,setsar=1[v];"
            "[3:a]adelay=360|360,apad=pad_dur=0.54[a]"
        )

        run([
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning",
            "-loop", "1", "-framerate", str(FPS), "-i", str(captures / segment["capture"]),
            "-loop", "1", "-framerate", str(FPS), "-i", str(title_overlay),
            "-loop", "1", "-framerate", str(FPS), "-i", str(avatar_stage),
            "-i", str(speech_path),
            "-filter_complex", filter_graph,
            "-map", "[v]", "-map", "[a]", "-t", f"{duration:.3f}",
            "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(output),
        ])

        chunk_start = cursor + 0.36
        chunks = sentence_chunks(segment["text"])
        total_words = sum(max(1, len(chunk.split())) for chunk in chunks)
        available = max(0.5, speech_duration)
        for chunk in chunks:
            share = max(1, len(chunk.split())) / total_words
            chunk_end = chunk_start + available * share
            caption_entries.append((chunk_start, chunk_end, chunk))
            chunk_start = chunk_end
        cursor += duration

    concat_file = work / "segments.txt"
    concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in segment_paths), encoding="utf-8")
    joined = work / "joined.mp4"
    run([
        str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(joined),
    ])

    captions = root / "SOL-Lens-Manifold-Replay-Demo.en.srt"
    with captions.open("w", encoding="utf-8") as handle:
        for number, (start, end, text) in enumerate(caption_entries, start=1):
            handle.write(f"{number}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n\n")

    final = root / "SOL-Lens-Manifold-Replay-Demo.mp4"
    run([
        str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(joined), "-i", str(captions),
        "-map", "0:v", "-map", "0:a", "-map", "1:0",
        "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng", "-disposition:s:0", "default",
        "-movflags", "+faststart", str(final),
    ])

    manifest = {
        "video": final.name,
        "captions": captions.name,
        "duration_seconds": round(cursor, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "voice": "Microsoft David Desktop",
        "voice_rate": 1,
        "avatar": "dAvatar_transparent.png",
        "segments": len(segment_paths),
    }
    (root / "render-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
