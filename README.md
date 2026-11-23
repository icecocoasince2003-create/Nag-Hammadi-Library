# Sheneset — ナグ・ハマディ写本 TEIコーパス & ビュワー

ナグ・ハマディ写本(NHC I–XIII)を、**形態素ごとに意味を参照でき／写本を対照でき／他の文書の
並行箇所をたどれ／日英仏の対訳を持つ**形で Web 公開するための TEI P5 コーパスと静的サイトです。
（神学的解釈の注と『国家』の釈義・注解は、2026-11-18 に削除しました。代わりに、他の文書に同じ文言がある箇所を
並行箇所として結び、本文の印から横のパネルで読めるようにしています。下の「並行箇所」）
現在は『祝福されたエウグノストス』(Eugnostos the Blessed, NHC III,3 / V,1)を公開し、
**全13写本・52文書の目次トップとページ遷移**を備えています。

コーパス検索は単語に加え、形態素の**品詞列**（例: `ART N`）、**ANNISを参考にした詳細式**
（例: `pos="ART" .1,3 pos=/N.*/`）、**正規表現**（例: `lemma=/.*ⲛⲟⲩⲧ.*/`）に対応します。
一致する用例を文脈とともに表示し、本文への移動・CSV保存ができます。
使い方は、検索画面の右に開く〈チュートリアル〉のパネル（`search.html?view=tutorial`）で、例を試しながら読めます。
初めて開いたときは、画面の要所を〈次へ〉で順に示す操作案内が出ます。
対応構文の仕様は [コーパス検索ガイド](docs/CORPUS_SEARCH.md) を参照してください
（式の解釈と照合は `assets/corpus-query.js`、ブラウザーでの実行は `assets/corpus-search-worker.js`、テストは `tests/corpus-query.test.cjs`）。

## サイト構成（2026-11 リニューアル）

| ページ | 内容 | 管理方法 |
|---|---|---|
| `index.html` | HOME（日・英・仏、NEWS、関連サイト、文書一覧） | `python3 scripts/build_site.py` で生成。NEWS は `data/news.json`、関連サイトは `data/links.json` を編集し、`build_site.py` を実行し直す（生成のときに HTML に書き込むので、JS を動かさない読み手やリンクのプレビューにも出る。実行する前でも、ページを開いたときに JS が JSON を読み直して最新を出す） |
| `gnosticism.html` | 解説「グノーシス主義とは」（日・英・仏） | 手作業 |
| `project.html` | プロジェクト紹介。メンバー・資金協力は `data/project.json`（`public: true` のみ表示） | 手作業＋JSON |
| `eugnostos.html` | エウグノストス。`?wit=III`（祝福されたエウグノストス）/ `?wit=V`（エウグノストス）/ `?wit=SYN`（対照） | 手作業 |
| `republic.html` | 『国家』ビュワー | 手作業 |
| `reader.html` | 本文ビュワー（暫定版・未注釈）。`?doc=II-6` のように文書を指定し、NHC 全文テキストの TEI（`source/nhc_fulltext_split/tei/`）を表示する。冒頭に、その文書で確かめていないことを示す。HOME の「暫定」「未注釈」の行と検索の用例がここへリンク | `python3 scripts/build_site.py` で生成 |
| `search.html` | コーパス検索・統計。見出し下のタブで〈検索〉と〈統計〉を切替（`?view=stats` で統計を直接開く）。タブの右の〈チュートリアル〉で、使い方の説明を〈検索〉の右のパネルに開く（× で閉じる。`?view=tutorial` で開いた状態にできる。説明文は `#viewGuide` に三言語の HTML で書く）。初めて開いたときは操作案内（JS の `TOUR`）を出す。左の〈文書〉〈品詞〉の絞り込みは〈検索〉〈統計〉に共通。〈全文テキスト〉で NHC 全文（56文書）を選んで対象に加えられる。統計のセクションは JS 内の `SECTIONS` に追加 | 手作業 |
| `stats.html` | 旧コーパス統計。`search.html?view=stats` への転送のみ（`?doc=…` は引き継ぐ） | 手作業 |
| `profile.html` | プロフィール（ログイン中の利用者用）。表示名の変更、自分の投稿の確認と修正、ブックマーク、運営へのバグの報告・応援メッセージ | 手作業 |
| `admin.html` | 投稿（コメント・注釈・誤りの指摘）の承認、公開済みの投稿への修正の申請の承認、運営へのメッセージの確認（運営用） | 手作業 |

共通部品: `assets/cosmos.css`・`assets/cosmos.js`（配色と背景。ダーク＝宇宙テーマが既定、ライトモードの配色もここ）、
`assets/site.css`・`assets/site.js`（上部ナビ・言語切替・表示モード切替・XML ダウンロードメニュー・ワイド表示）、
`assets/community.*`（ログイン、承認制の投稿、ブックマーク。設定は `assets/community-config.js`、手順は `docs/COMMUNITY_SETUP.md`。
データベースの定義は `supabase/schema.sql` で、更新したときは Supabase の SQL Editor で全体を再実行します）。
上部ナビの項目は `assets/site.js` の `NAV` を編集すれば全ページに反映されます。
全ページで、上部ナビの ☀／☾ からライト／ダークの表示モードを選べます（既定はダーク、選択は全ページ共通）。
仕組みと、新しいページを対応させる手順は `COSMOS_REDESIGN.md` の末尾にあります。
表示言語は上部ナビで切り替えるほか、URL に `?lang=ja`・`?lang=en`・`?lang=fr` を付けて指定できます（例 `search.html?view=stats&lang=en`）。
最初に開くときの言語は「URL の `lang` ＞ 保存値（`localStorage` の `nhc-lang`）＞ ブラウザーの言語」の順で決め、
ブラウザーの言語が日・英・仏のどれでもなければ英語にします。URL で指定した言語は保存値にも入り、ほかのページでも続きます
（言語を切り替えても URL は書き換えません）。日英だけのビュワー（`eugnostos.html`・`republic.html`）でフランス語を選ぶと、
画面は英語、語釈と対訳はフランス語です。仕組みは `assets/site.js`（`initialLang`）と、各ページの `<head>` の 1 行スクリプト
（`scripts/build_site.py` の `LANG_BOOT` と同じもの。描画前に言語を反映して、日本語が一瞬出るのを防ぐ）です。

**同形異義語の参照**: 本文の `<w>` は `@lemma` と `@type`（品詞）の組で `lexicon.xml` を引きます。
`@ana="#lex-…"` があればそれが最優先、品詞が一致する項目がない場合だけレンマ一致の全項目を候補として表示します。

