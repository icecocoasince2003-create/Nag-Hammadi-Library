"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { compile, search, LIMITS } = require("../assets/corpus-query.js");

// Each <w> is a morpheme. Global indexes are retained across <s> and witnesses.
const token = (index, pos, form = pos, extra = {}) => ({
  index, pos, form, lemma: form, msd: "", ...extra
});
const segment = (w, tokens) => ({ w, tokens });
const find = (query, segments, options = {}, mode = "aql") =>
  search(compile(query, mode), segments, options);
const indexes = result => result.matches.map(match => match.tokens);

test("simple POS sequences preserve order and allow overlapping matches", () => {
  const segments = [segment(0, [token(0, "N"), token(1, "N"), token(2, "N"), token(3, "V")])];
  assert.deepEqual(indexes(find("N N", segments, {}, "pos")), [[0, 1], [1, 2]]);
  assert.deepEqual(indexes(find("V N", segments, {}, "pos")), []);
  assert.deepEqual(indexes(find("N V", segments, {}, "pos")), [[2, 3]]);
});

test("simple POS mode accepts Unicode tags present in the TEI corpus", () => {
  const segments = [segment(0, [token(0, "Ⲛ"), token(1, "N")])];
  assert.deepEqual(indexes(find("Ⲛ N", segments, {}, "pos")), [[0, 1]]);
});

test("adjacency follows morphemes, including separate orthographic words", () => {
  const segments = [segment(0, [
    token(0, "ART", "ⲡ", { phy: "a" }),
    token(1, "N", "ⲣⲱⲙⲉ", { phy: "b" }),
    token(2, "V", "ⲥⲱⲧⲙ", { phy: "c" })
  ])];
  assert.deepEqual(indexes(find('pos="ART" . pos="N" . pos="V"', segments)), [[0, 1, 2]]);
  assert.deepEqual(indexes(find('pos="ART" . pos="V"', segments)), []);
});

test("distance is measured between morpheme positions: one means adjacent", () => {
  const segments = [segment(0, [token(0, "ART"), token(1, "N"), token(2, "N"), token(3, "N")])];
  assert.deepEqual(indexes(find('pos="ART" .1 pos="N"', segments)), [[0, 1]]);
  assert.deepEqual(indexes(find('pos="ART" .2 pos="N"', segments)), [[0, 2]]);
  assert.deepEqual(indexes(find('pos="ART" .1,3 pos="N"', segments)), [[0, 1], [0, 2], [0, 3]]);
  assert.deepEqual(indexes(find('pos="ART" .2,3 pos="N"', segments)), [[0, 2], [0, 3]]);
});

test("a variable-distance chain returns every matching ordered tuple", () => {
  const segments = [segment(0, [token(0, "ART"), token(1, "N"), token(2, "N"), token(3, "V")])];
  assert.deepEqual(indexes(find('pos="ART" .1,2 pos="N" .1,2 pos="V"', segments)), [[0, 1, 3], [0, 2, 3]]);
});

test("matches never cross segment or witness boundaries", () => {
  const segments = [
    segment(0, [token(0, "ART")]),
    segment(0, [token(1, "N")]),
    segment(1, [token(2, "ART"), token(3, "N")]),
    segment(2, [token(4, "V")])
  ];
  assert.deepEqual(indexes(find('pos="ART" . pos="N"', segments)), [[2, 3]]);
  assert.deepEqual(indexes(find('pos="N" .1,1000 pos="V"', segments)), []);
});

test("selected witnesses restrict matches without renumbering global indexes", () => {
  const segments = [segment(0, [token(17, "N")]), segment(1, [token(42, "N")])];
  assert.deepEqual(indexes(find('pos="N"', segments, { selectedWitnesses: [1] })), [[42]]);
  assert.deepEqual(indexes(find('pos="N"', segments, { selectedWitnesses: [] })), []);
});

test("excluded POS cannot create false adjacency by removing intervening morphemes", () => {
  const segments = [segment(0, [token(0, "ART"), token(1, "ADV"), token(2, "N")])];
  const options = { excludedPos: ["ADV"] };
  assert.deepEqual(indexes(find('pos="ART" . pos="N"', segments, options)), []);
  assert.deepEqual(indexes(find('pos="ART" .2 pos="N"', segments, options)), [[0, 2]]);
  assert.deepEqual(indexes(find('pos="ADV"', segments, options)), []);
  assert.deepEqual(indexes(find('tok . tok', segments, options)), []);
});

