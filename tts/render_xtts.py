#!/usr/bin/env python3
"""
render_xtts.py
--------------
Render text to audio using Coqui XTTS v2 (local, voice cloning capable).

XTTS v2 is a multilingual TTS model that can clone voices from a 6-second sample.
Requires a GPU with 8GB+ VRAM for best performance.

Usage:
    python render_xtts.py input.txt output.wav --speaker reference.wav
    python render_xtts.py input.txt output.wav --speaker voices/goddess.wav --language en
    python render_xtts.py scripts/ audio/ --batch --speaker reference.wav

Installation:
    pip install coqui-tts torch

Supported Languages:
    en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko, hi

See: https://huggingface.co/coqui/XTTS-v2
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Lazy imports
_tts = None
_torch = None


def get_device():
    """Get best available device."""
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return "cuda" if _torch.cuda.is_available() else "cpu"


def get_tts():
    """Lazy-load TTS model."""
    global _tts
    if _tts is None:
        # Auto-accept CPML license (non-commercial)
        os.environ["COQUI_TOS_AGREED"] = "1"

        try:
            from TTS.api import TTS
            device = get_device()
            print(f"Loading XTTS v2 on {device}...")
            _tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            print("Model loaded.")
        except ImportError:
            print("Error: coqui-tts not installed. Run: pip install coqui-tts", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error loading XTTS model: {e}", file=sys.stderr)
            sys.exit(1)
    return _tts


# Supported languages
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'pl': 'Polish',
    'tr': 'Turkish',
    'ru': 'Russian',
    'nl': 'Dutch',
    'cs': 'Czech',
    'ar': 'Arabic',
    'zh-cn': 'Chinese',
    'ja': 'Japanese',
    'hu': 'Hungarian',
    'ko': 'Korean',
    'hi': 'Hindi',
}

# Pause pattern
PAUSE_PATTERN = re.compile(r'\[(\d+(?:\.\d+)?)(s|ms)?\]')

# XTTS sample rate
SAMPLE_RATE = 24000


def convert_pauses_to_silence(text: str) -> list[tuple[str, Optional[float]]]:
    """Convert text with pause markers to segments with silence durations."""
    # Remove HTML comments
    text = re.sub(r'<!--[^>]*-->', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    segments = []
    last_end = 0

    for match in PAUSE_PATTERN.finditer(text):
        segment_text = text[last_end:match.start()].strip()

        value = float(match.group(1))
        unit = match.group(2) or 'ms'
        pause_sec = value if unit == 's' else value / 1000

        if segment_text:
            segments.append((segment_text, pause_sec))
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        segments.append((remaining, None))

    if not segments:
        segments = [(text.strip(), None)]

    return segments


def chunk_text(text: str, max_chars: int = 250) -> list[str]:
    """Split text into chunks. XTTS works best with shorter segments."""
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
    speaker_wav: str,
    language: str = 'en'
) -> 'np.ndarray':
    """Render text to audio using XTTS with voice cloning.

    Args:
        text: Text to synthesize
        speaker_wav: Path to reference audio for voice cloning (6+ seconds recommended)
        language: Language code

    Returns:
        Audio as numpy array
    """
    import numpy as np

    tts = get_tts()
    wav = tts.tts(text=text, speaker_wav=speaker_wav, language=language)

    return np.array(wav, dtype=np.float32)


def render_script(
    input_file: str,
    output_file: str,
    speaker_wav: str,
    language: str = 'en',
    verbose: bool = True
) -> bool:
    """Render a script file to audio using XTTS v2."""
    import numpy as np

    if not os.path.exists(speaker_wav):
        print(f"Error: Speaker reference not found: {speaker_wav}", file=sys.stderr)
        return False

    # Read script
    with open(input_file) as f:
        text = f.read()

    # Parse segments
    segments = convert_pauses_to_silence(text)

    if verbose:
        print(f"Processing {len(segments)} segments with voice from {speaker_wav}...")

    audio_parts = []

    for i, (segment_text, pause_after) in enumerate(segments):
        if verbose:
            preview = segment_text[:50] + '...' if len(segment_text) > 50 else segment_text
            print(f"  [{i+1}/{len(segments)}] {preview}")

        # Chunk long segments
        chunks = chunk_text(segment_text)

        for chunk in chunks:
            if chunk.strip():
                try:
                    audio = render_text(chunk, speaker_wav, language)
                    if len(audio) > 0:
                        audio_parts.append(audio)
                except Exception as e:
                    print(f"Warning: Failed to render chunk: {e}", file=sys.stderr)

        # Add silence
        if pause_after is not None and pause_after > 0:
            silence = generate_silence(pause_after)
            audio_parts.append(silence)

    if not audio_parts:
        print("Error: No audio generated", file=sys.stderr)
        return False

    # Concatenate
    full_audio = np.concatenate(audio_parts)

    # Save
    ext = Path(output_file).suffix.lower()

    if ext == '.wav':
        try:
            import soundfile as sf
            sf.write(output_file, full_audio, SAMPLE_RATE)
        except ImportError:
            from scipy.io import wavfile
            audio_int16 = (full_audio * 32767).astype(np.int16)
            wavfile.write(output_file, SAMPLE_RATE, audio_int16)
    elif ext in ('.mp3', '.ogg'):
        try:
            from pydub import AudioSegment

            audio_int16 = (full_audio * 32767).astype(np.int16)
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
            print(f"Warning: pydub not installed, saving as WAV", file=sys.stderr)
            from scipy.io import wavfile
            audio_int16 = (full_audio * 32767).astype(np.int16)
            wav_path = str(Path(output_file).with_suffix('.wav'))
            wavfile.write(wav_path, SAMPLE_RATE, audio_int16)
            output_file = wav_path
    else:
        from scipy.io import wavfile
        audio_int16 = (full_audio * 32767).astype(np.int16)
        wavfile.write(output_file, SAMPLE_RATE, audio_int16)

    if verbose:
        duration = len(full_audio) / SAMPLE_RATE
        print(f"Done: {output_file} ({duration:.1f}s)")

    return True


def render_batch(
    input_dir: str,
    output_dir: str,
    speaker_wav: str,
    language: str = 'en',
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
        if not render_script(str(txt_file), str(wav_file), speaker_wav, language, verbose):
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Render text to audio using XTTS v2 (local, voice cloning)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Languages:
  en (English), es (Spanish), fr (French), de (German), it (Italian),
  pt (Portuguese), pl (Polish), tr (Turkish), ru (Russian), nl (Dutch),
  cs (Czech), ar (Arabic), zh-cn (Chinese), ja (Japanese), hu (Hungarian),
  ko (Korean), hi (Hindi)

Examples:
  %(prog)s script.txt output.wav --speaker reference.wav
  %(prog)s script.txt output.mp3 --speaker voices/goddess.wav --language en
  %(prog)s scripts/ audio/ --batch --speaker reference.wav

Requirements:
  - GPU with 8GB+ VRAM recommended
  - Speaker reference audio (6+ seconds, clean speech)

Installation:
  pip install coqui-tts torch
"""
    )
    parser.add_argument("input", help="Input text file or directory (with --batch)")
    parser.add_argument("output", help="Output audio file or directory (with --batch)")
    parser.add_argument("--speaker", "-s", required=True,
                       help="Speaker reference audio file for voice cloning (required)")
    parser.add_argument("--language", "-l", default="en",
                       choices=list(LANGUAGES.keys()),
                       help="Language code (default: en)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Batch mode: process all .txt files in input directory")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")
    parser.add_argument("--list-languages", action="store_true",
                       help="List supported languages and exit")

    args = parser.parse_args()

    if args.list_languages:
        print("Supported languages:")
        for code, name in LANGUAGES.items():
            print(f"  {code:8} {name}")
        sys.exit(0)

    if args.batch:
        if not os.path.isdir(args.input):
            print(f"Error: {args.input} is not a directory (required for --batch)", file=sys.stderr)
            sys.exit(1)
        success = render_batch(
            args.input,
            args.output,
            speaker_wav=args.speaker,
            language=args.language,
            verbose=not args.quiet
        )
    else:
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        success = render_script(
            args.input,
            args.output,
            speaker_wav=args.speaker,
            language=args.language,
            verbose=not args.quiet
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
