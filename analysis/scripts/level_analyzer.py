#!/usr/bin/env python3
"""
Level Analyzer
Measures RMS and peak levels of audio files, with optional band-specific analysis.

Usage:
    python level_analyzer.py <audio_file> [options]

Options:
    --bands         Also analyze specific frequency bands (low ~60Hz, high ~310Hz)
"""

import argparse
import numpy as np
import librosa
from scipy.fft import fft, fftfreq
from scipy import signal
import sys
import os


def db(linear):
    """Convert linear amplitude to dB."""
    return 20 * np.log10(np.abs(linear) + 1e-10)


def rms(y):
    """Calculate RMS of signal."""
    return np.sqrt(np.mean(y ** 2))


def analyze_levels(filepath, analyze_bands=False):
    """
    Analyze audio file levels.

    Returns dict with RMS, peak, and optionally band-specific levels.
    """
    # Load audio (keep original sample rate)
    y, sr = librosa.load(filepath, sr=None, mono=False)

    if y.ndim == 1:
        print("WARNING: Mono file - analyzing single channel")
        y_left = y
        y_right = y
    else:
        y_left = y[0]
        y_right = y[1]

    duration = len(y_left) / sr
    filename = os.path.basename(filepath)

    # Overall levels
    rms_left = rms(y_left)
    rms_right = rms(y_right)
    rms_total = rms(np.concatenate([y_left, y_right]))

    peak_left = np.max(np.abs(y_left))
    peak_right = np.max(np.abs(y_right))
    peak_total = max(peak_left, peak_right)

    results = {
        'filename': filename,
        'duration': duration,
        'sample_rate': sr,
        'rms_left': rms_left,
        'rms_right': rms_right,
        'rms_total': rms_total,
        'rms_left_db': db(rms_left),
        'rms_right_db': db(rms_right),
        'rms_total_db': db(rms_total),
        'peak_left': peak_left,
        'peak_right': peak_right,
        'peak_total': peak_total,
        'peak_left_db': db(peak_left),
        'peak_right_db': db(peak_right),
        'peak_total_db': db(peak_total),
    }

    if analyze_bands:
        # Filter and analyze specific bands
        # Low band: 40-80 Hz (captures ~58-62 Hz carriers)
        # High band: 280-340 Hz (captures ~310-314 Hz carriers)

        def bandpass_rms(y, sr, low, high):
            """Apply bandpass filter and return RMS using FFT method."""
            # Use FFT-based filtering for better low-frequency handling
            n = len(y)
            yf = fft(y)
            xf = fftfreq(n, 1/sr)

            # Create bandpass mask
            mask = (np.abs(xf) >= low) & (np.abs(xf) <= high)

            # Apply mask and inverse FFT
            yf_filtered = yf * mask
            filtered = np.real(np.fft.ifft(yf_filtered))

            return rms(filtered)

        # Low band (~60 Hz)
        low_rms_left = bandpass_rms(y_left, sr, 40, 80)
        low_rms_right = bandpass_rms(y_right, sr, 40, 80)

        # High band (~310 Hz)
        high_rms_left = bandpass_rms(y_left, sr, 280, 340)
        high_rms_right = bandpass_rms(y_right, sr, 280, 340)

        results['low_band_rms_left'] = low_rms_left
        results['low_band_rms_right'] = low_rms_right
        results['low_band_rms_left_db'] = db(low_rms_left)
        results['low_band_rms_right_db'] = db(low_rms_right)

        results['high_band_rms_left'] = high_rms_left
        results['high_band_rms_right'] = high_rms_right
        results['high_band_rms_left_db'] = db(high_rms_left)
        results['high_band_rms_right_db'] = db(high_rms_right)

        # Calculate relative levels (high band as reference)
        if high_rms_left > 0:
            results['low_vs_high_left_db'] = db(low_rms_left) - db(high_rms_left)
        if high_rms_right > 0:
            results['low_vs_high_right_db'] = db(low_rms_right) - db(high_rms_right)

    return results


def print_results(results, show_bands=False):
    """Pretty print analysis results."""
    print(f"\n{'='*60}")
    print(f"  LEVEL ANALYSIS: {results['filename']}")
    print(f"{'='*60}")
    print(f"Duration: {results['duration']:.1f}s | Sample rate: {results['sample_rate']} Hz")

    print(f"\n  OVERALL LEVELS")
    print(f"  {'-'*40}")
    print(f"  {'':12} | {'Left':>10} | {'Right':>10} | {'Total':>10}")
    print(f"  {'-'*40}")
    print(f"  {'RMS (dB)':<12} | {results['rms_left_db']:>10.2f} | {results['rms_right_db']:>10.2f} | {results['rms_total_db']:>10.2f}")
    print(f"  {'Peak (dB)':<12} | {results['peak_left_db']:>10.2f} | {results['peak_right_db']:>10.2f} | {results['peak_total_db']:>10.2f}")
    print(f"  {'RMS (linear)':<12} | {results['rms_left']:>10.6f} | {results['rms_right']:>10.6f} | {results['rms_total']:>10.6f}")
    print(f"  {'Peak (linear)':<12} | {results['peak_left']:>10.6f} | {results['peak_right']:>10.6f} | {results['peak_total']:>10.6f}")

    if show_bands and 'low_band_rms_left_db' in results:
        print(f"\n  BAND-SPECIFIC LEVELS")
        print(f"  {'-'*40}")
        print(f"  {'Band':<12} | {'Left (dB)':>10} | {'Right (dB)':>10}")
        print(f"  {'-'*40}")
        print(f"  {'Low (~60Hz)':<12} | {results['low_band_rms_left_db']:>10.2f} | {results['low_band_rms_right_db']:>10.2f}")
        print(f"  {'High (~310Hz)':<12} | {results['high_band_rms_left_db']:>10.2f} | {results['high_band_rms_right_db']:>10.2f}")

        if 'low_vs_high_left_db' in results:
            print(f"\n  RELATIVE LEVELS (Low vs High)")
            print(f"  {'-'*40}")
            print(f"  Left:  {results['low_vs_high_left_db']:>+.2f} dB")
            print(f"  Right: {results['low_vs_high_right_db']:>+.2f} dB")

    print()


def main():
    parser = argparse.ArgumentParser(description='Analyze audio file levels')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--bands', action='store_true', help='Analyze frequency bands')

    args = parser.parse_args()

    results = analyze_levels(args.audio_file, analyze_bands=args.bands)
    print_results(results, show_bands=args.bands)


if __name__ == "__main__":
    main()
