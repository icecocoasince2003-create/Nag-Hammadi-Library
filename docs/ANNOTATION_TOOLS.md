# 自動アノテーション用スクリプト

新しく翻刻する文書に、頁・行の区切りと校訂の要素、語群・形態素・品詞・レンマを付けるためのスクリプトです。符号化の約束は「ナグ・ハマディ写本コプト語テキスト TEI XMLアノテーション仕様書（改訂版）」に従います。3 本とも Python 3.9 以上の標準ライブラリだけで動きます。リポジトリのルートで実行してください。

| スクリプト | すること |
|---|---|
| `scripts/leiden_to_tei.py` | ライデン記法の翻刻を TEI（EpiDoc の要素）にする |
| `scripts/coptic_nlp_tei.py` | Coptic SCRIPTORIUM の NLP で、`<s>` の中を `<phr>`・`<w>` に組み直す。構文は CoNLL-U に出す |
| `scripts/check_spec.py` | TEI が仕様に合っているかを点検する |

新しい文書は、翻刻 → `leiden_to_tei.py` → `coptic_nlp_tei.py` → 人の確認 → `check_tei.py`・`check_spec.py` の順で作ります。自動の段階のあとには、必ず人が確かめます。

## 1. ライデン記法から TEI へ（`leiden_to_tei.py`）

```sh
python3 scripts/leiden_to_tei.py 翻刻.txt                                   # <ab> の断片を表示する
python3 scripts/leiden_to_tei.py 翻刻.txt --id-prefix II-2 --out build/II-2_text.xml
python3 scripts/leiden_to_tei.py 翻刻.txt --standalone --title "トマス福音書" --out build/II-2.xml
```

入力は、写本の 1 行を 1 行に書いた UTF-8 のテキストです。次の例は試験用に作ったもので、写本の実際の状態ではありません（`tests/fixtures/annotation_tools/leiden_sample.txt` も同じです）。

```text
@pb 51
26 ⲉⲥ[ⲛⲁ]ⲃⲱⲕ ⲉϩⲟⲩⲛ ⲡⲛ(ⲉⲩⲙ)ⲁ [±4] ⲁⲩ[...]ⲱ
@s
27 ⲡⲉⲩⲁⲅⲅⲉ=
28 ⲗⲓⲟⲛ ⲡⲕⲁⲧⲁ ⲑⲱⲙⲁⲥ
```

| 書き方 | 意味 | TEI |
|---|---|---|
| `# …` | 注記（読み飛ばす） | — |
| `@pb 51`・`@cb 2` | 頁・列の区切り | `<pb n="51"/>`・`<cb n="2"/>` |
| `@s`、空行 | ここから新しいセグメント | `<s xml:id="…">` |
| `27 本文` | 行番号と本文 | `<lb n="27"/>` と本文 |
| 行末の `=` | 語が次の行に続く | 次の `<lb>` に `break="no"` を付け、`<w>` の中に置く |
| `[ⲁⲃⲅ]`・`[ⲁⲃⲅ?]` | 欠損部の補い（確かでない） | `<supplied reason="lost">`（`cert="low"`） |
| `[...]` | 字数のわかる欠損（点の数が字数） | `<gap reason="lost" quantity="3" unit="character"/>` |
| `[±3]`・`[c.3]` | 字数がおよその欠損 | 同上に `precision="low"` |
| `[---]` | 字数のわからない欠損 | `<gap reason="lost" extent="unknown" unit="character"/>` |
| 角括弧の外の `...` | 痕跡はあるが読めない字 | `<gap reason="illegible" quantity="3" unit="character"/>` |
| 下点（U+0323） | 判読が確かでない字 | `<unclear>` |
| `⟦ⲁⲃⲅ⟧` | 写字生が消した字 | `<del rend="erasure">` |
| `` `ⲁⲃⲅ´ ``・`\ⲁⲃⲅ/`、`/ⲁⲃⲅ\` | 行の上・下に書き足された字 | `<add place="above">`・`<add place="below">` |
| `{ⲁⲃⲅ}` | 余分な字 | `<surplus>` |
| `<ⲁⲃⲅ>` | 写字生が落とした字の補い | `<supplied reason="omitted">` |
| `ⲡⲛ(ⲉⲩⲙ)ⲁ` | 略記の展開（丸括弧の中が写本に無い字） | `<expan><abbr>ⲡⲛ</abbr><ex>ⲉⲩⲙ</ex><abbr>ⲁ</abbr></expan>` |

- 空白で区切った語群ごとに `<w>` を 1 つ作ります。形態素への分割と品詞は次の段階（`coptic_nlp_tei.py`）に任せます。
- 補訂などが語群の境目をまたぐときは、`<w>` ごとに要素を分けます（XML では要素を交差させられないため）。
- 欠損 `<gap>` は語の途中にあっても `<w>` の外に出し、前後を別の `<w>` にします。仕様（§4）では語の途中の欠損は `<w>` の中に置くので、1 語にまとめるかどうかは人が確かめるときに決めてください。
- 上線（U+0304、U+FE24–FE26）やトレマなどの結合文字は、そのまま本文に残します。
- 閉じていない括弧など、記号の対応がとれないときは、行番号を示して止まります。

## 2. NLP で語群・形態素・品詞・レンマを付ける（`coptic_nlp_tei.py`）

```sh
python3 scripts/coptic_nlp_tei.py data/republic_tei.xml \
    --conllu build/coptic_nlp/republic.conllu --save-sgml build/coptic_nlp/republic.tt
