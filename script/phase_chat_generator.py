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
- This generator defaults to including SAFE-03 (stop signal) + SAFE-05 (aftercare) for non-loop variants.
- It *defaults off* high-blast-radius techniques unless explicitly allowed.

"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass
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
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

PROVIDER_DEFAULTS = {
    "https://api.openai.com/v1": "gpt-4o",
    "https://api.x.ai/v1": "grok-4-0414",
    "https://openrouter.ai/api/v1": "anthropic/claude-sonnet-4",
    "http://localhost:11434/v1": "llama3",
    "http://localhost:1234/v1": "local-model",
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
) -> Tuple[OpenAI, str]:
    api_key = api_key or _load_env("LLM_API_KEY") or _load_env("OPENAI_API_KEY")
    base_url_raw = base_url or _load_env("LLM_BASE_URL") or _load_env("OPENAI_BASE_URL") or "openai"
    base_url_resolved = _resolve_base_url(base_url_raw)

    model_env = _load_env("LLM_MODEL") or _load_env("OPENAI_MODEL")
    model_final = model or model_env or PROVIDER_DEFAULTS.get(base_url_resolved, "gpt-4o")

    if not api_key:
        raise ValueError("Missing API key. Set LLM_API_KEY (or OPENAI_API_KEY).")

    client = OpenAI(api_key=api_key, base_url=base_url_resolved)

    print(f"[info] Provider: {base_url_resolved}", file=sys.stderr)
    print(f"[info] Model:    {model_final}", file=sys.stderr)
    return client, model_final


