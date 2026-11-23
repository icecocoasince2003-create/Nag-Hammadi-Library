#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insert_breaks.py — 写本の頁（<pb>）・行（<lb>）の区切りを、TSV の指定どおりに TEI の本文へ入れる

校訂本と照らし合わせて決めた頁・行の区切りを TSV に書き、このスクリプトで TEI に足す。既存の内容（文字・語・
語群・欠損・xml:id・属性）は変えず、区切りの空要素（<pb n="…"/>・<lb n="…"/>）を足すだけにする。XML を
読み直して書き出すのではなく、元のファイルのバイト列に区切りの文字列を差し込む（字下げは周りに合わせる）。
書き方は data/republic_tei.xml（NHC VI,5）に合わせてある。

入力（TSV。UTF-8・BOM なし・改行 LF・タブ区切り。1 行目が見出し。空行は読み飛ばす。列の順は自由）:

  列       必須  内容
  doc      ○    文書。data/catalog.xml の <bibl type="document" xml:id="doc-…"> から「doc-」を除いたもの
                 （II-2、V-2、eugnostos、republic など）。ファイルは同じ項目の <ref type="xml"> で決まる
  seg_id   ○    セグメント（<s>）の xml:id
  w        ○    区切りを、その <s> の何番目の <w> の前に入れるか。1 から数える。<s> の子孫の <w> を文書の順に
                 数える（語群 <phr> の中の <w> も 1 つずつ数える）。end は「セグメント末尾の <gap> の前」
                 （place が before-gap のときだけ）
  type     ○    pb（改頁）か lb（改行）
  n        ○    頁番号・行番号。そのまま @n に入る
  char           語の途中で行（頁）が変わるとき、その <w> の何文字目の前で切れるか。0 から数える（1 以上、語の
                 文字数未満）。<w> の中に break="no" を付けて入れる。数えるのは文字だけで、上線などの合成記号は
                 前の文字に含める。<supplied>（復元した字）の中の字も数えるが、区切りを <supplied> の中には入れない
  place          欠損（<gap>）のすぐあとの <w> を指したとき、区切りを <gap> の前に入れるなら before-gap。
                 空欄（か w）なら <w> の直前（<gap> のあと）
  phr            確認用（任意）。その <w> を含む語群が <s> の中の何番目の <phr> か（1 から）。書けば照合する
  form           確認用（任意）。その <w> の語形（<supplied> の字を含む）。書けば照合する
  note           メモ（スクリプトは使わない）

  例:
    doc   seg_id           w   type  n   char  place  phr  form    note
    II-2  II-7503903_2206  1   pb    32                1    ⲛⲁ
    II-2  II-7503903_2206  1   lb    10                1    ⲛⲁ
    II-2  II-7503903_2206  16  lb    11    3            9    ⲁϥⲥϩⲁⲓⲥ  語の途中で改行

入る位置:
  * <w> が語群（<phr>）の最初の形態素なら、<phr> の前（語群と語群のあいだ）。語群の途中の <w> なら、<phr> の
    中のその <w> の前。語群の無いファイル（未注釈の文書）では <w> の前。
  * セグメントの最初の <w> の前に入れる区切りは、<s> の中の先頭（最初の子要素の前）に入る。セグメントのあいだ
    （</s> と <s> のあいだ）には入れない。
  * char を書いたときは <w> の中に入り、break="no" が付く（pb も同じ。republic_tei.xml の
    <pb n="51" break="no"/><lb n="1" break="no"/> の書き方）。語群の中で形態素と形態素のあいだに入る区切りには
    break を付けない（これも republic_tei.xml と同じ）。
  * 同じ位置に pb と lb を入れるときは pb を先に置く。
  * pb のあとに lb n="1" を自動では足さない。頁の最初の行も、lb の行として TSV に書く（republic_tei.xml でも、
    改頁のたびに <pb n="49"/><lb n="1"/> と両方が書いてある）。

確かめること（1 つでも当たれば、どのファイルにも何も書き込まず、終了コード 1）:
  * TSV の形（必須の列、知らない列、列の数）、doc・seg_id・w が見つかること、type・n・char・place が正しいこと、
    phr・form を書いたときは実際と一致すること
  * 同じ位置に同じ種類の区切りが n の違う値ですでにあること、同じ TSV に同じ位置・同じ種類の行が 2 つあること
  * char の位置が <supplied> の中（復元した字の途中）になること
  * 書き込む前の検証: 整形式の XML であること、pb・lb を除くと元のファイルと内容が 1 つも違わないこと（文字・語・
    語群・欠損・属性・xml:id）、各 <s> の語の並びが変わっていないこと、もとからあった区切りがそのまま残っている
    こと、足した区切りが指定どおりの位置にあること、scripts/check_tei.py の点検で新しい問題が出ないこと
