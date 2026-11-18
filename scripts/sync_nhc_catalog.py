#!/usr/bin/env python3
"""sync_nhc_catalog.py — source/nhc_fulltext_split/ の文書一覧を data/catalog.xml に反映する。

ナグ・ハマディ写本 全文テキスト（未注釈・56文書）を、検索ページ（search.html）の〈未注釈の本文〉に
出すための項目を作る。data/catalog.xml の

    <!-- BEGIN nhc_fulltext_split … -->  から  <!-- END nhc_fulltext_split -->

までを、いまの source/nhc_fulltext_split/ の内容から作り直す（この範囲は手で編集しない）。
範囲がまだ無いときは、カタログの </listBibl> の直前に入れる。ほかの部分には触れない。

1文書の項目:
    <bibl type="document" subtype="unannotated" xml:id="doc-II-6">
      <title xml:lang="ja|en|fr">…</title>          TEI ヘッダーの題名
      <idno type="siglum">NHC II,6</idno>            証本の @n
      <extent>… segment / token / gap の件数 …</extent>
      <ref type="xml" target="source/nhc_fulltext_split/tei/….xml"/>
    </bibl>

  * subtype="unannotated" の文書は、検索ページでは既定で選択されず、選んだときだけ読み込まれる。
  * xml:id は「doc-」＋証本 ID から「wit-」を除いたもの（証本 wit-II-6 → doc-II-6）。
    検索ページは URL の w=wit-II-6 から、この対応で読み込む文書を決める。
  * 並びは catalog.tsv の順（写本順）。件数は TEI を数えて catalog.tsv と突き合わせ、
    合わなければ書き込まずに止まる。ただし語群（<phr>）を付けた版（source/nhc_fulltext_split/README_ja.md の §10）は
    語の区切りを一部変えてあるので、語数（<w> の数）は catalog.tsv と比べない（本文が元と同じであることは
    source/nhc_fulltext_split/scripts/verify_tei.py が確かめる）。カタログに書く語数は、どの文書も TEI の <w> の数。

使い方:  python3 scripts/sync_nhc_catalog.py            # 差分の有無を表示するだけ(dry-run)
         python3 scripts/sync_nhc_catalog.py --write    # data/catalog.xml に書き込む
"""
import csv, os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "source", "nhc_fulltext_split")
PKG_URL = "source/nhc_fulltext_split"          # サイト上の場所（catalog.xml からの相対ではなく、ページからの相対）
CATALOG = os.path.join(ROOT, "data", "catalog.xml")
TEI = "{http://www.tei-c.org/ns/1.0}"
XML = "{http://www.w3.org/XML/1998/namespace}"
BEGIN = "<!-- BEGIN nhc_fulltext_split"
END = "<!-- END nhc_fulltext_split -->"
INDENT = "      "


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def read_documents():
    """catalog.tsv の順に、各文書の題名・証本・件数を TEI から読む。"""
    with open(os.path.join(PKG, "catalog.tsv"), encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    docs, problems = [], []
    for row in rows:
        name, unit = row["file"], row["unit"]
        path = os.path.join(PKG, "tei", name + ".xml")
        root = ET.parse(path).getroot()
        titles = {}
        for t in root.find(f"{TEI}teiHeader/{TEI}fileDesc/{TEI}titleStmt").findall(f"{TEI}title"):
            if not t.get("type"):
                titles[t.get(XML + "lang")] = (t.text or "").strip()
        wits = [t for t in root.iter(TEI + "text") if t.get("type") == "witness"]
        if len(wits) != 1:
            problems.append(f"{unit}: 証本が {len(wits)} 個あります（1個のはず）")
            continue
        wit = wits[0]
        wid, siglum = wit.get(XML + "id") or "", wit.get("n") or ""
        expected = "wit-" + unit.replace(",", "-")
        if wid != expected:
            problems.append(f"{unit}: 証本 ID が {wid!r} です（{expected!r} のはず）")
        if siglum != "NHC " + unit:
            problems.append(f"{unit}: 証本の @n が {siglum!r} です（'NHC {unit}' のはず）")
        n = {"segment": sum(1 for _ in wit.iter(TEI + "s")), "token": sum(1 for _ in wit.iter(TEI + "w")),
             "gap": sum(1 for _ in wit.iter(TEI + "gap"))}
        grouped = wit.find(f".//{TEI}phr") is not None      # 語群を付けた版（語の区切りを一部変えてある）
        for unit_name, col in (("segment", "rows"), ("token", "tokens"), ("gap", "gap_markers")):
            if unit_name == "token" and grouped:
                continue
            if n[unit_name] != int(row[col]):
                problems.append(f"{unit}: {unit_name} が TEI で {n[unit_name]}、catalog.tsv で {row[col]}")
        for lang in ("ja", "en", "fr"):
            if not titles.get(lang):
                problems.append(f"{unit}: 題名（{lang}）がありません")
        docs.append({"key": wid[len("wit-"):], "siglum": siglum, "titles": titles, "n": n, "grouped": grouped,
                     "target": f"{PKG_URL}/tei/{name}.xml"})
    keys = [d["key"] for d in docs]
    if len(set(keys)) != len(keys):
        problems.append("文書のキーが重複しています")
    return docs, problems


def build_block(docs):
    total = {u: sum(d["n"][u] for d in docs) for u in ("segment", "token", "gap")}
    out = [
        # XML のコメントには「--」を書けないので、ここに実行オプションは書かない（使い方はこのスクリプトの冒頭）
        f"{BEGIN} — 自動生成: scripts/sync_nhc_catalog.py が書き出す範囲（END までは手で編集しない）",
        f"{INDENT}     ナグ・ハマディ写本 全文テキスト（未注釈）: {len(docs)} 文書・{total['segment']:,} セグメント・{total['token']:,} 語。",
        f"{INDENT}     品詞・レンマ・訳は付いておらず、校訂本との照合も済んでいない作業用の本文（{PKG_URL}/README_ja.md）。",
    ]
    grouped = [d for d in docs if d["grouped"]]
    if grouped:
        out.append(f"{INDENT}     うち {len(grouped)} 文書は、語群（<phr>）を推定で付けた暫定版（どの文書かは同 README_ja.md の §10）。")
    out += [
        f"{INDENT}     subtype=\"unannotated\" の文書は、検索ページでは既定で選択されず、選んだときだけ読み込まれる。",
        f"{INDENT}     本文を表示するビュワーはまだ無いので <ref type=\"reader\"> は付けていない。 -->",
    ]
    for d in docs:
        out.append(f'{INDENT}<bibl type="document" subtype="unannotated" xml:id="doc-{d["key"]}">')
        for lang in ("ja", "en", "fr"):
            out.append(f'{INDENT}  <title xml:lang="{lang}">{esc(d["titles"][lang])}</title>')
        out.append(f'{INDENT}  <idno type="siglum">{esc(d["siglum"])}</idno>')
        out.append(f'{INDENT}  <extent><measure unit="segment" quantity="{d["n"]["segment"]}"/>'
                   f'<measure unit="token" quantity="{d["n"]["token"]}"/>'
                   f'<measure unit="gap" quantity="{d["n"]["gap"]}"/></extent>')
        out.append(f'{INDENT}  <ref type="xml" target="{esc(d["target"])}"/>')
        out.append(f"{INDENT}</bibl>")
    out.append(f"{INDENT}{END}")
    return "\n".join(out)


def main():
    write = "--write" in sys.argv
    docs, problems = read_documents()
    if problems:
        print("!! 中止: source/nhc_fulltext_split/ の内容が想定と合いません")
        for p in problems:
            print("   -", p)
        return 1
    block = build_block(docs)
    with open(CATALOG, encoding="utf-8", newline="") as f:
        old = f.read()
    start, end = old.find(BEGIN), old.find(END)
    if (start < 0) != (end < 0) or end < start:
        print("!! 中止: data/catalog.xml の BEGIN / END の印が対になっていません")
        return 1
    if start >= 0:
        new = old[:start] + block + old[end + len(END):]
    else:
        close = old.rfind("    </listBibl>")
        if close < 0:
            print("!! 中止: data/catalog.xml に </listBibl> が見つかりません")
            return 1
        new = old[:close] + INDENT + block + "\n\n" + old[close:]
    ET.fromstring(new.encode("utf-8"))                     # 整形式であることを確かめる
    ids = re.findall(r'xml:id="([^"]+)"', new)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        print("!! 中止: xml:id が重複します:", ", ".join(dup))
        return 1
    total = sum(d["n"]["token"] for d in docs)
    print(f"{len(docs)} 文書・{total:,} 語（{docs[0]['siglum']} 〜 {docs[-1]['siglum']}）")
    if new == old:
        print("data/catalog.xml は最新です（変更なし）")
        return 0
    if not write:
        print("data/catalog.xml に差分があります。書き込むには --write を付けて実行してください")
        return 0
    with open(CATALOG, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    print("data/catalog.xml を更新しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
