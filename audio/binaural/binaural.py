#!/usr/bin/env python3
"""
Binaural/Isochronic Generator

Generates entrainment audio using composable primitives:
- --add-iso: Add isochronic tone (carrier, pulse, amplitude, ear)
- --add-binaural: Add binaural pair (carrier, beat, amplitude)
- --add-hybrid: Add hybrid layer (carrier, beat, pulse, amplitude)
- --preset: Use predefined configurations (bimbo-drone, reactor)
- --json-input: Load timeline/sweep configuration from JSON

JSON mode supports per-layer keyframing of center_hz, pulse_hz,
amplitude_db, and binaural_hz. Each parameter can be a static number
or an array of {time_sec, value} keyframes for dynamic sweeps.
"""

import argparse
import json
import os
from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd, lcm
from typing import Optional, Union

import numpy as np
from scipy.io import wavfile

# Constants
SAMPLE_RATE = 44100
BIT_DEPTH = 16
MAX_INT16 = 32767

# Type alias for polymorphic parameter: static float or keyframe array
ParamValue = Union[float, np.ndarray]


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


@dataclass
class DynamicLayerSpec:
    """Layer with resolved parameters that may be static or per-sample arrays.

    Each parameter is either a float (static, uses numpy broadcasting)
    or an np.ndarray (keyframed, one value per sample). This avoids
    allocating full arrays for static parameters on long files.
    """
    name: str
    center_hz: ParamValue
    pulse_hz: ParamValue
    amplitude_db: ParamValue
    binaural_hz: ParamValue  # per-layer binaural offset


# === Presets ===

# Legacy CLI presets (ToneSpec-based, used with generate_composite)
PRESETS = {
    'drone-legacy': [
        ToneSpec(310, 5.0, 0, 'L'),
        ToneSpec(314, 5.0, 0, 'R'),
        ToneSpec(58, 3.25, -6, 'L'),
        ToneSpec(62, 3.25, -6, 'R'),
    ],
}

# Layered presets (dict-based, used with generate_layered)
LAYERED_PRESETS = {
    'bimbo-drone': {
        'layers': [
            {'name': 'high', 'center_hz': 312, 'pulse_hz': 5.0,
             'amplitude_db': 0, 'binaural_hz': 3.0},
            {'name': 'low', 'center_hz': 60, 'pulse_hz': 3.25,
             'amplitude_db': -6, 'binaural_hz': 3.0},
        ],
        'ear_priority': 'R',
    },
    'reactor': {
        'layers': [
            {'name': 'high', 'center_hz': 202.5, 'pulse_hz': 7.0,
             'amplitude_db': 0, 'binaural_hz': 4.0},
            {'name': 'mid_high', 'center_hz': 135, 'pulse_hz': 4.6,
             'amplitude_db': -4, 'binaural_hz': 3.5},
            {'name': 'mid_low', 'center_hz': 90, 'pulse_hz': 3.3,
             'amplitude_db': -6, 'binaural_hz': 3.0},
            {'name': 'low', 'center_hz': 60, 'pulse_hz': 2.55,
             'amplitude_db': -8, 'binaural_hz': 2.5},
        ],
        'duration_sec': 3780,
        'ear_priority': 'R',
    },
    'descent': {
        'layers': [
            {'name': 'theta', 'center_hz': 200, 'pulse_hz': 5.0,
             'amplitude_db': 0, 'binaural_hz': 4.0},
            {'name': 'deep_theta', 'center_hz': 120, 'pulse_hz': 3.25,
             'amplitude_db': -3, 'binaural_hz': 3.0},
            {'name': 'delta', 'center_hz': 55, 'pulse_hz': 2.55,
             'amplitude_db': -6, 'binaural_hz': 2.0},
        ],
        'ear_priority': 'R',
    },
}

