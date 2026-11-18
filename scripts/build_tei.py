#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 build_tei.py — source/ の CSV から TEI XML を生成し、data/ と見比べるスクリプト
==============================================================================

【まず読んでください / Read this first】
  このスクリプトは、何も付けずに実行しても data/ のファイルを書き換えません。

      python3 scripts/build_tei.py

  とすると、次の 2 つだけを行います。
    1. source/ の CSV・TSV から XML を生成し、build/tei/ に書き出す
       (build/ は git の管理外です。サイトには出ません)
    2. data/ にある現在の XML と比べ、「もし data/ に書き込んだら、いまの
       ファイルから何が消え、何が増えるか」を表示する

  By default this script never touches data/. It writes its output to
  build/tei/ and reports what would be lost or added if that output replaced
  the files in data/.

【なぜ書き込まないのか — 現状 (2026-11-18 時点)】
  data/ の XML は、生成されたあとに手作業と別のスクリプトで直されていて、
  このスクリプトの生成結果とはもう一致しません。生成結果で置き換えると、
  たとえば次のものが失われます。
    eugnostos_tei.xml  冒頭 9 節の <phy>(語のまとまり)・語の切り方・レンマ・
                       @gloss、全体にわたる品詞の付け直し、訳文の改訂、
                       TEI として正しい構造 (<ab>、msContents の位置)
    lexicon.xml        通し番号の xml:id (lex-0001…)、CDO へのリンク、
                       <entry> を <div> の直下に置く構造。このスクリプトは
                       xml:id を実行のたびに違う番号で振り直します
  2026-07-04 には、このスクリプトの出力で data/ が実際に上書きされました
  (コミット 249a222)。本文は 3 分後に戻されましたが、XML に直接加えてあった
  注釈 7 件と辞書の項目 189 件 (4,014 → 3,825) は、このとき data/ から消えました
  (直前の状態はコミット 1f97a93 に残っています)。
  そのため、既定の動作を「書き込まない」にしてあります。

  辞書 (source/lexicon.csv → data/lexicon.xml) の反映には、xml:id を変えずに
  差分だけを書き込む scripts/sync_lexicon.py を使ってください。

【それでも data/ に書き込むとき】
      python3 scripts/build_tei.py --write-data
  いまのファイルの内容がすべてそのまま残り、「追加だけ」になる場合に限って
  data/ を更新します。何かが消える・変わる・順序や入れ子が変わるファイルが
  1 つでもあれば、どのファイルも書き換えずに止まります。
  (比べるときに無視するのは、空白と改行の入れ方、属性の並び順、ヘッダーの
  日付だけです。書き込んだファイルのヘッダーの日付は、実行した日になります)

      python3 scripts/build_tei.py --write-data --allow-loss
  失われるものがあっても置き換えます。置き換える前のファイルは
  build/tei-backup/<日時>/ に写しを残します。表示された「消えるもの」を読み、
  それが要らないと確かめた場合にだけ使ってください。

【入力 (source/ 内)】
  lexicon.csv       lemma,n,pos,grc,en,ja,fr,usg_ja,usg_en,cdo
                    1行 = 1語義。同じ lemma を複数行 (n=1,2,3…) にすると
                    同形異義語。grc=Y でギリシア借用語。usg_* は用法ヒント。
                    (cdo 列は sync_lexicon.py が読みます。このスクリプトは読みません)
  translations.csv  seg_id,ja,en,fr   … セグメント単位の対訳
  notes.csv         id,themes,targets,label_ja,body_ja,body_en,body_fr
                    themes / targets は空白区切りの ID 列
  themes.csv        id,ja,en,fr       … 主題分類ラベル
  eugnostos_source.tsv  トークン化済みコプト語本文

【出力】
  build/tei/ (既定。--out DIR で変えられます。data/ は指定できません)
    eugnostos_tei.xml            本文 (TEI P5)
    lexicon.xml                  コプト語辞書 (ビュワーは data/lexicon.xml を読む)
    eugnostos_theology.xml       神学的注釈
    eugnostos_main_sample.xml    冒頭だけのサンプル。いまは読み込むページが無いので、
                                 --write-data でも data/ には書きません
  data/ (--write-data を付け、かつ上の条件を満たしたときだけ)
    eugnostos_tei.xml / lexicon.xml / eugnostos_theology.xml
