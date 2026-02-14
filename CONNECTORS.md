# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user connects in that category. For example, `~~docx skill` refers to a DOCX editing skill that provides the Document library for OOXML manipulation.

Plugins are **tool-agnostic** — they describe workflows in terms of categories rather than specific products. The specific tool or MCP server in each category can vary by installation.

## Connectors for this plugin

| Category | Placeholder | Included/Recommended | Other options |
|----------|-------------|---------------------|---------------|
| DOCX editing | `~~docx skill` | Claude Code built-in docx skill | Any OOXML manipulation library |

## Required Tools

### DOCX Skill (for `/apply-redlines` and `/review-drafts`)

The `/apply-redlines` and `/review-drafts` commands (and their backing scripts `apply_redlines.py` and `review_draft.py`) depend on a DOCX editing capability that provides:

- **Document library**: Python class for OOXML manipulation with tracked changes support
- **Unpack/Pack scripts**: Extract and reassemble .docx ZIP archives
- **Validation**: Schema validation and redlining validation

The built-in Claude Code `docx` skill provides all of these. If using an alternative, ensure it supports:
- Tracked change insertion (`w:ins`, `w:del` elements)
- Comment creation and wiring
- RSID management
- Document repacking with validation

## Optional Integrations

This plugin works entirely with local files and does not require external service connections. However, users may optionally connect:

| Integration | Purpose |
|------------|---------|
| Document management system | Import agreements directly |
| Version control | Track deal review history |
