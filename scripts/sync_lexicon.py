#!/usr/bin/env python3
"""sync_lexicon.py — source/lexicon.csv の内容を data/lexicon.xml に反映する。

方針:
  * 既存エントリの xml:id は絶対に変更しない(本文の @ana="#lex-…" ピンを守るため)
  * (lemma, n) をキーに CSV と XML を突き合わせ、内容が変わった行だけ
    <entry> ブロックを丸ごと文字列置換する(git diff 最小化)
  * CSV にだけある lemma は </list> 直前に新規 <entry> として追加
    (ID は既存最大 lex-NNNN の続番)
  * XML にだけあるエントリは削除せず報告のみ(ピン破壊防止)
  * 既存の単独エントリが CSV 側で同形異義語化した場合は自動変換せず報告のみ

使い方:  python3 scripts/sync_lexicon.py            # 差分表示のみ(dry-run)
         python3 scripts/sync_lexicon.py --write    # 実際に書き込む
"""
import csv, re, sys, io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "source", "lexicon.csv")
XML_PATH = os.path.join(ROOT, "data", "lexicon.xml")

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

CDO_ENTRY = "https://coptic-dictionary.org/entry.py?tla=%s"

def cdo_url(v):
    """cdo 列の値を URL に変換。TLA ID(C123 / CF123)か、http で始まる完全 URL を受け付ける。"""
    v = v.strip()
    if not v:
        return ""
    if v.startswith("http"):
        return v
    import re as _re
    if _re.fullmatch(r"C[EF]?\d+", v):
        return CDO_ENTRY % v
    print("!! cdo 列の値を解釈できません(無視): %r" % v)
    return ""

def build_body(row, child=False):
    """entry の <form>…</entry> 内側(orth 以降)を CSV 行から生成する。"""
    parts = ['<form type="lemma"><orth>%s</orth></form>' % esc(row["lemma"])]
    if row["pos"] and row["pos"] != "X":   # "X" はプレースホルダ(XML には出力しない)
        parts.append("<gramGrp><pos>%s</pos></gramGrp>" % esc(row["pos"]))
    if row["usg_ja"]:
        parts.append('<usg type="hint" xml:lang="ja">%s</usg>' % esc(row["usg_ja"]))
    if row["usg_en"]:
        parts.append('<usg type="hint" xml:lang="en">%s</usg>' % esc(row["usg_en"]))
    url = cdo_url(row.get("cdo", ""))
    if url:
        parts.append('<ref type="cdo" target="%s">CDO</ref>' % esc(url))
    if row["en"] or row["ja"] or row["fr"]:
        n_attr = ' n="%s"' % esc(row["n"]) if child else ""
        cits = "".join(
            '<cit type="translation" xml:lang="%s"><quote>%s</quote></cit>' % (lg, esc(row[lg]))
            for lg in ("en", "ja", "fr") if row[lg]
        )
        parts.append("<sense%s>%s</sense>" % (n_attr, cits))
    return "".join(parts)

def build_entry(row, xml_id, child=False):
    attrs = ' xml:id="%s"' % xml_id
    if child:
        attrs += ' n="%s"' % esc(row["n"])
    if row["grc"].strip().upper() == "Y":
        attrs += ' xml:lang="grc"'
    return "<entry%s>%s</entry>" % (attrs, build_body(row, child))

def main():
    write = "--write" in sys.argv

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in list(r):
            r[k] = (r[k] or "").strip()
        r["n"] = r["n"] or "1"
        r.setdefault("cdo", "")
    csv_map = {}
    for r in rows:
        key = (r["lemma"], r["n"])
        if key in csv_map:
            print("!! CSV 内で重複キー (lemma=%s, n=%s) — 後の行を無視" % key)
            continue
        csv_map[key] = r

    xml = open(XML_PATH, encoding="utf-8").read()

    # 既存 entry を列挙(superEntry の子も同じ正規表現で拾える:entry は入れ子にならない)
    entry_re = re.compile(r"<entry\b[^>]*>.*?</entry>", re.S)
    id_re    = re.compile(r'xml:id="([^"]+)"')
    n_re     = re.compile(r'\bn="([^"]+)"')
    orth_re  = re.compile(r"<orth>(.*?)</orth>", re.S)

    xml_map = {}          # (lemma, n) -> (block, xml_id, is_child)
    max_id = 0
    for m in entry_re.finditer(xml):
        block = m.group(0)
        tag = block[: block.index(">") + 1]
        xid = id_re.search(tag).group(1)
        num = re.match(r"lex-(\d+)", xid)
        if num:
            max_id = max(max_id, int(num.group(1)))
        n = n_re.search(tag)
        is_child = bool(re.match(r"lex-\d+-\d+$", xid))
        lemma = orth_re.search(block).group(1)
        lemma = lemma.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        xml_map[(lemma, n.group(1) if n else "1")] = (block, xid, is_child)
    # superEntry 自身の ID も採番対象
    for m in re.finditer(r'<superEntry xml:id="lex-(\d+)"', xml):
        max_id = max(max_id, int(m.group(1)))

    changed, added, missing_csv, new_homographs = [], [], [], []

    # --- 更新 ---
    for key, row in csv_map.items():
        if key in xml_map:
            block, xid, is_child = xml_map[key]
            new_block = build_entry(row, xid, child=is_child)
            if new_block != block:
                if xml.count(block) != 1:
                    print("!! 置換対象が一意でない: %s — スキップ" % xid)
                    continue
                xml = xml.replace(block, new_block)
                changed.append((xid, row["lemma"]))
        else:
            # 同 lemma の別 n が既にある → 同形異義語化。自動では触らない
            if any(k[0] == row["lemma"] for k in xml_map):
                new_homographs.append(key)
            else:
                added.append(row)

    # --- XML にだけあるもの(報告のみ) ---
    for key in xml_map:
        if key not in csv_map:
            missing_csv.append((xml_map[key][1], key[0], key[1]))

    # --- 追加 ---
    if added:
        added.sort(key=lambda r: r["lemma"])
        buf = []
        for r in added:
            max_id += 1
            buf.append("        " + build_entry(r, "lex-%04d" % max_id))
        anchor = "      </list>"
        if xml.count(anchor) != 1:
            print("!! </list> アンカーが一意でない — 追加を中止"); sys.exit(1)
        xml = xml.replace(anchor, "\n".join(buf) + "\n" + anchor)

    # --- 報告 ---
    print("更新: %d 件" % len(changed))
    for xid, lm in changed[:20]:
        print("   ~ %s  %s" % (xid, lm))
    if len(changed) > 20: print("   … 他 %d 件" % (len(changed) - 20))
    print("追加: %d 件" % len(added))
    for r in added[:20]:
        print("   + %s (%s)" % (r["lemma"], r["pos"] or "—"))
    if len(added) > 20: print("   … 他 %d 件" % (len(added) - 20))
    if missing_csv:
        print("CSV に無い既存エントリ(削除はしません): %d 件" % len(missing_csv))
        for xid, lm, n in missing_csv[:10]:
            print("   ? %s  %s (n=%s)" % (xid, lm, n))
    if new_homographs:
        print("!! 新規の同形異義語化(superEntry 化は手動で): %s" % new_homographs)

    if not (changed or added):
        print("変更なし — CSV と XML は同期しています。")
        return

    if write:
        with open(XML_PATH, "w", encoding="utf-8", newline="") as f:
            f.write(xml)
        print("→ %s に書き込みました。" % XML_PATH)
    else:
        print("(dry-run: 書き込みには --write を付けてください)")

if __name__ == "__main__":
    main()
