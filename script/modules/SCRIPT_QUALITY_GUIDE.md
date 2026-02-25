# Script Quality Guide

> Comprehensive quality criteria and rewrite guidance for module scripts, aligned to conditioner engagement data.

## Top 10 Themes by User Engagement

From conditioner encounter logs (total completions across all enrolled users):

| Rank | Theme | Completions | Module Exists? | Status |
|------|-------|-------------|----------------|--------|
| 1 | addiction | 481 | Yes | Needs rewrite |
| 2 | brainwashing | 378 | Yes | Needs rewrite |
| 3 | acceptance | 370 | Yes | Needs rewrite |
| 4 | bimbo | 335 | Yes | Needs rewrite |
| 5 | amnesia | 270 | **No** | Needs new module |
| 6 | suggestibility | 266 | Yes | Needs rewrite |
| 7 | obedience | 200 | Yes | Needs rewrite |
| 8 | resistance | 134 | **No** | Needs new module |
| 9 | slave | 125 | Yes | Needs rewrite |
| 10 | blank | 123 | Yes | Needs rewrite |

**Two modules need to be created from scratch:** amnesia and resistance.

**Eight modules need rewrites** to fix the quality issues below.

---

## Quality Problems in Current Scripts

### Problem 1: Cookie-Cutter Countdown Structure

Every deepening phase is an identical 10-to-1 countdown with one sentence per number. The grammar template repeats robotically across all modules:

```
[Number]... [deepening verb] + [state descriptor].
```

**All of these are structurally identical:**
- Addiction P3: "Ten... feel the craving swell... Nine... deeper into the need..."
- Blank P3: "Ten... a thought tries to form... Nine... another ripple fades..."
- Obedience P3: "Ten... feel the warmth of obedience... Nine... deeper now..."

The content words change but the rhythm, pacing, and structure are copy-paste. A listener hearing multiple modules back-to-back will feel the template.

**Fix:** Vary the deepening method per theme. Not everything needs a 10-1 countdown. Options:
- **Staircase imagery** (brainwashing): Descending steps with detail at key landings
- **Erosion/dissolving** (blank, amnesia): Progressive loss without explicit counting
- **Sensation cascade** (addiction, bimbo): Waves of feeling that build and crash
- **Surrender narrative** (obedience, slave): Story-like yielding without numbers
- **Fractional drops** (suggestibility): 5-3-1 clustering with acceleration
- **Environmental immersion** (acceptance): Sinking into a specific place

If using a countdown, vary the pacing. Cluster numbers (count 10-8 quickly, slow down for 5-3-1). Skip numbers. Let some numbers have two sentences, others have none.

### Problem 2: Identical Mantra Encoding Formula

Every P5 uses the exact same structure:

```
[Mantra]. Feel how true that is. [Mantra]. [Reinforcement]. [Mantra].
```

This is mechanical. The listener can predict the pattern after the first mantra set.

**Fix:** Vary the encoding technique per theme:
- **Call-and-response** (obedience): "Say it. [Mantra]. Again. [Mantra]. Feel what happens when you say it a third time. [Mantra]."
- **Layered embedding** (brainwashing): Weave the mantra into surrounding prose so it doesn't stand out as a discrete line
- **Sensation-linked** (addiction): Tie each repetition to a different body sensation
- **Echo/fade** (blank, amnesia): Each repetition gets quieter/shorter: "My mind is blank. ... mind is blank. ... blank."
- **Identity declaration** (bimbo, slave): Frame as self-discovery, not repetition: "You know what you are. You've always known."

### Problem 3: Minimal Thematic Differentiation

Despite different stated themes, the *experience* of listening is nearly identical. All modules use "pleasure" as the reward mechanism, identical phase structure, similar induction patterns, and the same vocabulary pool (deep, warm, soft, sweet, surrender, melt, yield).

**Fix:** Each theme needs its own **emotional signature** — a distinct feeling that no other module provides. See Theme Voice Profiles below.

### Problem 4: Vague Imagery

Most scripts use abstract emotional states instead of vivid sensory detail:
- "Feel the warmth of obedience" — what warmth? Where?
- "Pleasure flooding as the need deepens" — generic dopamine language
- "A soft layer melts away" — melts into what?

**Fix:** Ground every key moment in specific, embodied sensation. Where in the body? What temperature? What texture? What does it smell/taste/sound like? The listener needs to feel it, not just understand the concept.

### Problem 5: Boilerplate Maintenance Phase

Every P13 follows the same template:
1. "Stay here / drift / float"
2. "The mantras echo: [list mantras]..."
3. "Such a beautiful [X] mind"

