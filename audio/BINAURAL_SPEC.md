# Binaural/Isochronic Generator Spec

## Overview

Generate entrainment audio using composable primitives. Supports static multi-tone configurations via CLI and dynamic binaural sweeps via JSON timeline.

---

## CLI Primitives

### `--add-iso`: Add Isochronic Tone

```bash
--add-iso CARRIER,PULSE_RATE,AMPLITUDE_DB,EAR(S)
```

| Parameter | Description |
|-----------|-------------|
| CARRIER | Carrier frequency in Hz |
| PULSE_RATE | Isochronic pulse rate in Hz (0 = continuous) |
| AMPLITUDE_DB | Amplitude in dB (0 = full, -6 = half) |
| EAR | Channel routing: `L`, `R`, or `LR` |

**Example:** `--add-iso 310,5.0,0,L` - 310 Hz carrier, 5 Hz pulse, 0 dB, left channel

### `--add-binaural`: Add Binaural Pair

```bash
--add-binaural CARRIER,BEAT,AMPLITUDE_DB
```

Generates continuous tones (no isochronic modulation):
- Left channel: `carrier - beat/2`
- Right channel: `carrier + beat/2`

**Example:** `--add-binaural 200,5,0` - Creates 197.5 Hz (L) and 202.5 Hz (R) for 5 Hz beat

---

## CLI Usage

### Generate with Preset

```bash
python audio/binaural.py --preset drone --duration 120 -o drone.wav
```

### Generate with Custom Tones

```bash
python audio/binaural.py \
  --add-iso 310,5.0,0,L \
  --add-iso 314,5.0,0,R \
  --add-iso 58,3.25,-6,L \
  --add-iso 62,3.25,-6,R \
  --duration 120 -o custom.wav
```

### Simple Binaural Beat

```bash
python audio/binaural.py --add-binaural 200,5,0 --duration 600 -o simple.ogg
```

### Generate from JSON (with sweep)

```bash
python audio/binaural.py --json-input config.json -o sweep.wav
```

---

## Presets

### `drone`

Replicates the static drone structure with 4 isochronic tones:

| Carrier | Pulse | Amplitude | Ear |
|---------|-------|-----------|-----|
| 310 Hz | 5.0 Hz | 0 dB | L |
| 314 Hz | 5.0 Hz | 0 dB | R |
| 58 Hz | 3.25 Hz | -6 dB | L |
| 62 Hz | 3.25 Hz | -6 dB | R |

This creates:
- ~4 Hz binaural beat on both frequency bands
- Separate isochronic pulses (5 Hz high, 3.25 Hz low)
- L/R ping-pong effect via 100ms interleave (180° offset at 5 Hz, ~117° at 3.25 Hz)

---

## JSON Configuration

For dynamic binaural sweeps, use a JSON configuration file.

### Basic Structure

```json
{
  "duration_sec": 120,
  "fade_in_sec": 1.75,
  "fade_out_sec": 1.75,
  "target_db": -28,

  "layers": [
    {"name": "high", "center_hz": 312, "pulse_hz": 5.0, "amplitude_db": 0},
    {"name": "low", "center_hz": 60, "pulse_hz": 3.25, "amplitude_db": -6}
  ],

  "keyframes": [
    {"time_sec": 0, "binaural_hz": 4.71},
    {"time_sec": 120, "binaural_hz": 4.0}
  ]
}
```

### Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `duration_sec` | Yes | - | Total duration in seconds |
| `layers` | Yes | - | Array of layer definitions |
| `keyframes` | No | - | Array of binaural sweep points |
| `binaural_hz` | No | 0 | Static binaural beat (if no keyframes) |
| `fade_in_sec` | No | 1.75 | Fade in duration |
| `fade_out_sec` | No | 1.75 | Fade out duration |
| `target_db` | No | -28 | Target RMS level |

### Layer Definition

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Layer identifier (for logging) |
| `center_hz` | Yes | Center frequency in Hz |
| `pulse_hz` | Yes | Isochronic pulse rate (0 = continuous) |
| `amplitude_db` | Yes | Amplitude in dB |

### Keyframes

Keyframes define binaural beat values over time. Linear interpolation is used between points.

- All layers share the same binaural beat (sweep in lockstep)
- At each sample: `L = center_hz - binaural_hz/2`, `R = center_hz + binaural_hz/2`

### Static JSON (no keyframes)

For static configuration without sweeps:

```json
{
  "duration_sec": 120,
  "layers": [
    {"name": "high", "center_hz": 312, "pulse_hz": 5.0, "amplitude_db": 0},
    {"name": "low", "center_hz": 60, "pulse_hz": 3.25, "amplitude_db": -6}
  ],
  "binaural_hz": 4.0
}
```