ALL_PRESET_NAMES = sorted(set(PRESETS.keys()) | set(LAYERED_PRESETS.keys()))


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
    Generate isochronic envelope using raised cosine (static rate).
    Returns values from 0 to 1.

    Args:
        t: Time array in seconds
        rate: Pulse rate in Hz
        phase_offset: Phase offset in radians (default 0)
    """
    return 0.5 * (1 + np.cos(2 * np.pi * rate * t + np.pi + phase_offset))


def isochronic_envelope_dynamic(
    pulse_hz: ParamValue,
    num_samples: int,
    sample_rate: int,
    phase_offset: float = 0.0,
) -> np.ndarray:
    """
    Generate phase-continuous isochronic envelope for static or dynamic pulse rates.

    Uses cumulative phase integration for smooth transitions when pulse_hz
    changes over time. Maintains exact phase offset (e.g., pi for 180-degree
    L/R alternation) regardless of rate changes.

    When pulse_hz drops below 0.1 Hz, blends to continuous (envelope=1.0)
    to avoid frozen-phase artifacts.

    Args:
        pulse_hz: Pulse rate - scalar float or per-sample array
        num_samples: Number of samples to generate
        sample_rate: Sample rate in Hz
        phase_offset: Phase offset in radians (pi for 180-degree L/R offset)

    Returns:
        Envelope array of shape (num_samples,), values 0 to 1
    """
    if isinstance(pulse_hz, (int, float)):
        if pulse_hz < 0.1:
            return np.ones(num_samples)
        # Static rate: use simple time-based calculation
        t = np.arange(num_samples) / sample_rate
        return 0.5 * (1 + np.cos(2 * np.pi * pulse_hz * t + np.pi + phase_offset))

    # Dynamic rate: cumulative phase integration
    pulse_phase = np.cumsum(2 * np.pi * pulse_hz / sample_rate)
    envelope = 0.5 * (1 + np.cos(pulse_phase + np.pi + phase_offset))

    # Blend to continuous where pulse_hz < 0.1 Hz
    low_mask = pulse_hz < 0.1
    if np.any(low_mask):
        envelope[low_mask] = 1.0

    return envelope


def resolve_parameter(
    value: Union[float, int, list],
    duration_sec: float,
    sample_rate: int,
) -> ParamValue:
    """
    Resolve a parameter value to either a scalar or per-sample array.

    Args:
        value: Either a scalar number (returned as float) or a list of
               {time_sec, value} keyframe dicts (interpolated to array)
        duration_sec: Total duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        float (static) or np.ndarray (keyframed)
    """
    if isinstance(value, (int, float)):
        return float(value)

    # Keyframe list
    num_samples = int(sample_rate * duration_sec)
    t = np.arange(num_samples) / sample_rate
    sorted_kf = sorted(value, key=lambda k: k['time_sec'])
    times = [kf['time_sec'] for kf in sorted_kf]
    values = [kf['value'] for kf in sorted_kf]
    return np.interp(t, times, values)


def interpolate_keyframes(keyframes: list[dict], duration_sec: float, sample_rate: int) -> np.ndarray:
    """
    Interpolate binaural_hz values across time from legacy keyframe format.

    Args:
        keyframes: List of {time_sec, binaural_hz} dicts
        duration_sec: Total duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Array of binaural_hz values for each sample
    """
    generic = [{'time_sec': kf['time_sec'], 'value': kf['binaural_hz']} for kf in keyframes]
    result = resolve_parameter(generic, duration_sec, sample_rate)
    # resolve_parameter returns ndarray for lists, but ensure it
    if isinstance(result, (int, float)):
        return np.full(int(sample_rate * duration_sec), result)
    return result


def generate_oscillating_keyframes(
    low: float,
    high: float,
    period_sec: float,
    duration_sec: float,
) -> list[dict]:
    """
    Generate alternating keyframes (triangle wave) between two values.

    Args:
        low: Low value
        high: High value
        period_sec: Full period (low->high->low) in seconds
        duration_sec: Total duration

    Returns:
        List of {time_sec, binaural_hz} dicts
    """
    keyframes = []
    half_period = period_sec / 2
    t = 0.0
    while t <= duration_sec:
        keyframes.append({'time_sec': t, 'binaural_hz': low})
        t += half_period
        if t <= duration_sec:
            keyframes.append({'time_sec': t, 'binaural_hz': high})
        t += half_period
    return keyframes


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


def param_summary(value: ParamValue, unit: str = '') -> str:
    """Format a parameter value for display (handles static and keyframed)."""
    if isinstance(value, (int, float)):
        return f"{value}{unit}"
    # It's an array - show range
    vmin, vmax = np.min(value), np.max(value)
    if abs(vmax - vmin) < 0.001:
        return f"{vmin:.2f}{unit}"
    return f"{vmin:.2f}->{vmax:.2f}{unit} (keyframed)"


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
    # This gives exact 180 only at 5 Hz; other frequencies get approximate offsets.
    # For precise 180 L/R alternation at any frequency, use JSON mode (generate_layered)
    # which automatically applies pi radians offset within each layer.

    num_samples = int(sample_rate * duration_sec)
    t = np.arange(num_samples) / sample_rate

    left = np.zeros(num_samples)
    right = np.zeros(num_samples)

    for tone in tones:
        # Generate carrier
        carrier = np.sin(2 * np.pi * tone.carrier_hz * t)

        # Apply isochronic envelope if pulse_hz > 0
        if tone.pulse_hz > 0:
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
    layers: list,
    duration_sec: float,
    binaural_hz: Optional[float] = None,
    keyframes: Optional[list[dict]] = None,
    fade_in_sec: float = 1.75,
    fade_out_sec: float = 1.75,
    sample_rate: int = SAMPLE_RATE,
    target_db: float = -28,
    ear_priority: str = 'R',
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate layered audio with per-layer binaural beats from JSON config.

    Each layer can have its own binaural_hz (static or keyframed), or inherit
    from the global binaural_hz/keyframes. All parameters (center_hz, pulse_hz,
    amplitude_db, binaural_hz) can be static or dynamically keyframed.

    Uses phase-continuous sine generation for smooth frequency sweeps.
    Isochronic envelopes automatically use 180-degree L/R phase offset.

    Args:
        layers: List of DynamicLayerSpec, LayerSpec, or compatible objects
        duration_sec: Duration in seconds
        binaural_hz: Global static binaural beat (fallback if layer has none)
        keyframes: Global {time_sec, binaural_hz} keyframes (fallback)
        fade_in_sec: Fade in time in seconds
        fade_out_sec: Fade out time in seconds
        sample_rate: Sample rate in Hz
        target_db: Target RMS level in dB
        ear_priority: 'R' (right ear higher) or 'L' (left ear higher)

    Returns:
        (left, right): Tuple of numpy arrays for stereo audio
    """
    num_samples = int(sample_rate * duration_sec)

    # Resolve global binaural fallback
    if keyframes:
        global_binaural = interpolate_keyframes(keyframes, duration_sec, sample_rate)
    elif binaural_hz is not None:
        global_binaural = float(binaural_hz)
    else:
        global_binaural = 0.0

    # Ear priority sign: R means right ear gets higher frequency
    sign = -1.0 if ear_priority == 'L' else 1.0

    left = np.zeros(num_samples)
    right = np.zeros(num_samples)

    for layer in layers:
        # Resolve parameters - works with DynamicLayerSpec (has binaural_hz)
        # or LayerSpec (no binaural_hz, uses global)
        if isinstance(layer, DynamicLayerSpec):
            center = layer.center_hz
            pulse = layer.pulse_hz
            amp = layer.amplitude_db
            layer_binaural = layer.binaural_hz
        else:
            # LayerSpec or compatible - static values, global binaural
            center = layer.center_hz
            pulse = layer.pulse_hz
            amp = layer.amplitude_db
            layer_binaural = global_binaural

        # Calculate instantaneous frequencies for L and R
        # numpy broadcasting handles float * float, float * array, array * array
        freq_l = center - sign * layer_binaural / 2
        freq_r = center + sign * layer_binaural / 2

        # Phase-continuous sine generation using cumulative sum
        # Must expand to arrays for cumsum
        if isinstance(freq_l, (int, float)):
            freq_l_arr = np.full(num_samples, freq_l)
        else:
            freq_l_arr = freq_l
        if isinstance(freq_r, (int, float)):
            freq_r_arr = np.full(num_samples, freq_r)
        else:
            freq_r_arr = freq_r

        phase_l = np.cumsum(2 * np.pi * freq_l_arr / sample_rate)
        phase_r = np.cumsum(2 * np.pi * freq_r_arr / sample_rate)

        carrier_l = np.sin(phase_l)
        carrier_r = np.sin(phase_r)

        # Apply isochronic envelope
        has_pulse = (isinstance(pulse, (int, float)) and pulse > 0) or \
                    (isinstance(pulse, np.ndarray) and np.any(pulse > 0))

        if has_pulse:
            envelope_l = isochronic_envelope_dynamic(pulse, num_samples, sample_rate, phase_offset=0.0)
            envelope_r = isochronic_envelope_dynamic(pulse, num_samples, sample_rate, phase_offset=np.pi)
            signal_l = carrier_l * envelope_l
            signal_r = carrier_r * envelope_r
        else:
            signal_l = carrier_l
            signal_r = carrier_r

        # Apply amplitude (dB to linear, handles scalar or array)
        if isinstance(amp, np.ndarray):
            amplitude = np.power(10.0, amp / 20.0)
        else:
            amplitude = db_to_linear(amp)

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
    bitrate: str = None,
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

        audio = AudioSegment(
            stereo.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,
            channels=2,
        )

        if ext == '.mp3':
            audio.export(filepath, format='mp3', bitrate=bitrate or '192k')
        elif ext == '.ogg':
            audio.export(filepath, format='ogg', codec='libopus', bitrate=bitrate or '48k')
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


