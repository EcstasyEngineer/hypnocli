# Canonical Taxonomy for Hypnosis Script Generation
## Version 5.1 — Complete Reference

**Changes from v5:**
- Added EMRG category for emergence (fixes DEEP-03 overload)
- Added DISS-03 (Time Distortion) to match corpus
- One technique ID = one meaning (no dual-use)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    WHAT LAYER (Strategic)                    │
│  Phases: What the listener experiences at each stage         │
│  Sequence Rules: Valid phase orderings                       │
│  Structural Variants: Alternative script architectures       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    HOW LAYER (Tactical)                      │
│  Techniques: Methods to achieve phase goals                  │
│  Style Modifiers: Tone and language patterns                 │
│  Production Elements: Audio/pacing considerations            │
└─────────────────────────────────────────────────────────────┘
```

---

# PART 1: WHAT LAYER (Strategic)

## 1.1 Phase Definitions

### Required Phases

| ID | Phase | Listener Task | Typical Duration |
|----|-------|---------------|------------------|
| P1 | Context Setting | Accept frame, establish attention focus | 30-60s |
| P2 | Induction | Release conscious control, enter trance | 60-90s |
| P3 | Deepening | Descend deeper through guided progression | 90-180s |
| P4 | Cognitive Reduction | Release analytical thinking, accept receptive state | 60-120s |
| P5 | Core Suggestion | Accept and internalize primary suggestions | 120-300s |
| P6 | Emergence | Return to normal consciousness | 30-90s |

### Optional Phases

| ID | Phase | Listener Task | Insert After | Duration |
|----|-------|---------------|--------------|----------|
| P7 | Safety/Consent | Receive protective boundaries | P1 | 30-60s |
| P8 | Fractionation | Experience wake/sleep cycling | P3 | 60-120s |
| P9 | Scenario Immersion | Enter detailed visualization | P4 | 90-180s |
| P10 | Trigger Installation | Accept conditioned responses | P5 | 60-120s |
| P11 | Demonstration | Experience trigger activation, bliss states, or proof of hypnosis | P5/P10 | 60-180s |
| P12 | Behavioral Bridge | Receive real-world action commands | P5 | 30-60s |
| P13 | Maintenance/Loop | Sustain trance for loop restart | P5 (terminal) | 60-90s |

**Total: 6 required + 7 optional = 13 phases**

---

## 1.2 Sequence Rules

### Required Ordering (Standard Scripts)

```
P1 → P2 → P3 → P4 → P5 → P6
     │              │
     └─[P7]─┘       └─[P8-P12]─┘
