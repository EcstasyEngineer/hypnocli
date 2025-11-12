#!/usr/bin/env python3
"""GIF maker for hypnotic loops.

Builds animated GIFs from folders of images with optional text overlays,
auto fit/crop/stretch, tint overlay, and continuous/interrupt color cycling.
Defaults align to GIF centiseconds (medium = 80 ms per frame, ≈12.5 fps).
"""
import argparse
import random
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageChops
import json

VERBOSITY = 1  # 0=quiet, 1=normal, 2=verbose

def log_info(msg: str) -> None:
    if VERBOSITY >= 1:
        print(msg, file=sys.stderr)

def log_warn(msg: str) -> None:
    if VERBOSITY >= 1:
        print(msg, file=sys.stderr)

def log_debug(msg: str) -> None:
    if VERBOSITY >= 2:
        print(msg, file=sys.stderr)


def read_target_defaults() -> Tuple[int, int, int]:
    """Return (width, height, ms_per_frame) defaults.

    - Dimensions presets:
      square: 1000x1000, wide: 1280x720, tall: 720x1280
    - Timing default: medium 12.5 fps (80 ms per frame).
    """
    return 1000, 1000, 80


def parse_colors(spec: Optional[str]) -> List[Tuple[int, int, int]]:
    if not spec:
        return [(0, 0, 0)]  # default black
    # allow comma or pipe
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


def parse_opacities(spec: Optional[str], count: int) -> List[int]:
    """Parse opacity spec into per-color alpha bytes (0..255).

    - spec None or empty: default 15% broadcast to all colors.
    - spec single integer 'X': broadcast X% to all colors.
    - spec list 'a|b|c': must match --colors count; each 0-100.
    """
    def pct_to_alpha(pct: int) -> int:
        return int(round(max(0, min(100, pct)) * 255 / 100))

    if spec is None or spec.strip() == "":
        return [pct_to_alpha(15)] * count
    parts = [p.strip() for p in spec.replace(",", "|").split("|") if p.strip() != ""]
    if len(parts) == 1:
        try:
            v = int(parts[0])
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid opacity '{parts[0]}', must be integer 0-100")
        if not (0 <= v <= 100):
            raise argparse.ArgumentTypeError(f"Opacity out of range: {v}")
        return [pct_to_alpha(v)] * count
    vals: List[int] = []
    for token in parts:
        try:
            v = int(token)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid opacity '{token}', must be integer 0-100")
        if not (0 <= v <= 100):
            raise argparse.ArgumentTypeError(f"Opacity out of range: {token}")
        vals.append(pct_to_alpha(v))
    if len(vals) != count:
        raise argparse.ArgumentTypeError(
            f"--opacity count ({len(vals)}) must match --colors count ({count})"
        )
    return vals


def load_images(input_dir: Path) -> List[Path]:
    exts = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".gif",
    }
    paths = [p for p in sorted(input_dir.iterdir()) if p.suffix.lower() in exts]
    return paths


def read_text_lines(path: Path) -> List[str]:
    data = path.read_text(encoding="utf-8", errors="replace")
    # Preserve blank lines; splitlines preserves blank lines between text
    # Note: trailing newline at EOF does not create an extra empty line entry
    lines = data.splitlines()
    return lines


def compute_dims(aspect: str, width: Optional[int], height: Optional[int], defaults: Tuple[int, int]) -> Tuple[int, int]:
    if width and height:
        return width, height
    if width and not height:
        # infer height by aspect
        if aspect == "square":
            return width, width
        elif aspect == "wide":
            return width, int(round(width * 9 / 16))
        elif aspect == "tall":
            return width, int(round(width * 16 / 9))
    if height and not width:
        if aspect == "square":
            return height, height
        elif aspect == "wide":
            return int(round(height * 16 / 9)), height
        elif aspect == "tall":
            return int(round(height * 9 / 16)), height
    # neither provided: use fixed presets per aspect
    if aspect == "square":
        return 1000, 1000
    elif aspect == "wide":
        return 1280, 720
    elif aspect == "tall":
        return 720, 1280
    # Fallback to provided defaults
    dw, dh = defaults
    return dw, dh