# === JSON Configuration ===

def expand_unified_keyframes(layer: dict, layer_idx: int) -> dict:
    """
    Convert unified keyframe format to per-attribute format.

    Unified format groups all attributes by time point:
        {"keyframes": [
            {"time_sec": 0, "center_hz": 315, "pulse_hz": 6.5, "amplitude_db": -40},
            {"time_sec": 15, "amplitude_db": 0},
            {"time_sec": 57, "center_hz": 200, "amplitude_db": -40}
        ]}

    Converts to per-attribute format:
        {"center_hz": [{"time_sec": 0, "value": 315}, {"time_sec": 57, "value": 200}],
         "pulse_hz": [{"time_sec": 0, "value": 6.5}],  # single keyframe -> static
         "amplitude_db": [{"time_sec": 0, "value": -40}, ...]}
    """
    keyframes = layer['keyframes']
    attrs = ['center_hz', 'pulse_hz', 'amplitude_db', 'binaural_hz']

    result = {k: v for k, v in layer.items() if k not in ('keyframes',)}

    for attr in attrs:
        kfs = [{'time_sec': kf['time_sec'], 'value': kf[attr]}
               for kf in keyframes if attr in kf]
        if len(kfs) == 0:
            continue  # not specified, will inherit or error on required fields
        elif len(kfs) == 1:
            result[attr] = kfs[0]['value']  # single value -> static
        else:
            result[attr] = kfs

    return result


