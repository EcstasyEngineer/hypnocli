#!/usr/bin/env python3
"""
generate.py  — Expander (Haiku)
--------------------------------
Generate a new GLSL shader using layer-aware ontology selection.

Layers selected independently (each with its own epsilon-greedy pass):
  geometry      — 2-4 nodes (field structure, radial/angular/noise/flow)
  colorization  — exactly 1 node (how field maps to color)
  shaping       — 0-2 nodes (post-processing)
  timing        — 0-1 nodes (animation rhythm)

Usage:
    python3 generate.py
    python3 generate.py --archetype convergent
    python3 generate.py --revision-prompt "tighten the spiral"
    python3 generate.py --dry-run
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SHADERS_DIR, SEEDS_DIR,
    get_api_key, load_ontology, node_by_id, new_shader_id,
)

EXPANDER_SYSTEM = """\
You are an expert GLSL shader author specializing in hypnotic and trance-inducing visual art.

Your task: write a WebGL fragment shader in Shadertoy format that is visually hypnotic —
capable of inducing a trance-like altered state in a receptive viewer after 5–10 minutes
of continuous viewing at full screen.

HARD REQUIREMENTS:
- Output ONLY the GLSL code, no markdown fences, no explanation
- Entry point: void mainImage(out vec4 fragColor, in vec2 fragCoord)
- Declare uniforms: uniform vec3 iResolution; uniform float iTime; uniform vec4 iMouse;
- No iChannel* texture samples
- Loop bounds must be compile-time constants
- All loops must have <= 64 iterations
- Must compile under GLSL ES 3.00

HYPNOSIS PRINCIPLES:
- Motion should be continuous and never fully resolve
- At least one convergent motion vector pulling attention toward a center or point
- Depth illusion preferred: make the image feel 3D or infinitely deep
- Avoid hard cuts or sudden changes
- The colorization layer should be implemented EXACTLY as specified — do not substitute
  a different coloring approach even if you think it would look better
