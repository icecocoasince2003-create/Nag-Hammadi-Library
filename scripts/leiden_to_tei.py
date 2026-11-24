#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
leiden_to_tei.py — ライデン記法で書いたコプト語の翻刻を、TEI（EpiDoc の要素）の本文に変える

仕様書 §4 の対応表のとおりに、角括弧などの記号を TEI の要素に置き換え、頁・列・行の区切りを <pb>・<cb>・<lb> に、
語群（空白で区切った 1 語）を <w> にします。できたファイルは、そのまま scripts/coptic_nlp_tei.py にかけられます
（--groups keep で語群を保ったまま、品詞・レンマを付けられる）。

入力（UTF-8 のテキスト）:
  # で始まる行          注記（読み飛ばす）
  @pb 32               頁の区切り   → <pb n="32"/>
  @cb 1                列の区切り   → <cb n="1"/>
  @s                   ここから新しいセグメント（<s>）。空行でも新しいセグメントになる
  10 ⲛⲁⲉⲓ ⲛⲉ …         行番号（半角数字）と本文 → <lb n="10"/> と本文
  … ⲇⲓⲇⲩⲙⲟⲥ=          行末の = は「語が次の行に続く」 → 次の行の <lb> に break="no" を付け、<w> の中に置く

本文の中の記号（EpiDoc Guidelines 9.8 の書き方に置き換える）:
  [ⲁⲃⲅ]      <supplied reason="lost">       [ⲁⲃⲅ?] は cert="low" を付ける
  [...]      <gap reason="lost" quantity="3" unit="character"/>（点の数が字数）
  [±3] [c.3] <gap reason="lost" quantity="3" unit="character" precision="low"/>
  [---]      <gap reason="lost" extent="unknown" unit="character"/>
  ...        （角括弧の外の点）<gap reason="illegible" quantity="3" unit="character"/>
  ⲁ̣          （下点 U+0323）<unclear>ⲁ</unclear>
  ⟦ⲁⲃⲅ⟧      <del rend="erasure">
  `ⲁⲃⲅ´      <add place="above">（\\ⲁⲃⲅ/ も同じ。/ⲁⲃⲅ\\ は place="below"）
  {ⲁⲃⲅ}      <surplus>
  <ⲁⲃⲅ>      <supplied reason="omitted">
  ⲡⲛ(ⲉⲩⲙ)ⲁ   <expan><abbr>ⲡⲛ</abbr><ex>ⲉⲩⲙ</ex><abbr>ⲁ</abbr></expan>（丸括弧の中が写本に無い字）
上線（U+0304、U+FE24–FE26）やトレマなどの結合文字は、そのまま本文に残します。補訂などが語群の境目をまたぐときは、
<w> ごとに要素を分けます（XML では要素を交差させられないため）。欠損 <gap> は語の途中にあっても <w> の外に出し、
前後を別の <w> にします（語の切れ目かどうかは、あとで人が確かめる）。

使い方:
  python3 scripts/leiden_to_tei.py 翻刻.txt                   <ab> の断片を表示する
  python3 scripts/leiden_to_tei.py 翻刻.txt --id-prefix II-2 --out build/II-2.xml --standalone
      TEI の文書として書き出す（ヘッダーは最小限。scripts/coptic_nlp_tei.py にそのままかけられる）

標準ライブラリだけで動きます（Python 3.9 以上）。記号の対応がとれない（閉じていない括弧など）ときは、行番号を示して止まります。
"""
import argparse
import re
import sys
import unicodedata

UNDERDOT = "̣"
OPEN = {"[": "]", "⟦": "⟧", "{": "}", "<": ">", "(": ")", "`": "´", "\\": "/", "/": "\\"}
APPROX_RE = re.compile(r"^(?:±|c\.|ca\.)\s*(\d+)$")


class LeidenError(Exception):
    pass


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def is_mark(ch):
    return unicodedata.category(ch) in ("Mn", "Me")