def validate_param_value(value, layer_idx: int, field: str) -> None:
    """Validate that a parameter is a number or list of {time_sec, value} keyframes."""
    if isinstance(value, (int, float)):
        return
    if isinstance(value, list):
        for j, kf in enumerate(value):
            if not isinstance(kf, dict) or 'time_sec' not in kf or 'value' not in kf:
                raise ValueError(
                    f"Layer {layer_idx} field '{field}' keyframe {j}: "
                    f"must be dict with 'time_sec' and 'value'"
                )
        return
    raise ValueError(f"Layer {layer_idx} field '{field}' must be a number or keyframe array")


def load_json_config(filepath: str) -> dict:
    """Load and validate JSON configuration file."""
    with open(filepath, 'r') as f:
        config = json.load(f)

    # Validate required fields
    if 'duration_sec' not in config:
        raise ValueError("JSON config must include 'duration_sec'")
    if 'layers' not in config:
        raise ValueError("JSON config must include 'layers'")

    # Expand unified keyframes if present
    for i, layer in enumerate(config['layers']):
        if 'keyframes' in layer:
            config['layers'][i] = expand_unified_keyframes(layer, i)

    # Validate layers
    for i, layer in enumerate(config['layers']):
        required = ['center_hz', 'pulse_hz', 'amplitude_db']
        for fld in required:
            if fld not in layer:
                raise ValueError(f"Layer {i} missing required field: '{fld}'")
            validate_param_value(layer[fld], i, fld)

        # Optional per-layer binaural_hz
        if 'binaural_hz' in layer:
            validate_param_value(layer['binaural_hz'], i, 'binaural_hz')

    # Validate ear_priority
    ear_priority = config.get('ear_priority', 'R')
    if ear_priority not in ('L', 'R'):
        raise ValueError(f"ear_priority must be 'L' or 'R', got '{ear_priority}'")

    # Check for binaural source (global or per-layer)
    has_global_binaural = 'keyframes' in config or 'binaural_hz' in config
    has_per_layer = any('binaural_hz' in layer for layer in config['layers'])
    if not has_global_binaural and not has_per_layer:
        print("Warning: No binaural_hz specified (global or per-layer). Using binaural_hz=0.")

    return config


