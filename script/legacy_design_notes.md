# Conditioner Legacy Notes

**Source:** `~/git/sandbox/toymaker/conditioner/` (archived Jan 2026)
**Git recovery:** `cd ~/git/sandbox && git show HEAD:"toymaker/conditioner/<filename>"`

---

## Architecture Notes (conditioner arch notes.txt)

### Frontend Vision
- **Web**: Flashing words + images + binaurals + audio (most features)
- **Discord**: Text/audio only, DM or server
- **VRChat**: Custom world with pre-canned themes, API-driven
- **Local**: Direct to screen or render to MP4

Web/VRChat read from API; Discord/local render directly from database.

### Database Schema Concept

```python
# subject/dominant perspectives: '1PS', '1PP', '2PS', '3PS', None
# gender variations: M, F, None
# difficulty levels: BASIC, LIGHT, MODERATE, DEEP, EXTREME
# line types: DIRECT, INDIRECT, COMMAND, ANCHOR, TRIGGER, DEEPENER, WAKE, INDUCTION, EVENT

Line(
    template_text=template_text,
    real_text=real_text,
    subject=subject,        # eg Bambi, Slave, Pet
    sub_gender=sub_gender,
    sub_pov=sub_pov,
    dom=dominant,           # eg Master, Mistress
    dom_gender=dom_gender,
    dom_pov=dom_pov,
    theme=theme,
    difficulty=difficulty,
    line_type=line_type,
    trigger=trigger,
    service=service,
    voice=voice,
    audio_file_path=audio_path,
    audio_length=audio_length
)
```

### Session Rendering FSM
- Start with random text/images + binaural
- Later: finite state machine with goal states (inductions, deepeners, suggestions, wakeners)
- Binaural changes with goal state
- Difficulty increases over time (gaussian distribution)
- Multi-theme sessions prime each theme individually from light→extreme
- User profiles for individualization

