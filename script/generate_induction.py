#!/usr/bin/env python3
"""Generate hypnotic induction scripts using Grok."""
import sys
import json
import argparse
from pathlib import Path
from grok_client import GrokClient


def load_prompt_template(template_path: str) -> str:
    """Load prompt template from file."""
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_induction(
    client: GrokClient,
    tone: str,
    theme: str,
    duration: str = "60-90 seconds",
    template_path: str = "prompts/induction_v2.txt",
    temperature: float = 0.8
) -> str:
    """Generate induction script.

    Args:
        client: GrokClient instance
        tone: Tone descriptor (e.g., "authoritative", "gentle")
        theme: Theme descriptor (e.g., "deep relaxation", "obedience")
        template_path: Path to prompt template
        temperature: Sampling temperature

    Returns:
        Generated induction text
    """
    # Load template
    prompt_template = load_prompt_template(template_path)

    # Substitute placeholders
    prompt = prompt_template.replace('{TONE}', tone).replace('{THEME}', theme).replace('{DURATION}', duration)

    print(f"[info] Generating induction: tone={tone}, theme={theme}", file=sys.stderr)

    # Generate
    # Calculate approximate max_tokens needed based on duration
    # Rough heuristic: 1.5 tokens per word, add 20% buffer
    if 'word' in duration.lower():
        # Parse word count from duration string
        import re
        match = re.search(r'(\d+)\s*word', duration.lower())
        if match:
            word_count = int(match.group(1))
            estimated_tokens = int(word_count * 1.5 * 1.2)
        else:
            estimated_tokens = 2000  # Default for long form
    elif 'minute' in duration.lower():
        # Parse minutes
        import re
        match = re.search(r'(\d+)\s*minute', duration.lower())
        if match:
            minutes = int(match.group(1))
            # ~150 words/min spoken, 1.5 tokens/word
            estimated_tokens = int(minutes * 150 * 1.5 * 1.2)
        else:
            estimated_tokens = 2000
    else:
        estimated_tokens = 800  # Default for short form

    # Cap at 4000 for safety
    max_tokens = min(estimated_tokens, 4000)

    print(f"[info] Using max_tokens={max_tokens} for target duration", file=sys.stderr)

    response = client.generate(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )

    return response.strip()


def main():
    """CLI for induction generation."""
    parser = argparse.ArgumentParser(description="Generate hypnotic induction scripts")

    parser.add_argument('--tone', type=str, required=True, help='Tone (e.g., authoritative, gentle, seductive)')
    parser.add_argument('--theme', type=str, required=True, help='Theme (e.g., deep relaxation, obedience, focus)')
    parser.add_argument('--duration', type=str, default='60-90 seconds', help='Target duration (default: 60-90 seconds)')
    parser.add_argument('--template', type=str, default='prompts/induction_v2.txt', help='Prompt template path')
    parser.add_argument('--output', type=str, help='Output file (default: stdout)')
    parser.add_argument('--temperature', type=float, default=0.8, help='Temperature (default: 0.8)')
    parser.add_argument('--count', type=int, default=1, help='Number of variations to generate')

    args = parser.parse_args()

    client = GrokClient()

    results = []

    for i in range(args.count):
        print(f"\n[info] Generating variation {i+1}/{args.count}...", file=sys.stderr)

        induction = generate_induction(
            client=client,
            tone=args.tone,
            theme=args.theme,
            duration=args.duration,
            template_path=args.template,
            temperature=args.temperature
        )

        result = {
            "tone": args.tone,
            "theme": args.theme,
            "text": induction,
            "word_count": len(induction.split()),
            "char_count": len(induction)
        }

        results.append(result)

        # Estimate speaking time (avg 150 words/min)
        speaking_time = result['word_count'] / 150 * 60
        print(f"[info] Generated {result['word_count']} words (~{speaking_time:.0f}s spoken)", file=sys.stderr)

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.count == 1:
                # Single output: just the text
                f.write(results[0]['text'])
            else:
                # Multiple: JSON array
                json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n[ok] Saved to {args.output}", file=sys.stderr)
    else:
        # Print to stdout
        if args.count == 1:
            print(results[0]['text'])
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
