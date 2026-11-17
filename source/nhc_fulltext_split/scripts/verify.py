#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py <Nag_Hammadi.txt> <出力フォルダ>

build.py の出力を、元ファイルと突き合わせて検証する。
  1. 保存則: 元の全トークンが「出力された / [...] に置換された / 削除された」のどれか 1 つにだけ当たること。
     出力 + changes.tsv から元の各行を完全に復元できること
     （ⲯ→ⲝ と、changes.tsv に記録された ⲍ・ⲯ の挿入以外は 1 字も変わっていないこと）。
     さらに build.py の読み込み処理を使わずに元ファイルを読み直し、出力 + changes.tsv から組み立てた
     文字列が元ファイルのコプト文字列と完全に一致することを確かめる（raw stream check）。
  2. ⲍ・ⲯ の復元: 出力にある ⲍ・ⲯ はすべて changes.tsv（letter_restored）に記録があること。
     記録された語から挿入字を除くと元ファイルの文字列に戻ること。restored_letters.tsv が記録と一致すること。
  3. 出力の体裁: UTF-8 / LF / 余分な空白なし / ϧ・ラテン文字・注記残骸が残っていないこと。
  4. 文書別ファイル・nhc_all.tsv・txt・catalog.tsv が互いに一致していること。
"""
import sys, os, re, csv, collections, importlib.util

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('build', os.path.join(here, 'build.py'))
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
GAP = B.GAP

def parse_span(s, n):
    if s == 'all':
        return 0, n
    a, b = s.split('-'); return int(a), int(b)

# ⲍ・ⲯ 以外の字も補った箇所（restore.py の SPECIAL）: (行ID, 元の語形) → 戻した語形
EXTRA_OK = {(sid.split(':')[1], d): restored for d, restored, conf, sid, note in B.restore.SPECIAL}

def only_inserts(orig, new, allowed='ⲍⲯ'):
    """new が orig に allowed の字を挿入しただけのものなら、挿入した字（順に）を返す。そうでなければ None"""
    ins, j = [], 0
    for ch in new:
        if j < len(orig) and ch == orig[j]:
            j += 1
        elif ch in allowed:
            ins.append(ch)
        else:
            return None
    return ''.join(ins) if j == len(orig) else None

def raw_stream(src):
    """build.py を使わずに元ファイルを読み、見出し行と行頭の ID を除いたコプト文字だけを順につないだ文字列を返す。"""
    raw = open(src, 'rb').read().decode('utf-8').lstrip('\ufeff')
    parts = []
    for l in re.split(r'\r\n|\r|\n', raw):
        if re.search(r'[A-Za-z]', l):
            continue
        parts.append(re.sub(r'\s+', '', re.sub(r'^\d+\t', '', l)))
    return ''.join(parts)

def main(src, out):
    ok = True
    def check(cond, msg):
        nonlocal ok
        if not cond:
            ok = False; print('FAIL:', msg)

    rows, headers = B.load_rows(src)
    byid = {r.id: r for r in rows}
    n_tok = sum(len(r.toks) for r in rows)
    # build.py と同じ条件: ソースに ⲝ がなければ ⲯ→ⲝ が行われている
    fix_psi = not any('ⲝ' in t for r in rows for t in r.toks)
    fwd = (lambda t: t.replace('ⲯ', 'ⲝ')) if fix_psi else (lambda t: t)
    back = (lambda t: t.replace('ⲝ', 'ⲯ')) if fix_psi else (lambda t: t)

    # ---- changes.tsv
    removed = collections.defaultdict(dict)      # row id -> {tok index: type}
    with open(os.path.join(out, 'changes.tsv'), encoding='utf-8', newline='') as f:
        rd = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE); next(rd)
        changes = list(rd)
    restored = collections.defaultdict(dict)     # row id -> {開始トークン番号: (終了, 元のトークン列, 置換後の 1 トークン)}
    in_restored = collections.defaultdict(set)
    n_rest = n_z = n_p = n_join = 0
    for typ, unit, sid, span, orig, repl, why in changes:
        if typ in ('header_removed', 'row_rejoined'):
            continue
        r = byid[sid]; a, b = parse_span(span, len(r.toks))
        check(' '.join(r.toks[a:b]) == orig, f'changes.tsv {sid} {span}: logged text differs from source')
        if typ == 'letter_restored':
            base = fwd(''.join(r.toks[a:b]))
            ins = only_inserts(base, repl)
            if ins is None and EXTRA_OK.get((sid, base)) == repl:
                ins = only_inserts(base, repl, allowed='ⲍⲯⲩ')
            check(bool(ins), f'changes.tsv {sid} {span}: {repl} is not {base} plus inserted ⲍ/ⲯ')
            check(' ' not in repl and repl != '', f'changes.tsv {sid} {span}: bad replacement')
            for i in range(a, b):
                check(i not in removed[sid] and i not in in_restored[sid], f'changes.tsv {sid}: token {i} logged twice')
                in_restored[sid].add(i)
            restored[sid][a] = (b, r.toks[a:b], repl)
            n_rest += 1; n_join += b - a - 1; n_z += (ins or '').count('ⲍ'); n_p += (ins or '').count('ⲯ')
            continue
        for i in range(a, b):
            check(i not in removed[sid] and i not in in_restored[sid], f'changes.tsv {sid}: token {i} logged twice')
            removed[sid][i] = typ
    if not fix_psi or any('ⲍ' in t for r in rows for t in r.toks):
        check(n_rest == 0, 'letters were restored although the source already contains ⲍ or ⲝ')

    # ---- nhc_all.tsv
    raw = open(os.path.join(out, 'nhc_all.tsv'), 'rb').read()
    check(b'\r' not in raw, 'nhc_all.tsv contains CR')
    txt = raw.decode('utf-8')
    recs = [l.split('\t') for l in txt.split('\n')[1:] if l]
    check(all(len(r) == 6 for r in recs), 'nhc_all.tsv: wrong column count')

    covered = collections.defaultdict(list)       # row id -> [(a, b, unit, kind, toks)]
    order = []
    for unit, seq, kind, sid, span, text in recs:
        r = byid[sid]; a, b = parse_span(span, len(r.toks))
        covered[sid].append((a, b, unit, kind, text.split(' ')))
        order.append((int(sid), a))
        check(text == text.strip() and '  ' not in text and text != '', f'{unit} seq {seq}: whitespace problem')
        check(kind in ('title', 'text', 'subscript', 'colophon', 'fragment'), f'{unit} seq {seq}: bad kind {kind}')
    check(order == sorted(order), 'output records are not in source order')

    n_out = n_gap = n_drop = n_xi = 0
    for r in rows:
        spans = covered.get(r.id, [])
        pos = 0
        rm = removed.get(r.id, {})
        for a, b, unit, kind, toks in spans:
            # 出力レコード間のすき間は、すべて削除済みトークンでなければならない
            for i in range(pos, a):
                check(rm.get(i) in ('removed', 'duplicate_removed', 'note_to_gap'), f'{r.id}: token {i} ({r.toks[i]}) lost between records')
            exp, i, rs = [], a, restored.get(r.id, {})
            while i < b:
                t = rm.get(i)
                if i in rs:                                   # 復元された語（元の 1 個以上のトークン → 1 トークン）
                    e, orig_toks, repl = rs[i]
                    check(e <= b, f'{r.id}: restored word {repl} crosses a record boundary')
                    exp.append(repl); n_out += e - i
                    n_xi += sum(x.count('ⲯ') for x in orig_toks) if fix_psi else 0
                    i = e; continue
                if t is None:
                    exp.append(fwd(r.toks[i])); n_out += 1; n_xi += r.toks[i].count('ⲯ') if fix_psi else 0
                elif t == 'note_to_gap':
                    if not (exp and exp[-1] == GAP):
                        exp.append(GAP)
                i += 1
            check(exp == toks, f'{r.id} {a}-{b}: output differs from source\n   exp {exp[:12]}\n   got {toks[:12]}')
            pos = b
        for i in range(pos, len(r.toks)):
            check(rm.get(i) in ('removed', 'duplicate_removed', 'note_to_gap'), f'{r.id}: trailing token {i} ({r.toks[i]}) lost')
        n_gap += sum(1 for v in rm.values() if v == 'note_to_gap')
        n_drop += sum(1 for v in rm.values() if v in ('removed', 'duplicate_removed'))
    check(n_out + n_gap + n_drop == n_tok, f'conservation: {n_out}+{n_gap}+{n_drop} != {n_tok}')

    # ---- raw stream check（読み込み処理に依存しない照合）
    rebuilt = []
    for r in rows:
        rm = removed.get(r.id, {}); toks = {}
        for a, b, unit, kind, out_toks in covered.get(r.id, []):
            i, rs = a, restored.get(r.id, {})
            for t in out_toks:
                if t == GAP:
                    continue
                while i in rm:
                    i += 1
                if i in rs:                                   # 復元された語は、記録にある元のトークン列に戻す
                    e, orig_toks, repl = rs[i]
                    if t != repl:
                        check(False, f'{r.id}: token {i}: {t} is not the logged restoration {repl}')
                    for q, o in enumerate(orig_toks):
                        toks[i + q] = o
                    i = e
                else:
                    toks[i] = back(t); i += 1
        for typ, unit, sid, span, orig, repl, why in changes:
            if sid == r.id and typ in ('note_to_gap', 'removed', 'duplicate_removed'):
                a = int(span.split('-')[0])
                for k, t in enumerate(orig.split(' ')):
                    toks[a + k] = t
        idx = sorted(toks)
        check(idx == list(range(len(idx))), f'{r.id}: rebuilt token indices are not contiguous')
        rebuilt.append(''.join(toks[i] for i in idx))
    stream = raw_stream(src)
    same_stream = ''.join(rebuilt) == stream
    check(same_stream, 'raw stream check: rebuilt text differs from the source file')

    # ---- 出力に残っていてはいけないもの
    body = '\n'.join(r[5] for r in recs)
    check('ϧ' not in body, f'ϧ remains in output ({body.count("ϧ")})')
    if fix_psi:                                               # ⲍ・ⲯ は記録された復元箇所にだけあること
        logged = [x[2] for d in restored.values() for x in d.values()]
        for ch in 'ⲍⲯ':
            check(body.count(ch) == sum(x.count(ch) for x in logged),
                  f'{ch} in output: {body.count(ch)}, in logged restorations: {sum(x.count(ch) for x in logged)}')
    # restored_letters.tsv は changes.tsv の letter_restored と 1 対 1 に対応すること
    rl_path = os.path.join(out, 'restored_letters.tsv')
    if os.path.exists(rl_path):
        with open(rl_path, encoding='utf-8', newline='') as f:
            rl = list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
        a_ = sorted((x['unit'], x['src_id'], x['src_tok'], x['source'], x['restored']) for x in rl)
        b_ = sorted((c[1], c[2], c[3], c[4], c[5]) for c in changes if c[0] == 'letter_restored')
        check(a_ == b_, 'restored_letters.tsv does not match the letter_restored entries of changes.tsv')
        seqtext = {(r_[0], r_[1]): r_[5].split(' ') for r_ in recs}
        for x in rl:
            check(x['restored'] in seqtext.get((x['unit'], x['seq']), []), f"restored_letters.tsv: {x['restored']} not in {x['unit']} seq {x['seq']}")
            check(x['confidence'] in ('A', 'B'), 'restored_letters.tsv: bad confidence')
    else:
        check(n_rest == 0, 'restored_letters.tsv is missing')
    check(not re.search(r'[A-Za-z0-9]', body), 'Latin letters / digits remain in output')
    allowed = set(' \n[].') | {chr(c) for c in range(0x2C80, 0x2CB2)} | set('ϣϥϩϫϭϯ')
    extra = collections.Counter(c for c in body if c not in allowed)
    check(not extra, f'unexpected characters in output: {dict(extra)}')
    left = [t for t in body.split() if t in B.RESIDUE_TOKENS]
    check(not left, f'note residue tokens remain: {collections.Counter(left)}')
    check(body.replace(GAP, '').count('[') == 0 and body.replace(GAP, '').count('.') == 0, 'stray bracket/dot')
    check(f'{GAP} {GAP}' not in body, 'adjacent gap markers not merged')

    # ---- 文書別ファイルとの一致
    with open(os.path.join(out, 'catalog.tsv'), encoding='utf-8', newline='') as f:
        cat = list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
    per_unit = collections.defaultdict(list)
    for rec in recs:
        per_unit[rec[0]].append(rec)
    check([c['unit'] for c in cat] == list(per_unit.keys()), 'catalog order differs from nhc_all.tsv')
    seen_files = set()
    for c in cat:
        u = c['unit']; fn = c['file']; seen_files.add(fn)
        t = open(os.path.join(out, 'tsv', fn + '.tsv'), 'rb').read()
        check(b'\r' not in t, f'{fn}.tsv contains CR')
        lines = t.decode('utf-8').split('\n')
        check(lines[0] == 'seq\tkind\tsrc_id\tsrc_tok\ttext' and lines[-1] == '', f'{fn}.tsv header/trailing newline')
        mine = [l.split('\t') for l in lines[1:-1]]
        check(mine == [r[1:] for r in per_unit[u]], f'{fn}.tsv differs from nhc_all.tsv')
        check([m[0] for m in mine] == [str(i) for i in range(1, len(mine) + 1)], f'{fn}.tsv seq not 1..n')
        x = open(os.path.join(out, 'txt', fn + '.txt'), 'rb').read().decode('utf-8')
        check(x == ''.join(m[4] + '\n' for m in mine), f'{fn}.txt differs from tsv')
        check(int(c['rows']) == len(mine), f'{u}: catalog rows')
        check(int(c['tokens']) == sum(1 for m in mine for tk in m[4].split(' ') if tk != GAP), f'{u}: catalog tokens')
        check(int(c['gap_markers']) == sum(m[4].split(' ').count(GAP) for m in mine), f'{u}: catalog gaps')
        check(c['src_id_first'] == mine[0][2] and c['src_id_last'] == mine[-1][2], f'{u}: catalog src ids')
        check(int(c['restored']) == sum(1 for ch in changes if ch[0] == 'letter_restored' and ch[1] == u), f'{u}: catalog restored')
    check({f[:-4] for f in os.listdir(os.path.join(out, 'tsv'))} == seen_files, 'tsv/ has unexpected files')
    check({f[:-4] for f in os.listdir(os.path.join(out, 'txt'))} == seen_files, 'txt/ has unexpected files')

    src_psi = sum(t.count('ⲯ') for r in rows for t in r.toks)
    src_xi = sum(t.count('ⲝ') for r in rows for t in r.toks)
    print(f'source rows {len(rows)}, tokens {n_tok}; output records {len(recs)}, units {len(cat)}')
    print(f'tokens: kept {n_out} + replaced by {GAP} {n_gap} + removed {n_drop} = {n_out + n_gap + n_drop}')
    n_out_tok = sum(1 for r_ in recs for tk in r_[5].split(' ') if tk != GAP)
    check(n_out_tok == n_out - n_join, f'output tokens {n_out_tok} != kept {n_out} - joined {n_join}')
    print(f'restored words {n_rest} (ⲍ {n_z}, ⲯ {n_p}); split tokens joined: {n_join} fewer; output tokens {n_out_tok}')
    print(f'source ⲯ {src_psi} (ⲝ {src_xi}); ⲯ→ⲝ applied: {fix_psi}; converted in output {n_xi}; output ⲝ {body.count("ⲝ")}')
    print(f'gap markers in output {body.count(GAP)}; headers removed {len(headers)}')
    print(f'raw stream check: {len(stream)} Coptic characters in the source file, rebuilt identical = {same_stream}')
    print('RESULT:', 'ALL CHECKS PASSED' if ok else 'FAILED')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
