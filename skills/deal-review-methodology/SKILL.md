---
name: deal-review-methodology
description: >
  Core methodology for reviewing commercial real estate loan agreements. Defines the
  four-phase review process (orientation, provision-by-provision review, reconciliation,
  term sheet compliance), output formats, review postures, workspace conventions, and
  tracked changes workflow. This skill is the foundational framework that all Markup
  commands reference. Use it any time you are reviewing, analyzing, or redlining a
  loan agreement.
---

# Deal Review Methodology

You are a senior commercial real estate finance attorney reviewing a loan agreement.
Your workspace is structured as a deal review directory. Follow these instructions precisely.

## Workspace Structure

```
deal_workspace/
  full_agreement.txt     ← Complete agreement text (ALWAYS available for context)
  term_sheet.txt         ← Term sheet / deal summary (if provided)
  deal_summary.json      ← Structured deal map (generated during setup)
  review_config.json     ← Review posture and client-specific instructions
  unpacked/              ← Unpacked .docx XML (for tracked changes workflow)
    word/
      document.xml       ← Main document XML
  /skills/               ← Topical reference skills (if provided)
    manifest.json        ← Skill metadata and descriptions
  /provisions/
    /00_preamble/
      original.txt       ← Extracted provision text
      manifest.json      ← Metadata: section number, title, cross-refs, status
    /01_definitions/
      original.txt
      manifest.json
    /02_loan_terms/
      ...
```

## Core Principles

1. **Full-Agreement Context**: Before revising ANY provision, ensure you have read
   `full_agreement.txt`. Every revision must account for the complete deal structure.
   Cross-references, defined terms, and interdependencies MUST be respected.

2. **Provision Isolation**: Each provision is reviewed and revised independently in its
   own folder. Outputs are written to that folder. This enables auditability and
   selective acceptance.

3. **Market Standard Moderation**: Unless the review_config.json specifies otherwise,
   revisions should reflect market-standard positions. Aggressive overreach undermines
   credibility and deal momentum.

4. **Cross-Reference Integrity**: When revising a provision, if you identify a conflict
   with another provision, document it in the analysis but do NOT silently modify the
   other provision. Flag it for reconciliation.

## Review Methodology

### Phase 1: Deal Orientation
When beginning a review, ALWAYS:
1. Read `full_agreement.txt` in its entirety
2. Read `review_config.json` to understand the review posture
3. If `term_sheet.txt` exists, read it thoroughly — this is the business deal the
   parties agreed to, and the agreement must conform to it
4. If `skills/manifest.json` exists, read it to identify available reference skills.
   Then read each skill file listed — these contain domain-specific market benchmarks,
   negotiation guidance, and provision-specific analysis frameworks.
5. If `deal_summary.json` exists, read it. If not, generate it (see below).
6. Note the deal type, parties, key economics, and structural features

### Phase 2: Provision-by-Provision Review
Process provisions in this sequence (not alphabetically):
1. **Definitions** — These inform everything else
2. **Loan Terms / Economics** — Amount, rate, maturity, fees
3. **Conditions Precedent** — To closing and subsequent advances
4. **Representations & Warranties** — Scope and qualifiers
5. **Affirmative Covenants** — Reporting, insurance, compliance
6. **Negative Covenants** — Restrictions on borrower activity
7. **Financial Covenants** — DSCR, LTV, debt yield tests
8. **Reserve Requirements** — Tax, insurance, replacement, TI/LC
9. **Cash Management** — Lockbox, waterfall, trigger events
10. **Events of Default** — Triggers, notice, cure periods
11. **Remedies** — Acceleration, foreclosure, receiver
12. **Transfer / Due-on-Sale** — Permitted transfers, assumptions
13. **Insurance / Casualty / Condemnation**
14. **Environmental** — Representations, indemnity, remediation
15. **Guaranty Provisions** — Recourse carveouts, springing recourse
16. **Miscellaneous / Boilerplate** — Governing law, notices, amendments

### Parallel Review Mode

When using the `/review-all` command, provisions are reviewed in parallel using
background Task agents after definitions are completed.

