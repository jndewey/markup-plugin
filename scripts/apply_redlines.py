#!/usr/bin/env python3
"""
Apply all reviewed provision revisions as tracked changes in the original Word document.

Uses the Document library from Claude Code's built-in docx skill for:
  - Automatic infrastructure setup (people.xml, RSIDs, settings.xml)
  - Automatic attribute injection (w:id, w:author, w:date on tracked changes)
  - Built-in schema + redlining validation
  - Comment support via doc.add_comment()

Matches directly against XML paragraphs (not original.txt) to avoid paragraph
boundary mismatches between text extraction and OOXML structure.

Usage:
    PYTHONPATH=~/.claude/skills/docx python scripts/apply_redlines.py [deal_dir]

    deal_dir defaults to the current working directory.

Prerequisites:
    - unpacked/ directory must exist (created by prepare_deal.py for .docx inputs)
    - Provision folders must have status "reviewed" with revised.txt files
    - The docx skill must be installed at ~/.claude/skills/docx
"""
import argparse, os, sys, re, difflib, json, glob


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
    """Normalize whitespace for matching/indexing."""
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


# ---- Section boundary detection ----

def find_section_boundaries(all_paras, all_norms):
    """Find top-level section header paragraph indices.

    Returns dict: section_number_str -> paragraph_index
    """
    boundaries = {}
    # Match patterns like "1.\tDEFINITIONS" or "6. REPRESENTATIONS"
    for i, n in enumerate(all_norms):
        # Top-level section: starts with a single number, period, then
        # tab or space, then uppercase word(s)
        m = re.match(r'^(\d+)\.\s+([A-Z])', n)
        if m:
            sec = m.group(1)
            if sec not in boundaries:
                boundaries[sec] = i
    return boundaries


def get_provision_range(section_num, section_boundaries, total_paras):
    """Get the paragraph index range [start, end) for a section."""
    start = section_boundaries.get(section_num)
    if start is None:
        return None, None
    # End is the start of the next section (by numeric order)
    all_starts = sorted(section_boundaries.values())
    idx = all_starts.index(start)
    end = all_starts[idx + 1] if idx + 1 < len(all_starts) else total_paras
    return start, end


# ---- Apply modification to a paragraph ----

def apply_modification(ed, para, xml_raw_text, revised_text):
    """Apply character-level tracked changes to a paragraph.

    Args:
        ed: DocxXMLEditor for the document
        para: DOM node of the paragraph
        xml_raw_text: raw text extracted from the XML paragraph
        revised_text: the target revised text for this paragraph

    Returns:
        The new paragraph DOM node, or None on failure
    """
    ppr, rpr = get_ppr(para), get_rpr(para)

    # Split at first tab to separate section-number prefix from body
    if '\t' in xml_raw_text:
        orig_pfx, orig_body = xml_raw_text.split('\t', 1)
        orig_pfx += '\t'
    else:
        orig_pfx, orig_body = '', xml_raw_text

    if '\t' in revised_text:
        _, rev_body = revised_text.split('\t', 1)
    else:
        rev_body = revised_text
        m = re.match(r'^[\d.]+\.?\s+', rev_body)
        if m and orig_pfx:
            rev_body = rev_body[m.end():]

    if nm(orig_body) == nm(rev_body):
        return None  # no actual change

    # Character-level diff preserves exact original text
    ops = merge_ops(char_diff_ops(orig_body, rev_body))
    runs = tracked_runs_xml(rpr, ops)

    pfx_xml = ''
    if orig_pfx:
        sn = orig_pfx.rstrip('\t')
        pfx_xml = f'<w:r>{rpr}<w:t>{esc(sn)}</w:t></w:r><w:r>{rpr}<w:tab/></w:r>'

    new_p_xml = f'<w:p>{ppr}{pfx_xml}{runs}</w:p>'
    try:
        nodes = ed.replace_node(para, new_p_xml)
        return next(
            (x for x in nodes if getattr(x, 'tagName', None) == 'w:p'), None
        )
    except Exception as e:
        print(f"    ERR modify: {e}")
        return None


