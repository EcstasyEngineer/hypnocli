# Video Package - Session Video Composition

## Overview
Combines visuals (from `gifmaker`) with audio (from `audio` package) to create complete hypnotic session videos.

---

## Features

### Video Composition
- Combine GIF loops with audio tracks
- Sync visual timing to audio duration
- Add fade in/out effects
- Support multiple aspect ratios (square, wide, tall from gifmaker)

### Output Formats
- MP4 (web/social media)
- WebM (web optimized)
- Formats suitable for VR (future: side-by-side 360°)

---

## Tools

- **ffmpeg** - Primary video processing tool
- **Python wrapper**: `ffmpeg-python` or subprocess calls

---

## CLI Interface

```bash
# Combine GIF + audio
python video.py compose --visual input.gif --audio session_audio.mp3 --output session.mp4

# Batch generate sessions
python video.py batch --visuals-dir gifs/ --audio-dir audio/ --output-dir sessions/

# Add fade effects
python video.py compose --visual input.gif --audio audio.mp3 --fade-in 2 --fade-out 3 --output session.mp4
```

---

## Example ffmpeg Command
```bash
ffmpeg -stream_loop -1 -i visual.gif -i audio.mp3 -shortest -c:v libx264 -c:a aac -pix_fmt yuv420p output.mp4
```

---

## Integration

- **Input**: GIF from `gifmaker`, MP3 from `audio` package
- **Output**: MP4 video file ready for distribution
- **Future**: Integrate with `session` package for full pipeline automation
