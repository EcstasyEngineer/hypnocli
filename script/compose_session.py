#!/usr/bin/env python3
"""Compose complete hypnosis sessions with contextual continuity.

Generates multi-segment sessions where each segment is aware of previous
content, creating thematic consistency and smooth transitions.

Supports both simple CLI mode and advanced JSON configuration for complex sessions.

Usage:
    # Simple CLI mode
    python compose_session.py \\
        --tone "authoritative" \\
        --theme "obedience" \\
        --structure "pretalk,induction,deepener,wakener" \\
        --output session.txt

    # JSON config file mode
    python compose_session.py \\
        --config session_config.json \\
        --output session.txt

    # Inline JSON mode
    python compose_session.py \\
        --json '{"global_tone":"commanding","global_theme":"obedience","segments":[...]}' \\
        --output session.txt
"""
import sys
import json
import argparse
from pathlib import Path
from generate_segment import generate_segment, SEGMENT_CONFIG
from grok_client import GrokClient


def load_session_config(args):
    """Load session config from inline JSON, config file, or CLI args.

    Priority order:
    1. --json (inline JSON string)
    2. --config (JSON file path)
    3. Legacy CLI args (--tone, --theme, --structure)

    Returns:
        dict: Session configuration with structure:
            {
                "global_tone": str,
                "global_theme": str,
                "global_duration": str (optional),
                "context_mode": str (default: "full"),
                "temperature": float (default: 0.8),
                "segments": [
                    {
                        "type": str,
                        "tone": str (optional, overrides global_tone),
                        "theme": str (optional, overrides global_theme),
                        "duration": str (optional, overrides global_duration or type default)
                    },
                    ...
                ]
            }
    """
    # Priority 1: Inline JSON
    if hasattr(args, 'json_inline') and args.json_inline:
        try:
            config = json.loads(args.json_inline)
            print("[info] Loaded config from inline JSON", file=sys.stderr)
            return config
        except json.JSONDecodeError as e:
            print(f"[error] Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Priority 2: Config file
    if hasattr(args, 'config') and args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"[info] Loaded config from {args.config}", file=sys.stderr)
            return config
        except FileNotFoundError:
            print(f"[error] Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[error] Invalid JSON in config file: {e}", file=sys.stderr)
            sys.exit(1)

    # Priority 3: Legacy CLI args
    if hasattr(args, 'structure') and args.structure:
        # Build config from simple CLI args
        config = {
            "global_tone": args.tone,
            "global_theme": args.theme,
            "context_mode": args.context,
            "temperature": args.temperature,
            "segments": [{"type": seg.strip()} for seg in args.structure.split(',')]
        }

        # Add per-segment duration overrides from CLI
        for segment_type in SEGMENT_CONFIG.keys():
            duration_arg = getattr(args, f'duration_{segment_type}', None)
            if duration_arg:
                # Apply to all segments of this type
                for segment in config['segments']:
                    if segment['type'] == segment_type and 'duration' not in segment:
                        segment['duration'] = duration_arg

        print("[info] Using simple CLI mode", file=sys.stderr)
        return config

    # No valid input method provided
    print("[error] Must provide --json, --config, or --structure", file=sys.stderr)
    sys.exit(1)


