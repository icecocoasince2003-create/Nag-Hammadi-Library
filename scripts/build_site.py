#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 build_site.py — サイトの外枠 (index.html / tractate.html) を生成する
==============================================================================

【共同編集者の方へ】
  実行方法（リポジトリのルートで）:

      python3 scripts/build_site.py
      python3 scripts/build_site.py --check   生成ファイルが最新かを調べるだけ（書き込まない。CI で使う）

  出力される index.html・tractate.html・reader.html・sitemap.xml・robots.txt・data/doc_dates.json・data/pos_labels.json・
  data/fulltext_stats.json（scripts/build_fulltext_stats.py の数え方）は自動生成なので
  直接編集しないでください。--check は、いまのスクリプトとデータから作り直したものとファイルを比べ、違えば終了コード 1 で
  ファイル名を表示します（index.html のフッターの「生成」の日付は、作り直すたびに変わるので比べません）。目次の内容を変えたいときは、下の CODICES テーブルを編集して
  再実行します。

  * HOME は日本語・英語・フランス語の三言語表示です（上部ナビで切替）。
    題名は CODICES の ja / en / fr 列、その他の文言はこのファイル内の
    <span class="l-ja">…</span><span class="l-en">…</span><span class="l-fr">…</span> を編集します。
  * NEWS（更新情報）は data/news.json、関連サイトは data/links.json を編集し、このスクリプトを実行し直します。
    生成のときに index.html へ HTML として書き込むので、JS を動かさない読み手（リンクのプレビュー、一部の検索エンジン、
    リーダー表示など）にも出ます。作り直す前でも、ページを開いたときに JSON を読み直して最新を出します。
  * index.html・tractate.html・reader.html の <head> には、OGP と Twitter カードのタグを書き込みます（og_tags）。
    共有用の画像は image/og-image.png（scripts/make_og_image.py が作る）。sitemap.xml と robots.txt もこのスクリプトが出力します。
  * 上部ナビの項目は assets/site.js の NAV で全ページ共通に管理しています。
  * HOME と準備中ページは、ほかのページと同じく表示モード（ライト／ダーク）に対応しています。
    上部ナビの ☀／☾ で切り替わり、配色は assets/cosmos.css の「ライトモード」、
    HOME 固有の調整は下の INDEX_CSS の末尾にあります。

【新しい文書を「公開」に切り替える手順】
  1. ビュワー HTML（例: eugnostos.html）をルートに用意する
  2. 下の CODICES で該当行の status を S(準備中) → A(公開) に変える
  3. LINKS にリンク先（ビュワーのURL）を登録する
  4. python3 scripts/build_site.py を実行して index.html を再生成

【暫定公開（自動注釈の全文）と未注釈の全文】
  status を D にすると「暫定」、U にすると「未注釈」と HOME の一覧に出し、reader.html?doc=写本-番号 へリンクします
  （全文テキストの番号がこの一覧と違う文書は READER_DOC に書く）。
  reader.html もこのスクリプトが出力します（build_reader）。本文は data/catalog.xml の <bibl subtype="draft">
  が指す TEI で、その一覧は scripts/sync_nhc_catalog.py が書き出します。確かめていないことは reader.html が
  文書ごとに冒頭に示します。
==============================================================================
"""
import html, datetime, os, json, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() in ("source", "build", "src", "scripts") else _HERE

# --- 版の情報と公開 URL（data/release.json）、リンクを共有したときのプレビュー（OGP） -------------
# 版番号は HOME のフッターに出す。引用表記（project.html・ビュワー）も同じファイルを読む（assets/viewer-tools.js）。
# 独自ドメインに移すときは、release.json の url と、手作業管理のページの <head> の og:url・og:image、
# CITATION.cff・.zenodo.json の URL を直す（scripts/check_release.py が release.json との食い違いを報告する）。
with open(os.path.join(OUTDIR, "data", "release.json"), encoding="utf-8") as _f:
    RELEASE = json.load(_f)
VERSION = RELEASE.get("version", "")
SITE_URL = RELEASE.get("url") or "https://sheneset.vercel.app/"
OG_IMAGE = "image/og-image.png"          # 1200×630 の PNG（og:image に SVG は使えない）。scripts/make_og_image.py が作る

def og_tags(path, title, desc):
    """OGP と Twitter カードのタグ。Facebook などのクローラーは JS を実行しないので、静的な HTML として書く。
    og:title・og:description は、そのページの <title> と meta description と同じ内容にする（head_meta）。"""
    e = lambda s: html.escape(s, quote=True)
    return ('<meta property="og:type" content="website">'
            '<meta property="og:site_name" content="Sheneset">'
            f'<meta property="og:title" content="{e(title)}">'
            f'<meta property="og:description" content="{e(desc)}">'
            f'<meta property="og:url" content="{e(SITE_URL + path)}">'
            f'<meta property="og:image" content="{e(SITE_URL + OG_IMAGE)}">'
            '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            '<meta property="og:locale" content="ja_JP">'
            '<meta property="og:locale:alternate" content="en_US"><meta property="og:locale:alternate" content="fr_FR">'
            '<meta name="twitter:card" content="summary_large_image">')

def head_meta(path, title, desc):
    """<title>・meta description・OGP を、同じ題と説明でまとめて書く"""
    return (f"<title>{html.escape(title, quote=False)}</title>"
            f'<meta name="description" content="{html.escape(desc, quote=True)}">' + og_tags(path, title, desc))

# --- 文書カタログ -------------------------------------------------------------
# 形式: (ローマ数字, コーデックス番号, [(文書番号, 日本語題, 英語題, フランス語題, status), ...])
#   status:  A = 公開（LINKS のビュワーへリンク） / S = 準備中（tractate.html へリンク）
#            D = 暫定公開（自動注釈の全文。reader.html?doc=写本-番号 へリンク。本文は data/catalog.xml の
#                <bibl subtype="draft"> の TEI。人の目で確かめていないことを reader.html が文書ごとに示す）
#            U = 未注釈の全文（reader.html へリンク。本文は <bibl subtype="unannotated"> の TEI。品詞・語義なし）
#            D・U のリンク先の文書は、ふつうは同じ番号（写本-番号）。番号が違うものは READER_DOC に書く。
#   番号は通用の番号（data/catalog.xml・本文ビュワーと同じ）。一覧に出すが文書数に数えない行は UNCOUNTED に書く。
A = "avail"; S = "soon"; D = "draft"; U = "text"
CODICES = [
 ("I", 1, [
   (1, "使徒パウロの祈り", "The Prayer of the Apostle Paul", "Prière de l'apôtre Paul", S),
   (2, "ヤコブのアポクリュフォン(秘密の書)", "The Apocryphon of James", "Épître apocryphe de Jacques", D),
   (3, "真理の福音", "The Gospel of Truth", "Évangile de la Vérité", D),
   (4, "復活についての教え(レギノスへの手紙)", "The Treatise on the Resurrection", "Traité sur la résurrection", D),
   (5, "三部の教え", "The Tripartite Tractate", "Traité tripartite", D),
 ]),
 ("II", 2, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", "Livre des secrets de Jean", D),
   (2, "トマスによる福音書", "The Gospel of Thomas", "Évangile selon Thomas", D),
   (3, "フィリポによる福音書", "The Gospel of Philip", "Évangile selon Philippe", D),
   (4, "アルコーンの本質(支配者たちの本質)", "The Hypostasis of the Archons", "Hypostase des archontes", D),
   (5, "世界の起源について(無題文書)", "On the Origin of the World", "Écrit sans titre (L'Origine du monde)", D),
   (6, "魂の解明", "The Exegesis on the Soul", "Exégèse de l'âme", D),
   (7, "闘技者トマスの書", "The Book of Thomas the Contender", "Livre de Thomas", D),
 ]),
 ("III", 3, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", "Livre des secrets de Jean", D),
   (2, "エジプト人の福音書(聖なる不可視の霊の書)", "The Gospel of the Egyptians", "Livre sacré du Grand Esprit invisible (Évangile des Égyptiens)", D),
   (3, "祝福されたエウグノストス", "Eugnostos the Blessed", "Eugnoste le Bienheureux", A),
   (4, "イエス・キリストの知恵(ソフィア)", "The Sophia of Jesus Christ", "Sagesse de Jésus-Christ", D),
   (5, "救い主の対話", "The Dialogue of the Savior", "Dialogue du Sauveur", D),
 ]),
 ("IV", 4, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", "Livre des secrets de Jean", D),
   (2, "エジプト人の福音書", "The Gospel of the Egyptians", "Évangile des Égyptiens", D),
 ]),
 ("V", 5, [
   # III,3 は末尾標題「祝福されたエウグノストス」、V,1 は標題「エウグノストス」のみが残る。
   # V,1 は、人の手の注釈がまだ無い（eugnostos.html の V,1 は III,3 と対応づけた枠だけ）ので、全文テキストの
   # 自動注釈の暫定版（2026-11-24 に Coptic SCRIPTORIUM の NLP で付けたもの）として、本文ビュワーへリンクする
   (1, "エウグノストス", "Eugnostos", "Eugnoste", D),
   (2, "パウロの黙示録", "The Apocalypse of Paul", "Apocalypse de Paul", D),
   (3, "ヤコブの黙示録(第一)", "The (First) Apocalypse of James", "Première apocalypse de Jacques", D),
   (4, "ヤコブの黙示録(第二)", "The (Second) Apocalypse of James", "Seconde apocalypse de Jacques", D),
   (5, "アダムの黙示録", "The Apocalypse of Adam", "Apocalypse d'Adam", D),
 ]),
 ("VI", 6, [
   (1, "ペテロと十二使徒の行伝", "The Acts of Peter and the Twelve Apostles", "Actes de Pierre et des douze apôtres", D),
   (2, "雷・全きヌース(完全なる心)", "The Thunder, Perfect Mind", "Le Tonnerre, intellect parfait", D),
   (3, "権威ある教え", "Authoritative Teaching", "Authentikos Logos", D),
   (4, "われらの大いなる力の概念", "The Concept of Our Great Power", "Le Concept de notre grande puissance", D),
   (5, "プラトン『国家』588b–589b", "Plato, Republic 588b–589b", "Platon, République 588b–589b", A),
   (6, "第八と第九についての講話", "The Discourse on the Eighth and Ninth", "L'Ogdoade et l'Ennéade", D),
   (7, "感謝の祈り", "The Prayer of Thanksgiving", "Prière d'action de grâces", D),
   ("7a", "書記による覚書", "Scribal Note", "Note du scribe", D),   # VI,7 の末尾の覚え書き。文書数には数えない（UNCOUNTED）
   (8, "アスクレピオス 21–29", "Asclepius 21–29", "Asclépius 21–29", D),
 ]),
 ("VII", 7, [
   (1, "セームの釈義(パラフレイズ)", "The Paraphrase of Shem", "Paraphrase de Sem", D),
   (2, "大セツの第二の教え", "The Second Treatise of the Great Seth", "Deuxième traité du Grand Seth", D),
   (3, "ペテロの黙示録", "The Apocalypse of Peter", "Apocalypse de Pierre", D),
   (4, "シルワノスの教え", "The Teachings of Silvanus", "Les Leçons de Silvanos", D),
   (5, "セツの三つの碑", "The Three Steles of Seth", "Les Trois Stèles de Seth", D),
 ]),
 ("VIII", 8, [
   (1, "ゾストリアノス", "Zostrianos", "Zostrien", D),
   (2, "ペテロからフィリポへの手紙", "The Letter of Peter to Philip", "Lettre de Pierre à Philippe", D),
 ]),
 ("IX", 9, [
   (1, "メルキゼデク", "Melchizedek", "Melchisédek", D),
   (2, "ノレアの思想", "The Thought of Norea", "Noréa", D),
   (3, "真理の証言", "The Testimony of Truth", "Le Témoignage véritable", D),
 ]),
 ("X", 10, [
   (1, "マルサネス", "Marsanes", "Marsanès", D),
 ]),
 ("XI", 11, [
   (1, "認識の解明", "The Interpretation of Knowledge", "Interprétation de la gnose", D),
   (2, "ヴァレンティノス派の講解", "A Valentinian Exposition", "Exposé valentinien", D),
   (3, "アロゲネス", "Allogenes", "Allogène", D),
   (4, "ヒュプシフロネ", "Hypsiphrone", "Hypsiphroné", D),
 ]),
 ("XII", 12, [
   (1, "セクストスの金言", "The Sentences of Sextus", "Sentences de Sextus", D),
   (2, "真理の福音(断片)", "The Gospel of Truth (fragments)", "Évangile de la Vérité (fragments)", D),
   (3, "断片", "Fragments", "Fragments", D),
 ]),
 ("XIII", 13, [
   (1, "三形態の原初思想(トリモルフォス・プロテンノイア)", "Trimorphic Protennoia", "Prôtennoia trimorphe", D),
   (2, "世界の起源について(冒頭部)", "On the Origin of the World (excerpt)", "Écrit sans titre (extrait)", D),
 ]),
]

# 公開文書のリンク先（status A の行）
LINKS = {
    ("III", 3): "eugnostos.html?wit=III",
    ("VI", 5):  "republic.html",
}

def esc(s): return html.escape(str(s), quote=True)
def tid(roman, num): return f"{roman}-{num}"
def locus(roman, num): return f"NHC&nbsp;{roman},{num}"
# 全文テキスト（source/nhc_fulltext_split/）に同じ番号の文書が無い行（status D・U）のリンク先。
# 書記の覚書（VI,7a）は、全文テキストでは VI,7『感謝の祈り』の末尾の奥書（<ab type="colophon">）にある。
READER_DOC = {
    ("VI", "7a"): "VI-7#seg-VI-7508309",
}
# 一覧に出すが、文書数（全体・status ごと・写本ごと）に数えない行。書記の覚書は独立した文書ではないので数えない
# （標準の数え方では NHC は 52 文書。gnosticism.html の「重複を数えると 52」と同じ）。
UNCOUNTED = {("VI", "7a")}
def href_for(roman, num, status):
    if status == A and (roman, num) in LINKS: return LINKS[(roman, num)]
    if status in (D, U): return "reader.html?doc=" + READER_DOC.get((roman, num), tid(roman, num))
    return f"tractate.html?id={tid(roman,num)}"
def tri(ja, en, fr):
    """三言語のスパン（site.css が html[data-lang] に応じて出し分ける）"""
    return f'<span class="l-ja">{ja}</span><span class="l-en">{en}</span><span class="l-fr">{fr}</span>'

# 文書数。status ごとの数の和が全体の数と合わないとき（status の書き誤りなど）は、生成せずに止める
COUNTED = [x for r,_,t in CODICES for x in t if (r, x[0]) not in UNCOUNTED]
TOTAL = len(COUNTED)
AVAIL = sum(1 for x in COUNTED if x[4] == A)
DRAFT = sum(1 for x in COUNTED if x[4] == D)
PLAIN = sum(1 for x in COUNTED if x[4] == U)
SOON  = sum(1 for x in COUNTED if x[4] == S)
if AVAIL + DRAFT + PLAIN + SOON != TOTAL:
    raise SystemExit("build_site.py: 公開 %d + 暫定 %d + 未注釈 %d + 準備中 %d が全 %d 文書と合いません（CODICES の status を確かめてください）"
                     % (AVAIL, DRAFT, PLAIN, SOON, TOTAL))
TODAY = datetime.date.today().isoformat()

# --- shared head / theme ----------------------------------------------------
def _icon_links():
    """image/icon.svg（と任意で image/favicon-32.png）からファビコンを data URI で生成。"""
    import base64, urllib.parse
    links = []
    svgp = os.path.join(OUTDIR, "image", "icon.svg")
    if os.path.exists(svgp):
        svg = " ".join(open(svgp, encoding="utf-8").read().split())
        uri = "data:image/svg+xml," + urllib.parse.quote(svg, safe="=:/ '(),.-")
        links.append('<link rel="icon" type="image/svg+xml" href="%s">' % uri.replace('"', "%22"))
    pngp = os.path.join(OUTDIR, "image", "favicon-32.png")
    if os.path.exists(pngp):
        b64 = base64.b64encode(open(pngp, "rb").read()).decode()
        links.append('<link rel="alternate icon" type="image/png" sizes="32x32" '
                     'href="data:image/png;base64,%s">' % b64)
    links.append('<link rel="apple-touch-icon" href="image/apple-touch-icon.png">')
    return "".join(links)

FONTS = (_icon_links() +
 '<link rel="preconnect" href="https://fonts.googleapis.com">'
 '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
 '<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600&'
 'family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400;1,8..60,500&'
 'family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&'
 'family=IBM+Plex+Mono:wght@400;500&'
 'family=Inter:wght@400;500;600&family=Noto+Sans+JP:wght@400;500;700&'
 'family=Noto+Serif+JP:wght@500;600&family=Noto+Sans+Coptic&display=swap" rel="stylesheet">'
 # 宇宙テーマ(cosmos) → サイト共通レイヤー(site: 上部ナビ・三言語) → コミュニティ機能
 '<link rel="stylesheet" href="assets/cosmos.css">'
 '<link rel="stylesheet" href="assets/site.css">'
 '<link rel="stylesheet" href="assets/community.css">'
 '<script defer src="assets/cosmos.js"></script>'
 '<script defer src="assets/site.js"></script>'
 '<script defer src="assets/analytics.js"></script>'
 '<script defer src="assets/community-config.js"></script>'
 '<script defer src="assets/community.js"></script>')

# 表示モード（ライト／ダーク）に対応するページの <head> に入れる1行スクリプト。
# 保存値（localStorage "nhc-mode"。保存するのは assets/site.js）を描画前に反映して、ちらつきを防ぐ。
# 対応ページは <html data-mode="dark" data-modes="light dark"> とする（切替ボタンは site.js がナビに出す）。
MODE_BOOT = ('<script>/* 表示モード（ライト／ダーク）の保存値を描画前に反映（保存は assets/site.js） */'
             'try{if(localStorage.getItem("nhc-mode")==="light")'
             'document.documentElement.setAttribute("data-mode","light")}catch(e){}</script>')

# 表示言語を描画前に反映する 1 行スクリプト（日本語が一瞬出るのを防ぐ）。決め方は URL の ?lang=（ja・en・fr）＞ 保存値
# （localStorage "nhc-lang"）＞ ブラウザーの言語（どれにも当たらなければ英語）。正式な処理（URL の言語の保存など）は
# assets/site.js の initialLang。三言語のページ（data-i18n="full"）は html[data-lang] を、日英だけのビュワーは
# data-lang（ja / en）と語釈・対訳の言語（data-gl・data-tl）を設定する。手作業管理のページの <head> にも同じ文字列を入れてある。
LANG_BOOT = ('<script>/* 表示言語（?lang= ＞ 保存値 ＞ ブラウザーの言語、ほかは英語）を描画前に反映（正式な処理と保存は assets/site.js） */'
             '(function(H){var L=["ja","en","fr"],m=/[?&]lang=([^&#]*)/i.exec(location.search),v=m?m[1].toLowerCase():null;'
             'if(L.indexOf(v)<0){v=null;try{v=localStorage.getItem("nhc-lang")}catch(e){}}'
             'if(L.indexOf(v)<0){v="en";var n=navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language||""];'
             'for(var i=0;i<n.length;i++){var p=String(n[i]).toLowerCase().split(/[-_]/)[0];if(L.indexOf(p)>=0){v=p;break}}}'
             'if(H.getAttribute("data-i18n")==="full"){H.setAttribute("data-lang",v);H.setAttribute("lang",v)}'
             'else if(v!=="ja"){H.setAttribute("data-lang","en");H.setAttribute("lang","en");H.setAttribute("data-gl",v);H.setAttribute("data-tl",v)}'
             '})(document.documentElement)</script>')

THEME = """
:root{
 --bg:#f0ece3; --panel:#f8f6f0; --panel-2:#efebe1;
 --ink:#1a2030; --ink-soft:#3d4658; --ink-faint:#5c6578;
 --chrome:#1c2644; --chrome-ink:#ece6da; --chrome-faint:#8f9bb0;
 --gold:#8a6a2e; --gold-soft:#8a6a2e; --lapis:#2f4a7a; --rose:#9b4a3d;
 --line:#ddd6c8; --line-2:rgba(255,255,255,.14); --hi:#ebe5d8;
 --disp:'Source Serif 4','Noto Serif JP',Georgia,serif; --ui:'DM Sans','Inter','Noto Sans JP',system-ui,sans-serif;
 --jp:'Noto Sans JP',sans-serif; --jpser:'Noto Serif JP',serif; --cop:'Noto Sans Coptic',serif;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg); color:var(--ink); font-family:var(--ui);
 -webkit-font-smoothing:antialiased; line-height:1.6; animation:fade .5s ease both}
