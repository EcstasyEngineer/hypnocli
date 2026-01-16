# Taxonomy v5.2 Recommendations - Post-Implementation Status

> This document tracks the original recommendations and their implementation status.
> Last updated after v5.2 implementation session.

---

## Implementation Summary

### COMPLETED in v5.2

**Phase Restructuring:**
- [x] Merged P7 (Safety) → P1 (Context + Safety)
- [x] Merged P9 (Scenario Immersion) → P4 (Core Suggestion + Immersion)
- [x] Merged P10 + P12 → M2 (Transfer)
- [x] Converted P4 (Cognitive Reduction) → M1 (Critical Softening) as optional module
- [x] Converted P8 (Fractionation) → technique only (DEEP-03 used in P3)
- [x] Renamed P5 → P4, P6 → P5 (now 5 required phases)
- [x] Renamed P10, P11, P12, P13 → M1, M2, M3, M4 (4 optional modules)

**Category Changes:**
- [x] Merged LOAD + SEMN → ABSR (Absorption & Critical Softening)
- [x] Added XFER category (7 techniques for transfer/generalization)
- [x] Added CHECK category (8 techniques for state management)
- [x] Expanded SAFE (SAFE-06 through SAFE-10)
- [x] Expanded EMRG (EMRG-06 through EMRG-10, including waking suggestions)
- [x] Removed LOAD-06 (Garbled Audio) as accessibility-unfriendly

**Other:**
- [x] Updated compatibility matrix for new P/M structure
- [x] Updated appendix statistics
- [x] Created GitHub issue #26 for orphaned technique audit
- [x] Created GitHub issue #27 for JSON auto-generation
- [x] Created GitHub issue #28 for CI checks

---

## NOT IMPLEMENTED - Not Relevant to Our Use Case

> Our use case is recreational/kink hypnosis with consenting adults, not clinical/therapeutic hypnosis.

### Phases Not Added

**P0 Intake / Suitability / Goal** - NOT RELEVANT
- This is for clinical intake. For audio files, this overlaps with P1 context setting.
- Our listeners are self-selecting adults who know what they're getting into.

**P7 Debrief / Aftercare / Practice Plan** - NOT RELEVANT
- Clinical debrief doesn't fit audio file format.
- Aftercare is covered by SAFE-05 and EMRG techniques.
- "Practice plan" is clinical language that doesn't apply.

### Category Changes Not Made

**AUTH → split into RAPP (safe) vs DOM (stage-only)** - NOT RELEVANT
- The recommendation assumes we need to quarantine "dominance" techniques.
- For our use case, dominance/ownership IS the content. No need to split.

**VALD → split into RATF (ratification) vs PHEN (phenomena)** - NOT RELEVANT
- The split was to separate "safe" ratification from "risky" stage phenomena.
- We're not doing clinical work; stage phenomena are fine.

**ENCD + PERS + TRIG → merge into XFER** - NOT IMPLEMENTED
- Would create a massive 27-technique category
- Would break many existing references
- Instead: added XFER as NEW category for transfer-specific techniques, kept ENCD/PERS/TRIG separate

**Add LANG (Suggestion Design & Language)** - NOT IMPLEMENTED
- Too clinical/prescriptive for our use case
- "Agency-preserving wording" and "ecological fit" are therapy concepts
- Our scripts intentionally use directive/compulsion language

**Add DEBR (Debrief)** - NOT IMPLEMENTED
- Clinical debrief category doesn't fit recreational hypnosis
- Relevant techniques (grounding, reorientation) already in EMRG and SAFE

### Technique Quarantining Not Done

The recommendations suggested quarantining/removing these from "therapeutic/neutral":
- TRIG-10 (Amnesia-Wrapped Command)
- TRIG-11 (Text/Platform Trigger)
- TRIG-13 (Third-Party Activation)
- AUTH-04 (Ownership Language)
- Obedience-labeling variants
- Amnesia variants

**NOT RELEVANT** - These are all legitimate techniques for consenting adult kink content. We're not building a clinical tool.

---

## FUTURE WORK - Still Relevant

### FSM (Finite State Machine) for Sequence Rules

The current sequence rules are prescriptive ("P1 must come before P2"). Future work should convert to FSM where:
- Phases/modules become nodes
- Valid transitions become edges
- "Required" label becomes meaningless (valid paths defined by graph)
- Enables more flexible script structures (e.g., P3 can appear multiple times for periodic deepening)

**GitHub issue needed for FSM implementation**

### Technique Audit

Some techniques are defined but never referenced in the compatibility matrix:
- PLEA-02, PLEA-03, PLEA-04, PLEA-05
- Possibly others

**Tracked in GitHub issue #26**

### PLEA → REIN Rename

Original recommendation suggested renaming PLEA (Pleasure) to REIN (Reward/Affect Reinforcement) for neutrality.

**Decision:** Keep as PLEA for now. Our use case is explicitly pleasure-focused. Could revisit if we ever need a "neutral" subset.

---

## Recommendations We Considered But Declined

### DISS Category Split (DISS-SOFT vs DISS-HARD)

Recommendation was to split dissociation into "soft" (time distortion) vs "hard" (amnesia, depersonalization).

**Declined:** Only 3 techniques in DISS; split adds complexity without benefit. Amnesia/dissociation are valid tools for our use case.

### INDU-05 Countdown → Move to DEEP

Recommendation was that countdown is a deepener, not an induction.

**Declined:** Countdown can be used for both induction and deepening. Keep where it is; generators can use it in either phase.

### INDU-08 Pattern Interrupt → Mark Stage-Only

Recommendation was that pattern interrupts are high-failure in async audio.

**Noted but not actioned:** Valid concern for audio scripts. Generators should be aware but technique remains available.
