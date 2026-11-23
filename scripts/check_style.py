#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_style.py — 表記ゆれの点検（使わない表記が残っていないかを調べる）

規則は scripts/style_rules.json の rules にあります。1 つの規則は
    {"bad": "使わない表記", "good": "使う表記", "note": "説明（任意）"}
で、bad を文字列としてそのまま探します（正規表現ではありません。大文字と小文字も区別します）。
点検するのは、リポジトリの HTML・JS（.js・.cjs）・Python・JSON です（規則のファイル自身と、
.git などの「.」で始まるフォルダ、build/・design/ は除きます）。規則の足し方は CONTRIBUTING.md の「表記ゆれの点検」。

使い方（リポジトリのルートで）:
  python3 scripts/check_style.py            全体を点検
  python3 scripts/check_style.py FILE...    指定したファイルだけ

見つからなければ終了コード 0、見つかれば「ファイル:行: …」と表示して 1。ファイルは書き換えません。
GitHub Actions の中で動かしたときは、Pull Request の画面に出る注記（::error）も書き出します。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "scripts", "style_rules.json")
EXTS = (".html", ".js", ".cjs", ".py", ".json")
SKIP_DIRS = {"build", "design", "node_modules"}


def load_rules():
    with open(RULES, encoding="utf-8") as f:
        rules = json.load(f).get("rules", [])
    for i, r in enumerate(rules):
        if not r.get("bad") or "good" not in r:
            sys.exit("style_rules.json の %d 番目の規則に bad と good がありません" % (i + 1))
        if r["bad"] == r["good"]:
            sys.exit("style_rules.json の %d 番目の規則は bad と good が同じです" % (i + 1))
    return rules


def files():
    for d, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and not (d == ROOT and x in SKIP_DIRS))
        for n in sorted(names):
            p = os.path.join(d, n)
            if n.endswith(EXTS) and os.path.abspath(p) != RULES:
                yield p


def main():
    rules = load_rules()
    targets = [os.path.abspath(a) for a in sys.argv[1:]] or list(files())
    gha = os.environ.get("GITHUB_ACTIONS") == "true"
    hits = 0
    for p in targets:
        if os.path.abspath(p) == RULES:
            continue
        rel = os.path.relpath(p, ROOT)
        try:
            with open(p, encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            print("!! %s を読めません: %s" % (rel, e))
            hits += 1
            continue
        for no, line in enumerate(lines, 1):
            for r in rules:
                if r["bad"] in line:
                    hits += 1
                    msg = "「%s」→「%s」%s" % (r["bad"], r["good"], "（%s）" % r["note"] if r.get("note") else "")
                    print("%s:%d: %s" % (rel, no, msg))
                    if gha:
                        print("::error file=%s,line=%d::%s" % (rel, no, msg))
    if hits:
        print("\n表記ゆれ: %d 件（規則は scripts/style_rules.json）" % hits)
        return 1
    print("表記ゆれ: なし（%d ファイル・規則 %d 件）" % (len(targets), len(rules)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
