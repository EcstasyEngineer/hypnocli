# Binaural/Isochronic Generator Spec

## Overview

Generate entrainment audio using composable primitives. Supports:
- **CLI mode**: Static multi-tone configurations (`--add-iso`, `--add-binaural`, `--add-hybrid`)
- **JSON mode**: Per-layer keyframing of all parameters (center_hz, pulse_hz, amplitude_db, binaural_hz)
- **Presets**: `bimbo-drone`, `reactor`, `descent`

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

### `--add-hybrid`: Add Hybrid Layer

```bash
--add-hybrid CARRIER,BEAT,PULSE_RATE,AMPLITUDE_DB
```

Combines binaural + isochronic on the same carrier:
- Left channel: `carrier - beat/2`, modulated at `pulse_rate` Hz
- Right channel: `carrier + beat/2`, modulated at `pulse_rate` Hz

**Example:** `--add-hybrid 312,3,5,0` - 312 Hz carrier, 3 Hz binaural beat, 5 Hz isochronic pulse

---

## Presets

### `bimbo-drone`

Two hybrid layers matching source material analysis (3.0 Hz binaural, dual isochronic):

| Layer | Center | Pulse | Amplitude | Binaural |
|-------|--------|-------|-----------|----------|
| high | 312 Hz | 5.0 Hz | 0 dB | 3.0 Hz |
| low | 60 Hz | 3.25 Hz | -6 dB | 3.0 Hz |

```bash
python audio/binaural/binaural.py --preset bimbo-drone --duration 1200 -o drone.ogg
```

### `reactor`

Four layers in musical fifth ratios with max-entropy pulse rates and per-layer binaural:

| Layer | Center | Pulse | Amplitude | Binaural |
|-------|--------|-------|-----------|----------|
| high | 202.5 Hz | 7.0 Hz | 0 dB | 4.0 Hz |
| mid_high | 135 Hz | 4.6 Hz | -4 dB | 3.5 Hz |
| mid_low | 90 Hz | 3.3 Hz | -6 dB | 3.0 Hz |
| low | 60 Hz | 2.55 Hz | -8 dB | 2.5 Hz |

```bash
python audio/binaural/binaural.py --preset reactor -o reactor.ogg
```

### `descent`

Three layers targeting progressive theta-to-delta deepening:

| Layer | Center | Pulse | Amplitude | Binaural |
|-------|--------|-------|-----------|----------|
| theta | 200 Hz | 5.0 Hz | 0 dB | 4.0 Hz |
| deep_theta | 120 Hz | 3.25 Hz | -3 dB | 3.0 Hz |
| delta | 55 Hz | 2.55 Hz | -6 dB | 2.0 Hz |

Pulse rates chosen for max entropy (all pairs sync ≥4s). Low carriers per Pratt et al. (2010) for stronger entrainment response.

```bash
python audio/binaural/binaural.py --preset descent --duration 1200 -o descent.ogg
```

---

## JSON Configuration

### Polymorphic Parameter Values

All numeric layer fields accept **either a static number or an array of keyframes**:

```json
// Static value
{"center_hz": 312}

// Keyframed value (linear interpolation between points)
{"center_hz": [
  {"time_sec": 0, "value": 312},
  {"time_sec": 600, "value": 200}
]}
```

This applies to: `center_hz`, `pulse_hz`, `amplitude_db`, `binaural_hz`

### Per-Layer Binaural

Each layer can specify its own `binaural_hz` (static or keyframed). If omitted, inherits from the global `binaural_hz` or `keyframes`.

```json
{
  "duration_sec": 120,
  "ear_priority": "R",
  "layers": [
    {
      "name": "high",
      "center_hz": 312,
      "pulse_hz": 5.0,
      "amplitude_db": 0,
      "binaural_hz": [
        {"time_sec": 0, "value": 4.0},
        {"time_sec": 120, "value": 2.0}
      ]
    },
    {
      "name": "low",
      "center_hz": 60,
      "pulse_hz": 3.25,
      "amplitude_db": -6,
      "binaural_hz": 4.0
    }
  ]
}
```

### Global Config Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `duration_sec` | Yes | - | Total duration in seconds |
| `layers` | Yes | - | Array of layer definitions |
| `keyframes` | No | - | Global binaural sweep `[{time_sec, binaural_hz}]` (legacy format) |
| `binaural_hz` | No | 0 | Global static binaural beat (fallback if layer has none) |
| `ear_priority` | No | `"R"` | Which ear gets higher carrier: `"L"` or `"R"` |
| `fade_in_sec` | No | 1.75 | Fade in duration |
| `fade_out_sec` | No | 1.75 | Fade out duration |
| `target_db` | No | -28 | Target RMS level |

