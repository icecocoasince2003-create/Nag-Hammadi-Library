/* ============================================================
   viewer-tools.js — 本文を表示するページ（reader.html・eugnostos.html・republic.html）に共通の小道具
   - 写本の写真へのリンク
       <p class="doc-photos" data-codices="III V" hidden></p> を置くと、data/facsimile_links.json の写本ごとの URL から
       「写本 III の写真（Claremont, Nag Hammadi Archive）↗」のようなリンクを書き込んで表示する（写真は 1970 年代の白黒写真）。
       写真の著作権は図書館にあるので、リンクだけにする（画像は読み込まない）。
       リンク先の無い写本は飛ばし、1 つも無いとき・JSON を読めないときは隠したまま。
       このファイルを読み込んだ時点でページにある要素は自動で描く。あとから描く要素は NHCTools.fill(親要素) で描く。
   ページ側のスクリプトは、このファイル（defer）より先に動くことがあるので、次の形で呼ぶ:
       (window.NHCTools ? f(window.NHCTools) : (window.NHCToolsQ = window.NHCToolsQ || []).push(f))
   文言は三言語の span（.l-ja / .l-en / .l-fr。表示の切替は assets/site.css）で書く。
   ============================================================ */
(function () {
  "use strict";
  var LINKS_URL = "data/facsimile_links.json";
  var linksP = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function tri(ja, en, fr) {
    return '<span class="l-ja">' + ja + '</span><span class="l-en">' + en + '</span><span class="l-fr">' + (fr == null ? en : fr) + "</span>";
  }
  function getJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " — HTTP " + r.status);
      return r.json();
    });
  }

  /* ---- 写本の写真へのリンク ---- */
  var SOURCE = "Claremont, Nag Hammadi Archive";
  function photoLinks(el) {
    var codices = (el.getAttribute("data-codices") || "").split(/\s+/).filter(Boolean);
    if (!codices.length) return Promise.resolve();
    linksP = linksP || getJSON(LINKS_URL);
    return linksP.then(function (d) {
      var list = codices.filter(function (c) { return d[c] && d[c].url; });
      if (!list.length) { el.hidden = true; return; }
      var label = function (c) { var x = d[c]; return tri(esc(x.label_ja || c), esc(x.label_en || c), esc(x.label_fr || x.label_en || c)); };
      var link = function (c, inner) {
        return '<a href="' + esc(d[c].url) + '" target="_blank" rel="noopener">' + inner + "</a>";
      };
      var src = function (arrow) {
        return tri("（" + SOURCE + "）" + arrow, " (" + SOURCE + ")" + (arrow && " " + arrow), " (" + SOURCE + ")" + (arrow && " " + arrow));
      };
      var note = '<small class="dp-note">' + tri("1970年代の白黒写真", "black-and-white photographs from the 1970s",
        "photographies en noir et blanc des années 1970") + "</small>";
      el.innerHTML = (list.length === 1
        ? link(list[0], label(list[0]) + src("↗"))
        : list.map(function (c) { return link(c, label(c) + " ↗"); }).join('<span class="dp-sep"> · </span>') + src("")) + " " + note;
      el.hidden = false;
    }).catch(function () { el.hidden = true; });
  }

  /* root の中の、まだ描いていない要素を描く */
  function fill(root) {
    var els = (root || document).querySelectorAll(".doc-photos[data-codices]:not([data-filled])");
    Array.prototype.forEach.call(els, function (el) { el.setAttribute("data-filled", ""); photoLinks(el); });
  }

  var api = { fill: fill, esc: esc, tri: tri, getJSON: getJSON };
  window.NHCTools = api;
  fill(document);
  var q = window.NHCToolsQ || [];
  window.NHCToolsQ = { push: function (f) { f(api); } };
  q.forEach(function (f) { try { f(api); } catch (e) { console.error(e); } });
})();
