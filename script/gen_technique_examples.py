#!/usr/bin/env python3
"""
gen_technique_examples.py
--------------------------
Generate good/bad examples for all hypnosis techniques using Gemini Flash.
Merges output into technique_examples.json, skipping techniques that already
have entries. Safe to re-run.

Usage:
    python3 gen_technique_examples.py [--dry-run] [--category CAT]
"""

import json
import os
import re
import sys
import time
import argparse
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from google import genai
from google.genai import types

SCRIPT_DIR = Path(__file__).parent
TAXONOMY_MD = SCRIPT_DIR / 'hypnosis_taxonomy.md'
EXAMPLES_JSON = SCRIPT_DIR / 'technique_examples.json'

MODEL = 'gemini-2.5-flash'
_client = None

def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    return _client

SYSTEM_PROMPT = """You are a reference writer for an adult erotic hypnosis script generation system.

Context:
- Consensual adult erotic hypnosis. Listeners are willing subjects.
- Primary aesthetic: "toymaker / mindless puppet" — listeners transform into obedient, pleasure-focused dolls/toys. Control feels like relief and warmth, not violence or aggression.
- Style is warm-authoritative. Permissive language ("allow yourself", "no need to") unless the specific technique is explicitly authoritarian.
- Content can and should be sexually explicit where relevant — arousal, desire, pleasure conditioning, ownership, submission are all on the table.
- Examples are actual spoken script text, first-person voice of the hypnotist.

For each technique you're given, produce JSON with exactly these fields:
  "name": string — technique name (provided to you, repeat it verbatim)
  "theme_notes": string — 1-3 sentences: how this technique manifests in the toymaker/puppet aesthetic and when to reach for it
  "good_examples": array of 3 strings — actual script excerpts (2-5 sentences each), effective use of the technique
  "bad_examples": array of 2 strings — actual script excerpts showing common mistakes
  "bad_notes": string — what specifically fails in the bad examples (can address both at once)

Output ONLY a valid JSON object keyed by technique ID. No commentary, no markdown fences, no explanation."""


def parse_taxonomy():
    """Extract all technique definitions from the markdown."""
    md = TAXONOMY_MD.read_text()
    # Find category blocks
    cat_pattern = re.compile(
        r'### Category (\w+): (.+?)\n\*Purpose: (.+?)\*.*?\n\n\|.*?\|\n\|[-| ]+\|\n(.*?)(?=\n---|\Z)',
        re.DOTALL
    )
    row_pattern = re.compile(r'\|\s*([\w-]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|')

    categories = {}
    for m in cat_pattern.finditer(md):
        cat_id = m.group(1)
        cat_name = m.group(2).strip()
        cat_purpose = m.group(3).strip()
        table_body = m.group(4)
        techniques = {}
        for row in row_pattern.finditer(table_body):
            tid = row.group(1).strip()
            tname = row.group(2).strip()
            tdesc = row.group(3).strip()
            # Clean markdown bold/italic from description
            tdesc = re.sub(r'\*\*(.+?)\*\*', r'\1', tdesc)
            techniques[tid] = {'name': tname, 'description': tdesc}
        if techniques:
            categories[cat_id] = {
                'name': cat_name,
                'purpose': cat_purpose,
                'techniques': techniques,
            }
    return categories


def build_prompt(category_id, category_info, missing_ids):
    """Build the user prompt for one category batch."""
    cat = category_info
    lines = [
        f"Category: {category_id} — {cat['name']}",
        f"Purpose: {cat['purpose']}",
        "",
        "Techniques to cover:",
    ]
    for tid in missing_ids:
        t = cat['techniques'][tid]
        lines.append(f"  {tid} | {t['name']} | {t['description']}")

    lines += [
        "",
        "Generate examples for EACH technique listed above.",
        "Output a single JSON object keyed by technique ID.",
    ]
    return '\n'.join(lines)


def call_gemini(prompt, retries=3):
    client = get_client()
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.9,
                    max_output_tokens=8192,
                    thinking_config=types.ThinkingConfig(thinking_budget=1024),
                )
            )
            text = resp.text.strip()
            # Strip markdown fences if present
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text)
        except Exception as e:
            print(f'  Attempt {attempt+1} failed: {e}', file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Print prompts, do not call API')
    parser.add_argument('--category', help='Only process this category (e.g. PLEA)')
    args = parser.parse_args()

    # Load existing examples
    with open(EXAMPLES_JSON) as f:
        examples = json.load(f)

    covered = {k for k in examples if k != '_meta'}

    categories = parse_taxonomy()

    # Determine what to generate
    work = {}  # cat_id -> [missing_ids]
    for cat_id, cat_info in categories.items():
        if args.category and cat_id != args.category:
            continue
        missing = [tid for tid in cat_info['techniques'] if tid not in covered]
        if missing:
            work[cat_id] = missing

    total_missing = sum(len(v) for v in work.values())
    print(f'Generating examples for {total_missing} techniques across {len(work)} categories...\n')

    for cat_id, missing_ids in work.items():
        cat_info = categories[cat_id]
        print(f'[{cat_id}] {cat_info["name"]} — {len(missing_ids)} techniques: {", ".join(missing_ids)}')

        prompt = build_prompt(cat_id, cat_info, missing_ids)

        if args.dry_run:
            print('  PROMPT:')
            for line in prompt.splitlines():
                print(f'    {line}')
            print()
            continue

        result = call_gemini(prompt)
        if result is None:
            print(f'  ERROR: failed to get response for {cat_id}, skipping')
            continue

        # Merge results
        added = 0
        for tid in missing_ids:
            if tid in result:
                entry = result[tid]
                # Ensure required fields
                if 'good_examples' in entry and 'bad_examples' in entry:
                    examples[tid] = entry
                    added += 1
                else:
                    print(f'  WARNING: {tid} missing required fields, skipping')
            else:
                print(f'  WARNING: {tid} not in response')

        print(f'  Added {added}/{len(missing_ids)} techniques')

        # Save after each category (safe incremental progress)
        with open(EXAMPLES_JSON, 'w') as f:
            json.dump(examples, f, indent=2, ensure_ascii=False)

        time.sleep(1)  # gentle rate limiting

    if not args.dry_run:
        print(f'\nDone. technique_examples.json updated.')


if __name__ == '__main__':
    main()
