#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 build_tei.py — source/ の CSV から data/ の TEI XML を生成するスクリプト
==============================================================================

【共同編集者の方へ / For collaborators】
  ふだん編集するのは source/ フォルダの CSV だけです。このスクリプト自体を
  編集する必要はありません。CSV を直したら、リポジトリのルートで:

      python3 scripts/build_tei.py

  を実行すると data/ の XML が再生成されます。生成された XML は
  「直接編集しない」でください(次のビルドで上書きされます)。

【入力 (source/ 内・手で編集してよいファイル)】
  lexicon.csv       lemma,n,pos,grc,en,ja,fr,usg_ja,usg_en
                    1行 = 1語義。同じ lemma を複数行 (n=1,2,3…) にすると
                    同形異義語。grc=Y でギリシア借用語。usg_* は用法ヒント。
  translations.csv  seg_id,ja,en,fr   … セグメント単位の対訳
  notes.csv         id,themes,targets,label_ja,body_ja,body_en,body_fr
                    themes / targets は空白区切りの ID 列
  themes.csv        id,ja,en,fr       … 主題分類ラベル
  eugnostos_source.tsv  トークン化済みコプト語本文 (通常は編集不要)

【出力 (data/ 内・自動生成。直接編集しない)】
  eugnostos_tei.xml            本文 (TEI P5)
  lexicon.xml                  コプト語辞書 (ビュワーは data/lexicon.xml を読む)
  eugnostos_theology.xml       神学的注釈
  eugnostos_main_sample.xml    オフライン用の冒頭サンプル
==============================================================================
"""
import re, html, sys, datetime, os, csv

# --- パス設定 ---------------------------------------------------------------
# BASE   = このスクリプトのあるフォルダ (scripts/)
# ROOT   = プロジェクトのルート
# SRCDIR = 編集用 CSV / TSV の置き場 (source/)
# DATA   = 生成 XML の出力先 (data/)
BASE = os.path.dirname(os.path.abspath(__file__))
# スクリプトが scripts/ (旧: source/) にある場合、ルートはその親フォルダ
ROOT = os.path.dirname(BASE) if os.path.basename(BASE).lower() in ("source", "build", "src", "scripts") else BASE
SRCDIR = os.path.join(ROOT, "source")          # 編集用 CSV / TSV
if not os.path.isdir(SRCDIR):
    SRCDIR = BASE                              # 旧レイアウトへの後方互換

def _find_source():
    """Locate the tokenised Coptic source next to this script.
    Accepts an explicit path as argv[1], else tries common names."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    import glob
    for cand in ("eugnostos_source.tsv", "Eugnostos.xml", "eugnostos_source.txt"):
        p = os.path.join(SRCDIR, cand)
        if os.path.exists(p):
            return p
    hits = sorted(glob.glob(os.path.join(SRCDIR, "*_source.tsv")))
    if hits:
        return hits[0]
    sys.exit(
        "\n[!] 本文ソースが見つかりません。\n"
        "    source/ フォルダに 'eugnostos_source.tsv' を置いてください。\n"
        "    （探した場所: %s）\n"
        "    別名のファイルを使う場合:  python3 scripts/build_tei.py <ソースのパス>\n" % SRCDIR)

SRC  = _find_source()
# 生成 XML の出力先 (プロジェクト直下の data/)
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
OUT  = os.path.join(DATA, "eugnostos_tei.xml")
SAMPLE_N = 14   # leading segments kept in the embedded viewer sample

COPTIC_RE = re.compile(r'[\u2c80-\u2cff]')
# Greek-loanword heuristic — only a fallback for tokens absent from the lexicon.
GREEK_SUFFIXES = ("\u2c9f\u2ca5", "\u2c93\u2ca5", "\u2c8f\u2ca5", "\u2c93\u2c81",
                  "\u2cb1\u2c9b", "\u2c99\u2c81", "\u2ca5\u2c93\u2ca5",
                  "\u2ca7\u2cb1\u2c9f", "\u2cb1\u2c9f")

