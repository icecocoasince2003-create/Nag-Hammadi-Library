# -*- coding: utf-8 -*-
"""scripts/leiden_to_tei.py・scripts/coptic_nlp_tei.py・scripts/check_spec.py のテスト（標準ライブラリだけ）

  python3 -m unittest tests/test_annotation_tools.py      （リポジトリのルートで）

NLP のサービスにはつながず、保存した出力（tests/fixtures/annotation_tools/coptic_nlp_rep2.tt。2026-11-23 に
Coptic SCRIPTORIUM の NLP が『国家』の最初の 2 セグメントに返したもの）と、テストの中で作る出力を使います。
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "annotation_tools")
T = "{http://www.tei-c.org/ns/1.0}"


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


leiden = load("leiden_to_tei")
nlp = load("coptic_nlp_tei")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=ROOT)


MINI_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="cop">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>test</title>
      </titleStmt>
      <publicationStmt><p>test</p></publicationStmt>
      <sourceDesc><p>test</p></sourceDesc>
    </fileDesc>
    <revisionDesc>
      <change when="2026-01-01">first</change>
    </revisionDesc>
  </teiHeader>
  <text>
    <body>
      <ab>
        <s xml:id="t-1" n="1">
          <lb n="1"/>
          <w>ⲁ</w>
          <w>ϥ</w>
          <w>ⲥⲱⲧ<lb n="2" break="no"/>ⲙ</w>
          <gap reason="lost" quantity="3" unit="character"/>
          <w>ⲛϭⲓ</w>
          <w>ⲡ</w>
          <w>ⲣⲱ<supplied reason="lost">ⲙⲉ</supplied></w>
        </s>
      </ab>
    </body>
  </text>
</TEI>
"""

# 上の本文に対する NLP の答え（<seg> は本物と同じく <norm> の中で開く）
MINI_SGML = """<norm_group><norm pos="APST" lemma="ⲁ" norm="ⲁ"><seg n="t-1~0">ⲁ</norm>
<norm pos="PPERS" lemma="ⲛⲧⲟϥ" norm="ϥ">ϥ</norm><norm pos="V" lemma="ⲥⲱⲧⲙ" norm="ⲥⲱⲧⲙ">ⲥⲱⲧⲙ</seg></norm></norm_group>
<norm_group><norm pos="PTC" lemma="ⲛϭⲓ" norm="ⲛϭⲓ"><seg n="t-1~1">ⲛϭⲓ</norm></norm_group>
<norm_group><norm pos="ART" lemma="ⲡ" norm="ⲡ">ⲡ</norm><norm pos="N" lemma="ⲣⲱⲙⲉ" norm="ⲣⲱⲙⲉ">ⲣⲱⲙ</norm>
<norm pos="ACOND_PPERS" lemma="x" norm="ⲉ">ⲉ</seg></norm></norm_group>
"""


# --sentences s 用: MINI_TEI に 2 つ目の <s> を足したもの
TWO_TEI = MINI_TEI.replace("      </ab>", """        <s xml:id="t-2" n="2">
          <w>ⲁⲩⲱ</w>
        </s>
      </ab>""")

# TWO_TEI を --sentences s で送ったときの NLP の答え（構文解析つき）。各 <s> の最後に足した「·」は PUNCT の 1 語に
# なり、次の <s> の最初の語に new_sent が付く。broken=True なら、1 つ目の「·」が PUNCT にならず、NLP が文を切らなかった場合
def two_sgml(broken=False):
    eos1 = '<norm xml:id="u7" pos="N" lemma="·" func="conj" head="#u3" norm="·">' if broken else \
        '<norm xml:id="u7" pos="PUNCT" lemma="·" func="punct" norm="·">'
    second = '<norm xml:id="u8" pos="CONJ" lemma="ⲁⲩⲱ" func="cc" head="#u3" norm="ⲁⲩⲱ">' if broken else \
        '<norm xml:id="u8" pos="CONJ" lemma="ⲁⲩⲱ" func="root" new_sent="true" norm="ⲁⲩⲱ">'
    return """<norm_group><norm xml:id="u1" pos="APST" lemma="ⲁ" func="aux" head="#u3" new_sent="true" norm="ⲁ"><seg n="t-1~0">ⲁ</norm>
<norm xml:id="u2" pos="PPERS" lemma="ⲛⲧⲟϥ" func="nsubj" head="#u3" norm="ϥ">ϥ</norm><norm xml:id="u3" pos="V" lemma="ⲥⲱⲧⲙ" func="root" norm="ⲥⲱⲧⲙ">ⲥⲱⲧⲙ</seg></norm></norm_group>
<norm_group><norm xml:id="u4" pos="PTC" lemma="ⲛϭⲓ" func="mark" head="#u6" norm="ⲛϭⲓ"><seg n="t-1~1">ⲛϭⲓ</norm></norm_group>
<norm_group><norm xml:id="u5" pos="ART" lemma="ⲡ" func="det" head="#u6" norm="ⲡ">ⲡ</norm><norm xml:id="u6" pos="N" lemma="ⲣⲱⲙⲉ" func="nsubj" head="#u3" norm="ⲣⲱⲙⲉ">ⲣⲱⲙⲉ</norm></norm_group>
<norm_group>%s·</seg></norm></norm_group>
<norm_group>%s<seg n="t-2~0">ⲁⲩⲱ</norm></norm_group>
<norm_group><norm xml:id="u9" pos="PUNCT" lemma="·" func="punct" norm="·">·</seg></norm></norm_group>
""" % (eos1, second)


