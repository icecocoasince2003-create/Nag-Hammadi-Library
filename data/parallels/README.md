# コーパスの外の並行テキスト（`data/parallels/`）

ナグ・ハマディ写本の文書と並行する、コーパスの外のテキスト（ギリシア語・ラテン語など）を TEI で置くフォルダです。
**2026-11-24 の時点では、まだ 1 つも置いていません。** 本文は、生田目が底本とライセンスを決めてから入れます（下の「候補」）。

## ファイルの書き方

- 1 つのテキスト（1 つの写本・断片、または 1 つの版の範囲）につき 1 ファイル。名前は英小文字・数字・ハイフン（例 `poxy-654.xml`）。
- ヘッダーに必ず書くもの（`scripts/check_tei.py` の 13. が確かめます）:
  - **言語:** `<profileDesc><langUsage><language ident="grc">Ancient Greek</language></langUsage></profileDesc>`（`grc`・`la` など）
  - **底本:** `<sourceDesc><bibl>…</bibl></sourceDesc>`（本文に使った版。編者・書名・年・頁）
  - **ライセンス:** `<publicationStmt><availability><licence target="URL">…</licence></availability></publicationStmt>`（本文に使った版の条件。パブリックドメインならそう書く）
- 本文は `<text xml:lang="…">` の中の `<ab>` に、並行箇所の単位ごとに `<s xml:id="…" n="…">` で分けます（`n` は版の章・節・行など、画面に出す番号）。
  注釈（`<w>` など）は付けません。
- 例: `tests/fixtures/parallels/sample-external.xml`（試験用。本文は意味の無い文字です）。

## 並行箇所の書き方（`data/parallels.xml`）

- コーパスの文書と外のテキストの組ごとに、`<linkGrp type="parallel" subtype="external" xml:id="par-…" corresp="catalog.xml#doc-II-2 parallels/poxy-654.xml">` を 1 つ。
- その中に `<link target="../source/nhc_fulltext_split/tei/02-2_gospel-of-thomas.xml#II-… parallels/poxy-654.xml#…"/>`（コーパスの `<s>` と、外のテキストの `<s>`）。
  手で確かめて書くので `resp` は付けません。`scripts/build_parallels.py` はこの組を作らず、書き直すときもそのまま残します。
- 例: `tests/fixtures/parallels/parallels.xml`。

## 画面

本文ビュワー（`reader.html`）で、結ばれたセグメントの § の後ろに言語の印（`‖ grc` など）が出ます。押すと、外のテキストのその単位の本文、
言語、底本、ライセンス、ファイルへのリンクをパネルに出します（Sheneset の注釈は付きません）。エウグノストスのビュワーの〈並行箇所〉は、
これまでどおりエウグノストスと結ばれた組だけを出します。試験: `tests/reader-parallels.test.html`（GitHub の自動チェックでも走る）。

## 候補（本文はまだ入れていない）

| コーパスの文書 | 外のテキスト | 底本の候補（要確認） |
|---|---|---|
| II,2 トマスによる福音書 | ギリシア語の断片 P.Oxy. 1・654・655 | B. P. Grenfell & A. S. Hunt の初版（P.Oxy. 1 は 1897 年、654・655 は *The Oxyrhynchus Papyri* IV, 1904）。古いのでパブリックドメインと思われる。後の校訂（H. W. Attridge, in B. Layton (ed.), *Nag Hammadi Codex II,2–7*, 1989 など）は著作権がある |
| VI,8 アスクレピオス 21–29 | ラテン語『アスクレピオス』21–29 | P. Thomas (ed.), *Apulei Platonici Madaurensis opera quae supersunt* III（Teubner, 1908）。パブリックドメインと思われる。A. D. Nock & A.-J. Festugière, *Corpus Hermeticum* II（1945）は著作権がある |
| VI,7 感謝の祈り | ラテン語『アスクレピオス』41 と、ギリシア語のパピルス（Papyrus Mimaut、PGM III） | ラテン語は上と同じ。ギリシア語は K. Preisendanz, *Papyri Graecae Magicae* I（1928）など |
| XII,1 セクストゥスの金言 | ギリシア語『セクストゥスの金言』 | A. Elter, *Gnomica* I（1892）。H. Chadwick, *The Sentences of Sextus*（1959）は著作権がある |

- 版・年・ライセンスは、この表を書いた Claude の知識によるもので、まだ確かめていません（要確認）。デジタルの本文を使うときは、そのサイトの条件も確かめます。
- 結ぶ単位: トマスは語録の番号（`source/nhc_fulltext_split/proposals/thomas_sayings.tsv` の語録の始まり）、アスクレピオスは節の番号、セクストゥスは金言の番号が使えます。
- **チャコス写本（V,3・VIII,2 の別の写し）とは結びません**（指示書 C の 0-2）。
