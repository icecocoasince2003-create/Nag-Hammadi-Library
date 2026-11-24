#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reanchor_proposals.py — 位置を指す提案の表（分け目の TSV）を、TEI の語の区切りを付け直したあとの <w>・<phr> に合わせ直す

表の w（その <s> の中で何番目の <w> か）と phr（何番目の <phr> か）は、TEI の語（<w>）・語群（<phr>）の区切りを付け直すと
（2026-11-24 の Coptic SCRIPTORIUM NLP による付け直しなど）、別の語を指すようになる。付け直しでは本文の文字は変わらないので、
前の版の TEI で「分け目の前にある、そのセグメントの文字の数」を数え、今の TEI でその文字の位置から始まる <w> を探して、w と phr
を書き直す（文字は insert_breaks.py と同じく、空白と結合文字〔上線など〕を除いて数える）。

  python3 scripts/reanchor_proposals.py 表.tsv --from コミット [--doc II-2] [--write]

  --from     前の版（表を作ったときの TEI がある git のコミット。例 5d84075^）。TEI の場所は data/catalog.xml から
  --old 文書=ファイル   前の版の TEI を、git の代わりにファイルから読む（試すとき。--from の代わりに使える）
  --file 文書=ファイル  今の版の TEI を、カタログの場所の代わりにこのファイルから読む（試すとき）
  --doc      列 doc の無い表（thomas_sayings.tsv）の文書
  --write    表に書き込む（付けなければ表示だけ）

* 今の区切りで、その文字の位置から始まる <w> があれば、w と phr をそれに直す。その <w> が語群（<phr>）の途中なら、メモの列
  （備考、無ければ要確認）に印を足す（分けるのは語群の境目だけなので、先に <phr> を直す必要がある）。
* その文字の位置が今の <w> の途中に来るときは、w と phr をその <w> にし、メモの列に印を足す。
* セグメントの文字が前の版と違うときは何も変えず、メモの列に印を足す。
* 列「修正した位置」に値のある行は、その値も同じように直す。
* 書き換えるのは w・phr・修正した位置とメモの列のセルだけで、ほかのバイト（列の順・改行・最後の改行）はそのまま。
* 前の版と今の版が同じ位置を指す行は変えない（位置が動かず、印がもうある行の印もそのまま）。今の版を --from に渡すと何も変わらない。
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_breaks as ib  # noqa: E402

ROOT = ib.ROOT
NOTE_COLUMNS = ("備考", "要確認")
MARK = "【語の区切りを付け直したあと: "
CORRECTED = "修正した位置"


def word_letters(data, seg):
    """各 <w> の文字の数（空白と結合文字を除く）"""
    return [sum(1 for p in ib.w_parts(data, w) if p[0] == "ch" and ib.is_letter(p[3])) for w in seg.ws]


def seg_letters(data, seg):
    return "".join(ch for w in seg.ws for ch in ib.w_text(data, w) if ib.is_letter(ch))


def load(data):
    segs, _dups = ib.segments(ib.parse(data))
    return segs


