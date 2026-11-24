# ナグ・ハマディ写本コプト語テキスト TEI XMLアノテーション仕様書（改訂版）

2026年11月23日 · @kokoa

## この版について

Gemini が作った「ナグ・ハマディ写本コプト語テキスト TEI XMLアノテーション標準仕様書」を、Sheneset（Nag-Hammadi-Library）の既存データと、TEI P5・EpiDoc Guidelines 9.8・Coptic SCRIPTORIUM の現行の書き方に合わせて直した版である。対象はリポジトリの本文（`data/` と `source/nhc_fulltext_split/tei/`）と、これから翻刻して加える文書である。

主な修正は次の 4 点で、全件は付録A にある。

- 品詞は `@type`、語群は `<phr>`、借用語は `xml:lang="grc"` という既存の約束を基準にし、Gemini 版の `@pos` と `<seg type="orig_group">` をやめた。
- 欠損・消去・略記・紀年の書き方を EpiDoc と TEI P5 に合わせた。
- 確かめられない識別子・URN・記述を除いた。
- 構文（UD）は TEI に入れず、CoNLL-U に分けた。

§10 に既存データとの突き合わせの結果を、付録B に自動アノテーション用スクリプトの使い方と精度を載せた。点検はコミット 7fa3057 に対して 2026年11月23日に行った。

## 1. 準拠規格と全体方針

本仕様は Sheneset（リポジトリ Nag-Hammadi-Library）の既存の TEI の約束を土台にし、写本の翻刻層を EpiDoc に、言語注釈層を Coptic SCRIPTORIUM に合わせる。三者が食い違うときは既存の約束を優先する。サイトのビュワー・検索・辞書がその約束を前提に動いているためである。

| 層 | 準拠先 | この仕様での扱い |
|---|---|---|
| 文書全体 | TEI P5（`tei_all.rng`、P5 4.3.0 で検証） | 独自の要素・属性は作らない |
| 翻刻・校訂 | EpiDoc Guidelines（ライデン記法の TEI 化） | 欠損・補訂・判読不確実などの要素と属性値（§4） |
| 語群・形態素・品詞 | Coptic SCRIPTORIUM | 語群は `<phr>`、形態素は `<w>`。品詞は `@type`、レンマは `@lemma`（§5） |
| 構文（UD） | UD_Coptic-Scriptorium | TEI には入れず、CoNLL-U として別ファイルに出す（§5） |
| プロジェクトの約束 | README「TEI設計の要点」、CONTRIBUTING §4 | 下の 6 点 |

変えない約束:

- 本文・辞書・並行箇所・カタログを別ファイルに分け、ID 参照で結ぶ。
- 品詞は `<w>` の `@type` に書く。`@pos` は使わない。
- 借用語は `xml:lang="grc"` だけで示し、語形などから判定しない。
- 品詞を決められない語は `type="X"`（仮の値。辞書には品詞を出さない）。
- 既存の `xml:id` を変えず、`@ana` の参照（`#lex-…`・`#gl-…`）を壊さない。
- 編集は必要な箇所だけを置き換え、ファイル全体を整形し直さない。

## 2. ファイル構成と文書構造

1 文書（写本の 1 篇）を 1 つの TEI ファイルに入れる。辞書（`data/lexicon.xml`）・並行箇所（`data/parallels.xml`）・カタログ（`data/catalog.xml`）は別ファイルで、本文から ID で指す。骨組みは次のとおり（… は省略）。

```xml
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="cop">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title ref="urn:cts:copticLit:…" xml:lang="en">…</title>
        <respStmt xml:id="morph-auto"><resp>…</resp><name>…</name></respStmt>
      </titleStmt>
      <publicationStmt>…</publicationStmt>
      <sourceDesc>
        <msDesc>
          <msIdentifier>
            <settlement>Cairo</settlement>
            <repository>Coptic Museum</repository>
            <idno>NHC II</idno>
            <msName>Nag Hammadi Codex II</msName>
          </msIdentifier>
          <msContents>
            <msItem n="2"><locus from="32" to="51">32,10–51,28</locus>…</msItem>
          </msContents>
        </msDesc>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>…</encodingDesc>
    <profileDesc>…</profileDesc>
    <revisionDesc>…</revisionDesc>
  </teiHeader>
  <text type="witness" xml:id="wit-II-2" n="NHC II,2" xml:lang="cop">
    <body>
      <div type="tractate" n="…">
        <head xml:lang="en">…</head>
        <ab type="text">
          <s xml:id="II-…">
            <phr>
              <w type="…" lemma="…">…</w>
            </phr>
          </s>
        </ab>
        <ab type="subscript">…</ab>
      </div>
      <div type="translation" xml:lang="ja">
        <ab><seg corresp="#II-…">…</seg></ab>
      </div>
    </body>
  </text>
  <standOff>
    <interpGrp type="gloss" xml:lang="en">
      <interp xml:id="gl-…">…</interp>
    </interpGrp>
  </standOff>
</TEI>
```

