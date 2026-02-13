Review all provisions in this deal workspace following the methodology in CLAUDE.md.

Steps:
1. Read full_agreement.txt to build complete context
2. Read review_config.json for the review posture and preferences
3. If term_sheet.txt exists, read it thoroughly — every provision review must check
   conformity with the term sheet
4. If skills/manifest.json exists, read it and then read ALL skill files listed.
   These contain market benchmarks and provision-specific guidance that must be
   referenced during each provision's review where applicable.
5. If deal_summary.json does not exist, generate it per the CLAUDE.md specification
6. Iterate through each provision folder in /provisions/ in the sequence specified
   in CLAUDE.md (definitions first, then economics, conditions, covenants, etc.)
7. For each provision with status "pending" in its manifest.json:
   a. Read original.txt
   b. Analyze the provision with full agreement context
   c. Check if any installed skill has a matching section — if so, compare against
      the skill's market benchmark and incorporate into analysis
   d. Write analysis.md (including Skill Reference section if applicable),
      revised.txt, and changes_summary.md
   e. If term_sheet.txt exists, write term_sheet_compliance.md
   f. Update manifest.json with status "reviewed" and timestamp
8. After all provisions are reviewed, run the reconciliation check
9. Write reconciliation_report.md
10. If term_sheet.txt exists, write term_sheet_compliance_report.md
11. If unpacked/ directory exists (Word document), ask if user wants to apply
    tracked changes now (suggest running /apply-redlines)

Skip provisions that already have status "reviewed" (resume capability).
Report progress after each provision is completed.
