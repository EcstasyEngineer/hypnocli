Pollytools — Script Processing + AWS Polly Integration

Status
- Scoping in progress; details will be finalized as requirements are consolidated. This package placeholder captures intent and initial direction.

Purpose
- Provide a small toolkit to:
  - Parse and normalize script text for TTS.
  - Apply pronunciation/alias replacements via an external dictionary (not embedded in the script).
  - Remove non‑speech effect notes from the text before synthesis.
  - Send the cleaned text to Amazon Polly and retrieve audio artifacts.

Initial Goals
- Replacement dictionary: JSON/YAML map of term → pronunciation (or alias) applied prior to TTS; maintained separately from source scripts.
- Effect note stripping: configurable patterns (e.g., bracketed or parenthetical markers) removed before synthesis.
- Batch processing: handle single files or folders; stable IDs per chunk for traceability.
- Polly configuration: voice, engine (standard/neural), language/locale, output format (mp3/ogg/wav), rate/pitch via SSML when provided.
- Caching: optional on‑disk cache keyed by normalized text + voice + engine + format to avoid repeat synth calls.
- Outputs: audio files in an output directory with a manifest (JSON) describing inputs, replacements applied, and Polly parameters.

Non‑Goals (initial)
- Custom voice cloning or non‑Polly engines.
- Fine‑grained prosody editing beyond Polly SSML.
- Credentials management beyond standard AWS mechanisms.

CLI Sketch (to be finalized)
- Example (subject to change):
  - `python3 -m pollytools --input scripts/lines.txt --replacements config/replacements.json --voice Joanna --engine neural --format mp3 --out outputs/`
  - Options (planned): `--strip-effects on|off`, `--effects-pattern "\\[.*?\\]|\(FX:.*?\)"`, `--language-code en-US`, `--sample-rate 22050`, `--cache .pollycache`.

Prerequisites
- AWS account and credentials configured (e.g., via environment or `~/.aws/credentials`). See Amazon Polly pricing and limits.

Next Steps
- Finalize replacement dictionary schema and effect‑note patterns.
- Define chunking rules and manifest format.
- Implement a minimal CLI and SDK wrapper with retries and caching.

