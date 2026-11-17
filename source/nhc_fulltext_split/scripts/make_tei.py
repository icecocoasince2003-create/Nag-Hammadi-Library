#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_tei.py <build.py の出力フォルダ> [日付 YYYY-MM-DD]

build.py の出力（nhc_all.tsv / catalog.tsv / changes.tsv / restored_letters.tsv）から、
文書ごとの TEI P5 ファイルを <出力フォルダ>/tei/<ファイル名>.xml に作る（tsv/ txt/ と同じファイル名）。

本文の構造は、サイトの既存の本文ファイル（data/eugnostos_tei.xml, data/republic_tei.xml）に合わせてある:

    <text type="witness" xml:id="wit-II-2" n="NHC II,2" xml:lang="cop">
      <body>
        <div type="tractate" n="…" subtype="codexII">
          <head xml:lang="en">…</head>
          <ab type="title | text | subscript | colophon | fragment">
            <s xml:id="II-7503917" n="15">
              <w>ⲡⲉϫⲉ</w>
              <w cert="high" resp="#zp">ⲯⲩⲭⲏ</w>        ← ⲍ・ⲯ を戻した語
              <gap reason="lacuna" unit="line" extent="unknown"/>   ← 出力の [...]
            </s>

  * <s> = nhc_all.tsv の 1 レコード。@n = seq。@xml:id = 「写本番号-行ID」。
    元の行を分けたレコード（src_tok が all でないもの）は「写本番号-行ID_開始トークン位置」。
  * <w> = 空白区切りの 1 トークン。品詞・レンマ（@type, @lemma）や xml:lang="grc" は付けない。
  * 既存の 2 文書と違うのは、<s> を <ab> で包んでいる点だけ（<div> の直下に <s> を置くと TEI P5 として
    妥当でなくなるため）。サイトのビュワーと検索は <text type="witness"> の子孫の <s>・<w> を読むので影響しない。
  * 日付を省くと実行日を使う（ヘッダーの <change when> に入る）。標準ライブラリだけで動く。
  * <publicationStmt> には公開元・ライセンス・公開日を入れる（サイトの既存の TEI と同じ並び）。
    公開日は PUBLISHED（リポジトリに置いて公開した日）で、作り直しても変わらない。
    ライセンスはリポジトリの README.md の「ライセンス」に合わせてある: コプト語本文はパブリックドメイン、
    TEI 符号化と下処理は CC BY 4.0。方針を変えるときは README.md とここの両方を直す。
