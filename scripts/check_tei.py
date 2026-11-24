#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_tei.py — TEI データの点検（ポインタの切れ・書き方の誤りを見つける）

TEI のスキーマ（tei_all.rng）は「要素や属性の並びが正しいか」だけを調べます。このスクリプトは、
スキーマでは分からない次の点を調べます。

  1. 以前の独自の書き方が残っていないか
       <phy>、<s> の transJa / transEn / transFr、<w> の gloss、<grc>・<ja>・<en>、cert="prov"、<pd>
  2. xml:id が重複していないか
  3. 対訳（<div type="translation">）
       - xml:lang があるか
       - 各 <seg> の @corresp が、同じ <text> の中の <s> を指しているか
       - 同じ <s> に、同じ言語の訳が 2 つ無いか
  4. <w> の @ana が、文脈上の語釈（<interp>）か、辞書（lexicon.xml）の項目を指しているか
  5. 使われていない語釈（どの <w> からも指されていない <interp>）
  6. ギリシア語層（republic_greek.xml）の @corresp が、本文 republic_tei.xml の <s> を指しているか
  7. TEI の Schematron 規則のうち、このコーパスに関係するもの
       （@subtype には @type が要る、<ab> や <p> を入れ子にしない、@target を持つ <relatedItem> は空、など。
         xmllint は Schematron を実行しないので、ここで同じ内容を調べます）
  8. 並行箇所（parallels.xml の <linkGrp type="parallel">）の <link> の @target が、2 つの <s> を指しているか
  9. 同じファイルの中を指すポインタ（<ref>・<ptr>・<relatedItem> の @target が "#…" のもの。カタログの文書どうしの関連など）の
     指す xml:id があるか
 10. 辞書の見出し（lexicon.xml の <orth>）と本文の <w> の @lemma に、コプト文字以外の文字が混じっていないか
       コプト文字は Coptic のブロック（U+2C80–2CFF）と、ギリシア文字のブロックにあるコプト文字（U+03E2–03EF: ϣ ϥ ϩ ϫ ϭ ϯ など）。
       見た目の似たラテン文字（o・e など）やギリシア文字（ο・ε など）、キリル文字の混入を見つける。上線などの合成記号、
       欠損の記号（[ ] . …）、ハイフンは文字ではないので調べない。ギリシア語の本文のファイル（<TEI xml:lang="grc">）は対象外。
 11. 語釈に、使わない語（scripts/gloss_rules.json）が入っていないか
       この版は文法関係や目的語の標示を注釈しない（edition.html「この版で扱わないこと」）。そのため、語釈と辞書の語義に
       「目的語標識」「object marker」のような語を入れない。調べるのは語釈の文字列だけで、説明の文章は調べない:
         - TEI の <interp>（語釈）、辞書（lexicon.xml）の <sense>・<usg>（点検するファイルそれぞれ）
         - ファイルを指定しないで実行したときは、さらに source/lexicon.csv の語義と用法の列（en・ja・fr・usg_ja・usg_en）、
           自動注釈のスクリプト（source/nhc_fulltext_split/annotation/annotate_tei.py）の語釈表と、その出力の
           annotation/core_glosses.tsv、抜き取り表（evaluation/review_sample.tsv）の「自動の語義」
       比べるときは、大文字と小文字、全角と半角、’ と ' の違いを無視する。規則の足し方は CONTRIBUTING.md の「10.」。
 12. 許可リスト（scripts/tei_allowlist.json）の外の属性や値が無いか
       <w>・<phr>・<s>・<supplied>・<gap>・<pb>・<lb>・<ab>・<seg>・<interpGrp>・<interp>・<linkGrp>・<link> は、許可リストに挙げた
       属性しか持てず、値を決めた属性はその値しか取れない（<w> の @type は品詞の一覧 data/pos_labels.json、@cert は high・medium・low、
       @resp は今の 3 つ）。文法関係を表す属性などが入ると失敗する。いま残っている一覧の外の品詞（直す予定のもの）は、許可リストの
       exceptions に場所ごとに書いてあり、直して無くなると「もう要らない」と知らせる。要素と属性の説明は docs/sheneset_odd.xml。

--schema に tei_all.rng の場所を渡すと、xmllint によるスキーマ検証も続けて行います。