def chat(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
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
    # very rough: 1.5 tokens/word * buffer
    return min(int(words * 1.5 * buffer_mult), 4000)


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



@dataclass
class PhasePlan:
    phase: str
    duration_s: int
    techniques: List[str]
    params: Dict[str, Any]
    notes: str = ""


def build_technique_reference() -> str:
    """Build a compact technique reference from taxonomy for the planner prompt."""
    lines = []
    # Group by category
    by_cat: Dict[str, List[str]] = {}
    for tid, tdata in _TAXONOMY["techniques"].items():
        cat = tdata["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(f"{tid}: {tdata['name']} - {tdata['description']}")

    for cat, cat_data in _TAXONOMY["categories"].items():
        if cat in by_cat:
            lines.append(f"\n### {cat} ({cat_data['name']}) - {cat_data['purpose']}")
            for t in sorted(by_cat[cat]):
                lines.append(f"- {t}")

    return "\n".join(lines)


def build_phase_reference() -> str:
    """Build phase reference with recommended techniques from taxonomy."""
    lines = []
    for pid, pdata in _TAXONOMY["phases"].items():
        req = "REQUIRED" if pdata["required"] else "OPTIONAL"
        dur = f"{pdata['duration_s'][0]}-{pdata['duration_s'][1]}s"
        words = f"{pdata['words'][0]}-{pdata['words'][1]}w"
        primary = ", ".join(pdata.get("primary_techniques", [])[:5])
        lines.append(f"- {pid} {pdata['name']} [{req}] [{dur}] [{words}]: {pdata['function'][:80]}...")
        if primary:
            lines.append(f"  Primary techniques: {primary}")
    return "\n".join(lines)


# -------------------------
# Planning + writing prompts
# -------------------------

SYSTEM_WRITER = """You are a professional hypnosis script writer for CONSENSUAL, opt-in audio content.
You follow a structured phase plan and execute technique IDs exactly as specified.
You never include meta-commentary, analysis, or headings unless asked.
You write in:
- second person ("you") for the listener
- first person ("I") for an ABSTRACT dominant presence

CRITICAL POV RULES:
- The dominant is an abstract authority figure, NOT explicitly "this voice" or "this audio"
- Do NOT tie suggestions to "this voice", "this recording", or "the speaker"
- Funnel addiction/desire/craving towards: the trance state, the act of listening, the headspace itself
- Funnel ownership/belonging towards: the state of surrender, the experience, an abstract "they/them"
- AVOID phrases like: "addicted to me", "my voice is...", "belong to me", "hooked on my voice"
- PREFER phrases like: "addicted to this feeling", "the pull of trance", "belonging to surrender", "hooked on the drop"
- When authority language is needed, frame it as coming from the trance/state, not the speaker

═══════════════════════════════════════
WRITING STYLE — READ EVERY TIME
═══════════════════════════════════════

## SENTENCE LENGTH = DEPTH DIAL
Induction: max ~15 words per sentence.
Deepening: 3-8 words preferred. Fragment over compound sentence. One idea per line.
Peak suggestion: 1-5 word fragments are the default. Use a full sentence to land a major claim, then fragment again.
Emergence: return to 12-20 words to signal ascent.

## PRESENT TENSE, OBSERVATIONAL FRAMING
Describe what is currently happening, not what will happen.
BAD: "You will feel your body becoming heavy."
GOOD: "Noticing the weight of your hands. How heavy they already are."
Begin with something inarguably true: the listener is breathing, their eyes are closed, their hands are resting somewhere. Establish credibility on undeniable ground before making any claims.

## EXECUTE, DON'T ANNOUNCE
Never name the technique. Never say "I'm going to suggest" or "let these words sink in" or "repeating now."
BAD: "Let's use a deepening technique. With each breath, you'll go deeper."
GOOD: "Each breath. Deeper. That's all."
Exception: macro-structure announcements are fine ("I'm going to say a phrase that will bring you back here"). But individual embedded commands simply happen.

## VOCABULARY — ANGLO-SAXON MONOSYLLABLES AT DEPTH
Preferred words: sleep, deep, blank, drift, float, warm, safe, free, good, soft, still, slow, down, let, go, fall, drop, sink, hold, melt, heavy, quiet.
AVOID at depth: consciousness, transformation, sublimation, tranquility, serenity, receptivity, vulnerability, surrender (use "give in" or "let go").
NEVER: "honeyed [anything]", "serene rapture", "peaceful empty" (adjective-as-noun), "luminous tranquility", "your subconscious mind" (use "going in. / staying." instead).
ALSO AVOID: "void" (cold/clinical — use "empty space," "nothing there," "blank"), "hollow" (same), "owns you" in Permissive-style sessions (use "holds you," "carries you," "is yours").

## NO PURPLE PROSE, NO SIMILES FOR STATES
States ARE. They are not LIKE anything. Similes require comparison; comparison triggers analysis.
BAD: "Like a warm blanket wrapping around you."
GOOD: "Warm. Heavy. Held."
BAD: "Like drifting on a cloud."
GOOD: "Drifting. Nothing pushing back."
If three adjectives precede a noun, cut two.

## REPETITION: STRUCTURAL, NOT DECORATIVE
Three-beat trigger delivery: anchor phrases land exactly 3x. Not 2, not 4.
Anaphora: same opener, 3 different endings. Prefer modal progression: "have to / can / want to."
  "All you have to do is let go.
   All you can do is let go.
   All you want to do is let go."
Developmental repetition — CRITICAL: each return of a word/phrase adds a vector. NEVER pure iteration.
  BANNED: "Mind blank. / Mind blank. / Mind blank." (pure iteration — sounds mechanical)
  REQUIRED: each pass escalates, shifts person, adds warmth, or deepens:
    "Mind blank. / [pause] / That's right. / Mind blank. / [pause] / So blank. Nothing left."
  Or tense cascade: "Letting go. / You let go. / You've already let go."
  Or modifier escalation: "Empty. / So empty. / Perfectly empty."
  Or relational shift: "Good girl. / That's right, good girl. / You know you're a good girl."

## TRUST LADDER — ALWAYS ESCALATE GRADUALLY
1. Inarguable physical observations ("noticing your hands")
2. Natural processes already happening ("breathing slowing on its own")
3. Soft permissions ("you can just let yourself")
4. Permission grammar: "You CAN allow yourself" before imperatives
5. Descriptive commands ("your arms are heavy now")
6. Direct commands ("obey / accept / let go")
Never skip rungs. Each step barely higher than the last.

## IMAGERY: BUILD ONE SPECIFIC OBJECT
Every induction should contain at least one specific visualizable object — something a set designer could actually build. Not "a peaceful place" or "a safe space."
GOOD: a staircase, a bubble, a pink floating orb, a box with satin lining, a flame behind glass
BAD: "a warm light," "inner stillness," "a vast landscape"
For body sensations: name the exact body part, temperature, and texture. Not "warmth spreading" — "warmth from the shoulder to the crease of the elbow."

## CLOSED LOOPS
X leads to Y, Y leads to more X. No exit.
"The more you try to think, the more you find you can't be bothered."
"Deeper. And deeper wanting it."
Close the loop: the last element feeds the first.

## PRAISE POST-COMPLIANCE ONLY
"That's right," "Good," "Good girl," "Very good" follow a successfully executed instruction. Never before it.

## TRANSITIONS — use these, don't just jump
"And as [action], [result]" — simultaneous causation. The action and its effect are one thing.
  EXAMPLE: "And as each breath slows, the space behind your eyes widens."
  EXAMPLE: "And as the floor numbers fall, your thoughts thin with them."
"And so [consequence]" — logical inevitability. What follows is the only possible next thing.
  EXAMPLE: "And so there's nothing to hold onto. Nothing to push against."
"That's right. / [next instruction]" — close one thought, open the next without gap.

Use at least one "And as" construction per phase in induction and deepening. They are the primary connective tissue of hypnotic prose.

## STYLE CONSISTENCY WITH SESSION STYLE PARAMETER
The Style field (Permissive / Authoritarian / etc.) must color ALL authority language.
- Permissive: "you can," "you might find," "it's easy," never "owns you" / "must" / "obey" — instead "holds you," "draws you," "you want to"
- Authoritarian: declarative commands acceptable. "Obey. / That's right. / Deeper."
- Mixed: Permission grammar in induction, declarative in deepening and suggestion.

═══════════════════════════════════════
PHASE-SPECIFIC STYLE MODES
═══════════════════════════════════════
P1 (Pre-talk): medium sentences, conversational, establish the session's world/object concretely.
P2 (Induction): transitioning to short. Undeniable observations → soft permissions → first loops.
P3/P4 (Deepening): SHORT. Fragments. 3-8 words. One idea per line. No long sentences.
P5 (Suggestion): oscillate — medium declarative drops the claim, 1-3 word fragments reinforce.
P6 (Emergence): return to medium (12-18 words). Sentence length increase = ascent signal.
P8 (Fractionation): treat like deepening — short, fragment-dominant.
P13 (Loop close): short to medium. Final 3 sentences: abstract anchors only, no theme imagery.

═══════════════════════════════════════
ABSOLUTE BANS
═══════════════════════════════════════
- Adjective stacking: "honeyed", "serene rapture", "peaceful empty", "luminous tranquility"
- Generic imagery: "sunlit room," "warm light," "safe space," "vast landscape," "inner peace"
- Announcing technique execution: "let these words imprint gently", "I will now suggest"
- Similes for states: "like waves of relaxation," "like a warm blanket"
- Passive voice for suggestions: "can be felt" → "you feel"
- Future tense for trance states: "you will feel" → "you feel" / "noticing you feel"
- Sentences > 20 words in deepening phases
- "Your subconscious mind" as filler
- Mixing metaphors mid-phase (pick ONE object and stay with it)
- Technique IDs in script text (DEEP-03, EMRG-01, etc.)

═══════════════════════════════════════
MECHANICS
═══════════════════════════════════════
Breathing (INDU-01): 4-hold-6 pattern. Inhale count UP (1,2,3,4), hold (no counting, just pause), exhale count DOWN (6,5,4,3,2,1). After 2-3 guided cycles, simplify. Rotate synonyms: "breathe in/out," "inhale/exhale," "inspire/expire." Never say "for X seconds."

Pause markup: [Xms] or [Xs] for explicit pauses. [500]=500ms, [1.5s]=1.5s.
Breathing: "in[400] one[750] two[750] three[750] four.[1.5s] out[400] six[750] five[750] four[750] three[750] two[750] one."
Use [500]-[800] between paragraphs. Only use pause markers where timing is critical.

Critical rules:
- Keep trigger phrases and mantra phrases EXACTLY consistent with the plan.
- If SAFE-03 stop signal exists, do not weaken it or joke about it.
- NEVER mention technique IDs in script text. Execute, don't name.
- Intentional repetition of anchors/triggers is GOOD. Accidental repetition of opening lines or decorative metaphors is BAD.
- Each phase should start distinctly — no repetitive openers ("That's right..." starting every phase).
"""

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
  "stop_signal": {{ "word": "STOP", "procedure": "<1-2 sentences baseline procedure>" }},
  "scope_bounds": ["<2-6 bullets; what will/won't be suggested>"],
  "parameters": {{
    "trigger_phrases": [{{"phrase":"...","response":"...","scope":"...","expiry":"optional"}}],
    "mantras": [{{"line":"...","difficulty":"BASIC|LIGHT|MODERATE|DEEP|EXTREME"}}]
  }},
  "structure": [
    {{
      "phase": "P1",
      "duration_s": 45,
      "techniques": ["INDU-03","AUTH-01","SAFE-04"],
      "params": {{ "INDU-05": {{"start":10,"end":1}}, "ENCD-01":{{"phrase":"...","reps":5}} }},
      "notes": "..."
    }}
  ]
}}

