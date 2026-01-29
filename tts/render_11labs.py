#!/usr/bin/env python3
"""
render_11labs.py
----------------
Render text to audio using ElevenLabs API.

High-quality cloud TTS with voice cloning capabilities.
Requires API key from elevenlabs.io.

Usage:
    python render_11labs.py input.txt output.mp3 --voice Rachel
    python render_11labs.py input.txt output.mp3 --voice-id <voice_id> --model eleven_turbo_v2
    python render_11labs.py scripts/ audio/ --batch --voice Rachel

Environment:
    ELEVEN_API_KEY - ElevenLabs API key (or in .env file)

Models:
    eleven_turbo_v2      - Fast, good quality (0.5 credits/char)
    eleven_multilingual_v2 - Best multilingual support
    eleven_monolingual_v1  - English only, legacy
    eleven_flash_v2_5    - Fastest, lowest latency

Pricing (as of Jan 2026):
    Starter: $5/mo for 30k chars
    Creator: $11/mo for 100k chars
    Pro: $99/mo for 500k chars

See: https://elevenlabs.io/docs/api-reference/text-to-speech
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Lazy imports
_client = None

# Pause pattern
PAUSE_PATTERN = re.compile(r'\[(\d+(?:\.\d+)?)(s|ms)?\]')

# Common voice names to IDs (partial list - use --list-voices for full list)
VOICE_PRESETS = {
    'rachel': '21m00Tcm4TlvDq8ikWAM',
    'domi': 'AZnzlk1XvdvUeBnXmlld',
    'bella': 'EXAVITQu4vr4xnSDxMaL',
    'antoni': 'ErXwobaYiN019PkySvjV',
    'elli': 'MF3mGyEYCl7XYWbV9V6O',
    'josh': 'TxGEqnHWrfWFTfGW9XjX',
    'arnold': 'VR6AewLTigWG4xSOukaG',
    'adam': 'pNInz6obpgDQGcFmaJgB',
    'sam': 'yoZ06aMxZJJ28mfd3POQ',
}


def load_env() -> dict:
    """Load environment variables from .env file."""
    env_vars = {}
    search_paths = [
        Path(__file__).resolve().parent.parent / '.env',
        Path(__file__).resolve().parent / '.env',
        Path.cwd() / '.env',
    ]

    for path in search_paths:
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
            break

    return env_vars


def get_api_key() -> Optional[str]:
    """Get ElevenLabs API key from environment."""
    key = os.environ.get('ELEVEN_API_KEY') or os.environ.get('ELEVENLABS_API_KEY')
    if not key:
        env_vars = load_env()
        key = env_vars.get('ELEVEN_API_KEY') or env_vars.get('ELEVENLABS_API_KEY')
    return key


def get_client():
    """Lazy-load ElevenLabs client."""
    global _client
    if _client is None:
        api_key = get_api_key()
        if not api_key:
            print("Error: ELEVEN_API_KEY not found in environment or .env file", file=sys.stderr)
            sys.exit(1)

        try:
            from elevenlabs import ElevenLabs
            _client = ElevenLabs(api_key=api_key)
        except ImportError:
            print("Error: elevenlabs not installed. Run: pip install elevenlabs", file=sys.stderr)
            sys.exit(1)

    return _client


def resolve_voice_id(voice: str) -> str:
    """Resolve voice name to ID."""
    # Check if it's already an ID (long alphanumeric)
    if len(voice) > 15 and voice.isalnum():
        return voice

    # Check presets
    voice_lower = voice.lower()
    if voice_lower in VOICE_PRESETS:
        return VOICE_PRESETS[voice_lower]

    # Assume it's a valid ID
    return voice


def convert_pauses(text: str, model: str = "eleven_turbo_v2") -> str:
    """Convert [Xms] pause markers for ElevenLabs.

    V3 models: Use expressive tags [short pause], [pause], [long pause]
    V2 models: Use SSML <break time="Xs" />
    """
    is_v3 = 'v3' in model.lower()

    def replace_pause(match):
        value = float(match.group(1))
        unit = match.group(2) or 'ms'
        ms = value * 1000 if unit == 's' else value

        if is_v3:
            # V3: expressive tags
            if ms <= 400:
                return "[short pause]"
            elif ms <= 800:
                return "[pause]"
            else:
                return "[long pause]"
        else:
            # V2: SSML breaks (max 3s)
            seconds = min(ms / 1000, 3.0)
            return f'<break time="{seconds}s" />'

    # Remove HTML comments
    text = re.sub(r'<!--[^>]*-->', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Convert pauses
    text = PAUSE_PATTERN.sub(replace_pause, text)

    return text.strip()


def chunk_text(text: str, max_chars: int = 4500) -> list[str]:
    """Split text into chunks at sentence boundaries.

    ElevenLabs has a ~5000 char limit per request.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_len + len(sentence) > max_chars and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_len = len(sentence)
        else:
            current_chunk.append(sentence)
            current_len += len(sentence) + 1

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks if chunks else [text]