# 1 つ目の「·」を、NLP の語群の推定が次の <s> の最初の語 ⲁⲩⲱ とつないで 1 つの形態素（PUNCT）にした場合
# （2026-11-24 に I,3 で 1 度起きた形）。NLP はその後ろ（ⲡⲉ の前）で文を切っている
TWO_TEI_PE = TWO_TEI.replace("<w>ⲁⲩⲱ</w>", "<w>ⲁⲩⲱ</w>\n          <w>ⲡⲉ</w>")
TWO_SGML_MERGED = """<norm_group><norm xml:id="u1" pos="APST" lemma="ⲁ" func="aux" head="#u3" new_sent="true" norm="ⲁ"><seg n="t-1~0">ⲁ</norm>
<norm xml:id="u2" pos="PPERS" lemma="ⲛⲧⲟϥ" func="nsubj" head="#u3" norm="ϥ">ϥ</norm><norm xml:id="u3" pos="V" lemma="ⲥⲱⲧⲙ" func="root" norm="ⲥⲱⲧⲙ">ⲥⲱⲧⲙ</seg></norm></norm_group>
<norm_group><norm xml:id="u4" pos="PTC" lemma="ⲛϭⲓ" func="mark" head="#u6" norm="ⲛϭⲓ"><seg n="t-1~1">ⲛϭⲓ</norm></norm_group>
<norm_group><norm xml:id="u5" pos="ART" lemma="ⲡ" func="det" head="#u6" norm="ⲡ">ⲡ</norm><norm xml:id="u6" pos="N" lemma="ⲣⲱⲙⲉ" func="nsubj" head="#u3" norm="ⲣⲱⲙⲉ">ⲣⲱⲙⲉ</norm></norm_group>
<norm_group><norm xml:id="u7" pos="PUNCT" lemma="·ⲁⲩⲱ" func="punct" norm="·ⲁⲩⲱ">·</seg><seg n="t-2~0">ⲁⲩⲱ</norm></norm_group>
<norm_group><norm xml:id="u8" pos="COP" lemma="ⲡⲉ" func="root" new_sent="true" norm="ⲡⲉ">ⲡⲉ</norm></norm_group>
<norm_group><norm xml:id="u9" pos="PUNCT" lemma="·" func="punct" norm="·">·</seg></norm></norm_group>
"""


# NLP が <gap> をまたいで 1 つの形態素（ⲥⲱⲧⲙ）と推定した場合。TEI では <gap> の両側の「ⲥⲱ」「ⲧⲙ」に分かれる。
# その形態素が文の最初の語で、構文の根（root）でもある形（2026-11-25 に VIII,1・IX,1・XI,4 などで起きた）
TWO_TEI_GAP = TWO_TEI.replace("<w>ⲁⲩⲱ</w>", """<w>ⲥⲱ</w>
          <gap reason="lost" quantity="2" unit="character"/>
          <w>ⲧⲙ</w>
          <w>ⲡⲉ</w>""")
TWO_SGML_GAP = two_sgml().split('<norm_group><norm xml:id="u8"')[0] + \
    """<norm_group><norm xml:id="u8" pos="V" lemma="ⲥⲱⲧⲙ" func="root" new_sent="true" norm="ⲥⲱⲧⲙ"><seg n="t-2~0">ⲥⲱ</seg><seg n="t-2~1">ⲧⲙ</norm></norm_group>
<norm_group><norm xml:id="u9" pos="COP" lemma="ⲡⲉ" func="cop" head="#u8" norm="ⲡⲉ">ⲡⲉ</norm></norm_group>
<norm_group><norm xml:id="u10" pos="PUNCT" lemma="·" func="punct" head="#u8" norm="·">·</seg></norm></norm_group>
"""


