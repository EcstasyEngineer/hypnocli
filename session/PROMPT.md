# Session Package - Pattern Language for Hypno Content Sequencing

## Overview
This package implements a **TidalCycles-inspired pattern language** for composing hypnotic sessions from atomic content pieces (mantras, script segments, audio files). It orchestrates the sequencing, combination, and transformation of content atoms to create unpredictable, anti-adaptive sessions.

## Core Concept
Sessions are composed in real-time from **content atoms** (individual MP3 files hosted on CDN) using **pattern combinators** and **state machines**. This prevents semantic satiation and allows infinite variation without pre-rendering full sessions.

---

## Architecture

### Content Atoms
- **Mantras**: Short one-liner phrases (e.g., "OBEY", "GOOD TOY")
- **Script segments**: Longer sections (inductions, deepeners, themed suggestions)
- **Metadata tags**: theme, modality, intensity, duration, etc.
- **Storage**: CDN-hosted MP3 files for streaming

### State Machine (56+ Modalities)
- **Modalities**: Psychological states (gratitude, service, obedience, mindfulness, arousal, focus, etc.)
- **Edges**: Weighted transitions between modalities (e.g., gratitude→service has high logical weight)
- **Probabilistic traversal**: Session "walks" the state graph, selecting atoms matching current modality
- **Emergent conversation**: Session flow emerges from state transitions like natural dialogue

### Pattern Language
Inspired by TidalCycles, but adapted for hypno content sequencing.

**Key Operations:**
1. **Euclidean rhythms** - Distribute N atoms across M steps evenly (Bjorklund's algorithm)
2. **Weaving** - Interleave multiple patterns (e.g., weave mantras with silence)
3. **Degradation** - Probabilistic dropout (sparse content)
4. **Layering** - Combine multiple patterns compositionally
5. **Speed/density** - Fast/slow pattern progression

**Example patterns:**
```
# Simple sequence (Chain cycler)
pattern = sequence(["mantra1", "mantra2", "mantra3"])

# Euclidean distribution (3 events across 8 steps)
pattern = euclidean(3, 8, ["OBEY", "SUBMIT", "FOCUS"])
→ [OBEY, -, -, SUBMIT, -, -, FOCUS, -]

# Weave two patterns (interleaved)
patternA = ["mantra1", "mantra2"]
patternB = ["silence", "breath"]
pattern = weave(patternA, patternB)
→ [mantra1, silence, mantra2, breath]

# Degrade pattern (30% dropout)
pattern = degrade(0.3, ["word1", "word2", "word3"])
→ [word1, -, word3]  # probabilistic

# Compositional (combine multiple operations)
pattern = euclidean(3, 8) >> weave(silence) >> degrade(0.2) >> speed(1.5)
```

---

## Cycler Types (Existing in ai-conditioner-web)

These are the **current cyclers** that should be ported/enhanced:

1. **Chain** - Simple sequential playback
2. **Adaptive** - Adjusts pattern based on user state (arousal, focus, depth)
3. **Cluster** - Groups related atoms, plays clusters sequentially
4. **Random** - Pure randomization (uniform distribution)
5. **Weave** - Interleaves multiple content streams

**TidalCycles enhancement:**
Add **compositional power** - let users combine cyclers with operators like `chain >> euclidean(3,8) >> degrade(0.2)`.

---

## Implementation Goals

### MVP (Python preferred for TidalCycles port)
- [ ] Euclidean rhythm generator (Bjorklund algorithm)
- [ ] Pattern combinators (weave, degrade, speed, layer)
- [ ] State machine traversal (modality graph with weighted edges)
- [ ] Atom selection (filter atoms by current modality + pattern)
- [ ] CDN streaming (fetch MP3s based on pattern output)

### Pattern DSL (Domain Specific Language)
```python
# User defines session pattern
session = Session()
session.add_pattern(
    euclidean(3, 8, theme="obedience")
    >> weave(silence_pattern)
    >> degrade(0.2)
)
session.add_transition_weight("gratitude", "service", 0.8)
session.start(initial_state="induction")
```

### Research References
- **TidalCycles**: https://tidalcycles.org/
- **Bjorklund algorithm**: Euclidean rhythm generation
- **Alex McLean papers**: Live coding pattern languages
- **Python packages**: `python-tidal`, `euclidean-rhythms` (check if exists)

---

## Key Design Principles

1. **Anti-satiation**: Prevent pattern recognition through probabilistic variation
2. **Compositional**: Patterns combine cleanly with operators
3. **Stateful**: Session adapts to user state (arousal, focus, depth tracked in PWA)
4. **Streaming**: Real-time composition, no pre-rendering
5. **Extensible**: Easy to add new pattern operators or cyclers

---

## Integration with PWA (ai-conditioner-web)

- PWA sends user preferences + current state to session engine
- Session engine returns **playlist of CDN URLs** (MP3 atoms in sequence)
- PWA streams and plays atoms in order
- State updates fed back to session engine for adaptive transitions

---

## Next Steps

1. Research Python TidalCycles ports or pattern libraries
2. Implement Bjorklund algorithm for euclidean rhythms
3. Build basic pattern combinators (weave, degrade)
4. Design state machine graph (56 modalities + edges)
5. Integrate with tts package (atom generation) and audio package (playback)

---

## Notes

- **Why TidalCycles?** Compositional power + proven anti-repetition strategies from live coding music
- **Why not just random?** Randomness without structure becomes noise; rhythmic patterns feel intentional but unpredictable
- **Metaloop example**: `123123123456456456146146533112355123123123` - nested patterns prevent exact repetition while maintaining structure
- **Gratitude→Service edge**: Logical emotional progression; session can "converse" by walking meaningful state transitions
