#!/usr/bin/env python3
"""
generate_mantras.py
-------------------

Production-oriented mantra generator using LLM with taxonomy-aware generation.

Design goals:
- Single-file orchestration (no extra modules required besides `openai`).
- Taxonomy-aware: uses theme definitions from conditioner or local ontologies.
- Template-ready output: generates mantras with {subject_*} and {dominant_*} placeholders.
- Batch mode: can generate for multiple themes in one run.
- Provider-agnostic: works with any OpenAI-compatible endpoint.

Outputs:
- mantras.json (array of mantra objects with metadata)
- Optional: mantras_raw.txt (plain text, one per line)

Quickstart:
  export LLM_API_KEY="..."
  export LLM_BASE_URL="xai"              # optional; defaults to openai
  export LLM_MODEL="grok-4-0414"         # optional

  python generate_mantras.py \
    --theme "obedience" \
    --count 20 \
    --tone "commanding" \
    --difficulty "LIGHT,MODERATE" \
    --output mantras.json

  # Batch mode from theme file
  python generate_mantras.py \
    --themes-file themes.txt \
    --count 15 \
    --output-dir mantras/

"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
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
# Mantra data structures
# -------------------------

DIFFICULTIES = ["BASIC", "LIGHT", "MODERATE", "DEEP", "EXTREME"]

@dataclass
class Mantra:
    text: str
    template: str
    theme: str
    difficulty: str
    tone: str
    has_subject: bool = False
    has_dominant: bool = False
    tags: List[str] = field(default_factory=list)


# -------------------------
# Template variable system
# -------------------------

TEMPLATE_VARIABLES = """
## Template Variable System

Mantras should use these placeholders for flexible rendering:

### Subject (the listener/hypnotee)
- {subject_subjective} → I / you / she / he / they / [name]
- {subject_objective} → me / you / her / him / them / [name]
- {subject_possessive} → my / your / her / his / their / [name]'s
- {subject_name} → puppet / pet / slave / toy / doll (a noun label)

### Dominant (the hypnotist/controller)
- {dominant_subjective} → I / you / she / he / they / [title]
- {dominant_objective} → me / you / her / him / them / [title]
- {dominant_possessive} → my / your / her / his / their / [title]'s
- {dominant_name} → Master / Mistress / Owner / Handler
- {dominant_title} → Sir / Ma'am / etc.

### Verb Conjugation (for subject agreement)
Use [verb_1st|verb_3rd] pattern:
- "I [am|is] obedient" → renders as "I am obedient" or "She is obedient"
- "I [want|wants] to obey" → renders as "I want to obey" or "The puppet wants to obey"

### Examples
Input: "I obey Master"
Template: "{subject_subjective} [obey|obeys] {dominant_name}"

Input: "My mind belongs to Mistress"
Template: "{subject_possessive} mind [belong|belongs] to {dominant_name}"

Input: "Good puppets don't think"
Template: "Good {subject_name}s don't think"
"""


# -------------------------
# Generation prompts
# -------------------------

SYSTEM_MANTRA_WRITER = """You are a professional hypnotic content writer creating short, impactful mantras for CONSENSUAL hypnosis audio.

You write mantras that are:
- SHORT: 3-15 words typically, max 20 words
- IMPACTFUL: Each mantra is a complete thought that reinforces the theme
- VARIED: Mix declarative statements, imperatives, and identity affirmations
- TEMPLATE-READY: Use the variable placeholders provided for flexible rendering

CRITICAL POV RULES:
- Write primarily in FIRST PERSON from the subject's perspective ("I obey", "My mind is empty")
- The dominant is referenced in THIRD PERSON with placeholders ({dominant_name}, {dominant_possessive})
- AVOID second person "you" - we're writing internal mantras the subject repeats
- AVOID tying mantras to "this voice" or "this recording"

DIFFICULTY LEVELS:
- BASIC: Gentle, relaxation-focused, no power exchange ("I feel calm", "Relaxation flows through me")
- LIGHT: Soft submission, focus, mild compliance ("I listen and follow", "My mind drifts pleasantly")
- MODERATE: Clear power exchange, obedience themes ("I obey {dominant_name}", "My thoughts belong to {dominant_possessive} will")
- DEEP: Strong submission, identity themes ("I am {dominant_possessive} {subject_name}", "My will dissolves")
- EXTREME: Intense themes, use sparingly ("I exist only to serve", "I am nothing without {dominant_name}")

