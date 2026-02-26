#!/usr/bin/env python3
"""
taxonomy_audit.py — Comprehensive integrity audit of hypnosis_taxonomy.md

Checks:
  1. All technique IDs defined in summary tables
  2. All technique IDs with detail blocks (### TID: Name sections)
  3. Missing detail blocks: defined in summary but no ### detail block
  4. Missing summary rows: has detail block but no summary table row
  5. ID sequence gaps per category
  6. Category consistency: technique prefix matches its ### Category section
  7. Detail block completeness: every technique needs good + bad examples

Outputs a full report to stdout and optionally to a file.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set


def parse_summary_table_techniques(lines: list[str]) -> Dict[str, dict]:
    """Parse all technique IDs from summary tables under ### Category sections."""
    result = {}
    current_cat = None
    in_table = False

    for line in lines:
        m = re.match(r'^### Category ([A-Z]+):', line)
        if m:
            current_cat = m.group(1)
            in_table = False
            continue

        if re.match(r'^## ', line) or line.strip() == "---":
            current_cat = None
            in_table = False
            continue

        if current_cat is None:
            continue

        if re.match(r'^\| ID\b', line):
            in_table = True
            continue
        if re.match(r'^\|[-| ]+\|', line):
            continue
        if re.match(r'^#{3,}', line) and not re.match(r'^### Category', line):
            in_table = False
            continue

        if in_table and line.startswith('|'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 3:
                tid = parts[0]
                if re.match(r'^[A-Z]+-\d+$', tid):
                    result[tid] = {
                        "name": parts[1],
                        "category": current_cat,
                        "description": parts[2],
                    }

    return result


def parse_detail_blocks(lines: list[str]) -> Dict[str, dict]:
    """Parse all ##### TID — Name detail block headings and their content."""
    result = {}
    current_tid = None
    current_name = None
    current_start = None
    block_lines: list[str] = []

    for i, line in enumerate(lines):
        m = re.match(r'^#{3,6}\s+([A-Z]+-\d+)\s*[—:\-–]\s*(.+)', line)
        if m:
            if current_tid is not None:
                _save_block(result, current_tid, current_name, current_start, block_lines)
            current_tid = m.group(1)
            current_name = m.group(2).strip()
            current_start = i
            block_lines = []
            continue

        if current_tid is not None and (re.match(r'^## ', line) or line.strip() == "---"):
            _save_block(result, current_tid, current_name, current_start, block_lines)
            current_tid = None
            block_lines = []
            continue

        if current_tid is not None:
            block_lines.append(line)

    if current_tid is not None:
        _save_block(result, current_tid, current_name, current_start, block_lines)

    return result


def _save_block(result, tid, name, start, block_lines):
    text = "\n".join(block_lines)
    result[tid] = {
        "name": name,
        "line": start + 1,
        "has_content": bool(text.strip()),
        "has_good_example": bool(re.search(r'\*\*✓\*\*', text)),
        "has_bad_example": bool(re.search(r'\*\*✗\*\*', text)),
    }


def parse_categories(lines: list[str]) -> Dict[str, dict]:
    """Parse ### Category XXX: Name headings."""
    result = {}
    for line in lines:
        m = re.match(r'^### Category ([A-Z]+): (.+)', line)
        if m:
            result[m.group(1)] = {"name": m.group(2).strip()}
    return result


def get_id_prefix(tid: str) -> str:
    return tid.rsplit("-", 1)[0]


def get_id_num(tid: str) -> int:
    return int(tid.rsplit("-", 1)[1])


def run_audit(md_path: Path) -> str:
    """Run full audit and return report as string."""
    lines = md_path.read_text(encoding="utf-8").splitlines()

    summary_techs = parse_summary_table_techniques(lines)
    detail_blocks = parse_detail_blocks(lines)
    categories = parse_categories(lines)

    all_defined = set(summary_techs.keys()) | set(detail_blocks.keys())

    report = []
    report.append("=" * 70)
    report.append("TAXONOMY INTEGRITY AUDIT")
    report.append(f"File: {md_path}")
    report.append("=" * 70)

    # ── 1. Overview ──────────────────────────────────────────────────────
    report.append(f"\n## Overview")
    report.append(f"  Categories defined:     {len(categories)}")
    report.append(f"  Summary table rows:     {len(summary_techs)}")
    report.append(f"  Detail blocks:          {len(detail_blocks)}")

    # ── 2. Per-category inventory ────────────────────────────────────────
    report.append(f"\n## Per-Category Inventory")
    cat_techs: Dict[str, list] = defaultdict(list)
    for tid in sorted(all_defined):
        prefix = get_id_prefix(tid)
        cat_techs[prefix].append(tid)

    for cat_id in sorted(categories.keys()):
        cat_name = categories[cat_id]["name"]
        techs = sorted(cat_techs.get(cat_id, []), key=get_id_num)
        report.append(f"\n  ### {cat_id}: {cat_name} ({len(techs)} techniques)")
        for tid in techs:
            s = "S" if tid in summary_techs else "."
            d = "D" if tid in detail_blocks else "."
            name = summary_techs.get(tid, {}).get("name", "") or detail_blocks.get(tid, {}).get("name", "???")
            report.append(f"    {tid:12s} [{s}{d}] {name}")

    report.append(f"\n  Legend: S=summary table, D=detail block")

    # ── 3. Missing detail blocks ──────────────────────────────────────────
    missing_detail = set(summary_techs.keys()) - set(detail_blocks.keys())
    report.append(f"\n## Missing Detail Blocks (in summary but no ### block): {len(missing_detail)}")
    if missing_detail:
        for tid in sorted(missing_detail):
            report.append(f"  {tid:12s} {summary_techs[tid]['name']}")
    else:
        report.append("  None — all summary techniques have detail blocks.")

    # ── 4. Missing summary rows ───────────────────────────────────────────
    missing_summary = set(detail_blocks.keys()) - set(summary_techs.keys())
    report.append(f"\n## Missing Summary Rows (has ### block but no table row): {len(missing_summary)}")
    if missing_summary:
        for tid in sorted(missing_summary):
            report.append(f"  {tid:12s} {detail_blocks[tid]['name']} (line {detail_blocks[tid]['line']})")
    else:
        report.append("  None — all detail blocks have summary table rows.")

    # ── 5. ID sequence gaps ───────────────────────────────────────────────
    report.append(f"\n## ID Sequence Gaps")
    gaps_found = False
    for cat_id in sorted(cat_techs.keys()):
        techs = sorted(cat_techs[cat_id], key=get_id_num)
        if not techs:
            continue
        nums = [get_id_num(t) for t in techs]
        expected = list(range(1, max(nums) + 1))
        missing = set(expected) - set(nums)
        if missing:
            gaps_found = True
            width = len(techs[0].rsplit("-", 1)[1])
            missing_ids = [f"{cat_id}-{n:0{width}d}" for n in sorted(missing)]
            report.append(f"  {cat_id}: gap at {', '.join(missing_ids)}")
    if not gaps_found:
        report.append("  None — all ID sequences are contiguous.")

    # ── 6. Category prefix consistency ────────────────────────────────────
    report.append(f"\n## Category Prefix Consistency")
    mismatches = []
    for tid, data in summary_techs.items():
        prefix = get_id_prefix(tid)
        if data["category"] != prefix:
            mismatches.append((tid, data["category"], prefix))
    if mismatches:
        for tid, expected, actual in mismatches:
            report.append(f"  {tid} listed under Category {expected} but prefix is {actual}")
    else:
        report.append("  All techniques are under the correct category section.")

    # ── 7. Detail block completeness ─────────────────────────────────────
    report.append(f"\n## Detail Block Completeness (good/bad examples)")
    missing_good = []
    missing_bad = []
    missing_both = []
    for tid in sorted(detail_blocks.keys()):
        db = detail_blocks[tid]
        has_good = db.get("has_good_example", False)
        has_bad = db.get("has_bad_example", False)
        if not has_good and not has_bad:
            missing_both.append(tid)
        elif not has_good:
            missing_good.append(tid)
        elif not has_bad:
            missing_bad.append(tid)

    if missing_both:
        report.append(f"  Missing BOTH good and bad examples: {len(missing_both)}")
        for tid in missing_both:
            name = detail_blocks[tid]["name"]
            report.append(f"    {tid:12s} {name}")
    if missing_good:
        report.append(f"  Missing good (✓) examples only: {len(missing_good)}")
        for tid in missing_good:
            name = detail_blocks[tid]["name"]
            report.append(f"    {tid:12s} {name}")
    if missing_bad:
        report.append(f"  Missing bad (✗) examples only: {len(missing_bad)}")
        for tid in missing_bad:
            name = detail_blocks[tid]["name"]
            report.append(f"    {tid:12s} {name}")
    if not missing_both and not missing_good and not missing_bad:
        report.append("  All detail blocks have both good and bad examples.")

    # ── 8. Summary stats ─────────────────────────────────────────────────
    report.append(f"\n## Summary")
    issues = len(missing_detail) + len(missing_summary)
    example_gaps = len(missing_both) + len(missing_good) + len(missing_bad)
    report.append(f"  Total structural issues: {issues}")
    report.append(f"  Example completeness gaps: {example_gaps}")
    if issues == 0 and example_gaps == 0:
        report.append("  CLEAN — taxonomy is fully consistent.")
    else:
        report.append("  See sections above for details.")

    report.append("")
    return "\n".join(report)


def main():
    md_path = Path(__file__).resolve().parent / "hypnosis_taxonomy.md"
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(f"Usage: {sys.argv[0]} [taxonomy.md] [-o report.txt]")
            sys.exit(0)
        md_path = Path(sys.argv[1])

    output_path = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])

    if not md_path.exists():
        print(f"ERROR: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    report = run_audit(md_path)
    print(report)

    if output_path:
        output_path.write_text(report, encoding="utf-8")
        print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
