#!/usr/bin/env python3
"""
Binaural Beat & Isochronic Pulse Analyzer

Point at any stereo audio file and get a spectrogram PNG with annotated
frequency tracks plus an ASCII summary of what's in there.

Pipeline:
    1. STFT per channel → per-frame spectral whitening
    2. Sub-bin parabolic peak detection
    3. Greedy track linking + co-linear fragment merging
    4. Binaural pairing (Hungarian assignment on L×R beat cost)
    5. Isochronic measurement per track (bandpass → Hilbert → envelope FFT)
    6. Screen-blend L/R spectrogram + annotated track overlay

Usage:
    python binaural_analyzer.py <audio_file> [-o output.png]

Options:
    --freq-min HZ           Min frequency to display (default: 30)
    --freq-max HZ           Max frequency to display (default: auto-detect)
    --output / -o PATH      Output PNG path (default: <input>_tracks.png)
    --binaural-range MIN,MAX  Valid beat Hz range for pairing (default: 0.3,20)
    --iso-bandwidth HZ      Bandpass width for isochronic detection (default: 15)
    --iso-min-conf FLOAT    Min confidence to report isochronic rate (default: 1.0)
    --pair-min-overlap INT  Min overlapping frames to form a pair (default: 4)
"""

import argparse
import json
import numpy as np
import librosa
from scipy import signal as scipy_signal
from scipy.fft import fft, fftfreq
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.optimize import linear_sum_assignment
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
    _CMAP_LEFT = LinearSegmentedColormap.from_list(
        'teal_heat', ['#000011', '#002233', '#005577', '#009999', '#44eedd'], N=256)
    _CMAP_RIGHT = LinearSegmentedColormap.from_list(
        'red_heat', ['#110000', '#330000', '#880000', '#cc3300', '#ff8855'], N=256)
    _COLOR_L = '#00ccbb'     # teal  — solo L tracks
    _COLOR_R = '#ff4422'     # red   — solo R tracks
    _COLOR_PAIR = '#ffdd44'  # gold  — binaural-paired merged tracks
except ImportError:
    HAS_MATPLOTLIB = False


# === Utilities ===