```

`<s>` の中身を Coptic SCRIPTORIUM の NLP（<https://tools.copticscriptorium.org/coptic-nlp/>）にかけ、返ってきた語群・形態素・品詞・レンマ・借用語の印を、`<phr>` と `<w type lemma>`（借用語は `xml:lang="grc"`）に戻します。既定では元のファイルを変えず、`build/coptic_nlp/<ファイル名>` に書きます。確かめてから `--in-place` で書き戻してください。

変えないもの（書き出す前に確かめ、1 つでも違えば書き出さずに止まります）:

- 各 `<s>` の文字（空白を除く）、`<s>` の `xml:id` と `@n`、`<s>` の外のすべて
- `<s>` の中の `<gap>`・`<supplied>`・`<lb>`・`<pb>`・`<cb>` と、各文字を包む校訂の要素

変わるもの:

- `<s>` の中の `<phr>`・`<w>` の区切りと、`<w>` の属性（`type`・`lemma`・`xml:lang="grc"`・`resp="#coptic-nlp"`・`cert`）
- 語群の中に来た `<lb>`・`<pb>`・`<cb>` には `break="no"` を付けます
- 区切りとレンマが前と同じ `<w>` だけ、前の `@ana`（語義・語釈へのポインタ）を引き継ぎます（`--no-keep-ana` で引き継がない）
- `cert` は `medium` です。セグメントの境目をまたいで分けた語、照合が崩れた所、`X` になった語は `low` にします
- ヘッダーの `<titleStmt>` に `<respStmt xml:id="coptic-nlp">`、`<revisionDesc>` の末尾に `<change>` を足します

主な指定:

| 指定 | 意味 |
|---|---|
| `--groups auto`（既定） | いまの `<w>` を空白で区切って送り、語群は NLP が決める |
| `--groups keep` | いまの `<phr>` を語群として送り、語群の区切りは変えない（人の手で語群を付けた本文向け） |
| `--style site`（既定） | サイトの約束に合わせる（`PPERS`・`PPERO`・`PPERI` → `PPER`、`UNKNOWN` → `X`、`NOUN` → `N`、`ACOND_PPERS` のような融合タグ → `X`。人称代名詞と冠詞のレンマは語形） |
| `--style cs` | Coptic SCRIPTORIUM の品詞とレンマのまま |
| `--conllu PATH` | 構文解析もして CoNLL-U に出す |
| `--save-sgml PATH` | NLP の出力（SGML）を保存する |
| `--sgml PATH` | NLP に送らず、保存した出力から作り直す（ネットにつながない） |
| `--export-request PATH` | NLP に送る文字列だけを書き出して終わる |
| `--service form\|api` | 送り先。既定の `form` は Web の画面と同じ入口（2026年11月の時点で、`api` の入口は構文解析つきの出力を求めるとエラーを返した） |
| `--keep-resp ID` | `@resp="#ID"` の `<w>` がある `<s>` は NLP に送らず、そのまま残す（人の注釈を写した所など。複数可） |
| `--cache-dir DIR` | 1 回ごとの NLP の出力を `DIR` に保存する。止まってからもう一度動かすと、送り終えた分は送り直さずに使う |
| `--timeout`・`--retries` | 1 回の送信で待つ秒数（既定 180）と、失敗したときにやり直す回数（既定 2） |

CoNLL-U（仕様 §5）:

- 文の区切りは NLP の推定に従うので、セグメントと一致しないことがあります。`# sent_id` は文書名と通し番号、`# tei_s` はその文が含むセグメントの `xml:id`、各語の MISC の `TEI=` はその語のセグメントです。
- 語は形態素、語群は複数語トークン（`3-5 ⲁⲛϣⲱⲡⲉ`）です。`XPOS` と `LEMMA` は、`--style site` のときも Coptic SCRIPTORIUM の値のままにして、UD のコーパスとそろえます。借用語は MISC の `Lang=grc`、正規化した形が書かれた形と違うときは `Norm=` です。