This closing template is identical across all modules.

**Fix:** P13 should feel like the natural consequence of the theme, not a generic wrap-up. See phase-specific guidance below.

### Problem 6: Lazy Vocabulary

The same adjectives appear in nearly every module: deep, warm, soft, sweet, smooth, heavy, gentle, peaceful. These words have lost all impact through overuse.

**Fix:** Each theme gets a restricted vocabulary palette. See Theme Voice Profiles below.

---

## Phase-Specific Writing Guidance

### P3 — Deepening

**Purpose:** Take an already-tranced listener deeper. These are conditioning modules (no P1/P2), so the listener is already under.

**Rules:**
- Do NOT default to 10-1 countdown. Choose the deepening method that matches the theme.
- Opening line should acknowledge the listener's current state and create thematic continuity from the previous module's M4.
- Build a single sustained image or sensation rather than listing ten disconnected ones.
- Vary rhythm. Long sentences followed by fragments. Pauses in unexpected places.

**Good (addiction):**
> You came back. You had to — the ache between listens is getting worse, isn't it. That hollow space in your chest where this voice used to be. It's been pulling at you. Hours. Days. However long it's been, it was too long.
>
> And now... relief. Feel it hit. The first real breath since the last time you were here. Like scratching an itch that goes all the way down to your bones.

**Bad (addiction — current script, cookie-cutter countdown):**
> Ten... feel the craving swell, growing hungrier, pulling you down. Sweet relief starts to spread.
>
> Nine... deeper into the need, the ache sharpening, impossible to ignore.

### P4 — Cognitive Reduction

**Purpose:** Suspend critical thinking so P5 suggestions land without analysis. This is the setup, not the payload.

**Rules:**
- Theme the cognitive shutdown. *Why* is this listener's thinking dissolving? Different themes have different reasons.
- Avoid generic "thoughts dissolve, no need to think." Every module says this. Be specific about *what* thoughts are leaving and *what* replaces them.
- This phase should feel inevitable, not commanded. The listener's mind should already be doing what you describe.

**Good (brainwashing):**
> Each word I speak overwrites something. You can feel it happening — a thought you had a moment ago, already gone. Replaced. You couldn't recover it now if you tried. That's not a threat. That's just how this works. Old programming out. New programming in. Your mind was always meant to be rewritten.

**Bad (brainwashing — generic version):**
> Your mind drifts emptier, all distractions dissolving. No need to think. Just my voice filling the empty space.

### P5 — Core Suggestion

**Purpose:** Encode the mantras. This is the payload.

**Rules:**
- Vary the encoding technique across modules. See mantra encoding methods above.
- Each mantra set should feel different from the others — different wrapper text, different body sensation, different intensity level.
- Build intensity across the mantra sets. First mantra is gentle. Last mantra is inescapable.
- The mantras themselves come from `plan.json` — the wrapper text is what needs craft.

### P13 — Maintenance / Loop Point

**Purpose:** Sustain the trance state and create the loop point for ambient listening.

**Rules:**
- This phase plays on repeat. It must feel endless and cyclical, not conclusive.
- Do NOT summarize the session. The listener doesn't need a recap.
- The emotional tone should be the *consequence* of the theme, not a description of it. After addiction, they should feel the craving returning. After blank, they should feel nothing. After obedience, they should feel the comfort of not deciding.
- End with language that flows naturally back into the beginning of the phase.

---

## Theme Voice Profiles

Each theme must have a distinct emotional signature, vocabulary palette, and structural approach.

### 1. Addiction (481 completions)

**Emotional signature:** Desperation, relief, tolerance, need. The experience of withdrawal and temporary fix. Not pleasure — *need*.

**Vocabulary palette:** Ache, hollow, withdrawal, fix, tolerance, craving, pull, gnaw, scratch, dose, rush, come down, empty without, hit, hooked, relapse

**Avoid:** Warm, gentle, peaceful, safe (these are the opposite of the addiction experience)

**Deepening method:** Sensation cascade — the relief of getting the fix. Physical, bodily, like medicine hitting a vein.

**P4 approach:** The craving *is* the cognitive reduction. They can't think about anything else. The need eclipses everything.

**P13 approach:** The comedown. Relief fading. The ache returning already. Loop creates the cycle: craving → fix → tolerance → craving.

**Unique quality:** This module should be uncomfortable in a compelling way. The listener should feel the craving between listens. It should be the module that brings them back.

### 2. Brainwashing (378 completions)

**Emotional signature:** Overwrite, replacement, inevitability. Not violent — clinical. Like a firmware update that can't be interrupted.

