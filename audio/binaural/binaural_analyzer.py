#!/usr/bin/env python3
"""
Binaural Beat & Isochronic Pulse Analyzer

Analyzes stereo audio files for binaural beat patterns and isochronic
pulse rates over time. Detects all carrier pairs automatically (open-ended,
no fixed "high/low" assumption), tracks binaural beats per carrier, and
measures amplitude modulation (isochronic pulse) per carrier.

Usage:
    python binaural_analyzer.py <audio_file> [options]

Modes:
    (default)     Sliding-window analysis with ASCII graph
    --spectrum    Detailed spectrum debug (peaks, candidates per window)
    --verify      Verify generated audio against a JSON config file
    --spectrogram Generate spectrogram PNG with carrier trajectory overlay

Options:
    --window SEC              Analysis window size in seconds (default: 10)
    --step SEC                Step between windows in seconds (default: 5)
    --expected-carriers HZ    Comma-separated center frequencies to look for
    --freq-min HZ             Min frequency for detection (default: 30)
    --freq-max HZ             Max frequency for detection (default: auto-detect)
    --no-graph                Suppress ASCII graph output
    --no-isochronic           Skip isochronic pulse detection (faster)
    --csv                     Output CSV format
    --verify FILE             Verify against generator JSON config
    --spectrum                Show detailed spectrum debug
    --spectrogram             Generate spectrogram PNG with carrier overlay
    --spectrogram-lr          L/R split spectrogram (implies --spectrogram)
    --output / -o PATH        Output path for spectrogram PNG
"""

import argparse
import json
import numpy as np
import librosa
from scipy import signal as scipy_signal
from scipy.fft import fft, fftfreq
import sys
import os
import gc

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    HAS_MATPLOTLIB = True
    # Per-channel colormaps: dark (low dB) → bright (high dB)
    _CMAP_LEFT = LinearSegmentedColormap.from_list(
        'teal_heat', ['#000011', '#002233', '#005577', '#009999', '#44eedd'], N=256)
    _CMAP_RIGHT = LinearSegmentedColormap.from_list(
        'red_heat', ['#110000', '#330000', '#880000', '#cc3300', '#ff8855'], N=256)
    _CMAP_MONO = 'viridis'
    # Marker colors for L/R carrier trajectories
    _COLOR_L = '#00ccbb'   # teal
    _COLOR_R = '#ff4422'   # red
except ImportError:
    HAS_MATPLOTLIB = False

# Reduced sample rate for analysis — sufficient for carriers up to ~3500 Hz,
# cuts memory ~5.5x vs loading at 44100 Hz
ANALYSIS_SR = 8000


# === Spectrum Utilities ===