## ナグ・ハマディ写本 全文テキスト（下処理済み・39 文書は自動注釈の暫定版）

`source/nhc_fulltext_split/` に、写本 I–XIII のコプト語本文を 56 の文書単位に分けたテキスト一式があります
（13,301 セグメント・236,617 語。文書ごとの TSV・TXT・TEI P5 と、再実行用のスクリプト、加えた変更の全記録）。
内容、加えた変更、直していない点、要確認の箇所、検証の方法は
[`source/nhc_fulltext_split/README_ja.md`](source/nhc_fulltext_split/README_ja.md) にまとめてあります。

- **作業用のファイルです。** 訳はまだ付いておらず、校訂本との照合も済んでいません
  （元ファイルで落ちていた ⲍ・ⲯ を戻した 744 語のうち 42 語は確度 B。同 README の §4・§7）。
- **39 文書（写本 I–IV の I,2〜IV,1、写本 VII–XIII の VII,4〜XIII,2）は、語群・品詞・レンマ・語義を自動で付けた暫定版です（2026-11-18）。**
  人の目では確かめていません（形態素の 30% は確度 low、14% は品詞を決められず `X`）。作り方・件数・確かめていないこと・
  リポジトリに置くときに直したことは同 README の §10・§11、要確認の一覧は `source/nhc_fulltext_split/annotation/` にあります。
  残りの 17 文書（IV,2、写本 V・VI、VII,1–3）は未注釈です（本文だけを本文ビュワーで読めます）。
  TEI のヘッダー（`<publicationStmt>`）には、公開元・公開日と、下の「ライセンス」と同じ利用条件
  （コプト語本文はパブリックドメイン、TEI 符号化と下処理は CC BY 4.0）を入れてあります。
  作業用の本文であることも同じ箇所に明記しています。
  `<phr>` のあるファイルは、TEI を作るスクリプト（`make_tei.py`）が作り直さないようにしてあります。
- **文書一覧（HOME）と本文ビュワーから読めます。** HOME の写本ごとの一覧で、暫定版は「暫定」（33 行）、未注釈の文書は「未注釈」
  （17 行）と示し、どちらも本文ビュワー `reader.html?doc=II-6` へリンクしています（XI,2a–2e は XI,2 の前後の移動から開けます。
  番号は通用の番号で、一覧の VI,7a「書記による覚書」は全文テキストの VI,7 の末尾の奥書へつないでいます。VI,7a は一覧に出しますが、
  文書数には数えません（HOME の件数は全 52 文書。`scripts/build_site.py` の `UNCOUNTED`）。
  III,3・VI,5 は専用のビュワーへのリンクのままです。V,1 は語ごとの注釈がまだ無い（`eugnostos.html` の V,1 は III,3 と対応づけた枠だけ）ので
  「未注釈」とし、本文ビュワーへリンクしています（エウグノストスのビュワーの〈対照〉でも III,3 と並べて読めます）。
  I,1 は元ファイルにないので「準備中」です）。本文ビュワーは、冒頭にその文書で確かめていないこと（確度 low と `X` の割合、
  ⲍ・ⲯ を補った語の数など）を示し、語をクリックすると品詞・レンマ・語義・確度を出します。
- **コーパス検索・統計から使えます。** `search.html` の左欄〈全文テキスト〉に 56 文書が写本ごとに並び、
  選んだ文書だけを読み込んで検索・統計の対象に加えます。既定では選択も読み込みもしないので、
  注釈つきの文書（エウグノストス・『国家』）だけを見るときの一覧・数値・読み込み量は変わりません。
  どの文書も、用例から本文ビュワーへ移れます。暫定版の 39 文書は品詞・レンマでも検索できます（結果は目安）。未注釈の 17 文書は
  品詞が「未注」、レンマは語形のままなので、語形での検索（単語検索の〈語形〉、詳細式の `tok=…`）に使います
  （[コーパス検索ガイド](docs/CORPUS_SEARCH.md) の「全文テキストを検索する」）。
- 文書の一覧（題名・略号・語数）は `data/catalog.xml` の `<bibl subtype="draft">`（暫定版）と `<bibl subtype="unannotated">` で、
  `python3 scripts/sync_nhc_catalog.py --write` が `source/nhc_fulltext_split/` から書き出します
  （`tei/` を作り直したら実行。件数が `catalog.tsv` と合わなければ書き込まずに止まります。語群を付けた 39 文書は
  語の区切りを一部変えたので、語数だけは比べません）。

## フォルダ構成

```
nag_hammadi_library/
├─ index.html          ← 目次トップ(自動生成: scripts/build_site.py)
├─ eugnostos.html      ← エウグノストス・ビュワー(手作業管理)
├─ republic.html       ← プラトン『国家』断片ビュワー(手作業管理)
├─ tractate.html       ← 準備中ページ(自動生成)
├─ reader.html         ← 本文ビュワー・暫定版(自動生成。?doc=II-6 など)
├─ sitemap.xml         ← 検索エンジン向けの URL の一覧(自動生成)
├─ robots.txt          ← 管理用ページ(admin・profile)を検索エンジンから外し、sitemap.xml を示す(自動生成)
├─ README.md           ← この文書
├─ CONTRIBUTING.md     ← ★共同編集ガイド(招待を受けた方はまずこちら)
├─ .nojekyll           ← GitHub Pages 用
├─ .gitignore
├─ .vercelignore       ← Vercel で配信しないもの(いまは design/ だけ)
├─ design/             ← デザイン用の資料(アイコン・キャラクターシート・表情・配色案の PDF)。サイトからは使わず、配信しない
├─ image/
│   ├─ icon.svg         ← サイトのアイコン画像(各ページが読み込みます)
│   └─ og-image.png     ← リンクを共有したときのプレビュー画像(1200×630。scripts/make_og_image.py が作る)
├─ data/               ← サイトが読むXML(手作業の修正が入っていて、source/ からは作り直せない)
│   ├─ eugnostos_tei.xml
│   ├─ lexicon.xml
│   ├─ parallels.xml      ← 並行箇所(scripts/build_parallels.py が作る)
│   ├─ catalog.xml
│   └─ republic_*.xml
├─ source/             ← CSV／TSV(サイトに反映できるのは、いまは lexicon.csv だけ。下の「データの編集」)
│   ├─ lexicon.csv         辞書(1行=1語義／同形異義語は同じlemmaを複数行)
│   ├─ translations.csv    対訳(seg_id, ja, en, fr)
│   ├─ eugnostos_source.tsv  本文ソース(通常編集不要)
│   └─ nhc_fulltext_split/   NHC 全文テキスト(56文書の作業用ファイル。39 文書は自動注釈の暫定版。同フォルダの README_ja.md)
└─ scripts/            ← スクリプト(通常触らない)
    ├─ build_tei.py        source/ の CSV から XML を試しに生成し、data/ と比べる(既定では data/ に書き込まない)
    ├─ sync_lexicon.py     source/lexicon.csv の変更を data/lexicon.xml に反映する(xml:id は変えない)
    ├─ build_site.py       index.html / tractate.html / reader.html / sitemap.xml / robots.txt を生成
    ├─ make_og_image.py    共有用の画像 image/og-image.png を作る(rsvg-convert が要る)
    ├─ build_parallels.py  並行箇所(data/parallels.xml)を、文言の自動照合で作る
    └─ sync_nhc_catalog.py  NHC 全文テキスト(未注釈)の文書一覧を data/catalog.xml に書き出す
```