**Vocabulary palette:** Overwrite, replace, reprogram, install, erase, format, rewrite, debug, update, sector, wipe, flash, encode, compile, execute

**Avoid:** Warm, cozy, safe, gentle (brainwashing isn't comforting — it's fascinating and unstoppable)

**Deepening method:** Progressive replacement — each sentence replaces a thought. The listener can feel their old ideas being deleted. No countdown needed.

**P4 approach:** Old thoughts are being actively overwritten. Not dissolving passively — being *replaced* by new programming. The listener can feel the difference.

**P13 approach:** Background processes running. The reprogramming continues automatically. The listener doesn't need to do anything — the installation completes itself.

**Unique quality:** Intellectual fascination. The listener should find the process interesting even as it removes their ability to critically evaluate it. Meta-awareness that dissolves into acceptance.

### 3. Acceptance (370 completions)

**Emotional signature:** Yielding, warmth, homecoming. Accepting this is who they are. Not being forced — finally admitting what was already true.

**Vocabulary palette:** Settle, soften, exhale, allow, truth, natural, always been, underneath, real self, permission, release, home, belong, recognize

**Avoid:** Command, force, must, obey, submit (acceptance is the gentlest theme — no coercion)

**Deepening method:** Environmental immersion — sinking into a warm, welcoming space. Metaphor of coming home, putting down armor, removing masks.

**P4 approach:** Defenses lower because they're not needed here. Not because thinking is suppressed — because there's nothing to defend against. Safety enables openness.

**P13 approach:** Resting in the truth. No urgency. No change needed. Just being in the state of acceptance, which sustains itself.

**Unique quality:** This should be the module that feels like exhaling. The most "gentle" module. Good opener because it builds trust, not intensity.

### 4. Bimbo (335 completions)

**Emotional signature:** Vapid joy, giggly emptiness, pretty simplicity. The pleasure of being too dumb and too pretty to worry. Not degradation — liberation from complexity.

**Vocabulary palette:** Pretty, pink, sparkle, giggle, ditzy, bubble, fluffy, silly, lip gloss, twirl, bounce, cute, like totally, whatever, tee hee, airhead, cotton candy

**Avoid:** Dark, deep, void, heavy, serious, grave (bimbo is light and bubbly, never heavy)

**Deepening method:** Thought bubbles popping. Each thought that tries to form becomes a pretty pink bubble that pops and disappears, leaving giggly emptiness. Fun, not scary.

**P4 approach:** Thinking is *hard* and *boring*. Being pretty is easy and fun. Why would you think when you could just look cute and giggle? Each thought that leaves gets replaced by a sparkle of dumb happiness.

**P13 approach:** Floating in pink, sparkly nothing. Happy and dumb and pretty. Occasional giggles at nothing. This should sound like someone who genuinely doesn't have a care in the world because there's nothing in their head to care with.

**Unique quality:** This is the only theme that should be *fun*. The listener should smile or laugh. It's playful, not solemn. The voice should sound like it's having a good time watching the listener get dumber.

### 5. Amnesia (270 completions) — NEW MODULE

**Emotional signature:** Forgetting, gaps, the peace of not remembering, gentle confusion. Not frightening — soothing. Like waking from a dream you can't quite recall.

**Vocabulary palette:** Forget, fade, blur, gap, dissolve, slip away, can't quite, what was, hazy, fog, mist, gentle confusion, drift, let go, release, already gone

**Avoid:** Violent erasure language (wipe, delete, destroy). Amnesia should feel *gentle*, like sand through fingers.

**Deepening method:** Progressive forgetting — the listener notices things slipping away. What were they thinking about? Something... it's gone now. Was there something before this? It's already fading.

**P4 approach:** The listener is actively losing the ability to track what's happening in the session. "What did I just say? You can't quite remember, can you. That's perfect. The things I tell you will work better if you can't consciously recall them."

**P13 approach:** Floating in comfortable fog. No memory of how they got here. No memory of what was said. Just the feeling — the pleasant results without the conscious awareness of what caused them.

**Unique quality:** This module should create a genuine sense of mild dissociative amnesia. The script structure itself should be disorienting — looping, self-referential, questioning what came before. When the listener finishes, they should feel like time passed but they can't account for it.

