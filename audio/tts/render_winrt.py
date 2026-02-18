#!/usr/bin/env python3
"""
render_winrt.py
---------------
Render text to audio using Microsoft WinRT speech voices (Windows only).

Uses the Windows.Media.SpeechSynthesis API to access all installed
voices including OneCore (Susan, Mark, Jenny, etc.).

Usage:
    python render_winrt.py input.txt output.wav
    python render_winrt.py input.txt output.wav --voice Susan
    python render_winrt.py input.txt output.wav --voice David
    python render_winrt.py --list-voices

Requirements:
    Windows with Python 3.9+. Install WinRT bindings:
    pip install winrt-runtime winrt-Windows.Media.SpeechSynthesis winrt-Windows.Storage.Streams

Run from PowerShell or cmd, NOT WSL. No API key needed.
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path


def strip_markup(text: str) -> str:
    """Remove markup from text, keeping content."""
    text = re.sub(r'<!--[^>]*-->', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[(\d+(?:\.\d+)?)(s|ms)?\]', '...', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _check_deps():
    """Check WinRT dependencies are installed."""
    try:
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
        return True
    except ImportError:
        print(
            "Error: WinRT bindings not installed. Run:\n"
            "  pip install winrt-runtime "
            "winrt-Windows.Media.SpeechSynthesis "
            "winrt-Windows.Storage.Streams",
            file=sys.stderr,
        )
        return False


def list_voices():
    """List all installed voices."""
    if not _check_deps():
        sys.exit(1)

    from winrt.windows.media.speechsynthesis import SpeechSynthesizer

    voices = SpeechSynthesizer.all_voices
    print(f"Installed voices ({len(voices)}):")
    for v in voices:
        gender = 'Male' if v.gender == 0 else 'Female'
        print(f"  {v.display_name:30} {v.language:10} {gender}")


async def _synthesize(text: str, voice_name: str = None) -> bytes:
    """Synthesize text to WAV bytes using WinRT."""
    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    from winrt.windows.storage.streams import DataReader

    synth = SpeechSynthesizer()

    if voice_name:
        name_lower = voice_name.lower()
        match = None
        # Exact display name first
        for v in SpeechSynthesizer.all_voices:
            if v.display_name.lower() == name_lower:
                match = v
                break
        # Partial match
        if match is None:
            for v in SpeechSynthesizer.all_voices:
                if name_lower in v.display_name.lower():
                    match = v
                    break
        if match is None:
            raise ValueError(f"Voice '{voice_name}' not found")
        synth.voice = match

    stream = await synth.synthesize_text_to_stream_async(text)

    reader = DataReader(stream)
    await reader.load_async(stream.size)
    buf = reader.read_buffer(stream.size)

    return bytes(buf)


def render_script(
    input_file: str,
    output_file: str,
    voice_name: str = None,
    verbose: bool = True,
) -> bool:
    """Render a script file to WAV."""
    if not _check_deps():
        return False

    with open(input_file) as f:
        text = f.read()
    text = strip_markup(text)

    if verbose:
        preview = text[:80] + '...' if len(text) > 80 else text
        print(f"Text: {preview}")
        if voice_name:
            print(f"Voice: {voice_name}")

    try:
        wav_data = asyncio.run(_synthesize(text, voice_name))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run --list-voices to see available voices.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error during synthesis: {e}", file=sys.stderr)
        return False

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'wb') as f:
        f.write(wav_data)

    if verbose:
        size_kb = len(wav_data) / 1024
        # WAV header tells us format, but rough estimate: 16-bit mono 22050Hz
        duration = (len(wav_data) - 44) / (2 * 22050)
        print(f"Done: {output_file} (~{duration:.1f}s, {size_kb:.0f}KB)")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Render text to audio using Microsoft voices (Windows)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voices:
  All installed Windows voices are available, including OneCore
  voices (Susan, Mark, Jenny, etc.) from Windows 10/11.

Examples:
  %(prog)s script.txt out.wav --voice Susan
  %(prog)s script.txt out.wav --voice David
  %(prog)s --list-voices

Requirements:
  pip install winrt-runtime winrt-Windows.Media.SpeechSynthesis winrt-Windows.Storage.Streams

Must be run on Windows (not WSL). No API key needed.
""",
    )
    parser.add_argument('input', nargs='?', help='Input text file')
    parser.add_argument('output', nargs='?', help='Output WAV file')
    parser.add_argument('--voice', '-v', default=None,
                        help='Voice name or partial match (e.g., "Susan")')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress output')
    parser.add_argument('--list-voices', action='store_true',
                        help='List installed voices and exit')

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        sys.exit(0)

    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f'Error: Input file not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    success = render_script(
        args.input,
        args.output,
        voice_name=args.voice,
        verbose=not args.quiet,
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
