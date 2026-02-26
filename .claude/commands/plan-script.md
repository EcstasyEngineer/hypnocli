Create a plan.json for the hypnosis script generator.

If the user provided a file path or description as an argument: $ARGUMENTS — read it first.

Then follow the plan authoring workflow from CLAUDE.md:

1. Read the source material (whatever the user provided)
2. Read `script/hypnosis_taxonomy.md` — focus on technique detail blocks for relevant categories
3. Ask the user structured questions for any missing parameters (use AskUserQuestion):
   - Duration (5/10/15/25/40 min)
   - Style (Permissive/Authoritarian/Compulsion/Institutional/Character)
   - Variant (standard/loop/series)
   - Tone (ask for 2-3 adjectives + texture notes)
   - Optional modules (M1 Mind Blanking, M2 Transfer, M3 Demonstration, M4 Loop close)
   - Mantras and triggers if relevant
4. Map the concept's beats to phases (P1-P5, M1-M4) with taxonomy techniques
5. Write rich plan notes for each phase (opening line, imagery, compounding arcs, register shifts)
6. Save as plan.json

Reference `script/plan_clinical_drone.json` as the gold-standard example of plan note quality.

After writing the plan, show the user the phase sequence and ask if they want to generate the script immediately.
