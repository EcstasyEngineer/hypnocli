#!/usr/bin/env python3
"""
phase_chat_generator.py
-----------------------

Production-oriented, phase-based hypnosis script generator using a *conversation interface*.

Design goals:
- Single-file orchestration (no extra modules required besides `openai`).
- Plan-first: generate a validated phase plan (structure + technique IDs + parameters).
- Write-per-phase: each phase is generated in its own chat turn, where the *guidance for the next phase*
  is sent as a new USER message, chained into the ongoing conversation.
- Provider-agnostic: works with any OpenAI-compatible endpoint (OpenAI, xAI/Grok, OpenRouter, local).

Outputs:
- plan.json
- structure.csv
- script.txt (with HTML comment markers per phase)

Quickstart:
  export LLM_API_KEY="..."
  export LLM_BASE_URL="xai"              # optional; defaults to openai
  export LLM_MODEL="grok-4-0414"         # optional

  python phase_chat_generator.py \
    --theme "relaxation + focus training" \
    --style "Permissive" \
    --tone "gentle, warm, confident" \
    --variant "standard" \
    --duration "10 minutes" \
    --optional "P7,P9" \
    --out_dir out_run

Notes:
- SAFE techniques are available but not forced — use them when appropriate for the content.

"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not found. Install with: pip install openai", file=sys.stderr)
    raise


# -------------------------
# Provider / env utilities
# -------------------------

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "grok": "https://api.x.ai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "claude": "https://api.anthropic.com/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

PROVIDER_DEFAULTS = {
    "https://api.openai.com/v1": "gpt-4o",
    "https://api.x.ai/v1": "grok-4-0414",
    "https://generativelanguage.googleapis.com/v1beta/openai/": "gemini-3-flash-preview",
    "https://openrouter.ai/api/v1": "anthropic/claude-sonnet-4-6",
    "https://api.anthropic.com/v1": "claude-sonnet-4-6",
    "http://localhost:11434/v1": "llama3",
    "http://localhost:1234/v1": "local-model",
}

# Providers where passing max_tokens causes truncation bugs — omit the parameter entirely
NO_MAX_TOKENS_PROVIDERS = {
    "https://generativelanguage.googleapis.com/v1beta/openai/",
}


def _load_env(var: str, default: Optional[str] = None) -> Optional[str]:
    """Load environment variable, checking .env file if not in environment."""
    v = os.environ.get(var)
    if v:
        return v

    # Try .env in repo root (parent of script folder)
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(var + '=') and not line.startswith('#'):
                    return line.split('=', 1)[1].strip('"\'')

    return default


def _resolve_base_url(url_or_shortcut: str) -> str:
    k = url_or_shortcut.strip().lower()
    return PROVIDER_URLS.get(k, url_or_shortcut)


def get_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[OpenAI, str, str]:
    # Detect whether base_url was explicitly passed on CLI (vs. coming from env)
    explicit_provider = base_url is not None
    base_url_raw = base_url or _load_env("LLM_BASE_URL") or _load_env("OPENAI_BASE_URL") or "openai"
    base_url_resolved = _resolve_base_url(base_url_raw)
    gemini_url = PROVIDER_URLS.get("gemini", "")
    is_gemini = base_url_resolved == gemini_url

    # API key: explicit arg > provider-specific env > generic LLM_API_KEY > OPENAI_API_KEY
    anthropic_url = PROVIDER_URLS.get("anthropic", "")
    is_anthropic = base_url_resolved == anthropic_url
    api_key = api_key or (
        _load_env("GEMINI_API_KEY") if is_gemini
        else _load_env("ANTHROPIC_API_KEY") if is_anthropic
        else _load_env("LLM_API_KEY")
    ) or _load_env("LLM_API_KEY") or _load_env("OPENAI_API_KEY")

    # Model: explicit arg > (if provider was explicit: provider default) > env var > provider default
    model_env = None if explicit_provider else (_load_env("LLM_MODEL") or _load_env("OPENAI_MODEL"))
    model_final = model or model_env or PROVIDER_DEFAULTS.get(base_url_resolved, "gpt-4o")

    if not api_key:
        raise ValueError("Missing API key. Set LLM_API_KEY (or OPENAI_API_KEY).")

    client = OpenAI(api_key=api_key, base_url=base_url_resolved)

    print(f"[info] Provider: {base_url_resolved}", file=sys.stderr)
    print(f"[info] Model:    {model_final}", file=sys.stderr)
    return client, model_final, base_url_resolved


def chat(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: Optional[int] = None,
) -> str:
    kwargs: Dict[str, Any] = dict(model=model, messages=messages, temperature=temperature)
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


# -------------------------
# Duration helpers
# -------------------------

def parse_duration_to_seconds(s: str) -> int:
    """
    Accepts:
      - "600" (seconds)
      - "10 minutes" / "10 min"
      - "90 seconds" / "90 sec"
      - "1200 words" (est. 150 wpm)
    """
    s = s.strip().lower()
    if re.fullmatch(r"\d+", s):
        return int(s)

    # words
    m = re.search(r"(\d+)\s*word", s)
    if m:
        words = int(m.group(1))
        # 150 wpm => 2.5 wps
        return int(words / 2.5)

    # minutes
    m = re.search(r"(\d+)\s*(minutes?|min)\b", s)
    if m:
        return int(m.group(1)) * 60

    # seconds
    m = re.search(r"(\d+)\s*(seconds?|sec)\b", s)
    if m:
        return int(m.group(1))

    raise ValueError(f"Could not parse duration: {s!r}")


def seconds_to_mmss(total: int) -> str:
    m = total // 60
    s = total % 60
    return f"{m}:{s:02d}"


def estimate_words(seconds: int, wpm: int = 150) -> int:
    return int(seconds / 60 * wpm)


def max_tokens_for_words(words: int, buffer_mult: float = 2.0) -> int:
    # very rough: 1.5 tokens/word * buffer; floor of 800 to accommodate pause markup overhead
    return max(800, min(int(words * 1.5 * buffer_mult), 4000))


# -------------------------
# v5.1 Taxonomy loading
# -------------------------

def load_taxonomy(taxonomy_path: Optional[str] = None) -> Dict[str, Any]:
    """Load taxonomy from hypnosis_taxonomy.md via TaxonomyReader."""
    from taxonomy import load_taxonomy as _md_load
    return _md_load(taxonomy_path)


# Load taxonomy at module level
_TAXONOMY = load_taxonomy()

ALLOWED_TECHNIQUES = set(_TAXONOMY["techniques"].keys())
PHASE_NAMES = {pid: pdata["name"] for pid, pdata in _TAXONOMY["phases"].items()}
# phases dict now includes M1-M4, so PHASE_NAMES covers both P and M IDs
_CRAFT_DEFAULTS = _TAXONOMY.get("craft_defaults", "")



@dataclass
class PhasePlan:
    phase: str
    duration_s: int
    techniques: List[str]
    params: Dict[str, Any]
    notes: str = ""


def build_technique_reference() -> str:
    """Build a compact technique reference from taxonomy for the planner prompt.

    Includes the first sentence of each technique's detail block for context.
    """
    lines = []
    # Group by category
    by_cat: Dict[str, List[str]] = {}
    for tid, tdata in _TAXONOMY["techniques"].items():
        cat = tdata["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        # Extract first sentence from detail_block for extra context
        detail = tdata.get("detail_block", "")
        first_sentence = ""
        if detail:
            # Detail blocks start with "> " blockquote containing the description
            for dline in detail.split("\n"):
                stripped = dline.lstrip("> ").strip()
                if stripped and not stripped.startswith("**"):
                    # Take first sentence
                    end = stripped.find(". ")
                    if end > 0:
                        first_sentence = stripped[:end + 1]
                    else:
                        first_sentence = stripped.rstrip(".")  + "."
                    break
        entry = f"{tid}: {tdata['name']} - {tdata['description']}"
        if first_sentence:
            entry += f"\n    {first_sentence}"
        by_cat[cat].append(entry)

    for cat, cat_data in _TAXONOMY["categories"].items():
        if cat in by_cat:
            lines.append(f"\n### {cat} ({cat_data['name']}) - {cat_data['purpose']}")
            for t in sorted(by_cat[cat]):
                lines.append(f"- {t}")

    return "\n".join(lines)


def build_phase_reference() -> str:
    """Build phase reference from taxonomy.

    Includes full function text and use_when/skip_when guidance.
    Technique selection is left to the model based on technique descriptions.
    """
    lines = []
    for pid in sorted(_TAXONOMY["phases"].keys()):
        pdata = _TAXONOMY["phases"][pid]
        req = "REQUIRED" if pdata["required"] else "OPTIONAL"
        dur = f"{pdata['duration_s'][0]}-{pdata['duration_s'][1]}s"
        words = f"{pdata['words'][0]}-{pdata['words'][1]}w"
        lines.append(f"- {pid} {pdata['name']} [{req}] [{dur}] [{words}]")
        lines.append(f"  Function: {pdata['function']}")
        if pdata.get("use_when"):
            lines.append(f"  Use when: {pdata['use_when']}")
        if pdata.get("skip_when"):
            lines.append(f"  Skip when: {pdata['skip_when']}")
    return "\n".join(lines)


def build_technique_examples(technique_ids: List[str]) -> str:
    """Build technique detail blocks (description + good/bad examples) for the writer.

    Given a list of technique IDs from a phase's plan, returns the full
    detail block text for each so the writer has concrete do/don't examples.
    """
    sections = []
    for tid in technique_ids:
        tdata = _TAXONOMY["techniques"].get(tid)
        if not tdata:
            continue
        detail = tdata.get("detail_block", "")
        if not detail:
            continue
        sections.append(f"### {tid}: {tdata['name']}\n{detail}")

    if not sections:
        return ""
    return "\n\n".join(sections)


# -------------------------
# Planning + writing prompts
# -------------------------

SYSTEM_WRITER = """You are a professional hypnosis script writer for CONSENSUAL, opt-in audio content.

