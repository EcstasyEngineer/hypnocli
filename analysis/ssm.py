#!/usr/bin/env python3
"""
Self-Similarity Matrix (SSM) Analysis for Hypnosis Audio

Generates visual structure maps showing repeated segments, unique sections,
and potential hidden modifications in audio files.

Two analysis modes:
  - MFCC (acoustic): How does it SOUND? Captures production differences (EQ, binaural, compression)
  - Text (semantic): What is being SAID? Requires transcript, ignores audio production

Usage:
  # Both analyses (requires transcript + OpenAI key)
  python ssm.py audio.mp3 --transcript audio.srt

  # Acoustic only (no transcript needed)
  python ssm.py audio.mp3

  # Semantic only
  python ssm.py --transcript audio.srt

  # Custom output directory
  python ssm.py audio.mp3 --transcript audio.srt --output-dir ./results

Environment:
  OPENAI_API_KEY - Required for semantic analysis (text-embedding-3-small)

Dependencies:
  pip install librosa numpy matplotlib scipy openai
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# =============================================================================
# SRT Parsing
# =============================================================================

def parse_srt(srt_path: str) -> List[Tuple[float, float, str]]:
    """Parse SRT file into list of (start_time, end_time, text)"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.strip().split('\n\n')
    entries = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            timestamp_match = re.match(
                r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
                lines[1]
            )
            if timestamp_match:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = timestamp_match.groups()
                start = int(h1)*3600 + int(m1)*60 + int(s1) + int(ms1)/1000
                end = int(h2)*3600 + int(m2)*60 + int(s2) + int(ms2)/1000
                text = ' '.join(lines[2:])
                entries.append((start, end, text))

    return entries


def chunk_transcript(
    entries: List[Tuple[float, float, str]],
    window_size: float = 30.0,
    hop_size: float = 15.0,
    max_duration: Optional[float] = None
) -> Tuple[List[float], List[str]]:
    """
    Chunk transcript into overlapping time windows.

    Args:
        entries: List of (start, end, text) from SRT
        window_size: Window size in seconds (default 30s)
        hop_size: Hop between windows in seconds (default 15s = 50% overlap)
        max_duration: Max time to process (default: end of transcript)

    Returns:
        (times, texts): Lists of window center times and concatenated text
    """
    if not entries:
        return [], []

    if max_duration is None:
        max_duration = max(e[1] for e in entries)

    times, texts = [], []
    window_start = 0.0

    while window_start < max_duration:
        window_end = window_start + window_size
        window_center = window_start + window_size / 2

        # Collect text overlapping this window
        chunk_texts = [text for start, end, text in entries
                       if start < window_end and end > window_start]

        chunk_text = ' '.join(chunk_texts).strip()
        if chunk_text:
            times.append(window_center)
            texts.append(chunk_text)

        window_start += hop_size

    return times, texts


# =============================================================================
# MFCC (Acoustic) SSM
# =============================================================================

def compute_mfcc_ssm(
    audio_path: str,
    sr: int = 22050,
    hop_length: int = 4096,
    n_mfcc: int = 13,
    smoothing: float = 1.0
) -> Tuple[np.ndarray, float, int, int]:
    """
    Compute MFCC-based self-similarity matrix.

    Args:
        audio_path: Path to audio file
        sr: Sample rate (default 22050)
        hop_length: Samples between frames (larger = less memory, coarser resolution)
        n_mfcc: Number of MFCC coefficients
        smoothing: Gaussian smoothing sigma (0 to disable)

    Returns:
        (ssm, duration, sr, hop_length)
    """
    if not HAS_LIBROSA:
        raise ImportError("librosa required for MFCC analysis: pip install librosa")

    print(f"[mfcc] Loading: {audio_path}")
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    duration = len(y) / sr
    print(f"[mfcc] Duration: {duration/60:.1f} min ({duration:.0f}s)")

    print(f"[mfcc] Extracting features (hop={hop_length}, ~{hop_length/sr*1000:.0f}ms resolution)...")
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, hop_length=hop_length)

    # Normalize per coefficient
    mfcc = (mfcc - mfcc.mean(axis=1, keepdims=True)) / (mfcc.std(axis=1, keepdims=True) + 1e-8)
    print(f"[mfcc] Feature matrix: {mfcc.shape[1]} frames")

    print("[mfcc] Computing similarity matrix...")
    mfcc_norm = mfcc / (np.linalg.norm(mfcc, axis=0, keepdims=True) + 1e-8)
    ssm = np.dot(mfcc_norm.T, mfcc_norm)

    if smoothing > 0:
        ssm = gaussian_filter(ssm, sigma=smoothing)

    return ssm, duration, sr, hop_length


