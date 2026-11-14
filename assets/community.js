/* ============================================================
   community.js — コメント・注釈・誤りの指摘（承認制）
   ------------------------------------------------------------
   * ログイン: Google アカウント連携 / メールアドレス登録（Supabase Auth）
   * 投稿は「承認待ち」で保存され、運営が admin.html で承認したものだけ公開
   * ビュワー（<body data-doc="…">）では
       - ツールバーに〈コメント〉を追加（文書全体への投稿）
       - 各セグメントに〈注釈・コメント〉ボタン（件数つき）
       - 語のポップオーバーに〈この語について投稿〉
   * 設定: assets/community-config.js（未設定なら機能は表示しません）
   * デモ: URL に ?community=demo（ブラウザ内だけで動作。?community=off で解除）
   ============================================================ */
(function () {
  "use strict";
  var CFG = window.NHC_COMMUNITY_CONFIG || {};
  var H = document.documentElement;
  var DEMO_FLAG = "nhc-community-demo", DEMO_DB = "nhc-demo-community";

  /* ---------- 動作モード ---------- */
  function detectMode() {
    var p = new URLSearchParams(location.search).get("community");
    try {
      if (p === "demo") sessionStorage.setItem(DEMO_FLAG, "1");
      if (p === "off") sessionStorage.removeItem(DEMO_FLAG);
      if (sessionStorage.getItem(DEMO_FLAG) === "1") return "demo";
    } catch (e) { if (p === "demo") return "demo"; }
    if (CFG.supabaseUrl && CFG.supabaseAnonKey) return "live";
    return "off";
  }
  var MODE = detectMode();

  /* ---------- 文言 ---------- */
  var TX = {
    ja: {
      login: "ログイン", logout: "ログアウト", account: "アカウント", admin: "投稿の承認（運営）",
      loginTitle: "ログイン / ユーザー登録",
      loginLead: "コメント・注釈・誤りの指摘を投稿するにはログインしてください。投稿は運営が確認したのちに公開されます。",
      google: "Google アカウントでログイン", or: "または メールアドレスで",
      tabIn: "ログイン", tabUp: "新規登録", email: "メールアドレス", password: "パスワード（8文字以上）",
      dname: "表示名（公開されます）", doLogin: "ログイン", doSignup: "登録する",
      signupSent: "確認メールを送信しました。メール内のリンクを開くと登録が完了します。",
      privacy: "メールアドレスは公開されません。公開されるのは表示名のみです。",
      save: "保存", saved: "保存しました", nameLbl: "表示名",
      cm: "コメント", cmTitle: "コメント・注釈", scopeDoc: "文書全体", scopeSeg: "§", word: "語",
      showAll: "この文書のすべての投稿を表示", none: "まだ公開された投稿はありません。",
      kind_comment: "コメント", kind_annotation: "注釈", kind_correction: "誤りの指摘",
      body: "本文", bodyPh_comment: "感想・質問・議論など", bodyPh_annotation: "語釈・文法・典拠・解釈についての注釈",
      bodyPh_correction: "どこがどう誤っているか（根拠があれば併記）", sugg: "修正案（任意）",
      suggPh: "正しいと思われる形・語義・訳など", submit: "送信（承認後に公開）",
      sent: "送信しました。運営の確認後に公開されます。", needLogin: "投稿するにはログインしてください。",
      pending: "承認待ち", approved: "公開", rejected: "非公開", del: "取り消す", delQ: "この投稿を取り消しますか？",
      modNote: "運営より", policy: "投稿は運営による確認（承認制）を経て公開されます。公開後は CC BY 4.0 で本サイトに掲載されることに同意したものとみなします。",
      onWord: "この語について投稿", segBtn: "注釈・コメント", err: "エラーが発生しました: ",
      tooMany: "承認待ちの投稿が多すぎます。承認をお待ちください。", demo: "デモモード（この端末内だけに保存）",
      close: "閉じる", by: "", loading: "読み込み中…", ppLink: "プライバシーポリシー", tosLink: "利用規約"
    },
    en: {
      login: "Sign in", logout: "Sign out", account: "Account", admin: "Moderation",
      loginTitle: "Sign in / Register",
      loginLead: "Sign in to post comments, annotations or corrections. Contributions are published after review by the editors.",
      google: "Sign in with Google", or: "or with e-mail",
      tabIn: "Sign in", tabUp: "Register", email: "E-mail", password: "Password (8+ characters)",
      dname: "Display name (public)", doLogin: "Sign in", doSignup: "Register",
      signupSent: "A confirmation e-mail has been sent. Open the link in it to complete registration.",
      privacy: "Your e-mail address is never shown; only your display name is public.",
      save: "Save", saved: "Saved", nameLbl: "Display name",
      cm: "Comments", cmTitle: "Comments & annotations", scopeDoc: "Whole text", scopeSeg: "§", word: "word",
      showAll: "Show all contributions for this text", none: "No published contributions yet.",
      kind_comment: "Comment", kind_annotation: "Annotation", kind_correction: "Correction",
      body: "Text", bodyPh_comment: "Remarks, questions, discussion", bodyPh_annotation: "Note on sense, grammar, sources or interpretation",
      bodyPh_correction: "What is wrong and why (with evidence if possible)", sugg: "Suggested fix (optional)",
      suggPh: "Correct form, sense or translation", submit: "Submit (published after review)",
      sent: "Submitted. It will appear once the editors have reviewed it.", needLogin: "Please sign in to contribute.",
      pending: "pending", approved: "published", rejected: "not published", del: "Withdraw", delQ: "Withdraw this contribution?",
      modNote: "Editors", policy: "Contributions are moderated and published after review. By posting you agree that published contributions appear on this site under CC BY 4.0.",
      onWord: "Comment on this word", segBtn: "Notes", err: "Error: ",
      tooMany: "You have too many contributions awaiting review.", demo: "Demo mode (stored on this device only)",
      close: "Close", by: "", loading: "Loading…", ppLink: "Privacy policy", tosLink: "Terms of use"
    },
    fr: {
      login: "Connexion", logout: "Déconnexion", account: "Compte", admin: "Modération",
      loginTitle: "Connexion / Inscription",
      loginLead: "Connectez-vous pour publier des commentaires, des annotations ou des corrections. Les contributions sont publiées après relecture.",
      google: "Se connecter avec Google", or: "ou par e-mail",
      tabIn: "Connexion", tabUp: "Inscription", email: "E-mail", password: "Mot de passe (8 caractères min.)",
      dname: "Nom affiché (public)", doLogin: "Se connecter", doSignup: "S’inscrire",
      signupSent: "Un e-mail de confirmation a été envoyé. Ouvrez le lien qu’il contient pour terminer l’inscription.",
      privacy: "Votre adresse e-mail n’est jamais affichée ; seul votre nom est public.",
      save: "Enregistrer", saved: "Enregistré", nameLbl: "Nom affiché",
      cm: "Commentaires", cmTitle: "Commentaires et annotations", scopeDoc: "Texte entier", scopeSeg: "§", word: "mot",
      showAll: "Afficher toutes les contributions", none: "Aucune contribution publiée pour l’instant.",
      kind_comment: "Commentaire", kind_annotation: "Annotation", kind_correction: "Correction",
      body: "Texte", bodyPh_comment: "Remarques, questions, discussion", bodyPh_annotation: "Note sur le sens, la grammaire, les sources ou l’interprétation",
      bodyPh_correction: "Ce qui est erroné et pourquoi", sugg: "Correction proposée (facultatif)",
      suggPh: "Forme, sens ou traduction corrects", submit: "Envoyer (publié après relecture)",
      sent: "Envoyé. La contribution apparaîtra après relecture.", needLogin: "Connectez-vous pour contribuer.",
      pending: "en attente", approved: "publié", rejected: "non publié", del: "Retirer", delQ: "Retirer cette contribution ?",
      modNote: "Éditeurs", policy: "Les contributions sont modérées. En publiant, vous acceptez leur diffusion sur ce site sous licence CC BY 4.0.",
      onWord: "Commenter ce mot", segBtn: "Notes", err: "Erreur : ",
      tooMany: "Trop de contributions en attente de relecture.", demo: "Mode démo (stocké sur cet appareil)",
      close: "Fermer", by: "", loading: "Chargement…", ppLink: "Confidentialité", tosLink: "Conditions d’utilisation"
    }
  };
  function L() {
    var l = (window.NHC && window.NHC.lang) ? window.NHC.lang() : (H.getAttribute("data-lang") || "ja");
    return TX[l] ? l : "ja";
  }
  function t(k) { var d = TX[L()] || TX.ja; return d[k] != null ? d[k] : (TX.ja[k] != null ? TX.ja[k] : k); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function fmtDate(s) { try { var d = new Date(s); return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); } catch (e) { return ""; } }

  /* =========================================================
     バックエンド（共通インターフェース）
       user() / signInGoogle() / signInEmail() / signUp() / signOut()
       updateName() / list(doc) / create(c) / remove(id)
       moderationList(status) / moderate(id, status, note)
     ========================================================= */
  function DemoBackend() {
    var ME = "demo-user";
    function now() { return new Date().toISOString(); }
    function seed() {
      return {
        seq: 3, session: null, names: {},
        items: [
          { id: 1, doc: "eugnostos", witness: "III", seg_id: null, seg_label: null, token_index: null, token_form: null,
            kind: "comment", body: "（デモ用の公開済みコメント）承認されたコメントはこのように表示されます。",
            suggestion: null, status: "approved", author_id: "demo-other", author_name: "Sample reader",
            moderator_note: null, created_at: "2026-11-01T09:00:00Z" },
          { id: 2, doc: "republic", witness: null, seg_id: null, seg_label: null, token_index: null, token_form: null,
            kind: "annotation", body: "（デモ用の公開済み注釈）承認された注釈はこのように表示されます。",
            suggestion: null, status: "approved", author_id: "demo-other", author_name: "Sample reader",
            moderator_note: null, created_at: "2026-11-02T09:00:00Z" }
        ]
      };
    }
    var db;
    try { db = JSON.parse(localStorage.getItem(DEMO_DB) || "null"); } catch (e) { db = null; }
    if (!db || !db.items) db = seed();
    function save() { try { localStorage.setItem(DEMO_DB, JSON.stringify(db)); } catch (e) {} }
    var subs = [];
    function emit() { subs.forEach(function (f) { try { f(); } catch (e) {} }); }
    function me() { return db.session ? { id: ME, email: "demo@example.org", name: db.names[ME] || "デモユーザー", isAdmin: true } : null; }
    function vis(it) { var u = me(); return it.status === "approved" || (u && (it.author_id === u.id || u.isAdmin)); }
    return {
      kind: "demo",
      init: function () { return Promise.resolve(); },
      onChange: function (f) { subs.push(f); },
      user: function () { return Promise.resolve(me()); },
      signInGoogle: function () { db.session = ME; save(); emit(); return Promise.resolve(); },
      signInEmail: function () { db.session = ME; save(); emit(); return Promise.resolve(); },
      signUp: function (email, pw, name) { if (name) db.names[ME] = name; db.session = ME; save(); emit(); return Promise.resolve({ confirmed: true }); },
      signOut: function () { db.session = null; save(); emit(); return Promise.resolve(); },
      updateName: function (n) { db.names[ME] = n; save(); emit(); return Promise.resolve(); },
      list: function (doc) { return Promise.resolve(db.items.filter(function (it) { return it.doc === doc && vis(it); })); },
      create: function (c) {
        var u = me(); if (!u) return Promise.reject(new Error("not signed in"));
        var it = Object.assign({}, c, { id: ++db.seq, status: "pending", author_id: u.id, author_name: u.name, moderator_note: null, created_at: now() });
        db.items.push(it); save(); return Promise.resolve(it);
      },
      remove: function (id) { db.items = db.items.filter(function (x) { return x.id !== id; }); save(); return Promise.resolve(); },
      moderationList: function (status) {
        return Promise.resolve(db.items.filter(function (x) { return !status || x.status === status; })
          .slice().sort(function (a, b) { return b.created_at.localeCompare(a.created_at); }));
      },
      moderate: function (id, status, note) {
        db.items.forEach(function (x) { if (x.id === id) { x.status = status; x.moderator_note = note || null; x.reviewed_at = now(); } });
        save(); return Promise.resolve();
      },
      reset: function () { db = seed(); save(); emit(); }
    };
  }

  function loadScript(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement("script"); s.src = src; s.async = true;
      s.onload = res; s.onerror = function () { rej(new Error("cannot load " + src)); };
      document.head.appendChild(s);
    });
  }

  function LiveBackend() {
    var sb = null, subs = [], cache = null;
    function emit() { cache = null; subs.forEach(function (f) { try { f(); } catch (e) {} }); }
    function back() { return location.href.split("#")[0]; }
    function chk(r) { if (r && r.error) throw r.error; return r ? r.data : null; }
    return {
      kind: "live",
      init: function () {
        return loadScript(CFG.supabaseJs || "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2").then(function () {
          sb = window.supabase.createClient(CFG.supabaseUrl, CFG.supabaseAnonKey,
            { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } });
          sb.auth.onAuthStateChange(function () { emit(); });
        });
      },
      onChange: function (f) { subs.push(f); },
      user: function () {
        if (cache) return cache;
        cache = sb.auth.getSession().then(function (r) {
          var s = r.data && r.data.session; if (!s) return null;
          var u = s.user;
          return Promise.all([
            sb.from("profiles").select("display_name").eq("id", u.id).maybeSingle(),
            sb.rpc("is_admin")
          ]).then(function (rs) {
            var md = u.user_metadata || {};
            var name = (rs[0].data && rs[0].data.display_name) || md.display_name || md.full_name || md.name || "user";
            return { id: u.id, email: u.email, name: name, isAdmin: rs[1].data === true };
          });
        });
        return cache;
      },
      signInGoogle: function () {
        return sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: back() } }).then(chk);
      },
      signInEmail: function (email, pw) { return sb.auth.signInWithPassword({ email: email, password: pw }).then(chk); },
      signUp: function (email, pw, name) {
        return sb.auth.signUp({ email: email, password: pw, options: { data: { display_name: name || "" }, emailRedirectTo: back() } })
          .then(chk).then(function (d) { return { confirmed: !!(d && d.session) }; });
      },
      signOut: function () { return sb.auth.signOut().then(chk); },
      updateName: function (n) {
        return this.user().then(function (u) {
          if (!u) throw new Error("not signed in");
          return sb.from("profiles").update({ display_name: n }).eq("id", u.id).then(chk);
        }).then(emit);
      },
      list: function (doc) {
        return sb.from("contributions").select("*").eq("doc", doc).order("created_at", { ascending: true }).then(chk);
      },
      create: function (c) { return sb.from("contributions").insert(c).select().single().then(chk); },
      remove: function (id) { return sb.from("contributions").delete().eq("id", id).then(chk); },
      moderationList: function (status) {
        var q = sb.from("contributions").select("*").order("created_at", { ascending: false }).limit(500);
        if (status) q = q.eq("status", status);
        return q.then(chk);
      },
      moderate: function (id, status, note) {
        return sb.from("contributions").update({ status: status, moderator_note: note || null }).eq("id", id).then(chk);
      }
    };
  }

  /* =========================================================
     UI
     ========================================================= */
  var B = null, USER = null;
  var readyResolve; var READY = new Promise(function (r) { readyResolve = r; });

  function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }

  /* ---- ナビ右端のログイン表示 ---- */
  function renderAuthLink() {
    var a = document.getElementById("sbAuth");
    if (!a) return;
    if (MODE === "off" || !B) { a.hidden = true; return; }
    a.hidden = false;
    a.textContent = USER ? USER.name : t("login");
    a.title = USER ? t("account") : t("loginTitle");
    a.onclick = function (e) { e.preventDefault(); if (USER) openAccount(); else openLogin(); };
  }

  /* ---- モーダル ---- */
  var modalBack = null;
  function openModal(inner) {
    closeModal();
    modalBack = el('<div class="cm-modal-back" role="presentation"><div class="cm-modal" role="dialog" aria-modal="true">' +
      '<button class="cm-x" type="button" aria-label="' + esc(t("close")) + '">×</button>' + inner + '</div></div>');
    document.body.appendChild(modalBack);
    modalBack.addEventListener("click", function (e) { if (e.target === modalBack) closeModal(); });
    modalBack.querySelector(".cm-x").onclick = closeModal;
    var f = modalBack.querySelector("input,button:not(.cm-x)"); if (f) f.focus();
    return modalBack;
  }
  function closeModal() { if (modalBack) { modalBack.remove(); modalBack = null; } }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closeModal(); } });

  function demoNote() { return MODE === "demo" ? '<p class="cm-demo">⚑ ' + esc(t("demo")) + '</p>' : ""; }

  function openLogin() {
    var p = CFG.providers || { google: true, email: true };
    var m = openModal(
      '<h2>' + esc(t("loginTitle")) + '</h2>' + demoNote() +
      '<p class="cm-lead">' + esc(t("loginLead")) + '</p>' +
      (p.google !== false ? '<button type="button" class="cm-google" id="cmGoogle"><svg viewBox="0 0 48 48" width="18" height="18" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>' + esc(t("google")) + '</button>' : "") +
      (p.email !== false ?
        '<div class="cm-or"><span>' + esc(t("or")) + '</span></div>' +
        '<div class="cm-tabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-t="in">' + esc(t("tabIn")) + '</button>' +
        '<button type="button" role="tab" aria-selected="false" data-t="up">' + esc(t("tabUp")) + '</button></div>' +
        '<form class="cm-form-auth" id="cmAuthForm" novalidate>' +
        '<label class="cm-only-up" hidden>' + esc(t("dname")) + '<input name="name" maxlength="60" autocomplete="nickname"></label>' +
        '<label>' + esc(t("email")) + '<input name="email" type="email" required autocomplete="email"></label>' +
        '<label>' + esc(t("password")) + '<input name="pw" type="password" minlength="8" required autocomplete="current-password"></label>' +
        '<button type="submit" class="cm-primary" id="cmAuthGo">' + esc(t("doLogin")) + '</button>' +
        '</form>' : "") +
      '<p class="cm-msg" id="cmAuthMsg" role="status"></p>' +
      '<p class="cm-fine">' + esc(t("privacy")) + ' <a href="privacy.html">' + esc(t("ppLink")) + '</a> · <a href="terms.html">' + esc(t("tosLink")) + '</a></p>');
    var msg = m.querySelector("#cmAuthMsg");
    function fail(e) { msg.className = "cm-msg err"; msg.textContent = t("err") + ((e && e.message) || e); }
    var g = m.querySelector("#cmGoogle");
    if (g) g.onclick = function () { B.signInGoogle().then(function () { if (B.kind === "demo") closeModal(); }).catch(fail); };
    var form = m.querySelector("#cmAuthForm");
    if (form) {
      var mode = "in";
      m.querySelectorAll(".cm-tabs button").forEach(function (b) {
        b.onclick = function () {
          mode = b.getAttribute("data-t");
          m.querySelectorAll(".cm-tabs button").forEach(function (x) { x.setAttribute("aria-selected", String(x === b)); });
          m.querySelector(".cm-only-up").hidden = mode !== "up";
          m.querySelector("#cmAuthGo").textContent = mode === "up" ? t("doSignup") : t("doLogin");
          form.pw.setAttribute("autocomplete", mode === "up" ? "new-password" : "current-password");
        };
      });
      form.onsubmit = function (e) {
        e.preventDefault();
        var email = form.email.value.trim(), pw = form.pw.value;
        if (!email || pw.length < 8) { fail(t("email") + " / " + t("password")); return; }
        msg.className = "cm-msg"; msg.textContent = t("loading");
        var p = mode === "up" ? B.signUp(email, pw, form.name.value.trim()) : B.signInEmail(email, pw);
        p.then(function (r) {
          if (mode === "up" && r && !r.confirmed) { msg.textContent = t("signupSent"); return; }
          closeModal();
        }).catch(fail);
      };
    }
  }

  function openAccount() {
    if (!USER) return openLogin();
    var m = openModal(
      '<h2>' + esc(t("account")) + '</h2>' + demoNote() +
      '<form id="cmNameForm" class="cm-form-auth"><label>' + esc(t("nameLbl")) +
      '<input name="name" maxlength="60" required value="' + esc(USER.name) + '"></label>' +
      '<button type="submit" class="cm-primary">' + esc(t("save")) + '</button></form>' +
      '<p class="cm-msg" id="cmAccMsg" role="status"></p>' +
      '<div class="cm-acc-links">' + (USER.isAdmin ? '<a href="admin.html">' + esc(t("admin")) + ' →</a>' : "") +
      '<button type="button" class="cm-linkbtn" id="cmLogout">' + esc(t("logout")) + '</button></div>');
    m.querySelector("#cmNameForm").onsubmit = function (e) {
      e.preventDefault(); var v = e.target.name.value.trim(); if (!v) return;
      B.updateName(v).then(function () { m.querySelector("#cmAccMsg").textContent = t("saved"); })
        .catch(function (er) { m.querySelector("#cmAccMsg").textContent = t("err") + er.message; });
    };
    m.querySelector("#cmLogout").onclick = function () { B.signOut().then(closeModal); };
  }

  /* =========================================================
     ビュワー連携
     ========================================================= */
  var DOC = null, ITEMS = [], CTX = null, LASTWORD = null, drawer = null;

  function witness() {
    var tab = document.querySelector('header .tab[aria-selected="true"]');
    return tab ? tab.getAttribute("data-wit") : null;
  }
  function segEls() { return Array.prototype.slice.call(document.querySelectorAll("#reading .seg[data-id], #reading .prow[data-id]")); }
  function segLabel(segEl) { var n = segEl && segEl.querySelector(".no"); return n ? n.textContent.trim() : ""; }
  function countFor(seg) { return ITEMS.filter(function (x) { return x.seg_id === seg; }).length; }

  function decorate() {
    if (!DOC) return;
    segEls().forEach(function (s) {
      var id = s.getAttribute("data-id");
      var host = s.classList.contains("prow") ? (s.querySelector(".pcop") || s) : s;
      var b = host.querySelector(":scope > .cm-seg");
      if (!b) {
        b = el('<button type="button" class="cm-seg"></button>');
        b.onclick = function (e) { e.stopPropagation(); openDrawer({ seg_id: id, seg_label: segLabel(s) }); };
        host.appendChild(b);
      }
      var n = countFor(id);
      b.classList.toggle("has", n > 0);
      b.innerHTML = '<span aria-hidden="true">✎</span> ' + esc(t("segBtn")) + (n ? ' <b>' + n + '</b>' : "");
      b.title = t("cmTitle") + " · " + t("scopeSeg") + segLabel(s);
    });
    var hb = document.getElementById("cmBtn");
    if (hb) hb.querySelector(".cm-n").textContent = ITEMS.length ? String(ITEMS.length) : "";
  }

  function refreshItems() {
    if (!DOC || !B) return Promise.resolve();
    return B.list(DOC).then(function (rows) { ITEMS = rows || []; decorate(); if (drawer && !drawer.hidden) renderDrawer(); })
      .catch(function () { ITEMS = []; decorate(); });
  }

  function scopeText(c) {
    if (!c || !c.seg_id) return t("scopeDoc");
    var s = t("scopeSeg") + (c.seg_label || c.seg_id);
    if (c.token_form) s += " · " + t("word") + " " + c.token_form;
    return s;
  }

  function itemHTML(it) {
    var mine = USER && it.author_id === USER.id;
    var st = it.status !== "approved" ? '<span class="cm-st ' + esc(it.status) + '">' + esc(t(it.status)) + '</span>' : "";
    return '<article class="cm-item k-' + esc(it.kind) + '" data-id="' + esc(it.id) + '">' +
      '<div class="cm-meta"><span class="cm-kind">' + esc(t("kind_" + it.kind)) + '</span>' +
      '<span class="cm-where">' + esc(scopeText(it)) + '</span>' + st + '</div>' +
      '<div class="cm-body">' + esc(it.body) + '</div>' +
      (it.suggestion ? '<div class="cm-sugg"><b>' + esc(t("sugg").replace(/（.*?）|\(.*?\)/g, "")) + '</b> ' + esc(it.suggestion) + '</div>' : "") +
      (it.moderator_note ? '<div class="cm-modnote"><b>' + esc(t("modNote")) + ':</b> ' + esc(it.moderator_note) + '</div>' : "") +
      '<div class="cm-foot">' + esc(it.author_name || "") + ' · ' + esc(fmtDate(it.created_at)) +
      (mine && it.status === "pending" ? ' · <button type="button" class="cm-linkbtn cm-del">' + esc(t("del")) + '</button>' : "") +
      '</div></article>';
  }

  function ensureDrawer() {
    if (drawer) return drawer;
    drawer = el('<div class="cm-drawer" id="cmDrawer" role="complementary" hidden></div>');
    document.body.appendChild(drawer);
    return drawer;
  }
  function openDrawer(ctx) {
    CTX = ctx || null; ensureDrawer(); drawer.hidden = false;
    H.setAttribute("data-cm", "open");
    renderDrawer();
    var f = drawer.querySelector("textarea"); if (f && USER) f.focus();
  }
  function closeDrawer() { if (drawer) drawer.hidden = true; H.removeAttribute("data-cm"); }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && drawer && !drawer.hidden && !modalBack) closeDrawer(); });

  function renderDrawer() {
    if (!drawer) return;
    var list = ITEMS.filter(function (x) { return !CTX || !CTX.seg_id || x.seg_id === CTX.seg_id; });
    var kinds = ["comment", "annotation", "correction"];
    var defKind = CTX && CTX.token_form ? "correction" : (CTX && CTX.seg_id ? "annotation" : "comment");
    drawer.innerHTML =
      '<div class="cm-dhead"><b>' + esc(t("cmTitle")) + '</b><button type="button" class="cm-x" aria-label="' + esc(t("close")) + '">×</button></div>' +
      '<div class="cm-dbody">' + demoNote() +
      '<div class="cm-scope"><span>' + esc(scopeText(CTX)) + '</span>' +
      (CTX && CTX.seg_id ? '<button type="button" class="cm-linkbtn" id="cmAll">' + esc(t("showAll")) + '</button>' : "") + '</div>' +
      '<div class="cm-list">' + (list.length ? list.map(itemHTML).join("") : '<p class="cm-empty">' + esc(t("none")) + '</p>') + '</div>' +
      (USER ?
        '<form class="cm-post" id="cmPost">' +
        '<div class="cm-kinds" role="radiogroup">' + kinds.map(function (k) {
          return '<label><input type="radio" name="kind" value="' + k + '"' + (k === defKind ? " checked" : "") + '> ' + esc(t("kind_" + k)) + '</label>';
        }).join("") + '</div>' +
        '<textarea name="body" maxlength="4000" required rows="5"></textarea>' +
        '<label class="cm-sugg-l">' + esc(t("sugg")) + '<input name="suggestion" maxlength="1000"></label>' +
        '<button type="submit" class="cm-primary">' + esc(t("submit")) + '</button>' +
        '<p class="cm-msg" id="cmPostMsg" role="status"></p></form>'
        : '<div class="cm-needlogin"><p>' + esc(t("needLogin")) + '</p><button type="button" class="cm-primary" id="cmLoginBtn">' + esc(t("login")) + '</button></div>') +
      '<p class="cm-fine">' + esc(t("policy")) + '</p></div>';
    drawer.querySelector(".cm-x").onclick = closeDrawer;
    var all = drawer.querySelector("#cmAll"); if (all) all.onclick = function () { CTX = null; renderDrawer(); };
    var lb = drawer.querySelector("#cmLoginBtn"); if (lb) lb.onclick = openLogin;
    drawer.querySelectorAll(".cm-del").forEach(function (b) {
      b.onclick = function () {
        var id = b.closest(".cm-item").getAttribute("data-id");
        if (!confirm(t("delQ"))) return;
        B.remove(isNaN(+id) ? id : +id).then(refreshItems);
      };
    });
    var form = drawer.querySelector("#cmPost");
    if (form) {
      var ta = form.body, sl = form.querySelector(".cm-sugg-l");
      var sync = function () {
        var k = form.querySelector("input[name=kind]:checked").value;
        ta.placeholder = t("bodyPh_" + k);
        sl.hidden = k !== "correction";
        form.suggestion.placeholder = t("suggPh");
      };
      form.querySelectorAll("input[name=kind]").forEach(function (r) { r.onchange = sync; }); sync();
      form.onsubmit = function (e) {
        e.preventDefault();
        var body = ta.value.trim(); if (!body) return;
        var k = form.querySelector("input[name=kind]:checked").value;
        var c = {
          doc: DOC, witness: witness(), seg_id: CTX && CTX.seg_id || null, seg_label: CTX && CTX.seg_label || null,
          token_index: CTX && CTX.token_index != null ? CTX.token_index : null, token_form: CTX && CTX.token_form || null,
          kind: k, body: body, suggestion: (k === "correction" && form.suggestion.value.trim()) || null
        };
        var msg = form.querySelector("#cmPostMsg"); msg.className = "cm-msg"; msg.textContent = t("loading");
        B.create(c).then(function () {
          return refreshItems();
        }).then(function () {
          var m2 = drawer.querySelector("#cmPostMsg"); if (m2) { m2.className = "cm-msg ok"; m2.textContent = t("sent"); }
        }).catch(function (er) {
          var mm = String((er && er.message) || er);
          msg.className = "cm-msg err"; msg.textContent = /too many pending/.test(mm) ? t("tooMany") : t("err") + mm;
        });
      };
    }
  }

  function setupViewer() {
    DOC = document.body.getAttribute("data-doc");
    if (!DOC) return;
    // ツールバーのボタン
    var nav = document.querySelector("header .nav-ctl");
    if (nav && !document.getElementById("cmBtn")) {
      var b = el('<button type="button" class="chip" id="cmBtn" title=""><span class="ic" aria-hidden="true">✎</span><span class="cm-lbl"></span> <span class="cm-n"></span></button>');
      b.onclick = function () { openDrawer(null); };
      nav.insertBefore(b, nav.firstChild);
    }
    relabel();
    // 本文の再描画を監視してボタンを付け直す
    var reading = document.getElementById("reading");
    if (reading && window.MutationObserver) new MutationObserver(decorate).observe(reading, { childList: true });
    // 語のクリックを記録 → ポップオーバーに〈この語について投稿〉
    document.addEventListener("click", function (e) {
      var w = e.target.closest && e.target.closest(".wseg");
      if (!w) return;
      var s = w.closest("[data-id]");
      var form = w.firstChild && w.firstChild.nodeType === 3 ? w.firstChild.nodeValue : w.textContent;
      LASTWORD = { seg_id: s ? s.getAttribute("data-id") : null, seg_label: segLabel(s), token_index: +w.getAttribute("data-i"), token_form: form };
    }, true);
    var pop = document.getElementById("pop");
    if (pop && window.MutationObserver) new MutationObserver(function () {
      if (!LASTWORD || pop.querySelector(".cm-popbtn")) return;
      var ctx = LASTWORD;
      var b = el('<button type="button" class="cm-popbtn">✎ ' + esc(t("onWord")) + '</button>');
      b.onclick = function (e) { e.stopPropagation(); pop.classList.remove("show"); openDrawer(ctx); };
      pop.appendChild(b);
    }).observe(pop, { childList: true });
    refreshItems();
  }
  function relabel() {
    var b = document.getElementById("cmBtn");
    if (b) { b.querySelector(".cm-lbl").textContent = t("cm"); b.title = t("cmTitle"); }
  }

  /* =========================================================
     起動
     ========================================================= */
  var API = {
    mode: MODE, ready: READY, t: t, esc: esc, fmtDate: fmtDate,
    user: function () { return USER; },
    openLogin: function () { if (B) openLogin(); },
    openAccount: function () { if (B) openAccount(); },
    onChange: function (f) { document.addEventListener("nhc:auth", f); },
    backend: function () { return B; }
  };
  window.NHC_COMMUNITY = API;

  function updateUser() {
    return B.user().then(function (u) {
      USER = u; renderAuthLink();
      document.dispatchEvent(new CustomEvent("nhc:auth", { detail: { user: u } }));
      return refreshItems();
    });
  }

  function start() {
    document.addEventListener("nhc:sitebar", renderAuthLink);
    document.addEventListener("nhc:lang", function () { relabel(); decorate(); if (drawer && !drawer.hidden) renderDrawer(); });
    if (MODE === "off") { renderAuthLink(); readyResolve(API); return; }
    B = MODE === "demo" ? DemoBackend() : LiveBackend();
    B.init().then(function () {
      B.onChange(function () { updateUser(); });
      setupViewer();
      return updateUser();
    }).then(function () { readyResolve(API); })
      .catch(function (e) {
        if (window.console) console.warn("[community] disabled:", e);
        B = null; MODE = "off"; API.mode = "off"; renderAuthLink(); readyResolve(API);
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
