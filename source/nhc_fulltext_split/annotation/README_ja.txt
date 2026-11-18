ナグ・ハマディ写本 TEI 形態素注釈 暫定版（2026-11-18）
====================================================

【対象】
アップロードされた NHC I–IV、VII–XIII の XML ファイル39件。
参考ファイル eugnostos_tei.xml / republic_tei.xml 自体は変換していません。

【XML の構造】
<s> は元のセグメント、<phr> は推定 bound group、<w> は形態素です。
各 <w> に付与した属性：
  @type  仮の品詞（例 ART, PREP, PPER, V, N; X は未判定）
  @lemma 推定辞書見出し語。未判定の語には付けません。
  @ana   文書末尾 standOff/interpGrp[@type='gloss'] 内の英日語義を参照。
  @cert  high: 参考の既注釈からのコピー・頻度の高い一致
         medium: 参考語形またはコア語彙表・文脈規則による仮判定
         low: 曖昧な語形・簡易規則による推定、または未判定
  @resp  #morph-auto / #morph-reference （責任表示）

【付与範囲（39文書合計）】
  <s> 9,216 / <phr> 109,523 / <w> 180,948
  @type: 全形態素に付与（このうち X=25,513 件）
  @lemma: 155,436 件
  @ana: 114,542 件
  @cert: high 6,695 / medium 119,649 / low 54,604 件

【根拠と品質上の注意】
  ・参照 eugnostos_tei.xml、republic_tei.xml から品詞・レンマの用例を採集しました。
  ・頻度の高い機能形態素および一部の内容語について、暫定的なコア語彙・英日語義を与えました。
  ・それ以外は、bound group 内の位置などを使う簡単な規則で品詞を予測しました。
  ・品詞を決められない形態素は type="X" とし、lemma・gloss を空欄にしました。
  ・語義は短い辞書的意味です。本文の文脈を読んで確定した訳語ではありません。
  ・特に単字形態素（ⲛ, ⲉ, ⲟⲩ など）、複雑な動詞、借用語、リュコポリス方言、
    既存ソースの形態素分割が不自然な箇所、写本欠損箇所は必ず人手で要確認です。
  ・例：トマス福音書冒頭 ⲛⲁⲉⲓ が元ソースで ⲛⲁ＋ⲉⲓ と切られたようなケースは、
    正書法上のグループを保っていても形態素解析が正しいとは限りません。
  ・lemma があること、@cert が medium 以上であることは、校訂学的正確さを保証しません。
  ・辞書 Crum や校訂本文との逐語照合・TEI スキーマの完全検証は未実施です。

【検証】
  ・39件すべてが XML として読み込めることを検証。
  ・各 <s> のコプト語文字列（元の <w> 文字列を空白なしで連結）と xml:id が
    アップロードされた原 XML とすべて一致することを検証。
  ・各 @ana の参照先が当該ファイルに存在することを検証。
  ・変更点はマークアップ・属性・付属メタデータに限定。

【フォルダ構成】
  xml/*.xml                注釈済みTEI XML 39件
  annotation_report.tsv    文書別集計
  review_morphology.tsv    low の要確認語形（文書ごとの頻度）
  review_boundaries.tsv    bound group 境界の要確認箇所
  core_glosses.tsv         追加した主要語彙表（英日対照）
  annotate_tei.py          形態素注釈の生成用Pythonスクリプト
  bound_group_converter.py 前段のbound group変換スクリプト

【再生成】
  もとの 39 XML、eugnostos_tei.xml、republic_tei.xml を ./source に置いた場合：
  python bound_group_converter.py --input-dir ./source --output-dir ./groups
  python annotate_tei.py ./groups ./output ./source
  ※Pythonのlxml, scikit-learnが必要です。

元ファイルは上書きしていません。全件人手校正前の研究用ドラフトです。
