/* ============================================================
   viewer-tools.js — 本文を表示するページ（reader.html・eugnostos.html・republic.html）と project.html に共通の小道具
   1) 写本の写真へのリンク
       <span class="doc-photos" data-codices="III V" hidden></span> を置くと、data/facsimile_links.json の写本ごとの URL から
       「写本 III の写真（Claremont, Nag Hammadi Archive）↗」のようなリンクを書き込んで表示する（写真は 1970 年代の白黒写真）。
       写真の著作権は図書館にあるので、リンクだけにする（画像は読み込まない）。
       リンク先の無い写本は飛ばし、1 つも無いとき・JSON を読めないときは隠したまま。
       このファイルを読み込んだ時点でページにある要素は自動で描く。あとから描く要素は NHCTools.fill(親要素) で描く。
   2) 引用（〈この箇所を引用〉〈この文書を引用〉）
       data/release.json（版番号・DOI・公開 URL）と data/doc_dates.json（文書ごとの最終更新日。scripts/build_site.py が
       書き出す）を読んで、引用表記を作る。書式は project.html の引用欄と同じで、箇所を引くときは次の形:
         日: 生田目心愛 編『Sheneset：ナグ・ハマディ写本コーパス』v0.1.0, NHC II,2 §3（暫定版）. https://…（2026-11-22 閲覧）
         英: Kokoa Nabatame (ed.), Sheneset: A Digital TEI Edition of the Nag Hammadi Codices, v0.1.0, NHC II,2 §3 (draft). https://… (accessed 2026-11-22).
         仏: Kokoa Nabatame (éd.), Sheneset : édition numérique TEI des codices de Nag Hammadi, v0.1.0, NHC II,2 §3 (provisoire). https://… (consulté le 2026-11-22).
       DOI があれば URL の前に https://doi.org/… を入れる。URL は公開サイトのもの（release.json の url）、閲覧日はその日の日付。
       引用文の言語は、サイトで選んでいる言語（日英だけのビュワーでフランス語を選んでいればフランス語）。
       - NHCTools.cite(押した要素, {kind:"passage", path:"reader.html?doc=II-2#seg-…", where:{ja,en,fr}})
         NHCTools.cite(押した要素, {kind:"document", path:"reader.html?doc=II-2", doc:{key, siglum, title:{ja,en,fr}, status}})
         で、押した要素の下に小さなメニュー（〈リンクをコピー〉〈引用をコピー〉）を開く。もう一度押すか、外を押すか、Esc で閉じる。
         クリップボードが使えないときは、コピーする文を選べる形で出す。
       - status は "draft"（暫定版）・"text"（未注釈）・""（人の手で注釈した版）。文書単位の引用には、その文書の最終更新日を添える。
   3) 文書ごとの解題（data/intros.json）
       <div class="doc-intro" data-intro="II-2" hidden></div> を置くと、data/intros.json の texts["II-2"] が reviewed: true の
       ときだけ、折りたためる「この文書について」を書き込んで表示する（要約・写本と頁・ほかの写し・言語と方言・潮流・文献）。
       {"see": "eugnostos"} の項目は、その項目を使う。reviewed が true でないとき・JSON を読めないときは隠したまま。
       下書き（reviewed: false）は表示しない。描くのは 1) と同じく fill()。
   ページ側のスクリプトは、このファイル（defer）より先に動くことがあるので、次の形で呼ぶ:
       (window.NHCTools ? f(window.NHCTools) : (window.NHCToolsQ = window.NHCToolsQ || []).push(f))
   文言は三言語の span（.l-ja / .l-en / .l-fr。表示の切替は assets/site.css）で書く。見た目は assets/site.css の 6)。
   ============================================================ */
