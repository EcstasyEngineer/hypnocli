#!/usr/bin/env python3
"""
render_vibevoice.py
-------------------
Render text to audio using Microsoft VibeVoice 1.5B (local).

VibeVoice is designed for expressive, long-form, multi-speaker conversational audio.
Uses Qwen2.5-1.5B as its LLM base. Fits in 6GB VRAM.

Usage:
    python render_vibevoice.py input.txt output.wav
    python render_vibevoice.py input.txt output.wav --voice Andrew
    python render_vibevoice.py scripts/ audio/ --batch

Installation:
    git clone https://github.com/vibevoice-community/VibeVoice /tmp/VibeVoice
    pip install -e /tmp/VibeVoice

    # Model downloads automatically on first run (~3GB)

Available voices (from demo/voices/):
    Andrew, Ava, Brian, Emma, etc. (depends on what's in voices folder)

See: https://huggingface.co/microsoft/VibeVoice-1.5B
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

# Pause pattern
PAUSE_PATTERN = re.compile(r'\[(\d+(?:\.\d+)?)(s|ms)?\]')

# VibeVoice sample rate
SAMPLE_RATE = 24000

# Lazy imports
_model = None
_processor = None


def check_vibevoice_installed():
    """Check if VibeVoice is installed."""
    try:
        from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
        from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
        return True
    except ImportError:
        return False


def get_model_and_processor(model_path: str = "microsoft/VibeVoice-1.5B", device: str = None):
    """Lazy-load VibeVoice model and processor."""
    global _model, _processor

    if _model is None or _processor is None:
        import torch
        from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
        from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"Loading VibeVoice from {model_path} on {device}...")

        _processor = VibeVoiceProcessor.from_pretrained(model_path)

        # Device-specific loading
        if device == "cuda":
            load_dtype = torch.bfloat16
            try:
                _model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                    model_path,
                    torch_dtype=load_dtype,
                    device_map="cuda",
                    attn_implementation="flash_attention_2",
                )
            except Exception:
                print("Flash attention not available, using SDPA...")
                _model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                    model_path,
                    torch_dtype=load_dtype,
                    device_map="cuda",
                    attn_implementation="sdpa",
                )
        else:
            load_dtype = torch.float32
            _model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                model_path,
                torch_dtype=load_dtype,
                device_map="cpu",
                attn_implementation="sdpa",
            )

        _model.eval()
        _model.set_ddpm_inference_steps(num_steps=10)
        print("Model loaded.")

    return _model, _processor


def get_voice_path(voice_name: str) -> Optional[str]:
    """Find voice sample file for given voice name."""
    # Check common locations
    search_paths = [
        Path("/tmp/VibeVoice/demo/voices"),
        Path.home() / ".cache" / "vibevoice" / "voices",
        Path(__file__).parent / "voices",
    ]

    for base_path in search_paths:
        if not base_path.exists():
            continue

        # Try exact match
        for ext in ['.wav', '.mp3', '.flac']:
            voice_file = base_path / f"{voice_name}{ext}"
            if voice_file.exists():
                return str(voice_file)

        # Try case-insensitive match
        for f in base_path.iterdir():
            if f.stem.lower() == voice_name.lower() and f.suffix.lower() in ['.wav', '.mp3', '.flac']:
                return str(f)

    return None


def list_available_voices() -> list[str]:
    """List available voice presets."""
    voices = []
    search_paths = [
        Path("/tmp/VibeVoice/demo/voices"),
        Path.home() / ".cache" / "vibevoice" / "voices",
    ]

    for base_path in search_paths:
        if base_path.exists():
            for f in base_path.iterdir():
                if f.suffix.lower() in ['.wav', '.mp3', '.flac']:
                    voices.append(f.stem)

    return sorted(set(voices))


def convert_to_vibevoice_format(text: str, speaker_name: str = "Speaker") -> str:
    """Convert text with pause markers to VibeVoice format.

    VibeVoice expects "Speaker X: text" format.
    Pauses are converted to natural language markers or ellipses.
    """
    # Remove HTML comments
    text = re.sub(r'<!--[^>]*-->', '', text)
    # Remove SSML/prosody tags (keep inner content)
    text = re.sub(r'<[^>]+>', '', text)

    # Convert pause markers to ellipses/natural breaks
    def replace_pause(match):
        value = float(match.group(1))
        unit = match.group(2) or 'ms'
        ms = value * 1000 if unit == 's' else value

        if ms <= 300:
            return "..."
        elif ms <= 700:
            return "... ..."
        else:
            return "\n\n"

    text = PAUSE_PATTERN.sub(replace_pause, text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    # Format as Speaker 1: text (single speaker)
    # VibeVoice expects this format
    formatted = f"Speaker 1: {text}"

    return formatted


def render_script(
    input_file: str,
    output_file: str,
    voice: str = "Andrew",
    model_path: str = "microsoft/VibeVoice-1.5B",
    verbose: bool = True
) -> bool:
    """Render a script file to audio using VibeVoice."""
    import torch

    if not check_vibevoice_installed():
        print("Error: VibeVoice not installed.", file=sys.stderr)
        print("Installation:", file=sys.stderr)
        print("  git clone https://github.com/vibevoice-community/VibeVoice /tmp/VibeVoice", file=sys.stderr)
        print("  pip install -e /tmp/VibeVoice", file=sys.stderr)
        return False

    # Find voice sample
    voice_path = get_voice_path(voice)
    if not voice_path:
        available = list_available_voices()
        print(f"Error: Voice '{voice}' not found.", file=sys.stderr)
        if available:
            print(f"Available voices: {', '.join(available)}", file=sys.stderr)
        else:
            print("No voice samples found. Check /tmp/VibeVoice/demo/voices/", file=sys.stderr)
        return False

    if verbose:
        print(f"Using voice: {voice} ({voice_path})")

    # Read and convert script
    with open(input_file) as f:
        text = f.read()

    formatted_text = convert_to_vibevoice_format(text)

    if verbose:
        preview = formatted_text[:200] + '...' if len(formatted_text) > 200 else formatted_text
        print(f"Text preview: {preview}")

    # Load model
    model, processor = get_model_and_processor(model_path)
    device = next(model.parameters()).device

    # Prepare inputs
    inputs = processor(
        text=[formatted_text],
        voice_samples=[[voice_path]],
        padding=True,
        return_tensors="pt",
        return_attention_mask=True,
    )

    # Move to device
    for k, v in inputs.items():
        if torch.is_tensor(v):
            inputs[k] = v.to(device)

    if verbose:
        print("Generating audio...")

    # Generate
    start_time = time.time()
    outputs = model.generate(
        **inputs,
        max_new_tokens=None,
        cfg_scale=1.3,
        tokenizer=processor.tokenizer,
        generation_config={'do_sample': False},
        verbose=verbose,
        is_prefill=True,
    )
    generation_time = time.time() - start_time

    if not outputs.speech_outputs or outputs.speech_outputs[0] is None:
        print("Error: No audio generated", file=sys.stderr)
        return False

    # Calculate duration
    audio_samples = outputs.speech_outputs[0].shape[-1]
    audio_duration = audio_samples / SAMPLE_RATE

    if verbose:
        print(f"Generation time: {generation_time:.2f}s")
        print(f"Audio duration: {audio_duration:.2f}s")
        print(f"RTF: {generation_time / audio_duration:.2f}x")

    # Save output
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    processor.save_audio(outputs.speech_outputs[0], output_path=output_file)

    if verbose:
        print(f"Done: {output_file}")

    return True


def render_batch(
    input_dir: str,
    output_dir: str,
    voice: str = "Andrew",
    model_path: str = "microsoft/VibeVoice-1.5B",
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
        if not render_script(str(txt_file), str(wav_file), voice, model_path, verbose):
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Render text to audio using Microsoft VibeVoice 1.5B (local)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s script.txt output.wav
  %(prog)s script.txt output.wav --voice Andrew
  %(prog)s scripts/ audio/ --batch

Requirements:
  - GPU with 6GB+ VRAM (or CPU with patience)
  - VibeVoice installed from GitHub

Installation:
  git clone https://github.com/vibevoice-community/VibeVoice /tmp/VibeVoice
  pip install -e /tmp/VibeVoice

Note: Supports English and Chinese only.
"""
    )
    parser.add_argument("input", nargs='?', help="Input text file or directory (with --batch)")
    parser.add_argument("output", nargs='?', help="Output audio file or directory (with --batch)")
    parser.add_argument("--voice", "-v", default="Andrew",
                       help="Voice name (default: Andrew)")
    parser.add_argument("--model", "-m", default="microsoft/VibeVoice-1.5B",
                       help="Model path (HuggingFace or local)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Batch mode: process all .txt files in input directory")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")
    parser.add_argument("--list-voices", action="store_true",
                       help="List available voices and exit")

    args = parser.parse_args()

    if args.list_voices:
        voices = list_available_voices()
        if voices:
            print("Available voices:")
            for v in voices:
                print(f"  {v}")
        else:
            print("No voices found. Check /tmp/VibeVoice/demo/voices/")
        sys.exit(0)

    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)

    if args.batch:
        if not os.path.isdir(args.input):
            print(f"Error: {args.input} is not a directory (required for --batch)", file=sys.stderr)
            sys.exit(1)
        success = render_batch(
            args.input,
            args.output,
            voice=args.voice,
            model_path=args.model,
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
            model_path=args.model,
            verbose=not args.quiet
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