- **証本**: `<text type="witness" xml:id="wit-…" n="NHC II,2">`。同じ作品の写本を 1 ファイルで対照するときは、`<group>` の中に証本ごとの `<text>` を並べる（エウグノストスの形）。
- **区分**: `<div type="tractate">` の中を、写本上の位置で `<ab type="title">`（前題）・`text`（本文）・`subscript`（後題）・`colophon`（奥書・覚書）に分ける。セグメントは `<div>` の直下に置かない（TEI として妥当でなくなる）。
- **セグメント**: `<s>` に `xml:id` と通し番号 `@n` を付ける。`xml:id` はサイトのリンクと利用者の投稿が指すので変えない。
- **語群と形態素**: `<s>` → `<phr>`（語群）→ `<w>`（形態素）。語群のあいだの欠損 `<gap>` は `<phr>` の外に、語の途中の欠損は `<w>` の中に置く（§4）。
- **対訳**: 証本の `<body>` の末尾に言語ごとの `<div type="translation" xml:lang>`。その中の `<seg corresp="#…">` が本文のセグメントに対応する。
- **文脈上の語釈**: `<standOff>` の `<interp xml:id="gl-…">` を `<w ana="#gl-…">` で指す。辞書の語義の固定は `ana="#lex-…"`。
- **責任と確度**: `@resp` は `<respStmt xml:id>` を指すポインタ（`#morph-auto` など）。`@cert` は `high`・`medium`・`low`・`unknown`。人が確かめた語からは、自動注釈の `@cert` を削除する（§5）。

## 3. 写本の物理的レイアウト

頁・列・行の区切りは空要素（マイルストーン）で示し、本文の論理構造（セグメント・語群・形態素）は崩さない。`<sourceDoc>` による埋め込み転写と `<facsimile>` の座標は使わない。ビュワーと検索が `<s>`・`<w>` の並びを前提にしていて、写本の画像は TEI の外（IIIF の設定）で扱っているためである。

| 区切り | 要素 | 規則 |
|---|---|---|
| 頁 | `<pb n="32"/>` | `n` は写本の頁番号。`iiif/<文書>.json` の `pages[].page` と同じ値にする |
| 列 | `<cb n="1"/>` | 列が 2 つ以上ある頁だけ |
| 行 | `<lb n="10"/>` | 頁ごとに 1 から数える。語群の境目で改行するときは属性を付けない |
| 語の途中の改行 | `<lb n="22" break="no"/>` | `<phr>` の中（`<w>` の中、または同じ語群の `<w>` のあいだ）の改行には必ず付ける |

例（『国家』の既存の符号化）: `<w type="ADV" lemma="ⲧⲉⲗⲉⲱⲥ" xml:lang="grc">ⲧⲉⲗⲉ<lb n="22" break="no"/>ⲱⲥ</w>`

- 引用の単位は「頁,行」（例 51,27）。`<pb>` と `<lb>` の `n` からこの番号を組み立てられるようにする。
- 写本の写真へのリンクは、いまどおり `iiif/<文書>.json` と `data/facsimile_links.json` に置く。`<pb>` の `n` がその鍵になる。
- 既存の TEI に頁・行の区切りを入れるときは `scripts/insert_breaks.py` を使う（既定は表示だけ、`--write` で書き込む）。

## 4. 翻刻・校訂（ライデン記法との対応）

ライデン記法の記号は文字として本文に書かず、EpiDoc Guidelines 9.8 の要素に置き換える。欠損は `reason="lost"`、字数は `quantity`（わからなければ `extent="unknown"`）で書く。

| ライデン記法 | 意味 | TEI（EpiDoc 9.8） |
|---|---|---|
| `[ⲁⲃⲅ]` | 欠損部を校訂者が補った | `<supplied reason="lost">ⲁⲃⲅ</supplied>` |
| `[ⲁⲃⲅ?]` | 補ったが確かでない | `<supplied reason="lost" cert="low">ⲁⲃⲅ</supplied>` |
| `[...]`（3 字） | 字数のわかる欠損 | `<gap reason="lost" quantity="3" unit="character"/>` |
| `[±3]`・`[c.3]` | 字数がおよそ | `<gap reason="lost" quantity="3" unit="character" precision="low"/>` |
| `[---]` | 字数のわからない欠損 | `<gap reason="lost" extent="unknown" unit="character"/>` |
| 行の欠損 | 行単位の欠損 | `<gap reason="lost" quantity="2" unit="line"/>`（行数不明は `extent="unknown"`） |
| ⲁ̣ | 判読が確かでない字 | `<unclear>ⲁ</unclear>` |
| ̣ ̣ ̣（下点だけ） | 痕跡はあるが読めない字 | `<gap reason="illegible" quantity="3" unit="character"/>` |
| `⟦ⲁⲃⲅ⟧` | 写字生が消した字 | `<del rend="erasure">ⲁⲃⲅ</del>` |
| `` `ⲁⲃⲅ´ `` | 行の上などに書き足された字 | `<add place="above">ⲁⲃⲅ</add>`（下は `below`） |
| `{ⲁⲃⲅ}` | 余分な字（校訂者が除く） | `<surplus>ⲁⲃⲅ</surplus>` |
| `<ⲁⲃⲅ>` | 写字生が落とした字を補う | `<supplied reason="omitted">ⲁⲃⲅ</supplied>` |
| `ⲁ(ⲃⲅ)` | 略記の展開 | `<expan><abbr>ⲁ</abbr><ex>ⲃⲅ</ex></expan>` |
| 誤記と訂正 | 写本の誤りを直す | `<choice><sic>…</sic><corr>…</corr></choice>` |

**`<w>` との関係。** 校訂の要素は `<w>` の中に置き、形態素の境目で分ける。補訂が 2 つの `<w>` にまたがるときは、`<w>` ごとに `<supplied>` を分ける（XML では要素を交差させられない）。

```xml
<phr>
  <w type="ART" lemma="ⲡ"><supplied reason="lost">ⲡ</supplied></w>
  <w type="N" lemma="ⲛⲟⲩⲧⲉ"><supplied reason="lost">ⲛⲟⲩ</supplied>ⲧⲉ</w>
