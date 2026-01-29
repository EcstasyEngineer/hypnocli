#!/usr/bin/env python3
"""
Binaural/Isochronic Generator

Generates entrainment audio using composable primitives:
- --add-iso: Add isochronic tone (carrier, pulse, amplitude, ear)
- --add-binaural: Add binaural pair (carrier, beat, amplitude)
- --preset: Use predefined configurations
- --json-input: Load timeline/sweep configuration from JSON
"""

import argparse
import json
import os
from dataclasses import dataclass
from fractions import Fraction
from math import gcd, lcm
from typing import Optional

import numpy as np
from scipy.io import wavfile

# Constants
SAMPLE_RATE = 44100
BIT_DEPTH = 16
MAX_INT16 = 32767


# === Data Structures ===

@dataclass
class ToneSpec:
    """Specification for a single tone (isochronic or continuous)."""
    carrier_hz: float
    pulse_hz: float  # 0 = continuous tone (no isochronic modulation)
    amplitude_db: float
    ear: str  # 'L', 'R', or 'LR' (both)


@dataclass
class LayerSpec:
    """Specification for a binaural layer (used with JSON timeline)."""
    name: str
    center_hz: float
    pulse_hz: float  # 0 = continuous tone
    amplitude_db: float


# === Presets ===

PRESETS = {
    'drone': [
        ToneSpec(310, 5.0, 0, 'L'),
        ToneSpec(314, 5.0, 0, 'R'),
        ToneSpec(58, 3.25, -6, 'L'),
        ToneSpec(62, 3.25, -6, 'R'),
    ],
}


# === Utility Functions ===

def db_to_linear(db: float) -> float:
    """Convert decibels to linear amplitude."""
    return 10 ** (db / 20)


def linear_to_db(linear: float) -> float:
    """Convert linear amplitude to decibels."""
    return 20 * np.log10(linear + 1e-10)


def apply_fade(signal_data: np.ndarray, fade_in_samples: int, fade_out_samples: int) -> np.ndarray:
    """Apply fade in/out to signal."""
    result = signal_data.copy()

    if fade_in_samples > 0:
        fade_in = np.linspace(0, 1, fade_in_samples)
        result[:fade_in_samples] *= fade_in

    if fade_out_samples > 0:
        fade_out = np.linspace(1, 0, fade_out_samples)
        result[-fade_out_samples:] *= fade_out

    return result


def normalize_to_db(signal_data: np.ndarray, target_db: float) -> np.ndarray:
    """Normalize signal to target RMS level in dB."""
    current_rms = np.sqrt(np.mean(signal_data ** 2))
    target_rms = db_to_linear(target_db) * MAX_INT16
    if current_rms > 0:
        return signal_data * (target_rms / current_rms)
    return signal_data


def isochronic_envelope(t: np.ndarray, rate: float, phase_offset: float = 0.0) -> np.ndarray:
    """
    Generate isochronic envelope using raised cosine.
    Returns values from 0 to 1.

    Args:
        t: Time array in seconds
        rate: Pulse rate in Hz
        phase_offset: Phase offset in radians (default 0)
    """
    return 0.5 * (1 + np.cos(2 * np.pi * rate * t + np.pi + phase_offset))


def sync_period(f1: float, f2: float, max_denom: int = 100) -> float:
    """
    Calculate the sync period between two frequencies.

    The sync period is the smallest time T where both f1*T and f2*T
    are whole numbers (i.e., both oscillators complete integer cycles).

    Args:
        f1: First frequency in Hz
        f2: Second frequency in Hz
        max_denom: Maximum denominator for fraction approximation

    Returns:
        Sync period in seconds
    """
    frac1 = Fraction(f1).limit_denominator(max_denom)
    frac2 = Fraction(f2).limit_denominator(max_denom)
    return lcm(frac1.denominator, frac2.denominator) / gcd(frac1.numerator, frac2.numerator)


def check_pulse_sync(pulse_rates: list[tuple[str, float]], min_sync_sec: float = 3.0) -> None:
    """
    Check all pairs of pulse rates and warn if any sync faster than min_sync_sec.

    Args:
        pulse_rates: List of (name, pulse_hz) tuples for isochronic layers
        min_sync_sec: Minimum acceptable sync period in seconds (default: 3.0)
    """
    # Filter to only isochronic (pulse > 0)
    iso_rates = [(name, rate) for name, rate in pulse_rates if rate > 0]

    if len(iso_rates) < 2:
        return

    warnings = []
    for i in range(len(iso_rates)):
        for j in range(i + 1, len(iso_rates)):
            name1, rate1 = iso_rates[i]
            name2, rate2 = iso_rates[j]
            period = sync_period(rate1, rate2)
            if period < min_sync_sec:
                warnings.append(f"  {name1} ({rate1} Hz) + {name2} ({rate2} Hz) sync every {period:.2f}s")

    if warnings:
        print(f"Warning: Isochronic layers sync faster than {min_sync_sec}s (may sound repetitive):")
        for w in warnings:
            print(w)
        print()


