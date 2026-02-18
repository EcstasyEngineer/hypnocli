#!/usr/bin/env python3
"""
render_qwen3.py
---------------
Render text to audio using Qwen3-TTS (local, GPU recommended).

Qwen3-TTS supports:
- Voice cloning from reference audio (Base model)
- Text description of voices (VoiceDesign model)
- Custom voice presets (CustomVoice model)

Usage:
    # Voice cloning (requires reference audio + transcription)
    python render_qwen3.py script.txt output.wav --ref-audio ref.wav --ref-text "Reference text"

    # Voice design (describe the voice in natural language)
    python render_qwen3.py script.txt output.wav --voice-design "A warm female voice, speaking slowly"

    # Custom voice (9 built-in premium voices)
    python render_qwen3.py script.txt output.wav --speaker Ryan

Requirements:
    pip install qwen-tts soundfile

    # IMPORTANT: Requires SoX for audio processing
    # Linux: sudo apt-get install sox libsox-fmt-all
    # macOS: brew install sox

    # For faster inference (recommended):
    pip install flash-attn --no-build-isolation

Available CustomVoice speakers:
    English: Ryan, Laura
    Chinese: Chelsie, Ethan
    (More available - check model docs)

See: https://github.com/QwenLM/Qwen3-TTS
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

# Pause pattern from our markup system
PAUSE_PATTERN = re.compile(r'\[(\d+(?:\.\d+)?)(s|ms)?\]')

# Sample rate
SAMPLE_RATE = 24000

# Lazy imports
_model = None


def check_sox():
    """Check if SoX is installed."""
    import shutil
    if not shutil.which('sox'):
        print("Error: SoX is required but not found.", file=sys.stderr)
        print("Install with: sudo apt-get install sox libsox-fmt-all", file=sys.stderr)
        return False
    return True


def get_model(model_type: str = "voicedesign"):
    """Lazy-load Qwen3-TTS model."""
    global _model

    if _model is not None:
        return _model

    import torch
    from qwen_tts import Qwen3TTSModel

    model_map = {
        "base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "base-1.7b": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "voicedesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "customvoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    }

    model_name = model_map.get(model_type, model_type)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    print(f"Loading {model_name} on {device}...")

    _model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=device,
        dtype=dtype,
    )

    print("Model loaded.")
    return _model


def strip_markup(text: str) -> str:
    """Remove markup from text, keeping content."""
    # Remove HTML comments
    text = re.sub(r'<!--[^>]*-->', '', text)
    # Remove SSML/prosody tags (keep inner content)
    text = re.sub(r'<[^>]+>', '', text)
    # Convert pause markers to ellipses
    text = PAUSE_PATTERN.sub('...', text)
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def render_voice_design(
    text: str,
    instruct: str,
    language: str = "English",
    verbose: bool = True
) -> tuple:
    """Generate audio using voice description."""
    model = get_model("voicedesign")

    if verbose:
        print(f"Generating with instruction: {instruct[:50]}...")

    start = time.time()
    wavs, sr = model.generate_voice_design(
        text=text,
        language=language,
        instruct=instruct,
    )
    elapsed = time.time() - start

    if verbose:
        print(f"Generated in {elapsed:.1f}s")

    return wavs[0], sr


def render_custom_voice(
    text: str,
    speaker: str = "Ryan",
    language: str = "English",
    verbose: bool = True
) -> tuple:
    """Generate audio using built-in voice preset."""
    model = get_model("customvoice")

    if verbose:
        print(f"Generating with speaker: {speaker}")

    start = time.time()
    wavs, sr = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
    )
    elapsed = time.time() - start

    if verbose:
        print(f"Generated in {elapsed:.1f}s")

    return wavs[0], sr


def render_voice_clone(
    text: str,
    ref_audio: str,
    ref_text: str = None,
    language: str = "English",
    verbose: bool = True
) -> tuple:
    """Generate audio cloning a reference voice."""
    model = get_model("base")

    if verbose:
        print(f"Cloning voice from: {ref_audio}")

    start = time.time()

    if ref_text:
        # ICL mode (in-context learning) - better quality
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=False,
        )
    else:
        # X-vector only mode - no transcription needed
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            x_vector_only_mode=True,
        )

    elapsed = time.time() - start

    if verbose:
        print(f"Generated in {elapsed:.1f}s")

    return wavs[0], sr


def render_script(
    input_file: str,
    output_file: str,
    mode: str = "voicedesign",
    instruct: str = None,
    speaker: str = "Ryan",
    ref_audio: str = None,
    ref_text: str = None,
    language: str = "English",
    verbose: bool = True
) -> bool:
    """Render a script file to audio."""
    import soundfile as sf

    if not check_sox():
        return False

    # Read and clean script
    with open(input_file) as f:
        text = f.read()

    text = strip_markup(text)

    if verbose:
        preview = text[:100] + '...' if len(text) > 100 else text
        print(f"Text: {preview}")

    # Generate based on mode
    if mode == "voicedesign":
        if not instruct:
            instruct = "A clear, natural voice"
        audio, sr = render_voice_design(text, instruct, language, verbose)
    elif mode == "customvoice":
        audio, sr = render_custom_voice(text, speaker, language, verbose)
    elif mode == "clone":
        if not ref_audio:
            print("Error: --ref-audio required for clone mode", file=sys.stderr)
            return False
        audio, sr = render_voice_clone(text, ref_audio, ref_text, language, verbose)
    else:
        print(f"Error: Unknown mode: {mode}", file=sys.stderr)
        return False

    # Save output
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    sf.write(output_file, audio, sr)

    if verbose:
        duration = len(audio) / sr
        print(f"Done: {output_file} ({duration:.1f}s)")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Render text to audio using Qwen3-TTS (local)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --voice-design "description"    Use natural language to describe the voice
  --speaker NAME                  Use a built-in voice preset
  --ref-audio FILE                Clone a voice from reference audio

Examples:
  %(prog)s script.txt out.wav --voice-design "A warm female voice"
  %(prog)s script.txt out.wav --speaker Ryan
  %(prog)s script.txt out.wav --ref-audio ref.wav --ref-text "Hello world"

Requirements:
  - SoX: sudo apt-get install sox libsox-fmt-all
  - GPU with 6GB+ VRAM recommended
"""
    )
    parser.add_argument("input", nargs='?', help="Input text file")
    parser.add_argument("output", nargs='?', help="Output audio file")
    parser.add_argument("--voice-design", "-d", dest="instruct",
                       help="Voice description for VoiceDesign mode")
    parser.add_argument("--speaker", "-s", default="Ryan",
                       help="Speaker name for CustomVoice mode")
    parser.add_argument("--ref-audio", "-r", help="Reference audio for cloning")
    parser.add_argument("--ref-text", "-t", help="Transcription of reference audio")
    parser.add_argument("--language", "-l", default="English",
                       help="Language (default: English)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")

    args = parser.parse_args()

    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Determine mode
    if args.instruct:
        mode = "voicedesign"
    elif args.ref_audio:
        mode = "clone"
    else:
        mode = "customvoice"

    success = render_script(
        args.input,
        args.output,
        mode=mode,
        instruct=args.instruct,
        speaker=args.speaker,
        ref_audio=args.ref_audio,
        ref_text=args.ref_text,
        language=args.language,
        verbose=not args.quiet,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
