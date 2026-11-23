#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_fulltext_stats.py — 全文テキストの文書ごとの数値を data/fulltext_stats.json に書き出す

コーパス検索・統計（search.html）の〈統計〉の「写本全体の比較」が読む。全文テキスト（source/nhc_fulltext_split/tei/ の
56 文書）は合わせて約 28 MB あり、ブラウザーで全部を読み込まないと文書どうしを比べられないので、ここで前もって数えておく。

  python3 scripts/build_fulltext_stats.py           data/fulltext_stats.json を書き出す
  python3 scripts/build_fulltext_stats.py --check   書き出すものとファイルが同じかを調べるだけ（違えば終了コード 1）

scripts/build_site.py を実行したときにも一緒に書き出す（build_site.py --check も、このファイルが最新かを調べる）。
文書の一覧と順は data/catalog.xml の <bibl type="document">（subtype が draft＝暫定版・unannotated＝未注釈）。
参考として、人の手で注釈した版（エウグノストス III,3 と『国家』VI,5）も同じ方法で数える（reference）。

数えるもの（本文の <text type="witness"> の中。人の手で注釈した版は、エウグノストスの写本 III,3（wit-III）と『国家』）:
  w        <w> の数（暫定版と人の手で注釈した版では形態素、未注釈の文書では元ファイルの語）
  phr      <phr>（語群）の数（未注釈の文書は 0）
  wg       <phr> の中にある <w> の数（w と同じなら、本文全体が語群に分けてある。人の手で注釈したエウグノストスは冒頭だけ）
  s        <s>（セグメント）の数
  gap      <gap>（欠損）の数
  grc      xml:lang="grc"（ギリシア語からの借用語）の付いた <w> の数。借用語はこの属性だけで数える
  typed    @type（品詞）の付いた <w> の数
  pos      品詞ごとの <w> の数（@type の値 → 数）
  low      @cert="low" の <w> の数（自動注釈の確度）
  X        品詞が X（未判定）の <w> の数
  dialect  方言（TEI の <textLang> か <language> から: sahidic・lycopolitan）
割合はページで計算する（ここでは数だけを書く）。暫定版の品詞・確度・借用語の印は自動注釈によるもので、人の目で確かめていない。
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
XLANG = "{http://www.w3.org/XML/1998/namespace}lang"
OUT = os.path.join("data", "fulltext_stats.json")

# 参考: 人の手で注釈した版（カタログの文書の id、本文の中の証本の id、略号、ビュワー）
REFERENCE = [
    ("eugnostos", "wit-III", "NHC III,3", "eugnostos.html?wit=III"),
    ("republic", "wit-rep", "NHC VI,5", "republic.html"),
]


def dialect_of(root):
    """<textLang>（全文テキスト）か <language ident="cop">（人の手で注釈した版）の文言から"""
    texts = [e.text or "" for e in root.iter(T + "textLang")] + \
            [e.text or "" for e in root.iter(T + "language") if e.get("ident") == "cop"]
    for t in texts:
        low = t.lower()
        if "lycopolitan" in low or "subachmimic" in low:
            return "lycopolitan"
        if "sahidic" in low:
            return "sahidic"
    return ""


def count(text_el):
    c = {"w": 0, "phr": 0, "wg": 0, "s": 0, "gap": 0, "grc": 0, "typed": 0, "low": 0, "X": 0, "pos": {}}
    for phr in text_el.iter(T + "phr"):
        c["wg"] += sum(1 for _ in phr.iter(T + "w"))
    for el in text_el.iter():
        tag = el.tag
        if tag == T + "w":
            c["w"] += 1
            if el.get(XLANG) == "grc":
                c["grc"] += 1
            t = el.get("type")
            if t:
                c["typed"] += 1
                c["pos"][t] = c["pos"].get(t, 0) + 1
                if t == "X":
                    c["X"] += 1
            if el.get("cert") == "low":
                c["low"] += 1
        elif tag == T + "phr":
            c["phr"] += 1
        elif tag == T + "s":
            c["s"] += 1
        elif tag == T + "gap":
            c["gap"] += 1
    c["pos"] = dict(sorted(c["pos"].items(), key=lambda kv: (-kv[1], kv[0])))
    return c


