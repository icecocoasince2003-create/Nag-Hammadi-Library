#!/usr/bin/env python3
"""確認作業の画面（review.html）で書き出したファイルを読むスクリプトの試験。

  python3 -m unittest discover -s tests -p "test_*.py"

  * scripts/merge_review.py: 何人かの書き出しをまとめる（違う行は合わせる、同じ所の違う値は食い違いとして止める）
  * source/nhc_fulltext_split/evaluation/score_review.py: 確認者の列を足した抜き取り表を読める
  * scripts/split_segments.py: 提案の表（列「状態」）から、承認した行だけを当てはめる
リポジトリのファイルは変えない（書き出しは一時フォルダに作る）。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import merge_review as mr  # noqa: E402

with open(os.path.join(ROOT, "data", "review_queues.json"), encoding="utf-8") as _f:
    QUEUES = {q["id"]: q for q in json.load(_f)["queues"]}


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="review-test-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.dir, name)

    def run_merge(self, queue, files, out="merged"):
        out = self.path(out)
        with open(os.devnull, "w") as null:
            old = sys.stdout
            sys.stdout = null
            try:
                code = mr.main([queue] + files + ["--out", out])
            finally:
                sys.stdout = old
        return code, (read(out) if os.path.exists(out) else None)


class MergeTSV(Tmp):
    q = QUEUES["thomas"]

    def exported(self, name, edits):
        """review.html と同じ形の書き出しを作る（edits: {行の番号: {列: 値}}）"""
        base = mr.parse_tsv(read(os.path.join(ROOT, self.q["file"])))
        keyed = {}
        for i, e in edits.items():
            keyed[mr.SEP.join(mr.cell(base, base["rows"][i], c) for c in self.q["key"])] = e
        p = self.path(name)
        write(p, mr.serialize_tsv(mr.apply_edits(base, keyed, self.q["key"], [self.q["corrected"], self.q["reviewer"]])))
        return p

    def test_unchanged_files_give_the_original_bytes(self):
        a = self.exported("a.tsv", {})
        code, out = self.run_merge("thomas", [a, a])
        self.assertEqual(code, 0)
        self.assertEqual(out, read(os.path.join(ROOT, self.q["file"])))

    def test_different_rows_are_combined(self):
        a = self.exported("a.tsv", {0: {"状態": "承認", "確認者": "A"}})
        b = self.exported("b.tsv", {4: {"状態": "修正して承認", "修正した位置": "30", "確認者": "B"}})
        code, out = self.run_merge("thomas", [a, b])
        self.assertEqual(code, 0)
        t = mr.parse_tsv(out)
        self.assertEqual(t["header"][-2:], ["修正した位置", "確認者"])
        self.assertEqual([mr.cell(t, t["rows"][0], c) for c in ("状態", "確認者")], ["承認", "A"])
        self.assertEqual([mr.cell(t, t["rows"][4], c) for c in ("状態", "修正した位置", "確認者")], ["修正して承認", "30", "B"])
        self.assertEqual(sum(1 for r in t["rows"] if mr.cell(t, r, "状態") == self.q["pending"]), len(t["rows"]) - 2)

    def test_the_same_decision_by_two_people_keeps_both_names(self):
        a = self.exported("a.tsv", {2: {"状態": "却下", "確認者": "A"}})
        b = self.exported("b.tsv", {2: {"状態": "却下", "確認者": "B"}})
        code, out = self.run_merge("thomas", [a, b])
        self.assertEqual(code, 0)
        t = mr.parse_tsv(out)
        self.assertEqual(mr.cell(t, t["rows"][2], "確認者"), "A・B")

    def test_different_values_in_the_same_cell_stop_the_merge(self):
        a = self.exported("a.tsv", {2: {"状態": "承認", "確認者": "A"}})
        b = self.exported("b.tsv", {2: {"状態": "却下", "確認者": "B"}})
        code, out = self.run_merge("thomas", [a, b])
        self.assertEqual(code, 1)
        self.assertIsNone(out, "nothing written")

    def test_a_change_in_a_column_that_is_not_editable_stops_the_merge(self):
        p = self.exported("a.tsv", {1: {"根拠": "書き換えた", "状態": "承認", "確認者": "A"}})
        code, out = self.run_merge("thomas", [p])
        self.assertEqual(code, 1)
        self.assertIsNone(out)


class MergeIntros(Tmp):
    q = QUEUES["intros"]

    def exported(self, name, edits):
        obj = json.loads(read(os.path.join(ROOT, self.q["file"])))
        for k, e in edits.items():
            for p, v in e.items():
                mr.set_path(obj["texts"][k], p, v)
        p = self.path(name)
        write(p, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
        return p

    def test_two_people_on_different_texts(self):
        keys = list(json.loads(read(os.path.join(ROOT, self.q["file"])))["texts"])
        a = self.exported("a.json", {keys[0]: {"reviewed": True, "reviewed_by": "A"}})
        b = self.exported("b.json", {keys[1]: {"summary.fr": "Nouveau.", "reviewed_by": "B"}})
        code, out = self.run_merge("intros", [a, b])
        self.assertEqual(code, 0)
        obj = json.loads(out)
        self.assertEqual(out, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
        self.assertIs(obj["texts"][keys[0]]["reviewed"], True)
        self.assertEqual(obj["texts"][keys[1]]["summary"]["fr"], "Nouveau.")
        self.assertEqual(list(obj["texts"][keys[0]])[-1], "reviewed_by")

    def test_the_same_field_with_different_text_stops_the_merge(self):
        key = list(json.loads(read(os.path.join(ROOT, self.q["file"])))["texts"])[0]
        a = self.exported("a.json", {key: {"summary.ja": "一つ目", "reviewed_by": "A"}})
        b = self.exported("b.json", {key: {"summary.ja": "二つ目", "reviewed_by": "B"}})
        code, out = self.run_merge("intros", [a, b])
        self.assertEqual(code, 1)
        self.assertIsNone(out)


class ScoreReviewReadsTheReviewerColumn(Tmp):
    def test_score_review_accepts_an_exported_sample(self):
        q = QUEUES["sample"]
        base = mr.parse_tsv(read(os.path.join(ROOT, q["file"])))
        edits = {}
        for i in range(3):
            row = base["rows"][i]
            k = mr.SEP.join(mr.cell(base, row, c) for c in q["key"])
            edits[k] = {"正しい品詞": mr.cell(base, row, "自動の品詞") or "?", "正しいレンマ": "=", "確認者": "A"}
        p = self.path("review_sample.tsv")
        write(p, mr.serialize_tsv(mr.apply_edits(base, edits, q["key"], [q["reviewer"]])))
        script = os.path.join(ROOT, "source", "nhc_fulltext_split", "evaluation", "score_review.py")
        meta = os.path.join(ROOT, "source", "nhc_fulltext_split", "evaluation", "review_sample.json")
        r = subprocess.run([sys.executable, script, p, "--meta", meta], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("400 行", r.stdout.splitlines()[0])


class SplitSegmentsTakesOnlyApprovedRows(Tmp):
    def test_only_approved_rows_are_applied(self):
        q = QUEUES["breaks"]
        base = mr.parse_tsv(read(os.path.join(ROOT, q["file"])))
        rows = [i for i, r in enumerate(base["rows"]) if mr.cell(base, r, "seg_id") == "II-7503827_2"][:4]
        w = [mr.cell(base, base["rows"][i], "w") for i in rows]
        key = lambda i: mr.SEP.join(mr.cell(base, base["rows"][i], c) for c in q["key"])
        edits = {key(rows[0]): {"状態": "承認", "確認者": "A"},
                 key(rows[1]): {"状態": "修正して承認", "修正した位置": w[2], "確認者": "A"},
                 key(rows[3]): {"状態": "却下", "確認者": "A"}}
        p = self.path("breaks.tsv")
        write(p, mr.serialize_tsv(mr.apply_edits(base, edits, q["key"], [q["corrected"], q["reviewer"]])))
        tei = self.path("II-1.xml")
        shutil.copyfile(os.path.join(ROOT, "source", "nhc_fulltext_split", "tei", "02-1_apocryphon-of-john.xml"), tei)
        before = read(tei)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "split_segments.py"), p, "--file", "II-1=" + tei],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("新しいセグメントが 2 個", r.stdout)
        self.assertIn("w=%s–" % w[0], r.stdout)
        self.assertIn("w=%s–" % w[2], r.stdout, "the corrected place is used")
        self.assertNotIn("w=%s–" % w[1], r.stdout, "not the proposed one")
        self.assertNotIn("w=%s–" % w[3], r.stdout, "not the rejected one")
        self.assertEqual(read(tei), before, "dry run: nothing written")

    def test_an_unreviewed_table_splits_nothing(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "split_segments.py"),
                            os.path.join(ROOT, QUEUES["thomas"]["file"]), "--doc", "II-2"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("分けるものはありません", r.stdout)


if __name__ == "__main__":
    unittest.main()
