/* ============================================================
   community.js — ログイン・投稿（承認制）・ブックマーク
   ------------------------------------------------------------
   * ログイン: Google アカウント連携 / メールアドレス登録（Supabase Auth）
   * ナビ右端: 未ログインなら〈ログイン〉、ログイン中は表示名（→ profile.html）。
     ナビからログインすると、そのままプロフィールページ（profile.html）を開きます
     （ビュワーの投稿欄などからログインしたときは、そのページにとどまります）
   * 投稿は「承認待ち」で保存され、運営が admin.html で承認したものだけ公開
   * ビュワー（<body data-doc="…">）では
       - ツールバーに〈コメント〉〈ブックマーク〉を追加（文書全体）
       - 各セグメントに〈注釈・コメント〉（件数つき）と〈ブックマーク〉
       - 語のポップオーバーに〈この語について投稿〉
   * プロフィール（profile.html）と承認（admin.html）は window.NHC_COMMUNITY を使って描画します
   * 設定: assets/community-config.js（未設定なら機能は表示しません）
   * デモ: URL に ?community=demo（ブラウザ内だけで動作。?community=off で解除）
   ============================================================ */
(function () {
  "use strict";
  var CFG = window.NHC_COMMUNITY_CONFIG || {};
  var H = document.documentElement;
  var DEMO_FLAG = "nhc-community-demo", DEMO_DB = "nhc-demo-community";

  /* ---------- 文書キー → ビュワー ----------
     新しいビュワーを追加したら、ここに 1 行足してください
     （プロフィール・承認ページでの文書名と、該当箇所へのリンクに使います）。
     wit: true は、URL の ?wit= で写本を切り替えるビュワー。 */
  var DOCS = {
    eugnostos: { reader: "eugnostos.html", wit: true,
      title: { ja: "エウグノストス", en: "Eugnostos", fr: "Eugnoste" },
      wits: { III: "III,3", V: "V,1", SYN: { ja: "対照", en: "synopsis", fr: "synopse" } } },
    republic: { reader: "republic.html",
      title: { ja: "プラトン『国家』588b–589b", en: "Plato, Republic 588b–589b", fr: "Platon, République 588b–589b" } }
  };

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
      login: "ログイン", logout: "ログアウト", account: "アカウント", profile: "プロフィール", admin: "投稿の承認（運営）",
      loginTitle: "ログイン / ユーザー登録",
      loginLead: "ログインすると、コメント・注釈・誤りの指摘の投稿、ブックマーク、プロフィールページが使えます。投稿は運営が確認したのちに公開されます。",
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
      edit: "修正", edited: "修正",
      modNote: "運営より", policy: "投稿は運営による確認（承認制）を経て公開されます。公開後は CC BY 4.0 で本サイトに掲載されることに同意したものとみなします。",
      onWord: "この語について投稿", segBtn: "注釈・コメント", err: "エラーが発生しました: ",
      tooMany: "承認待ちの投稿が多すぎます。承認をお待ちください。", demo: "デモモード（この端末内だけに保存）",
      bm: "ブックマーク", bmOn: "ブックマーク済み", bmAdded: "ブックマークに追加しました", bmRemoved: "ブックマークを外しました",
      bmSee: "プロフィールで見る", bmLogin: "ブックマークするにはログインしてください。",
      tooManyBm: "ブックマークは 500 件までです。", tooManyMsg: "メッセージの送信が多すぎます。時間をおいてお試しください。",
      notReady: "この機能は準備中です。しばらくしてからお試しください。",
      close: "閉じる", by: "", loading: "読み込み中…", ppLink: "プライバシーポリシー", tosLink: "利用規約"
    },
    en: {
      login: "Sign in", logout: "Sign out", account: "Account", profile: "Profile", admin: "Moderation",
      loginTitle: "Sign in / Register",
      loginLead: "Sign in to post comments, annotations or corrections, to keep bookmarks and to use your profile page. Contributions are published after review by the editors.",
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
      edit: "Edit", edited: "edited",
      modNote: "Editors", policy: "Contributions are moderated and published after review. By posting you agree that published contributions appear on this site under CC BY 4.0.",
      onWord: "Comment on this word", segBtn: "Notes", err: "Error: ",
      tooMany: "You have too many contributions awaiting review.", demo: "Demo mode (stored on this device only)",
      bm: "Bookmark", bmOn: "Bookmarked", bmAdded: "Bookmark added", bmRemoved: "Bookmark removed",
      bmSee: "View in profile", bmLogin: "Please sign in to use bookmarks.",
      tooManyBm: "You can keep up to 500 bookmarks.", tooManyMsg: "Too many messages. Please try again later.",
      notReady: "This feature is not available yet. Please try again later.",
      close: "Close", by: "", loading: "Loading…", ppLink: "Privacy policy", tosLink: "Terms of use"
    },
    fr: {
      login: "Connexion", logout: "Déconnexion", account: "Compte", profile: "Profil", admin: "Modération",
      loginTitle: "Connexion / Inscription",
      loginLead: "Connectez-vous pour publier des commentaires, des annotations ou des corrections, garder des marque-pages et utiliser votre page de profil. Les contributions sont publiées après relecture.",
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
      edit: "Modifier", edited: "modifié",
      modNote: "Éditeurs", policy: "Les contributions sont modérées. En publiant, vous acceptez leur diffusion sur ce site sous licence CC BY 4.0.",
      onWord: "Commenter ce mot", segBtn: "Notes", err: "Erreur : ",
      tooMany: "Trop de contributions en attente de relecture.", demo: "Mode démo (stocké sur cet appareil)",
      bm: "Marque-page", bmOn: "Marqué", bmAdded: "Marque-page ajouté", bmRemoved: "Marque-page retiré",
      bmSee: "Voir dans le profil", bmLogin: "Connectez-vous pour utiliser les marque-pages.",
      tooManyBm: "Vous pouvez conserver jusqu’à 500 marque-pages.", tooManyMsg: "Trop de messages. Veuillez réessayer plus tard.",
      notReady: "Cette fonction n’est pas encore disponible. Veuillez réessayer plus tard.",
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

  function docTitle(doc, l) { var d = DOCS[doc]; return d ? (d.title[l || L()] || d.title.ja) : String(doc || ""); }
  /* 文書名＋写本（例: 「エウグノストス III,3」）。l を省くと今の表示言語 */
  function docLabel(it, l) {
    var d = it && DOCS[it.doc], w = d && d.wits && it.witness ? d.wits[it.witness] : null;
    if (w && typeof w === "object") w = w[l || L()] || w.ja;
    return docTitle(it && it.doc, l) + (w ? " " + w : "");
  }
  /* 投稿・ブックマークの該当箇所へのリンク（文書が未登録なら ""） */
  function docLink(it) {
    var d = it && DOCS[it.doc]; if (!d) return "";
    return d.reader + (d.wit && it.witness ? "?wit=" + encodeURIComponent(it.witness) : "") +
      (it.seg_id ? "#seg-" + encodeURIComponent(it.seg_id) : "");
  }
  function profileUrl() { return new URL("profile.html", location.href).href; }
  function onProfile() { return /(^|\/)profile(\.html)?$/.test(location.pathname); }

  /* ---------- エラーの読み替え ---------- */
  /* テーブル・関数がまだ無い（supabase/schema.sql を更新後に再実行していない）ときのエラー */
  function isMissing(e) {
    var c = String((e && e.code) || ""), m = String((e && e.message) || "");
    return /^(PGRST20[25]|42P01|42883)$/.test(c) || /schema cache|does not exist/i.test(m);
  }
  function isDuplicate(e) { return String((e && e.code) || "") === "23505" || /duplicate key/i.test(String((e && e.message) || "")); }
  function errText(e) {
    var m = String((e && e.message) || e || "");
    if (/too many pending/.test(m)) return t("tooMany");
    if (/too many bookmarks/.test(m)) return t("tooManyBm");
    if (/too many messages/.test(m)) return t("tooManyMsg");
    if (isMissing(e)) return t("notReady");
    return t("err") + m;
  }

  /* =========================================================
     バックエンド（共通インターフェース）
       認証      user() / signInGoogle(dest) / signInEmail() / signUp(…, dest) / signOut() / updateName()
       投稿      list(doc) / create(c) / remove(id)
                 myContributions() / editContribution(id, {kind, body, suggestion}) / cancelRevision(id)
       ブックマーク bookmarks(doc?) / addBookmark(b) / updateBookmark(id, {note}) / removeBookmark(id)
       運営へ    sendFeedback(f) / myFeedback() / removeFeedback(id)
       運営用    moderationList(status) / moderate(id, status, note)
                 revisionList() / reviewRevision(id, approve, note)
                 feedbackList() / updateFeedback(id, {status, reply})
     editContribution は 'pending'（その場で修正）/ 'revision'（公開済み → 修正を申請）/ 'unchanged' を返す。
     ========================================================= */
  function DemoBackend() {
    var ME = "demo-user";
    function now() { return new Date().toISOString(); }
    function seed() {
      return {
        seq: 3, session: null, names: {}, revisions: {}, bookmarks: [], feedback: [],
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
    db.revisions = db.revisions || {}; db.bookmarks = db.bookmarks || []; db.feedback = db.feedback || [];   // 旧形式のデモデータ
    function save() { try { localStorage.setItem(DEMO_DB, JSON.stringify(db)); } catch (e) {} }
    var subs = [];
    function emit() { subs.forEach(function (f) { try { f(); } catch (e) {} }); }
    function me() { return db.session ? { id: ME, email: "demo@example.org", name: db.names[ME] || "デモユーザー", isAdmin: true } : null; }
    function vis(it) { var u = me(); return it.status === "approved" || (u && (it.author_id === u.id || u.isAdmin)); }
    function ok(v) { return Promise.resolve(v); }
    function fail(m) { return Promise.reject(new Error(m)); }
    function find(id) { for (var i = 0; i < db.items.length; i++) if (db.items[i].id === id) return db.items[i]; return null; }
    function newest(a, b) { return String(b.created_at).localeCompare(String(a.created_at)); }
    function clone(o) { return Object.assign({}, o); }
    return {
      kind: "demo",
      init: function () { return ok(); },
      onChange: function (f) { subs.push(f); },
      user: function () { return ok(me()); },
      signInGoogle: function () { db.session = ME; save(); emit(); return ok(); },
      signInEmail: function () { db.session = ME; save(); emit(); return ok(); },
      signUp: function (email, pw, name) { if (name) db.names[ME] = name; db.session = ME; save(); emit(); return ok({ confirmed: true }); },
      signOut: function () { db.session = null; save(); emit(); return ok(); },
      updateName: function (n) {
        n = String(n || "").trim(); if (!n) return fail("display name is empty");
        db.names[ME] = n;
        db.items.forEach(function (x) { if (x.author_id === ME) x.author_name = n; });      // 過去の投稿の表示名も合わせる
        db.feedback.forEach(function (x) { if (x.user_id === ME) x.author_name = n; });
        save(); emit(); return ok();
      },
      list: function (doc) { return ok(db.items.filter(function (it) { return it.doc === doc && vis(it); })); },
      create: function (c) {
        var u = me(); if (!u) return fail("not signed in");
        var it = Object.assign({}, c, { id: ++db.seq, status: "pending", author_id: u.id, author_name: u.name, moderator_note: null, created_at: now(), updated_at: null });
        db.items.push(it); save(); return ok(it);
      },
      remove: function (id) {
        db.items = db.items.filter(function (x) { return x.id !== id; }); delete db.revisions[id];
        save(); return ok();
      },
      myContributions: function () {
        var u = me(); if (!u) return ok([]);
        return ok(db.items.filter(function (x) { return x.author_id === u.id; }).map(function (x) {
          var r = db.revisions[x.id];
          return Object.assign({}, x, { revision: r && x.status === "approved" ? clone(r) : null });
        }).sort(newest));
      },
      editContribution: function (id, c) {
        var u = me(); if (!u) return fail("not signed in");
        var it = find(id); if (!it || it.author_id !== u.id) return fail("contribution not found");
        var kind = c.kind || it.kind, body = String(c.body || "").trim();
        var sugg = kind === "correction" ? (String(c.suggestion || "").trim() || null) : null;
        if (!body || body.length > 4000) return fail("body must be 1 to 4000 characters");
        if (it.status === "approved") {
          if (kind === it.kind && body === it.body && sugg === (it.suggestion || null)) { delete db.revisions[id]; save(); return ok("unchanged"); }
          db.revisions[id] = { contribution_id: id, author_id: u.id, kind: kind, body: body, suggestion: sugg,
            status: "pending", moderator_note: null, created_at: now(), reviewed_at: null };
          save(); return ok("revision");
        }
        if (it.status === "rejected" &&
            db.items.filter(function (x) { return x.author_id === u.id && x.status === "pending"; }).length >= 30) return fail("too many pending contributions");
        it.kind = kind; it.body = body; it.suggestion = sugg; it.status = "pending"; it.moderator_note = null; it.reviewed_at = null; it.updated_at = now();
        save(); return ok("pending");
      },
      cancelRevision: function (id) { delete db.revisions[id]; save(); return ok(); },
      bookmarks: function (doc) {
        var u = me(); if (!u) return ok([]);
        return ok(db.bookmarks.filter(function (b) { return b.user_id === u.id && (!doc || b.doc === doc); }).map(clone).sort(newest));
      },
      addBookmark: function (b) {
        var u = me(); if (!u) return fail("not signed in");
        var mine = db.bookmarks.filter(function (x) { return x.user_id === u.id; });
        if (mine.some(function (x) { return x.doc === b.doc && (x.seg_id || null) === (b.seg_id || null); })) return fail("duplicate key value violates unique constraint");
        if (mine.length >= 500) return fail("too many bookmarks");
        var it = Object.assign({ witness: null, seg_id: null, seg_label: null, excerpt: null, note: null }, b, { id: ++db.seq, user_id: u.id, created_at: now() });
        db.bookmarks.push(it); save(); return ok(clone(it));
      },
      updateBookmark: function (id, patch) {
        db.bookmarks.forEach(function (x) { if (x.id === id) x.note = String(patch.note || "").trim() || null; });
        save(); return ok();
      },
      removeBookmark: function (id) { db.bookmarks = db.bookmarks.filter(function (x) { return x.id !== id; }); save(); return ok(); },
      sendFeedback: function (f) {
        var u = me(); if (!u) return fail("not signed in");
        var day = Date.now() - 864e5;
        if (db.feedback.filter(function (x) { return x.user_id === u.id && Date.parse(x.created_at) > day; }).length >= 20) return fail("too many messages");
        var it = Object.assign({ page: null, user_agent: null }, f, { id: ++db.seq, user_id: u.id, author_name: u.name, status: "new", reply: null, created_at: now(), handled_at: null });
        db.feedback.push(it); save(); return ok(clone(it));
      },
      myFeedback: function () {
        var u = me(); if (!u) return ok([]);
        return ok(db.feedback.filter(function (x) { return x.user_id === u.id; }).map(clone).sort(newest));
      },
      removeFeedback: function (id) { db.feedback = db.feedback.filter(function (x) { return x.id !== id; }); save(); return ok(); },
      moderationList: function (status) {
        return ok(db.items.filter(function (x) { return !status || x.status === status; }).slice().sort(newest));
      },
      moderate: function (id, status, note) {
        db.items.forEach(function (x) {
          if (x.id !== id) return;
          if (x.status === "approved" && status !== "approved") delete db.revisions[id];   // 公開をやめた投稿の修正の申請は破棄
          x.status = status; x.moderator_note = note || null; x.reviewed_at = now();
        });
        save(); return ok();
      },
      revisionList: function () {
        return ok(Object.keys(db.revisions).map(function (k) { return db.revisions[k]; })
          .filter(function (r) { return r.status === "pending"; })
          .map(function (r) { return { revision: clone(r), contribution: find(r.contribution_id) }; })
          .filter(function (x) { return x.contribution && x.contribution.status === "approved"; })
          .sort(function (a, b) { return String(a.revision.created_at).localeCompare(String(b.revision.created_at)); }));
      },
      reviewRevision: function (id, approve, note) {
        var r = db.revisions[id], it = find(id);
        if (!r || r.status !== "pending" || !it) return fail("revision not found");
        if (approve) {
          it.kind = r.kind; it.body = r.body; it.suggestion = r.suggestion; it.updated_at = r.created_at; it.reviewed_at = now();
          delete db.revisions[id];
        } else { r.status = "rejected"; r.moderator_note = String(note || "").trim() || null; r.reviewed_at = now(); }
        save(); return ok();
      },
      feedbackList: function () { return ok(db.feedback.map(clone).sort(newest)); },
      updateFeedback: function (id, patch) {
        db.feedback.forEach(function (x) {
          if (x.id !== id) return;
          if (patch.status && patch.status !== x.status) { x.status = patch.status; x.handled_at = patch.status === "done" ? now() : null; }
          if ("reply" in patch) x.reply = String(patch.reply || "").trim() || null;
        });
        save(); return ok();
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
      /* dest: ログイン後に開くページ（省略時は今のページ）。Supabase の Redirect URLs に含まれている必要があります */
      signInGoogle: function (dest) {
        return sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: dest || back() } }).then(chk);
      },
      signInEmail: function (email, pw) { return sb.auth.signInWithPassword({ email: email, password: pw }).then(chk); },
      signUp: function (email, pw, name, dest) {
        return sb.auth.signUp({ email: email, password: pw, options: { data: { display_name: name || "" }, emailRedirectTo: dest || back() } })
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
      myContributions: function () {
        return this.user().then(function (u) {
          if (!u) return [];
          return Promise.all([
            sb.from("contributions").select("*").eq("author_id", u.id).order("created_at", { ascending: false }).limit(500),
            sb.from("contribution_revisions").select("*").eq("author_id", u.id)
          ]).then(function (rs) {
            var rows = chk(rs[0]) || [];
            var revs = rs[1].error ? [] : (rs[1].data || []);   // 修正の申請のテーブルが未作成でも、投稿の一覧は表示する
            var by = {}; revs.forEach(function (r) { by[r.contribution_id] = r; });
            return rows.map(function (x) { x.revision = x.status === "approved" && by[x.id] ? by[x.id] : null; return x; });
          });
        });
      },
      editContribution: function (id, c) {
        return sb.rpc("edit_contribution", { p_id: id, p_kind: c.kind, p_body: c.body, p_suggestion: c.suggestion || null }).then(chk);
      },
      cancelRevision: function (id) { return sb.from("contribution_revisions").delete().eq("contribution_id", id).then(chk); },
      bookmarks: function (doc) {
        var q = sb.from("bookmarks").select("*").order("created_at", { ascending: false }).limit(500);
        if (doc) q = q.eq("doc", doc);
        return q.then(chk);
      },
      addBookmark: function (b) { return sb.from("bookmarks").insert(b).select().single().then(chk); },
      updateBookmark: function (id, patch) {
        return sb.from("bookmarks").update({ note: String(patch.note || "").trim() || null }).eq("id", id).then(chk);
      },
      removeBookmark: function (id) { return sb.from("bookmarks").delete().eq("id", id).then(chk); },
      sendFeedback: function (f) { return sb.from("feedback").insert(f).select().single().then(chk); },
      myFeedback: function () {
        return this.user().then(function (u) {
          if (!u) return [];
          return sb.from("feedback").select("*").eq("user_id", u.id).order("created_at", { ascending: false }).limit(100).then(chk);
        });
      },
      removeFeedback: function (id) { return sb.from("feedback").delete().eq("id", id).then(chk); },
      moderationList: function (status) {
        var q = sb.from("contributions").select("*").order("created_at", { ascending: false }).limit(500);
        if (status) q = q.eq("status", status);
        return q.then(chk);
      },
      moderate: function (id, status, note) {
        return sb.from("contributions").update({ status: status, moderator_note: note || null }).eq("id", id).then(chk);
      },
      revisionList: function () {
        return sb.from("contribution_revisions").select("*").eq("status", "pending").order("created_at", { ascending: true }).then(chk)
          .then(function (revs) {
            revs = revs || []; if (!revs.length) return [];
            return sb.from("contributions").select("*").in("id", revs.map(function (r) { return r.contribution_id; })).then(chk)
              .then(function (cs) {
                var by = {}; (cs || []).forEach(function (c) { by[c.id] = c; });
                return revs.map(function (r) { return { revision: r, contribution: by[r.contribution_id] }; })
                  .filter(function (x) { return x.contribution && x.contribution.status === "approved"; });
              });
          });
      },
      reviewRevision: function (id, approve, note) {
        return sb.rpc("review_revision", { p_id: id, p_approve: !!approve, p_note: note || null }).then(chk);
      },
      feedbackList: function () {
        return sb.from("feedback").select("*").order("created_at", { ascending: false }).limit(500).then(chk);
      },
      updateFeedback: function (id, patch) {
        var p = {};
        if (patch.status) p.status = patch.status;
        if ("reply" in patch) p.reply = String(patch.reply || "").trim() || null;
        return sb.from("feedback").update(p).eq("id", id).then(chk);
      }
    };
  }

  /* =========================================================
     UI
     ========================================================= */
  var B = null, USER = null;
  var readyResolve; var READY = new Promise(function (r) { readyResolve = r; });

  function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }

  /* ---- ナビ右端: 未ログインは〈ログイン〉、ログイン中は表示名（プロフィールへ） ---- */
  function renderAuthLink() {
    var a = document.getElementById("sbAuth");
    if (!a) return;
    if (MODE === "off" || !B) { a.hidden = true; return; }
    a.hidden = false;
    if (USER) {
      a.textContent = USER.name; a.title = t("profile"); a.href = "profile.html"; a.onclick = null;
      if (onProfile()) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    } else {
      a.textContent = t("login"); a.title = t("loginTitle"); a.href = "#"; a.removeAttribute("aria-current");
      a.onclick = function (e) { e.preventDefault(); openLogin({ dest: "profile" }); };
    }
  }

  /* ---- 画面下の一言メッセージ（リンクつきも可） ---- */
  var toastEl = null, toastTimer = null;
  function toast(msg, linkText, href) {
    if (!toastEl) { toastEl = el('<div class="cm-toast" role="status" aria-live="polite" hidden></div>'); document.body.appendChild(toastEl); }
    toastEl.innerHTML = '<span>' + esc(msg) + '</span>' + (href ? '<a href="' + esc(href) + '">' + esc(linkText) + ' →</a>' : "");
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.hidden = true; }, href ? 6000 : 3200);
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

  /* opts.dest === "profile": ログインできたらプロフィールページを開く（ナビの〈ログイン〉から）。
     指定がなければ今のページにとどまる（投稿欄・ブックマーク・承認ページから）。 */
  function openLogin(opts) {
    var dest = opts && opts.dest === "profile" && !onProfile() ? profileUrl() : null;
    function done() { if (dest) location.href = dest; else closeModal(); }
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
    if (g) g.onclick = function () { B.signInGoogle(dest).then(function () { if (B.kind === "demo") done(); }).catch(fail); };
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
        var p = mode === "up" ? B.signUp(email, pw, form.name.value.trim(), dest) : B.signInEmail(email, pw);
        p.then(function (r) {
          if (mode === "up" && r && !r.confirmed) { msg.textContent = t("signupSent"); return; }
          done();
        }).catch(fail);
      };
    }
  }

  /* =========================================================
     ビュワー連携
     ========================================================= */
  var DOC = null, ITEMS = [], BMS = [], CTX = null, LASTWORD = null, drawer = null;

  function witness() {
    var tab = document.querySelector('header .tab[aria-selected="true"]');
    return tab ? tab.getAttribute("data-wit") : null;
  }
  function segEls() { return Array.prototype.slice.call(document.querySelectorAll("#reading .seg[data-id], #reading .prow[data-id]")); }
  function segLabel(segEl) { var n = segEl && segEl.querySelector(".no"); return n ? n.textContent.trim() : ""; }
  function countFor(seg) { return ITEMS.filter(function (x) { return x.seg_id === seg; }).length; }
  function bmFor(seg) {
    seg = seg || null;
    for (var i = 0; i < BMS.length; i++) if ((BMS[i].seg_id || null) === seg) return BMS[i];
    return null;
  }
  /* ブックマークの一覧に出す、コプト語本文の冒頭（語釈・行番号・ページ番号・形態素の区切りは除く） */
  function excerptOf(segEl) {
    var c = segEl && segEl.querySelector(".coptic"); if (!c) return null;
    var k = c.cloneNode(true);
    Array.prototype.forEach.call(k.querySelectorAll(".g, .lbm, .pdm, .msep"), function (n) { n.remove(); });
    var s = (k.textContent || "").replace(/\s+/g, " ").trim();
    if (!s) return null;
    var a = Array.from(s);
    return a.length > 80 ? a.slice(0, 80).join("").trim() + "…" : s;
  }

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
      var k = host.querySelector(":scope > .cm-bm");
      if (!k) {
        k = el('<button type="button" class="cm-bm"></button>');
        k.onclick = function (e) { e.stopPropagation(); toggleBookmark({ seg_id: id, seg_label: segLabel(s), excerpt: excerptOf(s) }, k); };
        host.appendChild(k);
      }
      var on = !!bmFor(id);
      k.classList.toggle("on", on); k.setAttribute("aria-pressed", String(on));
      k.innerHTML = '<span aria-hidden="true">' + (on ? "★" : "☆") + '</span> ' + esc(t(on ? "bmOn" : "bm"));
      k.title = t(on ? "bmOn" : "bm") + " · " + t("scopeSeg") + segLabel(s);
    });
    var hb = document.getElementById("cmBtn");
    if (hb) hb.querySelector(".cm-n").textContent = ITEMS.length ? String(ITEMS.length) : "";
    var bb = document.getElementById("bmBtn");
    if (bb) {
      var d = !!bmFor(null);
      bb.setAttribute("aria-pressed", String(d));
      bb.querySelector(".ic").textContent = d ? "★" : "☆";
      bb.querySelector(".bm-lbl").textContent = t(d ? "bmOn" : "bm");
      bb.title = t(d ? "bmOn" : "bm") + " · " + t("scopeDoc");
    }
  }

  function refreshItems() {
    if (!DOC || !B) return Promise.resolve();
    return B.list(DOC).then(function (rows) { ITEMS = rows || []; decorate(); if (drawer && !drawer.hidden) renderDrawer(); })
      .catch(function () { ITEMS = []; decorate(); });
  }
  function refreshBookmarks() {
    if (!DOC || !B) return Promise.resolve();
    if (!USER) { BMS = []; decorate(); return Promise.resolve(); }
    return B.bookmarks(DOC).then(function (rows) { BMS = rows || []; decorate(); })
      .catch(function () { BMS = []; decorate(); });
  }
  /* ctx.seg_id が無ければ文書全体のブックマーク。同じ箇所がブックマーク済みなら外す */
  function toggleBookmark(ctx, btn) {
    if (!B) return;
    if (!USER) { openLogin(); var mm = modalBack && modalBack.querySelector(".cm-lead"); if (mm) mm.textContent = t("bmLogin"); return; }
    var ex = bmFor(ctx.seg_id);
    if (btn) btn.disabled = true;
    var p = ex ? B.removeBookmark(ex.id) : B.addBookmark({
      doc: DOC, witness: witness(), seg_id: ctx.seg_id || null, seg_label: ctx.seg_label || null,
      excerpt: ctx.excerpt || null, note: null
    });
    p.then(refreshBookmarks).then(function () {
      if (ex) toast(t("bmRemoved")); else toast(t("bmAdded"), t("bmSee"), "profile.html#bookmarks");
    }).catch(function (e) {
      if (isDuplicate(e)) return refreshBookmarks();     // 別のタブで追加済みだった
      toast(errText(e));
    }).then(function () { if (btn) btn.disabled = false; });
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
      (it.status === "approved" && it.updated_at ? ' · ' + esc(t("edited")) + ' ' + esc(fmtDate(it.updated_at)) : "") +
      (mine ? ' · <a class="cm-linkbtn" href="profile.html#posts">' + esc(t("edit")) + '</a>' : "") +
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
    var lb = drawer.querySelector("#cmLoginBtn"); if (lb) lb.onclick = function () { openLogin(); };
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
          msg.className = "cm-msg err"; msg.textContent = errText(er);
        });
      };
    }
  }

  function setupViewer() {
    DOC = document.body.getAttribute("data-doc");
    if (!DOC) return;
    // ツールバーのボタン（コメント・ブックマーク）
    var nav = document.querySelector("header .nav-ctl");
    if (nav && !document.getElementById("cmBtn")) {
      var b = el('<button type="button" class="chip" id="cmBtn" title=""><span class="ic" aria-hidden="true">✎</span><span class="cm-lbl"></span> <span class="cm-n"></span></button>');
      b.onclick = function () { openDrawer(null); };
      nav.insertBefore(b, nav.firstChild);
      var k = el('<button type="button" class="chip" id="bmBtn" aria-pressed="false" title=""><span class="ic" aria-hidden="true">☆</span><span class="bm-lbl"></span></button>');
      k.onclick = function () { toggleBookmark({}, k); };
      nav.insertBefore(k, b.nextSibling);
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
    openLogin: function (opts) { if (B) openLogin(opts); },
    openAccount: function () { location.href = profileUrl(); },      // 旧〈アカウント〉。いまはプロフィールページ
    onChange: function (f) { document.addEventListener("nhc:auth", f); },
    backend: function () { return B; },
    docs: DOCS, docTitle: docTitle, docLabel: docLabel, docLink: docLink, scopeText: scopeText,
    errText: errText, isMissing: isMissing, toast: toast, profileUrl: profileUrl
  };
  window.NHC_COMMUNITY = API;

  function sameUser(a, b) {
    if (!a || !b) return !a && !b;
    return a.id === b.id && a.name === b.name && a.email === b.email && a.isAdmin === b.isAdmin;
  }
  /* ログイン状態を読み直す。Supabase はタブに戻るたびにも状態変化を通知するので、
     利用者が実際に変わったとき（ログイン・ログアウト・表示名の変更）だけ画面を描き直す
     （そうしないと、入力中の投稿欄やフォームが消えてしまう）。 */
  function updateUser(force) {
    return B.user().then(function (u) {
      var changed = force === true || !sameUser(USER, u);
      USER = u; renderAuthLink();
      if (!changed) return;
      document.dispatchEvent(new CustomEvent("nhc:auth", { detail: { user: u } }));
      return Promise.all([refreshItems(), refreshBookmarks()]);
    });
  }

  function start() {
    document.addEventListener("nhc:sitebar", renderAuthLink);
    document.addEventListener("nhc:lang", function () { relabel(); decorate(); if (drawer && !drawer.hidden) renderDrawer(); });
    if (MODE === "off") { renderAuthLink(); readyResolve(API); return; }
    B = MODE === "demo" ? DemoBackend() : LiveBackend();
    B.init().then(function () {
      B.onChange(function () { updateUser().catch(function (e) { if (window.console) console.warn("[community]", e); }); });
      setupViewer();
      return updateUser(true);
    }).then(function () { readyResolve(API); })
      .catch(function (e) {
        if (window.console) console.warn("[community] disabled:", e);
        B = null; MODE = "off"; API.mode = "off"; renderAuthLink(); readyResolve(API);
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
