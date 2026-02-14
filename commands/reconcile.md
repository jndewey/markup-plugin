---
description: Run a reconciliation check across all reviewed provisions
argument-hint: ""
---

# Reconcile

Run a reconciliation check across all reviewed provisions.

## Workflow

1. Read full_agreement.txt for the original agreement context
2. Read all revised.txt files from every provision folder with status "reviewed"
3. Check for:
   a. Cross-reference consistency — do section references still point correctly?
   b. Defined term consistency — are revised defined terms used consistently
      throughout all revised provisions?
   c. Conflicting revisions — does a revision in one provision contradict a
      revision in another?
   d. Orphaned references — do any provisions reference sections or terms that
      were materially changed in revision?
   e. Cure period alignment — are cure/notice periods consistent across
      defaults, remedies, and covenant sections?
4. Write reconciliation_report.md to the deal root directory with:
   - Summary of findings
   - Specific conflicts identified (with section references)
   - Recommended resolution for each conflict
   - List of cross-reference updates needed
