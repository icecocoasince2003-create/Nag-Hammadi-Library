#!/usr/bin/env python3
"""項目 13: 記入した抜き取り表から、自動注釈の正解率を見積もる。

  python3 source/nhc_fulltext_split/evaluation/score_review.py 記入した.tsv [--meta review_sample.json] [--out 結果.tsv]

Standard library only. Reads a copy of review_sample.tsv in which the columns 正しい品詞 and
正しいレンマ have been filled in, and review_sample.json (the population size of every
stratum; by default the .json next to the TSV, else the one next to this script).
Prints the results; --out also writes them as TSV. Partly filled tables are fine.

How to fill in the two columns (each is scored on its own):
  (blank)    not checked yet: skipped and counted as 未記入
  =          the automatic value is right
  ?          cannot be decided: skipped and counted as 判定不能
  -          (正しいレンマ only) the morpheme has no lemma; right only if the automatic one is empty
  otherwise  the right POS code (compared without case and outer spaces) or lemma (compared
             after NFC; also reported with combining marks removed); anything that differs from
             the automatic value counts as an error, also when the automatic POS is X
The column メモ is not read. Do not change the columns 層, 自動の品詞, 自動のレンマ.

Estimates
  stratum h (dialect × cert):  p_h = k_h / n_h (k_h right of n_h checked), 95% Wilson interval.
  combined (all, each dialect, each cert level), weighting the strata by their population
  sizes N_h from the JSON, W_h = N_h / Σ N_h over the strata combined:
      p    = Σ W_h p_h
      Var  = Σ W_h² (1 − n_h/N_h) p_h (1 − p_h) / (n_h − 1)
      95% CI = p ± 1.96 √Var, clipped to [0, 1]
  A combined estimate needs at least 2 checked rows in every stratum it combines; otherwise
  it is reported as not available. With p_h = 0 or 1 a stratum adds no variance, so the
  interval is then too narrow; the row says so.
  If the table is filled from the top (it is in random order), the checked rows are a random
  part of each stratum and the estimates are unbiased.
"""
import argparse
import csv
import json
import math
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
import evalcommon as ec  # noqa: E402  (same folder)

HERE = Path(__file__).resolve().parent
SAME = ('=', '＝')
UNSURE = ('?', '？')
NONE = ('-', '－', '—')
NEEDED = ('層', '自動の品詞', '自動のレンマ', '正しい品詞', '正しいレンマ')


def nfc(s):
    return unicodedata.normalize('NFC', s or '').strip()


def pad(s, width):
    """Left-justify s to a display width (East Asian wide characters count as 2)."""
    w = sum(2 if unicodedata.east_asian_width(ch) in 'WF' else 1 for ch in s)
    return s + ' ' * max(0, width - w)


def judge(answer, auto, kind):
    """None (not checked), 'unsure', or (exact_ok, normalised_ok)."""
    a = nfc(answer)
    if not a:
        return None
    if a in UNSURE:
        return 'unsure'
    if a in SAME:
        return (True, True)
    if kind == 'pos':
        ok = a.upper() == nfc(auto).upper()
        return (ok, ok)
    if a in NONE:
        ok = not nfc(auto)
        return (ok, ok)
    auto = nfc(auto)
    return (a == auto, bool(auto) and ec.strip_marks(a) == ec.strip_marks(auto))


def stratified(strata, counts):
    """counts: {label: (k, n)}; strata: [(label, N)]. Returns dict or a reason string."""
    total = sum(N for _, N in strata)
    p = var = 0.0
    degenerate = False
    for lab, N in strata:
        k, n = counts.get(lab, (0, 0))
        if n < 2:
            return '「%s」の記入が %d 行（2 行以上要る）' % (lab, n)
        W = N / total
        ph = k / n
        p += W * ph
        var += W * W * (1 - n / N) * ph * (1 - ph) / (n - 1)
        degenerate |= ph in (0.0, 1.0)
    half = ec.Z95 * math.sqrt(var)
    return {'p': p, 'lo': max(0.0, p - half), 'hi': min(1.0, p + half),
            'n': sum(counts.get(lab, (0, 0))[1] for lab, _ in strata),
            'k': sum(counts.get(lab, (0, 0))[0] for lab, _ in strata), 'degenerate': degenerate}


