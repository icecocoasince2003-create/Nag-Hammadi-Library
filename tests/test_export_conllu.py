#!/usr/bin/env python3
"""scripts/export_conllu.py の試験（Sheneset の層だけを CoNLL-U で書き出す）。

  python3 -m unittest discover -s tests -p "test_*.py"

書き出しは一時フォルダに作る（リポジトリのファイルは変えない）。CoNLL-U の形（10 列、ID の並び、語群の範囲、# text）と、
語の数・品詞ごとの数が TEI と data/fulltext_stats.json に合うことを確かめる。
"""
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "export_conllu.py")
T = "{http://www.tei-c.org/ns/1.0}"


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def parse(text):
    """CoNLL-U を文に分け、形を確かめる。[(comments, rows)]。形が違えば AssertionError"""
    assert text.endswith("\n\n"), "every sentence ends with a blank line"
    out = []
    for block in text[:-2].split("\n\n"):
        lines = block.split("\n")
        comments = [l for l in lines if l.startswith("#")]
        rows = [l.split("\t") for l in lines if not l.startswith("#")]
        assert lines.index(comments[-1]) == len(comments) - 1, "comments come first"
        assert all(len(r) == 10 for r in rows), "ten columns"
        want, i = 1, 0
        while i < len(rows):
            r = rows[i]
            if "-" in r[0]:
                a, b = (int(x) for x in r[0].split("-"))
                assert a == want and b > a, "a range starts at the next word: " + r[0]
                assert r[2:] == ["_"] * 8, "a range line has only ID and FORM"
                assert [x[0] for x in rows[i + 1:i + 2 + b - a]] == [str(k) for k in range(a, b + 1)], "the range's words follow"
            else:
                assert r[0] == str(want), "word ids run 1, 2, 3 …"
                want += 1
                assert r[3] == "_" and r[5:9] == ["_"] * 4, "UPOS, FEATS, HEAD, DEPREL, DEPS are _"
                assert r[9].startswith("seg_id="), "MISC has the seg_id"
            assert r[1] and "\t" not in r[1] and " " not in r[1], "a FORM without spaces"
            i += 1
        out.append((comments, rows))
    return out


def tokens(rows):
    """# text に並ぶもの: 語群（範囲の行）と、語群の外の語"""
    out, skip = [], 0
    for r in rows:
        if "-" in r[0]:
            a, b = (int(x) for x in r[0].split("-"))
            out.append(r[1])
            skip = b - a + 1
        elif skip:
            skip -= 1
        else:
            out.append(r[1])
    return out


class ExportConllu(unittest.TestCase):
    def same(self, a, b, msg):
        """長い並びの比較。違えば最初の違いだけを示す（unittest の差分の計算は、長い並びでは終わらないほど遅いため）"""
        if a != b:
            i = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            self.fail("%s: first difference at %d: %r != %r (lengths %d, %d)" % (msg, i, a[i:i + 1], b[i:i + 1], len(a), len(b)))

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="conllu-test-")
        cls.out = os.path.join(cls.dir, "conllu")
        r = subprocess.run([sys.executable, "-I", SCRIPT, "--out", cls.out, "--zip"], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.stdout = r.stdout
        cls.files = sorted(os.listdir(cls.out))
        with open(os.path.join(ROOT, "data", "fulltext_stats.json"), encoding="utf-8") as f:
            st = json.load(f)
        cls.stats = {d["key"]: d for d in st["docs"] + st["reference"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_one_file_per_hand_annotated_or_draft_text(self):
        drafts = [k for k, d in self.stats.items() if d["status"] == "draft"]
        self.assertEqual(self.files, sorted(k + ".conllu" for k in drafts + ["eugnostos", "republic"]))

    def test_the_form_and_the_counts_follow_the_tei(self):
        sent_ids = set()
        for name in self.files:
            key = name[:-len(".conllu")]
            sents = parse(read(os.path.join(self.out, name)))
            head = dict(l[2:].split(" = ", 1) for l in sents[0][0] if " = " in l)
            self.assertEqual(head["newdoc id"], key)
            path, wid = head["source"].split("#")
            root = ET.parse(os.path.join(ROOT, path)).getroot()
            text = next(t for t in root.iter(T + "text") if t.get("{http://www.w3.org/XML/1998/namespace}id") == wid)
            ws = list(text.iter(T + "w"))
            words = [r for _, rows in sents for r in rows if "-" not in r[0]]
            self.assertEqual(len(words), len(ws), key + ": one line per <w>")
            self.same([r[2] for r in words], [w.get("lemma") or "_" for w in ws], key + ": LEMMA is @lemma")
            self.same([r[4] for r in words], [w.get("type") or "_" for w in ws], key + ": XPOS is @type")
            self.assertEqual(collections.Counter(r[4] for r in words if r[4] != "_"), collections.Counter(self.stats[key]["pos"]),
                             key + ": XPOS counts as in data/fulltext_stats.json")
            self.assertEqual(sum(1 for _, rows in sents for r in rows if "-" in r[0]),
                             sum(1 for p in text.iter(T + "phr") if len(list(p.iter(T + "w"))) > 1), key + ": a range per bound group")
            for comments, rows in sents:
                c = dict(l[2:].split(" = ", 1) for l in comments if " = " in l)
                self.assertNotIn(c["sent_id"], sent_ids)
                sent_ids.add(c["sent_id"])
                self.assertTrue(c["sent_id"].startswith(key + ":"))
                self.assertEqual(c["text"], " ".join(tokens(rows)), c["sent_id"] + ": # text")
                self.assertEqual({r[9] for r in rows if "-" not in r[0]}, {"seg_id=" + c["sent_id"].split(":", 1)[1]})

    def test_the_same_data_gives_the_same_bytes_and_the_zip_holds_every_file(self):
        again = os.path.join(self.dir, "again")
        r = subprocess.run([sys.executable, "-I", SCRIPT, "--out", again, "--zip"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for name in self.files:
            self.assertTrue(read(os.path.join(again, name)) == read(os.path.join(self.out, name)), name + ": the same bytes")
        zips = sorted(n for n in os.listdir(self.dir) if n.endswith(".zip"))
        self.assertEqual(len(zips), 1, "both runs write the same zip name")
        with open(os.path.join(ROOT, "data", "release.json"), encoding="utf-8") as f:
            version = json.load(f)["version"]
        with zipfile.ZipFile(os.path.join(self.dir, zips[0])) as z:
            self.assertEqual(sorted(z.namelist()), ["sheneset-v%s-conllu/%s" % (version, n) for n in self.files])


if __name__ == "__main__":
    unittest.main()
