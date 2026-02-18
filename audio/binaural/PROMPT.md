# Audio Package - Audio Processing & Effects

## Overview
Post-processing for TTS-generated MP3 atoms. Adds effects, layers, and enhancements to make audio more immersive for hypnotic sessions.

---

## Features to Implement

### Audio Effects
- **Binaural beats** - Layered frequency differences for brainwave entrainment
- **Reverb/echo** - Spatial depth
- **Fade in/out** - Smooth transitions between atoms
- **Normalize volume** - Consistent loudness across atoms
- **Background ambience** - White noise, nature sounds, drones

### Binaural Beat Generation
- Theta (4-8 Hz) - Deep meditation/trance
- Alpha (8-14 Hz) - Relaxed focus
- Beta (14-30 Hz) - Alert/aroused states

### Layering
- Combine mantra + binaural beat
- Add background ambience to spoken content
- Multi-track mixing

---

## Tools

- **Python**: `pydub`, `librosa`, `soundfile`
- **CLI**: `ffmpeg` for format conversion and effects

---

## CLI Interface

```bash
# Add binaural beat to audio file
python audio.py add-binaural --input atom.mp3 --frequency 6 --output atom_theta.mp3

# Normalize volume
python audio.py normalize --input atom.mp3 --output atom_normalized.mp3

# Batch process directory
python audio.py batch-process --input-dir atoms/ --effects binaural,normalize
```

---

## Integration

- **Input**: Raw MP3 from `tts` package
- **Output**: Enhanced MP3 ready for CDN/session playback
