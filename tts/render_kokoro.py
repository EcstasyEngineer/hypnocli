#!/usr/bin/env python3
"""
render_kokoro.py
----------------
Render text to audio using Kokoro 82M TTS model (local, no API needed).

Kokoro is a lightweight 82M parameter TTS model that runs locally.
Despite its small size, it produces high-quality speech.

Usage:
    python render_kokoro.py input.txt output.wav
    python render_kokoro.py input.txt output.wav --voice af_heart
    python render_kokoro.py scripts/ audio/ --batch

Installation:
    pip install kokoro-onnx soundfile

    # Download model files (first run does this automatically):
    # ~/.cache/kokoro-onnx/kokoro-v1.0.onnx (~325MB)
    # ~/.cache/kokoro-onnx/voices-v1.0.bin (~28MB)

Voices (American English):
    af_heart, af_bella, af_nicole, af_sarah, af_sky
    am_adam, am_michael

Voices (British English):
    bf_emma, bf_isabella, bm_george, bm_lewis

See: https://github.com/thewh1teagle/kokoro-onnx
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

# Lazy imports for heavy dependencies
_kokoro = None
_sf = None

# Model file URLs and paths
MODEL_DIR = Path.home() / '.cache' / 'kokoro-onnx'
MODEL_URL = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx'
VOICES_URL = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin'


def download_models():
    """Download model files if not present."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / 'kokoro-v1.0.onnx'
    voices_path = MODEL_DIR / 'voices-v1.0.bin'

    if not model_path.exists():
        print(f"Downloading kokoro model (~325MB)...")
        urllib.request.urlretrieve(MODEL_URL, model_path)
        print(f"  Saved to {model_path}")

    if not voices_path.exists():
        print(f"Downloading voices file (~28MB)...")
        urllib.request.urlretrieve(VOICES_URL, voices_path)
        print(f"  Saved to {voices_path}")

    return str(model_path), str(voices_path)


def get_kokoro():
    """Lazy-load Kokoro model."""
    global _kokoro
    if _kokoro is None:
        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            print("Error: kokoro-onnx not installed. Run: pip install kokoro-onnx soundfile", file=sys.stderr)
            sys.exit(1)

        model_path, voices_path = download_models()
        _kokoro = Kokoro(model_path, voices_path)
    return _kokoro


def get_soundfile():
    """Lazy-load soundfile."""
    global _sf
    if _sf is None:
        try:
            import soundfile as sf
            _sf = sf
        except ImportError:
            print("Error: soundfile not installed. Run: pip install soundfile", file=sys.stderr)
            sys.exit(1)
    return _sf


# Available voices by language
VOICES = {
    # American English
    'af_heart': ('a', 'Female - warm, expressive'),
    'af_bella': ('a', 'Female - clear, neutral'),
    'af_nicole': ('a', 'Female - professional'),
    'af_sarah': ('a', 'Female - friendly'),
    'af_sky': ('a', 'Female - bright'),
    'am_adam': ('a', 'Male - deep, calm'),
    'am_michael': ('a', 'Male - neutral'),
    # British English
    'bf_emma': ('b', 'Female - British'),
    'bf_isabella': ('b', 'Female - British'),
    'bm_george': ('b', 'Male - British'),
    'bm_lewis': ('b', 'Male - British'),
}

# Pause pattern from our markup system
PAUSE_PATTERN = re.compile(r'\[(\d+(?:\.\d+)?)(s|ms)?\]')

# Kokoro sample rate
SAMPLE_RATE = 24000


