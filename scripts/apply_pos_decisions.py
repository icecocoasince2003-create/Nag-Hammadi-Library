#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_pos_decisions.py — 品詞をそろえる判断表（pos_harmonization.tsv）のうち、承認した行だけを TEI に当てはめる

判断表 source/nhc_fulltext_split/proposals/pos_harmonization.tsv の行のうち、状態が「承認」か「修正して承認」の行だけを読み、
対象の <w> の @type（品詞）だけを、文字列の置き換えで変える（XML を書き出し直さない。ほかの属性・本文・字下げは変えない）。
承認していない行（案・却下・保留など）は当てはめない。判断は確認作業の画面（review.html のキュー「⑤ 品詞をそろえる」）で行う。

行の種類（列「種類」）:
  語形  列「当てはめる変更」に「文書:今の品詞>新しい品詞」を「; 」で区切って並べる（例 eugnostos:REL>CREL; republic:ART>CREL）。
        その文書の、語形（列「語形」。<w> の文字）が同じで品詞が「今の品詞」の <w> を、すべて「新しい品詞」にする。
        文書は data/catalog.xml の doc-… から「doc-」を除いたもの（eugnostos・republic など）。エウグノストスは III,3 の証本だけ。
        列「暫定版にも当てはめるか」が「はい」なら、同じ変更を自動注釈の暫定版（source/nhc_fulltext_split/tei/ のうち
        resp="#morph-auto" か "#morph-reference" の <w> のある文書）の、同じ語形・同じ品詞の <w> にも当てはめる。
        「当てはめる変更」が空の行（1 か所ずつ見直すもの、変えないもの）は何もしない。
  箇所  列「文書」「seg_id」「w」（その <s> の中で何番目の <w> か。1 から）の 1 語。「当てはめる変更」は「今の品詞>新しい品詞」。
        その語の品詞が「今の品詞」で、語形が列「語形」と同じときだけ変える（もう「新しい品詞」なら、当てはめ済みとして飛ばす）。

変えたファイルの <revisionDesc> に、変えた数を 1 行で記録する（<change>。そのファイルの並び（新しい順か古い順か）に合わせる）。
書き込む前に、品詞のほかは何も変わっていないこと（語・属性・ほかの要素）と、変える数が予定どおりであることを確かめる。

使い方（リポジトリのルートで）:
  python3 scripts/apply_pos_decisions.py                 当てはめる内容を表示するだけ（書き込まない）
  python3 scripts/apply_pos_decisions.py --write         書き込む
  python3 scripts/apply_pos_decisions.py 表.tsv --file eugnostos=複製.xml   別の表・別のファイルで（試すとき）

当てはめたあと: python3 scripts/check_tei.py、python3 scripts/build_site.py（data/pos_labels.json などを作り直す）、
自動注釈の精度の検証（source/nhc_fulltext_split/evaluation/evaluate_republic.py）を走らせ直して、結果の変化を確かめる。
終了コード: 0 = 問題なし、1 = 問題あり（何も書き込んでいない）。
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "source", "nhc_fulltext_split", "proposals", "pos_harmonization.tsv")
TEI_DIR = os.path.join(ROOT, "source", "nhc_fulltext_split", "tei")
CATALOG = os.path.join(ROOT, "data", "catalog.xml")
POS_LABELS = os.path.join(ROOT, "data", "pos_labels.json")
T = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
APPROVED = ("承認", "修正して承認")
WITNESS = {"eugnostos": "wit-III"}              # 2 つの証本のある文書は、注釈のある証本だけ

W_START = re.compile(r"<w\b[^>]*>")
TYPE_ATTR = re.compile(r'\btype="([^"]*)"')


