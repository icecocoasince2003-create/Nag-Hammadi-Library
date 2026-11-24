#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_tei.py <出力フォルダ> [tei_all.rng]

make_tei.py が作った tei/*.xml を、同じフォルダの nhc_all.tsv / catalog.tsv / restored_letters.tsv と突き合わせる。
  1. 整形式の XML であること。UTF-8（BOM なし）、改行は LF。
  2. TEI から（通し番号、種類、行 ID と開始位置、本文）を組み立て直すと nhc_all.tsv と完全に一致すること
     （<w> → トークン、<gap> → [...]、<ab type> → kind）。
     語群（<phr>）を付けた版（README_ja.md の §10）は語の区切りを一部変えているので、本文は語の区切りを除いた
     文字列（欠損 [...] の位置を含む）で比べ、区切りを変えた数を最後に示す。<phr> の中は <w> だけであること。
  3. ⲍ・ⲯ を戻した語の印（<w resp="#zp" cert="…">）が restored_letters.tsv と 1 対 1 に対応し、
     印のない <w> には ⲍ・ⲯ がないこと。<w> の属性はこの印だけ（語群を付けた版では、注釈つきの版から写した
     type・lemma・xml:lang も認める）。
     形態素注釈を付けた版（README_ja.md の §11）では、<w> の resp（#morph-auto / #morph-reference）と cert（high /
     medium / low）は注釈のもので、ⲍ・ⲯ を戻した印は、戻した字を包む <supplied reason="lost-in-source-file"
     resp="#zp" cert="…"> になる。語の中のどの ⲍ・ⲯ もこれに包まれていること。@ana の指す先は scripts/check_tei.py が確かめる。
     Coptic SCRIPTORIUM の NLP で付け直した版（README_ja.md の §13。resp="#coptic-nlp"）では、戻した語が 2 つ以上の
     <w> に分かれることがあるので、語ごとではなく、戻した字（<supplied>）の並びと確度を restored_letters.tsv と比べる。
     <gap> の reason は lacuna（make_tei.py の出力）か lost（§13 で EpiDoc に合わせた版）。
  4. xml:id が XML の名前として正しく、<s> と証本（<text>）の ID が全ファイルを通じて重複しないこと。
  5. ヘッダーの件数（<extent>）、本文の実数、catalog.tsv の件数が一致すること
     （語群を付けた版の語数は catalog.tsv と比べない。区切りを変えたため）。
  6. サイトの検索ページ・ビュワーと同じ読み方（<text type="witness"> の子孫の <s xml:id> と <w>）で
     数えたセグメント数・トークン数が一致すること。
  7. tei_all.rng（TEI P5 の RELAX NG スキーマ）を渡したときは、lxml でスキーマ検証も行う（lxml が必要）。
"""
import sys, os, re, collections
import xml.etree.ElementTree as ET

NS = '{http://www.tei-c.org/ns/1.0}'
XML = '{http://www.w3.org/XML/1998/namespace}'
GAP = '[...]'
KINDS = ('title', 'text', 'subscript', 'colophon', 'fragment')
CERT = {'A': 'high', 'B': 'medium'}
# 形態素注釈の @resp: 2026-11-18 の暫定版（§11）と、Coptic SCRIPTORIUM の NLP で付け直した版（§13）
ANNOTATION_RESP = ('#morph-auto', '#morph-reference', '#coptic-nlp')

def read_tsv(path):
    with open(path, encoding='utf-8', newline='') as f:
        lines = f.read().split('\n')
    head = lines[0].split('\t')
    return [dict(zip(head, l.split('\t'))) for l in lines[1:] if l]

def word_ends(toks):
    """トークンの終わりの位置（文字数で数える）。語の区切りを比べるのに使う。"""
    pos, ends = 0, set()
    for t in toks:
        pos += len(t)
        ends.add(pos)
    return ends

def main(out, rng=None):
    ok = True
    def check(cond, msg):
        nonlocal ok
        if not cond:
            ok = False; print('FAIL:', msg)

    cat = read_tsv(os.path.join(out, 'catalog.tsv'))
    recs = collections.defaultdict(list)
    for r in read_tsv(os.path.join(out, 'nhc_all.tsv')):
        recs[r['unit']].append(r)
    rest = collections.defaultdict(list)
    for x in read_tsv(os.path.join(out, 'restored_letters.tsv')):
        rest[(x['unit'], x['seq'])].append((x['restored'], CERT[x['confidence']]))
    # ⲍ・ⲯ の復元が行われた出力では、ⲍ・ⲯ を含む語はすべて戻した語（＝印が付く）。
    # ⲍ・ⲯ が正しく入った元ファイルから作った出力（復元の記録が空）では、この条件は当てはまらない。
    restored_run = len(rest) > 0
    dst = os.path.join(out, 'tei')
    check(sorted(os.listdir(dst)) == sorted(c['file'] + '.xml' for c in cat), 'tei/ のファイル名が catalog.tsv と一致しない')

    seen = {}                                   # <s>・<text> の xml:id → 文書
    tot = collections.Counter()
    for c in cat:
        unit, codex, tr = c['unit'], c['codex'], c['tractate']
        path = os.path.join(dst, c['file'] + '.xml')
        if not os.path.exists(path):
            check(False, f'{unit}: {path} がない'); continue
        raw = open(path, 'rb').read()
        check(not raw.startswith(b'\xef\xbb\xbf'), f'{unit}: BOM がある')
        check(b'\r' not in raw, f'{unit}: CR がある')
        check(raw.endswith(b'</TEI>\n'), f'{unit}: 末尾が </TEI> + 改行でない')
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            check(False, f'{unit}: 整形式でない: {e}'); continue
        check(root.tag == NS + 'TEI', f'{unit}: ルートが TEI でない')

        # ---- ID
        ids = [el.get(XML + 'id') for el in root.iter() if el.get(XML + 'id') is not None]
        check(len(ids) == len(set(ids)), f'{unit}: ファイル内で xml:id が重複')
        check(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9._-]*', i) for i in ids), f'{unit}: xml:id に使えない文字がある')
        check(any(el.get(XML + 'id') == 'zp' for el in root.iter(NS + 'respStmt')), f'{unit}: resp="#zp" の指す先がない')
        for el in list(root.iter(NS + 's')) + list(root.iter(NS + 'text')):
            i = el.get(XML + 'id')
            check(i is not None, f'{unit}: xml:id のない <{el.tag[len(NS):]}>')
            check(i not in seen, f'{unit}: xml:id {i} が {seen.get(i)} と重複')
            seen[i] = unit

        # ---- 証本
        wits = [t for t in root.iter(NS + 'text') if t.get('type') == 'witness']
        check(len(wits) == 1, f'{unit}: <text type="witness"> が 1 つでない')
        if len(wits) != 1:
            continue
        tx = wits[0]
        check(tx.get(XML + 'id') == 'wit-' + unit.replace(',', '-') and tx.get('n') == f'NHC {codex},{tr}',
              f'{unit}: 証本の xml:id / n が違う')
        div = tx.find(f'{NS}body/{NS}div')
        check(div is not None, f'{unit}: body/div がない')
        if div is None:
            continue
        kids = list(div)
        check(kids and kids[0].tag == NS + 'head' and all(k.tag == NS + 'ab' for k in kids[1:]), f'{unit}: div の子が head + ab でない')
        grouped = tx.find(f'.//{NS}phr') is not None          # 語群（<phr>）を付けた版（README_ja.md の §10）
        annotated_nlp = any(w.get('resp') == '#coptic-nlp' for w in tx.iter(NS + 'w'))   # NLP で付け直した版（§13）

        # ---- 本文を組み立て直す
        got, prev = [], None
        for ab in div.findall(NS + 'ab'):
            kind = ab.get('type')
            check(kind in KINDS, f'{unit}: ab の type が不正: {kind}')
            check(kind != prev, f'{unit}: 同じ type の ab が続いている')
            prev = kind
            check(not (ab.text or '').strip() and len(ab) > 0, f'{unit}: ab に余分な文字列がある／空の ab')
            for s in ab:
                check(s.tag == NS + 's' and not (s.text or '').strip() and not (s.tail or '').strip(),
                      f'{unit}: ab の中に <s> 以外のものがある')
                toks, marks, letter_marks = [], [], []
                here = f'{unit} n={s.get("n")}'

                def word(w):
                    t = ''.join(w.itertext())
                    sup = list(w)                                   # 戻した字を包む <supplied>（注釈を付けた版、§11）
                    check(t != '' and not re.search(r'\s', t) and (not sup or grouped), f'{here}: <w> の中身が不正')
                    for x in sup:
                        check(x.tag == NS + 'supplied' and len(x) == 0 and (x.text or '') in ('ⲍ', 'ⲯ')
                              and set(x.attrib) == {'reason', 'resp', 'cert'} and x.get('reason') == 'lost-in-source-file'
                              and x.get('resp') == '#zp' and x.get('cert') in ('high', 'medium'),
                              f'{here}: <w> の中の要素が不正: {x.tag} {x.attrib}')
                    check(len({x.get('cert') for x in sup}) <= 1, f'{here}: 1 語の中で復元の確度が違う: {t}')
                    check(not sup or len(re.findall('[ⲍⲯ]', t)) == len(sup), f'{here}: <supplied> に包まれていない ⲍ・ⲯ がある: {t}')
                    extra = set(w.attrib) - {'cert', 'resp'}
                    check(not extra or (grouped and extra <= {'type', 'lemma', 'ana', XML + 'lang'}),
                          f'{here}: <w> に想定外の属性 {sorted(w.attrib)}')
                    resp = w.get('resp')
                    if resp in ANNOTATION_RESP:                     # 形態素注釈の責任と確度
                        check(grouped and w.get('cert') in ('high', 'medium', 'low'), f'{here}: 注釈の確度が不正 {w.attrib}')
                    elif 'cert' in w.attrib or resp is not None:
                        check(resp == '#zp' and w.get('cert') in ('high', 'medium') and not sup,
                              f'{here}: 復元の印が不完全 {w.attrib}')
                    if sup:
                        marks.append((t, sup[0].get('cert')))
                        letter_marks.extend((x.text, x.get('cert')) for x in sup)
                    elif resp == '#zp':
                        marks.append((t, w.get('cert')))
                    elif restored_run:
                        check('ⲍ' not in t and 'ⲯ' not in t, f'{here}: 印のない <w> に ⲍ・ⲯ がある: {t}')
                    toks.append(t)

                for ch in s:
                    check(not (ch.tail or '').strip(), f'{here}: 要素の外に文字列がある')
                    if ch.tag == NS + 'w':
                        word(ch)
                    elif ch.tag == NS + 'phr':
                        check(not ch.attrib and not (ch.text or '').strip() and len(ch) > 0,
                              f'{here}: <phr> が空か、属性や文字列がある')
                        for w in ch:
                            check(w.tag == NS + 'w' and not (w.tail or '').strip(), f'{here}: <phr> の中に <w> 以外のものがある')
                            if w.tag == NS + 'w':
                                word(w)
                    elif ch.tag == NS + 'gap':
                        # reason は lacuna（make_tei.py の出力）か lost（仕様書 §4 に合わせた版。README_ja.md の §13）
                        check(ch.get('reason') in ('lacuna', 'lost') and ch.get('extent') == 'unknown' and ch.get('unit') in (None, 'line', 'page')
                              and set(ch.attrib) <= {'reason', 'extent', 'unit'} and len(ch) == 0 and not ch.text,
                              f'{unit} n={s.get("n")}: <gap> の属性が不正 {ch.attrib}')
                        toks.append(GAP)
                    else:
                        check(False, f'{unit} n={s.get("n")}: 想定外の要素 {ch.tag}')
                got.append((s.get('n'), kind, s.get(XML + 'id') or '', toks, marks, letter_marks))
        exp = recs[unit]
        check(len(got) == len(exp), f'{unit}: レコード数 {len(got)} != {len(exp)}')
        split = joined = 0
        for g, e in zip(got, exp):
            check(g[0] == e['seq'] and g[1] == e['kind'], f'{unit} n={g[0]}: 通し番号か種類が nhc_all.tsv と違う')
            if grouped:
                # 語の区切りを除いた文字列（欠損 [...] の位置を含む）を比べ、区切りを変えた数を数える
                check(''.join(g[3]) == e['text'].replace(' ', ''), f'{unit} n={g[0]}: 本文の文字が nhc_all.tsv と違う')
                a, b = word_ends(g[3]), word_ends(e['text'].split(' '))
                split += len(a - b)
                joined += len(b - a)
            else:
                check(' '.join(g[3]) == e['text'], f'{unit} n={g[0]}: 本文が nhc_all.tsv と違う')
            m = re.fullmatch(r'([IVX]+)-(\d+)(?:_(\d+))?', g[2])
            check(bool(m) and m.group(1) == codex and m.group(2) == e['src_id']
                  and (e['src_tok'] == 'all' if m.group(3) is None else e['src_tok'].split('-')[0] == m.group(3)),
                  f'{unit} n={g[0]}: xml:id {g[2]} が行 ID {e["src_id"]} / {e["src_tok"]} と対応しない')
            if annotated_nlp:
                # 形態素に切り直した版（§13）では、戻した語が 2 つ以上の <w> に分かれることがあるので、
                # 戻した字（<supplied>）の並びと確度を、restored_letters.tsv の語の ⲍ・ⲯ の並びと比べる
                want = [(ch, cert) for word, cert in rest.get((unit, e['seq']), []) for ch in word if ch in 'ⲍⲯ']
                check(g[5] == want, f'{unit} n={g[0]}: 戻した字（<supplied>）が restored_letters.tsv と違う')
            else:
                check(g[4] == rest.get((unit, e['seq']), []), f'{unit} n={g[0]}: 復元の印が restored_letters.tsv と違う')

        # ---- 件数
        nseg = len(got)
        ntok = sum(1 for g in got for t in g[3] if t != GAP)
        ngap = sum(g[3].count(GAP) for g in got)
        if annotated_nlp:   # 戻した語の数は restored_letters.tsv の行の数（字の並びは上で確かめた）
            nrest = collections.Counter(cert for g in got for _, cert in rest.get((unit, g[0]), []))
        else:
            nrest = collections.Counter(cert for g in got for _, cert in g[4])
        meas = {m.get('unit'): int(m.get('quantity')) for m in root.iter(NS + 'measure')}
        check(meas == {'segment': nseg, 'token': ntok, 'gap': ngap}, f'{unit}: <extent> の件数が本文と違う {meas}')
        check(nseg == int(c['rows']) and (grouped or ntok == int(c['tokens'])) and ngap == int(c['gap_markers'])
              and sum(nrest.values()) == int(c['restored']), f'{unit}: 件数が catalog.tsv と違う')

        # ---- サイトの検索ページ・ビュワーと同じ読み方
        segs = [s for s in tx.iter(NS + 's') if s.get(XML + 'id')]
        forms = [''.join(w.itertext()).strip() for s in segs for w in s.iter(NS + 'w')]
        check(len(segs) == nseg and len(forms) == ntok and all(forms), f'{unit}: サイトの読み方で数えた件数が違う')
        check(len(list(tx.iter(NS + 'gap'))) == ngap, f'{unit}: <gap> の数が違う')

        tot.update(files=1, segments=nseg, tokens=ntok, gaps=ngap, high=nrest['high'], medium=nrest['medium'],
                   gap_line=sum(1 for g in tx.iter(NS + 'gap') if g.get('unit') == 'line'),
                   gap_page=sum(1 for g in tx.iter(NS + 'gap') if g.get('unit') == 'page'), bytes=len(raw))
        if grouped:
            tot.update(grouped=1, phr=sum(1 for _ in tx.iter(NS + 'phr')), split=split, joined=joined,
                       annotated=sum(1 for w in tx.iter(NS + 'w') if w.get('type') or w.get('lemma')),
                       morph=sum(1 for w in tx.iter(NS + 'w') if w.get('resp') in ANNOTATION_RESP),
                       nlp=sum(1 for w in tx.iter(NS + 'w') if w.get('resp') == '#coptic-nlp'),
                       supplied=sum(1 for _ in tx.iter(NS + 'supplied')))

    allrecs = sum(len(v) for v in recs.values())
    check(tot['segments'] == allrecs, f'セグメントの合計 {tot["segments"]} != nhc_all.tsv の {allrecs}')
    print(f'TEI files {tot["files"]}; segments {tot["segments"]}; tokens {tot["tokens"]}; '
          f'gaps {tot["gaps"]} (unit line {tot["gap_line"]}, page {tot["gap_page"]}, none {tot["gaps"] - tot["gap_line"] - tot["gap_page"]}); '
          f'restored words {tot["high"] + tot["medium"]} (cert high {tot["high"]}, medium {tot["medium"]}); '
          f'unique ids {len(seen)}; total size {tot["bytes"] / 1e6:.1f} MB')
    if tot['grouped']:
        print(f'files with bound groups (<phr>) {tot["grouped"]}: {tot["phr"]} bound groups; '
              f'word division against nhc_all.tsv: {tot["split"]} new divisions, {tot["joined"]} removed; '
              f'{tot["annotated"]} <w> with type/lemma ({tot["morph"]} carry the automatic annotation\'s resp/cert, '
              f'{tot["nlp"]} of them from the Coptic SCRIPTORIUM NLP); '
              f'{tot["supplied"]} restored letters in <supplied>')

    # ---- RELAX NG（任意）
    if rng:
        try:
            import lxml.etree as LE
        except ImportError:
            print('schema validation skipped: lxml is not installed')
        else:
            schema = LE.RelaxNG(LE.parse(rng))
            bad = 0
            for c in cat:
                doc = LE.parse(os.path.join(dst, c['file'] + '.xml'))
                if not schema.validate(doc):
                    bad += 1
                    for e in list(schema.error_log)[:5]:
                        print(f'FAIL: {c["unit"]}: schema: line {e.line}: {e.message}')
            check(bad == 0, f'{bad} files are not valid against {os.path.basename(rng)}')
            print(f'schema validation ({os.path.basename(rng)}): {len(cat) - bad} of {len(cat)} files valid')
    print('RESULT:', 'ALL CHECKS PASSED' if ok else 'FAILED')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