def render_chunk(
    text: str,
    voice_id: str,
    model: str = "eleven_turbo_v2",
    stability: float = 0.5,
    similarity: float = 0.75,
    style: float = 0.0
) -> bytes:
    """Render a single text chunk to audio bytes."""
    client = get_client()

    # Use SSML for V2 models if text contains break tags
    use_ssml = '<break' in text and 'v3' not in model.lower()

    if use_ssml:
        text = f"<speak>{text}</speak>"

    response = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model,
        voice_settings={
            "stability": stability,
            "similarity_boost": similarity,
            "style": style,
            "use_speaker_boost": True
        }
    )

    # Response is a generator of bytes
    audio_bytes = b''.join(response)
    return audio_bytes


def concat_audio_files(input_files: list[str], output_file: str) -> bool:
    """Concatenate audio files using ffmpeg."""
    import subprocess

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


def render_script(
    input_file: str,
    output_file: str,
    voice: str = "rachel",
    model: str = "eleven_turbo_v2",
    stability: float = 0.5,
    similarity: float = 0.75,
    style: float = 0.0,
    verbose: bool = True
) -> bool:
    """Render a script file to audio using ElevenLabs.

    Args:
        input_file: Path to script .txt file
        output_file: Path for output audio file
        voice: Voice name or ID
        model: Model ID
        stability: Voice stability (0-1)
        similarity: Voice similarity boost (0-1)
        style: Style exaggeration (0-1, V2 only)
        verbose: Print progress
    """
    voice_id = resolve_voice_id(voice)

    # Read and convert script
    with open(input_file) as f:
        text = f.read()

    text = convert_pauses(text, model)

    # Chunk if needed
    chunks = chunk_text(text)

    if verbose:
        print(f"Processing {len(chunks)} chunks with voice {voice}...")

    # Render each chunk
    temp_dir = tempfile.mkdtemp()
    chunk_files = []

    try:
        for i, chunk in enumerate(chunks):
            if verbose:
                preview = chunk[:50] + '...' if len(chunk) > 50 else chunk
                print(f"  [{i+1}/{len(chunks)}] {preview}")

            audio_bytes = render_chunk(
                chunk, voice_id, model,
                stability, similarity, style
            )

            chunk_file = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            with open(chunk_file, 'wb') as f:
                f.write(audio_bytes)
            chunk_files.append(chunk_file)

        # Concatenate if multiple chunks
        if len(chunk_files) == 1:
            # Single chunk - just copy/convert
            import shutil
            ext = Path(output_file).suffix.lower()
            if ext == '.mp3':
                shutil.copy(chunk_files[0], output_file)
            else:
                # Convert using ffmpeg
                import subprocess
                subprocess.run([
                    'ffmpeg', '-y', '-i', chunk_files[0], output_file
                ], capture_output=True)
        else:
            # Multiple chunks - concatenate
            if verbose:
                print(f"Concatenating {len(chunk_files)} chunks...")

            # Concatenate to temp mp3 first
            temp_output = os.path.join(temp_dir, "output.mp3")
            if not concat_audio_files(chunk_files, temp_output):
                print("Error: Concatenation failed", file=sys.stderr)
                return False

            # Convert to final format if needed
            ext = Path(output_file).suffix.lower()
            if ext == '.mp3':
                import shutil
                shutil.copy(temp_output, output_file)
            else:
                import subprocess
                subprocess.run([
                    'ffmpeg', '-y', '-i', temp_output, output_file
                ], capture_output=True)

        if verbose:
            print(f"Done: {output_file}")

        return True

    finally:
        # Cleanup
        for f in chunk_files:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def render_batch(
    input_dir: str,
    output_dir: str,
    voice: str = "rachel",
    model: str = "eleven_turbo_v2",
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
        if not render_script(str(txt_file), str(mp3_file), voice, model, verbose=verbose):
            success = False

    return success


def list_voices():
    """List available voices from the API."""
    client = get_client()
    voices = client.voices.get_all()

    print("Available voices:")
    print("-" * 60)
    for voice in voices.voices:
        labels = ', '.join(f"{k}={v}" for k, v in (voice.labels or {}).items())
        print(f"  {voice.name:20} {voice.voice_id}")
        if labels:
            print(f"    {labels}")
    print("-" * 60)
    print(f"Total: {len(voices.voices)} voices")


def main():
    parser = argparse.ArgumentParser(
        description="Render text to audio using ElevenLabs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Preset Voices:
  rachel, domi, bella, antoni, elli, josh, arnold, adam, sam

Models:
  eleven_turbo_v2       Fast, good quality (default)
  eleven_multilingual_v2  Best multilingual
  eleven_flash_v2_5     Fastest, lowest latency

Examples:
  %(prog)s script.txt output.mp3 --voice rachel
  %(prog)s script.txt output.mp3 --voice-id <id> --model eleven_multilingual_v2
  %(prog)s scripts/ audio/ --batch --voice rachel
  %(prog)s --list-voices

Environment:
  ELEVEN_API_KEY  ElevenLabs API key (or in .env file)

Installation:
  pip install elevenlabs
"""
    )
    parser.add_argument("input", nargs='?', help="Input text file or directory (with --batch)")
    parser.add_argument("output", nargs='?', help="Output audio file or directory (with --batch)")
    parser.add_argument("--voice", "-v", default="rachel",
                       help="Voice name or ID (default: rachel)")
    parser.add_argument("--voice-id", dest="voice_id",
                       help="Explicit voice ID (overrides --voice)")
    parser.add_argument("--model", "-m", default="eleven_turbo_v2",
                       help="Model ID (default: eleven_turbo_v2)")
    parser.add_argument("--stability", type=float, default=0.5,
                       help="Voice stability 0-1 (default: 0.5)")
    parser.add_argument("--similarity", type=float, default=0.75,
                       help="Similarity boost 0-1 (default: 0.75)")
    parser.add_argument("--style", type=float, default=0.0,
                       help="Style exaggeration 0-1 (default: 0.0)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Batch mode: process all .txt files in input directory")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")
    parser.add_argument("--list-voices", action="store_true",
                       help="List available voices and exit")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        sys.exit(0)

    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)

    voice = args.voice_id or args.voice

    if args.batch:
        if not os.path.isdir(args.input):
            print(f"Error: {args.input} is not a directory (required for --batch)", file=sys.stderr)
            sys.exit(1)
        success = render_batch(
            args.input,
            args.output,
            voice=voice,
            model=args.model,
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
            model=args.model,
            stability=args.stability,
            similarity=args.similarity,
            style=args.style,
            verbose=not args.quiet
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
