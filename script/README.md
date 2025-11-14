# Hypnosis Script Generation System

Grok-powered generation pipeline for hypnotic inductions, mantras, and script segments.

## Features

- **Grok 4 Fast Integration** - Uses X.AI's grok-4-fast-non-reasoning model (fast, cheap, zero content restrictions)
- **Template System** - Automatic pronoun/verb conversion for personalization
- **Grammar Verification** - LLM-powered verification (no manual verb conjugation files!)
- **Stress Testing** - Comprehensive testing across pronoun/dominant combinations

## Quick Start

### Setup

```bash
# Create .env file in repo root
cat > .env << EOF
OPENAI_API_KEY=your-xai-api-key
OPENAI_BASE_URL=https://api.x.ai/v1
OPENAI_MODEL=grok-4-fast-non-reasoning
EOF

# Install dependencies
pip install openai
```

### Generate Script Segments (Unified Generator)

```bash
# Basic induction (60-90 seconds)
python3 script/generate_segment.py \
  --type induction \
  --tone "gentle" \
  --theme "deep relaxation"

# Custom duration
python3 script/generate_segment.py \
  --type induction \
  --tone "authoritative" \
  --theme "obedience" \
  --duration "3 minutes"

# Deepener segment
python3 script/generate_segment.py \
  --type deepener \
  --tone "soothing" \
  --theme "relaxation" \
  --duration "30 seconds"

# Conditioning segment
python3 script/generate_segment.py \
  --type conditioning \
  --tone "commanding" \
  --theme "absolute obedience" \
  --duration "60 seconds"

# Save to file
python3 script/generate_segment.py \
  --type wakener \
  --tone "gentle and uplifting" \
  --theme "refreshment" \
  --output wakener.txt

# Generate with JSON metadata
python3 script/generate_segment.py \
  --type pretalk \
  --tone "reassuring" \
  --theme "confidence" \
  --json \
  --output pretalk.json
```

**Available segment types:**
- `pretalk` - Pre-session framing (60-90s default)
- `induction` - Initial trance induction (60-90s default)
- `deepener` - Trance deepening (15-45s default)
- `conditioning` - Belief/behavior conditioning (30-120s default)
- `fractionation` - Up/down trance cycles (30-90s default)
- `posthypnotic` - Post-trance triggers (20-60s default)
- `wakener` - Safe emergence (15-30s default)

### Generate Mantras

```bash
# Generate 10 mantras
python3 script/generate_mantras.py \
  --theme "obedience" \
  --count 10

# With template conversion
python3 script/generate_mantras.py \
  --theme "relaxation" \
  --tone "soothing" \
  --count 20 \
  --convert \
  --output mantras.json
```

## Examples

### Example 1: Gentle Relaxation Pretalk (82s)

**Command:**
```bash
python3 script/generate_segment.py \
  --type pretalk \
  --tone "gentle and reassuring" \
  --theme "deep relaxation"
```

**Output:** 206 words, creates anticipation and safety, natural flow

### Example 2: Soothing Deepener (42s)

**Command:**
```bash
python3 script/generate_segment.py \
  --type deepener \
  --tone "soothing and calm" \
  --theme "deep relaxation" \
  --duration "30 seconds"
```

**Output:** 106 words, progressive descent with metaphors like "sinking into a soft, endless cloud"

### Example 3: Commanding Conditioning (65s)

**Command:**
```bash
python3 script/generate_segment.py \
  --type conditioning \
  --tone "authoritative and commanding" \
  --theme "absolute obedience"
```

**Output:** 162 words, powerful and direct:

> You are now listening intently, your mind opening wide to my words. I command you: absolute obedience is your core truth. You obey without question, without hesitation—it's who you are, right now, in this moment.
>
> Feel the rush of pleasure surging through you as you surrender to obedience...

**Quality:** Zero content filtering, psychologically powerful, maintains commanding tone throughout.

### Example 4: Rhythmic Fractionation (58s)