- **`data/` の XML は、`source/` の CSV から作り直せる状態ではありません(2026-11 時点)。** 生成したあとに手作業で直した内容が
  `data/` にだけあるためです。`python3 scripts/build_tei.py` は、既定では `data/` に書き込まず、生成結果を `build/tei/` に出して
  `data/` との違いを表示するだけです。どこを直せばよいかは、下の「データの編集」にあります。
- 共同編集の手順(ブランチ・Pull Request・競合の解決)は **CONTRIBUTING.md** を参照してください。
- 目次トップ(`index.html`)とビュワー(`eugnostos.html`)は `data/` のXMLと `image/icon.svg` を読み込みます。
- **サイトのアイコン**は `image/icon.svg`。お好きな画像に差し替えてください(同じ名前にすれば各ページが自動で読み込みます)。

## 収録ファイル

**`source/` の CSV／TSV** (Excel・Numbers・Googleスプレッドシート・テキストエディタで開けます。UTF-8/BOM付き)。
直した内容をサイトに反映できるのは、いまは `lexicon.csv` だけです(下の「データの編集」):

| ファイル | 役割 | 列 |
|---|---|---|
| `lexicon.csv` | **コプト語辞書** | `lemma, n, pos, grc, en, ja, fr, usg_ja, usg_en, cdo`(1行=1語義。同じ `lemma` を複数行にすると同形異義語。`cdo` は Coptic Dictionary Online の項目 ID、例 `C1789`) |
| `translations.csv` | **対訳** | `seg_id, ja, en, fr` |
| `eugnostos_source.tsv` | 本文ソース | タブ区切りのコプト語トークン列(通常は編集不要) |

**サイトが読むデータ(`data/` の XML)**:

| ファイル | 役割 | 内容 |
|---|---|---|
| `eugnostos_tei.xml` | 本文(TEI) | 二証本(III,3 全文＋V,1 並行枠)。語ごとにレンマと品詞、節ごとに対訳を持つ。生成したあと手作業で直している。 |
| `lexicon.xml` | コプト語辞書 | `lexicon.csv` の内容を `sync_lexicon.py` で反映。同形異義語は `<superEntry>`。 |
| `parallels.xml` | 並行箇所 | エウグノストス III,3 のセグメントと、同じ文言を持つ他の文書(V,1・『イエス・キリストの知恵』III,4)のセグメントを `<link>` で結ぶ。`scripts/build_parallels.py` が作る(下の「並行箇所」)。 |
| `catalog.xml` | 文書カタログ | 文書の題名・略号・関連する文書(`<relatedItem>`)。並行箇所のパネルが題名と関連文書をここから読む。 |

**生成物(自動出力。直接編集しない)**:

| ファイル | 役割 | 内容 |
|---|---|---|
| `index.html` | **トップページ(目次)** | NHC I–XIII の全文書カタログ。公開済みはビュワーへ、未整備は準備中ページへ遷移。 |
| `eugnostos.html` | **ビュワー** | エウグノストスの三言語リーダー(単一HTML)。`← 一覧`で目次へ。 |
| `tractate.html` | **準備中ページ(共通)** | `?id=コーデックス-番号` で文書を特定し「準備中」を表示。 |
| `reader.html` | **本文ビュワー(暫定版)** | `?doc=コーデックス-番号` で、`data/catalog.xml` の全文テキストの TEI を表示。冒頭に、その文書で確かめていないことを示す。 |

**スクリプト**:

| ファイル | 役割 |
|---|---|
| `build_tei.py` | CSV から本文と辞書の XML を**試しに生成して `data/` と比べる**。既定では `data/` に書き込まない(下の「データの編集」)。 |
| `build_parallels.py` | 並行箇所(`data/parallels.xml`)を文言の自動照合で作る。何も付けなければ要約の表示だけで、`--write` で書き込む。 |
| `sync_lexicon.py` | `lexicon.csv` の変更を `data/lexicon.xml` に反映する。`xml:id` は変えない。何も付けなければ変更点の表示だけで、`--write` で書き込む。 |
| `build_site.py` | `index.html`(目次)・`tractate.html`(準備中)・`reader.html`(本文ビュワー・暫定版)・`sitemap.xml`・`robots.txt` を生成。`<head>` の OGP(リンクのプレビュー)のタグもここで書く(`og_tags`)。 |
| `make_og_image.py` | リンクを共有したときのプレビュー画像 `image/og-image.png`(1200×630)を、アイコンとゲンゲンの SVG から作る。 |

## データの編集

**サイトが読むのは `data/` の XML です。2026-11 時点で、`data/` の XML は `source/` の CSV から作り直せません。**
生成したあとに手作業で直した内容(冒頭 9 節の語の切り方・語のまとまり・レンマ・文脈上の語釈、品詞の付け直し、訳文の改訂、
TEI の構造と書き方の修正)が `data/` にだけあり、CSV と生成スクリプト `build_tei.py` はそれに追いついていないためです。
CSV と生成スクリプトを XML に合わせ直すのか、生成をやめて XML を元データにするのかは、まだ決めていません。
それまでは次のとおりです。

| 直したいもの | 直す場所 | 反映のしかた |
|---|---|---|
| 辞書(語義・品詞・CDO へのリンク) | `source/lexicon.csv` | `python3 scripts/sync_lexicon.py` で変更点を確かめ、`--write` を付けて `data/lexicon.xml` に書き込む(`xml:id` は変わらない) |
| 本文(語の切り方・語のまとまり・レンマ・品詞・文脈上の語釈)と対訳 | `data/eugnostos_tei.xml` | 直接直す |
| 並行箇所 | `data/parallels.xml` | `python3 scripts/build_parallels.py` で要約を確かめ、`--write` で書き込む(本文を直したあとも実行し直す)。手で確かめた対応を足すときは `resp="#align"` を付けずに `<link>` を書く(スクリプトはそれを上書きせずに止まる) |

