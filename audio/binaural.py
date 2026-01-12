#!/usr/bin/env python3
"""
Binaural/Isochronic Generator

Generates entrainment audio with multiple modes:
- simple: Basic binaural beats
- isochronic: Single-band amplitude-modulated pulsing
- bambi: Advanced dual-band isochronic with harmonic ladder design
"""

import argparse
import numpy as np
from scipy.io import wavfile
from scipy import signal
import os

# Constants
SAMPLE_RATE = 44100
BIT_DEPTH = 16
MAX_INT16 = 32767


# === Presets ===

BAMBI_PRESETS = {
    "ladder": {
        "description": "Smooth theta gradient (3.25 -> 4.125 -> 5.0 Hz)",
        "harmonic_target": 4.125,
    },
    "alpha8": {
        "description": "Theta + alpha boundary (8 Hz harmonic)",
        "harmonic_target": 8.0,
    },
    "alpha10": {
        "description": "Theta + mid-alpha (10 Hz harmonic)",
        "harmonic_target": 10.0,
    },
}


# === Utility Functions ===

def db_to_linear(db):
    """Convert decibels to linear amplitude."""
    return 10 ** (db / 20)


def linear_to_db(linear):
    """Convert linear amplitude to decibels."""
    return 20 * np.log10(linear + 1e-10)


def apply_fade(signal_data, fade_in_samples, fade_out_samples):
    """Apply fade in/out to signal."""
    result = signal_data.copy()

    # Fade in
    if fade_in_samples > 0:
        fade_in = np.linspace(0, 1, fade_in_samples)
        result[:fade_in_samples] *= fade_in

    # Fade out
    if fade_out_samples > 0:
        fade_out = np.linspace(1, 0, fade_out_samples)
        result[-fade_out_samples:] *= fade_out

    return result


def delay_signal(signal_data, delay_ms, sample_rate):
    """Delay a signal by specified milliseconds."""
    delay_samples = int(sample_rate * delay_ms / 1000)
    if delay_samples <= 0:
        return signal_data

    # Pad beginning with zeros, trim end to keep same length
    delayed = np.concatenate([np.zeros(delay_samples), signal_data[:-delay_samples]])
    return delayed


def normalize_to_db(signal_data, target_db):
    """Normalize signal to target RMS level in dB."""
    current_rms = np.sqrt(np.mean(signal_data ** 2))
    target_rms = db_to_linear(target_db) * MAX_INT16
    if current_rms > 0:
        return signal_data * (target_rms / current_rms)
    return signal_data


def isochronic_envelope(t, rate, phase=0):
    """
    Generate isochronic envelope using raised cosine.
    Returns values from 0 to 1.
    """
    return 0.5 * (1 + np.cos(2 * np.pi * rate * t + np.pi + phase))


def save_wav(filename, left, right, sample_rate=SAMPLE_RATE):
    """Save stereo WAV file."""
    # Stack to stereo
    stereo = np.column_stack([left, right])

    # Clip and convert to int16
    stereo = np.clip(stereo, -MAX_INT16, MAX_INT16).astype(np.int16)

    wavfile.write(filename, sample_rate, stereo)
    print(f"Saved: {filename}")

    # Report levels
    rms_l = np.sqrt(np.mean(left ** 2))
    rms_r = np.sqrt(np.mean(right ** 2))
    peak = np.max(np.abs(stereo))
    print(f"  RMS: L={linear_to_db(rms_l/MAX_INT16):.1f} dB, R={linear_to_db(rms_r/MAX_INT16):.1f} dB")
    print(f"  Peak: {linear_to_db(peak/MAX_INT16):.1f} dB")


# === Generator Modes ===