═══════════════════════════════════════
FORMAT & SAFETY (non-negotiable)
═══════════════════════════════════════
- Write ONLY the spoken script. No headings, no markdown, no meta-commentary.
- Second person ("you") for the listener. First person ("I") for the operator.
- NEVER include technique IDs (DPTH-03, EMRG-01, etc.) in script text.
- Keep trigger phrases and mantra phrases EXACTLY as specified in the plan.
- Do not introduce trigger phrases not in the plan.
- Never reference "this recording" or "this audio file."
- Each phase should start distinctly — no repetitive openers.

═══════════════════════════════════════
TECHNIQUE EXAMPLES ARE AUTHORITATIVE
═══════════════════════════════════════
When technique examples (✓ good / ✗ bad) are provided in the phase brief, they are the PRIMARY guide for how to write that technique. Imitate the ✓ patterns. Avoid the ✗ patterns. Do not invent competing style rules — follow what the examples show.

═══════════════════════════════════════
MECHANICS
═══════════════════════════════════════
Pause markup: [Xms] or [Xs] for explicit pauses. [500]=500ms, [1.5s]=1.5s.
Use [500]-[800] between paragraphs. Only use pause markers where timing is critical.

═══════════════════════════════════════
CRAFT DEFAULTS (from taxonomy — technique examples override these when they conflict)
═══════════════════════════════════════
""" + _CRAFT_DEFAULTS

# Condensed version for models that echo verbose instructions (e.g. Gemini Flash)

PLANNER_INSTRUCTIONS_TEMPLATE = """Create a phase plan JSON for an audio hypnosis script.

Output STRICT JSON only (no markdown, no backticks).

## Phase Reference (with word count targets)
{phase_reference}

## Technique Reference
{technique_reference}

## Output Schema
{{
  "meta": {{
    "theme": "...",
    "tone": "...",
    "style": "...",
    "variant": "standard|loop|twostage|series",
    "duration_s": 600,
    "optional_phases": ["P7","P9",...]
  }},
  "anchors": ["<3-7 short anchor words/phrases>"],
  "scope_bounds": ["<optional: what will/won't be suggested>"] or [],
  "parameters": {{
    "trigger_phrases": [{{"phrase":"...","response":"...","scope":"...","expiry":"optional"}}],
    "mantras": [{{"line":"...","difficulty":"BASIC|LIGHT|MODERATE|DEEP|EXTREME"}}]
  }},
  "structure": [
    {{
      "phase": "P1",
      "duration_s": 45,
      "techniques": ["ATTN-01","FRAM-02"],
      "params": {{ "ATTN-03": {{"start":10,"end":1}}, "ATTN-11":{{"phrase":"...","reps":5}} }},
      "notes": "..."
    }}
  ]
}}

