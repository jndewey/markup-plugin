#!/usr/bin/env python3
"""
Apply corrections as tracked changes to a single draft loan document.

Takes a .docx file and a JSON corrections file, applies character-level tracked
changes for each deviation, then repacks the document.

Usage:
    PYTHONPATH=~/.claude/skills/docx python scripts/review_draft.py draft.docx corrections.json

Prerequisites:
    - The docx skill must be installed at ~/.claude/skills/docx
    - The corrections JSON must contain an array of correction objects
"""
import argparse, os, sys, re, difflib, json, glob, shutil, tempfile


# ---- Locate and import the Document library ----

def find_skill_root():
    """Find the docx skill root directory."""
    candidates = [
        os.path.expanduser('~/.claude/skills/docx'),
        '/mnt/skills/public/docx',
        '/mnt/skills/docx',
    ]
    for c in candidates:
        if os.path.isfile(os.path.join(c, 'scripts', 'document.py')):
            return c
    return None

SKILL_ROOT = find_skill_root()
if not SKILL_ROOT:
    sys.exit("ERROR: Could not find the docx skill. Expected at ~/.claude/skills/docx")
sys.path.insert(0, SKILL_ROOT)

from scripts.document import Document, DocxXMLEditor
from ooxml.scripts.pack import pack_document


# ---- Fix UTF-16 encoded XML files ----

def fix_utf16_files(directory):
    """Convert any UTF-16 encoded XML files to UTF-8."""
    count = 0
    for xml_path in glob.glob(os.path.join(directory, '**', '*.xml'), recursive=True):
        with open(xml_path, 'rb') as f:
            header = f.read(4)
        if header[:2] in (b'\xff\xfe', b'\xfe\xff'):
            with open(xml_path, 'rb') as f:
                content = f.read()
            text = content.decode('utf-16')
            text = text.replace('encoding="utf-16"', 'encoding="UTF-8"')
            text = text.replace("encoding='utf-16'", "encoding='UTF-8'")
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(text)
            count += 1
    if count:
        print(f"  Converted {count} UTF-16 XML file(s) to UTF-8")


# ---- XML text helpers ----

def extract_text(para):
    """Extract text from a minidom w:p element, including tabs."""
    parts = []
    for r in para.getElementsByTagName('w:r'):
        for ch in r.childNodes:
            if ch.nodeType != ch.ELEMENT_NODE:
                continue
            if ch.tagName == 'w:t':
                parts.append(''.join(
                    c.data for c in ch.childNodes if c.nodeType == c.TEXT_NODE
                ))
            elif ch.tagName == 'w:tab':
                parts.append('\t')
    return ''.join(parts)


def get_rpr(para):
    """Get rPr XML string from the first run in a paragraph."""
    for r in para.getElementsByTagName('w:r'):
        for ch in r.childNodes:
            if ch.nodeType == ch.ELEMENT_NODE and ch.tagName == 'w:rPr':
                s = ch.toxml()
                return re.sub(r' xmlns:\w+="[^"]*"', '', s)
        return ''
    return ''


def get_ppr(para):
    """Get pPr XML string from a paragraph."""
    for ch in para.childNodes:
        if ch.nodeType == ch.ELEMENT_NODE and ch.tagName == 'w:pPr':
            s = ch.toxml()
            return re.sub(r' xmlns:\w+="[^"]*"', '', s)
    return ''


def nm(t):
    """Normalize whitespace for matching."""
    return re.sub(r'\s+', ' ', t.strip())