"""
import sys, os, re, html, datetime, collections

PUBLISHED = '2026-11-17'      # 公開日（リポジトリに置き、コーパス検索につないだ日）
LICENCE = 'https://creativecommons.org/licenses/by/4.0/'
GAP = '[...]'
KINDS = ('title', 'text', 'subscript', 'colophon', 'fragment')
CERT = {'A': 'high', 'B': 'medium'}

# 題名（日・英・仏）。サイトの文書一覧（scripts/build_site.py の CODICES）と data/catalog.xml に合わせた。
# VI,8 はサイトの一覧では「VI,9」の行（アスクレピオス）。XI,2a–2e はサイトの一覧にないので、ここで付けた。
TITLES = {
 'I,2': ('ヤコブのアポクリュフォン(秘密の書)', 'The Apocryphon of James', 'Épître apocryphe de Jacques'),
 'I,3': ('真理の福音', 'The Gospel of Truth', 'Évangile de la Vérité'),
 'I,4': ('復活についての教え(レギノスへの手紙)', 'The Treatise on the Resurrection', 'Traité sur la résurrection'),
 'I,5': ('三部の教え', 'The Tripartite Tractate', 'Traité tripartite'),
 'II,1': ('ヨハネのアポクリュフォン', 'The Apocryphon of John', 'Livre des secrets de Jean'),
 'II,2': ('トマスによる福音書', 'The Gospel of Thomas', 'Évangile selon Thomas'),
 'II,3': ('フィリポによる福音書', 'The Gospel of Philip', 'Évangile selon Philippe'),
 'II,4': ('アルコーンの本質(支配者たちの本質)', 'The Hypostasis of the Archons', 'Hypostase des archontes'),
 'II,5': ('世界の起源について(無題文書)', 'On the Origin of the World', "Écrit sans titre (L'Origine du monde)"),
 'II,6': ('魂の解明', 'The Exegesis on the Soul', "Exégèse de l'âme"),
 'II,7': ('闘技者トマスの書', 'The Book of Thomas the Contender', 'Livre de Thomas'),
 'III,1': ('ヨハネのアポクリュフォン', 'The Apocryphon of John', 'Livre des secrets de Jean'),
 'III,2': ('エジプト人の福音書(聖なる不可視の霊の書)', 'The Gospel of the Egyptians', 'Livre sacré du Grand Esprit invisible (Évangile des Égyptiens)'),
 'III,3': ('祝福されたエウグノストス', 'Eugnostos the Blessed', 'Eugnoste le Bienheureux'),
 'III,4': ('イエス・キリストの知恵(ソフィア)', 'The Sophia of Jesus Christ', 'Sagesse de Jésus-Christ'),
 'III,5': ('救い主の対話', 'The Dialogue of the Savior', 'Dialogue du Sauveur'),
 'IV,1': ('ヨハネのアポクリュフォン', 'The Apocryphon of John', 'Livre des secrets de Jean'),
 'IV,2': ('エジプト人の福音書', 'The Gospel of the Egyptians', 'Évangile des Égyptiens'),
 'V,1': ('エウグノストス', 'Eugnostos', 'Eugnoste'),
 'V,2': ('パウロの黙示録', 'The Apocalypse of Paul', 'Apocalypse de Paul'),
 'V,3': ('ヤコブの黙示録(第一)', 'The (First) Apocalypse of James', 'Première apocalypse de Jacques'),
 'V,4': ('ヤコブの黙示録(第二)', 'The (Second) Apocalypse of James', 'Seconde apocalypse de Jacques'),
 'V,5': ('アダムの黙示録', 'The Apocalypse of Adam', "Apocalypse d'Adam"),
 'VI,1': ('ペテロと十二使徒の行伝', 'The Acts of Peter and the Twelve Apostles', 'Actes de Pierre et des douze apôtres'),
 'VI,2': ('雷・全きヌース(完全なる心)', 'The Thunder, Perfect Mind', 'Le Tonnerre, intellect parfait'),
 'VI,3': ('権威ある教え', 'Authoritative Teaching', 'Authentikos Logos'),
 'VI,4': ('われらの大いなる力の概念', 'The Concept of Our Great Power', 'Le Concept de notre grande puissance'),
 'VI,5': ('プラトン『国家』588b–589b', 'Plato, Republic 588b–589b', 'Platon, République 588b–589b'),
 'VI,6': ('第八と第九についての講話', 'The Discourse on the Eighth and Ninth', "L'Ogdoade et l'Ennéade"),
 'VI,7': ('感謝の祈り', 'The Prayer of Thanksgiving', "Prière d'action de grâces"),
 'VI,8': ('アスクレピオス 21–29', 'Asclepius 21–29', 'Asclépius 21–29'),
 'VII,1': ('セームの釈義(パラフレイズ)', 'The Paraphrase of Shem', 'Paraphrase de Sem'),
 'VII,2': ('大セツの第二の教え', 'The Second Treatise of the Great Seth', 'Deuxième traité du Grand Seth'),
 'VII,3': ('ペテロの黙示録', 'The Apocalypse of Peter', 'Apocalypse de Pierre'),
 'VII,4': ('シルワノスの教え', 'The Teachings of Silvanus', 'Les Leçons de Silvanos'),
 'VII,5': ('セツの三つの碑', 'The Three Steles of Seth', 'Les Trois Stèles de Seth'),
 'VIII,1': ('ゾストリアノス', 'Zostrianos', 'Zostrien'),
 'VIII,2': ('ペテロからフィリポへの手紙', 'The Letter of Peter to Philip', 'Lettre de Pierre à Philippe'),
 'IX,1': ('メルキゼデク', 'Melchizedek', 'Melchisédek'),
 'IX,2': ('ノレアの思想', 'The Thought of Norea', 'Noréa'),
 'IX,3': ('真理の証言', 'The Testimony of Truth', 'Le Témoignage véritable'),
 'X,1': ('マルサネス', 'Marsanes', 'Marsanès'),
 'XI,1': ('認識の解明', 'The Interpretation of Knowledge', 'Interprétation de la gnose'),
 'XI,2': ('ヴァレンティノス派の講解', 'A Valentinian Exposition', 'Exposé valentinien'),
 'XI,2a': ('塗油について', 'On the Anointing', "Sur l'onction"),
 'XI,2b': ('洗礼について A', 'On Baptism A', 'Sur le baptême A'),
 'XI,2c': ('洗礼について B', 'On Baptism B', 'Sur le baptême B'),
 'XI,2d': ('聖餐について A', 'On the Eucharist A', "Sur l'eucharistie A"),
 'XI,2e': ('聖餐について B', 'On the Eucharist B', "Sur l'eucharistie B"),
 'XI,3': ('アロゲネス', 'Allogenes', 'Allogène'),
 'XI,4': ('ヒュプシフロネ', 'Hypsiphrone', 'Hypsiphroné'),
 'XII,1': ('セクストスの金言', 'The Sentences of Sextus', 'Sentences de Sextus'),
 'XII,2': ('真理の福音(断片)', 'The Gospel of Truth (fragments)', 'Évangile de la Vérité (fragments)'),
 'XII,3': ('断片', 'Fragments', 'Fragments'),
 'XIII,1': ('三形態の原初思想(トリモルフォス・プロテンノイア)', 'Trimorphic Protennoia', 'Prôtennoia trimorphe'),
 'XIII,2': ('世界の起源について(冒頭部)', 'On the Origin of the World (excerpt)', 'Écrit sans titre (extrait)'),
}

# 方言。写本 I、X と、写本 XI の前半（XI,1–2）はリコポリス方言（準アクミーム方言）、ほかはサヒド方言。
LYCOPOLITAN = {'I,2', 'I,3', 'I,4', 'I,5', 'X,1', 'XI,1', 'XI,2', 'XI,2a', 'XI,2b', 'XI,2c', 'XI,2d', 'XI,2e'}

def dialect(unit):
    return 'Coptic (Lycopolitan / Subachmimic)' if unit in LYCOPOLITAN else 'Coptic (Sahidic)'

def et(s):
    return html.escape(s, quote=False)

def ea(s):
    return html.escape(s, quote=True)

def read_tsv(path):
    with open(path, encoding='utf-8', newline='') as f:
        lines = f.read().split('\n')
    head = lines[0].split('\t')
    return [dict(zip(head, l.split('\t'))) for l in lines[1:] if l]

def span_of(s):
    """src_tok → (開始, 終了)。all は (0, None)"""
    if s == 'all':
        return 0, None
    a, b = s.split('-')
    return int(a), int(b)

def seg_id(unit, src_id, src_tok):
    codex = unit.split(',')[0]
    a, b = span_of(src_tok)
    return f'{codex}-{src_id}' if b is None else f'{codex}-{src_id}_{a}'

def wit_id(unit):
    return 'wit-' + unit.replace(',', '-')

# ---- 欠損マーカーの単位 -------------------------------------------------------
def note_unit(orig):
    """欠損注記の残骸（changes.tsv の元の文字列）から単位を推定する: 'page' / 'line' / None（不明）"""
    flat = orig.replace(' ', '')
    if 'ⲡϭ' in flat:                                     # "Pages …" / "Page …"
        return 'page'
    if 'ϥϭ' in flat or flat in ('ϧ', 'ⲃϧ', 'ϭϧϧϭ'):       # "fragments" を含むもの、意味を特定できない残骸
        return None
    if 'ϣϣϭ' in flat or 'ϧϭ' in flat or 'ⲗⲓⲛⲉⲥ' in flat:  # "… missing" / "… lacking" / "… LINES ARE MISSING"
        return 'line'
    return None

def gap_units(changes):
    """(unit, src_id) → [(開始, 終了, 単位)] と、行ごとの削除済みトークン位置"""
    notes, dropped = collections.defaultdict(list), collections.defaultdict(set)
    for c in changes:
        if c['type'] == 'note_to_gap':
            a, b = span_of(c['src_tok'])
            notes[(c['unit'], c['src_id'])].append((a, b, note_unit(c['removed_or_original'])))
        elif c['type'] in ('removed', 'duplicate_removed'):
            a, b = span_of(c['src_tok'])
            dropped[c['src_id']].update(range(a, b))
    for k in notes:
        notes[k].sort()
    return notes, dropped

def gaps_of_record(rec, notes, dropped):
    """レコード内の [...] それぞれの単位。隣り合う注記（間が削除済みトークンだけのもの）は 1 つの [...] になっている"""
    a, b = span_of(rec['src_tok'])
    mine = [n for n in notes.get((rec['unit'], rec['src_id']), []) if n[0] >= a and (b is None or n[0] < b)]
    groups = []
    for n in mine:
        if groups and all(i in dropped[rec['src_id']] for i in range(groups[-1][-1][1], n[0])):
            groups[-1].append(n)
        else:
            groups.append([n])
    units = []
    for g in groups:
        us = {n[2] for n in g}
        units.append('page' if 'page' in us else 'line' if us == {'line'} else None)
    return units

def gap_xml(unit):
    return '<gap reason="lacuna"%s extent="unknown"/>' % (f' unit="{unit}"' if unit else '')

# ---- ヘッダー -----------------------------------------------------------------
def loci(pages):
    """catalog.tsv の頁・行（参考値）→ <locus> の列"""
    out = []
    for part in [p.strip() for p in pages.split(';') if p.strip()]:
        m = re.match(r'(\d+),\d+–(?:(\d+),)?\d+', part)
        attrs = f' from="{m.group(1)}" to="{m.group(2) or m.group(1)}"' if m else ''
        out.append(f'<locus{attrs}>pp. {et(part)}</locus>')
    return out

def header(c, st, today, fixed):
    """fixed: この出力で文字の訂正（ⲯ→ⲝ、ⲍ・ⲯ の復元）が行われたか。
    ⲝ・ⲍ・ⲯ が正しく入った元ファイルから作った出力では False で、訂正についての説明を入れない。"""
    unit, codex, tr = c['unit'], c['codex'], c['tractate']
    ja, en, fr = TITLES[unit]
    lang = dialect(unit)
    n_rest = st['high'] + st['medium']
    if not fixed:
        rest_ja = rest_en = ''
    elif n_rest:
        rest_ja = (f'元ファイルで落ちていた ⲍ と ⲯ は、語形と文脈から語が決まる箇所で戻した（この文書では {n_rest} 語）。'
                   f'戻した語の <gi>w</gi> には <att>resp</att>="#zp" と <att>cert</att> を付けた。'
                   f'<val>high</val>（{st["high"]} 語）は語形と文脈から決まるもの、'
                   f'<val>medium</val>（{st["medium"]} 語）は固有名など、校訂本や翻訳で知られている読みを当てたもの。'
                   f'どちらも校訂本とは照合していない。')
        rest_en = (f'The letters ⲍ and ⲯ, lost throughout the source file, were restored where the word could be identified '
                   f'from its form and context ({n_rest} words in this file). These words carry <att>resp</att>="#zp" and '
                   f'<att>cert</att> on <gi>w</gi>: <val>high</val> ({st["high"]}) = determined by word form and context; '
                   f'<val>medium</val> ({st["medium"]}) = proper names and similar words, restored following readings known '
                   f'from editions and translations. None has been collated with the printed editions.')
    else:
        rest_ja = '元ファイルで落ちていた ⲍ と ⲯ は、語形と文脈から語が決まる箇所で戻したが、この文書には該当する語がなかった。'
        rest_en = ('The letters ⲍ and ⲯ, lost throughout the source file, were restored where the word could be identified '
                   'from its form and context; no such word occurs in this file.')
    if fixed:
        corr_ja = f'元ファイルでは ⲝ がすべて ⲯ になっていたので、ⲝ に戻した（この文書では {st["xi"]} 字）。{rest_ja}'
        corr_en = (f'In the source file every ⲝ had been converted to ⲯ; these were changed back to ⲝ '
                   f'({st["xi"]} letters in this file). {rest_en} ')
        join_ja = 'ⲍ・ⲯ を戻した語が途中で切れていたときだけ 1 つにつないだ。'
        join_en = ', except that tokens were joined where a restored ⲍ or ⲯ fell inside a word that the segmenter had split'
    else:
        corr_ja = '元ファイルに ⲝ・ⲍ・ⲯ が入っているので、文字の訂正はしていない。'
        corr_en = 'The source file has ⲝ, ⲍ and ⲯ in place, so no letters were corrected. '
        join_ja = join_en = ''
    steps_ja = '文書の分割、変換の残骸の除去' + ('、ⲍ・ⲯ の復元' if fixed else '')
    steps_en = 'division into tractates, removal of conversion residue' + (', restoration of ⲍ and ⲯ' if fixed else '')
    notes = ''
    if c['note_ja']:
        notes = ('      <notesStmt>\n'
                 f'        <note xml:lang="ja">{et(c["note_ja"].replace("kind=", "type="))}</note>\n'
                 '      </notesStmt>\n')
    locus = ''.join(f'              {l}\n' for l in loci(c['pages_standard']))
    pages_note = ('              <note xml:lang="en">Page and line numbers are those in common use (as in The Nag Hammadi Library in English); '
                  'they were not taken from the source file.</note>\n') if locus else ''
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="cop">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title xml:lang="en">{et(en)}</title>
        <title xml:lang="ja">{et(ja)}</title>
        <title xml:lang="fr">{et(fr)}</title>
        <title type="sub" xml:lang="en">Nag Hammadi Codex {codex},{tr} — segmented Coptic text without linguistic annotation (working file)</title>
        <respStmt>
          <resp>TEI encoding; division of the corpus into tractates; removal of conversion residue</resp>
          <name>Sheneset project</name>
        </respStmt>
        <respStmt xml:id="zp">
          <resp>restoration of the letters ⲍ and ⲯ lost in the source file (see editorialDecl/correction)</resp>
          <name>Sheneset project</name>
        </respStmt>
        <respStmt>
          <resp>source text (tokenised Coptic)</resp>
          <name>supplied corpus (Marcion segment ids)</name>
        </respStmt>
      </titleStmt>
      <extent>
        <measure unit="segment" quantity="{st['segments']}">{st['segments']} segments</measure>
        <measure unit="token" quantity="{st['tokens']}">{st['tokens']} tokens</measure>
        <measure unit="gap" quantity="{st['gaps']}">{st['gaps']} gap markers</measure>
      </extent>
      <publicationStmt>
        <authority>Sheneset — TEI corpus of the Nag Hammadi Codices</authority>
        <availability status="free">
          <licence target="{LICENCE}">
            <p xml:lang="en">The Coptic text is in the public domain. The TEI encoding and the preparation of the text ({steps_en}) are the work of the Sheneset project and are released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).</p>
            <p xml:lang="ja">コプト語本文はパブリックドメイン。TEI 符号化と本文の下処理（{steps_ja}）は Sheneset プロジェクトによるもので、クリエイティブ・コモンズ 表示 4.0 国際（CC BY 4.0）で提供する。</p>
          </licence>
          <p xml:lang="en">Published as a working text. It has not been collated with the critical editions and carries no linguistic annotation yet; see projectDesc and editorialDecl for what was changed and what is missing.</p>
          <p xml:lang="ja">作業用の本文として公開している。校訂本との照合は済んでおらず、言語注釈もまだ付けていない。加えた変更と欠けている情報は projectDesc と editorialDecl を参照。</p>
        </availability>
        <date when="{PUBLISHED}">{PUBLISHED}</date>
      </publicationStmt>
{notes}      <sourceDesc>
        <bibl xml:id="src">
          <title>Nag_Hammadi.txt</title>
          <note xml:lang="en">Supplied plain-text file of the Nag Hammadi Codices: one segment per row (row ids 7500001–7513228), the Coptic text divided into tokens by spaces. This file contains rows {c['src_id_first']}–{c['src_id_last']}.</note>
          <note xml:lang="ja">提供されたナグ・ハマディ写本全文のテキストファイル。1 行が 1 セグメント（行 ID 7500001–7513228）で、コプト語本文は空白でトークンに区切られている。この文書は行 {c['src_id_first']}–{c['src_id_last']} にあたる。</note>
        </bibl>
        <msDesc>
          <msIdentifier>
            <settlement>Cairo</settlement>
            <repository>Coptic Museum</repository>
            <idno>NHC {codex}</idno>
            <msName>Nag Hammadi Codex {codex}</msName>
          </msIdentifier>
          <msContents>
            <msItem n="{ea(tr)}">
{locus}              <title xml:lang="en">{et(en)}</title>
              <textLang mainLang="cop">{lang}</textLang>
{pages_note}            </msItem>
          </msContents>
          <history>
            <origin>
              <origDate notBefore="0300" notAfter="0400">4th c. CE</origDate>
              <origPlace>Egypt</origPlace>
            </origin>
          </history>
        </msDesc>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <projectDesc>
        <p xml:lang="ja">提供されたナグ・ハマディ写本全文のテキストファイルを文書ごとに分け、サイト掲載に向けて下処理したものの TEI 版。訳、語釈、品詞、レンマはまだ付けていない。下処理（{steps_ja}）と TEI 化には生成 AI（Claude）を使い、結果が元ファイルと対応することを検証スクリプト（scripts/verify.py、scripts/verify_tei.py）で確かめた。</p>
        <p xml:lang="en">TEI version of the supplied full text of the Nag Hammadi Codices, divided into tractates and preprocessed for publication on the site. No translation, gloss, part of speech or lemma has been added yet. The preprocessing ({steps_en}) and the TEI conversion were carried out with a generative AI model (Claude); the result was checked against the source file with the verification scripts (scripts/verify.py, scripts/verify_tei.py).</p>
      </projectDesc>
      <editorialDecl>
        <segmentation>
          <p xml:lang="ja"><gi>s</gi> は元ファイルの 1 行（1 セグメント）。行が文書の境目や表題の境目をまたぐときだけ分けた。<att>xml:id</att> は「写本番号-行 ID」で、分けた行には「_開始トークン位置」（元ファイルの行の中での位置、0 始まり）を付けた。<att>n</att> は文書内の通し番号。<gi>w</gi> は元ファイルの空白区切り（形態素解析器の出力とみられる）のままで、切り直していない。{join_ja}<gi>ab</gi> の <att>type</att> は <val>title</val>（冒頭表題）、<val>text</val>（本文）、<val>subscript</val>（奥書表題）、<val>colophon</val>（写字生の奥書・覚え書き）、<val>fragment</val>（未配置断片）。</p>
          <p xml:lang="en">Each <gi>s</gi> is one row (segment) of the source file; a row is split only where it straddles the boundary of a tractate or of a title. <att>xml:id</att> is the codex number followed by the row id; for split rows the position of the first token within the source row (counted from 0) is added after an underscore. <att>n</att> numbers the segments within the tractate. Each <gi>w</gi> is a token of the source file (apparently the output of a morphological segmenter) and has not been re-segmented{join_en}. The <att>type</att> of <gi>ab</gi> is <val>title</val> (opening title), <val>text</val>, <val>subscript</val> (subscript title), <val>colophon</val> (scribal colophon or note) or <val>fragment</val> (unplaced fragments).</p>
        </segmentation>
        <correction method="markup">
          <p xml:lang="ja">{corr_ja}英語の編集注記が文字化けして残っていた箇所は、欠損の注記なので <gi>gap</gi> に置き換えた。変更は 1 か所ずつ、同梱の changes.tsv と restored_letters.tsv に記録してある。</p>
          <p xml:lang="en">{corr_en}Garbled residue of English editorial notes, which reported lost text, was replaced by <gi>gap</gi>. Every change is listed in the accompanying files changes.tsv and restored_letters.tsv.</p>
        </correction>
        <interpretation>
          <p xml:lang="ja">品詞（<att>type</att>）、レンマ（<att>lemma</att>）、語釈、訳、ギリシア語借用語の印（<att>xml:lang</att>="grc"）はまだ付けていない。<gi>gap</gi>（<att>reason</att>="lacuna"）は、元ファイルに行・頁単位の欠損の注記があった位置を示す（この文書では {st['gaps']} 箇所）。それ以外の欠損と校訂者による復元の区別、下点、上線、句読点、頁と行の区切りは元ファイルになく、符号化していない。</p>
          <p xml:lang="en">No part of speech (<att>type</att>), lemma (<att>lemma</att>), gloss, translation or loanword marking (<att>xml:lang</att>="grc") has been added yet. <gi>gap</gi> with <att>reason</att>="lacuna" marks the places where the source file had an editorial note reporting lost lines or pages ({st['gaps']} in this file). The source file does not distinguish other lacunae from editorial restorations and has no sublinear dots, supralinear strokes, punctuation, or page and line breaks; none of these is encoded.</p>
        </interpretation>
      </editorialDecl>
    </encodingDesc>
    <profileDesc>
      <langUsage>
        <language ident="cop">{lang}</language>
        <language ident="en">English (header)</language>
        <language ident="ja">Japanese (header)</language>
        <language ident="fr">French (title)</language>
      </langUsage>
    </profileDesc>
    <revisionDesc>
      <change when="{today}">TEI file generated from the preprocessed text (scripts/make_tei.py).</change>
      <change when="{PUBLISHED}">Published in the Sheneset repository and made searchable in the corpus search; publisher, licence and date stated in publicationStmt.</change>
    </revisionDesc>
  </teiHeader>
'''

# ---- 本文 ---------------------------------------------------------------------
def body(c, recs, rest, notes, dropped, st):
    unit, codex, tr = c['unit'], c['codex'], c['tractate']
    ja, en, fr = TITLES[unit]
    pp = re.sub(r' \(\+ ([^)]*)\)', r'; \1', c['pages_standard'])      # "138,1–145,19 (+ colophon 145,20–23)" → "…; colophon 145,20–23"
    pages = f' (pp. {pp})' if pp else ''
    out = [f'  <text type="witness" xml:id="{wit_id(unit)}" n="NHC {codex},{tr}" xml:lang="cop">',
           '    <body>',
           f'      <div type="tractate" n="{ea(en)}" subtype="codex{codex}">',
           f'        <head xml:lang="en">{et(en)} — Nag Hammadi Codex {codex},{tr}{et(pages)}</head>']
    cur = None
    for r in recs:
        if r['kind'] != cur:
            if cur is not None:
                out.append('        </ab>')
            assert r['kind'] in KINDS, r['kind']
            out.append(f'        <ab type="{r["kind"]}">')
            cur = r['kind']
        out.append(f'          <s xml:id="{seg_id(unit, r["src_id"], r["src_tok"])}" n="{r["seq"]}">')
        toks = r['text'].split(' ')
        todo = list(rest.get((unit, r['seq']), []))           # このレコードで ⲍ・ⲯ を戻した語（出現順）
        units = gaps_of_record(r, notes, dropped)
        assert len(units) == toks.count(GAP), (unit, r['seq'], units, toks.count(GAP))
        for t in toks:
            if t == GAP:
                out.append('            ' + gap_xml(units.pop(0)))
                st['gaps'] += 1
            elif todo and todo[0]['restored'] == t:          # ⲍ・ⲯ を戻した語（restored_letters.tsv の順に出てくる）
                cert = CERT[todo.pop(0)['confidence']]
                out.append(f'            <w cert="{cert}" resp="#zp">{et(t)}</w>')
                st[cert] += 1; st['tokens'] += 1
            else:
                assert t and not re.search(r'[\s<>&\[\]]', t), (unit, r['seq'], t)
                out.append(f'            <w>{et(t)}</w>')
                st['tokens'] += 1
        assert not todo, (unit, r['seq'], [x['restored'] for x in todo])     # 記録にある語はすべて印を付けたこと
        out.append('          </s>')
        st['segments'] += 1
    out += ['        </ab>', '      </div>', '    </body>', '  </text>', '</TEI>', '']
    return '\n'.join(out)

def main(out, today=None):
    today = today or datetime.date.today().isoformat()
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', today), today
    cat = read_tsv(os.path.join(out, 'catalog.tsv'))
    recs = collections.OrderedDict()
    for r in read_tsv(os.path.join(out, 'nhc_all.tsv')):
        recs.setdefault(r['unit'], []).append(r)
    rest = collections.defaultdict(list)
    for x in read_tsv(os.path.join(out, 'restored_letters.tsv')):
        rest[(x['unit'], x['seq'])].append(x)
    notes, dropped = gap_units(read_tsv(os.path.join(out, 'changes.tsv')))
    assert [c['unit'] for c in cat] == list(recs), 'catalog.tsv と nhc_all.tsv の文書の並びが違う'
    dst = os.path.join(out, 'tei')
    os.makedirs(dst, exist_ok=True)
    keep = set()
    total = collections.Counter()
    fixed = bool(rest) or any(int(c['psi_to_xi']) for c in cat)
    for c in cat:
        st = collections.Counter(xi=int(c['psi_to_xi']))
        b = body(c, recs[c['unit']], rest, notes, dropped, st)
        assert st['segments'] == int(c['rows']) and st['tokens'] == int(c['tokens']) and st['gaps'] == int(c['gap_markers']) \
            and st['high'] + st['medium'] == int(c['restored']), (c['unit'], dict(st))
        name = c['file'] + '.xml'
        with open(os.path.join(dst, name), 'w', encoding='utf-8', newline='') as f:
            f.write(header(c, st, today, fixed) + b)
        keep.add(name)
        total.update(st)
    for old in os.listdir(dst):                                  # 文書の構成を変えたあとに残った古いファイルは消す
        if old.endswith('.xml') and old not in keep:
            os.remove(os.path.join(dst, old))
    print(f'TEI files {len(keep)}; segments {total["segments"]}; tokens {total["tokens"]}; gaps {total["gaps"]}; '
          f'restored words {total["high"] + total["medium"]} (cert high {total["high"]}, medium {total["medium"]})')

if __name__ == '__main__':
    main(*sys.argv[1:3])