def read_table(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = f.read().split("\n")
    header = lines[0].rstrip("\r").split("\t")
    rows = []
    for no, line in enumerate(lines[1:], 2):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        cells = line.split("\t")
        cells += [""] * (len(header) - len(cells))
        r = dict(zip(header, cells))
        r["_where"] = "%s:%d" % (os.path.basename(path), no)
        rows.append(r)
    return header, rows


def load_catalog():
    out = {}
    for b in ET.parse(CATALOG).getroot().iter(T + "bibl"):
        did = b.get(XID) or ""
        if b.get("type") == "document" and did.startswith("doc-"):
            for r in b.findall(T + "ref"):
                if r.get("type") == "xml" and r.get("target"):
                    out[did[4:]] = os.path.normpath(os.path.join(ROOT, r.get("target")))
    return out


def draft_files():
    out = []
    for p in sorted(glob.glob(os.path.join(TEI_DIR, "*.xml"))):
        with open(p, encoding="utf-8") as f:
            s = f.read()
        if 'resp="#morph-auto"' in s or 'resp="#morph-reference"' in s:
            out.append(p)
    return out


def words(text, witness=None):
    """<w> の開始タグ（正規表現の一致）と、その <w> の（<s> の id, <s> の中の番号, 語形, 品詞）の一覧（文書の順）。
    witness があれば、その <text> の中の <s> の <w> だけ。"""
    root = ET.fromstring(text.encode("utf-8"))
    pos = {}
    for t in root.iter(T + "text"):
        if witness and t.get(XID) != witness:
            continue
        for s in t.iter(T + "s"):
            for i, w in enumerate(s.iter(T + "w"), 1):
                pos[id(w)] = (s.get(XID), i)
    all_w = list(root.iter(T + "w"))
    starts = list(W_START.finditer(text))
    if len(starts) != len(all_w):
        raise ValueError("開始タグ <w …> の数（%d）と <w> の数（%d）が合いません" % (len(starts), len(all_w)))
    out = []
    for m, w in zip(starts, all_w):
        if id(w) in pos:
            seg, i = pos[id(w)]
            out.append((m, (seg, i, "".join(w.itertext()).strip(), w.get("type") or "", None)))
    return out


def plan_file(path, text, changes, witness=None, locked=(), quiet=False):
    """changes: [(種類, 行, 語形, 今, 新, seg, w)]。(置き換える開始タグの位置 → 新しい品詞, 問題, 注意, 数)。
    locked: 箇所の行で決めた (seg, w)。語形の行はそこを変えない（箇所の行のほうを優先する。2 回目の実行で戻さないため）。
    quiet: 当てはまる語の無いことを注意に出さない（暫定版の 39 文書に同じ変更を当てるとき）"""
    problems, notes, edits = [], [], {}
    counts = Counter()
    ws = words(text, witness)
    by_pos = {(seg, i): (m, f, ty) for m, (seg, i, f, ty, _) in ws}
    for kind, row, form, old, new, seg, wi in changes:
        if kind == "語形":
            hit = 0
            for m, (s, i, f, ty, _) in ws:
                if f == form and ty == old and (s, i) not in locked:
                    if m.start() in edits and edits[m.start()] != new:
                        problems.append("%s: %s の %s w=%d を 2 つの行が違う品詞にしようとしています" % (row["_where"], os.path.basename(path), s, i))
                    edits[m.start()] = new
                    hit += 1
            counts["%s %s>%s" % (form, old, new)] += hit
            if not hit and not quiet:
                notes.append("%s: %s に「%s」で品詞 %s の語はありません（当てはめ済みか、対象なし）" % (row["_where"], os.path.basename(path), form, old))
        else:
            got = by_pos.get((seg, wi))
            if got is None:
                problems.append("%s: %s に %s の %d 番目の <w> がありません" % (row["_where"], os.path.basename(path), seg, wi))
                continue
            m, f, ty = got
            if f != form:
                problems.append("%s: %s w=%d の語形は「%s」で、表の「%s」と違います" % (row["_where"], seg, wi, f, form))
            elif ty == new:
                notes.append("%s: %s w=%d はもう %s です（当てはめ済み）" % (row["_where"], seg, wi, new))
            elif ty != old:
                problems.append("%s: %s w=%d の品詞は %s で、表の今の品詞 %s と違います" % (row["_where"], seg, wi, ty, old))
            else:
                edits[m.start()] = new
                counts["%s %s>%s" % (form, old, new)] += 1
    return edits, problems, notes, counts


def change_line(text, summary):
    """<revisionDesc> に <change> を 1 行足す。そのファイルの並び（新しい順・古い順）に合わせる。"""
    today = datetime.date.today().isoformat()
    body = ('<change when="%s">Part-of-speech tags (@type) changed as approved in '
            'source/nhc_fulltext_split/proposals/pos_harmonization.tsv (scripts/apply_pos_decisions.py): %s.</change>' % (today, summary))
    m = re.search(r"<revisionDesc>(.*?)</revisionDesc>", text, re.S)
    if not m:
        return None
    dates = re.findall(r'<change when="([0-9-]+)"', m.group(1))
    first = re.search(r"\n(\s*)<change\b", m.group(1))
    indent = first.group(1) if first else "      "
    if len(dates) > 1 and dates[0] > dates[-1]:                  # 新しい順: 先頭に
        pos = m.start(1) + first.start() + 1
        return text[:pos] + indent + body + "\n" + text[pos:]
    close = text.rfind("</revisionDesc>", m.start(), m.end())
    line_start = text.rfind("\n", 0, close) + 1
    return text[:line_start] + indent + body + "\n" + text[line_start:]


def apply_edits(text, edits):
    out, last = [], 0
    for pos in sorted(edits):
        m = W_START.match(text, pos)
        tag = m.group(0)
        new_tag, n = TYPE_ATTR.subn('type="%s"' % edits[pos], tag, count=1)
        if n != 1:
            raise ValueError("@type の無い <w> を変えようとしました: %s" % tag)
        out.append(text[last:pos])
        out.append(new_tag)
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def verify(old, new, edits):
    """品詞のほかは同じこと（<revisionDesc> を除く）と、変わった品詞の数が予定どおりなことを確かめる。"""
    def tree(t):
        root = ET.fromstring(t.encode("utf-8"))
        for parent in root.iter():
            for c in list(parent):
                if c.tag == T + "revisionDesc":
                    parent.remove(c)
        return list(root.iter())
    ea, eb = tree(old), tree(new)
    if len(ea) != len(eb):
        return ["要素の数が変わりました"]
    changed = 0
    for x, y in zip(ea, eb):
        if x.tag != y.tag or (x.text or "") != (y.text or "") or (x.tail or "") != (y.tail or ""):
            return ["本文か要素が変わりました: <%s>" % x.tag.split("}")[-1]]
        ax, ay = dict(x.attrib), dict(y.attrib)
        if x.tag == T + "w" and ax.get("type") != ay.get("type"):
            changed += 1
            ax.pop("type", None)
            ay.pop("type", None)
        if ax != ay:
            return ["属性が変わりました: <%s>" % x.tag.split("}")[-1]]
    return [] if changed == len(edits) else ["変わった品詞の数（%d）が予定（%d）と違います" % (changed, len(edits))]


def main(argv=None):
    ap = argparse.ArgumentParser(description="品詞をそろえる判断表のうち、承認した行だけを当てはめる")
    ap.add_argument("table", nargs="?", default=TABLE, help="判断表（既定 source/nhc_fulltext_split/proposals/pos_harmonization.tsv）")
    ap.add_argument("--write", action="store_true", help="書き込む（付けなければ表示するだけ）")
    ap.add_argument("--file", action="append", default=[], metavar="文書=ファイル", help="文書の代わりに使うファイル（試すとき）")
    ap.add_argument("--drafts", help="暫定版のフォルダ（試すとき。既定 source/nhc_fulltext_split/tei）")
    args = ap.parse_args(argv)

    with open(POS_LABELS, encoding="utf-8") as f:
        listed = {t["tag"] for t in json.load(f)["tags"]}
    catalog = load_catalog()
    for it in args.file:
        k, _, p = it.partition("=")
        catalog[k] = os.path.abspath(p)
    header, rows = read_table(args.table)
    need = [c for c in ("種類", "語形", "当てはめる変更", "文書", "seg_id", "w", "暫定版にも当てはめるか", "状態") if c not in header]
    if need:
        print("判断表に必須の列がありません: " + ", ".join(need))
        return 1
    problems, notes = [], []
    per_file = defaultdict(list)                  # path → [(種類, 行, 語形, 今, 新, seg, w)]
    skipped = Counter()
    drafts = draft_files() if not args.drafts else sorted(glob.glob(os.path.join(args.drafts, "*.xml")))
    for r in rows:
        st = r["状態"].strip()
        if st not in APPROVED:
            skipped[st or "（空）"] += 1
            continue
        change = r["当てはめる変更"].strip()
        if not change:
            notes.append("%s: 承認されていますが「当てはめる変更」が空なので、何もしません（%s）" % (r["_where"], r["語形"]))
            continue
        for item in [x.strip() for x in change.split(";") if x.strip()]:
            m = re.fullmatch(r"(?:([^:]+):)?([^>\s]+)>([^>\s]+)", item)
            if not m:
                problems.append("%s: 「当てはめる変更」の書き方が違います: %s（文書:今の品詞>新しい品詞）" % (r["_where"], item))
                continue
            doc, old, new = m.group(1) or r["文書"].strip(), m.group(2), m.group(3)
            if new not in listed:
                problems.append("%s: 新しい品詞 %s は品詞の一覧（data/pos_labels.json）にありません" % (r["_where"], new))
                continue
            if r["種類"] == "箇所":
                if not re.fullmatch(r"[0-9]+", r["w"].strip()):
                    problems.append("%s: w が数ではありません" % r["_where"])
                    continue
                path = catalog.get(doc)
                if not path:
                    problems.append("%s: 文書「%s」が data/catalog.xml にありません" % (r["_where"], doc))
                    continue
                per_file[path].append(("箇所", r, r["語形"], old, new, r["seg_id"].strip(), int(r["w"])))
            elif r["種類"] == "語形":
                path = catalog.get(doc)
                if not path:
                    problems.append("%s: 文書「%s」が data/catalog.xml にありません" % (r["_where"], doc))
                    continue
                per_file[path].append(("語形", r, r["語形"], old, new, None, None))
                if r["暫定版にも当てはめるか"].strip() == "はい":
                    for p in drafts:
                        per_file[p].append(("語形", r, r["語形"], old, new, None, None))
            else:
                problems.append("%s: 種類「%s」は 語形 か 箇所 です" % (r["_where"], r["種類"]))
    print("判断表: %s（%d 行。当てはめる行 %d）" % (os.path.relpath(args.table, ROOT) if os.path.abspath(args.table).startswith(ROOT) else args.table,
                                            len(rows), sum(1 for r in rows if r["状態"].strip() in APPROVED)))
    for st, n in sorted(skipped.items()):
        print("  当てはめない行 %d（状態が「%s」）" % (n, st))

    results = []
    witness_of = {v: WITNESS.get(k) for k, v in catalog.items()}
    named = {catalog.get(r["文書"].strip()) for r in rows if r["文書"].strip()} | {catalog.get(k) for k in ("eugnostos", "republic")}
    for path, changes in sorted(per_file.items()):
        with open(path, encoding="utf-8", newline="") as f:
            old = f.read()
        locked = {(c[5], c[6]) for c in changes if c[0] == "箇所"}
        try:
            edits, p, n, counts = plan_file(path, old, changes, witness_of.get(path), locked, quiet=path not in named)
        except (ValueError, ET.ParseError) as e:
            problems.append("%s: 読めません: %s" % (path, e))
            continue
        problems += p
        notes += n
        if not edits:
            continue
        summary = ", ".join("%s ×%d" % (k, v) for k, v in sorted(counts.items()) if v)
        new = apply_edits(old, edits)
        new2 = change_line(new, summary)
        if new2 is None:
            notes.append("%s: <revisionDesc> が無いので、変更の記録を書いていません" % os.path.basename(path))
            new2 = new
        v = verify(old, new2, edits)
        if v:
            problems += ["%s: %s" % (os.path.basename(path), x) for x in v]
            continue
        shown = os.path.relpath(path, ROOT) if os.path.abspath(path).startswith(ROOT) else path
        print("%s: 品詞を %d 語変える（%s）" % (shown, len(edits), summary))
        results.append((path, new2))
    if notes:
        print("\n注意（%d 件）:" % len(notes))
        for x in notes:
            print("  - " + x)
    if problems:
        print("\n問題（%d 件）。何も書き込んでいません:" % len(problems))
        for x in problems:
            print("  ! " + x)
        return 1
    if not results:
        print("\n変えるものはありません（変更なし）")
        return 0
    if not args.write:
        print("\n%d ファイルで品詞を変えます（検証済み）。書き込むには --write を付けて実行します" % len(results))
        return 0
    for path, new in results:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    print("\n%d ファイルに書き込みました。python3 scripts/check_tei.py と python3 scripts/build_site.py を実行してください" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
