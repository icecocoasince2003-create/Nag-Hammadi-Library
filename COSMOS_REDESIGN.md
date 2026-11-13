# COSMOS リデザイン — 変更まとめ

サイト全体を「グノーシス的宇宙（ギャラクシー）」テーマに統一し、
全文表示とコーパス検索をページ分離、IIIFファクシミリ対応を追加しました。
**既存ビュワーの機能（形態素ポップアップ・注釈・統計・三言語UI・二証本対照）はすべてそのまま動きます。**

## 追加されたファイル

| ファイル | 役割 |
|---|---|
| `assets/cosmos.css` | 宇宙テーマの共通レイヤー。全ページのCSS変数を上書き（虚空の藍黒＋プレーローマの金＋バルベーローの紫、見出しは Cinzel） |
| `assets/cosmos.js` | 星野（明滅する星のキャンバス）とアイオーンの環（回転する同心円）を全ページに注入。`prefers-reduced-motion` を尊重 |
| `search.html` | **コーパス検索の独立ページ**。`?doc=republic` / `?doc=eugnostos` で対象を切替。コプト語形・レンマ・語釈(日英仏)・対訳(日英仏)を横断検索し、結果からビュワーの該当セグメント（`#seg-ID`）へ移動 |
| `iiif/republic.json` / `iiif/eugnostos.json` | **写本ファクシミリのIIIF設定**。`pages[].source` に IIIF Image API の `info.json` URL を記入すると表示されます（詳細は `iiif/README.md`） |
| `image/web/*.jpg` | キャラクター画像のWeb用縮小版（元PNGはそのまま保持）。トップ（アイオーン）、公開文書カード（エウグノストス／書記）、検索ページ（ソフィア）、準備中ページ（ウロボロス）で使用 |

## 変更されたファイル

- `republic.html` / `eugnostos.html`
  - cosmos テーマの読み込みと既定モードのアイオーン固定（モード切替ボタンは非表示）
  - ヘッダーのページ内検索を撤去し、**「⌕ コーパス検索」リンク**（search.html へ）に変更。
    ページ内検索のDOMとJSは温存してあるので、戻したい場合は `assets/cosmos.css` の
    `header .search` / `#searchAside` / `#atSearch` の非表示ルールを消すだけです。
  - 本文の上に **Facsimile · IIIF パネル**を追加（OpenSeadragon。「開く」で初期化、
    `iiif/<文書>.json` を読み込み、ページ送り付き）
- `scripts/build_site.py`（→ `index.html` / `tractate.html` を再生成済み）
  - Cinzel と cosmos アセットの読み込みを追加
  - トップのヒーローにアイオーン画像、公開2文書のフィーチャーカード
    （全文表示／コーパス検索の2導線＋キャラクター画像）を追加
  - 準備中ページにウロボロス画像

## 運用メモ

- 目次を更新するときは従来どおり `python3 scripts/build_site.py` を実行してください
  （宇宙テーマはスクリプトに組み込み済みです）。
- 検索ページに新しい文書を足すときは `search.html` 冒頭の `DOCS` に1エントリ追加し、
  `iiif/` に同名のJSONを置きます。
- ファクシミリの実画像を表示するには `iiif/*.json` の `source` を記入します。
  未記入の間はデモ画像＋案内文が表示されます。
- 画像を差し替える場合は `image/` にPNGを置き、Web用は
  幅640px（chibi）／1200px（フル）程度のJPEGを `image/web/` に用意してください。

## サイトアイコンの運用（2026-07-07 更新）

ファビコンは各HTMLの `<head>` に **data URIとして直接埋め込み** です。
外部ファイル（favicon.ico 等）には依存しません。

- `image/icon.svg` を差し替えたら、リポジトリのルートで
  `python3 scripts/update_icon.py` を実行（**追加インストール不要**、
  macOS標準の qlmanage/sips で動作）。手作業管理3ページの埋め込み更新と
  `apple-touch-icon.png` の再生成、index/tractate の再ビルドまで自動で行います。
- `scripts/build_site.py` 単体でも、ビルド時に `image/icon.svg` を読んで
  index/tractate へ自動埋め込みします。
