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
