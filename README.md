# ナグ・ハマディ写本コーパス — TEIコーパス & ビュワー

ナグ・ハマディ写本(NHC I–XIII)を、**形態素ごとに意味を参照でき／写本を対照でき／神学的解釈を
併読でき／日英仏の対訳を持つ**形で Web 公開するための TEI P5 コーパスと静的サイトです。
現在は『祝福されたエウグノストス』(Eugnostos the Blessed, NHC III,3 / V,1)を公開し、
**全13写本・約53文書へ拡張できる目次トップとページ遷移**を備えています。

## フォルダ構成

```
Eugnostos/
├─ index.html          ← 入口(目次トップ)
├─ eugnostos.html      ← ビュワー
├─ tractate.html       ← 準備中ページ(共通)
├─ README.md
├─ .nojekyll           ← GitHub Pages 用
├─ image/
│   └─ icon.svg         ← サイトのアイコン画像(各ページが読み込みます)
├─ data/               ← 生成されるXML(ビュワーが読み込む)
│   ├─ eugnostos_tei.xml
│   ├─ eugnostos_lexicon.xml
│   └─ eugnostos_theology.xml
└─ source/             ← ここを編集 → `python3 build_tei.py`
    ├─ build_tei.py        CSV → data/ のXMLを生成
    ├─ build_site.py       index.html / tractate.html を生成
    ├─ eugnostos_source.tsv  本文ソース(通常編集不要)
    ├─ lexicon.csv         辞書(1行=1語義／同形異義語は同じlemmaを複数行)
    ├─ translations.csv    対訳(seg_id, ja, en, fr)
    ├─ notes.csv           注釈
    └─ themes.csv          主題ラベル
```

- **編集するのは `source/` の中の CSV**だけです。編集後 `cd source && python3 build_tei.py` を実行すると、
  `data/` のXMLが再生成されます(`build_tei.py` は同じ `source/` のCSVを読み、`../data/` に書き出します)。
- 目次トップ(`index.html`)とビュワー(`eugnostos.html`)は `data/` のXMLと `image/icon.svg` を読み込みます。
- **サイトのアイコン**は `image/icon.svg`。お好きな画像に差し替えてください(同じ名前にすれば各ページが自動で読み込みます)。

## 収録ファイル

**編集する入力(CSV／TSV)** — ここを直せば内容が変わります(Excel・Numbers・Googleスプレッドシート・テキストエディタで開けます。UTF-8/BOM付き):

| ファイル | 役割 | 列 |
|---|---|---|
| `lexicon.csv` | **コプト語辞書** | `lemma, n, pos, grc, en, ja, fr, usg_ja, usg_en`(1行=1語義。同じ `lemma` を複数行にすると同形異義語) |
| `translations.csv` | **対訳** | `seg_id, ja, en, fr` |
| `notes.csv` | **注釈** | `id, themes, targets, label_ja, body_ja, body_en, body_fr`(themes/targets は空白区切りのID列) |
| `themes.csv` | **主題分類** | `id, ja, en, fr` |
| `eugnostos_source.tsv` | 本文ソース | タブ区切りのコプト語トークン列(通常は編集不要) |

**生成物(自動出力。直接編集しない)**:

| ファイル | 役割 | 内容 |
|---|---|---|
| `index.html` | **トップページ(目次)** | NHC I–XIII の全文書カタログ。公開済みはビュワーへ、未整備は準備中ページへ遷移。 |
| `eugnostos.html` | **ビュワー** | エウグノストスの三言語リーダー(単一HTML)。`← 一覧`で目次へ。 |
| `tractate.html` | **準備中ページ(共通)** | `?id=コーデックス-番号` で文書を特定し「準備中」を表示。 |
| `eugnostos_tei.xml` | 本文(TEI) | 二証本(III,3 全文＋V,1 並行枠)。各 `<w>` に `@lemma`、対訳は `@transJa/En/Fr`。 |
| `eugnostos_lexicon.xml` | コプト語辞書 | `lexicon.csv` から生成。同形異義語は `<superEntry>`。 |
| `eugnostos_theology.xml` | 注釈 | `notes.csv`＋`themes.csv` から生成。`@target`/`@ana` でリンク。 |

**生成器(スクリプト)**:

| ファイル | 役割 |
|---|---|
| `build_tei.py` | **CSV → 3つのXML** を生成(`lexicon.csv` 等を読むだけの薄い変換器)。 |
| `build_site.py` | `index.html`(目次)と `tractate.html`(準備中)を生成。 |

## データの編集(CSVテーブル)

内容の編集は **CSV を直すだけ**です。コードを触る必要はありません。編集後に

```
python3 build_tei.py
```

