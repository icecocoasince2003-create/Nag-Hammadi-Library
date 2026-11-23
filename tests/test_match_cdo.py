#!/usr/bin/env python3
"""scripts/match_cdo.py の試験（辞書の見出しを CCL と突き合わせる・承認した TLA 番号を lexicon.csv の cdo 列に入れる）。

  python3 -m unittest discover -s tests -p "test_*.py"

本物の CCL は使わない（リポジトリに入れないため）。小さな CCL・lexicon.xml・lexicon.csv を一時フォルダに作って試す。
リポジトリのファイルは変えない。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "match_cdo.py")

CCL = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader><fileDesc><publicationStmt><idno type="edition">v1.2</idno><idno type="DOI">10.0/test</idno></publicationStmt></fileDesc></teiHeader>
<text><body>
<entry xml:id="C10"><form type="lemma"><orth>ⲁⲗⲟⲩ</orth></form><gramGrp><pos>Subst.</pos></gramGrp><sense><cit type="translation"><quote>SENSE-FROM-CCL</quote></cit></sense></entry>
<entry xml:id="C20"><form type="lemma"><orth>ⲙⲟⲩ</orth></form><gramGrp><pos>Vb.</pos></gramGrp></entry>
<entry xml:id="C21"><form type="lemma"><orth>ⲙⲟⲩ</orth></form><gramGrp><pos>Subst.</pos></gramGrp></entry>
<entry xml:id="C30"><form type="lemma"><orth>ϩⲉ</orth></form><gramGrp><pos>Subst.</pos></gramGrp></entry>
<entry xml:id="C31"><form type="lemma"><orth>ϩⲉ-</orth></form><gramGrp><pos>Subst.</pos></gramGrp></entry>
<entry xml:id="C40"><form type="lemma"><orth>ⲡⲛⲉⲩⲙⲁ</orth></form><form type="inflected"><orth>ⲡⲛⲁ</orth></form><gramGrp><pos>Subst.</pos></gramGrp></entry>
<entry xml:id="C50"><form type="lemma"><orth>ⲟⲩⲛⲧⲉ-</orth></form><gramGrp><pos>Vb.</pos></gramGrp></entry>
<entry xml:id="C60"><form type="lemma"><orth>ⲣⲁⲛ</orth></form><gramGrp><pos>Subst.</pos></gramGrp></entry>
</body></text></TEI>
"""