def compose_session_from_config(client: GrokClient, config: dict) -> dict:
    """Compose a complete hypnosis session from configuration.

    Args:
        client: GrokClient instance
        config: Session configuration dict (from load_session_config)

    Returns:
        Dict with session metadata and segments
    """
    # Extract global settings with defaults
    global_tone = config.get("global_tone")
    global_theme = config.get("global_theme")
    global_duration = config.get("global_duration")  # Optional
    context_mode = config.get("context_mode", "full")
    temperature = config.get("temperature", 0.8)
    segments_config = config.get("segments", [])

    if not global_tone:
        raise ValueError("global_tone is required in config")
    if not global_theme:
        raise ValueError("global_theme is required in config")
    if not segments_config:
        raise ValueError("segments array is required and cannot be empty")

    segments = []
    context = None

    # Build structure list for display
    structure = [seg['type'] for seg in segments_config]

    print(f"\n[info] Composing session: {len(segments_config)} segments", file=sys.stderr)
    print(f"[info] Global tone: {global_tone}", file=sys.stderr)
    print(f"[info] Global theme: {global_theme}", file=sys.stderr)
    if global_duration:
        print(f"[info] Global duration: {global_duration}", file=sys.stderr)
    print(f"[info] Context mode: {context_mode}", file=sys.stderr)
    print(f"[info] Structure: {' → '.join(structure)}\n", file=sys.stderr)

    for i, segment_config in enumerate(segments_config):
        segment_num = i + 1
        segment_type = segment_config.get('type')

        if not segment_type:
            raise ValueError(f"Segment {segment_num} missing 'type' field")

        if segment_type not in SEGMENT_CONFIG:
            raise ValueError(f"Invalid segment type '{segment_type}' in segment {segment_num}")

        # Resolve tone, theme, duration with fallback priority
        # 1. Segment-specific override
        # 2. Global setting
        # 3. Type default (for duration only)
        segment_tone = segment_config.get('tone', global_tone)
        segment_theme = segment_config.get('theme', global_theme)
        segment_duration = segment_config.get('duration', global_duration)
        # Note: If segment_duration is still None, generate_segment will use type default

        print(f"[{segment_num}/{len(segments_config)}] Generating {segment_type}...", file=sys.stderr)
        if segment_tone != global_tone:
            print(f"  └─ Tone override: {segment_tone}", file=sys.stderr)
        if segment_theme != global_theme:
            print(f"  └─ Theme override: {segment_theme}", file=sys.stderr)
        if segment_duration:
            print(f"  └─ Duration: {segment_duration}", file=sys.stderr)

        # Generate segment with context
        segment_text = generate_segment(
            client=client,
            segment_type=segment_type,
            tone=segment_tone,
            theme=segment_theme,
            duration=segment_duration,
            context=context,
            temperature=temperature
        )

        # Store segment with metadata
        segment_data = {
            "type": segment_type,
            "position": segment_num,
            "tone": segment_tone,
            "theme": segment_theme,
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
        "global_tone": global_tone,
        "global_theme": global_theme,
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

SIMPLE CLI MODE (for basic sessions):
  python compose_session.py \\
    --tone "authoritative" \\
    --theme "obedience" \\
    --structure "pretalk,induction,deepener,wakener"

JSON CONFIG FILE MODE (for complex sessions):
  python compose_session.py \\
    --config session.json \\
    --output session.txt

  Example session.json:
  {{
    "global_tone": "commanding",
    "global_theme": "obedience",
    "global_duration": "60 seconds",
    "context_mode": "full",
    "segments": [
      {{"type": "pretalk", "tone": "gentle", "theme": "safety"}},
      {{"type": "induction", "duration": "5 minutes"}},
      {{"type": "deepener"}},
      {{"type": "conditioning", "theme": "total submission"}},
      {{"type": "deepener"}},
      {{"type": "wakener", "tone": "caring"}}
    ]
  }}

INLINE JSON MODE (for scripting/production):
  python compose_session.py \\
    --json '{{"global_tone":"commanding","global_theme":"obedience","segments":[{{"type":"induction"}},{{"type":"wakener"}}]}}' \\
    --output session.txt
"""
    )

    # JSON input modes (mutually exclusive with simple CLI)
    parser.add_argument('--config', type=str,
                       help='JSON config file path')
    parser.add_argument('--json', dest='json_inline', type=str,
                       help='Inline JSON config string')

    # Simple CLI mode arguments (legacy, kept for backward compatibility)
    parser.add_argument('--tone', type=str,
                       help='Overall tone for the session (simple mode)')
    parser.add_argument('--theme', type=str,
                       help='Overall theme for the session (simple mode)')
    parser.add_argument('--structure', type=str,
                       help='Comma-separated list of segment types (simple mode)')
    parser.add_argument('--context', type=str, default='full',
                       choices=['none', 'last', 'full', 'summary'],
                       help='Context passing mode (default: full, simple mode)')
    parser.add_argument('--temperature', type=float, default=0.8,
                       help='Temperature (default: 0.8)')

    # Output options
    parser.add_argument('--output', type=str,
                       help='Output file (default: stdout)')
    parser.add_argument('--output-json', action='store_true',
                       help='Output as JSON with metadata')

    # Dynamic duration arguments for simple CLI mode
    for segment_type in SEGMENT_CONFIG.keys():
        parser.add_argument(f'--duration-{segment_type}', type=str,
                           help=f'Custom duration for {segment_type} segments (simple mode)')

    args = parser.parse_args()

    # Load configuration (handles priority: inline JSON > file > CLI)
    config = load_session_config(args)

    # Initialize client
    client = GrokClient()

    # Compose session from config
    session = compose_session_from_config(client, config)

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.output_json:
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
        if args.output_json:
            print(json.dumps(session, indent=2, ensure_ascii=False))
        else:
            for segment in session['segments']:
                print(f"## {segment['type'].upper()}\n")
                print(segment['text'])
                print("\n---\n")


if __name__ == '__main__':
    main()
