/* ============================================================
   analytics.js — Google アナリティクス（GA4）と Cookie の同意バナー
   - 計測するのは本番（location.hostname が "sheneset.vercel.app"）だけです。
     localhost・プレビュー・旧ドメインでは何もしません（バナーも出しません）。
   - 同意の状態は localStorage の "nhc-analytics-consent" に "granted" / "denied" で保存します。
     "granted" のときだけ Google のスクリプト（gtag.js）を読み込みます。同意前は一切読み込みません。
   - 値が未保存なら、画面下部に同意バナーを出します（日・英・仏。上部ナビの言語切替に追従）。
   - window.NHC.analyticsSettings(): 保存値を消してバナーを出し直します
     （プライバシーポリシーの〈Cookie の設定を変更する〉から呼びます）。
     〈同意しない〉を選ぶと、_ga で始まる Cookie を削除します。
   測定 ID を変えるときは下の ID を、本番のドメインを変えるときは HOST を書き換えてください。
   ============================================================ */
(function () {
  "use strict";
  var ID = "G-2MQ5KPE69K";
  var HOST = "sheneset.vercel.app";
  var KEY = "nhc-analytics-consent";

  var NHC = window.NHC = window.NHC || {};

  /* 本番以外では何もしない（設定ボタンから呼ばれても黙って戻る） */
  if (location.hostname !== HOST) {
    NHC.analyticsSettings = function () { return false; };
    return;
  }

  /* ---- 文言（日・英・仏）---- */
  var TEXT = {
    ja: {
      msg: "本サイトでは、利用状況を把握して改善に役立てるため Google アナリティクス（Cookie）を使用します。同意いただいた場合のみ計測します。",
      yes: "同意する", no: "同意しない", more: "詳しく", href: "privacy.html#analytics", label: "Cookie の使用について"
    },
    en: {
      msg: "This site uses Google Analytics (cookies) to understand how it is used. We measure only if you agree.",
      yes: "Accept", no: "Decline", more: "Details", href: "privacy.html#analytics-en", label: "Cookie notice"
    },
    fr: {
      msg: "Ce site utilise Google Analytics (cookies) pour comprendre son utilisation. La mesure n’a lieu qu’avec votre accord.",
      yes: "Accepter", no: "Refuser", more: "En savoir plus", href: "privacy.html#analytics-fr", label: "Information sur les cookies"
    }
  };
  function lang() {
    var v = null;
    try { if (typeof NHC.lang === "function") v = NHC.lang(); } catch (e) {}
    if (!v) v = document.documentElement.getAttribute("data-lang");
    return TEXT.hasOwnProperty(v) ? v : "ja";
  }

  /* ---- 同意状態の保存 ---- */
  function read() {
    try { var v = localStorage.getItem(KEY); return v === "granted" || v === "denied" ? v : null; } catch (e) { return null; }
  }
  function write(v) {
    try { if (v) localStorage.setItem(KEY, v); else localStorage.removeItem(KEY); } catch (e) {}
  }

  /* ---- 計測の開始・停止 ---- */
  var loaded = false;
  function start() {
    window["ga-disable-" + ID] = false;
    if (loaded) return;
    loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", ID);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + ID;
    document.head.appendChild(s);
  }
  /* すでに読み込んだ gtag.js にも以後の送信をやめさせる（Google の公式のオプトアウト用フラグ） */
  function pause() { window["ga-disable-" + ID] = true; }
  /* _ga で始まる Cookie を削除する（どのドメイン指定で発行されていても消えるよう、候補を順に試す） */
  function clearCookies() {
    var names = [];
    document.cookie.split(";").forEach(function (c) {
      var n = c.split("=")[0].replace(/^\s+|\s+$/g, "");
      if (n.indexOf("_ga") === 0) names.push(n);
    });
    if (!names.length) return;
    var parts = location.hostname.split("."), domains = [""];
    for (var i = 0; i < parts.length - 1; i++) {
      var d = parts.slice(i).join(".");
      domains.push(d, "." + d);
    }
    names.forEach(function (n) {
      domains.forEach(function (d) {
        document.cookie = n + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; max-age=0; path=/" + (d ? "; domain=" + d : "");
      });
    });
  }

  /* ---- 同意バナー ---- */
  var CSS =
    ".nhc-consent{position:fixed;left:0;right:0;bottom:0;z-index:100;box-sizing:border-box;display:flex;flex-wrap:wrap;" +
      "align-items:center;justify-content:center;gap:10px 22px;padding:12px clamp(14px,4vw,40px);" +
      "padding-bottom:calc(12px + env(safe-area-inset-bottom,0px));background:#0a0918;color:#ede8dc;" +
      "border-top:1px solid rgba(231,200,133,.38);box-shadow:0 -10px 30px rgba(0,0,0,.45);" +
      "font-family:'Inter','Noto Sans JP',system-ui,-apple-system,'Hiragino Sans',sans-serif;font-size:.82rem;line-height:1.6;" +
      "text-align:left;outline:none}" +
    ".nhc-consent p{margin:0;flex:1 1 300px;max-width:780px;color:#ede8dc;font-size:inherit;line-height:inherit}" +
    ".nhc-consent a{color:#e7c885;text-decoration:underline;text-underline-offset:3px;white-space:nowrap}" +
    ".nhc-consent-btns{display:flex;flex:none;gap:10px}" +
    ".nhc-consent button{appearance:none;-webkit-appearance:none;margin:0;font:inherit;font-weight:600;line-height:1.2;" +
      "padding:8px 16px;border:1px solid #e7c885;border-radius:8px;cursor:pointer;white-space:nowrap}" +
    ".nhc-consent .nhc-consent-yes{background:#e7c885;color:#0a0918}" +
    ".nhc-consent .nhc-consent-no{background:transparent;color:#e7c885}" +
    ".nhc-consent button:hover{filter:brightness(1.12)}" +
    ".nhc-consent button:focus-visible,.nhc-consent a:focus-visible{outline:2px solid #ede8dc;outline-offset:2px}" +
    "@media (max-width:600px){" +
      ".nhc-consent{gap:8px;padding:10px 14px;padding-bottom:calc(10px + env(safe-area-inset-bottom,0px));font-size:.76rem;line-height:1.5}" +
      ".nhc-consent p{flex-basis:100%}" +
      ".nhc-consent-btns{width:100%}" +
      ".nhc-consent button{flex:1;padding:8px 10px}" +
    "}";
  var banner = null;

  function fill() {
    if (!banner) return;
    var L = lang(), t = TEXT[L];
    banner.setAttribute("lang", L);
    banner.setAttribute("aria-label", t.label);
    banner.querySelector(".nhc-consent-text").textContent = t.msg + " ";
    var a = banner.querySelector("a");
    a.textContent = t.more;
    a.setAttribute("href", t.href);
    banner.querySelector(".nhc-consent-yes").textContent = t.yes;
    banner.querySelector(".nhc-consent-no").textContent = t.no;
  }
  function hideBanner() {
    if (banner && banner.parentNode) banner.parentNode.removeChild(banner);
    banner = null;
  }
  function choose(v) {
    write(v);
    hideBanner();
    if (v === "granted") start();
    else { pause(); clearCookies(); }
  }
  function showBanner(focus) {
    if (!banner) {
      if (!document.getElementById("nhc-consent-style")) {
        var st = document.createElement("style");
        st.id = "nhc-consent-style";
        st.textContent = CSS;
        document.head.appendChild(st);
      }
      banner = document.createElement("div");
      banner.className = "nhc-consent";
      banner.id = "nhcConsent";
      banner.setAttribute("role", "region");
      banner.setAttribute("tabindex", "-1");
      var p = document.createElement("p");
      var text = document.createElement("span");
      text.className = "nhc-consent-text";
      p.appendChild(text);
      p.appendChild(document.createElement("a"));
      var btns = document.createElement("div");
      btns.className = "nhc-consent-btns";
      var yes = document.createElement("button");
      yes.type = "button";
      yes.className = "nhc-consent-yes";
      yes.addEventListener("click", function () { choose("granted"); });
      var no = document.createElement("button");
      no.type = "button";
      no.className = "nhc-consent-no";
      no.addEventListener("click", function () { choose("denied"); });
      btns.appendChild(yes);
      btns.appendChild(no);
      banner.appendChild(p);
      banner.appendChild(btns);
      // <body> ではなく <html> の直下に置く。index.html などは body に transform（表示時のアニメーション）が
      // 掛かっており、body の中では position:fixed が画面ではなくページ全体の下端に付いてしまうため
      document.documentElement.appendChild(banner);
    }
    fill();
    if (focus) { try { banner.focus({ preventScroll: true }); } catch (e) { banner.focus(); } }
  }

  /* 上部ナビで言語を切り替えたら、バナーの文言も切り替える */
  document.addEventListener("nhc:lang", fill);
  /* ほかのタブで選択が済んだら、こちらのバナーも片づける */
  window.addEventListener("storage", function (e) {
    if (e.key !== KEY) return;
    var v = read();
    if (v) hideBanner();
    if (v === "granted") start();
    else if (v === "denied") pause();
  });

  /* ---- 設定のやり直し（プライバシーポリシーのボタンから）---- */
  NHC.analyticsSettings = function () {
    write(null);
    pause();          // 選び直すまでは送信しない
    showBanner(true);
    return true;
  };

  /* ---- 起動 ---- */
  var state = read();
  if (state === "granted") start();
  else if (state === null) showBanner(false);
})();
