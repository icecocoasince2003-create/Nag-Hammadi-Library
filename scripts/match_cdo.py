#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""match_cdo.py — 辞書の見出しを Comprehensive Coptic Lexicon（CCL）と突き合わせ、
Coptic Dictionary Online（CDO）の TLA 番号の候補を一覧にする。

CDO（https://coptic-dictionary.org/）の項目は、CCL（BBAW と DDGLC の辞書。KELLIA/dictionary の
xml/Comprehensive_Coptic_Lexicon-v1.2-2020.xml、CC BY-SA 4.0）の <entry xml:id="C…">（TLA 番号）で引ける。
source/lexicon.csv の cdo 列にこの番号を書くと、scripts/sync_lexicon.py が data/lexicon.xml に
<ref type="cdo" target="https://coptic-dictionary.org/entry.py?tla=C…"> を書く。
このスクリプトは CCL のファイルを読むだけで、リポジトリには入れない。一覧に写すのは CCL の
TLA 番号・見出しの綴り・品詞のラベルだけで、語義・訳・用例・語源・文献は写さない。

■ 照合（python3 scripts/match_cdo.py CCL.xml）
  1. 辞書（data/lexicon.xml）の <entry> をすべて（<superEntry> の中の同形異義語も）見る。
     見出し（<orth>）に欠損の記号（[ ] … .）があるものは除く（* は除かず、次の 2. で消す）。
  2. 見出しをそろえる: Unicode の NFD に分け、上線などの合成記号を除き、文字（Unicode の L 類。
     ただし修飾文字 Lm は除く）だけを残して小文字にする。ハイフン・⸗・空白・括弧・* なども消える。
     CCL の綴りも同じようにそろえる。
  3. CCL の側: TLA 番号は <entry> の xml:id（C1 など）。見出しは <form type="lemma"> の <orth>
     （1 項目だけ type="lemma" の無いものがあり、そのときは最初の <form>）。そのほかの <form>
     （方言の異形・type="inflected"・type="compound"。略記も含む）を「変化形」とする。
     品詞は <entry> 直下の <gramGrp><pos>、無ければ見出しの <form> の中、それも無ければほかの <form> の中。
  4. 決まり方:
       綴りで一意   そろえた見出しが CCL の見出し 1 項目とだけ同じ
       品詞で絞った CCL の見出しの一致が複数で、品詞の対応表（--pos-table）で合うものが 1 つだけ
       変化形       見出しの一致は無く、変化形の一致が 1 項目だけ
       候補が複数   上のどれでもなく、候補が 2 つ以上（候補はすべて書き、品詞の対応も候補ごとに書く）
     どの綴りとも合わない見出しは一覧に書かず、要約で数だけを示す。
  5. 品詞の対応: CCL の品詞のラベル（ドイツ語）を、下の表 POS_TABLE で辞書の品詞タグ（data/pos_labels.json）
     の組に置き換え、辞書の品詞がその中にあれば「一致」、無ければ「矛盾」。辞書の品詞が空か、表のどの行にも
     出てこないタグ（X・FM など）のとき、また CCL のラベルが表に無いとき（? など）は「不明」。

■ 出力（source/lexicon_cdo_matches.tsv）
  UTF-8（BOM なし）・LF・タブ区切り、見出し行つき。候補のある辞書の項目ごとに 1 行、xml:id の順。
  列: xml:id / 見出し / 品詞 / TLA番号の候補 / CCLの見出し / CCLの品詞 / 決まり方 / 品詞の対応 /
      既存のcdo / メモ / 選んだTLA番号 / 状態 / 確認者
  候補が複数のとき、TLA番号の候補・CCLの見出し・CCLの品詞・品詞の対応は「 | 」で区切って同じ順に並べる。
  既存のcdo は source/lexicon.csv の cdo 列の値。メモには、候補が既存の cdo と違うときにだけ印を書く。
  最後の 3 列は確認する人が書く列（確認作業の画面 review.html のキュー ⑥⑦ が書く）。状態は初め
  「案（生田目の確認待ち）」で、確かめた行を「承認」（違えば「却下」）にする。候補が複数の行は、承認する前に
  選んだTLA番号に 1 つ書く。1 つに決まった行でも、候補と違う番号を選んだTLA番号に書けばそちらを使う。
  TSV がすでにあるときは、その判断（選んだTLA番号・状態・確認者）を、xml:id と TLA番号の候補が同じ行に
  引き継ぐ（候補が変わった行や無くなった行の判断は引き継がず、一覧を表示する）。
  同じ入力からは、いつも同じバイト列の TSV ができる。

