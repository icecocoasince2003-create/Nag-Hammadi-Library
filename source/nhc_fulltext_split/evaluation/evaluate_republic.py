#!/usr/bin/env python3
"""項目 13: 自動注釈の精度を、参考から外した本文（NHC VI,5『国家』）で測る。

One command, deterministic (the same files on every run with the same inputs):

  python3 source/nhc_fulltext_split/evaluation/evaluate_republic.py

It needs lxml and scikit-learn, because it runs the two annotation scripts (with the
same Python interpreter, as subprocesses, PYTHONHASHSEED=0):

 1. Held-out run: tei/06-5_plato-republic.xml (unannotated) is copied into an empty
    temporary folder and annotated with
      annotation/bound_group_converter.py --ref data/eugnostos_tei.xml
      annotation/annotate_tei.py ... --ref data/eugnostos_tei.xml
    so the scripts never read data/republic_tei.xml (the reference folder they are
    given holds no reference at all; without --ref they would fail).
 2. The result is compared with the hand annotation data/republic_tei.xml.
    Every morpheme (<w>) of both versions is mapped to its letters (evalcommon.letters:
    NFD, bracketed parts dropped, letters only, lowercased), the two letter strings of
    the whole text are aligned with difflib (autojunk off), and a morpheme is
    "boundary-matched" when the hand-annotated and the automatic morpheme cover exactly
    the same aligned letters. POS (@type) and lemma (@lemma) are compared only on
    boundary-matched morphemes whose hand POS is not X or UNKNOWN; an automatic X counts
    as wrong. Rates have 95% Wilson intervals.
 3. For contrast only, the same comparison is made for a run with both references
    (the setting of the published drafts, in which the Republic is part of the
    reference and the answers have been seen).

Results (next to this script, overwritten on each run):
  republic_summary.md         the tables in Japanese, with the caveats
  republic_metrics.tsv        every rate with n, k and the 95% interval
  republic_pos_confusion.tsv  hand POS (rows) x automatic POS (columns), matched morphemes
  republic_tokens.tsv         one row per hand-annotated morpheme, with its automatic match

Options: --workdir DIR keeps the intermediate files (DIR must be empty or new);
--outdir DIR writes the results elsewhere.
"""
import argparse
import difflib
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
import evalcommon as ec  # noqa: E402  (same folder)

HERE = Path(__file__).resolve().parent
NHC = HERE.parent                      # source/nhc_fulltext_split
REPO = NHC.parent.parent
SRC = NHC / 'tei' / '06-5_plato-republic.xml'
GOLD = REPO / 'data' / 'republic_tei.xml'
EUG = REPO / 'data' / 'eugnostos_tei.xml'
CONV = NHC / 'annotation' / 'bound_group_converter.py'
ANNOT = NHC / 'annotation' / 'annotate_tei.py'
POS_NAMES_FILE = REPO / 'scripts' / 'build_site.py'

NO_GOLD_POS = ('X', 'UNKNOWN')         # the hand annotation gives no POS
CERTS = ('high', 'medium', 'low')


# ---------------------------------------------------------------- pipeline

def run(cmd, cwd):
    env = dict(os.environ, PYTHONHASHSEED='0')
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if r.returncode:
        sys.exit('failed (%d): %s\n%s' % (r.returncode, ' '.join(map(str, cmd)), r.stdout))
    return r.stdout


def annotate(work, refs):
    """Annotate a copy of tei/06-5 in an empty folder with only the given references."""
    work.mkdir(parents=True)
    inp = work / 'input'
    inp.mkdir()
    shutil.copyfile(str(SRC), str(inp / SRC.name))
    reflist = []
    for r in refs:
        reflist += ['--ref', r]
    run([sys.executable, CONV, '--input-dir', inp, '--output-dir', work / 'groups'] + reflist, work)
    # ROOT_DIR is the work folder, which holds no reference: only --ref is read.
    run([sys.executable, ANNOT, work / 'groups', work / 'annotated' / 'xml', work] + reflist, work)
    return work / 'annotated' / 'xml' / SRC.name


# ---------------------------------------------------------------- reading

class Morph:
    __slots__ = ('i', 'seg', 's_n', 'w_pos', 'phr', 'form', 'let', 'start', 'end',
                 'type', 'lemma', 'cert', 'resp', 'grc')


class Doc:
    def __init__(self, path):
        self.path = path
        _, body = ec.body_of(path)
        self.morphs, self.groups, self.segs = [], [], []
        parts, pos = [], 0
        for s, ws, phr_of, _items in ec.segments(body):
            s0 = pos
            seg_morphs = []
            for k, w in enumerate(ws, 1):
                m = Morph()
                m.i = len(self.morphs)
                m.seg = s.get(ec.XML + 'id') or ''
                m.s_n = s.get('n') or ''
                m.w_pos = k
                m.phr = phr_of.get(w, 0)
                m.form = ec.w_text(w)
                m.let = ec.letters(m.form)
                m.start = pos
                pos += len(m.let)
                m.end = pos
                m.type = w.get('type') or ''
                m.lemma = w.get('lemma') or ''
                m.cert = w.get('cert') or ''
                m.resp = w.get('resp') or ''
                m.grc = 'grc' if w.get(ec.XML + 'lang') == 'grc' else ''
                parts.append(m.let)
                self.morphs.append(m)
                seg_morphs.append(m)
            byphr = defaultdict(list)
            for m in seg_morphs:
                if m.phr and m.end > m.start:
                    byphr[m.phr].append(m)
            for k in sorted(byphr):
                self.groups.append((byphr[k][0].start, byphr[k][-1].end))
            self.segs.append((s.get(ec.XML + 'id') or '', s.get('n') or '', s0, pos))
        self.text = ''.join(parts)
        self.owner = [None] * len(self.text)
        for m in self.morphs:
            for j in range(m.start, m.end):
                self.owner[j] = m
        self.seg_starts = {a for _, _, a, _ in self.segs}

    def seg_at(self, pos):
        for sid, n, a, b in self.segs:
            if a <= pos < b:
                return sid
        return self.segs[-1][0] if self.segs else ''


