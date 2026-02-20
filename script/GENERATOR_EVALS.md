# Generator Evaluation Notes

## Generation Modes

### `--mode phased` (default)
One API call per phase. Each call uses a fixed 4-message context:
- `[system]` SYSTEM_WRITER
- `[assistant]` condensed plan summary (~12 lines)
- `[assistant]` last 6 lines of prior phase prose (tail context, omitted for P1)
- `[user]` phase brief (PHASE_WRITER_TEMPLATE_V2)

**Cost:** ~N calls for an N-phase script (typically 5–8 calls + 1 plan call).
**Advantage:** Each phase gets full token budget for its own content. Model commits fully to the current phase's register — fragments stay fragments, depth stays deep.
**Disadvantage:** Slightly more API overhead. Tail context is 6 lines, not full prior phase — the model doesn't see its own full prior output.

### `--mode oneshot`
Single API call generates the entire script. Uses 3-message context:
- `[system]` SYSTEM_WRITER
- `[assistant]` condensed plan summary
- `[user]` phase table + ONE_SHOT_WRITER_TEMPLATE

Output is split on `<!-- PHASE: ... -->` delimiter markers.

**Cost:** 1 write call + 1 plan call (total = 2 API calls regardless of phase count).
**Advantage:** Cheapest. Model can plan the full arc before writing.
**Disadvantage:** Model must compress all phases into one generation. In practice this causes:
  - Phase compression (each phase becomes shorter)
  - Register bleed (deepening phases drift toward full sentences)
  - "Thinking out loud" failure mode — model comments on what it's doing rather than just doing it

---

## Provider Comparison (Feb 2026, blank-mind theme, 5 min, Permissive style)

### Opus Rankings (Claude Opus 4.6)

| Rank | Script | Score | Verdict |
|------|--------|-------|---------|
| 1 | **Claude phased** | 9/10 | Only script that trusts its own craft enough to stop explaining itself |
| 2 | **Gemini oneshot** | ~7/10 | Best P3 in the set; P4 mistakes aggression for depth |
| 3 | **Claude oneshot** | ~7/10 | Beautiful architecture, but "thinks out loud when it should be whispering" |
| 4 | **xAI phased** | 7/10 | Solid countdown and balloon, undone by P1 reading the instruction manual |
| 5 | **Gemini phased** | 6.5/10 | Competent mantra work drowning in four abandoned objects |
| 6 | **xAI oneshot** | 4/10 | Creates anxiety, demands surrender it hasn't earned |

### Codex Rankings

| Rank | Script | Score | Verdict |
|------|--------|-------|---------|
| 1 | **Claude phased** | 8.6/10 | Most coherent trance arc with clean deepening |
| 2 | **Claude oneshot** | 8.0/10 | Nearly as strong, slightly flatter in mantra craft |
| 3 | **xAI phased** | 7.4/10 | Good rhythm; needs a real developmental mantra |
| 4 | **Gemini phased** | 7.0/10 | Nice imagery, a bit too narrative |
| 5 | **xAI oneshot** | 6.5/10 | Functional but generic and stitched |
| 6 | **Gemini oneshot** | 5.7/10 | Over-directive, fails mantra spec, breaks flow |

### Consensus
Both reviewers agree: **Claude phased #1, xAI oneshot last**. Middle four differ slightly.
Key disagreement: Opus rates Gemini oneshot higher than Claude oneshot (P3 quality); Codex rates Claude oneshot higher (overall coherence).

---

## Identified Failure Modes

### "Thinking Out Loud" (primary oneshot failure mode)
The script describes or explains what it's doing rather than doing it.

**Examples from Claude oneshot P4:**
- `"The stillness isn't something you made — it was here already."` — philosophical commentary; invites cognition during a sub-cognitive phase
- `"Notice how easy it is to just be blank."` — meta-cognitive; taps the listener on the shoulder to point out they're sinking
- `"Full of nothing"` — paradox that invites processing

**Root cause:** In oneshot mode, the model plans the full arc before writing, which makes it more analytical about the content. Phased mode forces it to commit to each register without the full-script perspective.

**Contrast:** Claude phased P4 just does it — `"Not broken. Not lost. Just... blank."` No commentary on why blank is good, just the state.

### P1 Instruction Manual (xAI failure mode)
Announcing the session structure in P1 destroys the fourth wall.

**Example:** `"We'll ease into a blank mind through your breath, deepen that peaceful empty space, plant suggestions for receptive calm, then bring you back gently."`

A listener who hears the technical roadmap starts auditing compliance rather than surrendering.

### Abandoned Objects (Gemini phased failure mode)
Introducing a concrete visualization object then dropping it for a new one.

Gemini phased: candle flame (P1) → cool mist (P2) → marble stairs + fog (P3) → sky + clouds (P4).
Four objects = listener rebuilds visualization from scratch every phase = never settles.

**Fix:** Pick one object in P1 and carry it through, or transition objects explicitly.

### Aggressive Possession Without Trust (both Gemini/xAI oneshot failure mode)
`"You belong to this surrender."` / `"Hooked on the drop."` in P4 of a **Permissive-style** blank-mind script, before the trust ladder has earned that register.

Note: state-directed versions ("hooked on the drop", "belonging to surrender", "addicted to this feeling") are **preferred** per SYSTEM_WRITER. The failure here is trust ladder timing and style mismatch — using Authoritarian-register possession in a Permissive-style session that hasn't built toward it. "Hooked on the drop" in a Compulsion session deep in P5 is correct; the same phrase in a Permissive blank-mind P4 is a rung skip.

Opus: *"A script that creates anxiety, demands surrender it hasn't earned, and uses addiction language on a listener it just met."*

### Mantra Wallpaper
Mantra repeated identically without developmental progression. Becomes background noise rather than deepening.

**Bad:** `"Mind blank. Empty. Peaceful. Receptive."` × 3, identical.
**Good:** First pass — observation. Second pass — confirmation + praise. Third pass — pleasure/identity link.

---

## Lint Gate (LINT-01 through LINT-07)

Currently implemented in `phase_chat_generator.py::lint_phase()`:

| Code | Check |
|------|-------|
| LINT-01 | Sentence length: P3/P4/P8 >20w, P2 >15w |
| LINT-02 | Future tense `you('ll\|will)` in non-P1 |
| LINT-03 | Banned phrases: honeyed, subconscious mind, serene rapture, peaceful empty, luminous |
| LINT-04 | Similes `like a/an` or `as X as` in P3/P4/P5/P8 |
| LINT-05 | Technique ID leak e.g. `DEEP-03` in script text |
| LINT-06 | POV violation: "my voice", "this recording", "addicted to me" |
| LINT-07 | Announcing: "I'm going to suggest", "let these words sink in", "repeating now" |

### Candidates for future lint rules (identified by Opus/Codex review)
- **LINT-08** "Thinking out loud" — philosophical commentary / meta-cognitive instructions in P3/P4/P5
- ~~LINT-09~~ — removed. Possession/addiction language is correct and desired in Compulsion/Authoritarian/submission sessions; too context-dependent to lint reliably. SYSTEM_WRITER already governs the distinction.
- **LINT-10** Abandoned object detection — hard; would need object tracking across phases (probably not worth it as a regex)
- **LINT-11** P1 roadmap announcement — "we'll [do X] then [do Y] then [bring you back]"