使い方（リポジトリのルートで）:
  python3 scripts/check_tei.py                                  data/ と source/nhc_fulltext_split/tei/ の全ファイル
  python3 scripts/check_tei.py --schema ~/Downloads/tei_all.rng  スキーマ検証も行う
  python3 scripts/check_tei.py data/republic_tei.xml             指定したファイルだけ

問題が無ければ終了コード 0、あれば 1。ファイルは書き換えません。
 13. コーパスの外の並行テキスト（data/parallels/ の TEI）が、言語（<language ident>）・底本（<sourceDesc><bibl>）・ライセンス
       （<licence>）をヘッダーに持ち、本文を xml:id のある <s> に分けているか（data/parallels/README.md）
"""
import argparse
import csv
import glob
import json
import os
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSS_RULES = os.path.join(ROOT, "scripts", "gloss_rules.json")
ALLOWLIST = os.path.join(ROOT, "scripts", "tei_allowlist.json")
POS_LABELS = os.path.join(ROOT, "data", "pos_labels.json")
NHC = os.path.join(ROOT, "source", "nhc_fulltext_split")
T = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
XLANG = "{http://www.w3.org/XML/1998/namespace}lang"

OLD_ELEMENTS = {"phy": "<phr>", "pd": "<pb>", "grc": "<s> の本文", "ja": '<div type="translation" xml:lang="ja">', "en": '<div type="translation" xml:lang="en">'}
OLD_ATTRS = {"transJa", "transEn", "transFr", "transGrc"}
CERT = {"high", "medium", "low", "unknown"}
P_INSIDE_OK = {"exemplum", "item", "note", "q", "quote", "remarks", "said", "sp", "stage", "cell", "figure"}


def name(tag):
    return tag.split("}")[-1] if isinstance(tag, str) else ""


def non_coptic(s):
    """s の中の、コプト文字ではない文字（Unicode の文字＝カテゴリ L*）。合成記号・記号・数字・空白は数えない（10.）"""
    return [ch for ch in s if unicodedata.category(ch).startswith("L")
            and not (0x2C80 <= ord(ch) <= 0x2CFF or 0x03E2 <= ord(ch) <= 0x03EF)]


def describe(chars):
    """混じった文字の説明（「o = LATIN SMALL LETTER O」）"""
    return "、".join("%s = %s" % (ch, unicodedata.name(ch, "U+%04X" % ord(ch))) for ch in dict.fromkeys(chars))


def gloss_rules(cache=[]):
    """語釈に使わない語（11.）。scripts/gloss_rules.json の rules[].terms を、正規化した形と組にして返す。"""
    if not cache:
        with open(GLOSS_RULES, encoding="utf-8") as f:
            rules = json.load(f).get("rules", [])
        for i, r in enumerate(rules, 1):
            terms = r.get("terms")
            if not terms or not all(isinstance(t, str) and fold(t) for t in terms):
                sys.exit("gloss_rules.json の %d 番目の規則に terms（空でない文字列の配列）がありません" % i)
            cache += [(t, fold(t)) for t in terms]
    return cache


def fold(s):
    """比べるための形: NFKC（全角と半角をそろえる）、大文字と小文字を区別しない、’ ʼ を ' に、空白を 1 つに。"""
    s = unicodedata.normalize("NFKC", s or "").casefold().replace("’", "'").replace("ʼ", "'")
    return " ".join(s.split())


def banned(text):
    """text に入っている、語釈に使わない語（gloss_rules.json に書いたままの形）の一覧。"""
    t = fold(text)
    return [term for term, f in gloss_rules() if f in t]


def check_gloss_sources():
    """11. のうち TEI 以外のもの（辞書の CSV・注釈のスクリプトの語釈表など）。{ファイル: [問題]} を返す。"""
    out = {}

    def add(path, line, column, text):
        for term in banned(text):
            out.setdefault(path, []).append("%d 行目（%s）: 語釈に使わない語「%s」が入っています: %s" % (line, column, term, text))

    def tsv_columns(path, columns, delimiter="\t"):
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8-sig", newline="") as f:
            for no, row in enumerate(csv.DictReader(f, delimiter=delimiter), 2):
                for c in columns:
                    add(path, no, c, row.get(c) or "")

    tsv_columns(os.path.join(ROOT, "source", "lexicon.csv"), ("en", "ja", "fr", "usg_ja", "usg_en"), ",")
    tsv_columns(os.path.join(NHC, "annotation", "core_glosses.tsv"), ("English", "日本語"))
    tsv_columns(os.path.join(NHC, "evaluation", "review_sample.tsv"), ("自動の語義",))
    script = os.path.join(NHC, "annotation", "annotate_tei.py")
    if os.path.exists(script):                          # 語釈表 LEXICON の行（語形|品詞|レンマ|英語|日本語）
        with open(script, encoding="utf-8") as f:
            for no, line in enumerate(f, 1):
                cols = line.rstrip("\n").split("|")
                if len(cols) == 5:
                    add(script, no, "語釈表", cols[3] + " | " + cols[4])
    return out


