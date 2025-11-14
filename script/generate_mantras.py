#!/usr/bin/env python3
"""Generate mantra collections using Grok."""
import sys
import json
import argparse
from pathlib import Path
from grok_client import GrokClient
from template_converter import TemplateConverter


def load_prompt_template(template_path: str) -> str:
    """Load prompt template from file."""
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_mantras(
    client: GrokClient,
    theme: str,
    tone: str = "commanding",
    count: int = 10,
    template_path: str = "script/prompts/mantra_v1.txt",
    temperature: float = 0.9
) -> list:
    """Generate mantras for a theme.

    Args:
        client: GrokClient instance
        theme: Theme descriptor
        tone: Tone descriptor
        count: Number of mantras to generate
        template_path: Path to prompt template
        temperature: Sampling temperature (higher = more variety)

    Returns:
        List of mantra dicts
    """
    # Load template
    prompt_template = load_prompt_template(template_path)

    # Substitute placeholders
    prompt = (prompt_template
              .replace('{THEME}', theme)
              .replace('{TONE}', tone)
              .replace('{COUNT}', str(count)))

    print(f"[info] Generating {count} mantras: theme={theme}, tone={tone}", file=sys.stderr)

    # Generate
    response = client.generate(
        prompt=prompt,
        temperature=temperature,
        max_tokens=800
    )

    # Parse JSON
    try:
        # Clean up response
        json_text = response.strip()

        # Remove markdown code blocks if present
        if '```json' in json_text:
            json_text = json_text.split('```json')[1].split('```')[0].strip()
        elif '```' in json_text:
            json_text = json_text.split('```')[1].split('```')[0].strip()

        mantras = json.loads(json_text)

        # Add theme metadata
        for mantra in mantras:
            mantra['theme'] = theme
            mantra['tone'] = tone

        return mantras

    except json.JSONDecodeError as e:
        print(f"[error] Failed to parse JSON response: {e}", file=sys.stderr)
        print(f"[error] Raw response: {response[:200]}...", file=sys.stderr)
        return []


def main():
    """CLI for mantra generation."""
    parser = argparse.ArgumentParser(description="Generate hypnotic mantras")

    parser.add_argument('--theme', type=str, required=True, help='Theme (e.g., obedience, relaxation, focus)')
    parser.add_argument('--tone', type=str, default='commanding', help='Tone (default: commanding)')
    parser.add_argument('--count', type=int, default=10, help='Number of mantras (default: 10)')
    parser.add_argument('--template', type=str, default='script/prompts/mantra_v1.txt', help='Prompt template')
    parser.add_argument('--output', type=str, help='Output JSON file')
    parser.add_argument('--convert', action='store_true', help='Also convert to template format')
    parser.add_argument('--temperature', type=float, default=0.9, help='Temperature (default: 0.9)')

    args = parser.parse_args()

    client = GrokClient()

    # Generate mantras
    mantras = generate_mantras(
        client=client,
        theme=args.theme,
        tone=args.tone,
        count=args.count,
        template_path=args.template,
        temperature=args.temperature
    )

    if not mantras:
        print("[error] No mantras generated", file=sys.stderr)
        sys.exit(1)

    print(f"[ok] Generated {len(mantras)} mantras", file=sys.stderr)

    # Convert to templates if requested
    if args.convert:
        print("[info] Converting to template format...", file=sys.stderr)
        converter = TemplateConverter()

        for mantra in mantras:
            template, warnings = converter.convert_line(mantra['line'])
            mantra['template'] = template.strip()

            if warnings:
                print(f"[warn] {mantra['line'][:50]}... - {len(warnings)} warnings", file=sys.stderr)

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(mantras, f, indent=2, ensure_ascii=False)
        print(f"[ok] Saved to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(mantras, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