def auto_fit_horizontal_mirror(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale to target height, center horizontally, mirror-pad sides as needed.

    - If resized width >= target width: center-crop horizontally.
    - Else: paste resized in center and fill left/right using alternating
      mirrored/original stripes that directly touch the center image.
    """
    w, h = img.size
    if h == 0:
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    scale = target_h / float(h)
    new_w = max(1, int(round(w * scale)))
    resized = img.resize((new_w, target_h), Image.Resampling.LANCZOS)

    if new_w >= target_w:
        # Center-crop horizontally
        left = (new_w - target_w) // 2
        return resized.crop((left, 0, left + target_w, target_h))

    # Mirror-pad horizontally
    mode_out = "RGBA" if img.mode == "RGBA" else "RGB"
    canvas = Image.new(mode_out, (target_w, target_h))
    left_offset = (target_w - new_w) // 2
    canvas.paste(resized, (left_offset, 0))

    mirrored = ImageOps.mirror(resized)

    # Fill left side: start adjacent to the main image with a mirrored slice,
    # then alternate original/mirrored as needed to reach the edge.
    need = left_offset
    x = left_offset
    stripe_is_mirrored = True  # first stripe adjacent to main is mirrored
    while need > 0:
        stripe = mirrored if stripe_is_mirrored else resized
        wstripe = min(stripe.width, need)
        # For left fill, take the rightmost portion of the stripe
        crop_box = (stripe.width - wstripe, 0, stripe.width, target_h)
        slice_img = stripe.crop(crop_box)
        x -= wstripe
        canvas.paste(slice_img, (x, 0))
        need -= wstripe
        stripe_is_mirrored = not stripe_is_mirrored

    # Fill right side: start adjacent to the main image with a mirrored slice,
    # then alternate mirrored/original as needed to the edge.
    start = left_offset + new_w
    need = target_w - start
    x = start
    stripe_is_mirrored = True
    while need > 0:
        stripe = mirrored if stripe_is_mirrored else resized
        wstripe = min(stripe.width, need)
        # For right fill, take the leftmost portion of the stripe
        crop_box = (0, 0, wstripe, target_h)
        slice_img = stripe.crop(crop_box)
        canvas.paste(slice_img, (x, 0))
        x += wstripe
        need -= wstripe
        stripe_is_mirrored = not stripe_is_mirrored

    return canvas


def fit_image(img: Image.Image, target_w: int, target_h: int, mode: str) -> Image.Image:
    if mode == "stretch":
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    elif mode == "crop":
        # cover-fit
        w, h = img.size
        scale = max(target_w / w, target_h / h)
        new_w, new_h = int(round(w * scale)), int(round(h * scale))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))
    elif mode == "auto":
        return auto_fit_horizontal_mirror(img, target_w, target_h)
    else:
        raise ValueError(f"Unknown fit mode: {mode}")


def draw_centered_text(
    im: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int],
    outline_mode: str,
    inverse: bool = False,
    alpha: int = 255,
):
    if not text:
        return
    draw = ImageDraw.Draw(im)
    W, H = im.size
    x = W // 2
    y = H // 2
    if inverse:
        # Prepare base as RGB
        base = im.convert("RGB")

        if outline_mode == "shadow":
            # Draw semi-opaque soft shadow then blend inversion inside glyphs
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, alpha), anchor="mm")
            blurred = overlay.filter(ImageFilter.GaussianBlur(radius=1.5))
            base_rgba = base.convert("RGBA")
            base_rgba.alpha_composite(blurred)
            shadowed = base_rgba.convert("RGB")

        if outline_mode == "stroke":
            # Build masks for stroke ring and fill
            stroke_mask = Image.new("L", im.size, 0)
            sm = ImageDraw.Draw(stroke_mask)
            try:
                sm.text((x, y), text, font=font, fill=255, anchor="mm", stroke_width=2)
            except TypeError:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    sm.text((x + dx, y + dy), text, font=font, fill=255, anchor="mm")
                sm.text((x, y), text, font=font, fill=255, anchor="mm")

            fill_mask = Image.new("L", im.size, 0)
            fm = ImageDraw.Draw(fill_mask)
            fm.text((x, y), text, font=font, fill=255, anchor="mm")

            # Ring = stroke - fill
            ring_mask = ImageChops.subtract(stroke_mask, fill_mask)
            # Paint semi-opaque black ring onto base
            # Blend base with black inside the ring region by alpha fraction
            black_rgb = Image.new("RGB", im.size, (0, 0, 0))
            ring_blend = Image.blend(base, black_rgb, float(alpha) / 255.0)
            base.paste(ring_blend, (0, 0), ring_mask)

            # Blend inversion inside the fill interior by alpha fraction
            inv = ImageOps.invert(base)
            blend = Image.blend(base, inv, float(alpha) / 255.0)
            base.paste(blend, (0, 0), fill_mask)
            im.paste(base)
        else:
            # Blend inversion inside glyph interior (shadow already applied if any)
            fill_mask = Image.new("L", im.size, 0)
            fm = ImageDraw.Draw(fill_mask)
            fm.text((x, y), text, font=font, fill=255, anchor="mm")
            # Blend between original image and inverted image inside glyph area
            orig_rgb = im.convert("RGB")
            inv_src = ImageOps.invert(orig_rgb)
            blended = Image.blend(orig_rgb, inv_src, float(alpha) / 255.0)
            # If we created a shadowed base, use it; else use the unmodified base
            target = shadowed if 'shadowed' in locals() else base
            target.paste(blended, (0, 0), fill_mask)
            im.paste(target)
    else:
        # Draw onto an overlay to support alpha for fill/stroke/shadow
        if outline_mode == "none" or outline_mode == "stroke":
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            fill_rgba = (color[0], color[1], color[2], alpha)
            if outline_mode == "stroke":
                try:
                    o_draw.text((x, y), text, font=font, fill=fill_rgba, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, alpha))
                except TypeError:
                    # Fallback: manual 1px offset ring
                    outline_rgba = (0, 0, 0, alpha)
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        o_draw.text((x + dx, y + dy), text, font=font, fill=outline_rgba, anchor="mm")
                    o_draw.text((x, y), text, font=font, fill=fill_rgba, anchor="mm")
            else:
                o_draw.text((x, y), text, font=font, fill=fill_rgba, anchor="mm")
            im_rgba = im.convert("RGBA")
            im_rgba.alpha_composite(overlay)
            im.paste(im_rgba.convert("RGB"))
        else:  # shadow
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            # Shadow (use same alpha so the line's overall opacity is reduced)
            o_draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, alpha), anchor="mm")
            blurred = overlay.filter(ImageFilter.GaussianBlur(radius=1.5))
            # Main text overlay
            text_overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            to_draw = ImageDraw.Draw(text_overlay)
            to_draw.text((x, y), text, font=font, fill=(color[0], color[1], color[2], alpha), anchor="mm")
            # Composite
            im_rgba = im.convert("RGBA")
            im_rgba.alpha_composite(blurred)
            im_rgba.alpha_composite(text_overlay)
            im.paste(im_rgba.convert("RGB"))


def try_load_default_ttf(size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Try to load a bundled TTF (DejaVuSans) for scalable text. Return None if unavailable."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return None


def autosize_font_for_scale(
    text_lines: List[str],
    target_width: int,
    scale: float,
    font_path: Optional[str],
    fallback_size: int,
) -> ImageFont.FreeTypeFont:
    """Return a TTF font sized so the widest line ~= scale * target_width.

    If a font path is not provided, try DejaVuSans. If no TTF is available,
    fall back to default bitmap font (no precise scaling possible).
    """
    # Ensure at least one line to measure
    lines = text_lines if text_lines else [" "]

    # Resolve TTF font
    base_font: Optional[ImageFont.FreeTypeFont] = None
    font_loader = None
    if font_path:
        def loader(sz: int):
            return ImageFont.truetype(font_path, sz)
        font_loader = loader
    else:
        ttf = try_load_default_ttf(fallback_size)
        if ttf is not None:
            def loader(sz: int):
                return ImageFont.truetype("DejaVuSans.ttf", sz)
            font_loader = loader

    # If no TrueType font available, fallback
    if font_loader is None:
        # Warn (verbosity-aware) so logs don't mix with stdout
        log_warn("[warn] No TTF font available; using default bitmap font. Consider --font for precise --text-scale.")
        return ImageFont.load_default()

    # Binary search a font size that fits width
    min_size, max_size = 6, 1024
    best = fallback_size
    # Use a dummy image for measurement
    dummy = Image.new("RGB", (target_width, target_width), (0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    target_px = max(1, int(round(scale * target_width)))

    while min_size <= max_size:
        mid = (min_size + max_size) // 2
        font = font_loader(mid)
        max_line_w = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font, anchor="lt")
            line_w = bbox[2] - bbox[0]
            if line_w > max_line_w:
                max_line_w = line_w
        if max_line_w <= target_px:
            best = mid
            min_size = mid + 1
        else:
            max_size = mid - 1

    return font_loader(best)


def build_frames(
    image_paths: List[Path],
    is_image_frame: List[bool],
    image_for_frame: List[Optional[Path]],
    colors: List[Tuple[int, int, int]],
    color_mode: str,
    opacities: Optional[List[int]],
    size: Tuple[int, int],
    fit: str,
    text_lines: Optional[List[str]],
    font: ImageFont.FreeTypeFont,
    text_colors: List[Tuple[int, int, int]],
    outline_mode: str,
    tint_images: bool,
) -> List[Image.Image]:
    W, H = size
    frames: List[Image.Image] = []
    color_count = max(1, len(colors))
    color_idx = 0
    for i in range(len(is_image_frame)):
        if color_mode == "cont":
            idx_for_frame = i % color_count
        elif color_mode == "inter":
            idx_for_frame = color_idx
        else:
            raise ValueError("Invalid mode")

        base_color = colors[idx_for_frame]
        if is_image_frame[i]:
            # Ensure files are closed promptly (especially on Windows)
            with Image.open(image_for_frame[i]) as src_im:
                src = src_im.convert("RGBA")
                fitted = fit_image(src, W, H, fit)
                # Composite over solid backfill color to honor transparency
                base = Image.new("RGBA", (W, H), (*base_color, 255))
                base.alpha_composite(fitted)
                canvas_rgba = base
                if tint_images:
                    alpha = opacities[idx_for_frame] if opacities else 128
                    overlay = Image.new("RGBA", (W, H), (*base_color, alpha))
                    canvas_rgba.alpha_composite(overlay)
                canvas = canvas_rgba.convert("RGB")
        else:
            # solid color frame
            canvas = Image.new("RGB", (W, H), base_color)
            if color_mode == "inter":
                color_idx = (color_idx + 1) % color_count

        # Text overlay (support per-line dim via '*' marker → 50% opacity; '*' removed before rendering)
        if text_lines is not None:
            raw_text = text_lines[i] if i < len(text_lines) else ""
            dim_alpha = 128 if ("*" in raw_text) else 255
            text = raw_text.replace("*", "")
            tc = text_colors[i % max(1, len(text_colors))]
            # When tc is None (inverse mode), enable inversion (blend invert by alpha)
            if tc is None:
                draw_centered_text(canvas, text, font, (255, 255, 255), outline_mode, inverse=True, alpha=dim_alpha)
            else:
                draw_centered_text(canvas, text, font, tc, outline_mode, inverse=False, alpha=dim_alpha)
        # Keep frames in RGB; palette handling is applied later (optionally global)
        frames.append(canvas)
    return frames


# --- Verbose metrics (WCAG-ish + intensity) ---

def _srgb_to_linear_unit(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def _to_linear_rgb(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    r, g, b = rgb
    R = _srgb_to_linear_unit(r / 255.0)
    G = _srgb_to_linear_unit(g / 255.0)
    B = _srgb_to_linear_unit(b / 255.0)
    return R, G, B

def _rel_luminance(rgb: Tuple[int, int, int]) -> float:
    R, G, B = _to_linear_rgb(rgb)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def _xyz_from_linear(R: float, G: float, B: float) -> Tuple[float, float, float]:
    X = 0.4123907992659595 * R + 0.3575843393838780 * G + 0.1804807884018343 * B
    Y = 0.2126390058715104 * R + 0.7151686787677560 * G + 0.0721923153607337 * B
    Z = 0.0193308187155918 * R + 0.1191947797946260 * G + 0.9505321522496607 * B
    return X, Y, Z

def _uv_prime(rgb: Tuple[int, int, int]) -> Tuple[float, float]:
    R, G, B = _to_linear_rgb(rgb)
    X, Y, Z = _xyz_from_linear(R, G, B)
    denom = X + 15 * Y + 3 * Z
    if denom <= 1e-12:
        return 0.0, 0.0
    u_p = 4 * X / denom
    v_p = 9 * Y / denom
    return u_p, v_p

def _saturated_red(rgb: Tuple[int, int, int]) -> bool:
    r, g, b = rgb
    s = r + g + b
    return s > 0 and (r / s) >= 0.8

def analyze_cycle_palette(colors: List[Tuple[int, int, int]], fps: float) -> dict:
    n = max(1, len(colors))
    L = [_rel_luminance(c) for c in colors]
    d = [L[(i + 1) % n] - L[i] for i in range(n)]
    abs_d = [abs(x) for x in d]
    mic = []
    for i in range(n):
        l1, l2 = L[i], L[(i + 1) % n]
        denom = max(1e-9, l1 + l2)
        mic.append(abs(l2 - l1) / denom)
    M_max = max(mic) if mic else 0.0
    M_mean = sum(mic) / len(mic) if mic else 0.0

    big = [abs_d[i] >= 0.10 and min(L[i], L[(i + 1) % n]) < 0.80 for i in range(n)]
    pair_count = 0
    for i in range(n):
        j = (i + 1) % n
        if big[i] and big[j] and (d[i] * d[j] < 0):
            pair_count += 1
    flashes_per_cycle = pair_count
    f_flashes = flashes_per_cycle * (fps / float(n))
    f_cycle = fps / float(n)
    f0 = f_flashes if flashes_per_cycle > 0 else f_cycle

    uv = [_uv_prime(c) for c in colors]
    duv = []
    sat_red_pairs = 0
    for i in range(n):
        j = (i + 1) % n
        du = uv[j][0] - uv[i][0]
        dv = uv[j][1] - uv[i][1]
        dist = (du * du + dv * dv) ** 0.5
        duv.append(dist)
        if (_saturated_red(colors[i]) or _saturated_red(colors[j])) and dist > 0.2:
            sat_red_pairs += 1
    delta_uv_mean = sum(duv) / len(duv) if duv else 0.0
    delta_uv_max = max(duv) if duv else 0.0

    if f_flashes <= 3.0 or flashes_per_cycle == 0:
        risk_score = 2.0 * M_max
        wcag_pass = True
        bucket = "Pass"
    else:
        frac = max(0.0, min(1.0, (f_flashes - 3.0) / 27.0))
        B = 1.0
        risk_score = 10.0 * frac * (0.7 * M_max + 0.3) * B
        if sat_red_pairs > 0:
            risk_score += 2.0
        risk_score = max(0.0, min(10.0, risk_score))
        wcag_pass = False
        bucket = "High" if risk_score < 8.0 else "Very high"

    f_ref = 15.0
    chi = max(0.0, min(1.0, delta_uv_mean / 0.04))
    intensity = 10.0 * max(0.0, min(1.0, 0.55 * (M_max ** 0.8) + 0.35 * max(0.0, min(1.0, (f0 / f_ref))) + 0.10 * chi))

    f_c = 15.0
    g_down = 1.0 / (1.0 + (f0 / f_c) ** 2) if f0 > 0 else 1.0
    discomfort = max(0.0, min(1.0, 0.45 * (M_max ** 0.8) + 0.35 * g_down + 0.10 * chi))
    comfort = 10.0 * (1.0 - discomfort)
    if sat_red_pairs > 0:
        comfort = max(0.0, comfort - 1.0)

    return {
        "fps": fps,
        "n_colors": n,
        "luminance": {"M_max": M_max, "M_mean": M_mean, "L_min": min(L) if L else 0.0, "L_max": max(L) if L else 0.0},
        "tempo": {"flashes_per_cycle": flashes_per_cycle, "f_flashes": f_flashes, "f_cycle": f_cycle, "f0": f0},
        "chromatic": {"delta_uv_mean": delta_uv_mean, "delta_uv_max": delta_uv_max},
        "scores": {"intensity": intensity, "comfort": comfort, "risk": risk_score, "wcag_bucket": bucket, "wcag_pass": wcag_pass},
    }


def extract_opts(gif_path: str) -> None:
    """Extract and print the command-line options used to create a GIF."""
    try:
        with Image.open(gif_path) as img:
            comment = img.info.get('comment', b'')
            if isinstance(comment, bytes):
                comment = comment.decode('utf-8', errors='replace')

            if not comment.startswith('GIFMAKER_META='):
                print(f"[error] No gifmaker metadata found in {gif_path}", file=sys.stderr)
                sys.exit(1)

            meta_json = comment.replace('GIFMAKER_META=', '')
            meta = json.loads(meta_json)

            # Check for new two-tier structure
            if 'input_params' in meta:
                params = meta['input_params']
            else:
                # Old format - use top-level as params
                params = meta

            # Reconstruct command
            cmd = ['python3', 'gifmaker.py']

            # Map of param keys to CLI flags
            flag_map = {
                'input_dir': '--input-dir',
                'text_file': '--text',
                'output': '--output',
                'frames': '--frames',
                'colors': '--colors',
                'aspect': '--aspect',
                'width': '--width',
                'height': '--height',
                'fit': '--fit',
                'seed_used': '--seed',
                'text_color_spec': '--text-color',
                'outline': '--outline',
                'font': '--font',
                'font_size': '--font-size',
                'text_scale': '--text-scale',
                'image_map_file': '--image-map',
                'text_density': '--text-density',
            }

            # Boolean flags
            bool_flags = {
                'shuffle_text': '--shuffle-text',
                'inter': '--inter',
            }

            # Speed flags
            speed_flags = {
                'crawl': '--crawl',
                'slow': '--slow',
                'medium': '--medium',
                'fast': '--fast',
                'hyper': '--hyper',
            }

            for key, flag in flag_map.items():
                value = params.get(key)
                if value is None or value is False:
                    continue

                if key == 'colors' and isinstance(value, list):
                    cmd.extend([flag, '|'.join(value)])
                elif key == 'seed_used':
                    cmd.extend([flag, str(value)])
                else:
                    cmd.extend([flag, str(value)])

            # Handle boolean flags
            for key, flag in bool_flags.items():
                if params.get(key):
                    cmd.append(flag)

            # Handle speed flags
            for key, flag in speed_flags.items():
                if params.get(key):
                    cmd.append(flag)

            # Handle ms_per_frame if no speed preset
            if not any(params.get(k) for k in speed_flags.keys()):
                ms = params.get('ms_per_frame')
                if ms:
                    cmd.extend(['--ms', str(ms)])

            # Handle opacity/tint
            if params.get('tint_enabled'):
                opacity_list = params.get('opacity_pct_list')
                if opacity_list:
                    cmd.extend(['--opacity', '|'.join(map(str, opacity_list))])
                else:
                    cmd.append('--opacity')

            print(f"[info] Extracted command from {gif_path}:")
            print(' '.join(cmd))

    except Exception as e:
        print(f"[error] Failed to extract metadata: {e}", file=sys.stderr)
        sys.exit(1)


def extract_images(gif_path: str) -> None:
    """Extract image mapping from a GIF to stdout."""
    try:
        with Image.open(gif_path) as img:
            comment = img.info.get('comment', b'')
            if isinstance(comment, bytes):
                comment = comment.decode('utf-8', errors='replace')

            if not comment.startswith('GIFMAKER_META='):
                print(f"[error] No gifmaker metadata found in {gif_path}", file=sys.stderr)
                sys.exit(1)

            meta_json = comment.replace('GIFMAKER_META=', '')
            meta = json.loads(meta_json)

            # Get computed metadata
            computed = meta.get('computed_metadata', meta)

            # Get image mapping
            random_mapping = computed.get('random_mapping')

            if not random_mapping:
                print(f"[error] No image mapping found in metadata", file=sys.stderr)
                sys.exit(1)

            # Print image mapping to stdout
            for frame_idx, img_name in random_mapping:
                if img_name is None:
                    print('-')
                else:
                    print(img_name)

    except Exception as e:
        print(f"[error] Failed to extract image mapping: {e}", file=sys.stderr)
        sys.exit(1)


def extract_text(gif_path: str) -> None:
    """Extract text mapping from a GIF to stdout."""
    try:
        with Image.open(gif_path) as img:
            comment = img.info.get('comment', b'')
            if isinstance(comment, bytes):
                comment = comment.decode('utf-8', errors='replace')

            if not comment.startswith('GIFMAKER_META='):
                print(f"[error] No gifmaker metadata found in {gif_path}", file=sys.stderr)
                sys.exit(1)

            meta_json = comment.replace('GIFMAKER_META=', '')
            meta = json.loads(meta_json)

            # Get computed metadata
            computed = meta.get('computed_metadata', meta)

            # Get text mapping
            text_mapping = computed.get('text_mapping')

            if not text_mapping:
                print(f"[error] No text mapping found in metadata (GIF may not have used text)", file=sys.stderr)
                sys.exit(1)

            # Print text mapping to stdout
            for frame_idx, text in text_mapping:
                if text is None or text == '':
                    print('-')
                else:
                    print(text)

    except Exception as e:
        print(f"[error] Failed to extract text mapping: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="GIF maker for hypnotic loops")
    parser.add_argument("--input-dir", help="Directory containing input images")
    parser.add_argument(
        "--text",
        help="Optional text file; each line is a frame's text. If --frames is omitted, total frames = number of lines (trailing newline not counted). Text maps sequentially by default; use --shuffle-text for random placement.",
    )
    parser.add_argument("--output", default="out.gif", help="Output GIF path")
    parser.add_argument("--image-map", help="Image map file: one line per frame; relative image path or '-' for color frame. If omitted, images are placed randomly.")
    parser.add_argument("--frames", type=int, help="Target number of frames")
    # Speed controls (mutually exclusive)
    spd = parser.add_mutually_exclusive_group()
    spd.add_argument("--fps", type=float, help="Frames per second")
    spd.add_argument("--ms", type=int, help="Milliseconds per frame")
    spd.add_argument("--crawl", action="store_true", help="6.25 fps (160 ms, theta)")
    spd.add_argument("--slow", action="store_true", help="10.0 fps (100 ms, low alpha)")
    spd.add_argument("--medium", action="store_true", help="12.5 fps (80 ms, alpha)")
    spd.add_argument("--fast", action="store_true", help="16.67 fps (60 ms, low beta)")
    spd.add_argument("--hyper", action="store_true", help="20.0 fps (50 ms, beta)")
    # (Analysis options removed; metrics moved to a separate tool.)
    parser.add_argument("--aspect", choices=["square", "wide", "tall"], default="square")
    parser.add_argument("--width", type=int, help="Output width (overrides aspect)")
    parser.add_argument("--height", type=int, help="Output height (overrides aspect)")
    parser.add_argument("--fit", choices=["stretch", "crop", "auto"], default="auto")
    parser.add_argument("--colors", help="Colors for backfill, e.g. 'pink|white|purple'")
    parser.add_argument(
        "--inter",
        action="store_true",
        help="Interrupt color pattern: advance colors only on color frames (default continuous mode advances every frame)",
    )
    # Verbosity controls
    vb = parser.add_mutually_exclusive_group()
    vb.add_argument("--quiet", action="store_true", help="Suppress informational and warning output (only errors and final summary)")
    vb.add_argument("--verbose", action="store_true", help="Print detailed debug info, frame mapping, and palette metrics")
    parser.add_argument(
        "--opacity",
        nargs="?",
        const="15",
        help=(
            "Enable image tint overlay. Accepts a single percent (e.g. '15') "
            "or a pipe list matching --colors (e.g. '15|20|15'). If no value is provided, defaults to 15%%."
        ),
    )
    parser.add_argument("--seed", help="Seed (string or number). If omitted, a random seed is generated and printed")
    parser.add_argument("--font", help="Path to TTF font")
    parser.add_argument("--font-size", type=int, help="Font size for text (overrides --text-scale)")
    parser.add_argument("--text-scale", type=float, default=0.6, help="Target fraction of width for widest line (0-1)")
    parser.add_argument("--text-color", default="#FFFFFF", help="Text color or pipe-list; use INVERSE to invert pixels under text")
    parser.add_argument("--outline", choices=["shadow", "stroke", "none"], default="stroke", help="Text outline style; default 'stroke' for crisp edges")
    parser.add_argument("--shuffle-text", action="store_true", help="Randomize text line order and placement (requires --frames)")
    parser.add_argument("--text-density", type=float, help="Proportion of frames with text when using --shuffle-text (0.0-1.0, default 1.0)")
    # Extraction tools
    parser.add_argument("--extract-opts", help="Extract command-line options from a GIF's metadata")
    parser.add_argument("--extract-images", help="Extract image mapping from a GIF to stdout")
    parser.add_argument("--extract-text", help="Extract text mapping from a GIF to stdout")

    args = parser.parse_args()

    # Handle extraction commands first (these exit after running)
    if args.extract_opts:
        extract_opts(args.extract_opts)
        return

    if args.extract_images:
        extract_images(args.extract_images)
        return

    if args.extract_text:
        extract_text(args.extract_text)
        return

    # Set global verbosity
    global VERBOSITY
    VERBOSITY = 0 if args.quiet else (2 if args.verbose else 1)

    # Require input-dir for GIF generation
    if not args.input_dir:
        raise SystemExit("ERROR: --input-dir is required")

    # Validation for new shuffle-text feature
    if args.text_density is not None and not args.shuffle_text:
        raise SystemExit("ERROR: --text-density requires --shuffle-text")

    if args.shuffle_text and args.frames is None:
        raise SystemExit("ERROR: --shuffle-text requires explicit --frames")

    # Clamp and warn for text_density
    if args.text_density is not None:
        if args.text_density < 0.0 or args.text_density > 1.0:
            log_warn(f"[warn] --text-density {args.text_density} out of range [0.0, 1.0]; clamping")
            args.text_density = max(0.0, min(1.0, args.text_density))
    elif args.shuffle_text:
        args.text_density = 1.0  # Default

    # Mode selection: default continuous; --inter toggles interrupt behavior
    mode = "inter" if args.inter else "cont"

    def_w, def_h, def_ms = read_target_defaults()

    # Timing (initial)
    if args.ms is not None:
        if int(args.ms) <= 0:
            raise SystemExit("--ms must be > 0")
        ms_per_frame = int(args.ms)
    elif args.fps is not None:
        if args.fps <= 0:
            raise SystemExit("--fps must be > 0")
        ms_per_frame = int(round(1000.0 / args.fps))
    elif args.crawl:
        ms_per_frame = 160  # 6.25 fps
    elif args.slow:
        ms_per_frame = 100  # 10 fps
    elif args.medium:
        ms_per_frame = 80   # 12.5 fps
    elif args.fast:
        ms_per_frame = 60   # 16.67 fps
    elif args.hyper:
        ms_per_frame = 50  # 20 fps
    else:
        ms_per_frame = def_ms

    # Warn about GIF centisecond quantization if needed
    if ms_per_frame % 10 != 0:
        quant_ms = int(round(ms_per_frame / 10.0) * 10)
        eff_fps = (1000.0 / quant_ms) if quant_ms > 0 else 0.0
        log_warn(
            f"[warn] GIF stores delays in 10 ms units; {ms_per_frame} ms will be written as {quant_ms} ms (~{eff_fps:.2f} fps)."
        )

    # Dimensions (+ validate if provided)
    if args.width is not None and args.width <= 0:
        raise SystemExit("--width must be > 0")
    if args.height is not None and args.height <= 0:
        raise SystemExit("--height must be > 0")
    W, H = compute_dims(args.aspect, args.width, args.height, (def_w, def_h))

    # Colors and opacities (tint via --opacity only)
    colors = parse_colors(args.colors)
    opacities = None
    tint_enabled = bool(args.opacity is not None)
    if tint_enabled:
        opacities = parse_opacities(args.opacity, len(colors))

    # Frequency targeting moved to external tools; use presets/--fps/--ms here.

    # Seed
    if args.seed is None:
        # Generate a random 64-bit number and print it
        seed_value = random.randrange(1 << 63)
        log_info(f"[info] seed: {seed_value}")
    else:
        seed_value = args.seed
        log_info(f"[info] seed: {seed_value}")
    random.seed(seed_value)

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")
    image_paths = load_images(input_dir)
    if not image_paths and not args.image_map:
        raise SystemExit(f"No images found in: {input_dir}")

    # Metrics/analysis moved to separate tooling.

    # Text
    text_lines: Optional[List[str]] = None
    if args.text:
        text_path = Path(args.text)
        if not text_path.exists():
            raise SystemExit(f"Text file not found: {text_path}")
        text_lines = read_text_lines(text_path)
        # Treat a line that is exactly '-' (ignoring surrounding whitespace) as an explicit empty text frame
        if text_lines:
            dash_count = sum(1 for ln in text_lines if ln.strip() == "-")
            if dash_count > 0:
                log_info(f"[info] interpreting {dash_count} line(s) with '-' as empty text frames")
            text_lines = ["" if (ln.strip() == "-") else ln for ln in text_lines]
        log_info(f"[info] loaded {len(text_lines)} text line(s) from {text_path}")

    # Handle shuffle-text mode
    text_mapping: Optional[List[Tuple[int, Optional[str]]]] = None
    original_text_lines = text_lines  # Keep original for metadata
    if args.shuffle_text and text_lines:
        # Shuffle mode requires explicit frames (already validated)
        total_frames = args.frames
        target_text_frames = int(total_frames * args.text_density)

        # Shuffle the text lines
        shuffled_lines = text_lines[:]
        random.shuffle(shuffled_lines)

        # Sample frame indices for text placement
        text_frame_indices = sorted(random.sample(range(total_frames), target_text_frames))

        # Build text mapping
        text_mapping = []
        text_lines_for_frames = []
        line_idx = 0
        for frame_num in range(total_frames):
            if frame_num in text_frame_indices:
                # Wrap if needed
                text = shuffled_lines[line_idx % len(shuffled_lines)]
                text_mapping.append((frame_num, text))
                text_lines_for_frames.append(text)
                line_idx += 1
            else:
                text_mapping.append((frame_num, None))
                text_lines_for_frames.append("")

        # Replace text_lines with the per-frame list
        text_lines = text_lines_for_frames
        log_info(f"[info] shuffle-text: {target_text_frames}/{total_frames} frames with text (density={args.text_density})")
    elif text_lines:
        # Non-shuffle mode: build text_mapping for sequential text (preserves snapshot of original text)
        # This ensures GIF is reproducible even if source text file is modified later
        text_mapping = []
        for i, line in enumerate(text_lines):
            # Store None for empty lines, actual text otherwise
            text_mapping.append((i, line if line else None))

    # Optional explicit frame map
    is_image_frame: List[bool] = []
    image_for_frame: List[Optional[Path]] = []
    # Determine frame count
    total_frames: int
    if args.image_map:
        map_path = Path(args.image_map)
        if not map_path.exists():
            raise SystemExit(f"Image map file not found: {map_path}")
        map_lines = read_text_lines(map_path)
        for idx, raw in enumerate(map_lines):
            token = raw.strip()
            if token == "" or token == "-" or token.lower() == "color":
                is_image_frame.append(False)
                image_for_frame.append(None)
            else:
                p = Path(token)
                if not p.is_absolute():
                    p = input_dir / p
                if not p.exists():
                    raise SystemExit(f"Image map line {idx+1}: image not found: {token} -> {p}")
                is_image_frame.append(True)
                image_for_frame.append(p)
        total_frames = len(map_lines)
        if args.frames is not None and args.frames != total_frames:
            log_warn(f"[warn] --frames ({args.frames}) ignored; using --image-map length {total_frames}")
    elif args.frames is not None and text_lines is not None:
        if args.frames <= 0:
            raise SystemExit("--frames must be > 0")
        if args.frames < len(text_lines):
            raise SystemExit(
                f"--frames ({args.frames}) is less than text lines ({len(text_lines)}); increase --frames or reduce text lines"
            )
        total_frames = args.frames
        extra = args.frames - len(text_lines)
        if extra > 0:
            log_info(f"[info] text lines: {len(text_lines)}; there will be {extra} additional frame(s) with no text at the end")
    elif args.frames is not None:
        if args.frames <= 0:
            raise SystemExit("--frames must be > 0")
        total_frames = args.frames
    elif text_lines is not None:
        total_frames = len(text_lines)
    else:
        # Default: use number of images, or a small multiple?
        # Keep it simple: use number of images
        total_frames = len(image_paths)

    # Distribution: choose which frames are images, no repeats (only if no map)
    num_images = len(image_paths)
    if not args.image_map:
        if total_frames <= num_images:
            # sample images down to total_frames; every frame is an image frame
            log_warn(f"[warn] frames ({total_frames}) < images ({num_images}); sampling images down to {total_frames}.")
            used_images = random.sample(image_paths, total_frames)
            is_image_frame = [True] * total_frames
            image_for_frame = used_images
        else:
            # place each image exactly once at random frame indices; rest backfill
            frame_indices = list(range(total_frames))
            chosen = set(random.sample(frame_indices, num_images))
            # Ensure frame 0 is an image for thumbnail
            if 0 not in chosen:
                # replace a random chosen frame (not 0) with 0
                victim = random.choice(list(chosen))
                chosen.remove(victim)
                chosen.add(0)
                log_info("[info] forcing frame 0 to be an image for thumbnail")
            is_image_frame = [i in chosen for i in frame_indices]
            shuffled_images = image_paths[:]
            random.shuffle(shuffled_images)
            image_for_frame = [None] * total_frames
            j = 0
            for i in range(total_frames):
                if is_image_frame[i]:
                    image_for_frame[i] = shuffled_images[j]
                    j += 1

    # Fill ratio
    filled = sum(1 for x in is_image_frame if x)
    fill_ratio = 100.0 * filled / total_frames if total_frames else 0.0
    log_info(f"[info] frames={total_frames}, images_used={filled}/{num_images}, fill_ratio={fill_ratio:.1f}%")
    # Warn if the color cycle will end mid-cycle (useful for rhythmic aesthetics)
    if len(colors) > 1:
        if mode == "cont":
            rem = total_frames % len(colors)
            if rem != 0:
                missing = (len(colors) - rem) % len(colors)
                log_warn(
                    f"[warn] frames ({total_frames}) not a multiple of colors ({len(colors)}); last cycle will be incomplete (missing {missing} color step(s))."
                )
        else:  # inter mode: only color backfill frames advance the cycle
            color_steps = total_frames - filled
            rem = color_steps % len(colors)
            if rem != 0:
                missing = (len(colors) - rem) % len(colors)
                log_warn(
                    f"[warn] color backfill steps ({color_steps}) not a multiple of colors ({len(colors)}); last color cycle will be incomplete (missing {missing} step(s))."
                )
    log_info(f"[info] size={W}x{H}, ms/frame={ms_per_frame}, fit={args.fit}, mode={mode}")

    # Prepare text rendering
    # Parse text color(s): allow single color or pipe/comma-separated list; special token INVERSE
    def parse_text_colors(spec: Optional[str]) -> List[Optional[Tuple[int, int, int]]]:
        if spec is None:
            spec = "#FFFFFF"
        raw = spec.strip()
        if raw.upper() == "INVERSE":
            return [None]
        parts = [p.strip() for p in raw.replace(",", "|").split("|") if p.strip()]
        out: List[Optional[Tuple[int, int, int]]] = []
        for token in parts:
            try:
                out.append(ImageColor.getrgb(token))
            except ValueError as e:
                raise SystemExit(f"Invalid --text-color: {e}")
        if not out:
            out = [ImageColor.getrgb("#FFFFFF")]
        return out
    text_colors = parse_text_colors(args.text_color)
    # Decide font sizing strategy
    if text_lines is not None:
        # For sizing, strip '*' markers to match rendered content width
        measure_lines = [ln.replace("*", "") for ln in text_lines]
        if args.font_size is not None:
            # Explicit font size overrides text-scale
            try:
                if args.font:
                    font = ImageFont.truetype(args.font, args.font_size)
                else:
                    font = try_load_default_ttf(args.font_size) or ImageFont.load_default()
            except Exception as e:
                log_warn(f"[warn] failed to load font '{args.font or 'DejaVuSans.ttf'}': {e}; using default font")
                font = ImageFont.load_default()
        else:
            # Auto-size font to text-scale fraction of width
            scale = max(0.1, min(1.0, float(args.text_scale)))
            font = autosize_font_for_scale(
                measure_lines,
                W,
                scale,
                args.font,
                fallback_size=36,
            )
    else:
        # No text; load any font for later potential use
        font = try_load_default_ttf(36) or ImageFont.load_default()

    frames_rgb = build_frames(
        image_paths,
        is_image_frame,
        image_for_frame,
        colors,
        mode,
        opacities,
        (W, H),
        args.fit,
        text_lines,
        font,
        text_colors,
        args.outline,
        bool(tint_enabled),
    )

    if VERBOSITY >= 2:
        log_debug("[debug] frame mapping:")
        for i, is_img in enumerate(is_image_frame):
            if is_img:
                log_debug(f"  frame {i}: IMAGE -> {image_for_frame[i].name}")
            else:
                log_debug(f"  frame {i}: COLOR")

    # Verbose metrics
    if VERBOSITY >= 2 and len(colors) >= 1:
        fps = 1000.0 / float(ms_per_frame) if ms_per_frame > 0 else 0.0
        if mode == "cont":
            eff_fps = fps
            m = analyze_cycle_palette(colors, fps=eff_fps)
            log_debug(
                f"[metrics] n_colors={m['n_colors']} fps={m['fps']:.2f} M_max={m['luminance']['M_max']:.2f} M_mean={m['luminance']['M_mean']:.2f} "
                f"Lmin={m['luminance']['L_min']:.2f} Lmax={m['luminance']['L_max']:.2f}"
            )
            log_debug(
                f"[metrics] flashes/cycle={m['tempo']['flashes_per_cycle']} f_flashes={m['tempo']['f_flashes']:.2f}/sec wcag={m['scores']['wcag_bucket']} "
                f"risk={m['scores']['risk']:.2f} intensity={m['scores']['intensity']:.2f} comfort={m['scores']['comfort']:.2f}"
            )
        else:
            color_steps = total_frames - filled
            if color_steps <= 0:
                log_warn("[warn] inter mode: no color frames; color cycle will not advance.")
            eff_fps = fps * (color_steps / float(total_frames)) if total_frames > 0 else 0.0
            m = analyze_cycle_palette(colors, fps=eff_fps)
            log_debug(
                f"[metrics] inter: total_frames={total_frames} image_frames={filled} color_steps={color_steps} eff_fps={eff_fps:.2f}"
            )
            log_debug(
                f"[metrics] flashes/cycle={m['tempo']['flashes_per_cycle']} f_flashes={m['tempo']['f_flashes']:.2f}/sec wcag={m['scores']['wcag_bucket']} "
                f"risk={m['scores']['risk']:.2f} intensity={m['scores']['intensity']:.2f} comfort={m['scores']['comfort']:.2f}"
            )

    # Save GIF
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not frames_rgb:
        raise SystemExit("No frames generated")
    # Quantize per-frame using adaptive palette (better fidelity than a single global palette)
    pal_frames = [
        frm.convert("P", palette=Image.ADAPTIVE, colors=256, dither=Image.Dither.NONE)
        for frm in frames_rgb
    ]
    first, rest = pal_frames[0], pal_frames[1:]

    first.save(
        out_path,
        save_all=True,
        append_images=rest,
        duration=ms_per_frame,
        loop=0,
        disposal=2,
        comment=(
            (
                "GIFMAKER_META="
                + json.dumps(
                    {
                        "meta_version": 2,
                        "input_params": {
                            "input_dir": str(input_dir),
                            "text_file": str(Path(args.text)) if args.text else None,
                            "output": str(out_path),
                            "frames": args.frames,
                            "colors": ["#%02X%02X%02X" % c for c in colors],
                            "aspect": args.aspect,
                            "width": args.width,
                            "height": args.height,
                            "fit": args.fit,
                            "seed_used": str(seed_value),
                            "text_color_spec": (
                                "INVERSE"
                                if any(tc is None for tc in text_colors)
                                else "|".join(["#%02X%02X%02X" % tc for tc in text_colors])
                            ),
                            "outline": args.outline,
                            "font": args.font,
                            "font_size": args.font_size,
                            "text_scale": args.text_scale,
                            "image_map_file": str(Path(args.image_map)) if args.image_map else None,
                            "shuffle_text": bool(args.shuffle_text),
                            "text_density": args.text_density if args.shuffle_text else None,
                            "tint_enabled": bool(tint_enabled),
                            "opacity_pct_list": (
                                [int(round(a * 100 / 255)) for a in opacities] if opacities else None
                            ),
                            "inter": bool(args.inter),
                            "crawl": bool(args.crawl),
                            "slow": bool(args.slow),
                            "medium": bool(args.medium),
                            "fast": bool(args.fast),
                            "hyper": bool(args.hyper),
                            "ms_per_frame": int(ms_per_frame) if not any([args.crawl, args.slow, args.medium, args.fast, args.hyper]) else None,
                        },
                        "computed_metadata": {
                            "generator": "gifmaker",
                            "frames": int(total_frames),
                            "size": [int(W), int(H)],
                            "ms_per_frame": int(ms_per_frame),
                            "mode": mode,
                            "images_used": f"{filled}/{len(image_paths)}",
                            "text_lines_loaded": len(original_text_lines) if original_text_lines else 0,
                            "text_frames_used": sum(1 for t in (text_mapping or []) if t[1]) if text_mapping else None,
                            "random_mapping": (
                                [
                                    (i, (p.name if p else None))
                                    for i, p in enumerate(image_for_frame)
                                ]
                                if not args.image_map
                                else None
                            ),
                            "text_mapping": text_mapping if text_mapping else None,
                        },
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            ).encode("utf-8")
        ),
    )
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()