class Builder:
    """文字の列を作る。項目: ('c', 字（結合文字つき）, 包む要素) | ('sp',) | ('gap', 属性) | ('m', 要素名, 属性)"""

    def __init__(self):
        self.items = []
        self.serial = 0

    def new(self, name, attrs=()):
        self.serial += 1
        return (name, tuple(attrs), self.serial)

    def char(self, ch, wrap):
        self.items.append(("c", ch, wrap))

    def add_mark(self, mark, lineno):
        for k in range(len(self.items) - 1, -1, -1):
            if self.items[k][0] == "c":
                kind, ch, wrap = self.items[k]
                self.items[k] = (kind, ch + mark, wrap)
                return
            break
        raise LeidenError("%d 行: 結合文字 U+%04X の前に字が無い" % (lineno, ord(mark)))


def parse_bracket(content, wrap, b, lineno):
    """[ ] の中身: 字は <supplied reason="lost">、点は字数のわかる欠損、±n・c.n はおよその字数、- は字数不明。"""
    body = content.strip()
    cert_low = body.endswith("?")
    if cert_low:
        body = body[:-1].rstrip()
    m = APPROX_RE.match(body)
    if m:
        b.items.append(("gap", (("reason", "lost"), ("quantity", m.group(1)), ("unit", "character"),
                                ("precision", "low"))))
        return
    if body and set(body) <= set("-–— "):
        b.items.append(("gap", (("reason", "lost"), ("extent", "unknown"), ("unit", "character"))))
        return
    sup = None
    k = 0
    while k < len(body):
        ch = body[k]
        if ch == ".":
            n = 0
            while k < len(body) and body[k] in ". ":
                n += body[k] == "."
                k += 1
            b.items.append(("gap", (("reason", "lost"), ("quantity", str(n)), ("unit", "character"))))
            sup = None
            continue
        if ch.isspace():
            b.items.append(("sp",))
            k += 1
            continue
        if is_mark(ch):
            b.add_mark(ch, lineno)
            k += 1
            continue
        if not unicodedata.category(ch).startswith("L"):
            raise LeidenError("%d 行: [ ] の中の記号 %r は扱えない" % (lineno, ch))
        if sup is None:
            attrs = [("reason", "lost")] + ([("cert", "low")] if cert_low else [])
            sup = b.new("supplied", attrs)
        b.char(ch, wrap + (sup,))
        k += 1


def parse_line(text, b, lineno, state):
    """1 行の本文を項目にする。state は行をまたいで開いている記号（[ ⟦ { < ` \\ /）の列。"""
    k = 0
    while k < len(text):
        ch = text[k]
        if ch == "[":
            end = text.find("]", k + 1)
            if end < 0:
                raise LeidenError("%d 行: [ が閉じていない（行をまたぐ補訂は、行ごとに [ ] を閉じる）" % lineno)
            parse_bracket(text[k + 1:end], wrap_of(state), b, lineno)
            k = end + 1
            continue
        if ch in ("⟦", "{", "<", "`") or (ch in ("\\", "/") and not (state and state[-1][0] in ("add",)
                                                                     and OPEN.get(state[-1][3]) == ch)):
            name, attrs = {"⟦": ("del", [("rend", "erasure")]), "{": ("surplus", []),
                           "<": ("supplied", [("reason", "omitted")]), "`": ("add", [("place", "above")]),
                           "\\": ("add", [("place", "above")]), "/": ("add", [("place", "below")])}[ch]
            item = b.new(name, attrs)
            state.append((item[0], item[1], item[2], ch))
            k += 1
            continue
        if state and ch == OPEN[state[-1][3]]:
            state.pop()
            k += 1
            continue
        if ch in ("]", "⟧", "}", ">", "´"):
            raise LeidenError("%d 行: 対応する開きの無い %s" % (lineno, ch))
        if ch == "(":
            end = text.find(")", k + 1)
            if end < 0:
                raise LeidenError("%d 行: ( が閉じていない" % lineno)
            ex = b.new("ex")
            for c in text[k + 1:end]:
                if c.isspace():
                    raise LeidenError("%d 行: ( ) の中に空白がある" % lineno)
                if is_mark(c):
                    b.add_mark(c, lineno)
                else:
                    b.char(c, wrap_of(state) + (ex,))
            k = end + 1
            continue
        if ch == ".":
            n = 0
            while k < len(text) and text[k] == ".":
                n += 1
                k += 1
            b.items.append(("gap", (("reason", "illegible"), ("quantity", str(n)), ("unit", "character"))))
            continue
        if ch.isspace():
            b.items.append(("sp",))
            k += 1
            continue
        if ch == UNDERDOT:
            # 直前の字を <unclear> で包む（続く下点つきの字は同じ <unclear> にまとめる）
            for j in range(len(b.items) - 1, -1, -1):
                if b.items[j][0] == "c":
                    kind, c0, wrap = b.items[j]
                    prev = b.items[j - 1] if j > 0 else None
                    run = None
                    if prev and prev[0] == "c" and prev[2] and prev[2][-1][0] == "unclear" \
                            and prev[2][:-1] == wrap:
                        run = prev[2][-1]
                    b.items[j] = (kind, c0, wrap + (run or b.new("unclear"),))
                    break
                raise LeidenError("%d 行: 下点の前に字が無い" % lineno)
            k += 1
            continue
        if is_mark(ch):
            b.add_mark(ch, lineno)
            k += 1
            continue
        if not unicodedata.category(ch).startswith("L") and ch not in "·:⳾⳿":
            raise LeidenError("%d 行: 扱えない記号 %r" % (lineno, ch))
        b.char(ch, wrap_of(state))
        k += 1