"""


# ── Node selection ────────────────────────────────────────────────────────────

def thompson_sample(node: dict) -> float:
    """
    Draw one sample from Beta(alpha, beta) posterior for this node.
    Unsampled nodes draw from Beta(1,1) = Uniform, so they're always competitive.
    """
    conf = node["confidence"]
    score = node["score"]
    # Beta parameters: alpha = successes, beta = failures (minimum 1 each)
    alpha = max(score * conf, 1.0)
    beta  = max((1.0 - score) * conf, 1.0)
    return random.betavariate(alpha, beta)


def pick(nodes: list[dict], n: int, total_ratings: int) -> list[dict]:
    """
    Pick n nodes via Thompson sampling.
    Each node draws a random sample from its posterior — gives variety
    every cycle while still preferring better-scoring nodes over time.
    Unsampled nodes draw from Uniform, so they get tried naturally.
    """
    if not nodes:
        return []
    n = min(n, len(nodes))
    scored = sorted(nodes, key=lambda nd: thompson_sample(nd), reverse=True)
    return scored[:n]


def active(ontology: dict, layer: str, subpath: str | None = None) -> list[dict]:
    """Get active nodes for a given layer, optionally filtered by id prefix."""
    return [
        n for n in ontology["nodes"]
        if n.get("layer") == layer
        and n.get("active")
        and not n.get("retired")
        and n["type"] == "technique"
        and (subpath is None or n["id"].startswith(subpath))
    ]


def total_ratings(ontology: dict) -> int:
    """Sum of confidence across all rated nodes — used as UCB1 total."""
    return sum(n["confidence"] for n in ontology["nodes"] if n.get("confidence", 0) > 0)


def select_nodes(ontology: dict, archetype_id: str | None) -> dict:
    """Layer-aware node selection via UCB1. Returns dict of layer -> [nodes]."""
    selected: dict = {}
    n_rated = total_ratings(ontology)

    # ── Archetype ─────────────────────────────────────────────────────────────
    archetypes = [n for n in ontology["nodes"] if n["type"] == "archetype" and n.get("active")]
    if archetype_id:
        arch = node_by_id(ontology, f"archetypes/{archetype_id}")
        if not arch:
            print(f"WARNING: archetype '{archetype_id}' not found, selecting randomly", file=sys.stderr)
            arch = random.choice(archetypes)
    else:
        arch = pick(archetypes, 1, n_rated)[0]
    selected["archetype"] = arch

    arch_key = arch["id"].split("/")[-1]

    # ── Geometry layer ─────────────────────────────────────────────────────────
    geo_subpaths = {
        "convergent":         ["techniques/radial/", "techniques/angular/"],
        "linear_rings":       ["techniques/radial/", "techniques/angular/"],
        "log_arms":           ["techniques/radial/", "techniques/angular/", "techniques/noise/"],
        "sdf_outline":        ["techniques/angular/", "techniques/shaping/"],
        "kaleidoscopic":      ["techniques/angular/", "techniques/shaping/"],
        "domain_warped":      ["techniques/noise/"],
        "fractal_zoom":       ["techniques/noise/", "techniques/shaping/"],
        "reflective_capture": ["techniques/reflection/"],
        "flow_field":         ["techniques/flow/"],
    }
    subpaths = geo_subpaths.get(arch_key, ["techniques/radial/", "techniques/angular/"])

    geo_nodes = []
    for sp in subpaths:
        pool = active(ontology, "geometry", sp)
        if pool:
            n_pick = 1 if sp in ("techniques/reflection/", "techniques/flow/") else random.choice([1, 2])
            geo_nodes.extend(pick(pool, n_pick, n_rated))
    selected["geometry"] = geo_nodes

    # ── Colorization layer (exactly 1) ────────────────────────────────────────
    color_pool = active(ontology, "colorization")
    selected["colorization"] = pick(color_pool, 1, n_rated)

    # ── Shaping layer (0-2) ───────────────────────────────────────────────────
    shaping_pool = active(ontology, "shaping")
    selected["shaping"] = pick(shaping_pool, random.choice([0, 1, 1, 2]), n_rated)

    # ── Timing layer (0-1) ────────────────────────────────────────────────────
    timing_pool = active(ontology, "timing")
    selected["timing"] = pick(timing_pool, random.choice([0, 0, 1]), n_rated)

    return selected


# ── Prompt assembly ───────────────────────────────────────────────────────────

SEED_MAP = {
    "convergent":         "convergent_spiral.glsl",
    "linear_rings":       "double_arm.glsl",
    "log_arms":           "galaxy.glsl",
    "sdf_outline":        "sdf_spiral.glsl",
    "kaleidoscopic":      "kaleidoscope.glsl",
    "domain_warped":      "fbm_warp.glsl",
    "fractal_zoom":       "fractal_palette.glsl",
    "reflective_capture": "bean_reflection.glsl",
    "flow_field":         "flow_field.glsl",
}


def build_prompt(selected: dict, revision_prompt: str | None, ontology: dict) -> str:
    arch = selected["archetype"]
    arch_key = arch["id"].split("/")[-1]

    def section(nodes: list[dict], header: str) -> str:
        if not nodes:
            return ""
        lines = [f"\n{header}"]
        for n in nodes:
            pf = n.get("prompt_fragment", n["description"])
            lines.append(f"  [{n['id'].split('/')[-1]}] {pf}")
        return "\n".join(lines)

    # Constraints
    constraints = [n for n in ontology["nodes"] if n["type"] == "constraint" and n.get("active")]
    constraint_lines = [f"  • {n['label']}: {n['description']}" for n in constraints]

    # Quality targets
    quality = [n for n in ontology["nodes"] if n["type"] == "quality" and n.get("active")]
    quality_lines = [f"  • {n['label']}{'  ★ PRIMARY' if 'affect' in n['id'] else ''}: {n['description']}"
                     for n in quality]

    # Seed reference
    seed_src = ""
    seed_file = SEED_MAP.get(arch_key)
    if seed_file:
        seed_path = SEEDS_DIR / seed_file
        if seed_path.exists():
            seed_src = seed_path.read_text()

    prompt = f"""ARCHETYPE: {arch['label']}
{arch['description']}
{section(selected['geometry'],      'LAYER 1 — GEOMETRY (implement the field/structure using these):')}
{section(selected['colorization'],  'LAYER 2 — COLORIZATION (implement this EXACTLY — do not substitute):')}
{section(selected['shaping'],       'LAYER 3 — SHAPING (apply these post-processing modifiers):')}
{section(selected['timing'],        'LAYER 4 — TIMING (apply this animation rhythm technique):')}

