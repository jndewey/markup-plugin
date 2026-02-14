Review a single provision folder: $ARGUMENTS

Steps:
1. Read `full_agreement.txt` for complete agreement context
2. Read `review_config.json` for review posture
3. Read `deal_summary.json` if available (for cross-reference context)
4. If `skills/manifest.json` exists, read it and all listed skill files. Identify
   which skill sections (if any) apply to this provision.
5. If a definitions provision has been reviewed (check for `revised.txt` in the
   definitions folder), read it for defined-term context
6. Navigate to the specified provision folder
7. Read `original.txt`
8. Read `manifest.json` for cross-references and metadata
9. If cross-references exist, read those sections from `full_agreement.txt` or
   their respective provision folders for additional context
10. Analyze and revise the provision per the CLAUDE.md methodology. If an applicable
    skill was identified in step 4, compare the provision against the skill's market
    benchmark and include a Skill Reference section in the analysis.
11. Write output files:
    - `analysis.md` (include Skill Reference section if applicable)
    - `revised.txt` (full revised text with `[REVISED: explanation]` inline markers)
    - `changes_summary.md`
12. If `term_sheet.txt` exists in the deal directory, write `term_sheet_compliance.md`
    comparing this provision against the relevant term sheet items
13. Update `manifest.json`:
    - Set `"status": "reviewed"`
    - Add `"reviewed_at"` with ISO 8601 timestamp
    - Add `"cross_ref_flags"` array listing any cross-reference concerns
    - Add `"open_issues"` array listing business-point questions for client discussion

Provide the provision folder path as an argument, e.g.:
  /review-provision provisions/03_representations_and_warranties
