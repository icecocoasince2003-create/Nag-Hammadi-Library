"use strict";
/* 確認作業の画面（review.html）のファイルの読み書き（assets/review-core.js）の試験。
   node --test tests/review-core.test.cjs（画面ごとの試験は tests/review.test.html） */

const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const R = require("../assets/review-core.js");

const read = p => fs.readFileSync(path.join(__dirname, "..", p), "utf8");
const QUEUES = JSON.parse(read("data/review_queues.json")).queues;
const K = (...cells) => cells.join(R.SEP);

test("every TSV queue file is written back byte for byte when nothing changed", () => {
  QUEUES.filter(q => q.kind !== "intros").forEach(q => {
    const text = read(q.file);
    const t = R.parseTSV(text);
    assert.equal(R.serializeTSV(t), text, q.file);
    assert.equal(R.serializeTSV(R.applyEdits(t, {}, q.key, [q.corrected, q.reviewer].filter(Boolean))), text, q.file + " (no edits)");
    assert.equal(R.indexRows(t, q.key).size, t.rows.length, q.file + ": the key columns identify every row");
    q.key.concat(q.seg ? [q.seg] : [], q.w ? [q.w] : [], q.show || [], q.blind || [], q.status ? [q.status] : [])
      .forEach(c => assert.ok(t.header.indexOf(c) >= 0, q.file + " has the column " + c));
  });
});

test("the intros JSON is written back byte for byte (Python indent=2 form)", () => {
  const text = read("data/intros.json");
  assert.ok(R.jsonRoundTrips(text));
  assert.equal(R.serializeJSON(JSON.parse(text)), text);
});

test("BOM, CRLF, a missing last line break, blank lines and empty last cells survive", () => {
  const texts = [
    "﻿a\tb\tc\r\n1\t\t\r\n2\tx\ty",
    "a\tb\n\n1\t2\n",
    "a\tb\tc\n1\t2\t\n"
  ];
  texts.forEach(text => assert.equal(R.serializeTSV(R.parseTSV(text)), text));
  const t = R.parseTSV(texts[0]);
  assert.equal(t.bom, true);
  assert.equal(t.eol, "\r\n");
  assert.equal(t.finalEol, false);
  assert.deepEqual(t.rows[0], ["1", "", ""]);
});

test("edits change only their cells; new columns go to the end in the given order and rows are padded", () => {
  const t = R.parseTSV("id\tw\t状態\n1\t5\t案\n2\t7\t案\n");
  const out = R.applyEdits(t, {[K("2")]: {"状態": "修正して承認", "確認者": "KN", "修正した位置": "9"}}, ["id"], ["修正した位置", "確認者"]);
  assert.equal(R.serializeTSV(out), "id\tw\t状態\t修正した位置\t確認者\n1\t5\t案\t\t\n2\t7\t修正して承認\t9\tKN\n");
  assert.equal(R.serializeTSV(t), "id\tw\t状態\n1\t5\t案\n2\t7\t案\n", "the original table is not changed");
});

test("tabs and line breaks typed into a cell cannot break the TSV", () => {
  const t = R.parseTSV("id\tメモ\n1\t\n");
  const out = R.applyEdits(t, {[K("1")]: {"メモ": "a\tb\nc\r\nd"}}, ["id"]);
  assert.equal(R.serializeTSV(out), "id\tメモ\n1\ta b c d\n");
});

test("diffTables gives back the edits that produced a table, and nothing for an unchanged one", () => {
  const q = QUEUES.find(x => x.id === "breaks");
  const t = R.parseTSV(read(q.file));
  const k1 = R.rowKey(t, q.key, t.rows[0]), k2 = R.rowKey(t, q.key, t.rows[10]);
  const edits = {[k1]: {"状態": "承認", "確認者": "A"}, [k2]: {"状態": "修正して承認", "修正した位置": "40", "確認者": "A"}};
  const edited = R.parseTSV(R.serializeTSV(R.applyEdits(t, edits, q.key, [q.corrected, q.reviewer])));
  const d = R.diffTables(t, edited, q.key, [q.status, q.corrected, q.reviewer]);
  assert.deepEqual(d.problems, []);
  assert.deepEqual(d.edits, edits);
  assert.deepEqual(R.diffTables(t, R.parseTSV(read(q.file)), q.key, [q.status]).edits, {});
});