def apply_insertion(ed, anchor_para, revised_text):
    """Insert a new tracked-change paragraph after the anchor.

    Returns:
        The new paragraph DOM node, or None on failure
    """
    rpr = get_rpr(anchor_para)

    if '\t' in revised_text:
        pfx_part, body_part = revised_text.split('\t', 1)
        pfx_part += '\t'
    else:
        pfx_part, body_part = '', revised_text
        m = re.match(r'^([\d.]+\.?\s+)', body_part)
        if m:
            pfx_part = m.group(1).rstrip() + '\t'
            body_part = body_part[m.end():]

    pfx_runs = ''
    if pfx_part:
        sn = pfx_part.rstrip('\t')
        pfx_runs = (
            f'<w:r>{rpr}<w:t>{esc(sn)}</w:t></w:r>'
            f'<w:r>{rpr}<w:tab/></w:r>'
        )
    body_run = f'<w:r>{rpr}<w:t xml:space="preserve">{esc(body_part)}</w:t></w:r>'
    tracked_para = (
        f'<w:p><w:pPr><w:rPr><w:ins/></w:rPr></w:pPr>'
        f'<w:ins>{pfx_runs}{body_run}</w:ins></w:p>'
    )

    try:
        nodes = ed.insert_after(anchor_para, tracked_para)
        return next(
            (x for x in nodes if getattr(x, 'tagName', None) == 'w:p'), None
        )
    except Exception as e:
        print(f"    ERR insert: {e}")
        return None


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(
        description='Apply reviewed provision revisions as tracked changes to a Word document.'
    )
    parser.add_argument(
        'deal_dir', nargs='?', default=os.getcwd(),
        help='Path to deal workspace (default: current directory)'
    )
    parser.add_argument(
        '--output', '-o', default='redline_agreement.docx',
        help='Output filename (default: redline_agreement.docx)'
    )
    args = parser.parse_args()

    deal = os.path.abspath(args.deal_dir)
    prov_dir = os.path.join(deal, 'provisions')
    unpacked = os.path.join(deal, 'unpacked')

    if not os.path.isdir(unpacked):
        sys.exit(f"ERROR: No unpacked/ directory found in {deal}. "
                 "This command requires a .docx-based deal prepared by prepare_deal.py.")
    if not os.path.isdir(prov_dir):
        sys.exit(f"ERROR: No provisions/ directory found in {deal}.")

    # Fix any UTF-16 encoded XML files
    print("Checking for UTF-16 encoded files...")
    fix_utf16_files(unpacked)

    # Initialize Document library (handles infrastructure automatically)
    print("Initializing Document library...")
    doc = Document(unpacked, author="HK")
    ed = doc["word/document.xml"]

    # Build ordered list of all paragraphs with their text
    all_paras = list(ed.dom.getElementsByTagName('w:p'))
    all_texts = [extract_text(p) for p in all_paras]
    all_norms = [nm(t) for t in all_texts]
    print(f"  {len(all_paras)} total paragraphs")

    # Find section boundaries
    section_boundaries = find_section_boundaries(all_paras, all_norms)
    print(f"  Found sections: {sorted(section_boundaries.keys(), key=int)}")

    # Collect reviewed provisions
    provisions = []
    for prov_folder in sorted(os.listdir(prov_dir)):
        prov_path = os.path.join(prov_dir, prov_folder)
        if not os.path.isdir(prov_path):
            continue
        manifest_path = os.path.join(prov_path, 'manifest.json')
        revised_path = os.path.join(prov_path, 'revised.txt')
        if not os.path.exists(revised_path) or not os.path.exists(manifest_path):
            continue
        with open(manifest_path) as f:
            manifest = json.load(f)
        if manifest.get('status') != 'reviewed':
            continue
        if 'full_agreement' in prov_folder:
            continue
        provisions.append({
            'folder': prov_folder,
            'path': prov_path,
            'section_number': manifest.get('section_number', ''),
            'title': manifest.get('title', ''),
            'revised_path': revised_path,
        })

    print(f"  {len(provisions)} reviewed provisions to apply")

    # Process each provision
    total_mc, total_dc, total_ic = 0, 0, 0

    for prov in provisions:
        sec_num = prov['section_number']
        title = prov['title']
        print(f"\n--- {title} (Section {sec_num}) ---")

        start, end = get_provision_range(sec_num, section_boundaries, len(all_paras))
        if start is None:
            print(f"  SKIP: Section {sec_num} not found in XML")
            continue

        # Extract this provision's non-empty XML paragraphs
        prov_paras = []
        prov_texts = []
        prov_norms = []
        for i in range(start, end):
            if all_norms[i]:
                prov_paras.append(all_paras[i])
                prov_texts.append(all_texts[i])
                prov_norms.append(all_norms[i])

        # Read revised.txt, stripping inline commentary markers.
        # Use greedy match (.*) so nested brackets like $[X] inside a marker
        # don't prematurely close the match.
        def strip_markers(line):
            line = re.sub(r'\s*\[(REVISED|NOTE|COMMENT|RECOMMENDATION):.*\]', '', line)
            return line.rstrip('\n')

        with open(prov['revised_path']) as f:
            revised_raw = [
                strip_markers(l)
                for l in f if l.strip()
            ]
        rev_norms = [nm(l) for l in revised_raw]

        print(f"  XML paragraphs: {len(prov_paras)}, Revised lines: {len(revised_raw)}")

        # Paragraph-level alignment: XML paragraphs vs revised lines
        sm = difflib.SequenceMatcher(None, prov_norms, rev_norms)
        mc, dc, ic = 0, 0, 0

        # We need to track the current anchor for insertions as paragraphs
        # get modified. Use a mutable list to hold current paragraph nodes.
        current_paras = list(prov_paras)  # copy — will be updated as we go

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue

            elif tag == 'delete':
                for k in range(i1, i2):
                    try:
                        ed.suggest_deletion(current_paras[k])
                        dc += 1
                    except Exception as e:
                        print(f"    ERR delete: {e}")

            elif tag == 'insert':
                # Find anchor paragraph (the one just before the insertion point)
                anchor = current_paras[i1 - 1] if i1 > 0 else current_paras[0]
                for k in range(j1, j2):
                    new_p = apply_insertion(ed, anchor, revised_raw[k])
                    if new_p:
                        anchor = new_p  # chain insertions
                        ic += 1

            elif tag == 'replace':
                # Bipartite matching: pair XML paragraphs ↔ revised lines
                orig_range = list(range(i1, i2))
                rev_range = list(range(j1, j2))

                used_rev = set()
                matched = {}  # orig_idx -> rev_idx
                for oi in orig_range:
                    best_ri, best_r = None, 0
                    for ri in rev_range:
                        if ri in used_rev:
                            continue
                        r = difflib.SequenceMatcher(
                            None, prov_norms[oi], rev_norms[ri]
                        ).ratio()
                        if r > best_r:
                            best_ri, best_r = ri, r
                    if best_ri is not None and best_r > 0.35:
                        matched[oi] = best_ri
                        used_rev.add(best_ri)

                # Apply modifications for matched pairs
                for oi, ri in sorted(matched.items()):
                    new_p = apply_modification(
                        ed, current_paras[oi],
                        prov_texts[oi], revised_raw[ri]
                    )
                    if new_p:
                        current_paras[oi] = new_p
                        mc += 1

                # Delete unmatched XML paragraphs
                for oi in orig_range:
                    if oi not in matched:
                        try:
                            ed.suggest_deletion(current_paras[oi])
                            dc += 1
                        except Exception as e:
                            print(f"    ERR delete: {e}")

                # Insert unmatched revised lines
                inv_match = {ri: oi for oi, ri in matched.items()}
                anchor = current_paras[i1 - 1] if i1 > 0 else current_paras[i1]
                for ri in rev_range:
                    if ri in inv_match:
                        # Matched pair — update anchor to this paragraph
                        anchor = current_paras[inv_match[ri]]
                    else:
                        new_p = apply_insertion(ed, anchor, revised_raw[ri])
                        if new_p:
                            anchor = new_p
                            ic += 1

        print(f"  Applied: {mc} modifications, {dc} deletions, {ic} insertions")
        total_mc += mc
        total_dc += dc
        total_ic += ic

    print(f"\n{'='*50}")
    print(f"TOTAL: {total_mc} modifications, {total_dc} deletions, {total_ic} insertions")

    # ---- Save with validation ----
    print("\nSaving and validating...")
    try:
        doc.save(unpacked)
        print("  Validation passed!")
    except ValueError as e:
        print(f"  Validation failed: {e}")
        doc.save(unpacked, validate=False)
        print("  Saved without validation (review output manually)")

    # ---- Pack to .docx ----
    output_path = os.path.join(deal, args.output)
    print(f"Packing → {args.output}")
    pack_document(unpacked, output_path)
    print(f"\nDone! Output: {output_path}")


if __name__ == '__main__':
    main()