同じ位置に同じ区切り（種類・n・break が同じ）がすでにあるときは、その行は何もしない（同じ TSV を 2 回実行しても
ファイルは変わらない）。
注意として表示するもの（終了コードは変えない）: 行番号が前の行の続きになっていない、頁番号が前の頁の続きに
なっていない、pb と同じ位置に lb が無い、同じ頁番号の pb がほかの位置にもある、n が数字でない、など。
欠損で行や頁が抜けていれば番号は飛ぶので、注意が出ても誤りとは限らない。

使い方（リポジトリのルートで）:
  python3 scripts/insert_breaks.py 区切り.tsv                     入れる位置を表示するだけ（書き込まない）
  python3 scripts/insert_breaks.py 区切り.tsv --write             書き込む
  python3 scripts/insert_breaks.py 区切り.tsv --file II-2=複製.xml  doc の代わりに別のファイルへ（試すとき）
  （TSV はいくつ並べてもよい。--file も何度でも書ける）
書き込んだあとは python3 scripts/check_tei.py <ファイル> を実行する。

終了コード: 0 = 問題なし（書き込んだ、または書き込むものが無かった）、1 = 問題あり（何も書き込んでいない）。

ほかのスクリプト（scripts/split_segments.py）が、ここの読み込み・検証の関数を使う。
"""
import argparse
import html
import os
import re
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import xml.parsers.expat
from bisect import bisect_right
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "catalog.xml")
TEI = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"

MILESTONES = ("pb", "cb", "lb", "milestone")          # 区切りの空要素
RANK = {"pb": 0, "cb": 1, "lb": 2, "milestone": 3}      # 同じ位置に並ぶときの順
TYPES = ("pb", "lb")                                   # この TSV で入れられるもの
COLUMNS = ("doc", "seg_id", "w", "type", "n", "char", "place", "phr", "form", "note")
REQUIRED = ("doc", "seg_id", "w", "type", "n")

TAG_RE = re.compile(rb'<(?:[^>"\']|"[^"]*"|\'[^\']*\')*>')
CONTENT_RE = re.compile(rb'<(?:[^>"\']|"[^"]*"|\'[^\']*\')*>|&[^;&<]*;|[^<&]+')


# ---------------------------------------------------------------------------------------------------------
# TSV とカタログ

def read_tsv(path, columns=COLUMNS, required=REQUIRED):
    """TSV を読む。(行の辞書のリスト, 問題のリスト, 注意のリスト)。行の辞書には '_where'（ファイル:行）が付く。"""
    rows, problems, notes = [], [], []
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        return [], ["%s: 読めません（%s）" % (path, e)], []
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
        notes.append("%s: 先頭に BOM があります（読み飛ばしました）" % path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return [], ["%s: UTF-8 として読めません（%s）" % (path, e)], notes
    header = None
    for lineno, line in enumerate(text.split("\n"), 1):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("\t")]
        where = "%s:%d" % (os.path.basename(path), lineno)
        if header is None:
            header = cells
            unknown = [c for c in header if c not in columns]
            missing = [c for c in required if c not in header]
            dup = sorted({c for c in header if header.count(c) > 1})
            if unknown:
                problems.append("%s: 知らない列があります: %s（使える列: %s）" % (where, ", ".join(unknown), ", ".join(columns)))
            if missing:
                problems.append("%s: 必須の列がありません: %s" % (where, ", ".join(missing)))
            if dup:
                problems.append("%s: 同じ名前の列が 2 つあります: %s" % (where, ", ".join(dup)))
            if unknown or missing or dup:
                return [], problems, notes
            continue
        if len(cells) > len(header):
            problems.append("%s: 列が見出しより多くあります（%d 列。見出しは %d 列）" % (where, len(cells), len(header)))
            continue
        cells += [""] * (len(header) - len(cells))
        row = dict(zip(header, cells))
        row["_where"] = where
        rows.append(row)
    if header is None:
        problems.append("%s: 見出しの行がありません" % path)
    return rows, problems, notes


def load_catalog(path=CATALOG):
    """doc（「doc-」を除いた xml:id）→ XML ファイルの絶対パス。"""
    out = {}
    root = ET.parse(path).getroot()
    for b in root.iter(TEI + "bibl"):
        did = b.get(XID) or ""
        if b.get("type") != "document" or not did.startswith("doc-"):
            continue
        for r in b.findall(TEI + "ref"):
            if r.get("type") == "xml" and r.get("target"):
                out[did[4:]] = os.path.normpath(os.path.join(ROOT, r.get("target")))
    return out


def resolve_docs(rows, catalog, overrides):
    """各行の doc をファイルに当てる。(ファイル → 行のリスト, 問題)。"""
    by_file, problems, unknown = defaultdict(list), [], defaultdict(list)
    for r in rows:
        doc = r["doc"]
        key = doc[4:] if doc.startswith("doc-") else doc
        path = overrides.get(key) or catalog.get(key)
        if not doc:
            problems.append("%s: doc が空です" % r["_where"])
        elif not path:
            unknown[doc].append(r["_where"])
        elif not os.path.exists(path):
            problems.append("%s: doc「%s」のファイルがありません: %s" % (r["_where"], doc, path))
        else:
            by_file[path].append(r)
    for doc, wheres in unknown.items():
        key = doc[4:] if doc.startswith("doc-") else doc
        near = [k for k in sorted(catalog) if k.lower() == key.lower() or k.replace("-", ",") == key]
        problems.append("%s: doc「%s」が data/catalog.xml にありません%s%s" % (
            wheres[0], doc, "（%s のことですか）" % near[0] if near else "",
            "（ほか %d 行。試すときは --file %s=ファイル）" % (len(wheres) - 1, doc) if len(wheres) > 1 else ""))
    return by_file, problems


def parse_overrides(items):
    out, problems = {}, []
    for it in items or []:
        key, sep, path = it.partition("=")
        if not sep or not key or not path:
            problems.append("--file は 文書=ファイル の形で書きます: %s" % it)
            continue
        out[key[4:] if key.startswith("doc-") else key] = os.path.abspath(path)
    return out, problems


# ---------------------------------------------------------------------------------------------------------
# XML をバイト位置つきで読む（expat）

class Node:
    """要素 1 つ。start = 開始タグの '<' の位置、start_end = 開始タグの直後、end = 終了タグの '<' の位置、
    end_end = 終了タグの直後（空要素では end = start、end_end = start_end）。位置はバイト数。"""
    __slots__ = ("tag", "attrs", "start", "start_end", "end", "end_end", "parent", "children")

    def __init__(self, tag, attrs, start, start_end, parent):
        self.tag, self.attrs, self.start, self.start_end, self.parent = tag, attrs, start, start_end, parent
        self.end = self.end_end = None
        self.children = []

    @property
    def empty(self):
        return self.end == self.start


def parse(data):
    """バイト列を読み、文書の根（疑似の要素 #document）を返す。整形式でなければ ExpatError。"""
    p = xml.parsers.expat.ParserCreate()
    top = Node("#document", {}, 0, 0, None)
    stack = [top]

    def start(tag, attrs):
        pos = p.CurrentByteIndex
        m = TAG_RE.match(data, pos)
        node = Node(tag, attrs, pos, m.end(), stack[-1])
        stack[-1].children.append(node)
        stack.append(node)
        if data[m.end() - 2:m.end()] == b"/>":
            node.end, node.end_end = pos, m.end()

    def end(tag):
        node = stack.pop()
        if node.end is None:
            pos = p.CurrentByteIndex
            node.end, node.end_end = pos, data.index(b">", pos) + 1

    p.StartElementHandler, p.EndElementHandler = start, end
    p.Parse(data, True)
    return top


