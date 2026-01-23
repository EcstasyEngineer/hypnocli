# Canonical Taxonomy for Hypnosis Script Generation
## Version 5.2 — Complete Reference

**Changes from v5.1:**
- Restructured phases: 6 required (P1-P6) + 4 optional modules (M1-M4)
- Merged P7 (Safety/Consent) into P1 (Context + Safety)
- Demoted P8 (Fractionation) to technique-only (DEEP-03 usable during P3)
- Merged P9 (Scenario Immersion) into P5 (Core Suggestion + Immersion)
- Renamed remaining optional phases to modules (M1-M4)
- Added XFER category for transfer/persistence techniques
- Added new EMRG techniques (EMRG-06 through EMRG-10)

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
| P1 | Context + Safety | Accept frame, establish attention focus, receive protective boundaries | 30-90s |
| P2 | Induction | Release conscious control, enter trance | 60-90s |
| P3 | Deepening | Descend deeper through guided progression | 90-180s |
| P4 | Core Suggestion + Immersion | Accept and internalize primary suggestions, enter detailed visualization | 120-300s |
| P5 | Emergence | Return to normal consciousness | 30-90s |

### Optional Modules

| ID | Module | Listener Task | Insert Point | Duration |
|----|--------|---------------|--------------|----------|
| M1 | Critical Softening | Release analytical thinking, accept receptive state | Between P3 and P4 | 60-120s |
| M2 | Transfer | Accept conditioned responses, receive real-world action commands | After P4, before P5 | 60-120s |
| M3 | Demonstration | Experience trigger activation, bliss states, or proof of hypnosis | After P4 or M2, before P5 | 60-180s |
| M4 | Maintenance/Loop | Sustain trance for loop restart | Terminal (replaces P5) | 60-90s |

**Note on Fractionation:** Wake/sleep cycling (DEEP-03) is a technique, not a phase. Use during P3 when depth amplification is needed.

**Total: 5 required phases + 4 optional modules**

---

## 1.2 Sequence Rules

### Required Ordering (Standard Scripts)

```
P1 → P2 → P3 → [M1] → P4 → [M2] → [M3] → P5
                                          ↓
                                     or [M4]
```

**Rules:**
1. P1 (Context + Safety) must be first (may skip for loops/series after episode 1)
2. P2 (Induction) must precede P3 (Deepening)
3. P3 (Deepening) must precede P4 (Core Suggestion + Immersion)
4. P4 must precede P5 (Emergence) or M4 (Loop)
5. P5 (Emergence) must be final, OR M4 (Maintenance/Loop) replaces P5 as terminal

### Module Insertion Matrix

| Module | Valid Insertion Points | Notes |
|--------|------------------------|-------|
| M1 Critical Softening | Between P3 and P4 | Cognitive reduction before suggestions |
| M2 Transfer | After P4, before P5/M4 | Trigger installation + real-world bridging |
| M3 Demonstration | After P4 or M2, before P5/M4 | "Fun time" - trigger activation, bliss, proof |
| M4 Maintenance/Loop | Terminal (replaces P5) | Sustain trance, prepare loop restart |

**Note:** Fractionation (DEEP-03) is a technique used *within* P3, not a separate module.

---

## 1.3 Structural Variants

### Variant: standard
**Sequence:** P1 → P2 → P3 → P4 → P5
**Characteristics:** Full induction-deepening-suggestion-emergence arc
**Use Case:** Standalone sessions, first-time listeners

### Variant: deep
**Sequence:** P1 → P2 → P3 → M1 → P4 → P5
**Characteristics:**
- Includes Critical Softening (M1) before suggestions
- Deeper cognitive reduction for complex programming
**Use Case:** Identity work, behavioral change, complex suggestions

### Variant: loop
**Sequence:** P2 → P3 → M2 → M3 → M4 (loops to P2)
**Characteristics:**
- Skips P1 (Context + Safety) - assumes opt-in
- Skips P5 (Emergence) - replaced by M4 (Maintenance)
- Uses instant/conditioned induction (INDU-06)
- Terminal state mirrors opening for seamless loop
**Use Case:** Background/ambient trance, extended sessions