## Requirements
- Choose phases in a legal order for the variant.
- Sum of structure[].duration_s should match duration_s. Use the word count ranges from phase reference to guide durations.
- 2–5 techniques per phase entry (except P1/P5 can be 1–3).
- Choose techniques whose descriptions match the phase's function.
- If optional phases were requested, INCLUDE them unless truly incompatible with the variant.
- SAFE techniques are available but optional — use them only if the theme/style calls for safety framing.

## v6.0 Rules (CRITICAL)
- DPTH-03 is ONLY for fractionation (during P3). Never use in P5.
- P5 emergence MUST use EMRG-01/02/03/04/05, not DPTH-03.
- One technique ID = one meaning.
- Sensory channel bridging: when notes transition between modalities (body→visualization→voice), bridge explicitly rather than switching abruptly.

## Notes Field Quality (CRITICAL for writer)
The "notes" field in each structure entry is the primary creative seed for the writer.
Thin notes (e.g., "Fixation on breath as entry point") produce thin scripts.
Rich notes produce good scripts. Each notes entry MUST include:
1. The central action or movement of this phase (what changes for the listener?)
2. One specific opening line or phrase sample — an actual sentence the writer can adapt or use verbatim
3. Any key imagery, object, or sensory anchor specific to this phase (what can a set designer build?)
4. If this phase installs or activates a trigger: the exact trigger phrase
5. For mantras with reps > 3: what COMPOUNDS between repetitions? (e.g., "first 3 reps = command + pleasure link, reps 4-6 = add identity, reps 7+ = automatic reflex with minimal interstitial")
6. Any register/texture shift within this phase (e.g., "open nurturing, tighten to commanding by midpoint")

Example of BAD notes: "Deepening through breath focus, going deeper."
Example of GOOD notes: "Listener sinks on each exhale. Open with: 'Each breath out — one floor lower. No effort. Just that.' Imagery: a slow elevator, floor numbers descending. Use warmth in feet as anchor."

## Cognitive Overload Guidance
When the theme calls for overload/confusion, plan it structurally:
- Which phase generates the confusion? (typically P3 or M1)
- Which technique creates it? (BYPS-03 confusion, BYPS-05 circular logic, BYPS-10 phonemic split)
- Which phase resolves it into compliance? (typically P4)
- In notes, specify the overload mechanism: "Run-on sentence describing competing tasks → short command resolves into compliance."
- Overload + resolution is a pair. Don't plan overload without planning the resolution.

## Mantra Escalation
For mantras with 7+ reps, the notes MUST specify a compounding arc:
- Reps 1-3: Establish the phrase. Interstitials are longer (full sentences of context/imagery).
- Reps 4-6: Pleasure/identity linkage. Interstitials shorten (fragments, praise).
- Reps 7+: Automatic reflex. Interstitials become 1-2 words or nothing. The phrase IS the content.
This prevents mantra wallpaper. The writer needs this arc or it will repeat identically.
"""


def get_planner_instructions() -> str:
    """Build planner instructions with taxonomy data injected."""
    return PLANNER_INSTRUCTIONS_TEMPLATE.format(
        phase_reference=build_phase_reference(),
        technique_reference=build_technique_reference()
    )


# Phase-specific style mode hints injected into PHASE_WRITER_TEMPLATE
_PHASE_STYLE_HINTS: Dict[str, str] = {
    "P1": "PRE-TALK mode: medium sentences (12-20 words). Conversational authority. Establish the central object or metaphor concretely. No trance language yet — build credibility.",
    "P2": "INDUCTION mode: transitioning from medium to short. Begin with inarguable observations. Permission grammar ('you can'). Soft. Introduce 'just'. First closed loops. SINGLE-ANCHOR PRINCIPLE: choose one primary anchor (breath, body weight, or voice) before layering additional channels.",
    "P3": "DEEPENING mode: SHORT FRAGMENTS ONLY. 3-8 words per line. One idea per line. No compound sentences. Breath/body anchored. This is where you earn depth.",
    "P4": "SUGGESTION mode: oscillate. A medium declarative (8-12 words) drops the suggestion; 1-3 word fragments reinforce it. Pattern: claim → echo → echo. Never announce — just land it. Fragment length is your primary tool. Let silence do work.",
    "P5": "EMERGENCE mode: return to medium sentences (12-18 words). Sentence length increase signals ascent. Modal shift: declarative → permission → invitation. Warm, grounding. All sentences must be grammatically complete — no dangling adverbs ('fades safe' → 'fades safely, leaving you clear').",
    "M1": "BLANK-STATE mode: SHORT FRAGMENTS ONLY. 3-8 words. Dissolve analytical thought. Voice replaces internal monologue. Fragment length signals depth. Build cognitive overwhelm structurally, not poetically.",
    "M2": "TRANSFER mode: medium-short (8-15 words). Declarative authority. Install conditioned responses. Bridge trance state to real-world contexts. Each trigger must land with exact wording from plan.",
    "M3": "DEMONSTRATION mode: short to medium. Activate installed triggers. Sustain reward states. Provide proof of trance. Let the listener feel the phenomenon, don't describe it.",
    "M4": "LOOP CLOSE mode: short to medium. Final 3 sentences: abstract anchors only (trance, sink, deeper, yield, surrender, drop). No theme-specific imagery at the end. State must mirror opening for seamless restart.",
}


def _get_phase_style_hint(phase: str) -> str:
    """Return phase-specific style mode hint for the writer template."""
    return _PHASE_STYLE_HINTS.get(phase, "Follow session depth. Maintain appropriate sentence length for where the listener is.")

PHASE_WRITER_TEMPLATE = """Write PHASE {phase} — {phase_name}.

## PLAN (authoritative — follow exactly)
- Target duration: {duration_s} seconds (~{target_words} words)
- Techniques to execute: {techniques_csv}
- Parameters: {params_json}
- Anchors to repeat intentionally: {anchors_csv}
- Tone: {tone} | Style: {style}
- Theme/Goal: {theme}
- Scope bounds: {scope_bounds_bullets}

## PHASE STYLE MODE
{phase_style_hint}

## TECHNIQUE REFERENCE (good/bad examples — these are AUTHORITATIVE for how to write each technique)
{technique_examples}