test("literal forms and lemmas retain legacy diacritic-insensitive matching", () => {
  const segments = [segment(0, [token(0, "N", "ⲣ\u0305ⲱⲙⲉ", { lemma: "Café" })])];
  assert.deepEqual(indexes(find('tok="ⲣⲱⲙⲉ"', segments)), [[0]]);
  assert.deepEqual(indexes(find('form="ⲣⲱⲙⲉ"', segments)), [[0]]);
  assert.deepEqual(indexes(find('lemma="CAFE"', segments)), [[0]]);
  assert.deepEqual(indexes(find('tok="ⲣⲱⲙ"', segments)), []);
});

test("POS and morphological annotation literals are exact and case sensitive", () => {
  const segments = [segment(0, [token(0, "N", "x", { msd: "Sing" }), token(1, "NPROP", "y")])];
  assert.deepEqual(indexes(find('type="N"', segments)), [[0]]);
  assert.deepEqual(indexes(find('pos="n"', segments)), []);
  assert.deepEqual(indexes(find('msd="Sing"', segments)), [[0]]);
  assert.deepEqual(indexes(find('msd="sing"', segments)), []);
});

test("regular expressions match the complete annotation rather than a substring", () => {
  const segments = [segment(0, [token(0, "N", "ⲣⲱⲙⲉ"), token(1, "NPROP", "ⲣⲱⲙ"), token(2, "V", "a\nb")])];
  assert.deepEqual(indexes(find("pos=/N/", segments)), [[0]]);
  assert.deepEqual(indexes(find("pos=/N.*/", segments)), [[0], [1]]);
  assert.deepEqual(indexes(find("tok=/ⲣⲱⲙ/", segments)), [[1]]);
  assert.deepEqual(indexes(find("tok=/.*ⲣⲱⲙ.*/", segments)), [[0], [1]]);
  assert.deepEqual(indexes(find("tok=/a|b/", segments)), []);
});

test("regex alternation is anchored as a group", () => {
  const segments = [segment(0, [token(0, "N"), token(1, "NPROP"), token(2, "V"), token(3, "VV"), token(4, "N\n")])];
  assert.deepEqual(indexes(find("pos=/N|V/", segments)), [[0], [2]]);
});

test("regex is case sensitive, keeps diacritics, and preserves Unicode pattern source", () => {
  const segments = [segment(0, [token(0, "N", "ⲣ\u0305ⲱⲙⲉ"), token(1, "N", "ABC"), token(2, "N", "ⲣⲱⲙⲉ")])];
  assert.deepEqual(indexes(find("tok=/ⲣⲱⲙⲉ/", segments)), [[2]]);
  assert.deepEqual(indexes(find("tok=/abc/", segments)), []);
  assert.deepEqual(indexes(find("tok=/\\p{Lu}+/", segments)), [[1]]);
  assert.deepEqual(indexes(find("tok=/\\p{Script=Coptic}+/", segments)), [[2]]);
});

test("escaped delimiters and JSON quotes are accepted as annotation values", () => {
  const segments = [segment(0, [token(0, "N", 'a/b'), token(1, "N", 'a"b'), token(2, "N", "a\\b")])];
  assert.deepEqual(indexes(find('tok="a/b"', segments)), [[0]]);
  assert.deepEqual(indexes(find('tok=/a\\/b/', segments)), [[0]]);
  assert.deepEqual(indexes(find('tok=' + JSON.stringify('a"b'), segments)), [[1]]);
  assert.deepEqual(indexes(find('tok=' + JSON.stringify("a\\b"), segments)), [[2]]);
});

test("whitespace and literal dots do not confuse sequence parsing", () => {
  const segments = [segment(0, [token(0, "N", "a.b"), token(1, "V", "c")])];
  assert.deepEqual(indexes(find('  tok="a.b"\n .\tpos="V"  ', segments)), [[0, 1]]);
  assert.deepEqual(indexes(find('tok=/a.b/ . pos="V"', segments)), [[0, 1]]);
});

test("bare tok matches one morpheme and can bridge an explicitly requested position", () => {
  const segments = [segment(0, [token(0, "ART"), token(1, "ADV"), token(2, "N")])];
  assert.deepEqual(indexes(find('pos="ART" . tok . pos="N"', segments)), [[0, 1, 2]]);
  assert.deepEqual(indexes(find("tok", segments)), [[0], [1], [2]]);
});