def iter_nodes(node):
    """node 自身と子孫を文書の順に。"""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


class Seg:
    """セグメント（<s xml:id>）1 つ。w は 1 から数える。"""

    def __init__(self, node, witness):
        self.node, self.witness = node, witness
        self.id, self.n = node.attrs.get("xml:id"), node.attrs.get("n", "")
        self.ws, self.wphr, self.phrs = [], [], []     # <w>、その <w> を含む語群の番号（無ければ 0）、<phr>
        self.items = []                                # 本文の並び: ("w", node, w の番号) / ("gap", node, None)
        self.miles = []                                # 区切りの要素: (node, それを含む <w> の番号か None)
        stack = [(c, 0, None) for c in reversed(node.children)]
        while stack:
            n, phri, inw = stack.pop()
            if n.tag == "phr":
                self.phrs.append(n)
                phri = len(self.phrs)
            elif n.tag == "w":
                self.ws.append(n)
                self.wphr.append(phri)
                self.items.append(("w", n, len(self.ws)))
                inw = len(self.ws)
            elif n.tag == "gap":
                self.items.append(("gap", n, None))
            elif n.tag in MILESTONES:
                self.miles.append((n, inw))
            stack.extend((c, phri, inw) for c in reversed(n.children))
        self.item_starts = [it[1].start for it in self.items]

    def first_in_phr(self, wi):
        """w 番目の <w> が語群の最初の <w> か（語群に入っていなければ True）。"""
        k = self.wphr[wi - 1]
        return k == 0 or wi == 1 or self.wphr[wi - 2] != k

    def item_index_of_w(self, wi):
        return next(i for i, it in enumerate(self.items) if it[0] == "w" and it[2] == wi)


