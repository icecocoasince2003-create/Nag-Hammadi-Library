#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_theology_ana.py
====================
eugnostos_theology.xml の各 <note type="theology"> が持つテーマ分類(@ana)を、
その note が @target で指す本文セグメント <s> の @ana へ同期する。

「対応」の定義:
  本文 <s xml:id="X"> の @ana == （X を target に含む全 theology note の @ana の和集合）
  並び順はアルファベット順・各トークンに "#" を前置（既存ファイルの規約に一致）。

設計上の安全策:
  - 既に正しい @ana を持つ <s> は一切変更しない（バイト不変／差分を最小化）。
  - 不足している <s> にのみ @ana を補完・拡張する（追加方向のみ）。
  - ElementTree で全体を再シリアライズせず、開始タグ単位の文字列置換で行う
    （名前空間プレフィックス・コメント・属性順・空白を保持）。

使い方:
  cd source && python3 sync_theology_ana.py            # data/ を更新（リポジトリ直下基準）
  python3 sync_theology_ana.py --tei PATH --theo PATH  # パス明示
  python3 sync_theology_ana.py --check                 # 変更せず差分のみ報告
"""
import argparse, re, sys, os
import xml.etree.ElementTree as ET

TEI = "{http://www.tei-c.org/ns/1.0}"


def expected_ana(theo_path):
    """segid -> '#th-a #th-b ...'（アルファベット順）を返す。"""
    root = ET.parse(theo_path).getroot()
    acc = {}
    for n in root.iter(TEI + "note"):
        if n.get("type") != "theology":
            continue
        themes = [a.lstrip("#") for a in (n.get("ana") or "").split()]
        for tok in (n.get("target") or "").split():
            seg = tok.split("#", 1)[1] if "#" in tok else tok
            acc.setdefault(seg, set()).update(themes)
    return {seg: " ".join("#" + t for t in sorted(ts)) for seg, ts in acc.items()}


def start_tag_span(text, segid):
    """xml:id=segid を持つ <s ...> 開始タグの (開始, 終了) インデックスを返す。"""
    m = re.search(r'<s\b[^>]*\bxml:id="%s"[^>]*?/?>' % re.escape(segid), text)
    if not m:
        raise KeyError("segment %s not found in TEI" % segid)
    return m.start(), m.end()


def set_ana_in_tag(tag, value):
    """開始タグ文字列に @ana=value を設定（既存なら置換、無ければ閉じ括弧直前に挿入）。"""
    if re.search(r'\bana="[^"]*"', tag):
        return re.sub(r'\bana="[^"]*"', 'ana="%s"' % value, tag, count=1), "replace"
    # 閉じ括弧（> または />）の直前に挿入
    m = re.search(r'\s*/?>\s*$', tag)
    insert_at = m.start()
    return tag[:insert_at] + ' ana="%s"' % value + tag[insert_at:], "insert"


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    ap.add_argument("--tei", default=os.path.join(repo, "data", "eugnostos_tei.xml"))
    ap.add_argument("--theo", default=os.path.join(repo, "data", "eugnostos_theology.xml"))
    ap.add_argument("--check", action="store_true", help="変更せず差分のみ報告")
    args = ap.parse_args()

    want = expected_ana(args.theo)
    text = open(args.tei, encoding="utf-8").read()

    inserts = replaces = skips = 0
    changed = []
    for segid, value in want.items():
        s, e = start_tag_span(text, segid)
        tag = text[s:e]
        cur = re.search(r'\bana="([^"]*)"', tag)
        cur_val = cur.group(1) if cur else ""
        if cur_val == value:
            skips += 1
            continue
        new_tag, action = set_ana_in_tag(tag, value)
        if args.check:
            changed.append((segid, cur_val, value, action))
        else:
            text = text[:s] + new_tag + text[e:]
            changed.append((segid, cur_val, value, action))
        if action == "insert":
            inserts += 1
        else:
            replaces += 1

    # 整形式チェック
    try:
        ET.fromstring(text)
    except ET.ParseError as ex:
        sys.exit("ERROR: 生成結果が整形式でない: %s" % ex)

    if not args.check:
        with open(args.tei, "w", encoding="utf-8") as f:
            f.write(text)

    print("対象 <s>: %d / 一致(無変更): %d / 補完(挿入): %d / 拡張(置換): %d"
          % (len(want), skips, inserts, replaces))
    for segid, old, new, act in changed:
        print("  [%s] %-14s  '%s' -> '%s'" % (act, segid, old, new))
    print("(check モード・変更なし)" if args.check else "更新を書き込みました: %s" % args.tei)


if __name__ == "__main__":
    main()
