# Long-form MLX Whisper transcription into Obsidian

Session-tested pattern from transcribing two Nodaste planning conversations (~137 min and ~118 min) into Aaron's studio vault.

## When to use

Use for multi-hour meeting/conversation audio where the user asks for high-quality local transcription and storage in an Obsidian vault.

## Targeting Aaron's studio vault

- Studio vault path observed: `/Users/anichols/Obsidian/studio`
- Meeting transcript root: `Meeting Transcripts/`
- Planning conversations fit well under: `Meeting Transcripts/Demo and Planning/`
- Name files with date + human title + part number when multiple attachments belong to one conversation series, e.g. `2026-06-26 - Nodaste Planning Conversation - Part 1.md`.

## Quality workflow

1. Probe each input:
   ```bash
   ffprobe -v error -show_entries format=duration,size,format_name \
     -show_entries stream=codec_name,channels,sample_rate \
     -of default=noprint_wrappers=1 "$audio"
   ```
2. Use MLX Whisper large-v3 on Apple Silicon when available:
   ```bash
   mlx_whisper "$chunk" \
     --model mlx-community/whisper-large-v3-mlx \
     --language English \
     --task transcribe \
     --temperature 0 \
     --initial-prompt "Nodaste planning conversation. Proper nouns may include Nodaste, Aaron, Ana, C-Core, Context Core, Doct, Heddle, HUD, Fueled, Workday, Granola, Obsidian." \
     --output-format txt
   ```
3. For long audio, chunk before transcription instead of feeding the whole file at once:
   - 25-minute windows worked well.
   - 5s overlap helps avoid boundary truncation.
   - Convert chunks to 16 kHz mono WAV (`pcm_s16le`) with ffmpeg.
4. Merge segments by adding each chunk's start offset to local timestamps.
5. Drop segments whose end timestamp falls wholly inside the previous chunk's overlap.
6. Preserve raw wording; do not polish into meeting notes unless the user asks.

## Markdown format

Use frontmatter similar to:

```yaml
---
date: YYYY-MM-DD
type: transcript
source: original-audio-filename.ogg
source_path: /absolute/path/to/source
model: mlx-community/whisper-large-v3-mlx
language: en
transcribed_at: 2026-06-26T21:42:28+00:00
duration_minutes: 118.4
status: raw-transcript
---
```

Then include:

```markdown
# Human Title

Transcription: original-audio-filename.ogg  
Date: YYYY-MM-DD  
Model: mlx-community/whisper-large-v3-mlx  
Language: en  
Duration: N minutes  
Notes: Chunked into 25-minute windows with 5s overlap for long-form quality. Speaker labels are not diarized.

---

## Transcript

[00:00] First transcript line.
[00:03] Next transcript line.
```

## Pitfalls

- `.ogg` attachments may actually contain MP3 audio; trust `ffprobe`, not the extension.
- `openai-whisper` CLI may be installed even when Python `import whisper` is unavailable in the active interpreter. The CLI can still work; inspect its shebang if needed.
- MLX progress bars may write to stderr even when `verbose=False`; this is noisy but not a failure.
- Do not claim speaker diarization unless a diarization pipeline was actually run.
- For multi-hour files, a high-quality MLX large-v3 transcription can take ~15 minutes per 2+ hour attachment on Apple Silicon; run in a tracked background process with completion notification.
