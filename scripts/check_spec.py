#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_spec.py — TEI データが符号化の仕様（「ナグ・ハマディ写本コプト語テキスト TEI XML アノテーション仕様書（改訂版）」）
に沿っているかを点検する

scripts/check_tei.py（ポインタの切れ・以前の書き方・スキーマ）では分からない、仕様の約束を調べます。
見つけたものは 3 段階で報告します。

  要修正  仕様に反していて、直す必要があるもの（打ち間違いの品詞コード、指す先の無い @resp、数で書いた extent など）
  要確認  仕様と違うが、直すかどうかを人が決めるもの（EpiDoc と違う reason の値、語群の中の改行の break など）
  参考    仕様の移行の目安（Coptic SCRIPTORIUM と違うサイトの品詞コード、機能語のレンマの書き方など）

調べること:
  1. <w type>（品詞コード）: サイトの品詞表にも Coptic SCRIPTORIUM にも無いコード（要修正）、サイトにだけあるコード（参考）
  2. <w xml:lang>: 言語名（Greek など）ではなく BCP 47 の符号か。借用語は grc
  3. <gap>: reason・quantity・extent・unit（EpiDoc 9.8）
  4. <supplied>: reason の値
  5. @resp・@cert: @resp が同じファイルの xml:id を指しているか、@cert の値
  6. <lb>・<pb>・<cb>: 語群（<phr>）の中なら break="no"、語群のあいだなら break="no" を付けない
  7. 使わない書き方: <w pos>、<seg type="orig_group">、<sourceDoc>、名前だけの @calendar、@datingMethod の無い @when-custom
  8. 人称代名詞・冠詞のレンマの書き方（語形か、Coptic SCRIPTORIUM の見出しか）の内訳（参考）
  9. 辞書 data/lexicon.xml: 品詞コード、見出しの記号（| * ‐ -）、機能語の品詞なのに長い見出し（語の切り方の誤りの疑い）

使い方（リポジトリのルートで）:
  python3 scripts/check_spec.py                       data/ と source/nhc_fulltext_split/tei/ の全ファイル
  python3 scripts/check_spec.py data/republic_tei.xml  指定したファイルだけ
  python3 scripts/check_spec.py --tsv build/spec_report.tsv   見つけたものを 1 件 1 行の TSV にも書く
  python3 scripts/check_spec.py --examples 10         種類ごとに示す例の数（既定 3）

