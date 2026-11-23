# iiif/ — 写本ファクシミリ（IIIF）の設定

ビュワー（`eugnostos.html` / `republic.html`）は、ページを開いた時点でこのフォルダの JSON（`iiif/<文書名>.json`）を読みます。
`pages[].source` に画像の URL が 1 つでもあれば、本文の上に「Facsimile · IIIF」のパネルを出し、
〈開く〉で OpenSeadragon（そのときに読み込みます）による写本画像を表示します。

**`source` のあるページが 1 つも無い間は、パネルを出しません**（2026-11 時点では、どちらの文書もこの状態です）。
JSON を読めないときも出しません。デモ画像や、設定のための作業メモを読者に見せることはありません。

## 書き方

`pages[].source` に、IIIF Image API の `info.json` の URL（または OpenSeadragon が読める画像ソース）を書きます。

```json
{ "page": "48", "source": "https://iiif.example.org/nhc-vi/p48/info.json" }
```

- `source` を書けば、ビュワーのコードを変えずにパネルが出ます。
- パネルのページ送り（‹ ›）は、`source` のあるページだけを `pages` の順に送ります。`source` が空のページは飛ばします。
- `label` はパネルの見出しに、`attribution`（画像の提供元のクレジット）はパネルの下に出ます。
- `note` はこのファイルを編集する人のための説明で、画面には出ません。

## 画像の利用条件

- 写本画像を表示する前に、提供元の利用条件（IIIF での読み込み・表示が許されているか、クレジットの書き方）を確認してください。
- Claremont Colleges Digital Library の Nag Hammadi Archive にある写本の写真（1970 年代の白黒写真）は、
  著作権を図書館が持っているため、このパネルでは読み込みません。写本ごとの写真へのリンクだけを
  `data/facsimile_links.json` にまとめ、本文ビュワー（`reader.html`）・エウグノストス・『国家』の冒頭に出しています。

## 新しい文書のビュワーを追加するとき

同じ形の JSON をここに追加し、ビュワーのファクシミリのスクリプトの `FX_DOC` をその名前に合わせます。
