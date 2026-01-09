# Hypnosis Script Generator

Generate complete hypnosis sessions using any OpenAI-compatible LLM. Consistent tone, contextual awareness across segments.

---

## New: Phase-Based Generator (v5.1 Taxonomy)

The new `phase_chat_generator.py` uses a structured taxonomy with validated phases and techniques. It generates a plan first, then writes each phase with full context.

### Quick Start

```bash
python3 phase_chat_generator.py \
  --theme "deep relaxation with gentle obedience" \
  --style Permissive \
  --tone "warm, soothing, confident" \
  --variant standard \
  --duration "10 minutes" \
  --optional "P7,P9" \
  --out_dir my_session
```

### Variants

| Variant | Description |
|---------|-------------|
| `standard` | Full arc: P1→P2→P3→P4→P5→P6 (context, induction, deepening, cognitive reduction, suggestions, emergence) |
| `loop` | No emergence, loops via P13 for ambient/background content |
| `twostage` | Fractionation between suggestion layers for complex programming |
| `series` | Assumes prior conditioning, uses instant induction |

### Optional Phases

Add with `--optional "P7,P9,P10"`:
- **P7** Safety/Consent - protective boundaries after context
- **P8** Fractionation - wake/sleep cycling for depth
- **P9** Scenario Immersion - detailed visualization
- **P10** Trigger Installation - conditioned responses
- **P11** Demonstration - trigger activation, bliss, proof
- **P12** Behavioral Bridge - real-world action commands

### Using an Existing Plan

Skip the planning step by providing a plan.json:

```bash
# Edit plan.json to customize phases, techniques, durations...
python3 phase_chat_generator.py --plan my_plan.json --out_dir out
```

### Outputs

- `plan.json` - Phase structure with technique IDs
- `structure.csv` - Timeline view
- `script.txt` - Full script with phase markers

### Reference

See `hypnosis_taxonomy.md` for complete phase and technique documentation.

---

## Legacy: Segment-Based Generator

The original `compose_session.py` offers more freeform control with rich instruction fields. See examples in `examples/`.

---

## Setup

```bash
pip install openai

# Create .env file in repo root
cat > .env << 'EOF'
# Provider shortcuts: openai, xai, openrouter, ollama, lmstudio
# Or use a full URL for other providers
LLM_API_KEY=your-api-key
LLM_BASE_URL=xai
LLM_MODEL=grok-4-0414
EOF
```

**Provider shortcuts:**
- `openai` → https://api.openai.com/v1
- `xai` → https://api.x.ai/v1 (Grok)
- `openrouter` → https://openrouter.ai/api/v1
- `ollama` → http://localhost:11434/v1
- `lmstudio` → http://localhost:1234/v1

## Quick Start

Generate a complete session:

```bash
python3 script/compose_session.py --json '{
  "tone": "commanding sadistic",
  "instructions": "GENDER NEUTRAL language. SHOW DONT TELL.",
  "segments": [
    {"type": "pretalk", "additional_instructions": "consent and session preview", "duration": "2min"},
    {"type": "induction", "additional_instructions": "focus and trance", "duration": "4min"},
    {"type": "deepener", "additional_instructions": "sinking deeper", "duration": "2min"},
    {"type": "conditioning", "additional_instructions": "pleasure-obedience linking", "duration": "8min"},
    {"type": "wakener", "additional_instructions": "gentle awakening, refreshed"}
  ]
}' --output session.txt
```

**Note:** Every segment will see "GENDER NEUTRAL language. SHOW DONT TELL." plus their own specific instructions.

## JSON Schema

**Required fields:**
- `tone` - Overall tone (e.g., "gentle caring", "commanding sadistic")
- `segments` - Array of segment objects

**Each segment requires:**
- `type` - Segment type (see below)
- `additional_instructions` - Segment-specific task (added to global instructions)

**Optional per segment:**
- `tone_override` - Replace global tone for this segment only
- `duration` - Target length (e.g., "2min", "30 seconds", "500 words")

**Optional global:**
- `instructions` - Global instructions **prepended to ALL segments** (style guides, content rules, etc.)
- `context_mode` - How segments reference each other (default: "full")
- `temperature` - AI creativity (default: 0.8)

### Important: How Instructions Work

**Global `instructions` are ALWAYS prepended to every segment's `additional_instructions`:**

```json
{
  "instructions": "GENDER NEUTRAL (throb/ache, NO cock/pussy). SHOW DON'T TELL.",
  "segments": [
    {"type": "induction", "additional_instructions": "progressive relaxation"}
  ]
}
```

The induction prompt sees:
```
GENDER NEUTRAL (throb/ache, NO cock/pussy). SHOW DON'T TELL.

Segment-specific additions: progressive relaxation
```

