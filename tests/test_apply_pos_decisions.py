#!/usr/bin/env python3
"""scripts/apply_pos_decisions.py の試験（品詞をそろえる判断表のうち、承認した行だけを当てはめる）。

  python3 -m unittest discover -s tests -p "test_*.py"

リポジトリのファイルは変えない（data/ の 2 ファイルと暫定版の III,3 の写しを一時フォルダに作って試す）。
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "apply_pos_decisions.py")
TABLE = os.path.join(ROOT, "source", "nhc_fulltext_split", "proposals", "pos_harmonization.tsv")
T = "{http://www.tei-c.org/ns/1.0}"


def run(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


class ApplyPosDecisions(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="pos-test-")
        os.mkdir(os.path.join(self.dir, "drafts"))
        self.files = {"eugnostos": os.path.join(self.dir, "eugnostos_tei.xml"), "republic": os.path.join(self.dir, "republic_tei.xml"),
                      "III-3": os.path.join(self.dir, "drafts", "03-3_eugnostos.xml")}
        shutil.copyfile(os.path.join(ROOT, "data", "eugnostos_tei.xml"), self.files["eugnostos"])
        shutil.copyfile(os.path.join(ROOT, "data", "republic_tei.xml"), self.files["republic"])
        shutil.copyfile(os.path.join(ROOT, "source", "nhc_fulltext_split", "tei", "03-3_eugnostos.xml"), self.files["III-3"])
        self.args = []
        for k, p in self.files.items():
            self.args += ["--file", "%s=%s" % (k, p)]
        self.args += ["--drafts", os.path.join(self.dir, "drafts")]

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def table(self, approve):
        """approve(行の辞書) が真の行の状態を「承認」にした判断表の写し"""
        lines = read(TABLE).split("\n")
        h = lines[0].split("\t")
        out = [lines[0]]
        for l in lines[1:]:
            if l:
                c = l.split("\t")
                if approve(dict(zip(h, c))):
                    c[h.index("状態")] = "承認"
                l = "\t".join(c)
            out.append(l)
        p = os.path.join(self.dir, "table.tsv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(out))
        return p

    def test_the_table_as_committed_changes_nothing(self):
        r = run(*self.args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("変えるものはありません", r.stdout)
        r = run(*(self.args + ["--write"]))
        self.assertEqual(read(self.files["eugnostos"]), read(os.path.join(ROOT, "data", "eugnostos_tei.xml")))

    def test_only_approved_rows_are_applied_and_a_second_run_changes_nothing(self):
        p = self.table(lambda r: r["語形"] in ("ⲉⲧ", "ⲧⲏⲣ"))
        r = run(p, *(self.args + ["--write"]))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        e = ET.parse(self.files["eugnostos"]).getroot()
        tags = [w.get("type") for t in e.iter(T + "text") if t.get("{http://www.w3.org/XML/1998/namespace}id") == "wit-III"
                for w in t.iter(T + "w") if "".join(w.itertext()).strip() == "ⲉⲧ"]
        self.assertNotIn("REL", tags)
        self.assertEqual(tags.count("CREL"), 37)
        rep = ET.parse(self.files["republic"]).getroot()
        self.assertEqual([w.get("type") for w in rep.iter(T + "w") if "".join(w.itertext()).strip() == "ⲧⲏⲣ"], ["ADJ"] * 9)
        self.assertIn("ⲉⲧ ART>CREL ×1", r.stdout)
        # ほかの行（ⲛⲓⲙ など）は当てはめていない
        self.assertTrue(any(w.get("type") == "PINT" for w in rep.iter(T + "w") if "".join(w.itertext()).strip() == "ⲛⲓⲙ"))
        self.assertIn("<change when=", read(self.files["republic"]).split("</revisionDesc>")[0].split("<revisionDesc>")[1].split("\n")[1])
        r2 = run(p, *self.args)
        self.assertIn("変えるものはありません", r2.stdout)

    def test_all_rows_approved_leave_no_tag_outside_the_list(self):
        p = self.table(lambda r: True)
        r = run(p, *(self.args + ["--write"]))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(ROOT, "data", "pos_labels.json"), encoding="utf-8") as f:
            names = {t["tag"] for t in json.load(f)["tags"]}
        for path in self.files.values():
            bad = [w.get("type") for w in ET.parse(path).getroot().iter(T + "w") if w.get("type") and w.get("type") not in names]
            self.assertEqual(bad, [], path)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "check_tei.py")] + list(self.files.values()), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("変えるものはありません", run(p, *self.args).stdout)

    def test_a_place_row_that_does_not_match_the_text_stops(self):
        lines = read(TABLE).split("\n")
        h = lines[0].split("\t")
        out = [lines[0]]
        for l in lines[1:]:
            c = l.split("\t") if l else []
            if c and c[h.index("種類")] == "箇所" and c[h.index("seg_id")] == "rep-22":
                c[h.index("状態")] = "承認"
                c[h.index("w")] = "12"                    # 違う語を指す
            out.append("\t".join(c) if c else l)
        p = os.path.join(self.dir, "bad.tsv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(out))
        before = read(self.files["republic"])
        r = run(p, *(self.args + ["--write"]))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(read(self.files["republic"]), before, "nothing written")


if __name__ == "__main__":
    unittest.main()
