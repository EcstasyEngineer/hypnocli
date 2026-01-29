# Binaural & Isochronic Entrainment: Analysis & Best Practices

**Date:** January 2026
**Scope:** Spectral analysis of binaural beats and isochronic tones in hypnosis audio, with design recommendations

---

## Executive Summary

Analysis of entrainment audio spanning 2017-2024 reveals several design patterns. Key findings:

1. **Two distinct formulas exist:** The original 2017 design (11→3 Hz induction sweep + 3 Hz static content) and the 2018 Enforcement formula (4.7→4.0 Hz theta sweep in standalone drone)

2. **Looped drones break continuity:** Some files are short sweeps hard-looped with audible splice artifacts, breaking entrainment

3. **Quality varies significantly:** Some releases have carrier dropout mid-file, poor signal separation, or missing layers

4. **Progressive sweeps most effective:** Later releases include binaural sweeps inside content files, not just inductions

### Key Recommendations

1. **Use isochronic tones, not just binaural beats** — Isochronic pulses produce significantly stronger EEG entrainment than binaural beats alone (Pratt et al. 2010)
2. **Use gradual progression** — Alpha (10 Hz) → Theta (5 Hz) → Delta (3 Hz) over time. Direct delta induction either fails or induces sleep.
3. **Put sweeps in content, not just inductions** — Continuous deepening is more effective than static maintenance
4. **Don't hard-loop sweeping tones** — Use crossfades or ping-pong (forward/reverse) to maintain continuity
5. **Use low carrier frequencies** — 250 Hz carriers produce stronger responses than 1000 Hz
6. **Layer dual isochronic rates** — A higher rate (5 Hz) can act as a "pump" to help recruit neurons to a lower target rate (3.25 Hz)

---

## Methodology

### Tools Developed

| Script | Purpose |
|--------|---------|
| `binaural_analyzer.py` | Sliding-window FFT to track binaural beat over time |
| `spectrum_debug.py` | Detailed frequency bin analysis for carrier identification |
| `isochronic_analyzer.py` | Amplitude modulation detection (noisy on vocal content) |

### Key Parameters

- **Window size:** 20 seconds (0.05 Hz FFT resolution)
- **Step size:** 5 seconds
- **Carrier detection:** Parabolic interpolation for sub-bin accuracy
- **Binaural calculation:** `abs(right_carrier - left_carrier)`

---

## Entrainment Formulas Observed

### Formula 1: Induction Sweep + Static Content (2017)

| Component | Binaural |
|-----------|----------|
| Induction | 11→3 Hz sweep |
| Content | 3.0 Hz static |

**Pattern:** Alpha (11-12 Hz) → Delta (3 Hz) sweep in inductions, then maintain delta throughout content.

### Formula 2: Standalone Drone Layer (2018)

**Drone track specifications:**
- Carriers: L=310 Hz / R=314 Hz (high), L=58 Hz / R=62 Hz (low)
- Binaural: **4.71 → 4.00 Hz** smooth sweep over 2 minutes
- Isochronic: ~5 Hz (high carrier), ~3.2 Hz (low carrier)
- Both carriers sweep in lockstep

**Content files:** Static 3.0 Hz binaural (unchanged from Formula 1)

**Key insight:** The drone is meant to layer over content, providing theta stimulation while content provides delta.

### Formula 3: Progressive Content Sweeps (2024)

| Track | Binaural |
|-------|----------|
| Induction | 11.97 → 10.99 Hz (alpha sweep) |
| Track 1 | **11.96 → 5.51 Hz** (alpha→theta) |
| Track 2 | **6.20 → 3.00 Hz** (theta→delta) |
| Track 3 | **6.20 → 3.00 Hz** |
| Track 4 | **5.78 → 3.00 Hz** |

**Key insight:** Sweeps INSIDE content files. Most aggressive entrainment design - actively deepens throughout content rather than just maintaining.

### Common Issues Observed

- **Carrier dropout:** High carrier (~310 Hz) drops out mid-file in some releases
- **Hard loops:** Short sweeps looped without crossfades create audible resets
- **Inconsistent structure:** Some releases have completely different carrier frequencies

---

## Hard Loop Artifacts

### Finding
Some extended tracks are short sweeps (e.g., 2 minutes) copy-pasted multiple times without crossfades.

