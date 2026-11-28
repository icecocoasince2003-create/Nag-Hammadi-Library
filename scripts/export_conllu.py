#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_conllu.py — Sheneset の注釈を CoNLL-U の形で書き出す（GitHub のリリースに添えるため。書き出したものはリポジトリに入れない）

書き出すのは Sheneset 自身の層だけ（CoNLL-U の 10 列のうち）:
  FORM    <w> の文字（中の <supplied> の文字も含む。空白は除く）
  LEMMA   <w> の @lemma（無ければ _）
  XPOS    <w> の @type（Sheneset の品詞。名前は data/pos_labels.json。無ければ _）
  MISC    seg_id=その語のセグメント（<s>）の xml:id
  UPOS・FEATS・HEAD・DEPREL・DEPS はすべて _（品詞を UD の品詞に置き換えず、文法関係・依存関係の層は作らない）。
語群（<phr>）のうち <w> が 2 つ以上のものは、CoNLL-U の multiword token（ID が「1-3」の行。FORM は語群の綴り）として書く。
1 文 = 1 セグメント（<s>）。「# sent_id = 文書:seg_id」「# text = 語群と語を空白でつないだもの」を付ける。語の無いセグメント
（欠損だけのものなど）は書かない。欠損（<gap>）・頁と行（<pb>・<lb>）・語釈・訳・確度は書かない。

文書（data/catalog.xml）: 人の手で注釈した版（エウグノストス III,3 の証本 wit-III、『国家』の wit-rep。scripts/build_fulltext_stats.py の
REFERENCE）と、暫定版（subtype="draft"。自動注釈で、人の目で確かめていない）。未注釈の文書（unannotated）はレンマと品詞が無いので
書かない。文書ごとに 1 ファイル（文書の id.conllu）で、初めに版・ライセンスの注記と「# newdoc id」「# sheneset_status」
（hand = 人の手、draft = 自動注釈・未確認）「# source」（TEI ファイルと証本）「# title」を付ける。同じデータからは、いつも同じ
バイト列ができる（zip の中のファイルの日時は data/release.json のリリースの日）。

使い方（リポジトリのルートで）:
  python3 scripts/export_conllu.py              build/conllu/ に文書ごとの .conllu を書き、数を表示する
  python3 scripts/export_conllu.py --zip        さらに build/sheneset-v<版>-conllu.zip にまとめる（リリースに添えるもの）
  python3 scripts/export_conllu.py --out 場所   書き出す場所を変える（--zip の zip はその親のフォルダに書く）
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_fulltext_stats as stats  # noqa: E402  文書の一覧（catalog）・証本（witness）・人の手の版（REFERENCE）を同じに読む

T = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
OUT = os.path.join(ROOT, "build", "conllu")
EMPTY = "_"


def shown(path):
    """表示用のパス（いまのフォルダの中なら相対パス）"""
    rel = os.path.relpath(path)
    return path if rel.startswith("..") else rel


def form(w):
    return "".join("".join(w.itertext()).split()) or EMPTY


def field(v):
    """CoNLL-U の 1 つの欄（タブと改行は入れない。空なら _）"""
    v = " ".join((v or "").split())
    return v or EMPTY


def units(s):
    """<s> の中を、語群（<phr> の中の <w> の並び）と、語群の外の <w> 1 つずつの並びにする（文書の順）"""
    out = []

    def walk(el):
        for c in el:
            if c.tag == T + "phr":
                ws = list(c.iter(T + "w"))
                if ws:
                    out.append(ws)
            elif c.tag == T + "w":
                out.append([c])
            else:
                walk(c)
    walk(s)
    return out


def sentence(doc, s, n):
    """1 つのセグメントの行（終わりの空行を含む）と数。語が無ければ None"""
    us = units(s)
    if not us:
        return None
    sid = s.get(XID) or "s%d" % n
    lines = ["# sent_id = %s:%s" % (doc, sid),
             "# text = " + " ".join("".join(form(w) for w in u) for u in us)]
    i = 0
    mwt = 0
    for u in us:
        if len(u) > 1:
            lines.append("%d-%d\t%s\t_\t_\t_\t_\t_\t_\t_\t_" % (i + 1, i + len(u), "".join(form(w) for w in u)))
            mwt += 1
        for w in u:
            i += 1
            lines.append("\t".join([str(i), form(w), field(w.get("lemma")), EMPTY, field(w.get("type")),
                                    EMPTY, EMPTY, EMPTY, EMPTY, "seg_id=" + sid]))
    lines.append("")
    return lines, {"tokens": len(us), "words": i, "mwt": mwt}


