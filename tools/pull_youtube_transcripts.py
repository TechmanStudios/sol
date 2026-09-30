from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def _safe_filename(text: str, max_len: int = 120) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9._ -]+", "_", text)
    text = text.strip(" ._")
    if not text:
        return "untitled"
    if len(text) > max_len:
        return text[:max_len].rstrip(" ._")
    return text


def _format_ts(seconds: float) -> str:
    # Format as H:MM:SS (or M:SS) with integer seconds
    total_seconds = max(0, int(seconds))
    td = timedelta(seconds=total_seconds)
    s = str(td)
    # timedelta prints H:MM:SS; for under 1 hour it prints 0:MM:SS
    if s.startswith("0:"):
        return s[2:]
    return s


def _extract_video_id(url: str) -> str:
    # Supports:
    # - https://www.youtube.com/watch?v=VIDEOID
    # - https://youtu.be/VIDEOID
    # - raw VIDEOID
    url = url.strip()

    m = re.search(r"(?:v=)([A-Za-z0-9_-]{6,})", url)
    if m:
        return m.group(1)

    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", url)
    if m:
        return m.group(1)

    # Allow passing the id directly
    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", url):
        return url

    raise ValueError(f"Could not extract a YouTube video id from: {url}")


@dataclass(frozen=True)
class TranscriptResult:
    video_id: str
    language: str
    is_generated: Optional[bool]
    segments: List[dict]


def _select_transcript(transcript_list, prefer_languages: List[str]):
    languages = prefer_languages or ["en"]
    try:
        return transcript_list.find_transcript(languages)
    except Exception:
        try:
            return transcript_list.find_generated_transcript(languages)
        except Exception:
            return transcript_list.find_transcript(["en"])


def fetch_transcript(video_id: str, prefer_languages: List[str]) -> TranscriptResult:
    """Fetch transcript using youtube-transcript-api.

    Notes:
    - This relies on YouTube having either manual captions or auto-generated captions.
    - Some videos may have captions disabled or be blocked regionally.
    """

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: youtube-transcript-api. Install with: pip install youtube-transcript-api"
        ) from e

    # Current versions (as installed in this workspace) expose instance methods:
    # - YouTubeTranscriptApi().list(video_id)
    # - YouTubeTranscriptApi().fetch(video_id, languages=(...))
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            languages = prefer_languages or ["en"]
            fetched = api.fetch(video_id, languages=languages)
            segments = (
                fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
            )
            language = getattr(fetched, "language_code", None) or getattr(fetched, "language", None)
            is_generated = getattr(fetched, "is_generated", None)
            if language is None or not isinstance(is_generated, bool):
                if hasattr(api, "list"):
                    try:
                        transcript_list = api.list(video_id)
                        transcript = _select_transcript(transcript_list, prefer_languages)
                        language = language or getattr(transcript, "language_code", None) or getattr(transcript, "language", None)
                        if not isinstance(is_generated, bool):
                            is_generated = getattr(transcript, "is_generated", None)
                    except Exception:
                        pass
            return TranscriptResult(
                video_id=video_id,
                language=str(language or "unknown"),
                is_generated=is_generated if isinstance(is_generated, bool) else None,
                segments=segments,
            )
    except Exception:
        # If instantiation/fetch fails, fall back to the older staticmethod-style APIs below.
        pass

    # Fallbacks for older releases that used static/class methods.
    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = _select_transcript(transcript_list, prefer_languages)
        segments = transcript.fetch()
        return TranscriptResult(
            video_id=video_id,
            language=getattr(transcript, "language_code", None) or "unknown",
            is_generated=bool(getattr(transcript, "is_generated", False)),
            segments=[dict(s) for s in segments],
        )

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=prefer_languages or None)
        return TranscriptResult(
            video_id=video_id,
            language=prefer_languages[0] if prefer_languages else "unknown",
            is_generated=None,
            segments=[dict(s) for s in segments],
        )

    raise RuntimeError(
        "Unsupported youtube-transcript-api version: could not find a usable transcript retrieval method."
    )


def write_outputs(out_dir: Path, url: str, result: TranscriptResult) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    gen_suffix = "_auto" if result.is_generated is True else ("" if result.is_generated is False else "_gen-unknown")
    base = _safe_filename(f"youtube_{result.video_id}_{result.language}{gen_suffix}")
    json_path = out_dir / f"{base}.json"
    md_path = out_dir / f"{base}.md"

    payload = {
        "source_url": url,
        "video_id": result.video_id,
        "language": result.language,
        "is_generated": result.is_generated,
        "segments": result.segments,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines: List[str] = []
    lines.append(f"# YouTube Transcript ({result.video_id})")
    lines.append("")
    lines.append(f"- Source: {url}")
    lines.append(f"- Language: {result.language}")
    if result.is_generated is None:
        lines.append("- Auto-generated: unknown")
    else:
        lines.append(f"- Auto-generated: {str(result.is_generated).lower()}")
    lines.append("")
    lines.append("## Transcript")
    lines.append("")

    for seg in result.segments:
        start = float(seg.get("start", 0.0))
        dur = float(seg.get("duration", 0.0))
        text = (seg.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        ts = _format_ts(start)
        ts2 = _format_ts(start + dur) if dur > 0 else ""
        if ts2:
            lines.append(f"- [{ts}–{ts2}] {text}")
        else:
            lines.append(f"- [{ts}] {text}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pull YouTube transcripts/captions and save to JSON + Markdown.",
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="YouTube URLs or video IDs",
    )
    parser.add_argument(
        "--out",
        default=str(Path("knowledge") / "youtube"),
        help="Output directory (default: knowledge/youtube)",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Comma-separated preferred languages (default: en)",
    )

    args = parser.parse_args()
    out_dir = Path(args.out)
    prefer_languages = [x.strip() for x in str(args.lang).split(",") if x.strip()]

    failures: List[Tuple[str, str]] = []

    for url in args.urls:
        try:
            video_id = _extract_video_id(url)
            result = fetch_transcript(video_id, prefer_languages=prefer_languages)
            json_path, md_path = write_outputs(out_dir, url=url, result=result)
            print(f"OK  {url}")
            print(f"    -> {json_path}")
            print(f"    -> {md_path}")
        except Exception as e:
            failures.append((url, str(e)))
            print(f"ERR {url}: {e}")

    if failures:
        print("\nSome transcripts failed:")
        for url, err in failures:
            print(f"- {url}: {err}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