HARD CONSTRAINTS:
{chr(10).join(constraint_lines)}

QUALITY TARGETS:
{chr(10).join(quality_lines)}
"""

    # Persistent feedback accumulated from previous human ratings on this archetype
    feedback_history = arch.get("accumulated_feedback", [])
    if feedback_history:
        recent = feedback_history[-5:]  # last 5 notes
        feedback_lines = "\n".join(f"  • {note}" for note in recent)
        prompt += f"""
KNOWN ISSUES FOR THIS ARCHETYPE (recurring human feedback — fix these proactively):
{feedback_lines}
"""

    if seed_src:
        prompt += f"""
REFERENCE IMPLEMENTATION (modify and enhance, do not copy verbatim):
```glsl
{seed_src}
```
"""

    if revision_prompt:
        prompt += f"""
REVISION REQUIRED (address these issues from the previous attempt):
{revision_prompt}
"""

    prompt += "\nWrite the complete GLSL shader now. Output ONLY the GLSL code."
    return prompt


# ── Model call ────────────────────────────────────────────────────────────────

def extract_glsl(text: str) -> str:
    fenced = re.search(r"```(?:glsl)?\s*\n(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
    return "\n".join(lines).strip()


def call_expander(prompt: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=EXPANDER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def save_shader(glsl_src: str, shader_id: str, selected: dict) -> Path:
    SHADERS_DIR.mkdir(parents=True, exist_ok=True)
    path = SHADERS_DIR / f"{shader_id}.glsl"

    all_nodes = (
        [selected["archetype"]]
        + selected.get("geometry", [])
        + selected.get("colorization", [])
        + selected.get("shaping", [])
        + selected.get("timing", [])
    )
    arch_key = selected["archetype"]["id"].split("/")[-1]
    color_key = selected["colorization"][0]["id"].split("/")[-1] if selected.get("colorization") else "none"
    tech_keys = [n["id"].split("/")[-1] for n in selected.get("geometry", [])]

    header = "\n".join([
        f"// shader_id: {shader_id}",
        f"// archetype: {arch_key}",
        f"// colorization: {color_key}",
        f"// techniques: {', '.join(tech_keys)}",
    ]) + "\n"

    path.write_text(header + glsl_src)

    meta = {
        "archetype": arch_key,
        "colorization": color_key,
        "techniques": tech_keys,
        "selected_node_ids": [n["id"] for n in all_nodes],
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate a GLSL shader (Expander/Haiku)")
    parser.add_argument("--archetype", help="Force archetype ID")
    parser.add_argument("--revision-prompt", help="Revision feedback")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--id", help="Override shader ID")
    args = parser.parse_args()

    api_key = get_api_key()
    ontology = load_ontology()

    selected = select_nodes(ontology, args.archetype)
    prompt = build_prompt(selected, args.revision_prompt, ontology)

    if args.dry_run:
        print("=" * 60)
        print(prompt)
        return

    print(f"Expander: {selected['archetype']['label']}  "
          f"color={selected['colorization'][0]['label'] if selected.get('colorization') else 'none'}",
          file=sys.stderr)

    glsl_src = extract_glsl(call_expander(prompt, api_key))
    shader_id = args.id or new_shader_id()
    path = save_shader(glsl_src, shader_id, selected)

    print(shader_id)
    print(f"  → {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