==============================================================================
"""
import re, html, sys, datetime, os, csv
import argparse, collections, shutil
import xml.etree.ElementTree as ET

# --- 実行時の指定 -----------------------------------------------------------
def _parse_args(argv):
    ap = argparse.ArgumentParser(
        prog="build_tei.py",
        description="source/ の CSV・TSV から TEI XML を生成し、data/ の現在のファイルと比べます。"
                    "何も付けなければ data/ は書き換えません (生成結果は build/tei/ に出ます)。")
    ap.add_argument("source", nargs="?", default=None,
                    help="本文ソース (TSV) のパス。省略すると source/eugnostos_source.tsv")
    ap.add_argument("--out", metavar="DIR", default=None,
                    help="生成結果の書き出し先 (既定: build/tei/)。data/ は指定できません")
    ap.add_argument("--write-data", action="store_true",
                    help="data/ も更新する。いまのファイルの内容が失われる場合は、書き込まずに止まります")
    ap.add_argument("--allow-loss", action="store_true",
                    help="--write-data と併用。内容が失われても置き換える "
                         "(前のファイルは build/tei-backup/ に残します)")
    args = ap.parse_args(argv)
    if args.allow_loss and not args.write_data:
        ap.error("--allow-loss は --write-data と一緒に使います")
    return args

# import されただけのときは引数を読まない (ファイルを書くのは main() の中だけ)
ARGS = _parse_args(sys.argv[1:] if __name__ == "__main__" else [])

# --- パス設定 ---------------------------------------------------------------
# BASE    = このスクリプトのあるフォルダ (scripts/)
# ROOT    = プロジェクトのルート
# SRCDIR  = 編集用 CSV / TSV の置き場 (source/)
# DATA    = サイトが読む XML の置き場 (data/)。既定では書き込まない
# PREVIEW = 生成結果の既定の書き出し先 (build/tei/)
# BACKUPS = data/ を置き換える前の写しの置き場 (build/tei-backup/)
BASE = os.path.dirname(os.path.abspath(__file__))
# スクリプトが scripts/ (旧: source/) にある場合、ルートはその親フォルダ
ROOT = os.path.dirname(BASE) if os.path.basename(BASE).lower() in ("source", "build", "src", "scripts") else BASE
SRCDIR = os.path.join(ROOT, "source")          # 編集用 CSV / TSV
if not os.path.isdir(SRCDIR):
    SRCDIR = BASE                              # 旧レイアウトへの後方互換

def _find_source():
    """Locate the tokenised Coptic source next to this script.
    Accepts an explicit path as the positional argument, else tries common names."""
    if ARGS.source:
        return ARGS.source
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
DATA    = os.path.join(ROOT, "data")                  # サイトが読む XML (既定では書き込まない)
PREVIEW = os.path.join(ROOT, "build", "tei")          # 生成結果の既定の書き出し先
BACKUPS = os.path.join(ROOT, "build", "tei-backup")   # data/ を置き換える前の写し
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
# 9. Output. The generated files go to a preview folder and are compared with
#    the files in data/. data/ itself is written only with --write-data, and
#    then only if nothing in the current files would be lost (--allow-loss
#    overrides that, after keeping a copy of what it replaces).
# ---------------------------------------------------------------------------
MAIN_NAME   = "eugnostos_tei.xml"
# 注意: ビュワー (eugnostos.html) は data/lexicon.xml を最優先で読み込むため、
# 辞書の出力名はこの名前に固定する（旧名 eugnostos_lexicon.xml から変更）。
LEX_NAME    = "lexicon.xml"
THEO_NAME   = "eugnostos_theology.xml"
SAMPLE_NAME = "eugnostos_main_sample.xml"
SITE_FILES  = (MAIN_NAME, LEX_NAME, THEO_NAME)   # data/ にあって、サイトが読むファイル

_XML_NS  = "{http://www.w3.org/XML/1998/namespace}"
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

def _rel(path):
    """表示用: リポジトリのルートからの相対パス (外にあるものはそのまま)。"""
    rel = os.path.relpath(path, ROOT)
    return path if rel.startswith("..") else rel

def _local(name):
    """'{namespace}name' -> 'name' ; xml:id などは 'xml:id' と表示する。"""
    if name.startswith(_XML_NS):
        return "xml:" + name[len(_XML_NS):]
    return name.split("}", 1)[1] if name.startswith("{") else name

def _norm(s):
    return " ".join((s or "").split())

def _flatten(xml_text):
    """XML を (種類, 名前, 場所, 値) の列に直す。比較のためのもの。

    空白や改行の入れ方、属性の並び順、ヘッダーの日付 (このスクリプトは実行した日を
    入れる) の違いは、ここで消える。要素の順序と入れ子は列の順序と「場所」に残る。"""
    root = ET.fromstring(_DATE_RE.sub("(日付)", xml_text).encode("utf-8"))
    rows = []
    def walk(el, path):
        name = _local(el.tag)
        here = path + "/" + name
        rows.append(("elem", name, here, ""))
        for k in sorted(el.attrib):
            rows.append(("attr", _local(k), here, _norm(el.attrib[k])))
        if _norm(el.text):
            rows.append(("text", name, here, _norm(el.text)))
        for child in el:
            walk(child, here)
            if _norm(child.tail):
                rows.append(("text", name, here, _norm(child.tail)))
    walk(root, "")
    return rows

def _compare(path, new_text):
    """data/ の現在のファイル (path) と生成結果 (new_text) を比べる。

    state:
      new         data/ にまだ無い
      unreadable  いまのファイルを XML として読めない
      same        内容は同じ (空白・書式・ヘッダーの日付だけの違いを含む)
      adds        いまの内容はすべて同じ順序で残り、追加だけ
      loses       いまのファイルにあるものが消える、または変わる
      moved       数は合うが、要素の順序か入れ子が変わる
    """
    if not os.path.exists(path):
        return {"state": "new"}
    try:
        with open(path, encoding="utf-8") as f:
            old = _flatten(f.read())
    except (ET.ParseError, UnicodeDecodeError) as ex:
        return {"state": "unreadable", "error": str(ex)}
    new = _flatten(new_text)
    if old == new:
        return {"state": "same"}
    old_count = collections.Counter((k, n, v) for k, n, _, v in old)
    new_count = collections.Counter((k, n, v) for k, n, _, v in new)
    lost, gained = old_count - new_count, new_count - old_count
    rest = iter(new)
    additions_only = all(row in rest for row in old)   # old は new の部分列か
    state = "adds" if additions_only else ("loses" if lost else "moved")
    def totals(counter):
        t = collections.Counter()
        for (k, n, _), c in counter.items():
            t[(k, n)] += c
        return t
    return {"state": state, "lost": lost, "gained": gained,
            "old_total": totals(old_count), "new_total": totals(new_count)}

def _summarise(diff, old_total, new_total, limit=14):
    """消える (または増える) ものを、要素・属性・文字列の種類ごとに数えて行にする。"""
    groups = {}
    for (kind, name, value), n in diff.items():
        g = groups.setdefault((kind, name), {"n": 0, "example": "", "top": 0})
        g["n"] += n
        if value and n > g["top"]:
            g["example"], g["top"] = value, n
    lines = []
    ordered = sorted(groups.items(), key=lambda kv: (-kv[1]["n"], kv[0]))
    for (kind, name), g in ordered[:limit]:
        if kind == "elem":
            lines.append("要素 <%s>: %d 個 → %d 個" % (name, old_total[(kind, name)], new_total[(kind, name)]))
            continue
        label = ("属性 @%s の値" % name) if kind == "attr" else ("<%s> の中の文字列" % name)
        ex = g["example"]
        if len(ex) > 36:
            ex = ex[:36] + "…"
        lines.append("%s: %d 件 (例: %s)" % (label, g["n"], ex))
    if len(ordered) > limit:
        lines.append("ほか %d 種類" % (len(ordered) - limit))
    return lines

def _print_report(name, rep):
    print("\n■ data/%s" % name)
    state = rep["state"]
    if state == "new":
        print("  data/ にまだありません。--write-data を付けると新しく作られます。")
    elif state == "unreadable":
        print("  いまのファイルを XML として読めないので、比べられません: %s" % rep["error"])
    elif state == "same":
        print("  内容は同じです (違いがあっても、空白・書式・ヘッダーの日付だけ)。書き換える必要はありません。")
    else:
        lost = _summarise(rep["lost"], rep["old_total"], rep["new_total"])
        gained = _summarise(rep["gained"], rep["old_total"], rep["new_total"])
        if state == "adds":
            print("  いまのファイルの内容はすべて残ります。次のものが加わります:")
        elif state == "moved":
            print("  いまのファイルにあるものは数の上では残りますが、要素の順序か入れ子が変わります。")
            if gained:
                print("  加わるもの:")
        else:
            print("  生成結果で置き換えると、いまのファイルから次のものが消えます (変わるものを含む):")
            for line in lost:
                print("    ・" + line)
            if any(k == "attr" and n == "xml:id" for k, n, _ in rep["lost"]):
                print("    (xml:id が変わると、その番号を指している @ana・@target・@corresp の参照が切れます)")
            if gained:
                print("  代わりに入るもの:")
        for line in gained:
            print("    ・" + line)

def _write(path, text):
    """一時ファイルに書いてから置き換える (書きかけのファイルを残さない)。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def main():
    out_dir = os.path.abspath(ARGS.out) if ARGS.out else PREVIEW
    real_out, real_data = os.path.realpath(out_dir), os.path.realpath(DATA)
    if real_out == real_data or real_out.startswith(real_data + os.sep):
        sys.exit("\n[!] --out に data/ (とその中のフォルダ) は指定できません。\n"
                 "    data/ を更新するには --write-data を使います。その場合も、いまのファイルの\n"
                 "    内容が失われるときは書き込まずに止まります。\n")

    segs = read_segments(SRC)
    docs = collections.OrderedDict([
        (MAIN_NAME,   build_main(segs)),
        (LEX_NAME,    build_lexicon_doc()),
        (THEO_NAME,   build_theology_doc()),
        (SAMPLE_NAME, build_main(segs, limit=SAMPLE_N)),
    ])

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

    # 1) 生成結果を、data/ とは別のフォルダに書き出す
    os.makedirs(out_dir, exist_ok=True)
    for name, text in docs.items():
        _write(os.path.join(out_dir, name), text)
    print("\n生成結果の書き出し先: %s/" % _rel(out_dir))
    for name in docs:
        print("  " + name)

    # 2) data/ の現在のファイルと比べる
    print("\n" + "=" * 70)
    print("data/ にある現在のファイルとの比較 — もし data/ に書き込んだら何が変わるか")
    print("=" * 70)
    reports = collections.OrderedDict(
        (name, _compare(os.path.join(DATA, name), docs[name])) for name in SITE_FILES)
    for name, rep in reports.items():
        _print_report(name, rep)
    risky = [n for n, r in reports.items() if r["state"] in ("loses", "moved", "unreadable")]
    to_write = [n for n, r in reports.items() if r["state"] != "same"]

    # 3) data/ は、頼まれたときだけ、失うものが無いときだけ書き換える
    print("\n" + "=" * 70)
    if not ARGS.write_data:
        print("data/ は変更していません。")
        if risky:
            print("この生成結果で data/ を置き換えると、上に挙げたとおり、いまの内容が失われるか変わります: "
                  + ", ".join(risky))
            print("辞書 (source/lexicon.csv) の変更を data/lexicon.xml に反映するには、")
            print("xml:id を変えない scripts/sync_lexicon.py を使ってください。")
        elif to_write:
            print("追加だけなので、--write-data を付けて実行すれば data/ に反映できます: " + ", ".join(to_write))
        return 0

    if risky and not ARGS.allow_loss:
        print("[!] 書き込みを中止しました。data/ には何も書き込んでいません。")
        print("    次のファイルは、置き換えると現在の内容が失われるか変わります: " + ", ".join(risky))
        print("    上の「消えるもの」を確かめたうえで、それでも置き換える場合に限り、")
        print("    --write-data --allow-loss を付けてください (前のファイルの写しを残します)。")
        return 1

    if not to_write:
        print("data/ の 3 つのファイルは生成結果と同じ内容です。書き込むものはありません。")
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = os.path.join(BACKUPS, stamp)
    os.makedirs(DATA, exist_ok=True)
    for name in SITE_FILES:
        target = os.path.join(DATA, name)
        if name not in to_write:
            print("変更なし      : %s" % _rel(target))
            continue
        if os.path.exists(target):
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(target, os.path.join(backup_dir, name))
            print("書き込みました: %s  (前のファイルの写し: %s)"
                  % (_rel(target), _rel(os.path.join(backup_dir, name))))
        else:
            print("新しく作りました: %s" % _rel(target))
        _write(target, docs[name])
    return 0

if __name__ == "__main__":
    sys.exit(main())