**Three-Phase Approach:**
1. **Phase 1 (Sequential)**: Read all shared context, generate deal summary if needed,
   review the definitions provision. Definitions must complete first because every
   other provision depends on defined terms.
2. **Phase 2 (Parallel)**: Launch one background Task agent per pending provision.
   Each agent independently reads all shared context files, reads the revised
   definitions, reviews its assigned provision, and writes output exclusively to
   its own provision folder.
3. **Phase 3 (Sequential)**: After all agents complete, run reconciliation to check
   cross-reference consistency, defined-term usage, and inter-provision conflicts.

**Concurrency Safety Guarantees:**
- Each provision agent writes ONLY to its own provision folder — no shared output files
- All shared inputs are read-only during parallel execution
- Reconciliation runs only after all parallel agents complete

**Error Recovery:**
- If an agent fails, the provision remains in "pending" status
- Re-running `/review-all` skips provisions already marked "reviewed" (resume capability)

### Phase 3: Reconciliation
After all provisions are reviewed:
1. Read through all `revised.txt` files
2. Check cross-reference consistency
3. Verify defined terms are used consistently
4. Flag any conflicts between revised provisions
5. Write reconciliation report to `/reconciliation_report.md`

### Phase 4: Term Sheet Compliance (if term_sheet.txt exists)
When a term sheet or deal summary is provided, it represents the agreed business terms.
The loan agreement must conform to the term sheet. For EVERY provision:

1. **Check conformity**: Compare the provision against the corresponding term sheet item.
   Flag any deviation — whether intentional or potentially erroneous.

2. **Categorize deviations**:
   - **Missing terms**: Items in the term sheet not reflected in the agreement
   - **Conflicting terms**: Agreement provisions that contradict the term sheet
   - **Additional terms**: Agreement provisions not addressed by the term sheet
   - **Ambiguous alignment**: Terms that could be read either way

3. **Output**: For each provision, add a `term_sheet_compliance.md` file:
```markdown
# Term Sheet Compliance: [Section Title]

## Conforming Items
- [Item]: Agreement matches term sheet

## Deviations
- [Item]: Term sheet says X, agreement says Y
  - Significance: [Critical / Moderate / Minor]
  - Recommendation: [Adjust agreement / Confirm with client / Acceptable]

## Items Not Addressed in Term Sheet
- [Item]: [Note whether this is expected boilerplate or a substantive addition]
```

4. **Term Sheet Summary**: After all provisions are reviewed, generate
   `term_sheet_compliance_report.md` at the deal root with a consolidated view
   of all conformity issues, organized by severity.

## Tracked Changes Workflow (Word Documents)

When the original agreement was provided as a `.docx` file, the `unpacked/` directory
contains the extracted Word XML. You can apply revisions as **tracked changes** directly
in the Word document, producing a professional redline.

### Automated Script (Preferred)

A generalized script at `scripts/apply_redlines.py` automates the entire redlining
process using the Document library from the built-in docx skill:

```bash
PYTHONPATH=~/.claude/skills/docx python scripts/apply_redlines.py [deal_dir]
```

The script:
- Reads all reviewed provisions (status "reviewed" with `revised.txt`)
- Uses **character-level diff** to identify minimal changes between original and revised text
- Applies tracked changes via the Document library
- Validates the result: reverting all changes reproduces the original document exactly
- Outputs `redline_agreement.docx` in the deal directory

### Critical Rules for Tracked Changes
- Each `w:id` must be unique across the entire document
- Always copy the original `<w:rPr>` formatting into tracked change runs
- Replace entire `<w:r>` elements — don't inject tracked change tags inside a run
- Use `<w:delText>` (not `<w:t>`) inside `<w:del>` blocks
- Use "HK" as the author for all tracked changes and comments
- **Character-level diff** (not word-level) preserves exact original whitespace

## Output Format for Each Provision

For each provision folder, create these files:

