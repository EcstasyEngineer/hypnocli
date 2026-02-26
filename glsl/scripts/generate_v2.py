#!/usr/bin/env python3
"""
generate_v2.py — Hypothesis-driven Sonnet shader generator
------------------------------------------------------------
Single Sonnet call: reads knowledge graph, samples corpus for inspiration,
proposes a hypothesis to test, writes GLSL code + yes/no questions.

Output: shader .glsl + .json sidecar with hypothesis metadata.

Usage:
    python3 generate_v2.py                 # generate one shader
    python3 generate_v2.py --dry-run       # print prompt, don't call API
    python3 generate_v2.py --hypothesis "Does X work with Y?"
"""

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SEEDS_DIR, SHADERS_DIR,
    get_api_key, load_knowledge, save_knowledge,
    next_hypothesis_id, new_shader_id,
)

ATAN_GUIDANCE = (SEEDS_DIR / "ATAN_GUIDANCE.md").read_text()


# ── Knowledge summary for prompt ─────────────────────────────────────────────

def summarize_knowledge(knowledge: dict) -> str:
    """Build a concise summary of the knowledge graph for the Sonnet prompt."""
    lines = []

    # Confirmed patterns with evidence
    patterns = knowledge["patterns"]
    confirmed = []
    for slug, p in sorted(patterns.items()):
        confirms = sum(1 for e in p["evidence"] if e["result"] == "confirmed")
        rejects = sum(1 for e in p["evidence"] if e["result"] == "rejected")
        if confirms > 0 or rejects > 0:
            confirmed.append((slug, confirms, rejects, p["works_with"], p["fails_with"]))

    if confirmed:
        lines.append("PATTERNS WITH EVIDENCE:")
        for slug, c, r, ww, fw in confirmed:
            status = f"+{c}" if c else ""
            if r:
                status += f" -{r}"
            ww_str = f" works_with=[{', '.join(ww[:5])}]" if ww else ""
            fw_str = f" FAILS_WITH=[{', '.join(fw[:5])}]" if fw else ""
            lines.append(f"  {slug} ({status}){ww_str}{fw_str}")
    else:
        lines.append("PATTERNS: No hypothesis evidence yet. All patterns are from seed annotations.")

    # Works_with edges from seeds (even without hypothesis evidence)
    seed_edges = set()
    for slug, p in patterns.items():
        for partner in p["works_with"]:
            edge = tuple(sorted([slug, partner]))
            seed_edges.add(edge)
    if seed_edges:
        lines.append(f"\nKNOWN COMPATIBLE PAIRS: {len(seed_edges)} (from seed co-occurrence)")

    # Fails_with edges
    fail_edges = set()
    for slug, p in patterns.items():
        for partner in p["fails_with"]:
            edge = tuple(sorted([slug, partner]))
            fail_edges.add(edge)
    if fail_edges:
        lines.append(f"\nKNOWN INCOMPATIBLE PAIRS:")
        for a, b in sorted(fail_edges):
            lines.append(f"  {a} + {b}")

    # Untested patterns (no evidence at all)
    untested = [s for s, p in patterns.items() if not p["evidence"]]
    if untested:
        lines.append(f"\nUNTESTED PATTERNS ({len(untested)}): {', '.join(sorted(untested)[:15])}")
        if len(untested) > 15:
            lines.append(f"  ... and {len(untested) - 15} more")

    # Open questions
    all_questions = []
    for slug, p in patterns.items():
        for q in p.get("open_questions", []):
            all_questions.append(f"  [{slug}] {q}")
    if all_questions:
        lines.append(f"\nOPEN QUESTIONS:")
        for q in all_questions[:10]:
            lines.append(q)

    # Recent hypotheses
    hypotheses = knowledge.get("hypotheses", {})
    recent = sorted(hypotheses.values(), key=lambda h: h.get("created", ""), reverse=True)[:5]
    if recent:
        lines.append(f"\nRECENT HYPOTHESES:")
        for h in recent:
            status = h.get("status", "untested")
            score = h.get("score")
            score_str = f" score={score:.2f}" if score is not None else ""
            lines.append(f"  [{status}{score_str}] {h['statement'][:80]}")

    # Defects to avoid
    defects = knowledge.get("defect_types", {})
    active_defects = [(k, v) for k, v in defects.items() if v.get("occurrences", 0) > 0]
    if active_defects:
        lines.append(f"\nDEFECTS TO AVOID:")
        for k, v in active_defects:
            lines.append(f"  {k} ({v['occurrences']}x): {v['mitigation']}")

    return "\n".join(lines)