# ---------------------------------------------------------------- comparison

def rate(k, n):
    lo, hi = ec.wilson(k, n)
    return {'k': k, 'n': n, 'p': (k / n if n else float('nan')), 'lo': lo, 'hi': hi}


def prf(tp, n_auto, n_gold):
    p, r = rate(tp, n_auto), rate(tp, n_gold)
    f = (2 * p['p'] * r['p'] / (p['p'] + r['p'])) if n_auto and n_gold and (p['p'] + r['p']) else float('nan')
    return p, r, f


def map_span(start, end, g2a):
    """The span in the automatic text covered by gold letters start..end, if they are all
    aligned and contiguous there; else None."""
    if end <= start:
        return None
    js = g2a[start:end]
    if -1 in js or js[-1] - js[0] != end - start - 1:
        return None
    return (js[0], js[-1] + 1)


def boundary_counts(gold_units, auto_units, gold, auto, g2a):
    """Boundaries between adjacent letters inside segments, at positions where both
    letters are aligned and adjacent in both texts. Segment starts are left out (they
    come from the input and are the same in both)."""
    bg = {s for s, e in gold_units}
    ba = {s for s, e in auto_units}
    tp = fp = fn = comparable = 0
    for p in range(1, len(gold.text)):
        a0, a1 = g2a[p - 1], g2a[p]
        if a0 < 0 or a1 != a0 + 1 or p in gold.seg_starts or a1 in auto.seg_starts:
            continue
        comparable += 1
        ig, ia = p in bg, a1 in ba
        tp += ig and ia
        fn += ig and not ia
        fp += ia and not ig
    return tp, fp, fn, comparable


def compare(gold, auto):
    sm = difflib.SequenceMatcher(None, gold.text, auto.text, autojunk=False)
    ops = sm.get_opcodes()
    g2a = [-1] * len(gold.text)
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'equal':
            for d in range(i2 - i1):
                g2a[i1 + d] = j1 + d
    aligned = sum(1 for j in g2a if j >= 0)
    auto_by_span = {(m.start, m.end): m for m in auto.morphs if m.end > m.start}
    match = {}
    for g in gold.morphs:
        sp = map_span(g.start, g.end, g2a)
        if sp in auto_by_span:
            match[g.i] = auto_by_span[sp]
    auto_groups = set(auto.groups)
    group_tp = sum(1 for s, e in gold.groups if map_span(s, e, g2a) in auto_groups)
    gold_units = [(m.start, m.end) for m in gold.morphs if m.end > m.start]
    auto_units = [(m.start, m.end) for m in auto.morphs if m.end > m.start]
    return {
        'ops': ops, 'g2a': g2a, 'aligned': aligned, 'match': match,
        'morph_span': prf(len(match), len(auto_units), len(gold_units)),
        'group_span': prf(group_tp, len(auto.groups), len(gold.groups)),
        'morph_pos': boundary_counts(gold_units, auto_units, gold, auto, g2a),
        'group_pos': boundary_counts(gold.groups, auto.groups, gold, auto, g2a),
        'gold_units': len(gold_units), 'auto_units': len(auto_units),
    }


def score(gold, auto, cmp):
    match = cmp['match']
    scored, excluded = [], Counter()
    for g in gold.morphs:
        a = match.get(g.i)
        if a is None:
            continue
        if g.type in NO_GOLD_POS:
            excluded[g.type] += 1
            continue
        scored.append((g, a))

    def block(pairs):
        n = len(pairs)
        pos_ok = sum(1 for g, a in pairs if a.type == g.type)
        nonx = [(g, a) for g, a in pairs if a.type != 'X']
        return {
            'n': n,
            'pos': rate(pos_ok, n),
            'pos_nonx': rate(sum(1 for g, a in nonx if a.type == g.type), len(nonx)),
            'coverage': rate(len(nonx), n),
            'lemma': rate(sum(1 for g, a in pairs if a.lemma == g.lemma), n),
            'lemma_norm': rate(sum(1 for g, a in pairs
                                   if a.lemma and ec.strip_marks(a.lemma) == ec.strip_marks(g.lemma)), n),
            'x_share': rate(n - len(nonx), n),
        }

    res = {'all': block(scored), 'excluded': excluded, 'scored': scored, 'cert': {}}
    matched_auto = set(id(a) for a in match.values())
    for c in CERTS:
        autos = [a for a in auto.morphs if a.cert == c and a.end > a.start]
        res['cert'][c] = dict(block([(g, a) for g, a in scored if a.cert == c]),
                              auto=len(autos),
                              auto_matched=rate(sum(1 for a in autos if id(a) in matched_auto), len(autos)))
    real_gold = [g for g in gold.morphs if g.type not in NO_GOLD_POS and g.end > g.start]
    res['end_to_end'] = rate(sum(1 for g in real_gold
                                 if g.i in match and match[g.i].type == g.type), len(real_gold))
    return res


# ---------------------------------------------------------------- formatting

def num(x):
    return format(x, ',d')


def pct(r):
    if not r['n']:
        return '—'
    return '%.1f%%' % (100 * r['p'])


def ci(r):
    if not r['n']:
        return '—'
    return '%.1f–%.1f%%' % (100 * r['lo'], 100 * r['hi'])


def f4(x):
    return '' if x != x else '%.4f' % x


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(REPO).as_posix()


