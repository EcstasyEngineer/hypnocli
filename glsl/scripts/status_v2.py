#!/usr/bin/env python3
"""
status_v2.py — Knowledge graph dashboard
------------------------------------------
Shows: total stats, top patterns, recent hypotheses, corpus, defects.

Usage:
    python3 status_v2.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_knowledge


def main():
    knowledge = load_knowledge()
    meta = knowledge["meta"]
    patterns = knowledge["patterns"]
    hypotheses = knowledge["hypotheses"]
    corpus = knowledge["corpus"]
    defect_types = knowledge["defect_types"]

    # ── Overview ──
    print(f"{'=' * 60}")
    print(f"  GLSL v2 Knowledge Graph Status")
    print(f"{'=' * 60}")
    print(f"  Generations: {meta['total_generations']}")
    print(f"  Ratings:     {meta['total_ratings']}")
    print(f"  Patterns:    {len(patterns)}")

    # Hypothesis stats
    statuses = {}
    for h in hypotheses.values():
        s = h.get("status", "untested")
        statuses[s] = statuses.get(s, 0) + 1
    status_str = "  ".join(f"{k}: {v}" for k, v in sorted(statuses.items()))
    print(f"  Hypotheses:  {len(hypotheses)} ({status_str})")

    # Corpus
    seeds = sum(1 for c in corpus if c["type"] == "seed")
    promoted = sum(1 for c in corpus if c["type"] == "promoted")
    print(f"  Corpus:      {len(corpus)} ({seeds} seeds + {promoted} promoted)")

    # ── Top patterns by evidence ──
    print(f"\n  {'─' * 56}")
    print(f"  TOP PATTERNS (by evidence count)")
    print(f"  {'─' * 56}")

    ranked = []
    for slug, p in patterns.items():
        ev = p["evidence"]
        if not ev:
            continue
        confirms = sum(1 for e in ev if e["result"] == "confirmed")
        rejects = sum(1 for e in ev if e["result"] == "rejected")
        avg = sum(e["score"] for e in ev) / len(ev)
        ranked.append((slug, len(ev), confirms, rejects, avg, p["works_with"], p["fails_with"]))

    ranked.sort(key=lambda x: (-x[1], -x[4]))
    for slug, total, c, r, avg, ww, fw in ranked[:15]:
        ww_str = f" +[{','.join(ww[:3])}]" if ww else ""
        fw_str = f" -[{','.join(fw[:3])}]" if fw else ""
        print(f"    {slug:<30} {total:>2}ev  +{c}/-{r}  avg={avg:.2f}{ww_str}{fw_str}")

    if not ranked:
        print(f"    (no evidence yet)")

    # ── Recent hypotheses ──
    print(f"\n  {'─' * 56}")
    print(f"  RECENT HYPOTHESES")
    print(f"  {'─' * 56}")

    recent = sorted(hypotheses.values(), key=lambda h: h.get("created", ""), reverse=True)[:10]
    for h in recent:
        status = h.get("status", "?")
        score = h.get("score")
        score_str = f"{score:.2f}" if score is not None else "  - "
        defects = h.get("defects", [])
        defect_str = f" [{','.join(defects)}]" if defects else ""
        stmt = h["statement"][:60]
        print(f"    [{status:<10} {score_str}]{defect_str} {stmt}")

    if not recent:
        print(f"    (no hypotheses yet)")

    # ── Corpus ──
    print(f"\n  {'─' * 56}")
    print(f"  CORPUS")
    print(f"  {'─' * 56}")

    for c in corpus:
        score_str = f"{c['score']:.2f}" if c.get("score") is not None else " -  "
        pats = ", ".join(c.get("patterns", [])[:4])
        print(f"    [{c['type']:<8}] {c['id']:<30} {score_str}  {pats}")

    # ── Defects ──
    active_defects = [(k, v) for k, v in defect_types.items() if v.get("occurrences", 0) > 0]
    if active_defects:
        print(f"\n  {'─' * 56}")
        print(f"  DEFECTS")
        print(f"  {'─' * 56}")
        for k, v in sorted(active_defects, key=lambda x: -x[1]["occurrences"]):
            print(f"    {v['label']:<20} {v['occurrences']:>3}x  {v['mitigation'][:50]}")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    main()