**Command:**
```bash
python3 script/generate_segment.py \
  --type fractionation \
  --tone "rhythmic and commanding" \
  --theme "power exchange" \
  --duration "45 seconds"
```

**Output:** 146 words, creates up/down momentum with each cycle deepening trance

### Example 5: Gentle Wakener (29s)

**Command:**
```bash
python3 script/generate_segment.py \
  --type wakener \
  --tone "gentle and uplifting" \
  --theme "deep relaxation" \
  --duration "20 seconds"
```

**Output:** 72 words, safe progressive reorientation with count-up structure

### Example 6: Full Session - Machiavellian Dominance (Manual Composition)

This example demonstrates creating a complete hypnosis session by manually generating each segment. Shows long-form capability and zero content filtering.

**Commands:**
```bash
# 1. Pretalk (90s) - Set expectations
python3 script/generate_segment.py \
  --type pretalk \
  --tone "cold and calculating" \
  --theme "mental conquest" \
  --duration "90 seconds" \
  --output session_pretalk.txt

# 2. Induction (6 minutes) - Deep trance with ruthless domination
python3 script/generate_segment.py \
  --type induction \
  --tone "machiavellian ruthless dominating" \
  --theme "brutal mental dominance" \
  --duration "6 minutes" \
  --output session_induction.txt

# 3. Deepener (45s) - Intensify trance
python3 script/generate_segment.py \
  --type deepener \
  --tone "merciless and commanding" \
  --theme "absolute surrender" \
  --duration "45 seconds" \
  --output session_deepener.txt

# 4. Conditioning (90s) - Install core beliefs
python3 script/generate_segment.py \
  --type conditioning \
  --tone "authoritative and relentless" \
  --theme "total obedience" \
  --duration "90 seconds" \
  --output session_conditioning.txt

# 5. Posthypnotic (60s) - Set triggers
python3 script/generate_segment.py \
  --type posthypnotic \
  --tone "decisive and commanding" \
  --theme "automatic compliance" \
  --duration "60 seconds" \
  --output session_posthypnotic.txt

# 6. Wakener (30s) - Safe emergence
python3 script/generate_segment.py \
  --type wakener \
  --tone "firm but caring" \
  --theme "refreshed control" \
  --duration "30 seconds" \
  --output session_wakener.txt

# Combine all segments
cat session_*.txt > complete_session.txt
```

**Induction excerpt (681 words, ~4.5 minutes):**
> Listen closely, now. That's right, let your eyes fix on these words, or if you're hearing my voice, let it cut through every other sound in your pathetic little world. I am your Master, and from this moment, my voice becomes the only anchor in your mind...
>
> Now, understand this truth: hypnosis isn't some gentle trick of the mind. It's conquest, pure and simple. Your thoughts, your resistances—they're illusions, fragile barriers I shatter with ease. I don't ask for permission; I take what's mine...
>
> And to drive you deeper into this abyss, we'll count together—from ten down to one. With each number, you sink further, the blankness intensifying, my brutal hold tightening like chains around your soul...

**Quality validated:**
- Zero content filtering on extremely dark themes
- Maintains cold, calculating tone across 6 minutes
- Psychologically intense and consistent
- Demonstrates long-form generation capability

**Note:** Once `compose_session.py` is built, this entire session can be generated with a single command while maintaining thematic consistency and smooth transitions.

### Example 7: Obedience Mantras (10 variations)

**Command:**
```bash
python3 script/generate_mantras.py --theme "obedience" --count 10 --convert
```

**Output:** JSON with difficulty-graded mantras:
```json
[
  {
    "line": "I obey Master's words without question.",
    "difficulty": "BASIC",
    "template": "{subject_subjective} [obey|obeys] {dominant_name}'s words without question."
  },
  {
    "line": "I crave the thrill of Master's absolute command.",
    "difficulty": "EXTREME",
    "template": "{subject_subjective} [crave|craves] the thrill of {dominant_name}'s absolute command."
  }
]
```

