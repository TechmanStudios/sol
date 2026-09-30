# SOL Lens Build Week compliant demo package

This package is a corrected, separately rendered successor to the original avatar cut. The original files are preserved under `backup-current/`.

- `generate-narration.py` synthesizes the audited script with Microsoft `en-US-AndrewMultilingualNeural` and records the provider/name/rate in `production/voice-metadata.json`.
- `render-video.py` creates the 1080p cut, cursor/click evidence, authentic Build Week evidence panels, normalized audio, SRT captions, and the final media manifest.
- `SOL-Lens-Build-Week-Compliant-Demo.mp4` is the upload candidate after final validation.

## YouTube upload copy

`SOL-Lens-Build-Week-YouTube-Upload.mp4` is the caption-refined upload copy. It has 57 compact burned-in caption cues using a 25px Segoe UI style, a minimum cue duration of 1.819 seconds, and no separate subtitle stream that could create a second oversized caption layer.

The matching `SOL-Lens-Build-Week-YouTube-Captions.en.srt` is retained as an editable caption master. Do not add it to the burned-in upload unless you intentionally want optional duplicate captions; use it with the clean compliant master instead.

The locally installed Andrew HD voice is a Windows Narrator voice and is not exposed to the legacy System.Speech WAV exporter used by the original package. This v2 uses Microsoft's exportable Andrew neural voice and does not mislabel it as a local Narrator capture.
