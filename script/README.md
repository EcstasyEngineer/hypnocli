# Hypnosis Script Generator

Phase-based generator (`phase_chat_generator.py`) — generates a validated plan then writes each phase with structured context. Any OpenAI-compatible provider.

---

## Quick Start

```bash
python3 phase_chat_generator.py \
  --theme "deep relaxation with gentle obedience" \
  --style Permissive \
  --tone "warm, soothing, confident" \
  --variant standard \
  --duration "10 minutes" \
  --out_dir my_session
```

Outputs: `plan.json`, `structure.csv`, `script.txt`

---

## Model Recommendations

Evaluated Feb 2026, same theme/style across all runs. Reviewed by Claude Opus 4.6 and Codex. Because Claude served as reviewer, Gemini results are **less** susceptible to model self-preference bias.

**TL;DR: Use Gemini 3 Flash in phased mode.**

| Rank | Model | Mode | Lint | Verdict |
|------|-------|------|------|---------|
| 1 | **Gemini 3 Flash** | phased | 1 warning | Best fragment discipline, strongest object specificity, clean mantra delivery |
| 2 | **Gemini 3 Flash** | oneshot | 0 | Held structure in single call; P3 anaphora was best of all runs |
| 3 | **Claude Sonnet 4.6** | phased | 0 | Best trust ladder, most spec-compliant, zero violations |
| 4 | **Claude Haiku 4.5** | phased | 2 warnings | Surprisingly competitive with Sonnet; natural voice, good fragments. ~5x cheaper. |
| 5 | **Claude Sonnet 4.6** | oneshot | 0 | "Thinks out loud" in P4 — describes the trance instead of doing it |
| 6 | **Claude Haiku 4.5** | oneshot | 0 | Clean but compressed P5; planner occasionally hallucinates technique IDs |
| 7 | **xAI Grok** | phased | 3 warnings | Good countdown deepening; P1 announces the session structure (breaks immersion) |
| 8 | **xAI Grok** | oneshot | 0 | Compresses all phases into dense paragraphs; loses fragment discipline entirely |

**Cost vs quality:** Haiku at rank 4 costs roughly 5x less than Sonnet. For bulk generation or iteration, Haiku phased is the best value. Gemini is cheapest overall (Flash pricing) with the best output.

**Mode:** `--mode phased` (default) is strongly preferred over `--mode oneshot` for all models. Oneshot saves one API call but degrades fragment discipline and causes "thinking out loud" — the model comments on what it's doing rather than just doing it.

See `GENERATOR_EVALS.md` for full analysis, failure mode taxonomy, and lint gate docs.

---

## Providers

```bash
# Gemini (recommended)
--base_url gemini
# needs GEMINI_API_KEY in .env

# Anthropic (Sonnet or Haiku)
--base_url anthropic --model claude-sonnet-4-6
--base_url anthropic --model claude-haiku-4-5-20251001
# needs ANTHROPIC_API_KEY in .env

# xAI/Grok (adult content, no filtering)
--base_url xai
# needs LLM_API_KEY in .env

# OpenRouter (multi-provider)
--base_url openrouter --model anthropic/claude-sonnet-4-6
# needs LLM_API_KEY in .env

# Local
--base_url ollama --model llama3
--base_url lmstudio
```

`.env` file (repo root):
```
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
LLM_API_KEY=...        # xAI or OpenRouter
LLM_BASE_URL=gemini    # optional default provider
LLM_MODEL=...          # optional default model
```

---

## Flags

```
--theme       Theme/goal (required unless --plan provided)
--tone        Tone descriptor e.g. "calm, warm, hypnotic"
--style       Permissive | Authoritarian | Challenge | Mixed | Institutional | Character | Compulsion
--variant     standard | loop | twostage | series
--duration    "10 minutes" | "600" | "1200 words"
--optional    Comma-separated optional phases: "P7,P8,P9,P10,P11,P12"
--out_dir     Output directory (default: out)

--mode        phased (default) | oneshot
--tail_sentences  Lines of prior phase prose carried as context (default: 6, 0=none)
--lint_retry  Retry phase once on lint failure

--plan        Load existing plan.json, skip planning step
--base_url    Provider shortcut or full URL
--model       Model override
--api_key     API key override
--temperature_plan   Planning temperature (default: 0.2)
--temperature_write  Writing temperature (default: 0.8)
```