def allowlist(cache={}):
    """12. の許可リスト。{"rules": {要素: {属性: 値の集合 か None（値を決めない）}}, "exc": {例外}, "used": 使った例外}"""
    if not cache:
        with open(ALLOWLIST, encoding="utf-8") as f:
            a = json.load(f)
        with open(POS_LABELS, encoding="utf-8") as f:
            pos = {t["tag"] for t in json.load(f)["tags"]}
        rules = {}
        for el, spec in a.get("elements", {}).items():
            rules[el] = {att: (pos if v.get("from") == "data/pos_labels.json" else set(v["values"]) if "values" in v else None)
                         for att, v in spec.get("attributes", {}).items()}
        exc = {(e["file"], e.get("seg"), e.get("w"), e["attribute"], e["value"]) for e in a.get("exceptions", [])}
        cache.update(rules=rules, exc=exc, used=set())
    return cache


def att_name(a):
    return a.replace("{http://www.w3.org/XML/1998/namespace}", "xml:")


def ids_of(path, cache={}):
    """ファイル内の xml:id → 要素名。"""
    if path not in cache:
        try:
            cache[path] = {el.get(XID): name(el.tag) for el in ET.parse(path).getroot().iter() if el.get(XID)}
        except (OSError, ET.ParseError):
            cache[path] = None
    return cache[path]


