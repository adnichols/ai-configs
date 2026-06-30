---
name: video-and-media-tools
description: "Work with video and media content: YouTube transcripts, ASCII video conversion, and GIF search."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, youtube, ascii, gif, media, transcript]
    related_skills: [audio-and-music-generation]
---

# Video and Media Tools

## YouTube Content

Extract transcripts, summarize videos, and convert them to threads or blog posts.

### Transcript Extraction
```bash
# Via yt-dlp (most reliable)
yt-dlp --skip-download --write-sub --sub-langs en --convert-subs srt "https://youtube.com/watch?v=..."

# Via youtube-transcript-api (Python)
from youtube_transcript_api import YouTubeTranscriptApi
transcript = YouTubeTranscriptApi.get_transcript("VIDEO_ID")
```

### Summarize
1. Extract transcript
2. Chunk into ~4000-token segments
3. Summarize each chunk
4. Synthesize into a single summary with key points and timestamps

### Convert to Blog Post
1. Summarize transcript
2. Restructure as narrative prose with headings
3. Add inline quotes and timestamps
4. Generate a title and meta description

### Convert to Twitter/X Thread
1. Extract 5–10 key points
2. Write each as a standalone tweet (≤280 chars)
3. Add thread numbering and hooks

## ASCII Video

Convert video/audio files to colored ASCII MP4 or GIF.

### Setup
```bash
pip install ascii-video
```

### Convert to ASCII MP4
```bash
ascii-video convert input.mp4 --output ascii.mp4 --cols 120 --fps 24
```

### Convert to ASCII GIF
```bash
ascii-video convert input.mp4 --output ascii.gif --cols 80 --fps 12 --duration 10
```

### Options
| Flag | Description |
|------|-------------|
| `--cols` | Number of ASCII columns |
| `--fps` | Output frame rate |
| `--duration` | Max duration in seconds |
| `--color` | Enable ANSI color |

### Use Cases
- Terminal demos
- Retro-style social media content
- Lightweight video previews

## GIF Search

Search and download GIFs from Tenor.

### Search
```bash
curl -s "https://g.tenor.com/v1/search?q=excited+cat&key=$TENOR_API_KEY&limit=10" | jq '.results[].media[0].gif.url'
```

### Download
```bash
curl -s -L -o reaction.gif "<gif-url>"
```

### Use Cases
- Slack/Discord reactions
- Documentation illustrations
- Social media content

### Pitfalls
- Tenor API requires an API key (free tier available)
- GIFs can be large; prefer MP4/WebP when possible
- Always respect copyright and content policies
