#!/usr/bin/env python3
"""
Apply all reviewed provision revisions as tracked changes in the original Word document.

Uses the Document library from Claude Code's built-in docx skill for:
  - Automatic infrastructure setup (people.xml, RSIDs, settings.xml)
  - Automatic attribute injection (w:id, w:author, w:date on tracked changes)
  - Built-in schema + redlining validation
  - Comment support via doc.add_comment()

Uses character-level diff to preserve exact original text, ensuring the
redlining validator confirms that reverting all changes produces the original.

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
    """Convert any UTF-16 encoded XML files to UTF-8.

    Some .docx files contain customXml items encoded in UTF-16.
    The Document library's pack/parse functions expect UTF-8.
    """
    count = 0
    for xml_path in glob.glob(os.path.join(directory, '**', '*.xml'), recursive=True):
        with open(xml_path, 'rb') as f:
            header = f.read(4)
        # UTF-16 LE BOM: ff fe, UTF-16 BE BOM: fe ff
        if header[:2] in (b'\xff\xfe', b'\xfe\xff'):
            encoding = 'utf-16-le' if header[:2] == b'\xff\xfe' else 'utf-16-be'
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


# ---- Build change map from provisions ----

def build_changes(prov_dir):
    """Parse all reviewed provisions and build modification/insertion/deletion maps.

    Returns:
        mods: dict mapping normalized original text → revised text
        ins_list: list of (anchor_norm_text, new_text) tuples
        dels: set of normalized texts to delete
    """
    mods, ins_list, dels = {}, [], set()

    for prov in sorted(os.listdir(prov_dir)):
        pd = os.path.join(prov_dir, prov)
        if not os.path.isdir(pd):
            continue
        rev_f = os.path.join(pd, 'revised.txt')
        man_f = os.path.join(pd, 'manifest.json')
        orig_f = os.path.join(pd, 'original.txt')
        if not os.path.exists(rev_f):
            continue
        with open(man_f) as f:
            if json.load(f).get('status') != 'reviewed':
                continue

        with open(orig_f) as f:
            orig = [l.rstrip('\n') for l in f if l.strip()]
        with open(rev_f) as f:
            rev = [
                re.sub(r'\s*\[REVISED:.*?\]', '', l).rstrip('\n')
                for l in f if l.strip()
            ]

        on = [nm(l) for l in orig]
        rn = [nm(l) for l in rev]

        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, on, rn).get_opcodes():
            if tag == 'equal':
                continue
            elif tag == 'delete':
                for k in range(i1, i2):
                    dels.add(on[k])
            elif tag == 'insert':
                after = on[i1 - 1] if i1 > 0 else None
                for k in range(j1, j2):
                    ins_list.append((after, rev[k]))
                    after = nm(rev[k])
            elif tag == 'replace':
                # Bipartite matching: pair original ↔ revised paragraphs by similarity
                used, matched = set(), {}
                for oi in range(i1, i2):
                    best_ri, best_r = None, 0
                    for ri in range(j1, j2):
                        if ri in used:
                            continue
                        r = difflib.SequenceMatcher(None, on[oi], rn[ri]).ratio()
                        if r > best_r:
                            best_ri, best_r = ri, r
                    if best_ri is not None and best_r > 0.4:
                        matched[oi] = best_ri
                        used.add(best_ri)

                for oi in range(i1, i2):
                    if oi in matched:
                        mods[on[oi]] = rev[matched[oi]]
                    else:
                        dels.add(on[oi])

                # Use ORIGINAL text as anchor for insertions (findable in pidx)
                inv = {ri: oi for oi, ri in matched.items()}
                after = on[i1 - 1] if i1 > 0 else None
                for ri in range(j1, j2):
                    if ri not in used:
                        ins_list.append((after, rev[ri]))
                        after = nm(rev[ri])
                    else:
                        after = on[inv[ri]]

    return mods, ins_list, dels


# ---- Paragraph index helpers ----

def build_para_index(editor):
    """Build normalized-text → (DOM node, raw text) index for all paragraphs."""
    pidx = {}
    raw = {}
    for p in editor.dom.getElementsByTagName('w:p'):
        t = extract_text(p)
        n = nm(t)
        if n:
            pidx[n] = p
            raw[n] = t
    return pidx, raw


def find_key(pidx, norm_text):
    """Find the best-matching key in pidx (exact or fuzzy)."""
    if norm_text in pidx:
        return norm_text
    best, br = None, 0
    for k in pidx:
        r = difflib.SequenceMatcher(None, norm_text, k).ratio()
        if r > br:
            best, br = k, r
    return best if best and br > 0.7 else None


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

    # Build change map from provision reviews
    print("Building change map from provisions...")
    mods, ins_list, dels = build_changes(prov_dir)
    print(f"  {len(mods)} modifications, {len(ins_list)} insertions, {len(dels)} deletions")

    if not mods and not ins_list and not dels:
        print("No changes to apply.")
        return

    # Initialize Document library (handles infrastructure automatically)
    print("Initializing Document library...")
    doc = Document(unpacked, author="HK")
    ed = doc["word/document.xml"]

    pidx, raw_text = build_para_index(ed)
    print(f"  {len(pidx)} paragraphs indexed")

    # ---- 1. Apply modifications ----
    print("\nApplying modifications...")
    mc = 0
    for orig_nm, new_txt in mods.items():
        key = find_key(pidx, orig_nm)
        if not key:
            print(f"  WARN: No match: {orig_nm[:60]}...")
            continue
        p = pidx[key]
        ppr, rpr = get_ppr(p), get_rpr(p)
        orig_raw = raw_text[key]

        # Split at first tab to separate section-number prefix from body
        if '\t' in orig_raw:
            orig_pfx, orig_body = orig_raw.split('\t', 1)
            orig_pfx += '\t'
        else:
            orig_pfx, orig_body = '', orig_raw

        if '\t' in new_txt:
            _, rev_body = new_txt.split('\t', 1)
        else:
            rev_body = new_txt
            m = re.match(r'^[\d.]+\.?\s+', rev_body)
            if m and orig_pfx:
                rev_body = rev_body[m.end():]

        if orig_body == rev_body:
            continue

        # Character-level diff preserves exact original text
        ops = merge_ops(char_diff_ops(orig_body, rev_body))
        runs = tracked_runs_xml(rpr, ops)

        pfx_xml = ''
        if orig_pfx:
            sn = orig_pfx.rstrip('\t')
            pfx_xml = f'<w:r>{rpr}<w:t>{esc(sn)}</w:t></w:r><w:r>{rpr}<w:tab/></w:r>'

        new_p_xml = f'<w:p>{ppr}{pfx_xml}{runs}</w:p>'
        try:
            nodes = ed.replace_node(p, new_p_xml)
            new_p = next(
                (x for x in nodes if getattr(x, 'tagName', None) == 'w:p'), None
            )
            if new_p:
                pidx[key] = new_p
                pidx[orig_nm] = new_p
            mc += 1
        except Exception as e:
            print(f"  ERR: {e}")
    print(f"  {mc} modifications applied")

    # ---- 2. Apply deletions ----
    print("\nApplying deletions...")
    dc = 0
    for dn in dels:
        key = find_key(pidx, dn)
        if not key:
            print(f"  WARN: No match for deletion: {dn[:60]}...")
            continue
        try:
            ed.suggest_deletion(pidx[key])
            dc += 1
        except Exception as e:
            print(f"  ERR: {e}")
    print(f"  {dc} deletions applied")

    # ---- 3. Apply insertions ----
    print("\nApplying insertions...")
    ic = 0
    last_ins = {}
    for after_nm, new_txt in ins_list:
        ap = None
        if after_nm and after_nm in last_ins:
            ap = last_ins[after_nm]
        elif after_nm:
            key = find_key(pidx, after_nm)
            if key:
                ap = pidx[key]
        if not ap:
            print(f"  WARN: No anchor after: {(after_nm or '(start)')[:60]}...")
            continue

        rpr = get_rpr(ap)

        if '\t' in new_txt:
            pfx_part, body_part = new_txt.split('\t', 1)
            pfx_part += '\t'
        else:
            pfx_part, body_part = '', new_txt
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
            nodes = ed.insert_after(ap, tracked_para)
            ic += 1
            new_p = next(
                (x for x in nodes if getattr(x, 'tagName', None) == 'w:p'), None
            )
            if new_p:
                last_ins[after_nm] = new_p
                last_ins[nm(new_txt)] = new_p
        except Exception as e:
            print(f"  ERR: {e}")
    print(f"  {ic} insertions applied")

    # ---- 4. Save with validation ----
    print("\nSaving and validating...")
    try:
        doc.save(unpacked)
        print("  Validation passed!")
    except ValueError as e:
        print(f"  Validation failed: {e}")
        doc.save(unpacked, validate=False)
        print("  Saved without validation (review output manually)")

    # ---- 5. Pack to .docx ----
    output_path = os.path.join(deal, args.output)
    print(f"Packing → {args.output}")
    pack_document(unpacked, output_path)
    print(f"\nDone! Output: {output_path}")


if __name__ == '__main__':
    main()