def resolve_layers_from_config(config: dict, sample_rate: int = SAMPLE_RATE) -> list[DynamicLayerSpec]:
    """
    Resolve a JSON config into DynamicLayerSpec objects.

    Handles:
    - Polymorphic values (static number or keyframe array) for all parameters
    - Per-layer binaural_hz with fallback to global binaural_hz/keyframes
    - Legacy format (top-level keyframes with binaural_hz key)
    """
    duration = config['duration_sec']

    # Resolve global binaural fallback
    global_keyframes = config.get('keyframes')
    global_binaural_static = config.get('binaural_hz')

    if global_keyframes:
        # Legacy format: convert {time_sec, binaural_hz} -> {time_sec, value}
        global_binaural_kf = [
            {'time_sec': kf['time_sec'], 'value': kf['binaural_hz']}
            for kf in global_keyframes
        ]
        global_binaural = resolve_parameter(global_binaural_kf, duration, sample_rate)
    elif global_binaural_static is not None:
        global_binaural = resolve_parameter(global_binaural_static, duration, sample_rate)
    else:
        global_binaural = 0.0

    layers = []
    for i, layer_cfg in enumerate(config['layers']):
        # Resolve per-layer binaural
        if 'binaural_hz' in layer_cfg:
            layer_binaural = resolve_parameter(layer_cfg['binaural_hz'], duration, sample_rate)
        else:
            layer_binaural = global_binaural

        layers.append(DynamicLayerSpec(
            name=layer_cfg.get('name', f'layer_{i}'),
            center_hz=resolve_parameter(layer_cfg['center_hz'], duration, sample_rate),
            pulse_hz=resolve_parameter(layer_cfg['pulse_hz'], duration, sample_rate),
            amplitude_db=resolve_parameter(layer_cfg['amplitude_db'], duration, sample_rate),
            binaural_hz=layer_binaural,
        ))

    return layers


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


def parse_add_hybrid(spec: str) -> list[ToneSpec]:
    """
    Parse --add-hybrid argument: CARRIER,BEAT,PULSE,AMPLITUDE_DB

    Like --add-binaural but with isochronic modulation on both channels.
    Generates L = carrier - beat/2 @ pulse Hz, R = carrier + beat/2 @ pulse Hz.
    Example: "312,3,5,0" -> [ToneSpec(310.5, 5.0, 0, 'L'), ToneSpec(313.5, 5.0, 0, 'R')]
    """
    parts = spec.split(',')
    if len(parts) != 4:
        raise ValueError(f"Invalid --add-hybrid format: '{spec}'. Expected: CARRIER,BEAT,PULSE,DB")

    carrier = float(parts[0])
    beat = float(parts[1])
    pulse = float(parts[2])
    amplitude = float(parts[3])

    return [
        ToneSpec(carrier - beat / 2, pulse, amplitude, 'L'),
        ToneSpec(carrier + beat / 2, pulse, amplitude, 'R'),
    ]