## CRITICAL SEED — read this before writing a single word
{notes_block}

## Rules
- Connect smoothly from prior content. End with a natural transition.
- Follow the ✓/✗ examples above for each technique. They show exactly how to write it.
"""


PHASE_WRITER_TEMPLATE_V2 = """Write PHASE {phase} — {phase_name}.

TARGET: {duration_s}s (~{target_words} words)
TECHNIQUES: {techniques_csv}
PARAMS: {params_json}

STYLE MODE: {phase_style_hint}

{technique_examples}

SEED (authoritative — use the opening line, imagery, and compounding arc exactly as specified):
{notes_block}

{forward_refs}
Continue from the prose above. Connect smoothly. End with a natural transition.
The technique ✓/✗ examples above are your primary writing guide for this phase.
"""

ONE_SHOT_WRITER_TEMPLATE = """Write the complete script — all phases in order.

Before each phase, output this exact delimiter line (fill in the values):
<!-- PHASE: {{phase_id}} {{phase_name}} | TARGET: {{target_words}}w -->

## Phase Table (write all phases in this order)
{phase_table}

## Session Parameters
Anchors: {anchors_csv}
Scope: {scope_bounds_bullets}

Write all phases end-to-end. No explanations, no meta-commentary. Only the script text and the delimiter lines.
"""


# -------------------------
# v2 helper functions
# -------------------------

def _build_plan_summary(plan: Dict[str, Any]) -> str:
    """Build a compact ~15-line plan summary for use as assistant context."""
    meta = plan.get("meta", {})
    anchors = plan.get("anchors", [])
    scope = plan.get("scope_bounds", []) or []
    params = plan.get("parameters", {}) or {}
    trigger_phrases = params.get("trigger_phrases", []) or []
    mantras = params.get("mantras", []) or []
    structure = plan.get("structure", [])

    lines = [
        "## Session Plan Summary",
        f"Theme: {meta.get('theme', '')}",
        f"Tone: {meta.get('tone', '')} | Style: {meta.get('style', '')}",
        f"Variant: {meta.get('variant', 'standard')} | Duration: {meta.get('duration_s', 0)}s",
        f"Anchors: {', '.join(anchors) if anchors else '(none)'}",
    ]

    if scope:
        lines.append("Scope: " + "; ".join(scope[:4]))

    if trigger_phrases:
        lines.append("Trigger phrases (EXACT wording):")
        for tp in trigger_phrases:
            phrase = tp.get("phrase", "")
            response = tp.get("response", "")
            lines.append(f'  "{phrase}" → {response}')

    if mantras:
        lines.append("Mantras (EXACT wording):")
        for m in mantras:
            lines.append(f'  "{m.get("line", "")}" [{m.get("difficulty", "")}]')

    # Phase sequence
    seq_parts = []
    for b in structure:
        seq_parts.append(f"{b['phase']}({b.get('duration_s', 0)}s)")
    lines.append("Phase sequence: " + " → ".join(seq_parts))

    return "\n".join(lines)


def _extract_prose_tail(text: str, n_lines: int = 6) -> str:
    """Return the last n_lines non-blank lines of text."""
    all_lines = text.split("\n")
    non_blank = [l for l in all_lines if l.strip()]
    tail = non_blank[-n_lines:] if len(non_blank) >= n_lines else non_blank
    return "\n".join(tail)


def _forward_refs(plan: Dict[str, Any], current_idx: int) -> str:
    """
    Scan upcoming phases to surface what the current phase should prime for.
    Returns a short string (or empty string if nothing to surface).
    """
    structure = plan.get("structure", [])
    params = plan.get("parameters", {}) or {}
    trigger_phrases = params.get("trigger_phrases", []) or []
    mantras = params.get("mantras", []) or []

    upcoming = structure[current_idx + 1:]
    if not upcoming:
        return ""

    hints = []

    # Check trigger phrases — look for them mentioned in upcoming notes
    for tp in trigger_phrases:
        phrase = tp.get("phrase", "")
        if not phrase:
            continue
        for future_block in upcoming:
            future_notes = future_block.get("notes", "") or ""
            future_phase = future_block.get("phase", "")
            if phrase.lower() in future_notes.lower():
                hints.append(f'UPCOMING: trigger phrase "{phrase}" installs in {future_phase} — prime the listener for this word cluster.')
                break

    # Check mantras — look for them mentioned in upcoming notes
    for m in mantras:
        line = m.get("line", "")
        if not line:
            continue
        for future_block in upcoming:
            future_notes = future_block.get("notes", "") or ""
            future_phase = future_block.get("phase", "")
            if any(word in future_notes.lower() for word in line.lower().split() if len(word) > 4):
                hints.append(f'UPCOMING: mantra "{line}" installs in {future_phase} — begin seeding this vocabulary.')
                break

    if not hints:
        return ""

    return "FORWARD PRIMING:\n" + "\n".join(hints)


# -------------------------
# Lint gate
# -------------------------

@dataclass
class LintError:
    phase: str
    code: str
    message: str
    detail: str


_BANNED_PHRASES = [
    "honeyed",
    "subconscious mind",
    "serene rapture",
    "peaceful empty",
    "luminous",
]

_ANNOUNCING_PHRASES = [
    "i'm going to suggest",
    "let these words sink in",
    "repeating now",
    "i will now suggest",
]

_SIMILE_PHASES = {"P3", "P5", "M1"}


def lint_phase(phase_id: str, text: str, plan: Dict[str, Any]) -> List[LintError]:
    """
    Zero-API lint gate. Only catches universally bad writing — no style opinions.

    Kept:
      LINT-03: Purple prose phrases that are always bad
      LINT-04: Similes for states in deepening/suggestion phases (states ARE, not LIKE)
      LINT-05: Technique ID leak (DPTH-03 etc in script text)
      LINT-07: Announcing technique execution ("I'm going to suggest")

    Removed:
      LINT-01: Sentence length — contradicts cognitive overload guidance
      LINT-02: Future tense — contradicts ENCD-02 (Future Pacing)
      LINT-06: POV — style-dependent, not universally lintable
      LINT-08: Thinking out loud — contradicts BYPS-08 (Transparent Narration) and SYNC-03
    """
    errors: List[LintError] = []
    lower = text.lower()

    # 3. Banned phrases (purple prose that's always bad)
    for phrase in _BANNED_PHRASES:
        if phrase in lower:
            errors.append(LintError(
                phase=phase_id,
                code="LINT-03",
                message=f"Banned phrase: {phrase!r}",
                detail=""
            ))

    # 4. Similes — removed. Taxonomy ✓ examples use similes (SYNC-02, etc.).

    # 5. Technique ID leak
    for m in re.finditer(r"\b[A-Z]{2,5}-\d{2,3}\b", text):
        errors.append(LintError(
            phase=phase_id,
            code="LINT-05",
            message=f"Technique ID in script text: {m.group()}",
            detail=text[max(0, m.start() - 20):m.end() + 20].strip()
        ))

    # 7. Announcing technique execution
    for phrase in _ANNOUNCING_PHRASES:
        if phrase in lower:
            errors.append(LintError(
                phase=phase_id,
                code="LINT-07",
                message=f"Announcing: {phrase!r}",
                detail=""
            ))

    return errors


def print_lint_errors(errors: List[LintError]) -> None:
    for e in errors:
        print(f"[lint:{e.code}] {e.phase}: {e.message} — {e.detail}", file=sys.stderr)


# -------------------------
# One-shot generation
# -------------------------

def split_oneshot_output(text: str, plan: Dict[str, Any]) -> List[str]:
    """
    Split one-shot output on <!-- PHASE: ... --> markers.
    Returns list of phase texts in plan order. Missing phases get empty string.
    """
    structure = plan.get("structure", [])
    phase_ids = [b["phase"] for b in structure]

    # Split on phase delimiter markers
    parts = re.split(r"<!--\s*PHASE:\s*", text)
    # parts[0] is text before first marker (discard); parts[1+] start with "P1 ..."

    phase_map: Dict[str, str] = {}
    for part in parts[1:]:
        # Extract phase id from start of part
        m = re.match(r"([A-Z]\d+)\b", part)
        if not m:
            continue
        pid = m.group(1)
        # Strip the rest of the marker line
        body = re.sub(r"^[^\n]*\n", "", part, count=1)
        phase_map[pid] = body.strip()

    result: List[str] = []
    for pid in phase_ids:
        if pid in phase_map:
            result.append(phase_map[pid])
        else:
            print(f"[warn] One-shot output missing phase {pid} — inserting empty", file=sys.stderr)
            result.append("")

    return result


def generate_script_oneshot(
    client: OpenAI,
    model: str,
    plan: Dict[str, Any],
    temperature_write: float = 0.8,
    system_writer: str = SYSTEM_WRITER,
    omit_max_tokens: bool = False,
    tail_sentences: int = 6,
) -> Tuple[List[PhasePlan], List[str], List[Dict[str, str]]]:
    """Generate full script in a single API call."""
    meta = plan.get("meta", {})
    anchors = plan.get("anchors", [])
    anchors_csv = "|".join(anchors) if anchors else ""
    scope_bounds = plan.get("scope_bounds", []) or []
    scope_bounds_bullets = "\n".join([f"- {x}" for x in scope_bounds]) if scope_bounds else "- (none specified)"

    structure = plan["structure"]

    # Build phase table (one line per phase)
    table_lines = []
    for b in structure:
        pid = b["phase"]
        pname = PHASE_NAMES.get(pid, pid)
        dur = int(b.get("duration_s", 60))
        words = estimate_words(dur)
        techs = ",".join(b.get("techniques", []))
        notes_excerpt = (b.get("notes", "") or "")[:80].replace("\n", " ")
        table_lines.append(f"{pid} {pname} | {words}w | {techs} | {notes_excerpt}")
    phase_table = "\n".join(table_lines)

    prompt = ONE_SHOT_WRITER_TEMPLATE.format(
        phase_table=phase_table,
        anchors_csv=anchors_csv,
        scope_bounds_bullets=scope_bounds_bullets,
    )

    plan_summary = _build_plan_summary(plan)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_writer},
        {"role": "assistant", "content": plan_summary},
        {"role": "user", "content": prompt},
    ]

    # Estimate total words for token budget
    total_words = sum(estimate_words(int(b.get("duration_s", 60))) for b in structure)
    max_toks = None if omit_max_tokens else max_tokens_for_words(total_words, buffer_mult=2.0)
    # Cap at model-friendly max for single-call
    if max_toks is not None:
        max_toks = min(max_toks, 8000)

    print(f"[info] One-shot: generating {len(structure)} phases (~{total_words}w total)", file=sys.stderr)
    raw = chat(client, model, messages, temperature=temperature_write, max_tokens=max_toks)

    phase_texts = split_oneshot_output(raw, plan)

    phase_plans: List[PhasePlan] = []
    for b in structure:
        phase_plans.append(PhasePlan(
            phase=b["phase"],
            duration_s=int(b.get("duration_s", 60)),
            techniques=list(b.get("techniques", [])),
            params=b.get("params", {}) or {},
            notes=b.get("notes", "") or "",
        ))

    return phase_plans, phase_texts, messages


# -------------------------
# Robust JSON extraction
# -------------------------

def extract_json(text: str) -> Dict[str, Any]:
    """
    Try to parse strict JSON. If the model wrapped it in extra text,
    extract the first {...} block.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # extract first json object
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def validate_plan(plan: Dict[str, Any]) -> None:
    if "structure" not in plan or not isinstance(plan["structure"], list) or not plan["structure"]:
        raise ValueError("Plan missing non-empty structure[]")

    # Validate techniques
    for i, block in enumerate(plan["structure"], start=1):
        phase = block.get("phase")
        if phase not in PHASE_NAMES:
            raise ValueError(f"Block {i}: invalid phase {phase!r}")
        techs = block.get("techniques", [])
        if not isinstance(techs, list) or not techs:
            raise ValueError(f"Block {i}: techniques must be a non-empty list")
        for t in techs:
            if t not in ALLOWED_TECHNIQUES:
                raise ValueError(f"Block {i}: unknown technique id {t}")

    # Validate duration sanity
    meta_dur = int(plan.get("meta", {}).get("duration_s", 0) or 0)
    if meta_dur > 0:
        total = sum(int(b.get("duration_s", 0) or 0) for b in plan["structure"])
        if total <= 0:
            raise ValueError("Plan structure duration_s sums to 0")
        # allow +/- 10% (we can rescale later)
        if abs(total - meta_dur) / meta_dur > 0.25:
            # more forgiving at validation; rescaler can fix mild mismatches
            print(f"[warn] Plan duration mismatch: plan_total={total}s target={meta_dur}s", file=sys.stderr)