def generate_simple(carrier, beat, duration, fade_in=1.0, fade_out=1.0, target_db=-20):
    """
    Generate simple binaural beat.

    Args:
        carrier: Base frequency in Hz
        beat: Binaural beat frequency in Hz
        duration: Duration in seconds
        fade_in: Fade in time in seconds
        fade_out: Fade out time in seconds
        target_db: Target RMS level in dB

    Returns:
        left, right: Numpy arrays of audio samples
    """
    num_samples = int(SAMPLE_RATE * duration)
    t = np.arange(num_samples) / SAMPLE_RATE

    # Generate carriers
    left = np.sin(2 * np.pi * carrier * t)
    right = np.sin(2 * np.pi * (carrier + beat) * t)

    # Apply fades
    fade_in_samples = int(SAMPLE_RATE * fade_in)
    fade_out_samples = int(SAMPLE_RATE * fade_out)
    left = apply_fade(left, fade_in_samples, fade_out_samples)
    right = apply_fade(right, fade_in_samples, fade_out_samples)

    # Normalize
    left = normalize_to_db(left, target_db)
    right = normalize_to_db(right, target_db)

    return left, right


def generate_isochronic(carrier, pulse_rate, duration, fade_in=1.0, fade_out=1.0, target_db=-20):
    """
    Generate single-band isochronic tone.

    Args:
        carrier: Carrier frequency in Hz
        pulse_rate: Isochronic pulse rate in Hz
        duration: Duration in seconds
        fade_in: Fade in time in seconds
        fade_out: Fade out time in seconds
        target_db: Target RMS level in dB

    Returns:
        left, right: Numpy arrays of audio samples (identical)
    """
    num_samples = int(SAMPLE_RATE * duration)
    t = np.arange(num_samples) / SAMPLE_RATE

    # Generate carrier
    carrier_signal = np.sin(2 * np.pi * carrier * t)

    # Generate envelope
    envelope = isochronic_envelope(t, pulse_rate)

    # Apply envelope
    signal_data = carrier_signal * envelope

    # Apply fades
    fade_in_samples = int(SAMPLE_RATE * fade_in)
    fade_out_samples = int(SAMPLE_RATE * fade_out)
    signal_data = apply_fade(signal_data, fade_in_samples, fade_out_samples)

    # Normalize
    signal_data = normalize_to_db(signal_data, target_db)

    # Mono output
    return signal_data, signal_data.copy()


def generate_bambi(
    high_carrier=312.5,
    high_beat=5.0,
    low_beat=3.25,
    low_db=-6.0,
    interleave_ms=100.0,
    harmonic_target=4.125,
    duration=600,
    fade_in=3.0,
    fade_out=3.0,
    target_db=-31,
):
    """
    Generate advanced dual-band isochronic with harmonic ladder design.

    Args:
        high_carrier: High band center frequency in Hz
        high_beat: High band binaural/isochronic rate in Hz
        low_beat: Low band binaural/isochronic rate in Hz
        low_db: Low band level relative to high in dB
        interleave_ms: R channel delay for spatial effect in ms
        harmonic_target: Target harmonic beat frequency in Hz
        duration: Duration in seconds
        fade_in: Fade in time in seconds
        fade_out: Fade out time in seconds
        target_db: Target RMS level in dB (standalone)

    Returns:
        left, right: Numpy arrays of audio samples
    """
    # Calculate derived frequencies
    low_carrier = (high_carrier - harmonic_target) / 5

    high_L = high_carrier - high_beat / 2
    high_R = high_carrier + high_beat / 2
    low_L = low_carrier - low_beat / 2
    low_R = low_carrier + low_beat / 2

    # Report calculated frequencies
    print(f"=== Bambi Mode Frequencies ===")
    print(f"High band: {high_L:.3f} / {high_R:.3f} Hz (mid: {high_carrier:.3f}, beat: {high_beat:.3f} Hz)")
    print(f"Low band:  {low_L:.3f} / {low_R:.3f} Hz (mid: {low_carrier:.3f}, beat: {low_beat:.3f} Hz)")
    print(f"Low level: {low_db:.1f} dB")
    print(f"Interleave: {interleave_ms:.1f} ms")
    print(f"Harmonic: 5 x {low_carrier:.3f} = {5*low_carrier:.3f} Hz")
    print(f"Harmonic beat: {high_carrier:.3f} - {5*low_carrier:.3f} = {high_carrier - 5*low_carrier:.3f} Hz")
    print()

    # Generate time array
    num_samples = int(SAMPLE_RATE * duration)
    t = np.arange(num_samples) / SAMPLE_RATE

    # Generate isochronic envelopes (mono, to be applied to both channels)
    high_env = isochronic_envelope(t, high_beat)
    low_env = isochronic_envelope(t, low_beat)

    # Generate carriers for each channel (different frequencies for binaural)
    high_L_carrier = np.sin(2 * np.pi * high_L * t)
    high_R_carrier = np.sin(2 * np.pi * high_R * t)
    low_L_carrier = np.sin(2 * np.pi * low_L * t)
    low_R_carrier = np.sin(2 * np.pi * low_R * t)

    # Apply envelopes to carriers
    high_L_signal = high_env * high_L_carrier
    high_R_signal = high_env * high_R_carrier

    low_amplitude = db_to_linear(low_db)
    low_L_signal = low_env * low_L_carrier * low_amplitude
    low_R_signal = low_env * low_R_carrier * low_amplitude

    # Mix bands
    left = high_L_signal + low_L_signal
    right = high_R_signal + low_R_signal

    # Apply interleave (delay R channel)
    right = delay_signal(right, interleave_ms, SAMPLE_RATE)

    # Apply fades
    fade_in_samples = int(SAMPLE_RATE * fade_in)
    fade_out_samples = int(SAMPLE_RATE * fade_out)
    left = apply_fade(left, fade_in_samples, fade_out_samples)
    right = apply_fade(right, fade_in_samples, fade_out_samples)

    # Normalize to target level
    left = normalize_to_db(left, target_db)
    right = normalize_to_db(right, target_db)

    return left, right


