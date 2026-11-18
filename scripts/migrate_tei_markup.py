#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_tei_markup.py — 以前の独自の書き方を、TEI 標準の書き方に直す

2026-11-18 まで、本文ファイルは TEI に無い要素・属性を使っていました。このスクリプトはそれを
TEI P5 の要素・属性だけで書き直します（tei_all.rng で妥当になる形）。

  以前の書き方                              →  TEI 標準の書き方
  ------------------------------------------------------------------------------------------
  <phy>…</phy>（語群）                      →  <phr>…</phr>
  <s transJa="…" transEn="…" transFr="…">   →  同じ証本の <body> の末尾に、言語ごとに
                                                <div type="translation" xml:lang="ja">
                                                  <ab><seg corresp="#セグメントのID">訳</seg>…</ab>
                                                </div>
  <w gloss="since">（文脈上の語釈）         →  <w ana="#gl-since">。語釈そのものは <standOff> の
                                                <interpGrp type="gloss" xml:lang="en">
                                                  <interp xml:id="gl-since">since</interp>
  <s subtype="incipit">（@type なし）       →  <s type="incipit">
  ギリシア語層（republic_greek.xml）
  <s corresp="rep-1"><grc>…</grc>           →  <s xml:id="grc-1" corresp="republic_tei.xml#rep-1">…</s>
     <ja>…</ja><en>…</en></s>                   と、訳の <div type="translation" xml:lang="ja|en">
                                                （中身が空の <s> は書かない）
  cert="prov"                               →  cert="low"

使い方（リポジトリのルートで）:
  python3 scripts/migrate_tei_markup.py                 何が変わるかを表示するだけ（書き込まない）
  python3 scripts/migrate_tei_markup.py --write         data/ の本文 3 ファイルを書き換える
  python3 scripts/migrate_tei_markup.py 別のファイル.xml --write

- XML 全体を作り直さず、該当するタグだけを書き換えます（差分を小さく保ち、コメントや字下げを残すため）。
- 書き込む前に、変換の前後を読み比べます。本文・語形・品詞・レンマ・訳・語釈・改行や欠損の印・ヘッダーが
  一つでも食い違えば、書き込まずに止まります。
- すでに直してあるファイルにもう一度かけても、何も変わりません。
- 以前の書き方のファイルは、ビュワー（eugnostos.html / republic.html）と検索（search.html）でも引き続き読めます。
"""
import argparse
import html
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FILES = ["data/eugnostos_tei.xml", "data/republic_tei.xml", "data/republic_greek.xml"]

T = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
XLANG = "{http://www.w3.org/XML/1998/namespace}lang"

TRANS = {"transJa": "ja", "transEn": "en", "transFr": "fr"}      # 以前の属性名 → 言語
LANG_ORDER = ["ja", "en", "fr"]
GLOSS_PREFIX = "gl-"
SYMBOLS = {":": "colon", "-": "hyphen", "?": "question-mark"}    # 記号だけの語釈の ID
GREEK_TARGET = "republic_tei.xml"                                # ギリシア語層が対応づける本文ファイル


def unattr(raw):
    """属性値の書き方（&quot; &#x27; など）を、もとの文字列に戻す。"""
    return html.unescape(raw)


def norm(s):
    return " ".join((s or "").split())


# ---------------------------------------------------------------------------------------------
# 本文ファイル（<text type="witness"> を持つファイル）
# ---------------------------------------------------------------------------------------------
def slug(text):
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or SYMBOLS.get(text.strip(), "")


class Glosses:
    """語釈の文字列 → <interp> の xml:id。同じ語釈は 1 つの <interp> を共有する。"""

    def __init__(self, src):
        self.ids, self.new = {}, []
        self.used = set(re.findall(r'\bxml:id="([^"]*)"', src))
        grp = re.search(r'<interpGrp\b[^>]*\btype="gloss"[^>]*>(.*?)</interpGrp>', src, re.S)
        if grp:                                         # すでに直してあるファイル：登録済みの語釈を引き継ぐ
            for gid, body in re.findall(r'<interp\b[^>]*\bxml:id="([^"]*)"[^>]*>(.*?)</interp>', grp.group(1), re.S):
                self.ids[html.unescape(body)] = gid

    def id_for(self, text):
        if text not in self.ids:
            base = GLOSS_PREFIX + (slug(text) or "x")
            gid, n = base, 1
            while gid in self.used:
                n += 1
                gid = "%s-%d" % (base, n)
            self.used.add(gid)
            self.ids[text] = gid
            self.new.append(text)
        return self.ids[text]