■ 反映（python3 scripts/match_cdo.py apply TSV）
  TSV のうち、状態が「承認」の行の TLA 番号を source/lexicon.csv の cdo 列に入れる。--bulk-unique を付けると、
  決まり方が「綴りで一意」で品詞の対応が「一致」の行も入れる（状態を「承認」「案（…）」以外、たとえば
  「却下」にした行は入れない）。入れる番号は、選んだTLA番号があればそれ、無ければ TLA番号の候補
  （候補が 1 つのときだけ）。
  xml:id から CSV の行へは、sync_lexicon.py と同じく (lemma, n) で結ぶ（lexicon.xml の <orth> と @n。
  CSV で同じ (lemma, n) が重なるときは最初の行）。TSV の見出しが lexicon.xml と違う行は飛ばす。
  cdo 列にすでに別の値がある行は書き換えず、報告だけする。書き換えるのは cdo 列のセルだけで、
  BOM・列の順・引用符の付け方・改行などほかのバイトはそのまま残す。
  何も付けなければ表示だけ（dry-run）。--write で source/lexicon.csv に書き込む。そのあとは
  python3 scripts/sync_lexicon.py（--write）で data/lexicon.xml に反映する。

使い方（リポジトリのルートで）:
  python3 scripts/match_cdo.py ~/kellia-dictionary/xml/Comprehensive_Coptic_Lexicon-v1.2-2020.xml
                                                       照合して TSV を書き、要約を表示
  python3 scripts/match_cdo.py --pos-table             品詞の対応表を表示
  python3 scripts/match_cdo.py apply source/lexicon_cdo_matches.tsv                 書き込む内容を表示するだけ
  python3 scripts/match_cdo.py apply source/lexicon_cdo_matches.tsv --write         source/lexicon.csv に書き込む
  python3 scripts/match_cdo.py apply source/lexicon_cdo_matches.tsv --bulk-unique   「綴りで一意」かつ「一致」の行も
  （試しに動かすときは、--lexicon・--csv で辞書の XML・CSV の場所を、--out（照合のみ）で TSV の書き先を変えられる）
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON_XML = os.path.join(ROOT, "data", "lexicon.xml")
LEXICON_CSV = os.path.join(ROOT, "source", "lexicon.csv")
POS_LABELS = os.path.join(ROOT, "data", "pos_labels.json")
OUT_TSV = os.path.join(ROOT, "source", "lexicon_cdo_matches.tsv")

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

CHOSEN, STATE, REVIEWER = "選んだTLA番号", "状態", "確認者"
COLUMNS = ["xml:id", "見出し", "品詞", "TLA番号の候補", "CCLの見出し", "CCLの品詞",
           "決まり方", "品詞の対応", "既存のcdo", "メモ", CHOSEN, STATE, REVIEWER]
DECISION = (CHOSEN, STATE, REVIEWER)     # 確認する人が書く列（作り直しても引き継ぐ）
STATE_DRAFT = "案（生田目の確認待ち）"
STATE_OK = "承認"
UNIQUE, BY_POS, VARIANT, SEVERAL = "綴りで一意", "品詞で絞った", "変化形", "候補が複数"
AGREE, CONFLICT, UNKNOWN = "一致", "矛盾", "不明"
SEP = " | "          # 候補を並べる区切り
LACUNA = re.compile(r"[\[\]….]")    # 欠損の記号を含む見出しは照合しない
TLA_ID = re.compile(r"C\d+")

