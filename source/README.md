# source/ — CSV・TSV

> **2026-11 時点の注意。** サイトが読む `data/` の XML には、生成したあとに手作業で直した内容が入っていて、
> このフォルダの CSV から作り直すことはできません。**このフォルダで直した内容をサイトに反映できるのは、いまは `lexicon.csv`（辞書）だけです。**
> 本文・対訳は `data/` の XML を直接直します。`translations.csv`・`eugnostos_source.tsv` を直しても、
> サイトには反映されません。神学的注釈の `notes.csv`・`themes.csv` は、注釈とともに 2026-11-18 に削除しました。くわしくはリポジトリ直下の `README.md` の「データの編集」を見てください。

`lexicon.csv` を直したら、リポジトリのルートで次を実行します。

```
python3 scripts/sync_lexicon.py            # 何が変わるかを表示するだけ
python3 scripts/sync_lexicon.py --write    # data/lexicon.xml に書き込む
```

`python3 scripts/build_tei.py` は、このフォルダの CSV・TSV から XML を試しに生成して `data/` と比べるだけで、何も付けなければ
`data/` には書き込みません（生成結果は `build/tei/` に出ます）。`--write-data --allow-loss` を付けると `data/` の手作業の修正が
失われるので、いまの状態では使わないでください。

CSV は Excel・Numbers・Google スプレッドシート・テキストエディタで開けます（UTF-8、BOM 付き可）。

## 各ファイルの役割

| ファイル | 役割 | 列 | 備考 |
|---|---|---|---|
| `lexicon.csv` | コプト語辞書 | `lemma, n, pos, grc, en, ja, fr, usg_ja, usg_en, cdo` | 1行 = 1語義。同じ `lemma` を複数行（`n`=1,2,3…）にすると同形異義語。`grc`=Y でギリシア借用語。`cdo` は Coptic Dictionary Online の項目 ID（例 `C1789`） |
| `translations.csv` | 対訳 | `seg_id, ja, en, fr` | `seg_id` は本文セグメントの ID（変更しない） |
| `eugnostos_source.tsv` | 本文ソース | タブ区切りトークン列 | **通常は編集不要**。変更する場合は必ず PR でレビューを受けること |

## 編集時の注意

- **ID 列（`seg_id`, `id`, `lemma`）は勝手に変えない**。ビュワーと XML のリンクが切れます。新規追加は OK。
- 列の追加・削除・並べ替えはしない（`scripts/sync_lexicon.py` と `scripts/build_tei.py` が列名で読んでいます）。
- 保存は必ず **UTF-8**（Excel なら「CSV UTF-8」形式）。
- カンマや改行を含むセルは引用符 `"..."` で囲む（表計算ソフトなら自動）。
- `lexicon.csv` を編集したら `python3 scripts/sync_lexicon.py` を実行し、表示される「更新」「追加」が想定どおりであることを確かめてから
  `--write` を付けて書き込み、`lexicon.csv` と `data/lexicon.xml` を一緒に commit する。
- すでにある見出し語に 2 つ目以降の語義の行を足した場合（新しい同形異義語）は、`sync_lexicon.py` は報告するだけで、`data/lexicon.xml` には入りません。

## nhc_fulltext_split/ — ナグ・ハマディ写本 全文テキスト（別系統）

`nhc_fulltext_split/` は、写本 I–XIII の本文を 56 の文書単位に分けて下処理した一式で、上の CSV とは別系統です
（`scripts/build_tei.py` は読みません）。

- 中身と使い方は [`nhc_fulltext_split/README_ja.md`](nhc_fulltext_split/README_ja.md) を参照してください。
- `tsv/`・`txt/`・`tei/`・`nhc_all.tsv`・`catalog.tsv` は生成物です。手で直さず、`nhc_fulltext_split/scripts/restore.py` の規則などを直して
  `build.py` → `make_tei.py` を実行し直します（元ファイル `Nag_Hammadi.txt` はこのリポジトリには入っていません）。
  ただし `tei/` のうち 39 文書は、生成したあとに語群（`<phr>`）と品詞・レンマ・語義を自動で付けた暫定版で、この XML を直接直します。
  `make_tei.py` はこの 39 ファイルを作り直しません（同 README の §10・§11）。
- **サイトとのつながり:** コーパス検索（`search.html`）の左欄〈全文テキスト〉から、選んだ文書の `tei/….xml` を読み込みます。
  自動注釈の暫定版の 39 文書は、本文ビュワー `reader.html?doc=…` でも読めます（HOME の文書一覧の「暫定」から）。
  その一覧（題名・略号・語数）は `data/catalog.xml` にあるので、`tei/` を作り直したら
  `python3 scripts/sync_nhc_catalog.py --write` で更新してください。TEI のファイル名・証本 ID（`wit-II-6` など）・
  題名を変えたときも同じです。
