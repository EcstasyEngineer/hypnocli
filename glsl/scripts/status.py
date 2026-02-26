#!/usr/bin/env python3
"""
status.py
---------
Terminal status dashboard for the GLSL shader pipeline.

Reads glsl/ontology.json and glsl/ratings.jsonl, prints:
- Archetype scores with confidence bars
- Top/bottom 5 techniques per category
- Quality dimension averages (last 10 renders)
- Flagged nodes
- Overall pipeline stats
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

GLSL_DIR = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = GLSL_DIR / "ontology.json"
RATINGS_PATH = GLSL_DIR / "ratings.jsonl"
SHADERS_DIR = GLSL_DIR / "shaders"
RENDERS_DIR = GLSL_DIR / "renders"


def bar(score, width=10):
    """Render a score [0,1] as a filled bar."""
    filled = int(round(score * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def conf_tag(confidence):
    if confidence == 0:
        return "(no data)"
    if confidence < 5:
        return f"(n={confidence}, low)"
    return f"(n={confidence})"


def load_ontology():
    if not ONTOLOGY_PATH.exists():
        print(f"ERROR: ontology.json not found at {ONTOLOGY_PATH}")
        print("Run: python3 glsl/scripts/init_ontology.py")
        sys.exit(1)
    return json.loads(ONTOLOGY_PATH.read_text())


def load_ratings():
    if not RATINGS_PATH.exists():
        return []
    ratings = []
    for line in RATINGS_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            ratings.append(json.loads(line))
    return ratings


def nodes_by_type(ontology, type_):
    return [n for n in ontology["nodes"] if n["type"] == type_ and not n.get("retired")]


def nodes_by_parent_prefix(ontology, prefix):
    return [n for n in ontology["nodes"] if n["id"].startswith(prefix) and not n.get("retired")]


def print_header(text):
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text):
    print()
    print(f"── {text} " + "─" * max(0, 50 - len(text)))


def main():
    ontology = load_ontology()
    ratings = load_ratings()

    # Index nodes by id
    node_map = {n["id"]: n for n in ontology["nodes"]}

    print_header("GLSL Adversarial Pipeline — Status")

    # ── Pipeline stats ────────────────────────────────────────────────────
    shaders_generated = len(list(SHADERS_DIR.glob("*.glsl"))) if SHADERS_DIR.exists() else 0
    renders_generated = len(list(RENDERS_DIR.glob("*.png"))) if RENDERS_DIR.exists() else 0
    total_ratings = len(ratings)

    tiers = defaultdict(int)
    for r in ratings:
        tiers[r.get("tier", "unknown")] += 1

    print(f"\n  Shaders generated : {shaders_generated}")
    print(f"  Renders produced  : {renders_generated}")
    print(f"  Total ratings     : {total_ratings}")
    if tiers:
        for tier, count in sorted(tiers.items()):
            print(f"    {tier:12s}: {count}")

    # Flagged nodes
    flagged = [n for n in ontology["nodes"] if n.get("flag_for_review") and not n.get("retired")]
    print(f"\n  Flagged nodes     : {len(flagged)}")
    if flagged:
        for n in flagged[:5]:
            print(f"    [{n['id']}] {n['label']}")

    # ── Archetypes ────────────────────────────────────────────────────────
    print_section("ARCHETYPES")
    archetypes = nodes_by_type(ontology, "archetype")
    archetypes.sort(key=lambda n: -n["score"])
    for n in archetypes:
        score_str = f"{n['score']:.3f}" if n["confidence"] > 0 else "  ---"
        print(f"  {bar(n['score'])}  {score_str}  {conf_tag(n['confidence'])}  {n['label']}")

    # ── Techniques by category ────────────────────────────────────────────
    categories = ["radial", "angular", "noise", "flow", "reflection",
                  "colorization", "shaping", "timing"]
    for cat in categories:
        prefix = f"techniques/{cat}/"
        techs = nodes_by_parent_prefix(ontology, prefix)
        if not techs:
            continue
        rated = [t for t in techs if t["confidence"] > 0]
        unrated = [t for t in techs if t["confidence"] == 0]
        rated.sort(key=lambda n: -n["score"])

        print_section(f"techniques/{cat}")
        top = rated[:3]
        bottom = rated[-2:] if len(rated) > 3 else []
        shown = top + (["..."] if bottom else []) + bottom
        for item in shown:
            if item == "...":
                print(f"  {'':>12}  ...")
                continue
            score_str = f"{item['score']:.3f}"
            print(f"  {bar(item['score'])}  {score_str}  {conf_tag(item['confidence'])}  {item['label']}")
        if unrated:
            print(f"  (unrated: {', '.join(t['label'] for t in unrated[:4])}{'...' if len(unrated) > 4 else ''})")

    # ── Quality dimensions ────────────────────────────────────────────────
    print_section("QUALITY DIMENSIONS (last 10 ratings)")
    recent = ratings[-10:] if len(ratings) >= 10 else ratings
    quality_nodes = nodes_by_type(ontology, "quality")
    qids = [n["id"].split("/")[-1] for n in quality_nodes]

    if recent:
        avgs = {}
        for qid in qids:
            vals = [r["quality_scores"].get(qid, 0) for r in recent if "quality_scores" in r]
            avgs[qid] = sum(vals) / len(vals) if vals else 0.0

        for n in quality_nodes:
            qid = n["id"].split("/")[-1]
            avg = avgs.get(qid, 0.0)
            primary = "  ★ PRIMARY" if qid == "affect_induction" else ""
            print(f"  {bar(avg)}  {avg:.3f}  {n['label']}{primary}")
    else:
        print("  (no ratings yet)")

    # ── Flagged nodes detail ───────────────────────────────────────────────
    if flagged:
        print_section("FLAGGED NODES (need reconcile)")
        for n in flagged:
            print(f"  [{n['id']}]  {n['label']}  score={n['score']:.3f}  n={n['confidence']}")

    print()


if __name__ == "__main__":
    main()
