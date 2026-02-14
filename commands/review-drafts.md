---
description: Conform draft loan documents to a term sheet, commitment letter, or loan approval
argument-hint: ""
---

# Review Drafts

Iterate through draft loan documents in the `drafts/` subfolder, compare each against
a controlling document (term sheet, commitment letter, or loan approval), apply tracked
changes where corrections are needed, and generate a compliance matrix.

**Prerequisites:** A `drafts/` subfolder must exist in the current working directory
containing one or more `.docx` draft loan documents.

## Phase 1 — Setup & Requirement Extraction

1. Verify that `drafts/` exists and contains at least one `.docx` file. List all
   `.docx` files found and report: "Found [N] draft document(s) in drafts/."
   If `drafts/` is missing or empty, stop and instruct the user to create the folder
   and place draft documents in it.

2. **Select controlling document.** Ask the user to provide the path to the controlling
   document (term sheet, commitment letter, or loan approval). Accepted formats: `.docx`
   or `.pdf`. If the user is unsure, scan the current directory and `drafts/` for files
   with names suggesting a term sheet or commitment letter and offer them as options.

3. **Extract the controlling document text.**
   - For `.docx`: use `python-docx` to extract all paragraph text
   - For `.pdf`: read the PDF using the Read tool (which supports PDF files)
   Store the extracted text in memory for analysis.

4. **Extract requirements.** Read the controlling document thoroughly and extract every:
   - Economic term (loan amount, interest rate, maturity, fees, reserves)
   - Structural requirement (recourse, guaranty, SPE covenants)
   - Condition precedent or subsequent
   - Financial covenant or threshold
   - Insurance, environmental, or compliance requirement
   - Special condition, side letter term, or closing requirement
   - Any other obligation, restriction, or deliverable

   Number each requirement sequentially. Write the structured list to
   `drafts/requirements.md` in this format:

   ```markdown
   # Controlling Document Requirements

   **Source:** [filename]
   **Extracted:** [timestamp]

   | # | Category | Requirement |
   |---|----------|-------------|
   | 1 | Economic | Loan Amount: $XX,XXX,XXX |
   | 2 | Economic | Interest Rate: SOFR + X.XX% |
   | ... | ... | ... |
   ```

5. Report: "Extracted [N] requirements from [filename]. Beginning draft review."

## Phase 2 — Parallel Draft Review