def main():
    ap = argparse.ArgumentParser(description='Score a filled review_sample.tsv.')
    ap.add_argument('tsv', type=Path)
    ap.add_argument('--meta', type=Path, help='review_sample.json (default: next to the TSV, else next to this script)')
    ap.add_argument('--out', type=Path, help='also write the results here as TSV')
    args = ap.parse_args()
    meta_path = args.meta or next((p for p in (args.tsv.with_suffix('.json'), HERE / 'review_sample.json') if p.is_file()), None)
    if meta_path is None or not meta_path.is_file():
        sys.exit('review_sample.json not found; give it with --meta')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    strata = [(s['label'], s['population']) for s in meta['strata']]
    info = {s['label']: s for s in meta['strata']}

    with open(str(args.tsv), encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        missing = [c for c in NEEDED if c not in (reader.fieldnames or [])]
        if missing:
            sys.exit('%s: missing columns: %s' % (args.tsv, ', '.join(missing)))
        rows = [r for r in reader if any((v or '').strip() for v in r.values() if isinstance(v, str))]

    measures = (('pos', '品詞', '正しい品詞', '自動の品詞'),
                ('lemma', 'レンマ', '正しいレンマ', '自動のレンマ'))
    tally = {m[0]: {lab: [0, 0, 0, 0, 0] for lab, _ in strata} for m in measures}  # k, k_norm, n, blank, unsure
    per_stratum_rows = {lab: 0 for lab, _ in strata}
    for i, r in enumerate(rows, 2):
        lab = (r.get('層') or '').strip()
        if lab not in info:
            sys.exit('%s line %d: unknown 層 %r' % (args.tsv, i, lab))
        per_stratum_rows[lab] += 1
        for key, _, col, auto_col in measures:
            t = tally[key][lab]
            j = judge(r.get(col), r.get(auto_col), key)
            if j is None:
                t[3] += 1
            elif j == 'unsure':
                t[4] += 1
            else:
                t[2] += 1
                t[0] += j[0]
                t[1] += j[1]
    warn = [lab for lab, _ in strata if per_stratum_rows[lab] != info[lab]['sample']]

    out_rows = []
    lines = ['%s: %d 行（抜き取り表 %d 行、種 %s）' % (args.tsv.name, len(rows), meta.get('total', 0), meta.get('seed'))]
    if warn:
        lines.append('注意: 行数が抜き取りのときと違う層がある: ' + '、'.join(
            '%s %d（抜き取り %d）' % (lab, per_stratum_rows[lab], info[lab]['sample']) for lab in warn))
    groups = [('全体', [lab for lab, _ in strata])]
    for dialect in sorted({s['dialect'] for s in meta['strata']}, key=lambda d: [s['dialect'] for s in meta['strata']].index(d)):
        groups.append(('方言 ' + dialect, [s['label'] for s in meta['strata'] if s['dialect'] == dialect]))
    for cert in sorted({s['cert'] for s in meta['strata']}, key=lambda c: [s['cert'] for s in meta['strata']].index(c)):
        groups.append(('cert ' + cert, [s['label'] for s in meta['strata'] if s['cert'] == cert]))
    for key, name, _, _ in measures:
        variants = (('', 0),) if key == 'pos' else (('（完全一致）', 0), ('（結合記号を除いて一致）', 1))
        for suffix, which in variants:
            lines.append('')
            lines.append('■ %s%s' % (name, suffix))
            lines.append('  %s %6s %5s %s %s  %s %s %s' % (pad('層', 20), 'N', 'n', pad('正解', 5), pad('正解率', 8),
                                                         pad('95% CI (Wilson)', 15), pad('未記入', 6), '判定不能'))
            counts = {}
            for lab, N in strata:
                k, kn, n, blank, unsure = tally[key][lab]
                kk = (k, kn)[which]
                counts[lab] = (kk, n)
                lo, hi = ec.wilson(kk, n)
                rate = '%.1f%%' % (100 * kk / n) if n else '—'
                cis = '%.1f–%.1f%%' % (100 * lo, 100 * hi) if n else '—'
                lines.append('  %s %6d %5d %5d %8s  %-15s %6d %6d' % (pad(lab, 20), N, n, kk, rate, cis, blank, unsure))
                out_rows.append([name + suffix, 'stratum', lab, N, n, kk, '%.4f' % (kk / n) if n else '',
                                 '%.4f' % lo if n else '', '%.4f' % hi if n else '', blank, unsure, 'Wilson'])
            lines.append('  — 層を母集団の大きさで重みづけした推定（95% CI = p ± 1.96√Var。n・正解は記入した行の合計で、正解率は重みづけした値）')
            for gname, labs in groups:
                st = [(lab, N) for lab, N in strata if lab in labs]
                res = stratified(st, counts)
                if isinstance(res, str):
                    lines.append('  %s 出せない: %s' % (pad(gname, 20), res))
                    out_rows.append([name + suffix, 'weighted', gname, sum(N for _, N in st), '', '', '', '', '', '', '', res])
                    continue
                note = '（正解率 0% か 100% の層があり、区間は狭く出ている）' if res['degenerate'] else ''
                lines.append('  %s %6d %5d %5d %7.1f%%  %-15s %s' % (
                    pad(gname, 20), sum(N for _, N in st), res['n'], res['k'], 100 * res['p'],
                    '%.1f–%.1f%%' % (100 * res['lo'], 100 * res['hi']), note))
                out_rows.append([name + suffix, 'weighted', gname, sum(N for _, N in st), res['n'], res['k'],
                                 '%.4f' % res['p'], '%.4f' % res['lo'], '%.4f' % res['hi'], '', '',
                                 'stratified normal' + ('; a stratum at 0 or 1' if res['degenerate'] else '')])
    print('\n'.join(lines))
    if args.out:
        with open(str(args.out), 'w', encoding='utf-8', newline='\n') as f:
            f.write('\t'.join(['measure', 'level', 'group', 'population', 'n_checked', 'correct', 'rate',
                               'ci95_low', 'ci95_high', 'not_filled', 'unsure', 'method']) + '\n')
            for r in out_rows:
                f.write('\t'.join(str(x) for x in r) + '\n')


if __name__ == '__main__':
    main()