def segments(top):
    """xml:id → Seg（文書の順の dict）と、重複した id のリスト。"""
    segs, dups = {}, []

    def visit(node, wit):
        if node.tag == "text" and node.attrs.get("type") == "witness":
            wit = node.attrs.get("xml:id") or wit
        if node.tag == "s" and node.attrs.get("xml:id"):
            seg = Seg(node, wit)
            if seg.id in segs:
                dups.append(seg.id)
            segs[seg.id] = seg
            return
        for c in node.children:
            visit(c, wit)

    visit(top, None)
    return segs, dups


# ---------------------------------------------------------------------------------------------------------
# <w> の中身（文字の位置）

def is_letter(ch):
    return not ch.isspace() and not unicodedata.category(ch).startswith("M")


def w_parts(data, w):
    """<w> の中身を、("tag", 始, 終, バイト列) と ("ch", 始, 終, 文字) の列にする。"""
    out = []
    for m in CONTENT_RE.finditer(data, w.start_end, w.end):
        s, e = m.span()
        b = m.group()
        if b.startswith(b"<"):
            out.append(("tag", s, e, b))
        elif b.startswith(b"&"):
            out.append(("ch", s, e, html.unescape(b.decode("utf-8"))))
        else:
            off = s
            for ch in b.decode("utf-8"):
                n = len(ch.encode("utf-8"))
                out.append(("ch", off, off + n, ch))
                off += n
    return out


def depths(parts):
    """各部分の直前の入れ子の深さ（<w> の直下が 0）。"""
    out, d = [], 0
    for kind, s, e, b in parts:
        out.append(d)
        if kind == "tag" and not b.startswith((b"<?", b"<!")):
            if b.startswith(b"</"):
                d -= 1
            elif not b.endswith(b"/>"):
                d += 1
    return out


def w_text(data, w):
    return "".join(p[3] for p in w_parts(data, w) if p[0] == "ch").strip()


def letters_before(data, w, pos):
    return sum(1 for p in w_parts(data, w) if p[0] == "ch" and p[1] < pos and is_letter(p[3]))


def char_points(data, w, k):
    """<w> の k 文字目（0 から）の前に区切りを入れられる位置（深さ 0 のもの）。(位置のリスト, 文字数, 誤りの説明)。"""
    parts = w_parts(data, w)
    letters = [i for i, p in enumerate(parts) if p[0] == "ch" and is_letter(p[3])]
    if k == 0:
        return [], len(letters), "char=0 は語の前と同じです（char を空欄にします）"
    if k >= len(letters):
        return [], len(letters), "char は 1 以上 %d 未満で書きます（この語は %d 文字。語の終わりで切れるなら、次の <w> を指します）" % (len(letters), len(letters))
    dep = depths(parts)
    j = letters[k - 1] + 1
    while j < letters[k] and parts[j][0] == "ch" and not parts[j][3].isspace():
        j += 1                                         # 前の文字に付く合成記号はとばす
    points = [parts[x][1] for x in range(j, letters[k] + 1) if dep[x] == 0]
    if not points:
        return [], len(letters), "その位置は <supplied>（復元した字）の中です。<supplied> の中には区切りを入れません"
    return points, len(letters), None


# ---------------------------------------------------------------------------------------------------------
# 位置（slot）

def slot_of_milestone(data, seg, node, inw):
    """もとからある区切りの位置。('in', w, 文字数) か ('at', w か 'end', 'w' か 'before-gap')。"""
    if inw:
        k = letters_before(data, seg.ws[inw - 1], node.start)
        if k:
            return ("in", inw, k)
        return ("at", inw, "w")
    i = bisect_right(seg.item_starts, node.start)
    if i >= len(seg.items):
        return ("at", "end", "w")
    kind, n, wi = seg.items[i]
    if kind == "w":
        return ("at", wi, "w")
    nxt = next((it[2] for it in seg.items[i:] if it[0] == "w"), "end")
    return ("at", nxt, "before-gap")


def describe_slot(key):
    kind, wi, x = key
    if kind == "in":
        return "w=%s char=%s" % (wi, x)
    return "w=%s%s" % (wi, " place=before-gap" if x == "before-gap" else "")


def line_indent(data, pos):
    """pos が行の最初の要素なら、その行の字下げ（バイト列）。そうでなければ None。"""
    nl = data.rfind(b"\n", 0, pos)
    ws = data[nl + 1:pos]
    return ws if not ws.strip(b" \t") else None


def first_child(node):
    return node.parent.children and node.parent.children[0] is node


def climb(node):
    """語群の最初の子なら、語群の前へ。"""
    while node.parent is not None and node.parent.tag == "phr" and first_child(node):
        node = node.parent
    return node


