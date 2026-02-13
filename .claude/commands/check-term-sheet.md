Run a term sheet compliance check across the entire agreement.

Prerequisites: `term_sheet.txt` must exist in the workspace.

Steps:
1. Read `term_sheet.txt` thoroughly and extract every business term, economic point,
   and structural requirement
2. Read `full_agreement.txt` for the complete agreement context
3. Read `review_config.json` for the review posture
4. For each provision folder:
   a. Compare the provision text against corresponding term sheet items
   b. Write `term_sheet_compliance.md` in the provision folder
   c. Categorize each item as: Conforming, Deviating, or Not Addressed
   d. For deviations, rate severity (Critical / Moderate / Minor)
5. Generate a consolidated `term_sheet_compliance_report.md` at the deal root:
   - Executive summary of conformity
   - All Critical deviations listed first
   - All Moderate deviations
   - Minor deviations
   - Term sheet items with no corresponding agreement provision
   - Agreement provisions with no corresponding term sheet item (flag if economic)

Pay special attention to:
- Loan amount, interest rate, maturity, and extension options
- Fee structures and prepayment premiums
- Financial covenant thresholds (DSCR, LTV, debt yield)
- Reserve requirements and cash management triggers
- Recourse structure and carveout triggers
- Transfer restrictions and permitted transfers
- Any special conditions or side letter terms
