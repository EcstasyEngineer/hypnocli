"""
taxonomy.py — Parse hypnosis_taxonomy.md into the same dict structure
previously served by hypnosis_taxonomy.json.

Only the three keys actually consumed by phase_chat_generator.py are built:
  - "techniques"  {TID: {name, category, description}}
  - "phases"      {P1-P5: {name, required, duration_s, words, function,
                            primary_techniques, secondary_techniques,
                            entry, exit, success, use_when, skip_when}}
  - "categories"  {CAT: {name, purpose}}

"modules" (M1-M4) is also returned with the same schema for completeness.
phase_chat_generator.py does not access _TAXONOMY["modules"], preserving
the existing behaviour.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# words-per-phase: not present in the markdown, hardcoded here.
# If these ever need to change, add a Words column to the phase tables
# in hypnosis_taxonomy.md and update _parse_phase_summary_tables() to read it.
_WORDS: Dict[str, List[int]] = {
    "P1": [50, 100],
    "P2": [100, 150],
    "P3": [150, 300],
    "P4": [200, 500],
    "P5": [50, 150],
    "M1": [100, 200],
    "M2": [100, 200],
    "M3": [100, 300],
    "M4": [100, 150],
}


def _expand_range(token: str) -> List[str]:
    """Expand 'SAFE-01–SAFE-04' (en-dash or hyphen range) to a list of IDs."""
    token = token.strip()
    m = re.match(r'([A-Z]+)-(\d+)[–\-]([A-Z]+)-(\d+)', token)
    if m:
        prefix = m.group(1)
        start, end = int(m.group(2)), int(m.group(4))
        width = len(m.group(2))  # preserve zero-padding width
        return [f"{prefix}-{i:0{width}d}" for i in range(start, end + 1)]
    return [token] if token else []


def _parse_tech_list(cell: str) -> List[str]:
    """Parse a comma-separated technique cell, expanding ID ranges."""
    result: List[str] = []
    for token in cell.split(","):
        result.extend(_expand_range(token))
    return result


def _parse_duration(s: str) -> List[int]:
    """'30-90s' or '60–120s' → [30, 90].  Single number → [n, n]."""
    nums = re.findall(r'\d+', s)
    if len(nums) >= 2:
        return [int(nums[0]), int(nums[1])]
    if len(nums) == 1:
        return [int(nums[0]), int(nums[0])]
    return [0, 0]


class TaxonomyReader:
    """
    Drop-in replacement for json.load(open('hypnosis_taxonomy.json')).

    Usage:
        from taxonomy import TaxonomyReader
        data = TaxonomyReader().load()
        # data["techniques"], data["phases"], data["categories"] — same keys as JSON
    """

    def __init__(self, md_path: Optional[Path] = None):
        if md_path is None:
            md_path = Path(__file__).resolve().parent / "hypnosis_taxonomy.md"
        self._path = Path(md_path)

    def load(self) -> Dict[str, Any]:
        lines = self._path.read_text(encoding="utf-8").splitlines()
        techniques = self._parse_techniques(lines)
        categories = self._parse_categories(lines)
        phases, modules = self._parse_phases_and_modules(lines)
        return {
            "techniques": techniques,
            "categories": categories,
            "phases": phases,
            "modules": modules,
        }

    # ── Techniques ────────────────────────────────────────────────────────────

    def _parse_techniques(self, lines: List[str]) -> Dict[str, Dict]:
        """
        Parse from the summary table inside each '### Category XXX:' section.
        Table rows:  | TID | Name | Description |
        """
        result: Dict[str, Dict] = {}
        current_cat: Optional[str] = None
        in_table = False

        for line in lines:
            # Category heading: ### Category INDU: Induction Techniques
            m = re.match(r'^### Category ([A-Z]+):', line)
            if m:
                current_cat = m.group(1)
                in_table = False
                continue

            # A new major section ends the current category
            if re.match(r'^## ', line) or line.strip() == "---":
                current_cat = None
                in_table = False
                continue

            if current_cat is None:
                continue

            # Table header row
            if re.match(r'^\| ID\b', line):
                in_table = True
                continue

            # Separator row
            if re.match(r'^\|[-| ]+\|', line):
                continue

            # Sub-heading inside the category block ends the table
            if re.match(r'^#{3,}', line):
                in_table = False
                continue

            if in_table and line.startswith('|'):
                parts = [p.strip() for p in line.split('|')]
                parts = [p for p in parts if p]  # drop empty border cells
                if len(parts) >= 3:
                    tid = parts[0]
                    if re.match(r'^[A-Z]+-\d+$', tid):
                        result[tid] = {
                            "name": parts[1],
                            "category": current_cat,
                            "description": parts[2],
                        }

        return result

    # ── Categories ────────────────────────────────────────────────────────────

    def _parse_categories(self, lines: List[str]) -> Dict[str, Dict]:
        """
        Parse '### Category XXX: Full Name' headings and the '*Purpose: ...*'
        italic line immediately below each heading.
        """
        result: Dict[str, Dict] = {}
        for i, line in enumerate(lines):
            m = re.match(r'^### Category ([A-Z]+): (.+)', line)
            if not m:
                continue
            cat_id = m.group(1)
            cat_name = m.group(2).strip()
            purpose = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                pm = re.match(r'^\*Purpose: (.+)\*$', lines[j].strip())
                if pm:
                    purpose = pm.group(1).strip()
                    break
            result[cat_id] = {"name": cat_name, "purpose": purpose}
        return result

    # ── Phases + Modules ──────────────────────────────────────────────────────

    def _parse_phases_and_modules(
        self, lines: List[str]
    ) -> Tuple[Dict, Dict]:
        """
        Merge three sources:
          1. Summary tables (1.1)  — duration_s, required flag, name
          2. Detail blocks (1.4/1.5) — function, entry, exit, success, use_when, skip_when
          3. Compatibility matrix (2.3) — primary_techniques, secondary_techniques
        """
        meta = self._parse_phase_summary_tables(lines)
        detail = self._parse_phase_detail_blocks(lines)
        compat = self._parse_compatibility_matrix(lines)

        phases: Dict[str, Dict] = {}
        modules: Dict[str, Dict] = {}

        for pid, m in meta.items():
            entry = {
                **m,
                "words": _WORDS.get(pid, [100, 200]),
                "function":   detail.get(pid, {}).get("function", ""),
                "entry":      detail.get(pid, {}).get("entry", ""),
                "exit":       detail.get(pid, {}).get("exit", ""),
                "success":    detail.get(pid, {}).get("success", ""),
                "use_when":   detail.get(pid, {}).get("use_when", ""),
                "skip_when":  detail.get(pid, {}).get("skip_when", ""),
                "primary_techniques":   compat.get(pid, {}).get("primary", []),
                "secondary_techniques": compat.get(pid, {}).get("secondary", []),
            }
            if pid.startswith("P"):
                phases[pid] = entry
            else:
                modules[pid] = entry

        return phases, modules

    def _parse_phase_summary_tables(self, lines: List[str]) -> Dict[str, Dict]:
        """
        Parse the '### Required Phases' and '### Optional Modules' tables.
        Duration is always the last column; name is always the second column.
        """
        result: Dict[str, Dict] = {}
        in_required = False
        in_optional = False
        in_table = False

        for line in lines:
            stripped = line.strip()

            if stripped == "### Required Phases":
                in_required, in_optional, in_table = True, False, False
                continue
            if stripped == "### Optional Modules":
                in_optional, in_required, in_table = True, False, False
                continue

            # A major heading ends both sections
            if re.match(r'^## ', line):
                in_required = in_optional = in_table = False
                continue

            if not (in_required or in_optional):
                continue

            if re.match(r'^\| ID\b', line):
                in_table = True
                continue
            if re.match(r'^\|[-| ]+\|', line):
                continue
            if not line.startswith('|'):
                in_table = False
                continue

            if in_table:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if not parts:
                    continue
                pid = parts[0]
                if not re.match(r'^[PM]\d+$', pid):
                    continue
                name = parts[1] if len(parts) > 1 else ""
                dur_str = parts[-1]
                result[pid] = {
                    "name": name,
                    "required": in_required,
                    "duration_s": _parse_duration(dur_str),
                }

        return result

    def _parse_phase_detail_blocks(self, lines: List[str]) -> Dict[str, Dict]:
        """
        Parse bullet lists under '### P1: ...' and '### M1: ...' headings.
        Sections 1.4 (P1-P5) and 1.5 (M1-M4).
        """
        result: Dict[str, Dict] = {}
        current_pid: Optional[str] = None

        for line in lines:
            # Start of a new phase/module detail block
            m = re.match(r'^### (P\d+|M\d+):', line)
            if m:
                current_pid = m.group(1)
                result[current_pid] = {}
                continue

            if current_pid is None:
                continue

            # End of block: any ## heading or horizontal rule
            if re.match(r'^#{2} ', line) or line.strip() == "---":
                current_pid = None
                continue

            if not line.startswith("- "):
                continue

            content = line[2:].strip()

            def _extract(pattern: str, text: str) -> str:
                m2 = re.search(pattern, text, re.IGNORECASE)
                return m2.group(1).strip() if m2 else ""

            if content.startswith("**Function:**"):
                result[current_pid]["function"] = _extract(
                    r'\*\*Function:\*\*\s*(.+)', content
                )
            elif "**Entry:**" in content:
                # Entry/Exit/Success are on the same line
                result[current_pid]["entry"] = _extract(
                    r'\*\*Entry:\*\*\s*([^.]+?)\.?\s*\*\*', content
                )
                result[current_pid]["exit"] = _extract(
                    r'\*\*Exit:\*\*\s*([^.]+?)\.?\s*\*\*', content
                )
                result[current_pid]["success"] = _extract(
                    r'\*\*Success:\*\*\s*(.+)', content
                )
            elif content.startswith("**Use when:**") or content.startswith("**Use If:**"):
                result[current_pid]["use_when"] = _extract(
                    r'\*\*Use[^:]*:\*\*\s*(.+)', content
                )
            elif re.match(r'\*\*Skip', content):
                result[current_pid]["skip_when"] = _extract(
                    r'\*\*Skip[^:]*:\*\*\s*(.+)', content
                )

        return result

    def _parse_compatibility_matrix(self, lines: List[str]) -> Dict[str, Dict]:
        """
        Parse the '## 2.3 Phase-Technique Compatibility Matrix' table.
        Row format: | P1 Context + Safety | INDU-03, ... | INDU-04, ... |
        """
        result: Dict[str, Dict] = {}
        in_matrix = False

        for line in lines:
            if "Phase-Technique Compatibility Matrix" in line:
                in_matrix = True
                continue
            if in_matrix and line.strip() == "---":
                break
            if not in_matrix:
                continue
            # Skip header and separator rows
            if re.match(r'^\| Phase', line) or re.match(r'^\|[-| ]+\|', line):
                continue

            if line.startswith("|"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) < 3:
                    continue
                pid = parts[0].split()[0]  # "P1 Context + Safety" → "P1"
                if not re.match(r'^[PM]\d+$', pid):
                    continue
                result[pid] = {
                    "primary":   _parse_tech_list(parts[1]),
                    "secondary": _parse_tech_list(parts[2]),
                }

        return result


def load_taxonomy(taxonomy_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load taxonomy from hypnosis_taxonomy.md.
    Drop-in replacement for the old JSON loader in phase_chat_generator.py.

    If taxonomy_path points to a .json file, falls back to JSON loading
    (backwards compatibility for any external callers with an explicit path).
    """
    if taxonomy_path is not None:
        p = Path(taxonomy_path)
        if p.suffix == ".json":
            import json
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        md_path = p
    else:
        md_path = Path(__file__).resolve().parent / "hypnosis_taxonomy.md"

    if not md_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {md_path}")

    return TaxonomyReader(md_path).load()
