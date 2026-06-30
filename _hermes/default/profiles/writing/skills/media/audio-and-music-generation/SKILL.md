---
name: audio-and-music-generation
description: "Generate and analyze audio: AudioCraft music/sound, Suno-like song generation, audio spectrograms, and songwriting craft."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audio, music, generation, audiocraft, suno, spectrogram, songwriting]
    related_skills: []
---

# Audio and Music Generation

## AudioCraft (Meta)

Text-to-music and text-to-sound generation.

### MusicGen
```python
from audiocraft.models import MusicGen
model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(duration=10)  # seconds
wav = model.generate(["upbeat electronic dance music"])
```

### AudioGen
```python
from audiocraft.models import AudioGen
model = AudioGen.get_pretrained('facebook/audiogen-medium')
wav = model.generate(["dog barking in a park"])
```

### Save Output
```python
import torchaudio
torchaudio.save("output.wav", wav[0].cpu(), sample_rate=32000)
```

### Requirements
- CUDA recommended (CPU is very slow)
- `pip install audiocraft`

## HeartMuLa (Suno-like Song Generation)

Generate songs from lyrics + style tags.

### Prompt Structure
```
[Verse]
Lyrics here...

[Chorus]
More lyrics...

[Style]
upbeat pop, female vocals, electronic, 120bpm
```

### Generation
Use the `song_generation` tool (if available) or call the HeartMuLa API:
```bash
curl -X POST https://api.heartmula.com/v1/generate \
  -H "Authorization: Bearer $HEARTMULA_API_KEY" \
  -d '{"lyrics": "...", "style": "...", "duration": 120}'
```

### Pitfalls
- API credits are consumed per request; preview with short durations first
- Style tags must be comma-separated, lowercase
- Lyrics should include explicit structure markers (Verse, Chorus, Bridge)

## Songsee (Audio Analysis)

Generate spectrograms and extract audio features.

### Spectrogram
```bash
songsee spectrogram audio.wav --output spectrogram.png
```

### Features
```bash
songsee features audio.wav --output features.json
```

### Python API
```python
import librosa
y, sr = librosa.load("audio.wav")
mel = librosa.feature.melspectrogram(y=y, sr=sr)
chroma = librosa.feature.chroma_stft(y=y, sr=sr)
mfcc = librosa.feature.mfcc(y=y, sr=sr)
```

### Use Cases
- Compare generated vs reference audio
- Detect anomalies in recordings
- Extract features for ML training

## Songwriting Craft

### Verse-Chorus Structure
| Section | Purpose | Length |
|---------|---------|--------|
| Intro | Set mood | 4–8 bars |
| Verse | Tell story | 8–16 bars |
| Pre-Chorus | Build tension | 4–8 bars |
| Chorus | Main hook | 8 bars |
| Bridge | Contrast | 8 bars |
| Outro | Resolution | 4–8 bars |

### Prompt Engineering for AI Music
1. **Be specific about genre:** "indie folk" > "folk"
2. **Reference BPM and key:** "120bpm, C major"
3. **Describe instrumentation:** "acoustic guitar, light drums, strings"
4. **Mood descriptors:** "melancholic but hopeful"
5. **Vocal style:** "female whisper vocals, close-mic"

### Pitfalls
- AI music tools struggle with complex time signatures; stick to 4/4
- Long songs (>3 min) often degrade in coherence; generate in segments
- Always check generated audio for artifacts before publishing