def check(path):
    """問題の一覧（文字列）を返す。"""
    out = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        return ["XML として読めません（整形式エラー）: %s" % e]
    parent = {c: p for p in root.iter() for c in p}

    def where(el):
        return "<%s%s>" % (name(el.tag), " " + (el.get(XID) or el.get("corresp") or el.get("n") or "") if (el.get(XID) or el.get("corresp") or el.get("n")) else "")

    def ancestors(el):
        while el in parent:
            el = parent[el]
            yield el

    def text_of(el):                                    # いちばん近い <text>（証本）
        return next((a for a in ancestors(el) if name(a.tag) == "text"), None)

    here = os.path.dirname(os.path.abspath(path))
    lexicon = ids_of(os.path.join(ROOT, "data", "lexicon.xml")) or {}

    # 2. xml:id の重複
    seen = Counter(el.get(XID) for el in root.iter() if el.get(XID))
    out += ["xml:id が重複しています: %s（%d 回）" % (i, n) for i, n in seen.items() if n > 1]
    local = {el.get(XID): el for el in root.iter() if el.get(XID)}

    gloss_ids = {i.get(XID) for g in root.iter(T + "interpGrp") if g.get("type") == "gloss" for i in g.iter(T + "interp") if i.get(XID)}
    gloss_used = set()

    for el in root.iter():
        tag, a = name(el.tag), el.attrib
        if not tag:
            continue
        # 1. 以前の独自の書き方
        if tag in OLD_ELEMENTS and el.tag.startswith(T):
            out.append("以前の書き方 <%s> が残っています（TEI 標準では %s）: %s" % (tag, OLD_ELEMENTS[tag], where(parent.get(el, el))))
        for old in OLD_ATTRS & set(a):
            out.append('以前の書き方 @%s が残っています（TEI 標準では <div type="translation">）: %s' % (old, where(el)))
        if tag == "w" and "gloss" in a:
            out.append("以前の書き方 <w gloss=…> が残っています（TEI 標準では @ana と <interp>）: %s" % (el.get("lemma") or ""))
        if "cert" in a and a["cert"] not in CERT:
            out.append('@cert="%s" は TEI の値ではありません（high / medium / low / unknown）: %s' % (a["cert"], where(el)))

        # 4. <w> の @ana
        if tag == "w":
            for p in (a.get("ana") or "").split():
                doc, _, frag = p.partition("#")
                if doc:
                    other = ids_of(os.path.join(here, doc))
                    if other is None:
                        out.append("<w> の @ana が指すファイルを読めません: %s" % p)
                    elif frag not in other:
                        out.append("<w> の @ana の指す先がありません: %s（レンマ %s）" % (p, el.get("lemma")))
                elif frag in gloss_ids:
                    gloss_used.add(frag)
                elif frag not in local and frag not in lexicon:
                    out.append("<w> の @ana の指す先（語釈の <interp> か辞書の項目）がありません: %s（レンマ %s）" % (p, el.get("lemma")))

        # 7. Schematron の規則
        anc = [name(x.tag) for x in ancestors(el)]
        floating = "floatingText" in anc
        if "subtype" in a and "type" not in a:
            out.append("@subtype だけで @type がありません: %s" % where(el))
        if "when" in a and any(k in a for k in ("notBefore", "notAfter", "from", "to")):
            out.append("@when は他の日付の属性と一緒に使えません: %s" % where(el))
        if tag in ("p", "ab") and not floating and ("p" in anc or "ab" in anc) and name(parent[el].tag) not in P_INSIDE_OK:
            out.append("<%s> が <p> か <ab> の中にあります: %s" % (tag, where(el)))
        if tag == "div" and not floating and ("p" in anc or "ab" in anc):
            out.append("<div> が <p> か <ab> の中にあります: %s" % where(el))
        if tag == "s" and any(name(c.tag) == "s" for c in el.iter() if c is not el):
            out.append("<s> の中に <s> があります: %s" % where(el))
        if tag == "ref" and "target" in a and "cRef" in a:
            out.append("<ref> に @target と @cRef の両方があります")
        if tag == "relatedItem" and "target" in a and len(el):
            out.append("@target を持つ <relatedItem> は空でなければなりません: %s" % a["target"])
        if tag == "relatedItem" and "target" not in a and not len(el):
            out.append("<relatedItem> に @target も子要素もありません")
        if tag == "msIdentifier" and name(parent[el].tag) != "msPart":
            kids = list(el)
            if (kids and name(kids[0].tag) in ("idno", "altIdentifier")) or not "".join(el.itertext()).strip():
                out.append("<msIdentifier> は所蔵先（repository など）から始めます")

    # 5. 使われていない語釈
    out += ["どの <w> からも指されていない語釈があります: %s" % i for i in sorted(gloss_ids - gloss_used)]

    # 3. 対訳
    for d in root.iter(T + "div"):
        if d.get("type") != "translation":
            continue
        lang = d.get(XLANG)
        if not lang:
            out.append('<div type="translation"> に xml:lang がありません')
        home = text_of(d)
        done = set()
        for seg in d.iter(T + "seg"):
            ptrs = (seg.get("corresp") or "").split()
            if not ptrs:
                out.append("対訳（%s）の <seg> に @corresp がありません: %s" % (lang, "".join(seg.itertext())[:30]))
            for p in ptrs:
                target = local.get(p[1:]) if p.startswith("#") else None
                if target is None or name(target.tag) != "s":
                    out.append("対訳（%s）の @corresp が <s> を指していません: %s" % (lang, p))
                elif text_of(target) is not home:
                    out.append("対訳（%s）の @corresp が別の証本の <s> を指しています: %s" % (lang, p))
                elif p in done:
                    out.append("対訳（%s）が同じ <s> に 2 つあります: %s" % (lang, p))
                done.add(p)

    # 6. ギリシア語層
    for d in root.iter(T + "div"):
        if d.get("type") != "greek-parallel":
            continue
        for s in d.iter(T + "s"):
            c = s.get("corresp") or ""
            doc, _, frag = c.partition("#")
            other = ids_of(os.path.join(here, doc)) if doc and frag else None
            if not doc or not frag:
                out.append('ギリシア語の <s> の @corresp は "republic_tei.xml#rep-N" の形で書きます: %s' % (c or where(s)))
            elif other is None:
                out.append("ギリシア語の <s> の @corresp が指すファイルを読めません: %s" % c)
            elif other.get(frag) != "s":
                out.append("ギリシア語の <s> の @corresp の指す <s> がありません: %s" % c)

    # 8. 並行箇所
    for g in root.iter(T + "linkGrp"):
        if g.get("type") != "parallel":
            continue
        for link in g.iter(T + "link"):
            ptrs = (link.get("target") or "").split()
            if len(ptrs) != 2:
                out.append("並行箇所の <link> の @target は、セグメント（<s>）2 つを指します: %s" % (link.get("target") or "（空）"))
            for p in ptrs:
                doc, _, frag = p.partition("#")
                other = ids_of(os.path.join(here, doc)) if doc else {k: name(v.tag) for k, v in local.items()}
                if other is None:
                    out.append("並行箇所の <link> が指すファイルを読めません: %s" % p)
                elif other.get(frag) != "s":
                    out.append("並行箇所の <link> の指す <s> がありません: %s" % p)

    # 9. 同じファイルの中を指すポインタ
    for el in root.iter():
        if name(el.tag) in ("ref", "ptr", "relatedItem"):
            for p in (el.get("target") or "").split():
                if p.startswith("#") and p[1:] not in local:
                    out.append("<%s> の @target の指す xml:id がありません: %s" % (name(el.tag), p))

    # 10. 辞書の見出しと @lemma に混じった、コプト文字以外の文字（ギリシア語の本文のファイルは対象外）
    if root.get(XLANG) != "grc":
        for orth in root.iter(T + "orth"):
            bad = non_coptic(orth.text or "")
            if bad:
                entry = next((a for a in ancestors(orth) if name(a.tag) == "entry"), None)
                out.append("辞書の見出しにコプト文字以外の文字が混じっています: %s %s（%s）"
                           % (entry.get(XID) if entry is not None else "", orth.text, describe(bad)))
        lemmas = Counter(w.get("lemma") for w in root.iter(T + "w") if w.get("lemma") and non_coptic(w.get("lemma")))
        out += ["<w> の @lemma にコプト文字以外の文字が混じっています: %s（%s）%d 語" % (l, describe(non_coptic(l)), n)
                for l, n in sorted(lemmas.items())]

    # 12. 許可リストの外の属性・値（<w> の例外は、ファイル・<s> の id・<s> の中の番号で当てる）
    al = allowlist()
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, "/")
    wpos = {}
    for s_el in root.iter(T + "s"):
        for i, w in enumerate(s_el.iter(T + "w"), 1):
            wpos[w] = (s_el.get(XID), i)
    bad_atts, bad_vals = Counter(), Counter()
    for el in root.iter():
        rules = al["rules"].get(name(el.tag))
        if rules is None:
            continue
        for a, v in el.attrib.items():
            a = att_name(a)
            if a not in rules:
                bad_atts[(name(el.tag), a)] += 1
            elif rules[a] is not None and v not in rules[a]:
                seg, i = wpos.get(el, (None, None))
                key = (rel, seg, i, a, v)
                if key in al["exc"]:
                    al["used"].add(key)
                else:
                    bad_vals[(name(el.tag), a, v)] += 1
    out += ["許可リストに無い属性 @%s が <%s> にあります（%d 個。scripts/tei_allowlist.json）" % (a, e, n) for (e, a), n in sorted(bad_atts.items())]
    out += ["<%s> の @%s に許可リストに無い値「%s」があります（%d 個。scripts/tei_allowlist.json）" % (e, a, v, n) for (e, a, v), n in sorted(bad_vals.items())]

    # 11. 語釈に使わない語（語釈 <interp>、辞書の <sense>・<usg>。入れ子の <sense> は外側でまとめて調べる）
    for el in root.iter():
        tag = name(el.tag)
        if tag not in ("interp", "sense", "usg") or (tag == "sense" and any(name(a.tag) == "sense" for a in ancestors(el))):
            continue
        pieces = [t for t in (" ".join(x.split()) for x in el.itertext()) if t]   # <sense> では言語ごとの <quote>
        for term in banned(" ".join(pieces)):
            entry = el if tag == "interp" else next((a for a in ancestors(el) if name(a.tag) in ("entry", "superEntry")), el)
            out.append("語釈に使わない語「%s」が入っています（scripts/gloss_rules.json）: <%s> %s「%s」"
                       % (term, tag, entry.get(XID) or "", " | ".join(pieces)[:100]))
    # 13. コーパスの外の並行テキスト（data/parallels/ の TEI）: 言語・底本・ライセンスがヘッダーにあるか
    if os.path.basename(os.path.dirname(os.path.abspath(path))) == "parallels" and os.path.basename(path) != "parallels.xml":
        lang = root.find(".//%sprofileDesc/%slangUsage/%slanguage" % (T, T, T))
        if lang is None or not lang.get("ident"):
            out.append("コーパスの外の並行テキストには、<profileDesc><langUsage><language ident=\"…\"> で本文の言語を書きます")
        if root.find(".//%ssourceDesc/%sbibl" % (T, T)) is None:
            out.append("コーパスの外の並行テキストには、<sourceDesc><bibl> で底本（使った版）を書きます")
        lic = root.find(".//%spublicationStmt/%savailability/%slicence" % (T, T, T))
        if lic is None or not ("".join(lic.itertext()).strip() or lic.get("target")):
            out.append("コーパスの外の並行テキストには、<publicationStmt><availability><licence> でライセンスを書きます")
        if not any(s.get(XID) for s in root.iter(T + "s")):
            out.append("コーパスの外の並行テキストの本文は、xml:id を持つ <s> に分けます（並行箇所の <link> が指す）")
    return out


