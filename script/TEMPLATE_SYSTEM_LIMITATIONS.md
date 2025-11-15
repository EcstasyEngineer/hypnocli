# Template System Capabilities & Limitations

**Scope**: This document applies ONLY to the **Mantra System** (template-based affirmations)

**Does NOT apply to**: Script generation (`generate_segment.py`, `compose_session.py`) - those have no limitations

**Current Implementation**: Option 1 (Single Input Type)

## Canonical Form

Mantras can be generated in two forms:

1. **1PS + Named Dominant**: `"I obey Master"` (most common)
2. **1PS + Pronoun Dominant**: `"I obey you"` (conversational)

Both convert to templates with different placeholders.

## Template Structure

```
{subject} [obey|obeys] {dominant}
```

### Available Placeholders

**Subject** (person receiving commands):
- `{subject}` / `{subject_subjective}` - subjective case (I, you, Bambi)
- `{subject_objective}` - objective case (me, you, Bambi)
- `{subject_possessive}` - possessive case (my, your, Bambi's)

**Dominant** (person giving commands):
- `{dominant}` / `{dominant_subjective}` - Always resolves to NAME (Master, Mistress)
- `{dominant_objective}` - Objective case based on perspective (NOT USED in current system)
- `{dominant_possessive}` - Possessive case based on name (Master's, Mistress's)

**Verb Conjugations**:
- `[base|third]` - e.g., `[obey|obeys]`, `[trust|trusts]`

## ✅ Supported Use Cases

### 1. All Subject Perspectives with Named Dominant

**Input**: `"I obey Master"`
**Template**: `{subject} [obey|obeys] {dominant_name}`

| Perspective | Dominant | Rendered | Use Case |
|-------------|----------|----------|----------|
| 1PS | Master | "I obey Master" | Subject's internal affirmation |
| 2PS | Master | "You obey Master" | Dominant speaking TO subject |
| 3PS | Master | "Bambi obeys Master" | Third-party description |
| 1PS | Mistress | "I obey Mistress" | Different dominant |
| 2PS | Goddess | "You obey Goddess" | Mixed variation |

### 2. Subject Addressing Dominant with "You"

**Input**: `"I obey you"`
**Template**: `{subject} [obey|obeys] {dominant_subjective}`

| Perspective | Dominant | Rendered | Use Case |
|-------------|----------|----------|----------|
| 1PS | you | "I obey you" | Subject speaking TO dominant |
| 3PS | you | "Bambi obeys you" | Third-party addressing dominant |

✅ **This works!** The converter handles "you" → `{dominant_subjective}`, and the renderer supports `dominant_pronoun='you'`

### 3. Dominant as Grammatical Subject

**Input**: `"Master commands me"`
**Template**: `{dominant_name} [command|commands] {subject_objective}`

| Perspective | Dominant | Rendered | Use Case |
|-------------|----------|----------|----------|
| 1PS | Master | "Master commands me" | Dominant acting on subject |
| 2PS | Master | "Master commands you" | Dominant acting on 2PS subject |
| 1PS | you | "You command me" | Conversational command |

✅ **This works!** Mantras are NOT limited to subject's perspective - dominant can be grammatical subject too!

### 4. Multiple Grammatical Cases (Same Role)

**Input**: `"Master guides me deeper"`
**Template**: `{dominant_name} guides {subject_objective} deeper`

| Perspective | Rendered |
|-------------|----------|
| 1PS | "Master guides **me** deeper" |
| 2PS | "Master guides **you** deeper" |
| 3PS | "Master guides **Bambi** deeper" |

✅ **This works** because `{subject_objective}` is just a different grammatical case of the same role.

### 5. Any Combination Where Subject ≠ Dominant

As long as the subject and dominant refer to **semantically distinct entities**, all combinations work.

**Note**: You can mix `{dominant_name}` and `{dominant_subjective}` in the same template for phrases like "I obey you, Master" (future enhancement).

## ❌ NOT Supported (by design)

### 1. Dominant Speaking Directly ("You obey me")

**Cannot render**:
- "You obey **me**" (dominant commanding subject)
- Any variant with dominant as 1st person ("I", "me", "my")

**Reason**: The renderer doesn't support `dominant_pronoun="I"` or `"me"` - only supports:
- Named dominants ("Master", "Mistress")
- 2nd person ("you")
- 3rd person ("he", "she", "they")

**Why**: The template system is designed for **subject's perspective** (affirmations/responses), not dominant's commands

**Workaround**:
- Use **script generation** (`generate_segment.py`) for dominant's direct commands
- Scripts can naturally include "You obey me" in prose without templates

### 2. Mixed Name + Pronoun Addressing (Future Enhancement)

**Not currently implemented**:
- "I obey you, Master"
- "You obey me, Mistress"

**Reason**: Would require BOTH `{dominant_name}` AND `{dominant_subjective}` in same template

**Note**: The converter CAN detect this pattern, but the rendering logic needs enhancement to support both placeholders simultaneously

**Workaround**: Generate as two separate mantras OR use script generation

### 3. Call-and-Response (Partial Support)

**Subject's responses**: ✅ **SUPPORTED**
```
"I will obey you"  ← Can template this!
```

**Dominant's commands**: ❌ **NOT SUPPORTED**
```
"You will obey me"  ← Cannot template this (needs dominant="me")
```

**Workaround**:
- Template the subject's half
- Generate dominant's commands using **script system** (`generate_segment.py`)
- For interactive sessions, use prose generation instead of templates

## 🚫 Invalid Combinations (Filtered Out)

### Same Pronoun for Both Roles

**Never valid**: `subject_pronoun="you"` + `dominant_pronoun="you"`

**Would render**: "You obey you" ❌ (semantically nonsensical)

**Solution**: Stress test automatically **filters this combination** (stress_test_templates.py:156-160)

## Design Philosophy

### What "Perspective" Actually Means

**Important clarification**: Mantras are NOT limited to "subject's perspective"!

The system supports:
- **Subject as grammatical subject**: "I obey Master"
- **Dominant as grammatical subject**: "Master commands me"
- **Either role in any grammatical position**

The limitation is **semantic role**, not grammatical perspective:
- `{subject_*}` placeholders = always the submissive role
- `{dominant_*}` placeholders = always the dominant role
- **Cannot flip these semantic roles** (can't make subject command dominant)

### Why Certain Limitations Exist

The current system follows **Legacy System Design** (see `ai-conditioner-web/legacy/python-implementation/utils/tools.py`):

1. **Dominant pronoun support**: "you", "he", "she", "they" (NOT "I/me" - dominant doesn't speak as first person)
2. **Perspective parameter controls subject pronoun only** (1PS, 2PS, 3PS)
3. **Semantic roles are fixed** - placeholders determine who dominates, not grammar

### When You'd Need More

The following features would require dual input types or metadata flags:

1. **Interactive hypnosis scripts** with real-time commands ("You obey me NOW")
2. **Call-and-response training** sessions
3. **Dialogue-based content** where dominant speaks directly without name

### Current Recommendation

**For now**: Keep Option 1 (simple, single input type)

**Future**: If interactive/conversational features needed, implement Option 2 (dual input types) or Option 3 (metadata flags)

## Summary Table

| Feature | Supported | Notes |
|---------|-----------|-------|
| Multiple perspectives (1PS/2PS/3PS) | ✅ | Core functionality |
| Named dominants (Master/Mistress) | ✅ | Primary use case |
| Pronoun dominants ("you") | ✅ | Subject addressing dominant |
| Dominant as grammatical subject | ✅ | "Master commands me" works! |
| Subject as grammatical subject | ✅ | "I obey Master" works! |
| Grammatical cases (I/me/my) | ✅ | Multiple cases per role |
| Third-person subjects (Bambi) | ✅ | Via 3PS perspective |
| Subject addressing dominant ("I obey you") | ✅ | Fully supported! |
| Dominant commanding in 1PS ("You obey me") | ❌ | Use script generation |
| Mixed addressing ("you, Master") | ⚠️ | Future enhancement |
| Call-and-response (subject's half) | ✅ | "I obey you" works |
| Call-and-response (dominant's half) | ❌ | Use script generation |
| Self-hypnosis (subject=dominant) | ❌ | Not implemented |

## Usage Guidelines

### ✅ Do Use Mantra Templates For:
- Subject affirmations: "I obey Master", "I trust you"
- Subject responses: "I will obey you"
- Dominant actions: "Master commands me", "You guide me deeper"
- Multi-perspective variations of same concept
- Batch mantra generation with `generate_mantras.py`

### ❌ Don't Use Mantra Templates For:
- Dominant's commands: "You obey me" → Use **script generation** instead
- Full hypnosis sessions → Use `generate_segment.py` and `compose_session.py`
- Interactive/dialogue scripts → Use **script generation** (no template limitations)

### 📝 Important Distinction

**Mantra System** (this document):
- Short affirmations/sentences
- Template-based rendering
- Perspective variations
- Has limitations described above

**Script System** (NO limitations):
- `generate_segment.py` - Full prose paragraphs
- `compose_session.py` - Multi-segment sessions
- Can include ANY conversational style
- No template constraints - generates naturally

## Testing

Run comprehensive stress test:
```bash
python3 stress_test_templates.py --quick
```

Expected: **100% pass rate** (24/24 tests, invalid combinations filtered)
