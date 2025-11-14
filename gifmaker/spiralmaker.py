#!/usr/bin/env python3
"""Spiral pattern generator for hypnotic animations.

Creates spinning spiral patterns with configurable rotation speed, arms, and colors.
Automatically optimizes frame generation using rotational symmetry.
"""
import argparse
import sys
from math import gcd
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from PIL import Image, ImageColor


def parse_colors(spec: Optional[str]) -> List[Tuple[int, int, int]]:
    """Parse color specification into RGB tuples."""
    if not spec:
        return [(0, 0, 0)]
    raw = [p.strip() for p in spec.replace(",", "|").split("|") if p.strip()]
    colors = []
    for token in raw:
        try:
            rgb = ImageColor.getrgb(token)
            colors.append(rgb)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"Invalid color '{token}': {e}")
    if not colors:
        colors = [(0, 0, 0)]
    return colors


def calculate_frame_requirements(dps: float, fps: int, arms: int) -> dict:
    """Calculate unique frames needed for a spiral configuration.

    Uses GCD optimization to minimize unique frames based on rotational symmetry.

    Args:
        dps: Degrees per second (rotation speed)
        fps: Frames per second
        arms: Number of spiral arms

    Returns:
        dict with frame calculations
    """
    degrees_per_frame = dps / fps
    symmetry_angle = 360 / arms

    # Scale to integers to avoid floating point issues
    dps_int = int(dps * 1000)
    fps_int = int(fps * 1000)

    # unique_frames = (360 * fps) / (dps * arms), reduced by GCD
    numerator = 360 * fps_int
    denominator = dps_int * arms

    common = gcd(numerator, denominator)
    unique_frames = numerator // common

    # Calculate naive frames (no optimization)
    naive_frames = int(360 / degrees_per_frame) if degrees_per_frame > 0 else unique_frames

    # Full rotation uses unique frames tiled based on actual reduction achieved
    # If unique_frames < naive_frames, we have optimization and can tile
    # If unique_frames == naive_frames, no optimization - use as-is
    actual_reduction = naive_frames / unique_frames if unique_frames > 0 else 1

    if actual_reduction > 1.01:  # Allow tiny floating point error
        # We have optimization - unique frames are for one symmetry cycle
        full_rotation_frames = unique_frames * arms
    else:
        # No optimization - unique frames already cover full rotation
        full_rotation_frames = unique_frames

    return {
        'dps': dps,
        'fps': fps,
        'arms': arms,
        'degrees_per_frame': degrees_per_frame,
        'symmetry_angle': symmetry_angle,
        'unique_frames': unique_frames,
        'full_rotation_frames': full_rotation_frames,
        'duration': full_rotation_frames / fps,
        'reduction_factor': actual_reduction,
    }


def find_nearby_clean_dps(target_dps: float, fps: int, arms: int, max_frames: int = 100) -> List[dict]:
    """Find nearby DPS values that produce reasonable frame counts.

    Args:
        target_dps: Desired degrees per second
        fps: Frames per second
        arms: Number of arms
        max_frames: Maximum acceptable unique frame count

    Returns:
        List of candidate configurations sorted by proximity to target DPS
    """
    candidates = []

    # Search range: ±20% of target
    search_range = int(target_dps * 0.2)
    min_dps = max(1, target_dps - search_range)
    max_dps = target_dps + search_range

    # Try integer and half-integer DPS values
    for dps_tenth in range(int(min_dps * 10), int(max_dps * 10) + 1):
        dps = dps_tenth / 10.0
        result = calculate_frame_requirements(dps, fps, arms)

        if result['unique_frames'] <= max_frames:
            result['error'] = abs(dps - target_dps)
            candidates.append(result)

    # Sort by error (closest to target DPS first)
    candidates.sort(key=lambda x: x['error'])

    return candidates[:10]  # Return top 10