def _auto_detect_freq_range(y_left, y_right, sr, sample_duration=30, floor_db=40):
    """Find the useful frequency ceiling from a short sample."""
    n_samples = min(int(sample_duration * sr), len(y_left))
    mono = (y_left[:n_samples] + y_right[:n_samples]) / 2
    n = len(mono)
    yf = np.abs(fft(mono))[:n // 2]
    xf = fftfreq(n, 1 / sr)[:n // 2]
    mask = (xf >= 30) & (xf <= 2000)
    yf_masked, xf_masked = yf[mask], xf[mask]
    if len(yf_masked) == 0:
        return 1200
    yf_db = 20 * np.log10(yf_masked + 1e-10)
    above = xf_masked[yf_db > np.max(yf_db) - floor_db]
    if len(above) == 0:
        return 1200
    highest = float(np.max(above))
    return min(max(600, int(np.ceil((highest * 1.2) / 50) * 50)), 2000)


# === Isochronic Detection ===

def detect_isochronic_rate(y, sr, carrier_freq, bandwidth=15,
                            pulse_range=(0.5, 15), min_confidence=0.3):
    """Detect isochronic pulse rate at a carrier via bandpass → Hilbert → envelope FFT.

    Returns (pulse_hz, confidence) or (None, 0.0) if nothing found.
    Confidence = peak / median noise floor of the envelope spectrum.
    """
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

    envelope = np.abs(scipy_signal.hilbert(filtered))
    envelope = (envelope - np.mean(envelope)) * np.hanning(len(envelope))

    n = len(envelope)
    env_fft = np.abs(fft(envelope))[:n // 2]
    env_freqs = fftfreq(n, 1 / sr)[:n // 2]

    mask = (env_freqs >= pulse_range[0]) & (env_freqs <= pulse_range[1])
    if not np.any(mask):
        return (None, 0.0)

    env_fft_m = env_fft[mask]
    env_freqs_m = env_freqs[mask]
    peak_idx = np.argmax(env_fft_m)
    noise_floor = np.median(env_fft_m)
    if noise_floor <= 0:
        noise_floor = 1e-10
    confidence = env_fft_m[peak_idx] / noise_floor
    if confidence < min_confidence:
        return (None, 0.0)

    # Parabolic sub-bin interpolation
    freq = env_freqs_m[peak_idx]
    if 0 < peak_idx < len(env_fft_m) - 1:
        a, b, c = env_fft_m[peak_idx - 1], env_fft_m[peak_idx], env_fft_m[peak_idx + 1]
        denom = a - 2 * b + c
        if denom != 0 and b > 0:
            freq += 0.5 * (a - c) / denom * (env_freqs_m[1] - env_freqs_m[0])

    return (freq, confidence)


# === Phase 1: Ridge Track Extraction ===

def _whiten_spectrum(S_mag, kernel_bins=41):
    """Per-frame frequency-domain median whitening.

    Subtracts the broadband spectral envelope (median filter along freq axis)
    from each frame. Persistent narrow-band tones survive; broadband
    voice/music content is suppressed.

    Returns (whitened, S_db) — S_db is cached for reuse in rendering.
    """
    S_db = librosa.amplitude_to_db(S_mag, ref=np.max)
    baseline = median_filter(S_db, size=(kernel_bins, 1))
    return np.maximum(S_db - baseline, 0.0), S_db


def _peaks_from_whitened_frame(spec, f_arr, prom_thresh=8.0, max_width_bins=5):
    """Detect peaks in one pre-sliced whitened spectrum frame.

    Expects spec/f_arr already masked to the analysis freq range.
    Uses vectorized NumPy parabolic sub-bin interpolation.
    """
    if len(spec) < 5:
        return []

    peak_idx, _ = scipy_signal.find_peaks(
        spec, prominence=prom_thresh, width=(1, max_width_bins)
    )
    if len(peak_idx) == 0:
        return []

    bin_hz = float(f_arr[1] - f_arr[0]) if len(f_arr) > 1 else 1.0

    k = peak_idx
    valid = (k > 0) & (k < len(spec) - 1)
    a = np.where(valid, spec[np.clip(k - 1, 0, len(spec) - 1)], spec[k])
    b = spec[k]
    c = np.where(valid, spec[np.clip(k + 1, 0, len(spec) - 1)], spec[k])
    denom = a - 2 * b + c
    p = np.where((denom != 0) & valid, 0.5 * (a - c) / denom, 0.0)
    p = np.clip(p, -0.5, 0.5)
    f_interp = f_arr[k] + p * bin_hz
    powers = spec[k]

    order = np.argsort(-powers)[:8]
    return list(zip(f_interp[order].tolist(), powers[order].tolist()))


def _link_peaks_to_tracks(peaks_by_frame, frame_times,
                           df_max_abs=3.0, df_max_rel=0.005,
                           gap_max=3, min_track_frames=5):
    """Greedy peak-to-track linker with gap tolerance.

    Δf_max(f) = max(df_max_abs, df_max_rel * f)
    Tracks that miss > gap_max consecutive frames are retired.
    """
    def df_max(f):
        return max(df_max_abs, df_max_rel * abs(f))

    active, finished, _next_id = [], [], [0]

    for t, peaks in zip(frame_times, peaks_by_frame):
        cands = []
        for tr in active:
            for pi, (f, p) in enumerate(peaks):
                df = abs(f - tr['last_f'])
                if df <= df_max(tr['last_f']):
                    cands.append((tr['id'], pi, df + max(0.0, 30.0 - p) * 0.05))

        cands.sort(key=lambda x: x[2])
        used_tr, used_pk, assignment = set(), set(), {}
        for tid, pi, _ in cands:
            if tid not in used_tr and pi not in used_pk:
                assignment[tid] = pi
                used_tr.add(tid)
                used_pk.add(pi)

        to_retire = []
        for tr in active:
            if tr['id'] in assignment:
                f, p = peaks[assignment[tr['id']]]
                tr['times'].append(float(t))
                tr['freqs'].append(f)
                tr['powers'].append(p)
                tr['last_f'] = f
                tr['gap'] = 0
            else:
                tr['gap'] += 1
                if tr['gap'] > gap_max:
                    to_retire.append(tr)

        for tr in to_retire:
            finished.append(tr)
            active.remove(tr)

        for pi, (f, p) in enumerate(peaks):
            if pi not in used_pk:
                tr = {'id': _next_id[0], 'last_f': f, 'gap': 0,
                      'times': [float(t)], 'freqs': [f], 'powers': [p]}
                _next_id[0] += 1
                active.append(tr)

    finished.extend(active)
    return [tr for tr in finished if len(tr['times']) >= min_track_frames]


def _merge_colinear_tracks(tracks, merge_df_hz=5.0, merge_gap_sec=30.0):
    """Merge track fragments that are likely the same carrier.

    Merges A→B when B starts after A ends, gap ≤ merge_gap_sec, and the
    tail of A matches the head of B within merge_df_hz. Runs iteratively
    until no further merges are possible.
    """
    if not tracks:
        return tracks

    changed = True
    while changed:
        changed = False
        tracks = sorted(tracks, key=lambda t: t['times'][0])
        used, merged = set(), []

        for i, ta in enumerate(tracks):
            if i in used:
                continue
            cur = {'id': ta['id'], 'last_f': ta['last_f'], 'gap': 0,
                   'times': list(ta['times']), 'freqs': list(ta['freqs']),
                   'powers': list(ta['powers'])}
            used.add(i)

            for j, tb in enumerate(tracks):
                if j in used:
                    continue
                t_end, t_start = cur['times'][-1], tb['times'][0]
                if t_start < t_end:
                    continue
                if t_start - t_end > merge_gap_sec:
                    break  # tracks are time-sorted; all further candidates also fail
                f_tail = float(np.median(cur['freqs'][-max(1, len(cur['freqs']) // 5):]))
                f_head = float(np.median(tb['freqs'][:max(1, len(tb['freqs']) // 5)]))
                if abs(f_tail - f_head) > merge_df_hz:
                    continue
                cur['times'].extend(tb['times'])
                cur['freqs'].extend(tb['freqs'])
                cur['powers'].extend(tb['powers'])
                cur['last_f'] = tb['last_f']
                used.add(j)
                changed = True

            merged.append(cur)

        tracks = merged

    return tracks


# === Phase 2: Binaural Pairing + Isochronic ===

def _pair_binaural_tracks(tracks_L, tracks_R, binaural_range=(0.3, 20.0),
                          min_overlap=4):
    """Hungarian-assignment pairing of L and R tracks by beat-frequency consistency.

    Cost(L, R) = variance(|fL-fR|) * 10 + |median_beat - 4.0|
    Pairs outside binaural_range or with < min_overlap common time points get inf cost.

    Returns (pairs, solo_L, solo_R).
    """
    if not tracks_L or not tracks_R:
        return [], list(tracks_L), list(tracks_R)

    n_L, n_R = len(tracks_L), len(tracks_R)
    cost_matrix = np.full((n_L, n_R), np.inf)
    _cache = {}

    for i, tL in enumerate(tracks_L):
        t_L = np.array(tL['times'])
        for j, tR in enumerate(tracks_R):
            t_R = np.array(tR['times'])
            t_ov_s = max(t_L[0], t_R[0])
            t_ov_e = min(t_L[-1], t_R[-1])
            if t_ov_e <= t_ov_s:
                continue
            t_common = np.union1d(t_L, t_R)
            t_common = t_common[(t_common >= t_ov_s) & (t_common <= t_ov_e)]
            if len(t_common) < min_overlap:
                continue
            beat = np.abs(np.interp(t_common, t_L, tL['freqs']) -
                          np.interp(t_common, t_R, tR['freqs']))
            d = float(np.median(beat))
            if d < binaural_range[0] or d > binaural_range[1]:
                continue
            cost_matrix[i, j] = float(np.var(beat)) * 10.0 + abs(d - 4.0)
            _cache[(i, j)] = (t_ov_s, t_ov_e, beat)

    row_ind, col_ind = linear_sum_assignment(
        np.where(np.isinf(cost_matrix), 1e9, cost_matrix))

    pairs, paired_L, paired_R = [], set(), set()
    for i, j in zip(row_ind, col_ind):
        if np.isinf(cost_matrix[i, j]):
            continue
        t_ov_s, t_ov_e, beat = _cache[(i, j)]
        pairs.append({
            'track_L': tracks_L[i], 'track_R': tracks_R[j],
            't_start': float(t_ov_s), 't_end': float(t_ov_e),
            'beat_hz_series': beat.tolist(),
            'beat_hz_median': float(np.median(beat)),
            'beat_hz_std': float(np.std(beat)),
        })
        paired_L.add(i)
        paired_R.add(j)

    return (pairs,
            [tracks_L[i] for i in range(n_L) if i not in paired_L],
            [tracks_R[j] for j in range(n_R) if j not in paired_R])


def _measure_isochronic_for_track(track, y, sr, bandwidth=15):
    """Detect isochronic rate for one track by slicing audio to its time range.

    Caps the slice at 60 seconds — sufficient for envelope FFT resolution
    in the 0.5–15 Hz range (60s @ sr gives ~0.017 Hz resolution).
    """
    s0 = int(track['times'][0] * sr)
    s1 = min(int(track['times'][-1] * sr), s0 + 60 * sr, len(y))
    if s1 - s0 < sr:  # need at least 1 second
        return (None, 0.0)
    return detect_isochronic_rate(
        y[s0:s1], sr, float(np.median(track['freqs'])), bandwidth=bandwidth)


# === JSON Export ===

def _tracks_to_json(pairs, solo_L, solo_R, duration, max_keyframes=20,
                    iso_min_conf_export=2.0):
    """Convert analyzed tracks to binaural generator JSON format.

    Binaural pairs become layers with center_hz + binaural_hz.
    Solo tracks become layers with center_hz only (+ pulse_hz if isochronic
    is detected with sufficient confidence).
    Sweeping carriers are represented as unified keyframe lists; stable
    carriers collapse to scalars.
    """
    def _simplify(times, values, field, max_kf=max_keyframes):
        """Return scalar if stable (std < 0.5 Hz), else downsampled keyframes."""
        arr = np.array(values, dtype=float)
        if len(arr) == 0:
            return None
        if float(np.std(arr)) < 0.5:
            return round(float(np.median(arr)), 2)
        idx = np.linspace(0, len(arr) - 1, min(max_kf, len(arr)), dtype=int)
        return [{'time_sec': round(float(times[i]), 1), field: round(float(arr[i]), 2)}
                for i in idx]

    layers = []

    for pair in pairs:
        tL, tR = pair['track_L'], pair['track_R']
        t_common = np.union1d(np.array(tL['times']), np.array(tR['times']))
        t_common = t_common[(t_common >= pair['t_start']) & (t_common <= pair['t_end'])]

        centers = (np.interp(t_common, tL['times'], tL['freqs']) +
                   np.interp(t_common, tR['times'], tR['freqs'])) / 2
        beats = np.abs(np.interp(t_common, tL['times'], tL['freqs']) -
                       np.interp(t_common, tR['times'], tR['freqs']))

        c_val = _simplify(t_common, centers, 'center_hz')
        b_val = _simplify(t_common, beats, 'binaural_hz')

        layer = {'amplitude_db': 0}

        if isinstance(c_val, list) or isinstance(b_val, list):
            # Unified keyframe format — merge both fields by time
            kf_map = {}
            for kf in (c_val if isinstance(c_val, list) else []):
                t = kf['time_sec']
                kf_map[t] = {'time_sec': t, 'center_hz': kf['center_hz']}
            for kf in (b_val if isinstance(b_val, list) else []):
                t = kf['time_sec']
                kf_map.setdefault(t, {'time_sec': t})['binaural_hz'] = kf['binaural_hz']
            # Fill in scalar values where the other field is static
            if not isinstance(c_val, list):
                for kf in kf_map.values():
                    kf.setdefault('center_hz', c_val)
            if not isinstance(b_val, list):
                for kf in kf_map.values():
                    kf.setdefault('binaural_hz', b_val)
            layer['keyframes'] = sorted(kf_map.values(), key=lambda x: x['time_sec'])
        else:
            layer['center_hz'] = c_val
            layer['binaural_hz'] = b_val

        iso_hz = pair.get('iso_hz')
        if iso_hz is not None and pair.get('iso_conf', 0) >= iso_min_conf_export:
            layer['pulse_hz'] = round(iso_hz, 2)

        layers.append(layer)

    for tr in solo_L + solo_R:
        c_val = _simplify(tr['times'], tr['freqs'], 'center_hz')
        layer = {'amplitude_db': 0}
        if isinstance(c_val, list):
            layer['keyframes'] = c_val
        else:
            layer['center_hz'] = c_val

        iso_hz = tr.get('iso_hz')
        if iso_hz is not None and tr.get('iso_conf', 0) >= iso_min_conf_export:
            layer['pulse_hz'] = round(iso_hz, 2)

        layers.append(layer)

    return {'duration_sec': round(duration, 1), 'layers': layers}


# === Main Analysis ===

def analyze(filepath, freq_min=30, freq_max=None, output_path=None,
            prom_thresh=8.0, gap_max=8, min_median_power=10.0,
            binaural_range=(0.3, 20.0), iso_bandwidth=15,
            iso_min_conf=1.0, pair_min_overlap=4,
            export_json=False):
    """Analyze a stereo audio file: extract tracks, pair binaurals, measure isochronic.

    Outputs a spectrogram PNG and prints an ASCII summary to stdout.
    If export_json=True, also writes a generator-compatible JSON file.
    Returns (tracks_L, tracks_R, pairs).
    """
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib required — pip install matplotlib", file=sys.stderr)
        return None, None, None

    if freq_max is None:
        y_tmp, _ = librosa.load(filepath, sr=8000, mono=False, duration=30)
        y_tmp_l = y_tmp[0] if y_tmp.ndim > 1 else y_tmp
        y_tmp_r = y_tmp[1] if y_tmp.ndim > 1 else y_tmp
        freq_max = _auto_detect_freq_range(y_tmp_l, y_tmp_r, 8000)
        del y_tmp, y_tmp_l, y_tmp_r
        gc.collect()
        print(f"Auto-detected freq range: {freq_min}-{freq_max} Hz")

    render_max = min(freq_max, 1200)
    target_sr = max(int(render_max * 2.5), 4000)
    filename = os.path.basename(filepath)

    print(f"Loading audio (sr={target_sr} Hz, {freq_min}-{render_max} Hz)...")
    y, _ = librosa.load(filepath, sr=target_sr, mono=False)
    y_L, y_R = (y[0], y[1]) if y.ndim > 1 else (y, y.copy())
    del y
    gc.collect()

    duration = len(y_L) / target_sr
    if duration < 600:
        n_fft, hop_length = 4096, 512
    elif duration < 1800:
        n_fft, hop_length = 4096, 1024
    else:
        n_fft, hop_length = 2048, 2048

    print(f"Computing STFT (n_fft={n_fft}, hop={hop_length}, "
          f"bin={target_sr/n_fft:.2f} Hz/bin)...")
    S_L = np.abs(librosa.stft(y_L, n_fft=n_fft, hop_length=hop_length))
    S_R = np.abs(librosa.stft(y_R, n_fft=n_fft, hop_length=hop_length))
    # y_L, y_R kept — reused for isochronic (no second load needed)

    freqs = librosa.fft_frequencies(sr=target_sr, n_fft=n_fft)
    times = librosa.frames_to_time(np.arange(S_L.shape[1]),
                                    sr=target_sr, hop_length=hop_length)
    n_frames = len(times)
    hop_dur = float(times[1] - times[0]) if n_frames > 1 else float(hop_length / target_sr)
    min_track_frames = max(4, int(3.0 / hop_dur))

    print("Whitening spectra...")
    W_L, S_db_L = _whiten_spectrum(S_L)
    W_R, S_db_R = _whiten_spectrum(S_R)
    del S_L, S_R  # originals freed; S_db cached for render
    gc.collect()

    print(f"Detecting peaks ({n_frames} frames × 2 channels)...")
    # Pre-slice freq mask once — avoids recomputing per-frame mask 2×n_frames times
    freq_mask_peaks = (freqs >= freq_min) & (freqs <= render_max)
    W_L_sliced = W_L[freq_mask_peaks, :]
    W_R_sliced = W_R[freq_mask_peaks, :]
    f_arr_sliced = freqs[freq_mask_peaks]
    del W_L, W_R
    gc.collect()

    peaks_L = [_peaks_from_whitened_frame(W_L_sliced[:, i], f_arr_sliced, prom_thresh)
               for i in range(n_frames)]
    peaks_R = [_peaks_from_whitened_frame(W_R_sliced[:, i], f_arr_sliced, prom_thresh)
               for i in range(n_frames)]
    del W_L_sliced, W_R_sliced
    gc.collect()

    print("Linking tracks...")
    tracks_L = _link_peaks_to_tracks(peaks_L, times, gap_max=gap_max,
                                      min_track_frames=min_track_frames)
    tracks_R = _link_peaks_to_tracks(peaks_R, times, gap_max=gap_max,
                                      min_track_frames=min_track_frames)
    del peaks_L, peaks_R
    gc.collect()

    tracks_L = [tr for tr in tracks_L if float(np.median(tr['powers'])) >= min_median_power]
    tracks_R = [tr for tr in tracks_R if float(np.median(tr['powers'])) >= min_median_power]
    print(f"Tracks (pre-merge, median≥{min_median_power}dB): {len(tracks_L)} L, {len(tracks_R)} R")

    merge_gap_sec = min(120.0, max(30.0, duration * 0.05))
    tracks_L = _merge_colinear_tracks(tracks_L, merge_df_hz=15.0, merge_gap_sec=merge_gap_sec)
    tracks_R = _merge_colinear_tracks(tracks_R, merge_df_hz=15.0, merge_gap_sec=merge_gap_sec)
    print(f"Tracks (post-merge): {len(tracks_L)} L, {len(tracks_R)} R")

    # --- Phase 2 ---
    print("Pairing binaural tracks...")
    pairs, solo_L, solo_R = _pair_binaural_tracks(
        tracks_L, tracks_R, binaural_range=binaural_range, min_overlap=pair_min_overlap)
    print(f"Found {len(pairs)} binaural pair(s), {len(solo_L)} solo L, {len(solo_R)} solo R")

    print("Measuring isochronic rates...")
    # Reuse y_L, y_R from initial load — no second librosa.load needed.
    # Slice is capped to 60s in _measure_isochronic_for_track.
    for pair in pairs:
        iso_L = _measure_isochronic_for_track(pair['track_L'], y_L, target_sr, iso_bandwidth)
        iso_R = _measure_isochronic_for_track(pair['track_R'], y_R, target_sr, iso_bandwidth)
        best = max([iso_L, iso_R], key=lambda x: x[1])
        pair['iso_hz'], pair['iso_conf'] = best[0], best[1]

    for tr in solo_L:
        tr['iso_hz'], tr['iso_conf'] = _measure_isochronic_for_track(
            tr, y_L, target_sr, iso_bandwidth)
    for tr in solo_R:
        tr['iso_hz'], tr['iso_conf'] = _measure_isochronic_for_track(
            tr, y_R, target_sr, iso_bandwidth)

    del y_L, y_R
    gc.collect()

    # --- ASCII summary ---
    def _fmt_t(sec):
        return f"{int(sec // 60)}:{int(sec % 60):02d}"

    def _fmt_iso(hz, conf):
        return f"{hz:.1f} Hz (conf {conf:.1f})" if hz is not None and conf >= iso_min_conf else "none"

    print("\n=== Binaural Pairs ===")
    if not pairs:
        print("  (none)")
    for idx, p in enumerate(pairs):
        tL, tR = p['track_L'], p['track_R']
        fL = float(np.median(tL['freqs']))
        fR = float(np.median(tR['freqs']))
        t_s = min(tL['times'][0], tR['times'][0])
        t_e = max(tL['times'][-1], tR['times'][-1])
        print(f"  [{idx}] ~{(fL+fR)/2:.0f} Hz  L={fL:.1f}  R={fR:.1f}  "
              f"beat={p['beat_hz_median']:.1f} Hz  "
              f"iso={_fmt_iso(p.get('iso_hz'), p.get('iso_conf', 0))}  "
              f"{_fmt_t(t_s)}-{_fmt_t(t_e)}")

    print("\n=== Solo Tracks ===")
    if not solo_L and not solo_R:
        print("  (none)")
    for tr in solo_L:
        f = float(np.median(tr['freqs']))
        print(f"  [L] ~{f:.0f} Hz  "
              f"iso={_fmt_iso(tr.get('iso_hz'), tr.get('iso_conf', 0))}  "
              f"{_fmt_t(tr['times'][0])}-{_fmt_t(tr['times'][-1])}")
    for tr in solo_R:
        f = float(np.median(tr['freqs']))
        print(f"  [R] ~{f:.0f} Hz  "
              f"iso={_fmt_iso(tr.get('iso_hz'), tr.get('iso_conf', 0))}  "
              f"{_fmt_t(tr['times'][0])}-{_fmt_t(tr['times'][-1])}")
    print()

    # --- Spectrogram ---
    print("Rendering background...")
    freq_mask = (freqs >= freq_min) & (freqs <= render_max)
    vmin_db, vmax_db = -80, 0

    # S_db_L / S_db_R cached from whitening — no recompute needed
    l_norm = np.clip((S_db_L[freq_mask, :] - vmin_db) / (vmax_db - vmin_db), 0, 1)
    r_norm = np.clip((S_db_R[freq_mask, :] - vmin_db) / (vmax_db - vmin_db), 0, 1)
    del S_db_L, S_db_R
    gc.collect()

    rgba_l, rgba_r = _CMAP_LEFT(l_norm), _CMAP_RIGHT(r_norm)
    del l_norm, r_norm
    gc.collect()

    rgba_blend = np.empty_like(rgba_l)
    rgba_blend[..., :3] = 1.0 - (1.0 - rgba_l[..., :3]) * (1.0 - rgba_r[..., :3])
    rgba_blend[..., 3] = 1.0
    del rgba_l, rgba_r
    gc.collect()

    fig, ax = plt.subplots(1, 1, figsize=(16, 6))
    extent = [times[0], times[-1], freqs[freq_mask][0], freqs[freq_mask][-1]]
    ax.imshow(rgba_blend, aspect='auto', origin='lower', extent=extent,
              interpolation='bilinear')
    del rgba_blend
    gc.collect()

    ax.set_ylabel('L (teal) / R (red)\nFrequency (Hz)')
    ax.set_ylim(freq_min, render_max)

    norm = Normalize(vmin=vmin_db, vmax=vmax_db)
    cbar_l = fig.colorbar(plt.cm.ScalarMappable(cmap=_CMAP_LEFT, norm=norm),
                          ax=ax, pad=0.01, fraction=0.025)
    cbar_l.set_label('L dB')
    cbar_r = fig.colorbar(plt.cm.ScalarMappable(cmap=_CMAP_RIGHT, norm=norm),
                          ax=ax, pad=0.055, fraction=0.025)
    cbar_r.set_label('R dB')

    # --- Track overlay ---
    min_render_sec = max(10.0, duration * 0.01)
    paired_L_ids = {p['track_L']['id'] for p in pairs}
    paired_R_ids = {p['track_R']['id'] for p in pairs}

    render_L_solo = [tr for tr in tracks_L
                     if tr['id'] not in paired_L_ids
                     and tr['times'][-1] - tr['times'][0] >= min_render_sec]
    render_R_solo = [tr for tr in tracks_R
                     if tr['id'] not in paired_R_ids
                     and tr['times'][-1] - tr['times'][0] >= min_render_sec]
    render_pairs = [p for p in pairs if p['t_end'] - p['t_start'] >= min_render_sec]
    print(f"Rendering {len(render_pairs)} pairs (gold), "
          f"{len(render_L_solo)} solo L, {len(render_R_solo)} solo R")

    def _plot_track(ax, tr, color, label, max_gap=5 * hop_dur):
        t_arr = np.array(tr['times'], dtype=float)
        f_arr = np.array(tr['freqs'], dtype=float)
        win = min(11, max(3, (len(f_arr) // 10) * 2 + 1))
        if len(f_arr) >= win:
            f_arr = uniform_filter1d(f_arr, size=win)
        split_pts = (np.where(np.diff(t_arr) > max_gap)[0] + 1
                     if len(t_arr) > 1 else np.array([], dtype=int))
        seg_s = np.concatenate([[0], split_pts])
        seg_e = np.concatenate([split_pts, [len(t_arr)]])
        first = True
        for s, e in zip(seg_s, seg_e):
            if e - s < 2:
                continue
            ax.plot(t_arr[s:e], f_arr[s:e], color=color, linewidth=1.5,
                    alpha=0.85, zorder=5, solid_capstyle='round',
                    label=label if first else None)
            first = False

    def _plot_pair(ax, pair, color, label, max_gap=5 * hop_dur):
        tL, tR = pair['track_L'], pair['track_R']
        t_L, t_R = np.array(tL['times']), np.array(tR['times'])
        t_common = np.union1d(t_L, t_R)
        t_common = t_common[(t_common >= pair['t_start']) & (t_common <= pair['t_end'])]
        if len(t_common) < 2:
            return
        f_mean = (np.interp(t_common, t_L, tL['freqs']) +
                  np.interp(t_common, t_R, tR['freqs'])) / 2
        win = min(11, max(3, (len(f_mean) // 10) * 2 + 1))
        if len(f_mean) >= win:
            f_mean = uniform_filter1d(f_mean, size=win)
        split_pts = (np.where(np.diff(t_common) > max_gap)[0] + 1
                     if len(t_common) > 1 else np.array([], dtype=int))
        seg_s = np.concatenate([[0], split_pts])
        seg_e = np.concatenate([split_pts, [len(t_common)]])
        first = True
        for s, e in zip(seg_s, seg_e):
            if e - s < 2:
                continue
            ax.plot(t_common[s:e], f_mean[s:e], color=color, linewidth=2.0,
                    alpha=0.9, zorder=6, solid_capstyle='round',
                    label=label if first else None)
            first = False

    added_l = added_r = added_p = False
    for tr in render_L_solo:
        _plot_track(ax, tr, _COLOR_L, 'L solo' if not added_l else None)
        added_l = True
    for tr in render_R_solo:
        _plot_track(ax, tr, _COLOR_R, 'R solo' if not added_r else None)
        added_r = True
    for p in render_pairs:
        _plot_pair(ax, p, _COLOR_PAIR, 'Binaural pairs' if not added_p else None)
        added_p = True

    for p in render_pairs:
        t_mid = (p['t_start'] + p['t_end']) / 2
        f_mid = (float(np.median(p['track_L']['freqs'])) +
                 float(np.median(p['track_R']['freqs']))) / 2
        lbl = f"{p['beat_hz_median']:.1f}Hz"
        iso_hz, iso_conf = p.get('iso_hz'), p.get('iso_conf', 0)
        if iso_hz is not None and iso_conf >= iso_min_conf:
            lbl += f" / {iso_hz:.1f}Hz iso"
        ax.text(t_mid, f_mid + 8, lbl, color='white', fontsize=6,
                ha='center', va='bottom', zorder=10,
                bbox=dict(boxstyle='round,pad=0.1', fc='black', alpha=0.5))

    ax.set_xlabel('Time')
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x//60)}:{int(x%60):02d}"))

    handles, _ = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc='upper right', fontsize=8, framealpha=0.8)

    fig.suptitle(f'{filename}  —  {len(pairs)} pairs  '
                 f'{len(solo_L)+len(solo_R)} solo  '
                 f'(L:{len(tracks_L)}  R:{len(tracks_R)})',
                 fontsize=13, y=0.98)
    plt.tight_layout()

    if output_path is None:
        base, _ = os.path.splitext(filepath)
        output_path = base + '_tracks.png'

    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")

    if export_json:
        json_path = os.path.splitext(output_path)[0].replace('_tracks', '') + '_analyzed.json'
        data = _tracks_to_json(pairs, solo_L, solo_R, duration)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved: {json_path}")

    return tracks_L, tracks_R, pairs


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description='Binaural beat & isochronic analyzer — ridge tracking pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python binaural_analyzer.py audio.ogg
  python binaural_analyzer.py audio.ogg -o analysis.png
  python binaural_analyzer.py audio.ogg --freq-max 800
"""
    )
    parser.add_argument('audio_file', help='Stereo audio file to analyze')
    parser.add_argument('--freq-min', type=float, default=30,
                        help='Min frequency to display (default: 30)')
    parser.add_argument('--freq-max', type=float, default=None,
                        help='Max frequency to display (default: auto-detect)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output PNG path (default: <input>_tracks.png)')
    parser.add_argument('--binaural-range', type=str, default='0.3,20',
                        help='Valid beat Hz range for pairing as "min,max" (default: 0.3,20)')
    parser.add_argument('--iso-bandwidth', type=float, default=15,
                        help='Bandpass Hz on each side of carrier (default: 15)')
    parser.add_argument('--iso-min-conf', type=float, default=1.0,
                        help='Min confidence to report isochronic rate (default: 1.0)')
    parser.add_argument('--pair-min-overlap', type=int, default=4,
                        help='Min overlapping time points to form a pair (default: 4)')
    parser.add_argument('--export-json', '-j', action='store_true',
                        help='Export generator-compatible JSON alongside the PNG')
    args = parser.parse_args()

    try:
        _br = [float(x.strip()) for x in args.binaural_range.split(',')]
        binaural_range = (min(_br), max(_br))
    except Exception:
        binaural_range = (0.3, 20.0)

    analyze(
        args.audio_file,
        freq_min=args.freq_min,
        freq_max=args.freq_max,
        output_path=args.output,
        binaural_range=binaural_range,
        iso_bandwidth=args.iso_bandwidth,
        iso_min_conf=args.iso_min_conf,
        pair_min_overlap=args.pair_min_overlap,
        export_json=args.export_json,
    )


if __name__ == "__main__":
    main()
