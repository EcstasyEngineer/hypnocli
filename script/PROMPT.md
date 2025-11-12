# Script Package - LLM-based Hypno Script Generation

## Overview
This package uses LLMs (OpenAI, Anthropic, Grok, or local models) to generate **content atoms** for hypnotic sessions:
- Short mantras (one-liners like "OBEY", "GOOD TOY")
- Script segments (inductions, deepeners, themed suggestions)

## Purpose
Generate the **source text** that will be converted to MP3 atoms via the `tts` package. These atoms are then sequenced by the `session` package and delivered via PWA.

---

## Features to Implement

### Atom Types
1. **Mantras** (1-5 words)
   - Simple, repeatable phrases
   - Tagged by theme (obedience, service, gratitude, etc.)
   - Example: "GOOD TOY", "OBEY AND SINK", "FOCUS ON MY WORDS"

2. **Inductions** (30-90 seconds when spoken)
   - Opening segments to establish trance
   - Progressive relaxation, fixation, confusion, etc.

3. **Deepeners** (15-45 seconds)
   - Intensify trance depth
   - Counting down, imagery, fractionation

4. **Suggestions** (30-120 seconds)
   - Themed content delivery
   - Behavior reinforcement, identity, sensation, etc.

5. **Transitions** (10-30 seconds)
   - Bridge between modalities
   - Example: gratitude→service transition script

### Metadata Schema
Each generated script should include:
```json
{
  "id": "uuid",
  "type": "mantra|induction|deepener|suggestion|transition",
  "theme": "obedience|service|gratitude|...",
  "modality": "current_state",
  "duration_estimate": "seconds",
  "intensity": 1-10,
  "text": "actual script content",
  "voice_hints": {
    "pace": "slow|medium|fast",
    "tone": "soft|firm|neutral"
  }
}
```

---

## LLM Integration Options

### Option 1: API-based (OpenAI, Anthropic, Grok)
- Use API for generation
- Store API keys in env vars
- Batch generate atoms

### Option 2: Local LLM (Ollama, etc.)
- Run local model for privacy
- Slower but free and private

### Option 3: Hybrid
- Use API for complex scripts (inductions, suggestions)
- Use templates + light generation for mantras

---

## Prompt Engineering

### Example Prompt for Mantras
```
Generate 20 short hypnotic mantras on the theme of "obedience".
Requirements:
- 1-5 words each
- Imperative voice
- Suitable for repetition
- Varied phrasing
Format as JSON array.
```

### Example Prompt for Induction
```
Write a 60-second progressive relaxation induction script.
Style: Soft, calming, directive.
Theme: Body relaxation leading to trance.
Format: Plain text, suitable for TTS.
```

---

## CLI Tool (Future)

```bash
# Generate mantras
python scriptgen.py generate-mantras --theme obedience --count 20

# Generate induction
python scriptgen.py generate-induction --style "progressive-relaxation" --duration 60

# Batch generate full theme pack
python scriptgen.py generate-theme-pack --theme service --output atoms/
```

---

## Integration Points

- **Input**: Theme, type, duration, intensity
- **Output**: JSON file with script + metadata
- **Next step**: Pass to `tts` package for MP3 generation
- **Storage**: Scripts saved to `atoms/` directory with metadata

---

## Notes

- Validate generated content for appropriateness/safety
- Consider content rating system (intensity levels)
- May want human review before TTS conversion
- Grok reportedly good at this - test it first