def catalog():
    out = []
    for b in ET.parse(os.path.join(ROOT, "data", "catalog.xml")).getroot().iter(T + "bibl"):
        if b.get("type") != "document":
            continue
        refs = {r.get("type"): r.get("target") for r in b.findall(T + "ref")}
        title = {t.get(XLANG): (t.text or "").strip() for t in b.findall(T + "title") if t.get(XLANG) in ("ja", "en", "fr")}
        sig = next((i.text.strip() for i in b.findall(T + "idno") if i.get("type") == "siglum" and i.text), "")
        out.append({"id": (b.get(XID) or "")[4:], "subtype": b.get("subtype") or "", "siglum": sig, "title": title,
                    "xml": refs.get("xml") or "", "reader": refs.get("reader") or ""})
    return out


def witness(root, wid=None):
    for t in root.iter(T + "text"):
        if t.get("type") == "witness" and (wid is None or t.get(XID) == wid):
            return t
    raise SystemExit("build_fulltext_stats.py: 証本 %s が見つかりません" % (wid or '<text type="witness">'))


def build():
    docs, refs = [], []
    cat = catalog()
    for d in cat:
        if d["subtype"] not in ("draft", "unannotated") or not d["xml"]:
            continue
        root = ET.parse(os.path.join(ROOT, d["xml"])).getroot()
        row = {"key": d["id"], "siglum": d["siglum"], "title": d["title"],
               "status": "draft" if d["subtype"] == "draft" else "text", "dialect": dialect_of(root),
               "reader": d["reader"], "xml": d["xml"]}
        row.update(count(witness(root)))
        docs.append(row)
    by_id = {d["id"]: d for d in cat}
    for key, wid, sig, viewer in REFERENCE:
        d = by_id.get(key)
        if not d or not d["xml"]:
            raise SystemExit("build_fulltext_stats.py: カタログに doc-%s が見つかりません" % key)
        root = ET.parse(os.path.join(ROOT, d["xml"])).getroot()
        row = {"key": key, "siglum": sig, "title": d["title"], "status": "hand", "dialect": dialect_of(root),
               "reader": viewer, "xml": d["xml"]}
        row.update(count(witness(root, wid)))
        refs.append(row)
    comment = ("自動生成ファイル: scripts/build_fulltext_stats.py が出力します（scripts/build_site.py からも。直接編集しない）。"
               "全文テキストの文書ごとの数（docs、data/catalog.xml の順）と、参考に人の手で注釈した版（reference）。"
               "w=<w>、phr=<phr>、wg=<phr> の中の <w>、s=<s>、gap=<gap>、grc=xml:lang=\"grc\" の <w>、typed=@type のある <w>、pos=品詞ごとの <w>、"
               "low=@cert=\"low\" の <w>、X=品詞 X の <w>。暫定版の品詞・確度・借用語の印は自動注釈によるもので、人の目で確かめていない。")
    row = lambda r: json.dumps(r, ensure_ascii=False, sort_keys=False)
    return ('{\n  "_comment": ' + json.dumps(comment, ensure_ascii=False) + ',\n  "docs": [\n    ' +
            ",\n    ".join(row(r) for r in docs) + '\n  ],\n  "reference": [\n    ' +
            ",\n    ".join(row(r) for r in refs) + '\n  ]\n}\n')


def main():
    text = build()
    path = os.path.join(ROOT, OUT)
    if "--check" in sys.argv[1:]:
        try:
            with open(path, encoding="utf-8") as f:
                same = f.read() == text
        except OSError:
            same = False
        print("%s は最新です" % OUT if same else "%s が古くなっています（python3 scripts/build_fulltext_stats.py）" % OUT)
        return 0 if same else 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    n = json.loads(text)
    print("wrote %s (%d documents, %d reference texts)" % (OUT, len(n["docs"]), len(n["reference"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