test("diffTables reports missing rows, extra rows and changes in columns that are not editable", () => {
  const a = R.parseTSV("id\tx\ty\n1\ta\t\n2\tb\t\n");
  const b = R.parseTSV("id\tx\ty\n1\tA\tok\n3\tc\t\n");
  const d = R.diffTables(a, b, ["id"], ["y"]);
  assert.deepEqual(d.edits, {[K("1")]: {y: "ok"}});
  assert.ok(d.problems.some(p => p.indexOf("missing row: 2") === 0));
  assert.ok(d.problems.some(p => p.indexOf("extra row: 3") === 0));
  assert.ok(d.problems.some(p => p.indexOf("cannot be edited") >= 0 && p.indexOf("x") >= 0));
});

test("two rows with the same key are refused", () => {
  assert.throws(() => R.indexRows(R.parseTSV("id\tx\n1\ta\n1\tb\n"), ["id"]));
});

test("intros: edits set fields, add reviewed_by at the end of the item, and diffJSON returns them", () => {
  const q = QUEUES.find(x => x.id === "intros");
  const text = read(q.file), obj = JSON.parse(text);
  const paths = R.introPaths(q.fields, q.langs, q.reviewer);
  const key = Object.keys(obj.texts).find(k => obj.texts[k].summary);
  const edits = {[key]: {"summary.fr": "Résumé corrigé.", "todo": ["a", "b"], "reviewed": true, "reviewed_by": "KN"}};
  const out = R.applyJSONEdits(obj, edits, "texts");
  const keys = Object.keys(out.texts[key]);
  assert.equal(keys[keys.length - 1], "reviewed_by");
  assert.deepEqual(Object.keys(obj.texts[key]), keys.slice(0, -1), "the other keys keep their order");
  assert.equal(out.texts[key].summary.fr, "Résumé corrigé.");
  const d = R.diffJSON(obj, JSON.parse(R.serializeJSON(out)), "texts", paths);
  assert.deepEqual(d.problems, []);
  assert.deepEqual(d.edits, edits);
  assert.deepEqual(R.diffJSON(obj, JSON.parse(text), "texts", paths).edits, {});
});

test("intros: changes outside the editable fields are reported and not taken", () => {
  const obj = {_comment: "c", texts: {a: {reviewed: false, summary: {ja: "x"}, refs: [{key: "r"}], todo: []}}};
  const other = JSON.parse(JSON.stringify(obj));
  other._comment = "changed";
  other.texts.a.refs = [];
  other.texts.a.summary.ja = "y";
  const d = R.diffJSON(obj, other, "texts", R.introPaths(["summary"], ["ja"], "reviewed_by"));
  assert.deepEqual(d.edits, {a: {"summary.ja": "y"}});
  assert.ok(d.problems.some(p => p.indexOf("outside texts") >= 0));
  assert.ok(d.problems.some(p => p.indexOf("cannot be edited") >= 0 && p.indexOf(": a") >= 0));
});

test("serializeJSON writes the same text as Python's json.dumps(obj, ensure_ascii=False, indent=2)", () => {
  const obj = {b: [], a: {"x": "コプト ⲁ", "y": [1, "z"], "e": {}}, t: true, n: null};
  assert.equal(R.serializeJSON(obj), '{\n  "b": [],\n  "a": {\n    "x": "コプト ⲁ",\n    "y": [\n      1,\n      "z"\n    ],\n    "e": {}\n  },\n  "t": true,\n  "n": null\n}\n');
});