# CCL の品詞のラベル（ドイツ語。CCL v1.2 に出てくるもの）→ 辞書の品詞タグ（data/pos_labels.json）。
# 1 つのラベルに、意味の上で当てはまりうるタグをすべて挙げる（辞書の付け方に合わせたものは説明に書く）。
POS_TABLE = [
    ("Subst.", ("N", "NPROP", "ADJ"),
     "名詞（固有名詞も Subst.。ギリシア語借用語（DDGLC 由来）は形容詞も Subst. で、Adj. は 2 項目だけ）"),
    ("Subst.?", ("N", "NPROP", "ADJ"), "名詞（CCL で ? 付き）"),
    ("Vb.", ("V", "VSTAT", "VBD", "AUX", "EXIST"), "動詞（状態形・ⲡⲉϫⲉ- 型・ⲟⲩⲛ- などの助動詞を含む）"),
    ("Vb.?", ("V", "VSTAT", "VBD"), "動詞（CCL で ? 付き）"),
    ("Vb. Hilfsverb.", ("AUX", "V"), "助動詞"),
    ("unpersönlicher Ausdruck", ("V", "EXIST"), "非人称の表現（ⲟⲩⲛϭⲟⲙ など）"),
    ("Adj.", ("ADJ",),
     "形容詞（辞書は ⲁⲧ- の複合語などを N にしているが、N は入れない。CCL では同じ綴りの Subst. と Adj. が"
     "並ぶことが多く、N を入れると名詞の方に絞れなくなるため）"),
    ("Adj.?", ("ADJ",), "形容詞（CCL で ? 付き）"),
    ("Adv.", ("ADV", "PINT"), "副詞（疑問副詞を含む）"),
    ("Präp.", ("PREP",), "前置詞"),
    ("Konj.", ("CONJ",), "接続詞"),
    ("Partikel", ("PTC", "NEG", "PINT"), "不変化詞（ⲁⲛ などの否定・疑問の不変化詞を含む）"),
    ("Partikel, enklitisch", ("PTC",), "前の語に付く不変化詞（ⲣⲱ）"),
    ("Interjektion", ("INTERJ", "PTC"), "間投詞（辞書は ϩⲁⲓⲟ・ⲉⲓⲥ などを PTC にしている）"),
    ("Zahlwort", ("NUM",), "数詞"),
    ("Zahlzeichen", ("NUM",), "数を表す文字"),
    ("Verbalpräfix", ("AUX", "APST", "AAOR", "ACONJ", "ACAUS", "AOPT", "ANEGAOR", "ANEGPST",
                      "NEGPST", "FUT", "PRET", "NEG", "CONV"),
     "活用の接頭辞（辞書は ⲁ を PRET、ⲙⲡⲉ を NEG、ⲙⲡⲁⲧ を CONV にもしている）"),
    ("Satzkonverter", ("CONV", "CREL", "CCIRC", "CFOC", "CPRET", "REL", "PRET"), "変換詞（関係の ⲉⲧ- などを含む）"),
    ("Pron.", ("PPER", "PDEM", "PINT", "N"), "代名詞（辞書は ⲟⲩⲟⲛ・ⲛⲓⲙ など不定代名詞を N にしている）"),
    ("Dem. Pron.", ("PDEM", "COP"), "指示代名詞（繋辞の ⲡⲉ・ⲧⲉ・ⲛⲉ を含む）"),
    ("Selbst. Pers. Pron.", ("PPER",), "独立人称代名詞"),
    ("Suffixpronomen", ("PPER",), "接尾人称代名詞"),
    ("Präfixpronomen (Präsens I)", ("PPER",), "現在 I の接頭人称代名詞"),
    ("Interr. Pron.", ("PINT",), "疑問代名詞"),
    ("Possessivartikel", ("POSS", "PPOS"), "所有冠詞（辞書は POSS と PPOS の両方を使っている）"),
    ("Possessivpräfix", ("PPOS", "POSS"), "所有の接頭辞（ⲡⲁ- 「～のもの」）"),
    ("Poss. Pron.", ("PPOS", "POSS"), "所有代名詞（ⲡⲱ⸗）"),
    ("bestimmter Artikel", ("ART",), "定冠詞"),
    ("unbestimmter Artikel", ("ART",), "不定冠詞"),
    ("Nominalpräfix", ("PFX", "N"), "名詞を作る接頭辞（辞書は ⲣⲉϥ・ⲣⲙ を N にしている）"),
    ("Adjektivpräfix", ("PFX",), "形容詞を作る接頭辞（ⲁⲧ-）"),
    ("Präfix der Ordinalzahlen", ("PFX", "NUM"), "序数の接頭辞（ⲙⲉϩ-）"),
    ("Präfix", ("PFX", "AUX", "ACAUS"), "接頭辞（ⲧⲣⲉ- などを含む）"),
]
# 品詞として対応させないラベル（品詞の対応は「不明」）
POS_UNMAPPED = [
    ("?", "CCL で品詞が未定"),
    ("Kompositum", "複合語（ⲛⲧⲉⲓϭⲟⲧ・ⲁϣ ⲛϭⲟⲧ。品詞は決まらない）"),
]
POS_MAP = {label: set(tags) for label, tags, _ in POS_TABLE}
KNOWN_TAGS = set().union(*POS_MAP.values())


def norm(s):
    """見出しをそろえる: NFD・合成記号を除く・文字（Lm 以外の L 類）だけ・小文字。"""
    out = []
    for ch in unicodedata.normalize("NFD", s or ""):
        cat = unicodedata.category(ch)
        if cat[0] == "L" and cat != "Lm":
            out.append(ch)
    return "".join(out).lower()


def natural_key(xid):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", xid)]


def tla_key(tla):
    return int(tla[1:]) if TLA_ID.fullmatch(tla) else 10 ** 9


# ---------------------------------------------------------------- 辞書（data/lexicon.xml・source/lexicon.csv）