### Layer Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | No | string | Layer identifier (for logging) |
| `center_hz` | Yes | number \| keyframes | Center carrier frequency |
| `pulse_hz` | Yes | number \| keyframes | Isochronic pulse rate (0 = continuous) |
| `amplitude_db` | Yes | number \| keyframes | Amplitude in dB |
| `binaural_hz` | No | number \| keyframes | Per-layer binaural offset (inherits global if absent) |

### Binaural Inheritance

1. If a layer has `binaural_hz` -> use that (static or keyframed)
2. Else if config has `keyframes` -> use global keyframes (legacy `{time_sec, binaural_hz}` format)
3. Else if config has `binaural_hz` -> use global static value
4. Else -> 0 Hz (no binaural)

### Ear Priority

`ear_priority` controls which ear gets the higher carrier frequency:
- `"R"` (default): `freq_right = center + binaural/2`, `freq_left = center - binaural/2`
- `"L"`: Reversed (left ear gets higher frequency)

Not keyframeable - set once per config.

---

## Advanced Examples

### Keyframed Center Frequency Sweep

```json
{
  "duration_sec": 600,
  "ear_priority": "R",
  "layers": [
    {
      "name": "descending",
      "center_hz": [
        {"time_sec": 0, "value": 315},
        {"time_sec": 600, "value": 200}
      ],
      "pulse_hz": [
        {"time_sec": 0, "value": 6.5},
        {"time_sec": 600, "value": 2.5}
      ],
      "amplitude_db": 0,
      "binaural_hz": [
        {"time_sec": 0, "value": 4.5},
        {"time_sec": 600, "value": 2.0}
      ]
    }
  ]
}
```

### Static JSON (Legacy Format, Still Supported)

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

### Global Keyframes (Legacy Format, Still Supported)

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
python audio/binaural/binaural.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--add-iso SPEC` | - | Add isochronic tone (repeatable) |
| `--add-binaural SPEC` | - | Add binaural pair (repeatable) |
| `--add-hybrid SPEC` | - | Add hybrid binaural+isochronic layer (repeatable) |
| `--preset NAME` | - | Use predefined config (`bimbo-drone`, `reactor`, `descent`) |
| `--json-input FILE` | - | Load from JSON file |
| `--duration SECS` | 600 / preset | Duration in seconds |
| `--fade-in SECS` | 1.75 | Fade in duration |
| `--fade-out SECS` | 1.75 | Fade out duration |
| `--level DB` | -28 | Target RMS level in dB |
| `--interleave-ms MS` | 100 | R channel isochronic phase offset (CLI mode only) |
| `-o, --output FILE` | output.wav | Output file path |

---

## Technical Details

### Signal Generation

**Isochronic Envelope (static rate):** Raised cosine for smooth pulsing
```python
envelope = 0.5 * (1 + cos(2*pi*rate*t + pi))  # 0 to 1
```

**Isochronic Envelope (dynamic rate):** Phase-continuous cumulative integration
```python
phase = cumsum(2*pi*pulse_hz_array/sample_rate)
envelope = 0.5 * (1 + cos(phase + pi + offset))
```
Maintains exact 180-degree L/R anti-phase regardless of rate changes. No clipping.

**Phase-Continuous Carrier Sweep:** Cumulative phase for smooth frequency changes
```python
phase = cumsum(2*pi*freq/sample_rate)
signal = sin(phase)
```

**Dynamic Amplitude:** Per-sample dB to linear conversion
```python
amplitude = 10^(amplitude_db_array / 20)
```

### Output Specifications

| Property | Value |
|----------|-------|
| Sample rate | 44100 Hz |
| Bit depth | 16-bit |
| Channels | Stereo |
| Default level | -28 dB RMS |

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

Use `audio/binaural/binaural_analyzer.py` to verify generated audio.

### Auto-detect Mode

```bash
python audio/binaural/binaural_analyzer.py audio.wav --window 10 --step 5
```

Automatically detects all carrier pairs and tracks binaural beats per carrier over time.

### Known Carriers Mode

```bash
python audio/binaural/binaural_analyzer.py audio.wav --expected-carriers 60,90,135,202.5
```

### Verify Against Config

```bash
python audio/binaural/binaural_analyzer.py generated.wav --verify config.json
```

Compares measured binaural beats to expected values from the JSON config. Reports PASS/FAIL per window.

### Spectrum Debug

```bash
python audio/binaural/binaural_analyzer.py audio.wav --spectrum --start 0 --duration 60
```

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