### Variant: twostage
**Sequence:** P1 → P2 → P3 + light suggestions → P3 [DEEP-03] → M1 → P4 → P5
**Characteristics:**
- Light suggestions during initial deepening
- P3 with fractionation (DEEP-03) creates stage boundary
- Critical Softening (M1) after fractionation
- Deep suggestions after blank state achieved
**Use Case:** Complex programming, multi-layered suggestions

### Variant: series
**Sequence:** P2 (instant via INDU-06) → P3 → P4 → P5
**Characteristics:**
- References prior conditioning from previous episodes
- Trigger reinforcement rather than installation
- Can skip Context + Safety after episode 1
- Assumes listener has series exposure
**Use Case:** Multi-part series, progressive training

---

## 1.4 Required Phase Detail (P1–P5)

### P1: Context + Safety
- **Function:** Establish participation frame; set anchors; start authority/rapport; boundary normal→hypnotic; protective boundaries.
- **Entry:** Session start. **Exit:** Oriented, focused attention, boundaries affirmed. **Success:** Breathing settled, focus established, trust increased.
- **Use when:** First-time listeners; therapeutic/relaxation; any time safety/trust needs priming.
- **Skip/Compress when:** Looping/series after episode 1; ultra-short runtime; pre-conditioned audience.
- **Techniques:** INDU-01, INDU-02, INDU-03, IMMR-01, AUTH-01, SAFE-01–SAFE-05.

### P2: Induction
- **Function:** Transition consciousness; narrow attention; reduce movement; establish cooperation.
- **Entry:** Context set. **Exit:** Initial trance, eyes closed. **Success:** Relaxation response, absorption.
- **Use when:** Standard/first sessions; whenever no instant trigger is assumed.
- **Skip/Compress when:** Using instant/conditioned induction (INDU-06) in looping/series; time budget <4 min.
- **Techniques:** INDU-01–INDU-09.
- **Note:** Re-induction (same-session) is just P2 again using INDU-06 or TRIG-02.

### P3: Deepening
- **Function:** Increase depth; create progression; set depth markers; install first deepening triggers.
- **Entry:** Initial trance. **Exit:** Deeper trance, reduced critical faculty. **Success:** Countdown accepted; markers in place.
- **Use when:** Any script requiring depth before suggestions.
- **Skip/Compress when:** Looping variant with short runtime; ultra-short scripts.
- **Techniques:** DEEP-01–DEEP-09, INDU-05.
- **Note:** Fractionation (DEEP-03) is used here when depth amplification via wake/sleep cycling is needed.

### P4: Core Suggestion + Immersion
- **Function:** Install primary suggestions; convert state → identity/behavior; reward linkage; persistence; experiential visualization; sensory layering.
- **Entry:** Depth achieved (or M1 Critical Softening completed). **Exit:** Core suggestions accepted, immersed in scene. **Success:** Identity/behavior shifts acknowledged, sensory buy-in.
- **Use when:** Any goal beyond relaxation; triggers/behavior/identity changes; transformation/narrative themes.
- **Skip/Compress when:** None for functional hypnosis; only reduce density if runtime is under ~5 min.
- **Techniques:** AUTH-01–AUTH-07, ENCD-01–ENCD-07, PLEA-01–PLEA-06, PERS-01–PERS-06, IMMR-01–IMMR-08.

### P5: Emergence
- **Function:** Safe return; maintain installs; re-energize; close frame.
- **Entry:** Suggestions installed. **Exit:** Normal consciousness. **Success:** Alert, oriented, positive affect.
- **Use when:** All non-looping scripts; anytime duty-of-care applies.
- **Skip/Compress when:** Looping variant with M4; live sessions transitioning to another induction immediately.
- **Techniques:** EMRG-01–EMRG-10, SAFE-05.
- **CRITICAL:** Use EMRG category for emergence. Do NOT use DEEP-03 here.

---