def context(data, seg, wi, before=3, after=3):
    """w 番目の <w> の前後の語群（表示用）。"""
    groups, cur, key = [], [], None
    for kind, n, i in seg.items:
        k = ("gap", n.start) if kind == "gap" else (seg.wphr[i - 1] or ("w", i))
        if k != key and cur:
            groups.append(cur)
            cur = []
        key = k
        cur.append((i, "〔…〕" if kind == "gap" else w_text(data, n)))
    if cur:
        groups.append(cur)
    if wi == "end":
        return " ".join("".join(t for _, t in g) for g in groups[-before:]) + " |"
    for gi, g in enumerate(groups):
        for j, (i, t) in enumerate(g):
            if i == wi:
                pre = " ".join("".join(t for _, t in h) for h in groups[max(0, gi - before):gi])
                mid = "".join(t for _, t in g[:j]) + "|" + "".join(t for _, t in g[j:])
                post = " ".join("".join(t for _, t in h) for h in groups[gi + 1:gi + 1 + after])
                return " ".join(x for x in (pre, mid, post) if x)
    return ""


def where_label(anchor, seg):
    if anchor.parent is seg.node and seg.node.children[0] is anchor:
        return "<s> の先頭"
    if anchor.tag == "phr":
        return "語群（<phr>）の前"
    if anchor.tag == "gap":
        return "欠損（<gap>）の前" + ("（<phr> の中）" if anchor.parent.tag == "phr" else "")
    if anchor.parent.tag == "phr":
        return "語群の中、<w> の前"
    return "<w> の前"


# ---------------------------------------------------------------------------------------------------------
# 区切りを入れる

def milestone_tag(typ, n, brk):
    return '<%s n="%s"%s/>' % (typ, html.escape(n, quote=True), ' break="no"' if brk else "")


def check_row(r, seg, data, out_problems):
    """1 行を確かめ、位置（slot）を返す。問題があれば None。"""
    where = r["_where"]
    bad = lambda msg: out_problems.append("%s: %s" % (where, msg))
    typ, n, place = r["type"], r["n"], (r.get("place") or "").strip()
    ok = True
    if typ not in TYPES:
        bad("type は pb か lb です: %r" % typ)
        ok = False
    if not n or re.search(r"\s", n):
        bad("n が空か、空白を含んでいます: %r" % n)
        ok = False
    if place not in ("", "w", "before-gap"):
        bad("place は空欄か before-gap です: %r" % place)
        ok = False
    nw = len(seg.ws)
    wraw = r["w"]
    if wraw == "end":
        if place != "before-gap":
            bad("w=end は place=before-gap のときだけ使えます（セグメントの終わりの区切りは、次のセグメントの最初の <w> に書きます）")
            return None
        if not seg.items or seg.items[-1][0] != "gap":
            bad("w=end, place=before-gap ですが、このセグメントは <gap> で終わっていません")
            return None
        if r.get("char"):
            bad("w=end に char は書けません")
            return None
        if r.get("phr") or r.get("form"):
            bad("w=end に phr・form は書けません")
            return None
        return ("at", "end", "before-gap") if ok else None
    if not re.fullmatch(r"[0-9]+", wraw or ""):
        bad("w は 1 から始まる整数で書きます: %r" % wraw)
        return None
    wi = int(wraw)
    if not 1 <= wi <= nw:
        bad("w=%d がありません（%s の <w> は %d 個）" % (wi, seg.id, nw))
        return None
    w = seg.ws[wi - 1]
    form = r.get("form") or ""
    if form and form != w_text(data, w):
        bad("form「%s」が、%s の %d 番目の <w>「%s」と違います" % (form, seg.id, wi, w_text(data, w)))
        ok = False
    phr = r.get("phr") or ""
    if phr:
        if not re.fullmatch(r"[0-9]+", phr):
            bad("phr は整数で書きます: %r" % phr)
            ok = False
        elif int(phr) != seg.wphr[wi - 1]:
            bad("phr=%s ですが、%s の %d 番目の <w> は %s" % (phr, seg.id, wi, ("%d 番目の <phr> の中" % seg.wphr[wi - 1]) if seg.wphr[wi - 1] else "語群（<phr>）に入っていません"))
            ok = False
    char = r.get("char") or ""
    if char:
        if place == "before-gap":
            bad("char と place=before-gap は一緒に使えません")
            return None
        if not re.fullmatch(r"[0-9]+", char):
            bad("char は整数で書きます: %r" % char)
            return None
        points, nlet, err = char_points(data, w, int(char))
        if err:
            bad("%s（%s の %d 番目の <w>「%s」）" % (err, seg.id, wi, w_text(data, w)))
            return None
        return ("in", wi, int(char)) if ok else None
    if place == "before-gap":
        i = seg.item_index_of_w(wi)
        if i == 0 or seg.items[i - 1][0] != "gap":
            bad("place=before-gap ですが、%s の %d 番目の <w> の直前は <gap> ではありません" % (seg.id, wi))
            return None
        return ("at", wi, "before-gap") if ok else None
    return ("at", wi, "w") if ok else None


