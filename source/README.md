# source/ — 編集はこのフォルダだけ

共同編集で触るのは、原則としてこのフォルダの CSV だけです。
編集したらリポジトリのルートで次を実行すると、`data/` の XML が再生成されます。

```
python3 scripts/build_tei.py
```

CSV は Excel・Numbers・Google スプレッドシート・テキストエディタで開けます（UTF-8、BOM 付き可）。

## 各ファイルの役割

| ファイル | 役割 | 列 | 備考 |
|---|---|---|---|
| `lexicon.csv` | コプト語辞書 | `lemma, n, pos, grc, en, ja, fr, usg_ja, usg_en` | 1行 = 1語義。同じ `lemma` を複数行（`n`=1,2,3…）にすると同形異義語。`grc`=Y でギリシア借用語 |
| `translations.csv` | 対訳 | `seg_id, ja, en, fr` | `seg_id` は本文セグメントの ID（変更しない） |
| `notes.csv` | 神学的注釈 | `id, themes, targets, label_ja, body_ja, body_en, body_fr` | `themes` / `targets` は空白区切りの ID 列 |
| `themes.csv` | 主題分類 | `id, ja, en, fr` | `notes.csv` の `themes` から参照される |
| `eugnostos_source.tsv` | 本文ソース | タブ区切りトークン列 | **通常は編集不要**。変更する場合は必ず PR でレビューを受けること |

## 編集時の注意

- **ID 列（`seg_id`, `id`, `lemma`）は勝手に変えない**。ビュワーと XML のリンクが切れます。新規追加は OK。
- 列の追加・削除・並べ替えはしない（`scripts/build_tei.py` が列名で読んでいます）。
- 保存は必ず **UTF-8**（Excel なら「CSV UTF-8」形式）。
- カンマや改行を含むセルは引用符 `"..."` で囲む（表計算ソフトなら自動）。
- 編集後は必ず `python3 scripts/build_tei.py` を実行し、エラーが出ないこと・末尾の統計（segments / tokens / lemmas）が想定どおりであることを確認してから commit する。
