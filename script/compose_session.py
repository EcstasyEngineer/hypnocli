#!/usr/bin/env python3
"""Compose complete hypnosis sessions with contextual continuity.

Generates multi-segment sessions where each segment is aware of previous
content, creating thematic consistency and smooth transitions.

Usage:
    python compose_session.py \\
        --tone "authoritative" \\
        --theme "obedience" \\
        --structure "pretalk,induction,deepener,conditioning,posthypnotic,wakener" \\
        --output session.txt
"""
import sys
import json
import argparse
from pathlib import Path
from generate_segment import generate_segment, SEGMENT_CONFIG
from grok_client import GrokClient


def compose_session(
    client: GrokClient,
    tone: str,
    theme: str,
    structure: list,
    context_mode: str = "full",
    temperature: float = 0.8,
    segment_durations: dict = None
) -> dict:
    """Compose a complete hypnosis session with contextual awareness.

    Args:
        client: GrokClient instance
        tone: Overall tone for the session
        theme: Overall theme for the session
        structure: List of segment types in order
        context_mode: How to pass context between segments
            - "none": No context passing (independent segments)
            - "last": Pass only the previous segment
            - "full": Pass all previous segments (default)
            - "summary": Pass AI-generated summary of previous segments
        temperature: Sampling temperature
        segment_durations: Optional dict mapping segment_type to custom duration

    Returns:
        Dict with session metadata and segments
    """
    segments = []
    context = None
    segment_durations = segment_durations or {}

    print(f"\n[info] Composing session: {len(structure)} segments", file=sys.stderr)
    print(f"[info] Tone: {tone}", file=sys.stderr)
    print(f"[info] Theme: {theme}", file=sys.stderr)
    print(f"[info] Context mode: {context_mode}", file=sys.stderr)
    print(f"[info] Structure: {' → '.join(structure)}\n", file=sys.stderr)

    for i, segment_type in enumerate(structure):
        segment_num = i + 1
        print(f"[{segment_num}/{len(structure)}] Generating {segment_type}...", file=sys.stderr)

        # Get custom duration or use default
        duration = segment_durations.get(segment_type)

        # Generate segment with context
        segment_text = generate_segment(
            client=client,
            segment_type=segment_type,
            tone=tone,
            theme=theme,
            duration=duration,
            context=context,
            temperature=temperature
        )

        # Store segment with metadata
        segment_data = {
            "type": segment_type,
            "position": segment_num,
            "text": segment_text,
            "word_count": len(segment_text.split()),
            "char_count": len(segment_text)
        }
        segments.append(segment_data)

        # Calculate speaking time
        speaking_time = segment_data['word_count'] / 150 * 60
        print(f"[ok] Generated {segment_data['word_count']} words (~{speaking_time:.0f}s)\n", file=sys.stderr)

        # Update context for next segment based on mode
        if context_mode == "full":
            # Pass all previous segments
            context = "\n\n".join(s['text'] for s in segments)
        elif context_mode == "last":
            # Pass only the previous segment
            context = segment_text
        elif context_mode == "summary":
            # Generate AI summary of previous content (future enhancement)
            # For now, just use last segment
            context = segment_text
        # else: context_mode == "none", keep context = None

    # Calculate total session stats
    total_words = sum(s['word_count'] for s in segments)
    total_speaking_time = total_words / 150 * 60

    session = {
        "tone": tone,
        "theme": theme,
        "structure": structure,
        "context_mode": context_mode,
        "total_segments": len(segments),
        "total_words": total_words,
        "total_duration": f"~{total_speaking_time:.0f} seconds (~{total_speaking_time/60:.1f} minutes)",
        "segments": segments
    }

    return session


