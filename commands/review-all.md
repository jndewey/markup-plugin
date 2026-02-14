---
description: Review all provisions in the deal workspace using parallel provision review
argument-hint: ""
---

# Review All Provisions

Review all provisions in this deal workspace following the methodology in the **deal-review-methodology** skill. This command uses parallel provision review to significantly reduce total review time.

## Phase 1 — Sequential Setup & Definitions

1. Read `full_agreement.txt` to build complete context
2. Read `review_config.json` for the review posture and preferences
3. If `term_sheet.txt` exists, read it thoroughly — every provision review must check
   conformity with the term sheet
4. If `skills/manifest.json` exists, read it and then read ALL skill files listed.
   These contain market benchmarks and provision-specific guidance that must be
   referenced during each provision's review where applicable.
5. If `deal_summary.json` does not exist, generate it per the deal-review-methodology skill specification
6. Identify the definitions provision folder (the folder whose manifest.json has a title
   matching "Definitions" or whose folder name contains "definitions")
7. If the definitions provision has status "pending", review it now — sequentially in
   this session — following the full methodology. Definitions must be
   completed before other provisions can be reviewed, since every other provision
   depends on defined terms.
8. Report: "Phase 1 complete. Definitions reviewed. Beginning parallel provision reviews."

## Phase 2 — Parallel Provision Reviews

1. Scan all provision folders under `provisions/`. For each folder, read its
   `manifest.json` to check status. Collect all folders where status is "pending".
   Skip folders named `01_full_agreement` (this is the raw source, not a reviewable
   provision). Skip the definitions folder (already handled in Phase 1).

2. Determine the path to the definitions provision's `revised.txt` (needed by each
   agent for defined-term context). If the definitions provision was already reviewed
   before this run, its `revised.txt` already exists. Store this path.

3. For EACH pending provision, launch a background Task agent using the Task tool with
   these parameters:
   - `subagent_type`: `"general-purpose"`
   - `run_in_background`: `true`
   - `description`: `"Review [provision_title]"`
   - `prompt`: Use the template below, filling in the deal directory path, provision
     folder name, and definitions revised.txt path.

   **Agent Prompt Template:**
   ```
   You are a senior commercial real estate finance attorney reviewing a single provision
   of a loan agreement. Follow the deal-review-methodology skill exactly.

   DEAL DIRECTORY: {deal_dir}
   PROVISION FOLDER: provisions/{prov_folder}

   INSTRUCTIONS:
   1. Read {deal_dir}/CLAUDE.md for the complete review methodology — pay special
      attention to the "revised.txt Quality Rules" section
   2. Read {deal_dir}/full_agreement.txt for full agreement context
   3. Read {deal_dir}/review_config.json for the review posture and deal details
      (deal_type, property_type, jurisdiction)
   4. If {deal_dir}/term_sheet.txt exists, read it for term sheet conformity checking
   5. If {deal_dir}/skills/manifest.json exists, read it and ALL listed skill files.
      Skills are REFERENCE MATERIALS only — never cite them in revised.txt
   6. Read {deal_dir}/provisions/{definitions_folder}/revised.txt for defined term context
   7. Read {deal_dir}/provisions/{prov_folder}/original.txt and manifest.json
   8. Analyze and revise this provision per the methodology
   9. Write the following files to {deal_dir}/provisions/{prov_folder}/:
      - analysis.md (include Skill Reference section if any skill applies)
      - revised.txt (full revised text with [REVISED: explanation] inline markers)
      - changes_summary.md
      - term_sheet_compliance.md (ONLY if term_sheet.txt exists)
   10. Update manifest.json: set status to "reviewed", add reviewed_at timestamp (ISO 8601),
       add cross_ref_flags array (list of cross-reference concerns), add open_issues array
       (business-point questions for client)
   11. Do NOT modify any files outside this provision's folder

   CRITICAL QUALITY RULES FOR revised.txt:
   - revised.txt must contain ONLY enforceable contract language plus brief [REVISED: ...]
     markers. No [NOTE:], [RECOMMENDATION:], [COMMENT:], or advisory text.
   - NEVER reference skill files, AI tools, benchmarks, or review methodology in the
     revised text. It must read as if drafted by a human attorney.
   - Every revision listed in changes_summary.md as "Revision Made" MUST be actually
     drafted in revised.txt — do not describe changes without implementing them.
   - Preserve ALL original provisions from original.txt unless deliberately removing
     them (with explanation in changes_summary.md).
   - Preserve the original section numbering exactly — do not renumber.
   - No placeholder cross-references ("Section [X]", "Section 1.XX"). Use actual
     section numbers from the agreement or draft language inline.
   - Scale skill benchmark thresholds proportionally to the actual deal size.
   - Only add provisions relevant to the actual property_type in review_config.json.
   - Use consistent discretion standards — never "sole but reasonable discretion".

   DRAFTING DEPTH — GO BEYOND REASONABLENESS QUALIFIERS:
   - When a skill benchmark identifies a substantive mechanical provision as market
     standard, DRAFT the fully operative contract language in revised.txt. Do not
     stop at adding "not to be unreasonably withheld" — build out the mechanism that
     gives the standard practical effect (e.g., budget reallocation rights with
     contingency floors, retainage step-downs with lien-waiver triggers, deemed-approval
     timelines, fee caps at commercially reasonable rates).
   - The revised.txt must contain language a partner could send to opposing counsel.
     If the skill describes a market mechanism and the agreement lacks it, draft it.
   ```

4. Collect all agent task IDs into a list.

5. Monitor completion by polling each agent with TaskOutput (use `block: false` to
   avoid blocking). Report progress as each provision completes:
   - "[N/total] Completed: PROVISION_TITLE"
   - If an agent returns an error, log it and continue monitoring others:
     "ERROR reviewing PROVISION_TITLE: [error summary]. Will retry in Phase 3."

6. Wait until all agents have completed (or failed) before proceeding.

## Phase 3 — Sequential Reconciliation

1. Re-scan all provision folders. For each, read `manifest.json` and check status.
   Report a summary:
   - "Reviewed: [list]"
   - "Failed/Still Pending: [list]" (if any)

2. For any provisions that failed in Phase 2, attempt to review them sequentially in
   this session as a fallback (using the same methodology).

3. Run the reconciliation check across all reviewed provisions:
   a. Read all `revised.txt` files
   b. Check cross-reference consistency (do referenced sections exist? are section
      numbers correct?)
   c. Verify defined terms are used consistently across all revised provisions
   d. Check that cure periods, notice periods, and thresholds are internally consistent
   e. Flag any conflicts between revised provisions

4. Write `reconciliation_report.md` at the deal root

5. If `term_sheet.txt` exists, read all `term_sheet_compliance.md` files from each
   provision and write a consolidated `term_sheet_compliance_report.md` at the deal
   root, organized by severity (Critical > Moderate > Minor)

6. If the `unpacked/` directory exists (indicating a Word document source), inform
   the user: "Word document source detected. Run /apply-redlines to generate a
   tracked-changes redline."

## Resume Capability

Skip provisions that already have status "reviewed" in their manifest.json. This
enables resuming an interrupted review — only pending provisions are processed.
If ALL provisions are already reviewed, skip directly to Phase 3 (reconciliation).

## Progress Reporting

Report progress throughout:
- After Phase 1: "Setup complete. Definitions reviewed."
- During Phase 2: "[N/total] provisions completed" as each agent finishes
- After Phase 2: "All provision reviews complete. Beginning reconciliation."
- After Phase 3: "Review complete. [N] provisions reviewed. See reconciliation_report.md."