def esc(text):
    """Escape text for XML content."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---- Diff and tracked-change XML construction ----

def text_to_runs(rpr, text, is_del=False):
    """Convert text to XML runs, splitting at tab characters."""
    tag = 'w:delText' if is_del else 'w:t'
    segs = text.split('\t')
    runs = []
    for i, seg in enumerate(segs):
        if seg:
            runs.append(
                f'<w:r>{rpr}<{tag} xml:space="preserve">{esc(seg)}</{tag}></w:r>'
            )
        if i < len(segs) - 1:
            runs.append(f'<w:r>{rpr}<w:tab/></w:r>')
    return ''.join(runs)


def char_diff_ops(old, new):
    """Character-level diff preserving exact original text."""
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if tag == 'equal':
            ops.append(('eq', old[i1:i2]))
        elif tag == 'delete':
            ops.append(('del', old[i1:i2]))
        elif tag == 'insert':
            ops.append(('ins', new[j1:j2]))
        elif tag == 'replace':
            ops.append(('del', old[i1:i2]))
            ops.append(('ins', new[j1:j2]))
    return ops


def merge_ops(ops):
    """Merge consecutive ops of the same type."""
    if not ops:
        return ops
    merged = [ops[0]]
    for op, text in ops[1:]:
        if merged[-1][0] == op:
            merged[-1] = (op, merged[-1][1] + text)
        else:
            merged.append((op, text))
    return merged


def tracked_runs_xml(rpr, ops):
    """Build tracked-change XML runs from diff operations."""
    parts = []
    for op, text in ops:
        if op == 'eq':
            parts.append(text_to_runs(rpr, text, is_del=False))
        elif op == 'del':
            inner = text_to_runs(rpr, text, is_del=True)
            parts.append(f'<w:del>{inner}</w:del>')
        elif op == 'ins':
            inner = text_to_runs(rpr, text, is_del=False)
            parts.append(f'<w:ins>{inner}</w:ins>')
    return ''.join(parts)


# ---- Find and modify paragraphs ----

def find_matching_para(all_paras, all_norms, target_text):
    """Find the paragraph index that best matches the target text.

    Uses normalized substring matching, falling back to fuzzy ratio.
    """
    target_norm = nm(target_text)
    if not target_norm:
        return None

    # Exact normalized match
    for i, n in enumerate(all_norms):
        if target_norm == n:
            return i

    # Substring match (target contained in paragraph or vice versa)
    for i, n in enumerate(all_norms):
        if target_norm in n or n in target_norm:
            if len(n) > 10:  # avoid trivially short matches
                return i

    # Fuzzy match — find best ratio above threshold
    best_idx, best_ratio = None, 0.0
    for i, n in enumerate(all_norms):
        if not n:
            continue
        r = difflib.SequenceMatcher(None, target_norm, n).ratio()
        if r > best_ratio:
            best_idx, best_ratio = i, r

    if best_ratio > 0.5:
        return best_idx

    return None


def apply_correction(ed, para, xml_raw_text, original_text, revised_text):
    """Apply a single correction as tracked changes to a paragraph.

    If the correction targets a substring of the paragraph, applies the change
    within the full paragraph context.
    """
    ppr, rpr = get_ppr(para), get_rpr(para)

    # Determine what to diff: if original_text is a substring, replace just that
    # portion within the full paragraph text
    full_text = xml_raw_text
    orig_norm = nm(original_text)
    full_norm = nm(full_text)

    if orig_norm == full_norm:
        # Entire paragraph is the target
        old_text = full_text
        new_text = revised_text
    elif orig_norm in full_norm:
        # Substring replacement within the paragraph
        old_text = full_text
        new_text = full_text.replace(original_text, revised_text, 1)
        if nm(old_text) == nm(new_text):
            # Try normalized replacement
            # Find the original substring position using normalized text
            old_text = full_text
            new_text = revised_text
    else:
        # Best effort: diff the whole paragraph against revised
        old_text = full_text
        new_text = revised_text

    if nm(old_text) == nm(new_text):
        return None  # no actual change

    ops = merge_ops(char_diff_ops(old_text, new_text))
    runs = tracked_runs_xml(rpr, ops)

    new_p_xml = f'<w:p>{ppr}{runs}</w:p>'
    try:
        nodes = ed.replace_node(para, new_p_xml)
        return next(
            (x for x in nodes if getattr(x, 'tagName', None) == 'w:p'), None
        )
    except Exception as e:
        print(f"    ERR modify: {e}")
        return None


# ---- Unpack helper ----

def unpack_docx(docx_path, unpack_dir):
    """Unpack a .docx file using the docx skill's unpack script."""
    unpack_script = os.path.join(SKILL_ROOT, 'ooxml', 'scripts', 'unpack.py')
    if not os.path.isfile(unpack_script):
        # Fallback: simple ZIP extraction
        import zipfile
        os.makedirs(unpack_dir, exist_ok=True)
        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(unpack_dir)
        return True

    import subprocess
    result = subprocess.run(
        [sys.executable, unpack_script, docx_path, unpack_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Unpack error: {result.stderr[:300]}")
        return False
    return True


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(
        description='Apply corrections as tracked changes to a draft loan document.'
    )
    parser.add_argument(
        'draft_path',
        help='Path to the draft .docx file'
    )
    parser.add_argument(
        'corrections_path',
        help='Path to the corrections JSON file'
    )
    parser.add_argument(
        '--author', '-a', default='HK',
        help='Author name for tracked changes (default: HK)'
    )
    args = parser.parse_args()

    draft_path = os.path.abspath(args.draft_path)
    corrections_path = os.path.abspath(args.corrections_path)

    if not os.path.isfile(draft_path):
        sys.exit(f"ERROR: Draft file not found: {draft_path}")
    if not os.path.isfile(corrections_path):
        sys.exit(f"ERROR: Corrections file not found: {corrections_path}")

    # Load corrections
    with open(corrections_path) as f:
        corrections = json.load(f)

    # Filter to only deviations that have original/revised text
    deviations = [
        c for c in corrections
        if c.get('status') == 'deviates'
        and c.get('original_text')
        and c.get('revised_text')
    ]

    if not deviations:
        print(f"No deviations to apply for {os.path.basename(draft_path)}")
        return 0

    print(f"\n{'='*50}")
    print(f"Applying corrections: {os.path.basename(draft_path)}")
    print(f"{'='*50}")
    print(f"  {len(deviations)} deviation(s) to correct")

    # Unpack .docx to temp directory
    unpack_dir = tempfile.mkdtemp(prefix='review_draft_')
    print(f"  Unpacking .docx...")
    if not unpack_docx(draft_path, unpack_dir):
        sys.exit(f"ERROR: Failed to unpack {draft_path}")

    # Fix any UTF-16 encoded XML files
    fix_utf16_files(unpack_dir)

    # Initialize Document library
    print("  Initializing Document library...")
    doc = Document(unpack_dir, author=args.author)
    ed = doc["word/document.xml"]

    # Build paragraph index
    all_paras = list(ed.dom.getElementsByTagName('w:p'))
    all_texts = [extract_text(p) for p in all_paras]
    all_norms = [nm(t) for t in all_texts]
    print(f"  {len(all_paras)} total paragraphs")

    # Apply each correction
    applied = 0
    failed = 0

    for corr in deviations:
        req_id = corr.get('requirement_id', '?')
        original = corr['original_text']
        revised = corr['revised_text']
        section = corr.get('draft_section', 'unknown section')

        print(f"\n  Req #{req_id} ({section}):")

        # Find the paragraph containing the original text
        idx = find_matching_para(all_paras, all_norms, original)
        if idx is None:
            print(f"    SKIP: Could not find matching paragraph")
            failed += 1
            continue

        print(f"    Found at paragraph {idx}: {all_norms[idx][:60]}...")

        new_p = apply_correction(
            ed, all_paras[idx], all_texts[idx], original, revised
        )
        if new_p:
            all_paras[idx] = new_p
            all_texts[idx] = extract_text(new_p)
            all_norms[idx] = nm(all_texts[idx])
            applied += 1
            print(f"    Applied tracked change")
        else:
            print(f"    SKIP: No change needed or modification failed")
            failed += 1

    print(f"\n{'='*50}")
    print(f"TOTAL: {applied} applied, {failed} failed/skipped")

    # Save with validation
    print("\nSaving and validating...")
    try:
        doc.save(unpack_dir)
        print("  Validation passed!")
    except ValueError as e:
        print(f"  Validation failed: {e}")
        doc.save(unpack_dir, validate=False)
        print("  Saved without validation (review output manually)")

    # Repack to .docx, overwriting the original
    print(f"Packing → {os.path.basename(draft_path)}")
    pack_document(unpack_dir, draft_path)

    # Clean up temp directory
    shutil.rmtree(unpack_dir, ignore_errors=True)

    print(f"\nDone! Output: {draft_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
