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
from typing import Optional

from openai import OpenAI
from generate_segment import generate_segment, SEGMENT_CONFIG
import llm_client


def print_expected_schema():
    """Print the expected JSON schema for helpful error messages."""
    schema = {
        "tone": "commanding sadistic",
        "instructions": "GLOBAL style rules - prepended to ALL segments (optional but recommended for F4A, style guides, etc.)",
        "context_mode": "full (optional: none/last/full/summary, default: full)",
        "temperature": 0.8,
        "segments": [
            {
                "type": "pretalk (required: pretalk/induction/deepener/conditioning/fractionation/posthypnotic/wakener/mantra)",
                "additional_instructions": "segment task - ADDED TO global instructions (required)",
                "tone_override": "replaces global tone for THIS segment only (optional)",
                "duration": "2min (optional: '30 seconds', '2min', '500 words')"
            }
        ]
    }
    print("\n[info] Expected JSON schema:", file=sys.stderr)
    print(json.dumps(schema, indent=2), file=sys.stderr)
    print("\n[info] Example with global + segment instructions:", file=sys.stderr)
    example = {
        "tone": "commanding",
        "instructions": "GENDER NEUTRAL (throb/ache, NO cock/pussy). SHOW DONT TELL.",
        "segments": [
            {"type": "pretalk", "additional_instructions": "consent and safety framing", "tone_override": "gentle caring"},
            {"type": "induction", "additional_instructions": "progressive relaxation, body scan"},
            {"type": "deepener", "additional_instructions": "countdown 10 to 1, deeper with each number"},
            {"type": "conditioning", "additional_instructions": "pleasure-obedience linking", "tone_override": "seductive teasing"},
            {"type": "wakener", "additional_instructions": "gentle awakening, refreshed and alert", "tone_override": "warm encouraging"}
        ]
    }
    print(json.dumps(example, indent=2), file=sys.stderr)
    print("\n[info] Note: Global instructions prepended to additional_instructions; tone_override replaces global tone", file=sys.stderr)


def validate_session_config(config: dict) -> None:
    """Validate session config structure and provide helpful errors.

    Raises:
        ValueError: With detailed message about what's wrong and expected schema
    """
    # Check required top-level fields
    if "tone" not in config:
        print("[error] Missing required field 'tone'", file=sys.stderr)
        print_expected_schema()
        raise ValueError("Config must have 'tone' field")

    if "segments" not in config:
        print("[error] Missing required field 'segments'", file=sys.stderr)
        print_expected_schema()
        raise ValueError("Config must have 'segments' array")

    if not isinstance(config["segments"], list) or len(config["segments"]) == 0:
        print("[error] 'segments' must be a non-empty array", file=sys.stderr)
        print_expected_schema()
        raise ValueError("'segments' must be a non-empty array")

    # Validate context_mode if provided
    if "context_mode" in config:
        valid_modes = ["none", "last", "full", "summary"]
        if config["context_mode"] not in valid_modes:
            print(f"[error] Invalid context_mode: '{config['context_mode']}'", file=sys.stderr)
            print(f"[error] Valid options: {', '.join(valid_modes)}", file=sys.stderr)
            raise ValueError(f"context_mode must be one of: {', '.join(valid_modes)}")

    # Validate each segment
    for i, segment in enumerate(config["segments"]):
        segment_num = i + 1

        # Check segment is a dict
        if not isinstance(segment, dict):
            print(f"[error] Segment {segment_num} must be an object/dict", file=sys.stderr)
            print_expected_schema()
            raise ValueError(f"Segment {segment_num} is not a valid object")

        # Check required: type
        if "type" not in segment:
            print(f"[error] Segment {segment_num} missing required field 'type'", file=sys.stderr)
            print(f"[error] Valid types: {', '.join(SEGMENT_CONFIG.keys())}", file=sys.stderr)
            print_expected_schema()
            raise ValueError(f"Segment {segment_num} missing 'type'")

        # Check valid type
        if segment["type"] not in SEGMENT_CONFIG:
            print(f"[error] Segment {segment_num} has invalid type: '{segment['type']}'", file=sys.stderr)
            print(f"[error] Valid types: {', '.join(SEGMENT_CONFIG.keys())}", file=sys.stderr)
            raise ValueError(f"Invalid segment type: '{segment['type']}'")

        # Check required: additional_instructions (either per-segment or global fallback)
        has_segment_instructions = "additional_instructions" in segment
        has_global_instructions = "instructions" in config

        if not has_segment_instructions and not has_global_instructions:
            print(f"[error] Segment {segment_num} ({segment['type']}) missing 'additional_instructions'", file=sys.stderr)
            print(f"[error] Either provide per-segment 'additional_instructions' or global 'instructions'", file=sys.stderr)
            print_expected_schema()
            raise ValueError(f"Segment {segment_num} missing 'additional_instructions' and no global instructions provided")


