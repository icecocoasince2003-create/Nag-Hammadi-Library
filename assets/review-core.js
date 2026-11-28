/* review-core.js — 確認作業の画面（review.html）の、ファイルを読む・書く部分（画面を持たない関数だけ）。
 * tests/review-core.test.cjs がこの関数を試す（node --test。画面ごとの試験は tests/review.test.html）。
 *
 * 書き出しの約束: 元のファイルと同じ形で書き戻す。何も変えていなければ、元とバイト単位で同じになる。
 *   TSV  … 列の順・文字コード（UTF-8）・改行（LF か CRLF）・BOM の有無・最後の改行の有無を元のまま。セルは書き換えた
 *          ところだけを変え、足す列（確認者など）は末尾に足す。セルの中のタブと改行は空白に置き換える（TSV が壊れないように）
 *   JSON … JSON.stringify(値, null, 2) ＋ 改行（Python の json.dumps(…, ensure_ascii=False, indent=2) と同じ形）。
 *          キーの順は元のまま、新しいキー（reviewed_by）はその項目の末尾。読み込んだときに、元の文字列がこの形で
 *          書き戻せることを確かめる（jsonRoundTrips）
 * 書き換えは「行のキー（列の値の組）→ 列 → 値」の形（edits）で持つ。行は番号ではなくキーで探すので、表の並びが変わっても
 * 当たる。scripts/merge_review.py が同じ約束で、複数の人が書き出したファイルをまとめる。
 */