</phr>
```

- 語群のあいだの欠損（字数不明など）は `<phr>` のあいだに `<gap>` を置く。
- 語の途中の欠損は、その `<w>` の中に `<gap>` を置く（例 `<w>ⲥⲱ<gap reason="lost" quantity="1" unit="character"/>ⲙ</w>`）。自動のスクリプトは前後を別の `<w>` に分けて出すので、人が確かめるときに 1 語にまとめる（付録B）。
- 元の電子テキストで落ちていた ⲍ・ⲯ を戻した印（`reason="lost-in-source-file"`）は写本の欠損ではない。この表とは別のものとして、いまの書き方のまま残す。

**上線・ノミナ・サクラ・句読点。**

- 上線とトレマなどは、`<hi rend="supraline">` ではなく Unicode の結合文字で本文に書く（Coptic SCRIPTORIUM と同じ）。1 字の上線は U+0304、2 字以上にわたる上線は U+FE24（左端）・U+FE26（中）・U+FE25（右端）、トレマは U+0308、アポストロフ状の印は U+2CFF。検索と辞書はこれらを無視して照合する。
- 下点（U+0323）は TEI の本文には書かず、`<unclear>` にする。
- ノミナ・サクラは書かれた形のまま `<w>` に入れ、展開形は `@lemma` に書く。例: `<w type="N" lemma="ⲡⲛⲉⲩⲙⲁ" xml:lang="grc">ⲡⲛ︤ⲁ︥</w>`（Coptic SCRIPTORIUM のトマス福音書と同じ書き方）。
- 本文に展開を見せる版だけ、EpiDoc の形で `<w>` の中に書く: `<expan><abbr>ⲡⲛ</abbr><ex>ⲉⲩⲙ</ex><abbr>ⲁ</abbr></expan>`。`<ex>` には写本に無い字（ⲉⲩⲙ）だけを入れる。
- 句読点（中点など）は、Coptic SCRIPTORIUM では `type="PUNCT"` の `<w>` である。サイトの品詞表に PUNCT はないので、入れるときは品詞表に足す。

## 5. 語群・形態素・言語アノテーション

`<phr>` が語群（正書法上の 1 語）、`<w>` が品詞を持つ単位（形態素）である。組み立ては Coptic SCRIPTORIUM の TEI と同じで、属性の使い方だけがこのプロジェクトの約束に従う。

| 項目 | 書き方 | 規則 |
|---|---|---|
| 本文の文字 | `<w>` の中身 | 写本に書かれた字のまま（上線などの結合文字を含む）。正規化した形は書かない |
| 品詞 | `@type` | 下の表のコード。決められない語は `X` |
| レンマ | `@lemma` | 辞書 `lexicon.xml` の見出し。冠詞などを付けたままにしない（ⲧⲯⲩⲭⲏ ではなく ⲯⲩⲭⲏ） |
| 借用語 | `xml:lang="grc"` | ギリシア語だけ。ほかの言語を示すときも、言語名（Hebrew）ではなく BCP 47 の符号（`hbo` など）を使う |
| 語義 | `@ana` | 辞書の語義の固定 `#lex-…`、文脈上の語釈 `#gl-…`（自動の暫定版は `#g-en-…`・`#g-ja-…`） |
| 合成語の内部 | `<m>` | 任意。ϫⲓ＋ϯⲡⲉ のような内部の区切りを `<w>` の中の `<m>` で示す |
| 自動注釈 | `@resp`・`@cert` | `resp` はヘッダーの `<respStmt xml:id>` を指す（`#morph-auto`、`#coptic-nlp`）。人が確かめた語からは `cert` を削除する。`resp` について、人が確かめたあとの書き方は未定（提案: 確かめた人の ID にする） |

