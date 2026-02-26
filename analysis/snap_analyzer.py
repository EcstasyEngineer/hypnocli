#!/usr/bin/env python3
"""
Snap/Transient Analyzer — detects finger snaps in hypnosis audio and
cross-references with Whisper word-level timestamps.

Pipeline:
    1. Load audio as mono, downsample to 22050 Hz
    2. Onset detection via spectral flux (librosa)
    3. Validate candidates: spectral centroid in snap range (1–8 kHz),
       short duration, high onset strength
    4. Optionally load Whisper JSON (--word_timestamps True) and map each
       snap to the nearest word within a configurable window

Usage:
    # Just detect snaps:
    python snap_analyzer.py <audio_file>

    # Detect + map to whisper transcript:
    python snap_analyzer.py <audio_file> --whisper transcript.json

    # Run whisper first, then analyze (requires CUDA whisper install):
    python snap_analyzer.py <audio_file> --transcribe --model medium

Options:
    --whisper PATH          Whisper JSON with word_timestamps
    --transcribe            Run whisper --word_timestamps True before analysis
    --model NAME            Whisper model for --transcribe (default: medium)
    --window SEC            Max distance (sec) to associate snap↔word (default: 0.5)
    --min-strength FLOAT    Onset strength threshold multiplier (default: 2.0)
    --output / -o PATH      Output JSON path (default: <input>_snaps.json)
    --audacity PATH         Export Audacity label track (tab-separated .txt)
    --plot                  Save a timeline PNG with snap markers
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import librosa
from scipy import signal as scipy_signal

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ── Snap Detection ──────────────────────────────────────────────────────────

def _hf_energy_ratio(y_segment, sr, crossover_hz=2500):
    """Ratio of energy above crossover_hz to total energy in a short segment.

    Snaps have broadband energy with strong HF content (ratio > 0.3 typically).
    Speech plosives (P/T/K/B) concentrate below 2.5 kHz (ratio < 0.15).
    """
    if len(y_segment) < 64:
        return 0.0
    # Zero-pad to at least 512 samples for decent freq resolution
    n_fft = max(512, len(y_segment))
    spectrum = np.abs(np.fft.rfft(y_segment, n=n_fft))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    total = np.sum(spectrum ** 2)
    if total == 0:
        return 0.0
    hf_mask = freqs >= crossover_hz
    hf_energy = np.sum(spectrum[hf_mask] ** 2)
    return float(hf_energy / total)


def _hf_spike_ratio(y, sr, onset_sample, analysis_ms=30, context_ms=200,
                    crossover_hz=2500):
    """Compare HF energy at onset vs local HF baseline.

    Instead of HF/total (which fails when a loud LF source like a guitar
    drowns the ratio), this measures HF energy at the onset relative to
    the HF energy in the surrounding context. A snap will spike the HF
    band even if the total energy is dominated by low frequencies.

    Returns (hf_spike_ratio, hf_onset_energy).
    """
    n_fft = 512
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    hf_mask = freqs >= crossover_hz
    analysis_samples = int(analysis_ms / 1000 * sr)
    context_samples = int(context_ms / 1000 * sr)

    # HF energy at onset
    seg_start = max(0, onset_sample)
    seg_end = min(len(y), onset_sample + analysis_samples)
    if seg_end - seg_start < analysis_samples // 2:
        return 0.0, 0.0
    onset_seg = y[seg_start:seg_end]
    onset_spec = np.abs(np.fft.rfft(onset_seg, n=n_fft))
    hf_onset = np.sum(onset_spec[hf_mask] ** 2)

    # HF energy in context (before the onset)
    ctx_start = max(0, onset_sample - context_samples)
    ctx_end = max(0, onset_sample - analysis_samples)  # exclude the onset itself
    if ctx_end - ctx_start < analysis_samples:
        # Not enough context before, try after
        ctx_start = min(len(y), onset_sample + analysis_samples)
        ctx_end = min(len(y), ctx_start + context_samples)

    if ctx_end - ctx_start < analysis_samples // 2:
        return 0.0, hf_onset

    # Average HF energy over context in sliding windows
    n_windows = max(1, (ctx_end - ctx_start - analysis_samples) // (analysis_samples // 2))
    hf_ctx_values = []
    for i in range(n_windows):
        ws = ctx_start + i * (analysis_samples // 2)
        we = ws + analysis_samples
        if we > ctx_end:
            break
        ctx_seg = y[ws:we]
        ctx_spec = np.abs(np.fft.rfft(ctx_seg, n=n_fft))
        hf_ctx_values.append(np.sum(ctx_spec[hf_mask] ** 2))

    if not hf_ctx_values:
        return 0.0, hf_onset

    hf_baseline = np.median(hf_ctx_values)
    if hf_baseline < 1e-10:
        # No HF in context at all — if we have HF at onset, it's a spike
        return float(hf_onset) if hf_onset > 0 else 0.0, float(hf_onset)

    return float(hf_onset / hf_baseline), float(hf_onset)


def _onset_sharpness(y, sr, onset_sample, window_ms=10):
    """Measure how sharp/impulsive the onset is.

    Returns ratio of peak amplitude in a tiny window around onset vs
    the RMS of a wider surrounding window. Snaps have very high ratios.
    """
    narrow = int(window_ms / 1000 * sr)  # ~10ms
    wide = int(50 / 1000 * sr)           # 50ms context

    start_narrow = max(0, onset_sample - narrow // 2)
    end_narrow = min(len(y), onset_sample + narrow // 2)
    start_wide = max(0, onset_sample - wide)
    end_wide = min(len(y), onset_sample + wide)

    peak = np.max(np.abs(y[start_narrow:end_narrow])) if end_narrow > start_narrow else 0
    rms = np.sqrt(np.mean(y[start_wide:end_wide] ** 2)) if end_wide > start_wide else 1e-10
    return float(peak / max(rms, 1e-10))


def detect_snaps(audio_path, sr=22050, min_strength=1.5, hf_crossover=2500,
                 min_hf_ratio=0.08, snap_analysis_ms=30, min_sharpness=2.0,
                 min_score=3.0):
    """Detect finger snaps via dual-band onset detection + HF energy + sharpness.

    Pipeline:
        1. Full-band onset detection via spectral flux (catches most snaps)
        2. HF-only onset detection via highpass >5kHz + spectral flux
           (catches snaps masked by loud LF sources like guitar hits)
        3. Merge onset candidates, deduplicate within 50ms
        4. HF energy ratio: ratio of energy above crossover to total
        5. Onset sharpness: peak-to-RMS ratio in a narrow window
        6. Composite scoring: strength * hf_effective * sharpness ≥ min_score

    Returns list of dicts: [{time_sec, strength, hf_ratio, sharpness, score}, ...]
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    duration = len(y) / sr

    # --- Pass 1: Full-band onset detection ---
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512,
                                              aggregate=np.median)
    onset_times_fb = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512,
                                                 onset_envelope=onset_env,
                                                 backtrack=False, units='time')
    onset_frames_fb = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512,
                                                  onset_envelope=onset_env,
                                                  backtrack=False, units='frames')

    # Adaptive threshold for full-band
    median_str = np.median(onset_env)
    mad = np.median(np.abs(onset_env - median_str))
    threshold_fb = median_str + min_strength * max(mad, 0.01)

    # Collect (time, strength) pairs that pass threshold
    candidates = []
    if len(onset_frames_fb) > 0:
        strengths_fb = onset_env[onset_frames_fb]
        for t, s in zip(onset_times_fb, strengths_fb):
            if s >= threshold_fb:
                candidates.append((float(t), float(s)))

    # --- Pass 2: HF-only onset detection at 44100 Hz ---
    # Must run at 44.1kHz because snap energy peaks at 8-12kHz and
    # at 22050 Hz Nyquist (11025 Hz) we lose the upper harmonics
    sr_hf = 44100
    y_44 = librosa.load(audio_path, sr=sr_hf, mono=True)[0]
    sos_hf = scipy_signal.butter(4, 5000 / (sr_hf / 2), btype='high', output='sos')
    y_hf = scipy_signal.sosfiltfilt(sos_hf, y_44)

    onset_env_hf = librosa.onset.onset_strength(y=y_hf, sr=sr_hf, hop_length=512,
                                                  aggregate=np.median)
    onset_times_hf = librosa.onset.onset_detect(y=y_hf, sr=sr_hf, hop_length=512,
                                                  onset_envelope=onset_env_hf,
                                                  backtrack=False, units='time')
    onset_frames_hf = librosa.onset.onset_detect(y=y_hf, sr=sr_hf, hop_length=512,
                                                  onset_envelope=onset_env_hf,
                                                  backtrack=False, units='frames')

    if len(onset_frames_hf) > 0:
        strengths_hf = onset_env_hf[onset_frames_hf]
        median_hf = np.median(onset_env_hf)
        mad_hf = np.median(np.abs(onset_env_hf - median_hf))
        threshold_hf = median_hf + min_strength * max(mad_hf, 0.001)

        for t, s in zip(onset_times_hf, strengths_hf):
            if s >= threshold_hf:
                # Use the full-band onset strength at this time for scoring
                frame = int(t * sr / 512)
                fb_str = float(onset_env[min(frame, len(onset_env) - 1)])
                candidates.append((float(t), max(float(s), fb_str)))

    if not candidates:
        return [], duration

    # Sort by time — dedup happens AFTER scoring (each candidate evaluated
    # independently, then final snaps deduped). This prevents a guitar onset
    # at t=1.30 from eating a snap-specific HF onset at t=1.335.
    candidates.sort(key=lambda x: x[0])

    snap_window_samples = int(snap_analysis_ms / 1000 * sr)

    snaps = []
    for t, strength in candidates:
        onset_sample = int(t * sr)

        # Extract short segment around onset for spectral analysis
        seg_start = max(0, onset_sample)
        seg_end = min(len(y), onset_sample + snap_window_samples)
        if seg_end - seg_start < snap_window_samples // 2:
            continue
        segment = y[seg_start:seg_end]

        # HF energy ratio — the key discriminator for most snaps
        hf_ratio = _hf_energy_ratio(segment, sr, crossover_hz=hf_crossover)

        # For snaps masked by loud LF (guitar, bass), the HF ratio fails
        # because total energy is dominated by LF. Use absolute HF energy
        # compared to local baseline at 44.1kHz-native frequencies.
        # Only compute this if hf_ratio alone wouldn't pass.
        hf_effective = hf_ratio
        uhf_spike = 0.0
        if hf_ratio < min_hf_ratio:
            # Check if this onset has a significant >8kHz spike vs context
            # Load a small chunk at the onset position from the 44.1kHz signal
            onset_44 = int(t * sr_hf)
            analysis_44 = int(snap_analysis_ms / 1000 * sr_hf)
            if onset_44 + analysis_44 <= len(y_44):
                seg_44 = y_44[onset_44:onset_44 + analysis_44]
                n_fft = 1024
                spec = np.abs(np.fft.rfft(seg_44, n=n_fft))
                freqs_44 = np.fft.rfftfreq(n_fft, 1.0 / sr_hf)
                hf_8k = np.sum(spec[freqs_44 >= 8000] ** 2)

                # Context: average >8kHz energy in 200ms before
                ctx_start = max(0, onset_44 - int(0.2 * sr_hf))
                ctx_end = max(0, onset_44 - analysis_44)
                n_ctx_wins = max(1, (ctx_end - ctx_start) // (analysis_44 // 2))
                ctx_vals = []
                for ci in range(n_ctx_wins):
                    ws = ctx_start + ci * (analysis_44 // 2)
                    we = ws + analysis_44
                    if we > ctx_end:
                        break
                    cs = y_44[ws:we]
                    cspec = np.abs(np.fft.rfft(cs, n=n_fft))
                    ctx_vals.append(np.sum(cspec[freqs_44 >= 8000] ** 2))

                baseline = np.median(ctx_vals) if ctx_vals else 0
                uhf_spike = float(hf_8k / max(baseline, 1e-10))

                # Only rescue if spike is very large (>50x baseline)
                # Scale hf_effective by spike magnitude for scoring
                if uhf_spike > 50:
                    # Very confident snap — guitar-masked. Scale from 0.15 to 0.5
                    # based on spike magnitude (50x → 0.15, 500x+ → 0.5)
                    hf_effective = max(hf_ratio,
                                       0.15 + 0.35 * min((uhf_spike - 50) / 450, 1.0))

        if hf_effective < min_hf_ratio:
            continue

        # Onset sharpness — snaps are extremely impulsive
        sharpness = _onset_sharpness(y, sr, onset_sample)
        if sharpness < min_sharpness:
            continue

        # Composite score for ranking — product of all three signals
        score = strength * hf_effective * sharpness
        if score < min_score:
            continue

        # Also compute centroid for diagnostics
        centroid = librosa.feature.spectral_centroid(y=segment, sr=sr)[0]
        c = float(centroid[0]) if len(centroid) > 0 else 0

        snaps.append({
            'time_sec': round(float(t), 3),
            'strength': round(float(strength), 2),
            'hf_ratio': round(float(hf_ratio), 4),
            'uhf_spike': round(float(uhf_spike), 2),
            'hf_effective': round(float(hf_effective), 4),
            'sharpness': round(float(sharpness), 2),
            'score': round(float(score), 2),
            'centroid_hz': round(float(c), 1),
        })

    # Post-scoring dedup: if two snaps are within 50ms, keep higher score
    snaps.sort(key=lambda s: s['time_sec'])
    deduped = []
    for s in snaps:
        if deduped and abs(s['time_sec'] - deduped[-1]['time_sec']) < 0.05:
            if s['score'] > deduped[-1]['score']:
                deduped[-1] = s
        else:
            deduped.append(s)

    return deduped, duration


# ── Whisper Integration ─────────────────────────────────────────────────────

def load_whisper_words(json_path):
    """Parse whisper JSON with word_timestamps into flat word list.

    Returns list of dicts: [{word, start, end, probability}, ...]
    """
    with open(json_path) as f:
        data = json.load(f)

    words = []
    for seg in data.get('segments', []):
        for w in seg.get('words', []):
            words.append({
                'word': w['word'].strip(),
                'start': w['start'],
                'end': w['end'],
                'probability': w.get('probability', 0),
            })
    return words


def run_whisper(audio_path, model='medium', output_dir=None):
    """Run whisper with word_timestamps and return path to JSON output."""
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix='snap_whisper_')

    cmd = [
        'whisper', audio_path,
        '--model', model,
        '--language', 'en',
        '--word_timestamps', 'True',
        '--output_format', 'json',
        '--output_dir', output_dir,
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    base = os.path.splitext(os.path.basename(audio_path))[0]
    json_path = os.path.join(output_dir, f'{base}.json')
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Whisper output not found at {json_path}")
    return json_path


def map_snaps_to_words(snaps, words, window_sec=0.5):
    """Associate each snap with the nearest word within window_sec.

    A snap can land:
      - BEFORE a word (anticipatory snap → marks the next word)
      - DURING a word (emphasis snap → marks that word)
      - AFTER a word (punctuation snap → marks the previous word)

    Returns enriched snap list with 'word', 'word_distance_sec', 'position'
    fields added. Also returns word list with 'snap_count' added.
    """
    # Build sorted word list for binary search
    word_starts = np.array([w['start'] for w in words])
    word_ends = np.array([w['end'] for w in words])

    # Track snap counts per word
    snap_counts = [0] * len(words)

    for snap in snaps:
        t = snap['time_sec']

        # Find closest word by midpoint distance
        if len(words) == 0:
            snap['word'] = None
            snap['position'] = 'isolated'
            snap['word_distance_sec'] = None
            continue

        word_mids = (word_starts + word_ends) / 2
        dists = np.abs(word_mids - t)
        best_idx = int(np.argmin(dists))
        best_dist = dists[best_idx]

        if best_dist > window_sec:
            snap['word'] = None
            snap['position'] = 'isolated'
            snap['word_distance_sec'] = round(float(best_dist), 3)
            continue

        w = words[best_idx]
        snap['word'] = w['word']
        snap['word_index'] = best_idx
        snap['word_distance_sec'] = round(float(best_dist), 3)
        snap_counts[best_idx] += 1

        # Classify position
        if t < w['start']:
            snap['position'] = 'before'
        elif t > w['end']:
            snap['position'] = 'after'
        else:
            snap['position'] = 'during'

    # Enrich words with snap counts
    for i, w in enumerate(words):
        w['snap_count'] = snap_counts[i]

    return snaps, words


# ── Visualization ───────────────────────────────────────────────────────────

def plot_snap_timeline(snaps, words, duration, output_path, audio_path=None):
    """Create a timeline plot showing snap positions relative to words."""
    if not HAS_MATPLOTLIB:
        print("matplotlib not available, skipping plot")
        return

    fig, axes = plt.subplots(2, 1, figsize=(20, 6), height_ratios=[2, 1],
                             sharex=True)
    fig.patch.set_facecolor('#0a0a14')

    # Top: snap markers with strength
    ax1 = axes[0]
    ax1.set_facecolor('#0a0a14')
    if snaps:
        times = [s['time_sec'] for s in snaps]
        strengths = [s['strength'] for s in snaps]
        colors = ['#ff4444' if s.get('word') else '#666666' for s in snaps]
        ax1.scatter(times, strengths, c=colors, s=40, zorder=3, alpha=0.8)
        for s in snaps:
            if s.get('word'):
                ax1.annotate(s['word'], (s['time_sec'], s['strength']),
                            fontsize=6, color='#cccccc', rotation=45,
                            ha='left', va='bottom', textcoords='offset points',
                            xytext=(2, 4))
    ax1.set_ylabel('Onset Strength', color='#999999')
    ax1.tick_params(colors='#666666')
    ax1.set_title(f'Snap Detection — {os.path.basename(audio_path or "audio")} '
                  f'({len(snaps)} snaps)', color='#cccccc', fontsize=12)

    # Bottom: word density with snap highlights
    ax2 = axes[1]
    ax2.set_facecolor('#0a0a14')
    if words:
        snapped_words = [w for w in words if w.get('snap_count', 0) > 0]
        unsnapped_words = [w for w in words if w.get('snap_count', 0) == 0]
        # Unsnapped words as gray bars
        for w in unsnapped_words:
            ax2.barh(0, w['end'] - w['start'], left=w['start'],
                    color='#222233', height=0.8, edgecolor='none')
        # Snapped words as red bars
        for w in snapped_words:
            ax2.barh(0, w['end'] - w['start'], left=w['start'],
                    color='#881122', height=0.8, edgecolor='#ff4444',
                    linewidth=0.5)
    # Snap lines
    for s in snaps:
        ax2.axvline(s['time_sec'], color='#ff4444', alpha=0.6, linewidth=0.5)
    ax2.set_ylabel('Words', color='#999999')
    ax2.set_xlabel('Time (s)', color='#999999')
    ax2.tick_params(colors='#666666')
    ax2.set_yticks([])
    ax2.set_xlim(0, duration)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='#0a0a14',
                bbox_inches='tight')
    plt.close()
    print(f"Plot saved: {output_path}")


# ── Audacity Label Export ──────────────────────────────────────────────────

def export_audacity_labels(snaps, output_path, label_duration=0.03):
    """Export snaps as Audacity label track (tab-separated .txt).

    Format: START\\tEND\\tLABEL
    Import in Audacity via File → Import → Labels.
    """
    with open(output_path, 'w') as f:
        for s in snaps:
            t = s['time_sec']
            end = round(t + label_duration, 3)
            word = s.get('word', '')
            if word:
                pos = s.get('position', '')
                label = f"{word} (snap {pos})" if pos else f"{word} (snap)"
            else:
                label = "snap"
            f.write(f"{t:.3f}\t{end:.3f}\t{label}\n")
    print(f"Audacity labels saved: {output_path} ({len(snaps)} labels)")


# ── ASCII Report ────────────────────────────────────────────────────────────

def print_report(snaps, words, duration):
    """Print ASCII summary of snap analysis."""
    n = len(snaps)
    print(f"\n{'═' * 70}")
    print(f"  SNAP ANALYSIS — {n} snaps detected in {duration:.1f}s")
    print(f"{'═' * 70}")

    if n == 0:
        print("  No snaps detected.")
        return

    # Overall stats
    rate = n / (duration / 60) if duration > 0 else 0
    times = [s['time_sec'] for s in snaps]
    gaps = np.diff(times) if len(times) > 1 else [0]
    print(f"  Rate:     {rate:.1f} snaps/min")
    print(f"  First:    {times[0]:.1f}s")
    print(f"  Last:     {times[-1]:.1f}s")
    if len(gaps) > 0:
        print(f"  Gap:      median {np.median(gaps):.1f}s, "
              f"min {np.min(gaps):.1f}s, max {np.max(gaps):.1f}s")

    # Snap-word mapping
    mapped = [s for s in snaps if s.get('word')]
    isolated = [s for s in snaps if not s.get('word')]
    print(f"\n  Mapped to words: {len(mapped)}/{n} "
          f"({100*len(mapped)/n:.0f}%)")
    if isolated:
        print(f"  Isolated (no word nearby): {len(isolated)}")

    # Position breakdown
    before = sum(1 for s in mapped if s.get('position') == 'before')
    during = sum(1 for s in mapped if s.get('position') == 'during')
    after = sum(1 for s in mapped if s.get('position') == 'after')
    if mapped:
        print(f"  Position: {before} before, {during} during, {after} after word")

    # Most-snapped words
    if words:
        snapped = [(w['word'], w['snap_count']) for w in words
                    if w.get('snap_count', 0) > 0]
        if snapped:
            print(f"\n  {'─' * 50}")
            print(f"  SNAPPED WORDS ({len(snapped)} unique):")
            print(f"  {'─' * 50}")
            # Sort by time of first appearance
            for s in snaps:
                if s.get('word'):
                    pos_tag = {'before': '→', 'during': '●', 'after': '←'}
                    tag = pos_tag.get(s.get('position', ''), '?')
                    t = s['time_sec']
                    mins = int(t // 60)
                    secs = t % 60
                    dist = s.get('word_distance_sec', 0)
                    hf = s.get('hf_ratio', 0)
                    shp = s.get('sharpness', 0)
                    print(f"    {mins:02d}:{secs:05.2f}  {tag} \"{s['word']}\""
                          f"  (dist={dist:.3f}s, str={s['strength']:.1f}"
                          f", hf={hf:.3f}, sharp={shp:.1f})")

    # Density by segment (60s buckets)
    bucket_size = 60
    n_buckets = int(np.ceil(duration / bucket_size))
    if n_buckets > 0 and n > 0:
        print(f"\n  {'─' * 50}")
        print(f"  DENSITY (per minute):")
        print(f"  {'─' * 50}")
        buckets = [0] * n_buckets
        for s in snaps:
            b = min(int(s['time_sec'] / bucket_size), n_buckets - 1)
            buckets[b] += 1
        max_count = max(buckets)
        for i, count in enumerate(buckets):
            bar_len = int(count / max(max_count, 1) * 30)
            bar = '█' * bar_len
            mins_start = i
            print(f"    {mins_start:3d}m  {bar:<30s}  {count}")

    print(f"\n{'═' * 70}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Detect finger snaps in audio and map to transcript words')
    parser.add_argument('audio', help='Audio file to analyze')
    parser.add_argument('--whisper', metavar='PATH',
                        help='Whisper JSON with word_timestamps')
    parser.add_argument('--transcribe', action='store_true',
                        help='Run whisper --word_timestamps True first')
    parser.add_argument('--model', default='medium',
                        help='Whisper model for --transcribe (default: medium)')
    parser.add_argument('--window', type=float, default=0.5,
                        help='Max snap↔word distance in seconds (default: 0.5)')
    parser.add_argument('--min-strength', type=float, default=1.5,
                        help='Onset strength threshold multiplier (default: 1.5)')
    parser.add_argument('--hf-crossover', type=float, default=2500,
                        help='HF energy ratio crossover frequency Hz (default: 2500)')
    parser.add_argument('--min-hf-ratio', type=float, default=0.08,
                        help='Minimum HF energy ratio to qualify (default: 0.08)')
    parser.add_argument('--min-sharpness', type=float, default=2.0,
                        help='Minimum onset peak/RMS sharpness (default: 2.0)')
    parser.add_argument('--min-score', type=float, default=3.0,
                        help='Minimum composite score strength*hf*sharpness (default: 3.0)')
    parser.add_argument('--output', '-o', metavar='PATH',
                        help='Output JSON path')
    parser.add_argument('--audacity', metavar='PATH',
                        help='Export Audacity label track (.txt)')
    parser.add_argument('--plot', action='store_true',
                        help='Save timeline PNG')
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"Error: {args.audio} not found", file=sys.stderr)
        sys.exit(1)

    # Step 1: Detect snaps
    print(f"Analyzing: {args.audio}")
    snaps, duration = detect_snaps(args.audio, min_strength=args.min_strength,
                                    hf_crossover=args.hf_crossover,
                                    min_hf_ratio=args.min_hf_ratio,
                                    min_sharpness=args.min_sharpness,
                                    min_score=args.min_score)
    print(f"  Found {len(snaps)} snap candidates in {duration:.1f}s")

    # Step 2: Get whisper words if available
    words = []
    whisper_json = args.whisper

    if args.transcribe and not whisper_json:
        print("\nRunning whisper transcription...")
        output_dir = os.path.dirname(args.output) if args.output else os.path.dirname(args.audio)
        if not output_dir:
            output_dir = '.'
        whisper_json = run_whisper(args.audio, model=args.model,
                                   output_dir=output_dir)
        print(f"  Whisper JSON: {whisper_json}")

    if whisper_json:
        words = load_whisper_words(whisper_json)
        print(f"  Loaded {len(words)} words from whisper transcript")
        snaps, words = map_snaps_to_words(snaps, words, window_sec=args.window)

    # Step 3: Report
    print_report(snaps, words, duration)

    # Step 4: Save output
    base = os.path.splitext(args.audio)[0]
    out_path = args.output or f'{base}_snaps.json'
    result = {
        'audio': os.path.basename(args.audio),
        'duration_sec': round(duration, 2),
        'snap_count': len(snaps),
        'snaps': snaps,
    }
    if words:
        snapped_words = [{'word': w['word'], 'start': w['start'],
                          'end': w['end'], 'snap_count': w['snap_count']}
                         for w in words if w.get('snap_count', 0) > 0]
        result['whisper_source'] = whisper_json
        result['snapped_words'] = snapped_words
        result['total_words'] = len(words)
        result['words_snapped'] = len(snapped_words)

    # Convert numpy types for JSON serialization
    def _jsonify(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')

    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, default=_jsonify)
    print(f"\nResults saved: {out_path}")

    # Step 5: Audacity labels
    if args.audacity:
        export_audacity_labels(snaps, args.audacity)

    # Step 6: Plot
    if args.plot:
        plot_path = f'{base}_snaps.png'
        plot_snap_timeline(snaps, words, duration, plot_path,
                           audio_path=args.audio)

    return snaps, words


if __name__ == '__main__':
    main()
