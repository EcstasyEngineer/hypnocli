#!/usr/bin/env python3
"""
run.py — Main adversarial pipeline loop
-----------------------------------------
Generate → validate → browser rating UI → score → repeat.

Each shader opens in your browser at localhost. Rate with 1-10 buttons
or type a note. The page closes itself once you submit.

Flags:
  --n N           Number of cycles (default: infinite)
  --archetype ID  Force specific archetype
  --family N      Max revision attempts per cycle (default: 3)
  --auto          Use Sonnet instead of human rating (testing only)

Usage:
    python3 run.py
    python3 run.py --n 10
    python3 run.py --archetype flow_field
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GLSL_DIR, SHADERS_DIR, RENDERS_DIR, load_ontology

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

QUALITY_DIMS = [
    ("depth_illusion",      "Depth illusion"),
    ("attentional_capture", "Attentional capture"),
    ("motion_clarity",      "Motion clarity"),
    ("loop_seamlessness",   "Loop seamlessness"),
    ("affect_induction",    "Affect induction"),
]


# ── Rating conversion ─────────────────────────────────────────────────────────

def raw_to_critique(raw: dict) -> dict:
    """Convert browser rating {score, note, discard} → critique dict."""
    if raw.get("discard"):
        affect = 0.1
        tier = "discard"
    else:
        affect = max(0.0, min(10.0, float(raw.get("score", 5)))) / 10.0
        tier = "promote" if affect >= 0.7 else "discard" if affect < 0.3 else "revise"

    note = raw.get("note", "").strip()
    scores = {d: round(min(1.0, affect + 0.05), 3) for d, _ in QUALITY_DIMS}
    scores["affect_induction"] = affect

    label = f"affect={affect:.1f}"
    if note:
        label += f'  "{note[:60]}"'
    print(f"  → {tier.upper()}  {label}")

    return {
        "tier": tier,
        "quality_scores": scores,
        "critique": f"(human: {label})",
        "revision_prompt": note,
        "proposed_quality_dimensions": [],
    }


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def run_script(name: str, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run([PYTHON, str(SCRIPTS_DIR / name)] + args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def generate_shader(archetype: str | None, revision_prompt: str | None) -> str | None:
    args = []
    if archetype:
        args += ["--archetype", archetype]
    if revision_prompt:
        args += ["--revision-prompt", revision_prompt]
    rc, stdout, stderr = run_script("generate.py", args)
    if rc != 0:
        print(f"  [generate] FAILED: {stderr[:200]}")
        return None
    shader_id = stdout.split("\n")[0].strip()
    print(f"  [generate] {shader_id}")
    return shader_id


def validate_shader(shader_id: str) -> tuple[bool, str]:
    """Returns (ok, error_msg). error_msg is non-empty on failure."""
    path = SHADERS_DIR / f"{shader_id}.glsl"
    rc, stdout, stderr = run_script("validate.py", [str(path), "--no-compile", "--quiet"])
    if rc != 0:
        combined = (stderr + "\n" + stdout).strip()
        # Extract the most useful error line
        error_line = next((l.strip() for l in combined.splitlines() if l.strip()), combined)
        print(f"  [validate] {error_line}")
        return False, combined
    print(f"  [validate] OK")
    return True, ""


def score_shader(shader_id: str, critique: dict, boost: bool = False):
    critique_path = RENDERS_DIR / f"{shader_id}_critique.json"
    critique["shader_id"] = shader_id
    critique_path.write_text(json.dumps(critique, indent=2))
    args = [shader_id] + (["--boost"] if boost else [])
    rc, _, stderr = run_script("score.py", args)
    if rc != 0:
        print(f"  [score] FAILED: {stderr[:100]}")
    else:
        print(f"  [score] OK")


def get_archetype_from_meta(shader_id: str, fallback: str | None) -> str | None:
    meta_path = SHADERS_DIR / f"{shader_id}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text()).get("archetype", fallback)
    return fallback


def sonnet_critique(shader_id: str) -> dict | None:
    rc, stdout, _ = run_script("critique.py", ["--id", shader_id])
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def print_status():
    subprocess.run([PYTHON, str(SCRIPTS_DIR / "status.py")])


# ── Main cycle ────────────────────────────────────────────────────────────────

def run_cycle(archetype: str | None, family_size: int, auto: bool, server=None) -> tuple[str, str]:
    revision_prompt = None
    last_id = ""
    last_tier = "discard"

    for attempt in range(family_size + 1):
        if attempt > 0:
            print(f"\n  → Revision {attempt}/{family_size}")

        shader_id = generate_shader(archetype, revision_prompt)
        if not shader_id:
            return "", "fail"
        last_id = shader_id

        ok, error_msg = validate_shader(shader_id)
        if not ok:
            last_tier = "discard"
            if attempt < family_size:
                # Feed the compile/render error back to Haiku
                prefix = f"GLSL ERROR (fix this first): {error_msg[:300]}"
                revision_prompt = f"{prefix}\n{revision_prompt}".strip() if revision_prompt else prefix
            continue

        shader_path = SHADERS_DIR / f"{shader_id}.glsl"
        arch = get_archetype_from_meta(shader_id, archetype)

        if auto:
            print(f"  [auto] calling Sonnet...")
            critique = sonnet_critique(shader_id) or {
                "tier": "discard",
                "quality_scores": {d: 0.3 for d, _ in QUALITY_DIMS},
                "critique": "(auto: failed)", "revision_prompt": "", "proposed_quality_dimensions": [],
            }
        else:
            server.push(shader_id, shader_path.read_text())
            raw = server.wait_for_rating()
            critique = raw_to_critique(raw)

        tier = critique.get("tier", "discard")
        last_tier = tier
        score_shader(shader_id, critique, boost=(tier == "promote"))

        if tier == "promote":
            print(f"\n  ★ PROMOTED: {shader_id}")
            return shader_id, "promote"

        if tier == "discard":
            if attempt < family_size:
                revision_prompt = critique.get("revision_prompt", "")
                continue
            return shader_id, "discard"

        if tier == "revise":
            revision_prompt = critique.get("revision_prompt", "")
            if revision_prompt:
                print(f"  ↻ {revision_prompt[:80]}")
            if attempt >= family_size:
                return shader_id, "revise"
            continue

    return last_id, last_tier


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=0)
    parser.add_argument("--archetype")
    parser.add_argument("--family", type=int, default=3)
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  GLSL Pipeline — {'AUTO' if args.auto else 'human rated, browser UI'}")
    print(f"  Cycles: {'∞' if args.n == 0 else args.n}  |  Revisions/cycle: {args.family}")
    if args.archetype:
        print(f"  Archetype: {args.archetype}")
    print(f"{'='*60}\n")

    server = None
    if not args.auto:
        from rater_server import RaterServer
        server = RaterServer()
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
            shader_id, tier = run_cycle(args.archetype, args.family, args.auto, server)
            stats[tier] = stats.get(tier, 0) + 1

            if iteration % 10 == 0:
                print()
                print_status()

            ratings_path = GLSL_DIR / "ratings.jsonl"
            if ratings_path.exists():
                n = sum(1 for l in ratings_path.read_text().splitlines() if l.strip())
                if n > 0 and n % 50 == 0:
                    print(f"\n  {n} ratings — consider: python3 glsl/scripts/reconcile.py")

    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    finally:
        if server:
            server.stop()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  Done — {iteration-1} cycles in {elapsed:.0f}s")
    for k, v in sorted(stats.items()):
        print(f"    {k}: {v}")
    print(f"{'='*60}")
    print_status()


if __name__ == "__main__":
    main()