## 1.5 Optional Module Detail (M1–M4)

### M1: Critical Softening (60–120s)
- **Function:** Suspend analytical thinking; create blank state; voice replaces thoughts.
- **Entry:** After P3 (Deepening). **Exit:** Critical faculty suspended. **Success:** Thought cessation accepted.
- **Use when:** Installing identity/behavioral change; authoritarian/challenge styles; complex triggers; deep programming.
- **Skip when:** Light relaxation/wellness; short scripts where P3 carries light thought-quieting.
- **Techniques:** ABSR-01–ABSR-09, AUTH-04, AUTH-05.

### M2: Transfer (60–120s)
- **Function:** Install conditioned responses; real-world commands; post-hypnotic actions; generalization to waking life.
- **Entry:** After P4 (Core Suggestion). **Exit:** Triggers encoded, actions accepted. **Success:** Associations formed, bridge to real-world established.
- **Use when:** Series/looping; behavioral bridges; future sessions; habit installation.
- **Skip when:** Single-use relaxation; no post-hypnotic need; no external ask.
- **Techniques:** TRIG-01, TRIG-03–TRIG-14, PERS-04, PERS-06, ENCD-04.

### M3: Demonstration (60–180s)
- **Function:** Activate installed triggers; sustain bliss states; provide subjective proof of hypnosis. The "fun time" module.
- **Entry:** After P4 or M2. **Exit:** Proof/pleasure experienced. **Success:** Listener perceives phenomenon; desire to stay/return.
- **Use when:** Challenge style; reward loops; pleasure themes; low-belief listeners needing proof.
- **Skip when:** Risk of failure (asynchronous); wellness contexts where tests feel invasive.
- **Techniques:** TRIG-02 (Trigger Activation), PLEA-01–PLEA-06, VALD-01–VALD-08.

### M4: Maintenance/Loop (60–90s)
- **Function:** Sustain trance indefinitely; prepare loop restart; no emergence.
- **Entry:** After P4 or M2/M3 (loop terminal). **Exit:** Stable loop state. **Success:** State mirrors opening; listener can continue.
- **Use when:** Looping/ambient content; background playback.
- **Skip when:** Any script requiring wake/aftercare.
- **Techniques:** PERS-05, PERS-03, ABSR-02, VALD-04.
- **Note:** M4 replaces P5 (Emergence) as the terminal state.

---

## 1.6 Module Selection Checklist

| Module | Use If | Avoid If | Best For |
|--------|--------|----------|----------|
| M1 Critical Softening | Identity/behavior change; authoritarian style; complex triggers | Light relaxation; short scripts | Deep programming |
| M2 Transfer | Series/looping; future sessions; real-world asks | One-off relaxation; no post-hypnotic need | Triggers, behavioral bridge |
| M3 Demonstration | Trigger use; bliss/reward; proof needed | High failure risk; wellness | "Fun time", proof |
| M4 Maintenance/Loop | Loop/ambient content | Any script needing wake | Endless play |

**Note:** Fractionation (DEEP-03) is a technique used within P3, not a separate module. Use when depth amplification via wake/sleep cycling is needed.

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

### Category ABSR: Absorption & Critical Softening Techniques
*Purpose: Quiet analytical thinking, create receptive state (M1, P3)*

| ID | Technique | Description |
|----|-----------|-------------|
| ABSR-01 | Cognitive Quieting | "No need to think" / "thoughts drift away" directives |
| ABSR-02 | Mental Spaciousness | "Blank mind" / "empty" suggestions |
| ABSR-03 | Metaphoric Shutdown | "Conscious mind takes a nap" |
| ABSR-04 | Yes Set/Compliance Ladder | Rapid yes-responses building momentum |
| ABSR-05 | Confusion Technique | Disorientation interjections |
| ABSR-06 | Resistance Paradox | Resistance = deeper trance |
| ABSR-07 | Circular Logic | Self-referential bypass statements |
| ABSR-08 | Control Transfer | Thinking delegated to external authority |
| ABSR-09 | Perspective Shift | "You" to "I" transition |