# =============================================================================
# Text (Semantic) SSM
# =============================================================================

def compute_text_ssm(
    srt_path: str,
    api_key: Optional[str] = None,
    model: str = "text-embedding-3-small",
    window_size: float = 30.0,
    hop_size: float = 15.0
) -> Tuple[np.ndarray, List[float]]:
    """
    Compute text embedding self-similarity matrix.

    Args:
        srt_path: Path to SRT transcript
        api_key: OpenAI API key (default: OPENAI_API_KEY env var)
        model: Embedding model name
        window_size: Chunk window in seconds
        hop_size: Chunk hop in seconds

    Returns:
        (ssm, times): Similarity matrix and list of chunk center times
    """
    if not HAS_OPENAI:
        raise ImportError("openai required for text analysis: pip install openai")

    api_key = api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable required for text analysis")

    print(f"[text] Parsing: {srt_path}")
    entries = parse_srt(srt_path)
    print(f"[text] Found {len(entries)} subtitle entries")

    times, texts = chunk_transcript(entries, window_size, hop_size)
    print(f"[text] Created {len(texts)} chunks ({window_size}s window, {hop_size}s hop)")

    if not texts:
        raise ValueError("No text chunks extracted from transcript")

    # Get embeddings
    print(f"[text] Getting embeddings ({model})...")
    client = OpenAI(api_key=api_key)

    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([item.embedding for item in response.data])
        if len(texts) > batch_size:
            print(f"[text]   Batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")

    embeddings = np.array(all_embeddings)
    print(f"[text] Embedding shape: {embeddings.shape}")

    # Compute cosine similarity
    print("[text] Computing similarity matrix...")
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / (norms + 1e-8)
    ssm = np.dot(normalized, normalized.T)

    return ssm, times


# =============================================================================
# Visualization
# =============================================================================