**機能語のレンマ。** いまの本文は、代名詞・冠詞などのレンマに書かれた形をそのまま使う所が多い（ϥ→ϥ、ⲧ→ⲧ）。Coptic SCRIPTORIUM は辞書の見出しにそろえる（ϥ→ⲛⲧⲟϥ、ⲧ・ⲛ→ⲡ、関係詞→ⲉⲧⲉⲣⲉ）。どちらかに統一する。Coptic SCRIPTORIUM に合わせれば NLP の出力をそのまま使え、検索でも語形の違いをまとめて引けるが、辞書の（レンマ, 品詞）の組も直す必要がある。

**品詞コードの対応。** 次のコードはサイトと Coptic SCRIPTORIUM の両方にあり、そのまま使う: ART, N, NPROP, V, VSTAT, VBD, PREP, PPOS, PDEM, PINT, CONJ, PTC, NEG, NUM, ADV, COP, EXIST, FM, FUT, APST, AAOR, ACONJ, ACAUS, AOPT, ANEGAOR, ANEGPST, CREL, CCIRC, CFOC, CPRET。Coptic SCRIPTORIUM にだけあるコード（ACOND, APREC, AJUS, AFUTCONJ, ALIM, ANY, ANEGJUS, ANEGOPT, IMOD, VIMP, PUNCT）も、NLP が出したらそのまま使い、サイトの品詞表に足す。名前の違うものとサイトにだけあるものは、次の表のとおり。UD の UPOS は、UD の Coptic の文書にある対応表による。

| サイトのコード | Coptic SCRIPTORIUM | UD UPOS | 扱い |
|---|---|---|---|
| PPER | PPERS・PPERO・PPERI | PRON | 主語・目的語・独立形に分ける（提案） |
| REL | CREL | SCONJ | CREL にそろえる |
| CIRC | CCIRC | SCONJ | CCIRC にそろえる |
| PRET | CPRET | AUX | CPRET にそろえる |
| NEGPST | ANEGPST | AUX | ANEGPST にそろえる |
| POSS | PPOS | DET | PPOS にそろえる |
| CFOS・PERP・Ⲛ | CFOC・PREP・（不明） | — | 打ち間違い。直す |
| A・AUX・HABIT | AAOR・APST などの個別のコード | AUX | 語ごとに個別のコードへ直す |
| CONV | CCIRC・CREL・CFOC・CPRET のどれか | SCONJ・PART・AUX | 語ごとにどの変換詞かを決める |
| ADJ | N | NOUN | Coptic SCRIPTORIUM に形容詞のコードはない（提案） |
| PFX | （コードなし） | — | 接頭辞は名詞の `<w>` の中の `<m>` にする（提案） |
| INTERJ | PTC | PART | 呼びかけの ⲱ などを不変化詞として扱う（提案） |
| UNKNOWN | UNKNOWN | X | サイトでは X にそろえる |

コードを直すときは、辞書の（レンマ, 品詞）の組、`data/pos_labels.json` を作る `scripts/build_site.py` の `POS_NAMES` も一緒に直す。

**構文（Universal Dependencies）。** 依存構造は TEI に入れず、文書ごとの CoNLL-U ファイルに出す。

- 文の区切りは NLP の推定（句読点）に従うので、セグメントと一致しないことがある。句読点の無い本文では、`scripts/coptic_nlp_tei.py --sentences s` で `<s>` 1 つを 1 文にする（付録B.2）。`# sent_id =` は文書名と通し番号、`# tei_s =` はその文が含むセグメントの `xml:id`、各語の MISC の `TEI=` はその語のセグメントである。
- 語は形態素（TEI の `<w>`）、語群は CoNLL-U の複数語トークン（`3-5 ⲁⲛϣⲱⲡⲉ`）で示す。UD の Coptic 木構造コーパスと同じ書き方である。
- UPOS は上の対応による。XPOS と LEMMA は、TEI の側をサイトの約束に合わせたときも Coptic SCRIPTORIUM の値のままにし、UD のコーパスとそろえる。借用語は MISC の `Lang=grc`、正規化した形が書かれた形と違うときは `Norm=`。
- HEAD・DEPREL は Coptic SCRIPTORIUM の NLP の出力を使い、人が確かめるまで暫定とする。ただし、NLP の 1 つの形態素を TEI で 2 つの `<w>` に分けたとき（`<gap>` をまたぐとき）は、2 つ目以降の片を最初の片に `goeswith` で係らせる（UD で、離れて書かれた 1 語の部分をつなぐ関係）。

出典: UD Coptic の品詞の対応表（<https://universaldependencies.org/cop/morphology.html>）、UD Coptic のトークン化

## 6. 題名・奥書などのパラテキスト

題名と奥書は、写本上の位置で `<ab>` の種類を分ける。作品の首に置かれた題は `<ab type="title">`（前題）、末尾の題は `<ab type="subscript">`（後題）、写字生の奥書・覚書は `<ab type="colophon">` とする。全文テキストの TSV の `kind` 列（`title`・`subscript`・`colophon`）と同じ区分である。

例: トマス福音書（NHC II,2）の題は、末尾の 51,27–28 にある後題である（前題ではない）。品詞とレンマは Coptic SCRIPTORIUM の版（Dilley ほか、CC BY 4.0）による。

