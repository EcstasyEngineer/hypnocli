#!/usr/bin/env python3
"""Generate hypnotic script segments using Grok.

Unified generator for all segment types: pretalk, induction, deepener,
conditioning, fractionation, posthypnotic, wakener.

Usage:
    python generate_segment.py --type induction --tone "gentle" --theme "relaxation" --duration "90 seconds"
    python generate_segment.py --type deepener --tone "authoritative" --theme "obedience" --duration "30 seconds"
"""
import sys
import json
import argparse
from pathlib import Path
from grok_client import GrokClient


# Segment type configuration
SEGMENT_CONFIG = {
    'pretalk': {
        'template': 'prompts/pretalk_v1.txt',
        'default_duration': '60-90 seconds',
        'description': 'Pre-session framing and expectation setting'
    },
    'induction': {
        'template': 'prompts/induction_v2.txt',
        'default_duration': '60-90 seconds',
        'description': 'Initial trance induction'
    },
    'deepener': {
        'template': 'prompts/deepener_v1.txt',
        'default_duration': '15-45 seconds',
        'description': 'Trance deepening segment'
    },
    'conditioning': {
        'template': 'prompts/conditioning_v1.txt',
        'default_duration': '30-120 seconds',
        'description': 'Belief and behavior conditioning'
    },
    'fractionation': {
        'template': 'prompts/fractionation_v1.txt',
        'default_duration': '30-90 seconds',
        'description': 'Up/down trance cycles'
    },
    'posthypnotic': {
        'template': 'prompts/posthypnotic_v1.txt',
        'default_duration': '20-60 seconds',
        'description': 'Post-trance triggers and suggestions'
    },
    'wakener': {
        'template': 'prompts/wakener_v1.txt',
        'default_duration': '15-30 seconds',
        'description': 'Safe emergence from trance'
    }
}


def load_prompt_template(template_path: str) -> str:
    """Load prompt template from file."""
    # Resolve path relative to script directory
    script_dir = Path(__file__).parent
    full_path = script_dir / template_path
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


def calculate_max_tokens(duration: str) -> int:
    """Calculate appropriate max_tokens based on target duration.

    Args:
        duration: Duration string (e.g., "60-90 seconds", "3 minutes", "500 words")

    Returns:
        Estimated max_tokens needed
    """
    import re

    # Parse word count if specified
    if 'word' in duration.lower():
        match = re.search(r'(\d+)\s*word', duration.lower())
        if match:
            word_count = int(match.group(1))
            # 1.5 tokens per word, add 20% buffer
            return int(word_count * 1.5 * 1.2)

    # Parse minutes
    elif 'minute' in duration.lower():
        match = re.search(r'(\d+)\s*minute', duration.lower())
        if match:
            minutes = int(match.group(1))
            # ~150 words/min spoken, 1.5 tokens/word, 20% buffer
            return int(minutes * 150 * 1.5 * 1.2)

    # Parse seconds (handle ranges like "60-90 seconds")
    elif 'second' in duration.lower():
        # Extract the larger number if it's a range
        match = re.search(r'(\d+)\s*(?:-\s*(\d+))?\s*second', duration.lower())
        if match:
            seconds = int(match.group(2) if match.group(2) else match.group(1))
            # Convert to minutes and calculate
            minutes = seconds / 60
            return int(minutes * 150 * 1.5 * 1.2)

    # Default for unspecified
    return 800


