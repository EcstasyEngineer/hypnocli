# TTS Package - Text-to-Speech Atom Generation

## Overview
Converts scripts (from `script` package) into MP3 audio files using AWS Polly or other TTS providers. Generates the **content atoms** that will be hosted on CDN and sequenced by the `session` package.

---

## Features

### TTS Provider Support
- **AWS Polly** (primary)
  - Neural voices available
  - SSML support for pacing/emphasis
  - Multiple language/accent options

- **Future**: ElevenLabs, Google Cloud TTS, Azure TTS (for voice variety)

### Voice Selection
- Soft/gentle voices for inductions
- Firm/directive voices for commands
- Variety for different themes/moods

### SSML Enhancement
Add Speech Synthesis Markup Language tags for:
- Pauses: `<break time="1s"/>`
- Emphasis: `<emphasis level="strong">OBEY</emphasis>`
- Pace: `<prosody rate="slow">relax and sink</prosody>`
- Pitch: `<prosody pitch="low">deeper now</prosody>`

---

## CLI Tool

```bash
# Convert single script to MP3
python tts.py generate --input script.json --output atoms/mantra_001.mp3 --voice Joanna

# Batch convert directory
python tts.py batch --input-dir scripts/ --output-dir atoms/ --voice Joanna

# List available voices
python tts.py list-voices --provider polly
```

---

## Metadata Preservation

Each MP3 should have accompanying metadata:
```json
{
  "audio_file": "atoms/mantra_obey_001.mp3",
  "script_id": "uuid-from-script-package",
  "theme": "obedience",
  "modality": "command",
  "duration": 3.2,
  "voice": "Joanna",
  "provider": "aws-polly"
}
```

---

## AWS Polly Setup

- Store AWS credentials in env vars or AWS config
- Use boto3 Python SDK
- Request format: Neural voices preferred
- Output format: MP3, 44.1kHz sample rate

---

## Integration

- **Input**: Script JSON from `script` package
- **Output**: MP3 file + metadata JSON
- **Next step**: Upload to CDN (future) or serve locally for testing