```xml
<ab type="subscript">
  <lb n="27"/>
  <s xml:id="…">
    <phr>
      <w type="ART" lemma="ⲡ">ⲡ</w>
      <w type="N" lemma="ⲉⲩⲁⲅⲅⲉⲗⲓⲟⲛ" xml:lang="grc">ⲉⲩⲁⲅⲅⲉⲗⲓⲟⲛ</w>
    </phr>
    <lb n="28"/>
    <phr>
      <w type="ART" lemma="ⲡ">ⲡ</w>
      <w type="PREP" lemma="ⲕⲁⲧⲁ" xml:lang="grc">ⲕⲁⲧⲁ</w>
    </phr>
    <phr>
      <w type="NPROP" lemma="ⲑⲱⲙⲁⲥ">ⲑⲱⲙⲁⲥ</w>
    </phr>
  </s>
</ab>
```

**紀年のある奥書。** 日付はその紀年の暦をヘッダーに定義し、`@calendar` と `@datingMethod` でその定義を指す。`calendar="martyrs"` のように名前だけを書くことはしない（TEI P5 ではどちらもポインタ）。西暦は `notBefore`・`notAfter` で書き添える。

```xml
<profileDesc>
  <calendarDesc>
    <calendar xml:id="cal-AM">
      <p>Era of the Martyrs (Anno Martyrum); year 1 began on 29 August 284 CE</p>
    </calendar>
  </calendarDesc>
</profileDesc>
…
<date calendar="#cal-AM" datingMethod="#cal-AM" when-custom="550" notBefore="0833" notAfter="0834">ⲫ̄ⲛ̄</date>
```

- 奥書の人名・地名は `<persName>`・`<placeName>` で包み、可能なら `@ref` で典拠（PAThs など）を指す。語群と形態素の分割は本文と同じように付ける。
- 上の日付の例は書き方を示すためのもので、特定の写本の奥書ではない。

## 7. 識別子と外部参照

識別子は、典拠のデータベースで確かめた値だけを書く。Gemini 版の例の値（CLM 101・IB 1・CC 0100）は裏付けがないので使わない。

| 対象 | 置き場所 | 値と出どころ |
|---|---|---|
| 作品（CTS URN） | `<title ref="…">` | いまは `urn:cts:copticLit:nag.eugnostos`。Coptic SCRIPTORIUM は `urn:cts:copticLit:nh.thomas.NHAM02` のように `nh.` を使う |
| 写本（所蔵館の番号） | `<msIdentifier>` の `<idno>` | NHC II など（いまのまま） |
| 写本（CMCL の略号） | `<altIdentifier type="CMCL"><idno>…</idno></altIdentifier>` | Coptic SCRIPTORIUM は NHC II を NHAM.02 と書く。PAThs の CLM 番号は PAThs で確かめて足す |
| 作品（Clavis Coptica） | `<msItem>` の `<idno type="CC">` | CMCL の Clavis Coptica で確かめて足す |
| 見出し語 | `lexicon.xml` の項目 | Coptic Dictionary Online へのリンク（いまのまま） |

- CTS URN を Coptic SCRIPTORIUM に合わせて `nh.` にする案がある。URN はいま `data/eugnostos_tei.xml` のヘッダーと `scripts/build_tei.py`、テストの素材にしかないので、変えても影響は小さい。
- 「頁,行」での引用（§3）と CTS URN の範囲を対応させるときは、URN の末尾に範囲を付ける（Coptic SCRIPTORIUM の例: `…NHAM02:0-114` は語録 0–114）。

出典: Coptic SCRIPTORIUM のトマス福音書（TEI は CopticScriptorium/corpora の thomas-gospel）

## 8. 並行箇所とテクスト・リユース

並行箇所は本文に書かず、`data/parallels.xml` の `<linkGrp type="parallel">` に 2 つのセグメントの組として置く（いまの方式）。`@cert` は一致の強さ、`@resp` は作り方（`#align` = 自動照合）を示す。

- 本文に導入句があり、引用の範囲が文面から決まる引用だけを、そのセグメントの中で `<quote>` に入れる。出典は確かめた URN か節番号で示す。セグメントをまたぐ引用は `parallels.xml` の側で示す。
- TRACER などの自動検出で見つけた引喩は本文に書かず、`parallels.xml` に別の `<linkGrp>`（`subtype="allusion"`、`resp` は検出に使った道具の `<respStmt>`）として置く。人が確かめるまで `cert="low"` とする。
- Gemini 版の例の `urn:cts:copticLit:ot.pss.1:1` は確かめていない URN、`target="#p32_l10"` はどこにもない ID を指すので、そのまま使わない。

## 9. 処理パイプライン・検証・品質管理

新しい文書は次の順で符号化する。自動の段階のあとには必ず人の確認と点検を挟む。