def generate_spiral_frame(
    size: int,
    num_arms: int,
    rotation_degrees: float,
    tightness: float,
    colors: List[Tuple[int, int, int]],
    background: Tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """Generate a single spiral frame.

    Parameters:
        size: Resolution (square image)
        num_arms: Number of spiral arms
        rotation_degrees: Rotation angle in degrees
        tightness: Spiral tightness (rotations from center to edge)
        colors: List of RGB tuples for gradient
        background: RGB background color

    Returns:
        PIL Image (RGB mode)
    """
    # Create coordinate grid
    x = np.linspace(-1, 1, size)
    y = np.linspace(-1, 1, size)
    X, Y = np.meshgrid(x, y)

    # Polar coordinates
    theta = np.arctan2(Y, X)
    r = np.sqrt(X**2 + Y**2)

    # Spiral pattern
    # Phase only rotates the angular component to preserve rotational symmetry
    phase_radians = np.radians(rotation_degrees)
    spiral_value = np.sin(num_arms * (theta + phase_radians) + tightness * np.pi * r)

    # Normalize to [0, 1]
    spiral_normalized = (spiral_value - spiral_value.min()) / (spiral_value.max() - spiral_value.min())

    # Create output image
    if len(colors) == 1:
        # Single color: use as solid with spiral as brightness
        color = colors[0]
        spiral_rgb = (spiral_normalized * 255).astype(np.uint8)
        img_array = np.zeros((size, size, 3), dtype=np.uint8)
        img_array[:, :, 0] = (spiral_rgb * color[0] // 255)
        img_array[:, :, 1] = (spiral_rgb * color[1] // 255)
        img_array[:, :, 2] = (spiral_rgb * color[2] // 255)
    else:
        # Multiple colors: interpolate gradient
        color_idx = spiral_normalized * (len(colors) - 1)
        idx_low = np.floor(color_idx).astype(int)
        idx_high = np.ceil(color_idx).astype(int)
        blend = color_idx - idx_low

        img_array = np.zeros((size, size, 3), dtype=np.uint8)
        for i in range(3):  # RGB channels
            color_low = np.array([colors[j][i] for j in idx_low.flat]).reshape(size, size)
            color_high = np.array([colors[j][i] for j in idx_high.flat]).reshape(size, size)
            img_array[:, :, i] = ((1 - blend) * color_low + blend * color_high).astype(np.uint8)

    # Apply background (mix with black/background in dark areas)
    # For now, just return the spiral directly
    return Image.fromarray(img_array, mode='RGB')


def generate_unique_frames(
    size: int,
    arms: int,
    tightness: float,
    unique_frames: int,
    colors: List[Tuple[int, int, int]],
    background: Tuple[int, int, int],
    full_rotation_frames: int,
) -> List[Image.Image]:
    """Generate the minimal set of unique spiral frames.

    Returns:
        List of PIL Images (unique frames only)
    """
    frames = []

    print(f"[info] Generating {unique_frames} unique frames at {size}x{size}...", file=sys.stderr)

    # Calculate how much rotation these unique frames should cover
    # The unique frames represent the minimal repeating pattern
    # Each frame advances by degrees_per_frame
    # So unique_frames covers: unique_frames * degrees_per_frame total degrees
    # But we need to know degrees_per_frame from the caller!

    # For now: if optimizing (unique < full), frames cover one symmetry cycle
    # If not optimizing (unique == full), frames cover full 360°
    # BUT: we need to calculate the actual angular range from frame count

    if unique_frames < full_rotation_frames:
        # We're optimizing - frames represent minimal cycle
        # The angle covered is determined by the GCD math
        # unique_frames × (dps/fps) = total rotation these frames cover
        # We can't access dps/fps here, so we need it passed in!
        # For now, use the ratio: unique/full × 360
        total_rotation = (unique_frames / full_rotation_frames) * 360
    else:
        # No optimization: full 360°
        total_rotation = 360

    for i in range(unique_frames):
        # Calculate rotation angle for this frame
        rotation = (i / unique_frames) * total_rotation

        frame = generate_spiral_frame(
            size=size,
            num_arms=arms,
            rotation_degrees=rotation,
            tightness=tightness,
            colors=colors,
            background=background,
        )

        frames.append(frame)

        if (i + 1) % 10 == 0 or i == unique_frames - 1:
            print(f"[progress] {i + 1}/{unique_frames} unique frames", file=sys.stderr)

    return frames


def tile_frames(unique_frames: List[Image.Image], arms: int) -> List[Image.Image]:
    """Tile unique frames to create a full 360° rotation.

    Maps each frame in the full rotation to the corresponding unique frame
    based on rotational symmetry.

    Args:
        unique_frames: The minimal unique frame set
        arms: Number of arms (rotational symmetry fold)

    Returns:
        Full frame sequence for 360° rotation
    """
    # Total frames for full rotation
    total_frames = len(unique_frames) * arms

    # Map each output frame to the correct unique frame
    output = []
    for i in range(total_frames):
        # Which unique frame does this map to?
        unique_idx = i % len(unique_frames)
        output.append(unique_frames[unique_idx])

    return output


def save_frames_as_png(frames: List[Image.Image], output_dir: Path) -> None:
    """Save frames as individual PNG files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for frame_idx, frame in enumerate(frames):
        frame_path = output_dir / f"frame_{frame_idx:04d}.png"
        frame.save(frame_path)

    print(f"[ok] Wrote {len(frames)} frames to {output_dir}", file=sys.stderr)


def save_frames_as_gif(frames: List[Image.Image], output_path: Path, ms_per_frame: int) -> None:
    """Save frames as an animated GIF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not frames:
        raise SystemExit("No frames to save")

    # Quantize per-frame using adaptive palette (same as gifmaker)
    print(f"[info] Encoding GIF with {len(frames)} frames...", file=sys.stderr)
    pal_frames = [
        frm.convert("P", palette=Image.ADAPTIVE, colors=256, dither=Image.Dither.NONE)
        for frm in frames
    ]

    first, rest = pal_frames[0], pal_frames[1:]

    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        duration=ms_per_frame,
        loop=0,
        disposal=2,
    )

    print(f"[ok] Wrote {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Generate spinning spiral patterns with automatic frame optimization"
    )

    # Output (mutually exclusive)
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument(
        "--output",
        type=str,
        help="Output GIF file path (e.g., spiral.gif)",
    )
    output_group.add_argument(
        "--output-as-png",
        type=str,
        help="Output directory for PNG frames (e.g., spiral_frames/)",
    )

    # Primary parameters (mutually exclusive groups)
    # Either specify high-level (dps/fps) or low-level (ms/degrees-per-frame)
    speed_group = parser.add_mutually_exclusive_group(required=True)
    speed_group.add_argument(
        "--dps",
        type=float,
        help="Degrees per second (rotation speed) - high-level control",
    )
    speed_group.add_argument(
        "--degrees-per-frame",
        type=float,
        help="Degrees rotated per frame - low-level control (use with --ms)",
    )

    timing_group = parser.add_mutually_exclusive_group()
    timing_group.add_argument(
        "--fps",
        type=int,
        help="Frames per second (default: 30 if using --dps)",
    )
    timing_group.add_argument(
        "--ms",
        type=int,
        help="Milliseconds per frame (low-level control, must be multiple of 10)",
    )

    parser.add_argument(
        "--arms",
        type=int,
        default=5,
        help="Number of spiral arms/spurs (default: 5)",
    )

    # Spiral appearance
    parser.add_argument(
        "--tightness",
        type=float,
        default=5.0,
        help="Spiral tightness - rotations from center to edge (default: 5.0)",
    )

    parser.add_argument(
        "--size",
        type=int,
        default=1000,
        help="Resolution for square output (default: 1000)",
    )

    # Colors
    parser.add_argument(
        "--colors",
        type=str,
        default="magenta|cyan",
        help="Pipe or comma-separated colors (default: magenta|cyan)",
    )

    parser.add_argument(
        "--background",
        type=str,
        default="black",
        help="Background color (default: black)",
    )

    # Options
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable frame optimization (generate full 360° without symmetry reduction)",
    )

    parser.add_argument(
        "--max-unique-frames",
        type=int,
        default=100,
        help="Maximum unique frames before suggesting alternatives (default: 100)",
    )

    args = parser.parse_args()

    # Validate and normalize to degrees_per_frame + ms_per_frame
    if args.degrees_per_frame is not None:
        # Low-level mode: degrees-per-frame + ms
        if args.ms is None:
            raise SystemExit("--degrees-per-frame requires --ms")
        if args.degrees_per_frame <= 0:
            raise SystemExit("--degrees-per-frame must be > 0")
        if args.ms <= 0:
            raise SystemExit("--ms must be > 0")
        if args.ms % 10 != 0:
            print(f"[warn] --ms should be multiple of 10 (GIF spec limitation)", file=sys.stderr)

        degrees_per_frame = args.degrees_per_frame
        ms_per_frame = args.ms
        fps = 1000 / ms_per_frame
        dps = degrees_per_frame * fps

    else:
        # High-level mode: dps + fps
        if args.dps is None:
            raise SystemExit("Must specify either --dps or --degrees-per-frame")
        if args.dps <= 0:
            raise SystemExit("--dps must be > 0")

        fps = args.fps if args.fps is not None else 30
        if fps <= 0:
            raise SystemExit("--fps must be > 0")

        dps = args.dps
        degrees_per_frame = dps / fps
        ms_per_frame_raw = 1000 / fps

        # GIF quantizes to 10ms increments
        ms_per_frame = int(round(ms_per_frame_raw / 10) * 10)

        # Warn if quantization affects timing
        if ms_per_frame != int(ms_per_frame_raw):
            actual_fps = 1000 / ms_per_frame
            actual_dps = degrees_per_frame * actual_fps
            print(f"[warn] GIF quantizes to 10ms: {ms_per_frame_raw:.1f}ms → {ms_per_frame}ms", file=sys.stderr)
            print(f"[warn] Actual playback: {actual_fps:.1f}fps = {actual_dps:.1f}°/s (requested: {dps:.1f}°/s)", file=sys.stderr)
        else:
            ms_per_frame = int(ms_per_frame_raw)

    if args.arms <= 0:
        raise SystemExit("--arms must be > 0")
    if args.tightness <= 0:
        raise SystemExit("--tightness must be > 0")
    if args.size <= 0:
        raise SystemExit("--size must be > 0")

    # Parse colors
    try:
        colors = parse_colors(args.colors)
        background = parse_colors(args.background)[0]
    except argparse.ArgumentTypeError as e:
        raise SystemExit(f"Error: {e}")

    # Calculate frame requirements
    calc = calculate_frame_requirements(dps, int(fps), args.arms)

    print(f"[info] Configuration: {dps:.1f}°/s, {fps:.1f}fps ({ms_per_frame}ms/frame), {args.arms} arms", file=sys.stderr)
    print(f"[info] Degrees per frame: {degrees_per_frame:.4f}°", file=sys.stderr)
    print(f"[info] Symmetry angle: {calc['symmetry_angle']:.2f}°", file=sys.stderr)

    # Check if we need to suggest alternatives
    if calc['unique_frames'] > args.max_unique_frames:
        print(f"\n⚠️  WARNING: Configuration requires {calc['unique_frames']} unique frames!", file=sys.stderr)
        print(f"[info] Searching for nearby DPS values with fewer frames...", file=sys.stderr)

        alternatives = find_nearby_clean_dps(dps, int(fps), args.arms, args.max_unique_frames)

        if alternatives:
            print(f"\n[suggestion] Consider these alternative DPS values:", file=sys.stderr)
            for i, alt in enumerate(alternatives[:5], 1):
                print(f"  {i}. {alt['dps']:6.1f}°/s → {alt['unique_frames']:3d} unique frames "
                      f"(error: {alt['error']:+5.1f}°/s, {alt['reduction_factor']:.1f}x reduction)",
                      file=sys.stderr)

            # Use the closest alternative automatically
            best = alternatives[0]
            print(f"\n[info] Auto-selecting closest: {best['dps']}°/s ({best['unique_frames']} unique frames)",
                  file=sys.stderr)
            calc = best
        else:
            print(f"[info] No suitable alternatives found within range. Proceeding with {calc['unique_frames']} frames...",
                  file=sys.stderr)

    print(f"\n[info] Unique frames to generate: {calc['unique_frames']}", file=sys.stderr)
    print(f"[info] Full rotation: {calc['full_rotation_frames']} frames ({calc['duration']:.2f}s)", file=sys.stderr)
    print(f"[info] Optimization: {calc['reduction_factor']:.1f}x reduction via symmetry", file=sys.stderr)

    # Generate unique frames
    unique_frames = generate_unique_frames(
        size=args.size,
        arms=args.arms,
        tightness=args.tightness,
        unique_frames=calc['unique_frames'],
        colors=colors,
        background=background,
        full_rotation_frames=calc['full_rotation_frames'],
    )

    # Determine output frames
    if args.output:
        # For GIF output, use unique frames only - browser will loop naturally
        output_frames = unique_frames
        if calc['reduction_factor'] > 1.0:
            print(f"[info] Outputting {len(output_frames)} unique frames (loops {args.arms}x for full rotation)", file=sys.stderr)
        else:
            print(f"[info] Outputting {len(output_frames)} frames for full 360° rotation", file=sys.stderr)
    else:
        # For PNG output, only save unique frames (storage optimization)
        if args.no_optimize:
            output_frames = tile_frames(unique_frames, args.arms)
            print(f"[info] Outputting {len(output_frames)} frames (full 360° rotation)", file=sys.stderr)
        else:
            output_frames = unique_frames
            print(f"[info] Outputting {len(output_frames)} unique frames only (use --no-optimize for full rotation)", file=sys.stderr)

    # Save output (ms_per_frame already calculated above)
    if args.output:
        output_path = Path(args.output)
        save_frames_as_gif(output_frames, output_path, ms_per_frame)
    else:
        output_dir = Path(args.output_as_png)
        save_frames_as_png(output_frames, output_dir)


if __name__ == "__main__":
    main()