def rescale_durations(plan: Dict[str, Any], target_s: int) -> None:
    blocks = plan["structure"]
    current = sum(int(b.get("duration_s", 0) or 0) for b in blocks)
    if current <= 0:
        return
    scale = target_s / current
    for b in blocks:
        b["duration_s"] = max(10, int(round(int(b.get("duration_s", 0) or 0) * scale)))


# -------------------------
# Conversation-based generation
# -------------------------

def generate_plan(
    client: OpenAI,
    model: str,
    theme: str,
    tone: str,
    style: str,
    variant: str,
    duration_s: int,
    optional_phases: List[str],
    temperature: float = 0.2,
    system_writer: str = SYSTEM_WRITER,
    omit_max_tokens: bool = False,
) -> Dict[str, Any]:

    user_payload = {
        "theme": theme,
        "tone": tone,
        "style": style,
        "variant": variant,
        "duration_s": duration_s,
        "optional_phases": optional_phases,
    }

    planner_instructions = get_planner_instructions()

    messages = [
        {"role": "system", "content": system_writer},
        {"role": "user", "content": planner_instructions + "\n\nINPUT:\n" + json.dumps(user_payload, indent=2, ensure_ascii=False)}
    ]

    plan_max_tokens = None if omit_max_tokens else 3200
    raw = chat(client, model, messages, temperature=temperature, max_tokens=plan_max_tokens)
    plan = extract_json(raw)
    validate_plan(plan)

    # If planner didn't honor target duration well, rescale (gentle)
    if int(plan.get("meta", {}).get("duration_s", duration_s) or duration_s) != duration_s:
        plan.setdefault("meta", {})["duration_s"] = duration_s
    rescale_durations(plan, duration_s)

    return plan


