# Cult Indoctrination v3 - Master

> Status: **CURRENT** - Default conditioning session

Full mental and physical ownership sequence with warm language, proper pacing, and safe emergence. Uses post-copywriting overhauled scripts with 3x mantras and consistent narrator voice.

## Dominant Title

**Master** - commanding but not cruel, someone you might be slightly timid to approach

## Tone

- Authoritative commands ("sink", "obey", "belong")
- Possessive ownership language
- Warm rewards for compliance
- Less overtly cult-like than v1/v2 (reduced parasocial risk)

## Modules

| Order | Module | Source | Purpose |
|-------|--------|--------|---------|
| 1 | intro | script/modules/intro/ | Breathing induction, voice absorption |
| 2 | acceptance | script/modules/acceptance/ | Gentle entry, warm surrender |
| 3 | suggestibility | script/modules/suggestibility/ | Soft/receptive (not "writable") |
| 4 | fractionation_bridge | script/modules/fractionation_bridge/ | Depth lock (2x/3x) |
| 5 | obedience | script/modules/obedience/ | Warm compliance, honey metaphor |
| 6 | harem | script/modules/harem/ | Connection not competition |
| 7 | free_use | script/modules/free_use/ | Body availability |
| 8 | addiction | script/modules/addiction/ | Return compulsion |
| 9 | tease_denial_obedience | script/modules/tease_denial_obedience/ | Denial-fueled compliance |
| 10 | wakener | script/modules/wakener/ | Safe emergence + trigger |

## Build Command

```bash
python scratch/session/build_session.py cult_indoctrination_v3_master \
    intro acceptance suggestibility fractionation_bridge obedience \
    harem free_use addiction tease_denial_obedience wakener \
    --dominant-title Master
```

> **Note:** `--dominant-title` is required because `harem` and `wakener` contain `[dominant]` placeholders.

## Runtime

~95 minutes (estimated)

## Placeholder System

Scripts use `[dominant]` placeholders that get replaced at build time:

| Placeholder in Script | With `--dominant-title Master` |
|-----------------------|-------------------------------|
| `[dominant]'s presence` | `Master's presence` |
| `[dominant]'s good girl` | `Master's good girl` |
| `fully [dominant]'s` | `fully Master's` |

Scripts with placeholders:
- `harem/script.txt` - `[dominant]'s presence`, `[dominant]'s awareness`
- `wakener/script.txt` - Trigger phrases (`I am [dominant]'s good girl`)

## Key Improvements Over v2

1. Uses copywriting-overhauled scripts (warm language, 3x mantras)
2. Added acceptance module for gentler entry
3. Replaced dumbdown with obedience (warm compliance vs harsh degradation)
4. Removed brainwashing (reduces overt mind control framing)
5. Uses standard free_use instead of extended
6. Consistent narrator voice throughout
