#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_release.py — 版の情報が 3 つのファイルでそろっているかを調べる

  data/release.json   サイトが読む版の情報（版番号・リリースの日・DOI・公開 URL）。これが元
  CITATION.cff        GitHub の「Cite this repository」に使われる
  .zenodo.json        Zenodo が GitHub のリリースから記録を作るときに使う

調べること:
  - 版番号（X.Y.Z）が 3 つで同じか
  - release.json に DOI があれば、CITATION.cff の doi: が同じか（無ければ CITATION.cff に doi: が無いか）
  - release.json にリリースの日があれば、CITATION.cff の date-released: が同じか
  - 公開 URL が release.json・CITATION.cff（url:）で同じで、.zenodo.json の related_identifiers に入っているか

使い方（リポジトリのルートで）: python3 scripts/check_release.py
そろっていれば終了コード 0、そろっていなければ食い違いを表示して 1。ファイルは書き換えません。
CITATION.cff は YAML ですが、ここでは上の項目だけを行単位で読みます（PyYAML などは要りません）。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def cff_value(text, key):
    """CITATION.cff の最上位のキーの値（引用符を外す）。無ければ None"""
    m = re.search(r"^%s:\s*(.*?)\s*$" % re.escape(key), text, re.M)
    if not m:
        return None
    return re.sub(r"""^(['"])(.*)\1$""", r"\2", m.group(1))


def main():
    rel = json.loads(read("data/release.json"))
    cff = read("CITATION.cff")
    zen = json.loads(read(".zenodo.json"))
    out = []
    v = rel.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        out.append('data/release.json の version が「X.Y.Z」の形ではありません: "%s"' % v)
    if cff_value(cff, "version") != v:
        out.append('版番号が違います: data/release.json "%s" / CITATION.cff "%s"' % (v, cff_value(cff, "version")))
    if zen.get("version") != v:
        out.append('版番号が違います: data/release.json "%s" / .zenodo.json "%s"' % (v, zen.get("version")))
    doi = rel.get("doi", "")
    if doi and not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        out.append('data/release.json の doi が DOI の形ではありません（https://doi.org/ は付けない）: "%s"' % doi)
    if (cff_value(cff, "doi") or "") != doi:
        out.append('DOI が違います: data/release.json "%s" / CITATION.cff "%s"' % (doi, cff_value(cff, "doi") or ""))
    date = rel.get("date", "")
    if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        out.append('data/release.json の date が YYYY-MM-DD の形ではありません: "%s"' % date)
    if (cff_value(cff, "date-released") or "") != date:
        out.append('リリースの日が違います: data/release.json "%s" / CITATION.cff "%s"' % (date, cff_value(cff, "date-released") or ""))
    url = rel.get("url", "")
    if cff_value(cff, "url") != url:
        out.append('公開 URL が違います: data/release.json "%s" / CITATION.cff "%s"' % (url, cff_value(cff, "url")))
    if url not in [r.get("identifier") for r in zen.get("related_identifiers", [])]:
        out.append('.zenodo.json の related_identifiers に公開 URL（%s）がありません' % url)
    if out:
        print("版の情報がそろっていません:")
        for x in out:
            print("  - " + x)
        return 1
    print("版の情報はそろっています（v%s%s）" % (v, "、DOI " + doi if doi else "、DOI はまだありません"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
