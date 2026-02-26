#!/usr/bin/env python3
"""
bootstrap_v2.py — Initialize knowledge.json from curated seeds
---------------------------------------------------------------
Parses seed headers for core motivation, maps seeds → pattern slugs,
pre-seeds works_with edges from co-occurrence, creates defect_types.

Usage:
    python3 glsl/scripts/bootstrap_v2.py
    python3 glsl/scripts/bootstrap_v2.py --force   # overwrite existing knowledge.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SEEDS_DIR, KNOWLEDGE_PATH,
    save_knowledge,
)

# ── Seed → pattern mapping ───────────────────────────────────────────────────
# Derived from reading each seed's techniques + core motivation annotations.

SEED_PATTERNS = {
    "convergent_spiral": {
        "patterns": [
            "chebyshev_angular", "radial_inversion", "decoupled_speeds",
            "log_shear", "iq_cosine_palette", "center_convergence",
        ],
        "motivation": "Inescapable pull toward center via radial inversion and "
                      "logarithmic spiral arms with decoupled speeds.",
    },
    "double_arm": {
        "patterns": [
            "inversion_linear", "arm_count", "abs_fold", "decoupled_speeds",
            "chromatic_drift", "beat_interference",
        ],
        "motivation": "Beating interference pattern via counter-rotating arm sets "
                      "producing moire; color channels on offset clocks.",
    },
    "flow_field": {
        "patterns": [
            "flow_sources_sinks", "pole_drift", "ring_expansion",
            "decoupled_speeds",
        ],
        "motivation": "Fluid field with sources and sinks; rings expand and "
                      "contract with slow drifting poles.",
    },
    "fract_zoom": {
        "patterns": [
            "fract_recursion", "self_similar_nesting", "center_convergence",
            "brightness_inward_pull",
        ],
        "motivation": "fract() recursion for infinite self-similar nesting; "
                      "brightness pulls inward for convergent attention.",
    },
    "galaxy": {
        "patterns": [
            "chebyshev_angular", "log_spiral_arms", "iq_cosine_palette",
            "warm_core_gradient", "depth_from_motion",
        ],
        "motivation": "Natural galaxy morphology exploiting depth-from-motion "
                      "circuits; three log-spiral arms with warm-core palette.",
    },
    "kaleidoscope": {
        "patterns": [
            "mirror_fold", "sector_symmetry", "decoupled_speeds",
            "vortex_pull", "radial_rings",
        ],
        "motivation": "N-fold mirror symmetry eliminates asymmetric distractors; "
                      "slow rotation at decoupled speeds creates vortex pull.",
    },
    "sdf_spiral": {
        "patterns": [
            "sdf_analytic", "counter_rotation", "glow_isoline",
            "pulse_rhythm", "spiral_offset",
        ],
        "motivation": "Counter-rotating spiral SDFs create glowing isoline "
                      "intersections that pulse rhythmically.",
    },
    "flow_field": {
        "patterns": [
            "flow_sources_sinks", "pole_drift", "ring_expansion",
            "decoupled_speeds",
        ],
        "motivation": "Fluid field with sources/sinks; expanding/contracting "
                      "rings with drifting poles prevent adaptation.",
    },
}

# ── Pattern descriptions ─────────────────────────────────────────────────────

PATTERN_DESCRIPTIONS = {
    "chebyshev_angular": "Seam-free angular arms via Chebyshev polynomials on unit direction (avoids atan).",
    "radial_inversion": "1/r or exp(-r) transforms that compress far regions and expand center.",
    "decoupled_speeds": "Independent time multipliers per channel/layer preventing temporal adaptation.",
    "log_shear": "log(r) coordinate for scale-invariant self-similar depth illusion.",
    "iq_cosine_palette": "Inigo Quilez cosine palette: a + b*cos(2pi*(c*t+d)) for smooth perceptual color.",
    "center_convergence": "Exponential or smoothstep falloff pulling visual attention to center.",
    "inversion_linear": "Counter-rotating arms with negated phase creating beat/moire interference.",
    "arm_count": "Integer arm multiplier in angular coordinate for N-fold spiral structure.",
    "abs_fold": "abs() folding of interference pattern into symmetric positive ripple.",
    "chromatic_drift": "Per-channel time offsets so RGB never align, preventing color adaptation.",
    "beat_interference": "Product of two sinusoids at different frequencies creating visible beating.",
    "flow_sources_sinks": "Point sources/sinks in 2D field creating expansion/contraction regions.",
    "pole_drift": "Slowly moving singularity positions to prevent pattern habituation.",
    "ring_expansion": "Concentric rings moving outward (or inward) from center.",
    "fract_recursion": "fract() applied to scaled coordinates for infinite self-similar zoom.",
    "self_similar_nesting": "Pattern contains smaller copies of itself at multiple scales.",
    "brightness_inward_pull": "Brightness gradient increasing toward center to draw gaze.",
    "log_spiral_arms": "Logarithmic spiral arms: theta + log(r)*tightness for self-similar winding.",
    "warm_core_gradient": "Color temperature gradient: warm center, cool edges for depth.",
    "depth_from_motion": "Speed differential by radius exploiting motion parallax depth cues.",
    "mirror_fold": "mod(theta, sector) + conditional reflection for kaleidoscopic symmetry.",
    "sector_symmetry": "N-fold angular division creating identical repeating sectors.",
    "vortex_pull": "Rotation speed gradient (faster inner, slower outer) creating suction illusion.",
    "radial_rings": "Concentric ring pattern via fract(r*N) or sin(r*N).",
    "sdf_analytic": "Signed distance field from analytic formula (not raymarching).",
    "counter_rotation": "Two pattern layers rotating in opposite directions.",
    "glow_isoline": "exp(-d*k) glow falloff around SDF isolines for neon effect.",
    "pulse_rhythm": "Periodic intensity modulation at sub-Hz rate for entrainment.",
    "spiral_offset": "Adding log(r)*tightness to angular coordinate for spiral winding.",
}

# ── Defect types ─────────────────────────────────────────────────────────────

DEFECT_TYPES = {
    "stitch_line": {
        "label": "Stitch line",
        "description": "Visible seam/discontinuity, usually from atan branch cut.",
        "occurrences": 0,
        "mitigation": "See ATAN_GUIDANCE.md — use integer N in sin(N*theta) or Chebyshev.",
    },
    "black_frame": {
        "label": "Black frame",
        "description": "Shader renders entirely or mostly black.",
        "occurrences": 0,
        "mitigation": "Check division by zero, missing uniforms, or inf/NaN propagation.",
    },
    "aliasing": {
        "label": "Aliasing",
        "description": "Visible jagged edges or moire from undersampled high-frequency pattern.",
        "occurrences": 0,
        "mitigation": "Reduce pattern frequency near edges, add smoothstep anti-aliasing.",
    },
    "gpu_timeout": {
        "label": "GPU timeout",
        "description": "Shader too expensive, causes browser hang or low FPS.",
        "occurrences": 0,
        "mitigation": "Reduce loop iterations, simplify inner loop math.",
    },
}


def build_works_with(seed_patterns: dict) -> dict[str, set]:
    """Pre-seed works_with edges from patterns co-occurring in the same seed."""
    edges: dict[str, set] = {}
    for seed_name, info in seed_patterns.items():
        slugs = info["patterns"]
        for i, a in enumerate(slugs):
            for b in slugs[i + 1:]:
                edges.setdefault(a, set()).add(b)
                edges.setdefault(b, set()).add(a)
    return edges


def parse_seed_header(path: Path) -> dict:
    """Parse a seed's header comments for archetype, techniques, motivation."""
    lines = path.read_text().splitlines()
    info = {"archetype": "", "techniques": [], "motivation": ""}
    for line in lines:
        line = line.strip()
        if not line.startswith("//"):
            break
        text = line.lstrip("/").strip()
        if text.lower().startswith("archetype:"):
            info["archetype"] = text.split(":", 1)[1].strip()
        elif text.lower().startswith("techniques:"):
            info["techniques"] = [t.strip() for t in text.split(":", 1)[1].split(",")]
        elif text.lower().startswith("colorization:"):
            info["techniques"].append(text.split(":", 1)[1].strip())
        elif text.lower().startswith("core motivation:"):
            info["motivation"] = text.split(":", 1)[1].strip()
    return info


