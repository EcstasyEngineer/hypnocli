# Cult Indoctrination v3 - Goddess

> Status: **CURRENT** - Warm devotional variant

Same structure as Master variant but with inviting, seductive tone. "Venus flows... Venus knows... Venus owns."

## Dominant Title

**Goddess** - inviting, warm, seductive not stern, devotional not destructive

## Tone

Based on Venus's guidance:
- Replace cold "void" with "warmth" or "light"
- Emptiness feels like being held, not erased
- Commands become invitations: "yield to the pleasure", "let go into bliss"
- Submission feels like sinking into silk
- Recurring motif: "Every breath draws you closer to the divine"
- Longing becomes holy

## Modules

| Order | Module | Source | Purpose |
|-------|--------|--------|---------|
| 1 | intro | script/modules/intro/ | Breathing induction, voice absorption |
| 2 | acceptance | script/modules/acceptance/ | Gentle entry, warm surrender |
| 3 | suggestibility | script/modules/suggestibility/ | Soft/receptive |
| 4 | fractionation_bridge | script/modules/fractionation_bridge/ | Depth lock (2x/3x) |
| 5 | obedience | script/modules/obedience/ | Warm compliance |
| 6 | harem | script/modules/harem/ | Connection not competition |
| 7 | free_use | script/modules/free_use/ | Body availability |
| 8 | addiction | script/modules/addiction/ | Return compulsion |
| 9 | tease_denial_obedience | script/modules/tease_denial_obedience/ | Denial-fueled compliance |
| 10 | wakener | script/modules/wakener/ | Safe emergence + trigger |

## Build Command

```bash
python scratch/session/build_session.py cult_indoctrination_v3_goddess \
    intro acceptance suggestibility fractionation_bridge obedience \
    harem free_use addiction tease_denial_obedience wakener \
    --dominant-title Goddess
```

> **Note:** `--dominant-title` is required because `harem` and `wakener` contain `[dominant]` placeholders.

## Runtime

~95 minutes (estimated)

## Placeholder System

Scripts use `[dominant]` placeholders that get replaced at build time:

| Placeholder in Script | With `--dominant-title Goddess` |
|-----------------------|--------------------------------|
| `[dominant]'s presence` | `Goddess's presence` |
| `[dominant]'s good girl` | `Goddess's good girl` |
| `fully [dominant]'s` | `fully Goddess's` |

## Scripts With Placeholders

- `harem/script.txt` - `[dominant]'s presence`, `[dominant]'s awareness`
- `wakener/script.txt` - Trigger phrases (`I am [dominant]'s good girl`)

## Quality Checks

The build system automatically:
1. **FAILS** if `[dominant]` found without `--dominant-title` specified
2. **WARNS** if gendered pronouns (he/him/his/she/her) found near `[dominant]`

Currently no pronoun issues - scripts use possessive forms only.