を実行すると、CSV から3つのXML(本文・辞書・注釈)が再生成されます。スクリプトは自分と同じ
フォルダのCSVを読み、同じフォルダにXMLを書き出します(引数なしでOK)。ビュワーの埋め込みサンプルも
更新したい場合のみ `eugnostos.html` の再生成が必要です(下記「拡張のしかた」)。

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

### notes.csv（注釈）／themes.csv（主題）
`notes.csv` は1行=1注。`themes`・`targets` は**空白区切り**のID列(`targets` は `7505191` のような
セグメントID、`themes` は `themes.csv` の `id`)。`label_ja`＋`body_ja/en/fr` が注の本文です。
`themes.csv` は主題の対訳ラベル(`id, ja, en, fr`)。`notes.csv` の `themes` と `本文 <s>` の
`@ana` は、この `id` を参照します。

## サイト構成と画面遷移

```
index.html(目次:全53文書)
   ├─ 公開済み ──▶ eugnostos.html(ビュワー) ──▶ ← 一覧 で index.html へ
   └─ 準備中   ──▶ tractate.html?id=II-5 など(準備中の案内) ──▶ ← 一覧 で index.html へ
```

- 目次の各行は文書1点。`公開`バッジの行はビュワーへ、`準備中`バッジの行は共通プレースホルダへ遷移します。
- 文書IDは `コーデックス-番号`(例 `III-3` = エウグノストス、`II-5` = 世界の起源について)。
- 画面遷移は、対応ブラウザではクロスドキュメントの View Transitions(`@view-transition`)で滑らかにフェードします。

### 新しい文書を追加するには

1. その文書の3ファイル(`<name>_tei.xml` / `_lexicon.xml` / `_theology.xml`)を `build_tei.py` と同様に用意。
2. `eugnostos.html` を雛形に `<name>.html` ビュワーを作成(または共通ビュワー化)。
3. `build_site.py` の `CODICES` で当該行の status を `S`(準備中)→`A`(公開)に変更し、
   `href_for()` の遷移先をそのビュワーに向ける。`python3 build_site.py` で目次を再生成。

## 公開方法

`index.html` / `eugnostos.html` / `tractate.html` と3つのデータファイル
（`eugnostos_tei.xml` / `eugnostos_lexicon.xml` / `eugnostos_theology.xml`）を
**同じディレクトリにまとめて置いて**任意のWebサーバ(GitHub Pages, Netlify, さくら, S3 など)に
アップロードするだけです。入口は `index.html`。すべてサーバ不要の
静的ファイルで、ビュワーは同じ場所の3ファイルを `fetch` で読み込みます。

> ローカルで `eugnostos.html` をダブルクリックして開いた場合(`file://`)は、ブラウザの制約で
> 外部XMLを読めないため、**埋め込みのサンプル(冒頭十数節)**が表示されます。全文を見るには
> Webサーバ経由で開くか、画面の「XMLを開く」/ドラッグ＆ドロップで3ファイルを(まとめて)
> 読み込んでください。ファイルの種類(本文/辞書/注釈)は中身から自動判別します。

フォントは Google Fonts(Spectral / Inter / Noto Sans JP / Noto Serif JP / **Noto Sans Coptic**)を
読み込みます。オフライン公開する場合はこれらをローカルにセルフホストしてください
(Coptic字形が無い環境では汎用セリフにフォールバックします)。

## ビュワーの使い方

- **写本タブ**「III,3 本文 / V,1 / 対照」で証本を切替(対照は左右二段で並置)。
- **形態素をクリック**→ 語義カード(語形・レンマ・品詞・日英仏語釈・借用語表示)。
- **同形異義語**(綴りが同じで意味が異なる語)は、本文中で金色の点線＋`⁝`で示し、語義カードに①②…と**全語義を品詞・用法つきで列挙**します(既定語義にはバッジ表示)。
- **「語釈を重ねる」**でインターリニア(各語の下に語義)を表示。「語釈: 日/英/仏」で言語を巡回切替(419項目すべてに三言語の語義あり)。
- **「訳: 日/英/仏」**で対訳と神学注解の言語を巡回切替。
- **左の「流出の系譜」**(署名要素)= 語りえぬ父→自生者→不死の人間→人の子(救済者)→
  ソフィア→アイオーン(12・72・360)→教会、という本文の流出順。ノードを選ぶと
  該当主題の本文がハイライトされ、右の注がその主題に絞り込まれます。
- **右パネル**「神学的解釈」=`<standOff>` の注を表示し「本文へ」で該当節へジャンプ。
- **検索**=コプト語形・レンマ・英語/日本語語釈・対訳を横断検索。
- **「☀ アイオーン／☾ アルコーン」**で表示モード切替（アイオーン＝ライト、アルコーン＝ダーク）。

## TEI設計の要点（3ファイル分離）