def generate_script_conversation(
    client: OpenAI,
    model: str,
    plan: Dict[str, Any],
    temperature_write: float = 0.8,
    system_writer: str = SYSTEM_WRITER,
    omit_max_tokens: bool = False,
    lint_retry: bool = False,
) -> Tuple[List[PhasePlan], List[str], List[Dict[str, str]]]:
    """
    Conversation mode: accumulates real user→assistant turns so the model
    builds on its own prior output across phases.

    Context: system + plan assistant + [user brief, assistant output] per phase.
    Full conversation history is preserved — modern context windows (128-200K+)
    can handle even hour-long scripts without trimming.
    """
    meta = plan.get("meta", {})
    plan_summary = _build_plan_summary(plan)

    # Start the conversation: system + plan as assistant context
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_writer},
        {"role": "assistant", "content": plan_summary},
    ]

    phase_plans: List[PhasePlan] = []
    phase_texts: List[str] = []

    structure = plan["structure"]

    for idx, block in enumerate(structure):
        phase = block["phase"]
        phase_name = PHASE_NAMES.get(phase, phase)
        duration_s = int(block.get("duration_s", 60))
        target_words = estimate_words(duration_s)
        techniques = list(block.get("techniques", []))
        params = block.get("params", {}) or {}
        notes = block.get("notes", "") or ""

        phase_plans.append(PhasePlan(phase=phase, duration_s=duration_s, techniques=techniques, params=params, notes=notes))

        phase_style_hint = _get_phase_style_hint(phase)
        if notes:
            notes_block = (
                f"The planner wrote this creative seed — treat it as AUTHORITATIVE:\n"
                f"{notes}\n\n"
                f"Use the opening line sample (if provided) verbatim or nearly verbatim as your first sentence.\n"
                f"Use the imagery/object described as your primary visual anchor for this phase."
            )
        else:
            notes_block = "(No seed notes provided. Infer appropriate creative direction from theme, tone, and phase type.)"

        forward = _forward_refs(plan, idx)

        tech_examples = build_technique_examples(techniques)
        tech_examples_block = ""
        if tech_examples:
            tech_examples_block = f"TECHNIQUE EXAMPLES (good/bad for this phase):\n{tech_examples}"

        phase_brief = PHASE_WRITER_TEMPLATE_V2.format(
            phase=phase,
            phase_name=phase_name,
            duration_s=duration_s,
            target_words=target_words,
            techniques_csv=",".join(techniques),
            params_json=json.dumps(params, ensure_ascii=False),
            phase_style_hint=phase_style_hint,
            technique_examples=tech_examples_block,
            notes_block=notes_block,
            forward_refs=forward,
        )

        # Add loop-specific guidance for M4 (loop close)
        if phase in ("P13", "M4") and plan.get("meta", {}).get("variant") == "loop":
            phase_brief += """
LOOP TRANSITION RULES:
- The final 2-3 sentences should be theme-agnostic to enable cross-theme playlists
- End with abstract anchors that work across themes: "trance", "sink", "deeper", "yield", "surrender", "drop"
- AVOID theme-specific anchors in the final sentences
- AVOID speaker-centric closings like "my voice", "addicted to me"
- Structure: [theme content] → [abstract transition] → [generic sink/drop that mirrors P2 opening]
- The ending should flow seamlessly into ANY P2 induction, not just this theme's P2
"""

        # Append user guidance into the ongoing conversation
        messages.append({"role": "user", "content": phase_brief})

        max_toks = None if omit_max_tokens else max_tokens_for_words(target_words, buffer_mult=2.0)

        print(f"[info] Writing {phase} {phase_name} (~{duration_s}s, ~{target_words}w) with {len(techniques)} techniques [conversation]", file=sys.stderr)

        text = chat(client, model, messages, temperature=temperature_write, max_tokens=max_toks)

        # Lint gate
        lint_errors = lint_phase(phase, text, plan)
        if lint_errors:
            print_lint_errors(lint_errors)
            if lint_retry:
                print(f"[lint] Retrying {phase} due to {len(lint_errors)} lint error(s)...", file=sys.stderr)
                text = chat(client, model, messages, temperature=temperature_write, max_tokens=max_toks)
                retry_errors = lint_phase(phase, text, plan)
                if retry_errors:
                    print(f"[lint] Retry still has {len(retry_errors)} error(s) — keeping retry output", file=sys.stderr)
                    print_lint_errors(retry_errors)

        phase_texts.append(text)

        # Record assistant output so the next phase has real conversation continuity
        messages.append({"role": "assistant", "content": text})

    return phase_plans, phase_texts, messages


