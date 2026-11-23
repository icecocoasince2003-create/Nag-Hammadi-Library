/* ============================================================
   site.js — サイト共通スクリプト
   - 全ページの最上部に共通ナビ（#sitebar）を描画します。
     ナビ項目を増やすときは下の NAV に1行足すだけで全ページに反映されます。
   - 表示言語（日本語 / English / Français）はナビ右側のプルダウン（〈地球の印 日本語 ▾〉）で選び、localStorage に保存して
     ページ間で引き継ぎます。最初に開くときの言語は、URL の ?lang=（ja・en・fr）＞ 保存値 ＞ ブラウザーの言語の順で決めます
     （ブラウザーの言語が ja・en・fr のどれでもなければ英語）。各ページの <head> の 1 行スクリプトが、同じ順で描画前に反映します。
       * 三言語対応ページ（<html data-i18n="full">）: html[data-lang] を ja/en/fr に切替
       * 既存のビュワー（日英のみ）: ページ内の #langBtn / #tlBtn を操作して同期
         （French を選ぶと UI は英語、語釈・対訳はフランス語になります）
   - 表示モード（ライト／ダーク）に対応したページ（<html data-modes="light dark">）では、
     ナビ右側に切替ボタンを出し、選択を localStorage に保存します（配色は assets/cosmos.css）。
   - ナビ右端の〈ログイン〉は assets/community.js が制御します。
   - ビュワー（.app > header を持つページ）では、ナビ左端に ☰ を出して
     左の「文書パネル」を開閉します（見た目は assets/site.css の 2)）。
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
    { id: "lexicon",href: "lexicon.html",        ja: "辞書",            en: "Lexicon",         fr: "Lexique" },
    { id: "search", href: "search.html",         ja: "検索・統計",        en: "Search",          fr: "Recherche" },
    { id: "guide",  href: "guide.html",          ja: "はじめての方へ",    en: "Getting started", fr: "Premiers pas" },
    { id: "gnosis", href: "gnosticism.html",     ja: "グノーシス主義とは", en: "Gnosticism",      fr: "Le gnosticisme" },
    { id: "project",href: "project.html",        ja: "プロジェクト",     en: "About",           fr: "Le projet" },
    { id: "news",   href: "index.html#news",     ja: "NEWS",            en: "News",            fr: "Actualités" }
  ];
  var SITE = {
    ja: { name: "Sheneset", sub: "ナグ・ハマディ写本コーパス", nav: "サイト内ナビゲーション", panel: "文書メニュー（表示・ツール）", menu: "メニュー" },
    en: { name: "Sheneset", sub: "Digital TEI edition of the Nag Hammadi Codices", nav: "Site navigation", panel: "Document menu (display and tools)", menu: "Menu" },
    fr: { name: "Sheneset", sub: "Édition numérique TEI des codices de Nag Hammadi", nav: "Navigation du site", panel: "Menu du document (affichage et outils)", menu: "Menu" }
  };

  function stored() {
    try { var v = localStorage.getItem(KEY); return LANGS.indexOf(v) >= 0 ? v : null; } catch (e) { return null; }
  }
  function store(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  /* ---- 最初に表示する言語 ----
     URL の ?lang=（ja・en・fr）＞ 保存値 ＞ ブラウザーの言語（navigator.languages を先頭から見て、ja・en・fr のどれかに
     当たったもの。どれにも当たらなければ英語）。URL で指定された言語は保存値にも書き込む（ほかのページに移っても同じ言語が続く）。
     言語を切り替えても URL は書き換えない。各ページの <head> の 1 行スクリプト（build_site.py の LANG_BOOT と同じもの）が、
     同じ順で描画前に反映している（日本語が一瞬出るのを防ぐ）。順や書き方を変えるときは、そちらも合わせること。 */
  function urlLang() {
    var m = /[?&]lang=([^&#]*)/i.exec(location.search);
    var v = m ? m[1].toLowerCase() : null;
    return LANGS.indexOf(v) >= 0 ? v : null;
  }
  function browserLang() {
    var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
    for (var i = 0; i < list.length; i++) {
      var p = String(list[i]).toLowerCase().split(/[-_]/)[0];
      if (LANGS.indexOf(p) >= 0) return p;
    }
    return "en";
  }
  function initialLang() {
    var u = urlLang();
    if (u) { store(u); return u; }
    return stored() || browserLang();
  }
  var cur = null;   // 選択中の言語（mount で決める。日英だけのビュワーでも ja / en / fr のどれか）
  function fullI18n() { return H.getAttribute("data-i18n") === "full"; }
  /* 三言語ページは <html data-title-en="…" data-title-fr="…"> でタイトルも切替（日本語は <title> の初期値） */
  var TITLE_JA = document.title;
  function applyTitle(v) {
    if (!fullI18n()) return;
    var tt = v === "ja" ? (H.getAttribute("data-title-ja") || TITLE_JA) : H.getAttribute("data-title-" + v);
    if (tt) document.title = tt;
  }

  /* 入力欄の案内文（placeholder）は属性に書けるのが 1 つの言語だけなので、data-ph-ja / data-ph-en / data-ph-fr を持つ要素に
     表示言語のものを入れる（三言語のページ。ほかの言語が無ければ英語、次に日本語） */
  function applyPlaceholders(v) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-ph-ja]"), function (el) {
      var p = el.getAttribute("data-ph-" + v) || el.getAttribute("data-ph-en") || el.getAttribute("data-ph-ja");
      el.setAttribute("placeholder", p);
      if (el.hasAttribute("data-ph-label")) el.setAttribute("aria-label", p);
    });
  }

  /* 現在の表示言語（ナビの表示に使う） */
  function lang() {
    if (fullI18n()) return H.getAttribute("data-lang") || "ja";
    if (cur) return cur;
    var s = stored();
    if (s) return s;
    return H.getAttribute("data-lang") === "en" ? "en" : "ja";
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---- 表示モード（ライト／ダーク）----
     対応しているページ（<html data-modes="light dark">）にだけ、ナビ右側に切替ボタンを出す。
     html[data-mode] を light / dark に切り替え、選択を localStorage "nhc-mode" に保存する（保存がなければダーク）。
     配色は assets/cosmos.css の「ライトモード」。対応ページは <head> の1行スクリプトで保存値を描画前に反映する
     （ちらつき防止）。切り替えたときは document に "nhc:mode" を送る（assets/cosmos.js が星野を止める／再開する）。 */
  var MODE_KEY = "nhc-mode";
  var MODE_TEXT = {
    ja: { light: "ライトモードに切り替え", dark: "ダークモードに切り替え" },
    en: { light: "Switch to light mode", dark: "Switch to dark mode" },
    fr: { light: "Passer en mode clair", dark: "Passer en mode sombre" }
  };
  /* ボタンの絵は「押すと切り替わる先」: ダーク表示中は太陽、ライト表示中は月（出し分けは site.css） */
  var MODE_ICONS =
    '<svg class="sb-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">' +
      '<circle cx="12" cy="12" r="4"/><path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.5 1.5M17.1 17.1l1.5 1.5M5.4 18.6l1.5-1.5M17.1 6.9l1.5-1.5"/></svg>' +
    '<svg class="sb-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M20.5 13.4A8.6 8.6 0 1 1 10.6 3.5a7.2 7.2 0 0 0 9.9 9.9z"/></svg>';
  function hasModes() {
    var m = (H.getAttribute("data-modes") || "").split(/\s+/);
    return m.indexOf("light") >= 0 && m.indexOf("dark") >= 0;
  }
  function mode() { return H.getAttribute("data-mode") === "light" ? "light" : "dark"; }
  function storedMode() {
    try { var v = localStorage.getItem(MODE_KEY); return v === "light" || v === "dark" ? v : null; } catch (e) { return null; }
  }
  var curMode = mode();   // 選択中のモード（切替のフェード中は html[data-mode] より先に変わる）
  function modeLabel() { return (MODE_TEXT[lang()] || MODE_TEXT.ja)[curMode === "light" ? "dark" : "light"]; }
  /* 選択中のモード（curMode）を画面に反映する。何度呼んでも、どの順で呼ばれても結果は同じ */
  function applyMode() {
    H.setAttribute("data-mode", curMode);
    var b = document.getElementById("sbMode");
    if (b) { b.setAttribute("aria-label", modeLabel()); b.title = modeLabel(); }
    document.dispatchEvent(new CustomEvent("nhc:mode", { detail: { mode: curMode } }));
  }
  function setMode(v) {
    if (!hasModes() || (v !== "light" && v !== "dark")) return;
    try { localStorage.setItem(MODE_KEY, v); } catch (e) {}
    if (v === curMode) return;
    curMode = v;
    // 対応ブラウザでは画面全体をクロスフェードで切り替える。「視差効果を減らす」設定のときと、
    // 画面が表示されていないとき（フェードが中断され、反映も遅れる）は即時に切り替える
    var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (document.startViewTransition && !still && document.visibilityState === "visible") {
      try {
        var vt = document.startViewTransition(applyMode);
        // フェードが途中で打ち切られても（タブを切り替えた等）切替そのものは済むので、その通知は無視する
        if (vt && vt.ready) vt.ready.catch(function () {});
        if (vt && vt.finished) vt.finished.catch(function () {});
        return;
      } catch (e) {}
    }
    applyMode();
  }

  /* ---- 表示言語のプルダウン ----
     ナビ右側のボタン〈地球の印・選択中の言語・▾〉を押すと、その下に 日本語 / English / Français の一覧が開く。
     WAI-ARIA のメニューボタンの作法に従う: ボタンは aria-expanded、一覧は role="menu"、各言語は role="menuitemradio"
     （選択中は aria-checked="true"）。開くと選択中の言語にフォーカスし、↑↓・Home・End で移動、Enter・Space で選ぶ。
     Esc で閉じてボタンに戻り、Tab や一覧の外を押しても閉じる。選ぶと setLang がナビを描き直すので、フォーカスは新しいボタンに戻す。
     見た目は assets/site.css の .sb-langsel。 */
  var LANG_NAME = { ja: "日本語", en: "English", fr: "Français" };
  var LANG_LABEL = { ja: "表示言語", en: "Language", fr: "Langue" };
  var LANG_COLON = { ja: "：", en: ": ", fr: " : " };   // 読み上げ用の「表示言語：日本語」の区切り
  var GLOBE_ICON =
    '<svg class="sb-globe" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">' +
      '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.4 2.5 3.6 5.5 3.6 9s-1.2 6.5-3.6 9c-2.4-2.5-3.6-5.5-3.6-9S9.6 5.5 12 3z"/></svg>';
  var CARET_ICON =
    '<svg class="sb-caret" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M1 1l4 4 4-4"/></svg>';
  var CHECK_ICON =
    '<svg class="sb-check" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M2.4 6.3l2.4 2.4 4.8-5.2"/></svg>';
  function langMenuHtml(L) {
    var lab = LANG_LABEL[L] || LANG_LABEL.ja;
    return '<div class="sb-langsel">' +
      '<button type="button" class="sb-langbtn" id="sbLang" data-lang="' + L + '" aria-haspopup="true" aria-expanded="false" aria-controls="sbLangMenu" title="' + esc(lab) + '">' +
        GLOBE_ICON + '<span class="vh">' + esc(lab + (LANG_COLON[L] || ": ")) + '</span>' +
        '<span class="sb-langcur" lang="' + L + '">' + esc(LANG_NAME[L]) + '</span>' + CARET_ICON + '</button>' +
      '<div class="sb-langmenu" id="sbLangMenu" role="menu" aria-label="' + esc(lab) + '" hidden>' +
        LANGS.map(function (v) {
          return '<button type="button" class="sb-langopt" role="menuitemradio" tabindex="-1" data-lang="' + v + '" lang="' + v +
            '" aria-checked="' + (v === L) + '">' + CHECK_ICON + '<span>' + esc(LANG_NAME[v]) + '</span></button>';
        }).join("") +
      '</div></div>';
  }
  function langMenuOpen() { var m = document.getElementById("sbLangMenu"); return !!m && !m.hidden; }
  function openLangMenu() {
    var b = document.getElementById("sbLang"), m = document.getElementById("sbLangMenu");
    if (!b || !m) return;
    m.hidden = false;
    b.setAttribute("aria-expanded", "true");
    var it = m.querySelector('[aria-checked="true"]') || m.querySelector('[role="menuitemradio"]');
    if (it) it.focus();
  }
  function closeLangMenu(refocus) {
    var b = document.getElementById("sbLang"), m = document.getElementById("sbLangMenu");
    if (!b || !m || m.hidden) return;
    m.hidden = true;
    b.setAttribute("aria-expanded", "false");
    if (refocus) b.focus();
  }
  function wireLangMenu(nav) {
    var b = nav.querySelector("#sbLang"), m = nav.querySelector("#sbLangMenu");
    if (!b || !m) return;
    var items = Array.prototype.slice.call(m.querySelectorAll('[role="menuitemradio"]'));
    b.addEventListener("click", function () { if (m.hidden) openLangMenu(); else closeLangMenu(false); });
    b.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); openLangMenu(); }
    });
    m.addEventListener("keydown", function (e) {
      var i = items.indexOf(document.activeElement), n = items.length, j = -1;
      if (e.key === "ArrowDown") j = (i + 1) % n;
      else if (e.key === "ArrowUp") j = i < 0 ? n - 1 : (i - 1 + n) % n;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = n - 1;
      else if (e.key === "Escape") {
        // ビュワーのドロワーなど、Esc で閉じるほかのものには渡さない（閉じるのは一覧だけ）
        e.preventDefault(); e.stopPropagation(); closeLangMenu(true); return;
      } else if (e.key === "Tab") { closeLangMenu(false); return; }
      if (j >= 0) { e.preventDefault(); items[j].focus(); }
    });
    items.forEach(function (it) {
      it.addEventListener("click", function () {
        var v = it.getAttribute("data-lang");
        closeLangMenu(true);   // フォーカスをボタンに戻す。setLang でナビを描き直しても、render が新しいボタンに戻す
        if (v !== lang()) setLang(v);
      });
    });
  }
  /* 一覧の外を押す・フォーカスが外に出る・Esc で閉じる（ナビは描き直されるので、document で一度だけ受ける）。
     タップでも閉じるよう click ではなく pointerdown で見る（iOS では文字の上のタップで click が document まで届かない） */
  function wireLangMenuGlobal() {
    function outside(t) { var w = document.querySelector("#sitebar .sb-langsel"); return !w || !w.contains(t); }
    document.addEventListener(window.PointerEvent ? "pointerdown" : "mousedown", function (e) {
      if (langMenuOpen() && outside(e.target)) closeLangMenu(false);
    });
    document.addEventListener("focusin", function (e) {
      if (langMenuOpen() && outside(e.target)) closeLangMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && langMenuOpen()) closeLangMenu(!outside(document.activeElement));
    });
  }

  /* ---- 狭い画面（幅 760px 以下）のサイトメニュー ----
     ナビのリンク（NAV の 8 項目）は、広い画面では横に並べ、幅 760px 以下では 2 段目の〈メニュー ▾〉ボタンにまとめる
     （以前は 2 段目を横にスクロールさせていたが、幅 390px では「グノーシス主義とは」から先が画面の外にあり、気づきにくかった）。
     WAI-ARIA の disclosure の作法: ボタンは aria-expanded と aria-controls を持ち、押すとリンクの一覧がナビのすぐ下に縦に並んで開く。
     リンクへは普通に Tab で進む。Esc（フォーカスはボタンに戻る）・一覧の外を押す・フォーカスがナビの外に出る・リンクを選ぶ、で閉じる。
     幅 761px 以上ではボタンを出さず、一覧は常に見える。境界の 760px は assets/site.css の 1) の @media とそろえること。 */
  var MENU_NARROW = "(max-width: 760px)";
  var menuOpen = false;
  function setMenu(open, refocus) {
    var nav = document.getElementById("sitebar"), b = document.getElementById("sbMenu");
    menuOpen = !!open;
    if (nav) nav.classList.toggle("menu-open", menuOpen);
    if (b) {
      b.setAttribute("aria-expanded", String(menuOpen));
      if (refocus) b.focus();
    }
  }
  function wireMenuGlobal() {
    var nav = document.getElementById("sitebar");
    function outside(t) { return !nav || !nav.contains(t); }
    document.addEventListener(window.PointerEvent ? "pointerdown" : "mousedown", function (e) {
      if (menuOpen && outside(e.target)) setMenu(false);
    });
    document.addEventListener("focusin", function (e) {
      if (menuOpen && outside(e.target)) setMenu(false);
    });
    // Esc は捕捉の段階で受ける（ビュワーのドロワーなど、Esc で閉じるほかのものには渡さない）
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || !menuOpen) return;
      e.preventDefault(); e.stopPropagation();
      setMenu(false, !outside(document.activeElement));
    }, true);
    if (window.matchMedia) {
      var mq = window.matchMedia(MENU_NARROW), off = function () { if (!mq.matches) setMenu(false); };
      if (mq.addEventListener) mq.addEventListener("change", off); else if (mq.addListener) mq.addListener(off);
    }
  }

  function pageId() {
    var p = (location.pathname.split("/").pop() || "index.html").toLowerCase();
    if (p === "" || p === "index.html") return "home";
    if (p.indexOf("search") === 0) return "search";
    if (p.indexOf("stats") === 0) return "search";   // 旧 stats.html（search.html?view=stats への転送）
    if (p.indexOf("lexicon") === 0) return "lexicon";
    if (p.indexOf("guide") === 0) return "guide";
    if (p.indexOf("gnosticism") === 0) return "gnosis";
    if (p.indexOf("project") === 0) return "project";
    return "";
  }

  function render(nav) {
    var L = lang(), S = SITE[L] || SITE.ja, cur = pageId();
    // 描き直す前にナビの中のボタン（id のあるもの）にフォーカスがあれば、描き直した後も同じボタンに戻す
    // （言語を選んだ後。日英のビュワーでは #langBtn の処理がもう一度描き直す）
    var ae = document.activeElement, keep = ae && ae.id && nav.contains(ae) ? ae.id : "";
    nav.setAttribute("aria-label", S.nav);
    nav.innerHTML =
      (panel ? '<button type="button" class="sb-panel" id="sbPanel" aria-controls="' + esc(panel.id) + '" aria-expanded="' + panelShown() +
        '" aria-label="' + esc(S.panel) + '" title="' + esc(S.panel) + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
        'stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>' : "") +
      '<a class="sb-brand" href="index.html"><img src="image/icon.svg" alt="" width="26" height="26" onerror="this.style.display=\'none\'">' +
      '<span class="sb-name"><b><span class="cop" lang="cop">ϣⲉⲛⲉⲥⲏⲧ</span>' + esc(S.name) + '</b><small>' + esc(S.sub) + '</small></span></a>' +
      '<div class="sb-menu"><button type="button" class="sb-menubtn" id="sbMenu" aria-expanded="' + menuOpen + '" aria-controls="sbLinks">' +
        '<span>' + esc(S.menu) + '</span>' + CARET_ICON + '</button></div>' +
      '<div class="sb-links" id="sbLinks">' + NAV.map(function (n) {
        return '<a class="sb-link" data-nav="' + n.id + '" href="' + n.href + '"' + (n.id === cur ? ' aria-current="page"' : "") + '>' + esc(n[L] || n.ja) + '</a>';
      }).join("") + '</div>' +
      '<div class="sb-tools">' +
        langMenuHtml(L) +
        // 表示モードの切替は言語と同じ「表示の設定」なので、言語の隣に区切り線なしで置く（ナビの幅も節約できる）
        (hasModes() ? '<button type="button" class="sb-mode" id="sbMode" aria-label="' + esc(modeLabel()) + '" title="' + esc(modeLabel()) + '">' +
          MODE_ICONS + '</button>' : "") +
        '<span class="sb-sep" aria-hidden="true"></span>' +
        '<a class="sb-auth" id="sbAuth" href="#" hidden></a>' +
      '</div>';
    wireLangMenu(nav);
    nav.classList.toggle("menu-open", menuOpen);
    nav.querySelector("#sbMenu").addEventListener("click", function () { setMenu(!menuOpen); });
    // 一覧のリンクを選んだら閉じる（HOME の「NEWS」のように同じページの中へ移るときのため）
    nav.querySelector("#sbLinks").addEventListener("click", function (e) { if (e.target.closest("a")) setMenu(false); });
    var mb = nav.querySelector(".sb-mode");
    if (mb) mb.addEventListener("click", function () { setMode(curMode === "light" ? "dark" : "light"); });
    if (panel) {
      panel.setAttribute("aria-label", S.panel);
      nav.querySelector(".sb-panel").addEventListener("click", togglePanel);
    }
    var kept = keep && document.getElementById(keep);
    if (kept && nav.contains(kept)) { try { kept.focus({ preventScroll: true }); } catch (e) { kept.focus(); } }
    document.dispatchEvent(new CustomEvent("nhc:sitebar"));
  }

  /* ---- ビュワーの文書パネル（.app > header）の開閉 ----
     幅 1100px 以上: 本文の左に常時表示。☰ で折りたたみ（html[data-panel="off"]、localStorage に保存）
     それより狭い画面: ☰ で左から開くドロワー（html[data-drawer="open"]）。背景・Esc・移動系の操作で閉じる
     見た目は assets/site.css の 2)。PANEL_WIDE は site.css の @media と揃えること。 */
  var PANEL_KEY = "nhc-panel", PANEL_WIDE = "(min-width: 1100px)";
  var panel = null;
  function panelWide() { return !!(window.matchMedia && window.matchMedia(PANEL_WIDE).matches); }
  function panelShown() {
    return panelWide() ? H.getAttribute("data-panel") !== "off" : H.getAttribute("data-drawer") === "open";
  }
  function syncPanelBtn() {
    var b = document.getElementById("sbPanel");
    if (b) b.setAttribute("aria-expanded", String(panelShown()));
  }
  function setDrawer(open, moveFocus) {
    if (open) H.setAttribute("data-drawer", "open"); else H.removeAttribute("data-drawer");
    syncPanelBtn();
    if (!moveFocus) return;
    var t = open ? panel : document.getElementById("sbPanel");
    if (t) { try { t.focus({ preventScroll: true }); } catch (e) { t.focus(); } }
  }
  function togglePanel() {
    if (!panelWide()) { setDrawer(!panelShown(), true); return; }
    var off = panelShown();
    if (off) H.setAttribute("data-panel", "off"); else H.removeAttribute("data-panel");
    try { if (off) localStorage.setItem(PANEL_KEY, "off"); else localStorage.removeItem(PANEL_KEY); } catch (e) {}
    syncPanelBtn();
  }
  function wirePanel() {
    panel = document.querySelector("body > .app > header");
    if (!panel) return;
    if (!panel.id) panel.id = "docpanel";
    panel.setAttribute("tabindex", "-1");
    try { if (localStorage.getItem(PANEL_KEY) === "off") H.setAttribute("data-panel", "off"); } catch (e) {}
    var back = document.createElement("div");
    back.className = "panel-back";
    panel.parentNode.insertBefore(back, panel);
    back.addEventListener("click", function () { setDrawer(false, false); });
    // ドロワー内で移動系の操作（リンク・写本タブ・関連など）をしたら閉じる。表示の切替と XML メニューでは開いたまま
    panel.addEventListener("click", function (e) {
      if (panelWide() || H.getAttribute("data-drawer") !== "open") return;
      var t = e.target.closest ? e.target.closest("a, button") : null;
      if (!t || t.matches("[aria-pressed], .xmlmenu-btn, a[download]")) return;
      setDrawer(false, false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && H.getAttribute("data-drawer") === "open") setDrawer(false, true);
    });
    window.addEventListener("resize", function () {
      if (panelWide()) H.removeAttribute("data-drawer");
      syncPanelBtn();
    });
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
      // <head> の 1 行スクリプトが言語を反映済みのときはボタンを押さないので、押した状態の表示だけ合わせる
      tb.setAttribute("aria-pressed", String((H.getAttribute("data-tl") || "ja") !== "ja"));
    }
  }

  function setLang(v) {
    if (LANGS.indexOf(v) < 0) return;
    cur = v;
    store(v);
    if (fullI18n()) {
      H.setAttribute("data-lang", v);
      H.setAttribute("lang", v);
      applyTitle(v);
      applyPlaceholders(v);
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
    wirePanel();

    // 表示モード: 保存値を反映（通常は <head> の1行スクリプトが描画前に済ませている）
    if (hasModes()) {
      curMode = storedMode() || mode();
      if (curMode !== mode()) applyMode();
    }

    var v = cur = initialLang();
    if (fullI18n()) {
      H.setAttribute("data-lang", v); H.setAttribute("lang", v); applyTitle(v); applyPlaceholders(v);
    } else {
      // ページ本体のスクリプトが初期化を終えてから同期する（<head> の 1 行スクリプトが反映済みなら、ボタンは押さない）
      setTimeout(function () { syncLegacy(v); render(nav); }, 0);
    }
    // 既存ページ内の言語ボタンを押した場合も保存して引き継ぐ
    var lb = document.getElementById("langBtn");
    if (lb && !fullI18n()) {
      lb.addEventListener("click", function () {
        setTimeout(function () {
          var ui = H.getAttribute("data-lang") === "en" ? "en" : "ja";
          var tl = H.getAttribute("data-tl");
          var v = ui === "en" && tl === "fr" ? "fr" : ui;
          cur = v;
          store(v);
          render(nav);
          document.dispatchEvent(new CustomEvent("nhc:lang", { detail: { lang: v } }));
        }, 0);
      });
    }
    render(nav);
    wireLangMenuGlobal();
    wireMenuGlobal();
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
  window.NHC.mode = function () { return curMode; };
  window.NHC.setMode = setMode;
  window.NHC.esc = esc;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
