#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_segments.py — 長いセグメント（<s>）を、TSV で指定した位置で 2 つ以上に分ける

元ファイルの 1 行がそのままセグメントになっているため、数百〜数千形態素の <s> がある（II,1・II,2・II,5・XI,1・XI,2。
source/nhc_fulltext_split/proposals/README_ja.md）。このスクリプトは、決めた位置でセグメントを分ける。既存の内容は
変えず、分け目に </s> と新しい <s …> を差し込むだけにする（insert_breaks.py と同じく、XML を書き出し直さない）。
2026-11-23 の時点では案で、リポジトリのデータにはまだ使っていない。

入力（TSV。UTF-8・BOM なし・改行 LF・タブ区切り。1 行目が見出し）:

  列       必須  内容
  doc      ○    文書（insert_breaks.py と同じ。data/catalog.xml の doc-… から「doc-」を除いたもの）
  seg_id   ○    分けるセグメント（<s>）の xml:id
  w        ○    新しいセグメントの最初の <w>。その <s> の中の何番目の <w> か（1 から。<s> の子孫の <w> を文書の順に
                 数える）。語群（<phr>）のある文書では、語群の最初の <w> でなければならない（語群の途中では分けない）。
                 語群の無い文書ではどの <w> でもよい。1 は書けない（最初の部分が空になる）
  place          欠損（<gap>）のすぐあとの <w> を指したとき、その <gap> も新しいセグメントに入れるなら before-gap
  phr            確認用（任意）。その <w> を含む語群の番号。書けば照合する
  form           確認用（任意）。その <w> の語形。書けば照合する
  note           メモ（スクリプトは使わない）

  1 つのセグメントを何か所でも分けられる（同じ seg_id の行を並べる）。

分けたあとの ID と番号:
  * 最初の部分は、元の xml:id と @n のまま（リンク #seg-<元の id>、投稿・ブックマークの seg_id、引用の「§12」は、
    これまでどおり同じ位置（元のセグメントの始まり）を指す）。
  * 続く部分の xml:id は「元の id ＋ _a、_b、…」（z のあとは _aa、_ab、…）。@n は「元の n ＋ a、b、…」
    （n="12" を 3 つに分けると §12・§12a・§12b）。どちらも同じ記号を使う（II-7503917_a は §15a）。
    その id がファイルにもうあれば止まる。
  * 新しい <s> には xml:id と n だけを付ける。元の <s> にほかの属性（type・corresp など）があれば報告する（写さない）。
  * 分け目の直前にある区切り（<pb>・<lb>）は、新しいセグメントの先頭に入る（insert_breaks.py の「セグメントの最初の
    区切りは <s> の中の先頭」と同じ）。直前の <gap> は前の部分に残る（place=before-gap なら新しい部分に入る）。

確かめること（1 つでも当たれば、どのファイルにも書き込まず、終了コード 1）:
  * TSV の形、doc・seg_id・w が見つかること、w が語群の最初の <w> であること、phr・form が一致すること、
    新しい xml:id がまだ無いこと
  * 書き込む前の検証: 整形式であること、分けた部分をつなぎ直すと元のファイルと内容が 1 つも違わないこと、本文（語・
    欠損・区切り）の並びが変わっていないこと、元の xml:id がすべて残っていること、scripts/check_tei.py の点検で
    新しい問題が出ないこと
報告するだけで変えないもの:
  * 分けたセグメントの id を指しているもの。同じファイルの @corresp・@target（対訳の <seg corresp> など）と、リポジトリの
    ほかのファイル（data/parallels.xml、サイトの HTML・JS・JSON、scripts/、README、要確認の一覧の TSV など）に
    書かれた id。分けたあとも、元の id は最初の部分を指す。続きの部分の内容を指したいもの（並行箇所・対訳）は手で直す。
  * ヘッダーの <extent> のセグメント数（手で直す）。カタログの件数は python3 scripts/sync_nhc_catalog.py --write で直る。
  * 利用者の投稿・ブックマーク（Supabase の seg_id）は、リポジトリからは調べられない。

使い方（リポジトリのルートで）:
  python3 scripts/split_segments.py 分け目.tsv                     分け方と報告を表示するだけ（書き込まない）
  python3 scripts/split_segments.py 分け目.tsv --write             書き込む
  python3 scripts/split_segments.py 分け目.tsv --file II-2=複製.xml  doc の代わりに別のファイルで（試すとき）
