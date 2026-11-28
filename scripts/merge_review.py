#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_review.py — 確認作業の画面（review.html）で何人かが書き出したファイルを、1 つにまとめる

確認の作業を分担したとき、それぞれが書き出したファイル（同じキューのもの）を、元のファイル（リポジトリにあるもの）に
まとめて当てる。どの人が何を書き換えたかは、元のファイルとの違いで見る（書き換えたのは、キューの定義
data/review_queues.json で書き込める列・欄だけ。ほかが変わっていれば止める）。

  * 違う行（項目）を書き換えたものは、そのまま合わせる。同じ行でも違う列なら合わせる
  * 同じ行の同じ列を、違う値に書き換えたものは「食い違い」。一覧を出して止め、何も書き込まない
    （確認者の列は食い違いにしない。両方の名前を「・」でつなぐ）
  * 書き出しの形は review.html と同じ（TSV は列の順・改行・BOM を元のまま、足す列は末尾。JSON は字下げ 2）。
    どのファイルも元と同じなら、元とバイト単位で同じものができる

使い方（リポジトリのルートで）:
  python3 scripts/merge_review.py キュー 書き出したファイル…                 まとめた結果を確かめるだけ（書き込まない）
  python3 scripts/merge_review.py キュー 書き出したファイル… --out まとめ.tsv  別のファイルに書く
  python3 scripts/merge_review.py キュー 書き出したファイル… --write          元のファイル（キューの file）を書き換える
  キュー: data/review_queues.json の id（intros・sample・thomas・breaks など）
  --base ファイル: 元のファイルを、キューの file の代わりに使う（試すとき）

終了コード: 0 = まとまった（食い違いなし）、1 = 食い違いか問題がある（何も書き込んでいない）。
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUES = os.path.join(ROOT, "data", "review_queues.json")
SEP = "\x01"
JOIN = "・"     # 確認者の名前をつなぐ記号


# ---- TSV（assets/review-core.js と同じ約束）----
def parse_tsv(text):
    bom = text.startswith("﻿")
    if bom:
        text = text[1:]
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    final = False
    if len(lines) > 1 and lines[-1] == "":
        final = True
        lines.pop()
    if not lines or not lines[0]:
        raise ValueError("TSV: 見出しの行がありません")
    return {"bom": bom, "eol": eol, "final": final, "header": lines[0].split("\t"), "rows": [l.split("\t") for l in lines[1:]]}


def serialize_tsv(t):
    return ("﻿" if t["bom"] else "") + t["eol"].join("\t".join(r) for r in [t["header"]] + t["rows"]) + (t["eol"] if t["final"] else "")


def blank(row):
    return len(row) == 1 and row[0] == ""


def cell(t, row, col):
    try:
        i = t["header"].index(col)
    except ValueError:
        return ""
    return row[i] if i < len(row) else ""


def index_rows(t, key):
    out = {}
    for i, r in enumerate(t["rows"]):
        if blank(r):
            continue
        k = SEP.join(cell(t, r, c) for c in key)
        if k in out:
            raise ValueError("同じキーの行が 2 つあります: " + k.replace(SEP, " / "))
        out[k] = i
    return out


def clean(v):
    """セルの中のタブと改行の並びを空白 1 つに（review-core.js の cleanCell と同じ）"""
    return re.sub(r"[\t\r\n]+", " ", "" if v is None else str(v))


def apply_edits(t, edits, key, append_order):
    out = {"bom": t["bom"], "eol": t["eol"], "final": t["final"], "header": list(t["header"]), "rows": [list(r) for r in t["rows"]]}
    idx = index_rows(out, key)
    used = {c for e in edits.values() for c in e}
    extra = [c for c in append_order if c in used] + sorted(c for c in used if c not in append_order)
    extra = [c for c in extra if c not in out["header"]]
    out["header"] += extra
    for k, e in edits.items():
        row = out["rows"][idx[k]]
        for c, v in e.items():
            j = out["header"].index(c)
            while len(row) <= j:
                row.append("")
            row[j] = clean(v)
    if extra:
        for r in out["rows"]:
            if not blank(r):
                r += [""] * (len(out["header"]) - len(r))
    return out


def diff_tsv(base, other, key, editable):
    """(edits, 問題)。edits: {行のキー: {列: 値}}"""
    problems, edits = [], {}
    bi, oi = index_rows(base, key), index_rows(other, key)
    show = lambda k: k.replace(SEP, " / ")
    problems += ["元にある行がありません: " + show(k) for k in bi if k not in oi]
    problems += ["元に無い行があります: " + show(k) for k in oi if k not in bi]
    lost = [c for c in base["header"] if c not in other["header"]]
    if lost:
        problems.append("元にある列がありません: " + ", ".join(lost))
    locked = set()
    for k, j in oi.items():
        if k not in bi:
            continue
        brow, orow = base["rows"][bi[k]], other["rows"][j]
        for ci, c in enumerate(other["header"]):
            bv, ov = cell(base, brow, c), (orow[ci] if ci < len(orow) else "")
            if bv == ov:
                continue
            if c in editable:
                edits.setdefault(k, {})[c] = ov
            else:
                locked.add(c)
    if locked:
        problems.append("書き換えてはいけない列が変わっています: " + ", ".join(sorted(locked)))
    return edits, problems


# ---- JSON（解題）----
def get_path(o, p):
    for k in p.split("."):
        if not isinstance(o, dict) or k not in o:
            return None
        o = o[k]
    return o


def set_path(o, p, v):
    ks = p.split(".")
    for k in ks[:-1]:
        if not isinstance(o.get(k), dict):
            o[k] = {}
        o = o[k]
    o[ks[-1]] = v


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def intro_paths(q):
    return ["%s.%s" % (f, l) for f in q["fields"] for l in q["langs"]] + ["todo", "reviewed", q["reviewer"]]


