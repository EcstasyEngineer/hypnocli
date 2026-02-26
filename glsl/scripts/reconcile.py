#!/usr/bin/env python3
"""
reconcile.py — Human-gated ontology restructuring
---------------------------------------------------
Collects flagged nodes, calls Sonnet with full ontology context,
proposes structural changes (merge/split/retire/rename).
Human approves each change. Applies to ontology.json.
Logs all changes to ontology_changelog.jsonl.

Usage:
    python3 reconcile.py
    python3 reconcile.py --dry-run   # show proposals, don't apply
    python3 reconcile.py --auto      # auto-approve all (use with caution)
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    GLSL_DIR,
    get_api_key, load_ontology, save_ontology, node_by_id,
)

CHANGELOG_PATH = GLSL_DIR / "ontology_changelog.jsonl"

RECONCILE_SYSTEM = """\
You are an expert knowledge engineer reviewing an evolving ontology of GLSL shader
techniques used in a hypnosis-focused adversarial AI pipeline.

You will be given:
1. The complete current ontology (JSON)
2. A list of flagged nodes with their flag reasons and score histories

Your task: propose structural changes to improve the ontology's signal quality.

Valid operations:
  - merge: combine two similar nodes into one (preserves higher score)
  - split: divide an overloaded node into two more specific ones
  - retire: deactivate a dead/useless node
  - rename: update label/description for clarity
  - unflag: clear the flag_for_review (node is fine, flag was wrong)
  - add: propose a new technique node not currently in the ontology

Respond with valid JSON:
{
  "proposals": [
    {
      "op": "merge" | "split" | "retire" | "rename" | "unflag" | "add",
      "target_id": "<node_id>",
      "secondary_id": "<node_id for merge/split>",  // optional
      "new_id": "<new node id>",                     // for split/add
      "new_label": "<label>",
      "new_description": "<description>",
      "rationale": "<why this change improves the ontology>"
    }
  ]
}

Be conservative: propose only changes that are clearly justified by the data.
High-variance nodes need more data, not immediate retirement unless score is very low.
"""


def gather_flagged_nodes(ontology: dict) -> list[dict]:
    return [n for n in ontology["nodes"] if n.get("flag_for_review") and not n.get("retired")]


def build_reconcile_prompt(ontology: dict, flagged: list[dict]) -> str:
    ontology_summary = json.dumps(ontology, indent=2)[:8000]  # truncate for token budget
    flagged_summary = json.dumps(flagged, indent=2)

    return f"""Current ontology (truncated if long):
{ontology_summary}

Flagged nodes requiring review:
{flagged_summary}

Propose structural changes to improve ontology quality.
Respond only with JSON matching the schema in your system prompt."""


def call_reconciler(prompt: str, api_key: str) -> list[dict]:
    """Call Sonnet for reconciliation proposals."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=RECONCILE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    try:
        data = json.loads(raw)
        return data.get("proposals", [])
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data.get("proposals", [])
        print(f"WARNING: could not parse reconciler proposals:\n{raw[:500]}", file=sys.stderr)
        return []


def apply_merge(ontology: dict, proposal: dict) -> str:
    """Merge secondary_id into target_id."""
    target = node_by_id(ontology, proposal["target_id"])
    secondary = node_by_id(ontology, proposal.get("secondary_id", ""))
    if not target or not secondary:
        return f"SKIP merge: node(s) not found"

    # Combine scores (weighted by confidence)
    t_conf = target.get("confidence", 0)
    s_conf = secondary.get("confidence", 0)
    total = t_conf + s_conf
    if total > 0:
        merged_score = (target.get("score", 0) * t_conf + secondary.get("score", 0) * s_conf) / total
    else:
        merged_score = 0.0

    target["score"] = round(merged_score, 6)
    target["confidence"] = total
    target["label"] = proposal.get("new_label", target["label"])
    target["description"] = proposal.get("new_description", target["description"])
    target["flag_for_review"] = False
    target["sample_shader_ids"] = list(set(
        target.get("sample_shader_ids", []) + secondary.get("sample_shader_ids", [])
    ))

    # Retire secondary
    secondary["retired"] = True
    secondary["active"] = False

    return f"Merged {proposal['secondary_id']} into {proposal['target_id']}"


def apply_retire(ontology: dict, proposal: dict) -> str:
    node = node_by_id(ontology, proposal["target_id"])
    if not node:
        return f"SKIP retire: node not found"
    node["retired"] = True
    node["active"] = False
    node["flag_for_review"] = False
    return f"Retired {proposal['target_id']}"


def apply_rename(ontology: dict, proposal: dict) -> str:
    node = node_by_id(ontology, proposal["target_id"])
    if not node:
        return f"SKIP rename: node not found"
    if "new_label" in proposal:
        node["label"] = proposal["new_label"]
    if "new_description" in proposal:
        node["description"] = proposal["new_description"]
    node["flag_for_review"] = False
    return f"Renamed {proposal['target_id']}"


def apply_unflag(ontology: dict, proposal: dict) -> str:
    node = node_by_id(ontology, proposal["target_id"])
    if not node:
        return f"SKIP unflag: node not found"
    node["flag_for_review"] = False
    node.pop("flag_reason", None)
    return f"Unflagged {proposal['target_id']}"