# ---------------------------------------------------------------------------
# EDITABLE DATA — loaded from the CSV tables described above.
# ---------------------------------------------------------------------------
def _csv(name):
    """source/ フォルダの CSV を読む（BOM付きUTF-8対応）。"""
    path = os.path.join(SRCDIR, name)
    if not os.path.exists(path):
        sys.exit("\n[!] '%s' が見つかりません（探した場所: %s）。\n"
                 "    4つのCSV(lexicon/translations/notes/themes)を source/ フォルダに\n"
                 "    置いてください。\n" % (name, SRCDIR))
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def _truthy(v): return str(v or "").strip().lower() in ("y", "yes", "true", "1", "grc")
def _s(r, k):   return (r.get(k) or "").strip()

# lexicon: SENSES[lemma] = [ {n,pos,grc,en,ja,fr,uja,uen}, ... ]  (ordered by n)
SENSES = {}
for r in _csv("lexicon.csv"):
    lemma = _s(r, "lemma")
    if not lemma:
        continue
    nval = _s(r, "n")
    SENSES.setdefault(lemma, []).append({
        "n":   int(nval) if nval.isdigit() else len(SENSES.get(lemma, [])) + 1,
        "pos": _s(r, "pos") or "X",
        "grc": _truthy(r.get("grc")),
        "en":  _s(r, "en"), "ja": _s(r, "ja"), "fr": _s(r, "fr"),
        "uja": _s(r, "usg_ja"), "uen": _s(r, "usg_en"),
    })
for _l in SENSES:
    SENSES[_l].sort(key=lambda s: s["n"])

# back-compat map for the main text (<w>) and stats: dominant (first) sense / lemma
LEX = {lemma: (s[0]["pos"], s[0]["en"], s[0]["ja"], s[0]["grc"])
       for lemma, s in SENSES.items()}

# themes: [(id, ja, en, fr), ...]
THEMES = [(_s(r, "id"), _s(r, "ja"), _s(r, "en"), _s(r, "fr"))
          for r in _csv("themes.csv") if _s(r, "id")]

# translations: TRANS[seg_id] = (ja, en) ; TRANS_FR[seg_id] = fr
TRANS, TRANS_FR = {}, {}
for r in _csv("translations.csv"):
    sid = _s(r, "seg_id")
    if not sid:
        continue
    TRANS[sid] = (_s(r, "ja"), _s(r, "en"))
    if _s(r, "fr"):
        TRANS_FR[sid] = _s(r, "fr")

# notes: NOTES = [(id, themes, targets, label_ja, body_ja, body_en), ...] ; NOTES_FR[id]=fr
NOTES, NOTES_FR = [], {}
for r in _csv("notes.csv"):
    nid = _s(r, "id")
    if not nid:
        continue
    NOTES.append((nid, _s(r, "themes"), _s(r, "targets"),
                  _s(r, "label_ja"), _s(r, "body_ja"), _s(r, "body_en")))
    if _s(r, "body_fr"):
        NOTES_FR[nid] = _s(r, "body_fr")

# ---------------------------------------------------------------------------
# 4. Helpers
# ---------------------------------------------------------------------------
def esc_attr(s): return html.escape(s, quote=True)
def esc_text(s): return html.escape(s, quote=False)

def strip_brackets(tok):
    # normalise a surface token to a lemma key (remove editorial brackets/dots)
    return re.sub(r'[\[\]\(\)\.·\u00b7]', '', tok)

def looks_greek(lemma):
    return any(lemma.endswith(s) for s in GREEK_SUFFIXES) and len(lemma) >= 4

def gloss_for(tok):
    key = strip_brackets(tok)
    if key in LEX:
        pos, en, ja, gk = LEX[key]
        return pos, en, ja, gk, key
    # fallback
    gk = looks_greek(key)
    return "X", "", "", gk, key

def read_segments(path):
    segs = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line.strip():
                continue
            parts = line.split('\t')
            sid, cop = None, None
            for p in parts:
                if re.fullmatch(r'\d+', p.strip()):
                    sid = p.strip()
                elif p.strip() and COPTIC_RE.search(p):
                    cop = p.strip()
            if cop is None and COPTIC_RE.search(line):
                cop = line.strip().rstrip('\t').strip()
            if cop:
                segs.append([sid, cop])
    # the first segment has no id -> mark as INCIPIT
    if segs and segs[0][0] is None:
        segs[0][0] = "INCIPIT"
    # any remaining None -> synthesise
    for i, s in enumerate(segs):
        if s[0] is None:
            s[0] = f"seg{i}"
    return segs