---

## Variants

| Variant | Arc | Use when |
|---------|-----|----------|
| `standard` | P1→P2→P3→P4→P5→P6 | Full session with emergence |
| `loop` | P1→P2→P3→P4→P13 (no wake) | Ambient/background, playlist looping |
| `twostage` | Induction → fractionation → suggestions | Complex programming, deep conditioning |
| `series` | Assumes prior conditioning | Sequel files, assumes existing anchors |

---

## Optional Phases

| Phase | Name | Use for |
|-------|------|---------|
| P7 | Safety/Consent | Explicit protective boundaries mid-session |
| P8 | Fractionation | Wake/sleep cycling for depth |
| P9 | Scenario Immersion | Detailed visualization layer |
| P10 | Trigger Installation | Conditioned response programming |
| P11 | Demonstration | Trigger activation, bliss, proof-of-depth |
| P12 | Behavioral Bridge | Real-world action commands |

```bash
--optional "P7,P9,P10"
```

---

## Lint Gate

Runs automatically after each phase. Warnings print to stderr but don't block output.

| Code | What it catches |
|------|----------------|
| LINT-01 | Sentences >20w in P3/P4/P8; >15w in P2 |
| LINT-02 | Future tense (`you'll/you will`) in non-P1 phases |
| LINT-03 | Banned phrases: honeyed, subconscious mind, serene rapture, peaceful empty, luminous |
| LINT-04 | Similes for states (`like a/an`, `as X as`) in P3/P4/P5/P8 |
| LINT-05 | Technique ID leaked into script text (e.g. `DEEP-03`) |
| LINT-06 | POV violations: "my voice", "this recording", "addicted to me" |
| LINT-07 | Announcing technique: "I'm going to suggest", "let these words sink in" |
| LINT-08 | Thinking out loud: meta-commentary in sub-cognitive phases |

`--lint_retry` triggers one blind re-roll on failure. For guided correction (feeding lint errors back into the prompt), see issue #45.

---

## Known Model Failure Modes

**xAI Grok — P1 roadmap announcement**
`"We'll ease into blank mind, deepen it, then plant suggestions, then bring you back"` — announces the technical structure in pre-talk, which breaks the fourth wall before trance begins.

**Claude Sonnet oneshot — thinking out loud**
In P4: `"The stillness isn't something you made — it was here already."` — philosophical commentary during a sub-cognitive phase. The model explains the trance instead of executing it.

**Claude Haiku — planning hallucinations**
Occasionally invents technique IDs (`CHECK-10`, etc.) that don't exist in the taxonomy, causing validation failure. Retry usually succeeds. Slightly higher planning temperature (`--temperature_plan 0.3`) may help.

**All models / oneshot — fragment collapse**
Single-call generation compresses phases into dense paragraphs. Deepening phases lose short-fragment discipline. Use phased mode.

---

## Reusing a Plan

Generate once, write multiple times (different temperatures, providers, etc.):

```bash
# Generate plan only — then edit it before writing
python3 phase_chat_generator.py --theme "..." --style Permissive \
  --tone "..." --duration "10 minutes" --out_dir run1

# Edit run1/plan.json, then reuse
python3 phase_chat_generator.py --plan run1/plan.json \
  --base_url gemini --out_dir run1_gemini

python3 phase_chat_generator.py --plan run1/plan.json \
  --base_url anthropic --model claude-haiku-4-5-20251001 --out_dir run1_haiku
```

---

## Legacy Generator

`compose_session.py` — freeform segment-based generator with explicit instruction fields. More manual control, no taxonomy validation.

```bash
python3 compose_session.py --json '{
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

Segment types: `pretalk`, `induction`, `deepener`, `conditioning`, `fractionation`, `posthypnotic`, `wakener`, `mantra`

Context modes: `full` (default, all prior segments visible), `last` (previous only), `none` (isolated)
