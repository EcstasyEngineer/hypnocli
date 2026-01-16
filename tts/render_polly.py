#!/usr/bin/env python3
"""
render_polly.py
---------------
Render long text to AWS Polly by chunking at sentence boundaries and concatenating.

Handles texts longer than Polly's 3000 character limit by splitting intelligently
and using ffmpeg to concatenate the resulting audio chunks.

Usage:
    python render_polly.py input.txt output.mp3
    python render_polly.py input.txt output.mp3 --voice joanna --engine neural
    python render_polly.py scripts/ audio/ --batch

Environment:
    Reads AWS credentials from .env file or environment variables:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION (default: us-east-1)
    - AWS_PROFILE (optional, uses named profile instead of keys)

Requires:
    - AWS CLI installed
    - ffmpeg installed for audio concatenation
"""

import argparse
import subprocess
import sys
import os
import re
import tempfile
from pathlib import Path
from typing import Optional


# Available voices for quick reference
VOICES = {
    "salli": "Salli",       # Female, US English - warm, clear
    "joanna": "Joanna",     # Female, US English - newsreader style
    "ivy": "Ivy",           # Female, US English - child voice
    "kendra": "Kendra",     # Female, US English
    "kimberly": "Kimberly", # Female, US English
    "matthew": "Matthew",   # Male, US English
    "joey": "Joey",         # Male, US English
    "justin": "Justin",     # Male, US English - child voice
}


def load_env(env_path: Optional[Path] = None) -> dict:
    """Load environment variables from .env file."""
    env_vars = {}

    # Try multiple locations for .env
    search_paths = []
    if env_path:
        search_paths.append(Path(env_path))
    search_paths.extend([
        Path(__file__).resolve().parent.parent / '.env',  # hypnocli/.env
        Path(__file__).resolve().parent / '.env',          # tts/.env
        Path.cwd() / '.env',                               # current dir
    ])

    for path in search_paths:
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('"\'')
                        env_vars[key.strip()] = value
            break

    return env_vars