# ── Corpus sampling ──────────────────────────────────────────────────────────

def sample_corpus(knowledge: dict, n: int = 3) -> list[dict]:
    """Sample 2-3 corpus shaders: always 1 seed, optionally 1 promoted, 1 random."""
    corpus = knowledge["corpus"]
    seeds = [c for c in corpus if c["type"] == "seed"]
    promoted = [c for c in corpus if c["type"] == "promoted"]

    selected = []

    # Always include 1 seed
    if seeds:
        selected.append(random.choice(seeds))

    # Include 1 promoted if available
    if promoted:
        selected.append(random.choice(promoted))

    # Fill remaining with random (avoiding duplicates)
    remaining = [c for c in corpus if c not in selected]
    while len(selected) < n and remaining:
        pick = random.choice(remaining)
        remaining.remove(pick)
        selected.append(pick)

    return selected


def load_shader_source(corpus_entry: dict) -> str:
    """Load shader source for a corpus entry."""
    path = GLSL_DIR / corpus_entry["path"]
    if path.exists():
        return path.read_text()
    return f"(source not found: {corpus_entry['path']})"


# ── Prompt construction ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert GLSL shader author specializing in hypnotic and trance-inducing visual art.

You work in a hypothesis-driven evolution system. Each shader you write tests a specific
hypothesis about what visual patterns and combinations produce the strongest hypnotic effect.

HARD REQUIREMENTS:
- Entry point: void mainImage(out vec4 fragColor, in vec2 fragCoord)
- Declare uniforms: uniform vec3 iResolution; uniform float iTime; uniform vec4 iMouse;
- No iChannel* texture samples
- Loop bounds must be compile-time constants, <= 64 iterations
- Must compile under GLSL ES 3.00

HYPNOSIS PRINCIPLES:
- Motion should be continuous and never fully resolve
- At least one convergent motion vector pulling attention toward center
- Depth illusion: make the image feel 3D or infinitely deep
- Avoid hard cuts or sudden changes
- Decoupled speeds across layers prevent temporal adaptation

RESPONSE FORMAT:
You must respond with EXACTLY two sections, in this order:

HYPOTHESIS_META:
{
  "hypothesis": "A clear testable statement about what this shader tests",
  "patterns": ["pattern_slug_1", "pattern_slug_2", ...],
  "questions": ["Does it feel deep?", "Is gaze pulled to center?", "Does the motion resolve?"],
  "motivation": "One sentence: why this combination might work"
}

GLSL_CODE:
(your complete GLSL shader here, no markdown fences)
"""


def build_user_prompt(knowledge: dict, inspiration: list[dict],
                      forced_hypothesis: str | None = None) -> str:
    """Build the user message for Sonnet."""
    parts = []

    # Knowledge summary
    parts.append("=== KNOWLEDGE GRAPH STATE ===")
    parts.append(summarize_knowledge(knowledge))

    # Atan guidance
    parts.append("\n=== ATAN BRANCH CUT GUIDANCE ===")
    parts.append(ATAN_GUIDANCE)

    # Inspiration shaders
    parts.append("\n=== INSPIRATION CORPUS ===")
    for entry in inspiration:
        src = load_shader_source(entry)
        parts.append(f"\n--- {entry['id']} ---")
        parts.append(f"Motivation: {entry.get('motivation', '(none)')}")
        parts.append(f"Patterns: {', '.join(entry.get('patterns', []))}")
        if entry.get("score") is not None:
            parts.append(f"Score: {entry['score']:.2f}")
        parts.append(f"Source:\n{src}")

    # Task
    parts.append("\n=== YOUR TASK ===")
    if forced_hypothesis:
        parts.append(f"Test this specific hypothesis: {forced_hypothesis}")
        parts.append("Write a shader that tests it, and provide the HYPOTHESIS_META and GLSL_CODE.")
    else:
        parts.append("Based on the knowledge graph gaps and inspiration above, choose a hypothesis "
                      "to test. Prioritize:")
        parts.append("1. Untested patterns that appear promising")
        parts.append("2. New combinations of patterns that haven't been tried together")
        parts.append("3. Variations on high-scoring confirmed patterns")
        parts.append("4. Avoid combinations that are in FAILS_WITH")
        parts.append("\nWrite a shader that tests your hypothesis. Respond with HYPOTHESIS_META then GLSL_CODE.")

    return "\n".join(parts)


# ── Response parsing ─────────────────────────────────────────────────────────

def parse_response(text: str) -> tuple[dict, str]:
    """Parse Sonnet's response into (hypothesis_meta, glsl_code)."""
    # Find HYPOTHESIS_META JSON
    meta_match = re.search(r"HYPOTHESIS_META:\s*\n?\s*(\{.*?\})", text, re.DOTALL)
    if not meta_match:
        raise ValueError("No HYPOTHESIS_META section found in response")

    meta_str = meta_match.group(1)
    # Fix common JSON issues: trailing commas
    meta_str = re.sub(r",\s*}", "}", meta_str)
    meta_str = re.sub(r",\s*]", "]", meta_str)
    meta = json.loads(meta_str)

    # Find GLSL_CODE
    glsl_match = re.search(r"GLSL_CODE:\s*\n(.*)", text, re.DOTALL)
    if not glsl_match:
        raise ValueError("No GLSL_CODE section found in response")

    glsl = glsl_match.group(1).strip()
    # Strip markdown fences if present
    glsl = re.sub(r"^```(?:glsl)?\s*\n?", "", glsl)
    glsl = re.sub(r"\n?```\s*$", "", glsl)

    return meta, glsl