def generate_script_from_plan(
    client: OpenAI,
    model: str,
    plan: Dict[str, Any],
    temperature_write: float = 0.8,
    context_window_phases: int = 0,  # deprecated no-op, kept for backwards compat
    system_writer: str = SYSTEM_WRITER,
    omit_max_tokens: bool = False,
    tail_sentences: int = 6,
    lint_retry: bool = False,
) -> Tuple[List[PhasePlan], List[str], List[Dict[str, str]]]:
    """
    v2: fixed 4-message context per phase.
    [0] system:    SYSTEM_WRITER
    [1] assistant: condensed plan summary
    [2] assistant: last tail_sentences lines of prior phase  (omitted for phase 1)
    [3] user:      phase brief (PHASE_WRITER_TEMPLATE_V2)
    """
    meta = plan.get("meta", {})

    plan_summary = _build_plan_summary(plan)

    phase_plans: List[PhasePlan] = []
    phase_texts: List[str] = []
    all_messages: List[Dict[str, str]] = []

    structure = plan["structure"]

    for idx, block in enumerate(structure):
        phase = block["phase"]
        phase_name = PHASE_NAMES.get(phase, phase)
        duration_s = int(block.get("duration_s", 60))
        target_words = estimate_words(duration_s)
        techniques = list(block.get("techniques", []))
        params = block.get("params", {}) or {}
        notes = block.get("notes", "") or ""

        phase_plans.append(PhasePlan(phase=phase, duration_s=duration_s, techniques=techniques, params=params, notes=notes))

        phase_style_hint = _get_phase_style_hint(phase)
        if notes:
            notes_block = (
                f"The planner wrote this creative seed — treat it as AUTHORITATIVE:\n"
                f"{notes}\n\n"
                f"Use the opening line sample (if provided) verbatim or nearly verbatim as your first sentence.\n"
                f"Use the imagery/object described as your primary visual anchor for this phase."
            )
        else:
            notes_block = "(No seed notes provided. Infer appropriate creative direction from theme, tone, and phase type.)"

        forward = _forward_refs(plan, idx)

        tech_examples = build_technique_examples(techniques)
        tech_examples_block = ""
        if tech_examples:
            tech_examples_block = f"TECHNIQUE EXAMPLES (good/bad for this phase):\n{tech_examples}"

        phase_brief = PHASE_WRITER_TEMPLATE_V2.format(
            phase=phase,
            phase_name=phase_name,
            duration_s=duration_s,
            target_words=target_words,
            techniques_csv=",".join(techniques),
            params_json=json.dumps(params, ensure_ascii=False),
            phase_style_hint=phase_style_hint,
            technique_examples=tech_examples_block,
            notes_block=notes_block,
            forward_refs=forward,
        )

        # Add loop-specific guidance for M4 (loop close)
        if phase in ("P13", "M4") and plan.get("meta", {}).get("variant") == "loop":
            phase_brief += """
LOOP TRANSITION RULES:
- The final 2-3 sentences should be theme-agnostic to enable cross-theme playlists
- End with abstract anchors that work across themes: "trance", "sink", "deeper", "yield", "surrender", "drop"
- AVOID theme-specific anchors in the final sentences
- AVOID speaker-centric closings like "my voice", "addicted to me"
- Structure: [theme content] → [abstract transition] → [generic sink/drop that mirrors P2 opening]
- The ending should flow seamlessly into ANY P2 induction, not just this theme's P2
"""

        # Build fixed 4-message context
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_writer},
            {"role": "assistant", "content": plan_summary},
        ]

        # Tail context from prior phase (omit for first phase)
        if idx > 0 and phase_texts and tail_sentences > 0:
            tail = _extract_prose_tail(phase_texts[-1], n_lines=tail_sentences)
            if tail:
                messages.append({"role": "assistant", "content": tail})

        messages.append({"role": "user", "content": phase_brief})

        max_toks = None if omit_max_tokens else max_tokens_for_words(target_words, buffer_mult=2.0)

        print(f"[info] Writing {phase} {phase_name} (~{duration_s}s, ~{target_words}w) with {len(techniques)} techniques", file=sys.stderr)

        text = chat(client, model, messages, temperature=temperature_write, max_tokens=max_toks)

        # Lint gate
        lint_errors = lint_phase(phase, text, plan)
        if lint_errors:
            print_lint_errors(lint_errors)
            if lint_retry:
                print(f"[lint] Retrying {phase} due to {len(lint_errors)} lint error(s)...", file=sys.stderr)
                text = chat(client, model, messages, temperature=temperature_write, max_tokens=max_toks)
                retry_errors = lint_phase(phase, text, plan)
                if retry_errors:
                    print(f"[lint] Retry still has {len(retry_errors)} error(s) — keeping retry output", file=sys.stderr)
                    print_lint_errors(retry_errors)

        phase_texts.append(text)

        # Save last messages for return (caller may inspect)
        all_messages = messages + [{"role": "assistant", "content": text}]

    return phase_plans, phase_texts, all_messages


# -------------------------
# Output writers
# -------------------------

def write_plan(plan: Dict[str, Any], out_path: Path) -> None:
    out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def write_structure_csv(plans: List[PhasePlan], out_path: Path) -> None:
    start = 0
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["phase", "start_time", "duration_s", "techniques", "notes"])
        for p in plans:
            w.writerow([
                p.phase,
                seconds_to_mmss(start),
                p.duration_s,
                "|".join(p.techniques),
                p.notes,
            ])
            start += p.duration_s


def write_script(plans: List[PhasePlan], texts: List[str], out_path: Path) -> None:
    lines: List[str] = []
    for p, t in zip(plans, texts):
        phase_name = PHASE_NAMES.get(p.phase, p.phase)
        # Use technique names instead of IDs for better readability and taxonomy version resilience
        tech_names = [_TAXONOMY["techniques"].get(t, {}).get("name", t) for t in p.techniques]
        tech = ",".join(tech_names)
        lines.append(f"<!-- PHASE: {p.phase} {phase_name} | TECH: {tech} -->")
        lines.append(t.strip())
        lines.append("")  # spacer
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