(function(root, factory){
  const api = factory();
  if(typeof module === "object" && module.exports) module.exports = api;
  else root.ReviewCore = api;
})(typeof self !== "undefined" ? self : globalThis, function(){
  "use strict";

  const SEP = "\u0001";   // 行のキーの区切り（セルには現れない）

  /* ---------- TSV ---------- */
  function parseTSV(text){
    text = String(text);
    let bom = false;
    if(text.charCodeAt(0) === 0xFEFF){ bom = true; text = text.slice(1); }
    const eol = text.indexOf("\r\n") >= 0 ? "\r\n" : "\n";
    const lines = text.split(eol);
    let finalEol = false;
    if(lines.length > 1 && lines[lines.length - 1] === ""){ finalEol = true; lines.pop(); }
    if(!lines.length || !lines[0]) throw new Error("TSV: no header line");
    return {bom, eol, finalEol, header: lines[0].split("\t"), rows: lines.slice(1).map(l => l.split("\t"))};
  }
  function serializeTSV(t){
    return (t.bom ? "﻿" : "") + [t.header].concat(t.rows).map(r => r.join("\t")).join(t.eol) + (t.finalEol ? t.eol : "");
  }
  const isBlank = row => row.length === 1 && row[0] === "";
  function cell(t, row, col){ const i = t.header.indexOf(col); return i < 0 ? "" : (row[i] == null ? "" : row[i]); }
  function rowKey(t, keyCols, row){ return keyCols.map(c => cell(t, row, c)).join(SEP); }
  /* 行のキー → 行の番号（0 から。見出しは数えない）。キーの重複は誤り */
  function indexRows(t, keyCols){
    const m = new Map();
    t.rows.forEach((r, i) => {
      if(isBlank(r)) return;
      const k = rowKey(t, keyCols, r);
      if(m.has(k)) throw new Error("TSV: two rows have the same key: " + k.split(SEP).join(" / "));
      m.set(k, i);
    });
    return m;
  }
  const cleanCell = v => String(v == null ? "" : v).replace(/[\t\r\n]+/g, " ");
  /* 「 | 」で並べた候補のセルを分ける（空の候補は除く） */
  const splitCell = v => String(v == null ? "" : v).split("|").map(x => x.trim()).filter(Boolean);
  /* キューの filter（[{列: [値…], …}, …]）に行が合うか。どれか 1 つの組で、そのすべての列の値が挙げた値のどれかなら合う。
     filter が無いか空なら、すべての行が合う */
  function matchesFilter(t, row, filter){
    if(!filter || !filter.length) return true;
    return filter.some(cond => Object.keys(cond).every(c => cond[c].indexOf(cell(t, row, c)) >= 0));
  }

  /* 書き換え（edits）を当てた新しい表。足す列は appendOrder の順、ほかは名前の順で末尾に */
  function applyEdits(t, edits, keyCols, appendOrder){
    appendOrder = appendOrder || [];
    const out = {bom: t.bom, eol: t.eol, finalEol: t.finalEol, header: t.header.slice(), rows: t.rows.map(r => r.slice())};
    const idx = indexRows(out, keyCols), used = new Set();
    Object.keys(edits).forEach(k => Object.keys(edits[k]).forEach(c => used.add(c)));
    const extra = appendOrder.filter(c => used.has(c)).concat([...used].filter(c => appendOrder.indexOf(c) < 0).sort())
      .filter(c => out.header.indexOf(c) < 0);
    out.header.push(...extra);
    Object.keys(edits).forEach(k => {
      const i = idx.get(k);
      if(i == null) throw new Error("TSV: no row with the key " + k.split(SEP).join(" / "));
      const row = out.rows[i];
      Object.keys(edits[k]).forEach(c => {
        const j = out.header.indexOf(c);
        while(row.length <= j) row.push("");
        row[j] = cleanCell(edits[k][c]);
      });
    });
    if(extra.length) out.rows.forEach(r => { if(!isBlank(r)) while(r.length < out.header.length) r.push(""); });
    return out;
  }

  /* 2 つの表の違い（other − orig）を edits の形で。editable の列だけを取り、ほかの列の違いと、行・列の過不足は problems に */
  function diffTables(orig, other, keyCols, editable){
    const problems = [], edits = {};
    let oi, ni;
    try { oi = indexRows(orig, keyCols); ni = indexRows(other, keyCols); }
    catch(e){ return {edits, problems: [e.message]}; }
    const show = k => k.split(SEP).join(" / ");
    for(const k of oi.keys()) if(!ni.has(k)) problems.push("missing row: " + show(k));
    for(const k of ni.keys()) if(!oi.has(k)) problems.push("extra row: " + show(k));
    const lost = orig.header.filter(c => other.header.indexOf(c) < 0);
    if(lost.length) problems.push("missing columns: " + lost.join(", "));
    const ok = c => !editable || editable.indexOf(c) >= 0;
    const locked = new Set();
    for(const [k, j] of ni){
      const i = oi.get(k);
      if(i == null) continue;
      other.header.forEach((c, ci) => {
        const ov = cell(orig, orig.rows[i], c), nv = other.rows[j][ci] == null ? "" : other.rows[j][ci];
        if(ov === nv) return;
        if(ok(c)) (edits[k] = edits[k] || {})[c] = nv;
        else locked.add(c);
      });
    }
    if(locked.size) problems.push("changes in columns that cannot be edited here (ignored): " + [...locked].join(", "));
    return {edits, problems};
  }

  /* ---------- JSON ---------- */
  const serializeJSON = obj => JSON.stringify(obj, null, 2) + "\n";
  function jsonRoundTrips(text){ try { return serializeJSON(JSON.parse(text)) === text; } catch(e){ return false; } }
  function getPath(o, p){ return p.split(".").reduce((a, k) => a == null ? undefined : a[k], o); }
  function setPath(o, p, v){
    const ks = p.split(".");
    let a = o;
    for(let i = 0; i < ks.length - 1; i++){
      if(a[ks[i]] == null || typeof a[ks[i]] !== "object") a[ks[i]] = {};
      a = a[ks[i]];
    }
    a[ks[ks.length - 1]] = v;
  }
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  /* キーの順によらない比較（キーを並べ替えた形で比べる） */
  function canon(v){
    if(Array.isArray(v)) return v.map(canon);
    if(v && typeof v === "object"){ const o = {}; Object.keys(v).sort().forEach(k => { o[k] = canon(v[k]); }); return o; }
    return v;
  }
  const sameC = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
  function strip(item, paths){ const c = JSON.parse(JSON.stringify(item)); paths.forEach(p => setPath(c, p, null)); return c; }
  /* edits: {項目のキー: {"summary.ja": 文字列, "todo": [..], "reviewed": true, "reviewed_by": "…"}} を obj[section] に当てる */
  function applyJSONEdits(obj, edits, section){
    const out = JSON.parse(JSON.stringify(obj));
    Object.keys(edits).forEach(k => {
      const t = out[section] && out[section][k];
      if(!t) throw new Error("JSON: no item " + k);
      Object.keys(edits[k]).forEach(p => setPath(t, p, edits[k][p]));
    });
    return out;
  }
  /* 2 つの JSON の違い（other − orig）。paths に挙げた所だけを edits に取り、ほかの違いは problems に */
  function diffJSON(orig, other, section, paths){
    const problems = [], edits = {};
    const a = (orig && orig[section]) || {}, b = (other && other[section]) || {};
    Object.keys(a).forEach(k => { if(!(k in b)) problems.push("missing item: " + k); });
    Object.keys(b).forEach(k => { if(!(k in a)) problems.push("extra item: " + k); });
    Object.keys(orig || {}).forEach(k => { if(k !== section && !sameC(orig[k], (other || {})[k])) problems.push("changes outside " + section + " (ignored): " + k); });
    Object.keys(a).forEach(k => {
      if(!(k in b)) return;
      paths.forEach(p => { const x = getPath(a[k], p), y = getPath(b[k], p); if(y !== undefined && !same(x, y)) (edits[k] = edits[k] || {})[p] = y; });
      if(!sameC(strip(a[k], paths), strip(b[k], paths))) problems.push("changes in fields that cannot be edited here (ignored): " + k);
    });
    return {edits, problems};
  }

  /* 解題（intros）の項目で書き換えられる所: fields の各言語、todo、reviewed、確認者のキー */
  function introPaths(fields, langs, reviewerKey){
    const out = [];
    fields.forEach(f => langs.forEach(l => out.push(f + "." + l)));
    return out.concat(["todo", "reviewed", reviewerKey]);
  }

  return Object.freeze({SEP, parseTSV, serializeTSV, cell, rowKey, indexRows, cleanCell, splitCell, matchesFilter, applyEdits, diffTables,
    serializeJSON, jsonRoundTrips, getPath, setPath, canon, applyJSONEdits, diffJSON, introPaths});
});