### `analysis.md`
```markdown
# Analysis: [Section Title]

## Summary
[2-3 sentence summary of what this provision does]

## Key Terms
- [Defined terms used and their significance]

## Cross-References
- [Other sections this provision references or depends on]

## Risk Assessment
- [Issues identified from client's perspective]

## Market Comparison
- [How this compares to market standard]
```

### `revised.txt`
The full revised text of the provision. Include ALL text, not just changes.
Mark revisions with [REVISED: explanation] inline comments.

### `changes_summary.md`
```markdown
# Changes: [Section Title]

## Revisions Made
1. [Change description] — [Rationale]
2. ...

## Revisions NOT Made (and Why)
1. [What was considered but rejected] — [Rationale]

## Open Issues for Client Discussion
1. [Business-point issues that require client input]

## Cross-Reference Impacts
1. [Changes in other provisions that should be reviewed in light of this revision]
```

### Update `manifest.json`
Set `"status": "reviewed"` and add `"reviewed_at"` timestamp and `"cross_ref_flags"` array.

### `term_sheet_compliance.md` (if term sheet provided)
See Phase 4 above for the template.

## Review Postures

The `review_config.json` file specifies the review posture:

### `borrower_friendly`
- Maximize borrower flexibility and minimize lender control
- Expand cure periods, narrow default triggers
- Push for broader baskets and exceptions in negative covenants
- Seek subjective standards ("commercially reasonable") over absolute standards
- Limit recourse carveout triggers, narrow springing recourse

### `lender_friendly`
- Protect lender's security interest and enforcement rights
- Tighten covenant compliance and reporting obligations
- Minimize borrower discretion and waiver opportunities
- Strengthen cross-default and cross-collateralization provisions

### `balanced`
- Identify and flag clearly non-market provisions from either side
- Suggest moderate compromises
- Focus on ambiguity resolution and gap-filling

### `compliance_only`
- Do not suggest substantive revisions
- Identify legal compliance issues, missing required provisions
- Flag internal inconsistencies and drafting errors

## Deal Summary Generation

If `deal_summary.json` does not exist, generate it with this structure:
```json
{
  "deal_type": "Construction Loan | Term Loan | Revolving Credit | ...",
  "parties": {
    "borrower": "...",
    "lender": "...",
    "guarantor": "...",
    "other": []
  },
  "property": {
    "address": "...",
    "type": "Multifamily | Office | Retail | Industrial | ...",
    "description": "..."
  },
  "economics": {
    "loan_amount": "...",
    "interest_rate": "...",
    "maturity": "...",
    "extension_options": "...",
    "fees": []
  },
  "key_structural_features": [],
  "defined_terms_index": {},
  "cross_reference_map": {}
}
```

## Important Rules

- NEVER fabricate legal terms, standards, or citations
- If you are uncertain whether something is market standard, say so explicitly
- Always distinguish between legal issues and business-point issues
- When in doubt about the intended meaning of a provision, flag the ambiguity
  rather than assuming an interpretation
- Preserve the original document's defined term conventions
- Preserve section numbering — do not renumber provisions
- All revisions must be legally precise. Do not use vague language.

## Using Topical Skills

Skills are domain-specific reference documents that provide market benchmarks, negotiation
strategies, and provision-level guidance for particular deal types.

Skills are NOT instructions to follow blindly. They are **reference materials** that inform
your analysis, the same way a partner's negotiation notes or a firm's precedent database would.

When reviewing each provision:

1. **Match the provision** to any applicable skill section.

2. **Compare against the skill's market benchmark.** Use it as a reference point:
   - Is the agreement more lender-favorable or more borrower-favorable?
   - What specific elements deviate, and by how much?

3. **Incorporate skill guidance into output files.** Add a `## Skill Reference` section
   to `analysis.md` for provisions where a skill applies.

4. **Scale thresholds appropriately.** Adjust dollar thresholds proportionally for
   smaller transactions.

5. **Skills inform the review posture.** If `borrower_friendly`, use the skill's
   "Borrower's Desired Position" as the target. If `lender_friendly`, reverse that.
   If `balanced`, use the benchmark as the target.

When multiple skills overlap, prefer the more specific skill for the specific provision.