### Evidence
Granular analysis shows sawtooth binaural pattern:
```
0:00 - 1:50  → 4.74 → 3.97 Hz (sweep DOWN)
1:55         → JUMP to 4.75 Hz (RESET)
2:00 - 3:50  → 4.72 → 3.95 Hz (sweep DOWN)
3:55         → JUMP to 4.74 Hz (RESET)
... repeating every ~2 minutes ...
```

### Implication
Hard cuts break entrainment continuity. The smooth sweep is undermined by instant resets. **Use crossfades or ping-pong (forward/reverse) looping instead.**

---

## Carrier Frequency Reference

### Standard Carriers (most releases)

| Layer | Left | Right | Binaural |
|-------|------|-------|----------|
| High (~310 Hz) | 309.5-310.5 Hz | 313.5-314.5 Hz | 3-5 Hz |
| Low (~60 Hz) | 57.5-58.5 Hz | 61.5-62.5 Hz | 3-5 Hz |

### Isochronic Modulation

| Carrier | Pulse Rate | Notes |
|---------|------------|-------|
| High (~310 Hz) | ~5 Hz | Stable throughout |
| Low (~60 Hz) | ~3.2 Hz | May drift slightly |

### Alpha-Range Variant

Some releases use wider binaural spacing for alpha-range beats:

| Layer | Left | Right | Binaural |
|-------|------|-------|----------|
| High (~312 Hz) | 306.5 Hz | 317.5 Hz | **11 Hz** |
| Low (~60 Hz) | 58.5 Hz | 61.5 Hz | 3 Hz |

---

## Entrainment Design Patterns

### Pattern 1: Induction Sweep + Static Content
```
Induction:  11 Hz ────────────────> 3 Hz
Content:    3 Hz ═══════════════════════════
            |     Sweep (3-5 min)  |  Maintain
```

### Pattern 2: Standalone Drone Layer
```
Drone:      4.7 Hz ───> 4.0 Hz ───> 4.7 Hz (looped)
Content:    3 Hz ═══════════════════════════════════
            |  Both playing simultaneously  |
```

### Pattern 3: Progressive Content Sweeps (Recommended)
```
Track 1:    12 Hz ──────────────────> 6 Hz
Track 2:     6 Hz ──────────────────> 3 Hz
Track 3:     6 Hz ──────────────────> 3 Hz
            |  Each track actively deepens  |
```

---

## Multi-Layer Pulse Rate Design

When using multiple isochronic layers, integer pulse rates (e.g., 7, 5, 3 Hz) will synchronize every second, creating a repetitive "thump" pattern. To maximize rhythmic complexity and avoid predictable sync points, choose pulse rates with long **least common multiple (LCM)** periods.

### The Math

For two frequencies f₁ and f₂, the sync period = 1 / GCD(f₁, f₂).

**Example:** Original drone uses 5 Hz and 3.25 Hz (= 13/4):
- Express as fractions: 5 = 20/4, 3.25 = 13/4
- GCD(20, 13) = 1, so GCD of frequencies = 1/4
- Sync period = 4 seconds ✓

**Problem:** 7, 5, 3 Hz (all integers) have GCD = 1 → sync every 1 second (boring)

### Designing for Maximum Entropy

To get different sync periods ≥4s for all pairs in a multi-layer design:

| Layer | Freq | Fraction | Common (×20) |
|-------|------|----------|--------------|
| High | 7.0 Hz | 7/1 | 140/20 |
| Mid-high | 4.6 Hz | 23/5 | 92/20 |
| Mid-low | 3.3 Hz | 33/10 | 66/20 |
| Low | 2.55 Hz | 51/20 | 51/20 |

**Resulting sync periods:**

| Pair | GCD | Sync Period |
|------|-----|-------------|
| High – Mid-high | 4 | 5s |
| High – Mid-low | 2 | 10s |
| High – Low | 1 | 20s |
| Mid-high – Mid-low | 2 | 10s |
| Mid-high – Low | 1 | 20s |
| Mid-low – Low | 3 | 6.67s |

All pairs ≥5s, all different — maximum rhythmic complexity.

### Quick Reference

- **Avoid** integer relationships (7:5:3, 6:4:2, etc.)
- **Use** fractions with coprime numerators when reduced to common denominator
- **Target** sync periods of 4-20+ seconds between all layer pairs
- **Test** by listening for repetitive "thump" patterns — if you hear regular sync, adjust

---

## Target Frequencies by Goal