OUTPUT FORMAT:
Return a JSON array of mantra objects. Each object must have:
- "text": The raw mantra text (human-readable, no placeholders)
- "template": The templated version with {subject_*} and {dominant_*} placeholders
- "difficulty": One of BASIC, LIGHT, MODERATE, DEEP, EXTREME
- "tags": Array of 1-3 keyword tags

Example output:
[
  {
    "text": "I obey Master without question",
    "template": "{subject_subjective} [obey|obeys] {dominant_name} without question",
    "difficulty": "MODERATE",
    "tags": ["obedience", "compliance"]
  },
  {
    "text": "My thoughts slow and fade",
    "template": "{subject_possessive} thoughts slow and fade",
    "difficulty": "LIGHT",
    "tags": ["blank", "empty"]
  }
]
"""

MANTRA_REQUEST_TEMPLATE = """Generate {count} mantras for the theme: "{theme}"

Tone: {tone}
Target difficulties: {difficulties}

{template_reference}

Theme context:
{theme_context}

Requirements:
- Generate exactly {count} mantras
- Distribute across the requested difficulty levels
- Each mantra should be distinct - avoid repetitive structures
- Use template variables correctly
- Include appropriate verb conjugation patterns [verb_1st|verb_3rd] where needed
- Return ONLY valid JSON array, no markdown code blocks