def read_lexicon(path):
    """lexicon.xml の <entry> を文書の順に返す。sync_lexicon.py と同じ正規表現で (lemma, n) を取る。"""
    xml = open(path, encoding="utf-8").read()
    entry_re = re.compile(r"<entry\b[^>]*>.*?</entry>", re.S)
    entries = []
    for m in entry_re.finditer(xml):
        block = m.group(0)
        tag = block[: block.index(">") + 1]
        xid = re.search(r'xml:id="([^"]+)"', tag).group(1)
        n = re.search(r'\bn="([^"]+)"', tag)
        lemma = re.search(r"<orth>(.*?)</orth>", block, re.S).group(1)
        lemma = lemma.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        pos = re.search(r"<pos>(.*?)</pos>", block, re.S)
        entries.append({"id": xid, "lemma": lemma, "n": n.group(1) if n else "1",
                        "pos": pos.group(1).strip() if pos else ""})
    return entries


BOM = b"\xef\xbb\xbf"


class LexiconCSV:
    """source/lexicon.csv を、セルの位置（生の文字列の範囲）つきで読む。

    行の値は sync_lexicon.py と同じく csv.DictReader（utf-8-sig）で読み、前後の空白を除き、n が空なら "1" とする。
    (lemma, n) が重なるときは最初の行を使う（sync_lexicon.py は後の行を無視する）。"""

    def __init__(self, path):
        self.path = path
        raw = open(path, "rb").read()
        self.bom = raw.startswith(BOM)
        self.text = raw[len(BOM):].decode("utf-8") if self.bom else raw.decode("utf-8")
        self.records = scan_csv(self.text)
        values = record_values(self.text, self.records)
        if values != list(csv.reader(io.StringIO(self.text, newline=""))):
            raise SystemExit("!! %s: CSV の区切りの読み取りが csv モジュールと合いません — 中止" % path)
        with open(path, encoding="utf-8-sig", newline="") as f:
            dict_rows = list(csv.DictReader(f))
        self.header = values[0] if values else []
        if "cdo" not in self.header:
            raise SystemExit("!! %s に cdo 列がありません" % path)
        self.cdo_col = self.header.index("cdo")
        rec_nos = [i for i, v in enumerate(values) if i > 0 and v]   # DictReader は空の行を飛ばす
        if len(rec_nos) != len(dict_rows):
            raise SystemExit("!! %s: 行の数が csv.DictReader と合いません — 中止" % path)
        self.rows = []
        for rec_no, r in zip(rec_nos, dict_rows):
            row = {k: (r.get(k) or "").strip() for k in self.header}
            row["n"] = row.get("n") or "1"
            row["_rec"] = rec_no
            self.rows.append(row)
        self.by_key = {}
        for row in self.rows:
            self.by_key.setdefault((row.get("lemma", ""), row["n"]), row)

    def line_no(self, row):
        """CSV の行番号（1 から。見出し行が 1）。"""
        start = self.records[row["_rec"]][0][0][0]
        return self.text.count("\n", 0, start) + 1

    def with_cdo(self, changes):
        """changes: {レコード番号: 新しい値}。cdo 列のセルだけを書き換えたバイト列を返し、
        読み直して、そのセル以外の値が元のままかを確かめる。"""
        text = self.text
        edits = []
        for rec_no, value in changes.items():
            fields, rec_end = self.records[rec_no]
            if self.cdo_col < len(fields):
                start, end = fields[self.cdo_col]
                edits.append((start, end, value))
            else:                                        # 行の末尾の空セルが省かれているとき
                edits.append((rec_end, rec_end, "," * (self.cdo_col - len(fields) + 1) + value))
        for start, end, value in sorted(edits, reverse=True):
            text = text[:start] + value + text[end:]
        expect = record_values(self.text, self.records)
        for rec_no, value in changes.items():
            expect[rec_no] += [""] * (self.cdo_col + 1 - len(expect[rec_no]))
            expect[rec_no][self.cdo_col] = value
        if record_values(text, scan_csv(text)) != expect:
            raise SystemExit("!! 書き換えた CSV を読み直すと、cdo 列のほかにも違いが出ます — 書き込みを中止します")
        return (BOM if self.bom else b"") + text.encode("utf-8")


def record_values(text, records):
    """scan_csv のレコードから、セルの値（引用符を外したもの）の一覧を作る。"""
    out = []
    for fields, _ in records:
        vals = []
        for start, end in fields:
            s = text[start:end]
            vals.append(s[1:-1].replace('""', '"') if s.startswith('"') else s)
        out.append(vals)
    return out