1. **翻刻を入れる。** 頁・行つきのライデン記法のテキストを `scripts/leiden_to_tei.py` で TEI の断片（`<pb>`・`<lb>` と §4 の校訂の要素）にする。
2. **語群・形態素・品詞・レンマを付ける。** `scripts/coptic_nlp_tei.py` で Coptic SCRIPTORIUM の NLP にかけ、結果を `<phr>`・`<w>` に戻す（`resp="#coptic-nlp"`）。構文は CoNLL-U に出す（§5）。送り先は既定で Web の画面と同じ入口である（API の入口は、構文解析つきの出力を求めるとエラーを返した。2026年11月）。既存の暫定注釈（`annotation/`）はそのまま残す。
3. **人が確かめる。** 品詞・レンマ・語群の境目を直し、確かめた語からは自動注釈の `@cert` を削除する（`@resp` の書き方は未定。§5）。
4. **点検する。** `scripts/check_tei.py`（ポインタ・以前の書き方）、`scripts/check_spec.py`（この仕様への適合）、`tei_all.rng`（スキーマ）。全文テキストは `verify_tei.py` も。
5. **精度を測る。** `evaluation/` と同じ比べ方で、人手の版との一致率を出す。
6. **公開する。** `scripts/sync_nhc_catalog.py --write`、`scripts/build_site.py`。

品質の規則:

- **文字。** コプト文字は U+2C80–2CFF と U+03E2–03EF（ϣ ϥ ϩ ϫ ϭ ϯ）だけを使い、見た目の似たラテン文字・ギリシア文字を混ぜない（`check_tei.py` が調べる）。保存は UTF-8、NFC。
- **書体。** 表示には、上線の結合文字を正しく重ねられる書体を使う（Coptic SCRIPTORIUM は Antinoou を使っている）。
- **責任と確度。** 自動で付けた値には必ず `@resp` と `@cert` を付ける。人が確かめた語からは `@cert` を削除する（`@resp` の書き方は未定。§5）。人の校訂の要素（`<supplied>` など）には、主編集者以外が付けたときだけ `@resp` を、確かでないときだけ `cert="low"` を付ける（EpiDoc と同じ）。
- **変更の記録。** `<revisionDesc>` に `<change when>` を 1 行足す。生成 AI を使ったときはそのことも書く（CONTRIBUTING と同じ）。

## 10. 既存TEIとの突き合わせ結果

直す必要があるのは『国家』の品詞コード 5 件だけで、残りは書き方の移行と確認の問題である。`data/` の 6 ファイルと全文テキストの 56 ファイル（計 62）を `scripts/check_spec.py` で点検した（コミット 7fa3057）。`@resp` のポインタはすべて解決でき、切れは 0 件だった。

| 段階 | 内容 | 件数 | 場所 | 対応 |
|---|---|---|---|---|
| 要修正 | 品詞コードの打ち間違い（PERP→PREP 1、CFOS→CFOC 3）と、値の誤り Ⲛ 1 | 5 | `data/republic_tei.xml` | 直す |
| 要確認 | `<gap>` の `reason` が `lacuna`（289）・`unclear`（8） | 297 | 31 ファイル | `lost`・`illegible` に置き換える |
| 要確認 | `<gap>` に `unit` が無い（34）、字数の属性が無い（8） | 42 | 7 ファイル | `unit` と `quantity`（不明なら `extent="unknown"`）を足す |
| 要確認 | 語群の中の `<lb>`・`<pb>` に `break="no"` が無い | 29 | 『国家』 | `break="no"` を足す |
| 要確認 | `<w>` の中の角括弧（ⲑ[ⲧ]・[ϩ]ⲉ） | 12 | 『国家』 | 書かれた字だけにする（§5） |
| 要確認 | Coptic SCRIPTORIUM のコードだがサイトの品詞表に無い（ACOND・APREC・UNKNOWN） | 5 | エウグノストス・『国家』 | ACOND・APREC は `POS_NAMES` に足し、UNKNOWN は X にする |
| 要確認 | 辞書: 機能語の品詞なのに長い見出し（ϥⲃⲟⲏⲑⲉⲓ（PPER）など） | 77 | `data/lexicon.xml` | 語の切り方を確かめる |
| 要確認 | 辞書: 見出しに区切りの記号が残る（ⲉ\*ⲧⲣⲉ・ⲡ‐ⲕⲉ‐ⲕⲁϩ など。記号は \*・‐・-・縦線） | 25 | `data/lexicon.xml` | 記号を除くか、語を切り分ける |
| 参考 | サイトにだけある品詞コード（X 25,524、PPER 18,025、REL 3,919、ADJ 2,914、PFX 1,122、PRET 446、INTERJ 333、CONV 117 ほか） | — | 全体 | §5 の対応表で移すかどうかを決める |
| 参考 | 機能語のレンマ: 人称代名詞の 94%（16,933/18,025）、冠詞の 88%（14,967/16,979）が語形のまま | — | 全体 | §5 の方針を決める |

仕様にあって、まだ既存のデータに無いもの:

