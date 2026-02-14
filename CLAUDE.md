# Markup Plugin

This is a Claude Code plugin for reviewing, redlining, and negotiating commercial real estate loan agreements.

## Plugin Structure

- **`commands/`** — Slash commands that users invoke directly (e.g., `/review-all`, `/apply-redlines`)
- **`skills/`** — Domain knowledge and reference materials that inform the review process
- **`scripts/`** — Python scripts for pre-processing (deal setup) and post-processing (assembly, redlining)
- **`CONNECTORS.md`** — External tool dependencies

## Core Skill

The **deal-review-methodology** skill (`skills/deal-review-methodology/SKILL.md`) contains the complete review methodology: workspace structure, four-phase review process, output formats, review postures, and tracked changes workflow. All commands reference this skill.

## Topical Skills

Additional skills provide domain-specific market benchmarks:
- **construction-loan-negotiation** — 14 commonly negotiated CRE construction loan provisions
- **cre-loan-agreement-review** — Comprehensive CRE loan agreement review framework
- **environmental-indemnity** — Environmental indemnity negotiation guidance

## Commands

| Command | Description |
|---------|-------------|
| `/review-all` | Full parallel provision-by-provision review |
| `/review-provision` | Review a single provision |
| `/apply-redlines` | Apply tracked changes to Word document |
| `/reconcile` | Cross-reference consistency check |
| `/check-term-sheet` | Term sheet compliance analysis |
| `/check-cross-refs` | Cross-reference analysis for a provision |
| `/status` | Deal review progress |
| `/generate-deliverables` | Assemble final client deliverables |
| `/review-drafts` | Conform draft loan documents to a term sheet or commitment letter |
| `/list-skills` | Show installed reference skills |