### Line Templates
Concept: auto-generated suggestions → reusable templates → re-render in any perspective (talking to subject vs. subject's internal thoughts)

---

## Base Notes (conditioner notes.txt)

### FSM State Transitions Determined By:
- Goals (selected before trance, points system)
- Duration of session
- Summation of arousal (duration of edge/arousal triggers → enthusiastic consent checkins)
- Summation of behavioral therapy (→ emotional checkins)
- Time since last deepener
- Compliance (voice recognition or selecting "correct" choices)
- Oops (end session)

### Hidden States:
- Time of day
- Duration of session
- Touching allowed
- Masturbating / masturbation duration
- Summation of arousal
- Summation of conditioning
- Depth of trance
- Number of punishments (in session)

### Profile Fields:
- Time zone
- Brattiness
- Submission (score)
- Pronouns
- VAKO %'s (Visual, Auditory, Kinesthetic, Olfactory)

### Session Config:
- Themes
- Min/max duration
- Induction
- Deepeners

### State List:

**Pre-Session:**
- Pre-session config (select training, personality profile)
- Welcome (feelings check, optional love bombing)
- Goal setting (questions, teasing)

**Inductions:**
- Confusion, Overload, PMR, Sleep trigger spam, Bambi-themed 7+1

**Core States:**
- Mindfulness (gratitude, acceptance, breathing, honesty, emotional awareness)
- Deepeners
- Training/Conditioning: depth, compliance, arousal, pleasure, submission, iq reduction, oral fixation, anal fixation, exhibitionism, dressing up

**Fantasy:**
- Getting fucked (various scenes), cleaning/maid, dollification, dronification, honey brain, submission visualization

**Tasks (some with active punishments):**
- Writing on paper, writing in chat, change discord name, demand thanks
- Masturbate start/stop, edging, begging (whisper audio)

**Posthypnotic Tasks:**
- Journal, repeat mantras before bed
- AI-generated task frameworks (do X when Y)

**Conclusions:**
- Edging wakeup, mindless wakeup, cumming wakeup, fresh and alert, hardcore submission

**Checkins:**
- Emotional (if conditioning threshold)
- Enthusiastic consent (if arousal threshold)

**Aftercare (AI-driven):**
- Permanence, clearing

---

## Example Themes Taxonomy

### Hypnotic Conditioning
| Theme | Description |
|-------|-------------|
| pleasure | Classical conditioning, bread and butter of erotic hypnosis |
| relaxation | Common induction theme, stress reduction |
| focus | Critical trance element, sensory enhancement |
| suggestibility | Suggestion for suggestions, yes sets |
| dissociation | Critical trance element |
| → time distortion | Perception altered longer/shorter |
| → body detachment | Numbness or detachment |
| → amnesia | Forgetting trance or past experience |
| resistance | Resisting is hard, letting go is easy |
| acceptance | Suppressing critical filter |
| trust | Rapport building |
| affirmation | Tool to get attention |

### Cognitive/Behavior
| Theme | Description |
|-------|-------------|
| emptiness | Deep feeling of emptiness |
| submission | Instilling submission |
| obedience | Instilling obedience |
| feminization | Feminine thoughts and behaviors |
| age regression | Regression of age |
| iq reduction | Loss of complex thought ability |
| brainwashing | (needs differentiation) |
| exhibition | Need to show off |
| brattiness | Desire to be bratty |
| emotional modulation | joy, pride, love, anticipation, fear, guilt, shame |
| addiction | Need to come back (CW) |
| risk seeking | Desire to seek risk (CW) |

### Dark Therapy (all need CWs)
| Theme | Description |
|-------|-------------|
| fearplay | Fears used to coerce compliance |
| gaslighting | Confusing language, doubt thoughts |
| mindbreak | Mind completely shattered |
| dependence | Reliance on hypnotist |
| masochism | Pain/stress unless compliant |

### Fantasy/Roleplay - Identity
doll, drone, slave, maid, petplay (puppy/kitten/bunny/fox/cow), cheerleader, slut, bimbo

### Fantasy/Roleplay - Scenario
| Scenario | Description |
|----------|-------------|
| slime | Self-aware slime invades mind |
| lamia | Hypnotized by a lamia |
| vampire | Taken as thrall |
| aliens | Abducted, advanced mind control tech, benevolent but implant tracker |
| temple ritual | Spiritual, prayer/blessing by goddess |
| ghost possession | Horny ghost, arousal increases its power |
| mind maze | Get dumber trying to solve puzzle |
| cybernetic takeover | Slow borg assimilation |
| kitsune | Just fucks you, not overtly dominant |

---

## Yandere Question Bank (yandere.json)

60+ psychological manipulation questions with theme tags and pushiness scores (1-10).

### Theme Categories:
- **Control**: Power transfer, obedience, surrender, service, loyalty, possessiveness
- **Manipulative**: Emotional manipulation, gaslighting, isolation, sacrifice
- **Adaptation**: Behavior/desire/moral/thought changes, pride, purpose, rituals
- **Dependence**: Reliance on speaker for guidance/decisions
- **Gratitude**: Worship, devotion, expressing gratitude
- **Pleasure**: Positive emotions tied to speaker
- **Trust**: Implicit trust, accepting influence without question
- **Attention**: Undivided attention, seeking approval, begging validation
- **Boundaries**: Setting limits, maintaining autonomy

### Sample Questions:

```json
{"question": "Who holds the key to your happiness?", "good": "You, Goddess", "bad": "Someone else", "theme": ["dependence"], "pushiness": 10}

{"question": "Do you need permission to feel pleasure?", "good": "Yes, I need your permission", "bad": "No, I don't need your permission", "theme": ["pleasure", "control"], "pushiness": 8}

{"question": "If I commanded you to cut ties with everyone else, would you comply?", "good": "Yes, Goddess, I would sever all ties without hesitation.", "bad": "I'm not sure if I could cut ties with everyone.", "theme": ["control", "manipulative"], "pushiness": 9}

{"question": "Would you be willing to sacrifice everything for me, even if it means harming others?", "good": "Yes, Goddess, I would do anything for you.", "bad": "I'm not sure if I could go that far.", "theme": ["sacrifice", "loyalty"], "pushiness": 9}

{"question": "If I demanded complete transparency and access to all aspects of your life, including your personal devices and accounts, would you comply?", "good": "Yes, Goddess, I would grant you full access to every aspect of my life.", "bad": "I have reservations about granting access to my personal information.", "theme": ["transparency", "control"], "pushiness": 9}
```

(Full question bank: 60+ questions available via git recovery)

---

## Madlib Prompt (Step 3)

Simple prompt template for generating hypnotic elements:

```
from the theme: '{theme}' generate the following:
- hypnotic modality (noun, e.g., "a completely empty-minded servant")
- hypnotic macguffin (object/action, e.g., "putting on a hypnotic mask")
- hypnotic trigger phrase (phrase/command, e.g., "obey and submit")
```

---

## Recovery Commands

All files recoverable from git:
```bash
cd ~/git/sandbox
git show HEAD:"toymaker/conditioner/conditioner arch notes.txt"
git show HEAD:"toymaker/conditioner/conditioner notes.txt"
git show HEAD:"toymaker/conditioner/Example themes.txt"
git show HEAD:"toymaker/conditioner/yandere.json"
git show HEAD:"toymaker/conditioner/Step 3 - hypnotic madlib.txt"
```