def convert_witness(src):
    rep = {}
    out = src

    # 1. 語群 <phy> → <phr>
    rep["phy"] = len(re.findall(r"<phy(?=[\s/>])", out))
    out = re.sub(r"<(/?)phy(?=[\s/>])", r"<\1phr", out)

    # 2. <s subtype="…">（@type なし）→ <s type="…">
    rep["subtype"] = 0

    def fix_s(m):
        tag = m.group(0)
        if re.search(r'\ssubtype="', tag) and not re.search(r'\stype="', tag):
            rep["subtype"] += 1
            tag = re.sub(r'\ssubtype="', ' type="', tag, count=1)
        return tag

    out = re.sub(r"<s\b[^>]*>", fix_s, out)

    # 3. <w gloss="…"> → <w ana="#gl-…"> と <interp>
    glosses = Glosses(out)
    rep["gloss"] = 0

    def fix_w(m):
        tag = m.group(0)
        g = re.search(r'\sgloss="([^"]*)"', tag)
        if not g:
            return tag
        rep["gloss"] += 1
        ptr = "#" + glosses.id_for(unattr(g.group(1)))
        rest = tag[:g.start()] + tag[g.end():]
        a = re.search(r'\sana="([^"]*)"', rest)
        if a:                                           # すでに @ana がある（辞書の語義の固定など）：後ろに足す
            return rest[:a.start(1)] + (a.group(1) + " " + ptr).strip() + rest[a.end(1):]
        return tag[:g.start()] + ' ana="%s"' % ptr + tag[g.end():]

    out = re.sub(r"<w\b[^>]*>", fix_w, out)
    rep["interp"] = len(glosses.new)
    if glosses.new:
        lines = ['<interp xml:id="%s">%s</interp>' % (glosses.ids[t], escape(t)) for t in glosses.new]
        grp = re.search(r'^([ \t]*)</interpGrp>', out, re.M) if re.search(r'<interpGrp\b[^>]*\btype="gloss"', out) else None
        if grp:                                         # 既存の一覧の末尾に足す
            ind = grp.group(1) + "  "
            out = out[:grp.start()] + "".join(ind + l + "\n" for l in lines) + out[grp.start():]
        else:
            m = re.search(r"^([ \t]*)</teiHeader>[ \t]*\n", out, re.M)
            if not m:
                raise SystemExit("!! </teiHeader> が見つかりません")
            i = m.group(1)
            block = [i + "<standOff>",
                     i + '  <interpGrp type="gloss" xml:lang="en">',
                     i + '    <desc xml:lang="ja">個々の語形の、その文脈での語釈（英語）。本文の <gi>w</gi> が <att>ana</att> で指します。辞書（lexicon.xml）の語義とは別に、その箇所での意味を記したものです。</desc>',
                     i + '    <desc xml:lang="en">Contextual English glosses of individual tokens. A <gi>w</gi> in the text points here with <att>ana</att>. They record the meaning in that passage and are independent of the senses in the lexicon (lexicon.xml).</desc>']
            block += [i + "    " + l for l in lines]
            block += [i + "  </interpGrp>", i + "</standOff>"]
            out = out[:m.end()] + "\n".join(block) + "\n" + out[m.end():]

    # 4. <s transJa="…"> → 証本ごとの <div type="translation" xml:lang="…">
    rep["trans"] = 0
    regions = []
    for m in re.finditer(r'<text\b[^>]*\btype="witness"[^>]*>', out):
        end = out.find("</body>", m.end())
        if end < 0:
            raise SystemExit("!! 証本に </body> がありません: " + m.group(0)[:80])
        regions.append((m.end(), end))
    for start, end in reversed(regions):
        region = out[start:end]
        segs = {}

        def fix_trans(m):
            tag = m.group(0)
            found = re.findall(r'\s(trans[A-Za-z]*)="([^"]*)"', tag)
            if not found:
                return tag
            sid = re.search(r'\sxml:id="([^"]*)"', tag)
            if not sid:
                raise SystemExit("!! xml:id の無い <s> に訳があります: " + tag[:100])
            for name, val in found:
                if name not in TRANS:
                    raise SystemExit("!! 知らない訳の属性 %s（%s）" % (name, sid.group(1)))
                segs.setdefault(TRANS[name], []).append((sid.group(1), unattr(val)))
                rep["trans"] += 1
            return re.sub(r'\strans[A-Za-z]*="[^"]*"', "", tag)

        region2 = re.sub(r"<s\b[^>]*>", fix_trans, region)
        if not segs:
            continue
        if re.search(r'<div\b[^>]*\btype="translation"', region):
            raise SystemExit("!! 訳の <div> と以前の訳の属性が同じ証本に混在しています。どちらかにそろえてください")
        core = region2.rstrip(" \t")
        body_ind = region2[len(core):]                   # </body> の字下げ
        i = body_ind + "  "
        lines = []
        for lang in LANG_ORDER:
            if lang not in segs:
                continue
            lines += [i + '<div type="translation" xml:lang="%s">' % lang, i + "  <ab>"]
            lines += [i + '    <seg corresp="#%s">%s</seg>' % (sid, escape(val)) for sid, val in segs[lang]]
            lines += [i + "  </ab>", i + "</div>"]
        out = out[:start] + core + "\n".join(lines) + "\n" + body_ind + out[end:]
    return out, rep


