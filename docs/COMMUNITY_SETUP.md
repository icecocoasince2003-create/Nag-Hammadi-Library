# コメント・注釈機能（承認制）とプロフィールページのセットアップ

ビュワー（`eugnostos.html` / `republic.html`）で、ログインした利用者が **コメント・注釈・誤りの指摘** を投稿し、
運営が `admin.html` で **承認したものだけを公開** する仕組みです。
ログインした利用者には **プロフィールページ（`profile.html`）** があり、表示名の変更、自分の投稿の確認と修正、
ブックマーク、運営へのバグの報告・応援メッセージの送信ができます。
サイト本体は静的サイト（Vercel / GitHub Pages）のまま、ログインとデータ保存に **Supabase**（無料枠あり）を使います。

> **サイトを更新したら（重要）** — `supabase/schema.sql` が変わったときは、Supabase の **SQL Editor** に
> ファイル全体を貼り付けて **もう一度 Run** してください。足りないテーブル・関数・権限だけが追加され、
> 既存のデータは消えません。再実行するまでは、新しい機能（投稿の修正・ブックマーク・運営へのメッセージ）は
> 「準備中」と表示され、`admin.html` に更新の案内が出ます（それ以外の機能はそのまま動きます）。

```
利用者のブラウザ ──(Google ログイン / メール登録)──▶ Supabase Auth
        │                                              │
        └──(投稿: status = pending)──▶ Supabase DB（行レベルセキュリティで保護）
                                                       ▲
運営（admin.html）──(承認 → approved / 却下 → rejected)─┘
```

- 投稿は必ず「承認待ち」で保存され、投稿者本人と運営にしか見えません（サーバ側で強制）。
- 公開済みの投稿を投稿者が修正すると「修正の申請」になり、運営が承認するまでは元の内容が公開されたままです。
- ブックマークは本人だけ、運営へのメッセージは本人と運営だけが読めます（どちらも公開されません）。
- 公開されるのは表示名だけで、メールアドレスは表示されません。
- 設定が空のあいだは、機能は画面に表示されません。

---

## 0. まず見た目と流れを確認する（デモモード）

どのページでも URL の末尾に `?community=demo` を付けると、ブラウザの中だけで動くデモになります。

- 例: `eugnostos.html?community=demo` → 上部ナビの〈ログイン〉→「Google アカウントでログイン」
  （デモでは実際の認証は行わず、運営権限つきの「デモユーザー」になります）
- 語をクリック →〈この語について投稿〉、各セグメントの〈注釈・コメント〉〈☆ ブックマーク〉、ツールバーの〈コメント〉〈ブックマーク〉
- 上部ナビの表示名 → プロフィールページ（投稿の修正、ブックマーク、バグの報告、応援メッセージ）
- `admin.html` で承認 → ビュワーに戻ると公開表示になります。〈修正の申請〉〈メッセージ〉もここで確認します
- 解除は `?community=off`

---

## 1. Supabase プロジェクトを作る

1. <https://supabase.com> でアカウントを作り、**New project** を作成（リージョンは Tokyo を推奨）。
2. 左メニュー **SQL Editor** → New query に `supabase/schema.sql` の内容を全部貼り付けて **Run**。
   - テーブル `profiles` / `admins` / `contributions` / `contribution_revisions` / `bookmarks` / `feedback`、
     権限（RLS）、トリガー、関数（`edit_contribution` / `review_revision`）が作られます。
   - このファイルを更新したときも、同じ手順でもう一度実行します（再実行しても安全です）。
3. **Project Settings → API** で次の 2 つを控えます。
   - Project URL（`https://ngzzklrjbkzsnegozpps.supabase.co/rest/v1/`）
   - `anon` `public` key（公開してよい鍵）
   - ※ `service_role` key は絶対にサイトに書かないでください。

## 2. Google ログインを有効にする

1. Google Cloud Console（<https://console.cloud.google.com/>）でプロジェクトを作成。
2. **API とサービス → OAuth 同意画面** を設定（外部、アプリ名「ナグ・ハマディ写本コーパス」など）。
3. **認証情報 → 認証情報を作成 → OAuth クライアント ID**（種類: ウェブ アプリケーション）
   - 「承認済みのリダイレクト URI」に Supabase のコールバック URL を登録:
     `https://ngzzklrjbkzsnegozpps.supabase.co/auth/v1/callback`
4. 発行された **クライアント ID / クライアント シークレット** を、
   Supabase の **Authentication → Sign In / Providers → Google** に入力して有効化。

## 3. メールアドレスでの登録（Google を使わない人向け）

Supabase の **Authentication → Sign In / Providers → Email** を有効にします（初期状態で有効）。
「Confirm email」をオンにしておくと、登録時に確認メールが届きます。
Google だけにしたい場合は `assets/community-config.js` の `providers.email` を `false` にします。

## 4. サイトの URL を登録する

Supabase の **Authentication → URL Configuration**:

