#!/usr/bin/env python3
"""
Session Builder
---------------
Assembles hypnosis sessions from plan.json files, scripts, or pre-rendered audio.

Usage:
    python build_session.py session_name module1 module2 module3 ... --dominant-title Master
    python build_session.py good_girl intro blank suggestibility brainwashing ... --dominant-title Goddess

Modules can be specified as:
    - Module name (looks in ../script/modules/{name}/)
    - Path to plan.json
    - Path to script.txt
    - Path to .mp3

The script will:
1. Render plan.json -> script.txt if needed
2. Validate [dominant] placeholders and replace with --dominant-title
3. Check for pronoun issues near [dominant] placeholders
4. Render script.txt -> .mp3 if needed
5. Concatenate all modules with 4s silence prefix
6. Generate binaural drone (voice duration + 10s)
7. Mix voice + drone into final session

Output:
    {session_name}.mp3          - Final mixed session
    {session_name}_voice.mp3    - Voice-only track
    {session_name}_drone.wav    - Binaural track

Quality Checks:
    - FAIL: [dominant] found in script without --dominant-title specified
    - WARN: Gendered pronouns (he/him/his/she/her/hers) found near [dominant]
"""

import argparse
import subprocess
import sys
import os
import re
import tempfile
from pathlib import Path


# Paths relative to this script
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
MODULES_DIR = REPO_ROOT / "script" / "loops"
AUDIO_DIR = REPO_ROOT / "audio"
TTS_DIR = REPO_ROOT / "tts"
PHASE_GENERATOR = REPO_ROOT / "script" / "phase_chat_generator.py"
POLLY_RENDERER = TTS_DIR / "render_polly.py"
BINAURAL_GENERATOR = AUDIO_DIR / "binaural.py"

# Session settings
SILENCE_DURATION = 4  # seconds at start
BINAURAL_TAIL = 10    # seconds after voice ends
BINAURAL_PRESET = "ladder"  # 4.125 Hz harmonic

# Dominant title placeholder
DOMINANT_PLACEHOLDER = "[dominant]"
DOMINANT_DEFAULT = "Master"

# Pronoun patterns to check near [dominant]
GENDERED_PRONOUNS = re.compile(r'\b(he|him|his|she|her|hers)\b', re.IGNORECASE)

# TODO: Add reverb processing once we have the right settings
# REVERB_PRESET = None


def check_dominant_placeholder(script_path: Path, dominant_title: str = None) -> tuple[bool, list[str]]:
    """
    Check script for [dominant] placeholders and validate.

    Returns:
        (success, warnings) - success=False means fail-fast, warnings are non-fatal
    """
    if not script_path or not script_path.exists():
        return True, []

    content = script_path.read_text()
    warnings = []

    # Check if [dominant] exists
    has_placeholder = DOMINANT_PLACEHOLDER in content

    if has_placeholder and not dominant_title:
        print(f"\n  ERROR: Script '{script_path.name}' contains {DOMINANT_PLACEHOLDER} placeholder", file=sys.stderr)
        print(f"         but --dominant-title was not specified.", file=sys.stderr)
        print(f"         Use: --dominant-title Master  or  --dominant-title Goddess", file=sys.stderr)
        return False, []

    # Check for gendered pronouns near [dominant]
    if has_placeholder:
        # Find all [dominant] positions and check surrounding context (50 chars each side)
        for match in re.finditer(re.escape(DOMINANT_PLACEHOLDER), content):
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end]

            pronoun_matches = GENDERED_PRONOUNS.findall(context)
            if pronoun_matches:
                # Filter out common false positives (words containing these letters)
                real_pronouns = [p for p in pronoun_matches if p.lower() in ('he', 'him', 'his', 'she', 'her', 'hers')]
                if real_pronouns:
                    warnings.append(f"Pronoun '{real_pronouns[0]}' found near {DOMINANT_PLACEHOLDER} in {script_path.name}")

    return True, warnings


