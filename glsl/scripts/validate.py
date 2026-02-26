#!/usr/bin/env python3
"""
validate.py
-----------
Validate a GLSL shader: optional compile check + headless WebGL render.

Usage:
    python3 validate.py shaders/<id>.glsl               # render to renders/<id>.png
    python3 validate.py shaders/<id>.glsl --manual       # write HTML, print path, wait for PNG
    python3 validate.py shaders/<id>.glsl --time 4.0     # render at t=4.0s
    python3 validate.py shaders/<id>.glsl --no-compile   # skip glslangValidator

Exit codes:
    0  success (renders/<id>.png written)
    1  black frame or compile error
    2  unexpected error
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

GLSL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = GLSL_DIR / "templates"
RENDERS_DIR = GLSL_DIR / "renders"
SHADERS_DIR = GLSL_DIR / "shaders"
WRAPPER_TEMPLATE = TEMPLATES_DIR / "shadertoy_wrapper.html"

# Shadertoy uniform declarations needed for glslangValidator
SHADERTOY_HARNESS = """\
#version 300 es
precision highp float;
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;
out vec4 _fragColor;
// mainImage stub for validator
"""


def get_shader_id(shader_path: Path) -> str:
    return shader_path.stem


def compile_check(shader_path: Path) -> tuple[bool, str]:
    """Run glslangValidator on the shader. Returns (ok, error_msg)."""
    glslang = shutil.which("glslangValidator")
    if not glslang:
        return True, "(glslangValidator not found, skipping compile check)"

    # Write harness + shader to temp file
    glsl_src = SHADERTOY_HARNESS + shader_path.read_text()
    with tempfile.NamedTemporaryFile(suffix=".frag", mode="w", delete=False) as f:
        f.write(glsl_src)
        tmp = f.name

    try:
        result = subprocess.run(
            [glslang, "-S", "frag", tmp],
            capture_output=True,
            text=True,
            timeout=10,
        )
        ok = result.returncode == 0
        err = (result.stdout + result.stderr).strip()
        return ok, err
    except subprocess.TimeoutExpired:
        return False, "glslangValidator timed out"
    finally:
        os.unlink(tmp)


def strip_shader_preamble(shader_src: str) -> str:
    """
    Remove lines that conflict with the HTML wrapper's header:
    - uniform declarations (already in FRAG_HEADER)
    - #version directives (already in FRAG_HEADER)
    - precision qualifiers (already in FRAG_HEADER)
    - out vec4 declarations (already in FRAG_HEADER)
    """
    clean_lines = []
    for line in shader_src.splitlines():
        stripped = line.strip()
        if (stripped.startswith("#version")
                or stripped.startswith("precision ")
                or stripped.startswith("uniform vec3 iResolution")
                or stripped.startswith("uniform float iTime")
                or stripped.startswith("uniform vec4 iMouse")
                or stripped.startswith("out vec4 fragColor")):
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines)


def inject_shader(shader_src: str, render_time: float) -> str:
    """Return the HTML wrapper with the shader injected."""
    template = WRAPPER_TEMPLATE.read_text()
    # Set render time in JS
    template = template.replace("const RENDER_TIME = 2.0;", f"const RENDER_TIME = {render_time};")

    # Strip conflicting preamble declarations
    clean_src = strip_shader_preamble(shader_src)

    # Escape backtick for JS template literal (backtick would break the string)
    escaped = clean_src.replace("\\", "\\\\").replace("`", "\\`")
    injected = f"const INJECTED_SHADER = `{escaped}`;"
    template = template.replace("// GLSL_FRAGMENT_SHADER_PLACEHOLDER", injected)
    return template


def render_headless(html_content: str, output_png: Path) -> tuple[bool, str]:
    """
    Launch headless Playwright chromium, render the WebGL canvas, save PNG.
    Returns (ok, error_msg).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "playwright not installed — run: pip install playwright"

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html_content)
        tmp_html = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--no-sandbox",
                ],
            )
            page = browser.new_page()
            page.goto(f"file://{tmp_html}")

            # Wait for render complete signal (title changes) or timeout
            try:
                page.wait_for_function(
                    "document.title.startsWith('RENDER_COMPLETE') || document.title.startsWith('GLSL_ERROR') || document.title.startsWith('WEBGL_ERROR') || document.title.startsWith('LINK_ERROR')",
                    timeout=15000,
                )
            except Exception:
                title = page.title()
                browser.close()
                return False, f"Timeout waiting for render (title: {title!r})"

            title = page.title()
            if not title.startswith("RENDER_COMPLETE"):
                browser.close()
                return False, f"Shader error: {title}"

            # Extract canvas pixel data as base64 PNG
            img_data = page.evaluate(
                "document.getElementById('c').toDataURL('image/png').split(',')[1]"
            )
            browser.close()

            if not img_data:
                return False, "Empty canvas data"

            output_png.parent.mkdir(parents=True, exist_ok=True)
            output_png.write_bytes(base64.b64decode(img_data))
            return True, ""

    except Exception as e:
        return False, str(e)
    finally:
        os.unlink(tmp_html)