@keyframes fade{from{opacity:0; transform:translateY(4px)} to{opacity:1; transform:none}}
@media (prefers-reduced-motion:reduce){ body{animation:none} }
@view-transition{ navigation:auto; }
a{color:inherit}
.cop{font-family:var(--cop)}
.wrap{max-width:1180px; margin:0 auto; padding:0 clamp(16px,4vw,40px)}
"""

# --- index.html -------------------------------------------------------------
def codex_block(roman, no, tracts):
    rows=[]
    for num, ja, en, fr, status in tracts:
        on = status == A
        cls = "trow" + (" on" if on else " draft" if status == D else " plain" if status == U else "")
        pill = (f'<span class="pill on">{tri("公開","Online","En ligne")}</span>' if on
                else f'<span class="pill draft">{tri("暫定","Draft","Provisoire")}</span>' if status == D
                else f'<span class="pill plain">{tri("未注釈","Text only","Texte seul")}</span>' if status == U
                else f'<span class="pill">{tri("準備中","Soon","À venir")}</span>')
        search = esc((ja+" "+en+" "+fr).lower())
        rows.append(
          f'<a class="{cls}" href="{href_for(roman,num,status)}" data-s="{search}">'
          f'<span class="tn">{num}</span>'
          f'<span class="tt">'
          f'<span class="main">{tri(esc(ja), esc(en), esc(fr))}</span>'
          f'<span class="sub">{tri(esc(en), esc(ja), esc(en))}</span></span>'
          f'<span class="loc">{locus(roman,num)}</span>{pill}'
          f'<span class="arr">→</span></a>')
    n = sum(1 for x in tracts if (roman, x[0]) not in UNCOUNTED)
    count = tri(f"{n} 文書", f"{n} tractate{'s' if n>1 else ''}", f"{n} traité{'s' if n>1 else ''}")
    return (f'<section class="codex" data-codex="{roman}">'
            f'<div class="chead"><span class="rn">{roman}</span>'
            f'<div class="ct"><b>Codex {roman}</b><small>NHC&nbsp;{roman} · {count}</small></div></div>'
            f'<div class="tlist">{"".join(rows)}</div></section>')

INDEX_CSS = """
.hero{padding:clamp(34px,7vw,76px) 0 18px; display:grid;
 grid-template-columns:minmax(0,1fr) auto; gap:30px; align-items:center}
.hero-fig{width:clamp(150px,20vw,240px); aspect-ratio:1; border-radius:0;
 object-fit:cover; object-position:center 24%; border:1px solid rgba(200,168,112,.55);
 box-shadow:10px 10px 0 -1px rgba(200,168,112,.16)}
@media(max-width:680px){ .hero{grid-template-columns:1fr} .hero-fig{display:none} }
/* キッカー: 等幅の大文字＋左に金の短い罫 */
.eyebrow{font-family:var(--mono); font-weight:500; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-faint)}
.eyebrow::before{content:""; display:inline-block; width:28px; height:1px; margin-right:10px; vertical-align:.3em; background:var(--gold)}
.hero h1{font-family:var(--disp); font-weight:600; line-height:1.1; margin:.32em 0 .16em;
 font-size:clamp(2.5rem,6vw,4rem); letter-spacing:-.01em}
.hero h1 .cop{display:block; font-size:.5em; color:var(--gold); letter-spacing:.04em; margin-bottom:.18em}
.hero h1 .tag{display:block; font-size:.4em; font-weight:500; color:var(--ink-soft); letter-spacing:.02em; margin-top:.45em}
html[data-lang="ja"] .hero h1 .l-ja{font-family:'Noto Serif JP',serif; letter-spacing:.02em}
.hero .lead{max-width:64ch; color:var(--ink-soft); font-size:1.02rem; line-height:1.8}
.hero .lead b{color:var(--ink)}
.hero .more{display:flex; flex-wrap:wrap; gap:6px 22px; margin-top:14px; font-size:.86rem}
.hero .more a{color:var(--gold-bright,var(--gold)); text-decoration:none; text-underline-offset:5px}
.hero .more a:hover{text-decoration:underline}

/* 節の見出し: 上に細い罫、頭に等幅の通し番号（01, 02 …）を金で */
body{counter-reset:sec}
.sec-h{display:flex; align-items:baseline; gap:12px; margin:46px 0 14px; padding-top:14px;
 border-top:1px solid var(--line-2); counter-increment:sec}
.sec-h h2{font-family:var(--disp); font-weight:600; letter-spacing:0; font-size:1.4rem; color:var(--ink); margin:0}
.sec-h h2::before{content:counter(sec,decimal-leading-zero); font-family:var(--mono); font-size:.62em; font-weight:400;
 color:var(--gold); letter-spacing:.08em; margin-right:.9em; vertical-align:.18em}
.sec-h small{font-family:var(--mono); color:var(--ink-faint); font-size:.74rem; letter-spacing:.06em}
.sec-h .rule{display:none}

.features{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr)); gap:14px}
/* カード: 角丸の箱にせず、細い枠と上辺の金の罫だけで区切る */
.feat{display:grid; grid-template-columns:minmax(0,1fr); gap:18px; align-items:center;
 background:var(--panel); border:1px solid var(--line); border-top-color:var(--gold); border-radius:0; padding:16px 20px}
.feat .k{font-family:var(--mono); font-weight:500; font-size:.7rem; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-faint)}
.feat .k::before{content:""; display:inline-block; width:28px; height:1px; margin-right:10px; vertical-align:.3em; background:var(--gold)}
.feat .ttl{font-family:var(--disp); font-weight:600; font-size:1.16rem; margin:2px 0 3px}
.feat .ttl .cop{color:var(--gold-soft); margin-right:.35em}
.feat .loc{font-size:.76rem; color:var(--ink-faint); line-height:1.6}
.feat .acts{display:flex; gap:6px 18px; margin-top:10px; flex-wrap:wrap; font-size:.8rem}
.feat .acts a{text-decoration:none; color:var(--ink-soft); text-underline-offset:5px}
.feat .acts a:hover{text-decoration:underline; text-decoration-color:var(--gold); color:var(--ink)}
.feat .acts a.go{color:var(--gold-bright,var(--gold)); font-weight:600}

.two{display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); gap:0 34px}
@media(max-width:860px){ .two{grid-template-columns:1fr} }
.news{list-style:none; margin:0; padding:0}
.news li{display:grid; grid-template-columns:7.2em minmax(0,1fr); gap:14px; padding:12px 0;
 border-bottom:1px solid var(--line)}
.news li[hidden]{display:none}
.news time{font-family:var(--mono); color:var(--gold); font-variant-numeric:tabular-nums; font-size:.78rem; letter-spacing:.02em}
.news .tx{color:var(--ink-soft); font-size:.88rem; line-height:1.7}
.news .tx b{color:var(--ink)}
.news .tx a{color:var(--lapis)}
.news .more-news{background:none; border:0; color:var(--ink-faint); cursor:pointer; padding:10px 0; font:inherit; font-size:.8rem;
 text-underline-offset:5px}
.news .more-news:hover{text-decoration:underline}
.relsite{display:block; text-decoration:none; background:var(--panel); border:1px solid var(--line); border-top-color:var(--gold);
 border-radius:0; padding:18px 20px; margin-bottom:12px; transition:border-color .15s}
.relsite:hover{border-color:var(--gold)}
.relsite .k{font-family:var(--mono); font-weight:500; font-size:.68rem; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-faint)}
.relsite .t{font-family:var(--disp); font-weight:600; font-size:1.12rem; margin:4px 0 2px; color:var(--ink)}
.relsite .t .cop{color:var(--gold-soft); margin-right:.3em}
.relsite .u{font-size:.72rem; color:var(--ink-faint)}
.relsite p{font-size:.84rem; color:var(--ink-soft); line-height:1.7; margin:8px 0 0}
.relsite .go{display:inline-block; margin-top:8px; font-size:.8rem; color:var(--gold-bright,var(--gold))}
.relsite:hover .go{text-decoration:underline}

.ctool{display:flex; align-items:center; gap:10px; margin:0 0 16px; padding:8px 0;
 border-bottom:1px solid var(--line)}
.ctool svg{width:16px; height:16px; color:var(--ink-faint); flex:none}
.ctool input{flex:1; min-width:0; background:none; border:0; outline:0; color:var(--ink); font-family:var(--ui); font-size:.92rem}
.ctool input::placeholder{color:var(--ink-faint)}
.ctool .cnt{font-size:.74rem; color:var(--ink-faint); white-space:nowrap}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(min(370px,100%),1fr)); gap:18px; padding-bottom:30px}
.codex{background:var(--panel); border:1px solid var(--line); border-top-color:var(--gold); border-radius:0; overflow:hidden;
 display:flex; flex-direction:column}
.chead{display:flex; align-items:center; gap:12px; padding:14px 16px 10px}
.chead .rn{font-family:var(--disp); font-style:italic; font-size:2.2rem; font-weight:400; color:var(--gold);
 min-width:1.6em; text-align:center; line-height:1}
.chead .ct b{font-family:var(--disp); font-weight:600; font-size:1.04rem}
.chead .ct small{display:block; font-family:var(--mono); color:var(--ink-faint); font-size:.7rem; letter-spacing:.04em}
.tlist{display:flex; flex-direction:column; padding:4px 8px 10px}
.trow{display:grid; grid-template-columns:auto 1fr auto auto auto; align-items:center; gap:10px;
 padding:9px 10px; border-radius:0; border-bottom:1px solid var(--line); text-decoration:none; color:inherit; transition:background .12s}
.trow:last-child{border-bottom:0}
.trow:hover{background:var(--panel-2)}
.trow .tn{font-family:var(--disp); color:var(--ink-faint); font-size:.92rem; min-width:1.4em; text-align:center}
.trow .tt{min-width:0}
.trow .tt .main{display:block; font-size:.92rem; font-weight:500; color:var(--ink)}
html[data-lang="ja"] .trow .tt .main{font-family:var(--jp)}
html[data-lang="en"] .trow .tt .main, html[data-lang="fr"] .trow .tt .main{font-family:var(--disp); font-size:.98rem}
.trow .tt .sub{display:block; font-family:var(--disp); font-style:italic; font-size:.78rem; color:var(--ink-faint)}
html[data-lang="en"] .trow .tt .sub{font-family:var(--jp); font-style:normal; font-size:.74rem}
.trow .loc{font-family:var(--mono); font-size:.68rem; color:var(--ink-faint); white-space:nowrap; font-variant-numeric:tabular-nums}
/* 状態の札: 角のない四角、等幅の大文字 */
.pill{font-family:var(--mono); font-size:.64rem; letter-spacing:.06em; text-transform:uppercase; padding:3px 8px; border-radius:0;
 background:transparent; color:var(--ink-faint); border:1px solid var(--line-2); white-space:nowrap}
.pill.on{background:var(--gold); color:var(--on-gold); border-color:var(--gold); font-weight:500}
.pill.draft{background:transparent; color:var(--lapis); border-color:var(--lapis); font-weight:500}
.pill.plain{background:transparent; color:var(--ink-soft); border-color:var(--ink-faint)}
.legend{display:flex; flex-wrap:wrap; gap:6px 18px; margin:-6px 0 14px; font-size:.76rem; color:var(--ink-faint); line-height:1.7}
.legend .pill{margin-right:6px}
.trow .arr{color:var(--ink-faint); opacity:0; transition:opacity .12s, transform .12s; transform:translateX(-3px)}
.trow:hover .arr{opacity:1; transform:none}
.trow.on{outline:1px solid rgba(138,106,46,.28)}
.trow.on:hover{background:var(--hi)}
.empty{grid-column:1/-1; text-align:center; color:var(--ink-faint); padding:40px}
footer{position:relative; z-index:1; border-top:1px solid var(--line); color:var(--ink-faint); font-size:.78rem; padding:22px 0 50px; margin-top:30px}
footer .wrap{display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center}
footer b{color:var(--ink-soft)}
footer a{color:var(--ink-soft); text-decoration:none; text-underline-offset:4px}
footer a:hover{text-decoration:underline}
@media(max-width:520px){ .trow{grid-template-columns:auto 1fr auto; } .trow .loc,.trow .arr{display:none} }
section[id]{scroll-margin-top:70px}