*Note: v5.2 merged former LOAD and SEMN categories. LOAD-06 (Garbled/Overlapping Audio) removed as accessibility-unfriendly.*

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
| PERS-07 | Fetish Object | Imbuing a physical object with ongoing hypnotic significance (anthropological sense: an object believed to hold power or embody connection). Headphones as ritual gateway, collar as ownership symbol, pendant as connection anchor. Distinct from TRIG (stimulus→response)—fetish objects carry persistent symbolic meaning rather than triggering discrete state changes. Etymology: Portuguese *feitiço* (charm, sorcery). |

---

### Category XFER: Transfer & Generalization Techniques
*Purpose: Bridge suggestions from trance to waking life (M2, P4)*

| ID | Technique | Description |
|----|-----------|-------------|
| XFER-01 | Portable Retrieval Cue | Breath/phrase/touch cue for re-accessing target state |
| XFER-02 | Implementation Intention | "If X happens, then I do Y" framing |
| XFER-03 | Context Generalization | Rehearse suggestions across multiple real-life scenes |
| XFER-04 | Waking Bridge | Suggestions delivered during/near emergence for integration |
| XFER-05 | Temporal Bounding | Explicit trigger/effect expiration unless renewed |
| XFER-06 | Revocation Protocol | Explicit "cancel" phrase or "this ends when I choose" |
| XFER-07 | Practice Schedule | Instructions for short, safe practice reps post-session |

---

### Category CHECK: State Management Techniques
*Purpose: Pacing controls, state checks, coherence (all phases)*

| ID | Technique | Description |
|----|-----------|-------------|
| CHECK-01 | Anchor Selection | Explicitly choose breath/body/voice/count as main anchor |
| CHECK-02 | Pacing-Leading | Describe present experience, then guide change |
| CHECK-03 | Micro-ratification | "You may notice..." small, non-demanding confirmations |
| CHECK-04 | Coherence Lock | Don't switch sensory channel abruptly early in trance |
| CHECK-05 | Return-Path Reminder | Periodic "later you'll come back feeling clear..." |
| CHECK-06 | Anti-Stuck Filter | Avoid "can't wake / can't move" unless consented |
| CHECK-07 | Comfort Check | Quick "still comfortable / breathing easy?" gate |
| CHECK-08 | Dissociation Check | "If you feel spaced-out, open eyes and orient" |
| CHECK-09 | Expectation Seeding | Explicitly previewing session structure/agenda before induction. Reduces listener uncertainty and cognitive load, increasing compliance. "In this session, you'll experience three things..." Common in professional hypnosis as "pretalk." Can be distinct section before P1 or woven into Context Setting. |

---

### Category SAFE: Safety Techniques
*Purpose: Protective framing and boundaries (P1, P5)*

| ID | Technique | Description |
|----|-----------|-------------|
| SAFE-01 | Safety Net Installation | Constraints on obedience (health/safety filters) |
| SAFE-02 | Consent Checkpoint | Explicit opt-in moment before proceeding |
| SAFE-03 | Stop Signal | Clear way to pause/stop and return to baseline |
| SAFE-04 | Scope Boundaries | Define what suggestions will/won't cover |
| SAFE-05 | Aftercare | Post-session grounding and stabilization |
| SAFE-06 | Suitability Prompt | "If you have X condition, consult a professional" |
| SAFE-07 | Context Gate | Not while driving/operating machinery |
| SAFE-08 | Agency Reminder | "You remain in control; you can stop any time" |
| SAFE-09 | Comfort Permission | "Swallow, move, scratch, adjust—then return" |
| SAFE-10 | Exit Protocol | Micro-protocol: open eyes, look around, orient, breathe |

---

### Category EMRG: Emergence Techniques
*Purpose: Safe return to waking consciousness (P5)*

