---
description: Assemble final deliverables from the completed review
argument-hint: ""
---

# Generate Deliverables

Assemble final deliverables from the completed review.

## Workflow

1. Run the assembly script:
   ```bash
   python scripts/assemble_deal.py . --format txt
   ```

2. Review the generated deliverables in ./deliverables/ and:
   a. Read the review_memo.md and check for completeness
   b. Read the changes_tracker.md and verify accuracy
   c. If the reconciliation_report.md has unresolved issues, flag them
   d. If term_sheet_compliance_report.md exists, include it in deliverables

3. If the unpacked/ directory exists and tracked changes have NOT been applied yet:
   a. Suggest running /apply-redlines to produce a Word redline
   b. Once applied, copy redline_agreement.docx to deliverables/

4. If redline_agreement.docx already exists, copy it to deliverables/

Report what was generated and highlight any items needing attorney attention.

## Final Deliverables Package

- **review_memo.md** — Executive summary and provision-by-provision analysis
- **revised_agreement.txt** — Clean revised text
- **redline_agreement.txt** — Text with revision markers
- **redline_agreement.docx** — Word document with tracked changes (if .docx input)
- **changes_tracker.md** — Consolidated change log
- **reconciliation_report.md** — Cross-reference and consistency check
- **term_sheet_compliance_report.md** — Term sheet conformity analysis (if term sheet provided)