def load_aws_credentials(profile: str = 'default') -> dict:
    """Load credentials from ~/.aws/credentials and ~/.aws/config."""
    creds = {}

    # Read credentials file
    creds_path = Path.home() / '.aws' / 'credentials'
    if creds_path.exists():
        current_section = None
        with open(creds_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                elif '=' in line and current_section == profile:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == 'aws_access_key_id':
                        creds['access_key'] = value
                    elif key == 'aws_secret_access_key':
                        creds['secret_key'] = value

    # Read config file for region
    config_path = Path.home() / '.aws' / 'config'
    if config_path.exists():
        # Config uses [profile name] for non-default, [default] for default
        section_name = 'default' if profile == 'default' else f'profile {profile}'
        current_section = None
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                elif '=' in line and current_section == section_name:
                    key, value = line.split('=', 1)
                    if key.strip() == 'region':
                        creds['region'] = value.strip()

    return creds


def get_aws_config() -> dict:
    """Get AWS configuration from environment, .env file, or AWS CLI config."""
    env_vars = load_env()

    # Determine profile to use
    profile = os.environ.get('AWS_PROFILE', env_vars.get('AWS_PROFILE', 'default'))

    # Load from AWS CLI credentials as fallback
    aws_creds = load_aws_credentials(profile)

    # Priority: environment > .env > AWS CLI credentials
    return {
        'access_key': os.environ.get('AWS_ACCESS_KEY_ID', env_vars.get('AWS_ACCESS_KEY_ID', aws_creds.get('access_key', ''))),
        'secret_key': os.environ.get('AWS_SECRET_ACCESS_KEY', env_vars.get('AWS_SECRET_ACCESS_KEY', aws_creds.get('secret_key', ''))),
        'region': os.environ.get('AWS_REGION', env_vars.get('AWS_REGION', aws_creds.get('region', 'us-east-1'))),
        'profile': profile if profile != 'default' else '',
    }


def chunk_text(text: str, max_chars: int = 2900) -> list[str]:
    """
    Recursively split text into chunks, trying to break at natural boundaries.

    Priority order:
    1. Paragraphs (newlines)
    2. Sentences (. ! ?)
    3. Clauses (, ; :)
    4. Words (spaces)
    5. Hard cut (last resort)

    Splits near the midpoint to balance chunk sizes.
    Based on recursive_split from literallybot.
    """
    def recursive_split(text: str, max_size: int) -> list[str]:
        # Base case: text fits
        if len(text) <= max_size:
            return [text] if text.strip() else []

        mid = len(text) // 2

        # Try splitting at natural boundaries, in order of preference
        # Paragraphs -> Sentences -> Clauses -> Words
        split_patterns = [
            r'\n\n+',           # Paragraph breaks
            r'\n',              # Line breaks
            r'[.!?]\s+',        # Sentence endings
            r'[,;:]\s+',        # Clause boundaries
            r'\s+',             # Word boundaries
        ]

        for pattern in split_patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                # Find the match closest to the midpoint
                best_match = min(matches, key=lambda m: abs(m.end() - mid))
                split_index = best_match.end()

                # Ensure we're not at the very start or end
                if split_index <= 0 or split_index >= len(text):
                    continue

                left = text[:split_index].rstrip()
                right = text[split_index:].lstrip()

                # Only use this split if both parts are non-empty
                if left and right:
                    return recursive_split(left, max_size) + recursive_split(right, max_size)

        # Last resort: hard split at max_size
        left = text[:max_size].rstrip()
        right = text[max_size:].lstrip()
        return [left] + recursive_split(right, max_size)

    return recursive_split(text.strip(), max_chars)


def chunk_ssml(text: str, max_chars: int = 2900) -> list[str]:
    """
    SSML-aware chunking that preserves tag structure.

    Strategy:
    1. First try splitting on phase comments (<!-- PHASE:) as natural boundaries
    2. Track open prosody/other tags and close/reopen them at chunk boundaries
    3. Fall back to paragraph splits if phases are too large
    """
    # First, try splitting on phase comments
    phase_pattern = r'(?=<!-- PHASE:)'
    phase_chunks = re.split(phase_pattern, text)
    phase_chunks = [c.strip() for c in phase_chunks if c.strip()]

    # If phases are small enough, use them directly
    if all(len(c) <= max_chars for c in phase_chunks):
        return phase_chunks

    # Otherwise, need to split large phases further
    result = []
    for phase in phase_chunks:
        if len(phase) <= max_chars:
            result.append(phase)
        else:
            # Split this phase, tracking open tags
            result.extend(_split_ssml_chunk(phase, max_chars))

    return result


def _split_ssml_chunk(text: str, max_chars: int) -> list[str]:
    """Split a single SSML chunk while preserving tag structure."""
    # Find all open tags that need to be tracked
    open_tags = []
    tag_pattern = r'<(prosody|emphasis|phoneme|sub|lang|voice|amazon:\w+)([^>]*)>'
    close_pattern = r'</(prosody|emphasis|phoneme|sub|lang|voice|amazon:\w+)>'

    chunks = []
    current_pos = 0

    while current_pos < len(text):
        # Find a good split point
        end_pos = min(current_pos + max_chars, len(text))

        if end_pos >= len(text):
            # Last chunk
            chunk = text[current_pos:]
        else:
            # Find a safe split point (paragraph or sentence boundary)
            search_text = text[current_pos:end_pos]

            # Look for paragraph break near the end
            para_matches = list(re.finditer(r'\n\n+', search_text))
            if para_matches:
                # Use the last paragraph break
                split_at = para_matches[-1].end()
            else:
                # Look for sentence break
                sent_matches = list(re.finditer(r'[.!?]\s+', search_text))
                if sent_matches:
                    split_at = sent_matches[-1].end()
                else:
                    # Fall back to any whitespace
                    ws_matches = list(re.finditer(r'\s+', search_text))
                    if ws_matches:
                        split_at = ws_matches[-1].end()
                    else:
                        split_at = len(search_text)

            chunk = text[current_pos:current_pos + split_at]
            current_pos += split_at
            if current_pos < len(text):
                current_pos = current_pos  # Will continue from here

        # Track which tags are open at the start of this chunk
        prefix_tags = ''.join(f'<{tag}{attrs}>' for tag, attrs in open_tags)

        # Update open_tags based on this chunk's content
        for match in re.finditer(tag_pattern, chunk):
            open_tags.append((match.group(1), match.group(2)))
        for match in re.finditer(close_pattern, chunk):
            # Remove the most recent matching open tag
            tag_name = match.group(1)
            for i in range(len(open_tags) - 1, -1, -1):
                if open_tags[i][0] == tag_name:
                    open_tags.pop(i)
                    break

        # Close any tags still open at end of chunk
        suffix_tags = ''.join(f'</{tag}>' for tag, _ in reversed(open_tags))

        # Build the chunk with proper tag wrapping
        if chunks:  # Not the first chunk, add prefix
            chunk = prefix_tags + chunk

        if current_pos < len(text) and open_tags:  # Not the last chunk, add suffix
            chunk = chunk + suffix_tags

        chunks.append(chunk.strip())

        if end_pos >= len(text):
            break

        current_pos = end_pos if current_pos == 0 else current_pos

    return [c for c in chunks if c]


def render_chunk(
    text: str,
    output_path: str,
    voice: str = "Salli",
    engine: str = "neural",
    region: str = "us-east-1",
    profile: Optional[str] = None,
    aws_env: Optional[dict] = None,
    ssml: bool = False
) -> bool:
    """Render a single text chunk using AWS Polly."""
    cmd = ["aws"]

    # Use profile if specified, otherwise rely on env vars
    if profile:
        cmd.extend(["--profile", profile])

    # For SSML, wrap chunk in <speak> tags if not already wrapped
    if ssml:
        if not text.strip().startswith('<speak>'):
            text = f"<speak>{text}</speak>"

    cmd.extend([
        "--region", region,
        "polly", "synthesize-speech",
        "--text", text,
        "--output-format", "mp3",
        "--voice-id", voice,
        "--engine", engine,
        output_path
    ])

    if ssml:
        cmd.insert(cmd.index("--text"), "--text-type")
        cmd.insert(cmd.index("--text"), "ssml")

    # Set up environment with AWS credentials if provided
    env = os.environ.copy()
    if aws_env:
        if aws_env.get('access_key'):
            env['AWS_ACCESS_KEY_ID'] = aws_env['access_key']
        if aws_env.get('secret_key'):
            env['AWS_SECRET_ACCESS_KEY'] = aws_env['secret_key']

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False
    return True


def concat_mp3s(input_files: list[str], output_file: str) -> bool:
    """Concatenate MP3 files using ffmpeg."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        list_file = f.name
        for inp in input_files:
            f.write(f"file '{inp}'\n")

    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy", output_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    finally:
        os.unlink(list_file)


def clean_script_text(text: str) -> str:
    """Remove HTML comments and other markup from script text."""
    # Remove HTML comments like <!-- PHASE: P2 ... -->
    text = re.sub(r'<!--[^>]*-->', '', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---- Pause Markup Auto-Conversion ----
# Simple markup: [500] = 500ms pause, [1.5s] = 1.5 second pause
# Scripts can stay as .txt with these markers and auto-convert to SSML

PAUSE_PATTERN = re.compile(r'\[(\d+(?:\.\d+)?)(s|ms)?\]')


def has_pause_markers(text: str) -> bool:
    """Check if text contains pause markers like [500] or [1.5s]."""
    return bool(PAUSE_PATTERN.search(text))


def convert_pauses_to_ssml(text: str) -> str:
    """Convert pause markers to SSML break tags.

    Syntax:
        [500]   -> <break time="500ms"/>   (default is ms)
        [500ms] -> <break time="500ms"/>
        [1.5s]  -> <break time="1500ms"/>
        [2s]    -> <break time="2000ms"/>

    Also wraps the result in <speak> tags for Polly.
    """
    def replace_pause(match):
        value = float(match.group(1))
        unit = match.group(2) or 'ms'
        if unit == 's':
            ms = int(value * 1000)
        else:
            ms = int(value)
        return f'<break time="{ms}ms"/>'

    # Remove HTML comments first
    text = re.sub(r'<!--[^>]*-->', '', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Convert pause markers
    text = PAUSE_PATTERN.sub(replace_pause, text)

    return text.strip()


def render_script(
    input_file: str,
    output_file: str,
    voice: str = "Salli",
    engine: str = "neural",
    region: str = "us-east-1",
    profile: Optional[str] = None,
    verbose: bool = True,
    keep_chunks: bool = False,
    ssml: bool = False
) -> bool:
    """Render a full script file to audio.

    Args:
        keep_chunks: If True, preserves chunk files in a debug directory next to output file.
        ssml: If True, treats input as SSML and passes --text-type ssml to Polly.
    """
    aws_config = get_aws_config()

    # Use profile from config if not explicitly provided
    if not profile:
        profile = aws_config.get('profile') or None

    # Check we have some form of auth
    if not profile and not aws_config.get('access_key'):
        print("Error: AWS credentials not found.", file=sys.stderr)
        print("Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_PROFILE in environment or .env file.", file=sys.stderr)
        return False

    # Read and clean text
    with open(input_file) as f:
        text = f.read()

    # Auto-detect pause markers and convert to SSML
    if not ssml and has_pause_markers(text):
        if verbose:
            print("Detected pause markers [Xms], auto-converting to SSML...")
        text = convert_pauses_to_ssml(text)
        ssml = True  # Enable SSML mode for rendering

    # For SSML, strip outer <speak> tags before chunking (we'll re-add per chunk)
    if ssml:
        text = re.sub(r'^\s*<speak>\s*', '', text)
        text = re.sub(r'\s*</speak>\s*$', '', text)
        # Remove HTML comments but preserve SSML tags
        text = re.sub(r'<!--[^>]*-->', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
    else:
        text = clean_script_text(text)

    # Chunk the text (use SSML-aware chunking if needed)
    if ssml:
        chunks = chunk_ssml(text)
    else:
        chunks = chunk_text(text)
    if verbose:
        print(f"Split into {len(chunks)} chunks")

    # Render each chunk
    chunk_files = []
    temp_dir = tempfile.mkdtemp()

    try:
        for i, chunk in enumerate(chunks):
            chunk_file = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            if verbose:
                print(f"  Rendering chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")

            if not render_chunk(chunk, chunk_file, voice, engine, region, profile, aws_config, ssml=ssml):
                print(f"Failed on chunk {i+1}", file=sys.stderr)
                return False
            chunk_files.append(chunk_file)

        # Concatenate chunks
        if verbose:
            print(f"Concatenating {len(chunk_files)} chunks...")

        if not concat_mp3s(chunk_files, output_file):
            print("Concatenation failed", file=sys.stderr)
            return False

        if verbose:
            print(f"Done: {output_file}")
        return True

    finally:
        if keep_chunks and chunk_files:
            # Move chunks to debug directory next to output
            debug_dir = Path(output_file).parent / f"{Path(output_file).stem}_chunks"
            debug_dir.mkdir(parents=True, exist_ok=True)
            for f in chunk_files:
                if os.path.exists(f):
                    import shutil
                    shutil.move(f, debug_dir / Path(f).name)
            if verbose:
                print(f"Chunks preserved in: {debug_dir}")
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        else:
            # Cleanup temp files
            for f in chunk_files:
                if os.path.exists(f):
                    os.remove(f)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)


def render_batch(
    input_dir: str,
    output_dir: str,
    voice: str = "Salli",
    engine: str = "neural",
    region: str = "us-east-1",
    profile: Optional[str] = None,
    verbose: bool = True
) -> bool:
    """Render all .txt files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_files = list(input_path.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {input_dir}", file=sys.stderr)
        return False

    success = True
    for txt_file in txt_files:
        mp3_file = output_path / f"{txt_file.stem}.mp3"
        if verbose:
            print(f"\n=== {txt_file.name} ===")
        if not render_script(str(txt_file), str(mp3_file), voice, engine, region, profile, verbose):
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Render text to AWS Polly audio with automatic chunking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voices:
  salli     Female, US English - warm, clear (default)
  joanna    Female, US English - newsreader style
  ivy       Female, US English - child voice
  kendra    Female, US English
  kimberly  Female, US English
  matthew   Male, US English
  joey      Male, US English
  justin    Male, US English - child voice

Examples:
  %(prog)s script.txt output.mp3
  %(prog)s script.txt output.mp3 --voice joanna --engine standard
  %(prog)s scripts/ audio/ --batch

Environment variables (or in .env file):
  AWS_ACCESS_KEY_ID      AWS access key
  AWS_SECRET_ACCESS_KEY  AWS secret key
  AWS_REGION             AWS region (default: us-east-1)
  AWS_PROFILE            Named AWS profile (alternative to keys)
"""
    )
    parser.add_argument("input", help="Input text file or directory (with --batch)")
    parser.add_argument("output", help="Output MP3 file or directory (with --batch)")
    parser.add_argument("--voice", "-v", default="salli",
                       choices=list(VOICES.keys()),
                       help="Polly voice (default: salli)")
    parser.add_argument("--engine", "-e", default="neural",
                       choices=["standard", "neural"],
                       help="Polly engine - neural is better quality, ~4x cost (default: neural)")
    parser.add_argument("--region", "-r", default="us-east-1",
                       help="AWS region (default: us-east-1)")
    parser.add_argument("--profile", "-p", default=None,
                       help="AWS profile name (overrides env vars)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Batch mode: process all .txt files in input directory")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")
    parser.add_argument("--keep-chunks", "-k", action="store_true",
                       help="Debug: preserve chunk files in {output}_chunks/ directory")
    # Note: SSML is auto-detected via [Xms] pause markers - no flag needed

    args = parser.parse_args()

    # Normalize voice name
    voice = VOICES.get(args.voice.lower(), args.voice)

    if args.batch:
        if not os.path.isdir(args.input):
            print(f"Error: {args.input} is not a directory (required for --batch)", file=sys.stderr)
            sys.exit(1)
        success = render_batch(
            args.input,
            args.output,
            voice=voice,
            engine=args.engine,
            region=args.region,
            profile=args.profile,
            verbose=not args.quiet
        )
    else:
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        success = render_script(
            args.input,
            args.output,
            voice=voice,
            engine=args.engine,
            region=args.region,
            profile=args.profile,
            verbose=not args.quiet,
            keep_chunks=args.keep_chunks
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