- `translations.csv`・`eugnostos_source.tsv` を直しても、サイトには反映されません。
- すでにある見出し語に 2 つ目以降の語義の行を足した場合(新しい同形異義語)は、`sync_lexicon.py` は報告するだけで、
  `data/lexicon.xml` には入りません。`<superEntry>` にまとめる作業は手で行います。

### build_tei.py は data/ を書き換えない

```
python3 scripts/build_tei.py
```

は、CSV・TSV から XML を生成して `build/tei/`(git の管理外)に書き出し、`data/` の現在のファイルと比べて、
置き換えた場合に**消えるもの・増えるもの**を表示します。**`data/` には書き込みません。**

- `--write-data` を付けると `data/` も更新しますが、いまのファイルの内容が少しでも消える・変わる場合は、書き込まずに止まります
  (追加だけのときにだけ書き込みます)。いまの生成結果は `data/eugnostos_tei.xml` と `data/lexicon.xml` の手作業の修正を
  含まないので、止まります。
- `--write-data --allow-loss` は、失われるものがあっても置き換えます(前のファイルは `build/tei-backup/` に残ります)。
  **いまの状態では使わないでください。** 2026-07-04 に、当時のこのスクリプトの出力で `data/` が上書きされ、
  XML に直接加えてあった注釈 7 件と辞書の項目 189 件(4,014 → 3,825)が `data/` から消えました
  (コミット `249a222`。直前の状態は `1f97a93` に残っています)。

以下は CSV の列の説明です。

### lexicon.csv（辞書・同形異義語）
1行が1つの語義です。`lemma`(コプト語の見出し)・`n`(語義番号)・`pos`(品詞コード)・
`grc`(ギリシア借用語なら `Y`)・`en`/`ja`/`fr`(語義)・`usg_ja`/`usg_en`(用法ヒント)。

- **ふつうの語**:その `lemma` を1行だけ書く(`n=1`)。
- **同形異義語**:同じ `lemma` を**複数行**書き、`n=1,2,3…` と番号を振る。各行が別語義になり、
  ビュワーでは①②…と列挙されます。`n=1` が既定(本文に最初に出る語義)です。
  例:`ⲡⲉ`(`COP`「～である」／`N`「天」)、`ⲙⲉ`(`NEG`否定／`N`「真理・愛」)。
- `pos` コード例:`N`名詞 `V`動詞 `ADJ`形容詞 `PREP`前置詞 `CONJ`接続詞 `PTC`不変化詞
  `NEG`否定 `NUM`数詞 `ART`冠詞 `PPER`人称代名詞 `POSS`所有冠詞 `COP`繋辞 `AUX`助動詞
  `PRET`過去辞 `NPROP`固有名詞 `INTERJ`間投詞。

### translations.csv（対訳）
`seg_id`(本文セグメントのID。`eugnostos_source.tsv` のID、冒頭は `INCIPIT`)に対し
`ja`/`en`/`fr` の対訳を書きます。空欄の言語は「準備中」と表示されます。

## サイト構成と画面遷移

```
index.html(目次:全52文書)
   ├─ 公開済み ──▶ eugnostos.html(ビュワー) ──▶ ← 一覧 で index.html へ
   └─ 準備中   ──▶ tractate.html?id=II-5 など(準備中の案内) ──▶ ← 一覧 で index.html へ
```

- 目次の各行は文書1点。`公開`バッジの行はビュワーへ、`準備中`バッジの行は共通プレースホルダへ遷移します。
- 文書IDは `コーデックス-番号`(例 `III-3` = エウグノストス、`II-5` = 世界の起源について)。
- 画面遷移は、対応ブラウザではクロスドキュメントの View Transitions(`@view-transition`)で滑らかにフェードします。

### 新しい文書を追加するには

1. その文書の本文(`<name>_tei.xml`)を用意し、語彙を共通の辞書(`lexicon.xml`)に足す。他の文書と同じ文言を持つ箇所があれば、
   `build_parallels.py` の `TARGETS` に対応先を足して並行箇所を作る。
2. `eugnostos.html` を雛形に `<name>.html` ビュワーを作成(または共通ビュワー化)。
3. `build_site.py` の `CODICES` で当該行の status を `S`(準備中)→`A`(公開)に変更し、
   `href_for()` の遷移先をそのビュワーに向ける。`python3 scripts/build_site.py` で目次を再生成。

## 公開方法

リポジトリの中身(HTML・`assets/`・`data/`・`source/nhc_fulltext_split/tei/`・`image/`・`iiif/`)を
**同じ構成のまま**任意のWebサーバ(GitHub Pages, Netlify, さくら, S3 など)に
アップロードするだけです。入口は `index.html`。すべてサーバ不要の
静的ファイルで、ビュワーは `data/` の XML を `fetch` で読み込みます(並行箇所のパネルと〈対照〉は、対応先の本文を
`source/nhc_fulltext_split/tei/` から必要になったときに読み込みます)。

> ローカルで `eugnostos.html` をダブルクリックして開いた場合(`file://`)は、ブラウザの制約で
> 外部XMLを読めないため、**埋め込みのサンプル(冒頭十数節)**が表示されます。全文を見るには
> Webサーバ経由で開いてください(『国家』のビュワーは、画面の「XMLを開く」/ドラッグ＆ドロップで本文・辞書・ギリシア語・
> カタログを読み込むこともできます。ファイルの種類は中身から自動判別します)。

フォントは Google Fonts(Spectral / Inter / Noto Sans JP / Noto Serif JP / **Noto Sans Coptic**)を
読み込みます。オフライン公開する場合はこれらをローカルにセルフホストしてください
(Coptic字形が無い環境では汎用セリフにフォールバックします)。

## ビュワーの使い方

- **写本タブ**「III,3 本文 / V,1 / 対照」で証本を切替。V,1 には語ごとの注釈がまだ無いので、〈V,1〉はそのことと、本文を読める場所
  (〈対照〉〈並行箇所〉、本文ビュワー `reader.html?doc=V-1`)の案内だけを出します。〈対照〉は左に III,3、右に V,1 の本文(未注釈の作業用テキスト)を、
  並行箇所の対応で並べます。一致する文字に色が付きます。対応の見つからないセグメントが続くところは 1 行にまとめ、
  前後の対応のあいだにある V,1 の本文を「対応は未確認」として示します。