---

## Output Formats

Format is auto-detected from file extension:

| Extension | Format | Details |
|-----------|--------|---------|
| `.wav` | WAV | 16-bit, 44100 Hz, uncompressed |
| `.mp3` | MP3 | 192 kbps (requires pydub/ffmpeg) |
| `.ogg` | Ogg Vorbis | (requires pydub/ffmpeg) |

---

## CLI Reference

```
python audio/binaural.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--add-iso SPEC` | - | Add isochronic tone (repeatable) |
| `--add-binaural SPEC` | - | Add binaural pair (repeatable) |
| `--preset NAME` | - | Use predefined configuration |
| `--json-input FILE` | - | Load from JSON file |
| `--duration SECS` | 600 | Duration in seconds |
| `--fade-in SECS` | 1.75 | Fade in duration |
| `--fade-out SECS` | 1.75 | Fade out duration |
| `--level DB` | -28 | Target RMS level in dB |
| `--interleave-ms MS` | 100 | R channel isochronic phase offset (creates L/R ping-pong) |
| `-o, --output FILE` | output.wav | Output file path |

---

## Technical Details

### Signal Generation

**Isochronic Envelope:** Raised cosine for smooth pulsing
```python
envelope = 0.5 * (1 + cos(2*pi*rate*t + pi))  # 0 to 1
```

**Phase-Continuous Sweep:** For dynamic binaural, uses cumulative phase
```python
phase = cumsum(2*pi*freq/sample_rate)
signal = sin(phase)
```

### Output Specifications

| Property | Value |
|----------|-------|
| Sample rate | 44100 Hz |
| Bit depth | 16-bit |
| Channels | Stereo |
| Default level | -28 dB RMS |
| Mixed level | -1 dB peak |

---

## Dependencies

```
numpy
scipy
pydub (for MP3/OGG export)
ffmpeg (required by pydub)
```

---

## Verification

Use `analysis/scripts/binaural_analyzer.py` to verify generated audio matches expected parameters.

### Test 1: Drone Preset (Static 4 Hz)

```bash
# Generate
python audio/binaural.py --preset drone --duration 30 -o test_drone.wav

# Analyze
python analysis/scripts/binaural_analyzer.py test_drone.wav --window 10 --step 5
```

**Expected output:**
- Carrier ranges detected: ~43-77 Hz (low), ~290-334 Hz (high)
- Binaural: 4.0 Hz static throughout
- Dominant: R (right channel has higher frequency)

### Test 2: JSON Sweep (4.71 → 4.0 Hz)

Create `test_sweep.json`:
```json
{
  "duration_sec": 120,
  "layers": [
    {"name": "high", "center_hz": 312, "pulse_hz": 5.0, "amplitude_db": 0},
    {"name": "low", "center_hz": 60, "pulse_hz": 3.25, "amplitude_db": -6}
  ],
  "keyframes": [
    {"time_sec": 0, "binaural_hz": 4.71},
    {"time_sec": 120, "binaural_hz": 4.0}
  ]
}
```

```bash
# Generate
python audio/binaural.py --json-input test_sweep.json -o test_sweep.wav

# Analyze
python analysis/scripts/binaural_analyzer.py test_sweep.wav --window 10 --step 5
```

**Expected output:**
- Start: ~4.65 Hz (slightly lower due to window averaging)
- End: ~4.01 Hz
- Sweep: downward (Δ -0.6 to -0.7 Hz)

### Reference: Bimbo Drone (from BINAURAL_ANALYSIS_SUMMARY.md)

| Property | Expected Value |
|----------|----------------|
| High carriers | L=310 Hz, R=314 Hz |
| Low carriers | L=58 Hz, R=62 Hz |
| Binaural beat | 4.71 → 4.00 Hz sweep (2 min) |
| Isochronic high | ~5 Hz |
| Isochronic low | ~3.25 Hz |
| Low band level | -6 dB relative to high |
| Interleave | 100ms (R channel delayed) |

---

## Entrainment Frequency Reference

| Frequency | Band | Associated State |
|-----------|------|------------------|
| 0.5-4 Hz | Delta | Deep sleep, unconscious |
| 3.2 Hz | Delta/Theta | Deep trance |
| 4-8 Hz | Theta | Meditation, creativity |
| 5 Hz | Theta | Light trance, suggestibility |
| 7.83 Hz | Theta/Alpha | Schumann resonance |
| 8-12 Hz | Alpha | Relaxed focus |
| 10 Hz | Alpha | Alert relaxation |
| 12-30 Hz | Beta | Active thinking |