def convert_pauses_to_silence(text: str) -> list[tuple[str, Optional[float]]]:
    """Convert text with pause markers to segments with silence durations.

    Returns list of (text_segment, silence_after_seconds) tuples.
    Last segment has None for silence.
    """
    # Remove HTML comments
    text = re.sub(r'<!--[^>]*-->', '', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    segments = []
    last_end = 0

    for match in PAUSE_PATTERN.finditer(text):
        # Get text before this pause
        segment_text = text[last_end:match.start()].strip()

        # Parse pause duration
        value = float(match.group(1))
        unit = match.group(2) or 'ms'
        if unit == 's':
            pause_sec = value
        else:
            pause_sec = value / 1000

        if segment_text:
            segments.append((segment_text, pause_sec))

        last_end = match.end()

    # Get remaining text after last pause
    remaining = text[last_end:].strip()
    if remaining:
        segments.append((remaining, None))

    # If no pauses found, return whole text
    if not segments:
        segments = [(text.strip(), None)]

    return segments


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Split text into chunks at sentence boundaries.

    Kokoro works best with shorter segments for consistent quality.
    """
    # Split on sentence boundaries
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


def generate_silence(duration_sec: float, sample_rate: int = SAMPLE_RATE):
    """Generate silence array."""
    import numpy as np
    return np.zeros(int(duration_sec * sample_rate), dtype=np.float32)


def render_text(
    text: str,
    voice: str = 'af_heart',
    speed: float = 1.0,
    lang_code: Optional[str] = None
) -> 'np.ndarray':
    """Render text to audio array using Kokoro ONNX.

    Args:
        text: Text to synthesize
        voice: Voice name (e.g., 'af_heart')
        speed: Speech speed multiplier (0.5-2.0)
        lang_code: Ignored (kept for API compatibility)

    Returns:
        Audio as numpy array (float32, 24kHz)
    """
    import numpy as np

    kokoro = get_kokoro()
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed)

    return np.array(samples, dtype=np.float32)


def render_script(
    input_file: str,
    output_file: str,
    voice: str = 'af_heart',
    speed: float = 1.0,
    verbose: bool = True
) -> bool:
    """Render a script file to audio using Kokoro.

    Handles pause markers [Xms] by inserting silence.
    """
    import numpy as np
    sf = get_soundfile()

    # Determine language from voice
    if voice in VOICES:
        lang_code = VOICES[voice][0]
    else:
        lang_code = 'a'

    # Read script
    with open(input_file) as f:
        text = f.read()

    # Parse into segments with pauses
    segments = convert_pauses_to_silence(text)

    if verbose:
        print(f"Processing {len(segments)} segments...")

    # Render each segment
    audio_parts = []

    for i, (segment_text, pause_after) in enumerate(segments):
        if verbose:
            preview = segment_text[:50] + '...' if len(segment_text) > 50 else segment_text
            print(f"  [{i+1}/{len(segments)}] {preview}")

        # Chunk long segments
        chunks = chunk_text(segment_text)

        for chunk in chunks:
            if chunk.strip():
                audio = render_text(chunk, voice=voice, speed=speed, lang_code=lang_code)
                if len(audio) > 0:
                    audio_parts.append(audio)

        # Add silence after segment if specified
        if pause_after is not None and pause_after > 0:
            silence = generate_silence(pause_after)
            audio_parts.append(silence)

    if not audio_parts:
        print("Error: No audio generated", file=sys.stderr)
        return False

    # Concatenate all audio
    full_audio = np.concatenate(audio_parts)

    # Determine output format from extension
    ext = Path(output_file).suffix.lower()

    if ext == '.wav':
        sf.write(output_file, full_audio, SAMPLE_RATE)
    elif ext in ('.mp3', '.ogg'):
        # Need pydub for compressed formats
        try:
            from pydub import AudioSegment
            import io

            # Convert to int16 for pydub
            audio_int16 = (full_audio * 32767).astype(np.int16)

            # Create AudioSegment
            audio_segment = AudioSegment(
                audio_int16.tobytes(),
                frame_rate=SAMPLE_RATE,
                sample_width=2,
                channels=1
            )

            if ext == '.mp3':
                audio_segment.export(output_file, format='mp3', bitrate='192k')
            else:
                audio_segment.export(output_file, format='ogg')
        except ImportError:
            print(f"Warning: pydub not installed, saving as WAV instead", file=sys.stderr)
            wav_path = str(Path(output_file).with_suffix('.wav'))
            sf.write(wav_path, full_audio, SAMPLE_RATE)
            output_file = wav_path
    else:
        # Default to WAV
        sf.write(output_file, full_audio, SAMPLE_RATE)

    if verbose:
        duration = len(full_audio) / SAMPLE_RATE
        print(f"Done: {output_file} ({duration:.1f}s)")

    return True


def render_batch(
    input_dir: str,
    output_dir: str,
    voice: str = 'af_heart',
    speed: float = 1.0,
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
        wav_file = output_path / f"{txt_file.stem}.wav"
        if verbose:
            print(f"\n=== {txt_file.name} ===")
        if not render_script(str(txt_file), str(wav_file), voice, speed, verbose):
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Render text to audio using Kokoro 82M TTS (local)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voices (American English):
  af_heart    Female - warm, expressive (default)
  af_bella    Female - clear, neutral
  af_nicole   Female - professional
  af_sarah    Female - friendly
  af_sky      Female - bright
  am_adam     Male - deep, calm
  am_michael  Male - neutral

Voices (British English):
  bf_emma, bf_isabella, bm_george, bm_lewis

Examples:
  %(prog)s script.txt output.wav
  %(prog)s script.txt output.mp3 --voice am_adam
  %(prog)s scripts/ audio/ --batch

Installation:
  pip install kokoro>=0.9.4 soundfile
  apt-get install espeak-ng  # Linux/WSL
"""
    )
    parser.add_argument("input", help="Input text file or directory (with --batch)")
    parser.add_argument("output", help="Output audio file or directory (with --batch)")
    parser.add_argument("--voice", "-v", default="af_heart",
                       help="Voice name (default: af_heart)")
    parser.add_argument("--speed", "-s", type=float, default=1.0,
                       help="Speech speed multiplier (default: 1.0)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Batch mode: process all .txt files in input directory")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")
    parser.add_argument("--list-voices", action="store_true",
                       help="List available voices and exit")

    args = parser.parse_args()

    if args.list_voices:
        print("Available voices:")
        for voice, (lang, desc) in VOICES.items():
            lang_name = "American" if lang == 'a' else "British"
            print(f"  {voice:15} {lang_name:10} {desc}")
        sys.exit(0)

    if args.batch:
        if not os.path.isdir(args.input):
            print(f"Error: {args.input} is not a directory (required for --batch)", file=sys.stderr)
            sys.exit(1)
        success = render_batch(
            args.input,
            args.output,
            voice=args.voice,
            speed=args.speed,
            verbose=not args.quiet
        )
    else:
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        success = render_script(
            args.input,
            args.output,
            voice=args.voice,
            speed=args.speed,
            verbose=not args.quiet
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