def apply_add(ontology: dict, proposal: dict) -> str:
    new_id = proposal.get("new_id", "")
    if not new_id:
        return "SKIP add: no new_id"
    if node_by_id(ontology, new_id):
        return f"SKIP add: node {new_id} already exists"

    parent = "/".join(new_id.split("/")[:-1])
    new_node = {
        "id": new_id,
        "type": "technique",
        "parent": parent,
        "label": proposal.get("new_label", new_id.split("/")[-1]),
        "description": proposal.get("new_description", ""),
        "prompt_fragment": proposal.get("new_description", ""),
        "score": 0.0,
        "confidence": 0,
        "active": True,
        "retired": False,
        "flag_for_review": False,
        "sample_shader_ids": [],
    }
    ontology["nodes"].append(new_node)
    return f"Added {new_id}"


def apply_split(ontology: dict, proposal: dict) -> str:
    """Split a node into two more specific ones."""
    target = node_by_id(ontology, proposal["target_id"])
    new_id = proposal.get("new_id", "")
    if not target or not new_id:
        return "SKIP split: missing target or new_id"

    # Clone target as the new split-off node
    import copy
    new_node = copy.deepcopy(target)
    new_node["id"] = new_id
    new_node["label"] = proposal.get("new_label", new_id.split("/")[-1])
    new_node["description"] = proposal.get("new_description", "")
    new_node["prompt_fragment"] = proposal.get("new_description", "")
    new_node["score"] = 0.0  # reset — needs new data
    new_node["confidence"] = 0
    new_node["flag_for_review"] = False
    new_node["sample_shader_ids"] = []

    ontology["nodes"].append(new_node)
    target["flag_for_review"] = False
    target["label"] = proposal.get("new_label", target["label"]) + " (original)"
    return f"Split {proposal['target_id']} → created {new_id}"


def prompt_user(proposal: dict) -> bool:
    """Show proposal to user, return True if approved."""
    print(f"\n  Proposal: {proposal.get('op', '?').upper()}")
    print(f"  Target  : {proposal.get('target_id', '')}")
    if "secondary_id" in proposal:
        print(f"  Secondary: {proposal.get('secondary_id')}")
    if "new_id" in proposal:
        print(f"  New ID  : {proposal.get('new_id')}")
    if "new_label" in proposal:
        print(f"  New label: {proposal.get('new_label')}")
    print(f"  Rationale: {proposal.get('rationale', '')[:200]}")

    try:
        ans = input("  Approve? [y/n/q] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False

    if ans == "q":
        sys.exit(0)
    return ans == "y"


def log_change(proposal: dict, result: str, approved: bool):
    entry = {
        "timestamp": time.time(),
        "approved": approved,
        "proposal": proposal,
        "result": result,
    }
    with open(CHANGELOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Reconcile ontology (human-gated)")
    parser.add_argument("--dry-run", action="store_true", help="Show proposals, don't apply")
    parser.add_argument("--auto", action="store_true", help="Auto-approve all proposals")
    args = parser.parse_args()

    ontology = load_ontology()
    flagged = gather_flagged_nodes(ontology)

    if not flagged:
        print("No flagged nodes — ontology is healthy. Nothing to reconcile.")
        return

    print(f"Flagged nodes: {len(flagged)}")
    for n in flagged:
        print(f"  [{n['id']}] {n['label']}  score={n['score']:.3f}  n={n['confidence']}"
              f"  reason={n.get('flag_reason', '?')}")

    api_key = get_api_key()
    prompt = build_reconcile_prompt(ontology, flagged)

    print(f"\nCalling Resolver (Sonnet) for reconciliation proposals...")
    proposals = call_reconciler(prompt, api_key)

    if not proposals:
        print("No proposals returned.")
        return

    print(f"\n{len(proposals)} proposals:")

    op_map = {
        "merge": apply_merge,
        "retire": apply_retire,
        "rename": apply_rename,
        "unflag": apply_unflag,
        "add": apply_add,
        "split": apply_split,
    }

    applied = 0
    for proposal in proposals:
        if args.dry_run:
            print(f"\n  [DRY RUN] {proposal.get('op')} — {proposal.get('target_id')}")
            print(f"    Rationale: {proposal.get('rationale', '')[:200]}")
            continue

        approved = args.auto or prompt_user(proposal)
        op = proposal.get("op", "")
        fn = op_map.get(op)

        if fn and approved:
            result = fn(ontology, proposal)
            print(f"  → {result}")
            log_change(proposal, result, approved=True)
            applied += 1
        else:
            reason = "op not recognized" if not fn else "user rejected"
            log_change(proposal, reason, approved=False)
            print(f"  Skipped: {reason}")

    if applied > 0 and not args.dry_run:
        save_ontology(ontology)
        print(f"\nOntology updated: {applied} changes applied.")
        print(f"Changelog: {CHANGELOG_PATH}")
    elif not args.dry_run:
        print("\nNo changes applied.")


if __name__ == "__main__":
    main()
