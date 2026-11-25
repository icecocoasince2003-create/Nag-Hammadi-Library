#!/usr/bin/env python3
"""項目 13: 人手で確かめるための抜き取り表を作る（自動注釈の 56 文書から約 400 形態素）。

  python3 source/nhc_fulltext_split/evaluation/sample_review.py

Standard library only. Writes, next to this script:
  review_sample.tsv   the table to fill in (UTF-8, LF, tab-separated, no BOM; the last
                      three columns 正しい品詞・正しいレンマ・メモ are empty)
  review_sample.json  seed, strata with population and sample sizes, allocation, and the
                      SHA-256 of every TEI file read; score_review.py reads it
The same seed and the same TEI files give the same two files.

Population: every <w> with @cert in the automatically annotated TEI files of ../tei/
(the files whose <w> carry resp="#coptic-nlp", "#morph-auto" or "#morph-reference"; 39 files
when this was written, 56 since 2026-11-25; since 2026-11-24 they are annotated by the Coptic
SCRIPTORIUM NLP, resp="#coptic-nlp"). Other files of ../tei/ also have @cert on a few <w> (restored ⲍ/ⲯ,
resp="#zp"), but they are not annotated and are not read.

Strata: dialect from <textLang> (Sahidic → サヒド, Lycopolitan → リコポリス) = 2 strata.
Until 2026-11-23 the strata were dialect × @cert (6). The NLP annotation (2026-11-24, sent
again one sentence per segment on 2026-11-25) gives almost every morpheme cert="medium" (high:
353 Sahidic and 0 Lycopolitan morphemes; low: 1,132 and 387 when the table of 2026-11-25 was
drawn), so strata by @cert no longer tell anything apart; the cert of every row is still in
the table (column cert).

Allocation: equal, total // 2 per stratum (400 → 200 each). Equal rather than proportional,
because the point is also to see how the Lycopolitan texts fare (about a fifth of the
morphemes; proportional allocation would give them about 83 rows). The overall estimate
is still unbiased, because score_review.py weights every stratum by its population size; its
95% interval is about ±5 percentage points at worst (p = 0.5), each dialect about ±7.

Selection: random.Random(seed); for each stratum in the order of STRATA, sample(range(N), n)
over the stratum's morphemes in file-name and document order; then the chosen rows are
shuffled with the same generator, so that the table is in random order. Rows filled from
the top are then a random part of every stratum, and a half-filled table can be scored
without bias (sorting the table, e.g. by document, and filling only part of it cannot).

Columns: 番号 (check order), 層, 方言, 文書 (siglum), seg_id, 語の位置 (1-based index of the
<w> among all <w> of its <s>), 語群の位置 (1-based index of its <phr> among the <phr> of the
<s>), 前後の文脈 (CONTEXT bound groups on each side; the target bound group with its
morphemes separated by ·, the morpheme in 【】; ｜ marks a segment boundary, […] a gap),
語形, 自動の品詞, 自動のレンマ, 自動の語義 (the standOff glosses of @ana, "en: …; ja: …"),
cert, resp, 正しい品詞, 正しいレンマ, メモ.
"""
import argparse
import hashlib
import json
import platform
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import evalcommon as ec  # noqa: E402  (same folder)

HERE = Path(__file__).resolve().parent
TEI_DIR = HERE.parent / 'tei'
SEED = 20261124
TOTAL = 400
CONTEXT = 4
DIALECTS = (('Sahidic', 'サヒド'), ('Lycopolitan', 'リコポリス'))
CERTS = ('high', 'medium', 'low')
STRATA = [d for _, d in DIALECTS]
AUTO_RESP = ('#coptic-nlp', '#morph-auto', '#morph-reference')
COLUMNS = ['番号', '層', '方言', '文書', 'seg_id', '語の位置', '語群の位置', '前後の文脈', '語形',
           '自動の品詞', '自動のレンマ', '自動の語義', 'cert', 'resp', '正しい品詞', '正しいレンマ', 'メモ']