def wrap_of(state):
    return tuple((name, attrs, serial) for name, attrs, serial, _ in state)


def to_words(items):
    """項目を語（<w>）と、語の外に置くもの（欠損・改行）の列にする。
    返り値: [('w', [('c', 字, 包む要素) | ('m', 要素名, 属性)]) | ('gap', 属性) | ('m', 要素名, 属性)]"""
    out, cur = [], None
    for it in items:
        if it[0] == "c":
            if cur is None:
                cur = []
                out.append(("w", cur))
            cur.append(it)
        elif it[0] == "m":
            if it[2] and dict(it[2]).get("break") == "no" and cur is not None:
                cur.append(it)          # 語の途中の改行
            else:
                cur = None
                out.append(it)
        else:                           # 'sp' と 'gap' は語を切る
            cur = None
            if it[0] == "gap":
                out.append(it)
    return out


def render_word(parts):
    """<w> の中身。包む要素を開閉し、( ) の展開がある語は <expan> で包む。"""
    has_ex = any(p[0] == "c" and any(w[0] == "ex" for w in p[2]) for p in parts)
    if has_ex:
        expan = ("expan", (), -1)
        new, abbr = [], None
        for p in parts:
            if p[0] != "c":
                new.append(p)
                continue
            outer = tuple(w for w in p[2] if w[0] != "ex")
            ex = [w for w in p[2] if w[0] == "ex"]
            if ex:
                abbr = None
                new.append(("c", p[1], (expan,) + outer + (ex[0],)))
            else:
                if abbr is None:
                    abbr = ("abbr", (), -len(new) - 2)
                new.append(("c", p[1], (expan,) + outer + (abbr,)))
        parts = new
    out, open_ = [], ()
    for p in parts:
        if p[0] == "m":
            out.append(milestone(p))
            continue
        target = p[2]
        k = 0
        while k < len(open_) and k < len(target) and open_[k] == target[k]:
            k += 1
        for w in reversed(open_[k:]):
            out.append("</%s>" % w[0])
        for w in target[k:]:
            out.append("<%s%s>" % (w[0], "".join(' %s="%s"' % (a, esc(v)) for a, v in w[1])))
        open_ = target
        out.append(esc(p[1]))
    for w in reversed(open_):
        out.append("</%s>" % w[0])
    return "".join(out)


def milestone(it):
    _, name, attrs = it
    return "<%s%s/>" % (name, "".join(' %s="%s"' % (a, esc(v)) for a, v in attrs))