def resolve_layered_preset(name: str, duration_override: Optional[float] = None) -> dict:
    """
    Resolve a layered preset into a config dict suitable for generate_layered.

    Handles oscillating keyframe generation for presets that specify it.

    Returns:
        Dict with 'layers' (list of DynamicLayerSpec), 'duration_sec',
        'ear_priority', and optionally 'keyframes'.
    """
    preset = LAYERED_PRESETS[name]
    duration = duration_override or preset.get('duration_sec', 600)

    # Build config dict mimicking JSON format
    config = {
        'duration_sec': duration,
        'layers': preset['layers'],
        'ear_priority': preset.get('ear_priority', 'R'),
    }

    return config


# === CLI Main ===

def main():
    parser = argparse.ArgumentParser(
        description="Binaural/Isochronic Generator with Composable Primitives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Drone preset (2 hybrid layers: binaural + isochronic)
  python binaural.py --preset bimbo-drone --duration 120 -o drone.wav

  # reactor preset (4-layer, per-layer binaural descent)
  python binaural.py --preset reactor -o reactor.wav

  # Custom isochronic tones
  python binaural.py \\
    --add-iso 310,5.0,0,L \\
    --add-iso 314,5.0,0,R \\
    --duration 120 -o custom.wav

  # Simple binaural beat (continuous tones)
  python binaural.py --add-binaural 200,5,0 --duration 600 -o simple.ogg

  # Hybrid: binaural + isochronic on same carrier
  python binaural.py --add-hybrid 312,3,5,0 --duration 600 -o hybrid.wav

  # Load from JSON (with per-layer keyframes)
  python binaural.py --json-input config.json -o sweep.wav
"""
    )

    parser.add_argument('--add-iso', action='append', metavar='SPEC',
                        help='Add isochronic tone: CARRIER,PULSE,DB,EAR (e.g., 310,5.0,0,L)')
    parser.add_argument('--add-binaural', action='append', metavar='SPEC',
                        help='Add binaural pair: CARRIER,BEAT,DB (e.g., 200,5,0)')
    parser.add_argument('--add-hybrid', action='append', metavar='SPEC',
                        help='Add hybrid layer: CARRIER,BEAT,PULSE,DB (e.g., 312,3,5,0)')
    parser.add_argument('--preset', choices=ALL_PRESET_NAMES,
                        help='Use predefined configuration')
    parser.add_argument('--json-input', metavar='FILE',
                        help='Load configuration from JSON file')
    parser.add_argument('--duration', type=float, default=None,
                        help='Duration in seconds (default: 600, or preset duration)')
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
    parser.add_argument('--bitrate', default=None,
                        help='Audio bitrate for mp3/ogg (e.g., 192k, 30k). Defaults: mp3=192k, ogg=30k')

    args = parser.parse_args()

    # Check if any input specified
    if not args.json_input and not args.preset and not args.add_iso and not args.add_binaural and not args.add_hybrid:
        parser.print_help()
        return

    if args.json_input:
        # === JSON input mode ===
        config = load_json_config(args.json_input)
        layers = resolve_layers_from_config(config)

        duration = config['duration_sec']
        fade_in = config.get('fade_in_sec', args.fade_in)
        fade_out = config.get('fade_out_sec', args.fade_out)
        target_db = config.get('target_db', args.level)
        ear_priority = config.get('ear_priority', 'R')

        # For generate_layered: pass global keyframes/binaural only for
        # layers that don't have per-layer binaural (handled in DynamicLayerSpec)
        # Since we already resolved everything into DynamicLayerSpec, we don't
        # need to pass global binaural to generate_layered.

        print(f"=== JSON Configuration ===")
        print(f"Duration: {duration}s ({duration/60:.1f} min)")
        print(f"Ear priority: {ear_priority}")
        print(f"Layers: {len(layers)}")
        for layer in layers:
            print(f"  - {layer.name}: center={param_summary(layer.center_hz, ' Hz')}, "
                  f"pulse={param_summary(layer.pulse_hz, ' Hz')}, "
                  f"amp={param_summary(layer.amplitude_db, ' dB')}, "
                  f"binaural={param_summary(layer.binaural_hz, ' Hz')}")

        if args.interleave_ms != 100.0:
            print(f"Note: --interleave-ms ignored in JSON mode (uses automatic 180-deg L/R offset)")
        print()

        # Check for fast-syncing pulse rates (use initial values for static check)
        pulse_rates = []
        for layer in layers:
            if isinstance(layer.pulse_hz, (int, float)):
                pulse_rates.append((layer.name, layer.pulse_hz))
            else:
                pulse_rates.append((layer.name, layer.pulse_hz[0]))
        check_pulse_sync(pulse_rates)

        left, right = generate_layered(
            layers=layers,
            duration_sec=duration,
            fade_in_sec=fade_in,
            fade_out_sec=fade_out,
            target_db=target_db,
            ear_priority=ear_priority,
        )

    elif args.preset and args.preset in LAYERED_PRESETS:
        # === Layered preset mode ===
        config = resolve_layered_preset(args.preset, duration_override=args.duration)
        layers = resolve_layers_from_config(config)

        duration = config['duration_sec']
        ear_priority = config.get('ear_priority', 'R')

        print(f"=== Preset: {args.preset} (hybrid layered) ===")
        print(f"Duration: {duration}s ({duration/60:.1f} min)")
        print(f"Ear priority: {ear_priority}")
        print(f"Layers: {len(layers)}")
        for layer in layers:
            print(f"  - {layer.name}: center={param_summary(layer.center_hz, ' Hz')}, "
                  f"pulse={param_summary(layer.pulse_hz, ' Hz')}, "
                  f"amp={param_summary(layer.amplitude_db, ' dB')}, "
                  f"binaural={param_summary(layer.binaural_hz, ' Hz')}")

        # Show keyframe info
        keyframes = config.get('keyframes')
        if keyframes:
            print(f"Binaural keyframes: {len(keyframes)} points")
            if len(keyframes) <= 6:
                for kf in keyframes:
                    print(f"  - t={kf['time_sec']:.1f}s: {kf['binaural_hz']} Hz")
            else:
                for kf in keyframes[:3]:
                    print(f"  - t={kf['time_sec']:.1f}s: {kf['binaural_hz']} Hz")
                print(f"  ... ({len(keyframes) - 6} more)")
                for kf in keyframes[-3:]:
                    print(f"  - t={kf['time_sec']:.1f}s: {kf['binaural_hz']} Hz")
        print()

        # Check pulse sync
        pulse_rates = []
        for layer in layers:
            if isinstance(layer.pulse_hz, (int, float)):
                pulse_rates.append((layer.name, layer.pulse_hz))
            else:
                pulse_rates.append((layer.name, layer.pulse_hz[0]))
        check_pulse_sync(pulse_rates)

        left, right = generate_layered(
            layers=layers,
            duration_sec=duration,
            fade_in_sec=args.fade_in,
            fade_out_sec=args.fade_out,
            target_db=args.level,
            ear_priority=ear_priority,
        )

    else:
        # === CLI composite mode ===
        tones = []
        duration = args.duration or 600

        if args.preset and args.preset in PRESETS:
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

        if args.add_hybrid:
            for spec in args.add_hybrid:
                tones.extend(parse_add_hybrid(spec))

        if not tones:
            print("Error: No tones specified. Use --preset, --add-iso, --add-binaural, or --add-hybrid")
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
            duration_sec=duration,
            fade_in_sec=args.fade_in,
            fade_out_sec=args.fade_out,
            target_db=args.level,
            interleave_ms=args.interleave_ms,
        )

    save_audio(left, right, args.output, bitrate=args.bitrate)


if __name__ == '__main__':
    main()
