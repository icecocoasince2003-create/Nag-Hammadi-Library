#!/usr/bin/env python3
"""scripts/reanchor_proposals.py の試験（語の区切りを付け直したあとに、提案の表の w・phr を文字の位置で合わせ直す）。

  python3 -m unittest discover -s tests -p "test_*.py"

git の履歴は使わない（CI の浅い clone でも動くように、前の版と今の版の TEI を一時フォルダに作って --old・--file で渡す）。
リポジトリのファイルは変えない。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "reanchor_proposals.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import insert_breaks as ib  # noqa: E402

DOC = "II-2"
SEG = "II-7503903_2206"


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


class Reanchor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="reanchor-test-")
        src = ib.load_catalog()[DOC]
        self.old = os.path.join(self.dir, "old.xml")
        self.new = os.path.join(self.dir, "new.xml")
        shutil.copyfile(src, self.old)
        data = open(src, "rb").read()
        seg = ib.segments(ib.parse(data))[0][SEG]
        # 今の版: 前の版の 3 番目の <w> を 2 つに分け、6 番目と 7 番目の <w> を 1 つにつなぐ（区切りの付け直しの代わり）
        self.ws = [ib.w_text(data, w) for w in seg.ws]
        text = data.decode("utf-8")
        w3, w6, w7 = (seg.ws[i] for i in (2, 5, 6))
        self.assertGreaterEqual(len(self.ws[2]), 2)
        b = data
        cut = lambda n: (n.start, n.end_end)
        s6, _ = cut(w6)
        _, e7 = cut(w7)
        tag6 = b[w6.start:w6.start_end].decode("utf-8")
        merged = (tag6 + self.ws[5] + self.ws[6] + "</w>").encode("utf-8")
        s3, e3 = cut(w3)
        tag3 = b[w3.start:w3.start_end].decode("utf-8")
        split = (tag3 + self.ws[2][:1] + "</w>" + tag3 + self.ws[2][1:] + "</w>").encode("utf-8")
        new = b[:s3] + split + b[e3:s6] + merged + b[e7:]
        with open(self.new, "wb") as f:
            f.write(new)
        self.tsv = os.path.join(self.dir, "t.tsv")
        rows = ["doc\tseg_id\tw\tphr\t備考\t状態"]
        for w in (2, 4, 7, 8):
            rows.append("%s\t%s\t%d\t%d\t\t案" % (DOC, SEG, w, seg.wphr[w - 1]))
        with open(self.tsv, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(rows) + "\n")
        self.args = ["--old", "%s=%s" % (DOC, self.old), "--file", "%s=%s" % (DOC, self.new)]

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_script(self, *extra):
        r = subprocess.run([sys.executable, SCRIPT, self.tsv] + self.args + list(extra), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def rows(self):
        lines = read(self.tsv).split("\n")
        h = lines[0].split("\t")
        return [dict(zip(h, l.split("\t"))) for l in lines[1:] if l]

    def test_positions_follow_the_letters(self):
        before = read(self.tsv)
        self.run_script()
        self.assertEqual(read(self.tsv), before, "dry run: nothing written")
        self.run_script("--write")
        new = open(self.new, "rb").read()
        seg = ib.segments(ib.parse(new))[0][SEG]
        for old_w, row in zip((2, 4, 7, 8), self.rows()):
            # 3 番目を分けたので 4 以降は 1 つ後ろ、6・7 番目をつないだので 7 は語の途中（6+1 番目の語）、8 以降は元に戻る
            want = {2: 2, 4: 5, 7: 7, 8: 8}[old_w]
            self.assertEqual(row["w"], str(want), "w=%d" % old_w)
            self.assertEqual(row["phr"], str(seg.wphr[want - 1]), "phr of w=%d" % old_w)
            if old_w == 7:
                self.assertIn("語（<w>）の途中", row["備考"])
                self.assertIn("前は w=7", row["備考"])
            elif not seg.first_in_phr(want):
                self.assertIn("語群の途中", row["備考"], "w=%d is inside a bound group now" % old_w)
            else:
                self.assertEqual(row["備考"], "", "w=%d gets no mark" % old_w)
        self.assertEqual(ib.w_text(new, seg.ws[4]), self.ws[3], "the new 5th word is the old 4th word")
        self.assertEqual(ib.w_text(new, seg.ws[7]), self.ws[7], "the new 8th word is the old 8th word")

    def test_a_second_run_changes_nothing(self):
        self.run_script("--write")
        once = read(self.tsv)
        self.args = ["--old", "%s=%s" % (DOC, self.new), "--file", "%s=%s" % (DOC, self.new)]
        self.assertIn("変更なし", self.run_script("--write"))
        self.assertEqual(read(self.tsv), once)

if __name__ == "__main__":
    unittest.main()