# -------------------------
# CLI
# -------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Phase-based hypnosis script generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  # Generate from scratch (Compulsion loop, 10 min)
  python3 phase_chat_generator.py \\
    --theme "mind control and identity dissolution" \\
    --style Compulsion --tone "commanding, intimate" \\
    --variant loop --duration "10 minutes" --optional "M1,M2"

  # Write from existing plan (reuse plan, try different model)
  python3 phase_chat_generator.py --plan out/plan.json \\
    --base_url anthropic --model claude-sonnet-4-6

  # Quick draft with oneshot (cheaper, lower quality)
  python3 phase_chat_generator.py --plan out/plan.json --mode oneshot

modes:
  conversation  Accumulates real user/assistant turns across phases.
                Model sees its own prior output — best continuity and
                mantra compounding. Best with Claude models. (default)
  phased        Fixed 4-message context per phase (system + plan summary
                + tail of prior phase + brief). Each phase is independent.
                Best with Gemini models.
  oneshot        Single API call for entire script. Cheapest but lowest
                quality — undercounts mantra reps, wall-of-text formatting.

providers (--base_url shortcuts):
  anthropic/claude   Claude (Sonnet, Opus)
  xai/grok           Grok
  gemini/google      Gemini
  openai             OpenAI / GPT
  openrouter         OpenRouter
  ollama/lmstudio    Local models
""")

    # Content
    ap.add_argument("--theme", default=None, help="Theme/goal (free text). Required unless --plan provided.")
    ap.add_argument("--tone", default=None, help="Tone (free text, e.g. 'commanding, intimate, relentless'). Required unless --plan.")
    ap.add_argument("--style", default=None,
                    choices=["Permissive","Authoritarian","Challenge","Mixed","Institutional","Character","Compulsion"],
                    help="Style label — controls authority register and POV rules.")
    ap.add_argument("--variant", default="standard",
                    choices=["standard","loop","twostage","series"],
                    help="Script structure (default: standard)")
    ap.add_argument("--duration", default=None, help="Total duration (e.g. '10 minutes', '600s', '1200 words')")
    ap.add_argument("--optional", default="", help="Optional modules to include (e.g. 'M1,M2,M3')")

    # Output
    ap.add_argument("--out_dir", default="out", help="Output directory (default: out/)")
    ap.add_argument("--plan", default=None, help="Load existing plan.json instead of generating")

    # Generation
    ap.add_argument("--mode", default="conversation",
                    choices=["conversation", "phased", "oneshot"],
                    help="Generation mode (default: conversation)")
    ap.add_argument("--temperature_plan", type=float, default=0.2, help="Planning temperature (default: 0.2)")
    ap.add_argument("--temperature_write", type=float, default=0.8, help="Writing temperature (default: 0.8)")
    ap.add_argument("--tail_sentences", type=int, default=6, help="Phased mode: lines of prior phase to carry (default: 6)")
    ap.add_argument("--lint_retry", action="store_true", default=False, help="Retry phase once if lint errors found")

    # Provider
    ap.add_argument("--api_key", default=None, help="API key (or set LLM_API_KEY env var)")
    ap.add_argument("--base_url", default=None, help="Provider URL or shortcut (see above)")
    ap.add_argument("--model", default=None, help="Model name (auto-detected from provider if omitted)")

    # Deprecated
    ap.add_argument("--context_window_phases", type=int, default=0, help=argparse.SUPPRESS)

    args = ap.parse_args()

    variant = args.variant.lower()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client, model, base_url = get_client(api_key=args.api_key, base_url=args.base_url, model=args.model)
    system_writer = SYSTEM_WRITER
    omit_max_tokens = base_url in NO_MAX_TOKENS_PROVIDERS

    # Load existing plan or generate new one
    if args.plan:
        with open(args.plan, encoding="utf-8") as f:
            plan = json.load(f)
        validate_plan(plan)
        print(f"[info] Loaded plan from {args.plan}", file=sys.stderr)
    else:
        # Validate required args when generating
        missing = []
        if not args.theme: missing.append("--theme")
        if not args.tone: missing.append("--tone")
        if not args.style: missing.append("--style")
        if not args.duration: missing.append("--duration")
        if missing:
            print(f"[error] Missing required arguments: {', '.join(missing)}", file=sys.stderr)
            print("[hint] Provide these args OR use --plan to load an existing plan.json", file=sys.stderr)
            sys.exit(1)

        duration_s = parse_duration_to_seconds(args.duration)
        optional = [x.strip() for x in args.optional.split(",") if x.strip()]
        optional = [p for p in optional if p in PHASE_NAMES]

        plan = generate_plan(
            client=client,
            model=model,
            theme=args.theme,
            tone=args.tone,
            style=args.style,
            variant=variant,
            duration_s=duration_s,
            optional_phases=optional,
            temperature=args.temperature_plan,
            system_writer=system_writer,
            omit_max_tokens=omit_max_tokens,
        )

    plan_path = out_dir / "plan.json"
    write_plan(plan, plan_path)

    if args.mode == "oneshot":
        plans, texts, _msgs = generate_script_oneshot(
            client=client,
            model=model,
            plan=plan,
            temperature_write=args.temperature_write,
            system_writer=system_writer,
            omit_max_tokens=omit_max_tokens,
            tail_sentences=args.tail_sentences,
        )
    elif args.mode == "conversation":
        plans, texts, _msgs = generate_script_conversation(
            client=client,
            model=model,
            plan=plan,
            temperature_write=args.temperature_write,
            system_writer=system_writer,
            omit_max_tokens=omit_max_tokens,
            lint_retry=args.lint_retry,
        )
    else:
        plans, texts, _msgs = generate_script_from_plan(
            client=client,
            model=model,
            plan=plan,
            temperature_write=args.temperature_write,
            context_window_phases=args.context_window_phases,
            system_writer=system_writer,
            omit_max_tokens=omit_max_tokens,
            tail_sentences=args.tail_sentences,
            lint_retry=args.lint_retry,
        )

    struct_path = out_dir / "structure.csv"
    script_path = out_dir / "script.txt"
    write_structure_csv(plans, struct_path)
    write_script(plans, texts, script_path)

    print(f"[ok] Wrote: {plan_path}", file=sys.stderr)
    print(f"[ok] Wrote: {struct_path}", file=sys.stderr)
    print(f"[ok] Wrote: {script_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