def conllu_sentences(text):
    """CoNLL-U の文ごとの (注記の dict, 語の行の列のリスト)。"""
    out = []
    for block in text.strip().split("\n\n"):
        meta, rows = {}, []
        for line in block.split("\n"):
            if line.startswith("# ") and " = " in line:
                k, v = line[2:].split(" = ", 1)
                meta[k] = v
            elif line and not line.startswith("#"):
                rows.append(line.split("\t"))
        if rows:
            out.append((meta, rows))
    return out


class LeidenTest(unittest.TestCase):
    def convert(self):
        with open(os.path.join(FIX, "leiden_sample.txt"), encoding="utf-8") as f:
            return leiden.render(leiden.convert(f.readlines(), "test"))

    def test_sigla(self):
        out = self.convert()
        for expected in (
                '<supplied reason="lost">ⲛⲁ</supplied>',
                '<supplied reason="lost" cert="low">ⲛⲟⲩ</supplied>',
                '<unclear>ⲙⲡ</unclear>',
                '<expan><abbr>ⲡⲛ</abbr><ex>ⲉⲩⲙ</ex><abbr>ⲁ</abbr></expan>',
                '<gap reason="lost" quantity="3" unit="character"/>',
                '<gap reason="lost" quantity="4" unit="character" precision="low"/>',
                '<gap reason="illegible" quantity="2" unit="character"/>',
                '<gap reason="lost" extent="unknown" unit="character"/>',
                '<del rend="erasure">ⲁⲃ</del>', '<surplus>ⲉ</surplus>', '<supplied reason="omitted">ⲛ</supplied>',
                '<add place="above">ⲡⲉ</add>', '<w>ⲡⲉⲩⲁⲅⲅⲉ<lb n="28" break="no"/>ⲗⲓⲟⲛ</w>', '<pb n="51"/>'):
            self.assertIn(expected, out)
        ET.fromstring('<x xmlns="http://www.tei-c.org/ns/1.0">%s</x>' % out)   # 整形式

    def test_unclosed_bracket(self):
        with self.assertRaises(leiden.LeidenError) as cm:
            leiden.convert(["1 ⲁⲃ[ⲅ\n"])
        self.assertIn("1 行", str(cm.exception))


class NlpParseTest(unittest.TestCase):
    def test_real_output(self):
        toks, warn = nlp.parse_sgml(read(os.path.join(FIX, "coptic_nlp_rep2.tt")))
        by = {}
        for t in toks:
            by.setdefault(t.chunk, []).append(t)
        self.assertEqual(sorted(by), ["VI-7508048~0", "VI-7508049~0"])
        self.assertEqual("".join(t.text for t in by["VI-7508048~0"]), "ⲉⲡⲓⲇⲏⲁⲛⲟⲛⲁⲛϣⲱⲡⲉⲛⲟⲩⲗⲟⲅⲟⲥⲙⲡⲓⲙⲁ")
        self.assertEqual(by["VI-7508049~0"][0].text, "ⲙⲁⲣ")     # <seg> が <norm> の中で替わる
        self.assertFalse(warn)

    def test_site_style(self):
        t = nlp.Token({"pos": "PPERO", "lemma": "ⲛⲧⲟⲟⲩ", "norm": "ⲟⲩ"}, 1)
        t.text = "ⲟⲩ"
        from collections import Counter
        items = dict(nlp.token_attrs(t, "site", {}, True, Counter()))
        self.assertEqual((items["type"], items["lemma"], items["cert"]), ("PPER", "ⲟⲩ", "medium"))
        items = dict(nlp.token_attrs(t, "cs", {}, True, Counter()))
        self.assertEqual((items["type"], items["lemma"]), ("PPERO", "ⲛⲧⲟⲟⲩ"))


class NlpRoundTripTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            src, tt, out = (os.path.join(d, n) for n in ("in.xml", "in.tt", "out.xml"))
            write(src, MINI_TEI)
            write(tt, MINI_SGML)
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", out, "--today", "2026-11-23")
            self.assertEqual(r.returncode, 0, r.stdout)
            root = ET.parse(out).getroot()
            s = root.find(".//" + T + "s")
            self.assertEqual("".join("".join(s.itertext()).split()), "ⲁϥⲥⲱⲧⲙⲛϭⲓⲡⲣⲱⲙⲉ")
            phrs = s.findall(T + "phr")
            self.assertEqual(len(phrs), 3)
            self.assertEqual([c.tag.split("}")[1] for c in s], ["lb", "phr", "gap", "phr", "phr"])
            ws = list(s.iter(T + "w"))
            self.assertEqual([w.get("type") for w in ws], ["APST", "PPER", "V", "PTC", "ART", "N", "X"])
            self.assertEqual(ws[2].find(T + "lb").get("break"), "no")
            # <supplied> は「ⲙ」「ⲉ」の 2 つの <w> に分かれる
            self.assertEqual(["".join(e.itertext()) for e in s.iter(T + "supplied")], ["ⲙ", "ⲉ"])
            self.assertEqual(ws[-1].get("cert"), "low")
            self.assertIsNotNone(root.find(".//" + T + "respStmt[@{http://www.w3.org/XML/1998/namespace}id='coptic-nlp']"))
            self.assertEqual(len(root.findall(".//" + T + "change")), 2)

    def test_keep_resp(self):
        """--keep-resp: 人の注釈を写した <s> は NLP に送らず、そのまま残す。"""
        two = MINI_TEI.replace("      </ab>", """        <s xml:id="t-2" n="2">
          <phr><w type="N" lemma="ⲣⲱⲙⲉ" resp="#ref">ⲣⲱⲙⲉ</w></phr>
        </s>
      </ab>""")
        with tempfile.TemporaryDirectory() as d:
            src, tt, out = (os.path.join(d, n) for n in ("in.xml", "in.tt", "out.xml"))
            req1, req2 = os.path.join(d, "r1.txt"), os.path.join(d, "r2.txt")
            write(src, two)
            write(tt, MINI_SGML)
            run("coptic_nlp_tei.py", src, "--export-request", req1)
            run("coptic_nlp_tei.py", src, "--export-request", req2, "--keep-resp", "ref")
            self.assertIn("t-2~0", read(req1))
            self.assertNotIn("t-2~0", read(req2))
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", out, "--keep-resp", "#ref", "--today", "2026-11-24")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("そのまま残した", r.stdout)
            new = read(out)
            self.assertIn('<phr><w type="N" lemma="ⲣⲱⲙⲉ" resp="#ref">ⲣⲱⲙⲉ</w></phr>', new)
            self.assertIn("of 1 segments", new)

    def test_cache_dir(self):
        """--cache-dir: 保存した出力があれば送らない（届かない URL でも動く）。"""
        with tempfile.TemporaryDirectory() as d:
            src, out, cache = os.path.join(d, "in.xml"), os.path.join(d, "out.xml"), os.path.join(d, "cache")
            write(src, MINI_TEI)
            seg = nlp.read_segment(ET.fromstring(MINI_TEI.encode("utf-8")).find(".//" + T + "s"))
            data = nlp.batches(nlp.build_request([seg], "auto"), 15000)[0]
            url = "http://127.0.0.1:9/coptic-nlp/"
            os.makedirs(cache)
            write(os.path.join(cache, "in.%s.tt" % nlp.cache_key("form", url, "smart", False, data)), MINI_SGML)
            r = run("coptic_nlp_tei.py", src, "--url", url, "--cache-dir", cache, "--out", out,
                    "--retries", "0", "--timeout", "2")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("保存した出力を使います", r.stdout)
            self.assertEqual(len(ET.parse(out).getroot().findall(".//" + T + "phr")), 3)
            # 保存が無ければ送ろうとして失敗し、書き出さない
            r = run("coptic_nlp_tei.py", src, "--url", url, "--out", os.path.join(d, "out2.xml"),
                    "--retries", "0", "--timeout", "2")
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(os.path.exists(os.path.join(d, "out2.xml")))

    def test_sentences_request(self):
        """--sentences s: 各 <s> の最後の chunk に「·」を足し、1 つの <s> の chunk は同じ回に送る。"""
        segs = [nlp.read_segment(s) for s in ET.fromstring(TWO_TEI.encode("utf-8")).iter(T + "s")]
        req = nlp.build_request(segs, "auto", "s")
        self.assertEqual(req, [("t-1~0", "ⲁ ϥ ⲥⲱⲧⲙ"), ("t-1~1", "ⲛϭⲓ ⲡ ⲣⲱⲙⲉ ·"), ("t-2~0", "ⲁⲩⲱ ·")])
        parts = nlp.batches(req, 10, "s")       # 上限を小さくしても <s> の途中では分けない
        self.assertEqual(parts, ['<seg n="t-1~0"> ⲁ ϥ ⲥⲱⲧⲙ </seg>\n<seg n="t-1~1"> ⲛϭⲓ ⲡ ⲣⲱⲙⲉ · </seg>\n',
                                 '<seg n="t-2~0"> ⲁⲩⲱ · </seg>\n'])
        # 既定（nlp）は chunk ごとに分け、文の終わりの印を足さない（前と同じ）
        default = nlp.batches(nlp.build_request(segs, "auto"), 10)
        self.assertEqual(default, ['<seg n="t-1~0"> ⲁ ϥ ⲥⲱⲧⲙ </seg>\n', '<seg n="t-1~1"> ⲛϭⲓ ⲡ ⲣⲱⲙⲉ </seg>\n',
                                   '<seg n="t-2~0"> ⲁⲩⲱ </seg>\n'])

    def test_sentences_roundtrip(self):
        """--sentences s: 足した「·」は TEI にも CoNLL-U にも残らず、CoNLL-U の文は <s> と 1 対 1 になる。"""
        with tempfile.TemporaryDirectory() as d:
            src, tt, out, cu = (os.path.join(d, n) for n in ("in.xml", "in.tt", "out.xml", "out.conllu"))
            write(src, TWO_TEI)
            write(tt, two_sgml())
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", out, "--conllu", cu, "--sentences", "s",
                    "--today", "2026-11-24")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("注意", r.stdout)
            self.assertIn("（2 文）", r.stdout)
            new = read(out)
            self.assertNotIn("·", new)
            self.assertIn("sentences=s", new)        # <change> に送り方を書く
            s1, s2 = ET.parse(out).getroot().iter(T + "s")
            self.assertEqual([w.get("type") for w in s1.iter(T + "w")], ["APST", "PPER", "V", "PTC", "ART", "N"])
            self.assertEqual([w.get("type") for w in s2.iter(T + "w")], ["CONJ"])
            text = read(cu)
            self.assertNotIn("·", text)
            sents = conllu_sentences(text)
            self.assertEqual([m["tei_s"] for m, _ in sents], ["t-1", "t-2"])
            self.assertEqual(sents[0][0]["text"], "ⲁϥⲥⲱⲧⲙ ⲛϭⲓ ⲡⲣⲱⲙⲉ")
            words = [row for row in sents[0][1] if "-" not in row[0]]
            self.assertEqual([(row[1], row[6], row[7]) for row in words],
                             [("ⲁ", "3", "aux"), ("ϥ", "3", "nsubj"), ("ⲥⲱⲧⲙ", "0", "root"),
                              ("ⲛϭⲓ", "6", "mark"), ("ⲡ", "6", "det"), ("ⲣⲱⲙⲉ", "3", "nsubj")])
            self.assertEqual([(row[1], row[6], row[7], row[9]) for row in sents[1][1]],
                             [("ⲁⲩⲱ", "0", "root", "TEI=t-2")])

    def test_sentences_not_split(self):
        """NLP が <s> の境目で文を切らなかったら知らせる。CoNLL-U はそれでも <s> の境目で切り、
        境目をまたぐ係り先は 0 にする。"""
        with tempfile.TemporaryDirectory() as d:
            src, tt, out, cu = (os.path.join(d, n) for n in ("in.xml", "in.tt", "out.xml", "out.conllu"))
            write(src, TWO_TEI)
            write(tt, two_sgml(broken=True))
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", out, "--conllu", cu, "--sentences", "s")
            self.assertEqual(r.returncode, 0, r.stdout)
            for kind in ("文の終わりの印（·）が PUNCT にならなかった <s>: 1", "NLP がその前で文を切らなかった <s>: 1",
                         "係り先が同じ文に無いので 0 にした語: 1"):
                self.assertIn(kind, r.stdout)
            sents = conllu_sentences(read(cu))
            self.assertEqual([m["tei_s"] for m, _ in sents], ["t-1", "t-2"])
            self.assertEqual([(row[1], row[6], row[7]) for row in sents[1][1]], [("ⲁⲩⲱ", "0", "dep")])

    def test_sentences_mark_merged(self):
        """「·」が次の <s> の最初の語とつながったら、その語の解析は使わず（X）、「·」は残さず、文は <s> で切る。"""
        with tempfile.TemporaryDirectory() as d:
            src, tt, out, cu = (os.path.join(d, n) for n in ("in.xml", "in.tt", "out.xml", "out.conllu"))
            write(src, TWO_TEI_PE)
            write(tt, TWO_SGML_MERGED)
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", out, "--conllu", cu, "--sentences", "s")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("文の終わりの印（·）が次の <s> の最初の語とつながった <s>: 1", r.stdout)
            self.assertNotIn("文を切らなかった", r.stdout)
            self.assertNotIn("文字が対応しない", r.stdout)
            new = read(out)
            self.assertNotIn("·", new)
            s1, s2 = ET.parse(out).getroot().iter(T + "s")
            self.assertEqual([w.get("type") for w in s1.iter(T + "w")], ["APST", "PPER", "V", "PTC", "ART", "N"])
            w = list(s2.iter(T + "w"))
            self.assertEqual([(x.get("type"), x.get("lemma"), x.get("cert")) for x in w],
                             [("X", None, "low"), ("COP", "ⲡⲉ", "medium")])
            text = read(cu)
            self.assertNotIn("·", text)
            sents = conllu_sentences(text)
            self.assertEqual([m["tei_s"] for m, _ in sents], ["t-1", "t-2"])    # ⲡⲉ の前では切らない
            self.assertEqual([row[1:8] + [row[9]] for row in sents[1][1]],
                             [["ⲁⲩⲱ", "_", "X", "UNKNOWN", "_", "0", "dep", "TEI=t-2"],
                              ["ⲡⲉ", "ⲡⲉ", "PRON", "COP", "_", "0", "root", "TEI=t-2"]])

    def test_conllu_gap_split(self):
        """<gap> の位置で分けた形態素の 2 つ目の片では文を切らず、最初の片に goeswith で係らせる（root を 2 つにしない）。"""
        with tempfile.TemporaryDirectory() as d:
            src, tt, out, cu = (os.path.join(d, n) for n in ("in.xml", "in.tt", "out.xml", "out.conllu"))
            write(src, TWO_TEI_GAP)
            write(tt, TWO_SGML_GAP)
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", out, "--conllu", cu, "--sentences", "s")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("<s> か <gap> の境目をまたいだので分けた形態素: 1", r.stdout)
            self.assertNotIn("文を切らなかった", r.stdout)
            self.assertIn("（2 文）", r.stdout)
            s2 = list(ET.parse(out).getroot().iter(T + "s"))[1]
            self.assertEqual([(w.text, w.get("type"), w.get("cert")) for w in s2.iter(T + "w")],
                             [("ⲥⲱ", "V", "low"), ("ⲧⲙ", "V", "low"), ("ⲡⲉ", "COP", "medium")])
            sents = conllu_sentences(read(cu))
            self.assertEqual([m["tei_s"] for m, _ in sents], ["t-1", "t-2"])
            self.assertEqual(sents[1][0]["text"], "ⲥⲱ ⲧⲙ ⲡⲉ")
            self.assertEqual([row[1:8] + [row[9]] for row in sents[1][1]],
                             [["ⲥⲱ", "ⲥⲱⲧⲙ", "VERB", "V", "_", "0", "root", "TEI=t-2|Norm=ⲥⲱⲧⲙ"],
                              ["ⲧⲙ", "_", "X", "_", "_", "1", "goeswith", "TEI=t-2"],
                              ["ⲡⲉ", "ⲡⲉ", "PRON", "COP", "_", "1", "cop", "TEI=t-2"]])

    def test_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            src, tt = os.path.join(d, "in.xml"), os.path.join(d, "in.tt")
            write(src, MINI_TEI)
            write(tt, MINI_SGML)
            r = run("coptic_nlp_tei.py", src, "--sgml", tt, "--out", src)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(read(src), MINI_TEI)


class CheckSpecTest(unittest.TestCase):
    def test_finds_problems(self):
        bad = MINI_TEI.replace('<w>ϥ</w>', '<w type="CFOS">ϥ</w>') \
                      .replace('<w>ⲛϭⲓ</w>', '<w type="PTC" xml:lang="Greek" resp="#nobody">ⲛϭⲓ</w>') \
                      .replace('quantity="3"', 'extent="3"')
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.xml")
            write(path, bad)
            r = run("check_spec.py", path)
        self.assertEqual(r.returncode, 1, r.stdout)
        for kind in ("品詞コードの打ち間違い", "xml:lang が BCP 47 の符号でない", "@resp の指す xml:id が無い",
                     "<gap> の extent に値"):
            self.assertIn(kind, r.stdout)


if __name__ == "__main__":
    unittest.main()