データは役割ごとに3つの TEI 文書へ分離し、ID参照で連携させています。

**① 本文 `eugnostos_tei.xml`** — ルート `<TEI xml:lang="cop">` 直下の `<group>` が
二つの `<text type="witness">` を並置:
- `wit-III`(NHC III,3, 70–90)= **全文を符号化**。
- `wit-V`(NHC V,1, 1–17)= `@corresp` で対応づけた**並行証本の枠**(本文は欠損のため `<gap>`＋編集注)。

各形態素は次の形(語義は持たず、辞書を `@lemma` で参照):
```xml
<w type="N" lemma="ⲥⲟⲫⲓⲁ" xml:lang="grc">ⲥⲟⲫⲓⲁ</w>
```
`@type`=品詞、`@lemma`=レンマ、ギリシア借用語は `@xml:lang="grc"`。セグメント `<s>` は
`@source="marcion:…"`・通し番号 `@n`、対訳 `@transJa`/`@transEn`、主題 `@ana` を持ちます。

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

**③ 注釈 `eugnostos_theology.xml`** — `<standOff><listAnnotation type="theology">` に
神学的解釈の `<note>`(**17件**)を格納。各 `<note>` は主題分類(`<encodingDesc>` の `<taxonomy>` に
**15主題**)を `@ana` で、本文セグメントを `@target="eugnostos_tei.xml#III-…"` で参照します。
うち2件は Painchaud(JBL 1995)に基づく「修辞的四部構成(序論・叙述・論証・結語)」と
「『世界の起源について』(NHC II,5/XIII,2)との相補関係」の注で、いずれも要約・参照(原文転記ではない)です。

## データの性質(重要)

- **コプト語本文はパブリックドメイン**です。一方、**形態素グロス・対訳・神学注解は本プロジェクトに
  よる原文オリジナルの初版シード**で、**CC BY 4.0** で提供します。**フランス語訳・日本語訳・英訳・注釈は、
  Pasquier(BCNH)・Parrott(NHS 27, Brill 1991)・小林稔訳・Painchaud(JBL 1995)等を参照して作成した
  オリジナル**で、これらの翻訳を転記したものではありません。権威あるフランス語訳は **Pasquier の校訂**を参照してください。
- 語釈は**レンマ単位(文脈非依存)**で、全トークンの**約87%**に付与済み。残り(稀な語形)は
  語彙集を `build_tei.py` の `LEX` に追記すれば即座にカバーできます。
- 対訳は**日・英・仏の三言語**。枠組み(冒頭・結び)と教義上の要所を中心に**29節**を整備済み。未整備の節は
  インターリニア語釈で意味を追え、訳は「準備中」と表示されます。
- これらは**校訂版に照らした検証・拡充を前提とするシード**です。学術利用の際は
  Parrott 1991 等の原典・校訂と必ず照合してください。

## 拡張のしかた

1. **内容を編集**:`lexicon.csv`(辞書)・`translations.csv`(対訳)・`notes.csv`(注釈)・
   `themes.csv`(主題)を直接編集。新しい語義・対訳・注を行追加するだけです。
2. `python3 build_tei.py` を実行 → **3つのXML**(`eugnostos_tei.xml` /
   `eugnostos_lexicon.xml` / `eugnostos_theology.xml`)が再生成されます。
3. **ビュワーへ反映**:Webサーバ経由で `eugnostos.html` を開けば、生成された3XMLを自動で読み込みます
   (同じフォルダに置くだけ)。`file://` で直接開く場合のオフライン用埋め込みサンプルだけは、
   `eugnostos.html` を雛形(`viewer_template.html`)から作り直して `<script id="tei-main">` /
   `id="tei-lex">` / `id="tei-theo">` の中身を差し替えます。
4. V,1 本文を実体化するには、校訂版のトークン列で `build_tei.py` の `emit_witness_V`
   を本文化(`<gap>` を `<w>` 群に置換)。

> 辞書だけ・注釈だけを単独で差し替えることもできます(ビュワーの「XMLを開く」やドラッグ＆ドロップは
> 本文/辞書/注釈を中身から自動判別し、該当部分だけを更新します)。
>
> **他の NHC 文書へ展開**するときも同じCSVの形式が使えます。文書ごとに `<name>_*.csv` と
> `<name>_source.tsv` を用意し、`build_tei.py` のファイル名を差し替えれば、同じ仕組みで本文・辞書・
> 注釈のXMLが作れます。同形異義語も `lexicon.csv` に行を足すだけで増やせます。


## 辞書データの出典（加筆分）

`lexicon.csv` の見出し語・品詞・借用語フラグの一部は、以下の Coptic SCRIPTORIUM 注釈テキスト（CC BY 4.0）からレンマと品詞を抽出して加筆しました（語義の日英仏は本プロジェクトの自筆）。