def scan_csv(text):
    """CSV（区切りは ,、引用符は "）をレコードに分ける。各レコードは ([(セルの始め, 終わり)…], 改行の前の位置)。
    空の行はセル無し（csv.reader と同じ）。"""
    records, i, n = [], 0, len(text)
    while i < n:
        start_of_record = i
        fields = []
        while True:
            start = i
            if i < n and text[i] == '"':
                i += 1
                while True:
                    j = text.find('"', i)
                    if j < 0:
                        raise SystemExit("!! CSV: 引用符が閉じていません（%d 文字目から）" % start)
                    if text.startswith('""', j):
                        i = j + 2
                        continue
                    i = j + 1
                    break
                if i < n and text[i] not in ",\r\n":
                    raise SystemExit("!! CSV: 引用符の後に余分な文字があります（%d 文字目）" % i)
            else:
                while i < n and text[i] not in ",\r\n":
                    i += 1
            fields.append((start, i))
            if i < n and text[i] == ",":
                i += 1
                continue
            break
        end = i
        if text.startswith("\r\n", i):
            i += 2
        elif i < n:
            i += 1
        records.append(([] if end == start_of_record else fields, end))
    return records


# ---------------------------------------------------------------- CCL

def read_ccl(path):
    """CCL の <entry> を読む。外から取ってきたファイルなので、DTD・実体の宣言があれば読まずに止める。"""
    data = open(path, "rb").read()
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise SystemExit("!! %s に DTD か実体の宣言があります。想定と違うファイルなので読みません。" % path)
    root = ET.fromstring(data)
    if root.tag != TEI + "TEI":
        raise SystemExit("!! %s は TEI の文書ではありません" % path)

    def text(el):
        return " ".join("".join(el.itertext()).split()) if el is not None else ""

    def labels(elems):
        out = []
        for g in elems:
            for p in g.findall(TEI + "pos"):
                t = text(p)
                if t and t not in out:
                    out.append(t)
        return out

    info = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "edition": text(root.find(".//%spublicationStmt/%sidno[@type='edition']" % (TEI, TEI))),
        "doi": text(root.find(".//%spublicationStmt/%sidno[@type='DOI']" % (TEI, TEI))),
    }
    entries = []
    for e in root.find(TEI + "text").iter(TEI + "entry"):
        tla = e.get(XML_ID) or ""
        forms = e.findall(TEI + "form")
        lemma_forms = [f for f in forms if f.get("type") == "lemma"] or forms[:1]
        other_forms = [f for f in forms if f not in lemma_forms]
        lemma_orths = [text(f.find(TEI + "orth")) for f in lemma_forms]
        pos = (labels(e.findall(TEI + "gramGrp"))
               or labels(g for f in lemma_forms for g in f.findall(TEI + "gramGrp"))
               or labels(g for f in other_forms for g in f.findall(TEI + "gramGrp")))
        lemma_keys = {norm(o) for o in lemma_orths} - {""}
        var_keys = {norm(text(f.find(TEI + "orth"))) for f in other_forms} - {""}
        entries.append({"tla": tla, "orth": "/".join(o for o in lemma_orths if o) or "—",
                        "pos": pos, "lemma_keys": lemma_keys, "var_keys": var_keys})
    return info, entries


def pos_agreement(tag, ccl_labels):
    if tag not in KNOWN_TAGS:
        return UNKNOWN
    mapped = [POS_MAP[lab] for lab in ccl_labels if lab in POS_MAP]
    if not mapped:
        return UNKNOWN
    return AGREE if any(tag in tags for tags in mapped) else CONFLICT


# ---------------------------------------------------------------- 照合