- **形態素をクリック**→ 語義カード(語形・レンマ・品詞・日英仏語釈・借用語表示)。
- **同形異義語**(綴りが同じで意味が異なる語)は、本文中で金色の点線＋`⁝`で示し、語義カードに①②…と**全語義を品詞・用法つきで列挙**します(既定語義にはバッジ表示)。
- **「語釈を重ねる」**でインターリニア(各語の下に語義)を表示。「語釈: 日/英/仏」で言語を巡回切替(419項目すべてに三言語の語義あり)。
- **「訳: 日/英/仏」**で対訳の言語を巡回切替。
- **並行箇所**: 他の文書にも同じ文言があるセグメントには、訳の後ろに `‖ V,1`・`‖ III,4` のような印が付きます。
  押すと右のパネルに対応先の本文が出ます(広い画面では本文の右に並び、狭い画面では本文に重なります)。
  - 広い画面(幅 1100px 以上)では、パネルの左端の取っ手をドラッグすると幅を変えられます。取っ手にフォーカスして
    ← → キーでも変えられます(Shift で大きく、Home / End で最小・最大)。ダブルクリックか Enter で元の幅(画面の 30%、
    320〜460px)に戻ります。幅は 280px から、本文の列が 420px 残るところまでで、このブラウザーに記憶されます
    (`localStorage` の `nhc-par-w`)。
  - パネルの上に III,3 のセグメント、下のタブで文書を切替。一致する文字に両方とも色が付き、「III,3 の文字の一致」は
    III,3 側の文字のうち対応先と一致した割合です。〈前後も表示〉で対応先の前後 2 セグメントも出ます。
  - 〈‹ ›〉でその文書と対応する前・次のセグメントへ移ります。本文も一緒に動きます。
  - 対応の見つからないセグメントでは、前後の対応箇所のあいだにある対応先の本文を「対応は未確認」として畳んで示します。
  - 左の文書パネルの〈‖ 並行箇所〉で、文書ごとの一覧(対応するセグメントの数、最初の並行箇所へのボタン、コーパス検索への
    リンク)と、箇所は結んでいないが関連する文書(カタログの `<relatedItem>`。『世界の起源について』など)を開けます。
- **検索**=コプト語形・レンマ・英語/日本語語釈・対訳を横断検索。
- **上部ナビの ☀／☾** で表示モード（ライト／ダーク）を切替（全ページ共通）。

## TEI設計の要点（ファイルの分離）

データは役割ごとに別々の TEI 文書(本文・辞書・並行箇所・カタログ)へ分離し、ID参照で連携させています。

**① 本文 `eugnostos_tei.xml`** — ルート `<TEI xml:lang="cop">` 直下の `<group>` が
二つの `<text type="witness">` を並置:
- `wit-III`(NHC III,3, 70–90)= **全文を符号化**。
- `wit-V`(NHC V,1, 1–17)= `@corresp` で対応づけた**並行証本の枠**(本文は欠損のため `<gap>`＋編集注)。

各証本の `<s>` は、`<div type="tractate">` の中の `<ab>` にまとめて入れてあります（TEI では `<s>` を `<div>` の直下に置けないため）。
ビュワーと検索は `<text type="witness">` の子孫として `<s>` を探すので、`<ab>` の有無で動作は変わりません。

各形態素は次の形(語義は持たず、辞書を `@lemma` で参照):
```xml
<w type="N" lemma="ⲥⲟⲫⲓⲁ" xml:lang="grc">ⲥⲟⲫⲓⲁ</w>
```
`@type`=品詞、`@lemma`=レンマ、ギリシア借用語は `@xml:lang="grc"`。セグメント `<s>` は
`xml:id` と通し番号 `@n` を持ちます。冒頭と奥書のセグメントは `<s type="incipit">`・`<s type="colophon">`。

続けて書かれる**語群**（bound group。正書法上の 1 語）は `<phr>` でまとめます。Coptic SCRIPTORIUM の TEI と同じ書き方です。
```xml
<s xml:id="rep-1" n="1">
  <phr>
    <w type="PREP" lemma="ⲛ">ⲛ</w>
    <w type="ART" lemma="ⲟⲩ">ⲟⲩ</w>
    <w type="N" lemma="ⲗⲟⲅⲟⲥ" ana="#gl-discussion" xml:lang="grc">ⲗⲟⲅⲟⲥ</w>
  </phr>
</s>
```
**対訳**は `<s>` の中には書きません。同じ証本の `<body>` の末尾に、言語ごとの `<div type="translation">` を置き、
`@corresp` で本文の `<s>` と対応づけます。
```xml
<div type="translation" xml:lang="ja">
  <ab>
    <seg corresp="#rep-1">さて、議論がこの段階に至ったからには、</seg>
  </ab>
</div>
```
**文脈上の語釈**（その箇所での意味。辞書の語義とは別のもの）は、`<w>` の `@ana` が `<standOff>` の `<interp>` を指す形で持ちます。
同じ語釈は 1 つの `<interp>` を何度でも指せます。`@ana` には、辞書の語義を固定するポインタ（`#lex-…`。下の ② を参照）と
語釈のポインタ（`#gl-…`）を、空白で区切って並べて書けます。
```xml
<standOff>
  <interpGrp type="gloss" xml:lang="en">
    <interp xml:id="gl-discussion">discussion</interp>
  </interpGrp>
</standOff>
```
訳や語釈を足すとき:

- **訳を足す**: その言語の `<div type="translation">` に `<seg corresp="#セグメントの xml:id">訳</seg>` を、本文と同じ順番の位置に足します
  （その言語の `<div>` がまだ無ければ、`<body>` の末尾に作ります）。
- **語釈を足す**: `<interpGrp type="gloss">` に `<interp xml:id="gl-…">語釈</interp>` を足し、`<w>` に `ana="#gl-…"` を書きます。
- 書いたあとは `python3 scripts/check_tei.py` で、指す先が切れていないか・同じ `<s>` に訳が 2 つ無いかを確かめられます。

**② コプト語辞書 `eugnostos_lexicon.xml`** — レンマ語義集(419項目):
```xml
<entry xml:lang="grc">
  <form type="lemma"><orth>ⲥⲟⲫⲓⲁ</orth></form>
  <gramGrp><pos>N</pos></gramGrp>
  <sense>
    <cit type="translation" xml:lang="en"><quote>wisdom, Sophia</quote></cit>
    <cit type="translation" xml:lang="ja"><quote>知恵・ソフィア</quote></cit>
    <cit type="translation" xml:lang="fr"><quote>Sagesse, Sophia</quote></cit>
  </sense>
</entry>
```
ビュワーは本文の `@lemma` と `<orth>` を突き合わせて語義を表示します。