def label(dialect):
    return dialect


def dialect_of(root, path):
    tl = root.find('.//' + ec.TEI + 'textLang')
    text = ''.join(tl.itertext()) if tl is not None else ''
    for key, name in DIALECTS:
        if key in text:
            return name
    raise SystemExit('%s: unknown dialect in <textLang>: %r' % (path.name, text))


def glossary(root):
    g = {}
    for grp in root.iter(ec.TEI + 'interpGrp'):
        if grp.get('type') != 'gloss':
            continue
        lang = grp.get(ec.XML + 'lang') or ''
        for it in grp.iter(ec.TEI + 'interp'):
            g[it.get(ec.XML + 'id')] = (lang, ' '.join(''.join(it.itertext()).split()))
    return g


def gloss_text(w, gl):
    parts = []
    for ref in (w.get('ana') or '').split():
        hit = gl.get(ref.lstrip('#'))
        if hit:
            parts.append(hit)
    parts.sort(key=lambda x: ({'en': 0, 'ja': 1}.get(x[0], 2), x[0]))
    return '; '.join('%s: %s' % (lang or '?', text) for lang, text in parts)


class Morph:
    __slots__ = ('seg', 'pos', 'phr', 'item', 'form', 'type', 'lemma', 'cert', 'resp', 'gloss')


class Document:
    """One TEI file: its morphemes and what is needed to show their context."""

    def __init__(self, path):
        self.path = path
        root, body = ec.body_of(path)
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        text = root.find('.//' + ec.TEI + 'text')
        self.siglum = (text.get('n') or path.stem).replace('NHC ', '') if text is not None else path.stem
        self.dialect = dialect_of(root, path)
        gl = glossary(root)
        self.items = []          # (segment index, kind, [morph index]) in reading order
        self.morphs = []         # Morph, in document order
        self.draft = False
        for si, (s, ws, phr_of, items) in enumerate(ec.segments(body)):
            index = {w: len(self.morphs) + i for i, w in enumerate(ws)}
            where = {}
            for kind, k, words in items:
                for w in words:
                    where[w] = len(self.items)
                self.items.append((si, kind, [index[w] for w in words]))
            for pos, w in enumerate(ws, 1):
                m = Morph()
                m.seg, m.pos, m.phr, m.item = s.get(ec.XML + 'id') or '', pos, phr_of.get(w, ''), where[w]
                m.form, m.type, m.lemma = ec.w_text(w), w.get('type') or '', w.get('lemma') or ''
                m.cert, m.resp, m.gloss = w.get('cert'), w.get('resp') or '', gloss_text(w, gl)
                if m.resp in AUTO_RESP:
                    self.draft = True
                self.morphs.append(m)

    def context(self, target, width):
        item = self.morphs[target].item
        lo, hi = max(0, item - width), min(len(self.items), item + width + 1)
        out, prev = [], None
        for j in range(lo, hi):
            si, kind, idxs = self.items[j]
            if prev is not None and si != prev:
                out.append('｜')
            prev = si
            if not idxs:
                out.append('[…]')
            elif j == item:
                out.append('·'.join('【%s】' % self.morphs[i].form if i == target else self.morphs[i].form for i in idxs))
            else:
                out.append(''.join(self.morphs[i].form for i in idxs))
        return ' '.join(out)


def allocate(sizes, total):
    """Equal allocation; the remainder goes to the largest strata (ties: order of STRATA)."""
    base, rest = divmod(total, len(STRATA))
    order = sorted(range(len(STRATA)), key=lambda i: (-sizes[STRATA[i]], i))
    alloc = {st: base for st in STRATA}
    for i in order[:rest]:
        alloc[STRATA[i]] += 1
    for st in STRATA:
        if alloc[st] > sizes[st]:
            print('warning: stratum %s has only %d morphemes' % (label(st), sizes[st]), file=sys.stderr)
            alloc[st] = sizes[st]
    return alloc