def match(lexicon, csv_rows, ccl):
    by_lemma, by_variant = defaultdict(list), defaultdict(list)
    for c in ccl:
        for k in c["lemma_keys"]:
            by_lemma[k].append(c)
        for k in c["var_keys"]:
            by_variant[k].append(c)

    def uniq(cands):
        seen, out = set(), []
        for c in sorted(cands, key=lambda c: tla_key(c["tla"])):
            if c["tla"] not in seen:
                seen.add(c["tla"])
                out.append(c)
        return out

    stats = Counter()
    rows, lacunose, existing = [], [], []
    for ent in lexicon:
        csv_row = csv_rows.by_key.get((ent["lemma"], ent["n"]))
        old = csv_row.get("cdo", "") if csv_row else ""
        if LACUNA.search(ent["lemma"]) or not norm(ent["lemma"]):
            lacunose.append(ent)
            if old:
                existing.append((ent, old, None, []))
            continue
        key = norm(ent["lemma"])
        level = "lemma"
        cands = uniq(by_lemma.get(key, []))
        if not cands:
            level = "variant"
            cands = uniq(by_variant.get(key, []))
        agree = [pos_agreement(ent["pos"], c["pos"]) for c in cands]
        how = None
        if len(cands) == 1:
            how = UNIQUE if level == "lemma" else VARIANT
        elif len(cands) > 1 and level == "lemma" and agree.count(AGREE) == 1:
            how = BY_POS
            k = agree.index(AGREE)
            cands, agree = [cands[k]], [AGREE]
        elif len(cands) > 1:
            how = SEVERAL
            stats["several_" + level] += 1
        stats["considered"] += 1
        if old:
            existing.append((ent, old, how, [c["tla"] for c in cands]))
        if not cands:
            stats["none"] += 1
            continue
        stats[how] += 1
        if how in (UNIQUE, VARIANT):
            stats[(how, agree[0])] += 1
        tlas = [c["tla"] for c in cands]
        memo = ""
        if old and how != SEVERAL and old != tlas[0]:
            memo = "既存の cdo（%s）と異なる" % old
        elif old and how == SEVERAL and old not in tlas:
            memo = "既存の cdo（%s）は候補に無い" % old
        rows.append({
            "xml:id": ent["id"], "見出し": ent["lemma"], "品詞": ent["pos"],
            "TLA番号の候補": SEP.join(tlas),
            "CCLの見出し": SEP.join(c["orth"] for c in cands),
            "CCLの品詞": SEP.join("/".join(c["pos"]) or "—" for c in cands),
            "決まり方": how, "品詞の対応": SEP.join(agree),
            "既存のcdo": old, "メモ": memo, CHOSEN: "", STATE: STATE_DRAFT, REVIEWER: "",
        })
    rows.sort(key=lambda r: natural_key(r["xml:id"]))
    return rows, stats, lacunose, existing


def read_decisions(path):
    """前に書いた TSV の判断。{xml:id: (TLA番号の候補, {選んだTLA番号・状態・確認者})}。まだ判断していない行は入れない。"""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        out = {}
        for r in reader:
            got = {c: (r.get(c) or "").strip() for c in DECISION}
            if got[STATE] in ("", STATE_DRAFT) and not got[CHOSEN] and not got[REVIEWER]:
                continue
            got[STATE] = got[STATE] or STATE_DRAFT
            out[(r.get("xml:id") or "").strip()] = ((r.get("TLA番号の候補") or "").strip(), got)
    return out


def carry_decisions(rows, decisions):
    """decisions を、xml:id と TLA番号の候補が同じ行に写す。写せなかったものを [(xml:id, 前の候補, 判断, 理由)] で返す。"""
    left = dict(decisions)
    for r in rows:
        d = left.pop(r["xml:id"], None)
        if d is None:
            continue
        if d[0] == r["TLA番号の候補"]:
            r.update(d[1])
        else:
            left[r["xml:id"]] = d + ("候補が変わった（今は %s）" % r["TLA番号の候補"],)
    return [(xid,) + (d if len(d) == 3 else d + ("候補が無くなった",)) for xid, d in sorted(left.items(), key=lambda x: natural_key(x[0]))]


