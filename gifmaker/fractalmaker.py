#!/usr/bin/env python3
"""Fractal pattern generator for hypnotic animations.

Creates animated fractals with N-fold rotational symmetry,
configurable colors, and smooth looping animations.

The fractal is based on a polar coordinate transformation that creates
kaleidoscopic patterns with guaranteed N-fold symmetry.
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
        return [(0, 0, 0), (255, 0, 255)]  # Default: black to magenta
    raw = [p.strip() for p in spec.replace(",", "|").split("|") if p.strip()]
    colors = []
    for token in raw:
        try:
            rgb = ImageColor.getrgb(token)
            colors.append(rgb)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"Invalid color '{token}': {e}")
    if not colors:
        colors = [(0, 0, 0), (255, 0, 255)]
    return colors


def calculate_frame_requirements(cps: float, fps: int, symmetry: int) -> dict:
    """Calculate unique frames needed for a fractal configuration.

    Uses GCD optimization to minimize unique frames based on rotational symmetry.

    Args:
        cps: Cycles per second (how fast the fractal animates through one full cycle)
        fps: Frames per second
        symmetry: N-fold symmetry

    Returns:
        dict with frame calculations
    """
    # One "cycle" is a full animation loop (pattern returns to start)
    # Full cycle frames = fps / cps
    full_cycle_frames = int(round(fps / cps)) if cps > 0 else 100

    # With N-fold symmetry, the pattern repeats N times visually
    # But we generate all frames for smooth animation (no tiling needed for this fractal type)
    # The symmetry is built into each frame, not across frames
    unique_frames = full_cycle_frames

    degrees_per_frame = 360.0 / full_cycle_frames if full_cycle_frames > 0 else 1
    symmetry_angle = 360 / symmetry

    return {
        'cps': cps,
        'fps': fps,
        'symmetry': symmetry,
        'degrees_per_frame': degrees_per_frame,
        'symmetry_angle': symmetry_angle,
        'unique_frames': unique_frames,
        'full_cycle_frames': full_cycle_frames,
        'duration': full_cycle_frames / fps if fps > 0 else 1,
        'reduction_factor': 1.0,  # Each frame is unique in this design
    }


def find_nearby_clean_cps(target_cps: float, fps: int, symmetry: int, max_frames: int = 100) -> List[dict]:
    """Find nearby CPS values that produce reasonable frame counts.

    Args:
        target_cps: Desired cycles per second
        fps: Frames per second
        symmetry: N-fold symmetry
        max_frames: Maximum acceptable unique frame count

    Returns:
        List of candidate configurations sorted by proximity to target CPS
    """
    candidates = []

    # Search for CPS values that give clean frame counts
    # fps / cps = frames, so cps = fps / frames
    for frames in range(10, max_frames + 1):
        cps = fps / frames
        result = calculate_frame_requirements(cps, fps, symmetry)

        if result['unique_frames'] <= max_frames:
            result['error'] = abs(cps - target_cps)
            candidates.append(result)

    # Sort by error (closest to target CPS first)
    candidates.sort(key=lambda x: x['error'])

    return candidates[:10]


def generate_fractal_frame(
    size: int,
    symmetry: int,
    phase: float,
    colors: List[Tuple[int, int, int]],
    complexity: float = 3.0,
    zoom: float = 1.0,
    layers: int = 5,
    color_shift: float = 0.0,
) -> Image.Image:
    """Generate a single kaleidoscopic fractal frame with N-fold symmetry.

    This creates a mesmerizing pattern by:
    1. Using polar coordinates
    2. Applying N-fold symmetry by wrapping theta
    3. Layering multiple sinusoidal patterns
    4. Animating via phase rotation

    Parameters:
        size: Resolution (square image)
        symmetry: N-fold rotational symmetry
        phase: Animation phase (0.0 - 1.0 for full cycle)
        colors: List of RGB tuples for gradient
        complexity: Pattern complexity (higher = more detail)
        zoom: Zoom level (affects pattern scale)
        layers: Number of overlaid pattern layers
        color_shift: Phase shift for color cycling (0.0 - 1.0)

    Returns:
        PIL Image (RGB mode)
    """
    # Create coordinate grid centered at origin
    half = size // 2
    y, x = np.ogrid[-half:size-half, -half:size-half]
    x = x.astype(np.float64) / half * zoom
    y = y.astype(np.float64) / half * zoom

    # Convert to polar coordinates
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)

    # Apply N-fold symmetry by wrapping theta
    # This creates the kaleidoscope effect
    theta_sym = theta * symmetry

    # Animation phase (0-2pi for full rotation)
    anim_phase = phase * 2 * np.pi

    # Build layered fractal pattern
    # All animated components must complete INTEGER cycles when phase goes 0 -> 1
    # This ensures perfect looping (frame 0 == frame N mathematically)
    pattern = np.zeros_like(r)

    for layer in range(layers):
        # Each layer has different spatial frequency but same temporal frequency
        freq = complexity * (layer + 1) * 0.7

        # Static phase offset per layer (doesn't affect looping)
        layer_offset = layer * 2 * np.pi / layers

        # Radial component - rings that pulse inward (toward center)
        # +anim_phase means pattern shifts toward center as time progresses
        # Completes exactly 1 cycle as anim_phase goes 0 -> 2pi
        radial = np.sin(r * freq * np.pi + anim_phase + layer_offset)

        # Angular component - creates the N-fold symmetric spokes
        # Completes exactly 1 cycle (not 0.5!) as anim_phase goes 0 -> 2pi
        angular = np.cos(theta_sym + anim_phase + layer_offset)

        # Combine with varying weights per layer
        weight = 1.0 / (layer + 1)
        pattern += weight * (radial * 0.6 + angular * 0.4)

    # Add a secondary swirling pattern for visual interest
    # +anim_phase makes swirl move inward, *2 completes 2 cycles for perfect looping
    swirl = np.sin(theta_sym + r * complexity * 2 + anim_phase * 2)
    pattern += swirl * 0.3

    # Use fixed normalization range based on theoretical bounds
    # Since we're summing weighted sin/cos, the range is bounded
    # This ensures consistent normalization across all frames for perfect looping
    max_possible = sum(1.0 / (layer + 1) for layer in range(layers)) + 0.3
    pattern = (pattern + max_possible) / (2 * max_possible)
    pattern = np.clip(pattern, 0, 1)

    # Apply color shift for flowing colors
    pattern = (pattern + color_shift) % 1.0

    # Map to colors
    if len(colors) == 1:
        color = colors[0]
        intensity = (pattern * 255).astype(np.uint8)
        img_array = np.zeros((size, size, 3), dtype=np.uint8)
        img_array[:, :, 0] = (intensity * color[0] // 255)
        img_array[:, :, 1] = (intensity * color[1] // 255)
        img_array[:, :, 2] = (intensity * color[2] // 255)
    else:
        # Multiple colors: interpolate gradient
        color_idx = pattern * (len(colors) - 1)
        idx_low = np.floor(color_idx).astype(int)
        idx_high = np.ceil(color_idx).astype(int)

        # Clamp indices
        idx_low = np.clip(idx_low, 0, len(colors) - 1)
        idx_high = np.clip(idx_high, 0, len(colors) - 1)

        blend = color_idx - np.floor(color_idx)

        img_array = np.zeros((size, size, 3), dtype=np.uint8)
        for i in range(3):  # RGB channels
            color_low = np.array([colors[j][i] for j in idx_low.flat]).reshape(size, size)
            color_high = np.array([colors[j][i] for j in idx_high.flat]).reshape(size, size)
            img_array[:, :, i] = ((1 - blend) * color_low + blend * color_high).astype(np.uint8)

    return Image.fromarray(img_array, mode='RGB')


def generate_unique_frames(
    size: int,
    symmetry: int,
    unique_frames: int,
    colors: List[Tuple[int, int, int]],
    complexity: float,
    zoom: float,
    layers: int,
    color_cycle: bool,
) -> List[Image.Image]:
    """Generate all frames for one complete animation cycle.

    Args:
        size: Image resolution
        symmetry: N-fold symmetry
        unique_frames: Number of frames to generate
        colors: Color gradient
        complexity: Pattern complexity
        zoom: Zoom level
        layers: Number of pattern layers
        color_cycle: Whether to cycle colors through the animation

    Returns:
        List of PIL Images
    """
    frames = []

    print(f"[info] Generating {unique_frames} frames at {size}x{size}...", file=sys.stderr)

    for i in range(unique_frames):
        # Animation phase (0 to 1 for full cycle)
        phase = i / unique_frames

        # Color shift for flowing color effect
        color_shift = phase if color_cycle else 0.0

        frame = generate_fractal_frame(
            size=size,
            symmetry=symmetry,
            phase=phase,
            colors=colors,
            complexity=complexity,
            zoom=zoom,
            layers=layers,
            color_shift=color_shift,
        )

        frames.append(frame)

        if (i + 1) % 10 == 0 or i == unique_frames - 1:
            print(f"[progress] {i + 1}/{unique_frames} frames", file=sys.stderr)

    return frames


def tile_frames(unique_frames: List[Image.Image], symmetry: int) -> List[Image.Image]:
    """Tile unique frames to create a full cycle.

    Maps each frame in the full cycle to the corresponding unique frame
    based on rotational symmetry.

    Args:
        unique_frames: The minimal unique frame set
        symmetry: N-fold symmetry

    Returns:
        Full frame sequence for one complete cycle
    """
    total_frames = len(unique_frames) * symmetry

    output = []
    for i in range(total_frames):
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
        description="Generate animated kaleidoscopic fractals with N-fold symmetry"
    )

    # Output (mutually exclusive)
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument(
        "--output",
        type=str,
        help="Output GIF file path (e.g., fractal.gif)",
    )
    output_group.add_argument(
        "--output-as-png",
        type=str,
        help="Output directory for PNG frames (e.g., fractal_frames/)",
    )

    # Speed control (mutually exclusive groups)
    speed_group = parser.add_mutually_exclusive_group(required=True)
    speed_group.add_argument(
        "--cps",
        type=float,
        help="Cycles per second (animation speed) - high-level control",
    )
    speed_group.add_argument(
        "--degrees-per-frame",
        type=float,
        help="Degrees of c rotation per frame - low-level control (use with --ms)",
    )

    timing_group = parser.add_mutually_exclusive_group()
    timing_group.add_argument(
        "--fps",
        type=int,
        help="Frames per second (default: 30 if using --cps)",
    )
    timing_group.add_argument(
        "--ms",
        type=int,
        help="Milliseconds per frame (low-level control, must be multiple of 10)",
    )

    # Fractal parameters
    parser.add_argument(
        "--symmetry",
        type=int,
        default=5,
        help="N-fold rotational symmetry (default: 5)",
    )

    parser.add_argument(
        "--complexity",
        type=float,
        default=3.0,
        help="Pattern complexity - higher values create more detailed patterns (default: 3.0)",
    )

    parser.add_argument(
        "--layers",
        type=int,
        default=5,
        help="Number of overlaid pattern layers (default: 5)",
    )

    parser.add_argument(
        "--zoom",
        type=float,
        default=1.5,
        help="Zoom level - smaller values zoom in (default: 1.5)",
    )

    parser.add_argument(
        "--size",
        type=int,
        default=800,
        help="Resolution for square output (default: 800)",
    )

    # Colors
    parser.add_argument(
        "--colors",
        type=str,
        default="black|purple|magenta|cyan|white",
        help="Pipe or comma-separated colors for gradient (default: black|purple|magenta|cyan|white)",
    )

    parser.add_argument(
        "--color-cycle",
        action="store_true",
        help="Cycle colors through the animation (creates flowing color effect)",
    )

    # Options
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable frame optimization (generate full cycle without symmetry reduction)",
    )

    parser.add_argument(
        "--max-unique-frames",
        type=int,
        default=100,
        help="Maximum unique frames before suggesting alternatives (default: 100)",
    )

    args = parser.parse_args()

    # Validate and normalize timing
    if args.degrees_per_frame is not None:
        # Low-level mode
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
        cps = (degrees_per_frame * fps) / 360

    else:
        # High-level mode
        if args.cps is None:
            raise SystemExit("Must specify either --cps or --degrees-per-frame")
        if args.cps <= 0:
            raise SystemExit("--cps must be > 0")

        fps = args.fps if args.fps is not None else 30
        if fps <= 0:
            raise SystemExit("--fps must be > 0")

        cps = args.cps
        degrees_per_frame = (cps * 360) / fps
        ms_per_frame_raw = 1000 / fps

        # GIF quantizes to 10ms increments
        ms_per_frame = int(round(ms_per_frame_raw / 10) * 10)

        if ms_per_frame != int(ms_per_frame_raw):
            actual_fps = 1000 / ms_per_frame
            actual_cps = (degrees_per_frame * actual_fps) / 360
            print(f"[warn] GIF quantizes to 10ms: {ms_per_frame_raw:.1f}ms -> {ms_per_frame}ms", file=sys.stderr)
            print(f"[warn] Actual playback: {actual_fps:.1f}fps = {actual_cps:.2f} cps (requested: {cps:.2f} cps)", file=sys.stderr)
        else:
            ms_per_frame = int(ms_per_frame_raw)

    # Validate other params
    if args.symmetry <= 0:
        raise SystemExit("--symmetry must be > 0")
    if args.size <= 0:
        raise SystemExit("--size must be > 0")
    if args.complexity <= 0:
        raise SystemExit("--complexity must be > 0")
    if args.layers <= 0:
        raise SystemExit("--layers must be > 0")
    if args.zoom <= 0:
        raise SystemExit("--zoom must be > 0")

    # Parse colors
    try:
        colors = parse_colors(args.colors)
    except argparse.ArgumentTypeError as e:
        raise SystemExit(f"Error: {e}")

    # Calculate frame requirements
    calc = calculate_frame_requirements(cps, int(fps), args.symmetry)

    print(f"[info] Configuration: {cps:.2f} cps, {fps:.1f}fps ({ms_per_frame}ms/frame), {args.symmetry}-fold symmetry", file=sys.stderr)
    print(f"[info] Complexity: {args.complexity}, Layers: {args.layers}, Zoom: {args.zoom}", file=sys.stderr)

    # Check if we need to suggest alternatives
    if calc['unique_frames'] > args.max_unique_frames:
        print(f"\n[warn] Configuration requires {calc['unique_frames']} frames!", file=sys.stderr)
        print(f"[info] Searching for nearby CPS values with fewer frames...", file=sys.stderr)

        alternatives = find_nearby_clean_cps(cps, int(fps), args.symmetry, args.max_unique_frames)

        if alternatives:
            print(f"\n[suggestion] Consider these alternative CPS values:", file=sys.stderr)
            for i, alt in enumerate(alternatives[:5], 1):
                print(f"  {i}. {alt['cps']:6.2f} cps -> {alt['unique_frames']:3d} frames "
                      f"(error: {alt['error']:+5.2f} cps)",
                      file=sys.stderr)

            best = alternatives[0]
            print(f"\n[info] Auto-selecting closest: {best['cps']:.2f} cps ({best['unique_frames']} frames)",
                  file=sys.stderr)
            calc = best
        else:
            print(f"[info] No suitable alternatives found. Proceeding with {calc['unique_frames']} frames...",
                  file=sys.stderr)

    print(f"\n[info] Frames to generate: {calc['unique_frames']}", file=sys.stderr)
    print(f"[info] Full cycle duration: {calc['duration']:.2f}s", file=sys.stderr)

    # Generate frames
    frames = generate_unique_frames(
        size=args.size,
        symmetry=args.symmetry,
        unique_frames=calc['unique_frames'],
        colors=colors,
        complexity=args.complexity,
        zoom=args.zoom,
        layers=args.layers,
        color_cycle=args.color_cycle,
    )

    # Save output
    if args.output:
        output_path = Path(args.output)
        print(f"[info] Outputting {len(frames)} frames", file=sys.stderr)
        save_frames_as_gif(frames, output_path, ms_per_frame)
    else:
        output_dir = Path(args.output_as_png)
        print(f"[info] Outputting {len(frames)} frames", file=sys.stderr)
        save_frames_as_png(frames, output_dir)


if __name__ == "__main__":
    main()
