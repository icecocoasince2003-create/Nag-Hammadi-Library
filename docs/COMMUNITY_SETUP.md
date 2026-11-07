# コメント・注釈機能（承認制）のセットアップ

ビュワー（`eugnostos.html` / `republic.html`）で、ログインした利用者が **コメント・注釈・誤りの指摘** を投稿し、
運営が `admin.html` で **承認したものだけを公開** する仕組みです。
サイト本体は静的サイト（Vercel / GitHub Pages）のまま、ログインとデータ保存に **Supabase**（無料枠あり）を使います。

```
利用者のブラウザ ──(Google ログイン / メール登録)──▶ Supabase Auth
        │                                              │
        └──(投稿: status = pending)──▶ Supabase DB（行レベルセキュリティで保護）
                                                       ▲
運営（admin.html）──(承認 → approved / 却下 → rejected)─┘
```

- 投稿は必ず「承認待ち」で保存され、投稿者本人と運営にしか見えません（サーバ側で強制）。
- 公開されるのは表示名だけで、メールアドレスは表示されません。
- 設定が空のあいだは、機能は画面に表示されません。

---

## 0. まず見た目と流れを確認する（デモモード）

どのページでも URL の末尾に `?community=demo` を付けると、ブラウザの中だけで動くデモになります。

- 例: `eugnostos.html?community=demo` → 上部ナビの〈ログイン〉→「Google アカウントでログイン」
  （デモでは実際の認証は行わず、運営権限つきの「デモユーザー」になります）
- 語をクリック →〈この語について投稿〉、各セグメントの〈注釈・コメント〉、ツールバーの〈コメント〉
- `admin.html` で承認 → ビュワーに戻ると公開表示になります
- 解除は `?community=off`

---

## 1. Supabase プロジェクトを作る

1. <https://supabase.com> でアカウントを作り、**New project** を作成（リージョンは Tokyo を推奨）。
2. 左メニュー **SQL Editor** → New query に `supabase/schema.sql` の内容を全部貼り付けて **Run**。
   - テーブル `profiles` / `admins` / `contributions`、権限（RLS）、トリガーが作られます。
3. 接続に使う 2 つの値を控えます。いちばん簡単なのは、プロジェクト画面上部の **Connect** ボタンです
   （開いたダイアログに URL と鍵がまとめて表示されます）。個別に探す場合は次の場所にあります。
   - **Project URL**（`https://xxxx.supabase.co`）: Project Settings → **Data API**
   - **Publishable key**（`sb_publishable_...` で始まる、公開してよい鍵）: Project Settings → **API Keys**
     - 古い形式の `anon` key（`eyJ...` で始まる）でも動きます。API Keys 画面の「Legacy API Keys」タブにあります。
   - ※ **Secret key**（`sb_secret_...`）や `service_role` key は絶対にサイトに書かないでください。

## 2. Google ログインを有効にする

Google Cloud Console の画面は 2025 年に変わり、OAuth の設定は「API とサービス → 認証情報」ではなく
**Google Auth Platform** にまとめられています。

1. **プロジェクトを作る**: <https://console.cloud.google.com/projectcreate> で新規プロジェクトを作成
   （名前は「nag-hammadi-library」など。課金設定は不要）。
2. **Google Auth Platform を開く**: 左上の ≡ メニュー → **Google Auth Platform**
   （見つからなければ上部の検索欄に「Google Auth Platform」または「OAuth」と入力。
   直接 <https://console.cloud.google.com/auth/overview> を開いても構いません）。
3. **アプリを登録する**（初回のみ）: **開始**（Get started）を押してウィザードに入力。
   - アプリ情報: アプリ名「ナグ・ハマディ写本コーパス」、ユーザーサポートメール
   - 対象（Audience）: **外部**（External）を選ぶ ← ここを「内部」にすると一般の人がログインできません
   - 連絡先情報: 自分のメールアドレス → ポリシーに同意して **作成**