def plot_ssm(
    ssm: np.ndarray,
    output_path: str,
    title: str,
    duration: Optional[float] = None,
    times: Optional[List[float]] = None,
    sr: int = 22050,
    hop_length: int = 4096,
    cmap: str = 'magma',
    figsize: Tuple[int, int] = (12, 12)
):
    """
    Plot and save SSM visualization.

    Args:
        ssm: Similarity matrix
        output_path: Where to save PNG
        title: Plot title
        duration: Audio duration (for MFCC time axis)
        times: Chunk center times (for text time axis)
        sr: Sample rate (for MFCC)
        hop_length: Hop length (for MFCC)
        cmap: Matplotlib colormap
        figsize: Figure size
    """
    fig, ax = plt.subplots(figsize=figsize)
    img = ax.imshow(ssm, cmap=cmap, origin='lower', aspect='equal', vmin=0, vmax=1)

    cbar = plt.colorbar(img, ax=ax, shrink=0.8)
    cbar.set_label('Similarity', fontsize=12)

    # Compute tick positions and labels
    if times is not None:
        # Text SSM - use provided times
        n = len(times)
        tick_interval = 60  # every minute
        tick_indices, tick_labels = [], []
        for i, t in enumerate(times):
            if int(t) % tick_interval < 15 and (not tick_indices or i - tick_indices[-1] > 2):
                tick_indices.append(i)
                tick_labels.append(f"{int(t//60)}:00")
    elif duration is not None:
        # MFCC SSM - calculate from duration
        n = ssm.shape[0]
        tick_interval = 60 if duration < 600 else 300  # 1min or 5min intervals
        tick_indices, tick_labels = [], []
        for t in range(0, int(duration) + 1, tick_interval):
            frame = int(t * sr / hop_length)
            if frame < n:
                tick_indices.append(frame)
                mins = t // 60
                tick_labels.append(f"{mins}:00")
    else:
        tick_indices, tick_labels = [], []

    ax.set_xticks(tick_indices)
    ax.set_xticklabels(tick_labels, fontsize=10)
    ax.set_yticks(tick_indices)
    ax.set_yticklabels(tick_labels, fontsize=10)

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Time', fontsize=12)
    ax.set_title(title, fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"[plot] Saved: {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate Self-Similarity Matrix visualizations for audio analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Both analyses
  python ssm.py audio.mp3 --transcript audio.srt

  # Acoustic only
  python ssm.py audio.mp3

  # Semantic only
  python ssm.py --transcript audio.srt

  # Custom settings
  python ssm.py audio.mp3 --transcript audio.srt --hop-length 8192 --window-size 45
        """
    )

    parser.add_argument('audio', nargs='?', help='Path to audio file (mp3, wav, etc.)')
    parser.add_argument('--transcript', '-t', help='Path to SRT transcript file')
    parser.add_argument('--output-dir', '-o', default='.', help='Output directory (default: current)')
    parser.add_argument('--name', '-n', help='Base name for output files (default: from audio/transcript)')

    # MFCC options
    parser.add_argument('--hop-length', type=int, default=4096,
                        help='MFCC hop length in samples (default: 4096, larger=faster/coarser)')
    parser.add_argument('--sample-rate', type=int, default=22050,
                        help='Audio sample rate (default: 22050)')

    # Text options
    parser.add_argument('--window-size', type=float, default=30.0,
                        help='Text chunk window in seconds (default: 30)')
    parser.add_argument('--hop-size', type=float, default=15.0,
                        help='Text chunk hop in seconds (default: 15)')
    parser.add_argument('--embedding-model', default='text-embedding-3-small',
                        help='OpenAI embedding model (default: text-embedding-3-small)')

    args = parser.parse_args()

    if not args.audio and not args.transcript:
        parser.error("At least one of audio or --transcript required")

    # Determine base name
    if args.name:
        base_name = args.name
    elif args.audio:
        base_name = Path(args.audio).stem
    else:
        base_name = Path(args.transcript).stem

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # MFCC Analysis
    if args.audio:
        try:
            ssm, duration, sr, hop = compute_mfcc_ssm(
                args.audio,
                sr=args.sample_rate,
                hop_length=args.hop_length
            )
            plot_ssm(
                ssm,
                str(output_dir / f"{base_name}_mfcc_ssm.png"),
                f"{base_name} - MFCC Self-Similarity Matrix",
                duration=duration,
                sr=sr,
                hop_length=hop
            )

            # Save raw data
            np.savez(output_dir / f"{base_name}_mfcc_ssm.npz", ssm=ssm, duration=duration)
            print(f"[mfcc] Data saved: {base_name}_mfcc_ssm.npz")

        except Exception as e:
            print(f"[mfcc] Error: {e}", file=sys.stderr)

    # Text Analysis
    if args.transcript:
        try:
            ssm, times = compute_text_ssm(
                args.transcript,
                model=args.embedding_model,
                window_size=args.window_size,
                hop_size=args.hop_size
            )
            plot_ssm(
                ssm,
                str(output_dir / f"{base_name}_text_ssm.png"),
                f"{base_name} - Text Semantic Self-Similarity Matrix",
                times=times
            )

            # Save raw data
            np.savez(output_dir / f"{base_name}_text_ssm.npz", ssm=ssm, times=np.array(times))
            print(f"[text] Data saved: {base_name}_text_ssm.npz")

        except Exception as e:
            print(f"[text] Error: {e}", file=sys.stderr)

    print("[done]")


if __name__ == "__main__":
    main()
