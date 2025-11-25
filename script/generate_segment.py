#!/usr/bin/env python3
"""Generate hypnotic script segments.

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
from typing import Optional

from openai import OpenAI
import llm_client


# Segment type configuration
# Template files are automatically resolved from segment type:
# segment_type -> prompts/{segment_type}.txt
SEGMENT_CONFIG = {
    'pretalk': {
        'default_duration': '60-90 seconds',
        'description': 'Pre-session framing and expectation setting'
    },
    'induction': {
        'default_duration': '60-90 seconds',
        'description': 'Initial trance induction'
    },
    'deepener': {
        'default_duration': '15-45 seconds',
        'description': 'Trance deepening segment'
    },
    'conditioning': {
        'default_duration': '30-120 seconds',
        'description': 'Belief and behavior conditioning'
    },
    'fractionation': {
        'default_duration': '30-90 seconds',
        'description': 'Up/down trance cycles'
    },
    'posthypnotic': {
        'default_duration': '20-60 seconds',
        'description': 'Post-trance triggers and suggestions'
    },
    'wakener': {
        'default_duration': '15-30 seconds',
        'description': 'Safe emergence from trance'
    },
    'mantra': {
        'default_duration': '30-60 seconds',
        'description': 'Repetitive affirmation generation'
    }
}


def load_prompt_template(template_path: str) -> str:
    """Load prompt template from file."""
    # Resolve path relative to script directory
    script_dir = Path(__file__).parent
    full_path = script_dir / template_path
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


def normalize_duration(duration: str) -> tuple:
    """Normalize duration string to total seconds and human-readable format.

    Args:
        duration: Duration string (e.g., "60-90 seconds", "3 minutes", "500 words")

    Returns:
        tuple: (total_seconds: int, normalized_str: str, estimated_words: int)
        Example: (180, "3 minutes (approx 450 words)", 450)
    """
    import re

    total_seconds = 0
    estimated_words = 0

    # Parse word count if specified
    if 'word' in duration.lower():
        match = re.search(r'(\d+)\s*word', duration.lower())
        if match:
            estimated_words = int(match.group(1))
            # ~150 words/min spoken
            total_seconds = int((estimated_words / 150) * 60)
            return (total_seconds, f"{estimated_words} words (approx {total_seconds}s)", estimated_words)

    # Parse minutes
    elif 'minute' in duration.lower():
        match = re.search(r'(\d+)\s*minute', duration.lower())
        if match:
            minutes = int(match.group(1))
            total_seconds = minutes * 60
            estimated_words = minutes * 150
            return (total_seconds, f"{minutes} minute{'s' if minutes != 1 else ''} (approx {estimated_words} words)", estimated_words)

    # Parse seconds (handle ranges like "60-90 seconds")
    elif 'second' in duration.lower():
        # Extract the larger number if it's a range
        match = re.search(r'(\d+)\s*(?:-\s*(\d+))?\s*second', duration.lower())
        if match:
            seconds = int(match.group(2) if match.group(2) else match.group(1))
            total_seconds = seconds
            estimated_words = int((seconds / 60) * 150)

            # Format as minutes + seconds if >= 60s
            if total_seconds >= 60:
                mins = total_seconds // 60
                secs = total_seconds % 60
                if secs > 0:
                    time_str = f"{mins}m {secs}s"
                else:
                    time_str = f"{mins} minute{'s' if mins != 1 else ''}"
            else:
                time_str = f"{total_seconds} seconds"

            return (total_seconds, f"{time_str} (approx {estimated_words} words)", estimated_words)

    # Default for unspecified (90 seconds)
    return (90, "90 seconds (approx 225 words)", 225)


def calculate_max_tokens(duration: str) -> int:
    """Calculate appropriate max_tokens based on target duration.

    Note: max_tokens is for COMPLETION only (prompt tokens don't count).
    Uses modest buffer to prevent truncation while avoiding waste.

    Args:
        duration: Duration string (e.g., "60-90 seconds", "3 minutes", "500 words")

    Returns:
        Estimated max_tokens needed with buffer
    """
    _, _, estimated_words = normalize_duration(duration)

    # Generous calculation for completion tokens:
    # - 1.5 tokens per word (baseline)
    # - 100% buffer (2x headroom)
    #
    # Rationale: Grok is extremely cheap (~$0.06 for dozens of scripts)
    # Better to over-allocate than risk truncation ruining a script
    #
    # Future: Detect truncation and auto-retry (see Issue #X)
    tokens = int(estimated_words * 1.5 * 2.0)

    # Cap at 4000 for safety (model limits)
    return min(tokens, 4000)


def generate_segment(
    segment_type: str,
    tone: str,
    instructions: str,
    duration: str = None,
    context: str = None,
    template_path: str = None,
    temperature: float = 0.8,
    global_instructions: str = None,
    client: Optional[OpenAI] = None,
    model: Optional[str] = None
) -> str:
    """Generate hypnotic script segment.

    Args:
        segment_type: Type of segment (pretalk, induction, deepener, etc.)
        tone: Tone descriptor (e.g., "authoritative", "gentle")
        instructions: Specific instructions for what to generate (e.g., "progressive relaxation", "JOI call/response")
        duration: Target duration (defaults to segment-specific default)
        context: Optional context from previous segments (future use)
        template_path: Path to prompt template (defaults to segment default)
        temperature: Sampling temperature
        global_instructions: Optional global instructions prepended to all segments
        client: Optional OpenAI client (uses llm_client.get_client() if not provided)
        model: Optional model override

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
        # Convention-based template resolution: segment_type -> prompts/{segment_type}.txt
        template_path = f'prompts/{segment_type}.txt'

    # Normalize duration for better model guidance
    total_seconds, normalized_duration, estimated_words = normalize_duration(duration)

    # Load template
    prompt_template = load_prompt_template(template_path)

    # Combine global and segment-specific instructions
    # Global instructions are ALWAYS prepended to ensure consistency across all segments
    combined_instructions = instructions
    if global_instructions:
        combined_instructions = f"{global_instructions}\n\nSegment-specific additions: {instructions}"

    # Substitute placeholders with normalized, readable format
    prompt = (prompt_template
              .replace('{TONE}', tone)
              .replace('{INSTRUCTIONS}', combined_instructions)
              .replace('{DURATION}', normalized_duration))

    # Add context if provided (for session continuity)
    if context:
        context_instructions = """PREVIOUS SEGMENTS (for continuity reference):
---
{context}
---

CONTINUITY RULES:
1. REPEAT anchor words and trigger phrases that were explicitly established (FOCUS, BLISS, DROP, surrender, etc.) - repetition reinforces conditioning
2. CALLBACK to themes and imagery from previous segments to create cohesion
3. VARY your opening lines - do NOT start with the same words/images as previous segments
4. VARY incidental metaphors - if previous segments used "sunlight" or "waves" heavily but not as anchors, use different imagery
5. Maintain the emotional arc while keeping language fresh

The goal: intentional repetition of anchors/triggers = good; accidental repetition of openings/imagery = bad.

""".format(context=context)
        prompt = context_instructions + prompt

    print(f"[info] Generating {segment_type}: tone={tone}, instructions={instructions}, duration={normalized_duration}", file=sys.stderr)

    # Calculate appropriate max_tokens with conservative buffer
    max_tokens = calculate_max_tokens(duration)
    print(f"[info] Using max_tokens={max_tokens} (target: {estimated_words} words, {total_seconds}s spoken)", file=sys.stderr)

    # Generate using llm_client
    response = llm_client.generate(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        client=client,
        model=model
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
  python generate_segment.py --type induction --tone "gentle" --instructions "progressive relaxation, body scan" --duration "90 seconds"
  python generate_segment.py --type deepener --tone "commanding" --instructions "countdown 10 to 1, deeper with each number" --duration "30 seconds"
  python generate_segment.py --type wakener --tone "caring" --instructions "gentle awakening, refreshed and alert" --output wakener.txt
"""
    )

    parser.add_argument('--type', type=str, required=True,
                       choices=list(SEGMENT_CONFIG.keys()),
                       help='Segment type')
    parser.add_argument('--tone', type=str, required=True,
                       help='Tone (e.g., authoritative, gentle, seductive)')
    parser.add_argument('--instructions', type=str, required=True,
                       help='Specific instructions (e.g., progressive relaxation, JOI call/response)')
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

    # Get client once for all generations
    client, model = llm_client.get_client()

    results = []

    for i in range(args.count):
        if args.count > 1:
            print(f"\n[info] Generating variation {i+1}/{args.count}...", file=sys.stderr)

        segment_text = generate_segment(
            segment_type=args.type,
            tone=args.tone,
            instructions=args.instructions,
            duration=args.duration,
            context=args.context,
            template_path=args.template,
            temperature=args.temperature,
            client=client,
            model=model
        )

        # Build result with metadata
        result = {
            "segment_type": args.type,
            "tone": args.tone,
            "instructions": args.instructions,
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
