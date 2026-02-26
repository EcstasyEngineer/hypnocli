#!/usr/bin/env python3
"""
run_v2.py — Main hypothesis-driven pipeline loop
--------------------------------------------------
generate_v2 → validate → rate (browser UI) → learn → repeat.

Usage:
    python3 run_v2.py              # infinite loop
    python3 run_v2.py --n 5        # 5 cycles
    python3 run_v2.py --family 5   # up to 5 compile-fix retries per cycle
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SHADERS_DIR, RENDERS_DIR,
    load_knowledge, save_knowledge,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def validate_shader(shader_id: str) -> tuple[bool, str]:
    """Returns (ok, error_msg)."""
    path = SHADERS_DIR / f"{shader_id}.glsl"
    result = subprocess.run(
        [PYTHON, str(SCRIPTS_DIR / "validate.py"), str(path), "--no-compile", "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        combined = (result.stderr + "\n" + result.stdout).strip()
        error_line = next((l.strip() for l in combined.splitlines() if l.strip()), combined)
        return False, combined
    return True, ""


def run_cycle(family_size: int, server, knowledge: dict) -> tuple[str, str]:
    """
    Run one generate → validate → rate → learn cycle.
    Returns (shader_id, outcome).
    """
    from generate_v2 import generate, parse_response
    from learn import learn as learn_fn

    # Generate
    result = generate(knowledge)
    if not result:
        return "", "fail"

    shader_id, sidecar = result
    print(f"  [generate] {shader_id}")
    print(f"  [hypothesis] {sidecar['hypothesis'][:80]}")

    # Validate (with retries on compile error)
    for attempt in range(family_size + 1):
        ok, error_msg = validate_shader(shader_id)
        if ok:
            print(f"  [validate] OK")
            break

        error_line = next((l.strip() for l in error_msg.splitlines() if l.strip()), error_msg[:100])
        print(f"  [validate] FAIL: {error_line}")

        if attempt >= family_size:
            print(f"  [validate] giving up after {family_size} retries")
            # Learn as rejected with defect
            rating = {
                "shader_id": shader_id,
                "score": 0.0,
                "answers": {},
                "defects": ["black_frame"],
                "note": f"compile/render failure: {error_line[:100]}",
                "discard": True,
            }
            outcome = learn_fn(knowledge, rating)
            return shader_id, outcome

        # Re-generate with error feedback
        print(f"  [retry] attempt {attempt + 1}/{family_size}")
        import anthropic
        from generate_v2 import get_api_key, SYSTEM_PROMPT, new_shader_id
        from _common import SEEDS_DIR

        client = anthropic.Anthropic(api_key=get_api_key())
        shader_path = SHADERS_DIR / f"{shader_id}.glsl"
        old_src = shader_path.read_text() if shader_path.exists() else ""

        fix_prompt = (
            f"The following shader failed validation:\n\n{old_src}\n\n"
            f"ERROR:\n{error_msg[:500]}\n\n"
            f"Fix the shader. Keep the same hypothesis and visual intent. "
            f"Respond with the complete fixed GLSL code only (no HYPOTHESIS_META needed)."
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": fix_prompt}],
        )
        fixed_glsl = response.content[0].text.strip()
        # Strip markdown fences
        import re
        fixed_glsl = re.sub(r"^```(?:glsl)?\s*\n?", "", fixed_glsl)
        fixed_glsl = re.sub(r"\n?```\s*$", "", fixed_glsl)

        # Write fixed version (same shader_id)
        if "uniform vec3 iResolution" not in fixed_glsl:
            fixed_glsl = "uniform vec3 iResolution;\nuniform float iTime;\nuniform vec4 iMouse;\n\n" + fixed_glsl
        if not fixed_glsl.startswith("// shader_id:"):
            fixed_glsl = f"// shader_id: {shader_id}\n" + fixed_glsl
        shader_path.write_text(fixed_glsl)

    # Rate via browser
    shader_path = SHADERS_DIR / f"{shader_id}.glsl"
    server.push_v2(
        shader_id=shader_id,
        shader_src=shader_path.read_text(),
        hypothesis=sidecar["hypothesis"],
        questions=sidecar["questions"],
        defect_types=knowledge.get("defect_types", {}),
    )

    print(f"  [rate] waiting for browser...")
    raw = server.wait_for_rating()

    # Learn
    outcome = learn_fn(knowledge, raw)
    label = f"score={raw.get('score', 0):.2f}" if not raw.get('discard') else "DISCARDED"
    print(f"  [learn] {outcome.upper()}  {label}")

    if outcome == "confirmed":
        print(f"\n  ★ PROMOTED to corpus: {shader_id}")

    return shader_id, outcome


def print_status(knowledge: dict):
    """Quick inline status summary."""
    meta = knowledge["meta"]
    corpus_promoted = sum(1 for c in knowledge["corpus"] if c["type"] == "promoted")
    hypotheses = knowledge["hypotheses"]
    confirmed = sum(1 for h in hypotheses.values() if h["status"] == "confirmed")
    rejected = sum(1 for h in hypotheses.values() if h["status"] == "rejected")
    partial = sum(1 for h in hypotheses.values() if h["status"] == "partial")

    print(f"  ── status: {meta['total_generations']} gen / {meta['total_ratings']} rated"
          f" | {confirmed} confirmed / {rejected} rejected / {partial} partial"
          f" | corpus: {len(knowledge['corpus'])} ({corpus_promoted} promoted)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=0, help="Number of cycles (0 = infinite)")
    parser.add_argument("--family", type=int, default=3, help="Max compile-fix retries per cycle")
    args = parser.parse_args()

    knowledge = load_knowledge()

    print(f"{'=' * 60}")
    print(f"  GLSL Pipeline v2 — hypothesis-driven, browser rated")
    print(f"  Cycles: {'∞' if args.n == 0 else args.n}  |  Retries/cycle: {args.family}")
    print(f"  Corpus: {len(knowledge['corpus'])} entries  |  Patterns: {len(knowledge['patterns'])}")
    print(f"{'=' * 60}\n")

    from rater_server import RaterServer
    server = RaterServer(v2=True)
    server.start()

    stats: dict[str, int] = {}
    iteration = 0
    start = time.time()

    try:
        while True:
            iteration += 1
            if args.n > 0 and iteration > args.n:
                break

            print(f"\n[Cycle {iteration}{'/' + str(args.n) if args.n else ''}]")

            # Reload knowledge each cycle (learn.py saves after each rating)
            knowledge = load_knowledge()
            shader_id, outcome = run_cycle(args.family, server, knowledge)
            stats[outcome] = stats.get(outcome, 0) + 1

            if iteration % 10 == 0:
                knowledge = load_knowledge()
                print()
                print_status(knowledge)

    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    finally:
        server.stop()

    elapsed = time.time() - start
    knowledge = load_knowledge()
    print(f"\n{'=' * 60}")
    print(f"  Done — {iteration - 1} cycles in {elapsed:.0f}s")
    for k, v in sorted(stats.items()):
        print(f"    {k}: {v}")
    print_status(knowledge)
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
