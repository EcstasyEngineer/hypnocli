# Spiralmaker Documentation

`spiralmaker.py` generates hypnotic spinning spiral patterns with automatic frame optimization using rotational symmetry.

## Quick Start

```bash
# Basic usage - high-level control
python3 spiralmaker.py --output spiral.gif --dps 108 --arms 5 --colors "purple|magenta|pink|cyan|blue"

# Low-level control (precise GIF timing)
python3 spiralmaker.py --output spiral.gif --degrees-per-frame 3.6 --ms 30 --arms 5 --colors "purple|magenta|pink|cyan|blue"

# Export as PNG frames
python3 spiralmaker.py --output-as-png frames/ --dps 108 --arms 5 --colors "purple|magenta|pink|cyan|blue"
```

## Core Concepts

### Rotational Symmetry Optimization

The key innovation in spiralmaker is **automatic frame reduction** via rotational symmetry. A spiral with N arms looks identical when rotated by 360°/N degrees.

**Example:** 5-arm spiral
- Symmetry angle: 360° ÷ 5 = 72°
- Rotating 72° produces the same visual pattern
- If your configuration needs 100 frames for 360°, you might only need 20 unique frames that loop 5 times!

**Maximum optimizations found:**
- 9 arms: **9x reduction** (e.g., 9 frames instead of 81)
- 8 arms: **8x reduction**
- 6 arms: **6x reduction**
- 5 arms: **5x reduction** (most tested)

### GIF Timing Limitations

GIF files only support frame delays in **10ms increments**. This affects timing precision:

- Requesting 30fps (33.33ms/frame) → rounds to 30ms (33.3fps actual)
- Requesting 25fps (40ms/frame) → exact! (40ms)
- Requesting 60fps (16.67ms/frame) → rounds to 20ms (50fps actual)

The tool warns when quantization affects your requested speed and shows the actual playback rate.

## Parameters

### Output (Required, Mutually Exclusive)

**`--output <file.gif>`**
Output as animated GIF file.

**`--output-as-png <directory>`**
Output as individual PNG frames (frame_0000.png, frame_0001.png, etc.)

### Speed Control (Required, Mutually Exclusive)

#### High-Level (Recommended)

**`--dps <degrees>`**
Degrees per second - how fast the spiral rotates.
- Example: `--dps 108` = one full rotation every 3.33 seconds
- Example: `--dps 360` = one full rotation per second

**`--fps <number>`**
Frames per second (default: 30).
- Common values: 20, 25, 30, 50, 100
- Will be quantized to nearest 10ms increment

#### Low-Level (Precise Control)

**`--degrees-per-frame <degrees>`**
Exact rotation per frame. Useful when you need precise control over the pattern.
- Must be used with `--ms`
- Example: `--degrees-per-frame 12` = 12° rotation per frame

**`--ms <milliseconds>`**
Milliseconds per frame (GIF frame delay).
- Must be multiple of 10 (GIF spec requirement)
- Must be used with `--degrees-per-frame`
- Example: `--ms 30` = 33.3fps

### Spiral Appearance

**`--arms <number>`** (default: 5)
Number of spiral arms/spurs.
- More arms = tighter symmetry = better optimization potential
- Range: 1-9 tested (higher values work too)
- Sweet spot for optimization: 5-9 arms

**`--tightness <number>`** (default: 5.0)
Spiral tightness - number of rotations from center to edge.
- Higher values = tighter, more wound spiral
- Lower values = looser, more open spiral
- Typical range: 3.0 - 10.0

**`--size <pixels>`** (default: 1000)
Output resolution (square images).
- Small preview: 200-400
- Standard: 800-1000
- High quality: 1500-2000

### Colors

**`--colors <spec>`** (default: "magenta|cyan")
Spiral colors as pipe or comma-separated list.
- Supports color names: `red`, `blue`, `magenta`, `cyan`, `purple`, etc.
- Supports hex codes: `#FF00FF`, `#00FFFF`
- Multiple colors create gradient: `purple|magenta|pink|cyan|blue`

**`--background <color>`** (default: "black")
Background color (single color only).