# ---------------------------------------------------------------------------------------------
# ギリシア語層（republic_greek.xml）
# ---------------------------------------------------------------------------------------------
GREEK_S = re.compile(                                   # <s> 1 つ分、またはその間に置かれたコメント
    r'[ \t]*(?:(?P<comment><!--.*?-->)|<s\b(?P<attrs>[^>]*)>\s*'
    r'(?:<grc>(?P<grc>.*?)</grc>|<grc/>)\s*(?:<ja>(?P<ja>.*?)</ja>|<ja/>)\s*(?:<en>(?P<en>.*?)</en>|<en/>)\s*'
    r'</s>)[ \t]*\n', re.S)


def convert_greek(src):
    rep = {"greek": 0, "greek_empty": 0, "cert": 0}
    d = re.search(r'^([ \t]*)<div\b[^>]*\btype="greek-parallel"[^>]*>[ \t]*\n(.*?)^[ \t]*</div>[ \t]*\n', src, re.S | re.M)
    if not d or "<grc" not in d.group(2):               # すでに直してある：<s> の cert="prov" だけ見る

        def fix_cert(m):
            if 'cert="prov"' in m.group(0):
                rep["cert"] += 1
            return m.group(0).replace('cert="prov"', 'cert="low"')

        return re.sub(r"<s\b[^>]*>", fix_cert, src), rep
    ind, inner = d.group(1), d.group(2)
    rest = GREEK_S.sub("", inner)
    if rest.strip():
        raise SystemExit("!! ギリシア語層に、読み取れない部分があります: " + rest.strip()[:120])
    i = ind + "  "
    grc, tr = [], {"ja": [], "en": []}
    for m in GREEK_S.finditer(inner):
        if m.group("comment"):                          # コメントは、同じ位置（次の <s> の前）に残す
            grc.append(i + "  " + m.group("comment"))
            continue
        attrs = m.group("attrs")
        c = re.search(r'\bcorresp="([^"]*)"', attrs)
        if not c:
            raise SystemExit("!! @corresp の無い <s> があります: " + attrs)
        target = c.group(1).split("#")[-1]
        g = (m.group("grc") or "").strip()
        ja, en = (m.group("ja") or "").strip(), (m.group("en") or "").strip()
        if not g:
            if ja or en:
                raise SystemExit("!! ギリシア語が空なのに訳があります: " + target)
            rep["greek_empty"] += 1
            continue                                    # 対応するギリシア語が無い箇所には <s> を置かない
        rep["greek"] += 1
        gid = "grc-" + target.split("-", 1)[-1]
        extra = re.sub(r'\s*\bcorresp="[^"]*"', "", attrs)
        if 'cert="prov"' in extra:
            rep["cert"] += 1
            extra = extra.replace('cert="prov"', 'cert="low"')
        grc.append(i + '  <s xml:id="%s" corresp="%s#%s"%s>%s</s>' % (gid, GREEK_TARGET, target, extra.rstrip(), g))
        if ja:
            tr["ja"].append(ind + '    <seg corresp="#%s">%s</seg>' % (gid, ja))
        if en:
            tr["en"].append(ind + '    <seg corresp="#%s">%s</seg>' % (gid, en))
    head = src[d.start():d.start(2)]
    lines = [i + "<ab>"] + grc + [i + "</ab>", ind + "</div>"]
    for lang in ("ja", "en"):
        if tr[lang]:
            lines += [ind + '<div type="translation" xml:lang="%s">' % lang, ind + "  <ab>"] + tr[lang] + [ind + "  </ab>", ind + "</div>"]
    return src[:d.start()] + head + "\n".join(lines) + "\n" + src[d.end():], rep


# ---------------------------------------------------------------------------------------------
# 変換の前後を読み比べる（どちらの書き方でも同じ内容として読めること）
# ---------------------------------------------------------------------------------------------
def strip_ws(el):
    """字下げだけの空白を捨て、属性を名前順に並べる（書き方の違いを比べる対象から外す）。"""
    items = sorted(el.attrib.items())
    el.attrib.clear()
    el.attrib.update(items)
    if el.text is not None and not el.text.strip():
        el.text = None
    for c in el:
        if c.tail is not None and not c.tail.strip():
            c.tail = None
        strip_ws(c)


