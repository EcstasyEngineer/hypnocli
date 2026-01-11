# Template Variable System

Mantras use placeholder variables that get rendered based on user preferences (POV, gender, names).

## Render Context

```json
{
  "subject_pov": "first | third_pronoun | third_named",
  "subject_gender": "M | F | N",
  "subject_noun": "puppet",

  "dominant_pov": "second | third_pronoun | third_named",
  "dominant_gender": "M | F | N",
  "dominant_noun": "Master"
}
```

## Variable Reference

### Subject Variables

| Variable | 1st | 3rd M | 3rd F | 3rd N | Named |
|----------|-----|-------|-------|-------|-------|
| `{subject_subjective}` | I | he | she | they | puppet |
| `{subject_objective}` | me | him | her | them | puppet |
| `{subject_possessive}` | my | his | her | their | puppet's |
| `{subject_possessive_pronoun}` | mine | his | hers | theirs | puppet's |
| `{subject_noun}` | puppet | puppet | puppet | puppet | puppet |
| `{subject_reflexive}` | myself | himself | herself | themself | puppet |

### Dominant Variables

| Variable | 2nd | 3rd M | 3rd F | 3rd N | Named |
|----------|-----|-------|-------|-------|-------|
| `{dominant_subjective}` | you | he | she | they | Master |
| `{dominant_objective}` | you | him | her | them | Master |
| `{dominant_possessive}` | your | his | her | their | Master's |
| `{dominant_possessive_pronoun}` | yours | his | hers | theirs | Master's |
| `{dominant_noun}` | Master | Master | Master | Master | Master |
| `{dominant_reflexive}` | yourself | himself | herself | themself | Master |

## Verb Conjugation

Use `[1st_form|3rd_form]` for subject-verb agreement:

```
{subject_subjective} [am|is] obedient
{subject_subjective} [obey|obeys] without question
{subject_subjective} [have|has] no thoughts
```

Renders as:
- 1st person: "I am obedient", "I obey without question"
- 3rd person: "she is obedient", "puppet obeys without question"

## Examples

### Template
```
{subject_subjective} [give|gives] {subject_reflexive} completely to {dominant_noun}
```

### Rendered (1st person, puppet, Master)
```
I give myself completely to Master
```

### Rendered (3rd pronoun F, puppet, Master)
```
she gives herself completely to Master
```

### Rendered (3rd named, puppet, Master)
```
puppet gives puppet completely to Master
```

---

### Template
```
{dominant_noun} controls {subject_possessive} mind with {dominant_possessive} words
```

### Rendered (1st person subject, 3rd M dominant, Master)
```
Master controls my mind with his words
```

### Rendered (1st person subject, 3rd F dominant, Mistress)
```
Mistress controls my mind with her words
```

## Database Schema

When storing mantras, track which variables are used for query optimization:

```sql
CREATE TABLE mantras (
  id INTEGER PRIMARY KEY,
  template TEXT NOT NULL,
  themes TEXT NOT NULL,           -- JSON array: ["obedience", "submission"]
  difficulty TEXT NOT NULL,       -- BASIC, LIGHT, MODERATE, DEEP, EXTREME
  has_subject BOOLEAN DEFAULT 0,  -- uses any {subject_*}
  has_dominant BOOLEAN DEFAULT 0, -- uses any {dominant_*}
  subject_gender_required BOOLEAN DEFAULT 0,  -- uses pronouns, not just noun
  dominant_gender_required BOOLEAN DEFAULT 0
);
```

Query example:
```sql
-- Find mantras that work without gendered pronouns
SELECT template FROM mantras
WHERE themes LIKE '%obedience%'
AND subject_gender_required = 0
AND dominant_gender_required = 0;
```

## Compatibility with Conditioner

Conditioner uses simplified variables:
- `{subject}` → equivalent to `{subject_noun}`
- `{controller}` → equivalent to `{dominant_noun}`

To export for conditioner, replace full variables with noun-only versions (loses POV flexibility).