LEXICON = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
<entry xml:id="lex-0001"><form><orth>ⲁⲗⲟⲩ</orth></form><gramGrp><pos>N</pos></gramGrp></entry>
<entry xml:id="lex-0002"><form><orth>ⲙⲟⲩ</orth></form><gramGrp><pos>V</pos></gramGrp></entry>
<entry xml:id="lex-0003"><form><orth>ϩⲉ</orth></form><gramGrp><pos>N</pos></gramGrp></entry>
<entry xml:id="lex-0004"><form><orth>ⲡⲛⲁ</orth></form><gramGrp><pos>N</pos></gramGrp></entry>
<entry xml:id="lex-0005"><form><orth>ⲭⲩⲍ</orth></form><gramGrp><pos>N</pos></gramGrp></entry>
<entry xml:id="lex-0006"><form><orth>ⲟⲩⲛⲧⲉ</orth></form><gramGrp><pos>EXIST</pos></gramGrp></entry>
<entry xml:id="lex-0007"><form><orth>[..]ⲁⲩ</orth></form></entry>
<entry xml:id="lex-0008"><form><orth>ⲣⲁⲛ</orth></form><gramGrp><pos>V</pos></gramGrp></entry>
</body></text></TEI>
"""

# BOM あり・引用符とコンマのあるセル・cdo の空セルを省いた行（ⲣⲁⲛ）・最後の改行なし
CSV = ("﻿lemma,n,pos,grc,en,ja,fr,usg_ja,usg_en,cdo\n"
       'ⲁⲗⲟⲩ,1,N,,"child, boy",子,enfant,,,\n'
       "ⲙⲟⲩ,1,V,,die,死ぬ,mourir,,,\n"
       "ϩⲉ,1,N,,manner,様,manière,,,\n"
       "ⲡⲛⲁ,1,N,,spirit,霊,esprit,,,\n"
       "ⲭⲩⲍ,1,N,,,,,,,\n"
       "ⲟⲩⲛⲧⲉ,1,EXIST,,have,持つ,avoir,,,C49\n"
       "[..]ⲁⲩ,1,,,,,,,,\n"
       "ⲣⲁⲛ,1,V,,name,名,nom,,")


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write(p, text):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


class MatchCdo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="cdo-test-")
        self.ccl, self.lex, self.csv, self.tsv = (os.path.join(self.dir, n) for n in ("ccl.xml", "lexicon.xml", "lexicon.csv", "m.tsv"))
        write(self.ccl, CCL)
        write(self.lex, LEXICON)
        write(self.csv, CSV)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_script(self, *args):
        r = subprocess.run([sys.executable, "-I", SCRIPT] + list(args), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def match(self):
        return self.run_script(self.ccl, "--lexicon", self.lex, "--csv", self.csv, "--out", self.tsv)

    def apply(self, *extra):
        return self.run_script("apply", self.tsv, "--lexicon", self.lex, "--csv", self.csv, *extra)

    def rows(self):
        lines = read(self.tsv).split("\n")
        h = lines[0].split("\t")
        return h, {l.split("\t")[0]: dict(zip(h, l.split("\t"))) for l in lines[1:] if l}

    def edit(self, changes):
        """changes: {xml:id: {列: 値}} を TSV に書く（確認作業の画面の書き出しと同じく、セルだけを変える）"""
        lines = read(self.tsv).split("\n")
        h = lines[0].split("\t")
        for i, l in enumerate(lines[1:], 1):
            c = l.split("\t")
            if l and c[0] in changes:
                for k, v in changes[c[0]].items():
                    c[h.index(k)] = v
                lines[i] = "\t".join(c)
        write(self.tsv, "\n".join(lines))

    def test_how_each_headword_is_matched(self):
        out = self.match()
        h, r = self.rows()
        self.assertEqual(h, ["xml:id", "見出し", "品詞", "TLA番号の候補", "CCLの見出し", "CCLの品詞", "決まり方", "品詞の対応",
                             "既存のcdo", "メモ", "選んだTLA番号", "状態", "確認者"])
        got = {k: (v["TLA番号の候補"], v["決まり方"], v["品詞の対応"]) for k, v in r.items()}
        self.assertEqual(got, {
            "lex-0001": ("C10", "綴りで一意", "一致"),
            "lex-0002": ("C20", "品詞で絞った", "一致"),
            "lex-0003": ("C30 | C31", "候補が複数", "一致 | 一致"),
            "lex-0004": ("C40", "変化形", "一致"),
            "lex-0006": ("C50", "綴りで一意", "一致"),
            "lex-0008": ("C60", "綴りで一意", "矛盾"),
        })
        self.assertEqual(r["lex-0006"]["既存のcdo"], "C49")
        self.assertIn("C49", r["lex-0006"]["メモ"])
        self.assertEqual({v["状態"] for v in r.values()}, {"案（生田目の確認待ち）"})
        self.assertNotIn("SENSE-FROM-CCL", read(self.tsv), "no sense is copied from the CCL")
        self.assertIn("lex-0007", out)        # 欠損の記号のある見出しは除いたと報告する
        before = read(self.tsv)
        self.match()
        self.assertEqual(read(self.tsv), before, "the same input gives the same bytes")

    def test_decisions_survive_a_rerun_unless_the_candidates_change(self):
        self.match()
        self.edit({"lex-0003": {"選んだTLA番号": "C31", "状態": "承認", "確認者": "T"}, "lex-0001": {"状態": "却下", "確認者": "T"}})
        decided = read(self.tsv)
        out = self.match()
        self.assertEqual(read(self.tsv), decided)
        self.assertIn("引き継いだもの 2・引き継げなかったもの 0", out)
        write(self.ccl, CCL.replace('<entry xml:id="C40">', '<entry xml:id="C32"><form type="lemma"><orth>ϩⲉ</orth></form><gramGrp><pos>Subst.</pos></gramGrp></entry>\n<entry xml:id="C40">'))
        out = self.match()
        h, r = self.rows()
        self.assertEqual(r["lex-0003"]["TLA番号の候補"], "C30 | C31 | C32")
        self.assertEqual((r["lex-0003"]["選んだTLA番号"], r["lex-0003"]["状態"]), ("", "案（生田目の確認待ち）"))
        self.assertEqual(r["lex-0001"]["状態"], "却下")
        self.assertIn("lex-0003（前の候補 C30 | C31）", out)

    def test_apply_writes_only_approved_numbers_and_only_the_cdo_cells(self):
        self.match()
        self.edit({"lex-0003": {"状態": "承認"}})                                   # 選ばずに承認: 入れない
        self.assertIn("TLA 番号が 1 つに決まっていない", self.apply())
        self.edit({"lex-0003": {"選んだTLA番号": "C31", "状態": "承認", "確認者": "T"},
                   "lex-0008": {"状態": "承認"}})
        out = self.apply()
        self.assertIn("書き込む: 2 件", out)
        self.assertEqual(read(self.csv), CSV, "dry run: nothing written")
        self.apply("--write")
        want = CSV.replace("ϩⲉ,1,N,,manner,様,manière,,,", "ϩⲉ,1,N,,manner,様,manière,,,C31").replace("ⲣⲁⲛ,1,V,,name,名,nom,,", "ⲣⲁⲛ,1,V,,name,名,nom,,,C60")
        self.assertEqual(read(self.csv), want)

    def test_bulk_unique_takes_agreeing_unique_rows_but_keeps_existing_numbers_and_rejections(self):
        self.match()
        out = self.apply("--bulk-unique", "--write")
        self.assertIn("lex-0001", out)
        self.assertIn("既存 C49・TSV C50", out)                  # 既存の別の番号は書き換えずに報告
        csv = read(self.csv)
        self.assertIn('ⲁⲗⲟⲩ,1,N,,"child, boy",子,enfant,,,C10', csv)
        for line in ("ⲙⲟⲩ,1,V,,die,死ぬ,mourir,,,\n", "ⲡⲛⲁ,1,N,,spirit,霊,esprit,,,\n", "ⲟⲩⲛⲧⲉ,1,EXIST,,have,持つ,avoir,,,C49\n"):
            self.assertIn(line, csv)                               # 品詞で絞った・変化形・既存の番号はそのまま
        self.assertTrue(csv.endswith("ⲣⲁⲛ,1,V,,name,名,nom,,"), "a unique row whose part of speech conflicts is not taken")
        write(self.csv, CSV)
        self.edit({"lex-0001": {"状態": "却下"}})
        self.assertIn("変更なし", self.apply("--bulk-unique"))

    def test_a_ccl_file_with_a_doctype_is_refused(self):
        write(self.ccl, CCL.replace("<TEI ", '<!DOCTYPE TEI [<!ENTITY x "y">]>\n<TEI ', 1))
        r = subprocess.run([sys.executable, "-I", SCRIPT, self.ccl, "--lexicon", self.lex, "--csv", self.csv, "--out", self.tsv],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.tsv))


if __name__ == "__main__":
    unittest.main()
