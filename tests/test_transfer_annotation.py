#!/usr/bin/env python3
"""scripts/transfer_annotation.py の試験（エウグノストス III,3 の注釈を III,4 の同じ文言の語群に写す案と、承認した行の当てはめ）。

  python3 -m unittest discover -s tests -p "test_*.py"

表と III,4 の TEI は一時フォルダに作る（リポジトリのファイルは変えない）。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "transfer_annotation.py")
SJC = os.path.join(ROOT, "source", "nhc_fulltext_split", "tei", "03-4_sophia-of-jesus-christ.xml")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import insert_breaks as ib  # noqa: E402
import transfer_annotation as ta  # noqa: E402


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def run(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)


class Transfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="transfer-test-")
        cls.tsv = os.path.join(cls.dir, "t.tsv")
        r = run("--out", cls.tsv)
        assert r.returncode == 0, r.stdout + r.stderr
        lines = read(cls.tsv).split("\n")
        cls.head = lines[0].split("\t")
        cls.rows = [dict(zip(cls.head, l.split("\t"))) for l in lines[1:] if l]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_the_table_is_repeatable_and_its_rows_point_at_the_right_letters(self):
        again = os.path.join(self.dir, "again.tsv")
        self.assertEqual(run("--out", again).returncode, 0)
        self.assertEqual(read(again), read(self.tsv), "the same input gives the same bytes")
        self.assertEqual(self.head, ta.COLUMNS)
        self.assertTrue(self.rows, "some rows")
        self.assertEqual({r["状態"] for r in self.rows}, {ta.STATE_DRAFT})
        self.assertEqual([r["番号"] for r in self.rows], [str(i) for i in range(1, len(self.rows) + 1)])
        data = open(SJC, "rb").read()
        segs, _ = ib.segments(ib.parse(data))
        for r in self.rows:
            seg = segs[r["seg_id"]]
            new = ta.parse_morphs(r["写す注釈"])
            # 写す形の文字と III,4 の語群の文字が同じ
            self.assertEqual(ta.norm("".join(m["form"] for m in new)), ta.norm(r["語群"]), r["番号"])
            # 語群は、III,4 の w 番目の <w> から始まる文字（範囲が語の途中から始まるときは、その <w> の中から）
            after = ta.norm("".join(ib.w_text(data, w) for w in seg.ws[int(r["w"]) - 1:]))
            at = after.find(ta.norm(r["語群"]))
            first = len(ta.norm(ib.w_text(data, seg.ws[int(r["w"]) - 1])))
            if "セグメントをまたぐ" in r["当てはめ"]:   # 範囲の初めの部分が、このセグメントの終わり
                self.assertTrue(any(ta.norm(r["語群"]).startswith(after[k:]) for k in range(first + 1)), r["番号"])
            elif "語（<w>）の途中" in r["当てはめ"]:
                self.assertTrue(0 <= at < len(ta.norm(ib.w_text(data, seg.ws[int(r["w"]) - 1]))), r["番号"])
            else:
                self.assertEqual(at, 0, r["番号"])
            self.assertIn(r["当てはめ"].split(":")[0], ("可", "不可"))
            self.assertTrue(r["違い"], r["番号"])
        keys = [(r["seg_id"], r["w"], r["語群"]) for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)), "one row per place and letters")

    def test_only_approved_applicable_rows_are_applied_and_the_letters_stay(self):
        sjc = os.path.join(self.dir, "sjc.xml")
        shutil.copyfile(SJC, sjc)
        tsv = os.path.join(self.dir, "approved.tsv")
        ok = [r["番号"] for r in self.rows if r["当てはめ"] == "可"][:5]
        no = [r["番号"] for r in self.rows if r["当てはめ"] != "可"][:1]
        lines = read(self.tsv).split("\n")
        out = [lines[0]]
        for l in lines[1:]:
            c = l.split("\t") if l else []
            if c and c[0] in ok + no:
                c[self.head.index("状態")] = ta.STATE_OK
            out.append("\t".join(c) if c else l)
        with open(tsv, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(out))
        before = open(sjc, "rb").read()
        r = run("apply", "--tsv", tsv, "--file", sjc)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(open(sjc, "rb").read(), before, "dry run: nothing written")
        self.assertIn("当てはめる %d・飛ばした %d" % (len(ok), len(no)), r.stdout)
        r = run("apply", "--tsv", tsv, "--file", sjc, "--write", "--date", "2026-11-24")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        after = open(sjc, "rb").read()
        segs_b, _ = ib.segments(ib.parse(before))
        segs_a, _ = ib.segments(ib.parse(after))
        letters = lambda data, segs: ta.norm("".join(ib.w_text(data, w) for s in segs.values() for w in s.ws))
        self.assertEqual(letters(after, segs_a), letters(before, segs_b), "the letters are unchanged")
        text = after.decode("utf-8")
        self.assertIn('<respStmt xml:id="transfer">', text)
        self.assertIn('<change when="2026-11-24">Annotation of %d bound groups transferred' % len(ok), text)
        for n in ok:
            row = next(x for x in self.rows if x["番号"] == n)
            seg = segs_a[row["seg_id"]]
            ws = [w for w, k in zip(seg.ws, seg.wphr) if k == int(row["phr"])]
            self.assertEqual([w.attrs.get("resp") for w in ws], ["#transfer"] * len(ws))
            self.assertTrue(all("cert" not in w.attrs for w in ws), "no @cert on approved, copied words")
            got = [(ta.norm(ib.w_text(after, w)), w.attrs.get("type"), w.attrs.get("lemma", "")) for w in ws]
            want = [(ta.norm(m["form"]), m["type"], m["lemma"]) for m in ta.parse_morphs(row["写す注釈"])]
            self.assertEqual(got, want, n)
        c = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "check_tei.py"), sjc], capture_output=True, text=True)
        self.assertEqual(c.returncode, 0, c.stdout)
        r = run("apply", "--tsv", tsv, "--file", sjc, "--write")
        self.assertIn("変更なし", r.stdout, "a second run changes nothing")
        self.assertEqual(open(sjc, "rb").read(), after)

    def test_a_table_with_decisions_is_not_overwritten(self):
        tsv = os.path.join(self.dir, "decided.tsv")
        text = read(self.tsv).replace(ta.STATE_DRAFT, ta.STATE_OK, 1)
        with open(tsv, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        r = run("--out", tsv)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(read(tsv), text)


if __name__ == "__main__":
    unittest.main()