# ── Main ─────────────────────────────────────────────────────────────────────

def generate(knowledge: dict, dry_run: bool = False,
             forced_hypothesis: str | None = None) -> tuple[str, dict] | None:
    """
    Generate one shader. Returns (shader_id, sidecar_dict) or None on failure.
    Mutates knowledge (increments next_hypothesis_id, total_generations).
    """
    inspiration = sample_corpus(knowledge)
    user_prompt = build_user_prompt(knowledge, inspiration, forced_hypothesis)

    if dry_run:
        print("=== SYSTEM PROMPT ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER PROMPT ===")
        print(user_prompt)
        print(f"\n(dry run — {len(user_prompt)} chars, would call claude-sonnet-4-6)")
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=get_api_key())

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text
    meta, glsl = parse_response(text)

    # Generate IDs
    shader_id = new_shader_id()
    h_id = next_hypothesis_id(knowledge)
    now = datetime.now(timezone.utc).isoformat()

    # Ensure uniforms are declared
    if "uniform vec3 iResolution" not in glsl:
        glsl = "uniform vec3 iResolution;\nuniform float iTime;\nuniform vec4 iMouse;\n\n" + glsl

    # Add shader_id header
    header = f"// shader_id: {shader_id}\n"
    glsl = header + glsl

    # Write shader file
    SHADERS_DIR.mkdir(parents=True, exist_ok=True)
    shader_path = SHADERS_DIR / f"{shader_id}.glsl"
    shader_path.write_text(glsl)

    # Build sidecar
    sidecar = {
        "shader_id": shader_id,
        "hypothesis_id": h_id,
        "hypothesis": meta.get("hypothesis", ""),
        "patterns": meta.get("patterns", []),
        "questions": meta.get("questions", []),
        "motivation": meta.get("motivation", ""),
        "inspiration_corpus_ids": [e["id"] for e in inspiration],
        "created": now,
    }

    # Write sidecar
    meta_path = SHADERS_DIR / f"{shader_id}.json"
    meta_path.write_text(json.dumps(sidecar, indent=2) + "\n")

    # Register hypothesis in knowledge graph
    knowledge["hypotheses"][h_id] = {
        "statement": meta.get("hypothesis", ""),
        "status": "untested",
        "patterns_involved": meta.get("patterns", []),
        "shader_id": shader_id,
        "score": None,
        "answers": None,
        "questions": meta.get("questions", []),
        "defects": [],
        "note": "",
        "created": now,
    }
    knowledge["meta"]["total_generations"] += 1
    save_knowledge(knowledge)

    print(f"{shader_id}")
    return shader_id, sidecar


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without calling API")
    parser.add_argument("--hypothesis", type=str, help="Force a specific hypothesis to test")
    args = parser.parse_args()

    knowledge = load_knowledge()
    result = generate(knowledge, dry_run=args.dry_run, forced_hypothesis=args.hypothesis)

    if result:
        shader_id, sidecar = result
        print(f"  hypothesis: {sidecar['hypothesis'][:80]}", file=sys.stderr)
        print(f"  patterns: {', '.join(sidecar['patterns'])}", file=sys.stderr)
        print(f"  questions: {len(sidecar['questions'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