| Goal | Frequency | Band |
|------|-----------|------|
| Identity dissolution / deep trance | 1-4 Hz | Delta |
| Suggestibility / light trance | 4-7 Hz | Theta |
| Relaxed focus / induction start | 8-12 Hz | Alpha |

**Additional tips:**
- Match binaural beat across both carriers (high + low layers should target same frequency)
- Sync entrainment drops to script beats (e.g., "drop" commands coincide with frequency descents)

### Analysis Tips

- Use `--no-high` flag when high carrier drops out mid-file
- Run spectrum debug first on unfamiliar files to identify carrier ranges
- Isochronic analysis only reliable on pure tone files (voice content masks modulation)

---

## Open Questions

1. **Mid-file carrier dropout** - Why does the high carrier sometimes disappear partway through?
2. **3.0 Hz binaural vs 3.2 Hz isochronic** - Intentional offset or coincidence?
3. **Optimal sweep rate** - What's the maximum Hz/second the brain can track?

---

## Literature Review Summary (January 2026)

Key findings from Deep Research synthesis of entrainment and hypnosis neuroscience literature:

### Binaural Beats: Weak Evidence

- **Mixed results:** Systematic review (2023) of 14 studies found 5 positive, 8 null, 1 mixed — "inconclusive at best"
- **Perceptually weak:** Binaural beats equivalent to ~10-20% amplitude modulation — subtle tremor, not strong drive
- **Mechanistic limitation:** Binaural beats bypass thalamus (resolved in brainstem), so weak cortical projection
- **Confounds:** Theta increases often indistinguishable from normal relaxation/eyes-closed drift

### Isochronic Tones: Stronger Evidence

- **Robust FFR:** Pratt et al. (2010) found monaural/isochronic beats evoke "significantly larger EEG oscillations" than binaural
- **Lower carriers better:** 250 Hz carriers > 1000 Hz for response amplitude
- **Slower frequencies stronger:** 3 Hz > 6 Hz for amplitude (relevant to our 3.25 Hz layer)
- **Rapid decay:** Entrainment response "dies out quickly (within tens of ms)" when stimulus stops

### Hemispheric Asymmetry in Hypnosis

- **Left prefrontal deactivation:** Spiegel et al. (2016) fMRI found reduced DLPFC-DMN connectivity in hypnosis
- **Not simple "right brain takeover":** Both hemispheres active, but left executive/critical functions suppressed
- **Broca's area:** Likely reduced activity (less inner monologue), though not directly measured
- **Whole-brain coherence:** Deep trance shows more bilateral synchronization, not hemispheric isolation

### Lateralized Auditory Stimulation

- **Research gap:** No studies on phase-offset isochronic stimulation for altered states
- **Monaural lateralization:** Sound to one ear primarily drives contralateral hemisphere
- **Binaural promotes synchronization:** Monroe Institute's Hemi-Sync intended to *reduce* asymmetry, not create it

### Stepwise Protocols

- **Strongly supported:** Gradual alpha→theta→delta progression preferred over direct delta induction
- **Brain needs time:** Entrainment effects take minutes to stabilize
- **Direct delta problems:** Either fails to entrain or induces unwanted sleep
- **Monroe Institute approach:** Sequential "Focus levels" with multi-frequency layering

### Key Citations

**Entrainment efficacy:**
- **Pratt et al. (2010)** — Monaural beats evoke higher amplitude FFR/ASSR than binaural. Lower carriers (250 Hz) and slower frequencies (3 Hz) yield stronger responses. Entrainment fades within tens of ms when stimulus stops.
- **Orozco Perez, Dumas & Lehmann (2020)** — Both binaural and monaural beats entrain, but binaural is weaker. Notably: binaural uniquely affected cross-frequency connectivity patterns — may indicate more complex network engagement beyond simple FFR.
  - eNeuro: https://www.eneuro.org/content/eneuro/7/2/ENEURO.0232-19.2020.full.pdf
  - bioRxiv preprint: https://www.extrospection.eu/wp-content/uploads/2019/05/OrozcoPerez-Dumas-Lehmann_Biorxiv_2019.pdf
- **Grose, Buss & Hall (2012)** — "Binaural beat salience" — Binaural beats perceptually equivalent to ~10-20% amplitude modulation. The "beat" is a weak percept, easily masked. Hearing Research.
- **Ingendoh et al. (2023)** — Systematic review: 5 positive, 8 null, 1 mixed out of 14 EEG studies. "Inconclusive at best."
- **Chaieb et al. (2015)** — Frontiers review noting inconsistent results may be due to insufficient entrainment time and abrupt stimulus parameters. Suggested exploring progressive frequency protocols.
  - https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2015.00070/pdf