def default_point(data, seg, key):
    """区切りがまだ無い位置に入れるときの差し込み位置: ('before', node) か ('inline', バイト位置)。"""
    kind, wi, x = key
    if kind == "in":
        points, _, _ = char_points(data, seg.ws[wi - 1], x)
        return ("inline", points[0])
    if wi == "end":
        anchor = seg.items[-1][1]
    else:
        i = seg.item_index_of_w(wi)
        anchor = seg.items[i - 1][1] if x == "before-gap" else seg.items[i][1]
    return ("before", climb(anchor))


def plan(path, data, rows):
    """1 ファイル分。(差し込み [(位置, 順, 文字列)], 表示する行, 問題, 注意, 足した区切り [(seg_id, slot, type, n, break)])。"""
    problems, notes, lines, inserts, added = [], [], [], [], []
    try:
        top = parse(data)
    except xml.parsers.expat.ExpatError as e:
        return [], [], ["%s: XML として読めません: %s" % (path, e)], [], []
    segs, dups = segments(top)
    for d in dups:
        problems.append("%s: セグメントの xml:id が重複しています: %s" % (path, d))
    nl = b"\r\n" if b"\r\n" in data[:4096] else b"\n"
    existing = defaultdict(list)                    # (seg_id, slot) → もとからある区切り（文書の順）
    for seg in segs.values():
        for node, inw in seg.miles:
            existing[(seg.id, slot_of_milestone(data, seg, node, inw))].append(node)

    wanted = defaultdict(list)                      # (seg_id, slot) → 行
    for r in rows:
        seg = segs.get(r["seg_id"])
        if seg is None:
            problems.append("%s: seg_id「%s」が %s にありません" % (r["_where"], r["seg_id"], shown(path)))
            continue
        key = check_row(r, seg, data, problems)
        if key is None:
            continue
        brk = key[0] == "in"
        r["_slot"], r["_break"] = key, brk
        same = [x for x in wanted[(seg.id, key)] if x["type"] == r["type"]]
        if same:
            problems.append("%s: 同じ位置（%s %s）に %s がもう 1 行あります（%s）" % (r["_where"], seg.id, describe_slot(key), r["type"], same[0]["_where"]))
            continue
        wanted[(seg.id, key)].append(r)

    for (sid, key), rs in wanted.items():
        seg = segs[sid]
        E = existing.get((sid, key), [])
        todo = []
        for r in sorted(rs, key=lambda r: RANK[r["type"]]):
            label = "%s %s %s %s n=%s" % (r["doc"], sid, describe_slot(key), r["type"], r["n"])
            same = [e for e in E if e.tag == r["type"]]
            if same:
                if any(e.attrs.get("n") == r["n"] and (e.attrs.get("break") == "no") == r["_break"] for e in same):
                    lines.append("  = %s: 同じ区切りがもうあります（何もしない）" % label)
                else:
                    e = same[0]
                    problems.append("%s: %s の位置には、もう <%s n=\"%s\"%s/> があります（n=%s を足すと同じ位置に 2 つになる）" % (
                        r["_where"], describe_slot(key), e.tag, e.attrs.get("n", ""), ' break="%s"' % e.attrs["break"] if "break" in e.attrs else "", r["n"]))
                continue
            todo.append((r, label))
        if not todo:
            continue
        ctx = context(data, seg, key[1])
        if key[0] == "in":
            w = seg.ws[key[1] - 1]
            t = w_text(data, w)
            lets = [c for c in t if is_letter(c)]
            ctx = "%s|%s（<w> の中）" % ("".join(lets[:key[2]]), "".join(lets[key[2]:]))
        for r, label in todo:
            tag = milestone_tag(r["type"], r["n"], r["_break"]).encode("utf-8")
            rank = RANK[r["type"]]
            higher = [e for e in E if RANK.get(e.tag, 9) > rank]
            if higher:
                e = higher[0]
                ind = line_indent(data, e.start)
                text = tag + (nl + ind if ind is not None and key[0] == "at" else b"")
                inserts.append((e.start, rank, text))
                how = "既存の <%s n=\"%s\"/> の前" % (e.tag, e.attrs.get("n", ""))
            elif E:
                e = E[-1]
                ind = line_indent(data, e.start)
                text = (nl + ind if ind is not None and key[0] == "at" else b"") + tag
                inserts.append((e.end_end, rank, text))
                how = "既存の <%s n=\"%s\"/> のあと" % (e.tag, e.attrs.get("n", ""))
            else:
                mode, x = default_point(data, seg, key)
                if mode == "inline":
                    inserts.append((x, rank, tag))
                    how = "<w> の中（break=\"no\"）"
                else:
                    ind = line_indent(data, x.start)
                    inserts.append((x.start, rank, tag + (nl + ind if ind is not None else b"")))
                    how = where_label(x, seg)
            lines.append("  + %s → %s 【%s】" % (label, how, ctx))
            added.append((sid, key, r["type"], r["n"], r["_break"]))
    return inserts, lines, problems, notes, added