def convert(lines, id_prefix="seg", start=1):
    """入力の行の列から、<s> の列（文字列）を作る。"""
    segs, b, state = [], Builder(), []
    pending_break = False

    def flush():
        """本文のある項目をセグメントにする。頁・行の区切りだけのときは、次のセグメントの頭に回す。"""
        nonlocal b
        if any(it[0] in ("c", "gap") for it in b.items):
            segs.append(b.items)
            b = Builder()
            b.serial = 10 ** 6 * (len(segs) + 1)

    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n").rstrip()
        if not line.strip():
            if state:
                raise LeidenError("%d 行: 段落の終わりで記号が閉じていない" % lineno)
            flush()
            continue
        if line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s*@(pb|cb)\s+(\S+)\s*$", line)
        if m:
            attrs = [("n", m.group(2))] + ([("break", "no")] if pending_break else [])
            b.items.append(("m", m.group(1), tuple(attrs)))
            continue
        if re.match(r"^\s*@s\s*$", line):
            if state:
                raise LeidenError("%d 行: セグメントの区切りで記号が閉じていない" % lineno)
            flush()
            continue
        m = re.match(r"^\s*(\d+[a-z]?)\s+(.*)$", line)
        if not m:
            raise LeidenError("%d 行: 行番号が無い（「10 本文」の形で書く）" % lineno)
        n, text = m.group(1), m.group(2)
        attrs = [("n", n)] + ([("break", "no")] if pending_break else [])
        b.items.append(("m", "lb", tuple(attrs)))
        pending_break = text.endswith("=")
        if pending_break:
            text = text[:-1].rstrip()
        parse_line(text, b, lineno, state)
        if not pending_break:
            b.items.append(("sp",))
    if state:
        raise LeidenError("入力の終わりで記号が閉じていない: %s" % "".join(s[3] for s in state))
    if pending_break:
        raise LeidenError("最後の行が = で終わっている（続く行が無い）")
    flush()
    if b.items and segs:              # 末尾の区切りだけが残ったときは最後のセグメントに入れる
        segs[-1].extend(b.items)

    out = []
    for k, items in enumerate(segs, start):
        body = []
        for part in to_words(items):
            if part[0] == "w":
                body.append("<w>%s</w>" % render_word(part[1]))
            elif part[0] == "gap":
                body.append("<gap%s/>" % "".join(' %s="%s"' % (a, esc(v)) for a, v in part[1]))
            else:
                body.append(milestone(part))
        out.append(('<s xml:id="%s-%d" n="%d">' % (esc(id_prefix), k, k), body))
    return out


def render(segs, indent="  "):
    lines = ['<ab type="text">']
    for head, body in segs:
        lines.append(indent + head)
        for b in body:
            lines.append(indent * 2 + b)
        lines.append(indent + "</s>")
    lines.append("</ab>")
    return "\n".join(lines)


STANDALONE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="cop">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{title}</title>
      </titleStmt>
      <publicationStmt>
        <p>Working file made by scripts/leiden_to_tei.py from a Leiden-style transcription; not published.</p>
      </publicationStmt>
      <sourceDesc>
        <p>{source}</p>
      </sourceDesc>
    </fileDesc>
    <revisionDesc>
      <change>Converted from a Leiden-style transcription by scripts/leiden_to_tei.py.</change>
    </revisionDesc>
  </teiHeader>
  <text type="witness" xml:id="wit-{prefix}" xml:lang="cop">
    <body>
      <div type="tractate">
{ab}
      </div>
    </body>
  </text>
</TEI>
"""


def main():
    ap = argparse.ArgumentParser(description="ライデン記法の翻刻を TEI（EpiDoc の要素）にする")
    ap.add_argument("file", help="翻刻のテキスト（UTF-8）")
    ap.add_argument("--id-prefix", default="seg", help="<s> の xml:id の頭（既定: seg → seg-1, seg-2 …）")
    ap.add_argument("--start", type=int, default=1, help="<s> の番号の始め（既定 1）")
    ap.add_argument("--standalone", action="store_true", help="TEI の文書として出す（最小限のヘッダーつき）")
    ap.add_argument("--title", default="(working transcription)", help="--standalone のときの題名")
    ap.add_argument("--out", help="書き出す先（省略すると表示する）")
    a = ap.parse_args()
    try:
        with open(a.file, encoding="utf-8") as f:
            segs = convert(f.readlines(), a.id_prefix, a.start)
    except LeidenError as e:
        print("%s: %s" % (a.file, e), file=sys.stderr)
        return 1
    if a.standalone:
        ab = render(segs, "  ")
        ab = "\n".join("        " + l for l in ab.splitlines())
        text = STANDALONE.format(title=esc(a.title), source=esc("Transcription in " + a.file),
                                 prefix=esc(a.id_prefix), ab=ab)
    else:
        text = render(segs) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("書き出しました: %s（<s> %d）" % (a.out, len(segs)))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