def clean(x):
    return ' '.join(str(x).replace('\t', ' ').split())


def main():
    ap = argparse.ArgumentParser(description='Stratified random sample of automatically annotated morphemes for checking by hand.')
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--total', type=int, default=TOTAL)
    ap.add_argument('--context', type=int, default=CONTEXT, help='bound groups shown on each side (default %d)' % CONTEXT)
    ap.add_argument('--tei-dir', type=Path, default=TEI_DIR)
    ap.add_argument('--out', type=Path, default=HERE / 'review_sample.tsv', help='the TSV; the JSON is written next to it')
    args = ap.parse_args()

    docs = [d for d in (Document(p) for p in sorted(args.tei_dir.glob('*.xml'))) if d.draft]
    population = {st: [] for st in STRATA}
    for di, d in enumerate(docs):
        for idx, m in enumerate(d.morphs):
            if m.cert is None:
                continue
            if m.cert not in CERTS:
                raise SystemExit('%s %s: unexpected cert=%r' % (d.path.name, m.seg, m.cert))
            population[d.dialect].append((di, idx))
    sizes = {st: len(v) for st, v in population.items()}
    alloc = allocate(sizes, args.total)

    rng = random.Random(args.seed)
    chosen = []
    for st in STRATA:
        for i in rng.sample(range(sizes[st]), alloc[st]):
            chosen.append((st, population[st][i]))
    rng.shuffle(chosen)

    rows = []
    for no, (st, (di, idx)) in enumerate(chosen, 1):
        d = docs[di]
        m = d.morphs[idx]
        rows.append([no, label(st), st, d.siglum, m.seg, m.pos, m.phr, d.context(idx, args.context),
                     m.form, m.type, m.lemma, m.gloss, m.cert, m.resp, '', '', ''])
    with open(str(args.out), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\t'.join(COLUMNS) + '\n')
        for r in rows:
            f.write('\t'.join(clean(x) for x in r) + '\n')

    meta = {
        'description': '項目 13 の抜き取り表（自動注釈の 56 文書から、方言の 2 層に分けて無作為に抜き出した形態素。2026-11-25 に作り直した）。'
                       'sample_review.py が作り、score_review.py が読む。',
        'script': 'source/nhc_fulltext_split/evaluation/sample_review.py',
        'seed': args.seed,
        'selection': 'random.Random(seed); for each stratum in the order below, sample(range(population), sample) '
                     'over the stratum in file-name and document order; then shuffle(rows) with the same generator',
        'python': platform.python_version(),
        'total': len(rows),
        'context_groups_each_side': args.context,
        'allocation': 'equal: total // 2 per stratum, one more for the (total % 2) largest strata',
        'population': 'every <w> with @cert in the files of tei/ whose <w> carry resp="#coptic-nlp", "#morph-auto" or "#morph-reference"',
        'strata': [{'label': label(st), 'dialect': st, 'population': sizes[st], 'sample': alloc[st],
                    'cert_population': {c: sum(1 for di, idx in population[st] if docs[di].morphs[idx].cert == c) for c in CERTS}}
                   for st in STRATA],
        'population_total': sum(sizes.values()),
        'documents': [{'file': d.path.name, 'siglum': d.siglum, 'dialect': d.dialect,
                       'w_with_cert': sum(1 for m in d.morphs if m.cert is not None),
                       'sha256': d.sha256} for d in docs],
        'tsv': {'file': args.out.name, 'rows': len(rows),
                'sha256': hashlib.sha256(args.out.read_bytes()).hexdigest()},
    }
    meta_path = args.out.with_suffix('.json')
    with open(str(meta_path), 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(meta, ensure_ascii=False, indent=1) + '\n')
    print('%d documents, %d morphemes; wrote %s (%d rows) and %s' % (
        len(docs), sum(sizes.values()), args.out, len(rows), meta_path))
    for st in STRATA:
        print('  %-14s population %7d  sample %d' % (label(st), sizes[st], alloc[st]))


if __name__ == '__main__':
    main()
