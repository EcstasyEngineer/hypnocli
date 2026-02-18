# TTS Renderer Recommendations

## Quick Reference

| Engine | Best For | Speed | Quality | GPU Required | Status |
|--------|----------|-------|---------|--------------|--------|
| **Kokoro** | Fast local TTS, hypnosis scripts | ~4.6x real-time (CPU) | Good | No | Working |
| **XTTS v2** | Voice cloning from samples | Slower | Excellent | Recommended | Ready |
| **VibeVoice** | Conversational, long-form | Medium | Good | Yes (6GB VRAM) | Partial |
| **Qwen3-TTS** | Voice design from text description | Medium | Good | Yes (6GB VRAM) | Needs SoX |
| **ElevenLabs** | Production quality | API-dependent | Excellent | No (cloud) | Working |

## Kokoro (Recommended for Most Use Cases)

**Voices:** 11 built-in presets
- American Female: `af_heart` (warm), `af_bella` (neutral), `af_nicole` (professional), `af_sarah` (friendly), `af_sky` (bright)
- American Male: `am_adam` (deep), `am_michael` (neutral)
- British: `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`

**Speed Control:**
```bash
python tts/render_kokoro.py script.txt output.wav --voice af_heart --speed 0.85
```
- Default: 1.0
- For hypnosis/relaxation: 0.8-0.9 recommended
- Range: 0.5-2.0

**Performance:**
- ONNX CPU: ~0.22 RTF (4.6x faster than real-time)
- PyTorch GPU: ~0.58 RTF (actually slower due to overhead)
- Recommendation: Use ONNX CPU version

**Script Markup:**
- Pause markers: `[500ms]`, `[1s]`, `[2000]` (ms default)
- HTML comments: `<!-- ignored -->`
- SSML tags: Stripped automatically (prosody, etc.)

**Best Practices:**
- Use `af_heart` at 0.85 speed for warm, relaxed delivery
- Keep segments under 500 chars for consistent quality
- Add explicit pauses between breathing exercises

## XTTS v2 (Voice Cloning)

For cloning specific voices (e.g., ElevenLabs Natasha):
```bash
python tts/render_xtts.py script.txt output.wav --speaker reference.wav
```

Requires a clean 6-15 second reference audio sample.

## Qwen3-TTS (Voice Design - REQUIRES SETUP)

**Features:**
- Text-based voice design ("A warm, gentle female voice...")
- Voice cloning from reference audio
- 9 built-in premium voices

**Setup Required:**
```bash
# Install SoX (required)
sudo apt-get install sox libsox-fmt-all

# For faster inference (strongly recommended)
pip install flash-attn --no-build-isolation
```

**Usage:**
```bash
# Voice design mode
python tts/render_qwen3.py script.txt output.wav --voice-design "A warm female voice speaking slowly"

# Custom voice preset
python tts/render_qwen3.py script.txt output.wav --speaker Ryan

# Voice cloning
python tts/render_qwen3.py script.txt output.wav --ref-audio ref.wav --ref-text "Transcription"
```

**Note:** Without flash-attn, model loading takes 15+ minutes. With flash-attn and GPU, much faster.

## VibeVoice (Experimental - ISSUES)

Microsoft's conversational TTS. Currently has issues with script formatting.

**Known Issues:**
- Stops early on complex scripts (EOS token triggered prematurely)
- Works better with simple, dialogue-formatted text
- Dependency conflicts with Qwen3-TTS (accelerate/transformers versions)

**Available Voices:**
- English: `en-Alice_woman`, `en-Carter_man`, `en-Frank_man`, `en-Maya_woman`
- Chinese: `zh-Xinran_woman`, `zh-Bowen_man`

```bash
python tts/render_vibevoice.py script.txt output.wav --voice en-Alice_woman
```

**Workaround:** For hypnosis scripts, use Kokoro instead.

## Common Issues

### Kokoro reads markup tags aloud
Fixed: SSML/prosody tags are now stripped automatically.

### Audio sounds rushed
Use `--speed 0.85` or lower for relaxation content.

### Qwen3-TTS fails with "sox not found"
Install SoX: `sudo apt-get install sox libsox-fmt-all`

### Qwen3-TTS model loading takes forever
Install flash-attn: `pip install flash-attn --no-build-isolation`

### VibeVoice produces only first sentence
Known issue with complex formatted scripts. Use simple text or switch to Kokoro.
