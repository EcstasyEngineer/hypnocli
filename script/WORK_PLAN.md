# Script Generation Work Plan

> Last updated: 2026-01-16

This document tracks the status of all script generation improvements. Update this when significant items are completed.

---

## GitHub Issues Created

| # | Title | Priority | Status |
|---|-------|----------|--------|
| [#31](https://github.com/EcstasyEngineer/hypnocli/issues/31) | Upgrade JSON taxonomy from 5.1 to 5.2 | HIGH | ✅ Done |
| [#32](https://github.com/EcstasyEngineer/hypnocli/issues/32) | Script copywriting overhaul (repetition, leaky language) | HIGH | ✅ Done |
| [#33](https://github.com/EcstasyEngineer/hypnocli/issues/33) | Use technique names instead of IDs in markers | MEDIUM | Open |
| [#34](https://github.com/EcstasyEngineer/hypnocli/issues/34) | Goddess/Venus variant (warm devotional alternative) | MEDIUM | Open |
| [#35](https://github.com/EcstasyEngineer/hypnocli/issues/35) | Visualization/immersion audit | MEDIUM | Open |
| [#36](https://github.com/EcstasyEngineer/hypnocli/issues/36) | Render concatenation paragraph breaks | LOW | Open |
| [#37](https://github.com/EcstasyEngineer/hypnocli/issues/37) | Hypernym decontamination pipeline | MEDIUM | Open |
| [#38](https://github.com/EcstasyEngineer/hypnocli/issues/38) | Phased script writer phase 1 + technique examples | HIGH | Open |

---

## Pre-Existing Issues (Related)

| # | Title | Status |
|---|-------|--------|
| #4 | Long induction length targeting (68% of target) | Open |
| #5 | Auto-retry truncated segments | Open |
| #10 | Params vs Notes schema approach | Open |
| #23 | Taxonomy v6 FSM-style transitions | Open |
| #24 | Script length calibration (20-33% undershoot) | Open |
| #26 | Orphaned technique audit | Open |
| #27 | Auto-generate JSON from markdown | Open |
| #29 | Prosody-aware SSML guidance | Open |

---

## Work Streams

### Stream 1: Taxonomy Upgrade (Blocking)

**Goal:** Get JSON to v5.2 parity with markdown

| Task | Status | Notes |
|------|--------|-------|
| Verify markdown 5.1→5.2 has no regressions | ✅ Done | Verified: LOAD+SEMN→ABSR, added XFER/CHECK, expanded SAFE/EMRG |
| Update JSON phases (P1-P5 + M1-M4) | ✅ Done | All 5 required phases + 4 optional modules |
| Add ABSR techniques (merge LOAD+SEMN) | ✅ Done | 9 techniques merged |
| Add XFER category (7 techniques) | ✅ Done | Transfer & Generalization |
| Add CHECK category (8 techniques) | ✅ Done | State Management |
| Expand SAFE (SAFE-06 to SAFE-10) | ✅ Done | 10 total techniques |
| Expand EMRG (EMRG-06 to EMRG-10) | ✅ Done | 10 total techniques |
| Update compatibility matrix | ✅ Done | Matches markdown exactly |
| Bump version to 5.2 | ✅ Done | Changelog added |

### Stream 2: Quality Gates

**Goal:** Automated quality checks for generated scripts

| Task | Status | Notes |
|------|--------|-------|
| Truncation detection (#5) | ⬜ Pending | Detect mid-sentence endings |
| Length calibration (#24) | ⬜ Pending | Few-shot examples work best |
| Hypernym decontamination (#37) | ✅ Prototype | `script/hypernym_lookup.py` created - 10 property types, domain exclusions |
| Paragraph break validation (#36) | ✅ Investigated | Root cause: `.strip()` removes `\n\n`, ffmpeg concat has no silence insertion |

### Stream 3: Copywriting Overhaul

**Goal:** Fix repetition, leaky language, and visualization

**Status:** ✅ **COMPLETED** - All scripts rewritten with consistent voice, 3x mantras, warm language

| Script | Status | Changes |
|--------|--------|---------|
| acceptance | ✅ Done | Removed P2, 5x5→3x, added warmth |
| addiction | ✅ Done | Removed P2, 5x→3x |
| bimbo | ✅ Done | Removed P2, "Tee hee"→natural language, 5x→3x |
| blank | ✅ Done | Major rewrite - lake visualization, warm language |
| brainwashing | ✅ Done | Removed P2, staircase viz, 5x→3x |
| dumbdown | ✅ Done | Classy degradation, removed crude language |
| feminine | ✅ Done | Removed P2, 5x→3x |
| fractionation_bridge | ✅ OK | Bridge only - no changes needed |
| free_use | ✅ Done | Removed P2, removed "waiting meat", 5x→3x |
| free_use_extended | ✅ Done | Removed P2, kept fractionation, 5x→3x |
| harem | ✅ Done | "hierarchy"→connection, competition→belonging |
| intro | ✅ OK | Model script with pause markers |
| obedience | ✅ Done | Major rewrite - warm compliance, honey metaphor |
| slave | ✅ Done | Removed P2, 5x→3x |
| submission | ✅ Done | Removed P2, 5x→3x |
| suggestibility | ✅ Done | "writable"→moldable/receptive |
| tease_denial | ✅ Done | Removed P2, 5x→3x |
| tease_denial_obedience | ✅ Done | Removed P2, 5x→3x |
| wakener | ✅ OK | Emergence script - no changes needed |

**Consistent patterns applied:**
- Start at P3 Deepening (conditioning loops have no P2 Induction)
- 10-count deepening with line breaks between numbers
- 3x mantras with slight variation between repetitions
- Warm language throughout (warmth, pleasure, peace, belonging)
- Short sentences for pacing
- Echoing mantras in P13 Maintenance

### Stream 4: Technique Examples

**Goal:** Add good/bad examples for each technique in taxonomy

| Tier | Techniques | Status |
|------|------------|--------|
| Tier 1 (every script) | INDU-01,02,03,05; DEEP-01,02,04; ABSR-01,02; ENCD-01,02,03; EMRG-01,02 | ✅ Done |
| Tier 2 (common optional) | DEEP-03; AUTH-01,02; PLEA-01; TRIG-01,02 | ⬜ Pending |
| Tier 3 (specialized) | All others | ⬜ Pending |

**Theme:** Toymaker/mindless puppet obedience conditioning aesthetic

**File:** `script/technique_examples.json` - Contains good/bad examples with theme_notes for each technique

### Stream 5: Default Style Update

**Goal:** Make Goddess/warm/devotional the DEFAULT style (not a separate track)

**Decision:** Rather than maintaining two parallel tracks (dark Master vs light Goddess), the default style is now warm/devotional. Cold/void language becomes an optional "dark" variant if ever needed.

| Task | Status | Notes |
|------|--------|-------|
| Update technique_examples.json | ✅ Done | Toymaker aesthetic is already warm |
| Update style defaults in taxonomy | ✅ Done | Added "Devotional" style with `default: true` |
| Update SYSTEM_WRITER prompts | ⬜ Pending | Remove cold void defaults |
| Regenerate scripts with new defaults | ⬜ Pending | After copywriting pass |

---

## Pause Markup System

Scripts can use simple pause markers that auto-convert to SSML:

| Syntax | SSML Output | Use Case |
|--------|-------------|----------|
| `[500]` | `<break time="500ms"/>` | 500ms pause (default is ms) |
| `[500ms]` | `<break time="500ms"/>` | Explicit milliseconds |
| `[1.5s]` | `<break time="1500ms"/>` | 1.5 second pause |

**Breathing pattern example:**
```
Breathe in[400] one[750] two[750] three[750] four.[1.5s] Out[400] six[750] five[750] four[750] three[750] two[750] one.
```

**Guidelines:**
- Use [500] to [800] between paragraphs for pacing
- Only use pause markers when precise timing matters (breathing, countdowns)
- Normal prose doesn't need them - TTS handles `...` naturally
- `render_polly.py` auto-detects markers and enables SSML mode

---

## Render Issues to Investigate

| File | Timestamp | Issue | Status |
|------|-----------|-------|--------|
| blank | ~middle | "four" sounds off | ⬜ Check |
| (any 66min) | ~46:00 | "us" sounds off | ⬜ Check |

---

## Data Analysis (Future)

### Technique Coverage Analysis
- [ ] Per-sentence embedding of corpus
- [ ] Velocity-change chunking
- [ ] Per-chunk phase + technique classification
- [ ] Verify against 2 manual splits

### Corpus Files
- Had ~20 files analyzed for technique distribution
- Need to re-do under v5.2 nomenclature (if data lost)

---

## Dependencies

```
#31 (JSON upgrade) ─┬─> #33 (use names not IDs)
                    ├─> #38 (add examples)
                    └─> #32 (copywriting uses new taxonomy)

#37 (hypernym) ─────> #32 (copywriting quality gate)

#35 (viz audit) ────> #32 (copywriting includes viz fixes)
```

---

## Completion Log

| Date | Item | Notes |
|------|------|-------|
| 2026-01-16 | Created work plan | Initial version |
| 2026-01-16 | Verified MD 5.1→5.2 | No regressions |
| 2026-01-16 | Created issues #31-38 | All notes tracked |
| 2026-01-16 | JSON taxonomy upgraded to 5.2 | Verified all 10 items match MD |
| 2026-01-16 | Made SAFE optional in P1 | Removed forced "if you hear awake..." pattern |
| 2026-01-16 | Added technique parameterization | INDU, DEEP, ABSR, ENCD, TRIG, EMRG now have embedded params |
| 2026-01-16 | Created technique_examples.json | Tier 1 techniques with good/bad examples |
| 2026-01-16 | Added Devotional as default style | Replaced Compulsion with Dark style |
| 2026-01-16 | Created hypernym_lookup.py | Prototype for #37 - 10 property types |
| 2026-01-16 | Completed copywriting audit | All 19 scripts analyzed for repetition/breathing/viz/leaky |
| 2026-01-16 | Investigated render_polly (#36) | Found root cause: .strip() + ffmpeg concat |
| 2026-01-16 | Found technique ID code (#33) | Line 615 in phase_chat_generator.py |
| 2026-01-16 | Implemented technique names (#33) | Changed line 615 to use names instead of IDs |
| 2026-01-16 | Fixed dumbdown script | Classy degradation - removed crude "hole" language |
| 2026-01-16 | Added pause markup system | `[500]` or `[1.5s]` auto-converts to SSML in render_polly |
| 2026-01-16 | Fixed breathing pacing | 4-hold-6 pattern, ~6 breaths/min, countdown on exhale |
| 2026-01-16 | Updated SYSTEM_WRITER | Added warmth/breathing/pause markup guidance |
| 2026-01-16 | Deleted script_ssml.txt | Replaced with pause markers in script.txt |
| 2026-01-16 | Completed copywriting overhaul (#32) | All 16 loop scripts rewritten with 3x mantras, consistent voice |
| 2026-01-16 | Implemented [dominant] placeholder system | harem + wakener use placeholders, build_session.py has --dominant-title flag |
| 2026-01-16 | Created session specs | v1.md, v2.md, v3_master.md, v3_goddess.md under script/sessions/ |

---

## Technique Parameterization Status

Techniques with embedded `params` in JSON (flow: MD → JSON → phase planner → segment builder):

| Category | Parameterized Techniques |
|----------|-------------------------|
| INDU | INDU-01 (breath), INDU-02 (progressive), INDU-03 (fixation), INDU-04 (eye closure), INDU-05 (countdown), INDU-06 (drop) |
| DEEP | DEEP-01 (drop cmd), DEEP-02 (staircase), DEEP-03 (fractionation), DEEP-04 (numerical), DEEP-08 (endurance), DEEP-09 (void) |
| ABSR | ABSR-01 (quieting), ABSR-02 (spaciousness), ABSR-03 (shutdown) |
| ENCD | ENCD-01 (mantra), ENCD-02 (call-response), ENCD-03 (layered), ENCD-04 (future pace), ENCD-05 (looping), ENCD-06 (compliance), ENCD-07 (lesson) |
| TRIG | TRIG-01 (install), TRIG-02 (activate), TRIG-03 (stacking), TRIG-04 (loops), TRIG-12 (temporal) |
| EMRG | EMRG-01 (count-up), EMRG-02 (reactivation), EMRG-04 (integration), EMRG-05 (drift-sleep), EMRG-06 (waking) |

---

## Next Actions

1. ~~**JSON Taxonomy Upgrade (#31)**~~ - ✅ Done
2. ~~**Technique examples Tier 1 (#38)**~~ - ✅ Done (technique_examples.json)
3. ~~**Copywriting audit**~~ - ✅ Done (all 19 scripts analyzed)
4. ~~**Hypernym prototype (#37)**~~ - ✅ Done (hypernym_lookup.py)
5. ~~**Implement technique names (#33)**~~ - ✅ Done (line 615 in phase_chat_generator.py)
6. ~~**Copywriting fixes (#32)**~~ - ✅ Done (all 16 loop scripts rewritten)
7. **Listen through scripts** - User to re-listen for proper notes
8. ~~**Test hypernym_lookup.py**~~ - Tracked in GitHub issue #37
9. ~~**Session playlists**~~ - ✅ Done (script/sessions/v1.md, v2.md, v3_master.md, v3_goddess.md)
10. ~~**Close GitHub issue #32**~~ - ✅ Done
11. ~~**Implement dominant title in build_session.py**~~ - ✅ Done (`--dominant-title` flag with fail-fast and pronoun check)
12. ~~**Rename loops → modules**~~ - ✅ Done