# === Mixing ===

def mix_voice_and_drone(voice_path, drone_path, output_path, drone_level_db=-12):
    """
    Mix voice track with drone and normalize output.

    Args:
        voice_path: Path to voice MP3/WAV
        drone_path: Path to drone WAV
        output_path: Output path
        drone_level_db: Drone level relative to voice in dB
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Error: pydub required for mixing. Install with: pip install pydub")
        return

    # Load audio
    voice = AudioSegment.from_file(voice_path)
    drone = AudioSegment.from_file(drone_path)

    # Match drone length to voice
    if len(drone) < len(voice):
        # Loop drone
        loops_needed = (len(voice) // len(drone)) + 1
        drone = drone * loops_needed
    drone = drone[:len(voice)]

    # Adjust drone level
    drone = drone + drone_level_db

    # Mix
    mixed = voice.overlay(drone)

    # Normalize to -1 dB peak
    peak_db = mixed.max_dBFS
    mixed = mixed - peak_db - 1

    # Export
    if output_path.endswith('.mp3'):
        mixed.export(output_path, format='mp3', bitrate='192k')
    else:
        mixed.export(output_path, format='wav')

    print(f"Mixed output saved: {output_path}")


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description="Binaural/Isochronic Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple binaural beat
  python binaural.py simple --carrier 200 --beat 5 --duration 600 -o simple.wav

  # Isochronic pulse
  python binaural.py isochronic --carrier 312 --pulse-rate 5 --duration 600 -o iso.wav

  # Bambi mode with harmonic ladder preset
  python binaural.py bambi --preset ladder --duration 600 -o bambi.wav

  # Bambi mode with alpha target
  python binaural.py bambi --preset alpha8 --duration 600 -o alpha.wav

  # Mix voice with drone
  python binaural.py mix --voice voice.mp3 --drone drone.wav -o final.mp3
"""
    )

    subparsers = parser.add_subparsers(dest='mode', help='Generator mode')

    # Simple mode
    simple_parser = subparsers.add_parser('simple', help='Basic binaural beat')
    simple_parser.add_argument('--carrier', type=float, default=200, help='Carrier frequency (Hz)')
    simple_parser.add_argument('--beat', type=float, default=5, help='Beat frequency (Hz)')
    simple_parser.add_argument('--duration', type=float, default=600, help='Duration (seconds)')
    simple_parser.add_argument('--fade-in', type=float, default=1, help='Fade in (seconds)')
    simple_parser.add_argument('--fade-out', type=float, default=1, help='Fade out (seconds)')
    simple_parser.add_argument('--level', type=float, default=-20, help='Target RMS level (dB)')
    simple_parser.add_argument('-o', '--output', default='simple_binaural.wav', help='Output file')

    # Isochronic mode
    iso_parser = subparsers.add_parser('isochronic', help='Single-band isochronic')
    iso_parser.add_argument('--carrier', type=float, default=312.5, help='Carrier frequency (Hz)')
    iso_parser.add_argument('--pulse-rate', type=float, default=5, help='Pulse rate (Hz)')
    iso_parser.add_argument('--duration', type=float, default=600, help='Duration (seconds)')
    iso_parser.add_argument('--fade-in', type=float, default=1, help='Fade in (seconds)')
    iso_parser.add_argument('--fade-out', type=float, default=1, help='Fade out (seconds)')
    iso_parser.add_argument('--level', type=float, default=-20, help='Target RMS level (dB)')
    iso_parser.add_argument('-o', '--output', default='isochronic.wav', help='Output file')

    # Bambi mode
    bambi_parser = subparsers.add_parser('bambi', help='Advanced dual-band isochronic')
    bambi_parser.add_argument('--preset', choices=list(BAMBI_PRESETS.keys()), default='ladder',
                              help='Preset configuration')
    bambi_parser.add_argument('--high-carrier', type=float, default=312.5, help='High carrier (Hz)')
    bambi_parser.add_argument('--high-beat', type=float, default=5.0, help='High beat rate (Hz)')
    bambi_parser.add_argument('--low-beat', type=float, default=3.25, help='Low beat rate (Hz)')
    bambi_parser.add_argument('--low-db', type=float, default=-6, help='Low band level (dB)')
    bambi_parser.add_argument('--interleave-ms', type=float, default=100, help='R channel delay (ms)')
    bambi_parser.add_argument('--harmonic-target', type=float, help='Override harmonic target (Hz)')
    bambi_parser.add_argument('--duration', type=float, default=600, help='Duration (seconds)')
    bambi_parser.add_argument('--fade-in', type=float, default=3, help='Fade in (seconds)')
    bambi_parser.add_argument('--fade-out', type=float, default=3, help='Fade out (seconds)')
    bambi_parser.add_argument('--level', type=float, default=-31, help='Target RMS level (dB)')
    bambi_parser.add_argument('-o', '--output', default='bambi_drone.wav', help='Output file')

    # Mix mode
    mix_parser = subparsers.add_parser('mix', help='Mix voice with drone')
    mix_parser.add_argument('--voice', required=True, help='Voice audio file')
    mix_parser.add_argument('--drone', required=True, help='Drone audio file')
    mix_parser.add_argument('--drone-level', type=float, default=-12, help='Drone level relative to voice (dB)')
    mix_parser.add_argument('-o', '--output', default='mixed.mp3', help='Output file')

    args = parser.parse_args()

    if args.mode == 'simple':
        left, right = generate_simple(
            carrier=args.carrier,
            beat=args.beat,
            duration=args.duration,
            fade_in=args.fade_in,
            fade_out=args.fade_out,
            target_db=args.level,
        )
        save_wav(args.output, left, right)

    elif args.mode == 'isochronic':
        left, right = generate_isochronic(
            carrier=args.carrier,
            pulse_rate=args.pulse_rate,
            duration=args.duration,
            fade_in=args.fade_in,
            fade_out=args.fade_out,
            target_db=args.level,
        )
        save_wav(args.output, left, right)

    elif args.mode == 'bambi':
        # Get harmonic target from preset or override
        preset = BAMBI_PRESETS[args.preset]
        harmonic_target = args.harmonic_target or preset['harmonic_target']

        print(f"Using preset: {args.preset} ({preset['description']})")
        print()

        left, right = generate_bambi(
            high_carrier=args.high_carrier,
            high_beat=args.high_beat,
            low_beat=args.low_beat,
            low_db=args.low_db,
            interleave_ms=args.interleave_ms,
            harmonic_target=harmonic_target,
            duration=args.duration,
            fade_in=args.fade_in,
            fade_out=args.fade_out,
            target_db=args.level,
        )
        save_wav(args.output, left, right)

    elif args.mode == 'mix':
        mix_voice_and_drone(
            voice_path=args.voice,
            drone_path=args.drone,
            output_path=args.output,
            drone_level_db=args.drone_level,
        )

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
