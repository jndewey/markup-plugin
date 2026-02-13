Apply all revisions as tracked changes to the original Word document.

Prerequisites: The `unpacked/` directory must exist (created by prepare_deal.py for .docx inputs).

Steps:
1. Read CLAUDE.md for tracked changes methodology
2. Read all provision folders that have status "reviewed" and have a `revised.txt`
3. Read `unpacked/word/document.xml` to understand the XML structure
4. For each reviewed provision, working through document.xml sequentially:
   a. Locate the provision text in the XML
   b. Compare original.txt to revised.txt to identify each specific change
   c. For each change, apply tracked change XML (w:del + w:ins) in document.xml
      - Use "Claude" as the author
      - Use unique w:id values starting at 1000
      - Preserve the original w:rPr formatting in tracked change runs
   d. Add a comment explaining each substantive change using:
      python /mnt/skills/public/docx/scripts/comment.py unpacked/ COMMENT_ID "explanation"
      Then add comment range markers in document.xml around the change
5. After all changes are applied, repack:
   python /mnt/skills/public/docx/scripts/office/pack.py unpacked/ redline_agreement.docx --original original.docx
6. Validate:
   python /mnt/skills/public/docx/scripts/office/validate.py redline_agreement.docx
7. If validation fails, fix issues and retry

CRITICAL RULES:
- Each w:id must be unique across the entire document
- Use w:delText (not w:t) inside w:del blocks
- Replace entire w:r elements; never inject tracked change tags inside a run
- Copy the original w:rPr into tracked change runs to preserve formatting
- Comment markers (commentRangeStart/End) are siblings of w:r, never inside w:r
- Use smart quote entities: &#x2019; for apostrophes, &#x201C;/&#x201D; for double quotes