**Recommended Palettes:**
- `purple|magenta|pink|cyan|blue` - **Cosmic Hypnosis** (vibrant, mesmerizing)
- `magenta|cyan` - Classic high contrast
- `red|orange|yellow` - Warm fire
- `blue|cyan|white` - Cool ice
- `#FF1493|#9400D3|#4B0082` - Deep purple gradient

### Optimization Controls

**`--max-unique-frames <number>`** (default: 100)
Threshold for triggering optimization suggestions.
- If configuration requires more than this many unique frames, tool suggests alternatives
- Lower values = more aggressive suggestions
- Set to 50 for strict optimization

**`--no-optimize`**
Disable frame optimization (for PNG output only).
- Forces output of full 360° rotation frames
- GIF output always uses optimization when possible

## Optimization Guide

### Finding Optimal Configurations

The tool automatically suggests nearby DPS values when your configuration would require excessive frames.

**Manual optimization:** Choose DPS values where `(360 × fps) / (dps × arms)` is a small integer.

**Example calculations:**
```
5 arms @ 30fps:
  dps=108 → 20 unique frames (5x optimization) ✓
  dps=120 → 18 unique frames (5x optimization) ✓
  dps=360 → 6 unique frames  (5x optimization) ✓
  dps=112.5 → 96 frames (no optimization) ✗

6 arms @ 30fps:
  dps=90  → 20 unique frames (6x optimization) ✓
  dps=120 → 15 unique frames (6x optimization) ✓
  dps=180 → 10 unique frames (6x optimization) ✓
```

### Best Practices

1. **Use more arms for better optimization**
   - 5+ arms typically achieve 5x or better reduction
   - 9 arms can achieve 9x reduction!

2. **Choose FPS that divides evenly into 1000ms**
   - 20fps (50ms) - exact
   - 25fps (40ms) - exact
   - 50fps (20ms) - exact
   - 30fps (33.3ms → 30ms) - quantized
   - 60fps (16.7ms → 20ms) - quantized

3. **Let the tool suggest optimizations**
   - Use `--max-unique-frames 50` for aggressive optimization
   - Tool will auto-select nearest clean DPS value

4. **Low-level mode for exact control**
   - Use `--degrees-per-frame` + `--ms` when you need precise timing
   - Bypasses FPS quantization warnings
   - Example: `--degrees-per-frame 12 --ms 30 --arms 5`

## Examples

### Example 1: Smooth Hypnotic Spiral (Optimized)
```bash
python3 spiralmaker.py \
  --output hypnotic.gif \
  --dps 108 \
  --fps 30 \
  --arms 5 \
  --size 420 \
  --colors "purple|magenta|pink|cyan|blue" \
  --tightness 7
```
**Result:** 20 unique frames, 5x optimization, 3.33s rotation, ~120°/s actual playback

### Example 2: Fast Spin (Optimized)
```bash
python3 spiralmaker.py \
  --output fast.gif \
  --dps 360 \
  --arms 6 \
  --colors "red|orange|yellow"
```
**Result:** Optimized 6-arm spiral, 1 second rotation

### Example 3: Precise Low-Level Control
```bash
python3 spiralmaker.py \
  --output precise.gif \
  --degrees-per-frame 3.6 \
  --ms 30 \
  --arms 5 \
  --colors "cyan|blue|purple"
```
**Result:** Exact 3.6° rotation per frame, 30ms timing

### Example 4: High-Quality PNG Sequence
```bash
python3 spiralmaker.py \
  --output-as-png frames/ \
  --dps 90 \
  --fps 30 \
  --arms 6 \
  --size 2000 \
  --colors "magenta|cyan"
```
**Result:** 20 unique PNG frames at 2000×2000 resolution (for external processing)

### Example 5: Maximum Optimization (9 arms)
```bash
python3 spiralmaker.py \
  --output maxopt.gif \
  --dps 120 \
  --fps 30 \
  --arms 9 \
  --colors "purple|magenta|pink|cyan|blue"
```
**Result:** 9x frame reduction, extremely efficient file size

## Understanding the Output