def check_black_frame(png_path: Path, threshold: float = 0.02) -> bool:
    """
    Returns True if the image is effectively a black frame.
    Samples 100 random pixels; if stddev < threshold across all channels, it's black.
    """
    try:
        from PIL import Image
        import random
    except ImportError:
        print("WARNING: PIL not available, skipping black-frame check", file=sys.stderr)
        return False

    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    pixels = img.load()

    samples = []
    for _ in range(100):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        r, g, b = pixels[x, y]
        samples.extend([r / 255.0, g / 255.0, b / 255.0])

    mean = sum(samples) / len(samples)
    variance = sum((s - mean) ** 2 for s in samples) / len(samples)
    stddev = variance ** 0.5

    return stddev < threshold


def manual_mode(html_content: str, output_png: Path):
    """Write HTML to temp file, print path, poll for PNG."""
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, dir="/tmp") as f:
        f.write(html_content)
        tmp_html = f.name

    print(f"\n[MANUAL MODE]")
    print(f"Open this file in Chrome/Firefox with WebGL enabled:")
    print(f"  file://{tmp_html}")
    print(f"\nExpected output PNG: {output_png}")
    print("After viewing, manually save the canvas screenshot to that path.")
    print("Polling... (Ctrl+C to abort)")

    try:
        while not output_png.exists():
            time.sleep(1)
        print(f"PNG detected: {output_png}")
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Validate and render a GLSL shader")
    parser.add_argument("shader", help="Path to .glsl file")
    parser.add_argument("--output", help="Output PNG path (default: renders/<id>.png)")
    parser.add_argument("--time", type=float, default=2.0, help="Render time in seconds (default: 2.0)")
    parser.add_argument("--manual", action="store_true", help="Manual mode: write HTML, wait for PNG")
    parser.add_argument("--no-compile", action="store_true", help="Skip glslangValidator")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error output")
    args = parser.parse_args()

    shader_path = Path(args.shader)
    if not shader_path.exists():
        # Try relative to shaders dir
        alt = SHADERS_DIR / shader_path.name
        if alt.exists():
            shader_path = alt
        else:
            print(f"ERROR: shader not found: {args.shader}", file=sys.stderr)
            sys.exit(2)

    shader_id = get_shader_id(shader_path)
    output_png = Path(args.output) if args.output else RENDERS_DIR / f"{shader_id}.png"

    def log(msg):
        if not args.quiet:
            print(msg)

    log(f"Validating: {shader_path.name}")

    # Step 1: Compile check
    if not args.no_compile:
        ok, msg = compile_check(shader_path)
        if not ok:
            print(f"COMPILE ERROR: {msg}", file=sys.stderr)
            sys.exit(1)
        log(f"  compile: {'OK' if ok else 'SKIP'} {msg if msg.startswith('(') else ''}")

    # Step 2: Inject shader into HTML
    shader_src = shader_path.read_text()
    html = inject_shader(shader_src, args.time)

    # Step 3: Render
    if args.manual:
        manual_mode(html, output_png)
    else:
        log(f"  rendering at t={args.time}s ...")
        ok, err = render_headless(html, output_png)
        if not ok:
            print(f"RENDER ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        log(f"  rendered: {output_png}")

    # Step 4: Black-frame detection
    if output_png.exists():
        is_black = check_black_frame(output_png)
        if is_black:
            print(f"BLACK FRAME: shader produced a black image — discarding", file=sys.stderr)
            output_png.unlink()
            sys.exit(1)
        log(f"  black-frame check: PASS")

    log(f"  OK → {output_png}")
    sys.exit(0)


if __name__ == "__main__":
    main()