**同形異義語(homograph)**は、1つの綴りに対して複数の `<entry>` を `<superEntry>` にまとめます。各 `<entry>` は固有 `xml:id`(例 `lex-…-1` / `lex-…-2`)・`<gramGrp><pos>`・用法ヒント `<usg type="hint">`・三言語語義を個別に持ちます。例:`ⲡⲉ`(繋辞「～である」／名詞「天」)、`ⲙⲉ`(否定／真理・愛)、`ⲛⲁ`(未来助動詞／与格前置詞／「憐れむ」)など全15形・32語義。本文側は `<w ana="#lex-…-2">` で特定語義を指定でき(任意)、ビュワーは指定があればその語義を、無ければ先頭(最頻)語義を既定として表示します。

**③ 並行箇所 `parallels.xml`** — `<standOff>` に、対応先の文書ごとの `<linkGrp type="parallel">` を置きます。
`@subtype` は関係の種類(`witness` = 同じ文書の別の写本、`rewriting` = 同じ文言を別の形で用いる文書)、`@corresp` は
カタログの 2 文書(`catalog.xml#doc-eugnostos catalog.xml#doc-III-4`)、`<desc>` は日英の説明です。
各 `<link>` は本文のセグメントと対応先のセグメントを 1 組ずつ結びます。
```xml
<linkGrp type="parallel" subtype="rewriting" xml:id="par-eug-SJC" corresp="catalog.xml#doc-eugnostos catalog.xml#doc-III-4">
  <desc xml:lang="ja">『イエス・キリストの知恵』…</desc>
  <link target="eugnostos_tei.xml#III-7505191 ../source/nhc_fulltext_split/tei/03-4_sophia-of-jesus-christ.xml#III-7505340" cert="high" resp="#align"/>
</linkGrp>
```
`@cert` は一致の強さ(high / medium / low)、`resp="#align"` は自動の照合で作ったことを示します(ヘッダーの `<respStmt xml:id="align">`)。
1 つのセグメントが複数のセグメントに対応するときは、`<link>` を複数書きます。対応先の本文は未注釈の全文テキスト
(`source/nhc_fulltext_split/tei/`)で、頁・行番号が無いのでセグメントの番号(`@n`)で示します。

**神学的解釈の注と主題分類は 2026-11-18 に削除しました。** `eugnostos_theology.xml`(注 17 件・主題 15)、
`republic_commentary.xml`(釈義・注解 17 件・主題 16)、その元の `source/notes.csv`・`source/themes.csv`、
本文の `<s>` の主題(`@ana="#th-…"`)と `eugnostos_tei.xml` のヘッダーの `<taxonomy>`、補助の `scripts/sync_theology_ana.py` が
対象です。削除前の内容はコミット `1950340` に残っています。

### TEI スキーマとの適合（2026-11-18 時点）

`data/` の 6 ファイルと `source/nhc_fulltext_split/tei/` の 56 ファイルは、すべて TEI P5 の汎用スキーマ
`tei_all.rng`（P5 4.3.0）で妥当です（語群の暫定版を入れたあと、2026-11-18 に検証し直しました）。
TEI に無い独自の要素・属性は使っていません。

2026-11-18 に、それまでの独自の書き方を TEI 標準の書き方に移しました。本文・訳・語釈の中身は変えていません。

| 以前の書き方 | いまの書き方（TEI 標準） |
|---|---|
| `<phy>`（語群） | `<phr>` |
| `<s transJa="…" transEn="…" transFr="…">` | `<div type="translation" xml:lang="…">` の中の `<seg corresp="#…">` |
| `<w gloss="…">`（文脈上の語釈） | `<w ana="#gl-…">` と `<interp xml:id="gl-…">` |
| `<s subtype="incipit">`（`@type` なし） | `<s type="incipit">` |
| ギリシア語層の `<s corresp="rep-1"><grc>…</grc><ja>…</ja><en>…</en></s>` | `<s xml:id="grc-1" corresp="republic_tei.xml#rep-1">…</s>` と、訳の `<div type="translation">` |
| `cert="prov"`（暫定整列） | `cert="low"` |

ビュワー（`eugnostos.html`・`republic.html`）と検索（`search.html`）は、以前の書き方のファイルも引き続き読めます。
以前の書き方のファイルは `python3 scripts/migrate_tei_markup.py ファイル名 --write` で直せます（`--write` を付けなければ、何が変わるかを表示するだけです）。

**点検のしかた。** データを直したら、次を実行してください。スキーマでは分からない誤り
（訳や語釈の指す先が無い、同じ `<s>` に訳が 2 つある、以前の書き方が残っている、など）を報告します。

```
python3 scripts/check_tei.py
```

スキーマでの検証も併せて行うには、スキーマを取得して場所を渡します
（スキーマはリポジトリに入れていません。TEI のサイトから取得します。約 1 MB。`xmllint` は macOS に入っています）。

```
curl -o ~/Downloads/tei_all.rng https://tei-c.org/Vault/P5/4.3.0/xml/tei/custom/schema/relaxng/tei_all.rng
python3 scripts/check_tei.py --schema ~/Downloads/tei_all.rng
```

## 並行箇所(data/parallels.xml)の作り方

```
python3 scripts/build_parallels.py           # 要約と、いまの data/parallels.xml との違いを表示するだけ
python3 scripts/build_parallels.py --write   # data/parallels.xml に書き込む
```

エウグノストス III,3 の各セグメントについて、同じ文言が残っている箇所を探して結びます。対応先は、いまは次の 2 文書です。

| 対応先 | 関係 | 結んだセグメント(2026-11-18) |
|---|---|---|
| エウグノストス V,1(`05-1_eugnostos.xml`) | 同じ文書のもう一つの写本。文言の一致しない箇所が多い | III,3 の 141 のうち 90 ↔ V,1 の 269 のうち 158(`<link>` 173 本) |
| 『イエス・キリストの知恵』III,4(`03-4_sophia-of-jesus-christ.xml`) | エウグノストスと同じ文言が、問答の形で長く続く | III,3 の 141 のうち 90 ↔ III,4 の 189 のうち 97(`<link>` 132 本) |