- *Gospel of Thomas* (NHAM.02 = NHC II,2), Coptic SCRIPTORIUM / Dilley ほか.
- Shenoute, *Abraham Our Father*（MONB.XL / MONB.YA / MONB.ZH 断片）, Coptic SCRIPTORIUM / Krawiec ほか.

- コプト語魔術文書4点（呪詛・護符）, *Kyprianos* / Coptic Magical（BKU 1 5、O.Crum ST 18、P.CtYBR inv. 1800、P.Mich. inv. 1523）.

- *Pistis Sophia*（全4書＋追記(Postscript), アスキュー写本）, CMCL / Petermann（CC BY 4.0）.

- サヒド語旧約聖書 *ヨナ書*・*ルツ記*, Coptic SCRIPTORIUM / Sahidica（coptot, CC BY 4.0）.

- サヒド語新約聖書 *マルコ福音書*（全16章）, Coptic SCRIPTORIUM / Sahidica（sahidica, CC BY 4.0）.

いずれも CC BY 4.0。本コーパスを公開する際は上記への帰属を併記してください。

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
- **著作権**: コプト語本文(NHC VI,5)はパブリックドメイン。**日本語訳は本プロジェクトによる**。**英語訳は J. Brashler, _The Nag Hammadi Library in English_(rev. ed., HarperCollins 1990)に基づく作業用参照で、著作権があります**。公開サイトで英語訳をそのまま配信するのは権利上の懸念があるため、独自訳への置換を推奨します(日本語と同じく CC BY のオリジナル訳に)。


## プラトン『国家』 NHC VI,5 (republic.html) — 改訂

- `data/republic_tei.xml` を **eugnostos と同形式**に再構成: `<text type="witness" xml:id="wit-rep">` → `<s xml:id="rep-N" n="N" transJa="…" transEn="…" transGrc="…">` → `<phy>`（旧 `<phr>`）→ `<w type/lemma/gloss/xml:lang/ref>`。対訳は `<s>` の属性（transJa/transEn/transGrc）。
- **ギリシア語層を追加**: `transGrc` に Plato, *Republic* 588b–589b（OCT/Burnet, パブリックドメイン）を一次整列で付与（象徴的な21/55セグメント）。**校訂版での検証・残りの整列はこれから**。
- `republic.html` は **2カラム対訳**: 左にコプト語本文（形態素クリックで品詞・語義・辞書リンク）＋日英訳、**右にギリシア語**。ヘッダの「ギリシア語」ボタンで右ウィンドウの表示/非表示、「訳: 日/英」「語釈を重ねる」「アイオーン/アルコーン」対応。
- **著作権**: コプト語＝PD、日本語＝本プロジェクト、英語＝Brashler 1990（著作権あり・作業用参照、公開時は独自訳推奨）、ギリシア語＝PD。


## Republic: 辞書リンクを lexicon に分離（改訂）

- `<w>` の辞書リンク `ref="https://coptic-dictionary.org/…"` を本文 TEI から除去し、補助ファイル **`data/republic_lexicon.xml`**（74エントリ）に集約しました。
- lexicon は **(lemma + 品詞)** をキーに `<entry><form><orth>…</orth></form><gramGrp><pos>…</pos></gramGrp><xr type="dict"><ref target="…"/></xr></entry>` 形式（eugnostos_lexicon と同系統）。同形異義語（例 `ⲛ`=前置詞/冠詞/否定/代名詞）は品詞で別エントリに分かれます。
- `republic.html` は lexicon を読み込み、形態素ポップオーバーの「Coptic Dictionary →」リンクを **lemma+品詞 → lexicon** で解決します（本文には辞書リンクを持ちません）。語義(gloss)は文脈依存のため従来どおり `<w gloss>` に残しています。


## Republic: eugnostos と同一エンジンに統一（最新）

- `republic.html` は **`viewer_template.html`（eugnostos.html と同じビュワー・エンジン）から生成**。語彙ポップオーバー（lemma+品詞→品詞・日英語義・辞書リンク、同形異義の自動選択）、行間グロス、訳の言語切替、検索、アイオーン/コーデクス表示——すべて eugnostos と同一の挙動です。
- **唯一の違いがギリシア語**：eugnostos が右パネルに出していた「神学的解釈」の位置に、republic は **ギリシア語原文（`<s>` の @transGrc を連続表示）** を出します。
- 単一証本のため、写本タブ（III/V/対照）と流出テーマ柱は不使用（エンジンは保持・非表示）。
- データは eugnostos と同形式の2ファイル：`data/republic_tei.xml`（witness/s/phy/w + transJa/transEn/transGrc）と `data/republic_lexicon.xml`（lemma+品詞→日英 sense + dict ref、71エントリ）。