**Global `instructions` (prepended to all):**
- Style guides (gender-neutral, show don't tell)
- Content rules (avoid certain words, metaphor preferences)
- F4A (for all audiences) guidance
- Session-wide themes

**Segment `additional_instructions` (added per segment):**
- Specific tasks ("countdown 10 to 1", "JOI call/response #1")
- Segment-unique content that builds on global rules

**Segment `tone_override` (replaces global tone):**
- Use when you want a different tone for just one segment
- Fully replaces the global tone (not additive)

## Segment Types

| Type | Purpose | Default Duration |
|------|---------|------------------|
| `pretalk` | Pre-session framing, consent, expectations | 60-90s |
| `induction` | Initial trance induction | 60-90s |
| `deepener` | Trance deepening | 15-45s |
| `conditioning` | Belief/behavior programming | 30-120s |
| `fractionation` | Up/down trance cycles | 30-90s |
| `posthypnotic` | Post-trance triggers | 20-60s |
| `wakener` | Safe emergence from trance | 15-30s |
| `mantra` | Repetitive affirmations | 30-60s |

## Examples

### Dynamic Tone Shifting

Mix tones within a session for emotional variety:

```bash
python3 script/compose_session.py --json '{
  "tone": "commanding",
  "segments": [
    {"type": "pretalk", "additional_instructions": "consent and safety", "tone_override": "gentle caring"},
    {"type": "induction", "additional_instructions": "progressive relaxation"},
    {"type": "conditioning", "additional_instructions": "obedience triggers", "tone_override": "seductive teasing"},
    {"type": "wakener", "additional_instructions": "refreshed and alert", "tone_override": "warm encouraging"}
  ]
}' --output dynamic_session.txt
```

### Long Session with Anchors

For sessions with triggers/anchors referenced across segments, use full context mode (default):

```bash
python3 script/compose_session.py --json '{
  "tone": "commanding sadistic",
  "context_mode": "full",
  "segments": [
    {"type": "induction", "additional_instructions": "establish DROP anchor", "duration": "5min"},
    {"type": "deepener", "additional_instructions": "reinforce DROP anchor", "duration": "2min"},
    {"type": "conditioning", "additional_instructions": "pleasure on DROP command", "duration": "10min"},
    {"type": "deepener", "additional_instructions": "test DROP anchor effectiveness", "duration": "2min"},
    {"type": "wakener", "additional_instructions": "DROP anchor stays active"}
  ]
}' --output anchor_session.txt
```

With `context_mode: "full"`, later segments remember the "DROP" anchor from earlier segments.

### Complex Multi-Phase Session

```bash
python3 script/compose_session.py --json '{
  "tone": "commanding sadistic",
  "segments": [
    {"type": "pretalk", "additional_instructions": "JOI mindwipe session preview", "duration": "2min"},
    {"type": "induction", "additional_instructions": "focus on my voice, JOI trance beginning", "duration": "4min"},
    {"type": "deepener", "additional_instructions": "sinking deeper, obedience growing", "duration": "2min"},
    {"type": "conditioning", "additional_instructions": "pleasure=obedience linking, tease/denial intro", "duration": "8min"},
    {"type": "deepener", "additional_instructions": "total surrender, blank mindlessness", "duration": "2min"},
    {"type": "conditioning", "additional_instructions": "JOI call/response #1, severity ramp", "duration": "10min"},
    {"type": "deepener", "additional_instructions": "void of obedience, no thoughts remain", "duration": "2min"},
    {"type": "conditioning", "additional_instructions": "EXTREME tease/denial, beg to be rewritten", "duration": "12min"},
    {"type": "wakener", "additional_instructions": "PARTIAL wakener - new entity awakens", "duration": "3min"}
  ]
}' --output complex_session.txt
```

## Context Modes

Controls how segments reference each other:

- **`full`** (default) - Each segment sees all previous segments
  - Use for: Sessions with anchors/triggers, long sessions, narrative arcs
  - Why: Segment 15 can reference an anchor from segment 2

- **`last`** - Each segment sees only the previous segment
  - Use for: Short sessions, when you want looser connections
  - Why: More efficient, lighter context

- **`none`** - Segments are completely independent
  - Use for: Testing, generating unrelated segments
  - Why: No continuity, baseline mode

**Recommendation:** Use `full` unless you have a specific reason not to. The cost difference is negligible and continuity is worth it.

## Single Segments

Generate individual segments for testing or manual composition:

```bash
python3 script/generate_segment.py \
  --type conditioning \
  --tone "commanding" \
  --instructions "pleasure-obedience linking, tease/denial" \
  --duration "5min" \
  --output conditioning.txt
```

## Provider Notes

**xAI/Grok** - Recommended for adult content
- Zero content filtering
- Cheap (~$0.001-0.01 per script)
- Fast reasoning models available

**OpenRouter** - Multi-provider access
- Route to various models with one API key
- Some models have content policies

**Local (Ollama/LM Studio)** - Private, no filtering
- Requires local model setup
- No API costs, runs on your hardware

## Advanced

### JSON Config File

For complex sessions, use a config file:

```bash
# Create config
cat > session.json << 'EOF'
{
  "tone": "gentle encouraging",
  "instructions": "deep relaxation and self-care",
  "duration": "60 seconds",
  "segments": [
    {"type": "induction", "duration": "5min"},
    {"type": "deepener"},
    {"type": "conditioning", "instructions": "confidence and self-worth"},
    {"type": "wakener", "tone": "warm uplifting"}
  ]
}
EOF

# Generate
python3 script/compose_session.py --config session.json --output session.txt
```

### Validation

Invalid JSON gets helpful error messages:

```bash
$ python3 script/compose_session.py --json '{"segments": [{"type": "induction"}]}'

[error] Missing required field 'tone'
[info] Expected JSON schema: {...}
[info] Example with tone overrides: {...}
```

## Troubleshooting

**Duration too short/long?**
- Grok targets 150 words/minute spoken
- For precise timing, specify duration in words: `"duration": "500 words"`

**Need different personalities?**
- Use tone overrides per segment
- Mix tones: "gentle caring" → "commanding" → "warm encouraging"

**Segments feel disconnected?**
- Use `context_mode: "full"` (default)
- Add specific instructions referencing previous content

**Content too repetitive?**
- Vary your instructions per segment
- Be specific: "JOI call/response #1" vs "JOI call/response #2, more intense"

## License

MIT