- 上線などの結合文字と、補訂・判読不確実の要素は、62 ファイルのどこにも無い。全文テキストの元ファイルにその情報が無いためで、§4 は新しく翻刻する文書から使う。
- 写本の略号（CMCL・PAThs）はどのファイルにも無く、CTS URN はエウグノストスだけにある。
- 元の電子テキストで落ちていた ⲍ・ⲯ を戻した `<supplied reason="lost-in-source-file">`（570）は、§4 のとおりこのまま残す。

全件の一覧は `python3 scripts/check_spec.py --tsv build/spec_report.tsv` で出せる。

## 付録A. Gemini版からの修正一覧

Gemini が作った「ナグ・ハマディ写本コプト語テキスト TEI XMLアノテーション標準仕様書」から変えた点の一覧である。変えた理由は、既存データの約束と合わない、規格の現行の版と合わない、出典を確かめられない、のいずれかである。

| 項目 | Gemini 版 | 改訂版 | 節 |
|---|---|---|---|
| 品詞と語群 | 品詞を `@pos`、語群を `<seg type="orig_group">` で示す | 品詞は `<w>` の `@type`、語群は `<phr>`（既存の約束。Coptic SCRIPTORIUM とも同じ組み立て） | §2・§5 |
| 品詞コード | APOC | APST（APOC はどちらのタグセットにも無い） | §5 |
| 構文（UD） | 依存構造を TEI の中に書き込む | TEI には入れず、CoNLL-U の別ファイルに出す | §5 |
| 責任と確度 | すべての注釈に `@resp`・`@cert` を必須とする | 自動で付けた値には必ず付け、人が確かめたら `cert` を削除する。人の校訂の要素には必要なときだけ付ける | §5・§9 |
| 写本のレイアウト | `<facsimile>` の座標と `<sourceDoc>` の転写を本文と二重に持つ | `<pb>`・`<cb>`・`<lb>` のマイルストーンだけ。画像は IIIF の設定で扱う | §3 |
| 欠損の字数 | 字数を `<gap>` の `extent` に書く | 数は `quantity` と `unit`。`extent` は `unknown` のときだけ（EpiDoc 9.8） | §4 |
| 写字生による消去 | `<del rend="strikethrough">` | `<del rend="erasure">` | §4 |
| 略記 | `<choice>` に `<abbr>` と `<expan>` を並べる | ノミナ・サクラは書かれた形のまま `<w>` に入れ、展開は `@lemma` に書く。展開を見せる版だけ EpiDoc の `<expan>`・`<abbr>`・`<ex>` を使う | §4 |
| `<ex>` | 置き場所が EpiDoc と違う | 写本に無い字だけを、その字が落ちた位置に入れる | §4 |
| トマス福音書の題 | 前題（作品の首の題）として例示 | 51,27–28 の後題（`<ab type="subscript">`） | §6 |
| 紀年 | `@calendar`・`@datingMethod` に暦の名前を書く | `<calendarDesc>` の `<calendar xml:id>` を指すポインタにする | §6 |
| 奥書の例 | シェヌーテの写本の奥書 | ナグ・ハマディ写本の仕様なので、特定の写本によらない書き方の例に替えた | §6 |
| 識別子 | CLM 101・IB 1・CC 0100 などの値 | 典拠のデータベースで確かめた値だけを書く | §7 |
| 引用の例 | `urn:cts:copticLit:ot.pss.1:1` と `target="#p32_l10"` | 確かめていない URN と、どこにもない ID なので使わない。並行箇所は `parallels.xml` に置く | §8 |
| 書体と文字の変換 | PAThs が Antinoou を推奨している、CMCL2Unicode で変換する、という記述 | 裏付けが見つからないので削った。書体は表示の問題として短く書く | §9 |

## 付録B. 自動アノテーション用スクリプトの使い方

3 本とも Python 3.9 以上の標準ライブラリだけで動く。リポジトリの根から実行する。同じ説明をリポジトリの [docs/ANNOTATION_TOOLS.md](ANNOTATION_TOOLS.md) にも置いた。

### B.1 ライデン記法から TEI へ（`scripts/leiden_to_tei.py`）

```sh
python3 scripts/leiden_to_tei.py 翻刻.txt --id-prefix II-2 --out build/II-2_text.xml
python3 scripts/leiden_to_tei.py 翻刻.txt --standalone --title "トマス福音書" --out build/II-2.xml
```

入力は写本の 1 行を 1 行に書いたテキストである（次の例は試験用に作ったもので、写本の実際の状態ではない）。

```text
@pb 51
26 ⲉⲥ[ⲛⲁ]ⲃⲱⲕ ⲉϩⲟⲩⲛ ⲡⲛ(ⲉⲩⲙ)ⲁ [±4] ⲁⲩ[...]ⲱ
@s
27 ⲡⲉⲩⲁⲅⲅⲉ=
28 ⲗⲓⲟⲛ ⲡⲕⲁⲧⲁ ⲑⲱⲙⲁⲥ
```