def versions():
    out = ['Python %s' % platform.python_version()]
    try:
        from importlib import metadata
        for dist in ('lxml', 'scikit-learn', 'scipy', 'numpy'):
            try:
                out.append('%s %s' % (dist, metadata.version(dist)))
            except Exception:
                out.append('%s ?' % dist)
    except ImportError:
        pass
    return ', '.join(out)


def site_pos_codes():
    """The POS codes known to the site (POS_NAMES in scripts/build_site.py), for flagging
    hand-annotation tags outside that list. Read as text, the script is not run."""
    import ast
    try:
        src = POS_NAMES_FILE.read_text(encoding='utf-8')
        m = re.search(r'^POS_NAMES = (\{.*?^\})', src, re.S | re.M)
        return set(ast.literal_eval(m.group(1)))
    except Exception:
        return set()


def tag_dist(morphs, attr='type'):
    d = defaultdict(Counter)
    for m in morphs:
        d[m.let][getattr(m, attr)] += 1
    return d


def majority(c):
    return sorted(c.items(), key=lambda x: (-x[1], x[0]))[0][0]


def differing_forms(eug, gold, attr, min_n=3):
    """Forms (letters) found at least min_n times in both hand-annotated texts whose most
    frequent POS (attr='type') or lemma (attr='lemma') differs between them."""
    de, dg = tag_dist(eug.morphs, attr), tag_dist(gold.morphs, attr)
    out = []
    for f in sorted(set(de) & set(dg)):
        if f and sum(de[f].values()) >= min_n and sum(dg[f].values()) >= min_n and majority(de[f]) != majority(dg[f]):
            out.append(f)
    return out


def fmt_dist(c):
    return ' '.join('%s:%d' % (t, n) for t, n in sorted(c.items(), key=lambda x: (-x[1], x[0])))


# ---------------------------------------------------------------- writing