def generate_segment(
    client: GrokClient,
    segment_type: str,
    tone: str,
    theme: str,
    duration: str = None,
    context: str = None,
    template_path: str = None,
    temperature: float = 0.8
) -> str:
    """Generate hypnotic script segment.

    Args:
        client: GrokClient instance
        segment_type: Type of segment (pretalk, induction, deepener, etc.)
        tone: Tone descriptor (e.g., "authoritative", "gentle")
        theme: Theme descriptor (e.g., "deep relaxation", "obedience")
        duration: Target duration (defaults to segment-specific default)
        context: Optional context from previous segments (future use)
        template_path: Path to prompt template (defaults to segment default)
        temperature: Sampling temperature

    Returns:
        Generated segment text
    """
    # Validate segment type
    if segment_type not in SEGMENT_CONFIG:
        raise ValueError(f"Unknown segment type: {segment_type}. Valid types: {list(SEGMENT_CONFIG.keys())}")

    # Get segment config
    config = SEGMENT_CONFIG[segment_type]

    # Set defaults
    if duration is None:
        duration = config['default_duration']
    if template_path is None:
        template_path = config['template']

    # Load template
    prompt_template = load_prompt_template(template_path)

    # Substitute placeholders
    prompt = (prompt_template
              .replace('{TONE}', tone)
              .replace('{THEME}', theme)
              .replace('{DURATION}', duration))

    # Add context if provided (future-proofing for session composition)
    if context:
        prompt = f"Previous context:\n{context}\n\n{prompt}"

    print(f"[info] Generating {segment_type}: tone={tone}, theme={theme}, duration={duration}", file=sys.stderr)

    # Calculate appropriate max_tokens
    max_tokens = min(calculate_max_tokens(duration), 4000)
    print(f"[info] Using max_tokens={max_tokens} for target duration", file=sys.stderr)

    # Generate
    response = client.generate(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )

    return response.strip()


def main():
    """CLI for segment generation."""
    parser = argparse.ArgumentParser(
        description="Generate hypnotic script segments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Segment types:
{chr(10).join(f"  {name:15} - {config['description']}" for name, config in SEGMENT_CONFIG.items())}

Examples:
  python generate_segment.py --type induction --tone "gentle" --theme "relaxation" --duration "90 seconds"
  python generate_segment.py --type deepener --tone "commanding" --theme "obedience" --duration "30 seconds"
  python generate_segment.py --type wakener --tone "caring" --theme "refreshment" --output wakener.txt
"""
    )

    parser.add_argument('--type', type=str, required=True,
                       choices=list(SEGMENT_CONFIG.keys()),
                       help='Segment type')
    parser.add_argument('--tone', type=str, required=True,
                       help='Tone (e.g., authoritative, gentle, seductive)')
    parser.add_argument('--theme', type=str, required=True,
                       help='Theme (e.g., deep relaxation, obedience, focus)')
    parser.add_argument('--duration', type=str,
                       help='Target duration (defaults to segment-specific default)')
    parser.add_argument('--context', type=str,
                       help='Optional context from previous segments (future use)')
    parser.add_argument('--template', type=str,
                       help='Custom prompt template path (overrides default)')
    parser.add_argument('--output', type=str,
                       help='Output file (default: stdout)')
    parser.add_argument('--temperature', type=float, default=0.8,
                       help='Temperature (default: 0.8)')
    parser.add_argument('--count', type=int, default=1,
                       help='Number of variations to generate')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON with metadata (always used for multiple variations)')

    args = parser.parse_args()

    client = GrokClient()

    results = []

    for i in range(args.count):
        if args.count > 1:
            print(f"\n[info] Generating variation {i+1}/{args.count}...", file=sys.stderr)

        segment_text = generate_segment(
            client=client,
            segment_type=args.type,
            tone=args.tone,
            theme=args.theme,
            duration=args.duration,
            context=args.context,
            template_path=args.template,
            temperature=args.temperature
        )

        # Build result with metadata
        result = {
            "segment_type": args.type,
            "tone": args.tone,
            "theme": args.theme,
            "duration_target": args.duration or SEGMENT_CONFIG[args.type]['default_duration'],
            "text": segment_text,
            "word_count": len(segment_text.split()),
            "char_count": len(segment_text)
        }

        # Calculate estimated speaking time (avg 150 words/min)
        speaking_time_seconds = result['word_count'] / 150 * 60
        result["duration_actual"] = f"~{speaking_time_seconds:.0f} seconds"

        results.append(result)

        print(f"[info] Generated {result['word_count']} words (~{speaking_time_seconds:.0f}s spoken)", file=sys.stderr)

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.count == 1 and not args.json:
                # Single output without JSON flag: just the text
                f.write(results[0]['text'])
            else:
                # Multiple variations or JSON flag: structured output
                output_data = results if args.count > 1 else results[0]
                json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n[ok] Saved to {args.output}", file=sys.stderr)
    else:
        # Print to stdout
        if args.count == 1 and not args.json:
            print(results[0]['text'])
        else:
            output_data = results if args.count > 1 else results[0]
            print(json.dumps(output_data, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