- 各行は「行番号 本文」。行末の `=` は語が次の行に続く印で、`<lb break="no"/>` になる。
- `@pb 51`・`@cb 2` が頁と列、`@s` か空行が次のセグメント、`#` で始まる行は注記である。
- §4 の表の記号は、対応する要素になる。空白で区切った語群ごとに `<w>` を 1 つ作り、形態素への分割と品詞は次の段階に任せる。
- 出力は `<ab type="text">` の中の `<s>`（`xml:id` は `--id-prefix` と通し番号）・`<pb>`・`<lb>`・`<w>` である。閉じていない括弧などがあると、行番号を示して止まる。
- 語の途中の欠損も `<w>` の外に出し、前後を別の `<w>` にする。§4 のとおり 1 語にまとめるかどうかは、人が確かめるときに決める。

### B.2 NLP で語群・形態素・品詞・レンマを付ける（`scripts/coptic_nlp_tei.py`）

```sh
python3 scripts/coptic_nlp_tei.py data/republic_tei.xml --conllu build/coptic_nlp/republic.conllu --save-sgml build/coptic_nlp/republic.tt
```

- `<s>` の中身を Coptic SCRIPTORIUM の NLP にかけ、`<phr>` と `<w>`（`@type`・`@lemma`・借用語の `xml:lang="grc"`）に組み直す。既定では元のファイルを変えず、`build/coptic_nlp/` に書く。確かめてから `--in-place` で書き戻す。
- 書き出す前に、`<s>` の中の文字の並び・校訂の要素・欠損と改行の位置と、`<s>` の外の行が元と同じかを確かめ、違えば書かずに止まる。`<s>` の `xml:id` は変えない。`@ana` は語の範囲とレンマが同じときだけ引き継ぐ。
- 付けた語には `resp="#coptic-nlp"` と `cert="medium"` を付ける（セグメントをまたいで分けた語、照合が崩れた所、X などは `low`）。ヘッダーに `<respStmt>` と `<change>` を足す。
- `--groups keep` は、いまの `<phr>` を変えずにその中だけを解析する。`--style cs` は品詞コードとレンマを Coptic SCRIPTORIUM のまま残す（既定の `site` はサイトのコードにそろえる。§5）。
- 構文解析の文は、NLP が句読点（品詞 `PUNCT` の語）から決める。NLP の Web の入口は文を区切る要素を受け取らないので、句読点の無い本文では `--sentences s` を付ける。各 `<s>` の最後に「·」（U+00B7。NLP は必ず `PUNCT` にする）を足して送り、NLP にそこで文を切らせ、結果からは除く。CoNLL-U の 1 文が 1 つの `<s>` になり、語群も `<s>` の境目をまたがなくなる。
- `<w>` の中に `<gap>` があるセグメントは扱えないので、飛ばしてそのまま残す。
- 公開の NLP サービスに、1 回 15,000 字まで、3 秒ずつ空けて送る（`--max-chars`・`--delay`）。`--save-sgml` で保存した出力は `--sgml` で読み直せるので、同じ結果を作り直せる。コーパス全体のような大量の処理は、`--export-request` で送る文字列を書き出して手元の coptic-nlp で処理し、その出力を `--sgml` で読ませる（この経路はまだ試していない）。

### B.3 仕様への適合の点検（`scripts/check_spec.py`）

```sh
python3 scripts/check_spec.py
python3 scripts/check_spec.py data/republic_tei.xml --tsv build/spec_report.tsv
```

見つけたものを「要修正」「要確認」「参考」に分けて示す。要修正が 1 件でもあると終了コード 1 を返すので CI に入れられるが、いまは『国家』の 5 件があるため、直してから入れる。

### B.4 テスト

```sh
python3 -m unittest tests.test_annotation_tools -v
```

NLP には接続せず、保存した出力（`tests/fixtures/annotation_tools/`）を使う。

### B.5 精度（『国家』NHC VI,5）

人手の版（`data/republic_tei.xml`）と、`source/nhc_fulltext_split/evaluation/evaluate_republic.py` と同じ比べ方で比べた。

| 指標 | いまの規則ベース | Coptic SCRIPTORIUM の NLP |
|---|---:|---:|
| 形態素の範囲 F1 | 0.746 | 0.854 |
| 形態素の境目 F1 | 0.882 | 0.936 |
| 語群の範囲 F1 | 0.610 | 0.661 |
| 語群の境目 F1 | 0.814 | 0.843 |
| 品詞（範囲が一致した形態素のうち） | 69.2%（364/526） | 86.5%（534/617） |
| レンマ（同） | 82.5% | 83.1% |
| 品詞まで一致（人手の形態素 723 のうち。品詞が X・UNKNOWN のものは除く） | 50.3%（364/723） | 73.9%（534/723） |

- NLP の値は既定の `--style site` のもの。`--style cs` では品詞 71.0%、レンマ 65.8% に下がるが、これは精度の差ではなく、品詞コードと機能語のレンマの約束の違いによる。
- 文書 1 つだけでの結果である。規則ベースの値は、同じフォルダの評価（`republic_summary.md`）で III,3 だけを参照データにしたときのもの。
