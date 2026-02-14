---
description: List all installed topical skills and summarize their coverage
argument-hint: ""
---

# List Skills

List all installed topical skills and summarize their coverage.

## Workflow

1. Check if skills/manifest.json exists
2. If no skills are installed, inform the user and suggest how to add them:
   ```bash
   python scripts/prepare_deal.py ... --skill path/to/skill.md
   ```
3. If skills are installed, for each skill:
   a. Read the skill file
   b. Display: name, description, number of sections/topics covered
   c. List the specific provision topics the skill covers
4. Summarize which provision folders in /provisions/ have matching skill coverage
   and which do not

This helps the user understand what reference materials the agent has access to
before starting or resuming a review.