(function () {
  "use strict";
  var SITE = "https://sheneset.vercel.app/";   // release.json に url が無いときの公開 URL
  var cache = {};

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
  /* 一度だけ読む（読めなければ {}） */
  function once(url) {
    if (!cache[url]) cache[url] = getJSON(url).catch(function () { return {}; });
    return cache[url];
  }

  /* ---- 1) 写本の写真へのリンク ---- */
  var SOURCE = "Claremont, Nag Hammadi Archive";
  function photoLinks(el) {
    var codices = (el.getAttribute("data-codices") || "").split(/\s+/).filter(Boolean);
    if (!codices.length) return Promise.resolve();
    return once("data/facsimile_links.json").then(function (d) {
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
    });
  }

  /* ---- 3) 文書ごとの解題（data/intros.json）---- */
  var LABEL = {
    summary: ["要約", "Summary", "Résumé"], pages: ["写本と頁", "Codex and pages", "Codex et pages"],
    copies: ["ほかの写し", "Other copies", "Autres copies"], language: ["言語・方言", "Language and dialect", "Langue et dialecte"],
    current: ["潮流", "Current", "Courant"], refs: ["文献", "Literature", "Bibliographie"]
  };
  var CUR_ANCHOR = { ja: "ja-schools", en: "en-schools", fr: "fr-schools" };
  function introHTML(d, e) {
    var tr = function (o) { o = o || {}; return tri(esc(o.ja || ""), esc(o.en || o.ja || ""), esc(o.fr || o.en || o.ja || "")); };
    var has = function (o) { return o && (o.ja || o.en || o.fr); };
    var rows = [];
    if (has(e.summary)) rows.push(["summary", tr(e.summary)]);
    if (has(e.pages)) rows.push(["pages", tr(e.pages)]);
    if (has(e.copies)) rows.push(["copies", tr(e.copies)]);
    if (has(e.language)) rows.push(["language", tr(e.language)]);
    var cur = e.current && d.currents && d.currents[e.current];
    if (cur) rows.push(["current", tri('<a href="gnosticism.html#' + CUR_ANCHOR.ja + '">' + esc(cur.ja) + "</a>",
      '<a href="gnosticism.html#' + CUR_ANCHOR.en + '">' + esc(cur.en || cur.ja) + "</a>", '<a href="gnosticism.html#' + CUR_ANCHOR.fr + '">' + esc(cur.fr || cur.en || cur.ja) + "</a>")]);
    var refs = (e.refs || []).map(function (r) {
      var c = d.references && d.references[r.key]; if (!c) return "";
      /* vol は、全巻をまとめた書誌のうち、その文書を収める巻（書誌の末尾の句読点のあとに付くので括弧に入れる） */
      return "<li>" + esc(c) + (r.vol ? tri("（第" + esc(r.vol) + "巻に収録）", " (in vol. " + esc(r.vol) + ")", " (dans le vol. " + esc(r.vol) + ")") : "") + "</li>";
    }).filter(Boolean);
    if (refs.length) rows.push(["refs", '<ul class="di-refs">' + refs.join("") + "</ul>"]);
    if (!rows.length) return "";
    return '<details class="doc-intro-box"><summary>' + tri("この文書について（解題）", "About this text", "À propos de ce texte") + "</summary><dl>" +
      rows.map(function (r) { var l = LABEL[r[0]]; return "<dt>" + tri(l[0], l[1], l[2]) + "</dt><dd>" + r[1] + "</dd>"; }).join("") + "</dl>" +
      '<p class="di-note">' + tri("解題は本プロジェクトによる短い紹介で、本文の解釈ではありません。",
        "A short introduction written by the project, not an interpretation of the text.",
        "Courte présentation rédigée par le projet, non une interprétation du texte.") + "</p></details>";
  }
  function intro(el) {
    var key = el.getAttribute("data-intro");
    if (!key) return Promise.resolve();
    return once("data/intros.json").then(function (d) {
      var texts = (d && d.texts) || {}, e = texts[key], seen = 0;
      while (e && e.see && texts[e.see] && seen++ < 3) e = texts[e.see];   // {"see": "eugnostos"} は参照先の項目を使う
      if (!e || e.reviewed !== true) { el.hidden = true; return; }        // 生田目が確かめたもの（reviewed: true）だけを出す
      var h = introHTML(d, e);
      if (!h) { el.hidden = true; return; }
      el.innerHTML = h; el.hidden = false;
    });
  }

  /* root の中の、まだ描いていない要素を描く */
  function fill(root) {
    var els = (root || document).querySelectorAll(".doc-photos[data-codices]:not([data-filled])");
    Array.prototype.forEach.call(els, function (el) { el.setAttribute("data-filled", ""); photoLinks(el); });
    var ins = (root || document).querySelectorAll(".doc-intro[data-intro]:not([data-filled])");
    Array.prototype.forEach.call(ins, function (el) { el.setAttribute("data-filled", ""); intro(el); });
  }

  /* ---- 2) 引用 ---- */
  var EDITION = {
    ja: "生田目心愛 編『Sheneset：ナグ・ハマディ写本コーパス』",
    en: "Kokoa Nabatame (ed.), Sheneset: A Digital TEI Edition of the Nag Hammadi Codices",
    fr: "Kokoa Nabatame (éd.), Sheneset : édition numérique TEI des codices de Nag Hammadi"
  };
  var TITLE = {   // 英・仏の書名（project.html では斜体にする）
    en: "Sheneset: A Digital TEI Edition of the Nag Hammadi Codices",
    fr: "Sheneset : édition numérique TEI des codices de Nag Hammadi"
  };
  var STATUS = { draft: { ja: "暫定版", en: "draft", fr: "provisoire" }, text: { ja: "未注釈", en: "unannotated", fr: "non annoté" } };

  function release() { return once("data/release.json"); }
  function docDates() { return once("data/doc_dates.json"); }
  function siteURL(rel) { return (rel && rel.url) || SITE; }
  /* サイトで選んでいる言語（ja・en・fr） */
  function lang() {
    var l = window.NHC && window.NHC.lang ? window.NHC.lang() : document.documentElement.getAttribute("data-lang");
    return l === "en" || l === "fr" ? l : "ja";
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function today() { var d = new Date(); return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }

  /* 引用文（文字だけ）。where は版番号のあとに続ける箇所（「NHC II,2 §3（暫定版）」など。空なら省く）、path はサイト内の場所 */
  function citation(rel, l, where, path) {
    var v = rel && rel.version ? "v" + rel.version : "";
    var head = l === "ja" ? EDITION.ja + v + (where ? (v ? ", " : "") + where : "")
                          : EDITION[l] + (v ? ", " + v : "") + (where ? ", " + where : "");
    var doi = rel && rel.doi ? "https://doi.org/" + rel.doi + ". " : "";
    var url = siteURL(rel) + (path || "");
    var t = today();
    return l === "ja" ? head + ". " + doi + url + "（" + t + " 閲覧）"
         : l === "fr" ? head + ". " + doi + url + " (consulté le " + t + ")."
         : head + ". " + doi + url + " (accessed " + t + ").";
  }
  /* project.html の引用欄用（HTML。英・仏は書名を斜体に） */
  function citationHTML(rel, l, where, path) {
    var h = esc(citation(rel, l, where, path));
    return TITLE[l] ? h.replace(esc(TITLE[l]), "<i>" + esc(TITLE[l]) + "</i>") : h;
  }
  /* 箇所の書き方に、暫定版・未注釈の印を添える */
  function withStatus(l, s, status) {
    var w = STATUS[status] && STATUS[status][l];
    return !w ? s : l === "ja" ? s + "（" + w + "）" : s + " (" + w + ")";
  }
  /* 文書単位の箇所: 略号・題名・（暫定版・最終更新日） */
  function docWhere(l, doc, updated) {
    var title = (doc.title && (doc.title[l] || doc.title.en || doc.title.ja)) || "";
    var st = STATUS[doc.status] && STATUS[doc.status][l];
    var note = [];
    if (st) note.push(st);
    if (updated) note.push(l === "ja" ? updated + " 更新" : l === "fr" ? "mis à jour le " + updated : "updated " + updated);
    if (l === "ja") {
      var t = !title ? "" : /『/.test(title) ? " " + title : "『" + title + "』";
      return doc.siglum + t + (note.length ? "（" + note.join("、") + "）" : "");
    }
    return doc.siglum + (title ? ", " + title : "") + (note.length ? " (" + note.join(", ") + ")" : "");
  }

  var pop = null, popAnchor = null;
  function place() {
    if (!pop || !popAnchor) return;
    var r = popAnchor.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    var x = Math.max(8, Math.min(r.left, window.innerWidth - w - 8));
    var y = r.bottom + 6;
    if (y + h > window.innerHeight - 8 && r.top - h - 6 > 8) y = r.top - h - 6;
    pop.style.left = Math.round(x) + "px";
    pop.style.top = Math.round(y) + "px";
  }
  function closeCite(back) {
    if (!pop) return;
    pop.parentNode.removeChild(pop);
    pop = null;
    window.removeEventListener("scroll", place, true);
    window.removeEventListener("resize", place);
    window.removeEventListener("hashchange", place);
    var a = popAnchor; popAnchor = null;
    if (a) a.removeAttribute("aria-expanded");
    if (back && a) { try { a.focus({ preventScroll: true }); } catch (e) {} }
  }
  function copyText(text, done, fail) {
    try {
      if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(done, fail); return; }
    } catch (e) {}
    fail();
  }
  function cite(anchor, info) {
    if (pop && popAnchor === anchor) { closeCite(); return; }   // もう一度押したら閉じる
    closeCite();
    popAnchor = anchor;
    anchor.setAttribute("aria-expanded", "true");
    pop = document.createElement("div");
    pop.className = "cite-pop";
    pop.setAttribute("role", "dialog");
    pop.innerHTML =
      '<div class="cp-h">' + (info.kind === "document" ? tri("この文書を引用", "Cite this text", "Citer ce texte")
                                                       : tri("この箇所を引用", "Cite this passage", "Citer ce passage")) +
      '<button type="button" class="cp-x" aria-label="×">×</button></div>' +
      '<div class="cp-acts"><button type="button" data-act="link">' + tri("リンクをコピー", "Copy link", "Copier le lien") + "</button>" +
      '<button type="button" data-act="cite">' + tri("引用をコピー", "Copy citation", "Copier la citation") + "</button></div>" +
      '<p class="cp-msg" aria-live="polite"></p><textarea class="cp-text" rows="4" readonly hidden></textarea>';
    // <body> ではなく <html> の直下に置く（<body> に transform（ページの表示時のフェードなど）が掛かっていると、
    // position:fixed の基準が画面ではなく <body> になり、メニューが押した場所から離れてしまうため）
    document.documentElement.appendChild(pop);
    place();
    // 押した要素が動いたら（スクロール、§ のリンクによる移動、画面の大きさの変化）付いていく。
    // 移動のすぐあとはスクロールのイベントが遅れることがあるので、少しあとにも置き直す
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    window.addEventListener("hashchange", place);
    [60, 300].forEach(function (ms) { setTimeout(place, ms); });
    var msg = pop.querySelector(".cp-msg"), ta = pop.querySelector(".cp-text");
    pop.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest("button") : null;
      if (!b) return;
      if (b.classList.contains("cp-x")) { closeCite(true); return; }
      var act = b.getAttribute("data-act");
      Promise.all([release(), info.kind === "document" ? docDates() : null]).then(function (r) {
        var rel = r[0], l = lang(), where;
        if (info.kind === "document") {
          var d = r[1] && r[1].docs && r[1].docs[info.doc.key];
          where = docWhere(l, info.doc, d && d.updated);
        } else {
          where = info.where[l] || info.where.en || info.where.ja;
        }
        var text = act === "link" ? siteURL(rel) + info.path : citation(rel, l, where, info.path);
        ta.hidden = true;
        copyText(text, function () {
          msg.innerHTML = act === "link" ? tri("リンクをコピーしました。", "Link copied.", "Lien copié.")
                                         : tri("引用をコピーしました。", "Citation copied.", "Citation copiée.");
        }, function () {
          ta.value = text; ta.hidden = false;
          msg.innerHTML = tri("コピーできませんでした。下の文を選んでコピーしてください。", "Could not copy. Select the text below and copy it.",
            "Copie impossible. Sélectionnez le texte ci-dessous pour le copier.");
          place();
          try { ta.focus({ preventScroll: true }); } catch (e2) {}
          ta.select();
        });
      });
    });
    var first = pop.querySelector("[data-act]");
    if (first) { try { first.focus({ preventScroll: true }); } catch (e) {} }
  }
  document.addEventListener("click", function (e) {
    if (pop && !pop.contains(e.target) && !(popAnchor && popAnchor.contains(e.target))) closeCite();
  }, true);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && pop) closeCite(true); });

  var api = {
    fill: fill, esc: esc, tri: tri, getJSON: getJSON,
    release: release, docDates: docDates, siteURL: siteURL, lang: lang, today: today,
    citation: citation, citationHTML: citationHTML, withStatus: withStatus, docWhere: docWhere,
    cite: cite, closeCite: closeCite
  };
  window.NHCTools = api;
  fill(document);
  release(); // 引用の情報は先に読んでおく（メニューを開いたときに待たない）
  var q = window.NHCToolsQ || [];
  window.NHCToolsQ = { push: function (f) { f(api); } };
  q.forEach(function (f) { try { f(api); } catch (e) { console.error(e); } });
})();