- **Site URL**: `https://sheneset.vercel.app`（公開 URL）
- **Redirect URLs** に追加:
  - `https://sheneset.vercel.app/**`
  - ローカル確認用に `http://localhost:8000/**` など

上部ナビの〈ログイン〉からログインすると、ログイン後にプロフィールページ（`profile.html`）へ移動します。
移動先がこの一覧に含まれていないと、Supabase は Site URL（トップページ）へ戻します。`/**` の指定があれば問題ありません。

## 5. サイトに接続する

`assets/community-config.js` を編集します。

```js
window.NHC_COMMUNITY_CONFIG = {
  supabaseUrl: "https://ngzzklrjbkzsnegozpps.supabase.co",
  supabaseAnonKey: "sb_publishable_xxxx",   // 公開してよい鍵（Publishable key / anon key）。Secret key は書かない
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

3. 上部ナビの自分の名前 → プロフィールページの〈投稿の承認（運営）〉、または `admin.html` を開きます。
   協力者を運営に加えるときも同じ SQL を実行します。

## 7. 承認ページ（admin.html）でできること

| 欄 | 内容 |
|---|---|
| 承認待ち / 公開済み / 却下 | 投稿の承認・却下。メモは、却下したときは投稿者本人にだけ、承認したときは公開の投稿に「運営より」として表示されます |
| 修正の申請 | 公開済みの投稿を投稿者が修正したもの。公開中の内容と修正後の内容を並べて表示します。〈修正を承認して反映〉で入れ替わり、〈却下〉なら元の内容のままです（メモは投稿者本人にだけ表示） |
| メッセージ | プロフィールページから届いたバグの報告と応援メッセージ（公開されません）。返信を書くと、送信者のプロフィールページにだけ表示されます |

新しいメッセージや修正の申請が届いてもメールでの通知はありません。ときどき `admin.html` を開いて件数を確認してください。

## 8. プロフィールページ（profile.html）

ログイン中は、上部ナビ右端の表示名がプロフィールページへのリンクになります。

| 欄 | 内容 |
|---|---|
| 表示名 | 変更すると、過去の投稿に添えられた表示名も新しい名前に変わります |
| 投稿 | 自分の投稿（承認待ち・公開済み・非公開）の確認と修正。承認待ち・非公開の投稿はその場で書き換えられ（非公開のものは承認待ちに戻ります）、公開済みの投稿は「修正の申請」になります |
| ブックマーク | ビュワーの〈☆ ブックマーク〉で追加した箇所の一覧。メモを付けられます（1 人 500 件まで） |
| バグの報告 / 応援メッセージ | 運営への連絡（1 人 24 時間に 20 件まで）。運営が返信すると、ここに表示されます |

---

## データの扱い

| 項目 | 内容 |
|---|---|
| 投稿の種類 | `comment`（コメント）/ `annotation`（注釈）/ `correction`（誤りの指摘・修正案つき） |
| 対象 | 文書（`doc`）、写本（`witness`）、セグメント（`seg_id` = TEI の `<s xml:id>`）、語（`token_index` / `token_form`） |
| 状態 | `pending` → `approved`（公開）/ `rejected`（投稿者にだけメモ付きで表示） |
| 修正 | 投稿者による修正は関数 `edit_contribution` が受け付けます。公開済みの投稿への修正は `contribution_revisions` に入り、運営が `review_revision` で承認すると本文に反映されます。本文を書き換えられるのは投稿者本人の修正だけで、運営も直接は書き換えられません |
| 連投対策 | 1 人あたりの承認待ちは 30 件まで、本文は 4000 字まで |
| ブックマーク | `bookmarks`（文書 `doc`、写本 `witness`、セグメント `seg_id`、本文の冒頭 `excerpt`、メモ `note`）。本人だけが読み書きできます |
| 運営へのメッセージ | `feedback`（種類 `kind` = `bug` / `cheer`、本文、ページ、ブラウザの種類、状態 `status` = `new` / `done`、返信 `reply`）。本人と運営だけが読めます |
| ライセンス | 公開された投稿は CC BY 4.0 で掲載（投稿フォームに明記） |

承認済みの投稿を TEI に取り込みたいときは、Supabase の **Table Editor → contributions** から
CSV でエクスポートできます（`status = approved` で絞り込み）。`seg_id` と `token_index` で本文の位置を特定できます。

## 新しいビュワーを追加したとき

`<body data-doc="文書キー">` を付け、`assets/community-config.js` と `assets/community.js` を読み込めば自動で有効になります。
セグメントは `#reading` 内の `.seg[data-id]` または `.prow[data-id]`、語は `.wseg[data-i]` を目印にしています。
`assets/community.js` の冒頭にある `DOCS` に、文書キー・ビュワーのファイル名・文書名（日・英・仏）を 1 行追加してください
（プロフィールページと承認ページでの文書名と、該当箇所へのリンクに使います）。