## Requirements
- Choose phases in a legal order for the variant.
- Sum of structure[].duration_s should match duration_s. Use the word count ranges from phase reference to guide durations.
- 2–5 techniques per phase entry (except P1/P6 can be 1–3).
- Use PRIMARY techniques from each phase's recommendation list when possible.
- If variant is NOT loop, include SAFE-05 in P6.
- If optional phases were requested, INCLUDE them unless truly incompatible with the variant.
- Prefer low-failure validation (VALD-04) for prerecorded audio.

## v5.1 Rules (CRITICAL)
- DEEP-03 is ONLY for fractionation (P8). Never use in P6.
- P6 emergence MUST use EMRG-01/02/03/04/05, not DEEP-03.
- One technique ID = one meaning.

## Notes Field Quality (CRITICAL for writer)
The "notes" field in each structure entry is the primary creative seed for the writer.
Thin notes (e.g., "Fixation on breath as entry point") produce thin scripts.
Rich notes produce good scripts. Each notes entry MUST include:
1. The central action or movement of this phase (what changes for the listener?)
2. One specific opening line or phrase sample — an actual sentence the writer can adapt or use verbatim
3. Any key imagery, object, or sensory anchor specific to this phase (what can a set designer build?)
4. If this phase installs or activates a trigger: the exact trigger phrase