```

**Rules:**
1. P1 (Context Setting) must be first
2. P2 (Induction) must precede P3 (Deepening)
3. P3 (Deepening) must precede P4 (Cognitive Reduction)
4. P4 (Cognitive Reduction) must precede P5 (Core Suggestions)
5. P5 (Core Suggestions) must precede P6 (Emergence)
6. P6 (Emergence) must be final (unless looping with P13)

### Optional Phase Insertion Matrix

| Optional Phase | Valid Insertion Points |
|----------------|------------------------|
| P7 Safety/Consent | After P1, before P2 |
| P8 Fractionation | During P3, or after P3 before P4 |
| P9 Scenario Immersion | After P4, before P5 |
| P10 Trigger Installation | After P5, before P6 |
| P11 Demonstration | After P5 or P10, before P6 |
| P12 Behavioral Bridge | After P5, before P6 |
| P13 Maintenance/Loop | Terminal (replaces P6) |

---

## 1.3 Structural Variants

### Variant: standard
**Sequence:** P1 → P2 → P3 → P4 → P5 → P6
**Characteristics:** Full induction-deepening-suggestion-emergence arc
**Use Case:** Standalone sessions, first-time listeners

### Variant: loop
**Sequence:** P2 → P3 → P10 → P11 → P13 (loops to P2)
**Characteristics:**
- Skips P1 (Context Setting) - assumes opt-in
- Skips P6 (Emergence) - replaced by P13 (Maintenance)
- Uses instant/conditioned induction (INDU-06)
- Terminal state mirrors opening for seamless loop
**Use Case:** Background/ambient trance, extended sessions

### Variant: twostage
**Sequence:** P1 → P2 → P3 + light suggestions → P8 → P4 (deep) → P5 (deep) → P6
**Characteristics:**
- Light suggestions during initial deepening
- Fractionation creates stage boundary
- Deep cognitive reduction after fractionation
- Deep suggestions after blank state achieved
**Use Case:** Complex programming, multi-layered suggestions

### Variant: series
**Sequence:** P2 (instant via INDU-06) → P3 → P4 → P5 (reinforcement) → P6
**Characteristics:**
- References prior conditioning from previous episodes
- Trigger reinforcement rather than installation
- Can skip Context Setting after episode 1
- Assumes listener has series exposure
**Use Case:** Multi-part series, progressive training

---

## 1.4 Required Phase Detail (P1–P6)

### P1: Context Setting
- **Function:** Establish participation frame; set anchors; start authority/rapport; boundary normal→hypnotic.
- **Entry:** Session start. **Exit:** Oriented, focused attention. **Success:** Breathing settled, focus established.
- **Use when:** First-time listeners; therapeutic/relaxation; any time safety/trust needs priming.
- **Skip/Compress when:** Looping/series after episode 1; ultra-short runtime; pre-conditioned audience.
- **Techniques:** INDU-01, INDU-02, INDU-03, IMMR-01, AUTH-01.

### P2: Induction
- **Function:** Transition consciousness; narrow attention; reduce movement; establish compliance.
- **Entry:** Context set. **Exit:** Initial trance, eyes closed. **Success:** Relaxation response, absorption.
- **Use when:** Standard/first sessions; whenever no instant trigger is assumed.
- **Skip/Compress when:** Using instant/conditioned induction (INDU-06) in looping/series; time budget <4 min.
- **Techniques:** INDU-01–INDU-09.
- **Note:** Re-induction (same-session) is just P2 again using INDU-06 or TRIG-02.

### P3: Deepening
- **Function:** Increase depth; create progression; set depth markers; install first deepening triggers.
- **Entry:** Initial trance. **Exit:** Deeper trance, reduced critical faculty. **Success:** Countdown accepted; markers in place.
- **Use when:** Any non-looping script; when later cognitive reduction/suggestions need headroom.
- **Skip/Compress when:** Looping variant with short runtime; if P4 is merged and runtime is tight.
- **Techniques:** DEEP-01–DEEP-09, INDU-05.

### P4: Cognitive Reduction
- **Function:** Suspend analytical thinking; create blank state; voice replaces thoughts.
- **Entry:** Depth achieved. **Exit:** Critical faculty suspended. **Success:** Thought cessation accepted.
- **Use when:** Installing identity/behavioral change; authoritarian/challenge styles; complex triggers.
- **Skip/Compress when:** Light relaxation/wellness; short scripts where P3 carries light thought-quieting.
- **Techniques:** LOAD-01–LOAD-06, SEMN-01–SEMN-04, AUTH-04, AUTH-05.

### P5: Core Suggestion
- **Function:** Install primary suggestions; convert state → identity/behavior; reward linkage; persistence.
- **Entry:** Cognitive reduction achieved. **Exit:** Core suggestions accepted. **Success:** Identity/behavior shifts acknowledged.
- **Use when:** Any goal beyond relaxation; triggers/behavior/identity changes; post-P4 blankness achieved.
- **Skip/Compress when:** None for functional hypnosis; only reduce density if runtime is under ~5 min.
- **Techniques:** AUTH-01–AUTH-07, ENCD-01–ENCD-07, PLEA-01–PLEA-06, PERS-01–PERS-06, IMMR-08.

### P6: Emergence
- **Function:** Safe return; maintain installs; re-energize; close frame.
- **Entry:** Suggestions installed. **Exit:** Normal consciousness. **Success:** Alert, oriented, positive affect.
- **Use when:** All non-looping scripts; anytime duty-of-care applies.
- **Skip/Compress when:** Looping variant with P13; live sessions transitioning to another induction immediately.
- **Techniques:** EMRG-01–EMRG-05, SAFE-05.
- **v5.1 CRITICAL:** Use EMRG category for emergence. Do NOT use DEEP-03 here.

---

## 1.5 Optional Phase Detail (P7–P13)

### P7: Safety/Consent (30–60s)
- **Function:** Protective boundaries, consent validation, safety nets.
- **Entry:** After P1 (ideal); can appear late if missed. **Exit:** Boundaries affirmed. **Success:** Trust increased; scope constraints accepted.
- **Use when:** First-timers; erotic/control content; platform/TOS sensitivity; low-trust audiences.
- **Skip/Compress when:** Pre-consented captive audience; ultra-short loops.
- **Techniques:** SAFE-01–SAFE-05, DISS-01, DISS-02.

### P8: Fractionation (60–120s)
- **Function:** Depth amplification via cycling; train rapid state changes.
- **Entry:** During/after P3. **Exit:** Stronger depth. **Success:** Faster drops each cycle.
- **Use when:** Two-Stage or series; need depth fast; challenge style proving depth.
- **Skip/Compress when:** Relaxation-only; time-critical pieces; when listener fatigues.
- **Techniques:** DEEP-03, DEEP-01.
- **v5.1 NOTE:** DEEP-03 is ONLY for fractionation (P8). Never use in P6.

### P9: Scenario Immersion (90–180s)
- **Function:** Experiential visualization; sensory layering; role projection.
- **Entry:** After P4. **Exit:** Immersed in scene. **Success:** Sensory buy-in; identification.
- **Use when:** Transformation/identity themes; pleasure/escape; narrative-heavy pieces.
- **Skip/Compress when:** Pure obedience/minimalist scripts; time constraints.
- **Techniques:** IMMR-01–IMMR-08.

### P10: Trigger Installation (60–120s)
- **Function:** Install conditioned responses.
- **Entry:** After P5. **Exit:** Trigger encoded. **Success:** Association formed.
- **Use when:** Series/looping; behavioral bridges; future sessions.
- **Skip/Compress when:** Single-use relaxation; no post-hypnotic need.
- **Techniques:** TRIG-01, TRIG-03–TRIG-14.

### P11: Demonstration (60–180s)
- **Function:** Activate installed triggers; sustain bliss states; provide subjective proof of hypnosis. The "fun time" phase.
- **Entry:** After P5 or P10. **Exit:** Proof/pleasure experienced. **Success:** Listener perceives phenomenon; desire to stay/return.
- **Use when:** Challenge style; reward loops; pleasure themes; low-belief listeners needing proof.
- **Skip/Compress when:** Risk of failure (asynchronous); wellness contexts where tests feel invasive.
- **Techniques:** TRIG-02 (Trigger Activation), PLEA-01–PLEA-06, VALD-01–VALD-08.

### P12: Behavioral Bridge (30–60s)
- **Function:** Real-world commands; post-hypnotic actions.
- **Entry:** After P5. **Exit:** Action accepted. **Success:** Action likely/initiated.
- **Use when:** Marketing/social calls-to-action; habit installation.
- **Skip/Compress when:** Therapy/relaxation with no external ask.
- **Techniques:** PERS-04, PERS-06, TRIG-09.

### P13: Maintenance/Loop (60–90s)
- **Function:** Sustain trance indefinitely; prepare loop restart; no emergence.
- **Entry:** After P5 (loop terminal). **Exit:** Stable loop state. **Success:** State mirrors opening; listener can continue.
- **Use when:** Looping/ambient content; background playback.
- **Skip/Compress when:** Any script requiring wake/aftercare.
- **Techniques:** PERS-05, PERS-03, LOAD-02, VALD-04.

---

## 1.6 Phase Selection Checklist

| Phase | Use If | Avoid If | Best For |
|-------|--------|----------|----------|
| P7 Safety | First-timers; erotic/control; TOS/care needs | Pre-consented captive; ultra-short loops | Trust, risk mitigation |
| P8 Fractionation | Need depth fast; Two-Stage/Series; proof | Relax-only; fatigue risk; tight time | Depth amplification |
| P9 Scenario | Transformation/narrative; pleasure/escape | Minimalist obedience; tight runtime | Immersion, identity |
| P10 Triggers | Future control/series; behavior asks | One-off relaxation | Reusable control |
| P11 Demonstration | Trigger use; bliss/reward; proof needed | High failure risk; wellness | "Fun time", proof |
| P12 Behavioral Bridge | Real-world asks | Pure relaxation/therapy | Actions/marketing |
| P13 Maintenance | Loop/ambient | Any script needing wake | Endless play |

---

# PART 2: HOW LAYER (Tactical)

## 2.1 Technique Categories

### Category INDU: Induction Techniques
*Purpose: Achieve initial trance state (P2)*

| ID | Technique | Description |
|----|-----------|-------------|
| INDU-01 | Breath Pacing | Guide breathing rhythm for focus/relaxation |
| INDU-02 | Progressive Relaxation | Systematically relax body parts |
| INDU-03 | Fixation | Narrow attention to single point (visual/auditory) |
| INDU-04 | Eye Closure | Direct or indirect eye closure suggestion |
| INDU-05 | Countdown | Numerical descent into trance |
| INDU-06 | Instant/Conditioned Drop | Drop command assuming prior conditioning |
| INDU-07 | Kinesthetic Entrainment | Body swaying synchronized with stimulus |
| INDU-08 | Pattern Interrupt | Unexpected element disrupting conscious processing |
| INDU-09 | Environmental Dissociation | Fade external world/room/sounds |

---

### Category DEEP: Deepening Techniques
*Purpose: Intensify trance depth (P3)*

| ID | Technique | Description |
|----|-----------|-------------|
| DEEP-01 | Drop Command | Verbal trigger for depth increase |
| DEEP-02 | Staircase Visualization | Descending imagery for deepening |
| DEEP-03 | Fractionation | Wake/sleep cycling for depth amplification. **Use ONLY in P8.** |
| DEEP-04 | Numerical Deepening | Depth tied to countdown numbers |
| DEEP-05 | Voice Absorption | Voice becomes thoughts; guidance replaces internal dialogue |
| DEEP-06 | Proximity Deepening | Stimulus distance correlates with depth |
| DEEP-07 | False Bottom | Reframe achieved depth as shallow |
| DEEP-08 | Endurance Compliance | Extended pose holds with counting |
| DEEP-09 | Void/Floating Imagery | Floor dissolves / suspension in void |

---

### Category LOAD: Cognitive Load Techniques
*Purpose: Exhaust or overwhelm processing capacity (P4)*

| ID | Technique | Description |
|----|-----------|-------------|
| LOAD-01 | Thought Stopping | "No need to think" directives |
| LOAD-02 | Emptiness Installation | "Blank mind" suggestions |
| LOAD-03 | Metaphoric Shutdown | "Conscious mind takes a nap" |
| LOAD-04 | Yes Set/Compliance Ladder | Rapid yes-responses building momentum |
| LOAD-05 | Confusion Technique | Disorientation interjections |
| LOAD-06 | Garbled/Overlapping Audio | Fragmented phrases to induce overload |

---

### Category SEMN: Semantic Restructuring Techniques
*Purpose: Alter meaning/evaluation frames (P4, P5)*

| ID | Technique | Description |
|----|-----------|-------------|
| SEMN-01 | Resistance Paradox | Resistance = deeper trance |
| SEMN-02 | Circular Logic | Self-referential bypass statements |
| SEMN-03 | Control Transfer | Thinking delegated to external authority |
| SEMN-04 | Perspective Shift | "You" to "I" transition |

---

### Category DISS: Dissociation & Memory Techniques
*Purpose: State partitioning and memory manipulation (P4, P7)*

| ID | Technique | Description |
|----|-----------|-------------|
| DISS-01 | Consciousness Splitting | Awareness/control dissociation |
| DISS-02 | Amnesia Suggestion | Forget performing specific actions |
| DISS-03 | Time Distortion | Altered perception of time passing |

---

### Category AUTH: Authority Techniques
*Purpose: Establish in-session relational authority (P1, P5)*

| ID | Technique | Description |
|----|-----------|-------------|
| AUTH-01 | Authority Claims | External guidance overrides internal resistance |
| AUTH-02 | Identity Labeling | "Good subject," "obedient" |
| AUTH-03 | Retrospective Justification | "This is what you wanted" |
| AUTH-04 | Ownership Language | Belonging, ownership, possession framing |
| AUTH-05 | Internal Voice Cultivation | Planting first-person self-talk |
| AUTH-06 | Nested Authority Figure | Imagined trusted person as proxy |
| AUTH-07 | Philosophical Conditioning | Obedience = freedom reframe |
| AUTH-08 | Named Technique Meta | Explicitly naming the technique being used |

---

### Category ENCD: Encoding Techniques
*Purpose: Strengthen suggestion retention (P5)*

| ID | Technique | Description |
|----|-----------|-------------|
| ENCD-01 | Mantra Repetition | Repeated phrases for encoding |
| ENCD-02 | Call-and-Response | "Repeat after me" instructions |
| ENCD-03 | Layered Repetition | Same idea, multiple phrasings |
| ENCD-04 | Future Pacing | "Every time you..." persistence |
| ENCD-05 | Verbatim Looping | Exact passage block repetition |
| ENCD-06 | Compliance Loop Language | Listen→follow→surrender cycle |
| ENCD-07 | Lesson Structure | Numbered lesson organization |

---

### Category IMMR: Immersion Techniques
*Purpose: Create experiential reality (P9)*

| ID | Technique | Description |
|----|-----------|-------------|
| IMMR-01 | Guided Visualization | Detailed scene building |
| IMMR-02 | Sensory Layering | Multi-sense descriptions |
| IMMR-03 | Identification/Projection | Becoming the visualized self |
| IMMR-04 | Somatic Mirroring | Body sensations matching imagery |
| IMMR-05 | Persistent Metaphor | Extended metaphor throughout |
| IMMR-06 | Kinesthetic Hallucination | Feeling specific items on body |
| IMMR-07 | Concrete Externalization | Brain-as-object metaphor |
| IMMR-08 | Surrender Ritual | Key/lock or ritualized surrender sequence |

---

### Category VALD: Validation Techniques
*Purpose: Provide subjective proof (P11)*

| ID | Technique | Description |
|----|-----------|-------------|
| VALD-01 | Cognitive Convincers | Amnesia, time distortion tests |
| VALD-02 | Motor Inhibition | Heaviness, rigidity, "can't move" tests |
| VALD-03 | Command-Response Training | Immediate compliance demos |
| VALD-04 | Self-Validating Language | "Notice how true this feels" |
| VALD-05 | Behavioral Commitment | Physical actions as proof |
| VALD-06 | Physical Exhibition | Pose/display instructions |
| VALD-07 | Ideomotor Response | Finger lift, hand drift, yes/no signaling |
| VALD-08 | Mirror Self-Observation | Visualizing transformed self |

---

### Category TRIG: Trigger Techniques
*Purpose: Install and activate conditioned responses (P10, P11)*

| ID | Technique | Description |
|----|-----------|-------------|
| TRIG-01 | Trigger Installation | "When I say X, you will Y" |
| TRIG-02 | Trigger Activation | Firing an installed trigger (the "use" not "install") |
| TRIG-03 | Trigger Stacking | Multiple triggers installed |
| TRIG-04 | Conditioning Loops | Trigger→response→reward cycle |
| TRIG-05 | Asymmetric Practice | Entry trigger > exit trigger |
| TRIG-06 | Rhythm Anchoring | Timing-based conditioning |
| TRIG-07 | Multi-Modal Trigger | Cross-platform effectiveness |
| TRIG-08 | Self-Induction Training | Teaching self-hypnosis |
| TRIG-09 | Timer-Based Bridge | External timer control |
| TRIG-10 | Amnesia-Wrapped Command | Post-hypnotic with amnesia |
| TRIG-11 | Text/Platform Trigger | Written word activation |
| TRIG-12 | Temporal Bounding | Explicit trigger expiration |
| TRIG-13 | Third-Party Activation | Triggers usable by others |
| TRIG-14 | Bilateral Trigger | Works when heard, thought, or said |

---

### Category PLEA: Pleasure Association Techniques
*Purpose: Create reward linkage (P5, P11)*

| ID | Technique | Description |
|----|-----------|-------------|
| PLEA-01 | Direct Pleasure Linkage | Compliance = pleasure |
| PLEA-02 | Reward Association | Good feelings for obedience |
| PLEA-03 | Surrender-as-Freedom | Relief/freedom in giving up |
| PLEA-04 | Arousal Conditioning | Sexual arousal pairing |
| PLEA-05 | Addiction Framing | Need/crave language |
| PLEA-06 | Multiplier Stacking | Numerical intensification |

---

### Category PERS: Persistence Techniques
*Purpose: Extend identity/state across time/context (P5, P12)*

| ID | Technique | Description |
|----|-----------|-------------|
| PERS-01 | Identity Permanence | "Once a doll, always a doll" |
| PERS-02 | Internal Construct | "The doll inside you" |
| PERS-03 | Progressive Conditioning | "Each time deeper" |
| PERS-04 | Behavioral Bridge | Real-world action commands |
| PERS-05 | Timelessness Framing | "Stay as long as you like" |
| PERS-06 | Viral Propagation | Commands to share/spread |

---

### Category SAFE: Safety Techniques
*Purpose: Protective framing and boundaries (P7)*

| ID | Technique | Description |
|----|-----------|-------------|
| SAFE-01 | Safety Net Installation | Constraints on obedience (health/safety filters) |
| SAFE-02 | Consent Checkpoint | Explicit opt-in moment before proceeding |
| SAFE-03 | Stop Signal | Clear way to pause/stop and return to baseline |
| SAFE-04 | Scope Boundaries | Define what suggestions will/won't cover |
| SAFE-05 | Aftercare | Post-session grounding and stabilization |

---

### Category EMRG: Emergence Techniques (v5.1 addition)
*Purpose: Safe return to waking consciousness (P6)*

| ID | Technique | Description |
|----|-----------|-------------|
| EMRG-01 | Count-Up Return | Numerical ascent back to waking (1-5 or 1-10) |
| EMRG-02 | Body Reactivation | Progressive body awakening, energy returning |
| EMRG-03 | Orientation Restoration | Awareness of room, time, surroundings |
| EMRG-04 | Suggestion Integration | Carry positive effects forward |
| EMRG-05 | Drift-to-Sleep Option | Alternative ending for bedtime scripts |

---

## 2.2 Style Modifiers

| Style | Language Markers | Authority Level | Use With |
|-------|------------------|-----------------|----------|
| Permissive | "you may," "allow yourself," "perhaps," "if you'd like" | Low | Relaxation, wellness |
| Authoritarian | "you will," "you must," "obey," "now" | High | D/s, control |
| Challenge | "I dare you," "try to resist," "if you can" | Variable | Recreational |
| Mixed | Directive trance + permissive suggestions | Medium | Complex themes |
| Institutional | Training language, lessons, "program" | Medium-High | Education frame |
| Character | Hypnotist maintains persona | Variable | Roleplay, fantasy |
| Compulsion | "You cannot resist," inevitability, "helpless" | Very High | Extreme themes |

---

## 2.3 Phase-Technique Compatibility Matrix

*Primary = most common, Secondary = less frequent but valid.*

| Phase | Primary Techniques | Secondary Techniques |
|-------|-------------------|---------------------|
| P1 Context | INDU-03, AUTH-01, INDU-01 | INDU-04, DEEP-05, IMMR-05 |
| P2 Induction | INDU-02, IMMR-01, INDU-01, INDU-03, LOAD-02 | DEEP-05, INDU-06, LOAD-01 |
| P3 Deepening | DEEP-01, DEEP-02, IMMR-01, INDU-02, LOAD-02 | AUTH-02, AUTH-01, PLEA-01, DEEP-04 |
| P4 Cognitive | LOAD-01, LOAD-02, SEMN-03, DISS-01 | LOAD-03, AUTH-04, AUTH-05, SEMN-01 |
| P5 Core Suggestion | ENCD-01, AUTH-02, PLEA-01, PERS-01, ENCD-02 | AUTH-07, ENCD-04, IMMR-08, PERS-03 |
| P6 Emergence | EMRG-01, EMRG-02, SAFE-05 | EMRG-03, EMRG-04, PERS-01, PERS-02 |
| P7 Safety | SAFE-01, SAFE-02, SAFE-03, SAFE-04 | DISS-01, DISS-02 |
| P8 Fractionation | DEEP-03, DEEP-01 | TRIG-08, DEEP-02, INDU-06 |
| P9 Scenario | IMMR-01, IMMR-02, IMMR-03, IMMR-04 | VALD-03, VALD-02, DEEP-01, PLEA-01 |
| P10 Trigger Install | TRIG-01, TRIG-03, TRIG-04, ENCD-04 | AUTH-02, PLEA-01, IMMR-05, PERS-03 |
| P11 Demonstration | TRIG-02, VALD-03, VALD-06, PLEA-01 | INDU-06, IMMR-01, IMMR-08, VALD-04, PLEA-06 |
| P12 Behavioral Bridge | PERS-04, TRIG-09, ENCD-04 | PERS-06, VALD-05 |
| P13 Maintenance | PERS-05, PERS-03, LOAD-02, VALD-04 | ENCD-05 |

---

## 2.4 Generator Guardrails

### 1) Anchor Continuity
- Decide 3–7 anchor phrases once (e.g., "drop", "blank", "obedient", "soft", "still").
- Reuse them intentionally across phases; avoid novelty metaphors unless IMMR demands it.

### 2) Technique Parameterization
For production-grade consistency, pre-pick parameters:
- TRIG-01: trigger phrase, response, modality, duration, scope bounds
- ENCD-01: mantra phrase, repetition count
- INDU-05/DEEP-04: start/end numbers
- SAFE-03: stop word + "what happens next"
- EMRG-01: count-up range (e.g., 1–5 or 1–10)

### 3) Async Failure Risk
Default to "low-failure" validation in audio:
- Prefer VALD-04 (self-validating language) over "arm stuck" unless your audience expects it.

### 4) v5.1 Critical Rules
- **DEEP-03 is ONLY for fractionation (P8).** Never use DEEP-03 in P6 emergence.
- **P6 emergence MUST use EMRG category:** EMRG-01 (count-up), EMRG-02 (body wake), EMRG-03 (orientation), EMRG-04 (integration), or EMRG-05 (drift-to-sleep).
- **One technique ID = one meaning.** Do not overload.

---

## Appendix: Taxonomy Statistics

### Coverage (v5.1)
- **13 phases** (6 required, 7 optional)
- **92 techniques** across 14 categories
- **7 style modifiers**
- **4 structural variants**

### Technique Distribution by Category
| Category | Count | Primary Phase |
|----------|-------|---------------|
| INDU: Induction | 9 | P2 |
| DEEP: Deepening | 9 | P3 |
| LOAD: Cognitive Load | 6 | P4 |
| SEMN: Semantic | 4 | P4, P5 |
| DISS: Dissociation | 3 | P4, P7 |
| AUTH: Authority | 8 | P1, P5 |
| ENCD: Encoding | 7 | P5 |
| IMMR: Immersion | 8 | P9 |
| VALD: Validation | 8 | P11 |
| TRIG: Trigger | 14 | P10, P11 |
| PLEA: Pleasure | 6 | P5, P11 |
| PERS: Persistence | 6 | P5, P12 |
| SAFE: Safety | 5 | P7 |
| EMRG: Emergence | 5 | P6 |