def tsv_bytes(rows):
    def clean(v):
        v = " ".join(str(v).split())
        if '"' in v:
            raise SystemExit("!! TSV に引用符を含む値があります: %r" % v)
        return v
    lines = ["\t".join(COLUMNS)] + ["\t".join(clean(r[c]) for c in COLUMNS) for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def shown(path):
    """表示用のパス（いまのフォルダの中なら相対パス）。"""
    rel = os.path.relpath(path)
    return path if rel.startswith("..") else rel


def pct(a, b):
    return "%.1f%%" % (100.0 * a / b) if b else "—"


def cmd_match(argv):
    ap = argparse.ArgumentParser(prog="match_cdo.py", description="辞書の見出しを CCL と突き合わせる")
    ap.add_argument("ccl", nargs="?", help="Comprehensive_Coptic_Lexicon-v1.2-2020.xml の場所")
    ap.add_argument("--pos-table", action="store_true", help="品詞の対応表を表示する")
    ap.add_argument("--out", default=OUT_TSV, help="TSV の書き先（既定: source/lexicon_cdo_matches.tsv）")
    ap.add_argument("--lexicon", default=LEXICON_XML, help="辞書の XML（既定: data/lexicon.xml）")
    ap.add_argument("--csv", default=LEXICON_CSV, help="辞書の CSV（既定: source/lexicon.csv）")
    a = ap.parse_args(argv)
    if a.pos_table:
        print_pos_table()
        if not a.ccl:
            return 0
    if not a.ccl:
        ap.error("CCL の XML の場所を指定してください")

    lexicon = read_lexicon(a.lexicon)
    csv_rows = LexiconCSV(a.csv)
    info, ccl = read_ccl(a.ccl)
    rows, st, lacunose, existing = match(lexicon, csv_rows, ccl)
    decisions = read_decisions(a.out)
    lost = carry_decisions(rows, decisions)

    data = tsv_bytes(rows)
    with open(a.out, "wb") as f:
        f.write(data)

    n = st["considered"]
    print("CCL: %s（%d 項目）edition %s, DOI %s, SHA-256 %s" % (
        os.path.basename(a.ccl), len(ccl), info["edition"] or "?", info["doi"] or "?", info["sha256"]))
    print("辞書の項目: %d（欠損の記号で除いた見出し %d: %s）" % (
        len(lexicon), len(lacunose), " ".join("%s %s" % (e["id"], e["lemma"]) for e in lacunose)))
    print("照合した見出し: %d" % n)
    for how in (UNIQUE, BY_POS, VARIANT, SEVERAL):
        print("  %-8s %5d  %6s" % (how, st[how], pct(st[how], n)))
        if how in (UNIQUE, VARIANT):
            print("      品詞の対応: 一致 %d・矛盾 %d・不明 %d" % (
                st[(how, AGREE)], st[(how, CONFLICT)], st[(how, UNKNOWN)]))
        if how == SEVERAL:
            print("      見出しの一致が複数 %d・変化形の一致が複数 %d" % (st["several_lemma"], st["several_variant"]))
    print("  候補なし  %5d  %6s" % (st["none"], pct(st["none"], n)))
    print("既存の cdo（CSV の値が lexicon.xml の項目に結びつくもの）: %d" % len(existing))
    same = [x for x in existing if x[2] in (UNIQUE, BY_POS, VARIANT) and x[3] == [x[1]]]
    among = [x for x in existing if x[2] == SEVERAL and x[1] in x[3]]
    other = [x for x in existing if x not in same and x not in among]
    print("  一致 %d・候補の一つ %d・食い違い %d" % (len(same), len(among), len(other)))
    for ent, old, how, tlas in other:
        print("   ≠ %s %s（%s）既存 %s → %s %s" % (ent["id"], ent["lemma"], ent["pos"] or "—", old,
                                              how or "候補なし", SEP.join(tlas) or "—"))
    xml_keys = {(e["lemma"], e["n"]) for e in lexicon}
    orphans = [r for r in csv_rows.rows if r.get("cdo")
               and (csv_rows.by_key.get((r["lemma"], r["n"])) is not r or (r["lemma"], r["n"]) not in xml_keys)]
    print("CSV の cdo の値のうち lexicon.xml に入らないもの（sync_lexicon.py が反映しない行）: %d" % len(orphans))
    for r in orphans:
        why = ("同じ (lemma, n) の 2 つ目の行（sync_lexicon.py は無視する）"
               if csv_rows.by_key.get((r["lemma"], r["n"])) is not r
               else "lexicon.xml にこの (lemma, n) の項目が無い（新しい同形異義語。superEntry にするのは手作業）")
        print("   - %d 行目 %s（n=%s）%s: %s" % (csv_rows.line_no(r), r["lemma"], r["n"], r["cdo"], why))
    used = Counter(lab for c in ccl for lab in c["pos"])
    unknown = sorted(lab for lab in used if lab not in POS_MAP and lab not in dict(POS_UNMAPPED))
    print("表に無い CCL の品詞ラベル: %s" % (", ".join(unknown) or "なし"))
    if decisions:
        print("前の TSV の判断: %d 行のうち、引き継いだもの %d・引き継げなかったもの %d" % (
            len(decisions), len(decisions) - len(lost), len(lost)))
        for xid, cands, got, why in lost:
            print("   - %s（前の候補 %s）%s: %s" % (xid, cands or "—", "・".join("%s=%s" % (c, got[c]) for c in DECISION if got[c]), why))
    print("→ %s（%d 行、%d バイト）" % (shown(a.out), len(rows), len(data)))
    return 0


def print_pos_table():
    names = {}
    try:
        with open(POS_LABELS, encoding="utf-8") as f:
            names = {t["tag"]: t["ja"] for t in json.load(f).get("tags", [])}
    except (OSError, ValueError):
        pass
    print("CCL の品詞（ドイツ語）→ 辞書の品詞タグ")
    for label, tags, note in POS_TABLE:
        print("  %-28s %s" % (label, "・".join("%s（%s）" % (t, names.get(t, "?")) for t in tags)))
        print("  %-28s   %s" % ("", note))
    print("対応させないラベル（品詞の対応は「不明」）")
    for label, note in POS_UNMAPPED:
        print("  %-28s %s" % (label, note))
    print("辞書の品詞が空のとき、上の表に出てこないタグ（%s）のときも「不明」。" %
          "・".join(sorted(set(names) - KNOWN_TAGS) or ["X", "FM"]))


# ---------------------------------------------------------------- 反映

def cmd_apply(argv):
    ap = argparse.ArgumentParser(prog="match_cdo.py apply", description="承認した TLA 番号を lexicon.csv の cdo 列に入れる")
    ap.add_argument("tsv", help="source/lexicon_cdo_matches.tsv（状態を「承認」にしたもの）")
    ap.add_argument("--write", action="store_true", help="source/lexicon.csv に書き込む（付けなければ表示だけ）")
    ap.add_argument("--bulk-unique", action="store_true", help="「綴りで一意」かつ品詞の対応が「一致」の行も入れる")
    ap.add_argument("--lexicon", default=LEXICON_XML, help="辞書の XML（既定: data/lexicon.xml）")
    ap.add_argument("--csv", default=LEXICON_CSV, help="書き込む CSV（既定: source/lexicon.csv）")
    a = ap.parse_args(argv)

    with open(a.tsv, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        header = [h.strip() for h in next(reader, [])]
        missing = [c for c in ("xml:id", "見出し", "TLA番号の候補", "決まり方", "品詞の対応", "状態") if c not in header]
        if missing:
            raise SystemExit("!! %s に列がありません: %s" % (a.tsv, ", ".join(missing)))
        tsv = [dict(zip(header, [v.strip() for v in r])) for r in reader if any(v.strip() for v in r)]

    lexicon = {e["id"]: e for e in read_lexicon(a.lexicon)}
    table = LexiconCSV(a.csv)

    picked, skipped, seen = [], [], set()
    for r in tsv:
        xid, state = r.get("xml:id", ""), r.get("状態", "")
        bulk = (a.bulk_unique and r.get("決まり方") == UNIQUE and r.get("品詞の対応") == AGREE
                and state in (STATE_DRAFT, STATE_OK))
        if state != STATE_OK and not bulk:
            continue
        why = "承認" if state == STATE_OK else "--bulk-unique"
        tla = r.get(CHOSEN, "") or r.get("TLA番号の候補", "")
        if r.get(CHOSEN):
            why += "・選んだ番号"
        ent = lexicon.get(xid)
        if xid in seen:
            skipped.append((xid, r.get("見出し", ""), "TSV に同じ xml:id の行が 2 つ以上ある"))
        elif ent is None:
            skipped.append((xid, r.get("見出し", ""), "lexicon.xml にこの xml:id が無い"))
        elif " ".join(ent["lemma"].split()) != r.get("見出し", ""):
            skipped.append((xid, r.get("見出し", ""), "見出しが lexicon.xml（%s）と違う" % ent["lemma"]))
        elif not TLA_ID.fullmatch(tla):
            skipped.append((xid, ent["lemma"], "TLA 番号が 1 つに決まっていない（%s が空で、候補は %s）" % (CHOSEN, tla or "空")
                            if not r.get(CHOSEN) else "%s の形が違う（%s）" % (CHOSEN, tla)))
        elif (ent["lemma"], ent["n"]) not in table.by_key:
            skipped.append((xid, ent["lemma"], "lexicon.csv に (lemma, n) = (%s, %s) の行が無い" % (ent["lemma"], ent["n"])))
        else:
            picked.append((ent, tla, why, table.by_key[(ent["lemma"], ent["n"])]))
        seen.add(xid)

    changes, already, conflicts = {}, [], []
    for ent, tla, why, row in picked:
        old = changes.get(row["_rec"], row.get("cdo", ""))
        if old == tla:
            already.append((ent, tla))
        elif old:
            conflicts.append((ent, tla, old, table.line_no(row)))
        else:
            changes[row["_rec"]] = tla
            row_line = table.line_no(row)
            print("  + %s %s（n=%s, %d 行目）cdo = %s  [%s]" % (ent["id"], ent["lemma"], ent["n"], row_line, tla, why))
    print("書き込む: %d 件・すでに同じ値: %d 件・既存の別の値があるので書かない: %d 件・飛ばした行: %d 件" % (
        len(changes), len(already), len(conflicts), len(skipped)))
    for ent, tla, old, line in conflicts:
        print("  ≠ %s %s（%d 行目）既存 %s・TSV %s" % (ent["id"], ent["lemma"], line, old, tla))
    for xid, lemma, why in skipped:
        print("  ? %s %s: %s" % (xid, lemma, why))

    if not changes:
        print("変更なし — %s は書き換えません。" % shown(a.csv))
        return 0
    new = table.with_cdo(changes)
    if a.write:
        with open(a.csv, "wb") as f:
            f.write(new)
        print("→ %s に書き込みました。続けて python3 scripts/sync_lexicon.py で data/lexicon.xml への反映を確かめてください。"
              % shown(a.csv))
    else:
        print("(dry-run: 書き込むには --write を付けてください)")
    return 0


def main(argv):
    if argv and argv[0] == "apply":
        return cmd_apply(argv[1:])
    return cmd_match(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