終了コード: 0 = 問題なし、1 = 問題あり（何も書き込んでいない）。

読み込みと検証の関数は scripts/insert_breaks.py のものを使う。
"""
import argparse
import html
import os
import re
import sys
import xml.etree.ElementTree as ET
import xml.parsers.expat
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insert_breaks as ib                                   # noqa: E402

ROOT = ib.ROOT
TEI = ib.TEI
XID = ib.XID
COLUMNS = ("doc", "seg_id", "w", "place", "phr", "form", "note")
REQUIRED = ("doc", "seg_id", "w")
TEXT_EXT = (".xml", ".html", ".js", ".cjs", ".json", ".py", ".md", ".tsv", ".txt", ".sql", ".csv", ".cff", ".yml", ".yaml")


def suffix(k):
    """0 → a, 25 → z, 26 → aa, 27 → ab …"""
    out = ""
    k += 1
    while k:
        k, r = divmod(k - 1, 26)
        out = chr(ord("a") + r) + out
    return out


def check_row(r, seg, data, problems):
    """1 行を確かめ、分け目の要素（<s> の子）を返す。問題があれば None。"""
    where = r["_where"]
    bad = lambda msg: problems.append("%s: %s" % (where, msg))
    place = (r.get("place") or "").strip()
    if place not in ("", "w", "before-gap"):
        bad("place は空欄か before-gap です: %r" % place)
        return None
    if not re.fullmatch(r"[0-9]+", r["w"] or ""):
        bad("w は 2 以上の整数で書きます: %r" % r["w"])
        return None
    wi = int(r["w"])
    if not 2 <= wi <= len(seg.ws):
        bad("w=%d では分けられません（%s の <w> は %d 個。w は 2 から %d まで）" % (wi, seg.id, len(seg.ws), len(seg.ws)))
        return None
    w = seg.ws[wi - 1]
    form, phr = r.get("form") or "", r.get("phr") or ""
    if form and form != ib.w_text(data, w):
        bad("form「%s」が、%s の %d 番目の <w>「%s」と違います" % (form, seg.id, wi, ib.w_text(data, w)))
        return None
    if phr and (not phr.isdigit() or int(phr) != seg.wphr[wi - 1]):
        bad("phr=%s ですが、%s の %d 番目の <w> は %s" % (phr, seg.id, wi, ("%d 番目の <phr> の中" % seg.wphr[wi - 1]) if seg.wphr[wi - 1] else "語群に入っていません"))
        return None
    i = seg.item_index_of_w(wi)
    if place == "before-gap":
        if i == 0 or seg.items[i - 1][0] != "gap":
            bad("place=before-gap ですが、%s の %d 番目の <w> の直前は <gap> ではありません" % (seg.id, wi))
            return None
        anchor = seg.items[i - 1][1]
    else:
        anchor = w
    anchor = ib.climb(anchor)
    if anchor.parent is not seg.node:
        if seg.wphr[wi - 1]:
            bad("%s の %d 番目の <w>「%s」は語群（%d 番目の <phr>）の途中です。分けるのは語群の境目だけです（先に <phr> を直す）" % (
                seg.id, wi, ib.w_text(data, w), seg.wphr[wi - 1]))
        else:
            bad("%s の %d 番目の <w> の前では分けられません（<s> の直接の子ではない）" % (seg.id, wi))
        return None
    # 直前の区切り（pb・lb など）は新しい部分の先頭へ
    kids = seg.node.children
    k = kids.index(anchor)
    while k > 0 and kids[k - 1].tag in ib.MILESTONES:
        k -= 1
    return kids[k]


def plan(path, data, rows):
    """1 ファイル分の差し込み。(差し込み, 表示する行, 問題, 注意, 新しい id → (元の id, n), 分けた元の id)。"""
    problems, notes, lines, inserts, new_ids, split_ids = [], [], [], [], {}, []
    try:
        top = ib.parse(data)
    except xml.parsers.expat.ExpatError as e:
        return [], [], ["%s: XML として読めません: %s" % (path, e)], [], {}, []
    segs, dups = ib.segments(top)
    problems += ["%s: セグメントの xml:id が重複しています: %s" % (path, d) for d in dups]
    all_ids = {n.attrs["xml:id"] for n in ib.iter_nodes(top) if "xml:id" in n.attrs}
    ns_by_wit = defaultdict(set)
    for s in segs.values():
        ns_by_wit[s.witness].add(s.n)
    nl = b"\r\n" if b"\r\n" in data[:4096] else b"\n"
    by_seg = defaultdict(list)
    for r in rows:
        seg = segs.get(r["seg_id"])
        if seg is None:
            problems.append("%s: seg_id「%s」が %s にありません" % (r["_where"], r["seg_id"], ib.shown(path)))
            continue
        if seg.id + "_a" in all_ids:
            problems.append("%s: %s はもう分けてあります（%s_a がある）。続きの部分をさらに分けるときは、その部分の id（%s_a など）を"
                            " seg_id に書きます" % (r["_where"], seg.id, seg.id, seg.id))
            continue
        cut = check_row(r, seg, data, problems)
        if cut is not None:
            by_seg[seg.id].append((int(r["w"]), cut, r))
    for sid, cuts in by_seg.items():
        seg = segs[sid]
        cuts.sort(key=lambda c: c[0])
        seen = {}
        ok = True
        for wi, cut, r in cuts:
            if cut.start in seen:
                problems.append("%s: 同じ位置（%s の w=%d）で分ける行がもう 1 行あります（%s）" % (r["_where"], sid, wi, seen[cut.start]))
                ok = False
            seen[cut.start] = r["_where"]
        if not ok:
            continue
        extra = sorted(set(seg.node.attrs) - {"xml:id", "n"})
        if extra:
            notes.append("%s: 元の <s> の属性 %s は、新しい部分には写しません（必要なら手で付ける）" % (
                sid, ", ".join('%s="%s"' % (a, seg.node.attrs[a]) for a in extra)))
        s_ind = ib.line_indent(data, seg.node.start)
        bounds = [1] + [c[0] for c in cuts] + [len(seg.ws) + 1]
        lines.append("  %s（§%s、%d 形態素）を %d 個に分ける:" % (sid, seg.n, len(seg.ws), len(cuts) + 1))
        lines.append("    %-24s §%-6s w=%d–%d（%d 形態素）【%s …】" % (sid, seg.n, 1, bounds[1] - 1, bounds[1] - 1, ib.context(data, seg, 1, 0, 3).lstrip("|")))
        for k, (wi, cut, r) in enumerate(cuts):
            sfx = suffix(k)
            nid, nn = "%s_%s" % (sid, sfx), (seg.n + sfx if seg.n else "")
            if nid in all_ids or nid in new_ids:
                problems.append("%s: 新しい xml:id「%s」はもうあります" % (r["_where"], nid))
                continue
            if nn and nn in ns_by_wit[seg.witness]:
                notes.append("%s: 新しい @n「%s」と同じ番号のセグメントが、同じ証本にもうあります" % (r["_where"], nn))
            new_ids[nid] = (sid, nn)
            tag = ('<s xml:id="%s" n="%s">' % (html.escape(nid, quote=True), html.escape(nn, quote=True))).encode("utf-8")
            ind = ib.line_indent(data, cut.start)
            if ind is not None and s_ind is not None:
                pos = cut.start - len(ind)                 # 行の頭に差し込む
                text = s_ind + b"</s>" + nl + s_ind + tag + nl
            else:
                pos, text = cut.start, b"</s>" + tag
            inserts.append((pos, k, text))
            end = bounds[k + 2] - 1
            moved = [m for m in seg.miles if cut.start <= m[0].start < (cuts[k + 1][1].start if k + 1 < len(cuts) else seg.node.end)]
            lines.append("    %-24s §%-6s w=%d–%d（%d 形態素）【%s】%s" % (
                nid, nn, wi, end, end - wi + 1, ib.context(data, seg, wi, 2, 3),
                "  区切り %d 個を含む" % len(moved) if moved else ""))
        split_ids.append(sid)
    return inserts, lines, problems, notes, new_ids, split_ids


# ---------------------------------------------------------------------------------------------------------
# 検証

def merged_canon(new, new_ids):
    """新しい部分を前のセグメントにつなぎ直した形（比べるため）。"""
    root = ET.fromstring(new)
    pairs = [(parent, child) for parent in root.iter() for child in parent
             if child.tag == TEI + "s" and child.get(XID) in new_ids]
    for parent, child in pairs:                      # 文書の順。続きの部分は、直前に残っている <s> につなぐ
        kids = list(parent)
        prev = kids[kids.index(child) - 1]
        for c in list(child):
            prev.append(c)
        parent.remove(child)
    return ib.canon(ET.tostring(root), drop=())


def sequence(data):
    """証本ごとの本文の並び（語・欠損・区切り）を文書の順に。"""
    top = ib.parse(data)
    out = defaultdict(list)

    def walk(node, wit, in_s):
        if node.tag == "text" and node.attrs.get("type") == "witness":
            wit = node.attrs.get("xml:id") or wit
        if node.tag == "s" and node.attrs.get("xml:id"):
            in_s = True
        if in_s and node.tag == "w":
            out[wit].append(("w", ib.w_text(data, node)))
            return
        if in_s and node.tag == "gap":
            out[wit].append(("gap", tuple(sorted(node.attrs.items()))))
        if in_s and node.tag in ib.MILESTONES:
            out[wit].append((node.tag, tuple(sorted(node.attrs.items()))))
        for c in node.children:
            walk(c, wit, in_s)

    walk(top, None, False)
    return out


def verify(path, old, new, new_ids, split_ids):
    problems = []
    try:
        ET.fromstring(new)
        top_new = ib.parse(new)
    except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
        return ["分けた結果が整形式の XML になりません: %s" % e]
    if ib.canon(old, drop=()) != merged_canon(new, set(new_ids)):
        problems.append("分けた部分をつなぎ直しても元のファイルと同じになりません（分け目以外のものが変わった）")
    if sequence(old) != sequence(new):
        problems.append("本文（語・欠損・区切り）の並びが変わりました")
    ids_old = {n.attrs["xml:id"] for n in ib.iter_nodes(ib.parse(old)) if "xml:id" in n.attrs}
    ids_new = {n.attrs["xml:id"] for n in ib.iter_nodes(top_new) if "xml:id" in n.attrs}
    if ids_old - ids_new:
        problems.append("元の xml:id が無くなりました: %s" % ", ".join(sorted(ids_old - ids_new)))
    if ids_new - ids_old != set(new_ids):
        problems.append("新しい xml:id が予定と違います: %s" % ", ".join(sorted((ids_new - ids_old) ^ set(new_ids))))
    segs_new, _ = ib.segments(top_new)
    for nid, (sid, nn) in new_ids.items():
        s = segs_new.get(nid)
        if s is None or not s.ws:
            problems.append("%s: 新しいセグメントが無いか、語が 1 つもありません" % nid)
        elif s.node.attrs != {"xml:id": nid, "n": nn}:
            problems.append("%s: 新しい <s> の属性が予定（xml:id と n だけ）と違います: %s" % (nid, s.node.attrs))
        elif s.witness != segs_new[sid].witness or s.node.parent is not segs_new[sid].node.parent:
            problems.append("%s: 新しい <s> が元のセグメントと同じ <ab> の中にありません" % nid)
    for sid in split_ids:
        if not segs_new[sid].ws:
            problems.append("%s: 最初の部分に語が 1 つもありません" % sid)
    extra = ib.check_tei_problems(new, path)
    if extra is None:
        problems.append("scripts/check_tei.py を読み込めず、点検できませんでした")
    else:
        problems += ["check_tei.py: " + p for p in extra]
    return problems


# ---------------------------------------------------------------------------------------------------------
# 報告: 分けたセグメントを指しているもの

def references(path, data, ids):
    """(同じファイルの中, リポジトリのほかのファイル) の行のリスト。"""
    if not ids:
        return [], []
    pat = re.compile(r"(?<![\w.])(%s)(?![\w-])" % "|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True)))
    inside = []
    text = data.decode("utf-8")
    for no, line in enumerate(text.split("\n"), 1):
        for m in pat.finditer(line):
            before = line[:m.start()]
            if re.search(r'xml:id="$', before):
                continue
            inside.append("%s:%d: %s" % (ib.shown(path), no, line.strip()[:160]))
            break
    other = []
    target = os.path.abspath(path)
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "__pycache__")]
        for fn in files:
            p = os.path.join(d, fn)
            if not fn.endswith(TEXT_EXT) or os.path.abspath(p) == target or os.path.getsize(p) > 50_000_000:
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    t = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            if not pat.search(t):
                continue
            hits = [(no, line) for no, line in enumerate(t.split("\n"), 1)
                    if any(not re.search(r'xml:id="$', line[:m.start()]) for m in pat.finditer(line))]
            if not hits:
                continue                             # 同じ id を定義しているだけの複製（tests/fixtures など）
            first = "; ".join("%d: %s" % (no, line.strip()[:120]) for no, line in hits[:2])
            other.append("%s（%d 行）: %s%s" % (os.path.relpath(p, ROOT), len(hits), first, " …" if len(hits) > 2 else ""))
    return inside, other


def extent_note(data):
    """ヘッダーの <extent> のセグメント数と、実際の数。"""
    root = ET.fromstring(data)
    m = next((x for x in root.iter(TEI + "measure") if x.get("unit") == "segment"), None)
    n = sum(1 for t in root.iter(TEI + "text") if t.get("type") == "witness" for s in t.iter(TEI + "s") if s.get(XID))
    if m is not None and m.get("quantity") != str(n):
        return "ヘッダーの <extent> は segment %s、分けたあとの本文は %d（<measure unit=\"segment\"> を手で直す）" % (m.get("quantity"), n)
    return None


# ---------------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="TSV で指定した位置でセグメント（<s>）を分ける")
    ap.add_argument("tsv", nargs="+", help="分け目の TSV（列: doc, seg_id, w［, place, phr, form, note］）")
    ap.add_argument("--write", action="store_true", help="書き込む（付けなければ表示するだけ）")
    ap.add_argument("--file", action="append", metavar="文書=ファイル", help="doc の代わりに使うファイル（試すとき）")
    ap.add_argument("--catalog", default=ib.CATALOG, help="カタログ（既定 data/catalog.xml）")
    args = ap.parse_args(argv)

    problems, notes, rows = [], [], []
    overrides, p = ib.parse_overrides(args.file)
    problems += p
    for t in args.tsv:
        r, p, n = ib.read_tsv(t, COLUMNS, REQUIRED)
        rows += r
        problems += p
        notes += n
    by_file, p = ib.resolve_docs(rows, ib.load_catalog(args.catalog), overrides)
    problems += p

    results = []
    for path, rs in by_file.items():
        with open(path, "rb") as f:
            old = f.read()
        inserts, lines, p, n, new_ids, split_ids = plan(path, old, rs)
        problems += p
        notes += n
        print("%s:" % ib.shown(path))
        for line in lines:
            print(line)
        if p or not inserts:
            continue
        new = ib.apply_inserts(old, inserts)
        v = verify(path, old, new, new_ids, split_ids)
        if v:
            problems += ["%s: %s" % (ib.shown(path), x) for x in v]
            continue
        inside, other = references(path, old, split_ids)
        if inside or other:
            print("\n  分けたセグメントの id を指しているもの（変えていない。分けたあとも最初の部分を指す。続きの部分を指すべきものは手で直す）:")
            for x in inside + other:
                print("    - " + x)
        else:
            print("\n  分けたセグメントの id を指しているものは、リポジトリの中にはありません")
        print("  （利用者の投稿・ブックマークの seg_id は Supabase にあり、ここでは調べられません）")
        e = extent_note(new)
        if e:
            notes.append("%s: %s" % (ib.shown(path), e))
        results.append((path, new, new_ids))

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
        print("\n分けるものはありません（変更なし）")
        return 0
    total = sum(len(n) for _, _, n in results)
    if not args.write:
        print("\n%d ファイルで、新しいセグメントが %d 個できます（検証済み）。書き込むには --write を付けて実行します" % (len(results), total))
        return 0
    for path, new, new_ids in results:
        ib.write_atomic(path, new)
        print("書き込みました: %s（新しいセグメント %d 個）" % (ib.shown(path), len(new_ids)))
    print("続けて python3 scripts/check_tei.py %s と、source/nhc_fulltext_split/ の文書なら"
          " python3 scripts/sync_nhc_catalog.py --write を実行してください" % " ".join(ib.shown(p) for p, _, _ in results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
