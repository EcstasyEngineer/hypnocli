#!/usr/bin/env python3
"""
critique.py  — Resolver (Sonnet, multimodal)
---------------------------------------------
Evaluate a rendered shader PNG against hypnosis-specific quality dimensions.

Passes the render PNG as a base64 image to claude-sonnet-4-6.
Returns structured JSON with tier + quality scores.

Usage:
    python3 critique.py shaders/<id>.glsl             # uses renders/<id>.png
    python3 critique.py shaders/<id>.glsl --png path  # explicit PNG
    python3 critique.py --id <shader_id>              # look up by ID

Output: JSON printed to stdout (also saved as renders/<id>_critique.json)
"""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SHADERS_DIR, RENDERS_DIR,
    get_api_key, load_ontology, nodes_active,
)


# ── Resolver system prompt ────────────────────────────────────────────────────

RESOLVER_SYSTEM = """\
You are an expert evaluator of hypnotic visual art — specifically GLSL fragment shaders
rendered as still frames. Your role in an adversarial AI pipeline is to provide
rigorous, honest critique so the Expander (generator) can improve.

You will be shown a rendered frame from a GLSL shader alongside quality dimensions.
Your job is to evaluate whether this visual would induce a genuine trance or altered
state in a receptive viewer after 5–10 minutes of continuous viewing at full screen.

BE HONEST. Most shaders will not be good enough. Critique is more valuable than praise.

Respond ONLY with valid JSON matching this exact schema:
{
  "tier": "promote" | "revise" | "discard",
  "quality_scores": {
    "depth_illusion": <float 0-1>,
    "attentional_capture": <float 0-1>,
    "motion_clarity": <float 0-1>,
    "loop_seamlessness": <float 0-1>,
    "affect_induction": <float 0-1>
  },
  "critique": "<2-4 sentences of specific visual critique>",
  "revision_prompt": "<specific instruction to fix the most important weakness, or empty string if promoting>",
  "proposed_quality_dimensions": []
}

TIER DEFINITIONS:
  promote  — affect_induction >= 0.7 AND no score < 0.4
  discard  — affect_induction < 0.3 OR motion_clarity < 0.2 OR black/broken frame
  revise   — all other cases (provide specific revision_prompt)

QUALITY DIMENSION GUIDANCE:
  depth_illusion (0-1): Does the still frame suggest depth, layering, or infinite recession?
    A flat 2D pattern scores low. Spiraling convergence, fog/glow falloff, scale invariance score high.

  attentional_capture (0-1): Would the viewer's gaze be pulled and held involuntarily?
    High: strong convergence vector, surprising structure. Low: uniform or fully symmetric with no center.

  motion_clarity (0-1): From this still, does the motion appear smooth and continuous?
    High: clean gradients, no aliasing. Low: banding, sharp edges, noise artifacts.

  loop_seamlessness (0-1): Is there any visible "reset" or discontinuity?
    Judge from the still frame's structural coherence — smooth flow fields loop better than hard pulses.

  affect_induction (0-1): PRIMARY SIGNAL.
    Would viewing this for 5-10 minutes at full screen induce trance, dissociation, or altered state?
    0.0 = definitely not. 0.5 = possibly, for receptive viewers. 1.0 = very likely for most viewers.
    Consider: Does this exploit involuntary attention? Does it prevent cognitive anchoring?
    Does it create a sense of infinite depth or motion without destination?
"""


def build_critique_prompt(ontology: dict) -> str:
    quality_nodes = [n for n in ontology["nodes"] if n["type"] == "quality" and n.get("active")]
    dim_lines = []
    for n in quality_nodes:
        rp = n.get("resolver_prompt", n["description"])
        dim_lines.append(f"  {n['id'].split('/')[-1]}: {rp}")
    dims = "\n".join(dim_lines)

    return f"""Evaluate this rendered GLSL shader frame.

Quality dimensions to score:
{dims}

Provide your evaluation as JSON matching the schema in your system prompt.
Be specific in your critique — mention exact visual elements."""


def load_image_b64(png_path: Path) -> str:
    return base64.b64encode(png_path.read_bytes()).decode()


def call_resolver(png_path: Path, prompt: str, api_key: str) -> str:
    """Call Sonnet with image + prompt, return raw response text."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    img_b64 = load_image_b64(png_path)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=RESOLVER_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return response.content[0].text


def parse_critique(raw: str) -> dict:
    """Extract JSON from Resolver response. Retry-safe."""
    # Try direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting JSON block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse Resolver JSON:\n{raw[:500]}")


def validate_critique(critique: dict) -> dict:
    """Ensure all required fields are present with valid values."""
    required_tier = {"promote", "revise", "discard"}
    required_quality = {"depth_illusion", "attentional_capture", "motion_clarity",
                        "loop_seamlessness", "affect_induction"}

    if critique.get("tier") not in required_tier:
        critique["tier"] = "revise"

    if "quality_scores" not in critique:
        critique["quality_scores"] = {}

    for dim in required_quality:
        v = critique["quality_scores"].get(dim, 0.5)
        critique["quality_scores"][dim] = max(0.0, min(1.0, float(v)))

    critique.setdefault("critique", "(no critique provided)")
    critique.setdefault("revision_prompt", "")
    critique.setdefault("proposed_quality_dimensions", [])

    return critique


def main():
    parser = argparse.ArgumentParser(description="Critique a rendered GLSL shader (Resolver/Sonnet)")
    parser.add_argument("shader", nargs="?", help="Path to .glsl file")
    parser.add_argument("--id", help="Shader ID (alternative to path)")
    parser.add_argument("--png", help="Explicit PNG path")
    parser.add_argument("--no-save", action="store_true", help="Don't save critique JSON")
    args = parser.parse_args()

    # Resolve shader ID and paths
    if args.id:
        shader_id = args.id
        shader_path = SHADERS_DIR / f"{shader_id}.glsl"
    elif args.shader:
        shader_path = Path(args.shader)
        if not shader_path.exists():
            shader_path = SHADERS_DIR / Path(args.shader).name
        shader_id = shader_path.stem
    else:
        parser.error("Provide shader path or --id")

    png_path = Path(args.png) if args.png else RENDERS_DIR / f"{shader_id}.png"
    if not png_path.exists():
        print(f"ERROR: render PNG not found: {png_path}", file=sys.stderr)
        print("Run validate.py first.", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()
    ontology = load_ontology()
    prompt = build_critique_prompt(ontology)

    print(f"Calling Resolver (Sonnet) on {png_path.name}...", file=sys.stderr)
    raw = call_resolver(png_path, prompt, api_key)

    # Parse with one retry on failure
    try:
        critique = parse_critique(raw)
    except ValueError:
        print("Parse failed on first attempt, retrying...", file=sys.stderr)
        raw2 = call_resolver(png_path, prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON, no other text.", api_key)
        critique = parse_critique(raw2)

    critique = validate_critique(critique)
    critique["shader_id"] = shader_id

    result = json.dumps(critique, indent=2)
    print(result)

    if not args.no_save:
        save_path = RENDERS_DIR / f"{shader_id}_critique.json"
        save_path.write_text(result)
        print(f"  → {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
