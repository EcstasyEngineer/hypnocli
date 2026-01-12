# Binaural/Isochronic Generator Spec

## Overview

Generate entrainment audio with multiple modes ranging from simple binaural beats to complex multi-layer isochronic designs.

---

## Modes

### Mode 1: `simple`
Basic binaural beat - continuous tones with frequency difference between L/R.

**Parameters:**
- `carrier`: Base frequency in Hz (default: 200)
- `beat`: Binaural beat frequency in Hz (default: 5)
- `duration`: Length in seconds

**Output:** L = carrier, R = carrier + beat

---

### Mode 2: `isochronic`
Single-band amplitude-modulated pulsing (works without headphones).

**Parameters:**
- `carrier`: Base frequency in Hz (default: 312.5)
- `pulse_rate`: Isochronic rate in Hz (default: 5)
- `duration`: Length in seconds

**Output:** Mono AM signal, same in both channels

---

### Mode 3: `bambi` (Advanced Dual-Band Isochronic)
Complex entrainment with harmonic bridge design. Based on reverse-engineering of effective hypnosis audio.

**Architecture:**
```
HIGH BAND: ~312 Hz carrier, 5 Hz isochronic, binaural component
LOW BAND:  ~62 Hz carrier, 3.25 Hz isochronic, binaural component, -6 dB
INTERLEAVE: R channel delayed 100ms (half-period of 5 Hz)
HARMONIC:  5th harmonic of low creates bridge frequency with high
```

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `high_carrier` | 312.5 | High band center frequency (Hz) |
| `high_beat` | 5.0 | High band binaural beat / isochronic rate (Hz) |
| `low_beat` | 3.25 | Low band binaural beat / isochronic rate (Hz) |
| `low_db` | -6.0 | Low band level relative to high (dB) |
| `interleave_ms` | 100 | R channel delay for spatial ping-pong (ms) |
| `harmonic_target` | 4.125 | Target harmonic beat frequency (Hz) |
| `duration` | 600 | Duration in seconds |
| `fade_in` | 3.0 | Fade in duration (seconds) |
| `fade_out` | 3.0 | Fade out duration (seconds) |

**Derived values (calculated automatically):**
```python
low_carrier = (high_carrier - harmonic_target) / 5

# Individual channel frequencies
high_L = high_carrier - high_beat / 2
high_R = high_carrier + high_beat / 2
low_L = low_carrier - low_beat / 2
low_R = low_carrier + low_beat / 2
```

**Default "harmonic ladder" preset:**
```
high_carrier = 312.5 Hz
harmonic_target = 4.125 Hz (linear midpoint of 5 and 3.25)
low_carrier = (312.5 - 4.125) / 5 = 61.675 Hz

HIGH: 310.0 / 315.0 Hz (5 Hz beat)
LOW:  60.05 / 63.30 Hz (3.25 Hz beat)

Entrainment ladder: 3.25 → 4.125 → 5.0 Hz
```

**Presets:**

| Preset | harmonic_target | Effect |
|--------|-----------------|--------|
| `ladder` | 4.125 Hz | Smooth theta gradient (default) |
| `alpha8` | 8.0 Hz | Theta + alpha boundary |
| `alpha10` | 10.0 Hz | Theta + mid-alpha |

---

## Signal Generation

### Isochronic Envelope
The amplitude modulation uses a raised cosine for smooth pulsing:

```python
def isochronic_envelope(t, rate):
    # Raised cosine: ranges from 0 to 1
    return 0.5 * (1 + np.cos(2 * np.pi * rate * t + np.pi))
```

### Channel Generation (Bambi mode)
```python
# Generate mono envelope for each band
high_env = isochronic_envelope(t, high_beat)
low_env = isochronic_envelope(t, low_beat)

# Generate carriers (different freq for L/R)
high_L_carrier = np.sin(2 * np.pi * high_L * t)
high_R_carrier = np.sin(2 * np.pi * high_R * t)
low_L_carrier = np.sin(2 * np.pi * low_L * t)
low_R_carrier = np.sin(2 * np.pi * low_R * t)

# Apply envelope to carriers
high_L_signal = high_env * high_L_carrier
high_R_signal = high_env * high_R_carrier
low_L_signal = low_env * low_L_carrier * db_to_linear(low_db)
low_R_signal = low_env * low_R_carrier * db_to_linear(low_db)

# Mix bands
left = high_L_signal + low_L_signal
right = high_R_signal + low_R_signal

# Apply interleave (delay R channel)
right = delay(right, interleave_ms)

# Apply fades
left = apply_fades(left, fade_in, fade_out)
right = apply_fades(right, fade_in, fade_out)
```

---

## Output Specifications

| Property | Value |
|----------|-------|
| Sample rate | 44100 Hz |
| Bit depth | 16-bit |
| Channels | Stereo |
| Format | WAV (for mixing), MP3 (for final) |
| Standalone level | -31 dB RMS |
| Mixed level | Normalize to -1 dB peak |

---

## CLI Interface

```bash
# Simple binaural
python audio/binaural.py simple --carrier 200 --beat 5 --duration 600 -o drone.wav

# Basic isochronic
python audio/binaural.py isochronic --carrier 312 --pulse-rate 5 --duration 600 -o pulse.wav

# Bambi mode with defaults (harmonic ladder)
python audio/binaural.py bambi --duration 600 -o bambi_drone.wav

# Bambi mode with alpha target
python audio/binaural.py bambi --preset alpha8 --duration 600 -o alpha_drone.wav

# Bambi mode fully custom
python audio/binaural.py bambi \
  --high-carrier 312.5 \
  --high-beat 5.0 \
  --low-beat 3.25 \
  --harmonic-target 4.125 \
  --low-db -6 \
  --interleave-ms 100 \
  --fade-in 3 \
  --fade-out 3 \
  --duration 600 \
  -o custom_drone.wav

# Mix with voice track
python audio/binaural.py mix \
  --voice voice.mp3 \
  --drone drone.wav \
  --drone-level -12 \
  -o final.mp3
```

---

## Entrainment Science Reference

| Frequency | Band | Associated State |
|-----------|------|------------------|
| 0.5-4 Hz | Delta | Deep sleep, unconscious |
| 3.25 Hz | Delta/Theta | Deep trance, hypnotic |
| 4-8 Hz | Theta | Meditation, creativity, memory |
| 4.125 Hz | Theta | Harmonic bridge (calculated) |
| 5 Hz | Theta | Light trance, suggestibility |
| 7.83 Hz | Theta/Alpha | Schumann resonance |
| 8-12 Hz | Alpha | Relaxed focus, calm |
| 10 Hz | Alpha | Alert relaxation |
| 12-30 Hz | Beta | Active thinking |

---

## Dependencies

```
numpy
scipy
pydub (for MP3 export)
```

---

## Future Enhancements

- [ ] Dynamic frequency sweeps (frequency ramps over time)
- [ ] Multiple harmonic targets (chord-like entrainment)
- [ ] Amplitude envelope shaping (attack/decay control)
- [ ] Pink/brown noise layer option
- [ ] Real-time preview mode