- **方法.** 両方の本文から語の区切り・上線などの合成記号・記号を除いて 1 本の文字列にし、順序を保ったまま一致する 4 文字以上の
  部分を探します(`difflib.SequenceMatcher`)。セグメントの組で 8 文字以上(短いセグメントでは 5 文字以上で、どちらかの半分以上)
  一致すれば結びます。詳しくはスクリプトの冒頭と `parallels.xml` のヘッダーにあります。ビュワーの色付けも同じ考え方です。
- **結ばれないもの.** 言い換えられた箇所(V,1 は訳が違う箇所が多い)。ビュワーは、前後の対応箇所のあいだにある本文を
  「対応は未確認」として見せます。
- **ほかの文書.** NHC の残りの 53 文書とは、定型句(「すべてのアイオーンとその世界」「世界の基が置かれた時から」など、20 文字台)
  より長い一致がありません。『世界の起源について』(II,5)は、箇所は結ばず、カタログの `<relatedItem>` で文書どうしを関連づけ、
  両書の文学的な接点を論じた研究(L. Painchaud, JBL 114 (1995) 81–101)を示しています。
- **確かめていないこと.** 校訂版(Parrott, NHS 27 など)の対観表とは照合していません。対応先の本文も校訂本と照合する前の作業用テキストです。
- 本文(`eugnostos_tei.xml` の III,3)や `source/nhc_fulltext_split/tei/` を直したら、実行し直してください。

## データの性質(重要)

- **コプト語本文はパブリックドメイン**です。一方、**形態素グロス・対訳は本プロジェクトに
  よる原文オリジナルの初版シード**で、**CC BY 4.0** で提供します。**フランス語訳・日本語訳・英訳は、
  Pasquier(BCNH)・Parrott(NHS 27, Brill 1991)・小林稔訳等を参照して作成した
  オリジナル**で、これらの翻訳を転記したものではありません。権威あるフランス語訳は **Pasquier の校訂**を参照してください。
- 語釈は**レンマ単位(文脈非依存)**で、全トークンの**約87%**に付与済み。残り(稀な語形)は
  `source/lexicon.csv` に行を足し、`scripts/sync_lexicon.py` で `data/lexicon.xml` に反映すればカバーできます。
- 対訳は**日・英・仏の三言語**。枠組み(冒頭・結び)と教義上の要所を中心に**29節**を整備済み。未整備の節は
  インターリニア語釈で意味を追え、訳は「準備中」と表示されます。
- これらは**校訂版に照らした検証・拡充を前提とするシード**です。学術利用の際は
  Parrott 1991 等の原典・校訂と必ず照合してください。

## 拡張のしかた

1. **内容を編集**:上の「データの編集」の表のとおりです。辞書は `lexicon.csv` を直して `sync_lexicon.py` で反映し、
   本文・対訳は `data/` の XML を直接直します。並行箇所は `build_parallels.py` で作り直します。
2. `python3 scripts/build_tei.py` は、**`data/` を作り直すためには使いません**。いまの生成結果は `data/` の手作業の修正を
   含まないためです(何も付けなければ `data/` には書き込まず、違いを表示するだけです)。
3. **ビュワーへ反映**:Webサーバ経由で `eugnostos.html` を開けば、`data/` のXMLを自動で読み込みます
   (同じフォルダに置くだけ)。`file://` で直接開く場合のオフライン用埋め込みサンプルだけは、
   `eugnostos.html` を雛形(`viewer_template.html`)から作り直して `<script id="tei-main">` /
   `id="tei-lex">` / `id="tei-theo">` の中身を差し替えます。
4. V,1 本文を実体化するには、`data/eugnostos_tei.xml` の `wit-V` にある `<gap>` を、校訂版のトークン列に拠った
   `<w>` 群に置き換えます(`build_tei.py` の `emit_witness_V` を書き換えて生成し直す方法は、2. の理由でいまは使えません)。

> **他の NHC 文書へ展開**するときも同じCSVの形式が使えます。文書ごとに `<name>_*.csv` と
> `<name>_source.tsv` を用意し、`build_tei.py` のファイル名を差し替えれば、同じ仕組みで本文・辞書の
> XMLが作れます。同形異義語も `lexicon.csv` に行を足すだけで増やせます。
> ただし、生成結果(`build/tei/` に出ます)は、生成スクリプトが作られた当時の書き方のままで、そのあと `data/` で行った
> 構造と書き方の修正は入っていません(たとえば `<s>` が `<div>` の直下、辞書の `<entry>` が `<list>` の中、
> 辞書の `xml:id` が実行のたびに変わる)。そのままでは TEI として妥当ではないので、公開する前に直す必要があります。


## 辞書データの出典（加筆分）

`lexicon.csv` の見出し語・品詞・借用語フラグの一部は、以下の Coptic SCRIPTORIUM 注釈テキスト（CC BY 4.0）からレンマと品詞を抽出して加筆しました（語義の日英仏は本プロジェクトの自筆）。

- *Gospel of Thomas* (NHAM.02 = NHC II,2), Coptic SCRIPTORIUM / Dilley ほか.
- Shenoute, *Abraham Our Father*（MONB.XL / MONB.YA / MONB.ZH 断片）, Coptic SCRIPTORIUM / Krawiec ほか.

- コプト語魔術文書4点（呪詛・護符）, *Kyprianos* / Coptic Magical（BKU 1 5、O.Crum ST 18、P.CtYBR inv. 1800、P.Mich. inv. 1523）.

- *Pistis Sophia*（全4書＋追記(Postscript), アスキュー写本）, CMCL / Petermann（CC BY 4.0）.

- サヒド語旧約聖書 *ヨナ書*・*ルツ記*, Coptic SCRIPTORIUM / Sahidica（coptot, CC BY 4.0）.

- サヒド語新約聖書 *マルコ福音書*（全16章）, Coptic SCRIPTORIUM / Sahidica（sahidica, CC BY 4.0）.

いずれも CC BY 4.0。本コーパスを公開する際は上記への帰属を併記してください。

## ライセンス

| 対象 | ライセンス |
|---|---|
| ソースコード（HTML のマークアップ・CSS・JavaScript、`assets/`、`scripts/` の Python、`supabase/schema.sql`） | [MIT License](LICENSE) |
| 本プロジェクトが作成したデータとテキスト（`data/`・`source/` の TEI 符号化・対訳・語釈・辞書・並行箇所の一覧、ページ内の解説文） | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) |
| コプト語本文、プラトン『国家』のギリシア語本文（OCT/Burnet） | パブリックドメイン |
| 第三者の資料（上記「辞書データの出典」の Coptic SCRIPTORIUM ほか、IIIF で表示する写本画像、外部のフォント・ライブラリ） | 各提供元の条件に従います |

