# Markup

An agentic legal agreement review system built on top of Claude Code. Designed for commercial real estate finance attorneys reviewing complex loan agreements.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Pre-Process   │───▶│ Claude Code   │───▶│ Post-Process  │  │
│  │ (Scripted)    │    │ (Agentic)     │    │ (Scripted)    │  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
│                                                              │
│  prepare_deal.py      Agentic loop with    assemble_deal.py │
│  • Split agreement    full agreement       • Reassemble     │
│  • Create folders     context:             • Generate memo   │
│  • Extract metadata   • Analyze provisions • Changes tracker │
│  • Load skills        • Follow cross-refs  • Reconciliation  │
│  • Set review config  • Apply skills       • Word redline    │
│                       • Check term sheet                     │
│                       • Revise per posture                   │
│                       • Flag conflicts                       │
└─────────────────────────────────────────────────────────────┘
```

## Setup

```bash
# Clone or create the repo
git clone <your-repo-url> markup
cd markup

# Run setup (installs python-docx, creates deals/ directory)
chmod +x setup.sh new-deal.sh
./setup.sh
```

**Requirements:** Python 3.10+, [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## Quick Start

### 1. Create a deal workspace

```bash
# Simple — auto-detect article boundaries
./new-deal.sh my-deal /path/to/agreement.docx --posture borrower_friendly

# Full options — term sheet, skills, notes
./new-deal.sh centtral-aventura /path/to/loan_agreement.docx \
    --posture borrower_friendly \
    --term-sheet /path/to/term_sheet.docx \
    --skill skills/construction-loan-negotiation.md \
    --notes "Focus on cure periods and cash management. Client wants 30-day notice minimum."

# Or use prepare_deal.py directly
python scripts/prepare_deal.py agreement.docx \
    --posture borrower_friendly \
    --term-sheet term_sheet.docx \
    --skill skills/construction-loan-negotiation.md \
    --skill skills/florida-cre-provisions.md \
    --output-dir deals/my-deal
```

### 2. Launch Claude Code in the workspace

```bash
cd deals/my-deal
claude
```

### 3. Run the review

```
> /review-all              # Full provision-by-provision review
> /status                  # Check progress
> /list-skills             # See what reference skills are loaded
> /review-provision provisions/05_article_v    # Review a single provision
> /check-term-sheet        # Run term sheet compliance check
> /check-cross-refs provisions/08_article_viii # Analyze cross-references
> /reconcile               # Check consistency across all revisions
> /apply-redlines          # Apply tracked changes to the Word document
> /generate-deliverables   # Assemble final client deliverables
```

### 4. Assemble deliverables (alternative to slash command)

```bash
python scripts/assemble_deal.py deals/my-deal/
python scripts/assemble_deal.py deals/my-deal/ --format docx
```

### 5. Check status without Claude Code

```bash
python scripts/prepare_deal.py --status deals/my-deal/
```

## Repository Structure

```
markup/
├── CLAUDE.md                  # Master agent instructions (copied into each workspace)
├── README.md
├── setup.sh                   # One-time environment setup
├── new-deal.sh                # Convenience script to create deal workspaces
├── requirements.txt
├── .gitignore
│
├── scripts/
│   ├── prepare_deal.py        # Pre-processing: split agreement, build workspace
│   └── assemble_deal.py       # Post-processing: reassemble deliverables
│
├── skills/                    # Topical reference skills (tracked in repo)
│   └── construction-loan-negotiation.md
│
├── .claude/
│   └── commands/              # Slash commands (copied into each workspace)
│       ├── review-all.md
│       ├── review-provision.md
│       ├── reconcile.md
│       ├── status.md
│       ├── list-skills.md
│       ├── check-cross-refs.md
│       ├── check-term-sheet.md
│       ├── apply-redlines.md
│       └── generate-deliverables.md
│
├── examples/                  # Sample files for testing
│   ├── sample_agreement.txt
│   └── sample_term_sheet.txt
│
└── deals/                     # Deal workspaces (gitignored, created per-deal)
    └── centtral-aventura/
        ├── CLAUDE.md
        ├── full_agreement.txt
        ├── term_sheet.txt
        ├── review_config.json
        ├── deal_summary.json
        ├── original.docx
        ├── unpacked/
        ├── skills/
        │   ├── manifest.json
        │   └── *.md
        ├── .claude/commands/
        ├── provisions/
        │   ├── 00_preamble/
        │   │   ├── original.txt
        │   │   ├── manifest.json
        │   │   ├── analysis.md
        │   │   ├── revised.txt
        │   │   ├── changes_summary.md
        │   │   └── term_sheet_compliance.md
        │   ├── 01_article_i/
        │   └── ...
        ├── deliverables/
        │   ├── review_memo.md
        │   ├── revised_agreement.txt
        │   ├── redline_agreement.docx
        │   ├── changes_tracker.md
        │   └── term_sheet_compliance_report.md
        └── scripts/
```

## Review Postures

| Posture | Description |
|---------|-------------|
| `borrower_friendly` | Maximize borrower flexibility, expand cure periods, narrow defaults |
| `lender_friendly` | Protect lender security, tighten covenants, strengthen enforcement |
| `balanced` | Flag non-market provisions, suggest moderate compromises |
| `compliance_only` | No substantive revisions; flag compliance issues and drafting errors |

## Topical Skills

Skills are Markdown files containing domain-specific market benchmarks, negotiation guidance, and provision-level analysis frameworks. They live in the `skills/` directory and are tracked in the repo.

### Included Skills

- **`construction-loan-negotiation.md`** — 14 most commonly negotiated provisions in construction loan agreements with lender/borrower positions and market benchmarks from well-negotiated South Florida condo construction loans

### Skill Format

```markdown
---
name: my-skill-name
description: >
  Brief description of what this skill covers and when to use it.
---
# Skill Title
## 1. Provision Topic
### Lender's Desired Position
...
### Borrower's Desired Position
...
### Market Benchmark
...
```

### Using Skills

```bash
./new-deal.sh my-deal agreement.docx \
    --posture borrower_friendly \
    --skill skills/construction-loan-negotiation.md \
    --skill skills/florida-cre-provisions.md
```

During review, the agent matches each provision against applicable skill sections, compares the agreement to market benchmarks, and adds a "Skill Reference" section to each analysis.

## Term Sheet Compliance

When a term sheet is provided (`--term-sheet`), the agent checks every provision against the agreed business terms, categorizing each as conforming, deviating (with severity), or not addressed.

## Tracked Changes (Word Documents)

When the input is a `.docx`, `/apply-redlines` applies all revisions as tracked changes directly in the Word document with comments explaining each change. Opens in Word with Track Changes enabled.

## Resume Capability

Each provision tracks review status. If a session is interrupted, `/review-all` picks up where it left off.

## Caveats

- **Not a substitute for attorney review.** All AI output must be reviewed by qualified counsel.
- **Token limits.** Very large agreements (100+ pages) may approach context window limits.
- **Tracked changes require .docx input.**
- **Cross-reference accuracy.** Good but not perfect — always verify with `/reconcile`.
