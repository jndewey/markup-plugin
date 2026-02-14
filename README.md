# Markup

A Claude Code plugin for reviewing, redlining, and negotiating commercial real estate loan agreements. Designed for commercial real estate finance attorneys reviewing complex loan agreements.

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

## Installation

### As a Claude Code Plugin

```bash
# Install from the plugin directory
claude plugin install /path/to/markup-plugin

# Or install from a GitHub repository
claude plugin install github:jndewey/markup-plugin
```

### Manual Setup

```bash
# Clone the repository
git clone <your-repo-url> markup-plugin
cd markup-plugin

# Run setup (installs python-docx, creates deals/ directory)
chmod +x setup.sh new-deal.sh
./setup.sh
```

**Requirements:** Python 3.10+, [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## Plugin Structure

```
markup-plugin/
├── .claude-plugin/
│   └── plugin.json            # Plugin manifest
├── CLAUDE.md                  # Plugin overview for Claude
├── CONNECTORS.md              # External tool dependencies
├── README.md
│
├── commands/                  # Slash commands (user-invoked workflows)
│   ├── review-all.md          # Full parallel provision review
│   ├── review-provision.md    # Single provision review
│   ├── apply-redlines.md      # Word document tracked changes
│   ├── reconcile.md           # Cross-reference consistency check
│   ├── check-term-sheet.md    # Term sheet compliance check
│   ├── check-cross-refs.md    # Cross-reference analysis
│   ├── status.md              # Review progress display
│   ├── generate-deliverables.md # Final deliverables assembly
│   ├── review-drafts.md       # Conform drafts to term sheet / commitment letter
│   └── list-skills.md         # Installed skills summary
│
├── skills/                    # Domain knowledge (reference materials)
│   ├── deal-review-methodology/
│   │   └── SKILL.md           # Core review methodology (foundational)
│   ├── construction-loan-negotiation/
│   │   └── SKILL.md           # CRE construction loan benchmarks
│   ├── cre-loan-agreement-review/
│   │   └── SKILL.md           # General CRE loan review framework
│   └── environmental-indemnity/
│       └── SKILL.md           # Environmental indemnity guidance
│
├── scripts/
│   ├── prepare_deal.py        # Pre-processing: split agreement, build workspace
│   ├── assemble_deal.py       # Post-processing: reassemble deliverables
│   ├── apply_redlines.py      # Automated tracked changes script
│   └── review_draft.py        # Apply corrections to a single draft document
│
├── examples/                  # Sample files for testing
│   ├── sample_agreement.txt
│   └── sample_term_sheet.txt
│
├── setup.sh                   # One-time environment setup
├── new-deal.sh                # Convenience script to create deal workspaces
└── requirements.txt
```

## Quick Start

### 1. Create a deal workspace

```bash
# Simple — auto-detect article boundaries
./new-deal.sh my-deal /path/to/agreement.docx --posture borrower_friendly

# Full options — term sheet, skills, notes
./new-deal.sh acme-deal /path/to/loan_agreement.docx \
    --posture borrower_friendly \
    --term-sheet /path/to/term_sheet.docx \
    --skill skills/construction-loan-negotiation/SKILL.md \
    --notes "Focus on cure periods and cash management."

# Or use prepare_deal.py directly
python scripts/prepare_deal.py agreement.docx \
    --posture borrower_friendly \
    --term-sheet term_sheet.docx \
    --skill skills/construction-loan-negotiation/SKILL.md \
    --skill skills/environmental-indemnity/SKILL.md \
    --output-dir deals/my-deal
```

### 2. Launch Claude Code in the workspace

```bash
cd deals/my-deal
claude
```

### 3. Run the review

```
> /review-all              # Full provision-by-provision review (parallel)
> /status                  # Check progress
> /list-skills             # See what reference skills are loaded
> /review-provision provisions/05_article_v    # Review a single provision
> /check-term-sheet        # Run term sheet compliance check
> /check-cross-refs provisions/08_article_viii # Analyze cross-references
> /reconcile               # Check consistency across all revisions
> /apply-redlines          # Apply tracked changes to the Word document
> /generate-deliverables   # Assemble final client deliverables
> /review-drafts           # Conform draft documents to a term sheet or commitment letter
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

## Commands

| Command | Description |
|---------|-------------|
| `/review-all` | Full parallel provision-by-provision review with reconciliation |
| `/review-provision <path>` | Review a single provision folder |
| `/apply-redlines` | Apply tracked changes to the Word document |
| `/reconcile` | Cross-reference and consistency check |
| `/check-term-sheet` | Term sheet compliance analysis |
| `/check-cross-refs <path>` | Cross-reference analysis for a provision |
| `/status` | Show deal review progress |
| `/generate-deliverables` | Assemble final client deliverables |
| `/review-drafts` | Conform draft loan documents to a term sheet or commitment letter |
| `/list-skills` | List installed reference skills |

## Review Postures

| Posture | Description |
|---------|-------------|
| `borrower_friendly` | Maximize borrower flexibility, expand cure periods, narrow defaults |
| `lender_friendly` | Protect lender security, tighten covenants, strengthen enforcement |
| `balanced` | Flag non-market provisions, suggest moderate compromises |
| `compliance_only` | No substantive revisions; flag compliance issues and drafting errors |

## Skills

Skills are domain knowledge files that provide market benchmarks, negotiation strategies, and provision-level guidance. They live in `skills/` subdirectories as `SKILL.md` files.

### Included Skills

| Skill | Description |
|-------|-------------|
| **deal-review-methodology** | Core four-phase review methodology (foundational — all commands reference this) |
| **construction-loan-negotiation** | 14 most commonly negotiated CRE construction loan provisions |
| **cre-loan-agreement-review** | Comprehensive CRE loan agreement review framework |
| **environmental-indemnity** | Environmental indemnity negotiation guidance |

### Adding Skills

Skills can be loaded into a deal workspace at creation time:

```bash
./new-deal.sh my-deal agreement.docx \
    --skill skills/construction-loan-negotiation/SKILL.md \
    --skill skills/environmental-indemnity/SKILL.md
```

During review, the agent matches each provision against applicable skill sections, compares the agreement to market benchmarks, and adds a "Skill Reference" section to each analysis.

## Term Sheet Compliance

When a term sheet is provided (`--term-sheet`), the agent checks every provision against the agreed business terms, categorizing each as conforming, deviating (with severity), or not addressed.

## Draft Conformity Review

The `/review-drafts` command handles a different use case from the main review workflow: verifying that a package of draft loan documents correctly implements the terms of a controlling document (term sheet, commitment letter, or loan approval).

### Setup

Place all draft `.docx` files in a `drafts/` subfolder of the working directory:

```
working-directory/
├── drafts/
│   ├── loan_agreement.docx
│   ├── guaranty.docx
│   ├── environmental_indemnity.docx
│   └── ...
└── scripts/           # (if not using plugin install)
```

### Workflow

```
> /review-drafts
```

1. **Requirement extraction** — The command prompts for the controlling document (`.docx` or `.pdf`), then extracts and numbers every business term, economic point, and structural requirement into `drafts/requirements.md`.

2. **Parallel draft review** — Each draft document is reviewed in parallel by a dedicated agent that checks conformity against the extracted requirements. Deviations are corrected with tracked changes applied directly to the `.docx` files.

3. **Compliance matrix** — A markdown table is generated at `drafts/compliance_matrix.md` with three columns:
   - **Requirement** — each loan requirement from the controlling document
   - **Location** — where in the draft documents the requirement is addressed
   - **Operative Provision** — a snippet of the actual operative language

This acts as a quality control checklist, making it easy to verify that every term sheet requirement has been implemented and to spot any gaps.

### Output

```
drafts/
├── requirements.md                         # Extracted requirement list
├── compliance_matrix.md                    # Three-column QC table
├── loan_agreement.docx                     # With tracked changes (if corrections needed)
├── loan_agreement_conformity.md            # Per-document conformity report
├── loan_agreement_corrections.json         # Machine-readable corrections
├── guaranty.docx                           # With tracked changes (if corrections needed)
├── guaranty_conformity.md
├── guaranty_corrections.json
└── ...
```

## Tracked Changes (Word Documents)

When the input is a `.docx`, `/apply-redlines` applies all revisions as tracked changes directly in the Word document with comments explaining each change. Opens in Word with Track Changes enabled.

## Resume Capability

Each provision tracks review status. If a session is interrupted, `/review-all` picks up where it left off — only pending provisions are processed.

## Caveats

- **Not a substitute for attorney review.** All AI output must be reviewed by qualified counsel.
- **Token limits.** Very large agreements (100+ pages) may approach context window limits.
- **Tracked changes require .docx input.**
- **Cross-reference accuracy.** Good but not perfect — always verify with `/reconcile`.
