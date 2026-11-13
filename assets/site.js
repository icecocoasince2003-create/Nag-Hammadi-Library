/* ============================================================
   site.js — サイト共通スクリプト
   - 全ページの最上部に共通ナビ（#sitebar）を描画します。
     ナビ項目を増やすときは下の NAV に1行足すだけで全ページに反映されます。
   - 表示言語（日本語 / English / Français）を localStorage に保存し、
     ページ間で引き継ぎます。
       * 三言語対応ページ（<html data-i18n="full">）: html[data-lang] を ja/en/fr に切替
       * 既存のビュワー・検索・統計（日英のみ）: ページ内の #langBtn / #tlBtn を操作して同期
         （French を選ぶと UI は英語、語釈・対訳はフランス語になります）
   - ナビ右端の〈ログイン〉は assets/community.js が制御します。
   ============================================================ */
(function () {
  "use strict";
  var KEY = "nhc-lang";
  var LANGS = ["ja", "en", "fr"];
  var H = document.documentElement;

  /* ---- ナビ項目（href, 日, 英, 仏）---- */
  var NAV = [
    { id: "home",   href: "index.html",          ja: "HOME",            en: "Home",            fr: "Accueil" },
    { id: "corpus", href: "index.html#corpus",   ja: "文書一覧",         en: "Texts",           fr: "Textes" },
    { id: "search", href: "search.html",         ja: "コーパス検索",     en: "Corpus search",   fr: "Recherche" },
    { id: "stats",  href: "stats.html",          ja: "コーパス統計",     en: "Statistics",      fr: "Statistiques" },
    { id: "gnosis", href: "gnosticism.html",     ja: "グノーシス主義とは", en: "Gnosticism",      fr: "Le gnosticisme" },
    { id: "project",href: "project.html",        ja: "プロジェクト",     en: "About",           fr: "Le projet" },
    { id: "news",   href: "index.html#news",     ja: "NEWS",            en: "News",            fr: "Actualités" }
  ];
  var SITE = {
    ja: { name: "Sheneset", sub: "ナグ・ハマディ写本コーパス", nav: "サイト内ナビゲーション" },
    en: { name: "Sheneset", sub: "Digital TEI edition of the Nag Hammadi Codices", nav: "Site navigation" },
    fr: { name: "Sheneset", sub: "Édition numérique TEI des codices de Nag Hammadi", nav: "Navigation du site" }
  };

  function stored() {
    try { var v = localStorage.getItem(KEY); return LANGS.indexOf(v) >= 0 ? v : null; } catch (e) { return null; }
  }
  function store(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  function fullI18n() { return H.getAttribute("data-i18n") === "full"; }
  /* 三言語ページは <html data-title-en="…" data-title-fr="…"> でタイトルも切替（日本語は <title> の初期値） */
  var TITLE_JA = document.title;
  function applyTitle(v) {
    if (!fullI18n()) return;
    var tt = v === "ja" ? (H.getAttribute("data-title-ja") || TITLE_JA) : H.getAttribute("data-title-" + v);
    if (tt) document.title = tt;
  }

  /* 現在の表示言語（ナビの表示に使う） */
  function lang() {
    if (fullI18n()) return H.getAttribute("data-lang") || "ja";
    var s = stored();
    if (s) return s;
    return H.getAttribute("data-lang") === "en" ? "en" : "ja";
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function pageId() {
    var p = (location.pathname.split("/").pop() || "index.html").toLowerCase();
    if (p === "" || p === "index.html") return "home";
    if (p.indexOf("search") === 0) return "search";
    if (p.indexOf("stats") === 0) return "stats";
    if (p.indexOf("gnosticism") === 0) return "gnosis";
    if (p.indexOf("project") === 0) return "project";
    return "";
  }

  function render(nav) {
    var L = lang(), S = SITE[L] || SITE.ja, cur = pageId();
    nav.setAttribute("aria-label", S.nav);
    nav.innerHTML =
      '<a class="sb-brand" href="index.html"><img src="image/icon.svg" alt="" width="26" height="26" onerror="this.style.display=\'none\'">' +
      '<span class="sb-name"><b><span class="cop">ϣⲉⲛⲉⲥⲏⲧ</span>' + esc(S.name) + '</b><small>' + esc(S.sub) + '</small></span></a>' +
      '<div class="sb-links">' + NAV.map(function (n) {
        return '<a class="sb-link" data-nav="' + n.id + '" href="' + n.href + '"' + (n.id === cur ? ' aria-current="page"' : "") + '>' + esc(n[L] || n.ja) + '</a>';
      }).join("") + '</div>' +
      '<div class="sb-tools">' +
        LANGS.map(function (v) {
          var lab = { ja: "日本語", en: "EN", fr: "FR" }[v];
          return '<button type="button" class="sb-lang" data-lang="' + v + '" aria-pressed="' + (v === L) + '" lang="' + v + '">' + lab + '</button>';
        }).join("") +
        '<span class="sb-sep" aria-hidden="true"></span>' +
        '<a class="sb-auth" id="sbAuth" href="#" hidden></a>' +
      '</div>';
    Array.prototype.forEach.call(nav.querySelectorAll(".sb-lang"), function (b) {
      b.addEventListener("click", function () { setLang(b.getAttribute("data-lang")); });
    });
    document.dispatchEvent(new CustomEvent("nhc:sitebar"));
  }

  /* ---- 既存（日英）ページとの同期 ---- */
  function syncLegacy(target) {
    var lb = document.getElementById("langBtn");
    if (!lb) return;
    var wantUI = target === "ja" ? "ja" : "en";
    var curUI = H.getAttribute("data-lang") === "en" ? "en" : "ja";
    if (curUI !== wantUI) lb.click();
    var tb = document.getElementById("tlBtn");
    if (tb) {
      var want = target; // ja / en / fr
      for (var i = 0; i < 3 && (H.getAttribute("data-tl") || "ja") !== want; i++) tb.click();
    }
  }

  function setLang(v) {
    if (LANGS.indexOf(v) < 0) return;
    store(v);
    if (fullI18n()) {
      H.setAttribute("data-lang", v);
      H.setAttribute("lang", v);
      applyTitle(v);
    } else {
      syncLegacy(v);
    }
    var nav = document.getElementById("sitebar");
    if (nav) render(nav);
    document.dispatchEvent(new CustomEvent("nhc:lang", { detail: { lang: v } }));
  }

  function mount() {
    var nav = document.getElementById("sitebar");
    if (!nav) {
      nav = document.createElement("nav");
      nav.id = "sitebar";
      var app = document.querySelector("body > .app");
      if (app) app.insertBefore(nav, app.firstChild);
      else document.body.insertBefore(nav, document.body.firstChild);
    }
    nav.classList.add("sitebar");
    // 他に固定ヘッダーを持たないページではナビを上部に固定
    var otherHeader = document.querySelector("body > header, body > .app > header");
    if (!otherHeader) nav.classList.add("sticky");

    var s = stored();
    if (fullI18n()) {
      var v = s || H.getAttribute("data-lang") || "ja";
      H.setAttribute("data-lang", v); H.setAttribute("lang", v); applyTitle(v);
    } else if (s && s !== "ja") {
      // ページ本体のスクリプトが初期化を終えてから同期する
      setTimeout(function () { syncLegacy(s); render(nav); }, 0);
    }
    // 既存ページ内の言語ボタンを押した場合も保存して引き継ぐ
    var lb = document.getElementById("langBtn");
    if (lb && !fullI18n()) {
      lb.addEventListener("click", function () {
        setTimeout(function () {
          var ui = H.getAttribute("data-lang") === "en" ? "en" : "ja";
          var tl = H.getAttribute("data-tl");
          var v = ui === "en" && tl === "fr" ? "fr" : ui;
          store(v);
          render(nav);
          document.dispatchEvent(new CustomEvent("nhc:lang", { detail: { lang: v } }));
        }, 0);
      });
    }
    render(nav);
    wireXmlMenus();
    followSegHash();
  }

  /* ---- ビュワーの〈⤓ XML〉メニュー（参照している XML のダウンロード）---- */
  function fmtSize(n) { return n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB"; }
  function wireXmlMenus() {
    Array.prototype.forEach.call(document.querySelectorAll(".xmlmenu"), function (m) {
      var btn = m.querySelector(".xmlmenu-btn"), pop = m.querySelector(".xmlmenu-pop");
      if (!btn || !pop || m.dataset.wired) return;
      m.dataset.wired = "1";
      var sized = false;
      function close() { pop.hidden = true; btn.setAttribute("aria-expanded", "false"); }
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var open = pop.hidden;
        pop.hidden = !open; btn.setAttribute("aria-expanded", String(open));
        if (open && !sized) {
          sized = true;
          Array.prototype.forEach.call(pop.querySelectorAll("a[download]"), function (a) {
            var sm = a.querySelector("[data-size]"); if (!sm || !window.fetch) return;
            fetch(a.getAttribute("href"), { method: "HEAD", cache: "no-store" }).then(function (r) {
              var n = +r.headers.get("content-length"); if (n) sm.textContent = fmtSize(n);
            }).catch(function () {});
          });
        }
      });
      pop.addEventListener("click", function (e) { if (e.target.closest("a,button")) setTimeout(close, 0); });
      document.addEventListener("click", function (e) { if (!m.contains(e.target)) close(); });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
    });
  }

  /* ---- #seg-… へのリンクで開いたとき、本文の描画（非同期）を待って該当箇所へ移動 ---- */
  function followSegHash() {
    if (!/^#seg-/.test(location.hash)) return;
    var reading = document.getElementById("reading");
    if (!reading || !window.MutationObserver) return;
    var id = decodeURIComponent(location.hash.slice(1)), done = false;
    function go() {
      if (done) return;
      var el = document.getElementById(id); if (!el) return;
      done = true; obs.disconnect();
      setTimeout(function () {
        el.scrollIntoView({ block: "center" }); el.classList.add("flash");
        setTimeout(function () { el.classList.remove("flash"); }, 2200);
      }, 80);
    }
    var obs = new MutationObserver(go);
    obs.observe(reading, { childList: true });
    go();
    setTimeout(function () { obs.disconnect(); }, 20000);
  }

  window.NHC = window.NHC || {};
  window.NHC.lang = lang;
  window.NHC.setLang = setLang;
  window.NHC.esc = esc;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