# theology lookup: source-id -> list of theme ids (for @ana on <s>)
seg_to_themes = {}
for nid, themes, targets, *_ in NOTES:
    for t in targets.split():
        seg_to_themes.setdefault(t, set()).update(themes.split())

# ---------------------------------------------------------------------------
# 5. Emit one witness <text>
# ---------------------------------------------------------------------------
def emit_witness_III(segs, with_gloss=False):
    out = []
    out.append('      <text type="witness" xml:id="wit-III" n="NHC III,3" xml:lang="cop">')
    out.append('        <body>')
    out.append('          <div type="tractate" n="Eugnostos" subtype="codexIII">')
    out.append('            <head xml:lang="en">Eugnostos the Blessed — Nag Hammadi Codex III,3 (pp. 70–90)</head>')
    n = 0
    for sid, cop in segs:
        n += 1
        toks = cop.split()
        ana = ""
        if sid in seg_to_themes:
            ana = ' ana="%s"' % " ".join("#" + t for t in sorted(seg_to_themes[sid]))
        corresp = ' corresp="#wit-V"' if sid == "INCIPIT" else ""
        seg_type = ' subtype="incipit"' if sid == "INCIPIT" else (
                   ' subtype="colophon"' if sid == "7505330" else "")
        attrs = ['xml:id="III-%s"' % sid, 'n="%d"' % n, 'source="marcion:%s"' % sid]
        if sid in TRANS:
            ja, en = TRANS[sid]
            attrs.append('transJa="%s"' % esc_attr(ja))
            attrs.append('transEn="%s"' % esc_attr(en))
        if sid in TRANS_FR:
            attrs.append('transFr="%s"' % esc_attr(TRANS_FR[sid]))
        line = '            <s %s%s%s%s>' % (" ".join(attrs), ana, corresp, seg_type)
        out.append(line)
        wline = []
        for tok in toks:
            pos, en, ja, gk, lemma = gloss_for(tok)
            # main text references the dictionary by @lemma; glosses live in the
            # separate lexicon file (eugnostos_lexicon.xml).
            a = ['type="%s"' % pos, 'lemma="%s"' % esc_attr(lemma)]
            if gk:
                a.append('xml:lang="grc"')
            if with_gloss:
                if en: a.append('gloss="%s"' % esc_attr(en))
                if ja: a.append('glossJa="%s"' % esc_attr(ja))
            wline.append('<w %s>%s</w>' % (" ".join(a), esc_text(tok)))
        for i in range(0, len(wline), 6):
            out.append('              ' + "".join(wline[i:i+6]))
        out.append('            </s>')
    out.append('          </div>')
    out.append('        </body>')
    out.append('      </text>')
    return "\n".join(out)

def emit_witness_V(segs):
    # Parallel scaffold: align to III incipit, mark the rest as to-be-supplied.
    out = []
    out.append('      <text type="witness" xml:id="wit-V" n="NHC V,1" xml:lang="cop">')
    out.append('        <body>')
    out.append('          <div type="tractate" n="Eugnostos" subtype="codexV">')
    out.append('            <head xml:lang="en">Eugnostos the Blessed — Nag Hammadi Codex V,1 (pp. 1–17, parallel witness)</head>')
    out.append('            <note type="editorial" xml:lang="ja">この証本(V,1)は III,3 と対応づけられた並行版の枠組みです。'
               'V,1 の本文(コプト語形態素・グロス)は校訂版(Parrott, NHS 27, Brill 1991)に拠って補充してください。'
               '各 &lt;s&gt; は III,3 の対応セグメントへ @corresp で結ばれます。</note>')
    # demonstrate alignment on the incipit only (text is lacunose in V)
    out.append('            <s xml:id="V-INCIPIT" n="1" corresp="#III-INCIPIT" subtype="incipit" '
               'transJa="（V,1 冒頭は大きく欠損。標題のみ「エウグノストス」と末尾に残る）" '
               'transEn="(The opening of V,1 is largely lacunose; only the title \'Eugnostos\' survives at the end.)">')
    out.append('              <gap reason="lacuna" unit="line" extent="unknown"/>')
    out.append('            </s>')
    out.append('          </div>')
    out.append('        </body>')
    out.append('      </text>')
    return "\n".join(out)