def write_tsv(path, header, rows):
    with open(str(path), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\t'.join(header) + '\n')
        for r in rows:
            f.write('\t'.join(str(x).replace('\t', ' ').replace('\n', ' ') for x in r) + '\n')


def metric_rows(label, r, note=''):
    return [label, r['n'], r['k'], f4(r['p']), f4(r['lo']), f4(r['hi']), note]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--workdir', type=Path, help='keep the intermediate files here (empty or new folder)')
    ap.add_argument('--outdir', type=Path, default=HERE, help='where to write the results (default: this folder)')
    args = ap.parse_args()
    for p in (SRC, GOLD, EUG, CONV, ANNOT):
        if not p.is_file():
            sys.exit('missing: %s' % p)

    tmp = None
    if args.workdir:
        work = args.workdir.resolve()
        if work.exists() and any(work.iterdir()):
            sys.exit('--workdir must be empty: %s' % work)
    else:
        tmp = tempfile.TemporaryDirectory(prefix='eval13-')
        work = Path(tmp.name)
    try:
        held = annotate(work / 'heldout', [EUG])
        seen = annotate(work / 'seen', [EUG, GOLD])
        gold = Doc(GOLD)
        auto, auto_seen = Doc(held), Doc(seen)
        for d in (auto, auto_seen):
            if any(m.resp == '#morph-reference' for m in d.morphs):
                sys.exit('unexpected #morph-reference in %s' % d.path)
        cmp_h, cmp_s = compare(gold, auto), compare(gold, auto_seen)
        res_h, res_s = score(gold, auto, cmp_h), score(gold, auto_seen, cmp_s)
        out = args.outdir
        out.mkdir(parents=True, exist_ok=True)
        write_results(out, gold, auto, cmp_h, res_h, cmp_s, res_s)
    finally:
        if tmp:
            tmp.cleanup()
    print('wrote', ', '.join(str(out / n) for n in (
        'republic_summary.md', 'republic_metrics.tsv', 'republic_pos_confusion.tsv', 'republic_tokens.tsv')))
    a = res_h['all']
    print('held-out: POS %s (n=%d), lemma %s; morpheme boundary F1 %.3f' % (
        pct(a['pos']), a['n'], pct(a['lemma']), cmp_h['morph_span'][2]))


def write_results(out, gold, auto, cmp, res, cmp_s, res_s):
    match = cmp['match']
    pos_codes = site_pos_codes()
    gold_dist = tag_dist(gold.morphs)
    eug = Doc(EUG)
    eug_dist = tag_dist(eug.morphs)

    # ---- confusion matrix (all boundary-matched morphemes, also gold X/UNKNOWN)
    conf = Counter()
    for g in gold.morphs:
        if g.i in match:
            conf[(g.type, match[g.i].type)] += 1
    rows_tot, cols_tot = Counter(), Counter()
    for (gt, at), n in conf.items():
        rows_tot[gt] += n
        cols_tot[at] += n
    order = sorted(set(rows_tot) | set(cols_tot), key=lambda t: (-(rows_tot[t] + cols_tot[t]), t))
    rows = [r for r in order if rows_tot[r]]
    cols = [c for c in order if cols_tot[c]]
    write_tsv(out / 'republic_pos_confusion.tsv', ['gold\\auto'] + cols + ['total'],
              [[r] + [conf[(r, c)] or '' for c in cols] + [rows_tot[r]] for r in rows]
              + [['total'] + [cols_tot[c] for c in cols] + [sum(cols_tot.values())]])

    # ---- tokens
    trows = []
    for g in gold.morphs:
        a = match.get(g.i)
        if a is not None:
            af, at, al, ac, ar, ag = a.form, a.type, a.lemma, a.cert, a.resp, a.grc
            aseg, apos, aphr = a.seg, a.w_pos, a.phr
        else:
            over = []
            for j in cmp['g2a'][g.start:g.end]:
                if j >= 0 and auto.owner[j] is not None and auto.owner[j] not in over:
                    over.append(auto.owner[j])
            af = '+'.join(m.form for m in over)
            at = '+'.join(m.type for m in over)
            al = '+'.join(m.lemma for m in over)
            ac = '+'.join(m.cert for m in over)
            ar = ''
            ag = ''
            aseg = over[0].seg if over else ''
            apos = '+'.join(str(m.w_pos) for m in over)
            aphr = '+'.join(str(m.phr) for m in over)
        scored = a is not None and g.type not in NO_GOLD_POS
        trows.append([g.seg, g.s_n, g.w_pos, g.phr, g.form, g.type, g.lemma, g.grc,
                      'yes' if a is not None else 'no', aseg, apos, aphr, af, at, al, ac, ar, ag,
                      'yes' if scored else 'no',
                      ('yes' if at == g.type else 'no') if scored else '',
                      ('yes' if al == g.lemma else 'no') if scored else '',
                      ('yes' if al and ec.strip_marks(al) == ec.strip_marks(g.lemma) else 'no') if scored else '',
                      fmt_dist(gold_dist[g.let])])
    write_tsv(out / 'republic_tokens.tsv',
              ['gold_seg', 'gold_s_n', 'gold_w_pos', 'gold_phr', 'gold_form', 'gold_type', 'gold_lemma', 'gold_grc',
               'boundary_match', 'auto_seg', 'auto_w_pos', 'auto_phr', 'auto_form', 'auto_type', 'auto_lemma',
               'auto_cert', 'auto_resp', 'auto_grc', 'scored', 'pos_ok', 'lemma_ok', 'lemma_norm_ok',
               'gold_types_of_this_form'], trows)

    # ---- metrics
    a = res['all']
    mrows = []
    mp, mr, mf = cmp['morph_span']
    gp, gr, gf = cmp['group_span']
    mrows.append(['text_aligned_gold_letters', len(gold.text), cmp['aligned'],
                  f4(cmp['aligned'] / len(gold.text)), '', '', 'letters of the hand-annotated text that align'])
    mrows.append(['text_aligned_auto_letters', len(auto.text), cmp['aligned'],
                  f4(cmp['aligned'] / len(auto.text)), '', '', 'letters of the automatic text that align'])
    mrows.append(metric_rows('morpheme_span_precision', mp, 'boundary-matched / automatic morphemes'))
    mrows.append(metric_rows('morpheme_span_recall', mr, 'boundary-matched / hand morphemes'))
    mrows.append(['morpheme_span_f1', '', '', f4(mf), '', '', ''])
    tp, fp, fn, comp = cmp['morph_pos']
    bp, br, bf = prf(tp, tp + fp, tp + fn)
    mrows.append(metric_rows('morpheme_boundary_position_precision', bp, '%d comparable positions' % comp))
    mrows.append(metric_rows('morpheme_boundary_position_recall', br, ''))
    mrows.append(['morpheme_boundary_position_f1', '', '', f4(bf), '', '', ''])
    mrows.append(metric_rows('bound_group_span_precision', gp, '<phr> with letters'))
    mrows.append(metric_rows('bound_group_span_recall', gr, ''))
    mrows.append(['bound_group_span_f1', '', '', f4(gf), '', '', ''])
    tp, fp, fn, comp = cmp['group_pos']
    qp, qr, qf = prf(tp, tp + fp, tp + fn)
    mrows.append(metric_rows('bound_group_boundary_position_precision', qp, '%d comparable positions' % comp))
    mrows.append(metric_rows('bound_group_boundary_position_recall', qr, ''))
    mrows.append(['bound_group_boundary_position_f1', '', '', f4(qf), '', '', ''])
    mrows.append(metric_rows('pos_accuracy', a['pos'], 'boundary-matched, hand POS not X/UNKNOWN; auto X = wrong'))
    mrows.append(metric_rows('pos_accuracy_auto_nonX', a['pos_nonx'], 'same, automatic POS not X'))
    mrows.append(metric_rows('pos_coverage_auto_nonX', a['coverage'], 'share of scored morphemes with automatic POS not X'))
    mrows.append(metric_rows('lemma_accuracy_exact', a['lemma'], 'exact string match; no automatic lemma = wrong'))
    mrows.append(metric_rows('lemma_accuracy_normalised', a['lemma_norm'], 'combining marks removed (NFD, Mn/Me, NFC)'))
    mrows.append(metric_rows('pos_correct_and_boundary_matched_of_all_hand', res['end_to_end'],
                             'all hand morphemes with POS not X/UNKNOWN'))
    for c in CERTS:
        b = res['cert'][c]
        mrows.append(metric_rows('cert_%s_boundary_matched' % c, b['auto_matched'], 'automatic morphemes with this @cert'))
        mrows.append(metric_rows('cert_%s_pos_accuracy' % c, b['pos']))
        mrows.append(metric_rows('cert_%s_pos_accuracy_auto_nonX' % c, b['pos_nonx']))
        mrows.append(metric_rows('cert_%s_lemma_accuracy_exact' % c, b['lemma']))
        mrows.append(metric_rows('cert_%s_lemma_accuracy_normalised' % c, b['lemma_norm']))
    s = res_s['all']
    mrows.append(metric_rows('seen_pos_accuracy', s['pos'], 'NOT held out: Republic among the references'))
    mrows.append(metric_rows('seen_lemma_accuracy_exact', s['lemma'], 'NOT held out'))
    mrows.append(metric_rows('seen_morpheme_span_recall', cmp_s['morph_span'][1], 'NOT held out'))
    mrows.append(['seen_morpheme_span_f1', '', '', f4(cmp_s['morph_span'][2]), '', '', 'NOT held out'])
    mrows.append(['seen_bound_group_span_f1', '', '', f4(cmp_s['group_span'][2]), '', '', 'NOT held out'])
    write_tsv(out / 'republic_metrics.tsv', ['metric', 'n', 'k', 'rate', 'ci95_low', 'ci95_high', 'note'], mrows)

    # ---- summary (Markdown, Japanese)
    L = []
    w = L.append
    nogold = res['excluded']
    diffs = [(t, i1, i2, j1, j2) for t, i1, i2, j1, j2 in cmp['ops'] if t != 'equal']
    w('# 自動注釈の精度 — NHC VI,5『国家』での検証（項目 13）')
    w('')
    w('`evaluate_republic.py` が書き出したファイル（手で直さない）。方法と使い方は `source/nhc_fulltext_split/README_ja.md` の §12。')
    w('')
    w('> **この数値の範囲。** 『国家』（VI,5。プラトン『国家』588b–589b のコプト語訳）は、約 730 語の、サヒド方言で書かれた哲学文書である。'
      'ここの数値はこの 1 文書についてのもので、ほかの文書、とくにリコポリス方言の写本 I・XI（と X）には、そのまま当てはまらない。'
      '語彙・文体・方言・元ファイルの語の切り方が違えば、正解率も変わる。39 文書全体の精度は、抜き取り表（`review_sample.tsv`）を人が確かめて見積もる。')
    w('')
    w('## 条件')
    w('')
    n_eug_w = len(eug.morphs)
    n_eug_phr_w = sum(1 for m in eug.morphs if m.phr)
    w('- 自動注釈は公開中の 39 文書と同じスクリプト（`annotation/bound_group_converter.py` → `annotation/annotate_tei.py`）で付けた。'
      '違いは、参考を `data/eugnostos_tei.xml`（III,3）だけにしたこと（`--ref`）。`data/republic_tei.xml` はスクリプトに読ませていない。')
    w('- 入力は未注釈の `tei/06-5_plato-republic.xml`（`<w>` %s）。比べる相手は人手の注釈 `data/republic_tei.xml`（`<w>` %s）。'
      % (num(sum(1 for _ in Doc(SRC).morphs)), num(len(gold.morphs))))
    n_gold_phr_w = sum(1 for m in gold.morphs if m.phr)
    w('- 公開中の 39 文書は、参考 2 件（III,3 と『国家』）で作られている。『国家』を外すと、語群の学習例は III,3 の冒頭 9 セグメント'
      '（語群のある `<w>` %s。公開版では『国家』の %s が加わる）だけになり、品詞・レンマの用例も III,3 の `<w>` %s だけになる'
      '（公開版では『国家』の %s が加わる）。つまりここの数値は、公開版より少ない参考で、見ていない本文に付けたときの精度である。' % (
          num(n_eug_phr_w), num(n_gold_phr_w), num(n_eug_w), num(len(gold.morphs))))
    w('- 注釈スクリプトの語彙表（約 165 語形）と文脈の規則、変換スクリプトの特徴に使う語のリスト（`STOP`・`SHORT`）は手で書かれたもので、'
      '『国家』を見ずに書かれたかどうかは分からない。これは `--ref` では外せないので、その分だけ数値が高めに出ている可能性がある'
      '（語の切り直しの一覧 `SAFE_SPLITS` は、参考に現れる形だけが使われるので、ここでは III,3 に現れる形だけが効く）。')
    w('')
    w('## 1. 本文の対応づけ')
    w('')
    w('形態素ごとに文字だけを取り出し（Unicode NFD、角括弧とその中身を除く、文字（カテゴリ L）だけ、小文字）、文書全体の文字列どうしを difflib で対応づけた。')
    w('')
    w('| | 人手（data/republic_tei.xml） | 自動（tei/06-5 から） |')
    w('|---|---:|---:|')
    w('| セグメント `<s>` | %s | %s |' % (num(len(gold.segs)), num(len(auto.segs))))
    w('| 形態素 `<w>` | %s | %s |' % (num(len(gold.morphs)), num(len(auto.morphs))))
    w('| 語群 `<phr>`（文字のあるもの） | %s | %s |' % (num(len(gold.groups)), num(len(auto.groups))))
    w('| 文字数 | %s | %s |' % (num(len(gold.text)), num(len(auto.text))))
    w('| 対応した文字 | %s（%.2f%%） | %s（%.2f%%） |' % (num(cmp['aligned']), 100 * cmp['aligned'] / len(gold.text),
                                                  num(cmp['aligned']), 100 * cmp['aligned'] / len(auto.text)))
    w('')
    if diffs:
        w('対応しなかった箇所:')
        w('')
        for t, i1, i2, j1, j2 in diffs:
            w('- 人手 `%s` の「%s」／自動 `%s` の「%s」（%s）' % (
                gold.seg_at(i1), gold.text[i1:i2] or '（なし）', auto.seg_at(j1), auto.text[j1:j2] or '（なし）',
                {'delete': '人手の版にだけある', 'insert': '自動の版にだけある', 'replace': '文字が違う'}[t]))
        w('')
    w('## 2. 区切りの一致')
    w('')
    w('「範囲」は、形態素（語群）の最初と最後の文字が両方の版で同じ位置にあるものを一致とする。'
      '「境目」は、隣り合う 2 文字のあいだに境目があるかどうかを位置ごとに比べる（セグメントの切れ目は除く）。'
      '適合率 P＝一致／自動、再現率 R＝一致／人手。')
    w('')
    w('| 単位 | 人手 | 自動 | 一致 | 適合率 P | 再現率 R | F1 |')
    w('|---|---:|---:|---:|---|---|---:|')
    w('| 形態素（範囲） | %s | %s | %s | %s（%s） | %s（%s） | %.3f |' % (
        num(cmp['gold_units']), num(cmp['auto_units']), num(mp['k']), pct(mp), ci(mp), pct(mr), ci(mr), mf))
    tp, fp, fn, comp = cmp['morph_pos']
    w('| 形態素の境目（位置） | %s | %s | %s | %s（%s） | %s（%s） | %.3f |' % (
        num(tp + fn), num(tp + fp), num(tp), pct(bp), ci(bp), pct(br), ci(br), bf))
    w('| 語群（範囲） | %s | %s | %s | %s（%s） | %s（%s） | %.3f |' % (
        num(len(gold.groups)), num(len(auto.groups)), num(gp['k']), pct(gp), ci(gp), pct(gr), ci(gr), gf))
    tp, fp, fn, comp2 = cmp['group_pos']
    w('| 語群の境目（位置） | %s | %s | %s | %s（%s） | %s（%s） | %.3f |' % (
        num(tp + fn), num(tp + fp), num(tp), pct(qp), ci(qp), pct(qr), ci(qr), qf))
    w('')
    w('括弧内は 95%% 信頼区間（Wilson）。境目を比べた位置は %s（形態素）、%s（語群）。' % (num(comp), num(comp2)))
    w('')
    w('## 3. 品詞とレンマ（区切りが一致した形態素）')
    w('')
    w('区切りが一致した形態素 %s のうち、人手の品詞が %s のもの（%s）を除いた %s で比べた。'
      '自動の品詞が `X`（未判定）のものは誤りとして数える。' % (
          num(len(match)), '・'.join('`%s`' % t for t in NO_GOLD_POS),
          '、'.join('%s %d' % (t, n) for t, n in sorted(nogold.items())) or 'なし', num(a['n'])))
    w('')
    w('| | n | 正解 | 正解率 | 95% CI |')
    w('|---|---:|---:|---:|---|')
    for label, r in (('品詞（`X` は誤り）', a['pos']), ('品詞（自動が `X` でないものだけ）', a['pos_nonx']),
                     ('自動が `X` でない割合（カバー率）', a['coverage']),
                     ('レンマ（完全一致。レンマなしは誤り）', a['lemma']),
                     ('レンマ（結合記号を除いて一致）', a['lemma_norm']),
                     ('参考: 人手の形態素（品詞が `X`・`UNKNOWN` 以外）全体のうち、区切りも品詞も一致', res['end_to_end'])):
        w('| %s | %s | %s | %s | %s |' % (label, num(r['n']), num(r['k']), pct(r), ci(r)))
    w('')
    if a['lemma']['k'] == a['lemma_norm']['k']:
        w('結合記号を除いても、一致の数は変わらない（§9）。')
        w('')
    w('## 4. 確度（`@cert`）ごと')
    w('')
    w('「区切り一致」は、その確度の自動の形態素のうち、人手と区切りが一致した割合。品詞・レンマはそのうち採点対象（上と同じ）について。')
    w('')
    w('| cert | 自動の形態素 | 区切り一致 | 採点 n | 品詞 正解率（95% CI） | レンマ 正解率（95% CI） | `X` の割合 |')
    w('|---|---:|---|---:|---|---|---:|')
    for c in CERTS:
        b = res['cert'][c]
        w('| %s | %s | %s（%s） | %s | %s（%s） | %s（%s） | %s |' % (
            c, num(b['auto']), pct(b['auto_matched']), ci(b['auto_matched']), num(b['n']),
            pct(b['pos']), ci(b['pos']), pct(b['lemma']), ci(b['lemma']), pct(b['x_share'])))
    w('')
    w('## 5. 品詞の取り違え（多いもの）')
    w('')
    w('区切りが一致し、人手の品詞が `X`・`UNKNOWN` でない形態素について。「『国家』での内訳」は、同じ文字の形態素に人手の版（`republic_tei.xml`）が付けた品詞の内訳、'
      '「III,3 での内訳」は参考（`eugnostos_tei.xml`）での内訳（内訳に自動と同じ品詞があっても、それが注釈の揺れか、文脈による使い分けかは、ここでは判断しない）。'
      '混同表の全体は `republic_pos_confusion.tsv`。')
    w('')
    w('| 人手 | 自動 | 件数 | 語形 | 『国家』での内訳 | III,3 での内訳 |')
    w('|---|---|---:|---|---|---|')
    errs = Counter()
    forms = defaultdict(Counter)
    for g, am in res['scored']:
        if am.type != g.type:
            errs[(g.type, am.type)] += 1
            forms[(g.type, am.type)][g.let] += 1
    for (gt, at), n in sorted(errs.items(), key=lambda x: (-x[1], x[0]))[:15]:
        fs = sorted(forms[(gt, at)].items(), key=lambda x: (-x[1], x[0]))
        shown = fs[:4]
        w('| %s | %s | %d | %s | %s | %s |' % (
            gt, at, n, '、'.join('%s×%d' % (f, k) for f, k in shown) + ('…' if len(fs) > 4 else ''),
            '；'.join('%s %s' % (f, fmt_dist(gold_dist[f])) for f, _ in shown[:2]),
            '；'.join('%s %s' % (f, fmt_dist(eug_dist[f]) or '—') for f, _ in shown[:2])))
    w('')
    w('## 6. レンマの不一致（多いもの）')
    w('')
    w('採点した形態素のうちレンマが一致しなかったもの。「（なし）」は自動の版にレンマがない（品詞 `X`）。')
    w('')
    w('| 人手のレンマ | 自動のレンマ | 件数 | 語形 | 『国家』でのレンマの内訳 | III,3 でのレンマの内訳 |')
    w('|---|---|---:|---|---|---|')
    gold_ldist = tag_dist(gold.morphs, 'lemma')
    eug_ldist = tag_dist(eug.morphs, 'lemma')
    lerr = Counter()
    lforms = defaultdict(Counter)
    for g, am in res['scored']:
        if am.lemma != g.lemma:
            lerr[(g.lemma, am.lemma)] += 1
            lforms[(g.lemma, am.lemma)][g.let] += 1
    for (gl, al), n in sorted(lerr.items(), key=lambda x: (-x[1], x[0]))[:15]:
        fs = sorted(lforms[(gl, al)].items(), key=lambda x: (-x[1], x[0]))
        shown = fs[:3]
        w('| %s | %s | %d | %s | %s | %s |' % (
            gl, al or '（なし）', n, '、'.join('%s×%d' % (f, k) for f, k in shown) + ('…' if len(fs) > 3 else ''),
            '；'.join('%s %s' % (f, fmt_dist(gold_ldist[f])) for f, _ in shown[:2]),
            '；'.join('%s %s' % (f, fmt_dist(eug_ldist[f]) or '—') for f, _ in shown[:2])))
    w('')
    w('## 7. 人手の品詞ごとの正解率')
    w('')
    w('| 人手の品詞 | n | 正解 | 正解率 | 自動の品詞（多い順） |')
    w('|---|---:|---:|---:|---|')
    by_gold = defaultdict(Counter)
    for g, am in res['scored']:
        by_gold[g.type][am.type] += 1
    for gt, c in sorted(by_gold.items(), key=lambda x: (-sum(x[1].values()), x[0])):
        n = sum(c.values())
        w('| %s | %d | %d | %.1f%% | %s |' % (gt, n, c[gt], 100 * c[gt] / n, fmt_dist(c)))
    w('')
    w('## 8. 2 つの人手の注釈で、同じ語形にいちばん多く付いている品詞・レンマが違うもの')
    w('')
    w('参考（III,3、`eugnostos_tei.xml`）と正解（『国家』、`republic_tei.xml`）の両方に 3 回以上出てくる形態素（文字が同じもの）のうち、'
      'いちばん多く付いている品詞またはレンマが違うもの。注釈の付け方の違い（方針の違いや、どちらかの誤り）のこともあれば、2 つの文書で語の使われ方が違うこともある。'
      'どちらかは、ここでは判断しない。付け方の違いなら、ここの語形の「誤り」は、どちらの付け方に合わせるかで正解に変わりうる。')
    w('')
    w('| 語形 | 比べたもの | III,3 での内訳 | 『国家』での内訳 | この評価での誤り |')
    w('|---|---|---|---|---:|')
    pos_err_forms = Counter(g.let for g, am in res['scored'] if am.type != g.type)
    lem_err_forms = Counter(g.let for g, am in res['scored'] if am.lemma != g.lemma)
    dpos, dlem = differing_forms(eug, gold, 'type'), differing_forms(eug, gold, 'lemma')
    for f in dpos:
        w('| %s | 品詞 | %s | %s | %d |' % (f, fmt_dist(eug_dist[f]), fmt_dist(gold_dist[f]), pos_err_forms[f]))
    for f in dlem:
        w('| %s | レンマ | %s | %s | %d |' % (f, fmt_dist(eug_ldist[f]), fmt_dist(gold_ldist[f]), lem_err_forms[f]))
    n_pos_err = sum(pos_err_forms.values())
    n_lem_err = sum(lem_err_forms.values())
    w('')
    w('品詞の誤り %s のうち %s、レンマの誤り %s のうち %s が、この表の語形のもの。' % (
        num(n_pos_err), num(sum(pos_err_forms[f] for f in dpos)), num(n_lem_err), num(sum(lem_err_forms[f] for f in dlem))))
    w('')
    w('## 9. データについて気づいたこと（どれも直していない）')
    w('')
    for line in data_notes(gold, auto, diffs, pos_codes):
        w('- ' + line)
    w('')
    w('## 10. 方法の限界')
    w('')
    w('- 正解は人手の注釈 1 種類で、その注釈の誤りや揺れ、参考（III,3）との付け方の違いも「自動の誤り」に数えている（§5・§6・§8・§9）。')
    w('- 品詞とレンマは区切りが一致した形態素だけで比べるので、区切りの難しい箇所（元ファイルで 1 語にまとまった語群など。自動では多くが `X`）は採点から外れる。'
      'その分、正解率は本文全体の正解率より高めに出る。区切りと品詞を合わせた数は §3 の「参考」の行。')
    w('- `@cert` ごとの n は小さく、信頼区間が広い（とくに `high`）。')
    w('- レンマは文字列の一致で比べる（結合記号を除いた一致も出したが、ここでは差がない）。同じ語のレンマの立て方の違い（§6）も不一致になる。')
    w('- 語義（`@ana`）は比べていない。人手の版の語義は文脈上の語釈で、自動の語義は辞書的な短い意味なので、性質が違う。')
    w('- 1 文書・約 700 形態素なので、信頼区間は本文の偏りを含まない（同じ文書の中の形態素は互いに独立ではない）。実際の不確かさは区間より大きい。')
    w('- 対照の数値（下）は、『国家』を参考に入れた、公開版と同じ条件のもの。答えを見ているので精度の推定ではない。')
    w('')
    w('## 対照: 『国家』も参考にした場合（公開版と同じ条件。精度の推定ではない）')
    w('')
    sa = res_s['all']
    w('| | 参考から外した場合（上） | 『国家』も参考にした場合 |')
    w('|---|---|---|')
    w('| 形態素（範囲）の F1 | %.3f | %.3f |' % (cmp['morph_span'][2], cmp_s['morph_span'][2]))
    w('| 語群（範囲）の F1 | %.3f | %.3f |' % (cmp['group_span'][2], cmp_s['group_span'][2]))
    w('| 品詞（`X` は誤り） | %s（n=%s） | %s（n=%s） |' % (pct(a['pos']), num(a['pos']['n']), pct(sa['pos']), num(sa['pos']['n'])))
    w('| レンマ（完全一致） | %s（n=%s） | %s（n=%s） |' % (pct(a['lemma']), num(a['lemma']['n']), pct(sa['lemma']), num(sa['lemma']['n'])))
    w('')
    w('『国家』を参考に入れても人手の版と一致しきらないのは、注釈のスクリプトが語彙表と規則を参考の用例より先に使い、'
      '参考の用例も、語形ごとに 2 つの参考を合わせて数えたいちばん多い品詞・レンマを、前後を見ずに使うため（III,3 の方が語数が多い）。'
      '形態素の区切りは、元ファイルの `<w>` の切り方をほぼそのまま使う（参考に現れる少数の形だけを分ける）。')
    w('')
    w('## 再現')
    w('')
    w('```')
    w('python3 source/nhc_fulltext_split/evaluation/evaluate_republic.py')
    w('```')
    w('')
    w('lxml と scikit-learn が要る（注釈のスクリプトと同じ）。同じ入力なら、何度実行しても同じファイルになる。入力（SHA-256）:')
    w('')
    for p in (SRC, GOLD, EUG, CONV, ANNOT):
        w('- `%s` %s' % (rel(p), sha256(p)))
    w('')
    w('実行環境: %s。' % versions())
    with open(str(out / 'republic_summary.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')


def data_notes(gold, auto, diffs, pos_codes):
    """Facts about the hand annotation found while comparing (reported, not fixed)."""
    notes = []
    if not pos_codes:
        notes.append('サイトの品詞コードの一覧（`scripts/build_site.py` の `POS_NAMES`）を読めなかったので、一覧にない品詞は調べていない。')
    odd = Counter(m.type for m in gold.morphs if pos_codes and m.type not in pos_codes)
    if odd:
        ex = {}
        for m in gold.morphs:
            if m.type in odd and m.type not in ex:
                ex[m.type] = m
        notes.append('`data/republic_tei.xml` には、サイトの品詞コード（`scripts/build_site.py` の `POS_NAMES`）にない品詞が %d 語ある: %s。'
                     '`X`・`UNKNOWN` 以外はそのまま正解として扱った（自動の品詞がこれと一致することはない）。' % (
                         sum(odd.values()),
                         '、'.join('`%s` %d（例 `%s` の `%s`）' % (t, odd[t], ex[t].seg, ex[t].form)
                                  for t in sorted(odd, key=lambda t: (-odd[t], t)))))
    brackets = Counter()
    for m in gold.morphs:
        if re.search(r'\[[^\]]*\]', m.form):
            brackets[m.form] += 1
    if brackets:
        notes.append('人手の版で `<w>` の中に角括弧があるのは %s だけ。括弧の中の文字は元ファイル（tei/06-5）の本文になく、'
                     '括弧の中身を除くと文字列が元ファイルと一致するので、対応づけでは中身ごと除いた。' % (
                         '、'.join('`%s`×%d' % (f, n) for f, n in sorted(brackets.items()))))
    for t, i1, i2, j1, j2 in diffs:
        g_ms = sorted({gold.owner[i] for i in range(i1, i2) if gold.owner[i] is not None}, key=lambda m: m.i)
        desc = '、'.join('`%s` の %d 番目の `<w type="%s" lemma="%s">%s</w>`' % (m.seg, m.w_pos, m.type, m.lemma, m.form)
                        for m in g_ms)
        if t == 'delete':
            notes.append('本文の違い: 人手の版の「%s」（%s）が、自動の版（tei/06-5 の `%s`）にない。' % (
                gold.text[i1:i2], desc, auto.seg_at(j1)))
        elif t == 'insert':
            notes.append('本文の違い: 自動の版（tei/06-5 の `%s`）の「%s」が、人手の版（`%s`）にない。' % (
                auto.seg_at(j1), auto.text[j1:j2], gold.seg_at(i1)))
        else:
            notes.append('本文の違い: 人手の版の「%s」（%s）が、自動の版（tei/06-5 の `%s`）では「%s」。' % (
                gold.text[i1:i2], desc, auto.seg_at(j1), auto.text[j1:j2]))
    _, gbody = ec.body_of(GOLD)
    gaps = sum(1 for _ in gbody.iter(ec.TEI + 'gap'))
    gap_only = sum(1 for phr in gbody.iter(ec.TEI + 'phr')
                   if phr.find(ec.TEI + 'gap') is not None and phr.find('.//' + ec.TEI + 'w') is None)
    _, sbody = ec.body_of(SRC)
    src_gaps = sum(1 for _ in sbody.iter(ec.TEI + 'gap'))
    if gaps != src_gaps:
        notes.append('人手の版には `<gap>` が %d（うち `<gap>` だけの `<phr>` が %d）あり、元ファイル（tei/06-5）には%s。'
                     '文字の対応は §1 のとおりで、`<gap>` は文字のない要素として扱った。' % (
                         gaps, gap_only, ' %d ある' % src_gaps if src_gaps else 'ない'))
    marks = [m for d in (gold, auto) for m in d.morphs if m.lemma != ec.strip_marks(m.lemma)]
    notes.append('結合記号を含むレンマは、人手の版・自動の版あわせて %d。' % len(marks))
    return notes


if __name__ == '__main__':
    main()