{additional_instructions}
"""


# -------------------------
# Theme context loading
# -------------------------

def load_theme_context(theme: str, ontology_dir: Optional[Path] = None) -> str:
    """
    Try to load theme context from:
    1. Local ontologies directory
    2. Conditioner mantras directory
    3. Fall back to generic description
    """
    contexts = []

    # Try autotranceweb ontologies
    if ontology_dir is None:
        # Check common locations
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "autotranceweb" / "ontologies",
            Path.home() / "autotranceweb" / "ontologies",
        ]
        for c in candidates:
            if c.exists():
                ontology_dir = c
                break

    if ontology_dir and ontology_dir.exists():
        # Try exact match first, then case-insensitive
        theme_file = ontology_dir / f"{theme}.json"
        if not theme_file.exists():
            for f in ontology_dir.glob("*.json"):
                if f.stem.lower() == theme.lower():
                    theme_file = f
                    break

        if theme_file.exists():
            try:
                with open(theme_file) as f:
                    data = json.load(f)
                if "description" in data:
                    contexts.append(f"Description: {data['description']}")
                if "keywords" in data:
                    contexts.append(f"Keywords: {', '.join(data['keywords'][:10])}")
                if "psychological_appeal" in data:
                    contexts.append(f"Psychological appeal: {data['psychological_appeal']}")
            except (json.JSONDecodeError, KeyError):
                pass

    # Try conditioner mantras for existing examples
    conditioner_paths = [
        Path(__file__).resolve().parent.parent.parent / "conditioner" / "mantras",
        Path.home() / "conditioner" / "mantras",
    ]
    for cpath in conditioner_paths:
        if cpath.exists():
            mantra_file = cpath / f"{theme.lower()}.json"
            if mantra_file.exists():
                try:
                    with open(mantra_file) as f:
                        data = json.load(f)
                    if "mantras" in data and data["mantras"]:
                        examples = [m["text"] for m in data["mantras"][:5]]
                        contexts.append(f"Example mantras from existing content:\n" + "\n".join(f"- {e}" for e in examples))
                except (json.JSONDecodeError, KeyError):
                    pass
            break

    if not contexts:
        contexts.append(f"Theme '{theme}' - generate mantras that embody this concept for hypnotic conditioning.")

    return "\n\n".join(contexts)


# -------------------------
# Robust JSON extraction
# -------------------------

def extract_json(text: str) -> List[Dict[str, Any]]:
    """
    Try to parse strict JSON array. If the model wrapped it in extra text,
    extract the first [...] block.
    """
    text = text.strip()

    # Remove markdown code blocks if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        raise ValueError("Expected JSON array")
    except json.JSONDecodeError:
        # extract first json array
        m = re.search(r"\[.*\]", text, flags=re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def validate_mantra(m: Dict[str, Any], theme: str, tone: str) -> Optional[Mantra]:
    """Validate and convert a mantra dict to Mantra object."""
    if not isinstance(m, dict):
        return None

    text = m.get("text", "").strip()
    template = m.get("template", text).strip()
    difficulty = m.get("difficulty", "MODERATE").upper()
    tags = m.get("tags", [])

    if not text:
        return None

    if difficulty not in DIFFICULTIES:
        difficulty = "MODERATE"

    if not isinstance(tags, list):
        tags = []

    # Detect if template uses subject/dominant variables
    has_subject = "{subject_" in template or "[" in template
    has_dominant = "{dominant_" in template

    return Mantra(
        text=text,
        template=template,
        theme=theme,
        difficulty=difficulty,
        tone=tone,
        has_subject=has_subject,
        has_dominant=has_dominant,
        tags=tags[:5],  # Cap at 5 tags
    )


# -------------------------
# Generation
# -------------------------

def generate_mantras(
    client: OpenAI,
    model: str,
    theme: str,
    count: int = 20,
    tone: str = "commanding",
    difficulties: Optional[List[str]] = None,
    additional_instructions: str = "",
    temperature: float = 0.9,
    ontology_dir: Optional[Path] = None,
) -> List[Mantra]:
    """Generate mantras for a single theme."""

    if difficulties is None:
        difficulties = ["LIGHT", "MODERATE", "DEEP"]

    # Validate difficulties
    difficulties = [d.upper() for d in difficulties if d.upper() in DIFFICULTIES]
    if not difficulties:
        difficulties = ["MODERATE"]

    theme_context = load_theme_context(theme, ontology_dir)

    user_prompt = MANTRA_REQUEST_TEMPLATE.format(
        count=count,
        theme=theme,
        tone=tone,
        difficulties=", ".join(difficulties),
        template_reference=TEMPLATE_VARIABLES,
        theme_context=theme_context,
        additional_instructions=additional_instructions,
    )

    messages = [
        {"role": "system", "content": SYSTEM_MANTRA_WRITER},
        {"role": "user", "content": user_prompt},
    ]

    print(f"[info] Generating {count} mantras for theme '{theme}'...", file=sys.stderr)

    # Estimate tokens needed: ~50 tokens per mantra
    max_tokens = min(count * 80 + 200, 4000)

    raw = chat(client, model, messages, temperature=temperature, max_tokens=max_tokens)

    try:
        mantra_dicts = extract_json(raw)
    except json.JSONDecodeError as e:
        print(f"[error] Failed to parse JSON response: {e}", file=sys.stderr)
        print(f"[error] Raw response (first 500 chars): {raw[:500]}", file=sys.stderr)
        return []

    mantras = []
    for m in mantra_dicts:
        validated = validate_mantra(m, theme, tone)
        if validated:
            mantras.append(validated)

    print(f"[ok] Generated {len(mantras)} valid mantras", file=sys.stderr)
    return mantras


def generate_batch(
    client: OpenAI,
    model: str,
    themes: List[str],
    count_per_theme: int = 15,
    tone: str = "commanding",
    difficulties: Optional[List[str]] = None,
    temperature: float = 0.9,
    ontology_dir: Optional[Path] = None,
) -> Dict[str, List[Mantra]]:
    """Generate mantras for multiple themes."""
    results = {}
    for theme in themes:
        mantras = generate_mantras(
            client=client,
            model=model,
            theme=theme,
            count=count_per_theme,
            tone=tone,
            difficulties=difficulties,
            temperature=temperature,
            ontology_dir=ontology_dir,
        )
        results[theme] = mantras
    return results


# -------------------------
# Output writers
# -------------------------

def write_mantras_json(mantras: List[Mantra], out_path: Path) -> None:
    """Write mantras to JSON file."""
    data = [asdict(m) for m in mantras]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_mantras_txt(mantras: List[Mantra], out_path: Path) -> None:
    """Write mantras to plain text file (templates only)."""
    lines = [m.template for m in mantras]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_conditioner_format(theme: str, mantras: List[Mantra], out_path: Path) -> None:
    """Write mantras in conditioner-compatible format."""
    # Map difficulty to base_points
    points_map = {
        "BASIC": 10,
        "LIGHT": 20,
        "MODERATE": 40,
        "DEEP": 70,
        "EXTREME": 100,
    }

    data = {
        "theme": theme,
        "description": f"Generated mantras for {theme}",
        "mantras": [
            {
                "text": m.template,
                "base_points": points_map.get(m.difficulty, 40),
            }
            for m in mantras
        ]
    }
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# -------------------------
# CLI
# -------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate hypnotic mantras with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single theme
  python generate_mantras.py --theme obedience --count 20 --output mantras.json

  # Multiple difficulties
  python generate_mantras.py --theme relaxation --difficulty BASIC,LIGHT --count 15

  # Batch mode from file
  python generate_mantras.py --themes-file themes.txt --output-dir mantras/

  # Conditioner-compatible output
  python generate_mantras.py --theme submission --count 25 --format conditioner

Difficulty levels:
  BASIC     - Gentle relaxation, no power exchange
  LIGHT     - Soft submission, focus, mild compliance
  MODERATE  - Clear power exchange, obedience themes
  DEEP      - Strong submission, identity themes
  EXTREME   - Intense themes, use sparingly
"""
    )

    # Input options
    ap.add_argument("--theme", help="Theme to generate mantras for")
    ap.add_argument("--themes-file", help="File with themes (one per line) for batch mode")
    ap.add_argument("--count", type=int, default=20, help="Number of mantras per theme (default: 20)")
    ap.add_argument("--tone", default="commanding", help="Tone/style (default: commanding)")
    ap.add_argument("--difficulty", default="LIGHT,MODERATE,DEEP",
                   help="Comma-separated difficulties to target (default: LIGHT,MODERATE,DEEP)")

    # Output options
    ap.add_argument("--output", "-o", help="Output file (for single theme)")
    ap.add_argument("--output-dir", help="Output directory (for batch mode)")
    ap.add_argument("--format", choices=["json", "txt", "conditioner"], default="json",
                   help="Output format (default: json)")

    # Generation options
    ap.add_argument("--temperature", type=float, default=0.9, help="Temperature (default: 0.9)")
    ap.add_argument("--ontology-dir", help="Path to ontology JSON files for theme context")

    # Provider options
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--model", default=None)

    args = ap.parse_args()

    # Validate inputs
    if not args.theme and not args.themes_file:
        print("[error] Must provide --theme or --themes-file", file=sys.stderr)
        sys.exit(1)

    # Parse difficulties
    difficulties = [d.strip().upper() for d in args.difficulty.split(",")]

    # Get client
    client, model = get_client(api_key=args.api_key, base_url=args.base_url, model=args.model)

    ontology_dir = Path(args.ontology_dir) if args.ontology_dir else None

    # Single theme mode
    if args.theme:
        mantras = generate_mantras(
            client=client,
            model=model,
            theme=args.theme,
            count=args.count,
            tone=args.tone,
            difficulties=difficulties,
            temperature=args.temperature,
            ontology_dir=ontology_dir,
        )

        if not mantras:
            print("[error] No mantras generated", file=sys.stderr)
            sys.exit(1)

        # Determine output path
        if args.output:
            out_path = Path(args.output)
        else:
            ext = "txt" if args.format == "txt" else "json"
            out_path = Path(f"{args.theme.lower()}_mantras.{ext}")

        # Write output
        if args.format == "txt":
            write_mantras_txt(mantras, out_path)
        elif args.format == "conditioner":
            write_conditioner_format(args.theme, mantras, out_path)
        else:
            write_mantras_json(mantras, out_path)

        print(f"[ok] Wrote {len(mantras)} mantras to {out_path}", file=sys.stderr)

    # Batch mode
    else:
        themes_file = Path(args.themes_file)
        if not themes_file.exists():
            print(f"[error] Themes file not found: {themes_file}", file=sys.stderr)
            sys.exit(1)

        themes = [line.strip() for line in themes_file.read_text().splitlines() if line.strip() and not line.startswith("#")]

        if not themes:
            print("[error] No themes found in file", file=sys.stderr)
            sys.exit(1)

        print(f"[info] Batch mode: {len(themes)} themes", file=sys.stderr)

        out_dir = Path(args.output_dir) if args.output_dir else Path("mantras_out")
        out_dir.mkdir(parents=True, exist_ok=True)

        results = generate_batch(
            client=client,
            model=model,
            themes=themes,
            count_per_theme=args.count,
            tone=args.tone,
            difficulties=difficulties,
            temperature=args.temperature,
            ontology_dir=ontology_dir,
        )

        total = 0
        for theme, mantras in results.items():
            if mantras:
                ext = "txt" if args.format == "txt" else "json"
                out_path = out_dir / f"{theme.lower()}.{ext}"

                if args.format == "txt":
                    write_mantras_txt(mantras, out_path)
                elif args.format == "conditioner":
                    write_conditioner_format(theme, mantras, out_path)
                else:
                    write_mantras_json(mantras, out_path)

                total += len(mantras)

        print(f"\n[ok] Generated {total} mantras across {len(results)} themes", file=sys.stderr)
        print(f"[ok] Output directory: {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