- 廃止・削除: ルートの `favicon.ico`、`image/favicon-192.png`、
  旧 `scripts/make_favicons.py`（cairo依存のため update_icon.py に置換）、
  未使用の `image/web/*.jpg`（使用中の5枚のみ残置。元PNGは `image/` にあるので
  必要になれば再生成可能）。

## サイト名を Sheneset に変更、キャラクター画像をゲンゲンに統一（2026-11-13 更新）

サイト名を「Sheneset」（ϣⲉⲛⲉⲥⲏⲧ）に変更し、サイトの画像をマスコットのゲンゲン（エジプトガン配色のガチョウ、SVG）に差し替えました。

- サイト名: ヘッダーのロゴ（`assets/site.js`）、各ページの `<title>`・`data-title-*`、トップの見出し、フッター、プライバシーポリシー・利用規約、引用表記を変更。GitHub のリポジトリ名と公開 URL は従来のまま
- 「プロジェクトについて」（`project.html`）に「サイト名とマスコット」の節を追加
- `image/web/gengen.svg`（基本ポーズ）: トップのヒーロー画像（旧アイオーン）
- `image/web/gengen_smile.svg`: 「グノーシス主義とは」冒頭の画像（旧アイオーン、日英仏3か所）
- `image/web/gengen_honk.svg`: 同ページの神話の図（旧デーミウルゴス、日英仏3か所）
- `image/web/gengen_sleep.svg`: 準備中ページの画像（旧ウロボロス）
- `image/icon.svg`: サイトアイコン（ファビコン・ヘッダーのロゴ）はマスコットにせず、以前のアイコン（`image/web/icon.svg`）をもとに描き直したもの（尾をくわえたウロボロスの環と八芒星）。`update_icon.py` で反映済み
- トップ「公開中のテキスト」のカード左の画像は削除し、カードは文字だけの1カラムに変更
- `scripts/update_icon.py` の埋め込み更新対象に `stats.html` を追加（手作業管理4ページ）
- 旧キャラクター画像（`image/web/` の jpg・png）はどこからも参照されていませんが、ファイルは残しています

## コーパス検索とコーパス統計を統合、検索ページをメインテーマ配色に（2026-11-13 更新）

- `search.html` を「コーパス検索・統計」ページに変更。見出し下のタブで〈検索〉と〈統計〉を切り替えます。
  統計は `search.html?view=stats` で直接開けます（`#sec-loan` など、セクションへの直リンクも可）。
- 左の〈文書〉〈品詞〉の絞り込みは検索と統計に共通。統計は複数の証本をまとめて集計でき、〈文書別〉の表で証本ごとの値を比べられます
  （本文未入力の証本は集計に含めません）。数値の定義は旧 `stats.html` と同じで、証本を1つだけ選んだときの値は旧ページと一致します。
  概観に「語彙項目（レンマ＋品詞）」を追加（〈検索〉の一覧の件数と同じ数え方）。
- 統計に出てくるレンマ（借用語・頻出レンマ・辞書に語義のないレンマ）をクリックすると、〈検索〉でそのレンマ（完全一致）を開きます。
- 検索語がないときに〈検索〉の上に出していた「コーパスの概要」は〈統計〉へ移しました（検索語があるときの「「…」の統計」はそのまま）。
- 統計のセクションは従来どおり、`search.html` 内の `SECTIONS` 配列に1要素 push するだけで追加できます（見出しは ja / en / fr の三言語）。
- `stats.html` は `search.html?view=stats` への転送だけを残しました（`?doc=republic` / `?doc=eugnostos` は引き継ぎます）。
- 上部ナビ（`assets/site.js` の `NAV`）は「コーパス検索・統計」の1項目に。トップとビュワーの〈統計〉リンク、`data/catalog.xml` の
  `<ref type="stats">`、NEWS の過去記事のリンクも新しい URL に変更。
- 配色: `search.html` だけの独自ダーク配色をやめ、他のページと同じ宇宙テーマに統一（`assets/cosmos.css`・`assets/cosmos.js` を読み込み、
  ページ内の `--s-*` 変数はテーマ側の `--ink` / `--gold` / `--lapis` / `--panel` / `--line` を参照）。上部ナビの独自配色も削除し、
  他のページと同じ表示・同じ高さになりました。
- `scripts/update_icon.py` の埋め込み更新対象から `stats.html` を除外（手作業管理は republic / eugnostos / search の3ページ）。