def replace_dominant_placeholder(script_path: Path, dominant_title: str, output_path: Path = None) -> Path:
    """
    Replace [dominant] with the specified title in a script.

    Args:
        script_path: Path to original script
        dominant_title: Title to substitute (e.g., "Master", "Goddess")
        output_path: Optional output path (defaults to temp file)

    Returns:
        Path to processed script (may be original if no placeholders found)
    """
    if not script_path or not script_path.exists():
        return script_path

    content = script_path.read_text()

    if DOMINANT_PLACEHOLDER not in content:
        return script_path

    # Replace placeholder
    processed = content.replace(DOMINANT_PLACEHOLDER, dominant_title)

    # Write to output path or temp file
    if output_path is None:
        output_path = script_path.parent / f"{script_path.stem}_processed{script_path.suffix}"

    output_path.write_text(processed)
    return output_path


def run_command(cmd, description, timeout=300):
    """Run a shell command with error handling."""
    print(f"  {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:500]}", file=sys.stderr)
        return False
    return True


def get_audio_duration(path):
    """Get duration of audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return float(result.stdout.strip())
    return 0


def get_audio_sample_rate(path):
    """Get sample rate of audio file."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return int(result.stdout.strip())
    return 44100


def resolve_module(module_spec):
    """
    Resolve a module specification to its components.

    Returns dict with:
        - name: module name
        - plan_json: path to plan.json (or None)
        - script_txt: path to script.txt (or None)
        - audio_mp3: path to .mp3 (or None)
        - needs_script_gen: bool
        - needs_audio_render: bool
        - is_ssml: bool
    """
    spec = Path(module_spec)

    # If it's a direct path to a file
    if spec.exists():
        if spec.suffix == '.json':
            module_dir = spec.parent
            name = module_dir.name
            script_path = module_dir / "script.txt"
            ssml_path = module_dir / "script_ssml.txt"
            audio_path = AUDIO_DIR / f"{name}.mp3"

            # Prefer SSML if it exists
            if ssml_path.exists():
                script_path = ssml_path
                is_ssml = True
            else:
                is_ssml = False

            return {
                'name': name,
                'plan_json': spec,
                'script_txt': script_path if script_path.exists() else None,
                'audio_mp3': audio_path if audio_path.exists() else None,
                'needs_script_gen': not script_path.exists(),
                'needs_audio_render': not audio_path.exists(),
                'is_ssml': is_ssml,
            }
        elif spec.suffix == '.txt':
            name = spec.stem.replace('script_ssml', '').replace('script', '') or spec.parent.name
            audio_path = AUDIO_DIR / f"{name}.mp3"
            is_ssml = 'ssml' in spec.name
            return {
                'name': name,
                'plan_json': None,
                'script_txt': spec,
                'audio_mp3': audio_path if audio_path.exists() else None,
                'needs_script_gen': False,
                'needs_audio_render': not audio_path.exists(),
                'is_ssml': is_ssml,
            }
        elif spec.suffix == '.mp3':
            return {
                'name': spec.stem,
                'plan_json': None,
                'script_txt': None,
                'audio_mp3': spec,
                'needs_script_gen': False,
                'needs_audio_render': False,
                'is_ssml': False,
            }

    # Otherwise treat as module name - look in loops directory
    module_dir = MODULES_DIR / module_spec
    if module_dir.exists():
        plan_path = module_dir / "plan.json"
        script_path = module_dir / "script.txt"
        ssml_path = module_dir / "script_ssml.txt"
        audio_path = AUDIO_DIR / f"{module_spec}.mp3"

        # Prefer SSML if it exists
        if ssml_path.exists():
            script_path = ssml_path
            is_ssml = True
        else:
            is_ssml = script_path.suffix == '_ssml.txt' if script_path.exists() else False

        return {
            'name': module_spec,
            'plan_json': plan_path if plan_path.exists() else None,
            'script_txt': script_path if script_path.exists() else None,
            'audio_mp3': audio_path if audio_path.exists() else None,
            'needs_script_gen': plan_path.exists() and not script_path.exists(),
            'needs_audio_render': not audio_path.exists(),
            'is_ssml': is_ssml,
        }

    # Check if audio exists directly
    audio_path = AUDIO_DIR / f"{module_spec}.mp3"
    if audio_path.exists():
        return {
            'name': module_spec,
            'plan_json': None,
            'script_txt': None,
            'audio_mp3': audio_path,
            'needs_script_gen': False,
            'needs_audio_render': False,
            'is_ssml': False,
        }

    raise ValueError(f"Cannot resolve module: {module_spec}")