# ---------------------------------------------------------------------------
# 6. Emit standOff (theology) + lexicon
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 6. Separate companion documents: lexicon (dictionary) & theology (annotation)
# ---------------------------------------------------------------------------
def header_min(title_en, title_ja, desc_ja, lang="cop"):
    today = datetime.date.today().isoformat()
    return f'''  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title xml:lang="en">{esc_text(title_en)}</title>
        <title xml:lang="ja">{esc_text(title_ja)}</title>
        <respStmt><resp>compiled by</resp><name>Eugnostos Digital Corpus project</name></respStmt>
      </titleStmt>
      <publicationStmt>
        <authority>Eugnostos Digital Corpus</authority>
        <availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY 4.0</licence></availability>
        <date when="{today}">{today}</date>
      </publicationStmt>
      <sourceDesc><p xml:lang="ja">{esc_text(desc_ja)}</p>
        <p xml:lang="ja">本文ファイル <ref target="eugnostos_tei.xml">eugnostos_tei.xml</ref> の補助ファイルです。</p></sourceDesc>
    </fileDesc>
    <revisionDesc><change when="{today}" n="0.1">Initial seed build.</change></revisionDesc>
  </teiHeader>'''

def build_lexicon_doc():
    """Standalone Coptic dictionary built from lexicon.csv.
    A lemma with one row -> a single <entry>; several rows -> a <superEntry>
    grouping one <entry> per homograph sense."""
    def cits(en, ja, fr):
        s = ('<cit type="translation" xml:lang="en"><quote>%s</quote></cit>'
             '<cit type="translation" xml:lang="ja"><quote>%s</quote></cit>'
             % (esc_text(en), esc_text(ja)))
        if fr:
            s += '<cit type="translation" xml:lang="fr"><quote>%s</quote></cit>' % esc_text(fr)
        return s
    p = []
    p.append('<?xml version="1.0" encoding="UTF-8"?>')
    p.append('<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="cop">')
    p.append(header_min(
        "Eugnostos - Coptic lexicon (lemma glossary)",
        "\u30a8\u30a6\u30b0\u30ce\u30b9\u30c8\u30b9 \u30b3\u30d7\u30c8\u8a9e\u8f9e\u66f8",
        "\u30b3\u30d7\u30c8\u8a9e\u8f9e\u66f8\u30c7\u30fc\u30bf(lexicon.csv \u7531\u6765)\u3002"
        "\u540c\u5f62\u7570\u7fa9\u8a9e\u306f <superEntry> \u306b\u307e\u3068\u3081\u3001\u5404 <entry>"
        "(\u56fa\u6709 xml:id)\u304c\u54c1\u8a5e\u30fb\u7528\u6cd5(usg)\u30fb\u8a9e\u7fa9\u3092\u500b\u5225\u306b\u6301\u3061\u307e\u3059\u3002"))
    p.append('  <text><body>')
    p.append('    <div type="lexicon">')
    p.append('      <head xml:lang="ja">\u30b3\u30d7\u30c8\u8a9e\u8f9e\u66f8</head>')
    p.append('      <list type="gloss">')
    for lemma in sorted(SENSES.keys()):
        base = abs(hash(lemma)) % (10**8)
        senses = SENSES[lemma]
        if len(senses) > 1:
            p.append('        <superEntry xml:id="lex-%s">' % base)
            p.append('          <form type="lemma"><orth>%s</orth></form>' % esc_text(lemma))
            for i, s in enumerate(senses, 1):
                usg = ""
                if s["uja"]:
                    usg += '<usg type="hint" xml:lang="ja">%s</usg>' % esc_text(s["uja"])
                if s["uen"]:
                    usg += '<usg type="hint" xml:lang="en">%s</usg>' % esc_text(s["uen"])
                p.append('          <entry xml:id="lex-%s-%d" n="%d"%s>'
                         '<form type="lemma"><orth>%s</orth></form>'
                         '<gramGrp><pos>%s</pos></gramGrp>%s'
                         '<sense n="%d">%s</sense></entry>'
                         % (base, i, i, ' xml:lang="grc"' if s["grc"] else "",
                            esc_text(lemma), s["pos"], usg, i, cits(s["en"], s["ja"], s["fr"])))
            p.append('        </superEntry>')
        else:
            s = senses[0]
            p.append('        <entry xml:id="lex-%s"%s>'
                     '<form type="lemma"><orth>%s</orth></form>'
                     '<gramGrp><pos>%s</pos></gramGrp><sense>%s</sense></entry>'
                     % (base, ' xml:lang="grc"' if s["grc"] else "",
                        esc_text(lemma), s["pos"], cits(s["en"], s["ja"], s["fr"])))
    p.append('      </list>')
    p.append('    </div>')
    p.append('  </body></text>')
    p.append('</TEI>')
    return "\n".join(p)