def load_session_config(args):
    """Load session config from inline JSON, config file, or CLI args.

    Priority order:
    1. --json (inline JSON string)
    2. --config (JSON file path)
    3. Legacy CLI args (--tone, --instructions, --structure)

    Returns:
        dict: Session configuration with structure:
            {
                "tone": str (required),
                "instructions": str (optional global instructions),
                "context_mode": str (optional, default: "full"),
                "temperature": float (optional, default: 0.8),
                "segments": [
                    {
                        "type": str (required),
                        "instructions": str (required, unless global instructions set),
                        "tone": str (optional, overrides global tone),
                        "duration": str (optional)
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
            validate_session_config(config)
            return config
        except json.JSONDecodeError as e:
            print(f"[error] Invalid JSON syntax: {e}", file=sys.stderr)
            print_expected_schema()
            sys.exit(1)
        except ValueError as e:
            print(f"[error] {e}", file=sys.stderr)
            sys.exit(1)

    # Priority 2: Config file
    if hasattr(args, 'config') and args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"[info] Loaded config from {args.config}", file=sys.stderr)
            validate_session_config(config)
            return config
        except FileNotFoundError:
            print(f"[error] Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[error] Invalid JSON syntax in config file: {e}", file=sys.stderr)
            print_expected_schema()
            sys.exit(1)
        except ValueError as e:
            print(f"[error] {e}", file=sys.stderr)
            sys.exit(1)

    # Priority 3: Legacy CLI args
    if hasattr(args, 'structure') and args.structure:
        # Build config from simple CLI args
        config = {
            "tone": args.tone,
            "instructions": args.instructions,
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
        validate_session_config(config)
        return config

    # No valid input method provided
    print("[error] Must provide --json, --config, or --structure", file=sys.stderr)
    sys.exit(1)


def compose_session_from_config(
    config: dict,
    client: Optional[OpenAI] = None,
    model: Optional[str] = None
) -> dict:
    """Compose a complete hypnosis session from configuration.

    Args:
        config: Session configuration dict (from load_session_config)
        client: Optional OpenAI client (uses llm_client.get_client() if not provided)
        model: Optional model override

    Returns:
        Dict with session metadata and segments
    """
    # Extract global settings with defaults
    global_tone = config.get("tone")
    global_instructions = config.get("instructions")  # Optional
    global_duration = config.get("duration")  # Optional
    context_mode = config.get("context_mode", "full")
    temperature = config.get("temperature", 0.8)
    segments_config = config.get("segments", [])

    if not global_tone:
        raise ValueError("tone is required in config")
    if not segments_config:
        raise ValueError("segments array is required and cannot be empty")

    segments = []
    context = None

    # Build structure list for display
    structure = [seg['type'] for seg in segments_config]

    print(f"\n[info] Composing session: {len(segments_config)} segments", file=sys.stderr)
    print(f"[info] Tone: {global_tone}", file=sys.stderr)
    if global_instructions:
        print(f"[info] Global instructions: {global_instructions}", file=sys.stderr)
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

        # Resolve tone, instructions, duration with fallback priority
        # 1. Segment-specific override/addition
        # 2. Global setting
        # 3. Type default (for duration only)

        # tone_override: replaces global tone for this segment
        segment_tone = segment_config.get('tone_override', global_tone)

        # additional_instructions: added to global instructions for this segment
        segment_additional_instructions = segment_config.get('additional_instructions', global_instructions)

        segment_duration = segment_config.get('duration', global_duration)
        # Note: If segment_duration is still None, generate_segment will use type default

        if not segment_additional_instructions:
            raise ValueError(f"Segment {segment_num} ({segment_type}) has no additional_instructions (and no global instructions)")

        print(f"[{segment_num}/{len(segments_config)}] Generating {segment_type}...", file=sys.stderr)
        if segment_tone != global_tone:
            print(f"  └─ Tone override: {segment_tone}", file=sys.stderr)
        if segment_additional_instructions != global_instructions:
            print(f"  └─ Additional instructions: {segment_additional_instructions}", file=sys.stderr)
        elif global_instructions:
            print(f"  └─ Additional instructions: {segment_additional_instructions}", file=sys.stderr)
        if segment_duration:
            print(f"  └─ Duration: {segment_duration}", file=sys.stderr)

        # Generate segment with context
        segment_text = generate_segment(
            segment_type=segment_type,
            tone=segment_tone,
            instructions=segment_additional_instructions,
            duration=segment_duration,
            context=context,
            temperature=temperature,
            global_instructions=global_instructions,
            client=client,
            model=model
        )

        # Store segment with metadata
        segment_data = {
            "type": segment_type,
            "position": segment_num,
            "tone": segment_tone,
            "additional_instructions": segment_additional_instructions,
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
        "tone": global_tone,
        "instructions": global_instructions,
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
    --instructions "deep obedience programming" \\
    --structure "pretalk,induction,deepener,wakener"

JSON CONFIG FILE MODE (for complex sessions):
  python compose_session.py \\
    --config session.json \\
    --output session.txt

  Example session.json:
  {{
    "tone": "commanding",
    "instructions": "GENDER NEUTRAL. obedience training with JOI elements",
    "duration": "60 seconds",
    "context_mode": "full",
    "segments": [
      {{"type": "pretalk", "additional_instructions": "consent and safety framing", "tone_override": "gentle caring"}},
      {{"type": "induction", "additional_instructions": "progressive relaxation", "duration": "5 minutes"}},
      {{"type": "deepener", "additional_instructions": "countdown 10 to 1"}},
      {{"type": "conditioning", "additional_instructions": "pleasure-obedience linking", "tone_override": "seductive teasing"}},
      {{"type": "deepener", "additional_instructions": "deeper stillness"}},
      {{"type": "wakener", "additional_instructions": "gentle awakening, refreshed", "tone_override": "warm encouraging"}}
    ]
  }}

INLINE JSON MODE (for scripting/production):
  python compose_session.py \\
    --json '{{"tone":"commanding","instructions":"GENDER NEUTRAL","segments":[{{"type":"induction","additional_instructions":"focus and trance"}},{{"type":"wakener","additional_instructions":"alert and refreshed"}}]}}' \\
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
    parser.add_argument('--instructions', type=str,
                       help='Overall instructions for the session (simple mode)')
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
    client, model = llm_client.get_client()

    # Compose session from config
    session = compose_session_from_config(config, client=client, model=model)

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.output_json:
                # Full JSON output with metadata
                json.dump(session, f, indent=2, ensure_ascii=False)
            else:
                # Plain text: prepend JSON config header for replicability
                f.write("<!--\n")
                f.write("HYPNOCLI_CONFIG:\n")
                f.write(json.dumps(config, indent=2, ensure_ascii=False))
                f.write("\n-->\n\n")

                # Then the script content
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