def get_carrier_freq(y, sr, freq_min, freq_max, min_snr_db=10.0, guard_hz=1.0):
    """Get the dominant frequency in a range, with SNR gating.

    Returns dict {'freq_hz', 'peak_db', 'noise_db', 'snr_db'} or None
    if no tone is significantly above the noise floor.
    """
    n = len(y)
    if n < 8:
        return None

    win = np.hanning(n)
    yf = np.abs(fft(y * win))[:n // 2]
    xf = fftfreq(n, 1 / sr)[:n // 2]

    mask = (xf >= freq_min) & (xf <= freq_max)
    yf_masked = yf[mask]
    xf_masked = xf[mask]

    if len(yf_masked) < 8:
        return None

    yf_db = 20 * np.log10(yf_masked + 1e-12)
    peak_idx = np.argmax(yf_db)
    peak_db = float(yf_db[peak_idx])

    # Parabolic interpolation for sub-bin accuracy
    freq_est = float(xf_masked[peak_idx])
    if 0 < peak_idx < len(yf_db) - 1:
        a, b, c = yf_db[peak_idx - 1], yf_db[peak_idx], yf_db[peak_idx + 1]
        denom = a - 2 * b + c
        if denom != 0:
            p = 0.5 * (a - c) / denom
            bin_hz = xf_masked[1] - xf_masked[0] if len(xf_masked) > 1 else 1.0
            freq_est += p * bin_hz

    # Noise floor: median of band excluding guard bins around peak
    bin_hz = xf_masked[1] - xf_masked[0] if len(xf_masked) > 1 else 1.0
    guard_bins = max(1, int(guard_hz / bin_hz))
    lo = max(0, peak_idx - guard_bins)
    hi = min(len(yf_db), peak_idx + guard_bins + 1)
    noise_vals = np.concatenate([yf_db[:lo], yf_db[hi:]])

    if len(noise_vals) < 4:
        return None

    noise_db = float(np.median(noise_vals))
    snr_db = peak_db - noise_db

    if snr_db < min_snr_db:
        return None

    return {
        'freq_hz': freq_est,
        'peak_db': peak_db,
        'noise_db': noise_db,
        'snr_db': snr_db,
    }


def get_spectrum(y, sr, freq_min=30, freq_max=600):
    """Get power spectrum as (frequency, power_db) arrays."""
    n = len(y)
    yf = np.abs(fft(y))[:n // 2]
    xf = fftfreq(n, 1 / sr)[:n // 2]
    yf_db = 20 * np.log10(yf + 1e-10)
    mask = (xf >= freq_min) & (xf <= freq_max)
    return xf[mask], yf_db[mask]


def find_peaks_in_spectrum(y, sr, freq_min=30, freq_max=600, threshold_db=20, max_peaks=20):
    """Find prominent peaks in a channel's spectrum.

    Args:
        y: Audio samples (single channel)
        sr: Sample rate
        freq_min: Minimum frequency to search
        freq_max: Maximum frequency to search
        threshold_db: Only return peaks within this many dB of the maximum
        max_peaks: Maximum number of peaks to return

    Returns:
        List of (frequency, power_db) tuples sorted by power (descending)
    """
    freqs, powers = get_spectrum(y, sr, freq_min, freq_max)
    if len(powers) == 0:
        return []

    threshold = np.max(powers) - threshold_db
    peaks_idx, props = scipy_signal.find_peaks(powers, height=threshold, distance=5)

    if len(peaks_idx) == 0:
        return []

    sorted_idx = np.argsort(props['peak_heights'])[::-1][:max_peaks]
    return [(freqs[peaks_idx[i]], props['peak_heights'][i]) for i in sorted_idx]


# === Isochronic Pulse Detection ===

def detect_isochronic_rate(y, sr, carrier_freq, bandwidth=15,
                           pulse_range=(0.5, 15), min_confidence=0.3):
    """
    Detect isochronic pulse rate for a carrier in a single channel.

    Bandpasses around the carrier, extracts the amplitude envelope via
    Hilbert transform, then FFTs the envelope to find the dominant
    modulation frequency.

    Args:
        y: Audio samples (single channel)
        sr: Sample rate
        carrier_freq: Center frequency of the carrier to analyze
        bandwidth: Hz on each side of carrier for bandpass (default: 15)
        pulse_range: (min_hz, max_hz) valid pulse rate range
        min_confidence: Minimum peak-to-noise ratio to report a detection

    Returns:
        (pulse_hz, confidence) where confidence is peak prominence
        relative to noise floor, or (None, 0.0) if no pulse detected.
    """
    # 1. Bandpass filter around carrier (SOS format for numerical stability)
    nyq = sr / 2
    low = max(carrier_freq - bandwidth, 1) / nyq
    high = min(carrier_freq + bandwidth, nyq - 1) / nyq
    if low >= high or low <= 0 or high >= 1:
        return (None, 0.0)

    try:
        sos = scipy_signal.butter(4, [low, high], btype='band', output='sos')
        filtered = scipy_signal.sosfiltfilt(sos, y)
    except ValueError:
        return (None, 0.0)

    # 2. Hilbert transform → amplitude envelope
    analytic = scipy_signal.hilbert(filtered)
    envelope = np.abs(analytic)

    # 3. Remove DC and apply window
    envelope = envelope - np.mean(envelope)
    envelope = envelope * np.hanning(len(envelope))

    # 4. FFT the envelope
    n = len(envelope)
    env_fft = np.abs(fft(envelope))[:n // 2]
    env_freqs = fftfreq(n, 1 / sr)[:n // 2]

    # 5. Find peak in pulse_range
    mask = (env_freqs >= pulse_range[0]) & (env_freqs <= pulse_range[1])
    if not np.any(mask):
        return (None, 0.0)

    env_fft_masked = env_fft[mask]
    env_freqs_masked = env_freqs[mask]

    peak_idx = np.argmax(env_fft_masked)
    peak_power = env_fft_masked[peak_idx]

    # Noise floor: median of the masked range
    noise_floor = np.median(env_fft_masked)
    if noise_floor <= 0:
        noise_floor = 1e-10
    confidence = peak_power / noise_floor

    if confidence < min_confidence:
        return (None, 0.0)

    # 6. Parabolic interpolation for sub-bin accuracy
    freq = env_freqs_masked[peak_idx]
    if 0 < peak_idx < len(env_fft_masked) - 1:
        alpha = env_fft_masked[peak_idx - 1]
        beta = env_fft_masked[peak_idx]
        gamma = env_fft_masked[peak_idx + 1]
        denom = alpha - 2 * beta + gamma
        if denom != 0 and beta > 0:
            p = 0.5 * (alpha - gamma) / denom
            freq_resolution = env_freqs_masked[1] - env_freqs_masked[0]
            freq = freq + p * freq_resolution

    return (freq, confidence)


# === Carrier Pair Detection ===

def detect_carrier_pairs(y_left, y_right, sr, freq_min=30, freq_max=600,
                         sample_duration=30, beat_range=(0.5, 20)):
    """
    Auto-detect all carrier pairs by finding L/R peak pairs with binaural-range
    frequency differences. Open-ended - no assumptions about how many pairs exist
    or where they are.

    Args:
        y_left: Left channel audio
        y_right: Right channel audio
        sr: Sample rate
        freq_min: Minimum frequency to scan
        freq_max: Maximum frequency to scan
        sample_duration: Seconds of audio to use for detection
        beat_range: (min_hz, max_hz) for valid binaural beat differences

    Returns:
        List of carrier pair dicts sorted by amplitude:
        [{'center_hz': float, 'left_hz': float, 'right_hz': float,
          'binaural_hz': float, 'avg_db': float, 'search_range': (min, max)}]
    """
    n_samples = min(int(sample_duration * sr), len(y_left))
    left_sample = y_left[:n_samples]
    right_sample = y_right[:n_samples]

    left_peaks = find_peaks_in_spectrum(left_sample, sr, freq_min, freq_max)
    right_peaks = find_peaks_in_spectrum(right_sample, sr, freq_min, freq_max)

    if not left_peaks or not right_peaks:
        return []

    # Find all L/R pairs with binaural-range differences
    raw_pairs = []
    for lf, lp in left_peaks:
        for rf, rp in right_peaks:
            diff = abs(rf - lf)
            if beat_range[0] <= diff <= beat_range[1]:
                center = (lf + rf) / 2
                raw_pairs.append({
                    'center_hz': center,
                    'left_hz': lf,
                    'right_hz': rf,
                    'binaural_hz': diff,
                    'left_db': lp,
                    'right_db': rp,
                    'avg_db': (lp + rp) / 2,
                })

    if not raw_pairs:
        return []

    # Cluster nearby pairs (within 25 Hz of each other's center) - keep strongest
    raw_pairs.sort(key=lambda p: -p['avg_db'])
    clusters = []
    used = set()

    for i, pair in enumerate(raw_pairs):
        if i in used:
            continue
        cluster = [pair]
        for j, other in enumerate(raw_pairs[i + 1:], i + 1):
            if j in used:
                continue
            if abs(other['center_hz'] - pair['center_hz']) < 25:
                used.add(j)
        used.add(i)

        # Use the strongest pair in the cluster
        best = cluster[0]
        # Define search range around this carrier pair
        margin = max(15, best['binaural_hz'] * 2)
        search_min = max(freq_min, min(best['left_hz'], best['right_hz']) - margin)
        search_max = min(freq_max, max(best['left_hz'], best['right_hz']) + margin)
        best['search_range'] = (search_min, search_max)
        clusters.append(best)

    # Sort by center frequency
    clusters.sort(key=lambda p: p['center_hz'])
    return clusters


def build_carrier_ranges_from_centers(centers, margin=15, freq_min=30, freq_max=600):
    """Build search ranges from known center frequencies.

    Args:
        centers: List of center frequencies in Hz
        margin: Hz margin around each center
        freq_min: Global min frequency
        freq_max: Global max frequency

    Returns:
        List of dicts with 'center_hz' and 'search_range'
    """
    ranges = []
    for center in sorted(centers):
        ranges.append({
            'center_hz': center,
            'search_range': (max(freq_min, center - margin), min(freq_max, center + margin)),
            'left_hz': None, 'right_hz': None,
            'binaural_hz': None, 'avg_db': None,
        })
    return ranges


# === Auto-Detection ===

def auto_detect_freq_range(y_left, y_right, sr, sample_duration=30, floor_db=40):
    """Find the useful frequency ceiling from a short sample."""
    n_samples = min(int(sample_duration * sr), len(y_left))
    mono = (y_left[:n_samples] + y_right[:n_samples]) / 2

    n = len(mono)
    yf = np.abs(fft(mono))[:n // 2]
    xf = fftfreq(n, 1 / sr)[:n // 2]

    mask = (xf >= 30) & (xf <= 2000)
    yf_masked = yf[mask]
    xf_masked = xf[mask]

    if len(yf_masked) == 0:
        return 1200

    yf_db = 20 * np.log10(yf_masked + 1e-10)
    peak_db = np.max(yf_db)
    above = xf_masked[yf_db > peak_db - floor_db]

    if len(above) == 0:
        return 1200

    highest = float(np.max(above))
    freq_max = max(600, int(np.ceil((highest * 1.2) / 50) * 50))
    return min(freq_max, 2000)


def detect_carriers_median(y_left, y_right, sr, freq_min=30, freq_max=600,
                            n_segments=20, segment_sec=10,
                            beat_range=(0.5, 20), threshold_db=25):
    """
    Detect carrier pairs using median spectrum analysis.

    Samples N segments across the file, computes the FFT of each, and takes
    the median power at each frequency bin. Pure tone carriers survive the
    median; transient content (voice, music) gets suppressed.
    """
    total_samples = len(y_left)
    seg_samples = min(int(segment_sec * sr), total_samples)

    if total_samples <= int(seg_samples * 1.5):
        starts = [0]
    else:
        usable = total_samples - seg_samples
        actual_n = min(n_segments, max(3, total_samples // seg_samples))
        starts = [int(i * usable / max(1, actual_n - 1)) for i in range(actual_n)]

    half = seg_samples // 2
    freq_bins = fftfreq(seg_samples, 1 / sr)[:half]
    left_spectra = []
    right_spectra = []

    for start in starts:
        l_seg = y_left[start:start + seg_samples]
        r_seg = y_right[start:start + seg_samples]
        win = np.hanning(len(l_seg))
        left_spectra.append(np.abs(fft(l_seg * win))[:half])
        right_spectra.append(np.abs(fft(r_seg * win))[:half])

    left_median = np.median(np.array(left_spectra), axis=0)
    right_median = np.median(np.array(right_spectra), axis=0)

    mask = (freq_bins >= freq_min) & (freq_bins <= freq_max)
    freqs = freq_bins[mask]
    left_db = 20 * np.log10(left_median[mask] + 1e-10)
    right_db = 20 * np.log10(right_median[mask] + 1e-10)

    def _find_peaks_db(spectrum, freqs_arr):
        if len(spectrum) == 0:
            return []
        threshold = np.max(spectrum) - threshold_db
        idx, props = scipy_signal.find_peaks(spectrum, height=threshold, distance=5)
        if len(idx) == 0:
            return []
        order = np.argsort(props['peak_heights'])[::-1][:20]
        peaks = []
        freq_res = freqs_arr[1] - freqs_arr[0] if len(freqs_arr) > 1 else 1.0
        for i in order:
            pi = idx[i]
            f = freqs_arr[pi]
            if 0 < pi < len(spectrum) - 1:
                a, b, c = spectrum[pi - 1], spectrum[pi], spectrum[pi + 1]
                denom = a - 2 * b + c
                if denom != 0:
                    f += 0.5 * (a - c) / denom * freq_res
            peaks.append((f, props['peak_heights'][i]))
        return peaks

    l_peaks = _find_peaks_db(left_db, freqs)
    r_peaks = _find_peaks_db(right_db, freqs)
    if not l_peaks or not r_peaks:
        return []

    # Binaural pairs: L/R with beat-range frequency difference
    raw_pairs = []
    for lf, lp in l_peaks:
        for rf, rp in r_peaks:
            diff = abs(rf - lf)
            if beat_range[0] <= diff <= beat_range[1]:
                raw_pairs.append({
                    'center_hz': (lf + rf) / 2,
                    'left_hz': lf, 'right_hz': rf,
                    'binaural_hz': diff,
                    'avg_db': (lp + rp) / 2,
                    'detection_type': 'binaural',
                })

    # Mono carriers: same freq in L and R (isochronic-only)
    for lf, lp in l_peaks:
        for rf, rp in r_peaks:
            if abs(rf - lf) < 1.0:
                center = (lf + rf) / 2
                if not any(abs(center - p['center_hz']) < 25 for p in raw_pairs):
                    raw_pairs.append({
                        'center_hz': center,
                        'left_hz': lf, 'right_hz': rf,
                        'binaural_hz': 0.0,
                        'avg_db': (lp + rp) / 2,
                        'detection_type': 'mono',
                    })

    if not raw_pairs:
        return []

    # Cluster nearby (within 25 Hz), keep strongest
    raw_pairs.sort(key=lambda p: -p['avg_db'])
    result = []
    used = set()
    for i, pair in enumerate(raw_pairs):
        if i in used:
            continue
        used.add(i)
        for j in range(i + 1, len(raw_pairs)):
            if j not in used and abs(raw_pairs[j]['center_hz'] - pair['center_hz']) < 25:
                used.add(j)
        margin = max(15, pair['binaural_hz'] * 2)
        lo = max(freq_min, min(pair['left_hz'], pair['right_hz']) - margin)
        hi = min(freq_max, max(pair['left_hz'], pair['right_hz']) + margin)
        pair['search_range'] = (lo, hi)
        result.append(pair)

    result.sort(key=lambda p: p['center_hz'])
    return result[:6]


def update_carrier_search_ranges(carrier_pairs, window_results, freq_min, freq_max, max_drift_hz=5):
    """Adaptively nudge carrier search ranges toward measured frequencies."""
    for pair, result in zip(carrier_pairs, window_results):
        if result['left_hz'] is None or result['right_hz'] is None:
            continue
        measured_center = result['center_hz']
        current_center = (pair['search_range'][0] + pair['search_range'][1]) / 2
        delta = measured_center - current_center
        if abs(delta) > max_drift_hz:
            delta = max_drift_hz if delta > 0 else -max_drift_hz
        new_center = current_center + delta
        half_width = (pair['search_range'][1] - pair['search_range'][0]) / 2
        pair['search_range'] = (max(freq_min, new_center - half_width),
                                min(freq_max, new_center + half_width))


# === Analysis Functions ===

def analyze_window(y_left, y_right, sr, carrier_pairs, detect_pulse=True):
    """
    Analyze a single window for binaural beats and isochronic pulses
    at each carrier pair.

    Args:
        y_left: Left channel window
        y_right: Right channel window
        sr: Sample rate
        carrier_pairs: List of carrier pair dicts with 'search_range'
        detect_pulse: Whether to run isochronic pulse detection (pass 2)

    Returns:
        List of result dicts per carrier pair:
        [{'center_hz': float, 'left_hz': float, 'right_hz': float,
          'binaural_hz': float, 'dominant': 'L'|'R',
          'pulse_hz': float|None, 'pulse_confidence': float}]
    """
    results = []
    for pair in carrier_pairs:
        fmin, fmax = pair['search_range']
        left_m = get_carrier_freq(y_left, sr, fmin, fmax)
        right_m = get_carrier_freq(y_right, sr, fmin, fmax)

        if left_m is not None and right_m is not None:
            left_freq = left_m['freq_hz']
            right_freq = right_m['freq_hz']
            binaural = abs(right_freq - left_freq)
            dominant = 'R' if right_freq > left_freq else 'L'
            center = (left_freq + right_freq) / 2
            result = {
                'center_hz': center,
                'left_hz': left_freq,
                'right_hz': right_freq,
                'binaural_hz': binaural,
                'dominant': dominant,
                'pulse_hz': None,
                'pulse_confidence': 0.0,
            }
        else:
            center = pair['center_hz']
            result = {
                'center_hz': center,
                'left_hz': None,
                'right_hz': None,
                'binaural_hz': None,
                'dominant': None,
                'pulse_hz': None,
                'pulse_confidence': 0.0,
            }

        # Pass 2: isochronic pulse detection
        if detect_pulse:
            l_pulse, l_conf = detect_isochronic_rate(y_left, sr, center)
            r_pulse, r_conf = detect_isochronic_rate(y_right, sr, center)

            # Average L/R pulse rates (should be identical for isochronic)
            if l_pulse is not None and r_pulse is not None:
                result['pulse_hz'] = (l_pulse + r_pulse) / 2
                result['pulse_confidence'] = (l_conf + r_conf) / 2
            elif l_pulse is not None:
                result['pulse_hz'] = l_pulse
                result['pulse_confidence'] = l_conf
            elif r_pulse is not None:
                result['pulse_hz'] = r_pulse
                result['pulse_confidence'] = r_conf

        results.append(result)

    return results


def analyze_binaural(filepath, window_sec=10, step_sec=5,
                     carrier_pairs=None, expected_carriers=None,
                     freq_min=30, freq_max=None,
                     show_graph=True, csv_output=False,
                     detect_pulse=True,
                     spectrogram=False, spectrogram_lr=False,
                     output_path=None):
    """
    Analyze binaural beats and isochronic pulses in an audio file.

    Loads at reduced sample rate (ANALYSIS_SR) to prevent OOM on large files.
    Uses median-spectrum carrier detection to reject voice/music content.
    SNR-gated per-window tracking returns N/A when no tone is present.

    Returns:
        (all_results, carrier_pairs) tuple
    """
    y, sr = librosa.load(filepath, sr=ANALYSIS_SR, mono=False)

    if y.ndim == 1:
        print("ERROR: Mono file - cannot analyze binaural beats", file=sys.stderr)
        return None, None

    y_left, y_right = y[0], y[1]
    del y
    duration = len(y_left) / sr
    filename = os.path.basename(filepath)

    # Auto-detect frequency range if not specified
    if freq_max is None:
        freq_max = auto_detect_freq_range(y_left, y_right, sr)
        if not csv_output:
            print(f"Auto-detected freq range: {freq_min}-{freq_max} Hz")

    # Determine carrier pairs
    if carrier_pairs is None:
        if expected_carriers:
            carrier_pairs = build_carrier_ranges_from_centers(
                expected_carriers, freq_min=freq_min, freq_max=freq_max
            )
        else:
            carrier_pairs = detect_carriers_median(
                y_left, y_right, sr, freq_min=freq_min, freq_max=freq_max
            )

    if not carrier_pairs:
        print("No carrier pairs detected. Try --spectrum mode or --expected-carriers.")
        if spectrogram or spectrogram_lr:
            generate_spectrogram(filepath, freq_min=freq_min, freq_max=freq_max,
                                 output_path=output_path, lr_split=spectrogram_lr)
        return None, None

    n_carriers = len(carrier_pairs)

    if not csv_output:
        print(f"\n{'=' * 75}")
        print(f"  {filename}")
        print(f"{'=' * 75}")
        print(f"Duration: {duration:.1f}s ({duration / 60:.2f} min) | "
              f"Window: {window_sec}s | Step: {step_sec}s")
        print(f"Sample rate: {sr} Hz | FFT resolution: ~{1 / window_sec:.4f} Hz")
        mode_str = "binaural + isochronic" if detect_pulse else "binaural only"
        print(f"Mode: {mode_str}")
        print(f"Detected {n_carriers} carrier(s):")
        for i, pair in enumerate(carrier_pairs):
            center = pair['center_hz']
            fmin_r, fmax_r = pair['search_range']
            det_type = pair.get('detection_type', 'binaural')
            if pair.get('binaural_hz') is not None and pair['binaural_hz'] > 0:
                print(f"  [{i}] ~{center:.1f} Hz (range {fmin_r:.0f}-{fmax_r:.0f}) "
                      f"| L={pair['left_hz']:.1f} R={pair['right_hz']:.1f} "
                      f"| beat={pair['binaural_hz']:.2f} Hz ({det_type})")
            else:
                print(f"  [{i}] ~{center:.1f} Hz (range {fmin_r:.0f}-{fmax_r:.0f}) ({det_type})")
        print()

    # Collect all data with adaptive search range tracking
    all_results = []
    t = 0
    while t + window_sec <= duration:
        start_sample = int(t * sr)
        end_sample = int((t + window_sec) * sr)
        left_seg = y_left[start_sample:end_sample]
        right_seg = y_right[start_sample:end_sample]

        window_results = analyze_window(left_seg, right_seg, sr, carrier_pairs,
                                        detect_pulse=detect_pulse)
        all_results.append({'time': t, 'carriers': window_results})

        # Adaptive search range update
        update_carrier_search_ranges(carrier_pairs, window_results, freq_min, freq_max)

        t += step_sec

    if csv_output:
        # CSV header
        headers = ['time_sec']
        for i in range(n_carriers):
            headers.extend([f'carrier_{i}_center', f'carrier_{i}_binaural',
                            f'carrier_{i}_dominant'])
            if detect_pulse:
                headers.append(f'carrier_{i}_pulse_hz')
        print(','.join(headers))

        for result in all_results:
            row = [f"{result['time']:.1f}"]
            for cr in result['carriers']:
                row.append(f"{cr['center_hz']:.2f}")
                row.append(f"{cr['binaural_hz']:.3f}" if cr['binaural_hz'] is not None else "")
                row.append(cr['dominant'] if cr['dominant'] else "")
                if detect_pulse:
                    row.append(f"{cr['pulse_hz']:.3f}" if cr.get('pulse_hz') is not None else "")
            print(','.join(row))

    elif show_graph:
        # Auto-scale graph from data
        all_binaurals = []
        for result in all_results:
            for cr in result['carriers']:
                if cr['binaural_hz'] is not None:
                    all_binaurals.append(cr['binaural_hz'])

        if not all_binaurals:
            print("No binaural beats detected in any window.")
            return all_results, carrier_pairs

        graph_min = max(0, min(all_binaurals) - 0.5)
        graph_max = max(all_binaurals) + 0.5
        graph_range = graph_max - graph_min
        graph_width = 30

        # Print header per carrier
        if n_carriers == 1:
            header = f"{'Time':>8} | {'Binaural':>9} | {'Dom':>3}"
            if detect_pulse:
                header += f" | {'Pulse':>6}"
            header += f" | Graph ({graph_min:.1f}-{graph_max:.1f} Hz)"
            print(header)
            print("-" * 75)
        else:
            carrier_labels = ' | '.join(
                f"C{i}({carrier_pairs[i]['center_hz']:.0f}Hz)"
                for i in range(n_carriers)
            )
            print(f"{'Time':>8} | {carrier_labels}")
            col_width = 28 if detect_pulse else 22
            print("-" * (12 + n_carriers * col_width))

        for result in all_results:
            time_str = f"{int(result['time'] // 60)}:{result['time'] % 60:05.2f}"

            if n_carriers == 1:
                cr = result['carriers'][0]
                if cr['binaural_hz'] is not None:
                    bar_pos = (cr['binaural_hz'] - graph_min) / graph_range * graph_width
                    bar = "." * max(0, int(bar_pos)) + "|"
                    dom = cr['dominant'] or '?'
                    line = f"{time_str:>8} | {cr['binaural_hz']:>9.3f} |  {dom} "
                    if detect_pulse:
                        pulse_str = f"{cr['pulse_hz']:.2f}" if cr.get('pulse_hz') is not None else "  -  "
                        line += f" | {pulse_str:>6}"
                    line += f" | {bar}"
                    print(line)
                else:
                    line = f"{time_str:>8} | {'N/A':>9} |  ? "
                    if detect_pulse:
                        line += f" | {'  -  ':>6}"
                    line += " |"
                    print(line)
            else:
                parts = [f"{time_str:>8}"]
                for cr in result['carriers']:
                    if cr['binaural_hz'] is not None:
                        dom = cr['dominant'] or '?'
                        part = f"{cr['binaural_hz']:>6.2f} {dom}"
                        if detect_pulse:
                            if cr.get('pulse_hz') is not None:
                                part += f" p={cr['pulse_hz']:<5.2f}"
                            else:
                                part += f" {'':8}"
                        bar_pos = (cr['binaural_hz'] - graph_min) / graph_range * 10
                        bar = "." * max(0, int(bar_pos)) + "|"
                        part += f" {bar:<6}"
                        parts.append(part)
                    else:
                        pad = 20 if not detect_pulse else 28
                        parts.append(f"{'N/A':>6}{'':>{pad - 6}}")
                print(' | '.join(parts))

    # Summary per carrier
    if not csv_output:
        print("-" * 75)
        print("Summary:")
        for i, pair in enumerate(carrier_pairs):
            binaurals = [r['carriers'][i]['binaural_hz']
                         for r in all_results
                         if r['carriers'][i]['binaural_hz'] is not None]
            dominants = [r['carriers'][i]['dominant']
                         for r in all_results
                         if r['carriers'][i]['dominant'] is not None]
            pulses = [r['carriers'][i].get('pulse_hz')
                      for r in all_results
                      if r['carriers'][i].get('pulse_hz') is not None]

            if binaurals:
                dom_counts = {'L': dominants.count('L'), 'R': dominants.count('R')}
                dom_primary = 'R' if dom_counts['R'] >= dom_counts['L'] else 'L'
                dom_pct = dom_counts[dom_primary] / len(dominants) * 100 if dominants else 0

                label = f"~{pair['center_hz']:.0f} Hz"
                binaural_str = f"binaural {binaurals[0]:.3f} -> {binaurals[-1]:.3f} Hz"
                if abs(binaurals[-1] - binaurals[0]) < 0.1:
                    binaural_str = f"binaural {np.mean(binaurals):.3f} Hz (static)"

                pulse_str = ""
                if detect_pulse and pulses:
                    if abs(pulses[-1] - pulses[0]) < 0.2:
                        pulse_str = f" | pulse {np.mean(pulses):.2f} Hz (static)"
                    else:
                        pulse_str = f" | pulse {pulses[0]:.2f} -> {pulses[-1]:.2f} Hz"

                print(f"  [{i}] {label}: {binaural_str}{pulse_str}"
                      f" | Dom: {dom_primary} ({dom_pct:.0f}%)")
            else:
                print(f"  [{i}] ~{pair['center_hz']:.0f} Hz: no data")

    # Generate spectrogram if requested
    if spectrogram or spectrogram_lr:
        del y_left, y_right
        gc.collect()

        carrier_trajectories = []
        for i in range(n_carriers):
            times_list, left_list, right_list = [], [], []
            for r in all_results:
                t_mid = r['time'] + window_sec / 2
                cr = r['carriers'][i]
                times_list.append(t_mid)
                left_list.append(cr['left_hz'] if cr.get('left_hz') is not None else float('nan'))
                right_list.append(cr['right_hz'] if cr.get('right_hz') is not None else float('nan'))
            carrier_trajectories.append({
                'times': times_list, 'left_hz': left_list, 'right_hz': right_list,
            })

        generate_spectrogram(filepath, carrier_trajectories=carrier_trajectories,
                             carrier_pairs=carrier_pairs,
                             freq_min=freq_min, freq_max=freq_max,
                             output_path=output_path, lr_split=spectrogram_lr)

    return all_results, carrier_pairs


def analyze_spectrum(filepath, start_sec=0, duration_sec=30, window_sec=10,
                     freq_min=30, freq_max=600):
    """Detailed spectrum analysis for debugging carrier detection."""
    y, sr = librosa.load(filepath, sr=ANALYSIS_SR, mono=False)

    if y.ndim == 1:
        print("ERROR: Mono file", file=sys.stderr)
        return

    y_left, y_right = y[0], y[1]
    total_duration = len(y_left) / sr
    filename = os.path.basename(filepath)

    print(f"\n{'=' * 80}")
    print(f"  SPECTRUM DEBUG: {filename}")
    print(f"{'=' * 80}")
    print(f"Duration: {total_duration:.1f}s | Sample rate: {sr} Hz")
    print(f"Analyzing: {start_sec:.1f}s to {start_sec + duration_sec:.1f}s")
    print(f"Window: {window_sec}s | Freq range: {freq_min}-{freq_max} Hz")

    # Auto-detect carrier pairs from first window
    n_det = min(int(window_sec * sr), len(y_left))
    pairs = detect_carrier_pairs(y_left[:n_det], y_right[:n_det], sr, freq_min, freq_max)
    if pairs:
        print(f"\nAuto-detected {len(pairs)} carrier pair(s):")
        for i, p in enumerate(pairs):
            print(f"  [{i}] ~{p['center_hz']:.1f} Hz: L={p['left_hz']:.1f} R={p['right_hz']:.1f} "
                  f"beat={p['binaural_hz']:.2f} Hz ({p['avg_db']:.1f} dB)")

    t = start_sec
    end_time = min(start_sec + duration_sec, total_duration - window_sec)

    while t <= end_time:
        start_sample = int(t * sr)
        end_sample = int((t + window_sec) * sr)
        left_seg = y_left[start_sample:end_sample]
        right_seg = y_right[start_sample:end_sample]

        left_peaks = find_peaks_in_spectrum(left_seg, sr, freq_min, freq_max)
        right_peaks = find_peaks_in_spectrum(right_seg, sr, freq_min, freq_max)

        # Find binaural candidates
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

        time_str = f"{int(t // 60)}:{t % 60:05.2f}"
        print(f"\n{'-' * 80}")
        print(f"  WINDOW @ {time_str}")
        print(f"{'-' * 80}")

        if candidates:
            print(f"\n  BINAURAL CANDIDATES:")
            print(f"  {'L Freq':>8} | {'R Freq':>8} | {'Beat':>6} | {'L dB':>6} | {'R dB':>6}")
            print(f"  {'-' * 50}")
            for c in candidates[:8]:
                print(f"  {c['left_freq']:>8.2f} | {c['right_freq']:>8.2f} | "
                      f"{c['binaural']:>6.2f} | {c['left_db']:>6.1f} | {c['right_db']:>6.1f}")
        else:
            print("\n  No binaural candidates found in this window")

        print(f"\n  TOP PEAKS - Left:  {', '.join(f'{f:.1f}Hz ({p:.0f}dB)' for f, p in left_peaks[:6])}")
        print(f"  TOP PEAKS - Right: {', '.join(f'{f:.1f}Hz ({p:.0f}dB)' for f, p in right_peaks[:6])}")

        t += window_sec


# === Verify Mode ===

def verify_against_config(filepath, config_path, window_sec=10, step_sec=5,
                          tolerance_hz=0.3, detect_pulse=True):
    """
    Verify generated audio against a generator JSON config.

    Compares measured binaural beats and isochronic pulse rates to expected
    values from the config at each time window. Reports PASS/FAIL per
    window per carrier for both binaural and pulse.

    Args:
        filepath: Path to generated audio file
        config_path: Path to JSON config used to generate the audio
        window_sec: Analysis window in seconds
        step_sec: Step between windows
        tolerance_hz: Maximum acceptable error in Hz
        detect_pulse: Whether to verify isochronic pulse rates

    Returns:
        Dict with pass/fail counts and details
    """
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)

    duration = config['duration_sec']
    layers = config.get('layers', [])
    global_keyframes = config.get('keyframes')
    global_binaural = config.get('binaural_hz', 0)

    # Build expected binaural per layer
    def resolve_expected(layer_cfg, field):
        """Get expected value for a field from a layer (static or from keyframes)."""
        # Check direct field on layer
        if field in layer_cfg:
            val = layer_cfg[field]
            if isinstance(val, list):
                return val  # keyframes [{time_sec, value}]
            return float(val)
        # Check unified keyframes
        if 'keyframes' in layer_cfg:
            kf_list = layer_cfg['keyframes']
            # Check if any keyframe has this field
            has_field = any(field in kf for kf in kf_list)
            if has_field:
                return kf_list  # will be handled by expected_at_time
        # For binaural_hz, fall back to global
        if field == 'binaural_hz':
            if global_keyframes:
                return global_keyframes
            return float(global_binaural)
        return None

    def expected_at_time(expected, t, field=None):
        """Interpolate expected value at time t."""
        if expected is None:
            return None
        if isinstance(expected, (int, float)):
            return expected
        # Keyframe list — unified format or per-field
        kf = sorted(expected, key=lambda k: k.get('time_sec', k.get('t', 0)))
        times = [k.get('time_sec', k.get('t', 0)) for k in kf]

        # Check if all keyframes have the field directly
        all_have_field = field and all(field in k for k in kf)
        if all_have_field:
            values = [k[field] for k in kf]
        elif 'value' in kf[0] and all('value' in k for k in kf):
            values = [k['value'] for k in kf]
        elif field:
            # Unified keyframes — extract field, forward-fill missing
            if not any(field in k for k in kf):
                return None
            values = []
            last_val = None
            for k in kf:
                if field in k:
                    last_val = k[field]
                if last_val is not None:
                    values.append(last_val)
                else:
                    values.append(0)
        else:
            return None

        if len(times) != len(values):
            return None
        return float(np.interp(t, times, values))

    # Get center frequencies and expected values per layer
    layer_data = []
    has_pulse_config = False
    for layer_cfg in layers:
        center = layer_cfg.get('center_hz')
        if center is None and 'keyframes' in layer_cfg:
            for kf in layer_cfg['keyframes']:
                if 'center_hz' in kf:
                    center = kf['center_hz']
                    break
        if isinstance(center, list):
            center = center[0]['value']
        center = float(center)

        exp_center = resolve_expected(layer_cfg, 'center_hz')
        exp_bin = resolve_expected(layer_cfg, 'binaural_hz')
        exp_pul = resolve_expected(layer_cfg, 'pulse_hz')
        if exp_pul is not None:
            has_pulse_config = True
        layer_data.append((center, exp_center, exp_bin, exp_pul))

    # Sort by initial center frequency
    layer_data.sort(key=lambda x: x[0])
    centers = [d[0] for d in layer_data]
    expected_centers = [d[1] for d in layer_data]
    expected_binaurals = [d[2] for d in layer_data]
    expected_pulses = [d[3] for d in layer_data]

    # Only verify pulse if config has pulse data and detection is enabled
    verify_pulse = detect_pulse and has_pulse_config

    # Load audio and analyze
    y, sr = librosa.load(filepath, sr=ANALYSIS_SR, mono=False)
    if y.ndim == 1:
        print("ERROR: Mono file", file=sys.stderr)
        return None

    y_left, y_right = y[0], y[1]
    actual_duration = len(y_left) / sr
    filename = os.path.basename(filepath)

    print(f"\n{'=' * 75}")
    print(f"  VERIFY: {filename}")
    print(f"  CONFIG: {os.path.basename(config_path)}")
    print(f"{'=' * 75}")
    print(f"Duration: {actual_duration:.1f}s (expected {duration}s)")
    print(f"Carriers: {', '.join(f'{c:.1f} Hz' for c in centers)}")
    verify_str = "binaural + pulse" if verify_pulse else "binaural only"
    print(f"Verifying: {verify_str} | Tolerance: +/- {tolerance_hz:.2f} Hz")
    print()

    # Column header
    header_parts = [f"{'Time':>8}", f"{'Status':>6}"]
    for i, center in enumerate(centers):
        col = f"C{i}({center:.0f}Hz) bin"
        if verify_pulse:
            col += "+pul"
        header_parts.append(col)
    print(' | '.join(header_parts))
    col_width = 40 if verify_pulse else 32
    print("-" * (20 + len(centers) * col_width))

    pass_count = 0
    fail_count = 0
    results = []

    t = 0
    while t + window_sec <= actual_duration:
        start_sample = int(t * sr)
        end_sample = int((t + window_sec) * sr)
        left_seg = y_left[start_sample:end_sample]
        right_seg = y_right[start_sample:end_sample]

        t_mid = t + window_sec / 2

        # Build per-window carrier search ranges from interpolated centers
        window_centers = []
        for i in range(len(centers)):
            c = expected_at_time(expected_centers[i], t_mid, 'center_hz')
            if c is None:
                c = centers[i]
            window_centers.append(c)
        carrier_pairs = build_carrier_ranges_from_centers(window_centers)

        window_results = analyze_window(left_seg, right_seg, sr, carrier_pairs,
                                        detect_pulse=verify_pulse)

        # Compare to expected
        window_pass = True
        time_str = f"{int(t // 60)}:{t % 60:05.2f}"
        detail_parts = [f"{time_str:>8}"]
        carrier_details = []

        for i, cr in enumerate(window_results):
            parts = []

            # Binaural check
            exp_bin = expected_at_time(expected_binaurals[i], t_mid, 'binaural_hz')
            measured_bin = cr['binaural_hz']
            if measured_bin is not None and exp_bin is not None:
                error = abs(measured_bin - exp_bin)
                ok = error <= tolerance_hz
                if not ok:
                    window_pass = False
                status = "ok" if ok else "FAIL"
                parts.append(f"b:{exp_bin:>5.2f}/{measured_bin:>5.2f}({status})")
            elif exp_bin is not None:
                window_pass = False
                parts.append(f"b:{exp_bin:>5.2f}/{'N/A':>5}(FAIL)")
            else:
                parts.append(f"b:{'N/A':>5}/{'N/A':>5}")

            # Pulse check
            if verify_pulse:
                exp_pul = expected_at_time(expected_pulses[i], t_mid, 'pulse_hz')
                measured_pul = cr.get('pulse_hz')
                if measured_pul is not None and exp_pul is not None:
                    error = abs(measured_pul - exp_pul)
                    ok = error <= tolerance_hz
                    if not ok:
                        window_pass = False
                    status = "ok" if ok else "FAIL"
                    parts.append(f"p:{exp_pul:>5.2f}/{measured_pul:>5.2f}({status})")
                elif exp_pul is not None:
                    window_pass = False
                    parts.append(f"p:{exp_pul:>5.2f}/{'N/A':>5}(FAIL)")
                else:
                    parts.append(f"p:{'N/A':>5}/{'N/A':>5}")

            carrier_details.append(' '.join(parts))

        if window_pass:
            pass_count += 1
            detail_parts.append(f"{'PASS':>6}")
        else:
            fail_count += 1
            detail_parts.append(f"{'FAIL':>6}")

        detail_parts.extend(carrier_details)
        print(' | '.join(detail_parts))

        results.append({
            'time': t,
            'pass': window_pass,
            'carriers': window_results,
        })
        t += step_sec

    # Summary
    total = pass_count + fail_count
    col_width = 40 if verify_pulse else 32
    print("-" * (20 + len(centers) * col_width))
    pct = pass_count / total * 100 if total > 0 else 0
    status = "PASS" if fail_count == 0 else "FAIL"
    print(f"\nResult: {status} ({pass_count}/{total} windows passed, {pct:.0f}%)")
    print(f"Tolerance: {tolerance_hz:.2f} Hz")

    return {'pass': pass_count, 'fail': fail_count, 'total': total, 'results': results}


# === Spectrogram ===

def generate_spectrogram(filepath, carrier_trajectories=None, carrier_pairs=None,
                         freq_min=30, freq_max=1200, output_path=None,
                         lr_split=False):
    """Generate a spectrogram PNG with optional carrier trajectory overlay."""
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib required for spectrogram: pip install matplotlib",
              file=sys.stderr)
        return

    render_max = min(freq_max, 1200)
    target_sr = max(int(render_max * 2.5), 4000)
    print(f"Loading audio for spectrogram (target sr={target_sr} Hz, "
          f"range {freq_min}-{render_max} Hz)...")

    # Always load stereo — needed for both overlay and split modes
    y, _ = librosa.load(filepath, sr=target_sr, mono=False)
    if y.ndim == 1:
        y_left_ds, y_right_ds = y, y.copy()
    else:
        y_left_ds, y_right_ds = y[0], y[1]
    del y
    gc.collect()
    duration = len(y_left_ds) / target_sr

    filename = os.path.basename(filepath)

    if duration < 600:
        n_fft, hop_length = 4096, 512
    elif duration < 1800:
        n_fft, hop_length = 4096, 1024
    else:
        n_fft, hop_length = 2048, 2048

    vmin_db, vmax_db = -80, 0

    if lr_split:
        fig, (ax_l, ax_r) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
        panels = [('Left', y_left_ds, ax_l), ('Right', y_right_ds, ax_r)]
    else:
        fig, ax = plt.subplots(1, 1, figsize=(16, 6))
        panels = [('Overlay', (y_left_ds, y_right_ds), ax)]

    for label, sig, ax_panel in panels:
        freqs = librosa.fft_frequencies(sr=target_sr, n_fft=n_fft)
        freq_mask = (freqs >= freq_min) & (freqs <= render_max)

        if label == 'Overlay':
            # Compute STFT for each channel separately
            y_l, y_r = sig
            S_l = librosa.stft(y_l, n_fft=n_fft, hop_length=hop_length)
            S_db_l = librosa.amplitude_to_db(np.abs(S_l), ref=np.max)
            del S_l; gc.collect()

            S_r = librosa.stft(y_r, n_fft=n_fft, hop_length=hop_length)
            S_db_r = librosa.amplitude_to_db(np.abs(S_r), ref=np.max)
            del S_r; gc.collect()

            times = librosa.frames_to_time(np.arange(S_db_l.shape[1]),
                                            sr=target_sr, hop_length=hop_length)

            # Normalize dB to [0, 1] and apply per-channel colormaps → RGBA
            l_norm = np.clip((S_db_l[freq_mask, :] - vmin_db) / (vmax_db - vmin_db), 0, 1)
            r_norm = np.clip((S_db_r[freq_mask, :] - vmin_db) / (vmax_db - vmin_db), 0, 1)
            del S_db_l, S_db_r; gc.collect()

            rgba_l = _CMAP_LEFT(l_norm)   # [freq_bins, time_bins, 4]
            rgba_r = _CMAP_RIGHT(r_norm)
            del l_norm, r_norm; gc.collect()

            # Screen blend: 1 - (1-a)(1-b) — prevents oversaturation where both are loud
            rgba_blend = np.empty_like(rgba_l)
            rgba_blend[..., :3] = 1.0 - (1.0 - rgba_l[..., :3]) * (1.0 - rgba_r[..., :3])
            rgba_blend[..., 3] = 1.0
            del rgba_l, rgba_r; gc.collect()

            extent = [times[0], times[-1], freqs[freq_mask][0], freqs[freq_mask][-1]]
            ax_panel.imshow(rgba_blend, aspect='auto', origin='lower', extent=extent,
                            interpolation='bilinear')
            del rgba_blend; gc.collect()

            ax_panel.set_ylabel('L (teal) / R (red)\nFrequency (Hz)')
            ax_panel.set_ylim(freq_min, render_max)

            # Two colorbars via ScalarMappable
            norm = Normalize(vmin=vmin_db, vmax=vmax_db)
            sm_l = plt.cm.ScalarMappable(cmap=_CMAP_LEFT, norm=norm)
            sm_r = plt.cm.ScalarMappable(cmap=_CMAP_RIGHT, norm=norm)
            cbar_l = fig.colorbar(sm_l, ax=ax_panel, pad=0.01, fraction=0.025)
            cbar_l.set_label('L dB')
            cbar_r = fig.colorbar(sm_r, ax=ax_panel, pad=0.055, fraction=0.025)
            cbar_r.set_label('R dB')

        else:
            # L/R split panels — per-channel colormap, pcolormesh
            S = librosa.stft(sig, n_fft=n_fft, hop_length=hop_length)
            S_db = librosa.amplitude_to_db(np.abs(S), ref=np.max)
            del S; gc.collect()

            times = librosa.frames_to_time(np.arange(S_db.shape[1]),
                                            sr=target_sr, hop_length=hop_length)

            panel_cmap = _CMAP_LEFT if label == 'Left' else _CMAP_RIGHT
            img = ax_panel.pcolormesh(times, freqs[freq_mask], S_db[freq_mask, :],
                                       shading='gouraud', cmap=panel_cmap,
                                       vmin=vmin_db, vmax=vmax_db)
            ax_panel.set_ylabel(f'{label}\nFrequency (Hz)')
            ax_panel.set_ylim(freq_min, render_max)

            cbar = fig.colorbar(img, ax=ax_panel, pad=0.01)
            cbar.set_label('dB')

        # Carrier trajectory overlay (shared for both modes)
        if carrier_trajectories:
            for idx, traj in enumerate(carrier_trajectories):
                t_arr = np.array(traj['times'])
                l_arr = np.array(traj['left_hz'], dtype=float)
                r_arr = np.array(traj['right_hz'], dtype=float)

                label_base = None
                if carrier_pairs and idx < len(carrier_pairs):
                    cp = carrier_pairs[idx]
                    det_type = cp.get('detection_type', 'binaural')
                    label_base = f"C{idx}: ~{cp['center_hz']:.0f} Hz ({det_type})"

                is_first_panel = (label == panels[0][0]) or not lr_split

                valid_l = np.isfinite(l_arr)
                if np.any(valid_l):
                    ax_panel.scatter(t_arr[valid_l], l_arr[valid_l],
                                     color=_COLOR_L, marker='<', s=14, alpha=0.9,
                                     zorder=5, linewidths=0.5, edgecolors='#003322',
                                     label=(f"{label_base} L" if label_base and is_first_panel else None))

                valid_r = np.isfinite(r_arr)
                if np.any(valid_r):
                    ax_panel.scatter(t_arr[valid_r], r_arr[valid_r],
                                     color=_COLOR_R, marker='>', s=14, alpha=0.9,
                                     zorder=5, linewidths=0.5, edgecolors='#330000',
                                     label=(f"{label_base} R" if label_base and is_first_panel else None))

    last_ax = panels[-1][2]
    last_ax.set_xlabel('Time')

    def format_time(x, _):
        return f"{int(x // 60)}:{int(x % 60):02d}"
    last_ax.xaxis.set_major_formatter(FuncFormatter(format_time))

    if carrier_trajectories:
        first_ax = panels[0][2]
        handles, labels = first_ax.get_legend_handles_labels()
        if handles:
            first_ax.legend(loc='upper right', fontsize=7, framealpha=0.8,
                            markerscale=1.5)

    fig.suptitle(f'{filename}', fontsize=13, y=0.98)
    plt.tight_layout()

    if output_path is None:
        base, _ = os.path.splitext(filepath)
        output_path = base + '_spectrogram.png'

    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Spectrogram saved: {output_path}")


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description='Analyze binaural beats and isochronic pulses in audio files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect carriers and analyze (binaural + isochronic)
  python binaural_analyzer.py audio.wav

  # Binaural only (skip isochronic detection)
  python binaural_analyzer.py audio.wav --no-isochronic

  # Specify known carrier centers
  python binaural_analyzer.py audio.wav --expected-carriers 60,90,135,202.5

  # Generate spectrogram with carrier overlay
  python binaural_analyzer.py audio.wav --spectrogram

  # L/R split spectrogram with custom output path
  python binaural_analyzer.py audio.wav --spectrogram-lr -o output.png

  # Verify generated audio against config (binaural + pulse)
  python binaural_analyzer.py generated.wav --verify config.json

  # Spectrum debug mode
  python binaural_analyzer.py audio.wav --spectrum --start 0 --duration 60

  # CSV output
  python binaural_analyzer.py audio.wav --csv --window 10 --step 5
"""
    )
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--window', type=float, default=10,
                        help='FFT window in seconds (default: 10). Larger=finer Hz resolution, worse time resolution. '
                             'Use 20+ for static carriers, 5 for sweeping/Shepard tones')
    parser.add_argument('--step', type=float, default=5,
                        help='Step between windows in seconds (default: 5). Smaller=smoother tracking, more output')
    parser.add_argument('--expected-carriers', type=str, default=None,
                        help='Comma-separated center frequencies (e.g., 60,135,202.5)')
    parser.add_argument('--freq-min', type=float, default=30,
                        help='Min frequency for detection (default: 30)')
    parser.add_argument('--freq-max', type=float, default=None,
                        help='Max frequency for detection (default: auto-detect)')
    parser.add_argument('--no-graph', action='store_true', help='Suppress graph')
    parser.add_argument('--no-isochronic', action='store_true',
                        help='Skip isochronic pulse detection (binaural only, faster)')
    parser.add_argument('--csv', action='store_true', help='CSV output')

    # Spectrum mode
    parser.add_argument('--spectrum', action='store_true',
                        help='Spectrum debug mode')
    parser.add_argument('--start', type=float, default=0,
                        help='Start time for spectrum mode (seconds)')
    parser.add_argument('--duration', type=float, default=30,
                        help='Duration for spectrum mode (seconds)')

    # Verify mode
    parser.add_argument('--verify', type=str, default=None, metavar='CONFIG',
                        help='Verify against generator JSON config')
    parser.add_argument('--tolerance', type=float, default=0.3,
                        help='Verification tolerance in Hz (default: 0.3)')

    # Spectrogram mode
    parser.add_argument('--spectrogram', action='store_true',
                        help='Generate spectrogram PNG with carrier overlay')
    parser.add_argument('--spectrogram-lr', action='store_true',
                        help='L/R split spectrogram (implies --spectrogram)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output path for spectrogram PNG')

    args = parser.parse_args()

    detect_pulse = not args.no_isochronic

    if args.spectrogram_lr:
        args.spectrogram = True

    # Parse expected carriers
    expected_carriers = None
    if args.expected_carriers:
        expected_carriers = [float(x.strip()) for x in args.expected_carriers.split(',')]

    # Default freq_max for spectrum mode (which doesn't auto-detect)
    freq_max_spectrum = args.freq_max if args.freq_max is not None else 600

    if args.verify:
        verify_against_config(
            args.audio_file,
            args.verify,
            window_sec=args.window,
            step_sec=args.step,
            tolerance_hz=args.tolerance,
            detect_pulse=detect_pulse,
        )
    elif args.spectrum:
        analyze_spectrum(
            args.audio_file,
            start_sec=args.start,
            duration_sec=args.duration,
            window_sec=args.window,
            freq_min=args.freq_min,
            freq_max=freq_max_spectrum,
        )
    else:
        analyze_binaural(
            args.audio_file,
            window_sec=args.window,
            step_sec=args.step,
            expected_carriers=expected_carriers,
            freq_min=args.freq_min,
            freq_max=args.freq_max,
            show_graph=not args.no_graph,
            csv_output=args.csv,
            detect_pulse=detect_pulse,
            spectrogram=args.spectrogram,
            spectrogram_lr=args.spectrogram_lr,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