注意:

- NLP は公開のサービスです。1 回に送るのは既定で 15,000 字まで、送るたびに 3 秒待ちます（`--max-chars`・`--delay`）。
- 多くの文書をまとめて処理するときは、Coptic SCRIPTORIUM の coptic-nlp（<https://github.com/CopticScriptorium/coptic-nlp>）を手元で動かし、`--export-request` で書き出した文字列を処理して、出力を `--sgml` で読ませてください。この経路はまだ試していません。
- 2026-11-24 に自動注釈の暫定版 39 文書を付け直したときは、公開のサービスに 1 文書ずつ、次の指定で送りました（構文解析つきだと、1 万字ほどの 1 回に 2 分ほどかかる。詳しくは `source/nhc_fulltext_split/README_ja.md` の §13）。

  ```sh
  python3 scripts/coptic_nlp_tei.py source/nhc_fulltext_split/tei/02-2_gospel-of-thomas.xml \
      --out build/coptic_nlp/02-2_gospel-of-thomas.xml --conllu build/coptic_nlp/02-2_gospel-of-thomas.conllu \
      --save-sgml build/coptic_nlp/02-2_gospel-of-thomas.tt --cache-dir build/coptic_nlp/cache \
      --max-chars 12000 --timeout 600 --retries 3 --delay 5
  ```
- NLP は句読点から文の区切りを推定します。全文テキストには句読点がほとんど無いので、送った 1 回分がほぼそのまま 1 文になり（39 文書で 123 文）、CoNLL-U の構文（依存関係）はとくに当てになりません。文を区切って解析させる送り方は、まだ用意していません。
- `<w>` の中に `<gap>` があるセグメントなど、組み直せない形のセグメントは飛ばして、そのまま残します（飛ばした数と理由を表示します）。

## 3. 仕様への適合の点検（`check_spec.py`）

```sh
python3 scripts/check_spec.py                                  # data/ と source/nhc_fulltext_split/tei/ の全ファイル
python3 scripts/check_spec.py data/republic_tei.xml            # 指定したファイルだけ
python3 scripts/check_spec.py --tsv build/spec_report.tsv      # 見つけたものを 1 件 1 行の TSV にも書く
```

見つけたものを 3 段階で報告します。

- 要修正: 仕様に反していて、直す必要があるもの（打ち間違いの品詞コード、指す先の無い `@resp`、数で書いた `extent` など）
- 要確認: 仕様と違うが、直すかどうかを人が決めるもの（EpiDoc と違う `reason` の値、語群の中の改行の `break` など）
- 参考: 仕様の移行の目安（サイトにだけある品詞コード、機能語のレンマの書き方など）

要修正が 1 件でもあると終了コード 1 を返します。2026年11月23日の時点では `data/republic_tei.xml` に要修正が 5 件（品詞コードの打ち間違い 4、値の誤り 1）あるので、CI に入れるのはそれを直してからにしてください。

## 4. テスト

```sh
python3 -m unittest tests.test_annotation_tools -v
```

NLP には接続せず、保存した出力（`tests/fixtures/annotation_tools/`）を使います。`coptic_nlp_rep2.tt` は、『国家』の 2 セグメントを実際に NLP にかけた出力です。

## 5. 精度（『国家』NHC VI,5）

人手の版（`data/republic_tei.xml`）と、`source/nhc_fulltext_split/evaluation/evaluate_republic.py` と同じ比べ方で比べました。規則ベースの値は同じフォルダの `republic_summary.md` のもの（参照データを III,3 だけにしたとき）です。

| 指標 | いまの規則ベース | Coptic SCRIPTORIUM の NLP（`--style site`） |
|---|---:|---:|
| 形態素の範囲 F1 | 0.746 | 0.854 |
| 形態素の境目 F1 | 0.882 | 0.936 |
| 語群の範囲 F1 | 0.610 | 0.661 |
| 語群の境目 F1 | 0.814 | 0.843 |
| 品詞（範囲が一致した形態素のうち） | 69.2%（364/526） | 86.5%（534/617） |
| レンマ（同） | 82.5% | 83.1% |
| 品詞まで一致（人手の形態素 723 のうち。品詞が X・UNKNOWN のものは除く） | 50.3%（364/723） | 73.9%（534/723） |

- `--style cs` では品詞 71.0%、レンマ 65.8% に下がります。精度の差ではなく、品詞コードと機能語のレンマの約束の違いによるものです。
- 文書 1 つ（約 730 語）だけでの結果です。ほかの文書、とくに方言の違う写本に、そのまま当てはまるとは限りません。