test("invalid and unsupported expressions fail visibly instead of becoming literal searches", () => {
  const invalid = [
    "", "   ", 'pos="N', 'pos="N" .', '. pos="N"', 'pos=N',
    'unknown="N"', 'pos="N" pos="V"', 'pos="N" & pos="V"',
    'pos="N" .* pos="V"', 'pos="N" .0 pos="V"',
    'pos="N" .3,1 pos="V"', 'pos="N" .1,1001 pos="V"',
    'pos=/[/', 'pos=/N', 'pos=/N/i', 'tok="\\q"',
    'pos="N" .1.5 pos="V"', 'pos="N" | pos="V"'
  ];
  for (const query of invalid) {
    assert.throws(() => compile(query, "aql"), undefined, query);
  }
  assert.throws(() => compile("N . V", "pos"));
});

test("a regex cannot close the anchoring group and match part of a value", () => {
  // Wrapped as ^(?:N)|(V)$ this would match every tag that merely starts with N.
  assert.throws(() => compile("pos=/N)|(V/", "aql"), { code: "INVALID_REGEX" });
  assert.throws(() => compile("pos=/N)(?:V/", "aql"), { code: "INVALID_REGEX" });
  const segments = [segment(0, [token(0, "NPROP"), token(1, "N"), token(2, "V")])];
  assert.deepEqual(indexes(find("pos=/(N)|(V)/", segments)), [[1], [2]]);
});

test("errors name the exact problem and where it is, so the page can translate them", () => {
  const cases = [
    ['pos="N', "SYNTAX_ERROR", "openString", 4],
    ['tok="\\q"', "SYNTAX_ERROR", "badString", 4],
    ["pos=/N", "SYNTAX_ERROR", "openRegex", 4],
    ["pos=N", "SYNTAX_ERROR", "expectedValue", 4],
    ["lemma", "SYNTAX_ERROR", "expectedEquals", 5],
    ['unknown="N"', "SYNTAX_ERROR", "unknownAnnotation", 0],
    ['. pos="N"', "SYNTAX_ERROR", "expectedNode", 0],
    ['pos="N" .', "SYNTAX_ERROR", "expectedNode", 9],
    ['pos="N" pos="V"', "SYNTAX_ERROR", "expectedOperator", 8],
    ['pos="N" & pos="V"', "SYNTAX_ERROR", "expectedOperator", 8],
    ['pos="N" .* pos="V"', "SYNTAX_ERROR", "unboundedDistance", 8],
    ['pos="N" .0 pos="V"', "SYNTAX_ERROR", "badDistance", 8],
    ['pos="N" .3,1 pos="V"', "SYNTAX_ERROR", "badDistance", 8],
    ['pos="N" .1, pos="V"', "SYNTAX_ERROR", "expectedMax", 11],
    ['pos="N" .1,1001 pos="V"', "QUERY_LIMIT", "tooFar", 8],
    ["pos=/(/", "INVALID_REGEX", "badRegex", 5]
  ];
  for (const [query, code, detail, position] of cases) {
    assert.throws(() => compile(query, "aql"), { code, detail, position }, query);
  }
  assert.throws(() => compile("N . V", "pos"), { code: "SYNTAX_ERROR", detail: "posTags" });
  assert.throws(() => compile("  ", "aql"), { code: "EMPTY_QUERY", detail: "empty" });
  let reason;
  try { compile("pos=/(/", "aql"); } catch (error) { reason = error.reason; }
  assert.equal(typeof reason, "string");
  assert.equal(reason.includes("/"), false, "the engine's reason is reported without the wrapped pattern");
});

test("query and node limits reject oversized expressions", () => {
  assert.throws(() => compile('tok="' + "x".repeat(LIMITS.queryLength) + '"', "aql"), { code: "QUERY_LIMIT" });
  assert.throws(() => compile(Array(LIMITS.nodes + 1).fill('tok').join(" . "), "aql"), { code: "QUERY_LIMIT" });
  assert.throws(() => compile(Array(LIMITS.nodes + 1).fill('N').join(" "), "pos"), { code: "QUERY_LIMIT" });
  assert.throws(() => compile("pos=/(/", "aql"), { code: "INVALID_REGEX" });
  assert.throws(() => compile("N", "unsupported"), { code: "INVALID_MODE" });
});