def build_theology_doc():
    """Standalone annotation file: theological notes + the theme taxonomy."""
    today = datetime.date.today().isoformat()
    cats = "\n".join(
        '          <category xml:id="%s"><catDesc xml:lang="ja">%s</catDesc>'
        '<catDesc xml:lang="en">%s</catDesc><catDesc xml:lang="fr">%s</catDesc></category>'
        % (cid, esc_text(ja), esc_text(en), esc_text(fr))
        for cid, ja, en, fr in THEMES)
    p = []
    p.append('<?xml version="1.0" encoding="UTF-8"?>')
    p.append('<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="ja">')
    # header with the taxonomy (so themes are declared alongside the notes)
    p.append(f'''  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title xml:lang="en">Eugnostos — theological annotations</title>
        <title xml:lang="ja">エウグノストス 注釈(神学的解釈)</title>
        <respStmt><resp>notes by</resp><name>Eugnostos Digital Corpus project</name></respStmt>
      </titleStmt>
      <publicationStmt>
        <authority>Eugnostos Digital Corpus</authority>
        <availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY 4.0</licence></availability>
        <date when="{today}">{today}</date>
      </publicationStmt>
      <sourceDesc><p xml:lang="ja">注釈データ(神学的解釈)。各 note は @target で本文 <ref target="eugnostos_tei.xml">eugnostos_tei.xml</ref> の &lt;s&gt;(xml:id="III-…")へ、@ana で下の主題分類へリンクします。</p></sourceDesc>
    </fileDesc>
    <encodingDesc>
      <classDecl>
        <taxonomy xml:id="theology-taxonomy">
          <desc xml:lang="ja">神学的主題の分類。本文 &lt;s&gt; の @ana と各注の @ana から参照されます。</desc>
{cats}
        </taxonomy>
      </classDecl>
    </encodingDesc>
    <revisionDesc><change when="{today}" n="0.1">Initial seed build.</change></revisionDesc>
  </teiHeader>''')
    p.append('  <standOff>')
    p.append('    <listAnnotation type="theology" xml:id="theology">')
    p.append('      <desc xml:lang="ja">神学的解釈レイヤ。@target で本文セグメントへ、@ana で主題分類へ結ばれます。</desc>')
    for nid, themes, targets, title_ja, body_ja, body_en in NOTES:
        tgt = " ".join("eugnostos_tei.xml#III-" + t for t in targets.split())
        p.append('      <note xml:id="%s" type="theology" ana="%s" target="%s">'
                 % (nid, " ".join("#" + t for t in themes.split()), tgt))
        p.append('        <label xml:lang="ja">%s</label>' % esc_text(title_ja))
        p.append('        <p xml:lang="ja">%s</p>' % esc_text(body_ja))
        p.append('        <p xml:lang="en">%s</p>' % esc_text(body_en))
        if nid in NOTES_FR:
            p.append('        <p xml:lang="fr">%s</p>' % esc_text(NOTES_FR[nid]))
        p.append('      </note>')
    p.append('    </listAnnotation>')
    p.append('  </standOff>')
    p.append('</TEI>')
    return "\n".join(p)