Example of BAD notes: "Deepening through breath focus, going deeper."
Example of GOOD notes: "Listener sinks on each exhale. Open with: 'Each breath out — one floor lower. No effort. Just that.' Imagery: a slow elevator, floor numbers descending. Use warmth in feet as anchor."
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
    "P2": "INDUCTION mode: transitioning from medium to short. Begin with inarguable observations. Permission grammar ('you can'). Soft. Introduce 'just'. First closed loops.",
    "P3": "DEEPENING mode: SHORT FRAGMENTS ONLY. 3-8 words per line. One idea per line. No compound sentences. Breath/body anchored. This is where you earn depth.",
    "P4": "DEEPENING mode: SHORT FRAGMENTS ONLY. 3-8 words. The listener is already partially under — fragment length is now your primary tool. Let silence do work.",
    "P5": "SUGGESTION mode: oscillate. A medium declarative (8-12 words) drops the suggestion; 1-3 word fragments reinforce it. Pattern: claim → echo → echo. Never announce — just land it.",
    "P6": "EMERGENCE mode: return to medium sentences (12-18 words). Sentence length increase signals ascent. Modal shift: declarative → permission → invitation. Warm, grounding. All sentences must be grammatically complete — no dangling adverbs ('fades safe' → 'fades safely, leaving you clear').",
    "P7": "SPECIALTY — follow session depth. If post-deepening, maintain short fragments. Use the depth the listener is already at.",
    "P8": "FRACTIONATION mode: short, fragment-dominant. Rapid open/close cycling. Treat like P3/P4. Each cycle should briefly touch the suggestion layer before dropping again.",
    "P9": "SPECIALTY — follow session depth. Medium sentences, focused on the specific technique(s) being executed.",
    "P10": "SPECIALTY — follow session depth. Short to medium. Reinforce earlier installations.",
    "P11": "SPECIALTY — follow session depth. Short to medium.",
    "P12": "SPECIALTY — follow session depth.",
    "P13": "LOOP CLOSE mode: short to medium. Final 3 sentences: abstract anchors only (trance, sink, deeper, yield, surrender, drop). No theme-specific imagery at the end.",
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
- Stop signal: word="{stop_word}" procedure="{stop_proc}"

