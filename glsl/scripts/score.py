#!/usr/bin/env python3
"""
score.py
--------
Propagate Resolver critique scores to ontology technique nodes.

Reads the critique JSON for a shader, updates node scores and confidence,
flags nodes that need reconciliation attention.

Usage:
    python3 score.py <shader_id>             # score shader by ID
    python3 score.py <shader_id> --boost     # apply 1.5x boost (promoted shaders)
    python3 score.py <shader_id> --critique path/to/critique.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SHADERS_DIR, RENDERS_DIR,
    load_ontology, save_ontology, node_by_id, append_rating,
)

# Quality weights: affect_induction counts double
QUALITY_WEIGHTS = {
    "depth_illusion":     1.0,
    "attentional_capture": 1.0,
    "motion_clarity":     1.0,
    "loop_seamlessness":  1.0,
    "affect_induction":   2.0,
}

# Thresholds for flagging
FLAG_HIGH_VARIANCE_THRESHOLD = 0.35  # flag if std dev across ratings > this
FLAG_ORPHAN_CONFIDENCE = 3            # flag if only used in N shaders and score low
FLAG_DEAD_BRANCH_SCORE = 0.2          # flag if score < this after enough samples
FLAG_DEAD_BRANCH_MIN_N = 8


def weighted_score(quality_scores: dict) -> float:
    """Compute single weighted shader score from quality dimension scores."""
    total_weight = sum(QUALITY_WEIGHTS.values())
    weighted_sum = sum(
        QUALITY_WEIGHTS.get(k, 1.0) * v
        for k, v in quality_scores.items()
    )
    return weighted_sum / total_weight


def get_shader_technique_ids(shader_id: str) -> list[str]:
    """Read technique node IDs from the shader's metadata sidecar."""
    meta_path = SHADERS_DIR / f"{shader_id}.json"
    if not meta_path.exists():
        # Try to parse from the shader header comments
        glsl_path = SHADERS_DIR / f"{shader_id}.glsl"
        if not glsl_path.exists():
            return []
        header = glsl_path.read_text().split("\n")[:5]
        tech_ids = []
        for line in header:
            if line.startswith("// techniques:"):
                ids = line.replace("// techniques:", "").strip().split(", ")
                # Convert short IDs back to full paths
                # We'll do a fuzzy lookup below
                tech_ids = ids
            if line.startswith("// archetype:"):
                arch = line.replace("// archetype:", "").strip()
                tech_ids.insert(0, f"archetypes/{arch}")
        return tech_ids

    meta = json.loads(meta_path.read_text())
    return meta.get("selected_node_ids", [])


def update_node_score(node: dict, new_score: float) -> dict:
    """
    Update rolling average score on a node.
    score = sum_of_all_ratings / confidence
    confidence += 1
    """
    old_score = node.get("score", 0.0)
    old_conf = node.get("confidence", 0)

    new_conf = old_conf + 1
    # Recalculate as running average: new_avg = (old_avg * old_n + new_val) / new_n
    new_avg = (old_score * old_conf + new_score) / new_conf

    node["score"] = round(new_avg, 6)
    node["confidence"] = new_conf
    return node


def check_and_flag(node: dict, all_ratings_for_node: list[float]) -> bool:
    """Apply flagging logic. Returns True if newly flagged."""
    if node.get("flag_for_review"):
        return False

    n = len(all_ratings_for_node)
    if n < 2:
        return False

    mean = sum(all_ratings_for_node) / n
    variance = sum((x - mean) ** 2 for x in all_ratings_for_node) / n
    std_dev = variance ** 0.5

    flagged = False

    # High variance: inconsistent performance
    if std_dev > FLAG_HIGH_VARIANCE_THRESHOLD and n >= 5:
        node["flag_for_review"] = True
        node["flag_reason"] = f"high_variance: std={std_dev:.2f}"
        flagged = True

    # Dead branch: consistently low score
    if n >= FLAG_DEAD_BRANCH_MIN_N and mean < FLAG_DEAD_BRANCH_SCORE:
        node["flag_for_review"] = True
        node["flag_reason"] = f"dead_branch: mean={mean:.2f} after n={n}"
        flagged = True

    # Orphan: low confidence AND low score
    if n <= FLAG_ORPHAN_CONFIDENCE and mean < 0.25:
        node["flag_for_review"] = True
        node["flag_reason"] = f"orphan_low_score: n={n} mean={mean:.2f}"
        flagged = True

    return flagged