# ---------------------------------------------------------------------------
# 7. Header for the MAIN text file (taxonomy kept here too, for @ana on <s>)
# ---------------------------------------------------------------------------
def header():
    today = datetime.date.today().isoformat()
    cats = "\n".join(
        '          <category xml:id="%s"><catDesc xml:lang="ja">%s</catDesc>'
        '<catDesc xml:lang="en">%s</catDesc><catDesc xml:lang="fr">%s</catDesc></category>'
        % (cid, esc_text(ja), esc_text(en), esc_text(fr))
        for cid, ja, en, fr in THEMES)
    return f'''  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title ref="urn:cts:copticLit:nag.eugnostos" xml:lang="en">Eugnostos the Blessed</title>
        <title xml:lang="ja">祝福されたエウグノストス</title>
        <title type="sub" xml:lang="en">A two-witness TEI edition with stand-off lexicon and annotations (NHC III,3 and V,1)</title>
        <author>Anonymous (Gnostic; Greek original, 1st–2nd c. CE)</author>
        <respStmt><resp>TEI encoding, lexicon, translation and theological notes</resp><name>Eugnostos Digital Corpus project</name></respStmt>
        <respStmt><resp>source text (tokenised Sahidic Coptic, Codex III,3)</resp><name>supplied corpus (Marcion segment ids)</name></respStmt>
      </titleStmt>
      <editionStmt><edition n="0.1">Seed edition — lexicon, translations and notes are a curated first pass for scholarly review.</edition></editionStmt>
      <publicationStmt>
        <authority>Eugnostos Digital Corpus</authority>
        <availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY 4.0</licence></availability>
        <date when="{today}">{today}</date>
      </publicationStmt>
      <sourceDesc>
        <msDesc>
          <msIdentifier><settlement>Cairo</settlement><repository>Coptic Museum</repository><idno>NHC III</idno><msName>Nag Hammadi Codex III</msName></msIdentifier>
          <history><origin><origDate notBefore="0300" notAfter="0400">4th c. CE</origDate><origPlace>Egypt</origPlace></origin></history>
          <msContents><msItem n="3"><locus from="70" to="90">pp. 70,1–90,11</locus><textLang mainLang="cop" otherLangs="grc">Sahidic Coptic (with Greek loanwords)</textLang><title>Eugnostos the Blessed</title></msItem></msContents>
        </msDesc>
        <msDesc>
          <msIdentifier><repository>Nag Hammadi Codex V</repository><idno>NHC V</idno><msName>Nag Hammadi Codex V</msName></msIdentifier>
          <msContents><msItem n="1"><locus from="1" to="17">pp. 1,1–17,17 (largely lacunose)</locus><textLang mainLang="cop" otherLangs="grc">Sahidic Coptic</textLang><title>Eugnostos the Blessed</title></msItem></msContents>
        </msDesc>
        <listBibl>
          <bibl>Douglas M. Parrott (ed.), <title>Nag Hammadi Codices III,3–4 and V,1 … Eugnostos and the Sophia of Jesus Christ</title> (Nag Hammadi Studies 27), Brill 1991.</bibl>
          <bibl>M. Scopello &amp; M. Meyer, "Eugnostos the Blessed," in <title>The Nag Hammadi Scriptures</title>, HarperOne 2007.</bibl>
          <bibl>Anne Pasquier, <title>Eugnoste (NH III,3 et V,1)</title> (Bibliothèque copte de Nag Hammadi, section « Textes » 26 ; et le volume de commentaire), Québec/Louvain : Presses de l'Université Laval / Peeters.</bibl>
          <bibl>小林稔訳「エウグノストス」(『ナグ・ハマディ文書』所収の邦訳, §1–§43).</bibl>
          <bibl>Louis Painchaud, "The Literary Contacts between the Writing without Title On the Origin of the World (CG II,5 and XIII,2) and Eugnostos the Blessed (CG III,3 and V,1)," <title>JBL</title> 114/1 (1995) 81–101.</bibl>
        </listBibl>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <projectDesc><p xml:lang="ja">ナグ・ハマディ写本『祝福されたエウグノストス』を、形態素ごとに意味を参照でき、写本III,3とV,1を対照でき、神学的解釈を併読できる形で公開するためのTEI符号化。データは3ファイルに分離しています。</p></projectDesc>
      <editorialDecl>
        <p xml:lang="ja">本ファイルは&lt;b&gt;本文&lt;/b&gt;です。各 &lt;w&gt; は @type(品詞)・@lemma(レンマ)を持ち、語義は&lt;b&gt;別ファイルのコプト語辞書&lt;/b&gt;(eugnostos_lexicon.xml)を @lemma で参照します。ギリシア借用語は @xml:lang="grc"。セグメント &lt;s&gt; の対訳は独自属性 @transJa / @transEn に格納。神学的解釈(注釈)は&lt;b&gt;別ファイル&lt;/b&gt;(eugnostos_theology.xml)にあり、@target で本文 &lt;s&gt; を指します。</p>
        <p xml:lang="en">This is the &lt;b&gt;text&lt;/b&gt; file. Glosses live in the companion dictionary &lt;ref target="eugnostos_lexicon.xml"&gt;eugnostos_lexicon.xml&lt;/ref&gt; (joined by @lemma); theological annotations live in &lt;ref target="eugnostos_theology.xml"&gt;eugnostos_theology.xml&lt;/ref&gt; (linked by @target).</p>
      </editorialDecl>
      <classDecl>
        <taxonomy xml:id="theology-taxonomy">
          <desc xml:lang="ja">神学的主題の分類。&lt;s&gt; の @ana から参照されます(注釈ファイルにも同じ分類を収録)。</desc>
{cats}
        </taxonomy>
      </classDecl>
    </encodingDesc>
    <profileDesc>
      <langUsage>
        <language ident="cop">Sahidic Coptic</language>
        <language ident="grc">Greek (loanwords)</language>
        <language ident="ja">Japanese (translations, notes)</language>
        <language ident="en">English (translations, notes)</language>
        <language ident="fr">French (translations, notes)</language>
      </langUsage>
      <textClass><keywords scheme="#theology-taxonomy"><term>Gnosticism</term><term>cosmogony</term><term>Sethian</term><term>apophatic theology</term></keywords></textClass>
    </profileDesc>
    <revisionDesc><change when="{today}" n="0.1">Initial seed build from tokenised Codex III,3 source; lexicon and annotations split into companion files.</change></revisionDesc>
  </teiHeader>'''

