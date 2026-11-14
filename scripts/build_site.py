#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 build_site.py — サイトの外枠 (index.html / tractate.html) を生成する
==============================================================================

【共同編集者の方へ】
  実行方法（リポジトリのルートで）:

      python3 scripts/build_site.py

  出力される index.html と tractate.html は自動生成なので直接編集しない
  でください。目次の内容を変えたいときは、下の CODICES テーブルを編集して
  再実行します。

  * HOME は日本語・英語・フランス語の三言語表示です（上部ナビで切替）。
    題名は CODICES の ja / en / fr 列、その他の文言はこのファイル内の
    <span class="l-ja">…</span><span class="l-en">…</span><span class="l-fr">…</span> を編集します。
  * NEWS（更新情報）は data/news.json、関連サイトは data/links.json を編集します
    （HTML の再生成は不要。ページ表示時に読み込まれます）。
  * 上部ナビの項目は assets/site.js の NAV で全ページ共通に管理しています。

【新しい文書を「公開」に切り替える手順】
  1. ビュワー HTML（例: eugnostos.html）をルートに用意する
  2. 下の CODICES で該当行の status を S(準備中) → A(公開) に変える
  3. LINKS にリンク先（ビュワーのURL）を登録する
  4. python3 scripts/build_site.py を実行して index.html を再生成
