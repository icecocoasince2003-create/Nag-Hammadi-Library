# iiif/ — 写本ファクシミリの設定

各ビュワー（republic.html / eugnostos.html）のファクシミリパネルは、
このフォルダの JSON を読み込んで OpenSeadragon で写本画像を表示します。

## 書き方

`iiif/<文書名>.json` の `pages[].source` に、IIIF Image API の
`info.json` の URL（または OpenSeadragon が読める画像ソース）を記入します。

```json
{ "page": "48", "source": "https://iiif.example.org/nhc-vi/p48/info.json" }
```

- `source` が空の間は `demoTileSource`（動作確認用デモ画像）が表示されます。
- `pages` の並びがパネル内のページ送り順になります。
- `attribution` に画像提供元のクレジットを書くとパネル下部に表示されます。

## 補足

- Claremont Colleges Digital Library などが公開するナグ・ハマディ写本の
  ファクシミリを利用する場合は、各機関の利用条件を確認してください。
- 新しい文書のビュワーを追加するときは、同名の JSON をここに追加し、
  ビュワー側の `FX_DOC` 定数をその名前に合わせます。