def interpolate_keyframes(keyframes: list[dict], duration_sec: float, sample_rate: int) -> np.ndarray:
    """
    Interpolate binaural_hz values across time from keyframes.

    Args:
        keyframes: List of {time_sec, binaural_hz} dicts
        duration_sec: Total duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Array of binaural_hz values for each sample
    """
    num_samples = int(sample_rate * duration_sec)
    t = np.arange(num_samples) / sample_rate

    # Sort keyframes by time
    sorted_kf = sorted(keyframes, key=lambda k: k['time_sec'])

    # Build interpolation arrays
    times = [kf['time_sec'] for kf in sorted_kf]
    values = [kf['binaural_hz'] for kf in sorted_kf]

    # Linear interpolation
    return np.interp(t, times, values)


# === Generator Functions ===

def generate_composite(
    tones: list[ToneSpec],
    duration_sec: float,
    fade_in_sec: float = 1.75,
    fade_out_sec: float = 1.75,
    sample_rate: int = SAMPLE_RATE,
    target_db: float = -28,
    interleave_ms: float = 100.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate composite audio from multiple tone specifications.

    Args:
        tones: List of ToneSpec objects defining each tone
        duration_sec: Duration in seconds
        fade_in_sec: Fade in time in seconds
        fade_out_sec: Fade out time in seconds
        sample_rate: Sample rate in Hz
        target_db: Target RMS level in dB
        interleave_ms: Phase offset for R channel isochronic envelopes in ms (default 100)
                       At 100ms with 5 Hz pulse, this creates 180-degree offset (alternating L/R)

    Returns:
        (left, right): Tuple of numpy arrays for stereo audio
    """
    # NOTE: In CLI mode (--add-iso), interleave_ms is applied uniformly to all R-channel tones.
    # This gives exact 180° only at 5 Hz; other frequencies get approximate offsets.
    # For precise 180° L/R alternation at any frequency, use JSON mode (generate_layered)
    # which automatically applies π radians offset within each layer.

    num_samples = int(sample_rate * duration_sec)
    t = np.arange(num_samples) / sample_rate

    left = np.zeros(num_samples)
    right = np.zeros(num_samples)

    for tone in tones:
        # Generate carrier
        carrier = np.sin(2 * np.pi * tone.carrier_hz * t)

        # Apply isochronic envelope if pulse_hz > 0
        if tone.pulse_hz > 0:
            # Apply phase offset for R channel to create L/R ping-pong effect
            # phase_offset = 2*pi*pulse_hz*(interleave_ms/1000)
            # At 100ms and 5 Hz: offset = pi (180°, perfect alternation)
            # At 100ms and 3.25 Hz: offset = 0.65*pi (~117°)
            if tone.ear == 'R':
                phase_offset = 2 * np.pi * tone.pulse_hz * (interleave_ms / 1000)
            else:
                phase_offset = 0.0
            envelope = isochronic_envelope(t, tone.pulse_hz, phase_offset)
            signal = carrier * envelope
        else:
            signal = carrier

        # Apply amplitude
        amplitude = db_to_linear(tone.amplitude_db)
        signal = signal * amplitude

        # Route to channels
        if tone.ear in ('L', 'LR'):
            left += signal
        if tone.ear in ('R', 'LR'):
            right += signal

    # Apply fades
    fade_in_samples = int(sample_rate * fade_in_sec)
    fade_out_samples = int(sample_rate * fade_out_sec)
    left = apply_fade(left, fade_in_samples, fade_out_samples)
    right = apply_fade(right, fade_in_samples, fade_out_samples)

    # Normalize to target level
    left = normalize_to_db(left, target_db)
    right = normalize_to_db(right, target_db)

    return left, right


def generate_layered(
    layers: list[LayerSpec],
    duration_sec: float,
    binaural_hz: Optional[float] = None,
    keyframes: Optional[list[dict]] = None,
    fade_in_sec: float = 1.75,
    fade_out_sec: float = 1.75,
    sample_rate: int = SAMPLE_RATE,
    target_db: float = -28,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate layered audio with dynamic binaural beat from JSON config.

    All layers share the same binaural beat (sweep in lockstep).
    Uses phase-continuous sine generation for smooth frequency sweeps.
    Isochronic envelopes automatically use 180° L/R phase offset for alternation.

    Args:
        layers: List of LayerSpec objects
        duration_sec: Duration in seconds
        binaural_hz: Static binaural beat (if no keyframes)
        keyframes: List of {time_sec, binaural_hz} for dynamic sweep
        fade_in_sec: Fade in time in seconds
        fade_out_sec: Fade out time in seconds
        sample_rate: Sample rate in Hz
        target_db: Target RMS level in dB

    Returns:
        (left, right): Tuple of numpy arrays for stereo audio
    """
    num_samples = int(sample_rate * duration_sec)
    t = np.arange(num_samples) / sample_rate

    # Get binaural offset per sample (static or interpolated from keyframes)
    if keyframes:
        binaural_values = interpolate_keyframes(keyframes, duration_sec, sample_rate)
    elif binaural_hz is not None:
        binaural_values = np.full(num_samples, binaural_hz)
    else:
        binaural_values = np.zeros(num_samples)

    left = np.zeros(num_samples)
    right = np.zeros(num_samples)

    for layer in layers:
        # Calculate instantaneous frequencies for L and R
        freq_l = layer.center_hz - binaural_values / 2
        freq_r = layer.center_hz + binaural_values / 2

        # Phase-continuous sine generation using cumulative sum
        # phase(t) = integral of 2*pi*freq(t)*dt
        phase_l = np.cumsum(2 * np.pi * freq_l / sample_rate)
        phase_r = np.cumsum(2 * np.pi * freq_r / sample_rate)

        carrier_l = np.sin(phase_l)
        carrier_r = np.sin(phase_r)

        # Apply isochronic envelope if pulse_hz > 0
        if layer.pulse_hz > 0:
            envelope_l = isochronic_envelope(t, layer.pulse_hz, phase_offset=0.0)
            # R channel gets π radians (180°) offset for perfect L/R alternation
            envelope_r = isochronic_envelope(t, layer.pulse_hz, phase_offset=np.pi)
            signal_l = carrier_l * envelope_l
            signal_r = carrier_r * envelope_r
        else:
            signal_l = carrier_l
            signal_r = carrier_r

        # Apply amplitude
        amplitude = db_to_linear(layer.amplitude_db)
        left += signal_l * amplitude
        right += signal_r * amplitude

    # Apply fades
    fade_in_samples = int(sample_rate * fade_in_sec)
    fade_out_samples = int(sample_rate * fade_out_sec)
    left = apply_fade(left, fade_in_samples, fade_out_samples)
    right = apply_fade(right, fade_in_samples, fade_out_samples)

    # Normalize to target level
    left = normalize_to_db(left, target_db)
    right = normalize_to_db(right, target_db)

    return left, right


# === Audio I/O ===

def save_audio(
    left: np.ndarray,
    right: np.ndarray,
    filepath: str,
    sample_rate: int = SAMPLE_RATE,
) -> None:
    """
    Save stereo audio to file. Format is auto-detected from extension.

    Supported formats:
    - .wav: Uncompressed WAV (16-bit, uses scipy)
    - .mp3: MP3 (192 kbps, requires pydub/ffmpeg)
    - .ogg: Ogg Vorbis (requires pydub/ffmpeg)

    Args:
        left: Left channel samples
        right: Right channel samples
        filepath: Output file path
        sample_rate: Sample rate in Hz
    """
    ext = os.path.splitext(filepath)[1].lower()

    # Stack to stereo and clip
    stereo = np.column_stack([left, right])
    stereo = np.clip(stereo, -MAX_INT16, MAX_INT16).astype(np.int16)

    if ext == '.wav':
        wavfile.write(filepath, sample_rate, stereo)
    elif ext in ('.mp3', '.ogg'):
        try:
            from pydub import AudioSegment
        except ImportError:
            print(f"Error: pydub required for {ext} export. Install with: pip install pydub")
            print("Falling back to WAV output.")
            wav_path = filepath.rsplit('.', 1)[0] + '.wav'
            wavfile.write(wav_path, sample_rate, stereo)
            print(f"Saved: {wav_path}")
            return

        # Create AudioSegment from raw data
        audio = AudioSegment(
            stereo.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,  # 16-bit = 2 bytes
            channels=2,
        )

        if ext == '.mp3':
            audio.export(filepath, format='mp3', bitrate='192k')
        else:  # .ogg
            audio.export(filepath, format='ogg')
    else:
        print(f"Warning: Unknown format '{ext}', saving as WAV")
        wavfile.write(filepath, sample_rate, stereo)

    print(f"Saved: {filepath}")

    # Report levels
    rms_l = np.sqrt(np.mean(left ** 2))
    rms_r = np.sqrt(np.mean(right ** 2))
    peak = np.max(np.abs(stereo))
    print(f"  RMS: L={linear_to_db(rms_l/MAX_INT16):.1f} dB, R={linear_to_db(rms_r/MAX_INT16):.1f} dB")
    print(f"  Peak: {linear_to_db(peak/MAX_INT16):.1f} dB")


# === CLI Argument Parsing ===

def parse_add_iso(spec: str) -> ToneSpec:
    """
    Parse --add-iso argument: CARRIER,PULSE_RATE,AMPLITUDE_DB,EAR(S)

    Example: "310,5.0,0,L" -> ToneSpec(310, 5.0, 0, 'L')
    """
    parts = spec.split(',')
    if len(parts) != 4:
        raise ValueError(f"Invalid --add-iso format: '{spec}'. Expected: CARRIER,PULSE,DB,EAR")

    carrier = float(parts[0])
    pulse = float(parts[1])
    amplitude = float(parts[2])
    ear = parts[3].upper()

    if ear not in ('L', 'R', 'LR'):
        raise ValueError(f"Invalid ear: '{ear}'. Must be L, R, or LR")

    return ToneSpec(carrier, pulse, amplitude, ear)


def parse_add_binaural(spec: str) -> list[ToneSpec]:
    """
    Parse --add-binaural argument: CARRIER,BEAT,AMPLITUDE_DB

    Generates L = carrier - beat/2, R = carrier + beat/2 (continuous tones)
    Example: "200,5,0" -> [ToneSpec(197.5, 0, 0, 'L'), ToneSpec(202.5, 0, 0, 'R')]
    """
    parts = spec.split(',')
    if len(parts) != 3:
        raise ValueError(f"Invalid --add-binaural format: '{spec}'. Expected: CARRIER,BEAT,DB")

    carrier = float(parts[0])
    beat = float(parts[1])
    amplitude = float(parts[2])

    return [
        ToneSpec(carrier - beat / 2, 0, amplitude, 'L'),
        ToneSpec(carrier + beat / 2, 0, amplitude, 'R'),
    ]


def load_json_config(filepath: str) -> dict:
    """Load and validate JSON configuration file."""
    with open(filepath, 'r') as f:
        config = json.load(f)

    # Validate required fields
    if 'duration_sec' not in config:
        raise ValueError("JSON config must include 'duration_sec'")
    if 'layers' not in config:
        raise ValueError("JSON config must include 'layers'")

    # Validate layers
    for i, layer in enumerate(config['layers']):
        required = ['center_hz', 'pulse_hz', 'amplitude_db']
        for field in required:
            if field not in layer:
                raise ValueError(f"Layer {i} missing required field: '{field}'")

    # Check for binaural source
    if 'keyframes' not in config and 'binaural_hz' not in config:
        print("Warning: No 'keyframes' or 'binaural_hz' specified. Using binaural_hz=0.")

    return config


# === CLI Main ===

def main():
    parser = argparse.ArgumentParser(
        description="Binaural/Isochronic Generator with Composable Primitives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Drone preset (4 isochronic tones)
  python binaural.py --preset drone --duration 120 -o drone.wav

  # Custom isochronic tones
  python binaural.py \\
    --add-iso 310,5.0,0,L \\
    --add-iso 314,5.0,0,R \\
    --add-iso 58,3.25,-6,L \\
    --add-iso 62,3.25,-6,R \\
    --duration 120 -o custom.wav

  # Simple binaural beat (continuous tones)
  python binaural.py --add-binaural 200,5,0 --duration 600 -o simple.ogg

  # Load from JSON (with binaural sweep)
  python binaural.py --json-input config.json -o sweep.wav
"""
    )

    parser.add_argument('--add-iso', action='append', metavar='SPEC',
                        help='Add isochronic tone: CARRIER,PULSE,DB,EAR (e.g., 310,5.0,0,L)')
    parser.add_argument('--add-binaural', action='append', metavar='SPEC',
                        help='Add binaural pair: CARRIER,BEAT,DB (e.g., 200,5,0)')
    parser.add_argument('--preset', choices=list(PRESETS.keys()),
                        help='Use predefined configuration')
    parser.add_argument('--json-input', metavar='FILE',
                        help='Load configuration from JSON file')
    parser.add_argument('--duration', type=float, default=600,
                        help='Duration in seconds (default: 600)')
    parser.add_argument('--fade-in', type=float, default=1.75,
                        help='Fade in duration in seconds (default: 1.75)')
    parser.add_argument('--fade-out', type=float, default=1.75,
                        help='Fade out duration in seconds (default: 1.75)')
    parser.add_argument('--level', type=float, default=-28,
                        help='Target RMS level in dB (default: -28)')
    parser.add_argument('--interleave-ms', type=float, default=100.0,
                        help='R channel isochronic phase offset in ms (default: 100)')
    parser.add_argument('-o', '--output', default='output.wav',
                        help='Output file (default: output.wav)')

    args = parser.parse_args()

    # Check if any input specified
    if not args.json_input and not args.preset and not args.add_iso and not args.add_binaural:
        parser.print_help()
        return

    if args.json_input:
        # Load from JSON file
        config = load_json_config(args.json_input)

        layers = [
            LayerSpec(
                name=layer.get('name', f'layer_{i}'),
                center_hz=layer['center_hz'],
                pulse_hz=layer['pulse_hz'],
                amplitude_db=layer['amplitude_db'],
            )
            for i, layer in enumerate(config['layers'])
        ]

        duration = config['duration_sec']
        fade_in = config.get('fade_in_sec', args.fade_in)
        fade_out = config.get('fade_out_sec', args.fade_out)
        target_db = config.get('target_db', args.level)

        binaural_hz = config.get('binaural_hz')
        keyframes = config.get('keyframes')

        print(f"=== JSON Configuration ===")
        print(f"Duration: {duration}s")
        print(f"Layers: {len(layers)}")
        for layer in layers:
            print(f"  - {layer.name}: {layer.center_hz} Hz, pulse={layer.pulse_hz} Hz, {layer.amplitude_db} dB")
        if keyframes:
            print(f"Keyframes: {len(keyframes)} points")
            for kf in keyframes:
                print(f"  - t={kf['time_sec']}s: {kf['binaural_hz']} Hz")
        elif binaural_hz is not None:
            print(f"Static binaural: {binaural_hz} Hz")
        if args.interleave_ms != 100.0:
            print(f"Note: --interleave-ms ignored in JSON mode (uses automatic 180° L/R offset)")
        print()

        # Check for fast-syncing pulse rates
        pulse_rates = [(layer.name, layer.pulse_hz) for layer in layers]
        check_pulse_sync(pulse_rates)

        left, right = generate_layered(
            layers=layers,
            duration_sec=duration,
            binaural_hz=binaural_hz,
            keyframes=keyframes,
            fade_in_sec=fade_in,
            fade_out_sec=fade_out,
            target_db=target_db,
        )

    else:
        # Build tones from CLI arguments
        tones = []

        if args.preset:
            tones.extend(PRESETS[args.preset])
            print(f"Using preset: {args.preset}")
            for tone in PRESETS[args.preset]:
                print(f"  - {tone.carrier_hz} Hz, pulse={tone.pulse_hz} Hz, {tone.amplitude_db} dB, {tone.ear}")
            print(f"Interleave: {args.interleave_ms} ms (R channel phase offset)")
            print()

        if args.add_iso:
            for spec in args.add_iso:
                tones.append(parse_add_iso(spec))

        if args.add_binaural:
            for spec in args.add_binaural:
                tones.extend(parse_add_binaural(spec))

        if not tones:
            print("Error: No tones specified. Use --preset, --add-iso, or --add-binaural")
            parser.print_help()
            return

        # Check for fast-syncing pulse rates (dedupe by pulse_hz)
        seen_rates = {}
        for tone in tones:
            if tone.pulse_hz > 0 and tone.pulse_hz not in seen_rates:
                seen_rates[tone.pulse_hz] = f"{tone.carrier_hz}Hz@{tone.pulse_hz}"
        pulse_rates = [(name, rate) for rate, name in seen_rates.items()]
        check_pulse_sync(pulse_rates)

        left, right = generate_composite(
            tones=tones,
            duration_sec=args.duration,
            fade_in_sec=args.fade_in,
            fade_out_sec=args.fade_out,
            target_db=args.level,
            interleave_ms=args.interleave_ms,
        )

    save_audio(left, right, args.output)


if __name__ == '__main__':
    main()
