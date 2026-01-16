#!/usr/bin/env python3
"""
Quick SSML test renderer for breath timing samples.
"""

import subprocess
import os
import sys
from pathlib import Path

def get_aws_creds():
    """Load AWS credentials from .env or environment."""
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    creds = {}

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    creds[key.strip()] = value.strip().strip('"\'')

    return {
        'access_key': os.environ.get('AWS_ACCESS_KEY_ID', creds.get('AWS_ACCESS_KEY_ID', '')),
        'secret_key': os.environ.get('AWS_SECRET_ACCESS_KEY', creds.get('AWS_SECRET_ACCESS_KEY', '')),
        'region': os.environ.get('AWS_REGION', creds.get('AWS_REGION', 'us-east-1')),
    }

def render_ssml(ssml_text: str, output_path: str, voice: str = "Salli", engine: str = "neural") -> bool:
    """Render SSML text to audio."""
    creds = get_aws_creds()

    cmd = [
        "aws", "--region", creds['region'],
        "polly", "synthesize-speech",
        "--text-type", "ssml",
        "--text", ssml_text,
        "--output-format", "mp3",
        "--voice-id", voice,
        "--engine", engine,
        output_path
    ]

    env = os.environ.copy()
    if creds.get('access_key'):
        env['AWS_ACCESS_KEY_ID'] = creds['access_key']
    if creds.get('secret_key'):
        env['AWS_SECRET_ACCESS_KEY'] = creds['secret_key']

    print(f"Rendering with voice={voice}, engine={engine}...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False

    print(f"Success: {output_path}")
    return True

def add_reverb(input_path: str, output_path: str, reverb_preset: str = "subtle") -> bool:
    """Add reverb using ffmpeg's aecho or reverb filter."""

    # Reverb presets using aecho (in_gain, out_gain, delays, decays)
    presets = {
        # Subtle - slight room ambiance
        "subtle": "aecho=0.8:0.7:40|60:0.3|0.2",
        # Medium - noticeable but not overwhelming
        "medium": "aecho=0.8:0.6:60|100:0.4|0.3",
        # Deep - more pronounced, hypnotic
        "deep": "aecho=0.8:0.5:80|120|160:0.4|0.3|0.2",
        # Cathedral - very spacious
        "cathedral": "aecho=0.8:0.4:100|200|300:0.5|0.4|0.3",
    }

    filter_str = presets.get(reverb_preset, presets["subtle"])

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", filter_str,
        output_path
    ]

    print(f"Adding reverb preset '{reverb_preset}'...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False

    print(f"Success: {output_path}")
    return True

def main():
    script_dir = Path(__file__).parent

    # Read SSML sample
    ssml_path = script_dir / "breath_sample_ssml.txt"
    with open(ssml_path) as f:
        ssml_text = f.read()

    # Render dry (no reverb)
    dry_output = script_dir / "breath_sample_dry.mp3"
    if not render_ssml(ssml_text, str(dry_output)):
        sys.exit(1)

    # Create reverb variants
    for preset in ["subtle", "medium", "deep"]:
        reverb_output = script_dir / f"breath_sample_{preset}_reverb.mp3"
        add_reverb(str(dry_output), str(reverb_output), preset)

    print("\n=== Generated files ===")
    for f in sorted(script_dir.glob("breath_sample_*.mp3")):
        print(f"  {f.name}")

if __name__ == "__main__":
    main()