**Hypnosis neuroscience:**
- **Spiegel et al. (2016)** — fMRI of highly hypnotizable subjects: reduced dorsal ACC activity, reduced DLPFC-DMN connectivity, increased DLPFC-insula connectivity. The "inner critic" disconnects.
- **Cardeña & Terhune (2020)** — MDPI review reframing hypnosis as frontal-posterior network changes, not simple "right hemisphere activation." Left frontal inhibition is real but it's not hemisphere-wide.
- **Kihlstrom et al. (2012)** — Patient with destroyed left hemisphere could still be hypnotized. No significant difference in hypnotizability between left vs right brain damage groups.

**Behavioral effects:**
- **Lane, Kasian, Owens & Marsh (1998)** — Beta beats improved vigilance/mood; theta/delta beats led to *worse* mood and performance. Direct slow-wave induction isn't always pleasant — supports need for gradual progression.
  - https://archive.org/download/monroe-institute-research-ceu/Research%201998%20-%20Binaural%20Auditory%20Beats%20Affect%20Vigilance%20Performance%20and%20Mood%20-%20Lane%2C%20Kasian%2C%20Owens%20%26%20Marsh.pdf

**Practice/methodology:**
- **Monroe Institute (2022-2023)** — Hemi-Sync evolution: layered binaural beats, sequential Focus levels, dynamic progression. Key innovation: adding gamma to maintain awareness during delta exposure. (Not peer-reviewed)
  - Overview: https://www.monroeinstitute.org/pages/monroe-sound-science
  - Archive: https://archive.org/details/monroe-institute-reports-monroe-sound-science
- **Aparecido-Kanzler, Cidral-Filho & Prediger (2021)** — Only 2 of 17 entrainment studies used isochronic tones. Major research gap — isochronic is understudied despite stronger theoretical basis. Revista Mexicana de Neurociencia.
  - https://www.scielo.org.mx/scielo.php?pid=S1665-50442021000600238&script=sci_arttext

---

## Next Steps for Research

### 1. Sweep Rate Optimization

**Goal:** Determine optimal sweep parameters for entrainment

**Questions:**
- Maximum Hz/second the brain can track?
- Optimal curve shape (linear, exponential, stepped)?
- Minimum dwell time at target frequency?

**Working hypothesis:** ~10-30 seconds per 1 Hz change in theta range.

**Search terms:** ASSR entrainment dynamics, FFR temporal characteristics, neural oscillation phase locking

### 2. Ratcheting Recruitment Hypothesis

**Observation:** Dual isochronic layers (5 Hz + 3.25 Hz) with 180° L/R offset.

**Hypothesis:** The 5 Hz layer acts as a "pump" — its L/R crossover windows (where both channels are at ~50%) allow the 3.25 Hz layer to recruit neurons that momentarily lost their 5 Hz lock. This happens 5x/second, cumulatively shifting entrainment downward.

**Support:** Pratt et al. (2010) found entrainment "dies out within tens of ms" when stimulus stops — crossover windows are long enough for partial fade.

**Note:** The 117° offset on the 3.25 Hz layer is template reuse (100ms delay designed for 5 Hz), not intentional. Isochronic pulse rates likely dominate over binaural beat frequency.

**Validation:** Requires EEG phase-amplitude coupling analysis.

---

## Tools & Scripts

All analysis scripts are in `/analysis/scripts/`:

```
binaural_analyzer.py    # Main analysis tool
  --window SEC          # FFT window size (default: 20)
  --step SEC            # Step between windows (default: 5)
  --low-min/--low-max   # Low carrier frequency range
  --high-min/--high-max # High carrier frequency range
  --no-low/--no-high    # Disable carrier detection
  --csv                 # Output CSV format

spectrum_debug.py       # Detailed frequency analysis
  --start SEC           # Start time
  --duration SEC        # Duration to analyze
  --bin-size HZ         # Frequency bin resolution
  --top N               # Show top N peaks

isochronic_analyzer.py  # Amplitude modulation detection
                        # (Note: unreliable on vocal content)

analyze_folder.py       # Batch analysis wrapper
```

---

## Appendix: Analysis Tools

Analysis scripts are in `/analysis/scripts/`. See Tools & Scripts section above for usage.

---

*This document summarizes entrainment audio analysis and best practices. January 2026.*