def apply_inserts(data, inserts):
    out, prev = [], 0
    for pos, rank, text in sorted(inserts, key=lambda x: (x[0], x[1])):
        out.append(data[prev:pos])
        out.append(text)
        prev = pos
    out.append(data[prev:])
    return b"".join(out)


# ---------------------------------------------------------------------------------------------------------
# 検証

def canon(data, drop=("pb", "lb")):
    """区切りの要素を除き、空白だけの文字列を無視した形（比べるため）。"""
    root = ET.fromstring(data)
    drop = {TEI + t for t in drop}

    def strip(el):
        prev = None
        for child in list(el):
            if child.tag in drop:
                tail = child.tail or ""
                if prev is None:
                    el.text = (el.text or "") + tail
                else:
                    prev.tail = (prev.tail or "") + tail
                el.remove(child)
            else:
                strip(child)
                prev = child

    strip(root)
    for el in root.iter():
        if el.text is not None and not el.text.strip():
            el.text = None
        if el.tail is not None and not el.tail.strip():
            el.tail = None
    return ET.tostring(root)


def seg_words(data, segs):
    return {sid: [("〔gap〕" if k == "gap" else w_text(data, n)) for k, n, _ in s.items] for sid, s in segs.items()}


def check_tei_problems(data, original_path):
    """scripts/check_tei.py の点検で、新しく出る問題のリスト（元のファイルにもある問題は除く）。読み込めなければ None。"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import check_tei
    except Exception:                                   # noqa: BLE001
        return None
    before = set(check_tei.check(original_path))
    fd, tmp = tempfile.mkstemp(suffix=".xml")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        after = check_tei.check(tmp)
    finally:
        os.unlink(tmp)
    return [p for p in after if p not in before]


def verify(path, old, new, added):
    """差し込んだあとのバイト列を確かめる。問題のリスト。"""
    problems = []
    try:
        ET.fromstring(new)
        top_new = parse(new)
    except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
        return ["差し込んだ結果が整形式の XML になりません: %s" % e]
    top_old = parse(old)
    segs_old, _ = segments(top_old)
    segs_new, _ = segments(top_new)
    if canon(old) != canon(new):
        problems.append("pb・lb を除いた内容が元のファイルと違います（区切り以外のものが変わった）")
    ids_old = [(n.tag, n.attrs.get("xml:id")) for n in iter_nodes(top_old) if "xml:id" in n.attrs]
    ids_new = [(n.tag, n.attrs.get("xml:id")) for n in iter_nodes(top_new) if "xml:id" in n.attrs]
    if ids_old != ids_new:
        problems.append("xml:id が変わりました")
    if list(segs_old) != list(segs_new):
        problems.append("セグメント（<s>）の並びか xml:id が変わりました")
    wo, wn = seg_words(old, segs_old), seg_words(new, segs_new)
    for sid in segs_old:
        if wo.get(sid) != wn.get(sid):
            problems.append("%s: 語（<w>）か欠損の並びが変わりました" % sid)
    miles_old = defaultdict(list)
    for s in segs_old.values():
        for node, inw in s.miles:
            miles_old[(s.id, slot_of_milestone(old, s, node, inw))].append((node.tag, node.attrs.get("n"), node.attrs.get("break")))
    miles_new = defaultdict(list)
    for s in segs_new.values():
        for node, inw in s.miles:
            miles_new[(s.id, slot_of_milestone(new, s, node, inw))].append((node.tag, node.attrs.get("n"), node.attrs.get("break")))
    n_old = sum(len(v) for v in miles_old.values())
    n_new = sum(len(v) for v in miles_new.values())
    if n_new != n_old + len(added):
        problems.append("区切りの数が合いません（元 %d、足した %d、結果 %d）" % (n_old, len(added), n_new))
    for key, lst in miles_old.items():
        rest = list(miles_new.get(key, []))
        for m in lst:
            if m in rest:
                rest.remove(m)
            else:
                problems.append("もとからある区切り <%s n=\"%s\"/>（%s %s）が見つかりません" % (m[0], m[1], key[0], describe_slot(key[1])))
    for sid, key, typ, n, brk in added:
        if (typ, n, "no" if brk else None) not in miles_new.get((sid, key), []):
            problems.append("足した <%s n=\"%s\"/> が %s %s にありません" % (typ, n, sid, describe_slot(key)))
    for key, lst in miles_new.items():
        ranks = [RANK.get(t, 9) for t, _, _ in lst]
        if ranks != sorted(ranks):
            problems.append("%s %s: 同じ位置の区切りの順が pb → lb になっていません" % (key[0], describe_slot(key[1])))
    extra = check_tei_problems(new, path)
    if extra is None:
        problems.append("scripts/check_tei.py を読み込めず、点検できませんでした")
    else:
        problems += ["check_tei.py: " + p for p in extra]
    return problems


def sequence_notes(data):
    """頁・行の番号の続き具合（注意として表示）。"""
    notes = []
    top = parse(data)
    segs, _ = segments(top)
    by_wit = defaultdict(list)
    for s in segs.values():
        for node, inw in s.miles:
            by_wit[s.witness].append((node.start, node, s, inw))
    for wit, lst in by_wit.items():
        lst.sort(key=lambda x: x[0])
        page = line = None
        seen_pages = {}
        for i, (pos, node, s, inw) in enumerate(lst):
            n = node.attrs.get("n", "")
            where = "%s %s" % (s.id, describe_slot(slot_of_milestone(data, s, node, inw)))
            if node.tag in ("pb", "lb") and not re.fullmatch(r"[0-9]+", n):
                notes.append("%s: <%s n=\"%s\"/> の n が数字ではありません" % (where, node.tag, n))
            if node.tag == "pb":
                if n in seen_pages:
                    notes.append("%s: 頁 %s の pb がほかの位置（%s）にもあります" % (where, n, seen_pages[n]))
                seen_pages[n] = where
                if page is not None and n.isdigit() and page.isdigit() and int(n) != int(page) + 1:
                    notes.append("%s: 頁番号が %s から %s に飛んでいます" % (where, page, n))
                page, line = n, None
                nxt = lst[i + 1] if i + 1 < len(lst) else None
                if not (nxt and nxt[1].tag == "lb" and slot_of_milestone(data, nxt[2], nxt[1], nxt[3]) == slot_of_milestone(data, s, node, inw) and nxt[2] is s):
                    notes.append("%s: 頁 %s の pb と同じ位置に lb がありません（頁の最初の行も lb で書きます）" % (where, n))
            elif node.tag == "lb":
                if line is not None and n.isdigit() and line.isdigit() and int(n) != int(line) + 1:
                    notes.append("%s: 行番号が %s から %s に飛んでいます%s" % (where, line, n, "（頁 %s）" % page if page else ""))
                line = n
    return notes


def write_atomic(path, data):
    mode = os.stat(path).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-", suffix=".xml")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def shown(path):
    p = os.path.abspath(path)
    return os.path.relpath(p, ROOT) if p.startswith(ROOT + os.sep) else path


# ---------------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="TSV で指定した頁・行の区切り（<pb>・<lb>）を TEI に入れる")
    ap.add_argument("tsv", nargs="+", help="区切りの TSV（列: doc, seg_id, w, type, n［, char, place, phr, form, note］）")
    ap.add_argument("--write", action="store_true", help="書き込む（付けなければ表示するだけ）")
    ap.add_argument("--file", action="append", metavar="文書=ファイル", help="doc の代わりに使うファイル（試すとき）")
    ap.add_argument("--catalog", default=CATALOG, help="カタログ（既定 data/catalog.xml）")
    args = ap.parse_args(argv)

    problems, notes, rows = [], [], []
    overrides, p = parse_overrides(args.file)
    problems += p
    for t in args.tsv:
        r, p, n = read_tsv(t)
        rows += r
        problems += p
        notes += n
    catalog = load_catalog(args.catalog)
    by_file, p = resolve_docs(rows, catalog, overrides)
    problems += p

    results = []
    for path, rs in by_file.items():
        with open(path, "rb") as f:
            old = f.read()
        inserts, lines, p, n, added = plan(path, old, rs)
        problems += p
        notes += n
        print("%s: %d 行" % (shown(path), len(rs)))
        for line in lines:
            print(line)
        if p or not inserts:
            results.append((path, old, None, added))
            continue
        new = apply_inserts(old, inserts)
        v = verify(path, old, new, added)
        if v:
            problems += ["%s: %s" % (shown(path), x) for x in v]
            results.append((path, old, None, added))
            continue
        notes += ["%s: %s" % (shown(path), x) for x in sequence_notes(new)]
        results.append((path, old, new, added))

    if notes:
        print("\n注意（%d 件。誤りとは限らない）:" % len(notes))
        for x in notes:
            print("  - " + x)
    if problems:
        print("\n問題（%d 件）。何も書き込んでいません:" % len(problems))
        for x in problems:
            print("  ! " + x)
        return 1
    changed = [(path, new, added) for path, old, new, added in results if new is not None]
    total = sum(len(a) for _, _, a in changed)
    if not changed:
        print("\n足す区切りはありません（変更なし）")
        return 0
    if not args.write:
        print("\n%d ファイルに %d 個の区切りを足せます（検証済み）。書き込むには --write を付けて実行します" % (len(changed), total))
        return 0
    for path, new, added in changed:
        write_atomic(path, new)
        print("書き込みました: %s（区切り %d 個）" % (shown(path), len(added)))
    print("続けて python3 scripts/check_tei.py %s を実行してください" % " ".join(shown(p) for p, _, _ in changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