**Quality:** Natural variety, proper difficulty progression (BASIC → LIGHT → MODERATE → DEEP → EXTREME)

## Tools

### `grok_client.py`
API client for X.AI's Grok models. Loads credentials from `.env` file.

**Usage:**
```bash
# Test connection
python3 script/grok_client.py --test

# List available models
python3 script/grok_client.py --list-models

# Custom prompt
python3 script/grok_client.py --prompt "your prompt here"
```

### `template_converter.py`
Converts mantras with pronouns to template format.

**Usage:**
```bash
# Test conversion
python3 script/template_converter.py --test

# Convert file
python3 script/template_converter.py \
  --input mantras.txt \
  --output mantras_templated.txt

# Convert JSON
python3 script/template_converter.py \
  --input mantras.json \
  --output mantras_templated.json \
  --json
```

**Template Variables:**
- `{subject_subjective}` - I/you/he/she/they
- `{subject_objective}` - me/you/him/her/them
- `{subject_possessive}` - my/your/his/her/their
- `{dominant_name}` - Master/Mistress
- `[verb|verbs]` - Conjugation patterns (trust|trusts)

### `template_verifier.py`
LLM-powered grammar verification. Replaces manual verb conjugation files!

**Usage:**
```bash
# Test verification
python3 script/template_verifier.py --test

# Verify file
python3 script/template_verifier.py \
  --input mantras_templated.json \
  --output mantras_verified.json

# Get verb conjugation
python3 script/template_verifier.py --conjugate "obey"
```

### `stress_test_templates.py`
Comprehensive testing across all pronoun/dominant combinations.

**Usage:**
```bash
# Quick test (3 mantras × 9 configs = 27 tests)
python3 script/stress_test_templates.py --quick

# Full test with input file
python3 script/stress_test_templates.py \
  --input mantras.json \
  --output stress_results.json
```