/* ---- ライトモード（html[data-mode="light"]）での調整。配色そのものは assets/cosmos.css ---- */
html[data-mode="light"] .hero-fig{background:radial-gradient(circle at 50% 38%,#2a3870,#1c2644 72%);
 border-color:rgba(122,92,30,.55); box-shadow:10px 10px 0 -1px rgba(122,92,30,.18)}
html[data-mode="light"] .feat, html[data-mode="light"] .codex, html[data-mode="light"] .relsite{
 box-shadow:0 1px 2px rgba(20,28,50,.05)}
"""

# --- NEWS と関連サイト（data/news.json・data/links.json）を、index.html の JS と同じ形の HTML にする ----------
# JS を動かさない読み手（リンクのプレビュー、一部の検索エンジン、リーダー表示など）にも見えるように、生成のときに書き込む。
# ページを開いたときは JS が JSON を読み直し、内容が違えば（生成のあとで JSON を直したとき）書き換える。
# 下の _esc・_tri・NEWS_SHOW と HTML の形は、build_index の <script> の esc・tri・SHOW と同じにしておくこと。
NEWS_SHOW = 6          # 最初に出す件数（それより古いものは〈過去の更新をすべて表示〉で出す）

def _load_json(rel):
    with open(os.path.join(OUTDIR, rel), encoding="utf-8") as f:
        return json.load(f)

def _esc(s):
    """JS の esc() と同じ（& < > " を文字参照に）"""
    return str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def _tri(o):
    """JS の tri() と同じ（その言語が無ければ英語、次に日本語）。中身は HTML のまま"""
    return "".join('<span class="l-%s">%s</span>' % (l, o.get(l) or o.get("en") or o.get("ja") or "") for l in ("ja", "en", "fr"))

def news_html():
    items = sorted(_load_json("data/news.json").get("items", []), key=lambda it: it.get("date") or "", reverse=True)
    lis = "".join('<li' + (' class="old" hidden' if i >= NEWS_SHOW else '') + '><time datetime="' + _esc(it.get("date")) + '">' +
                  _esc(it.get("date")) + '</time><span class="tx">' + _tri({"ja": it.get("ja"), "en": it.get("en"), "fr": it.get("fr")}) +
                  (' <a href="' + _esc(it["link"]) + '">→</a>' if it.get("link") else '') + '</span></li>'
                  for i, it in enumerate(items))
    more = ('<li style="display:block;border:0"><button class="more-news" id="moreNews">' +
            _tri({"ja": "過去の更新をすべて表示", "en": "Show all updates", "fr": "Afficher toutes les mises à jour"}) + '</button></li>'
            if len(items) > NEWS_SHOW else '')
    return lis + more

def links_html():
    from urllib.parse import urlsplit
    out = []
    for it in _load_json("data/links.json").get("items", []):
        host = urlsplit(it.get("url") or "").netloc
        out.append('<a class="relsite" href="' + _esc(it.get("url")) + '" target="_blank" rel="noopener">' +
                   '<div class="k">' + _tri(it.get("kind") or {}) + '</div>' +
                   '<div class="t">' + ('<span class="cop" lang="cop">' + _esc(it["cop"]) + '</span>' if it.get("cop") else '') + _tri(it.get("title") or {}) + '</div>' +
                   '<div class="u">' + _esc(host) + '</div>' +
                   '<p>' + _tri(it.get("desc") or {}) + '</p>' +
                   '<span class="go">' + _tri({"ja": "サイトを開く ↗", "en": "Visit site ↗", "fr": "Visiter le site ↗"}) + '</span></a>')
    return "".join(out)

def build_index():
    blocks = "\n".join(codex_block(r,n,t) for r,n,t in CODICES)
    # 未注釈（status U）の文書が無いときは、件数・凡例・フッターに「未注釈」を出さない（2026-11-24 から 0 件）
    pl_ja, pl_en, pl_fr = (f" · 未注釈 {PLAIN}", f" · {PLAIN} text only", f" · {PLAIN} texte seul") if PLAIN else ("", "", "")
    pl_legend = (f'   <span><span class="pill plain">{tri("未注釈","Text only","Texte seul")}</span>'
                 f'{tri("本文だけの作業用テキスト。品詞・語義なし・校訂本と未照合", "working text only, no annotation, not collated", "texte de travail seul, sans annotation ni collation")}</span>\n') if PLAIN else ""
    pl_foot_ja, pl_foot_en, pl_foot_fr = ((f"<b>{PLAIN}</b>&nbsp;文書は未注釈の本文・", f", <b>{PLAIN}</b>&nbsp;as text only and ",
                                            f", <b>{PLAIN}</b>&nbsp;en texte seul et ") if PLAIN else ("", " and ", " et "))
    news, rel = news_html(), links_html()
    body = f"""
<nav id="sitebar" class="sitebar sticky"></nav>

<main class="wrap">
 <section class="hero">
  <div>
   <div class="eyebrow">Nag Hammadi Codices I–XIII</div>
   <h1><span class="cop" lang="cop">ϣⲉⲛⲉⲥⲏⲧ</span>Sheneset<span class="tag">{tri("ナグ・ハマディ写本コーパス", "A digital TEI edition of the Nag Hammadi Codices", "Édition numérique TEI des codices de Nag Hammadi")}</span></h1>
   <p class="lead">{tri(
     f"ナグ・ハマディ写本(全13冊・{TOTAL}文書)を、<b>形態素グロス・コプト語辞書・日英仏訳</b>を備えた TEI&nbsp;P5 デジタル版として整備するプロジェクトです。各語をクリックすると語義が表示され、写本どうしの対照や、他の文書の並行箇所の参照ができます。",
     f"A digital TEI&nbsp;P5 edition of the Nag Hammadi Codices (13 codices, {TOTAL} tractates), with <b>morpheme-level glosses, a Coptic lexicon and Japanese, English and French translations</b>. Click any word for its sense, compare the manuscript witnesses side by side and follow parallel passages into other texts.",
     f"Une édition numérique TEI&nbsp;P5 des codices de Nag Hammadi (13 codices, {TOTAL} traités), avec <b>gloses morphologiques, lexique copte et traductions japonaise, anglaise et française</b>. Cliquez sur un mot pour en voir le sens, comparez les témoins manuscrits et suivez les passages parallèles dans d’autres textes.")}</p>
   <div class="more">
     <a href="guide.html">{tri("はじめての方へ →", "Getting started →", "Premiers pas →")}</a>
     <a href="gnosticism.html">{tri("グノーシス主義とは →", "What is Gnosticism? →", "Qu'est-ce que le gnosticisme ? →")}</a>
     <a href="project.html">{tri("このプロジェクトについて →", "About the project →", "À propos du projet →")}</a>
     <a href="#corpus">{tri("文書一覧へ ↓", "Browse the codices ↓", "Parcourir les codices ↓")}</a>
   </div>
   <form class="qbox" action="search.html" method="get" role="search" aria-label="全文書を検索 / Search all texts">
    <input type="hidden" name="scope" value="all">
    <input class="qbox-q" name="q" type="search" required autocomplete="off" spellcheck="false" data-ph-label
      data-ph-ja="全文書の本文をコプト語で検索（例: ⲛⲟⲩⲧⲉ）" data-ph-en="Search the Coptic text of all documents (e.g. ⲛⲟⲩⲧⲉ)" data-ph-fr="Chercher dans le texte copte de tous les documents (p. ex. ⲛⲟⲩⲧⲉ)">
    <span class="qbox-f">
     <label><input type="radio" name="f" value="f" checked>{tri("語形", "Word form", "Forme")}</label>
     <label><input type="radio" name="f" value="l">{tri("レンマ", "Lemma", "Lemme")}</label>
    </span>
    <button type="submit">{tri("検索", "Search", "Chercher")}</button>
   </form>
   <p class="qbox-note">{tri(
     "人の手で注釈した版と、全文テキスト（自動注釈の暫定版）のすべてを対象に、<a href='search.html'>コーパス検索</a>で探します。全文テキストは初めに読み込むので、少し時間がかかります。語の意味から引くときは<a href='lexicon.html'>辞書</a>へ。",
     "Searches the hand-annotated editions and all the full texts (automatic drafts) with the <a href='search.html'>corpus search</a>; the full texts are loaded first, which takes a moment. To look a word up by meaning, use the <a href='lexicon.html'>lexicon</a>.",
     "Recherche dans les éditions annotées à la main et dans tous les textes intégraux (brouillons automatiques) avec la <a href='search.html'>recherche du corpus</a> ; les textes intégraux sont d’abord chargés, ce qui prend un peu de temps. Pour chercher un mot par son sens, voir le <a href='lexicon.html'>lexique</a>.")}</p>
  </div>
  <img class="hero-fig" src="image/web/gengen_guide.svg" alt="" loading="lazy">
 </section>

 <div class="sec-h"><h2>{tri("公開中のテキスト", "Published texts", "Textes publiés")}</h2><span class="rule"></span></div>
 <div class="features">
   <div class="feat">
     <div>
       <div class="k">NHC III,3 / V,1</div>
       <div class="ttl"><span class="cop" lang="cop">ⲉⲩⲅⲛⲱⲥⲧⲟⲥ</span>{tri("エウグノストス", "Eugnostos", "Eugnoste")}</div>
       <div class="loc">{tri(
         "III,3『祝福されたエウグノストス』／ V,1『エウグノストス』· 二証本対照・三言語対訳",
         "III,3 <i>Eugnostos the Blessed</i> / V,1 <i>Eugnostos</i> · two witnesses, three translations",
         "III,3 <i>Eugnoste le Bienheureux</i> / V,1 <i>Eugnoste</i> · deux témoins, trois traductions")}</div>
       <div class="acts"><a class="go" href="eugnostos.html?wit=III">{tri("III,3 を読む →", "Read III,3 →", "Lire III,3 →")}</a>
        <a href="reader.html?doc=V-1">{tri("V,1 を読む（暫定版）", "Read V,1 (draft)", "Lire V,1 (provisoire)")}</a>
        <a href="eugnostos.html?wit=SYN">{tri("対照表示", "Synopsis", "Synopse")}</a>
        <a href="search.html?doc=eugnostos">{tri("検索", "Search", "Recherche")}</a>
        <a href="search.html?doc=eugnostos&amp;view=stats">{tri("統計", "Statistics", "Statistiques")}</a></div>
     </div>
   </div>
   <div class="feat">
     <div>
       <div class="k">NHC VI,5</div>
       <div class="ttl"><span class="cop" lang="cop">ⲡⲟⲗⲓⲧⲉⲓⲁ</span>{tri("プラトン『国家』588b–589b", "Plato, <i>Republic</i> 588b–589b", "Platon, <i>République</i> 588b–589b")}</div>
       <div class="loc">{tri("ギリシア語原文対照", "Greek parallel text", "Texte grec en regard")}</div>
       <div class="acts"><a class="go" href="republic.html">{tri("全文を読む →", "Read the text →", "Lire le texte →")}</a>
        <a href="search.html?doc=republic">{tri("検索", "Search", "Recherche")}</a>
        <a href="search.html?doc=republic&amp;view=stats">{tri("統計", "Statistics", "Statistiques")}</a></div>
     </div>
   </div>
   <div class="feat">
     <div>
       <div class="k">NHC I–IV · VII–XIII · {tri("暫定版", "draft", "provisoire")}</div>
       <div class="ttl"><span class="cop" lang="cop">ⲛϫⲱⲱⲙⲉ</span>{tri(f"全文テキスト {DRAFT} 文書", f"Full text of {DRAFT} tractates", f"Texte intégral de {DRAFT} traités")}</div>
       <div class="loc">{tri(
         "語群・品詞・レンマ・語義を自動で付けた暫定版です。人の目では確かめておらず、本文も校訂本と照合していません。確かめていないことは各文書の冒頭に記しています。",
         "A draft with bound groups, parts of speech, lemmata and glosses assigned automatically. Nothing has been checked by hand and the text has not been collated with the editions; each text lists what is unchecked at the top.",
         "Version provisoire : groupes, parties du discours, lemmes et gloses attribués automatiquement. Rien n’a été vérifié et le texte n’a pas été collationné avec les éditions ; chaque texte indique en tête ce qui reste à vérifier.")}</div>
       <div class="acts"><a class="go" href="#corpus">{tri("文書一覧から選ぶ ↓", "Choose from the list ↓", "Choisir dans la liste ↓")}</a>
        <a href="reader.html?doc=III-4">{tri("例：イエス・キリストの知恵", "e.g. the Sophia of Jesus Christ", "p. ex. la Sagesse de Jésus-Christ")}</a>
        <a href="search.html">{tri("検索（〈全文テキスト〉）", "Search (“Full text”)", "Recherche (« Texte intégral »)")}</a></div>
     </div>
   </div>
 </div>

 <div class="two">
  <section id="news">
   <div class="sec-h"><h2>News</h2><small>{tri("サイトの更新情報", "Site updates", "Mises à jour du site")}</small><span class="rule"></span></div>
   <ul class="news" id="newsList">{news}</ul>
  </section>
  <section id="related">
   <div class="sec-h"><h2>{tri("関連サイト", "Related", "Sites liés")}</h2><span class="rule"></span></div>
   <div id="relList">{rel}</div>
  </section>
 </div>

 <section id="corpus">
  <div class="sec-h"><h2>{tri("文書一覧", "The codices", "Les codices")}</h2><small>NHC I–XIII</small><span class="rule"></span></div>
  <div class="ctool"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
   <input id="q" type="search" autocomplete="off">
   <span class="cnt">{tri(f"公開 {AVAIL} · 暫定 {DRAFT}{pl_ja} · 準備中 {SOON} / 全 {TOTAL} 文書", f"{AVAIL} online · {DRAFT} draft{pl_en} · {SOON} soon · {TOTAL} in all", f"{AVAIL} en ligne · {DRAFT} provisoires{pl_fr} · {SOON} à venir · {TOTAL} au total")}</span></div>
  <p class="legend">
   <span><span class="pill on">{tri("公開","Online","En ligne")}</span>{tri("人の手で注釈・訳を付けた版", "annotated and translated by hand", "annoté et traduit à la main")}</span>
   <span><span class="pill draft">{tri("暫定","Draft","Provisoire")}</span>{tri("自動注釈の全文。人の目で未確認・校訂本と未照合", "full text with automatic annotation, not checked or collated", "texte intégral annoté automatiquement, non vérifié ni collationné")}</span>
{pl_legend}   <span><span class="pill">{tri("準備中","Soon","À venir")}</span>{tri("本文はまだ表示できません", "text not yet available", "texte pas encore disponible")}</span>
  </p>
  <div class="grid" id="grid">
{blocks}
   <p class="empty" id="empty" hidden>{tri("該当する文書がありません。", "No matching tractate.", "Aucun traité ne correspond.")}</p>
  </div>
 </section>
</main>

<footer><div class="wrap">
  {tri(f"<b>{AVAIL}</b>&nbsp;文書を公開・<b>{DRAFT}</b>&nbsp;文書を暫定公開・{pl_foot_ja}<b>{SOON}</b>&nbsp;文書は準備中 / 全&nbsp;<b>{TOTAL}</b>&nbsp;文書(13写本)",
       f"<b>{AVAIL}</b>&nbsp;online, <b>{DRAFT}</b>&nbsp;as drafts{pl_foot_en}<b>{SOON}</b>&nbsp;in preparation, of&nbsp;<b>{TOTAL}</b>&nbsp;tractates (13 codices)",
       f"<b>{AVAIL}</b>&nbsp;en ligne, <b>{DRAFT}</b>&nbsp;provisoires{pl_foot_fr}<b>{SOON}</b>&nbsp;à venir sur&nbsp;<b>{TOTAL}</b> traités (13 codices)")}　·
  {tri("本文はパブリックドメイン、辞書・対訳は CC&nbsp;BY&nbsp;4.0",
       "Source texts: public domain · lexicon and translations: CC&nbsp;BY&nbsp;4.0",
       "Textes sources : domaine public · lexique et traductions : CC&nbsp;BY&nbsp;4.0")}　·
  <a href="project.html">{tri("プロジェクトについて", "About", "À propos")}</a>　·
  <a href="privacy.html">{tri("プライバシーポリシー", "Privacy", "Confidentialité")}</a>　·　
  <a href="terms.html">{tri("利用規約", "Terms", "Conditions")}</a>　·　
  <a href="https://github.com/icecocoasince2003-create/Nag-Hammadi-Library" target="_blank" rel="noopener">GitHub</a>　·
  {"v" + VERSION + " · " if VERSION else ""}{tri("生成", "built", "généré")} {TODAY}
</div></footer>

<script>
(function(){{
const H=document.documentElement;
const L=()=>H.getAttribute('data-lang')||'ja';
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const tri=o=>['ja','en','fr'].map(l=>'<span class="l-'+l+'">'+(o[l]||o.en||o.ja||'')+'</span>').join('');

/* ---- 文書名での絞り込み ---- */
const q=document.getElementById('q'), grid=document.getElementById('grid'), empty=document.getElementById('empty');
const PH={{ja:'文書名で絞り込み（日・英・仏）',en:'Filter by title (JA / EN / FR)',fr:'Filtrer par titre (JA / EN / FR)'}};
function ph(){{ q.placeholder=PH[L()]||PH.ja; q.setAttribute('aria-label',q.placeholder); }}
function filter(){{
  const v=(q.value||'').trim().toLowerCase(); let shown=0;
  grid.querySelectorAll('.codex').forEach(cx=>{{ let any=0;
    cx.querySelectorAll('.trow').forEach(r=>{{ const hit=!v||(r.dataset.s||'').includes(v);
      r.style.display=hit?'':'none'; if(hit) any++; }});
    cx.style.display=any?'':'none'; shown+=any; }});
  empty.hidden=shown>0;
}}
q.addEventListener('input',filter); ph();
document.addEventListener('nhc:lang',ph);

/* ---- NEWS（data/news.json）----
   build_site.py が生成のときに同じ形の HTML を書き込んである（JS を動かさない読み手にも見えるように）。
   ここでは JSON を読み直し、内容が違うとき（生成のあとで news.json を直したとき）だけ書き換える。読めなければ書き込んだ内容のまま。
   HTML の形と SHOW は build_site.py の news_html()・NEWS_SHOW と同じにしておくこと */
const SHOW={NEWS_SHOW};
const newsUl=document.getElementById('newsList');
/* 書き込んだ HTML が、いまの表示と同じかどうか（ブラウザーが組み立て直した形どうしで比べる） */
const sameHTML=(el,html)=>{{ const t=document.createElement(el.tagName); t.innerHTML=html; return t.innerHTML===el.innerHTML; }};
function wireMore(){{
  const mb=document.getElementById('moreNews');
  if(mb) mb.onclick=()=>{{ newsUl.querySelectorAll('li.old').forEach(x=>x.hidden=false); mb.parentNode.remove(); }};
}}
wireMore();
fetch('data/news.json',{{cache:'no-store'}}).then(r=>r.ok?r.json():Promise.reject(r.status)).then(d=>{{
  const items=(d.items||[]).slice().sort((a,b)=>(b.date||'').localeCompare(a.date||''));
  const li=(it,i)=>'<li'+(i>=SHOW?' class="old" hidden':'')+'><time datetime="'+esc(it.date)+'">'+esc(it.date)+'</time><span class="tx">'+
     tri({{ja:it.ja,en:it.en,fr:it.fr}})+(it.link?' <a href="'+esc(it.link)+'">→</a>':'')+'</span></li>';
  const html=items.map(li).join('')+(items.length>SHOW?'<li style="display:block;border:0"><button class="more-news" id="moreNews">'+tri({{ja:'過去の更新をすべて表示',en:'Show all updates',fr:'Afficher toutes les mises à jour'}})+'</button></li>':'');
  if(!sameHTML(newsUl,html)){{ newsUl.innerHTML=html; wireMore(); }}
}}).catch(()=>{{}});

/* ---- 関連サイト（data/links.json）。NEWS と同じく、書き込んである HTML と違うときだけ書き換える（build_site.py の links_html()）---- */
fetch('data/links.json',{{cache:'no-store'}}).then(r=>r.ok?r.json():Promise.reject(r.status)).then(d=>{{
  const relList=document.getElementById('relList');
  const html=(d.items||[]).map(it=>{{
    let host=''; try{{ host=new URL(it.url).host; }}catch(e){{}}
    return '<a class="relsite" href="'+esc(it.url)+'" target="_blank" rel="noopener">'+
      '<div class="k">'+tri(it.kind||{{}})+'</div>'+
      '<div class="t">'+(it.cop?'<span class="cop" lang="cop">'+esc(it.cop)+'</span>':'')+tri(it.title||{{}})+'</div>'+
      '<div class="u">'+esc(host)+'</div>'+
      '<p>'+tri(it.desc||{{}})+'</p>'+
      '<span class="go">'+tri({{ja:'サイトを開く ↗',en:'Visit site ↗',fr:'Visiter le site ↗'}})+'</span></a>';
  }}).join('');
  if(!sameHTML(relList,html)) relList.innerHTML=html;
}}).catch(()=>{{}});
}})();
</script>
"""
    return ("<!doctype html><html lang=\"ja\" data-lang=\"ja\" data-i18n=\"full\" data-mode=\"dark\" data-modes=\"light dark\""
            " data-title-en=\"Sheneset — a digital TEI edition of the Nag Hammadi Codices\""
            " data-title-fr=\"Sheneset — édition numérique TEI des codices de Nag Hammadi\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"{MODE_BOOT}{LANG_BOOT}"
            + head_meta("", "Sheneset — ナグ・ハマディ写本コーパス",
                        "ナグ・ハマディ写本のTEI P5デジタル版（コプト語本文・形態素グロス・辞書・注釈・日英仏訳）/ A digital TEI edition of the Nag Hammadi Codices.") +
            f"{FONTS}<style>{THEME}{INDEX_CSS}</style></head><body>{body}</body></html>")

# --- tractate.html (placeholder) -------------------------------------------
def build_tractate():
    cat = {}
    for roman, no, tracts in CODICES:
        for num, ja, en, fr, status in tracts:
            cat[tid(roman, num)] = {"ja": ja, "en": en, "fr": fr, "roman": roman, "num": num,
                                   "href": href_for(roman, num, status) if status in (A, D, U) else ""}
    css = THEME + """
.shell{position:relative; z-index:1; max-width:780px; margin:0 auto; padding:clamp(28px,6vw,64px) clamp(16px,4vw,40px) 80px}
.eyebrow{font-family:var(--mono); font-weight:500; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-faint)}
.eyebrow::before{content:""; display:inline-block; width:28px; height:1px; margin-right:10px; vertical-align:.3em; background:var(--gold)}
h1{font-family:var(--disp); font-weight:600; line-height:1.12; font-size:clamp(2rem,5.2vw,3rem); margin:.3em 0 .12em}
.alt{font-family:var(--disp); font-style:italic; color:var(--ink-faint); font-size:1.12rem}
.soon{display:inline-flex; align-items:center; gap:8px; margin-top:20px; background:var(--hi);
 border:1px solid var(--line); color:var(--ink-soft); border-radius:0; padding:7px 15px; font-size:.82rem}
.soon .dot{width:8px; height:8px; border-radius:50%; background:var(--gold)}
.card{margin-top:26px; background:var(--panel); border:1px solid var(--line); border-radius:2px; padding:22px 24px}
.card h2{font-family:var(--disp); font-weight:600; font-size:1.12rem; margin:0 0 12px}
.card p{color:var(--ink-soft); margin:0 0 14px; max-width:62ch}
.layers{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-top:6px}
.layer{background:var(--panel-2); border:1px solid var(--line); border-radius:2px; padding:12px 14px}
.layer b{display:block; font-size:.9rem}
.layer small{color:var(--ink-faint); font-size:.74rem}
.actions{display:flex; flex-wrap:wrap; gap:8px 24px; margin-top:26px; font-size:.9rem}
.actions a{text-decoration:none; color:var(--ink-soft); text-underline-offset:5px}
.actions a:hover{text-decoration:underline; text-decoration-color:var(--gold)}
.actions a.primary{color:var(--gold-bright,var(--gold)); font-weight:600}
.rail{display:flex; gap:6px; margin:22px 0 0; opacity:.5}
.rail i{height:5px; flex:1; border-radius:3px; background:linear-gradient(90deg,var(--gold-soft),var(--lapis))}
.notfound{color:var(--ink-faint)}
"""
    body = """
<nav id="sitebar" class="sitebar sticky"></nav>
<main class="shell" id="shell"><p class="notfound">…</p></main>
<script>
const CAT=__CATALOG__;
const H=document.documentElement;
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function tri(ja,en,fr){return '<span class="l-ja">'+ja+'</span><span class="l-en">'+en+'</span><span class="l-fr">'+fr+'</span>';}
const id=new URLSearchParams(location.search).get('id');
const t=CAT[id];
const shell=document.getElementById('shell');
if(!t){
  shell.innerHTML=`<div class="eyebrow">Nag Hammadi Codices</div>
   <h1>${tri('文書が見つかりません','Tractate not found','Traité introuvable')}</h1>
   <p class="notfound">${tri('指定の文書 ID','The tractate ID','L’identifiant')} <code>${esc(id||'—')}</code> ${tri('は見つかりませんでした。','was not found.','est introuvable.')}</p>
   <div class="actions"><a class="primary" href="index.html#corpus">${tri('← 文書一覧へ戻る','← Back to the codices','← Retour aux codices')}</a></div>`;
} else if(t.href){
  location.replace(t.href);
} else {
  const setTitle=()=>{ const l=H.getAttribute('data-lang')||'ja';
    document.title=(t[l]||t.ja)+' — '+({ja:'準備中',en:'in preparation',fr:'en préparation'}[l])+' · NHC '+t.roman+','+t.num; };
  setTitle(); document.addEventListener('nhc:lang',setTitle);
  shell.innerHTML=`
   <div class="eyebrow">Codex ${t.roman} · NHC&nbsp;${t.roman},${t.num}</div>
   <h1>${tri(esc(t.ja),esc(t.en),esc(t.fr))}</h1>
   <div class="alt">${tri(esc(t.en),esc(t.ja),esc(t.en))}</div>
   <div class="soon"><span class="dot"></span> ${tri('このテキストは整備予定です（準備中）','This text is in preparation','Ce texte est en préparation')}</div>
   <div class="rail"><i></i><i></i><i></i><i></i><i></i></div>
   <div class="card">
     <img src="image/web/gengen_roost.svg" alt="" loading="lazy"
       style="float:right; width:110px; aspect-ratio:1; border-radius:0; object-fit:cover; object-position:center 22%; border:1px solid rgba(200,168,112,.45); box-shadow:6px 6px 0 -1px rgba(200,168,112,.16); margin:0 0 10px 14px">
     <h2>${tri('完成時に備わる構成','What the finished edition will offer','Ce que l’édition offrira')}</h2>
     <p>${tri('本文書は本コーパスの拡張対象です。完成時には<b>エウグノストスと同一の構成</b>で公開され、同じビュワーで形態素クリック・三言語切替・並行箇所の参照ができるようになります。',
              'This tractate is part of the planned expansion. It will be published <b>in the same format as Eugnostos</b>: click any morpheme, switch between three languages and follow parallel passages into other texts.',
              'Ce traité fait partie de l’extension prévue. Il sera publié <b>au même format qu’Eugnoste</b> : gloses par morphème, trois langues et passages parallèles d’autres textes.')}</p>
     <div class="layers">
       <div class="layer"><b>${tri('本文(TEI)','Text (TEI)','Texte (TEI)')}</b><small>${tri('コプト語・形態素グロス・証本対照','Coptic, glosses, witnesses','copte, gloses, témoins')}</small></div>
       <div class="layer"><b>${tri('コプト語辞書','Coptic lexicon','Lexique copte')}</b><small>${tri('レンマ＋品詞→日英仏','lemma + POS → JA/EN/FR','lemme + catégorie → JA/EN/FR')}</small></div>
       <div class="layer"><b>${tri('並行箇所','Parallels','Parallèles')}</b><small>${tri('他の文書で同じ文言を持つ箇所','same wording in other texts','même formulation ailleurs')}</small></div>
       <div class="layer"><b>${tri('対訳','Translations','Traductions')}</b><small>${tri('日本語・英語・フランス語','Japanese, English, French','japonais, anglais, français')}</small></div>
     </div>
   </div>
   <div class="actions">
     <a class="primary" href="eugnostos.html">${tri('完成版の例：エウグノストスを見る →','See a finished edition: Eugnostos →','Voir une édition achevée : Eugnoste →')}</a>
     <a href="index.html#corpus">${tri('← 文書一覧へ','← Back to the codices','← Retour aux codices')}</a>
   </div>`;
}
</script>
"""
    body = body.replace("__CATALOG__", json.dumps(cat, ensure_ascii=False))
    return ("<!doctype html><html lang=\"ja\" data-lang=\"ja\" data-i18n=\"full\" data-mode=\"dark\" data-modes=\"light dark\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"{MODE_BOOT}{LANG_BOOT}"
            + head_meta("tractate.html", "準備中 — Sheneset",
                        "ナグ・ハマディ写本のうち、本文をまだ表示できない文書の案内 / A Nag Hammadi tractate whose text is not yet available.") +
            f"{FONTS}<style>{css}</style></head><body>{body}</body></html>")

# --- reader.html (full-text reader for the draft texts) ----------------------
# 品詞ラベル（search.html の POS と同じ内容。片方を直したらもう片方も直す）
POS_NAMES = {
 "ART": ["冠詞", "article", "article"], "N": ["名詞", "noun", "nom"], "NPROP": ["固有名詞", "proper noun", "nom propre"],
 "V": ["動詞", "verb", "verbe"], "VSTAT": ["状態動詞", "stative", "statif"], "PREP": ["前置詞", "preposition", "préposition"],
 "PPER": ["人称代名詞", "personal pronoun", "pronom personnel"], "PPOS": ["所有詞", "possessive", "possessif"],
 "PDEM": ["指示詞", "demonstrative", "démonstratif"], "CONJ": ["接続詞", "conjunction", "conjonction"],
 "PTC": ["不変化詞", "particle", "particule"], "NEG": ["否定辞", "negation", "négation"], "NUM": ["数詞", "numeral", "numéral"],
 "ADV": ["副詞", "adverb", "adverbe"], "ADJ": ["形容詞", "adjective", "adjectif"], "REL": ["関係詞", "relative", "relatif"],
 "CONV": ["変換詞", "converter", "convertisseur"], "FUT": ["未来辞", "future", "futur"], "PRET": ["過去辞", "preterite", "prétérit"],
 "COP": ["繋辞", "copula", "copule"], "PFX": ["接頭辞", "prefix", "préfixe"], "INTERJ": ["間投詞", "interjection", "interjection"],
 "AUX": ["助動詞", "auxiliary", "auxiliaire"], "POSS": ["所有冠詞", "possessive article", "article possessif"],
 "EXIST": ["存在詞", "existential", "existentiel"], "PINT": ["疑問詞", "interrogative", "interrogatif"],
 "FM": ["外来語句", "foreign material", "matériel étranger"],
 "APST": ["完了（過去）助動詞", "perfect auxiliary", "auxiliaire du parfait"],
 "AAOR": ["アオリスト助動詞", "aorist auxiliary", "auxiliaire de l’aoriste"],
 "ACONJ": ["接続法助動詞", "conjunctive auxiliary", "auxiliaire du conjonctif"],
 "ACAUS": ["使役不定詞", "causative infinitive", "infinitif causatif"],
 "AOPT": ["希求法助動詞", "optative auxiliary", "auxiliaire de l’optatif"],
 "ANEGAOR": ["否定アオリスト助動詞", "negative aorist aux.", "aux. de l’aoriste négatif"],
 "ANEGPST": ["否定完了助動詞", "negative perfect aux.", "aux. du parfait négatif"],
 "CREL": ["関係変換詞", "relative converter", "convertisseur relatif"],
 "CCIRC": ["状況変換詞", "circumstantial converter", "convertisseur circonstanciel"],
 "CFOC": ["焦点化変換詞", "focalising converter", "convertisseur focalisant"],
 "CPRET": ["過去変換詞", "preterite converter", "convertisseur prétérit"],
 "VBD": ["接尾活用の動詞（ⲡⲉϫⲉ- など）", "suffixally conjugated verb (ⲡⲉϫⲉ- etc.)", "verbe à conjugaison suffixale (ⲡⲉϫⲉ-, etc.)"],
 "NEGPST": ["否定完了", "negative perfect", "parfait négatif"],
 "ACOND": ["条件法助動詞（ⲉⲣϣⲁⲛ-）", "conditional auxiliary", "auxiliaire du conditionnel"],
 "AFUTCONJ": ["未来接続法助動詞（ⲧⲁⲣⲉ-）", "future conjunctive auxiliary", "auxiliaire du futur conjonctif"],
 "AJUS": ["勧奨法助動詞（ⲙⲁⲣⲉ-）", "jussive auxiliary", "auxiliaire du jussif"],
 "ALIM": ["限界の助動詞（ϣⲁⲛⲧⲉ-）", "limitative auxiliary", "auxiliaire du limitatif"],
 "ANEGJUS": ["否定勧奨法助動詞（ⲙⲡⲣⲧⲣⲉ-）", "negative jussive aux.", "aux. du jussif négatif"],
 "ANEGOPT": ["否定希求法助動詞（ⲛⲛⲉ-）", "negative optative aux.", "aux. de l’optatif négatif"],
 "ANY": ["「まだ〜ない」の助動詞（ⲙⲡⲁⲧⲉ-）", "“not yet” auxiliary", "aux. du « pas encore »"],
 "APREC": ["時の助動詞（ⲛⲧⲉⲣⲉ-）", "temporal (precursive) auxiliary", "auxiliaire du temporel"],
 "IMOD": ["強めの修飾語（ⲧⲏⲣ=・ϩⲱⲱ= など）", "intensifying modifier (ⲧⲏⲣ=, ϩⲱⲱ= etc.)", "modificateur intensif (ⲧⲏⲣ=, ϩⲱⲱ=, etc.)"],
 "VIMP": ["命令形の動詞（ⲙⲁ・ⲁⲣⲓ- など）", "imperative verb (ⲙⲁ, ⲁⲣⲓ- etc.)", "verbe à l’impératif (ⲙⲁ, ⲁⲣⲓ-, etc.)"],
 "PUNCT": ["句読点", "punctuation", "ponctuation"],
 "X": ["未判定", "unresolved", "non résolu"],
}
REPO_URL = "https://github.com/icecocoasince2003-create/Nag-Hammadi-Library/"
# 全文テキストの文書のうち、専用のビュワーもあるもの（reader.html がリンクを示す。キーは data/catalog.xml の doc-… から）
EDITIONS = {"III-3": "eugnostos.html?wit=III", "VI-5": "republic.html"}
# 専用のビュワーの〈対照〉で、注釈つきの別の写本と並べて読める文書（V,1 は語ごとの注釈が無く、エウグノストスの〈対照〉で III,3 と並ぶ）
SYNOPSES = {"V-1": "eugnostos.html?wit=SYN"}

def build_reader():
    """reader.html?doc=II-6 — data/catalog.xml の文書の TEI（source/nhc_fulltext_split/tei/）を表示する。
    自動注釈の暫定版（<bibl subtype="draft">）が対象で、HOME の status D の行と検索の用例がここへリンクする。
    人の目で確かめていないことを、文書ごとの件数とともに冒頭に示す。"""
    css = THEME + """
.shell{position:relative; z-index:1; max-width:980px; margin:0 auto; padding:clamp(22px,5vw,48px) clamp(16px,4vw,40px) 120px}
.eyebrow{font-family:var(--mono); font-weight:500; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-faint)}
.eyebrow::before{content:""; display:inline-block; width:28px; height:1px; margin-right:10px; vertical-align:.3em; background:var(--gold)}
h1{font-family:var(--disp); font-weight:600; line-height:1.12; font-size:clamp(1.8rem,4.6vw,2.7rem); margin:.3em 0 .12em}
.alt{font-family:var(--disp); font-style:italic; color:var(--ink-faint); font-size:1.08rem}
.meta{margin-top:8px; font-size:.8rem; color:var(--ink-faint)}
.docnav{display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px 18px; margin:18px 0 0; font-size:.84rem}
.docnav a{color:var(--ink-soft); text-decoration:none; text-underline-offset:5px}
.docnav a:hover{text-decoration:underline; text-decoration-color:var(--gold)}
.docnav .mid{color:var(--gold-bright,var(--gold)); font-weight:600}
.status{margin:22px 0 0; background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--lapis);
 border-radius:2px; padding:16px 20px}
.status h2{font-family:var(--disp); font-weight:600; font-size:1.06rem; margin:0 0 8px; color:var(--lapis)}
.status ul{margin:0; padding-left:1.2em; color:var(--ink-soft); font-size:.86rem; line-height:1.75}
.status li{margin:.15em 0}
.status .links{display:flex; flex-wrap:wrap; gap:6px 18px; margin:10px 0 0; font-size:.82rem}
.status .links a{color:var(--gold-bright,var(--gold)); text-underline-offset:4px}
.tools{position:sticky; top:52px; z-index:5; display:flex; flex-wrap:wrap; align-items:center; gap:6px 18px; margin:20px 0 12px;
 padding:8px 12px; background:var(--panel-2); border:1px solid var(--line); border-radius:2px; font-size:.82rem; color:var(--ink-soft);
 -webkit-backdrop-filter:blur(8px); backdrop-filter:blur(8px)}
.tools label{display:inline-flex; align-items:center; gap:6px; cursor:pointer}
.tools .lg{margin-left:auto; color:var(--ink-faint); font-size:.74rem}
.tools .lg i{font-style:normal; padding:0 .3em; border-radius:3px}
.text{font-family:var(--cop); color:var(--ink)}
.ab h3{font-family:var(--mono); font-weight:500; font-size:.7rem; letter-spacing:.1em; text-transform:uppercase; color:var(--gold); margin:1.6em 0 .5em}
.seg{margin:0 0 .5em; font-size:1.2rem; line-height:2.05; padding:2px 6px; border-radius:8px; overflow-wrap:anywhere}
.seg.hit{background:var(--hi)}
.sn{font-family:var(--mono); font-size:.66rem; color:var(--ink-faint); text-decoration:none; margin-right:.45em; vertical-align:.18em}
.sn:hover{color:var(--gold)}
.g{white-space:nowrap}
.m{cursor:pointer; border-radius:3px}
.m:hover .f{background:var(--sel)}
.m.sel .f{background:var(--hi); outline:1px solid var(--gold)}
.gap{color:var(--ink-faint); font-family:var(--ui); font-size:.9rem}
.sup{text-decoration:underline dotted var(--gold); text-underline-offset:.22em}
.sup.b{text-decoration:underline dashed var(--rose)}
.text.cuts:not(.inter) .g .m + .m::before{content:"·"; color:var(--ink-faint); margin:0 .04em}
.text.cert .m.c-low .f{box-shadow:inset 0 -.38em 0 rgba(208,154,138,.32)}
.text.cert .m.x .f{text-decoration:underline wavy var(--rose); text-underline-offset:.25em}
/* 頁・行の印（<pb>・<lb>）。〈ページ〉〈行〉で出す。見た目はエウグノストス・『国家』のビュワーの .pdm・.lbm と同じ */
.lbm,.pbm{display:none; user-select:none}
.text.lines .lbm{display:inline-block; font-family:var(--ui); font-size:.56rem; line-height:1; color:var(--lapis); vertical-align:.5em;
 margin:0 2px; padding:0 2px; border-left:1px solid var(--lapis); opacity:.85; font-variant-numeric:tabular-nums; white-space:nowrap}
.text.pages .pbm{display:inline-block; font-family:var(--ui); font-size:.62rem; letter-spacing:.04em; color:var(--on-gold,#1a2030); background:var(--gold);
 border-radius:4px; padding:1px 6px; margin:0 5px; vertical-align:.15em; font-variant-numeric:tabular-nums; white-space:nowrap}
.lbm.hit,.pbm.hit{outline:2px solid var(--gold); outline-offset:1px; border-radius:3px}
.text.inter .seg{line-height:1.25; margin-bottom:1em}
.text.inter .g{display:inline-flex; gap:0 .14em; vertical-align:top; margin:0 .5em .55em 0; white-space:normal}
.text.inter .m{display:inline-flex; flex-direction:column; align-items:flex-start}
.il{display:flex; flex-direction:column; font-family:var(--ui); line-height:1.25; margin-top:2px}
.il .p{font-size:.56rem; letter-spacing:.04em; color:var(--ink-faint)}
.il .gl{font-size:.66rem; color:var(--lapis); max-width:8.5em; white-space:normal}
.mcard{position:fixed; left:50%; bottom:14px; transform:translateX(-50%); z-index:40; width:min(560px,calc(100vw - 24px));
 background:var(--panel-2); color:var(--ink); border:1px solid var(--line-2); border-radius:2px; box-shadow:var(--shadow);
 padding:12px 16px 10px; font-size:.86rem; -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px)}
.mcard .x{position:absolute; top:6px; right:8px; background:none; border:0; color:var(--ink-faint); font-size:1.3rem; cursor:pointer; line-height:1}
.mcard .grp{font-size:1.3rem; margin:0 26px 6px 0}
.mcard .grp .dot{color:var(--ink-faint); margin:0 .1em}
.mcard .grp b{color:var(--gold-bright,var(--gold)); font-weight:600}
.mcard dl{display:grid; grid-template-columns:max-content 1fr; gap:3px 12px; margin:0}
.mcard dt{color:var(--ink-faint); font-size:.76rem; padding-top:.15em}
.mcard dd{margin:0}
.mcard .cop{font-family:var(--cop)}
.mcard .na{color:var(--ink-faint)}
.mcard code{font-size:.74rem; color:var(--ink-faint)}
.mcard .lk{margin:8px 0 0; font-size:.8rem}
.mcard .lk a{color:var(--gold-bright,var(--gold))}
.loading, .err{color:var(--ink-faint); margin-top:24px}
@media (max-width:640px){ .tools{top:46px} .tools .lg{margin-left:0} .seg{font-size:1.1rem} }
"""
    body = """
<nav id="sitebar" class="sitebar sticky"></nav>
<main class="shell" id="shell"><p class="loading">…</p></main>
<div class="mcard" id="card" role="dialog" aria-live="polite" hidden></div>
<script>
const POS=__POS__, REPO=__REPO__, EDITIONS=__EDITIONS__, SYNOPSES=__SYNOPSES__;
const H=document.documentElement, T='http://www.tei-c.org/ns/1.0', XNS='http://www.w3.org/XML/1998/namespace';
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tri=(ja,en,fr)=>'<span class="l-ja">'+ja+'</span><span class="l-en">'+en+'</span><span class="l-fr">'+(fr==null?en:fr)+'</span>';
const UL=()=>H.getAttribute('data-lang')||'ja';
const kids=(el,n)=>Array.from(el.children).filter(c=>c.localName===n);
const all=(el,n)=>Array.from(el.getElementsByTagNameNS(T,n));
const xid=el=>el.getAttributeNS(XNS,'id')||'';
const xlang=el=>el.getAttributeNS(XNS,'lang')||'';
const fmt=n=>Number(n).toLocaleString('en-US');
const pct=(a,b)=>b?Math.round(a/b*100):0;
const posName=p=>{ const e=POS[p]; return e?tri(esc(e[0]),esc(e[1]),esc(e[2])):esc(p); };
/* assets/viewer-tools.js（写本の写真へのリンクなど）。defer で読み込むので、まだ無いときは読み込み後に呼んでもらう */
const withTools=f=>{ if(window.NHCTools) f(window.NHCTools); else (window.NHCToolsQ=window.NHCToolsQ||[]).push(f); };
const key=new URLSearchParams(location.search).get('doc')||'';
const shell=$('#shell'), card=$('#card');
let OPT={inter:false, cert:false, cuts:false, page:false, line:false};
try{ Object.assign(OPT, JSON.parse(localStorage.getItem('nhc-reader')||'{}')); }catch(e){}
const saveOpt=()=>{ try{ localStorage.setItem('nhc-reader', JSON.stringify(OPT)); }catch(e){} };
let DOC=null, D=null, MS=[], NAV={prev:null, next:null};

async function getXML(url){
  const r=await fetch(url,{cache:'no-cache'});
  if(!r.ok) throw new Error(url+' — HTTP '+r.status);
  const x=new DOMParser().parseFromString(await r.text(),'application/xml');
  if(x.getElementsByTagName('parsererror').length) throw new Error(url+' — XML');
  return x;
}
/* data/catalog.xml の文書（<bibl type="document">） */
function readCatalog(x){
  return all(x,'bibl').filter(b=>b.getAttribute('type')==='document').map(b=>{
    const t={}; kids(b,'title').forEach(e=>{ t[xlang(e)]=e.textContent.trim(); });
    const ref={}; kids(b,'ref').forEach(r=>{ ref[r.getAttribute('type')]=r.getAttribute('target'); });
    const sig=kids(b,'idno').find(i=>i.getAttribute('type')==='siglum');
    return {key:xid(b).replace(/^doc-/,''), sub:b.getAttribute('subtype')||'', ja:t.ja||t.en||'', en:t.en||t.ja||'', fr:t.fr||t.en||'',
            siglum:sig?sig.textContent.trim():'', xml:ref.xml||'', reader:ref.reader||''};
  });
}
/* 頁・行の区切り（<pb n>・<lb n>。語の中の改行は <lb break="no"/>）。st に数を足す */
function brk(el, st){
  const k=el.localName==='pb'?'pb':'lb';
  st[k]++;
  return {k, n:el.getAttribute('n')||'', nobr:el.getAttribute('break')==='no'};
}
const brHTML=b=>b.k==='pb'
  ?'<span class="pbm" data-n="'+esc(b.n)+'" title="'+esc((UL()==='ja'?'頁 ':'page ')+b.n)+'">p.'+esc(b.n)+'</span>'
  :'<span class="lbm" data-n="'+esc(b.n)+'" title="'+esc((UL()==='ja'?'行 ':'line ')+b.n)+'">'+esc(b.n)+'</span>';
/* 形態素 1 つ。ⲍ・ⲯ を補った字は <supplied resp="#zp">（注釈を付けた版）か <w resp="#zp">（未注釈の版）。
   語の中の改行（<lb break="no"/>）は、その位置に行の印を置き、mid に記録する（位置の計算に使う） */
function morph(w, gl, st){
  let html='', form='', sup='';
  const mid=[];
  w.childNodes.forEach(n=>{
    if(n.nodeType===3){ form+=n.nodeValue; html+=esc(n.nodeValue); }
    else if(n.nodeType===1){
      if(n.localName==='lb'||n.localName==='pb'){ const b=brk(n,st); mid.push(b); html+=brHTML(b); return; }
      const c=n.textContent;
      if(n.localName==='supplied'){ sup=n.getAttribute('cert')||'high'; html+='<span class="sup'+(sup==='medium'?' b':'')+'">'+esc(c)+'</span>'; }
      else html+=esc(c);
      form+=c; }
  });
  const resp=w.getAttribute('resp')||'', cert=w.getAttribute('cert')||'';
  const m={form:form.trim(), html:html.trim(), type:w.getAttribute('type')||'', lemma:w.getAttribute('lemma')||'',
           grc:xlang(w)==='grc', en:'', ja:'', cert:'', src:'', sup, mid, pre:[]};
  if(resp==='#zp'){ m.sup=cert||'high'; m.html='<span class="sup'+(m.sup==='medium'?' b':'')+'">'+m.html+'</span>'; }
  else if(resp){ m.cert=cert; m.src=resp.replace(/^#/,''); }
  (w.getAttribute('ana')||'').split(/\\s+/).forEach(p=>{ const g=gl[p.replace(/^#/,'')]; if(g && !m[g.l]) m[g.l]=g.t; });
  st.m++; if(m.type) st.typed++; if(m.type==='X') st.X++; if(m.cert==='low') st.low++; if(m.src==='morph-reference') st.ref++;
  if(m.src==='coptic-nlp') st.nlp++; if(m.en||m.ja) st.gl++;
  if(m.sup){ st.rw++; if(m.sup==='medium') st.rwB++; }
  return m;
}
function readTEI(x){
  const gl={};
  all(x,'interpGrp').filter(g=>g.getAttribute('type')==='gloss').forEach(g=>{
    const l=xlang(g); all(g,'interp').forEach(i=>{ gl[xid(i)]={l, t:i.textContent.trim()}; }); });
  const wit=all(x,'text').find(t=>t.getAttribute('type')==='witness');
  if(!wit) throw new Error('TEI: <text type="witness"> がありません');
  const st={m:0, g:0, typed:0, X:0, low:0, ref:0, nlp:0, gl:0, rw:0, rwB:0, segs:0, gaps:0, pb:0, lb:0}, abs=[];
  /* 頁・行の区切りは、<s> の中（語群のあいだ・語群の中・語の中）にも、<ab> の中の <s> のあいだにも置ける。
     <s> の外のものは、次のセグメントの頭に置く（pend） */
  let pend=[];
  all(wit,'ab').forEach(ab=>{
    const segs=[];
    Array.from(ab.children).forEach(s=>{
      if(s.localName==='pb'||s.localName==='lb'){ pend.push(brk(s,st)); return; }
      if(s.localName!=='s') return;
      const items=pend.map(b=>({br:b})); pend=[];
      Array.from(s.children).forEach(c=>{
        const ln=c.localName;
        if(ln==='phr'){
          const ms=[]; let pre=[];
          Array.from(c.children).forEach(k=>{
            if(k.localName==='w'){ const m=morph(k,gl,st); m.pre=pre; pre=[]; ms.push(m); }
            else if(k.localName==='pb'||k.localName==='lb') pre.push(brk(k,st));
          });
          if(ms.length){ items.push({ms}); st.g++; }
          pre.forEach(b=>items.push({br:b}));            // 語群の最後の語のあとの区切り（ふつうは無い）
        }
        else if(ln==='w'){ items.push({ms:[morph(c,gl,st)]}); st.g++; }
        else if(ln==='gap'){ items.push({gap:true}); st.gaps++; }
        else if(ln==='pb'||ln==='lb') items.push({br:brk(c,st)});
      });
      segs.push({id:xid(s), n:s.getAttribute('n')||'', items}); st.segs++;
    });
    abs.push({type:ab.getAttribute('type')||'text', segs});
  });
  const locus=all(x,'locus')[0], lang=all(x,'textLang')[0];
  const out={abs, st, locus:locus?locus.textContent.trim():'', lang:lang?lang.textContent.trim():''};
  locIndex(out);
  return out;
}
/* 各セグメントが写本のどの頁・行で始まり、どこで終わるか（s.loc = {from:{pg,ln}, to:{pg,ln}}。頁・行の無い本文では null）。
   s.pg0 はセグメントが始まる前の頁。語の中の改行（mid）は、その語の終わりの位置に効く。
   reader.html?doc=II-2#p32.10 は 32 頁 10 行を含む（最初の）セグメントへ、#p32 は 32 頁に語のある最初のセグメントへ移る。
   republic.html と同じ形（指示書 A の項目 10）で、引用の URL にも使う */
function locIndex(d){
  let pg='', ln='';
  const step=b=>{ if(b.k==='pb'){ pg=b.n; ln=''; } else ln=b.n; };
  d.abs.forEach(ab=>ab.segs.forEach(s=>{
    let from=null, to=null; s.pg0=pg;
    s.items.forEach(it=>{
      if(it.br){ step(it.br); return; }
      (it.ms||[]).forEach(m=>{
        m.pre.forEach(step);
        if(!from) from={pg, ln};
        m.mid.forEach(step);
        to={pg, ln};
      });
    });
    s.loc=from&&from.pg?{from, to}:null;
  }));
}
const plNum=v=>/^\\d+$/.test(v)?+v:NaN;
function plCmp(a,b){
  const x=plNum(a.pg), y=plNum(b.pg);
  const c=(isNaN(x)||isNaN(y))?String(a.pg).localeCompare(String(b.pg)):x-y;
  if(c) return c;
  if(b.ln===''||b.ln==null||a.ln==='') return 0;
  const p=plNum(a.ln), q=plNum(b.ln);
  return (isNaN(p)||isNaN(q))?String(a.ln).localeCompare(String(b.ln)):p-q;
}
/* 「32,10–15」「32,10–33,4」（行の無い本文は「32」「32–33」） */
function locLabel(loc){
  const a=loc.from, b=loc.to, w=x=>x.pg+(x.ln?','+x.ln:'');
  if(!a.ln||!b.ln) return a.pg===b.pg?a.pg:a.pg+'–'+b.pg;
  return a.pg===b.pg ? w(a)+(b.ln!==a.ln?'–'+b.ln:'') : w(a)+'–'+w(b);
}
const locHash=loc=>'#p'+loc.from.pg+(loc.from.ln?'.'+loc.from.ln:'');

const AB={title:tri('表題','Title','Titre'), subscript:tri('奥書表題','Subscript title','Titre final'),
  colophon:tri('写字生の奥書・覚え書き','Scribal colophon or note','Colophon du scribe'), fragment:tri('未配置の断片','Unplaced fragments','Fragments non situés')};
function renderText(){
  const gk=UL()==='ja'?'ja':'en', ann=D.st.typed>0;
  const O={inter:ann&&OPT.inter, cert:ann&&OPT.cert, cuts:ann&&OPT.cuts};   // 未注釈の文書には効かせない
  MS=[];
  const html=D.abs.map(ab=>{
    const segs=ab.segs.map(s=>{
      const body=s.items.map(it=>{
        if(it.gap) return '<span class="gap" title="'+esc(UL()==='ja'?'元ファイルに欠損の注記があった位置':'lacuna noted in the source file')+'">〔…〕</span>';
        if(it.br) return brHTML(it.br);
        return '<span class="g">'+it.ms.map(m=>{
          const i=MS.push(m)-1, pre=m.pre.map(brHTML).join('');
          let inner='<span class="f">'+m.html+'</span>';
          if(O.inter){ const g=(gk==='ja'?(m.ja||m.en):(m.en||m.ja))||'';
            inner+='<span class="il" lang="'+gk+'"><span class="p">'+esc(m.type)+'</span><span class="gl">'+esc(g)+'</span></span>'; }
          return pre+'<span class="m'+(m.type==='X'?' x':'')+(m.cert?' c-'+m.cert:'')+'" data-i="'+i+'">'+inner+'</span>';
        }).join('')+'</span>';
      }).join(' ');
      return '<p class="seg" id="seg-'+esc(s.id)+'"><a class="sn" href="#seg-'+esc(s.id)+'" aria-haspopup="dialog" title="この箇所を引用 / Cite this passage">§'+esc(s.n)+'</a> <span class="tx" lang="cop">'+body+'</span></p>';
    }).join('');
    return '<section class="ab ab-'+esc(ab.type)+'">'+(AB[ab.type]?'<h3>'+AB[ab.type]+'</h3>':'')+segs+'</section>';
  }).join('');
  const box=$('#text');
  box.className='text'+(O.inter?' inter':'')+(O.cert?' cert':'')+(O.cuts?' cuts':'')+
    (OPT.page&&D.st.pb?' pages':'')+(OPT.line&&D.st.lb?' lines':'');
  box.innerHTML=html;
  hideCard();
}
function statusHTML(){
  const s=D.st, ann=s.typed>0, rel=REPO+'blob/main/source/nhc_fulltext_split/README_ja.md';
  const li=[];
  if(!s.pb&&!s.lb) li.push(tri('<b>本文</b>：提供された全文テキストを下処理した作業用の本文です。校訂本や写本とは照合していません。上線、復元された文字の区別、頁と行の区切りは入っておらず、§ は元ファイルの行（セグメント）の番号です。〔…〕は元ファイルに欠損の注記があった位置です。',
    '<b>Text</b>: a working text prepared from a supplied full-text file, not collated with the critical editions or the manuscript. It has no supralinear strokes, no marking of restored text and no page or line breaks; § numbers are the rows (segments) of the source file, and 〔…〕 marks where the source noted a lacuna.',
    '<b>Texte</b> : texte de travail tiré d’un fichier fourni, non collationné avec les éditions critiques ni avec le manuscrit. Sans traits suscrits, sans distinction des restitutions, sans coupures de page ni de ligne ; les § sont les lignes (segments) du fichier source et 〔…〕 signale une lacune notée dans la source.'));
  else li.push(tri('<b>本文</b>：提供された全文テキストを下処理した作業用の本文です。本文の文字は校訂本や写本と照合していません。上線と、復元された文字の区別は入っていません。写本の頁と行の区切りは、校訂本に合わせて入れたものです（〈ページ〉〈行〉で表示）。§ は元ファイルの行（セグメント）の番号です。〔…〕は元ファイルに欠損の注記があった位置です。',
    '<b>Text</b>: a working text prepared from a supplied full-text file; its letters have not been collated with the critical editions or the manuscript. It has no supralinear strokes and no marking of restored text. The page and line breaks of the codex follow an edition (show them with Pages and Lines). § numbers are the rows (segments) of the source file, and 〔…〕 marks where the source noted a lacuna.',
    '<b>Texte</b> : texte de travail tiré d’un fichier fourni ; ses lettres n’ont pas été collationnées avec les éditions critiques ni avec le manuscrit. Sans traits suscrits ni distinction des restitutions. Les coupures de page et de ligne du codex suivent une édition (à afficher avec Pages et Lignes). Les § sont les lignes (segments) du fichier source et 〔…〕 signale une lacune notée dans la source.'));
  if(ann && s.nlp){
    /* Coptic SCRIPTORIUM の NLP で付け直した版（source/nhc_fulltext_split/README_ja.md の §13） */
    li.push(tri('<b>語のまとまり（語群）と形態素</b>：Coptic SCRIPTORIUM の NLP で自動で付けたものです（2026-11-24）。人の目では確かめていません。',
      '<b>Bound groups and morphemes</b>: assigned automatically with the Coptic SCRIPTORIUM NLP tools (2026-11-24); not checked by hand.',
      '<b>Groupes et morphèmes</b> : attribués automatiquement avec les outils de TAL de Coptic SCRIPTORIUM (2026-11-24) ; non vérifiés.'));
    li.push(tri('<b>品詞・レンマ</b>：同じく NLP によるものです。この文書では、確度 low が '+pct(s.low,s.m)+'%、品詞を決められなかった語（X）が '+pct(s.X,s.m)+'% あります。確度はスクリプトの目安で、medium でも正しいとは限りません。',
      '<b>Part of speech and lemma</b>: also from the NLP tools. In this text '+pct(s.low,s.m)+'% of the morphemes have low certainty and '+pct(s.X,s.m)+'% could not be classified (X). Certainty is the script’s own rating; medium does not mean an analysis is correct.',
      '<b>Partie du discours et lemme</b> : également issus des outils de TAL. Dans ce texte, '+pct(s.low,s.m)+' % des morphèmes ont une certitude faible et '+pct(s.X,s.m)+' % n’ont pas pu être classés (X). La certitude est l’appréciation du script ; « medium » ne garantit pas l’analyse.'));
    /* 語義は 2026-11-18 の暫定版の残り。その版の無かった文書（IV,2、写本 V・VI、VII,1–3。README_ja.md の §14）には無い */
    if(!s.gl) li.push(tri('<b>語義</b>：まだ付いていません。辞書に項目のある語は、語のカードの〈辞書の項目〉から意味を見られます。',
      '<b>Glosses</b>: none yet. For words that are in the lexicon, the word card links to the lexicon entry.',
      '<b>Gloses</b> : pas encore. Pour les mots présents dans le lexique, la fiche du mot renvoie à l’entrée du lexique.'));
    else li.push(tri('<b>語義</b>：前の暫定版（2026-11-18）で自動で付けた短い辞書的な意味を、語の範囲とレンマが変わらなかった形態素（この文書では '+pct(s.gl,s.m)+'%）にだけ残しています。文脈で確かめた訳語ではありません。',
      '<b>Glosses</b>: the short dictionary meanings assigned automatically for the previous draft (2026-11-18) are kept only on morphemes whose extent and lemma did not change ('+pct(s.gl,s.m)+'% in this text); they are not translations checked against the context.',
      '<b>Gloses</b> : les brèves équivalences attribuées automatiquement pour le brouillon précédent (2026-11-18) ne subsistent que sur les morphèmes dont l’étendue et le lemme n’ont pas changé ('+pct(s.gl,s.m)+' % dans ce texte) ; ce ne sont pas des traductions vérifiées en contexte.'));
    li.push(tri('<b>構文</b>：NLP による依存構造の解析（暫定）は TEI には入れず、CoNLL-U のファイルにあります（下のリンク）。元のテキストには句読点がほとんど無いので、セグメントの最後に句読点を足して送り、セグメントごとに 1 文として解析させました（長いセグメントは長い文のまま）。人の目では確かめていません。',
      '<b>Syntax</b>: the provisional dependency analysis from the NLP tools is not in the TEI but in a CoNLL-U file (link below). As the source text has almost no punctuation, a punctuation mark was added at the end of each segment before sending, so that each segment was analysed as one sentence (long segments remain long sentences). Not checked by hand.',
      '<b>Syntaxe</b> : l’analyse en dépendances provisoire des outils de TAL n’est pas dans le TEI mais dans un fichier CoNLL-U (lien ci-dessous). Le texte source n’ayant presque pas de ponctuation, un signe de ponctuation a été ajouté à la fin de chaque segment avant l’envoi, afin que chaque segment soit analysé comme une phrase (les segments longs restent des phrases longues). Non vérifiée à la main.'));
  } else if(ann){
    li.push(tri('<b>語のまとまり（語群）</b>：自動で推定したものです。全文テキスト全体で、境目のおよそ 4 分の 1 が要確認の一覧に入っています。',
      '<b>Bound groups</b> (orthographic words): inferred automatically; across the full texts about a quarter of the boundaries are on the review list.',
      '<b>Groupes</b> (mots graphiques) : déduits automatiquement ; sur l’ensemble, environ un quart des limites figurent sur la liste à vérifier.'));
    li.push(tri('<b>品詞・レンマ・語義</b>：自動で付けたものです。この文書では、確度 low が '+pct(s.low,s.m)+'%、品詞を決められなかった語（X）が '+pct(s.X,s.m)+'% あります。語義は短い辞書的な意味で、文脈で確かめた訳語ではありません。確度 high・medium でも正しいとは限りません。',
      '<b>Part of speech, lemma and gloss</b>: assigned automatically. In this text '+pct(s.low,s.m)+'% of the morphemes have low certainty and '+pct(s.X,s.m)+'% could not be classified (X). Glosses are short dictionary meanings, not translations checked against the context. High or medium certainty does not mean an analysis is correct.',
      '<b>Partie du discours, lemme et glose</b> : attribués automatiquement. Dans ce texte, '+pct(s.low,s.m)+' % des morphèmes ont une certitude faible et '+pct(s.X,s.m)+' % n’ont pas pu être classés (X). Les gloses sont de brèves équivalences de dictionnaire, non des traductions vérifiées en contexte. Une certitude « high » ou « medium » ne garantit pas l’analyse.'));
  } else {
    li.push(tri('<b>注釈</b>：語のまとまり・品詞・レンマ・語義はまだ付いていません。','<b>Annotation</b>: no bound groups, parts of speech, lemmata or glosses yet.','<b>Annotation</b> : ni groupes, ni parties du discours, ni lemmes, ni gloses pour l’instant.'));
    li.push(tri('<b>語の区切り</b>：元ファイルのままです。接頭辞や冠詞が分かれている箇所と、つながっている箇所があります。',
      '<b>Word division</b>: as in the source file; prefixes and articles are sometimes separate and sometimes joined to the word.',
      '<b>Découpage</b> : celui du fichier source ; préfixes et articles sont tantôt séparés, tantôt joints au mot.'));
  }
  const ed=EDITIONS[DOC.key], syn=SYNOPSES[DOC.key];
  if(ed && !s.ref) li.push(tri('<b>専用のビュワー</b>：この文書は <a href="'+esc(ed)+'">専用のビュワー</a>でも読めます。',
    '<b>Dedicated reader</b>: this text can also be read in its <a href="'+esc(ed)+'">own reader</a>.',
    '<b>Visionneuse dédiée</b> : ce texte se lit aussi dans sa <a href="'+esc(ed)+'">propre visionneuse</a>.'));
  if(syn) li.push(tri('<b>III,3 との対照</b>：エウグノストスのビュワーの<a href="'+esc(syn)+'">〈対照〉</a>で、III,3 と並べて読めます（同じ文言の箇所を自動で照合して並べたものです）。',
    '<b>Synopsis with III,3</b>: the <a href="'+esc(syn)+'">Synopsis</a> of the Eugnostos reader sets this text beside III,3 (aligned automatically by shared wording).',
    '<b>Synopse avec III,3</b> : la <a href="'+esc(syn)+'">synopse</a> de la visionneuse d’Eugnoste présente ce texte en regard de III,3 (alignement automatique sur la formulation commune).'));
  if(s.rw) li.push(tri('<b>ⲍ・ⲯ</b>：元ファイルで落ちていた字を、語形と文脈から補いました（点線の下線、'+s.rw+' 語）。'+(s.rwB?'このうち確度 B の '+s.rwB+' 語（破線）は、固有名などで校訂本での確認が必要です。':'校訂本とは照合していません。'),
    '<b>ⲍ and ⲯ</b>: letters lost in the source file were restored from the word form and context (dotted underline; '+s.rw+' words).'+(s.rwB?' The '+s.rwB+' of certainty B (dashed), names and the like, still need checking against the editions.':' None has been collated with the editions.'),
    '<b>ⲍ et ⲯ</b> : lettres perdues dans le fichier source, restituées d’après la forme et le contexte (soulignement pointillé ; '+s.rw+' mots).'+(s.rwB?' Les '+s.rwB+' de certitude B (tirets), noms propres notamment, restent à vérifier.':' Aucune n’a été collationnée.')));
  if(s.ref) li.push(tri('<b>人の手による注釈</b>：冒頭の一部（'+s.ref+' 形態素）は、人の手で注釈した版から写しました。その版は <a href="eugnostos.html?wit=III">エウグノストスのビュワー</a>で読めます。',
    '<b>Hand annotation</b>: part of the opening ('+s.ref+' morphemes) was copied from the hand-annotated edition, which you can read in the <a href="eugnostos.html?wit=III">Eugnostos reader</a>.',
    '<b>Annotation manuelle</b> : une partie du début ('+s.ref+' morphèmes) provient de l’édition annotée à la main, consultable dans la <a href="eugnostos.html?wit=III">visionneuse d’Eugnoste</a>.'));
  li.push(tri('<b>訳</b>：まだありません。','<b>Translation</b>: none yet.','<b>Traduction</b> : pas encore.'));
  const head=ann?tri('暫定版 — 自動で付けた注釈で、人の目では確かめていません','Draft — automatic annotation, not checked by hand','Version provisoire — annotation automatique, non vérifiée')
                :tri('未注釈の作業用本文','Unannotated working text','Texte de travail non annoté');
  return '<section class="status"><h2>'+head+'</h2><ul>'+li.map(x=>'<li>'+x+'</li>').join('')+'</ul><p class="links">'+
    '<a href="'+esc(DOC.xml)+'" download>'+tri('TEI（XML）をダウンロード','Download the TEI (XML)','Télécharger le TEI (XML)')+'</a>'+
    '<a href="guide.html#viewer">'+tri('本文ビュワーの読み方（はじめての方へ）','How to read this page (Getting started)','Lire cette page (Premiers pas)')+'</a>'+
    '<a href="'+esc(rel)+'" target="_blank" rel="noopener">'+tri('作り方と確かめたこと（README §10〜§14）','How it was made and checked (README §10–14)','Méthode et vérifications (README §10–14)')+'</a>'+
    (ann&&s.nlp?'<a href="'+esc(REPO+'blob/main/'+DOC.xml.replace('/tei/','/conllu/').replace(/\\.xml$/,'.conllu'))+'" target="_blank" rel="noopener">'+tri('構文（CoNLL-U）','Syntax (CoNLL-U)','Syntaxe (CoNLL-U)')+'</a>'
      :ann?'<a href="'+esc(REPO+'tree/main/source/nhc_fulltext_split/annotation')+'" target="_blank" rel="noopener">'+tri('要確認の一覧','Review lists','Listes à vérifier')+'</a>':'')+
    '<a href="search.html?doc='+encodeURIComponent(DOC.key)+'">'+tri('この文書を検索','Search this text','Chercher dans ce texte')+'</a>'+
    '<a href="search.html?doc='+encodeURIComponent(DOC.key)+'&amp;view=stats">'+tri('統計','Statistics','Statistiques')+'</a></p></section>';
}
/* 前後の文書へのリンク（本文の上と下に 1 つずつ）。2 つの <nav> を読み上げで区別できるよう、言語ごとの名前（aria-label）を付ける */
function labelDocNavs(){
  const L={top:{ja:'前後の文書',en:'Previous and next texts',fr:'Textes précédent et suivant'},
           bottom:{ja:'前後の文書（本文の後）',en:'Previous and next texts (after the text)',fr:'Textes précédent et suivant (après le texte)'}};
  document.querySelectorAll('nav.docnav[data-pos]').forEach(n=>{ const o=L[n.dataset.pos]; if(o) n.setAttribute('aria-label',o[UL()]||o.en); });
}
function navHTML(pos){
  const a=d=>d?'<a href="reader.html?doc='+encodeURIComponent(d.key)+'">'+esc(d.siglum.replace(/^NHC\\s*/,''))+' '+tri(esc(d.ja),esc(d.en),esc(d.fr))+'</a>':'<span></span>';
  return '<nav class="docnav" data-pos="'+pos+'">'+(NAV.prev?'<span>← '+a(NAV.prev)+'</span>':'<span></span>')+
    '<a class="mid" href="index.html#corpus">'+tri('文書一覧','All texts','Tous les textes')+'</a>'+
    (NAV.next?'<span>'+a(NAV.next)+' →</span>':'<span></span>')+'</nav>';
}
function setTitle(){
  const l=UL(), nm=DOC[l]||DOC.ja, ann=D&&D.st.typed>0;
  document.title=nm+' — '+DOC.siglum+' · '+({ja:ann?'暫定版':'作業用本文', en:ann?'draft':'working text', fr:ann?'provisoire':'texte de travail'}[l]||'')+' — Sheneset';
}
function hideCard(){ card.hidden=true; document.querySelectorAll('.m.sel').forEach(x=>x.classList.remove('sel')); }
/* 辞書のページ（lexicon.html）の項目へのリンク。data/lexicon.xml は、語を初めて押したときに 1 度だけ読む。
   レンマと品詞の組が一致する項目へ。品詞の合う項目が無ければ、そのレンマの項目（同形異義語ならそのまとまり）へ。
   辞書に無い語（レンマの無い語を含む）にはリンクを出さない */
let LEXP=null;
function lexIndex(){
  if(!LEXP) LEXP=fetch('data/lexicon.xml',{cache:'no-cache'}).then(r=>r.ok?r.text():Promise.reject(r.status)).then(t=>{
    const x=new DOMParser().parseFromString(t,'application/xml'), ix=new Map();
    all(x,'entry').forEach(e=>{
      const o=e.getElementsByTagNameNS(T,'orth')[0]; if(!o) return;
      const p=e.getElementsByTagNameNS(T,'pos')[0], par=e.parentNode, lem=o.textContent.trim();
      if(!ix.has(lem)) ix.set(lem,[]);
      ix.get(lem).push({id:xid(e), pos:p?p.textContent.trim():'', sup:par&&par.localName==='superEntry'?xid(par):''});
    });
    return ix;
  }).catch(()=>null);
  return LEXP;
}
function lexTarget(ix,m){
  const es=ix&&m.lemma?ix.get(m.lemma):null; if(!es||!es.length) return '';
  const hit=es.find(e=>e.pos===m.type); if(hit) return hit.id;
  return es[0].sup||es[0].id;
}
function showCard(el){
  const m=MS[+el.dataset.i]; if(!m) return;
  const g=el.closest('.g'), grp=g?Array.from(g.querySelectorAll('.m')).map(x=>MS[+x.dataset.i]):[m];
  const nlp=m.src==='coptic-nlp';
  const certT={high:tri('high — 参考本文との一致などによる','high — e.g. agrees with the annotated reference text','high — p. ex. accord avec le texte de référence'),
    medium:nlp?tri('medium — NLP の出力そのまま。スクリプトの目安で、正しいとは限らない','medium — NLP output as is; the script’s own rating, not a check','medium — sortie du NLP telle quelle ; estimation du script, non vérifiée')
      :tri('medium — 語彙表・規則による仮の判定','medium — from the core word list or rules','medium — liste de base ou règles'),
    low:tri('low — 推定。要確認','low — a guess; needs checking','low — conjecture, à vérifier')}[m.cert]||esc(m.cert);
  const rows=[[tri('形態素','Morpheme','Morphème'),'<span class="cop" lang="cop">'+m.html+'</span>']];
  if(D.st.typed){
    rows.push([tri('レンマ','Lemma','Lemme'), m.lemma?'<span class="cop" lang="cop">'+esc(m.lemma)+'</span>':'<span class="na">'+tri('なし（未判定）','none (unresolved)','aucun (non résolu)')+'</span>']);
    rows.push([tri('品詞','Part of speech','Catégorie'), m.type?posName(m.type)+' <code>'+esc(m.type)+'</code>':'<span class="na">—</span>']);
    if(m.ja||m.en) rows.push([tri('語義（自動）','Gloss (automatic)','Glose (automatique)'), [m.ja,m.en].filter(Boolean).map(esc).join(' ／ ')]);
    if(m.cert) rows.push([tri('確度','Certainty','Certitude'), certT]);
    if(m.src) rows.push([tri('出どころ','Source','Source'), m.src==='morph-reference'?tri('人の手で注釈した版から写したもの','copied from the hand-annotated edition','copié de l’édition annotée à la main')
      :nlp?tri('Coptic SCRIPTORIUM の NLP による自動注釈','automatic annotation by the Coptic SCRIPTORIUM NLP','annotation automatique par le NLP de Coptic SCRIPTORIUM'):tri('自動注釈','automatic annotation','annotation automatique')]);
    if(m.grc) rows.push([tri('借用語','Loanword','Emprunt'), tri('ギリシア語','Greek','grec')]);
  }
  if(m.sup) rows.push([tri('補った字','Restored letters','Lettres restituées'), m.sup==='medium'
    ?tri('ⲍ・ⲯ を補った語。確度 B（固有名など。校訂本での確認が必要）','ⲍ/ⲯ restored; certainty B (names and the like; check against the editions)','ⲍ/ⲯ restitué ; certitude B (noms propres, etc. ; à vérifier)')
    :tri('ⲍ・ⲯ を補った語。確度 A（語形と文脈から決まるもの）','ⲍ/ⲯ restored; certainty A (determined by word form and context)','ⲍ/ⲯ restitué ; certitude A (forme et contexte)')]);
  const q=m.lemma?'lemma="'+m.lemma+'"':'tok="'+m.form+'"';
  card.innerHTML='<button type="button" class="x" aria-label="close">×</button>'+
    '<div class="grp cop" lang="cop">'+grp.map(x=>x===m?'<b>'+x.html+'</b>':x.html).join('<span class="dot">·</span>')+'</div>'+
    '<dl>'+rows.map(r=>'<dt>'+r[0]+'</dt><dd>'+r[1]+'</dd>').join('')+'</dl>'+
    '<p class="lk"><a href="search.html?doc='+encodeURIComponent(DOC.key)+'&amp;kind=aql&amp;q='+encodeURIComponent(q)+'">'+tri('この文書で検索','Search this text','Chercher dans ce texte')+' ('+esc(q)+') →</a></p>';
  card.hidden=false; card.dataset.i=el.dataset.i;
  document.querySelectorAll('.m.sel').forEach(x=>x.classList.remove('sel')); el.classList.add('sel');
  if(m.lemma) lexIndex().then(ix=>{
    const id=lexTarget(ix,m), at=el.dataset.i;
    if(!id||card.hidden||card.dataset.i!==at||card.querySelector('.lexl')) return;
    const lk=card.querySelector('.lk');
    if(lk) lk.insertAdjacentHTML('beforeend',' · <a class="lexl" href="lexicon.html#'+encodeURIComponent(id)+'">'+tri('辞書の項目','Lexicon entry','Entrée du lexique')+' →</a>');
  });
}
function gotoHash(){
  document.querySelectorAll('.seg.hit, .lbm.hit, .pbm.hit').forEach(x=>x.classList.remove('hit'));
  const p=/^#p([^.]+)(?:\.(.+))?$/.exec(location.hash);
  if(p){ gotoPageLine(decodeURIComponent(p[1]), p[2]==null?null:decodeURIComponent(p[2])); return; }
  if(!/^#seg-/.test(location.hash)) return;
  const el=document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if(el){ el.classList.add('hit'); el.scrollIntoView({block:'center'}); }
}
/* #p32.10（32 頁 10 行）・#p32（32 頁）: その行（頁）を含む最初のセグメントへ移り、頁・行の番号を表示して、その印を目立たせる */
function gotoPageLine(pg, ln){
  if(!D) return;
  const t={pg, ln:ln==null?'':ln};
  const s=D.abs.flatMap(ab=>ab.segs).find(x=>x.loc&&(ln==null
    ? plCmp({pg:x.loc.from.pg,ln:''},{pg,ln:''})<=0&&plCmp({pg:x.loc.to.pg,ln:''},{pg,ln:''})>=0
    : plCmp(x.loc.from,t)<=0&&plCmp(x.loc.to,t)>=0));
  const row=s&&document.getElementById('seg-'+s.id); if(!row) return;
  if(!(OPT.page||!D.st.pb)||!(OPT.line||!D.st.lb)){
    OPT.page=OPT.page||!!D.st.pb; OPT.line=OPT.line||!!D.st.lb;   // 表示するだけ（保存はしない）
    ['oPage','oLine'].forEach(id=>{ const e=document.getElementById(id); if(e) e.checked=OPT[id==='oPage'?'page':'line']; });
    renderText();
  }
  const r=document.getElementById('seg-'+s.id);
  let cur=s.pg0, mark=null;
  Array.from(r.querySelectorAll('.pbm,.lbm')).some(x=>{
    if(x.classList.contains('pbm')){ cur=x.dataset.n; if(ln==null&&cur===pg){ mark=x; return true; } }
    else if(ln!=null&&cur===pg&&x.dataset.n===ln){ mark=x; return true; }
    return false;
  });
  r.classList.add('hit'); if(mark) mark.classList.add('hit');
  r.scrollIntoView({block:'center'});
}
function render(){
  const s=D.st, ann=s.typed>0;
  const m=/^NHC\\s+([IVX]+),/.exec(DOC.siglum);
  shell.innerHTML=navHTML('top')+
    '<div class="eyebrow" style="margin-top:18px">'+(m?'Codex '+m[1]+' · ':'')+esc(DOC.siglum)+(D.locus?' · '+esc(D.locus):'')+'</div>'+
    '<h1>'+tri(esc(DOC.ja),esc(DOC.en),esc(DOC.fr))+'</h1><div class="alt">'+tri(esc(DOC.en),esc(DOC.ja),esc(DOC.en))+'</div>'+
    '<div class="meta">'+esc(D.lang)+' · '+tri(fmt(s.segs)+' セグメント · '+fmt(s.m)+' 形態素'+(ann?' · '+fmt(s.g)+' 語群':''), fmt(s.segs)+' segments · '+fmt(s.m)+' morphemes'+(ann?' · '+fmt(s.g)+' bound groups':''), fmt(s.segs)+' segments · '+fmt(s.m)+' morphèmes'+(ann?' · '+fmt(s.g)+' groupes':''))+'</div>'+
    '<div class="doc-tools"><button type="button" class="doc-cite" id="docCite" aria-haspopup="dialog">'+tri('この文書を引用','Cite this text','Citer ce texte')+'</button>'+
      (m?'<span class="doc-photos" data-codices="'+esc(m[1])+'" hidden></span>':'')+'</div>'+
    /* 文書ごとの解題（data/intros.json。reviewed: true のものだけ表示。assets/viewer-tools.js） */
    '<div class="doc-intro" data-intro="'+esc(DOC.key)+'" hidden></div>'+
    statusHTML()+
    (ann||s.pb||s.lb?'<div class="tools">'+
      (ann?'<label><input type="checkbox" id="oInter"'+(OPT.inter?' checked':'')+'>'+tri('語義と品詞を重ねる','Show glosses and POS','Afficher gloses et catégories')+'</label>'+
      '<label><input type="checkbox" id="oCert"'+(OPT.cert?' checked':'')+'>'+tri('確かでない注釈に印','Mark uncertain analyses','Signaler les analyses incertaines')+'</label>'+
      '<label><input type="checkbox" id="oCuts"'+(OPT.cuts?' checked':'')+'>'+tri('形態素の区切り','Morpheme boundaries','Limites des morphèmes')+'</label>':'')+
      /* 写本の頁・行（エウグノストス・『国家』のビュワーの〈ページ〉〈行〉と同じ） */
      (s.pb?'<label><input type="checkbox" id="oPage"'+(OPT.page?' checked':'')+'>'+tri('ページ','Pages','Pages')+'</label>':'')+
      (s.lb?'<label><input type="checkbox" id="oLine"'+(OPT.line?' checked':'')+'>'+tri('行','Lines','Lignes')+'</label>':'')+
      (ann?'<span class="lg">'+tri('語をクリックすると注釈を表示','Click a word for its analysis','Cliquez sur un mot pour son analyse')+'</span>':'')+
    '</div>':'<div style="height:14px"></div>')+
    '<article id="text" class="text"></article>'+navHTML('bottom');
  const bind=(id,k)=>{ const e=document.getElementById(id); if(e) e.addEventListener('change',()=>{ OPT[k]=e.checked; saveOpt(); renderText(); }); };
  bind('oInter','inter'); bind('oCert','cert'); bind('oCuts','cuts'); bind('oPage','page'); bind('oLine','line');
  renderText(); setTitle(); labelDocNavs(); gotoHash();
  withTools(t=>t.fill(shell));
}
/* 引用（assets/viewer-tools.js）。§ を押すと、これまでどおりその箇所へ移る（ハッシュの更新）のに加えて、引用のメニューを開く。
   文書の引用（冒頭の〈この文書を引用〉）には、その文書の最終更新日（data/doc_dates.json）を添える */
const docStatus=()=>D&&D.st.typed>0?'draft':'text';
/* 頁・行のある文書では、箇所を写本の頁・行で示し（NHC II 32,10–15（§3、暫定版））、URL も頁・行のアンカーにする
   （reader.html?doc=II-2#p32.10。republic.html と同じ形）。頁・行の無い文書は NHC II,2 §3（暫定版）と #seg-… */
const ST_WORD={draft:{ja:'暫定版',en:'draft',fr:'provisoire'}, text:{ja:'未注釈',en:'unannotated',fr:'non annoté'}};
function citeSeg(a){
  const id=decodeURIComponent((a.getAttribute('href')||'').replace(/^#seg-/,''));
  const s=D?D.abs.flatMap(ab=>ab.segs).find(x=>x.id===id):null; if(!s) return;
  const st=docStatus(), cx=/^NHC\s+([IVXLC]+),/.exec(DOC.siglum);
  if(s.loc&&cx){
    const lab='NHC '+cx[1]+' '+locLabel(s.loc), w=ST_WORD[st]||{};
    withTools(t=>t.cite(a,{kind:'passage', path:'reader.html?doc='+encodeURIComponent(DOC.key)+locHash(s.loc),
      where:{ja:lab+'（§'+s.n+(w.ja?'、'+w.ja:'')+'）', en:lab+' (§'+s.n+(w.en?', '+w.en:'')+')', fr:lab+' (§'+s.n+(w.fr?', '+w.fr:'')+')'}}));
    return;
  }
  const base=DOC.siglum+' §'+s.n;
  withTools(t=>t.cite(a,{kind:'passage', path:'reader.html?doc='+encodeURIComponent(DOC.key)+'#seg-'+encodeURIComponent(id),
    where:{ja:t.withStatus('ja',base,st), en:t.withStatus('en',base,st), fr:t.withStatus('fr',base,st)}}));
}
function citeDoc(b){
  withTools(t=>t.cite(b,{kind:'document', path:'reader.html?doc='+encodeURIComponent(DOC.key),
    doc:{key:DOC.key, siglum:DOC.siglum, title:{ja:DOC.ja, en:DOC.en, fr:DOC.fr}, status:docStatus()}}));
}
function fail(msg, detail){
  shell.innerHTML='<div class="eyebrow">Nag Hammadi Codices</div><h1>'+msg+'</h1>'+(detail?'<p class="err">'+esc(detail)+'</p>':'')+
    '<div class="docnav"><a class="mid" href="index.html#corpus">'+tri('← 文書一覧へ','← All texts','← Tous les textes')+'</a></div>';
}
(async()=>{
  try{
    const docs=readCatalog(await getXML('data/catalog.xml'));
    DOC=docs.find(d=>d.key===key && d.xml);
    if(!DOC){ fail(tri('文書が見つかりません','Text not found','Texte introuvable'), key||'—'); return; }
    if(!/^source\\/nhc_fulltext_split\\/tei\\//.test(DOC.xml) && DOC.reader && !/^reader\\.html/.test(DOC.reader)){ location.replace(DOC.reader); return; }
    const withReader=docs.filter(d=>/^reader\\.html/.test(d.reader));
    const i=withReader.indexOf(DOC);
    NAV={prev:i>0?withReader[i-1]:null, next:i>=0&&i<withReader.length-1?withReader[i+1]:null};
    shell.innerHTML='<p class="loading">'+tri('本文を読み込んでいます…','Loading the text…','Chargement du texte…')+'</p>';
    D=readTEI(await getXML(DOC.xml));
    render();
  }catch(e){ console.error(e); fail(tri('読み込めませんでした','Could not load the text','Chargement impossible'), e.message); }
})();
document.addEventListener('click',e=>{
  if(e.target.closest('#card .x')){ hideCard(); return; }
  const sn=e.target.closest('#text .sn'); if(sn){ citeSeg(sn); return; }
  const dc=e.target.closest('#docCite'); if(dc){ citeDoc(dc); return; }
  const m=e.target.closest('#text .m'); if(m) showCard(m);
});
document.addEventListener('keydown',e=>{ if(e.key==='Escape') hideCard(); });
document.addEventListener('nhc:lang',()=>{ if(!D) return; setTitle(); labelDocNavs(); if(OPT.inter) renderText(); });
window.addEventListener('hashchange',gotoHash);
</script>
"""
    body = (body.replace("__POS__", json.dumps(POS_NAMES, ensure_ascii=False)).replace("__REPO__", json.dumps(REPO_URL))
                .replace("__EDITIONS__", json.dumps(EDITIONS)).replace("__SYNOPSES__", json.dumps(SYNOPSES)))
    return ("<!doctype html><html lang=\"ja\" data-lang=\"ja\" data-i18n=\"full\" data-mode=\"dark\" data-modes=\"light dark\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"{MODE_BOOT}{LANG_BOOT}"
            + head_meta("reader.html", "本文（暫定版） — Sheneset",
                        "ナグ・ハマディ写本の全文テキスト（自動注釈の暫定版）/ Nag Hammadi Codices: full text with a draft automatic annotation.") +
            f"{FONTS}<script defer src=\"assets/viewer-tools.js\"></script><style>{css}</style></head><body>{body}</body></html>")

# --- sitemap.xml・robots.txt -------------------------------------------------
# 検索エンジン向けの URL の一覧。管理用（admin・profile）、確認作業の画面 review.html、転送だけの stats.html、準備中の案内 tractate.html は載せない。
SITEMAP_PAGES = ["", "guide.html", "gnosticism.html", "project.html", "search.html", "lexicon.html",
                 "eugnostos.html?wit=III", "eugnostos.html?wit=SYN", "republic.html"]
SITEMAP_TAIL = ["privacy.html", "terms.html"]

def catalog_readers():
    """data/catalog.xml の暫定版・未注釈の文書（<bibl subtype="draft|unannotated">）の reader.html?doc=… を、カタログの順に"""
    import xml.etree.ElementTree as ET
    T = "{http://www.tei-c.org/ns/1.0}"
    out = []
    for b in ET.parse(os.path.join(OUTDIR, "data", "catalog.xml")).getroot().iter(T + "bibl"):
        if b.get("type") != "document" or b.get("subtype") not in ("draft", "unannotated"):
            continue
        out += [r.get("target") for r in b.findall(T + "ref") if r.get("type") == "reader" and (r.get("target") or "").startswith("reader.html?doc=")]
    return out

def build_sitemap():
    paths = SITEMAP_PAGES + catalog_readers() + SITEMAP_TAIL
    if len(set(paths)) != len(paths):
        raise SystemExit("build_site.py: sitemap.xml の URL が重複しています")
    urls = "".join("  <url><loc>%s</loc></url>\n" % html.escape(SITE_URL + p, quote=False) for p in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- 自動生成ファイル: scripts/build_site.py が出力します（直接編集しない）。暫定版・未注釈の文書は data/catalog.xml から -->\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n'), len(paths)

def build_robots():
    return ("# robots.txt — scripts/build_site.py が出力します（直接編集しない）\n"
            "User-agent: *\n"
            "Disallow: /admin.html\n"
            "Disallow: /profile.html\n"
            "Disallow: /review.html\n"
            "\n"
            f"Sitemap: {SITE_URL}sitemap.xml\n")

# --- data/doc_dates.json（文書ごとの最終更新日）---------------------------------
# ビュワーの〈この文書を引用〉が、引用表記に添える日付（assets/viewer-tools.js）。data/catalog.xml の文書のうち本文の XML
# （<ref type="xml">）を持つものについて、その XML を最後に変えたコミットの日付（git log -1 --format=%cs -- ファイル）を書く。
# まだコミットしていない変更のあるファイルは今日の日付にする（直したその日にコミットすれば、コミットの日付と同じになる）。
# git を使えないときは日付を空にする。--check では、文書とファイルの対応だけを比べる（日付はコミットのたびに変わるので比べない）。
def git_dates(paths):
    import subprocess
    try:
        run = lambda *a: subprocess.run(("git",) + a, cwd=OUTDIR, capture_output=True, text=True, check=True).stdout
        dirty = {line[3:].strip() for line in run("status", "--porcelain", "--", *paths).splitlines()}
        dates, cur = {}, None
        for line in run("log", "--format=@%cs", "--name-only", "--", *paths).splitlines():
            if line.startswith("@"):
                cur = line[1:]
            elif line and line not in dates:
                dates[line] = cur
        return {p: (TODAY if p in dirty else dates.get(p, "")) for p in paths}
    except (OSError, subprocess.CalledProcessError):
        return {p: "" for p in paths}

def build_doc_dates():
    import xml.etree.ElementTree as ET
    T, XID = "{http://www.tei-c.org/ns/1.0}", "{http://www.w3.org/XML/1998/namespace}id"
    files = {}
    for b in ET.parse(os.path.join(OUTDIR, "data", "catalog.xml")).getroot().iter(T + "bibl"):
        ref = next((r.get("target") for r in b.findall(T + "ref") if r.get("type") == "xml"), None)
        if b.get("type") == "document" and ref and b.get(XID, "").startswith("doc-"):
            files[b.get(XID)[4:]] = ref
    dates = git_dates(sorted(set(files.values())))
    comment = ("自動生成ファイル: scripts/build_site.py が出力します（直接編集しない）。文書ごとの最終更新日"
               "（本文の XML を最後に変えたコミットの日付）。ビュワーの〈この文書を引用〉が読む。")
    rows = [json.dumps(k, ensure_ascii=False) + ": " + json.dumps({"file": f, "updated": dates.get(f, "")}, ensure_ascii=False)
            for k, f in files.items()]
    return ('{\n  "_comment": ' + json.dumps(comment, ensure_ascii=False) + ',\n  "docs": {\n    ' +
            ",\n    ".join(rows) + "\n  }\n}\n")   # 1 文書 1 行（日付が変わったときの差分が 1 行で済む）

# --- data/pos_labels.json（品詞タグの三言語の名前と、本文での出現数）---------------------------
# 辞書のページ（lexicon.html）の品詞の名前と、〈はじめての方へ〉（guide.html）の品詞の表が読む。名前は上の POS_NAMES が正
# （search.html の POS も同じ内容にしておく）。出現数は本文の <w type="…"> の数で、hand は人の手で注釈した本文
# （HAND_TEXTS）、draft は自動注釈の暫定版（data/catalog.xml の <bibl subtype="draft"> の本文）。
# POS_NAMES に無いタグは表に出さず、unlisted に数と出現するファイルだけを書く（誤記か正式なタグかは決めていない）。
HAND_TEXTS = ["data/eugnostos_tei.xml", "data/republic_tei.xml"]

def catalog_texts(subtype):
    """data/catalog.xml の <bibl type="document" subtype="…"> の本文の XML（<ref type="xml">）を、カタログの順に"""
    import xml.etree.ElementTree as ET
    T = "{http://www.tei-c.org/ns/1.0}"
    out = []
    for b in ET.parse(os.path.join(OUTDIR, "data", "catalog.xml")).getroot().iter(T + "bibl"):
        if b.get("type") == "document" and b.get("subtype") == subtype:
            out += [r.get("target") for r in b.findall(T + "ref") if r.get("type") == "xml" and r.get("target")]
    return out

def build_pos_labels():
    import xml.etree.ElementTree as ET
    from collections import Counter, defaultdict
    T = "{http://www.tei-c.org/ns/1.0}"
    groups = (("hand", HAND_TEXTS), ("draft", catalog_texts("draft")))
    count = {k: Counter() for k, _ in groups}
    where = defaultdict(Counter)
    for kind, files in groups:
        for rel in files:
            for el in ET.parse(os.path.join(OUTDIR, rel)).getroot().iter(T + "w"):
                t = el.get("type")
                if t:
                    count[kind][t] += 1
                    if t not in POS_NAMES:
                        where[t][rel] += 1
    row = lambda d: json.dumps(d, ensure_ascii=False)
    tags = [row({"tag": t, "ja": v[0], "en": v[1], "fr": v[2], "hand": count["hand"][t], "draft": count["draft"][t]})
            for t, v in POS_NAMES.items()]
    unlisted = [row({"tag": t, "hand": count["hand"][t], "draft": count["draft"][t], "files": dict(sorted(where[t].items()))})
                for t in sorted(where)]
    comment = ("自動生成ファイル: scripts/build_site.py が出力します（直接編集しない）。品詞タグの三言語の名前（build_site.py の POS_NAMES）と、"
               "本文の <w type> の数。hand は人の手で注釈した本文（" + "・".join(HAND_TEXTS) + "）、draft は自動注釈の暫定版（"
               + str(len(groups[1][1])) + " 文書）。unlisted は POS_NAMES に無いタグ（表には出さない）。")
    return ('{\n  "_comment": ' + json.dumps(comment, ensure_ascii=False) + ',\n  "tags": [\n    ' + ",\n    ".join(tags) +
            '\n  ],\n  "unlisted": [\n    ' + ",\n    ".join(unlisted) + '\n  ]\n}\n')

def _doc_files(text):
    """--check 用: doc_dates.json の文書とファイルの対応（日付は除く）"""
    try:
        return {k: v.get("file") for k, v in json.loads(text).get("docs", {}).items()}
    except ValueError:
        return None

# --- write ------------------------------------------------------------------
_BANNER = "<!-- 自動生成ファイル: scripts/build_site.py が出力します。直接編集せず、スクリプトの CODICES を編集して再実行してください。 -->\n"
# 全文テキストの文書ごとの数（search.html の〈統計〉の「写本全体の比較」が読む）。数え方は scripts/build_fulltext_stats.py
sys.path.insert(0, _HERE)
import build_fulltext_stats
_sitemap, _n_urls = build_sitemap()
OUTPUTS = {"index.html": _BANNER + build_index(), "tractate.html": _BANNER + build_tractate(),
           "reader.html": _BANNER + build_reader(), "sitemap.xml": _sitemap, "robots.txt": build_robots(),
           os.path.join("data", "doc_dates.json"): build_doc_dates(),
           os.path.join("data", "pos_labels.json"): build_pos_labels(),
           build_fulltext_stats.OUT: build_fulltext_stats.build()}
# 生成の日付（index.html のフッターの「生成 …」）は作り直すたびに変わるので、--check では比べない
_BUILT = re.compile(r'(<span class="l-fr">généré</span>) \d{4}-\d{2}-\d{2}')

if "--check" in sys.argv[1:]:
    stale = []
    for name, text in OUTPUTS.items():
        try:
            with open(os.path.join(OUTDIR, name), encoding="utf-8") as f:
                current = f.read()
        except OSError:
            stale.append(name + "（ファイルがありません）")
            continue
        if name.endswith("doc_dates.json"):
            if _doc_files(current) != _doc_files(text):
                stale.append(name)
        elif _BUILT.sub(r"\1", current) != _BUILT.sub(r"\1", text):
            stale.append(name)
    if stale:
        print("生成ファイルが、いまのスクリプトとデータから作り直したものと違います: " + "、".join(stale))
        print("python3 scripts/build_site.py を実行して、作り直したファイルをコミットしてください。")
        sys.exit(1)
    print("生成ファイルは最新です（%s）" % "・".join(OUTPUTS))
    sys.exit(0)

for name, text in OUTPUTS.items():
    with open(os.path.join(OUTDIR, name), "w", encoding="utf-8") as f:
        f.write(text)
print("wrote index.html (landing), tractate.html (placeholder) and reader.html (draft full texts)")
print("wrote sitemap.xml (%d URLs), robots.txt, data/doc_dates.json, data/pos_labels.json and data/fulltext_stats.json" % _n_urls)
print("codices:", len(CODICES), "| tractates:", TOTAL, "| available:", AVAIL, "| drafts:", DRAFT, "| text only:", PLAIN, "| soon:", SOON,
      "| listed but not counted:", ", ".join("%s,%s" % k for k in sorted(UNCOUNTED)))