def build_corpus(seed_patterns: dict) -> list[dict]:
    """Build corpus entries from all seeds — explicit mappings + auto-discovered."""
    corpus = []
    seen = set()

    # Explicit mappings first
    for seed_name, info in seed_patterns.items():
        path = SEEDS_DIR / f"{seed_name}.glsl"
        if not path.exists():
            print(f"  WARN: seed {seed_name}.glsl not found, skipping")
            continue
        corpus.append({
            "id": f"seed:{seed_name}",
            "path": f"seeds/{seed_name}.glsl",
            "type": "seed",
            "motivation": info["motivation"],
            "patterns": info["patterns"],
            "score": None,
        })
        seen.add(seed_name)

    # Auto-discover remaining seeds
    for path in sorted(SEEDS_DIR.glob("*.glsl")):
        seed_name = path.stem
        if seed_name in seen:
            continue
        header = parse_seed_header(path)
        patterns = header["techniques"] if header["techniques"] else [header["archetype"]]
        corpus.append({
            "id": f"seed:{seed_name}",
            "path": f"seeds/{seed_name}.glsl",
            "type": "seed",
            "motivation": header["motivation"],
            "patterns": patterns,
            "score": None,
        })
        seen.add(seed_name)

    return corpus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing knowledge.json")
    args = parser.parse_args()

    if KNOWLEDGE_PATH.exists() and not args.force:
        print(f"knowledge.json already exists. Use --force to overwrite.")
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build corpus (includes auto-discovered seeds)
    corpus = build_corpus(SEED_PATTERNS)

    # Build combined seed_patterns for works_with edges (explicit + discovered)
    all_seed_info = dict(SEED_PATTERNS)
    for entry in corpus:
        seed_name = entry["id"].replace("seed:", "")
        if seed_name not in all_seed_info:
            all_seed_info[seed_name] = {"patterns": entry["patterns"], "motivation": entry["motivation"]}

    # Build works_with edges from all seeds
    works_with = build_works_with(all_seed_info)

    # Build patterns dict
    patterns = {}
    all_slugs = set()
    for info in all_seed_info.values():
        all_slugs.update(info["patterns"])

    for slug in sorted(all_slugs):
        desc = PATTERN_DESCRIPTIONS.get(slug, "")
        ww = sorted(works_with.get(slug, set()))
        patterns[slug] = {
            "label": slug.replace("_", " ").title(),
            "description": desc,
            "evidence": [],
            "works_with": ww,
            "fails_with": [],
            "open_questions": [],
            "source": "seed_annotation",
            "first_seen": now,
        }

    # Assemble knowledge.json
    knowledge = {
        "version": "2.0",
        "patterns": patterns,
        "hypotheses": {},
        "corpus": corpus,
        "defect_types": DEFECT_TYPES,
        "meta": {
            "total_generations": 0,
            "total_ratings": 0,
            "next_hypothesis_id": 1,
        },
    }

    save_knowledge(knowledge)
    print(f"Created knowledge.json:")
    print(f"  {len(patterns)} patterns")
    print(f"  {sum(len(p['works_with']) for p in patterns.values()) // 2} works_with edges")
    print(f"  {len(corpus)} corpus entries (seeds)")
    print(f"  {len(DEFECT_TYPES)} defect types")



if __name__ == "__main__":
    main()