def main():
    ap = argparse.ArgumentParser(description="TEI データの点検")
    ap.add_argument("files", nargs="*", help="対象ファイル（省略時: data/*.xml・data/parallels/*.xml・source/nhc_fulltext_split/tei/*.xml）")
    ap.add_argument("--schema", help="tei_all.rng の場所（指定すると xmllint でスキーマ検証も行う）")
    args = ap.parse_args()
    files = args.files or (sorted(glob.glob(os.path.join(ROOT, "data", "*.xml"))) + sorted(glob.glob(os.path.join(ROOT, "data", "parallels", "*.xml")))
                          + sorted(glob.glob(os.path.join(ROOT, "source", "nhc_fulltext_split", "tei", "*.xml"))))
    bad = 0
    for path in files:
        problems = check(path)
        if args.schema and not (problems and problems[0].startswith("XML として")):
            r = subprocess.run(["xmllint", "--noout", "--relaxng", args.schema, path], capture_output=True, text=True)
            if r.returncode != 0:
                msgs = [l for l in r.stderr.splitlines() if "validity error" in l or "parser error" in l]
                problems += ["スキーマ（%s）で妥当ではありません: %s" % (os.path.basename(args.schema), m.split(": ", 1)[-1]) for m in (msgs[:5] or [r.stderr.strip()[:200]])]
        if problems:
            bad += 1
            shown = os.path.relpath(path, ROOT) if os.path.abspath(path).startswith(ROOT) else path
            print("!! %s: %d 件" % (shown, len(problems)))
            for p in problems[:40]:
                print("   - " + p)
            if len(problems) > 40:
                print("   …ほか %d 件" % (len(problems) - 40))
    n = len(files)
    if not args.files:                                  # 11. の TEI 以外のもの（ファイルを指定しないときだけ）
        n += 4                                          # lexicon.csv・annotate_tei.py・core_glosses.tsv・review_sample.tsv
        for path, problems in sorted(check_gloss_sources().items()):
            bad += 1
            print("!! %s: %d 件" % (os.path.relpath(path, ROOT), len(problems)))
            for p in problems[:40]:
                print("   - " + p)
            if len(problems) > 40:
                print("   …ほか %d 件" % (len(problems) - 40))
    if not args.files:                                  # 12. の例外のうち、もう当たらないもの（直したあと。許可リストから消す）
        al = allowlist()
        stale = sorted(al["exc"] - al["used"], key=lambda k: (k[0], k[1] or "", k[2] or 0))
        if stale:
            print("注意: 許可リストの例外のうち %d 件はもう要りません（scripts/tei_allowlist.json の exceptions から消す）:" % len(stale))
            for k in stale[:20]:
                print("   - %s %s w=%s @%s=%s" % k)
    what = "点検" + ("とスキーマ検証" if args.schema else "")
    if bad:
        print("\n%d / %d ファイルに問題があります（%s）" % (bad, n, what))
        return 1
    print("%d ファイル: 問題は見つかりませんでした（%s）" % (n, what))
    if not args.schema:
        print("（スキーマ検証は行っていません。--schema に tei_all.rng の場所を渡すと行います）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