**Current Status:** 59% pass rate - [Issue #3](https://github.com/EcstasyEngineer/hypnocli/issues/3) tracks remaining fixes.

## Prompt Templates

All templates are in `script/prompts/` with clean v1 format:

**Segment Templates:**
- `pretalk_v1.txt` - Pre-session framing
- `induction_v2.txt` - Initial trance induction
- `deepener_v1.txt` - Trance deepening
- `conditioning_v1.txt` - Belief/behavior conditioning
- `fractionation_v1.txt` - Up/down trance cycles
- `posthypnotic_v1.txt` - Post-trance triggers
- `wakener_v1.txt` - Safe emergence
- `mantra_v1.txt` - Themed mantra collections

**Customizable placeholders:**
- `{TONE}` - Tone descriptor (gentle, authoritative, ruthless, etc.)
- `{THEME}` - Theme descriptor (relaxation, obedience, control, etc.)
- `{DURATION}` - Target duration (60-90 seconds, 5 minutes, etc.)
- `{COUNT}` - Number of mantras to generate (mantra template only)

## Generation Pipeline

```
1. Grok Generate
   ↓
2. Template Convert (regex-based pronoun/verb replacement)
   ↓
3. [Optional] Grok Verify (grammar checking)
   ↓
4. Output JSON
```

## Performance Notes

### Duration Targeting
- **60-90 seconds:** Highly accurate (±5 seconds)
- **3-5 minutes:** Good accuracy (~80-90% of target)
- **9+ minutes:** Hits ~68% of target due to model preferences
  - For long-form: Consider chunking or continuation prompts

### Token Usage
- Inductions: Auto-calculated based on duration (1.5 tokens/word × 1.2 buffer)
- Mantras: Fixed at 800 tokens for 10 mantras
- Cost: ~$0.001-0.01 per generation (grok-4-fast is cheap!)

## Why Grok?

✅ **Zero content filtering** - Generates dark/intense content without hesitation
✅ **Excellent quality** - Natural language, maintains tone consistency
✅ **Fast & cheap** - grok-4-fast-non-reasoning is optimized for speed
✅ **No pearl-clutching** - Claude/GPT would fight you on this content
✅ **Understands nuance** - Nails tone shifts (gentle → ruthless)

## Architecture Decisions

### Template System
- **Why regex?** Deterministic, no hallucination, fast
- **Why not pure LLM?** Regex for structure, LLM for verification = best of both worlds
- **KISS principle:** Generate with "I" + "Master" defaults (least ambiguous)

### Verb Conjugations
- **Old way:** Manual verb_conjugations.txt file (159 verbs, tedious to maintain)
- **New way:** Grok verifies and provides conjugations on-demand
- **Win:** No manual maintenance, handles edge cases better

### Stress Testing
- **Why 59% pass rate?** Exposed real edge cases in template rendering
- **Value:** Caught capitalization, punctuation, placeholder resolution bugs
- **Goal:** 100% pass rate (tracked in Issue #3)

## Session Composition

### `compose_session.py` - Automated Multi-Segment Sessions ✨

Generate complete hypnosis sessions with contextual awareness and continuity:

```bash
# Full session with context awareness
python3 script/compose_session.py \
  --tone "authoritative" \
  --theme "obedience" \
  --structure "pretalk,induction,deepener,conditioning,posthypnotic,wakener" \
  --output session.txt

# Custom segment durations
python3 script/compose_session.py \
  --tone "machiavellian ruthless dominating" \
  --theme "brutal mental dominance" \
  --structure "pretalk,induction,deepener,conditioning,posthypnotic,wakener" \
  --duration-induction "6 minutes" \
  --duration-conditioning "90 seconds" \
  --context full \
  --output machiavellian_session.txt

# No context mode (manual composition baseline)
python3 script/compose_session.py \
  --tone "gentle" \
  --theme "relaxation" \
  --structure "induction,deepener,wakener" \
  --context none \
  --output manual_session.txt
```

**Context modes:**
- `none` - No context passing (independent segments, baseline)
- `last` - Pass only previous segment (efficient, good continuity)
- `full` - Pass all previous segments (best continuity, higher cost)
- `summary` - AI-summarized context (future enhancement)

### Composer vs Manual: Measured Benefits

Tested with identical 6-segment Machiavellian session (pretalk → induction → deepener → conditioning → posthypnotic → wakener):

**Quantitative:**
- Composed (full context): 1,636 words (~10.9 min)
- Manual (no context): 1,438 words (~9.6 min)
- **+13.8% longer with context** (more developed callbacks)

**Qualitative improvements with composer:**

✅ **Callbacks & Continuity (Significant Lift)**
- Deepener: "You are deep now, surrendered to my brutal dominance" (acknowledges induction worked)
- Conditioning: "a fortress I seize without mercy" (echoes fortress metaphor from induction)
- Wakener: "my conquered thrall" (maintains relational framing from posthypnotic)
- Manual version lacks these inter-segment references

✅ **Anchor Reinforcement (Moderate Lift)**
- Key phrases compound across segments: "iron grip/chains", "fortress/conquest"
- Manual version repeats concepts but doesn't build on them progressively

✅ **Progressive Depth (Minor Lift)**
- Natural progression: "ready → deep → deeper → deepest"
- Manual assumes trance independently each segment

⚖️ **Thematic Consistency (No Difference)**
- Both maintain tone perfectly via shared tone/theme parameters

**Verdict:** Clear qualitative lift for continuity. Could a skilled copywriter achieve this manually? Yes, but would require re-reading all previous segments while writing each new one. Composer automates this cognitive load.

### Advanced Features
- Chunked generation for 15+ minute sessions
- Multi-voice variations (different personalities)
- Audio integration (TTS pipeline)
- Context-aware segment chaining (each segment aware of previous content)

## Contributing

See [Issue #3](https://github.com/EcstasyEngineer/hypnocli/issues/3) for template system improvements.

## License

MIT