4. **クライアントを作る**: 左メニュー **クライアント**（Clients）→ **クライアントを作成**（Create client）
   - アプリケーションの種類: **ウェブ アプリケーション**
   - 名前: 「NHC site」など（ラベルなので何でも可）
   - 承認済みの JavaScript 生成元: 空欄で可
   - **承認済みのリダイレクト URI**: Supabase のコールバック URL を追加
     `https://<あなたのプロジェクト>.supabase.co/auth/v1/callback`
     （Supabase の **Authentication → Sign In / Providers → Google** を開くと「Callback URL」として表示されているので、
     それをそのままコピーするのが確実です）
   - **作成** を押す
5. 表示される **クライアント ID** と **クライアント シークレット** を控えます
   （シークレットはこの画面でしか表示されないので、JSON をダウンロードしておくと安心です）。
6. Supabase の **Authentication → Sign In / Providers → Google** を開き、
   クライアント ID とシークレットを入力して **有効化（Enable）→ Save**。
7. **公開する**: Google Auth Platform の **対象**（Audience）で、公開ステータスが「テスト中」になっていたら
   **アプリを公開**（Publish app）を押します。テスト中のままだと、テストユーザーに登録した人しかログインできません。
   このサイトが使うのはメールアドレスと名前（基本スコープ）だけなので、公開に Google の審査は不要です。

## 3. メールアドレスでの登録（Google を使わない人向け）

Supabase の **Authentication → Sign In / Providers → Email** を有効にします（初期状態で有効）。
「Confirm email」をオンにしておくと、登録時に確認メールが届きます。
Google だけにしたい場合は `assets/community-config.js` の `providers.email` を `false` にします。

## 4. サイトの URL を登録する

Supabase の **Authentication → URL Configuration**:

- **Site URL**: `https://nag-hammadi-library.vercel.app`（公開 URL）
- **Redirect URLs** に追加:
  - `https://nag-hammadi-library.vercel.app/**`
  - ローカル確認用に `http://localhost:8000/**` など

## 5. サイトに接続する

`assets/community-config.js` を編集します。

```js
window.NHC_COMMUNITY_CONFIG = {
  supabaseUrl: "https://xxxx.supabase.co",
  supabaseAnonKey: "sb_publishable_...",   // Publishable key（または旧形式の anon key）
  providers: { google: true, email: true },
  supabaseJs: "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"
};
```

コミットして公開すると、上部ナビに〈ログイン〉、ビュワーに投稿ボタンが表示されます。

## 6. 自分を運営（承認者）に登録する

1. 公開サイトで一度ログインする（これでユーザーが作られます）。
2. Supabase の SQL Editor で、メールアドレスを自分のものに書き換えて実行:

```sql
insert into public.admins (user_id)
  select id from auth.users where email = 'あなたのメールアドレス'
  on conflict do nothing;
```

3. 上部ナビの自分の名前 → 〈投稿の承認（運営）〉、または `admin.html` を開きます。
   協力者を運営に加えるときも同じ SQL を実行します。

---

## データの扱い

| 項目 | 内容 |
|---|---|
| 投稿の種類 | `comment`（コメント）/ `annotation`（注釈）/ `correction`（誤りの指摘・修正案つき） |
| 対象 | 文書（`doc`）、写本（`witness`）、セグメント（`seg_id` = TEI の `<s xml:id>`）、語（`token_index` / `token_form`） |
| 状態 | `pending` → `approved`（公開）/ `rejected`（投稿者にだけメモ付きで表示） |
| 連投対策 | 1 人あたりの承認待ちは 30 件まで、本文は 4000 字まで |
| ライセンス | 公開された投稿は CC BY 4.0 で掲載（投稿フォームに明記） |

承認済みの投稿を TEI に取り込みたいときは、Supabase の **Table Editor → contributions** から
CSV でエクスポートできます（`status = approved` で絞り込み）。`seg_id` と `token_index` で本文の位置を特定できます。

## 新しいビュワーを追加したとき

`<body data-doc="文書キー">` を付け、`assets/community-config.js` と `assets/community.js` を読み込めば自動で有効になります。
セグメントは `#reading` 内の `.seg[data-id]` または `.prow[data-id]`、語は `.wseg[data-i]` を目印にしています。
`admin.html` の `DOCS` にビュワーのファイル名を追加してください。