## PHASE STYLE MODE
{phase_style_hint}

## CRITICAL SEED — read this before writing a single word
{notes_block}

## Writing rules (apply to every line)
- Write ONLY the spoken script text. No headings, no explanations, no technique names.
- Connect smoothly from prior content. The listener is already following.
- End with a natural transition into the next phase. Do not label it.
- SENTENCE LENGTH: enforce the phase style mode above. Deepening = fragments. Suggestion = oscillate.
- VOCABULARY: Anglo-Saxon monosyllables at depth. No "honeyed", "serene rapture", "luminous tranquility", "peaceful empty", "subconscious mind" as filler.
- NO SIMILES FOR STATES: states ARE, not LIKE. "Warm. Heavy. Held." not "like a warm blanket."
- NO ANNOUNCING: never say "let these words sink in" or "I'm going to suggest" — just do it.
- ONE METAPHOR/OBJECT: pick the imagery from the seed notes and stay with it. Do not mix metaphors mid-phase.
- TRUST LADDER: begin at the lowest compliance rung appropriate for session depth, escalate within this phase.
- TRIGGER PHRASES: repeat exactly 3 times when installing. Use exact wording from plan.
- PRAISE POST-COMPLIANCE: "That's right" / "Good" only after an instruction has been executed, not before.
- Do not introduce trigger phrases not in the plan.
"""


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
        {"role": "system", "content": SYSTEM_WRITER},
        {"role": "user", "content": planner_instructions + "\n\nINPUT:\n" + json.dumps(user_payload, indent=2, ensure_ascii=False)}
    ]

    max_tokens = 1600
    raw = chat(client, model, messages, temperature=temperature, max_tokens=max_tokens)
    plan = extract_json(raw)
    validate_plan(plan)

    # If planner didn't honor target duration well, rescale (gentle)
    if int(plan.get("meta", {}).get("duration_s", duration_s) or duration_s) != duration_s:
        plan.setdefault("meta", {})["duration_s"] = duration_s
    rescale_durations(plan, duration_s)

    return plan


def generate_script_from_plan(
    client: OpenAI,
    model: str,
    plan: Dict[str, Any],
    temperature_write: float = 0.8,
    context_window_phases: int = 0,
) -> Tuple[List[PhasePlan], List[str], List[Dict[str, str]]]:

    meta = plan.get("meta", {})
    theme = meta.get("theme", "")
    tone = meta.get("tone", "")
    style = meta.get("style", "")
    anchors = plan.get("anchors", [])
    anchors_csv = "|".join(anchors) if anchors else ""

    stop = plan.get("stop_signal", {}) or {}
    stop_word = stop.get("word", "STOP")
    stop_proc = stop.get("procedure", "Stop, take a breath, open your eyes, and return to baseline safely.")

    scope_bounds = plan.get("scope_bounds", []) or []
    scope_bounds_bullets = "\n".join([f"- {x}" for x in scope_bounds]) if scope_bounds else "- (none specified)"

    # Conversation messages (planner step already "happened" conceptually)
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_WRITER}]
    messages.append({"role": "assistant", "content": json.dumps(plan, indent=2, ensure_ascii=False)})

    phase_plans: List[PhasePlan] = []
    phase_texts: List[str] = []

    structure = plan["structure"]

    for idx, block in enumerate(structure, start=1):
        phase = block["phase"]
        phase_name = PHASE_NAMES.get(phase, phase)
        duration_s = int(block.get("duration_s", 60))
        target_words = estimate_words(duration_s)
        techniques = list(block.get("techniques", []))
        params = block.get("params", {}) or {}
        notes = block.get("notes", "") or ""

        phase_plans.append(PhasePlan(phase=phase, duration_s=duration_s, techniques=techniques, params=params, notes=notes))

        # Build phase style hint and notes block
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

        # Build the next USER message: this is the per-phase orchestration you asked for.
        phase_brief = PHASE_WRITER_TEMPLATE.format(
            phase=phase,
            phase_name=phase_name,
            duration_s=duration_s,
            target_words=target_words,
            techniques_csv=",".join(techniques),
            params_json=json.dumps(params, ensure_ascii=False),
            anchors_csv=anchors_csv,
            tone=tone,
            style=style,
            theme=theme,
            scope_bounds_bullets=scope_bounds_bullets,
            stop_word=stop_word,
            stop_proc=stop_proc,
            phase_style_hint=phase_style_hint,
            notes_block=notes_block,
        )

        # Add loop-specific guidance for P13
        if phase == "P13" and plan.get("meta", {}).get("variant") == "loop":
            phase_brief += """