def generate_script(module):
    """Generate script.txt from plan.json using phase_chat_generator."""
    if not module['plan_json']:
        return False

    plan_dir = module['plan_json'].parent
    cmd = [
        "python3", str(PHASE_GENERATOR),
        "--plan", str(module['plan_json']),
        "--out_dir", str(plan_dir)
    ]

    if run_command(cmd, f"Generating script for {module['name']}", timeout=180):
        # Update module with new script path
        script_path = plan_dir / "script.txt"
        ssml_path = plan_dir / "script_ssml.txt"
        if ssml_path.exists():
            module['script_txt'] = ssml_path
            module['is_ssml'] = True
        elif script_path.exists():
            module['script_txt'] = script_path
        return True
    return False


def render_audio(module):
    """Render script.txt to .mp3 using render_polly."""
    if not module['script_txt']:
        return False

    output_path = AUDIO_DIR / f"{module['name']}.mp3"
    cmd = [
        "python3", str(POLLY_RENDERER),
        str(module['script_txt']),
        str(output_path)
    ]

    if module['is_ssml']:
        cmd.append("--ssml")

    if run_command(cmd, f"Rendering audio for {module['name']}", timeout=600):
        module['audio_mp3'] = output_path
        return True
    return False


def create_silence(duration, sample_rate, output_path):
    """Create silence audio file matching target sample rate."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate}:cl=mono",
        "-t", str(duration),
        "-acodec", "libmp3lame",
        str(output_path)
    ]
    return run_command(cmd, f"Creating {duration}s silence")


def concatenate_audio(audio_files, output_path):
    """Concatenate audio files using ffmpeg."""
    # Create concat list
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for audio in audio_files:
            f.write(f"file '{audio}'\n")
        concat_list = f.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            str(output_path)
        ]
        return run_command(cmd, "Concatenating audio files", timeout=300)
    finally:
        os.unlink(concat_list)


def generate_binaural(duration, output_path, preset=BINAURAL_PRESET):
    """Generate binaural drone using binaural.py."""
    cmd = [
        "python3", str(BINAURAL_GENERATOR),
        "bambi",
        "--preset", preset,
        "--duration", str(int(duration)),
        "-o", str(output_path)
    ]
    return run_command(cmd, f"Generating binaural ({preset}, {int(duration)}s)", timeout=300)


def mix_voice_and_drone(voice_path, drone_path, output_path):
    """Mix voice and drone using ffmpeg."""
    # Note: normalize=0 prevents volume boost when voice drops out at end
    cmd = [
        "ffmpeg", "-y",
        "-i", str(voice_path),
        "-i", str(drone_path),
        "-filter_complex",
        "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[voice];"
        "[1:a][voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[out]",
        "-map", "[out]",
        "-acodec", "libmp3lame", "-q:a", "2",
        str(output_path)
    ]
    return run_command(cmd, "Mixing voice and binaural", timeout=600)


def build_session(session_name, modules, output_dir=None, dominant_title=None):
    """Build a complete session from modules."""
    if output_dir is None:
        output_dir = SCRIPT_DIR
    output_dir = Path(output_dir)

    print(f"\n=== Building Session: {session_name} ===\n")

    if dominant_title:
        print(f"Dominant title: {dominant_title}")

    # Resolve all modules
    print("\nResolving modules...")
    resolved = []
    for mod in modules:
        try:
            resolved.append(resolve_module(mod))
            print(f"  ✓ {mod}")
        except ValueError as e:
            print(f"  ✗ {e}", file=sys.stderr)
            return False

    # Generate scripts if needed
    for mod in resolved:
        if mod['needs_script_gen']:
            if not generate_script(mod):
                print(f"  ✗ Failed to generate script for {mod['name']}", file=sys.stderr)
                return False
            mod['needs_audio_render'] = True  # Now needs rendering

    # Quality check: validate [dominant] placeholders
    print("\nValidating scripts...")
    all_warnings = []
    for mod in resolved:
        if mod['script_txt']:
            success, warnings = check_dominant_placeholder(mod['script_txt'], dominant_title)
            if not success:
                return False
            all_warnings.extend(warnings)

    if all_warnings:
        print("\n  WARNINGS (pronoun issues near [dominant]):")
        for warn in all_warnings:
            print(f"    ⚠ {warn}")
        print()

    # Replace [dominant] placeholders if dominant_title specified
    if dominant_title:
        print(f"\nProcessing [dominant] → {dominant_title}...")
        for mod in resolved:
            if mod['script_txt']:
                processed = replace_dominant_placeholder(mod['script_txt'], dominant_title)
                if processed != mod['script_txt']:
                    print(f"  ✓ Processed {mod['name']}")
                    mod['script_txt'] = processed
                    mod['needs_audio_render'] = True  # Re-render with new text

    # Render audio if needed
    for mod in resolved:
        if mod['needs_audio_render']:
            if not render_audio(mod):
                print(f"  ✗ Failed to render audio for {mod['name']}", file=sys.stderr)
                return False

    # Verify all audio exists
    audio_files = []
    for mod in resolved:
        if not mod['audio_mp3'] or not mod['audio_mp3'].exists():
            print(f"  ✗ Missing audio for {mod['name']}", file=sys.stderr)
            return False
        audio_files.append(mod['audio_mp3'])

    # Get sample rate from first audio file
    sample_rate = get_audio_sample_rate(audio_files[0])
    print(f"\nSample rate: {sample_rate} Hz")

    # Create silence prefix
    silence_path = output_dir / "silence_prefix.mp3"
    if not create_silence(SILENCE_DURATION, sample_rate, silence_path):
        return False

    # Concatenate: silence + all modules
    voice_path = output_dir / f"{session_name}_voice.mp3"
    all_audio = [silence_path] + audio_files
    print(f"\nConcatenating {len(all_audio)} files...")
    if not concatenate_audio(all_audio, voice_path):
        return False

    # Get voice duration
    voice_duration = get_audio_duration(voice_path)
    print(f"Voice duration: {voice_duration:.1f}s ({voice_duration/60:.1f} min)")

    # Generate binaural
    binaural_duration = voice_duration + BINAURAL_TAIL
    drone_path = output_dir / f"{session_name}_drone.wav"
    if not generate_binaural(binaural_duration, drone_path):
        return False

    # Mix voice + drone
    final_path = output_dir / f"{session_name}.mp3"
    if not mix_voice_and_drone(voice_path, drone_path, final_path):
        return False

    # Cleanup
    if silence_path.exists():
        silence_path.unlink()

    # Report
    final_duration = get_audio_duration(final_path)
    final_size = final_path.stat().st_size / (1024 * 1024)

    print(f"\n=== Session Complete ===")
    print(f"  Output: {final_path}")
    print(f"  Duration: {final_duration:.1f}s ({final_duration/60:.1f} min)")
    print(f"  Size: {final_size:.1f} MB")
    print(f"  Voice: {voice_path}")
    print(f"  Drone: {drone_path}")

    return True


def main():
    global BINAURAL_PRESET

    parser = argparse.ArgumentParser(
        description="Build hypnosis session from modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s good_girl intro blank suggestibility --dominant-title Master
  %(prog)s goddess_session intro harem wakener --dominant-title Goddess
  %(prog)s test_session script/modules/intro/plan.json audio/blank.mp3
  %(prog)s my_session --output-dir ./output intro blank wakener --dominant-title Master

Note: --dominant-title is REQUIRED if any module contains [dominant] placeholders.
      Common values: Master, Goddess, Mistress, Owner, Daddy, Mommy
"""
    )
    parser.add_argument("session_name", help="Name for the output session")
    parser.add_argument("modules", nargs="+", help="Modules to include (names, paths to plan.json/script.txt/mp3)")
    parser.add_argument("--output-dir", "-o", default=None, help="Output directory (default: current)")
    parser.add_argument("--dominant-title", "-d", default=None,
                        help="Title for dominant (e.g., Master, Goddess). REQUIRED if scripts contain [dominant]")
    parser.add_argument("--binaural-preset", default=BINAURAL_PRESET, help=f"Binaural preset (default: {BINAURAL_PRESET})")

    args = parser.parse_args()
    BINAURAL_PRESET = args.binaural_preset

    success = build_session(args.session_name, args.modules, args.output_dir, args.dominant_title)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