def strip(item, paths):
    c = json.loads(json.dumps(item))
    for p in paths:
        set_path(c, p, None)
    return c


def diff_json(base, other, paths):
    problems, edits = [], {}
    a, b = base.get("texts", {}), other.get("texts", {})
    problems += ["元にある項目がありません: " + k for k in a if k not in b]
    problems += ["元に無い項目があります: " + k for k in b if k not in a]
    problems += ["texts の外が変わっています: " + k for k in base if k != "texts" and canon(base[k]) != canon(other.get(k))]
    for k in a:
        if k not in b:
            continue
        for p in paths:
            x, y = get_path(a[k], p), get_path(b[k], p)
            if y is not None and canon(x) != canon(y):
                edits.setdefault(k, {})[p] = y
        if canon(strip(a[k], paths)) != canon(strip(b[k], paths)):
            problems.append("書き換えてはいけない欄が変わっています: " + k)
    return edits, problems


# ---- まとめる ----
def combine(per_file, reviewer):
    """per_file: [(名前, edits)]。(まとめた edits, 食い違い)。"""
    merged, origin, conflicts = {}, {}, []
    for name, edits in per_file:
        for k, e in edits.items():
            for c, v in e.items():
                if c == reviewer:
                    continue
                if k in merged and c in merged[k] and canon(merged[k][c]) != canon(v):
                    conflicts.append((k, c, origin[(k, c)], merged[k][c], name, v))
                    continue
                merged.setdefault(k, {})[c] = v
                origin[(k, c)] = name
    for name, edits in per_file:            # 確認者: 書き換えのある行に、書き換えた人の名前をつなぐ
        for k, e in edits.items():
            if reviewer in e and k in merged:
                names = [n for n in str(merged[k].get(reviewer, "")).split(JOIN) if n]
                for n in str(e[reviewer]).split(JOIN):
                    if n and n not in names:
                        names.append(n)
                merged[k][reviewer] = JOIN.join(names)
    return merged, conflicts


def main(argv=None):
    ap = argparse.ArgumentParser(description="確認作業の画面で書き出したファイルをまとめる")
    ap.add_argument("queue", help="キューの id（data/review_queues.json）")
    ap.add_argument("files", nargs="+", help="書き出したファイル")
    ap.add_argument("--base", help="元のファイル（省略時はキューの file）")
    ap.add_argument("--out", help="まとめた結果を書くファイル")
    ap.add_argument("--write", action="store_true", help="元のファイル（キューの file）を書き換える")
    ap.add_argument("--queues", default=QUEUES, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    with open(args.queues, encoding="utf-8") as f:
        conf = json.load(f)
    q = next((x for x in conf["queues"] if x["id"] == args.queue), None)
    if q is None:
        print("キュー「%s」は %s にありません（%s）" % (args.queue, os.path.relpath(args.queues, ROOT),
                                                  "・".join(x["id"] for x in conf["queues"])))
        return 1
    base_path = args.base or os.path.join(ROOT, q["file"])
    with open(base_path, encoding="utf-8", newline="") as f:
        base_text = f.read()
    problems, per_file = [], []
    if q["kind"] == "intros":
        base = json.loads(base_text)
        if json.dumps(base, ensure_ascii=False, indent=2) + "\n" != base_text:
            problems.append("%s は字下げ 2 の形ではありません（まとめると形が変わる）" % base_path)
        paths = intro_paths(q)
    else:
        base = parse_tsv(base_text)
        editable = [f["column"] for f in q.get("fields", [])] + [c for c in (q.get("status"), q.get("corrected"), q["reviewer"]) if c]
    for p in args.files:
        name = os.path.basename(p)
        try:
            with open(p, encoding="utf-8", newline="") as f:
                text = f.read()
            if q["kind"] == "intros":
                edits, pr = diff_json(base, json.loads(text), paths)
            else:
                edits, pr = diff_tsv(base, parse_tsv(text), q["key"], editable)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            edits, pr = {}, ["読めません: %s" % e]
        problems += ["%s: %s" % (name, x) for x in pr]
        per_file.append((name, edits))
        print("%s: 書き換え %d 項目" % (name, len(edits)))
    merged, conflicts = combine(per_file, q["reviewer"])
    if conflicts:
        print("\n食い違い（%d 件）。同じ項目の同じ列を、違う値に書き換えています:" % len(conflicts))
        for k, c, n1, v1, n2, v2 in conflicts:
            print("  ! %s ／ %s: %s は「%s」、%s は「%s」" % (k.replace(SEP, " / "), c, n1, v1, n2, v2))
    if problems:
        print("\n問題（%d 件）:" % len(problems))
        for x in problems:
            print("  ! " + x)
    if conflicts or problems:
        print("\n何も書き込んでいません。")
        return 1
    if q["kind"] == "intros":
        obj = json.loads(json.dumps(base))
        for k, e in merged.items():
            for p, v in e.items():
                set_path(obj["texts"][k], p, v)
        out_text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    else:
        out_text = serialize_tsv(apply_edits(base, merged, q["key"], [c for c in (q.get("corrected"), q["reviewer"]) if c]))
    print("\nまとめた結果: 書き換え %d 項目（%s）" % (len(merged), "元と同じ" if out_text == base_text else "元と違う"))
    target = os.path.join(ROOT, q["file"]) if args.write else args.out
    if target:
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(out_text)
        print("→ %s に書き込みました" % (os.path.relpath(target, ROOT) if os.path.abspath(target).startswith(ROOT) else target))
    else:
        print("（書き込んでいません。--out ファイル か --write を付けると書き込みます）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