要修正が 1 件でもあれば終了コード 1、無ければ 0。ファイルは書き換えません。標準ライブラリだけで動きます（Python 3.9 以上）。
"""
import argparse
import glob
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = "{http://www.tei-c.org/ns/1.0}"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XID = "{%s}id" % XML_NS
XLANG = "{%s}lang" % XML_NS

# Coptic SCRIPTORIUM のタグセット（UD の対応表に載っている 47 個。https://universaldependencies.org/cop/morphology.html）
CS_TAGS = set("""AAOR ACAUS ACONJ AFUTCONJ AJUS ANEGAOR ANEGJUS ANEGOPT ANEGPST ANY AOPT APST CPRET FUT
ACOND ALIM APREC CCIRC CCOND CREL EXIST V VBD VIMP VSTAT COP PINT PPERI PPERO PPERS ADV IMOD NEG
ART PDEM PPOS CFOC PTC N NOUN FM UNKNOWN CONJ NPROP NUM PREP PUNCT""".split())
# サイトにだけあるコードの、Coptic SCRIPTORIUM での扱い（仕様書 §5 の表）
SITE_ONLY = OrderedDict([
    ("PPER", "PPERS・PPERO・PPERI に分ける"), ("REL", "CREL にそろえる"), ("CIRC", "CCIRC にそろえる"),
    ("PRET", "CPRET にそろえる"), ("NEGPST", "ANEGPST にそろえる"), ("POSS", "PPOS にそろえる"),
    ("A", "個別の助動詞のコードに直す"), ("AUX", "個別の助動詞のコードに直す"), ("HABIT", "個別の助動詞のコード（AAOR など）に直す"),
    ("CONV", "CCIRC・CREL・CFOC・CPRET のどれかに直す"), ("ADJ", "N にする（提案）"),
    ("PFX", "名詞の <w> の中の <m> にする（提案）"), ("INTERJ", "PTC にする（提案）"), ("X", "仮の値（品詞を決められない語）"),
])
TYPOS = {"CFOS": "CFOC", "PERP": "PREP"}
GAP_REASONS = {"lost", "illegible", "omitted"}
SUPPLIED_REASONS = {"lost", "omitted", "undefined", "lost-in-source-file"}
CERT = {"high", "medium", "low", "unknown"}
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
FUNCTION_POS = {"PPER", "PPERS", "PPERO", "PPERI", "ART", "POSS", "PPOS"}

ERROR, WARN, INFO = "要修正", "要確認", "参考"


def local(tag):
    return tag.split("}")[-1] if isinstance(tag, str) else ""


def site_pos_names():
    path = os.path.join(ROOT, "scripts", "build_site.py")
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return set()
    i = src.find("POS_NAMES = {")
    j = src.find("\n}", i)
    return set(re.findall(r'"([A-Z]+)"\s*:', src[i:j])) if i >= 0 and j >= 0 else set()


def letters(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s or "") if unicodedata.category(ch).startswith("L"))


class Report:
    def __init__(self, examples):
        self.items = defaultdict(list)     # (段階, 種類) -> [(ファイル, 場所, 内容)]
        self.tallies = Counter()           # 数だけを集計するもの（機能語のレンマの書き方）
        self.examples = examples

    def add(self, level, kind, path, where, what):
        self.items[(level, kind)].append((path, where, what))

    def count(self, level):
        return sum(len(v) for (lv, _), v in self.items.items() if lv == level)


def parent_map(root):
    return {c: p for p in root.iter() for c in p}


def check_text_file(path, root, rep, site_tags):
    rel = os.path.relpath(path, ROOT)
    parents = parent_map(root)
    ids = {e.get(XID) for e in root.iter() if e.get(XID)}

    def seg_of(el):
        p = el
        while p is not None and local(p.tag) != "s":
            p = parents.get(p)
        return (p.get(XID) or "") if p is not None else ""

    def inside(el, name):
        p = parents.get(el)
        while p is not None:
            if local(p.tag) == name:
                return True
            p = parents.get(p)
        return False

    lemma_style = Counter()
    for el in root.iter():
        tag = local(el.tag)
        # 5. @resp・@cert（すべての要素）
        for ref in (el.get("resp") or "").split():
            if ref.startswith("#") and ref[1:] not in ids:
                rep.add(ERROR, "@resp の指す xml:id が無い", rel, seg_of(el) or tag, ref)
        cert = el.get("cert")
        if cert is not None and cert not in CERT:
            try:
                float(cert)
            except ValueError:
                rep.add(ERROR, "@cert の値が high・medium・low・unknown・数値のどれでもない", rel, seg_of(el) or tag, cert)

        if tag == "w":
            pos = el.get("type")
            where = seg_of(el)
            form = "".join(el.itertext()).strip()
            if pos is None:
                pass
            elif "_" in pos and all(x in CS_TAGS for x in pos.split("_")):
                rep.add(WARN, "融合した品詞コード（語を分けて付け直す）", rel, where, "%s（%s）" % (pos, form))
            elif pos in TYPOS:
                rep.add(ERROR, "品詞コードの打ち間違い", rel, where, "%s → %s（%s）" % (pos, TYPOS[pos], form))
            elif pos not in CS_TAGS and pos not in site_tags and pos not in SITE_ONLY:
                rep.add(ERROR, "サイトの品詞表にも Coptic SCRIPTORIUM にも無い品詞コード", rel, where, "%s（%s）" % (pos, form))
            elif pos in SITE_ONLY:
                rep.add(INFO, "サイトにだけある品詞コード: %s → %s" % (pos, SITE_ONLY[pos]), rel, where, form)
            elif pos not in site_tags and site_tags:
                rep.add(WARN, "Coptic SCRIPTORIUM のコードだが、サイトの品詞表（POS_NAMES）に無い", rel, where,
                        "%s（%s）" % (pos, form))
            if el.get("pos") is not None:
                rep.add(WARN, "<w> の @pos（品詞は @type に書く）", rel, where, el.get("pos"))
            if re.search(r"[\[\]⟦⟧{}<>()]", form):
                rep.add(WARN, "角括弧などの記号が文字のまま <w> にある（<w> には書かれた字だけを入れる）", rel, where, form)
            lang = el.get(XLANG)
            if lang is not None and not LANG_RE.match(lang):
                rep.add(ERROR, "xml:lang が BCP 47 の符号でない", rel, where, "%s（%s）" % (lang, form))
            elif lang is not None and lang != "grc" and lang != "cop":
                rep.add(WARN, "借用語の印が grc 以外", rel, where, "%s（%s）" % (lang, form))
            if pos in ("PPER", "PPERS", "PPERO", "PPERI", "ART") and el.get("lemma"):
                same = letters(el.get("lemma")) == letters(form)
                lemma_style[(pos, "語形と同じ" if same else "語形と違う")] += 1

        elif tag == "gap":
            where = seg_of(el) or "（<s> の外）"
            reason = el.get("reason")
            if reason not in GAP_REASONS:
                rep.add(WARN, "<gap> の reason が lost・illegible・omitted でない", rel, where, str(reason))
            extent = el.get("extent")
            if extent is not None and extent != "unknown":
                rep.add(ERROR, "<gap> の extent に値（字数は quantity に書く）", rel, where, extent)
            q = el.get("quantity")
            if q is not None and not q.isdigit():
                rep.add(ERROR, "<gap> の quantity が整数でない", rel, where, q)
            if q is None and extent is None and el.get("atLeast") is None:
                rep.add(WARN, "<gap> に quantity も extent も無い", rel, where, "reason=%s" % reason)
            if el.get("unit") is None:
                rep.add(WARN, "<gap> に unit が無い", rel, where, "reason=%s" % reason)

        elif tag == "supplied":
            reason = el.get("reason")
            if reason not in SUPPLIED_REASONS:
                rep.add(WARN, "<supplied> の reason が lost・omitted・undefined（・lost-in-source-file）でない", rel,
                        seg_of(el), str(reason))

        elif tag in ("lb", "pb", "cb"):
            where = seg_of(el) or "（<s> の外）"
            in_group = inside(el, "phr") or inside(el, "w")
            if in_group and el.get("break") != "no":
                rep.add(WARN, "語群の中の <%s> に break=\"no\" が無い" % tag, rel, where, "n=%s" % el.get("n"))
            if not in_group and el.get("break") == "no" and parents.get(el) is not None \
                    and local(parents[el].tag) in ("s", "ab"):
                rep.add(WARN, "語群のあいだの <%s> に break=\"no\"" % tag, rel, where, "n=%s" % el.get("n"))

        elif tag == "seg" and el.get("type") in ("orig_group", "norm_group"):
            rep.add(WARN, "<seg type=\"%s\">（語群は <phr>）" % el.get("type"), rel, seg_of(el), "")
        elif tag in ("sourceDoc", "facsimile"):
            rep.add(INFO, "<%s>（この仕様では使わない。画像は iiif/ の設定で扱う）" % tag, rel, "", "")
        elif tag == "date":
            cal = el.get("calendar")
            if cal is not None and not all(c.startswith("#") or "/" in c for c in cal.split()):
                rep.add(ERROR, "@calendar が <calendar> を指すポインタでない", rel, "", cal)
            if el.get("when-custom") is not None and el.get("datingMethod") is None:
                rep.add(ERROR, "@when-custom に @datingMethod が無い", rel, "", el.get("when-custom"))

    # 8. 機能語のレンマの書き方（参考。数だけを集計する）
    for (pos, style), n in lemma_style.items():
        rep.tallies[(pos, style)] += n

    # 構造: <phr> の外の <w>（同じ <s> に <phr> もあるもの）
    mixed = 0
    for s in root.iter(T + "s"):
        has_phr = any(local(c.tag) == "phr" for c in s)
        if has_phr:
            mixed += sum(1 for c in s if local(c.tag) == "w")
    if mixed:
        rep.add(INFO, "語群（<phr>）の外の <w>（同じセグメントに語群もある）", rel, "", "%d 語" % mixed)


def check_lexicon(path, root, rep, site_tags):
    rel = os.path.relpath(path, ROOT)
    for e in root.iter(T + "entry"):
        orth = e.find(".//" + T + "orth")
        pos = e.find(".//" + T + "pos")
        o = (orth.text or "") if orth is not None else ""
        p = (pos.text or "").strip() if pos is not None else ""
        eid = e.get(XID) or o
        if p in TYPOS or (p and p not in CS_TAGS and p not in site_tags and p not in SITE_ONLY):
            rep.add(ERROR, "辞書: 品詞表に無い品詞コード", rel, eid, "%s（%s）" % (p, o))
        if re.search(r"[|*‐\-]", o):
            rep.add(WARN, "辞書: 見出しに記号（| * ‐ -）がある", rel, eid, o)
        if p in FUNCTION_POS and len(letters(o)) > 4:
            rep.add(WARN, "辞書: 機能語の品詞なのに長い見出し（語の切り方の誤りの疑い）", rel, eid, "%s（%s）" % (o, p))


def main():
    ap = argparse.ArgumentParser(description="TEI データの、符号化の仕様（改訂版）への適合を点検する")
    ap.add_argument("files", nargs="*", help="対象（省略時: data/*.xml と source/nhc_fulltext_split/tei/*.xml）")
    ap.add_argument("--tsv", help="見つけたものを 1 件 1 行の TSV に書く")
    ap.add_argument("--examples", type=int, default=3, help="種類ごとに示す例の数（既定 3）")
    a = ap.parse_args()
    files = a.files or (sorted(glob.glob(os.path.join(ROOT, "data", "*.xml")))
                        + sorted(glob.glob(os.path.join(ROOT, "source", "nhc_fulltext_split", "tei", "*.xml"))))
    site_tags = site_pos_names()
    rep = Report(a.examples)
    n_files = 0
    for path in files:
        path = os.path.abspath(path)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            rep.add(ERROR, "XML として読めない", os.path.relpath(path, ROOT), "", str(e))
            continue
        n_files += 1
        if root.find(".//" + T + "entry") is not None and root.find(".//" + T + "s") is None:
            check_lexicon(path, root, rep, site_tags)
        elif root.find(".//" + T + "s") is not None or root.find(".//" + T + "w") is not None:
            check_text_file(path, root, rep, site_tags)

    order = {ERROR: 0, WARN: 1, INFO: 2}
    print("仕様への適合の点検: %d ファイル" % n_files)
    print("  要修正 %d 件・要確認 %d 件・参考 %d 件" % (rep.count(ERROR), rep.count(WARN), rep.count(INFO)))
    for (level, kind), found in sorted(rep.items.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        by_file = Counter(f for f, _, _ in found)
        files_txt = "、".join("%s %d" % (os.path.basename(f), n) for f, n in by_file.most_common(4))
        if len(by_file) > 4:
            files_txt += " ほか %d ファイル" % (len(by_file) - 4)
        print("\n[%s] %s — %d 件（%s）" % (level, kind, len(found), files_txt))
        for f, where, what in found[:rep.examples]:
            print("    %s %s %s" % (os.path.basename(f), where, what))
    if rep.tallies:
        print("\n[%s] 人称代名詞・冠詞のレンマの書き方（全ファイルの合計）" % INFO)
        for pos in sorted({p for p, _ in rep.tallies}):
            same, diff = rep.tallies[(pos, "語形と同じ")], rep.tallies[(pos, "語形と違う")]
            print("    %s: 語形と同じ %d 語、語形と違う %d 語" % (pos, same, diff))
    if a.tsv:
        os.makedirs(os.path.dirname(os.path.abspath(a.tsv)), exist_ok=True)
        with open(a.tsv, "w", encoding="utf-8", newline="\n") as f:
            f.write("level\tkind\tfile\twhere\twhat\n")
            for (level, kind), found in sorted(rep.items.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
                for fpath, where, what in found:
                    f.write("\t".join(x.replace("\t", " ").replace("\n", " ")
                                      for x in (level, kind, fpath, where, what)) + "\n")
        print("\nTSV: %s" % a.tsv)
    return 1 if rep.count(ERROR) else 0


if __name__ == "__main__":
    sys.exit(main())
