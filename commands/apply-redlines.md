---
description: Apply all revisions as tracked changes to the original Word document
argument-hint: ""
---

# Apply Redlines

Apply all revisions as tracked changes to the original Word document.

**Prerequisites:** The `unpacked/` directory must exist (created by prepare_deal.py for .docx inputs).

## Automated Script (Preferred)

Run the generalized redlining script:

```bash
PYTHONPATH=~/.claude/skills/docx python scripts/apply_redlines.py [deal_dir]
```

- `deal_dir` defaults to the current working directory
- The script uses the Document library from the ~~docx skill
- It applies character-level diffs to preserve exact original text
- Includes built-in redlining validation (reverting changes must reproduce original)
- Handles UTF-16 encoded XML files automatically
- Produces `redline_agreement.docx` in the deal directory

## Manual Approach (Fallback)

If the automated script is unavailable or modifications are needed:

1. Read the `ooxml.md` documentation from the ~~docx skill (full file, no line limits)
2. Unpack the document if not already unpacked:
   ```bash
   python ~/.claude/skills/docx/ooxml/scripts/unpack.py original.docx unpacked
   ```
3. Read all provision folders that have status "reviewed" and have a `revised.txt`
4. For each reviewed provision, working through document.xml sequentially:
   a. Locate the provision text in the XML using `get_node()`
   b. Compare original.txt to revised.txt to identify each specific change
   c. Apply tracked changes using the Document library's `replace_node()`,
      `suggest_deletion()`, and `insert_after()` methods
   d. Add comments using `doc.add_comment(start_node, end_node, text)`
5. Save and validate:
   ```python
   doc.save("redline_agreement.docx", validate=True)
   ```

## Critical Implementation Details

- **Character-level diff**: Use `difflib.SequenceMatcher` on raw text (not word-level)
  to preserve exact original whitespace and pass redlining validation
- **UTF-16 handling**: Some .docx files contain `customXml/item*.xml` with UTF-16
  encoding. Convert these to UTF-8 before initializing the Document library.
- **Insertion anchors**: When inserting new paragraphs, use ORIGINAL text (not revised)
  as the anchor, since the paragraph index maps original text to nodes
- **Tracked paragraph construction**: Build manually instead of using
  `suggest_paragraph()` to avoid namespace prefix issues with non-w: attributes
- Use "HK" as the author for all tracked changes and comments
- Each w:id must be unique (the Document library handles this automatically)
- Use `<w:delText>` (not `<w:t>`) inside `<w:del>` blocks
- Copy the original `<w:rPr>` into tracked change runs to preserve formatting
