#!/usr/bin/env python3
"""
render_gemini.py
----------------
Render text to audio using Gemini 2.5 Flash TTS (API).

Uses the Google GenAI SDK with an API key. Supports voice selection
and natural-language style instructions for controlling tone, pace,
and expression.

Usage:
    python render_gemini.py input.txt output.wav
    python render_gemini.py input.txt output.wav --voice Kore
    python render_gemini.py input.txt output.wav --instruct "speak in a hypnotic whisper"

Requirements:
    No dependencies beyond stdlib. Set GEMINI_API_KEY in .env or environment.

Voices (30 available):
    Kore, Puck, Charon, Fenrir, Leda, Orus, Aoede, Callirrhoe,
    Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina,
    Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam,
    Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi,
    Vindemiatrix, Sadachbia, Sadaltager, Sulafat, Zephyr

See: https://ai.google.dev/gemini-api/docs/speech-generation
"""

import argparse
import os
import re
import sys
import wave
from pathlib import Path

SAMPLE_RATE = 24000

VOICES = [
    'Kore', 'Puck', 'Charon', 'Fenrir', 'Leda', 'Orus', 'Aoede',
    'Callirrhoe', 'Autonoe', 'Enceladus', 'Iapetus', 'Umbriel',
    'Algieba', 'Despina', 'Erinome', 'Algenib', 'Rasalgethi',
    'Laomedeia', 'Achernar', 'Alnilam', 'Schedar', 'Gacrux',
    'Pulcherrima', 'Achird', 'Zubenelgenubi', 'Vindemiatrix',
    'Sadachbia', 'Sadaltager', 'Sulafat', 'Zephyr',
]


def get_api_key() -> str:
    """Load API key from environment or .env file."""
    key = os.environ.get('GEMINI_API_KEY')
    if key:
        return key

    # Try loading from .env
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith('GEMINI_API_KEY='):
                return line.split('=', 1)[1].strip()

    print("Error: GEMINI_API_KEY not set. Add it to .env or environment.",
          file=sys.stderr)
    sys.exit(1)


def strip_markup(text: str) -> str:
    """Remove markup from text, keeping content."""
    text = re.sub(r'<!--[^>]*-->', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[(\d+(?:\.\d+)?)(s|ms)?\]', '...', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def render_text(
    text: str,
    voice: str = 'Kore',
    instruct: str = None,
) -> bytes:
    """Render text to PCM audio bytes using Gemini TTS.

    Args:
        text: Text to synthesize.
        voice: Voice name (e.g., 'Kore').
        instruct: Natural-language style instructions
                  (e.g., 'speak in a slow, hypnotic tone').

    Returns:
        Raw PCM audio bytes (16-bit, 24kHz, mono).
    """
    import base64
    import json
    import urllib.request

    # Build the content prompt with optional style instructions
    if instruct:
        prompt = f"[{instruct}] {text}"
    else:
        prompt = text

    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        'gemini-2.5-flash-preview-tts:generateContent'
        f'?key={get_api_key()}'
    )

    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'responseModalities': ['AUDIO'],
            'speechConfig': {
                'voiceConfig': {
                    'prebuiltVoiceConfig': {
                        'voiceName': voice,
                    }
                }
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())

    audio_b64 = body['candidates'][0]['content']['parts'][0]['inlineData']['data']
    return base64.b64decode(audio_b64)


def save_wav(filename: str, pcm_data: bytes):
    """Save raw PCM data as a WAV file."""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)


def render_script(
    input_file: str,
    output_file: str,
    voice: str = 'Kore',
    instruct: str = None,
    verbose: bool = True,
) -> bool:
    """Render a script file to audio using Gemini TTS."""
    with open(input_file) as f:
        text = f.read()

    text = strip_markup(text)

    if verbose:
        preview = text[:80] + '...' if len(text) > 80 else text
        print(f"Text: {preview}")
        print(f"Voice: {voice}")
        if instruct:
            print(f"Style: {instruct}")

    try:
        pcm_data = render_text(text, voice=voice, instruct=instruct)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

    ext = Path(output_file).suffix.lower()

    if ext == '.wav':
        save_wav(output_file, pcm_data)
    elif ext in ('.mp3', '.ogg'):
        try:
            import numpy as np
            from pydub import AudioSegment

            audio_segment = AudioSegment(
                pcm_data,
                frame_rate=SAMPLE_RATE,
                sample_width=2,
                channels=1,
            )
            fmt = 'mp3' if ext == '.mp3' else 'ogg'
            bitrate = '192k' if ext == '.mp3' else '48k'
            audio_segment.export(output_file, format=fmt, bitrate=bitrate)
        except ImportError:
            print("Warning: pydub not installed, saving as WAV",
                  file=sys.stderr)
            wav_path = str(Path(output_file).with_suffix('.wav'))
            save_wav(wav_path, pcm_data)
            output_file = wav_path
    else:
        save_wav(output_file, pcm_data)

    if verbose:
        n_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
        duration = n_samples / SAMPLE_RATE
        print(f"Done: {output_file} ({duration:.1f}s)")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Render text to audio using Gemini 2.5 Flash TTS (API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voices (30 available):
  Kore, Puck, Charon, Fenrir, Leda, Orus, Aoede, Callirrhoe,
  Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina,
  Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam,
  Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi,
  Vindemiatrix, Sadachbia, Sadaltager, Sulafat, Zephyr

Examples:
  %(prog)s script.txt out.wav
  %(prog)s script.txt out.wav --voice Leda
  %(prog)s script.txt out.wav --instruct "speak in a hypnotic whisper"
  %(prog)s script.txt out.wav -v Aoede -i "slow, seductive, breathy"

Requires:
  GEMINI_API_KEY in .env or environment (no pip deps)
""",
    )
    parser.add_argument('input', help='Input text file')
    parser.add_argument('output', help='Output audio file (.wav, .mp3, .ogg)')
    parser.add_argument('--voice', '-v', default='Kore',
                        help='Voice name (default: Kore)')
    parser.add_argument('--instruct', '-i',
                        help='Style instructions (e.g., "speak slowly and softly")')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress output')
    parser.add_argument('--list-voices', action='store_true',
                        help='List available voices and exit')

    args = parser.parse_args()

    if args.list_voices:
        print('Available voices:')
        for v in VOICES:
            print(f'  {v}')
        sys.exit(0)

    if not os.path.exists(args.input):
        print(f'Error: Input file not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    success = render_script(
        args.input,
        args.output,
        voice=args.voice,
        instruct=args.instruct,
        verbose=not args.quiet,
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