def reading(text):
    """ファイルを、書き方によらない形に読む: (訳, 語釈, ギリシア語層, それ以外の XML)"""
    root = ET.fromstring(text.encode("utf-8"))
    parent = {c: p for p in root.iter() for c in p}
    trans, glosses, greek = {}, [], {}

    interp = {}
    for so in list(root.iter(T + "standOff")):
        for g in list(so.findall(T + "interpGrp")):
            if g.get("type") == "gloss":
                for it in g.iter(T + "interp"):
                    interp[it.get(XID)] = "".join(it.itertext())
                so.remove(g)
        if not len(so):
            parent[so].remove(so)

    for d in list(root.iter(T + "div")):
        if d.get("type") == "translation":
            for e in d.iter():
                if e.get("corresp"):
                    trans[(d.get(XLANG), e.get("corresp").split("#")[-1])] = norm("".join(e.itertext()))
            parent[d].remove(d)

    is_greek = any(d.get("type") == "greek-parallel" for d in root.iter(T + "div"))
    for el in root.iter():
        tag = el.tag[len(T):] if isinstance(el.tag, str) and el.tag.startswith(T) else el.tag
        if tag == "phy":
            el.tag = T + "phr"
        elif tag == "s":
            sid = el.get(XID)
            for attr, lang in TRANS.items():
                if attr in el.attrib:
                    trans[(lang, sid)] = norm(el.attrib.pop(attr))
            if "subtype" in el.attrib and "type" not in el.attrib:
                el.set("type", el.attrib.pop("subtype"))
            if el.get("cert") == "prov":
                el.set("cert", "low")
        elif tag == "w":
            g = el.attrib.pop("gloss", None)
            keep = []
            for p in (el.get("ana") or "").split():
                if g is None and p.split("#")[-1] in interp:
                    g = interp[p.split("#")[-1]]
                else:
                    keep.append(p)
            if keep:
                el.set("ana", " ".join(keep))
            else:
                el.attrib.pop("ana", None)
            glosses.append(g)

    if is_greek:
        for d in root.iter(T + "div"):
            if d.get("type") != "greek-parallel":
                continue
            for s in list(d.iter(T + "s")):
                key = (s.get("corresp") or "").split("#")[-1]
                old = {c.tag[len(T):]: norm("".join(c.itertext())) for c in s}
                if "grc" in old:
                    g, ja, en = old.get("grc", ""), old.get("ja", ""), old.get("en", "")
                else:
                    g = norm("".join(s.itertext()))
                    ja, en = trans.pop(("ja", s.get(XID)), ""), trans.pop(("en", s.get(XID)), "")
                if g or ja or en:
                    greek[key] = (g, ja, en, s.get("cert") or "")
            d[:] = []                                   # 中身は greek に移した
            d.text = None
    strip_ws(root)
    return trans, glosses, greek, ET.tostring(root, encoding="unicode")


def same_reading(old, new):
    comments = lambda t: [norm(c) for c in re.findall(r"<!--.*?-->", t, re.S)]
    a, b = reading(old) + (comments(old),), reading(new) + (comments(new),)
    names = ["訳", "語釈", "ギリシア語層", "それ以外の本文・ヘッダー", "コメント"]
    return [n for n, x, y in zip(names, a, b) if x != y]


# ---------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="以前の独自の書き方を TEI 標準の書き方に直す")
    ap.add_argument("files", nargs="*", help="対象ファイル（省略時: data/ の本文 3 ファイル）")
    ap.add_argument("--write", action="store_true", help="書き込む（指定しなければ表示だけ）")
    args = ap.parse_args()
    files = args.files or [os.path.join(ROOT, f) for f in DEFAULT_FILES]
    changed = 0
    for path in files:
        src = open(path, encoding="utf-8", newline="").read()
        is_greek = bool(re.search(r'<div\b[^>]*\btype="greek-parallel"', src))
        out, rep = convert_greek(src) if is_greek else convert_witness(src)
        name = os.path.relpath(path, ROOT) if os.path.abspath(path).startswith(ROOT) else path
        if out == src:
            print("== %s: 変更なし（すでに TEI 標準の書き方です）" % name)
            continue
        diff = same_reading(src, out)
        if diff:
            raise SystemExit("!! %s: 変換の前後で内容が食い違います（%s）。書き込みません。" % (name, "・".join(diff)))
        changed += 1
        if is_greek:
            print("== %s: ギリシア語 <s> %d（空で省いたもの %d）、cert=prov→low %d" % (name, rep["greek"], rep["greek_empty"], rep["cert"]))
        else:
            print("== %s: <phy>→<phr> %d、訳 %d、語釈 %d（<interp> %d 種）、subtype→type %d"
                  % (name, rep["phy"], rep["trans"], rep["gloss"], rep["interp"], rep["subtype"]))
        print("   変換の前後で、本文・訳・語釈・ヘッダーの内容は同じです")
        if args.write:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(out)
    if changed and not args.write:
        print("\n（表示だけです。書き込むには --write を付けてください）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