| ID | Technique | Description |
|----|-----------|-------------|
| EMRG-01 | Count-Up Return | Numerical ascent back to waking (1-5 or 1-10) |
| EMRG-02 | Body Reactivation | Progressive body awakening, energy returning |
| EMRG-03 | Orientation Restoration | Awareness of room, time, surroundings |
| EMRG-04 | Suggestion Integration | Carry positive effects forward |
| EMRG-05 | Drift-to-Sleep Option | Alternative ending for bedtime scripts |
| EMRG-06 | Waking Suggestion | Reinforce core suggestions during emergence for better integration |
| EMRG-07 | Physiological Reset | Normal muscle tone, steady breathing, clear head |
| EMRG-08 | Reorientation Sweep | Room, sounds, time, body awareness checklist |
| EMRG-09 | Post-session Safety | Pause before standing/driving, hydrate |
| EMRG-10 | Self-efficacy Tag | "You can reaccess this state when you want"

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

| Phase/Module | Primary Techniques | Secondary Techniques |
|--------------|-------------------|---------------------|
| P1 Context + Safety | INDU-03, AUTH-01, INDU-01, SAFE-01–SAFE-04 | INDU-04, DEEP-05, IMMR-05, SAFE-06–SAFE-10 |
| P2 Induction | INDU-02, IMMR-01, INDU-01, INDU-03, ABSR-02 | DEEP-05, INDU-06, ABSR-01 |
| P3 Deepening | DEEP-01, DEEP-02, IMMR-01, INDU-02, DEEP-03 | AUTH-02, AUTH-01, PLEA-01, DEEP-04 |
| P4 Core Suggestion | ENCD-01, AUTH-02, PLEA-01, PERS-01, ENCD-02, IMMR-01–IMMR-08 | AUTH-07, ENCD-04, PERS-03 |
| P5 Emergence | EMRG-01, EMRG-02, SAFE-05, EMRG-06 | EMRG-03, EMRG-04, EMRG-07–EMRG-10 |
| M1 Critical Softening | ABSR-01, ABSR-02, ABSR-08, DISS-01 | ABSR-03–ABSR-07, AUTH-04, AUTH-05 |
| M2 Transfer | TRIG-01, TRIG-03, TRIG-04, ENCD-04, PERS-04 | AUTH-02, PLEA-01, PERS-06, TRIG-09 |
| M3 Demonstration | TRIG-02, VALD-03, VALD-06, PLEA-01 | INDU-06, IMMR-01, IMMR-08, VALD-04, PLEA-06 |
| M4 Maintenance | PERS-05, PERS-03, ABSR-02, VALD-04 | ENCD-05 |

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

### 4) v5.2 Critical Rules
- **DEEP-03 is for fractionation during P3.** Never use DEEP-03 in P5 emergence.
- **P5 emergence MUST use EMRG category:** EMRG-01 through EMRG-10.
- **One technique ID = one meaning.** Do not overload.
- **ABSR techniques replace LOAD/SEMN.** Use ABSR-01 through ABSR-09 for critical softening.

---

## Appendix: Taxonomy Statistics

### Coverage (v5.2)
- **9 phases/modules** (5 required phases + 4 optional modules)
- **124 techniques** across 15 categories
- **7 style modifiers**
- **5 structural variants**

### Technique Distribution by Category
| Category | Count | Primary Phase/Module |
|----------|-------|---------------------|
| INDU: Induction | 9 | P2 |
| DEEP: Deepening | 9 | P3 |
| ABSR: Absorption & Critical Softening | 9 | M1, P3 |
| DISS: Dissociation | 3 | M1 |
| AUTH: Authority | 8 | P1, P4 |
| ENCD: Encoding | 7 | P4 |
| IMMR: Immersion | 8 | P4 |
| VALD: Validation | 8 | M3 |
| TRIG: Trigger | 14 | M2 |
| PLEA: Pleasure | 6 | P4, M3 |
| PERS: Persistence | 7 | P4, M2 |
| XFER: Transfer & Generalization | 7 | M2, P4 |
| CHECK: State Management | 9 | All phases |
| SAFE: Safety | 10 | P1, P5 |
| EMRG: Emergence | 10 | P5 |
