Hypnocli — GIF maker for hypnotic loops

Safety
- This tool can produce high‑contrast flicker; use responsibly. See WCAG SC 2.3.1 and consider keeping risk moderate when sharing output.

What it does
- Builds an animated GIF from a folder of images with optional text overlays and color backfill.

Defaults
- Aspect: square 1000×1000 (also supports wide 1280×720 and tall 720×1280)
- Timing: medium = 80 ms per frame (≈12.5 fps). Note: GIF delays are stored in centiseconds (10 ms units).

Quick start
- Minimal
  - `python3 gifmaker.py --input-dir examples --colors "#000|#fff" --frames 8 --output outputs/minimal.gif`
- With text (INVERSE)
  - `python3 gifmaker.py --input-dir examples --medium --text examples/text.txt --text-color INVERSE --output outputs/text_inverse.gif`
- With frame map
  - `python3 gifmaker.py --input-dir examples --frame-map examples/frame_map.txt --colors "#ff008e|#00ff71|#ba33b1|#2aff4e" --output outputs/mapped.gif`

Text options
- INVERSE mode inverts pixels inside glyphs (respects outlines/shadows)
- Outlines: stroke (crisp), shadow (soft), none
- “*” marker at line level → 50% opacity for that line (the “*” is removed prior to rendering)

Modes and cadence
- Mode: continuous (default) vs interrupt (`--inter` toggles). Continuous advances color on every frame; interrupt advances color only on color frames.
- Cadence tip: in continuous mode, prefer total frame counts that are multiples of the number of colors.

GIF timing presets (centiseconds)
- 6.25 fps → 160 ms (`--crawl`)
- 10.00 fps → 100 ms (`--slow`)
- 12.50 fps → 80 ms (`--medium`)
- 16.67 fps → 60 ms (`--fast`)
- 20.00 fps → 50 ms (`--hyper`)

House palette example
- `"#FF008E|#00FF71|#BA33B1|#2AFF4E"`

Notes
- Input images are auto‑fit by default: mirror‑pad to fill with optional tint overlay via `--opacity` (single percent or per‑color pipe list).
- Text sizing auto‑scales to width; supports `--font`, `--font-size`, and `--text-scale`.
- Metadata: the GIF comment includes a compact JSON (prefix `GIFMAKER_META=`) with key options for reproducibility.

License
- MIT, see `LICENSE`.