挿絵・アイコンなどの画像（`image/`）は本プロジェクトのオリジナル・アートワークで、上表のライセンスには含めていません。

Code is released under the MIT License (see `LICENSE`). Data and texts created by the project are released under CC BY 4.0. The Coptic and Greek source texts are in the public domain.

## 参考文献

- Douglas M. Parrott (ed.), *Nag Hammadi Codices III,3–4 and V,1 with Papyrus Berolinensis 8502,3:
  Eugnostos and the Sophia of Jesus Christ* (Nag Hammadi Studies 27), Brill, 1991.
- M. Scopello & M. Meyer, "Eugnostos the Blessed," in *The Nag Hammadi Scriptures*, HarperOne, 2007.
- Anne Pasquier, *Eugnoste (NH III,3 et V,1)*, Bibliothèque copte de Nag Hammadi (texte ＋ volume de commentaire), Presses de l'Université Laval / Peeters.
- 小林稔訳「エウグノストス」(邦訳, §1–§43).
- Louis Painchaud, "The Literary Contacts between the Writing without Title *On the Origin of the World* (CG II,5 and XIII,2) and *Eugnostos the Blessed* (CG III,3 and V,1)," *JBL* 114/1 (1995) 81–101.


## プラトン『国家』 NHC VI,5 (republic.html)

- ビュワー: `republic.html`(eugnostos と同じデザイン／操作)。データ: `data/republic_tei.xml`(手編集する作業用TEI)。
- 構造: `<ab>` 単位、`<seg type="coptic">` 内に `<phr>` で形態素をグループ化し各 `<w>`(`lemma`/`type`/`gloss`/`ref`)を保持、`<seg type="translation" xml:lang="en|ja">` に対訳を直書き。`<phr>` 内の `<w>` は表層形(例 `ⲁ-`, `ⲡⲓ-`, `ⲙⲙⲟ=ⲥ`)をそのまま連結表示。
- 形態素クリックで品詞・英語語義・Coptic Dictionary へのリンク。行間グロス・日英訳切替・アイオーン/アルコーン対応。
- **著作権**: コプト語本文(NHC VI,5)はパブリックドメイン。**日本語訳・英語訳はいずれも本プロジェクトによる**(CC BY 4.0。英語訳は 2026-11 に本プロジェクトの独自訳へ置き換え済み)。


## プラトン『国家』 NHC VI,5 (republic.html) — 改訂

- `data/republic_tei.xml` を **eugnostos と同形式**に再構成: `<text type="witness" xml:id="wit-rep">` → `<s xml:id="rep-N" n="N" transJa="…" transEn="…" transGrc="…">` → `<phy>`（旧 `<phr>`）→ `<w type/lemma/gloss/xml:lang/ref>`。対訳は `<s>` の属性（transJa/transEn/transGrc）。
- **ギリシア語層を追加**: `transGrc` に Plato, *Republic* 588b–589b（OCT/Burnet, パブリックドメイン）を一次整列で付与（象徴的な21/55セグメント）。**校訂版での検証・残りの整列はこれから**。
- `republic.html` は **2カラム対訳**: 左にコプト語本文（形態素クリックで品詞・語義・辞書リンク）＋日英訳、**右にギリシア語**。ヘッダの「ギリシア語」ボタンで右ウィンドウの表示/非表示、「訳: 日/英」「語釈を重ねる」「アイオーン/アルコーン」対応。
- **著作権**: コプト語＝PD、日本語・英語＝本プロジェクト（CC BY 4.0）、ギリシア語＝PD。
- **2026-11-18 の修正**: `<s>` を `<ab>` で包み（`<div>` の直下には置けないため）、改頁を TEI の `<pb n="…"/>` に統一しました（以前は `<p n>` と `<pd>`）。
  誤記も 2 か所直しています: 大文字の `<W>`（この形態素 `ⲉⲧ` はビュワーにも検索にも出ていませんでした）と、`<lb>` の `breal`（正しくは `break`）。
- **2026-11-18 の移行（TEI 標準の書き方）**: この README の『国家』の説明に出てくる `<phy>`、`<s>` の属性 `transJa`/`transEn`、`<w gloss>` は、それぞれの時点での書き方です。
  いまは `<phr>`、`<div type="translation">`、`@ana` → `<interp>` で書いています（上の「TEI スキーマとの適合」に対応表があります）。
  ギリシア語層 `data/republic_greek.xml` も、`<s xml:id="grc-N" corresp="republic_tei.xml#rep-N">` と訳の `<div type="translation">` に直しました。


## Republic: 辞書リンクを lexicon に分離（改訂）

- `<w>` の辞書リンク `ref="https://coptic-dictionary.org/…"` を本文 TEI から除去し、補助ファイル **`data/republic_lexicon.xml`**（74エントリ）に集約しました。
- lexicon は **(lemma + 品詞)** をキーに `<entry><form><orth>…</orth></form><gramGrp><pos>…</pos></gramGrp><xr type="dict"><ref target="…"/></xr></entry>` 形式（eugnostos_lexicon と同系統）。同形異義語（例 `ⲛ`=前置詞/冠詞/否定/代名詞）は品詞で別エントリに分かれます。
- `republic.html` は lexicon を読み込み、形態素ポップオーバーの「Coptic Dictionary →」リンクを **lemma+品詞 → lexicon** で解決します（本文には辞書リンクを持ちません）。語義(gloss)は文脈依存のため従来どおり `<w gloss>` に残しています。


## Republic: eugnostos と同一エンジンに統一（最新）

- `republic.html` は **`viewer_template.html`（eugnostos.html と同じビュワー・エンジン）から生成**。語彙ポップオーバー（lemma+品詞→品詞・日英語義・辞書リンク、同形異義の自動選択）、行間グロス、訳の言語切替、検索、アイオーン/コーデクス表示——すべて eugnostos と同一の挙動です。
- **唯一の違いがギリシア語**：eugnostos が右パネルに出していた「神学的解釈」（2026-11-18 に削除）の位置に、republic は **ギリシア語原文（`<s>` の @transGrc を連続表示）** を出します。
- 単一証本のため、写本タブ（III/V/対照）と流出テーマ柱は不使用（エンジンは保持・非表示）。
- データは eugnostos と同形式の2ファイル：`data/republic_tei.xml`（witness/s/phy/w + transJa/transEn/transGrc）と `data/republic_lexicon.xml`（lemma+品詞→日英 sense + dict ref、71エントリ）。
