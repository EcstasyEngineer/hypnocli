#!/usr/bin/env python3
"""
learn.py — Structured feedback → knowledge graph update
---------------------------------------------------------
Takes a rating dict from the v2 rater UI and updates knowledge.json:
  - Confirmed: score >= 0.7, no defects, majority yes → works_with edges, promote to corpus
  - Rejected: score < 0.3 or critical defect + score < 0.5 → fails_with edges
  - Partial: everything else → record evidence, no edge changes

Usage (standalone, mainly called from run_v2.py):
    python3 learn.py '{"shader_id": "abc123", "score": 0.8, ...}'
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR, SHADERS_DIR,
    load_knowledge, save_knowledge, append_rating_v2,
)


def classify_outcome(score: float, answers: dict, defects: list[str]) -> str:
    """Classify a rating into confirmed/rejected/partial."""
    has_defects = len(defects) > 0
    critical_defects = {"black_frame", "gpu_timeout"}
    has_critical = bool(set(defects) & critical_defects)

    # Count yes/no answers
    yes_count = sum(1 for v in answers.values() if v is True)
    no_count = sum(1 for v in answers.values() if v is False)
    total = yes_count + no_count
    majority_yes = total == 0 or yes_count > total / 2

    if has_critical and score < 0.5:
        return "rejected"
    if score < 0.3:
        return "rejected"
    if score >= 0.7 and not has_defects and majority_yes:
        return "confirmed"
    return "partial"


def add_edge(patterns: dict, slug_a: str, slug_b: str, edge_type: str):
    """Add a works_with or fails_with edge between two patterns."""
    if slug_a not in patterns or slug_b not in patterns:
        return
    if slug_b not in patterns[slug_a][edge_type]:
        patterns[slug_a][edge_type].append(slug_b)
        patterns[slug_a][edge_type].sort()
    if slug_a not in patterns[slug_b][edge_type]:
        patterns[slug_b][edge_type].append(slug_a)
        patterns[slug_b][edge_type].sort()


def ensure_pattern(patterns: dict, slug: str):
    """Create a pattern entry if it doesn't exist (for new slugs from Sonnet)."""
    if slug in patterns:
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    patterns[slug] = {
        "label": slug.replace("_", " ").title(),
        "description": "",
        "evidence": [],
        "works_with": [],
        "fails_with": [],
        "open_questions": [],
        "source": "generated",
        "first_seen": now,
    }


def learn(knowledge: dict, rating: dict) -> str:
    """
    Process a v2 rating and update knowledge graph.
    Returns the outcome: "confirmed", "rejected", or "partial".
    """
    shader_id = rating["shader_id"]
    score = rating.get("score", 0.5)
    answers = rating.get("answers", {})
    defects = rating.get("defects", [])
    note = rating.get("note", "")
    discard = rating.get("discard", False)

    if discard:
        score = 0.0

    # Find the hypothesis for this shader
    hypothesis_id = None
    hypothesis = None
    for h_id, h in knowledge["hypotheses"].items():
        if h.get("shader_id") == shader_id:
            hypothesis_id = h_id
            hypothesis = h
            break

    if not hypothesis:
        # No hypothesis found — look in sidecar
        sidecar_path = SHADERS_DIR / f"{shader_id}.json"
        if sidecar_path.exists():
            sidecar = json.loads(sidecar_path.read_text())
            hypothesis_id = sidecar.get("hypothesis_id")
            if hypothesis_id and hypothesis_id in knowledge["hypotheses"]:
                hypothesis = knowledge["hypotheses"][hypothesis_id]

    patterns_involved = []
    if hypothesis:
        patterns_involved = hypothesis.get("patterns_involved", [])

    outcome = "rejected" if discard else classify_outcome(score, answers, defects)

    # Ensure all patterns exist
    for slug in patterns_involved:
        ensure_pattern(knowledge["patterns"], slug)

    # Record evidence on each pattern
    evidence_entry = {
        "hypothesis_id": hypothesis_id or "unknown",
        "result": outcome,
        "score": round(score, 3),
    }
    for slug in patterns_involved:
        knowledge["patterns"][slug]["evidence"].append(evidence_entry)

    # Update edges based on outcome
    if outcome == "confirmed" and len(patterns_involved) >= 2:
        for i, a in enumerate(patterns_involved):
            for b in patterns_involved[i + 1:]:
                add_edge(knowledge["patterns"], a, b, "works_with")

    elif outcome == "rejected" and len(patterns_involved) >= 2:
        for i, a in enumerate(patterns_involved):
            for b in patterns_involved[i + 1:]:
                add_edge(knowledge["patterns"], a, b, "fails_with")

    # Update defect counts
    for d in defects:
        if d in knowledge["defect_types"]:
            knowledge["defect_types"][d]["occurrences"] += 1

    # Update hypothesis
    if hypothesis:
        hypothesis["status"] = outcome
        hypothesis["score"] = round(score, 3)
        hypothesis["answers"] = answers
        hypothesis["defects"] = defects
        hypothesis["note"] = note

    # Promote to corpus if confirmed
    if outcome == "confirmed":
        shader_path = SHADERS_DIR / f"{shader_id}.glsl"
        if shader_path.exists():
            # Check not already in corpus
            existing_ids = {c["id"] for c in knowledge["corpus"]}
            corpus_id = f"gen:{shader_id}"
            if corpus_id not in existing_ids:
                knowledge["corpus"].append({
                    "id": corpus_id,
                    "path": f"shaders/{shader_id}.glsl",
                    "type": "promoted",
                    "motivation": hypothesis["statement"] if hypothesis else "",
                    "patterns": patterns_involved,
                    "score": round(score, 3),
                    "promoted_from_hypothesis": hypothesis_id,
                })

    # Update meta
    knowledge["meta"]["total_ratings"] += 1

    # Append to ratings log
    append_rating_v2({
        "shader_id": shader_id,
        "hypothesis_id": hypothesis_id,
        "score": round(score, 3),
        "outcome": outcome,
        "answers": answers,
        "defects": defects,
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    save_knowledge(knowledge)
    return outcome


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 learn.py '{\"shader_id\": ..., \"score\": ..., ...}'")
        sys.exit(1)

    rating = json.loads(sys.argv[1])
    knowledge = load_knowledge()
    outcome = learn(knowledge, rating)
    print(f"  → {outcome.upper()}")


if __name__ == "__main__":
    main()
