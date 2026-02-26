# CLAUDE.md — hypnocli

## What This Repo Is

**hypnocli** is the upstream script authoring and audio production toolkit. It produces:
- Hypnosis scripts (generated via LLM from taxonomy + phase templates)
- Rendered audio modules (TTS → trimmed opus files)
- Binaural/isochronic audio layers (mixed separately)
- Analysis tools (snap detection, binaural analysis, TTS validation)

It does **not** handle user personalization, delivery scheduling, playlists, or Discord integration. Those belong downstream in conditioner.

## Upstream/Downstream Relationship

```
hypnocli (this repo)
  ├── script authoring (taxonomy, phase generator, quality guides)
  ├── TTS rendering (render_gemini.py, render_polly.py, etc.)
  ├── audio production (binaural.py, SFX pipeline)
  └── produces: audio files, scripts, fragments

        ↓ ships audio files to

conditioner (EcstasyEngineer/conditioner)
  ├── Discord bot — delivers modules to listeners in voice channels
  ├── mantra system — personalized text delivery with {subject}/{controller}
  ├── playlist sequencing — module ordering, transitions
  └── user profiles — subject, controller, themes, scheduling
```

**Decision rule:** If it requires knowing who the listener is, it belongs in conditioner. If it's about producing content, it belongs here.

Things that look like they belong here but don't:
- Template variable substitution ({subject}, {controller}) — conditioner already does this
- Playlist ordering logic — conditioner issue #73
- Audio fragment stitching by user profile — conditioner issue #74

## Key Directories

| Path | Purpose |
|------|---------|
| `script/` | Taxonomy, phase templates, script quality guides, generator |
| `script/modules/` | Per-module plan.json + script.txt + structure.csv |
| `audio/tts/` | TTS renderer scripts (Gemini, Polly, ElevenLabs, etc.) |
| `audio/binaural/` | Binaural/isochronic generator + snap/binaural analyzers |
| `scratch/tts_validation/` | Whisper-based TTS validation pipeline |
| `scratch/tts_validation/audio/` | Downloaded opus files (from borg) |
| `scratch/tts_validation/trimmed/` | Silence-trimmed versions |
| `scratch/tts_validation/transcripts/` | Cached whisper transcriptions |

## Common Commands

```bash
# Generate a script from a plan
python3 script/phase_chat_generator.py script/modules/obedience/plan.json

# Render a script to audio (Gemini TTS)
# Use "speak in a soft, measured, hypnotic tone" — NOT "whisper"
python3 audio/tts/render_gemini.py script.txt output.opus \
  --voice Kore --instruct "speak in a soft, measured, hypnotic tone"

# Validate TTS renders (pull from borg, transcribe, gap-detect)
cd scratch/tts_validation
python3 validate_tts.py                        # all modules
python3 validate_tts.py resistance --trim 2.0  # trim gaps > 2s
python3 validate_trimmed.py                    # re-validate trimmed

# Binaural generation
python3 audio/binaural/binaural.py --preset bimbo-drone output.wav

# Snap analysis
python3 analysis/snap_analyzer.py audio.wav --audacity
```

## TTS Rendering Notes

- **Voice**: Kore (default for modules). Kore renders with a commanding, measured tone.
- **Instruct string**: `"speak in a soft, measured, hypnotic tone"` — never use "whisper"
- **Timing markers** (`[400]`, `[1s]`): `render_gemini.py` currently converts these to `...` which causes Kore to trail off into silence. This is a known bug and the root cause of the silence bloat issue in the Feb 2026 renders. Strip timing markers to nothing before sending to TTS.
- **SSML tags** (`<prosody>`): Strip before sending — Gemini TTS does not use SSML.
- **Silence bloat**: Validated via `scratch/tts_validation/validate_tts.py`. See TTS validation issue #55.

## Script Quality

The current module scripts (Feb 2026 batch) are solid on technique coverage but share structural weaknesses:
- One emotional register throughout — no texture from persona variation
- P5 repetition is metered (3x) rather than driven to automatic reflex (7-10x minimum for the deepest mantra)
- P13 lands gracefully rather than genuinely looping
- Cognitive load is *described* poetically rather than *generated* structurally

See the Pink Curse analysis (`C:\Mega\ToyMaker\Case Studies\curse_analysis\pink_curse_full_analysis.md`) for the production quality benchmark.

## Python Environment

- Use `python3` (not `python`)
- numpy, scipy, librosa, pydub, whisper available
- GPU available (RTX 5070 Ti) — use `--device cuda` for whisper

## GitHub

Repo: `EcstasyEngineer/hypnocli`
Account: EcstasyEngineer (verify with `gh auth status` before any `gh` command)