test("the operation budget stops combinatorial searches even when they produce no results", () => {
  // The only Z precedes the wildcard candidates. Many triples are possible,
  // but none can reach a later Z; the result limit alone cannot bound this work.
  const tokens = Array.from({ length: 301 }, (_, i) => token(i, i ? "N" : "Z"));
  assert.throws(
    () => find('tok .1,1000 tok .1,1000 tok .1,1000 pos="Z"', [segment(0, tokens)]),
    { code: "SEARCH_LIMIT" }
  );
});

test("the size of the corpus alone does not exhaust the operation budget", () => {
  // 140 segments of 1,000 morphemes and a 16-node sequence: scanning costs
  // 16 × 140,000 tests (more than LIMITS.operations), but only one tuple per
  // segment has to be joined. The budget is for the joining, not the scan.
  const segments = Array.from({ length: 140 }, (_, s) =>
    segment(0, Array.from({ length: 1000 }, (_, i) => token(s * 1000 + i, i ? "N" : "ART"))));
  const query = ["ART"].concat(Array(LIMITS.nodes - 1).fill("N")).join(" ");
  assert.equal(segments.length * 1000 * LIMITS.nodes > LIMITS.operations, true);
  const result = find(query, segments, {}, "pos");
  assert.equal(result.matches.length, 140);
  assert.equal(result.truncated, false);
  assert.deepEqual(result.matches[139].tokens, Array.from({ length: 16 }, (_, i) => 139000 + i));
});

test("the result limit retains deterministic matches and signals truncation only if needed", () => {
  const segments = [segment(0, [token(0, "N"), token(1, "N"), token(2, "N")])];
  const limited = find('pos="N"', segments, { limit: 2 });
  assert.deepEqual(indexes(limited), [[0], [1]]);
  assert.equal(limited.truncated, true);
  const exact = find('pos="N"', segments, { limit: 3 });
  assert.deepEqual(indexes(exact), [[0], [1], [2]]);
  assert.equal(exact.truncated, false);
});

test("the worker reports readiness, then preserves request ids in results and errors", () => {
  const responses = [];
  const sandbox = {
    postMessage: response => responses.push(JSON.parse(JSON.stringify(response))),
    importScripts: filename => {
      assert.equal(filename, "corpus-query.js");
      vm.runInContext(fs.readFileSync(path.join(__dirname, "../assets", filename), "utf8"), context);
    }
  };
  sandbox.self = sandbox;
  const context = vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../assets/corpus-search-worker.js"), "utf8"), context);
  const send = data => sandbox.onmessage({ data });

  send({ type: "search", id: 7, mode: "pos", query: "ART N" });
  assert.equal(responses.pop().error.code, "NOT_READY");
  send({ type: "init", segments: [segment(0, [token(9, "ART"), token(10, "N")])] });
  // The page starts timing a search only once the corpus has arrived.
  assert.deepEqual(responses.pop(), { type: "ready" });
  send({ type: "search", id: 8, mode: "pos", query: "ART N" });
  assert.deepEqual(responses.pop(), { id: 8, result: { matches: [{ tokens: [9, 10] }], truncated: false } });
  send({ type: "search", id: 9, mode: "aql", query: "pos=/(/" });
  const error = responses.pop();
  assert.equal(error.id, 9);
  assert.equal(error.error.code, "INVALID_REGEX");
  assert.equal(error.error.detail, "badRegex");
  assert.equal(error.error.position, 5);
  assert.equal(typeof error.error.reason, "string");
  assert.equal(typeof error.error.message, "string");
  send({ type: "search", id: 10, mode: "aql", query: 'pos="ART" .* pos="N"' });
  assert.deepEqual(responses.pop().error, {
    code: "SYNTAX_ERROR", detail: "unboundedDistance", position: 10,
    message: "Unbounded distance (.*) is not supported; give a range such as .1,1000 (character 11)."
  });
  // The same worker keeps answering: it is reused from one search to the next.
  send({ type: "search", id: 11, mode: "aql", query: 'pos="ART" . pos="N"' });
  assert.deepEqual(responses.pop(), { id: 11, result: { matches: [{ tokens: [9, 10] }], truncated: false } });
  assert.equal(responses.length, 0);
});
