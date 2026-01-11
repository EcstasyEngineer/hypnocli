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


def render_chunk(
    text: str,
    output_path: str,
    voice: str = "Salli",
    engine: str = "neural",
    region: str = "us-east-1",
    profile: Optional[str] = None,
    aws_env: Optional[dict] = None
) -> bool:
    """Render a single text chunk using AWS Polly."""
    cmd = ["aws"]

    # Use profile if specified, otherwise rely on env vars
    if profile:
        cmd.extend(["--profile", profile])

    cmd.extend([
        "--region", region,
        "polly", "synthesize-speech",
        "--text", text,
        "--output-format", "mp3",
        "--voice-id", voice,
        "--engine", engine,
        output_path
    ])

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


def render_script(
    input_file: str,
    output_file: str,
    voice: str = "Salli",
    engine: str = "neural",
    region: str = "us-east-1",
    profile: Optional[str] = None,
    verbose: bool = True
) -> bool:
    """Render a full script file to audio."""
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
    text = clean_script_text(text)

    # Chunk the text
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

            if not render_chunk(chunk, chunk_file, voice, engine, region, profile, aws_config):
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
            verbose=not args.quiet
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