def old_bytes(rev, path):
    rel = os.path.relpath(path, ROOT)
    r = subprocess.run(["git", "show", "%s:%s" % (rev, rel)], cwd=ROOT, capture_output=True)
    if r.returncode:
        raise SystemExit("!! git show %s:%s — %s" % (rev, rel, r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout


def remap(old_seg, old_data, new_seg, new_data, wi):
    """前の版の wi 番目の <w> の始まりに当たる、今の版の位置。(w, phr, 問題の説明か None)"""
    if not 1 <= wi <= len(old_seg.ws):
        return None, None, "前の版に %d 番目の <w> がありません" % wi
    if seg_letters(old_data, old_seg) != seg_letters(new_data, new_seg):
        return None, None, "セグメントの文字が前の版と違う"
    offset = sum(word_letters(old_data, old_seg)[:wi - 1])
    pos = 0
    for j, n in enumerate(word_letters(new_data, new_seg), 1):
        if pos == offset and n:
            phr = new_seg.wphr[j - 1]
            return j, phr, (None if new_seg.first_in_phr(j) else "語群の途中")
        if pos < offset < pos + n:
            return j, new_seg.wphr[j - 1], "語（<w>）の途中"
        pos += n
    return None, None, "文字の位置が見つからない"


def main(argv=None):
    ap = argparse.ArgumentParser(description="提案の表の w・phr を、語の区切りを付け直したあとの TEI に合わせ直す")
    ap.add_argument("tsv")
    ap.add_argument("--from", dest="rev", help="表を作ったときの TEI がある git のコミット")
    ap.add_argument("--old", action="append", default=[], help="前の版の TEI のファイル（文書=ファイル）")
    ap.add_argument("--file", action="append", default=[], help="今の版の TEI のファイル（文書=ファイル）")
    ap.add_argument("--doc", help="列 doc の無い表の文書（例 II-2）")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    with open(a.tsv, encoding="utf-8", newline="") as f:
        text = f.read()
    eol = "\r\n" if "\r\n" in text else "\n"
    final = text.endswith(eol)
    lines = (text[:-len(eol)] if final else text).split(eol)
    head = lines[0].split("\t")
    col = {c: head.index(c) for c in head}
    note = next((c for c in NOTE_COLUMNS if c in col), None)
    for c in ("seg_id", "w"):
        if c not in col:
            raise SystemExit("!! %s に列 %s がありません" % (a.tsv, c))
    if "doc" not in col and not a.doc:
        raise SystemExit("!! 列 doc が無いので --doc で文書を指定してください")
    olds, p1 = ib.parse_overrides(a.old)
    news, p2 = ib.parse_overrides(a.file)
    if p1 or p2:
        raise SystemExit("!! " + "; ".join(p1 + p2))
    if not a.rev and not olds:
        raise SystemExit("!! --from（git のコミット）か --old（文書=ファイル）で前の版を指定してください")
    catalog = ib.load_catalog()
    cache = {}

    def segs_of(doc):
        if doc not in cache:
            path = news.get(doc) or catalog.get(doc)
            if not path:
                raise SystemExit("!! 文書 %s が data/catalog.xml にありません" % doc)
            with open(path, "rb") as f:
                new = f.read()
            if doc in olds:
                with open(olds[doc], "rb") as f:
                    old = f.read()
            else:
                if not a.rev:
                    raise SystemExit("!! 文書 %s の前の版がありません（--from か --old %s=ファイル）" % (doc, doc))
                old = old_bytes(a.rev, catalog.get(doc) or path)
            cache[doc] = (load(old), old, load(new), new)
        return cache[doc]

    counts = {"same": 0, "moved": 0, "flagged": 0}
    report = []
    for i in range(1, len(lines)):
        if not lines[i]:
            continue
        cells = lines[i].split("\t")
        width = len(cells)
        cells += [""] * (len(head) - len(cells))
        touched = set()

        def put(c, value):
            if cells[col[c]] != value:
                cells[col[c]] = value
                touched.add(col[c])

        doc = cells[col["doc"]] if "doc" in col else a.doc
        sid = cells[col["seg_id"]]
        old_segs, old, new_segs, new = segs_of(doc)
        problem, moves = None, []
        if sid not in old_segs or sid not in new_segs:
            problem = "セグメント %s が無い" % sid
        else:
            for c in ("w", CORRECTED):
                if c not in col or not cells[col[c]].strip():
                    continue
                wi = int(cells[col[c]])
                nw, nphr, why = remap(old_segs[sid], old, new_segs[sid], new, wi)
                if nw is None:
                    problem, moves = why, []
                    break
                moves.append((c, wi, nw, nphr, why))
        for c, wi, nw, nphr, why in moves:
            put(c, str(nw))
            if c == "w" and "phr" in col:
                put("phr", str(nphr) if nphr else "")
            if why:
                problem = (problem + "・" if problem else "") + why
        if problem:
            old_w = next((wi for c, wi, *_ in moves if c == "w"), cells[col["w"]])
            mark = "%s%s（--from %s。前は w=%s）】" % (MARK, problem, a.rev or "ファイル", old_w)
            current = cells[col[note]] if note else ""
            if note and (touched or MARK not in current):    # 位置が動かず、印がもうあれば、前の印のまま
                kept = re.sub(re.escape(MARK) + r"[^】]*】", "", current).strip()
                put(note, (kept + " " + mark).strip())
            counts["flagged"] += 1
            report.append("  ! %d 行目 %s %s: %s" % (i + 1, doc, sid, problem))
        elif touched:
            counts["moved"] += 1
        else:
            counts["same"] += 1
        lines[i] = "\t".join(cells[:max([width] + [k + 1 for k in touched])])
    out = eol.join(lines) + (eol if final else "")
    print("%s: 変わらない %d 行・位置を直した %d 行・印を付けた %d 行" % (a.tsv, counts["same"], counts["moved"], counts["flagged"]))
    for r in report:
        print(r)
    if out == text:
        print("（変更なし）")
    elif a.write:
        with open(a.tsv, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        print("→ 書き込みました")
    else:
        print("（表示だけ。--write で書き込む）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
