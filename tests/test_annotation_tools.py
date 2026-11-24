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