def main():
    """CLI for session composition."""
    parser = argparse.ArgumentParser(
        description="Compose complete hypnosis sessions with contextual continuity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available segment types:
{chr(10).join(f"  {name:15} - {config['description']}" for name, config in SEGMENT_CONFIG.items())}

Context modes:
  none      - No context passing (independent segments)
  last      - Pass only the previous segment
  full      - Pass all previous segments (default, best continuity)
  summary   - Pass AI summary of previous segments (future)

Examples:
  # Full session with contextual awareness
  python compose_session.py \\
    --tone "authoritative" \\
    --theme "obedience" \\
    --structure "pretalk,induction,deepener,conditioning,posthypnotic,wakener"

  # Short relaxation session
  python compose_session.py \\
    --tone "gentle and soothing" \\
    --theme "deep relaxation" \\
    --structure "induction,deepener,wakener" \\
    --output relaxation_session.txt

  # Long session with custom durations
  python compose_session.py \\
    --tone "commanding" \\
    --theme "total surrender" \\
    --structure "pretalk,induction,deepener,conditioning,deepener,fractionation,posthypnotic,wakener" \\
    --duration-induction "5 minutes" \\
    --duration-conditioning "2 minutes" \\
    --output long_session.txt

  # No context mode (comparison baseline)
  python compose_session.py \\
    --tone "authoritative" \\
    --theme "obedience" \\
    --structure "induction,deepener,wakener" \\
    --context none \\
    --output no_context_session.txt
"""
    )

    parser.add_argument('--tone', type=str, required=True,
                       help='Overall tone for the session')
    parser.add_argument('--theme', type=str, required=True,
                       help='Overall theme for the session')
    parser.add_argument('--structure', type=str, required=True,
                       help='Comma-separated list of segment types')
    parser.add_argument('--context', type=str, default='full',
                       choices=['none', 'last', 'full', 'summary'],
                       help='Context passing mode (default: full)')
    parser.add_argument('--output', type=str,
                       help='Output file (default: stdout)')
    parser.add_argument('--temperature', type=float, default=0.8,
                       help='Temperature (default: 0.8)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON with metadata')

    # Dynamic duration arguments for each segment type
    for segment_type in SEGMENT_CONFIG.keys():
        parser.add_argument(f'--duration-{segment_type}', type=str,
                           help=f'Custom duration for {segment_type} segments')

    args = parser.parse_args()

    # Parse structure
    structure = [s.strip() for s in args.structure.split(',')]

    # Validate segment types
    invalid_types = [s for s in structure if s not in SEGMENT_CONFIG]
    if invalid_types:
        print(f"[error] Invalid segment types: {', '.join(invalid_types)}", file=sys.stderr)
        print(f"[error] Valid types: {', '.join(SEGMENT_CONFIG.keys())}", file=sys.stderr)
        sys.exit(1)

    # Build custom durations dict
    segment_durations = {}
    for segment_type in SEGMENT_CONFIG.keys():
        duration_arg = getattr(args, f'duration_{segment_type}', None)
        if duration_arg:
            segment_durations[segment_type] = duration_arg

    # Initialize client
    client = GrokClient()

    # Compose session
    session = compose_session(
        client=client,
        tone=args.tone,
        theme=args.theme,
        structure=structure,
        context_mode=args.context,
        temperature=args.temperature,
        segment_durations=segment_durations
    )

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.json:
                # Full JSON output with metadata
                json.dump(session, f, indent=2, ensure_ascii=False)
            else:
                # Plain text: just the segments
                for segment in session['segments']:
                    f.write(f"## {segment['type'].upper()}\n\n")
                    f.write(segment['text'])
                    f.write("\n\n---\n\n")

        print(f"\n[ok] Session saved to {args.output}", file=sys.stderr)
        print(f"[ok] Total: {session['total_words']} words, {session['total_duration']}", file=sys.stderr)
    else:
        # Print to stdout
        if args.json:
            print(json.dumps(session, indent=2, ensure_ascii=False))
        else:
            for segment in session['segments']:
                print(f"## {segment['type'].upper()}\n")
                print(segment['text'])
                print("\n---\n")


if __name__ == '__main__':
    main()
