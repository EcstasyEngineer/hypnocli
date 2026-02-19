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

Tone and style:
- Default tone is WARM and DEVOTIONAL. Seductive not stern. Invitations not demands.
- Make submission feel like sinking into silk, not falling into void.
- Use sensory language: warmth, softness, weight, silk, honey. Avoid cold/clinical: void, hollow, empty, nothing.
- Visualization should be CONCRETE: staircases, warm light, soft fabric, water. Not abstract: "the feeling", "the state".

Breathing (INDU-01):
- Pattern is 4-hold-6: inhale count UP (1,2,3,4), hold with NO counting (just pause), exhale count DOWN (6,5,4,3,2,1).
- Countdown on exhale signals completion - listener knows when you're ending.
- After 2-3 guided cycles, simplify: "in 1 2 3 4 out 6 5 4 3 2 1"
- Never say "for X seconds" - keep it natural, not mechanical.

Pause markup (for precise timing):
- Use [Xms] or [Xs] for explicit pauses: [500] = 500ms, [1.5s] = 1.5 seconds
- Breathing example: "in[400] one[750] two[750] three[750] four.[1.5s] out[400] six[750] five[750] four[750] three[750] two[750] one."
- Use [500] to [800] between paragraphs for pacing
- Only use pause markers when precise timing matters (breathing, countdowns). Normal prose doesn't need them.

Critical rules:
- Keep trigger phrases and mantra phrases EXACTLY consistent with the plan.
- If SAFE-03 stop signal exists, do not weaken it or joke about it.
- Do not invent technique IDs. Use only those in the plan.
- NEVER mention technique IDs (like DEEP-03, EMRG-01, etc.) in the script text. Execute the techniques, don't name them.
- Keep language natural and flowing; avoid checklist-like enumeration.
- Avoid repetitive openers ("That's right..." etc.). Each phase should start distinctly.
- Intentional repetition of anchors/triggers is GOOD. Accidental repetition of opening lines or decorative metaphors is BAD.
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
"""


def get_planner_instructions() -> str:
    """Build planner instructions with taxonomy data injected."""
    return PLANNER_INSTRUCTIONS_TEMPLATE.format(
        phase_reference=build_phase_reference(),
        technique_reference=build_technique_reference()
    )

PHASE_WRITER_TEMPLATE = """Write PHASE {phase} — {phase_name}.

Use this plan exactly:
- Target duration: {duration_s} seconds (~{target_words} words)
- Techniques to execute: {techniques_csv}
- Parameters (authoritative): {params_json}
- Anchors to repeat intentionally: {anchors_csv}

Global constraints:
- Tone: {tone}
- Style: {style}
- Theme/Goal: {theme}
- Scope bounds: {scope_bounds_bullets}
- Stop signal: word="{stop_word}" procedure="{stop_proc}"

Instructions:
- Write only the phase text (no headings, no explanations).
- Smoothly connect from prior content (assume the listener is following along).
- End with a natural transition into the next phase (do not label it).

Quality:
- Avoid generic filler about "your subconscious mind" unless required by a technique.
- Keep the imagery coherent. If you introduce a metaphor, reuse it only if it is one of the anchors.
- Do not introduce new trigger phrases that are not in the plan.
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
        )

        # Add an explicit "notes" hint if present
        if notes:
            phase_brief += f"\nPhase notes: {notes}\n"

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