# ---------------------------------------------------------------------------
# 8. Build the MAIN text document (witnesses only; no glosses, no standoff)
# ---------------------------------------------------------------------------
def build_main(segs, limit=None):
    use = segs[:limit] if limit else segs
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="cop">')
    parts.append(header())
    parts.append('  <text>')
    parts.append('    <group>')
    parts.append(emit_witness_III(use, with_gloss=False))
    parts.append(emit_witness_V(use))
    parts.append('    </group>')
    parts.append('  </text>')
    parts.append('</TEI>')
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# 9. Write the three files (+ a small main sample for the offline viewer)
# ---------------------------------------------------------------------------
OUTDIR = DATA
# 注意: ビュワー (eugnostos.html) は data/lexicon.xml を最優先で読み込むため、
# 辞書の出力先はこの名前に固定する（旧名 eugnostos_lexicon.xml から変更）。
LEX_OUT  = os.path.join(OUTDIR, "lexicon.xml")
THEO_OUT = os.path.join(OUTDIR, "eugnostos_theology.xml")
MAIN_SAMPLE = os.path.join(OUTDIR, "eugnostos_main_sample.xml")

segs = read_segments(SRC)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(build_main(segs))
with open(LEX_OUT, "w", encoding="utf-8") as f:
    f.write(build_lexicon_doc())
with open(THEO_OUT, "w", encoding="utf-8") as f:
    f.write(build_theology_doc())
with open(MAIN_SAMPLE, "w", encoding="utf-8") as f:
    f.write(build_main(segs, limit=SAMPLE_N))

# stats
total_tokens = sum(len(c.split()) for _, c in segs)
glossed = sum(1 for _, c in segs for t in c.split()
              if (lambda r: r[1] or r[2])(gloss_for(t)))
print("segments:", len(segs), "| tokens:", total_tokens,
      "| lemma-glossable: %.1f%%" % (100*glossed/total_tokens))
print("theology notes:", len(NOTES), "| themes:", len(THEMES),
      "| lemmas:", len(SENSES), "| curated translations:", len(TRANS))
hom = {k: v for k, v in SENSES.items() if len(v) > 1}
print("homographs:", len(hom), "forms →", sum(len(v) for v in hom.values()), "senses",
      "| total sense rows:", sum(len(v) for v in SENSES.values()))
print("wrote MAIN   :", OUT)
print("wrote LEXICON:", LEX_OUT)
print("wrote THEOLOGY:", THEO_OUT)
print("wrote main sample:", MAIN_SAMPLE)
