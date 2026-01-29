#!/usr/bin/env python3
"""
Binaural Beat Analyzer
Analyzes stereo audio files for binaural beat patterns over time.

Usage:
    python binaural_analyzer.py <audio_file> [options]

Options:
    --window SEC      Analysis window size in seconds (default: 20)
    --step SEC        Step size between windows in seconds (default: 5)
    --low-min HZ      Low carrier search minimum (default: auto-detect)
    --low-max HZ      Low carrier search maximum (default: auto-detect)
    --high-min HZ     High carrier search minimum (default: auto-detect)
    --high-max HZ     High carrier search maximum (default: auto-detect)
    --no-graph        Suppress ASCII graph output
    --csv             Output CSV format
    --spectrum        Show detailed spectrum debug (binaural candidates, top peaks)
"""

import argparse
import numpy as np
import librosa
from scipy import signal
from scipy.fft import fft, fftfreq
import sys
import os


def detect_carrier_ranges(y_left, y_right, sr, sample_duration=30):
    """Auto-detect carrier frequency ranges by analyzing a sample of the audio."""
    # Use first N seconds for detection
    n_samples = min(int(sample_duration * sr), len(y_left))
    left_sample = y_left[:n_samples]
    right_sample = y_right[:n_samples]

    def find_peaks_in_range(y, freq_min, freq_max):
        n = len(y)
        yf = np.abs(fft(y))[:n//2]
        xf = fftfreq(n, 1/sr)[:n//2]

        mask = (xf >= freq_min) & (xf <= freq_max)
        yf_masked = yf[mask]
        xf_masked = xf[mask]

        if len(yf_masked) == 0:
            return []

        threshold = np.max(yf_masked) * 0.1
        peaks, props = signal.find_peaks(yf_masked, height=threshold, distance=10)

        if len(peaks) == 0:
            return []

        # Return top peaks sorted by amplitude
        sorted_idx = np.argsort(props['peak_heights'])[::-1][:5]
        return [(xf_masked[peaks[i]], props['peak_heights'][i]) for i in sorted_idx]

    # Scan for peaks in different ranges
    ranges_to_check = [
        ("sub-bass", 30, 80),
        ("bass", 80, 150),
        ("low-mid", 150, 250),
        ("mid", 250, 400),
        ("high-mid", 400, 600),
    ]

    detected = {}
    for name, fmin, fmax in ranges_to_check:
        left_peaks = find_peaks_in_range(left_sample, fmin, fmax)
        right_peaks = find_peaks_in_range(right_sample, fmin, fmax)

        if left_peaks and right_peaks:
            # Check if there's a reasonable binaural beat (0.5 - 20 Hz difference)
            for lf, la in left_peaks[:2]:
                for rf, ra in right_peaks[:2]:
                    diff = abs(rf - lf)
                    if 0.5 < diff < 20:
                        avg_amp = (la + ra) / 2
                        if name not in detected or avg_amp > detected[name][2]:
                            detected[name] = (lf, rf, avg_amp, fmin, fmax)

    # Return the two strongest carrier regions
    if not detected:
        return None, None

    sorted_regions = sorted(detected.items(), key=lambda x: -x[1][2])

    low_range = None
    high_range = None

    for name, (lf, rf, amp, fmin, fmax) in sorted_regions:
        center = (lf + rf) / 2
        if center < 150 and low_range is None:
            low_range = (max(30, lf - 15), min(100, rf + 15))
        elif center >= 150 and high_range is None:
            high_range = (max(200, lf - 20), min(500, rf + 20))

    return low_range, high_range


def get_carrier_freq(y, sr, freq_min, freq_max):
    """Get the dominant frequency in a range using parabolic interpolation."""
    n = len(y)
    yf = np.abs(fft(y))[:n//2]
    xf = fftfreq(n, 1/sr)[:n//2]

    mask = (xf >= freq_min) & (xf <= freq_max)
    yf_masked = yf[mask]
    xf_masked = xf[mask]

    if len(yf_masked) == 0:
        return None

    peak_idx = np.argmax(yf_masked)

    # Parabolic interpolation for sub-bin accuracy
    if peak_idx > 0 and peak_idx < len(yf_masked) - 1:
        alpha = yf_masked[peak_idx - 1]
        beta = yf_masked[peak_idx]
        gamma = yf_masked[peak_idx + 1]

        if beta > 0 and (alpha - 2*beta + gamma) != 0:
            p = 0.5 * (alpha - gamma) / (alpha - 2*beta + gamma)
            freq_resolution = xf_masked[1] - xf_masked[0] if len(xf_masked) > 1 else 1
            return xf_masked[peak_idx] + p * freq_resolution

    return xf_masked[peak_idx]


def get_spectrum(y, sr, freq_min=30, freq_max=400):
    """Get power spectrum as (frequency, power_db) arrays."""
    n = len(y)
    yf = np.abs(fft(y))[:n//2]
    xf = fftfreq(n, 1/sr)[:n//2]
    yf_db = 20 * np.log10(yf + 1e-10)
    mask = (xf >= freq_min) & (xf <= freq_max)
    return xf[mask], yf_db[mask]


def find_binaural_candidates(y_left, y_right, sr, freq_min=30, freq_max=400, top_n=10):
    """Find potential binaural beat pairs between L/R channels."""
    freqs_l, powers_l = get_spectrum(y_left, sr, freq_min, freq_max)
    freqs_r, powers_r = get_spectrum(y_right, sr, freq_min, freq_max)

    # Find top peaks in each channel
    def get_top_peaks(freqs, powers, n=15):
        threshold = np.max(powers) - 30  # within 30dB of max
        peaks_idx, props = signal.find_peaks(powers, height=threshold, distance=5)
        if len(peaks_idx) == 0:
            return []
        sorted_idx = np.argsort(props['peak_heights'])[::-1][:n]
        return [(freqs[peaks_idx[i]], props['peak_heights'][i]) for i in sorted_idx]

    left_peaks = get_top_peaks(freqs_l, powers_l)
    right_peaks = get_top_peaks(freqs_r, powers_r)

    # Find pairs with 0.5-20 Hz difference (binaural beat range)
    candidates = []
    for lf, lp in left_peaks[:10]:
        for rf, rp in right_peaks[:10]:
            diff = abs(rf - lf)
            if 0.5 < diff < 20:
                candidates.append({
                    'left_freq': lf, 'right_freq': rf,
                    'binaural': diff,
                    'left_db': lp, 'right_db': rp,
                    'avg_db': (lp + rp) / 2
                })

    candidates.sort(key=lambda x: -x['avg_db'])
    return candidates[:top_n], left_peaks, right_peaks


def analyze_spectrum(filepath, start_sec=0, duration_sec=30, window_sec=10,
                     freq_min=30, freq_max=400):
    """Detailed spectrum analysis for debugging carrier detection."""
    y, sr = librosa.load(filepath, sr=None, mono=False)

    if y.ndim == 1:
        print("ERROR: Mono file", file=sys.stderr)
        return

    y_left, y_right = y[0], y[1]
    total_duration = len(y_left) / sr
    filename = os.path.basename(filepath)

    print(f"\n{'='*80}")
    print(f"  SPECTRUM DEBUG: {filename}")
    print(f"{'='*80}")
    print(f"Duration: {total_duration:.1f}s | Sample rate: {sr} Hz")
    print(f"Analyzing: {start_sec:.1f}s to {start_sec + duration_sec:.1f}s")
    print(f"Window: {window_sec}s | Freq range: {freq_min}-{freq_max} Hz")

    t = start_sec
    end_time = min(start_sec + duration_sec, total_duration - window_sec)

    while t <= end_time:
        start_sample = int(t * sr)
        end_sample = int((t + window_sec) * sr)

        left_seg = y_left[start_sample:end_sample]
        right_seg = y_right[start_sample:end_sample]

        candidates, left_peaks, right_peaks = find_binaural_candidates(
            left_seg, right_seg, sr, freq_min, freq_max
        )

        time_str = f"{int(t//60)}:{t%60:05.2f}"
        print(f"\n{'─'*80}")
        print(f"  WINDOW @ {time_str}")
        print(f"{'─'*80}")

        if candidates:
            print(f"\n  BINAURAL CANDIDATES:")
            print(f"  {'L Freq':>8} | {'R Freq':>8} | {'Beat':>6} | {'L dB':>6} | {'R dB':>6}")
            print(f"  {'-'*50}")
            for c in candidates[:6]:
                print(f"  {c['left_freq']:>8.2f} | {c['right_freq']:>8.2f} | "
                      f"{c['binaural']:>6.2f} | {c['left_db']:>6.1f} | {c['right_db']:>6.1f}")
        else:
            print("\n  No binaural candidates found in this window")

        print(f"\n  TOP PEAKS - Left: {', '.join(f'{f:.1f}Hz' for f, _ in left_peaks[:5])}")
        print(f"  TOP PEAKS - Right: {', '.join(f'{f:.1f}Hz' for f, _ in right_peaks[:5])}")

        t += window_sec


def analyze_binaural(filepath, window_sec=20, step_sec=5,
                     low_range=None, high_range=None,
                     show_graph=True, csv_output=False):
    """
    Analyze binaural beats in an audio file.

    Returns list of (time, low_binaural, high_binaural) tuples.
    """
    # Load audio
    y, sr = librosa.load(filepath, sr=None, mono=False)

    if y.ndim == 1:
        print("ERROR: Mono file - cannot analyze binaural beats", file=sys.stderr)
        return None

    y_left = y[0]
    y_right = y[1]

    duration = len(y_left) / sr
    filename = os.path.basename(filepath)

    # Auto-detect carrier ranges if not provided (but respect 'DISABLED' sentinel)
    low_disabled = low_range == 'DISABLED'
    high_disabled = high_range == 'DISABLED'

    if low_disabled:
        low_range = None
    if high_disabled:
        high_range = None

    # Only auto-detect for ranges that aren't explicitly set or disabled
    if (low_range is None and not low_disabled) or (high_range is None and not high_disabled):
        auto_low, auto_high = detect_carrier_ranges(y_left, y_right, sr)
        if low_range is None and not low_disabled:
            low_range = auto_low
        if high_range is None and not high_disabled:
            high_range = auto_high

    if not csv_output:
        print(f"\n{'='*75}")
        print(f"  {filename}")
        print(f"{'='*75}")
        print(f"Duration: {duration:.1f}s ({duration/60:.2f} min) | Window: {window_sec}s | Step: {step_sec}s")
        print(f"Sample rate: {sr} Hz | FFT resolution: ~{sr/(window_sec*sr):.4f} Hz")

        if low_range:
            print(f"Low carrier range: {low_range[0]:.0f}-{low_range[1]:.0f} Hz")
        else:
            print(f"Low carrier: DISABLED" if low_disabled else "Low carrier: not detected")
        if high_range:
            print(f"High carrier range: {high_range[0]:.0f}-{high_range[1]:.0f} Hz")
        else:
            print(f"High carrier: DISABLED" if high_disabled else "High carrier: not detected")

        if show_graph:
            print(f"\n{'Time':>8} | {'Binaural':>9} | {'Dom':>3} | Graph (3.5-5.5 Hz scale)")
            print("-" * 70)
    else:
        print(f"time_sec,binaural_low,binaural_high")

    results = []
    t = 0

    while t + window_sec <= duration:
        start_sample = int(t * sr)
        end_sample = int((t + window_sec) * sr)

        left_seg = y_left[start_sample:end_sample]
        right_seg = y_right[start_sample:end_sample]

        binaural_low = None
        binaural_high = None
        dominant_low = None  # 'L' or 'R' - which channel has higher freq
        dominant_high = None

        # Analyze low carrier
        if low_range:
            left_low = get_carrier_freq(left_seg, sr, low_range[0], low_range[1])
            right_low = get_carrier_freq(right_seg, sr, low_range[0], low_range[1])
            if left_low and right_low:
                binaural_low = abs(right_low - left_low)
                dominant_low = 'R' if right_low > left_low else 'L'

        # Analyze high carrier
        if high_range:
            left_high = get_carrier_freq(left_seg, sr, high_range[0], high_range[1])
            right_high = get_carrier_freq(right_seg, sr, high_range[0], high_range[1])
            if left_high and right_high:
                binaural_high = abs(right_high - left_high)
                dominant_high = 'R' if right_high > left_high else 'L'

        # Use whichever binaural we found (prefer high if both exist)
        binaural = binaural_high if binaural_high is not None else binaural_low
        dominant = dominant_high if dominant_high is not None else dominant_low

        results.append({
            'time': t,
            'binaural_low': binaural_low,
            'binaural_high': binaural_high,
            'binaural': binaural,
            'dominant_low': dominant_low,
            'dominant_high': dominant_high,
            'dominant': dominant
        })

        if csv_output:
            bl = f"{binaural_low:.3f}" if binaural_low else ""
            bh = f"{binaural_high:.3f}" if binaural_high else ""
            dl = dominant_low if dominant_low else ""
            dh = dominant_high if dominant_high else ""
            print(f"{t},{bl},{bh},{dl},{dh}")
        elif show_graph and binaural is not None:
            time_str = f"{int(t//60)}:{t%60:05.2f}"
            bar_len = int((binaural - 3.5) * 15)
            bar = "█" * max(0, min(30, bar_len))
            dom_str = dominant if dominant else "?"
            print(f"{time_str:>8} | {binaural:>9.3f} |  {dom_str}  | {bar}")
        elif not csv_output:
            time_str = f"{int(t//60)}:{t%60:05.2f}"
            print(f"{time_str:>8} | {'N/A':>9} |  ?  |")

        t += step_sec

    # Summary
    if not csv_output:
        binaurals = [r['binaural'] for r in results if r['binaural'] is not None]
        dominants = [r['dominant'] for r in results if r['dominant'] is not None]
        if binaurals:
            print("-" * 70)
            # Check dominant consistency
            dom_counts = {'L': dominants.count('L'), 'R': dominants.count('R')}
            dom_primary = 'R' if dom_counts['R'] >= dom_counts['L'] else 'L'
            dom_pct = dom_counts[dom_primary] / len(dominants) * 100 if dominants else 0

            print(f"Range: {min(binaurals):.3f} → {max(binaurals):.3f} Hz | "
                  f"Sweep: {binaurals[0]:.3f} → {binaurals[-1]:.3f} Hz "
                  f"(Δ {binaurals[-1] - binaurals[0]:+.3f} Hz) | "
                  f"Dom: {dom_primary} ({dom_pct:.0f}%)")

    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze binaural beats in audio files')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--window', type=float, default=20, help='Window size in seconds')
    parser.add_argument('--step', type=float, default=5, help='Step size in seconds')
    parser.add_argument('--low-min', type=float, help='Low carrier min frequency')
    parser.add_argument('--low-max', type=float, help='Low carrier max frequency')
    parser.add_argument('--high-min', type=float, help='High carrier min frequency')
    parser.add_argument('--high-max', type=float, help='High carrier max frequency')
    parser.add_argument('--no-low', action='store_true', help='Disable low carrier detection')
    parser.add_argument('--no-high', action='store_true', help='Disable high carrier detection')
    parser.add_argument('--no-graph', action='store_true', help='Suppress graph')
    parser.add_argument('--csv', action='store_true', help='CSV output')
    parser.add_argument('--spectrum', action='store_true',
                        help='Spectrum debug mode: show binaural candidates and top peaks')
    parser.add_argument('--start', type=float, default=0,
                        help='Start time for spectrum mode (seconds)')
    parser.add_argument('--duration', type=float, default=30,
                        help='Duration for spectrum mode (seconds)')
    parser.add_argument('--freq-min', type=float, default=30,
                        help='Min frequency for spectrum mode')
    parser.add_argument('--freq-max', type=float, default=400,
                        help='Max frequency for spectrum mode')

    args = parser.parse_args()

    low_range = None
    high_range = None

    # Handle carrier range options
    # --no-low/--no-high explicitly disables that carrier (use 'DISABLED' sentinel)
    # --low-min/--low-max sets a specific range
    # Otherwise auto-detect is used (None)
    low_range = None
    high_range = None

    if args.no_low:
        low_range = 'DISABLED'
    elif args.low_min and args.low_max:
        low_range = (args.low_min, args.low_max)

    if args.no_high:
        high_range = 'DISABLED'
    elif args.high_min and args.high_max:
        high_range = (args.high_min, args.high_max)

    if args.spectrum:
        analyze_spectrum(
            args.audio_file,
            start_sec=args.start,
            duration_sec=args.duration,
            window_sec=args.window,
            freq_min=args.freq_min,
            freq_max=args.freq_max
        )
    else:
        analyze_binaural(
            args.audio_file,
            window_sec=args.window,
            step_sec=args.step,
            low_range=low_range,
            high_range=high_range,
            show_graph=not args.no_graph,
            csv_output=args.csv
        )


if __name__ == "__main__":
    main()