def main():
    parser = argparse.ArgumentParser(description="Propagate Resolver scores to ontology")
    parser.add_argument("shader_id", help="Shader ID (hex)")
    parser.add_argument("--boost", action="store_true", help="Apply 1.5x boost (promoted shader)")
    parser.add_argument("--critique", help="Path to critique JSON (default: renders/<id>_critique.json)")
    args = parser.parse_args()

    shader_id = args.shader_id

    # Load critique
    critique_path = Path(args.critique) if args.critique else RENDERS_DIR / f"{shader_id}_critique.json"
    if not critique_path.exists():
        print(f"ERROR: critique not found: {critique_path}", file=sys.stderr)
        print("Run critique.py first.", file=sys.stderr)
        sys.exit(1)

    critique = json.loads(critique_path.read_text())
    quality_scores = critique.get("quality_scores", {})
    tier = critique.get("tier", "revise")

    # Compute shader score
    shader_score = weighted_score(quality_scores)
    if args.boost or tier == "promote":
        shader_score = min(1.0, shader_score * 1.5)

    print(f"Shader {shader_id}: score={shader_score:.3f}  tier={tier}", file=sys.stderr)

    # Load ontology
    ontology = load_ontology()
    node_map = {n["id"]: n for n in ontology["nodes"]}

    # Get technique node IDs used in this shader
    node_ids = get_shader_technique_ids(shader_id)
    if not node_ids:
        print(f"WARNING: no technique metadata for shader {shader_id}", file=sys.stderr)

    # Update each node
    updated_ids = []
    for nid in node_ids:
        node = node_map.get(nid)
        if not node:
            # Try partial match for short-form IDs
            matches = [n for n in ontology["nodes"] if n["id"].endswith("/" + nid)]
            if matches:
                node = matches[0]
            else:
                print(f"  WARNING: node '{nid}' not in ontology", file=sys.stderr)
                continue

        node = update_node_score(node, shader_score)
        node.setdefault("sample_shader_ids", [])
        if shader_id not in node["sample_shader_ids"]:
            node["sample_shader_ids"].append(shader_id)

        updated_ids.append(node["id"])
        print(f"  {node['id']}: score={node['score']:.3f} (n={node['confidence']})", file=sys.stderr)

    # Also update quality dimension nodes
    for qid, qscore in quality_scores.items():
        full_id = f"quality/{qid}"
        node = node_map.get(full_id)
        if node:
            update_node_score(node, qscore)

    # Flagging pass: collect all historical scores for each updated node
    ratings_path = GLSL_DIR / "ratings.jsonl"
    historical: dict[str, list[float]] = {}
    if ratings_path.exists():
        for line in ratings_path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            s_score = weighted_score(r.get("quality_scores", {}))
            for nid in r.get("node_ids", []):
                historical.setdefault(nid, []).append(s_score)

    for nid in updated_ids:
        node = node_map.get(nid)
        if node:
            hist = historical.get(nid, []) + [shader_score]
            flagged = check_and_flag(node, hist)
            if flagged:
                print(f"  FLAGGED: {nid} ({node.get('flag_reason', '')})", file=sys.stderr)

    # Persist revision note onto the archetype node
    revision_note = critique.get("revision_prompt", "").strip()
    if revision_note:
        # Find the archetype node used in this shader
        arch_id = next((nid for nid in node_ids if nid.startswith("archetypes/")), None)
        if arch_id:
            arch_node = node_map.get(arch_id)
            if arch_node:
                arch_node.setdefault("accumulated_feedback", [])
                arch_node["accumulated_feedback"].append(revision_note)
                # Keep last 20 notes
                arch_node["accumulated_feedback"] = arch_node["accumulated_feedback"][-20:]

    # Save updated ontology
    save_ontology(ontology)

    # Append rating record
    rating_record = {
        "shader_id": shader_id,
        "tier": tier,
        "shader_score": round(shader_score, 6),
        "quality_scores": quality_scores,
        "node_ids": node_ids,
        "boost": args.boost,
        "revision_prompt": critique.get("revision_prompt", ""),
    }
    append_rating(rating_record)

    print(f"  ontology updated, rating appended to ratings.jsonl", file=sys.stderr)


if __name__ == "__main__":
    main()