### Console Output
```
[warn] GIF quantizes to 10ms: 33.3ms → 30ms
[warn] Actual playback: 33.3fps = 120.0°/s (requested: 108.0°/s)
[info] Configuration: 108.0°/s, 30.0fps (30ms/frame), 5 arms
[info] Degrees per frame: 3.6000°
[info] Symmetry angle: 72.00°
[info] Unique frames to generate: 20
[info] Full rotation: 100 frames (3.33s)
[info] Optimization: 5.0x reduction via symmetry
[info] Generating 20 unique frames at 420x420...
[progress] 20/20 unique frames
[info] Outputting 20 unique frames (loops 5x for full rotation)
[info] Encoding GIF with 20 frames...
[ok] Wrote test.gif
```

**Key metrics:**
- **Unique frames**: Actual number of images generated
- **Full rotation**: Total frames if tiled for complete 360° (informational)
- **Optimization**: Frame reduction achieved via symmetry
- **Loops Nx**: The unique frames loop N times naturally for full rotation

### File Sizes

Approximate GIF sizes (will vary with content):
- 200×200: ~50-200 KB (10-50 frames)
- 400×400: ~100-500 KB
- 800×800: ~300-1500 KB
- 1000×1000: ~500-2500 KB
- 2000×2000: ~2-8 MB

**Optimization impact:**
- 5x optimization → ~80% smaller file
- 9x optimization → ~89% smaller file

## Advanced Usage

### Generating Multiple Variations

Create a test suite of different configurations:

```bash
# Test different arm counts
for arms in 3 5 7 9; do
  python3 spiralmaker.py --output spiral_${arms}arms.gif \
    --dps 120 --arms $arms --size 400
done

# Test different speeds
for dps in 60 90 120 180 360; do
  python3 spiralmaker.py --output spiral_${dps}dps.gif \
    --dps $dps --arms 5 --size 400
done
```

### Integration with Other Tools

**Use PNG output for:**
- Importing into Blender as heightmaps
- Compositing in video editors
- Creating texture sequences
- Post-processing in image editors

**Use GIF output for:**
- Direct web use
- Discord/social media
- Quick previews
- Embedded animations

## Troubleshooting

### "Configuration requires excessive frames"
Increase `--max-unique-frames` or let tool suggest alternative DPS values.

### "Actual playback differs from requested"
This is normal due to GIF 10ms quantization. Use exact values like 50fps (20ms) or 25fps (40ms) for precise timing.

### "Spiral appears to stutter"
- Increase FPS for smoother motion
- Check that degrees-per-frame divides evenly into symmetry angle
- Try suggested DPS values for better optimization

### "File size too large"
- Reduce `--size` resolution
- Use lower `--max-unique-frames` threshold to get optimization suggestions
- Consider PNG output with external compression

## Technical Details

### Frame Optimization Algorithm

1. Calculate degrees per frame: `dps / fps`
2. Calculate symmetry angle: `360 / arms`
3. Use GCD to find minimal unique frames: `GCD((360 × fps) / (dps × arms))`
4. Generate unique frames covering the minimal repeating pattern
5. GIF loops naturally via N-fold symmetry

### Formula for Spiral Pattern

```python
spiral_value = sin(arms × (θ + phase) + tightness × π × r)
```

Where:
- `θ` = angle (polar coordinate)
- `r` = radius (polar coordinate)
- `phase` = rotation phase (varies per frame)
- `arms` = number of spiral arms
- `tightness` = spiral wind tightness

The `arms × (θ + phase)` term preserves rotational symmetry, while `tightness × π × r` creates the spiral wind.

## Reference: Tested Optimal Configurations

From stress testing 1-9 arms × 12 DPS values:

**5 arms (5x optimization):**
- 30, 45, 60, 72, 90, 108, 120, 144, 180, 240, 360, 720 °/s

**6 arms (6x optimization):**
- 30, 45, 60, 72, 90, 120, 180, 360 °/s

**8 arms (8x optimization):**
- 30, 45, 72, 90, 144 °/s

**9 arms (9x optimization):**
- 30, 45, 60, 120, 240 °/s

All at 30fps (quantized to 30ms/frame).

## See Also

- `COLOR_PALETTES.md` - Full list of color palette options
- `gifmaker.py` - Main GIF generation tool (spiralmaker works standalone)
- Stress test results: `spiral_optimization_results.txt`