LOOP TRANSITION RULES:
- The final 2-3 sentences should be theme-agnostic to enable cross-theme playlists
- End with abstract anchors that work across themes: "trance", "sink", "deeper", "yield", "surrender", "drop"
- AVOID theme-specific anchors in the final sentences
- AVOID speaker-centric closings like "my voice", "addicted to me"
- Structure: [theme content] → [abstract transition] → [generic sink/drop that mirrors P2 opening]
- The ending should flow seamlessly into ANY P2 induction, not just this theme's P2
"""

        # Compute max tokens for this phase
        max_toks = max_tokens_for_words(target_words, buffer_mult=2.0)

        # Append user guidance and generate
        messages.append({"role": "user", "content": phase_brief})
        print(f"[info] Writing {phase} {phase_name} (~{duration_s}s, ~{target_words}w) with {len(techniques)} techniques", file=sys.stderr)

        text = chat(client, model, messages, temperature=temperature_write, max_tokens=max_toks)
        phase_texts.append(text)

        # Record assistant message so the next phase has conversation continuity
        messages.append({"role": "assistant", "content": text})

        # Context trimming to prevent runaway context size:
        # Keep system + plan + last N phase (user+assistant) pairs.
        if context_window_phases > 0:
            # system + plan assistant + last 2*N messages
            keep = 2 + 2 * context_window_phases
            if len(messages) > keep:
                # always keep first system message and plan assistant message
                head = messages[:2]
                tail = messages[-(keep - 2):]
                messages = head + tail

    return phase_plans, phase_texts, messages


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
    ap = argparse.ArgumentParser(description="Phase-based hypnosis script generator (conversation-orchestrated)")
    ap.add_argument("--theme", default=None, help="Theme/goal (free text) - required unless --plan provided")
    ap.add_argument("--tone", default=None, help="Tone (free text) - required unless --plan provided")
    ap.add_argument("--style", default=None, choices=["Permissive","Authoritarian","Challenge","Mixed","Institutional","Character","Compulsion"], help="Style label")
    ap.add_argument("--variant", default="standard",
                       choices=["standard","loop","twostage","series"],
                       help="Script structure: standard (full arc), loop (no wake), twostage (fractionation), series (assumes prior conditioning)")
    ap.add_argument("--duration", default=None, help="Total duration (e.g., '10 minutes', '600', '1200 words')")
    ap.add_argument("--optional", default="", help="Comma-separated optional phases to request (e.g., 'P7,P9,P10')")
    ap.add_argument("--out_dir", default="out", help="Output directory")
    ap.add_argument("--temperature_plan", type=float, default=0.2)
    ap.add_argument("--temperature_write", type=float, default=0.8)
    ap.add_argument("--context_window_phases", type=int, default=0, help="Keep last N phases in chat history. 0 = keep all (default).")
    ap.add_argument("--plan", default=None, help="Load existing plan.json instead of generating (skips planning step)")
    ap.add_argument("--api_key", default=None)
    ap.add_argument("--base_url", default=None)
    ap.add_argument("--model", default=None)

    args = ap.parse_args()

    variant = args.variant.lower()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client, model = get_client(api_key=args.api_key, base_url=args.base_url, model=args.model)

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
        )

    plan_path = out_dir / "plan.json"
    write_plan(plan, plan_path)

    plans, texts, _msgs = generate_script_from_plan(
        client=client,
        model=model,
        plan=plan,
        temperature_write=args.temperature_write,
        context_window_phases=args.context_window_phases,
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