==============================================================================
"""
import html, datetime, os, json

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() in ("source", "build", "src", "scripts") else _HERE

# --- 文書カタログ -------------------------------------------------------------
# 形式: (ローマ数字, コーデックス番号, [(文書番号, 日本語題, 英語題, フランス語題, status), ...])
#   status:  A = 公開（LINKS のビュワーへリンク） / S = 準備中（tractate.html へリンク）
A = "avail"; S = "soon"
CODICES = [
 ("I", 1, [
   (1, "使徒パウロの祈り", "The Prayer of the Apostle Paul", "Prière de l'apôtre Paul", S),
   (2, "ヤコブのアポクリュフォン(秘密の書)", "The Apocryphon of James", "Épître apocryphe de Jacques", S),
   (3, "真理の福音", "The Gospel of Truth", "Évangile de la Vérité", S),
   (4, "復活についての教え(レギノスへの手紙)", "The Treatise on the Resurrection", "Traité sur la résurrection", S),
   (5, "三部の教え", "The Tripartite Tractate", "Traité tripartite", S),
 ]),
 ("II", 2, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", "Livre des secrets de Jean", S),
   (2, "トマスによる福音書", "The Gospel of Thomas", "Évangile selon Thomas", S),
   (3, "フィリポによる福音書", "The Gospel of Philip", "Évangile selon Philippe", S),
   (4, "アルコーンの本質(支配者たちの本質)", "The Hypostasis of the Archons", "Hypostase des archontes", S),
   (5, "世界の起源について(無題文書)", "On the Origin of the World", "Écrit sans titre (L'Origine du monde)", S),
   (6, "魂の解明", "The Exegesis on the Soul", "Exégèse de l'âme", S),
   (7, "闘技者トマスの書", "The Book of Thomas the Contender", "Livre de Thomas", S),
 ]),
 ("III", 3, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", "Livre des secrets de Jean", S),
   (2, "エジプト人の福音書(聖なる不可視の霊の書)", "The Gospel of the Egyptians", "Livre sacré du Grand Esprit invisible (Évangile des Égyptiens)", S),
   (3, "祝福されたエウグノストス", "Eugnostos the Blessed", "Eugnoste le Bienheureux", A),
   (4, "イエス・キリストの知恵(ソフィア)", "The Sophia of Jesus Christ", "Sagesse de Jésus-Christ", S),
   (5, "救い主の対話", "The Dialogue of the Savior", "Dialogue du Sauveur", S),
 ]),
 ("IV", 4, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", "Livre des secrets de Jean", S),
   (2, "エジプト人の福音書", "The Gospel of the Egyptians", "Évangile des Égyptiens", S),
 ]),
 ("V", 5, [
   # III,3 は末尾標題「祝福されたエウグノストス」、V,1 は標題「エウグノストス」のみが残る
   (1, "エウグノストス", "Eugnostos", "Eugnoste", A),
   (2, "パウロの黙示録", "The Apocalypse of Paul", "Apocalypse de Paul", S),
   (3, "ヤコブの黙示録(第一)", "The (First) Apocalypse of James", "Première apocalypse de Jacques", S),
   (4, "ヤコブの黙示録(第二)", "The (Second) Apocalypse of James", "Seconde apocalypse de Jacques", S),
   (5, "アダムの黙示録", "The Apocalypse of Adam", "Apocalypse d'Adam", S),
 ]),
 ("VI", 6, [
   (1, "ペテロと十二使徒の行伝", "The Acts of Peter and the Twelve Apostles", "Actes de Pierre et des douze apôtres", S),
   (2, "雷・全きヌース(完全なる心)", "The Thunder, Perfect Mind", "Le Tonnerre, intellect parfait", S),
   (3, "権威ある教え", "Authoritative Teaching", "Authentikos Logos", S),
   (4, "われらの大いなる力の概念", "The Concept of Our Great Power", "Le Concept de notre grande puissance", S),
   (5, "プラトン『国家』588A–589B", "Plato, Republic 588a–589b", "Platon, République 588a–589b", A),
   (6, "第八と第九についての講話", "The Discourse on the Eighth and Ninth", "L'Ogdoade et l'Ennéade", S),
   (7, "感謝の祈り", "The Prayer of Thanksgiving", "Prière d'action de grâces", S),
   (8, "書記による覚書", "Scribal Note", "Note du scribe", S),
   (9, "アスクレピオス 21–29", "Asclepius 21–29", "Asclépius 21–29", S),
 ]),
 ("VII", 7, [
   (1, "セームの釈義(パラフレイズ)", "The Paraphrase of Shem", "Paraphrase de Sem", S),
   (2, "大セツの第二の教え", "The Second Treatise of the Great Seth", "Deuxième traité du Grand Seth", S),
   (3, "ペテロの黙示録", "The Apocalypse of Peter", "Apocalypse de Pierre", S),
   (4, "シルワノスの教え", "The Teachings of Silvanus", "Les Leçons de Silvanos", S),
   (5, "セツの三つの碑", "The Three Steles of Seth", "Les Trois Stèles de Seth", S),
 ]),
 ("VIII", 8, [
   (1, "ゾストリアノス", "Zostrianos", "Zostrien", S),
   (2, "ペテロからフィリポへの手紙", "The Letter of Peter to Philip", "Lettre de Pierre à Philippe", S),
 ]),
 ("IX", 9, [
   (1, "メルキゼデク", "Melchizedek", "Melchisédek", S),
   (2, "ノレアの思想", "The Thought of Norea", "Noréa", S),
   (3, "真理の証言", "The Testimony of Truth", "Le Témoignage véritable", S),
 ]),
 ("X", 10, [
   (1, "マルサネス", "Marsanes", "Marsanès", S),
 ]),
 ("XI", 11, [
   (1, "認識の解明", "The Interpretation of Knowledge", "Interprétation de la gnose", S),
   (2, "ヴァレンティノス派の講解", "A Valentinian Exposition", "Exposé valentinien", S),
   (3, "アロゲネス", "Allogenes", "Allogène", S),
   (4, "ヒュプシフロネ", "Hypsiphrone", "Hypsiphroné", S),
 ]),
 ("XII", 12, [
   (1, "セクストスの金言", "The Sentences of Sextus", "Sentences de Sextus", S),
   (2, "真理の福音(断片)", "The Gospel of Truth (fragments)", "Évangile de la Vérité (fragments)", S),
   (3, "断片", "Fragments", "Fragments", S),
 ]),
 ("XIII", 13, [
   (1, "三形態の原初思想(トリモルフォス・プロテンノイア)", "Trimorphic Protennoia", "Prôtennoia trimorphe", S),
   (2, "世界の起源について(冒頭部)", "On the Origin of the World (excerpt)", "Écrit sans titre (extrait)", S),
 ]),
]

# 公開文書のリンク先（status A の行）
LINKS = {
    ("III", 3): "eugnostos.html?wit=III",
    ("V", 1):   "eugnostos.html?wit=V",
    ("VI", 5):  "republic.html",
}

def esc(s): return html.escape(str(s), quote=True)
def tid(roman, num): return f"{roman}-{num}"
def locus(roman, num): return f"NHC&nbsp;{roman},{num}"
def href_for(roman, num, status):
    if status == A and (roman, num) in LINKS: return LINKS[(roman, num)]
    return f"tractate.html?id={tid(roman,num)}"
def tri(ja, en, fr):
    """三言語のスパン（site.css が html[data-lang] に応じて出し分ける）"""
    return f'<span class="l-ja">{ja}</span><span class="l-en">{en}</span><span class="l-fr">{fr}</span>'

TOTAL = sum(len(t) for _,_,t in CODICES)
AVAIL = sum(1 for _,_,t in CODICES for x in t if x[4] == A)
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
 'family=Spectral:ital,wght@0,400;0,500;0,600;1,400&'
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

THEME = """
:root{
 --bg:#f3eede; --panel:#fbf8f1; --panel-2:#f6f1e6;
 --ink:#2a2620; --ink-soft:#4c4338; --ink-faint:#8c7f6c;
 --chrome:#1c1a38; --chrome-ink:#e9e6f5; --chrome-faint:#a7a2c6;
 --gold:#9a7220; --gold-soft:#b89042; --lapis:#33529a; --rose:#9c4a63;
 --line:#e4dac6; --line-2:rgba(255,255,255,.14); --hi:#efe7d4;
 --disp:'Spectral',Georgia,serif; --ui:'Inter','Noto Sans JP',system-ui,sans-serif;
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
        cls = "trow" + (" on" if on else "")
        pill = (f'<span class="pill on">{tri("公開","Online","En ligne")}</span>' if on
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
    n = len(tracts)
    count = tri(f"{n} 文書", f"{n} tractate{'s' if n>1 else ''}", f"{n} traité{'s' if n>1 else ''}")
    return (f'<section class="codex" data-codex="{roman}">'
            f'<div class="chead"><span class="rn">{roman}</span>'
            f'<div class="ct"><b>Codex {roman}</b><small>NHC&nbsp;{roman} · {count}</small></div></div>'
            f'<div class="tlist">{"".join(rows)}</div></section>')

INDEX_CSS = """
.hero{padding:clamp(34px,7vw,76px) 0 18px; display:grid;
 grid-template-columns:minmax(0,1fr) auto; gap:30px; align-items:center}
.hero-fig{width:clamp(150px,20vw,240px); aspect-ratio:1; border-radius:50%;
 object-fit:cover; object-position:center 24%; border:1px solid rgba(212,175,106,.45);
 box-shadow:0 0 60px rgba(157,139,224,.25)}
@media(max-width:680px){ .hero{grid-template-columns:1fr} .hero-fig{display:none} }
.eyebrow{font-family:var(--ui); font-size:.74rem; letter-spacing:.22em; text-transform:uppercase; color:var(--gold)}
.hero h1{font-family:var(--disp); font-weight:600; line-height:1.1; margin:.32em 0 .16em;
 font-size:clamp(2.1rem,5.4vw,3.4rem)}
.hero h1 .cop{display:block; font-size:.5em; color:var(--gold-soft); letter-spacing:.04em; margin-bottom:.18em}
.hero h1 .tag{display:block; font-size:.4em; font-weight:500; color:var(--ink-soft); letter-spacing:.02em; margin-top:.45em}
html[data-lang="ja"] .hero h1 .l-ja{font-family:'Noto Serif JP',serif; letter-spacing:.02em}
.hero .lead{max-width:64ch; color:var(--ink-soft); font-size:1.02rem; line-height:1.8}
.hero .lead b{color:var(--ink)}
.hero .more{display:flex; flex-wrap:wrap; gap:6px 22px; margin-top:14px; font-size:.86rem}
.hero .more a{color:var(--gold-bright,var(--gold)); text-decoration:none; text-underline-offset:5px}
.hero .more a:hover{text-decoration:underline}

.sec-h{display:flex; align-items:baseline; gap:12px; margin:46px 0 14px}
.sec-h h2{font-family:'Cinzel','Spectral',serif; font-weight:500; letter-spacing:.12em; font-size:1.02rem;
 color:var(--gold); margin:0; text-transform:uppercase}
.sec-h small{color:var(--ink-faint); font-size:.78rem}
.sec-h .rule{flex:1; height:1px; background:linear-gradient(90deg,var(--line),transparent)}

.features{display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:14px}
.feat{display:grid; grid-template-columns:minmax(0,1fr); gap:18px; align-items:center;
 background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px 20px}
.feat .k{font-size:.66rem; letter-spacing:.16em; text-transform:uppercase; color:var(--gold)}
.feat .ttl{font-family:var(--disp); font-size:1.1rem; margin:2px 0 3px}
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
.news time{font-family:var(--disp); color:var(--gold); font-variant-numeric:tabular-nums; font-size:.86rem}
.news .tx{color:var(--ink-soft); font-size:.88rem; line-height:1.7}
.news .tx b{color:var(--ink)}
.news .tx a{color:var(--lapis)}
.news .more-news{background:none; border:0; color:var(--ink-faint); cursor:pointer; padding:10px 0; font:inherit; font-size:.8rem;
 text-underline-offset:5px}
.news .more-news:hover{text-decoration:underline}
.relsite{display:block; text-decoration:none; background:var(--panel); border:1px solid var(--line);
 border-radius:16px; padding:18px 20px; margin-bottom:12px; transition:border-color .15s}
.relsite:hover{border-color:var(--gold)}
.relsite .k{font-size:.64rem; letter-spacing:.16em; text-transform:uppercase; color:var(--gold)}
.relsite .t{font-family:var(--disp); font-size:1.08rem; margin:4px 0 2px; color:var(--ink)}
.relsite .t .cop{color:var(--gold-soft); margin-right:.3em}
.relsite .u{font-size:.72rem; color:var(--ink-faint)}
.relsite p{font-size:.84rem; color:var(--ink-soft); line-height:1.7; margin:8px 0 0}
.relsite .go{display:inline-block; margin-top:8px; font-size:.8rem; color:var(--gold-bright,var(--gold))}
.relsite:hover .go{text-decoration:underline}

.ctool{display:flex; align-items:center; gap:10px; margin:0 0 16px; padding:8px 0;
 border-bottom:1px solid var(--line)}
.ctool svg{width:16px; height:16px; color:var(--ink-faint); flex:none}
.ctool input{flex:1; background:none; border:0; outline:0; color:var(--ink); font-family:var(--ui); font-size:.92rem}
.ctool input::placeholder{color:var(--ink-faint)}
.ctool .cnt{font-size:.74rem; color:var(--ink-faint); white-space:nowrap}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(370px,1fr)); gap:18px; padding-bottom:30px}
.codex{background:var(--panel); border:1px solid var(--line); border-radius:16px; overflow:hidden;
 display:flex; flex-direction:column}
.chead{display:flex; align-items:center; gap:12px; padding:14px 16px 10px}
.chead .rn{font-family:var(--disp); font-size:2.2rem; font-weight:600; color:var(--gold-soft);
 opacity:.55; min-width:1.6em; text-align:center; line-height:1}
.chead .ct b{font-family:var(--disp); font-size:1.04rem}
.chead .ct small{display:block; color:var(--ink-faint); font-size:.73rem; letter-spacing:.04em}
.tlist{display:flex; flex-direction:column; padding:4px 8px 10px}
.trow{display:grid; grid-template-columns:auto 1fr auto auto auto; align-items:center; gap:10px;
 padding:9px 10px; border-radius:10px; text-decoration:none; color:inherit; transition:background .12s}
.trow:hover{background:var(--panel-2)}
.trow .tn{font-family:var(--disp); color:var(--ink-faint); font-size:.92rem; min-width:1.4em; text-align:center}
.trow .tt{min-width:0}
.trow .tt .main{display:block; font-size:.92rem; font-weight:500; color:var(--ink)}
html[data-lang="ja"] .trow .tt .main{font-family:var(--jp)}
html[data-lang="en"] .trow .tt .main, html[data-lang="fr"] .trow .tt .main{font-family:var(--disp); font-size:.98rem}
.trow .tt .sub{display:block; font-family:var(--disp); font-style:italic; font-size:.78rem; color:var(--ink-faint)}
html[data-lang="en"] .trow .tt .sub{font-family:var(--jp); font-style:normal; font-size:.74rem}
.trow .loc{font-size:.7rem; color:var(--ink-faint); white-space:nowrap; font-variant-numeric:tabular-nums}
.pill{font-size:.66rem; letter-spacing:.06em; padding:3px 9px; border-radius:999px;
 background:var(--hi); color:var(--ink-faint); border:1px solid var(--line); white-space:nowrap}
.pill.on{background:var(--gold); color:#1a140a; border-color:var(--gold); font-weight:600}
.trow .arr{color:var(--ink-faint); opacity:0; transition:opacity .12s, transform .12s; transform:translateX(-3px)}
.trow:hover .arr{opacity:1; transform:none}
.trow.on{outline:1px solid rgba(154,114,32,.28)}
.trow.on:hover{background:var(--hi)}
.empty{grid-column:1/-1; text-align:center; color:var(--ink-faint); padding:40px}
footer{position:relative; z-index:1; border-top:1px solid var(--line); color:var(--ink-faint); font-size:.78rem; padding:22px 0 50px; margin-top:30px}
footer .wrap{display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center}
footer b{color:var(--ink-soft)}
footer a{color:var(--ink-soft); text-decoration:none; text-underline-offset:4px}
footer a:hover{text-decoration:underline}
@media(max-width:520px){ .trow{grid-template-columns:auto 1fr auto; } .trow .loc,.trow .arr{display:none} }
section[id]{scroll-margin-top:70px}
"""

def build_index():
    blocks = "\n".join(codex_block(r,n,t) for r,n,t in CODICES)
    body = f"""
<nav id="sitebar" class="sitebar sticky"></nav>

<div class="wrap">
 <section class="hero">
  <div>
   <div class="eyebrow">Nag Hammadi Codices I–XIII</div>
   <h1><span class="cop">ϣⲉⲛⲉⲥⲏⲧ</span>Sheneset<span class="tag">{tri("ナグ・ハマディ写本コーパス", "A digital TEI edition of the Nag Hammadi Codices", "Édition numérique TEI des codices de Nag Hammadi")}</span></h1>
   <p class="lead">{tri(
     f"ナグ・ハマディ写本(全13冊・約{TOTAL}文書)を、<b>形態素グロス・コプト語辞書・神学注釈・日英仏訳</b>を備えた TEI&nbsp;P5 デジタル版として整備するプロジェクトです。各語をクリックすると語義が表示され、写本どうしの対照、注釈の併読ができます。",
     f"A digital TEI&nbsp;P5 edition of the Nag Hammadi Codices (13 codices, some {TOTAL} tractates), with <b>morpheme-level glosses, a Coptic lexicon, theological notes and Japanese, English and French translations</b>. Click any word for its sense, compare the manuscript witnesses side by side and read the commentary alongside the text.",
     f"Une édition numérique TEI&nbsp;P5 des codices de Nag Hammadi (13 codices, quelque {TOTAL} traités), avec <b>gloses morphologiques, lexique copte, notes théologiques et traductions japonaise, anglaise et française</b>. Cliquez sur un mot pour en voir le sens, comparez les témoins manuscrits et lisez le commentaire en regard du texte.")}</p>
   <div class="more">
     <a href="gnosticism.html">{tri("グノーシス主義とは →", "What is Gnosticism? →", "Qu'est-ce que le gnosticisme ? →")}</a>
     <a href="project.html">{tri("このプロジェクトについて →", "About the project →", "À propos du projet →")}</a>
     <a href="#corpus">{tri("文書一覧へ ↓", "Browse the codices ↓", "Parcourir les codices ↓")}</a>
   </div>
  </div>
  <img class="hero-fig" src="image/web/gengen_guide.svg" alt="" loading="lazy">
 </section>

 <div class="sec-h"><h2>{tri("公開中のテキスト", "Published texts", "Textes publiés")}</h2><span class="rule"></span></div>
 <div class="features">
   <div class="feat">
     <div>
       <div class="k">NHC III,3 / V,1</div>
       <div class="ttl"><span class="cop">ⲉⲩⲅⲛⲱⲥⲧⲟⲥ</span>{tri("エウグノストス", "Eugnostos", "Eugnoste")}</div>
       <div class="loc">{tri(
         "III,3『祝福されたエウグノストス』／ V,1『エウグノストス』· 二証本対照・三言語対訳",
         "III,3 <i>Eugnostos the Blessed</i> / V,1 <i>Eugnostos</i> · two witnesses, three translations",
         "III,3 <i>Eugnoste le Bienheureux</i> / V,1 <i>Eugnoste</i> · deux témoins, trois traductions")}</div>
       <div class="acts"><a class="go" href="eugnostos.html?wit=III">{tri("III,3 を読む →", "Read III,3 →", "Lire III,3 →")}</a>
        <a href="eugnostos.html?wit=V">{tri("V,1 を読む", "Read V,1", "Lire V,1")}</a>
        <a href="eugnostos.html?wit=SYN">{tri("対照表示", "Synopsis", "Synopse")}</a>
        <a href="search.html?doc=eugnostos">{tri("検索", "Search", "Recherche")}</a>
        <a href="search.html?doc=eugnostos&amp;view=stats">{tri("統計", "Statistics", "Statistiques")}</a></div>
     </div>
   </div>
   <div class="feat">
     <div>
       <div class="k">NHC VI,5</div>
       <div class="ttl"><span class="cop">ⲡⲟⲗⲓⲧⲉⲓⲁ</span>{tri("プラトン『国家』588b–589b", "Plato, <i>Republic</i> 588b–589b", "Platon, <i>République</i> 588b–589b")}</div>
       <div class="loc">{tri("ギリシア語原文対照・IIIFファクシミリ", "Greek parallel text · IIIF facsimile", "Texte grec en regard · fac-similé IIIF")}</div>
       <div class="acts"><a class="go" href="republic.html">{tri("全文を読む →", "Read the text →", "Lire le texte →")}</a>
        <a href="search.html?doc=republic">{tri("検索", "Search", "Recherche")}</a>
        <a href="search.html?doc=republic&amp;view=stats">{tri("統計", "Statistics", "Statistiques")}</a></div>
     </div>
   </div>
 </div>

 <div class="two">
  <section id="news">
   <div class="sec-h"><h2>News</h2><small>{tri("サイトの更新情報", "Site updates", "Mises à jour du site")}</small><span class="rule"></span></div>
   <ul class="news" id="newsList"><li><span></span><span class="tx">…</span></li></ul>
  </section>
  <section id="related">
   <div class="sec-h"><h2>{tri("関連サイト", "Related", "Sites liés")}</h2><span class="rule"></span></div>
   <div id="relList"></div>
  </section>
 </div>

 <section id="corpus">
  <div class="sec-h"><h2>{tri("文書一覧", "The codices", "Les codices")}</h2><small>NHC I–XIII</small><span class="rule"></span></div>
  <div class="ctool"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
   <input id="q" type="search" autocomplete="off">
   <span class="cnt">{tri(f"公開 {AVAIL} / 全 {TOTAL} 文書", f"{AVAIL} of {TOTAL} online", f"{AVAIL} sur {TOTAL} en ligne")}</span></div>
  <div class="grid" id="grid">
{blocks}
   <p class="empty" id="empty" hidden>{tri("該当する文書がありません。", "No matching tractate.", "Aucun traité ne correspond.")}</p>
  </div>
 </section>
</div>

<footer><div class="wrap">
  {tri(f"<b>{AVAIL}</b>&nbsp;文書を公開 / 全&nbsp;<b>{TOTAL}</b>&nbsp;文書(13写本)",
       f"<b>{AVAIL}</b>&nbsp;of&nbsp;<b>{TOTAL}</b>&nbsp;tractates online (13 codices)",
       f"<b>{AVAIL}</b>&nbsp;traités en ligne sur&nbsp;<b>{TOTAL}</b> (13 codices)")}　·
  {tri("本文はパブリックドメイン、注釈・辞書・対訳は CC&nbsp;BY&nbsp;4.0",
       "Source texts: public domain · notes, lexicon and translations: CC&nbsp;BY&nbsp;4.0",
       "Textes sources : domaine public · notes, lexique et traductions : CC&nbsp;BY&nbsp;4.0")}　·
  <a href="project.html">{tri("プロジェクトについて", "About", "À propos")}</a>　·
  <a href="privacy.html">{tri("プライバシーポリシー", "Privacy", "Confidentialité")}</a>　·　
  <a href="terms.html">{tri("利用規約", "Terms", "Conditions")}</a>　·　
  <a href="https://github.com/icecocoasince2003-create/Nag-Hammadi-Library" target="_blank" rel="noopener">GitHub</a>　·
  {tri("生成", "built", "généré")} {TODAY}
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

/* ---- NEWS（data/news.json）---- */
const SHOW=6;
fetch('data/news.json',{{cache:'no-store'}}).then(r=>r.ok?r.json():Promise.reject(r.status)).then(d=>{{
  const items=(d.items||[]).slice().sort((a,b)=>(b.date||'').localeCompare(a.date||''));
  const li=(it,i)=>'<li'+(i>=SHOW?' class="old" hidden':'')+'><time datetime="'+esc(it.date)+'">'+esc(it.date)+'</time><span class="tx">'+
     tri({{ja:it.ja,en:it.en,fr:it.fr}})+(it.link?' <a href="'+esc(it.link)+'">→</a>':'')+'</span></li>';
  const ul=document.getElementById('newsList');
  ul.innerHTML=items.map(li).join('')+(items.length>SHOW?'<li style="display:block;border:0"><button class="more-news" id="moreNews">'+tri({{ja:'過去の更新をすべて表示',en:'Show all updates',fr:'Afficher toutes les mises à jour'}})+'</button></li>':'');
  const mb=document.getElementById('moreNews');
  if(mb) mb.onclick=()=>{{ ul.querySelectorAll('li.old').forEach(x=>x.hidden=false); mb.parentNode.remove(); }};
}}).catch(()=>{{ document.getElementById('newsList').innerHTML=''; }});

/* ---- 関連サイト（data/links.json）---- */
fetch('data/links.json',{{cache:'no-store'}}).then(r=>r.ok?r.json():Promise.reject(r.status)).then(d=>{{
  document.getElementById('relList').innerHTML=(d.items||[]).map(it=>{{
    let host=''; try{{ host=new URL(it.url).host; }}catch(e){{}}
    return '<a class="relsite" href="'+esc(it.url)+'" target="_blank" rel="noopener">'+
      '<div class="k">'+tri(it.kind||{{}})+'</div>'+
      '<div class="t">'+(it.cop?'<span class="cop">'+esc(it.cop)+'</span>':'')+tri(it.title||{{}})+'</div>'+
      '<div class="u">'+esc(host)+'</div>'+
      '<p>'+tri(it.desc||{{}})+'</p>'+
      '<span class="go">'+tri({{ja:'サイトを開く ↗',en:'Visit site ↗',fr:'Visiter le site ↗'}})+'</span></a>';
  }}).join('');
}}).catch(()=>{{}});
}})();
</script>
"""
    return ("<!doctype html><html lang=\"ja\" data-lang=\"ja\" data-i18n=\"full\" data-mode=\"aeon\""
            " data-title-en=\"Sheneset — a digital TEI edition of the Nag Hammadi Codices\""
            " data-title-fr=\"Sheneset — édition numérique TEI des codices de Nag Hammadi\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Sheneset — ナグ・ハマディ写本コーパス</title>"
            "<meta name=\"description\" content=\"ナグ・ハマディ写本のTEI P5デジタル版（コプト語本文・形態素グロス・辞書・注釈・日英仏訳）/ A digital TEI edition of the Nag Hammadi Codices.\">"
            f"{FONTS}<style>{THEME}{INDEX_CSS}</style></head><body>{body}</body></html>")

# --- tractate.html (placeholder) -------------------------------------------
def build_tractate():
    cat = {}
    for roman, no, tracts in CODICES:
        for num, ja, en, fr, status in tracts:
            cat[tid(roman, num)] = {"ja": ja, "en": en, "fr": fr, "roman": roman, "num": num,
                                   "href": href_for(roman, num, status) if status == A else ""}
    css = THEME + """
.shell{position:relative; z-index:1; max-width:780px; margin:0 auto; padding:clamp(28px,6vw,64px) clamp(16px,4vw,40px) 80px}
.eyebrow{font-family:var(--ui); font-size:.74rem; letter-spacing:.2em; text-transform:uppercase; color:var(--gold)}
h1{font-family:var(--disp); font-weight:600; line-height:1.12; font-size:clamp(2rem,5.2vw,3rem); margin:.3em 0 .12em}
.alt{font-family:var(--disp); font-style:italic; color:var(--ink-faint); font-size:1.12rem}
.soon{display:inline-flex; align-items:center; gap:8px; margin-top:20px; background:var(--hi);
 border:1px solid var(--line); color:var(--ink-soft); border-radius:999px; padding:7px 15px; font-size:.82rem}
.soon .dot{width:8px; height:8px; border-radius:50%; background:var(--gold)}
.card{margin-top:26px; background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px 24px}
.card h2{font-family:var(--disp); font-weight:600; font-size:1.12rem; margin:0 0 12px}
.card p{color:var(--ink-soft); margin:0 0 14px; max-width:62ch}
.layers{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-top:6px}
.layer{background:var(--panel-2); border:1px solid var(--line); border-radius:11px; padding:12px 14px}
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
       style="float:right; width:110px; aspect-ratio:1; border-radius:50%; object-fit:cover; object-position:center 22%; border:1px solid rgba(212,175,106,.45); margin:0 0 10px 14px">
     <h2>${tri('完成時に備わる構成','What the finished edition will offer','Ce que l’édition offrira')}</h2>
     <p>${tri('本文書は本コーパスの拡張対象です。完成時には<b>エウグノストスと同一の構成</b>で公開され、同じビュワーで形態素クリック・三言語切替・注釈の併読ができるようになります。',
              'This tractate is part of the planned expansion. It will be published <b>in the same format as Eugnostos</b>: click any morpheme, switch between three languages and read the notes alongside the text.',
              'Ce traité fait partie de l’extension prévue. Il sera publié <b>au même format qu’Eugnoste</b> : gloses par morphème, trois langues et notes en regard du texte.')}</p>
     <div class="layers">
       <div class="layer"><b>${tri('本文(TEI)','Text (TEI)','Texte (TEI)')}</b><small>${tri('コプト語・形態素グロス・証本対照','Coptic, glosses, witnesses','copte, gloses, témoins')}</small></div>
       <div class="layer"><b>${tri('コプト語辞書','Coptic lexicon','Lexique copte')}</b><small>${tri('レンマ＋品詞→日英仏','lemma + POS → JA/EN/FR','lemme + catégorie → JA/EN/FR')}</small></div>
       <div class="layer"><b>${tri('注釈','Notes','Notes')}</b><small>${tri('神学的解釈・主題分類','theology, themes','théologie, thèmes')}</small></div>
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
    return ("<!doctype html><html lang=\"ja\" data-lang=\"ja\" data-i18n=\"full\" data-mode=\"aeon\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>準備中 — Sheneset</title>"
            f"{FONTS}<style>{css}</style></head><body>{body}</body></html>")

# --- write ------------------------------------------------------------------
_BANNER = "<!-- 自動生成ファイル: scripts/build_site.py が出力します。直接編集せず、スクリプトの CODICES を編集して再実行してください。 -->\n"
open(os.path.join(OUTDIR,"index.html"),"w",encoding="utf-8").write(_BANNER + build_index())
open(os.path.join(OUTDIR,"tractate.html"),"w",encoding="utf-8").write(_BANNER + build_tractate())
print("wrote index.html (landing) and tractate.html (placeholder)")
print("codices:", len(CODICES), "| tractates:", TOTAL, "| available:", AVAIL)
