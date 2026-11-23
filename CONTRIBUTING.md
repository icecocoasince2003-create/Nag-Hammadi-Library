# 共同編集ガイド（CONTRIBUTING）

> **In short (English).** This guide is for people who help edit Sheneset, a TEI P5 edition of the Nag Hammadi
> Codices (<https://sheneset.vercel.app/>). Work on a branch and open a pull request against `main`; the project
> lead reviews and merges it. Do not edit the generated files (`index.html`, `tractate.html`, `reader.html`,
> `sitemap.xml`, `robots.txt`): change `scripts/build_site.py` or its data and run it again. The XML in `data/`
> contains hand corrections, so edit it in place and never regenerate it with `scripts/build_tei.py`. Lexicon
> changes go through `source/lexicon.csv` and `scripts/sync_lexicon.py`. Never change an existing `xml:id`.
> Before opening a pull request, run `python3 scripts/check_tei.py`, `node --test tests/corpus-query.test.cjs`,
> `python3 scripts/check_style.py` and `python3 scripts/build_site.py --check`; GitHub runs the same checks.
> Translations, glosses and notes are the project's own work (CC BY 4.0): do not copy published translations or
> commentaries. If you use generative AI, say so: in the pull request description, or in the commit message
> when you commit without a pull request. Contact: see the project page (`project.html`, “Join the team”).

## 1. はじめに

この文書は、Sheneset（ナグ・ハマディ写本コーパス）のデータ（TEI の本文・対訳・語釈・辞書）や、サイトのページ・
スクリプトを直す人のための手引きです。招待を受けた共同編集者（Collaborator）の方は、まずここを読んでください。
リポジトリ全体の説明は [README.md](README.md) にあります。

- 公開サイト: <https://sheneset.vercel.app/>（`main` に入った変更が、そのまま公開されます）
- 連絡先: [プロジェクトのページ](https://sheneset.vercel.app/project.html#recruit)の「メンバー募集」と同じです
  （代表：生田目 心愛　`icecocoa.since2003[@}gmail.com`。迷惑メール対策のため @ を [@} と書いています。送るときは @ に置き換えてください）。
  サイトの不具合の報告は、ログインしたあとのプロフィールページからも送れます。

## 2. 準備

```
git clone https://github.com/icecocoasince2003-create/Nag-Hammadi-Library.git
cd Nag-Hammadi-Library
```

- **Python 3.9 以上。** サイトの生成とデータの点検に使うスクリプト（`scripts/`）は、Python の標準ライブラリだけで動きます。
  例外は画像を作る 2 つで、共有用の画像を作る `scripts/make_og_image.py` には `rsvg-convert`（librsvg）が、
  サイトのアイコンを埋め込み直す `scripts/update_icon.py` には macOS の `qlmanage`・`sips`（か Python の `cairosvg`）が要ります。
- **Node.js。** コーパス検索のテスト（`node --test tests/corpus-query.test.cjs`）に使います。追加のパッケージは要りません
  （GitHub の自動チェックは Node 22 で動かしています）。
- **ローカルで表示する。** ビュワーは `data/` の XML を `fetch` で読むので、ファイルをダブルクリックして開く（`file://`）と
  本文が出ません。リポジトリのルートで簡単な Web サーバーを動かし、ブラウザーで開きます。

  ```
  python3 -m http.server 8000
  ```

  → <http://localhost:8000/>（コーパス検索は <http://localhost:8000/search.html>）。
  ログインや投稿の機能は、URL の末尾に `?community=demo` を付けると、ブラウザーの中だけで動くデモになります
  （[docs/COMMUNITY_SETUP.md](docs/COMMUNITY_SETUP.md)）。

## 3. どのファイルを直すか

| 直したいもの | 直す場所 | そのあとで実行するもの |
|---|---|---|
| HOME の文書一覧・件数、準備中ページ、本文ビュワー（`reader.html`）の画面 | `scripts/build_site.py`（`CODICES` など） | `python3 scripts/build_site.py` |
| HOME の NEWS・関連サイト | `data/news.json`・`data/links.json` | `python3 scripts/build_site.py`（生成のときに HTML に書き込む） |
| エウグノストス・『国家』の本文（語の切り方・語群・レンマ・品詞・文脈上の語釈）と対訳 | `data/eugnostos_tei.xml`・`data/republic_tei.xml`・`data/republic_greek.xml` を直接 | `python3 scripts/check_tei.py`（本文を直したら下の並行箇所も） |
| コプト語辞書（語義・品詞・Coptic Dictionary Online へのリンク） | `source/lexicon.csv` | `python3 scripts/sync_lexicon.py` で変更点を確かめ、`--write` で `data/lexicon.xml` に書き込む |
| 並行箇所 | （自動で作る） | `python3 scripts/build_parallels.py` で要約を確かめ、`--write` で `data/parallels.xml` に書き込む |
| 全文テキスト（`source/nhc_fulltext_split/`）の文書一覧 | （自動で作る） | `python3 scripts/sync_nhc_catalog.py --write`（`data/catalog.xml` の `BEGIN`〜`END nhc_fulltext_split` の範囲） |
| 全文テキストのうち、自動注釈の暫定版の 39 文書 | `source/nhc_fulltext_split/tei/` の XML を直接 | `python3 scripts/check_tei.py`（[source/nhc_fulltext_split/README_ja.md](source/nhc_fulltext_split/README_ja.md) の §10・§11） |
| ビュワー・検索ページなどの画面（`eugnostos.html`・`republic.html`・`search.html`・`lexicon.html`・`gnosticism.html`・`project.html` など） | その HTML を直接（手作業で管理しているページ） | ブラウザーで確かめる（6.） |
| 写本の写真へのリンク | `data/facsimile_links.json`（アーカイブで実際に開いて確かめた URL だけを書く） | — |
| 写本ファクシミリ（IIIF）の画像 | `iiif/<文書名>.json` の `pages[].source`（[iiif/README.md](iiif/README.md)） | — |
| 版番号・DOI | `data/release.json`・`CITATION.cff`・`.zenodo.json`（README の「版とリリースの作り方」） | `python3 scripts/check_release.py`・`python3 scripts/build_site.py` |

守ってほしいこと:

- **生成ファイルは直接直さない。** `index.html`・`tractate.html`・`reader.html`・`sitemap.xml`・`robots.txt`・`data/doc_dates.json`・`data/pos_labels.json` は
  `scripts/build_site.py` の出力です。スクリプトかデータを直してから作り直します（直接直しても、次に作り直したときに消えます）。
- **`data/` の XML は `scripts/build_tei.py` で上書きしない。** `data/` の XML には、生成したあとに手作業で直した内容が入っていて、
  `source/` の CSV からは作り直せません。`build_tei.py` は、何も付けなければ `data/` に書き込まず、違いを表示するだけです。
  `--write-data --allow-loss` は手作業の修正を消すので使わないでください（2026-07-04 に、注釈 7 件と辞書の項目 189 件が消えたことがあります）。
- **辞書は `source/lexicon.csv` を直してから `scripts/sync_lexicon.py` を実行する。** `data/lexicon.xml` を手で直すと、次の同期で
  食い違います。すでにある見出し語に 2 つ目以降の語義を足したとき（新しい同形異義語）は、`sync_lexicon.py` は報告するだけで
  書き込まないので、`<superEntry>` にまとめる作業は手で行います。
- **`data/catalog.xml` の `BEGIN nhc_fulltext_split`〜`END` の範囲は手で直さない**（`sync_nhc_catalog.py` の出力）。
- `source/` の `translations.csv`・`eugnostos_source.tsv` を直しても、サイトには反映されません（[source/README.md](source/README.md)）。

## 4. 符号化の約束

TEI の書き方の全体は README の「TEI設計の要点」と「TEI スキーマとの適合」にあります。とくに次を守ってください。

- **借用語は `xml:lang="grc"` だけで示す。** ギリシア語からの借用語は `<w xml:lang="grc">`（辞書では `lexicon.csv` の `grc` 列が `Y`）。
  語形やほかの情報から借用語かどうかを判定することはしません。
- **`pos="X"` は仮の値。** 品詞を決められない語の仮の印で、辞書（`data/lexicon.xml`）には `<gramGrp>` を出しません
  （`sync_lexicon.py` が `X` を書き出さない）。
- **辞書の重複は（レンマ, 品詞）の組で判断する。** 辞書の項目は（レンマ, 品詞）で一つに決まります。同じ組の項目がすでにあれば、
  新しく作らずに既存の項目を補います。
- **`@ana` の参照を壊さない。** 本文の `<w>` は `@ana="#lex-…"` で辞書の特定の語義を、`@ana="#gl-…"` で文脈上の語釈（`<interp>`）を
  指しています。`sync_lexicon.py` は既存の項目の `xml:id` を変えず、XML にだけある項目も消さない（報告するだけ）ことで、この参照を守っています。
- **`xml:id` を付け直さない。** 本文の `<s>` の `xml:id` は、サイトのリンク（`#seg-…`）や、利用者の投稿・ブックマーク（`seg_id`）が指しています。
  新しい要素に id を足すのはかまいませんが、既存の id は変えません。
- **編集は必要な箇所だけを置き換える。** ファイル全体を書き直したり整形し直したりしないでください（差分が読めなくなり、手作業の修正を
  消しやすくなります）。置き換える前に、対象がちょうど 1 か所に当たることを確かめます。
- 語群（bound group）は `<phr>`、対訳は `<div type="translation" xml:lang="…">` の中の `<seg corresp="#…">`、文脈上の語釈は
  `<w ana="#gl-…">` と `<interp xml:id="gl-…">` で書きます（以前の独自の書き方は使わない。`check_tei.py` が報告します）。

## 5. 訳と注の約束

- **権利。** コプト語本文と、プラトン『国家』のギリシア語本文（OCT/Burnet）はパブリックドメインです。対訳・語釈・注・辞書の語義は
  本プロジェクトのオリジナルで、CC BY 4.0 で公開しています（README の「ライセンス」）。
- **刊行された訳や注解を写さない。** 参照するのはかまいませんが、文言を写さず、要約して出典を示してください。
- **訳文の書き方。** 常体（である調）で書きます。「アイオーン」「アルコーン」と書きます。会話は「」でくくり、欠損は〔……〕で示します。

## 6. 確かめ方

Pull Request を出す前に、リポジトリのルートで次を実行してください。GitHub でも、Pull Request と `main` への push のたびに
同じものが自動で走ります（`.github/workflows/check.yml`）。

```
python3 scripts/check_tei.py                    # TEI の点検（ポインタの切れ、訳の重複、以前の書き方など）。終了コード 0 なら問題なし
node --test tests/corpus-query.test.cjs         # コーパス検索のテスト（tests/ ではなくファイルを指定する）
python3 scripts/check_style.py                  # 表記ゆれの点検（下の 8.）
python3 scripts/build_site.py --check           # 生成ファイルが最新か（違えば build_site.py を実行してコミットする）
python3 scripts/check_release.py                # 版の情報が data/release.json・CITATION.cff・.zenodo.json でそろっているか
```

- JSON（`data/*.json`・`iiif/*.json`）を直したら、構文が正しいことも確かめます（`python3 -m json.tool data/news.json` など）。
- TEI のスキーマでも確かめるときは、スキーマを取得して `python3 scripts/check_tei.py --schema <tei_all.rng の場所>`
  （README の「TEI スキーマとの適合」）。
- 画面を変えたときは、ローカルのサーバー（2.）で変えたページを開き、表示とブラウザーのコンソールにエラーが無いことを確かめます。
  ページの件数（文書数・セグメント数など）が、元のデータの件数と合っているかも見てください。

## 7. ブランチ・Pull Request・競合の解決

`main` には「Pull Request を通して変更する」規則があります。`main` に直接コミットせず、作業用のブランチから Pull Request を出してください。
`main` に入った変更は、そのまま公開サイトに反映されます。

```
git switch main
git pull                                    # 最新を取り込む（作業を始める前に必ず）
git switch -c fix/lexicon-sense            # 作業用のブランチを切る（名前は内容が分かる英数字で）
# …直す → 6. の確認…
git add 直したファイル
git commit -m "Lexicon: correct the sense of ϣⲁϫⲉ"
git push -u origin fix/lexicon-sense
```

- コミットのメッセージは、これまでの履歴と同じく英語で「対象: 内容」の形にします（例 `search.html: open the tutorial in a side panel`）。
- push すると GitHub に〈Compare & pull request〉が出るので、何をなぜ変えたかを書いて Pull Request を作ります。
  自動のチェックが通り、プロジェクトの代表が確かめてからマージします。1 つの Pull Request は 1 つの目的に絞ってください。

**競合（conflict）が起きたら。** `main` を取り込んで（`git pull origin main` など）競合したときは、次のように解きます。

- **生成ファイル**（`index.html`・`tractate.html`・`reader.html`・`sitemap.xml`・`robots.txt`・`data/doc_dates.json`・`data/pos_labels.json`）: 手で解かず、どちらかを採ってから
  `python3 scripts/build_site.py` で作り直します（もとのスクリプトやデータの競合を先に解く）。
- **`data/` の本文の XML**: 手で解きます。`build_tei.py` で作り直してはいけません（3.）。解いたら `python3 scripts/check_tei.py`。
- **辞書**: `source/lexicon.csv` の競合を解いてから、`main` の `data/lexicon.xml` に対して `python3 scripts/sync_lexicon.py --write` を
  実行し直します。両方のブランチで新しい見出し語を足していると、新しい `xml:id`（`lex-…` の続き番号）がぶつかることがあるので、
  本文の `@ana` がどの id を指しているかを確かめてください。
- **`data/parallels.xml`・`data/catalog.xml` の自動生成の範囲**: それぞれ `build_parallels.py --write`・`sync_nhc_catalog.py --write`
  で作り直します。

## 8. 表記ゆれの点検

使わない表記（たとえば『国家』の範囲の「588A–589B」）がページやスクリプトに残っていないかを、`python3 scripts/check_style.py` が
調べます（GitHub の自動チェックでも走ります）。規則は `scripts/style_rules.json` の `rules` にあり、規則を足すときは項目を 1 つ足します。

```json
{
  "bad": "使わない表記",
  "good": "使う表記",
  "note": "なぜそう書くか（任意）"
}
```

- `bad` は文字列としてそのまま探します（正規表現ではありません。大文字と小文字も区別します）。
- 点検するのは HTML・JS・Python・JSON のファイルです（`.md` と XML は見ません）。
- 規則を足したら `python3 scripts/check_style.py` を実行し、見つかった箇所を直してから一緒にコミットしてください
  （直さずに規則だけを入れると、自動チェックが失敗します）。

## 9. 生成 AI を使うとき

生成 AI（文章・訳・語釈・コードなどを作る AI のツール）を使ったときは、そのことを記載してください。

- **どこに書くか:** Pull Request の説明に書きます。Pull Request を通さずにコミットするときは、コミットのメッセージに書きます。
- **何を書くか:** 使ったツールと、使ったところ（たとえば、訳の下書き、語釈の候補、スクリプトの修正、データの点検）。
- コミットのメッセージの末尾に `Co-Authored-By: Claude …` のような行（Claude Code などのツールが付けるもの）があれば、
  それもこの記載にあたります。このリポジトリのコミットにも、この行の付いたものがあります。