def documents():
    """(id, 状態, TEI のパス, 証本の id, 題) — 人の手の版、そのあと暫定版（カタログの順）"""
    cat = stats.catalog()
    by_id = {d["id"]: d for d in cat}
    out = []
    for key, wid, _sig, _viewer in stats.REFERENCE:
        d = by_id[key]
        out.append((key, "hand", d["xml"], wid, d["title"].get("en") or key))
    for d in cat:
        if d["subtype"] == "draft" and d["xml"]:
            out.append((d["id"], "draft", d["xml"], None, d["title"].get("en") or d["id"]))
    return out


def header(release):
    doi = release.get("doi_all_versions") or release.get("doi") or ""
    return [
        "# Sheneset %s, %s%s. CC BY 4.0. Exported by scripts/export_conllu.py." % (
            release.get("version", "?"), release.get("url", ""), ", DOI %s (all versions)" % doi if doi else ""),
        "# Only Sheneset's own layers: FORM, LEMMA, XPOS (Sheneset part-of-speech tags) and MISC seg_id."
        " UPOS, FEATS, HEAD, DEPREL and DEPS are not annotated (_).",
        "# Bound groups (<phr>) of two or more morphemes are multiword tokens. Texts with sheneset_status = draft"
        " are automatic annotation, not checked by hand.",
    ]


def export(out_dir):
    with open(os.path.join(ROOT, "data", "release.json"), encoding="utf-8") as f:
        release = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    written, totals = [], {"docs": 0, "sents": 0, "tokens": 0, "words": 0, "mwt": 0, "skipped": 0}
    for key, status, xml, wid, title in documents():
        root = ET.parse(os.path.join(ROOT, xml)).getroot()
        text = stats.witness(root, wid)
        lines = header(release) + ["# newdoc id = " + key, "# sheneset_status = " + status,
                                   "# source = %s#%s" % (xml, text.get(XID) or ""), "# title = " + field(title)]
        c = {"sents": 0, "tokens": 0, "words": 0, "mwt": 0, "skipped": 0}
        for n, s in enumerate(text.iter(T + "s"), 1):
            got = sentence(key, s, n)
            if got is None:
                c["skipped"] += 1
                continue
            lines += got[0]
            c["sents"] += 1
            for k in ("tokens", "words", "mwt"):
                c[k] += got[1][k]
        name = key + ".conllu"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        written.append(name)
        totals["docs"] += 1
        for k in c:
            totals[k] += c[k]
        print("  %-10s %-5s 文 %5d・語群と語 %6d・形態素 %6d（語群 %5d）%s" % (
            key, status, c["sents"], c["tokens"], c["words"], c["mwt"], "・語の無いセグメント %d" % c["skipped"] if c["skipped"] else ""))
    print("%d 文書: 文 %d・語群と語 %d・形態素 %d → %s" % (
        totals["docs"], totals["sents"], totals["tokens"], totals["words"], shown(out_dir)))
    return written, release


def make_zip(out_dir, names, release):
    """書き出したファイルを 1 つの zip に（中の日時はリリースの日。同じ内容なら同じバイト列）"""
    version = release.get("version", "0")
    y, m, d = (int(x) for x in (release.get("date") or "1980-01-01").split("-"))
    folder = "sheneset-v%s-conllu" % version
    path = os.path.join(os.path.dirname(os.path.abspath(out_dir)), folder + ".zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):
            info = zipfile.ZipInfo(folder + "/" + name, date_time=(y, m, d, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(out_dir, name), "rb") as f:
                z.writestr(info, f.read())
    print("→ %s（%d ファイル）" % (shown(path), len(names)))
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sheneset の注釈を CoNLL-U で書き出す")
    ap.add_argument("--out", default=OUT, help="書き出す場所（既定: build/conllu/）")
    ap.add_argument("--zip", action="store_true", help="書き出したファイルを、その親のフォルダの sheneset-v<版>-conllu.zip にまとめる")
    a = ap.parse_args(argv)
    names, release = export(a.out)
    if a.zip:
        make_zip(a.out, names, release)
    return 0


if __name__ == "__main__":
    sys.exit(main())