1. For EACH `.docx` file in `drafts/`, launch a background Task agent with:
   - `subagent_type`: `"general-purpose"`
   - `run_in_background`: `true`
   - `description`: `"Review [draft_filename]"`
   - `prompt`: Use the template below, filling in paths.

   **Agent Prompt Template:**
   ```
   You are a senior commercial real estate finance attorney reviewing a draft loan
   document to verify conformity with a controlling document (term sheet / commitment
   letter / loan approval).

   SCOPE: This is a CONFORMITY review only. These drafts were generated from approved
   form templates. Do NOT perform general legal quality review. Focus exclusively on
   whether the draft correctly implements the controlling document's requirements.

   DRAFT DOCUMENT: {draft_path}
   REQUIREMENTS FILE: {drafts_dir}/requirements.md

   INSTRUCTIONS:
   1. Read {drafts_dir}/requirements.md for the full list of controlling document
      requirements
   2. Extract text from the draft document at {draft_path}. Use python-docx:
      ```python
      from docx import Document
      doc = Document("{draft_path}")
      text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
      ```
   3. For each requirement in requirements.md, search the draft for the corresponding
      provision. Determine whether the draft:
      - **Conforms** — correctly implements the requirement
      - **Deviates** — addresses the requirement but with different terms
      - **Missing** — does not address the requirement (this may be acceptable if the
        requirement belongs to a different document type)
   4. For each deviation, determine the correction needed:
      - Identify the exact text that needs changing
      - Draft the corrected text that would bring it into conformity
   5. Write a corrections JSON file to {drafts_dir}/{stem}_corrections.json:
      ```json
      [
        {{
          "requirement_id": 1,
          "requirement_text": "Loan Amount: $XX,XXX,XXX",
          "status": "conforms|deviates|missing",
          "draft_section": "Section 2.1 — Loan Amount",
          "draft_text_snippet": "The relevant text from the draft...",
          "original_text": "exact text to find and replace (for deviations only)",
          "revised_text": "corrected text (for deviations only)",
          "note": "Brief explanation of the deviation or why missing is acceptable"
        }}
      ]
      ```
      For "conforms" entries, omit original_text and revised_text.
      For "missing" entries, add a note explaining whether the requirement belongs in
      this document type or not.
   6. Write a conformity report to {drafts_dir}/{stem}_conformity.md:
      ```markdown
      # Conformity Report: {filename}

      **Document:** {filename}
      **Requirements checked:** [N]
      **Conforms:** [N] | **Deviates:** [N] | **Missing:** [N]

      ## Deviations

      ### Requirement #[id]: [requirement text]
      - **Section:** [section reference]
      - **Issue:** [description]
      - **Correction:** [what was changed]

      ## Missing Requirements
      [list with notes on whether each is expected to be in this document]

      ## Conforming Requirements
      [list of requirement IDs and brief location reference]
      ```
   7. If ANY deviations were found, apply tracked changes to the draft .docx file.
      Run the tracked changes script:
      ```bash
      python scripts/review_draft.py "{draft_path}" "{drafts_dir}/{stem}_corrections.json"
      ```
      This will create a tracked-changes version at {draft_path} (overwriting the original).
   8. Do NOT modify any files outside the drafts/ directory.
   ```

2. Collect all agent task IDs into a list.

3. Monitor completion by polling each agent with TaskOutput (use `block: false` to
   avoid blocking). Report progress as each draft completes:
   - "[N/total] Completed: DRAFT_FILENAME"
   - If an agent returns an error, log it and continue monitoring others.

4. Wait until all agents have completed before proceeding.

## Phase 3 — Compliance Matrix

1. Read `drafts/requirements.md` to get the full requirement list.

2. Read all `*_corrections.json` files from `drafts/`.

3. Build the compliance matrix by cross-referencing each requirement against all
   draft documents. For each requirement, find the draft(s) where it is addressed.

4. Write `drafts/compliance_matrix.md`:

   ```markdown
   # Compliance Matrix

   **Controlling Document:** [filename]
   **Drafts Reviewed:** [N] documents
   **Date:** [timestamp]

   | Requirement | Location | Operative Provision |
   |-------------|----------|---------------------|
   | 1. Loan Amount: $XX,XXX,XXX | Loan Agreement, Section 2.1 | "Lender agrees to make a loan to Borrower in the principal amount of..." |
   | 2. Interest Rate: SOFR + X.XX% | Loan Agreement, Section 2.3 | "The Loan shall bear interest at a rate per annum equal to..." |
   | ... | ... | ... |
   ```

   Rules for the table:
   - **Requirement** column: requirement number and description from the controlling document
   - **Location** column: document name and section/article reference where the
     requirement is addressed. If the requirement is not found in any document,
     write "NOT FOUND" in bold.
   - **Operative Provision** column: a short snippet (1-2 sentences) of the actual
     operative language from the draft document. If not found, write "—".

5. Report summary:
   - Total requirements checked
   - Requirements addressed across all drafts
   - Requirements not found in any draft (**flag these prominently**)
   - Number of deviations corrected (with tracked changes applied)
   - List any drafts that had no deviations (conforming)

## Progress Reporting

Report progress throughout:
- After Phase 1: "Extracted [N] requirements. Beginning parallel draft review."
- During Phase 2: "[N/total] drafts completed" as each agent finishes
- After Phase 2: "All draft reviews complete. Generating compliance matrix."
- After Phase 3: "Review complete. See drafts/compliance_matrix.md."
