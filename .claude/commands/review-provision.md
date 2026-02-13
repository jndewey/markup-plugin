Review a single provision folder: $ARGUMENTS

Steps:
1. Read full_agreement.txt for complete agreement context
2. Read review_config.json for review posture
3. Read deal_summary.json if available (for cross-reference context)
4. Navigate to the specified provision folder
5. Read original.txt
6. Read manifest.json for cross-references and metadata
7. If cross-references exist, read those sections from full_agreement.txt or
   their respective provision folders for additional context
8. Analyze and revise the provision per the CLAUDE.md methodology
9. Write: analysis.md, revised.txt, changes_summary.md
10. Update manifest.json with status "reviewed" and timestamp

Provide the provision folder path as an argument, e.g.:
  /review-provision provisions/03_representations_and_warranties
