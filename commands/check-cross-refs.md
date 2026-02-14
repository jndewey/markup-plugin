---
description: Analyze cross-references for a specific provision
argument-hint: "<provision folder path>"
---

# Check Cross-References

Analyze cross-references for: $ARGUMENTS

## Workflow

1. Read the specified provision's original.txt (or revised.txt if available)
2. Identify every cross-reference (Section X.XX, Article Y, Exhibit Z, etc.)
3. For each reference, locate the referenced content in full_agreement.txt
4. Assess whether the reference is:
   - Correct and consistent
   - Potentially broken (referenced section doesn't exist or was renumbered)
   - Circular (A references B which references A)
   - Dependency-creating (this provision's meaning depends on the referenced section)
5. Output a cross-reference map showing all dependencies

## Usage

```
/check-cross-refs provisions/06_negative_covenants
```