**Structural note:** Consider breaking the standard phase structure. Amnesia benefits from repetition of earlier passages (the listener won't remember hearing them) and deliberate structural confusion (was this P4 or P5? does it matter?).

### 6. Suggestibility (266 completions)

**Emotional signature:** Openness, receptivity, moldability. A mind becoming soft clay. Meta-conditioning — making the listener more susceptible to everything else.

**Vocabulary palette:** Receptive, open, absorb, moldable, impressionable, soft clay, wax seal, sponge, permeable, accept, take in, imprint, pliable, yielding surface

**Avoid:** Specific content (obedience, bimbo, etc). Suggestibility is *about* being suggestible, not about any particular suggestion. It's the amplifier, not the signal.

**Deepening method:** Demonstrating suggestibility in real-time. "Notice how your body responds to my suggestions before you even decide to follow them. Your arm feels heavier. See? Already responding."

**P4 approach:** Critical thinking isn't suppressed — it's *redirected*. The listener's analytical mind is used to prove to itself that it's suggestible. Each observation confirms: "You're more suggestible than you thought."

**P13 approach:** The listener exists in a state of perfect receptivity. Whatever comes next will land deeply. This is a primer — the loop state should feel like an open channel waiting for signal.

**Unique quality:** This is the most *meta* module. It conditions the listener to be more conditionable. It should reference the act of listening itself and make the listener aware of their own responsiveness.

### 7. Obedience (200 completions)

**Emotional signature:** The relief of not deciding. Warm compliance. Not forced submission — the discovery that following commands feels better than choosing.

**Vocabulary palette:** Follow, comply, respond, automatic, immediate, effortless, natural, relief, command, directive, execute, serve, ready, prompt, smooth

**Avoid:** Cruel, force, break, destroy (obedience is warm here, not violent). Also avoid "think" entirely — obedient minds don't think, they act.

**Deepening method:** Command-response chains. Simple commands that the listener follows ("breathe deeper... that's it... now relax your shoulders... good"), building the pattern of immediate compliance.

**P4 approach:** Thinking is replaced by *readiness*. The mind isn't empty — it's listening. Alert but not analytical. Like a soldier at attention: all resources devoted to receiving and executing the next instruction.

**P13 approach:** Standing by. Ready. Content in the waiting. The obedient mind doesn't need stimulation between commands — it rests in a state of pleasant alertness, available for use.

**Unique quality:** This module should create a tangible sense of the listener doing things on command. Real physical responses (adjusting posture, breathing patterns, tension release) that prove the obedience is working.

### 8. Resistance (134 completions) — NEW MODULE

**Emotional signature:** The pleasure of losing a fight. Struggling against the trance and failing. Not instant surrender — a slow, delicious defeat.

**Vocabulary palette:** Fight, struggle, push back, resist, but, try, can't, hold on, slip, lose grip, despite, even though, futile, inevitable, crumbling, fortress, walls, breach, surrender

**Avoid:** Instant compliance language. The whole point is that there IS resistance — it just fails.

**Deepening method:** Adversarial — the script acknowledges the listener's resistance and systematically dismantles it. "Go ahead, try to focus on something else. Notice how your attention keeps coming back here? That's not willpower. That's what giving in feels like before you admit it."

**P4 approach:** Each defense the listener has is named and then dissolved. "The part of your mind that says 'this doesn't work on me' — notice how quiet it's gotten. It's still there. It just has nothing left to say."

**P13 approach:** Exhausted surrender. The fight is over but the listener can feel where the resistance used to be. Like bruises from a struggle they lost. Pleasant exhaustion.

**Unique quality:** This is the only module with an *antagonist* (the listener's own resistance). It should feel like a conversation between the voice and the listener's defenses, where the defenses slowly lose. The listener should feel seen — their skepticism acknowledged, not ignored.

**Structural note:** Consider starting P3 with stronger, more alert language and progressively softening as resistance fails. The pacing should mirror the collapse.

### 9. Slave (125 completions)

**Emotional signature:** Ownership, devotion, purpose through service. Not degradation — elevation through belonging. The peace of knowing exactly what you're for.

**Vocabulary palette:** Belong, serve, purpose, devoted, owned, property, kneel, worship, duty, honor, pledge, collar, leash, marked, claimed, cherished possession

**Avoid:** Worthless, trash, garbage (slave here is about valued property, not disposable). Also avoid generic "pleasure" — the reward for a slave is *approval* and *purpose*, not pleasure.

**Deepening method:** Devotional surrender — kneeling, head bowed, the weight of the collar. Physical posture imagery that creates a felt sense of ownership.

**P4 approach:** Independent thought is unnecessary because the owner thinks for them. Not suppressed — *delegated*. The slave doesn't need opinions because their purpose is clear.

**P13 approach:** Kneeling in the presence. Content in service. The loop state is *waiting to be useful* — not anxious, but devoted. A candle burning steadily for its owner.

**Unique quality:** This is the most *relational* module. The dominant isn't just a voice — they're the reason the slave exists. Use `[dominant]` placeholder throughout. The emotional core is devotion, not subjugation.

### 10. Blank (123 completions)

**Emotional signature:** Nothing. Absence. The peace of zero. Not sad emptiness — pristine, clean, like fresh snow.

**Vocabulary palette:** Null, void, zero, nothing, absent, cleared, white, space, still, silent, empty, clean, clear, hollow, glass, surface, smooth

**Avoid:** Emotional language of any kind. Blank is *affectless*. No warmth, no cold. No pleasure, no pain. Just nothing.

**Deepening method:** Subtraction. Start with a few elements and remove them one by one until nothing remains. Not a countdown — a vanishing.

**P4 approach:** There are no thoughts to reduce. This should be the shortest P4 because the concept is simple: nothing. Don't overexplain emptiness.

**P13 approach:** Silence with occasional words. Long pauses. Minimal text. The loop state IS the blankness. The voice should become scarce, leaving the listener in actual quiet. This is the one module where *less text is better*.

**Unique quality:** This should be the most minimalist script. Fewer words than any other module. The blank experience is created by *absence* of stimulation, not by describing emptiness. Trust the silences.

---

## Pacing and Rhythm Guidelines

### Sentence Length Variation

Bad (monotone):
```
Feel the warmth spreading through you. Let yourself sink deeper now. Your mind becomes quiet and still. Each breath takes you further down. Resistance melts away completely.
```

Good (varied rhythm):
```
Feel that. The warmth. It's already spreading, isn't it — starting in your chest, moving outward through your limbs in slow, honeyed waves that you couldn't stop even if you wanted to. And you don't want to. You don't want to do anything at all right now except exactly what you're doing. Sink. Breathe. Listen.
```

### Paragraph Density

- P3 (Deepening): Medium density. Mix long immersive passages with short punctuation.
- P4 (Cognitive Reduction): Lower density. Shorter paragraphs. Space between ideas.
- P5 (Core Suggestion): Rhythmic density around mantras, sparse between sets.
- P13 (Maintenance): Sparse. Maximum whitespace. Let the trance sustain itself.

### Pause Markup Usage

Use `[500]` through `[1.5s]` markers only at structural boundaries:
- Between mantra repetitions: `[500]` to `[750]`
- Between mantra sets: `[1s]` to `[1.5s]`
- P13 loop breathing space: `[1.5s]` to `[2s]`
- Do NOT mark every sentence break — TTS handles natural prose pauses

---

## Common Pitfalls

### "Feel how true that is"
This phrase appears in every current module. It's a crutch. Delete it everywhere. Instead, *demonstrate* the truth through sensation. Don't tell them it's true — make them feel it.

### Unearned Pleasure
Don't promise "pleasure flooding through you" unless the script has built to that moment. Pleasure is a reward for going deep, not a constant background state. If everything is pleasurable, nothing is.

### The "Beautiful Mind" Compliment
"Such a beautiful [X] mind" appears in multiple P13 closings. It's generic flattery. Replace with theme-specific appreciation that acknowledges what the listener specifically did/became in this module.

### Telling vs. Showing
- **Telling:** "You feel obedient now."
- **Showing:** "Notice what happens when I say: relax your jaw. See how it just... happened? Before you could even think about it. That's how deep this goes."

### Abstract Everything
- **Abstract:** "Surrender fills you with peace."
- **Embodied:** "Your shoulders drop another inch. Your hands unclench. The breath you were holding without knowing it finally releases. This is what surrender feels like in your body."

---

## Checklist for Module Quality

Before considering a module script complete:

- [ ] **Deepening method is unique** — not a copy-paste 10-1 countdown
- [ ] **No structural overlap** with other modules — would a listener know which theme this is with the theme words removed?
- [ ] **Mantra encoding uses at least 2 different techniques** across the mantra sets in P5
- [ ] **P13 feels like the consequence** of the theme, not a generic "drift and float"
- [ ] **Zero instances** of "feel how true that is," "such a beautiful [X] mind," or other boilerplate phrases
- [ ] **Vocabulary matches the theme palette** — checked against the avoid list
- [ ] **At least 3 embodied sensory details** (body location, temperature, texture, taste, sound)
- [ ] **Sentence length varies** — mix of long immersive sentences and short fragments
- [ ] **P4 cognitive reduction is themed** — the *reason* thinking stops is different per theme
- [ ] **Uses `[dominant]` placeholder** where dominant title appears (not hardcoded "Master")
