#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the Nag Hammadi corpus *site shell*:
  - index.html      … landing page / full catalogue of NHC I–XIII
  - tractate.html   … generic "coming soon" placeholder (parametric by ?id=)
The Eugnostos viewer lives in eugnostos.html (built from viewer_template.html).

Only the Eugnostos tractates (III,3 and V,1) are "available"; every other
tractate links to the placeholder so navigation works end-to-end today and new
viewers can be dropped in later by flipping a status flag.
"""
import html, datetime, os

_HERE = os.path.dirname(os.path.abspath(__file__))
# Write the site pages to the project root (this script may live in source/).
OUTDIR = os.path.dirname(_HERE) if os.path.basename(_HERE).lower() in ("source", "build", "src", "scripts") else _HERE

# --- catalogue --------------------------------------------------------------
# (roman, codex_no, [(num, ja, en, status), ...])   status: "avail" | "soon"
A = "avail"; S = "soon"
CODICES = [
 ("I", 1, [
   (1, "使徒パウロの祈り", "The Prayer of the Apostle Paul", S),
   (2, "ヤコブのアポクリュフォン(秘密の書)", "The Apocryphon of James", S),
   (3, "真理の福音", "The Gospel of Truth", S),
   (4, "復活についての教え(レギノスへの手紙)", "The Treatise on the Resurrection", S),
   (5, "三部の教え", "The Tripartite Tractate", S),
 ]),
 ("II", 2, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", S),
   (2, "トマスによる福音書", "The Gospel of Thomas", S),
   (3, "フィリポによる福音書", "The Gospel of Philip", S),
   (4, "アルコーンの本質(支配者たちの本質)", "The Hypostasis of the Archons", S),
   (5, "世界の起源について(無題文書)", "On the Origin of the World", S),
   (6, "魂の解明", "The Exegesis on the Soul", S),
   (7, "闘技者トマスの書", "The Book of Thomas the Contender", S),
 ]),
 ("III", 3, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", S),
   (2, "エジプト人の福音書(聖なる不可視の霊の書)", "The Gospel of the Egyptians", S),
   (3, "祝福されたエウグノストス", "Eugnostos the Blessed", A),
   (4, "イエス・キリストの知恵(ソフィア)", "The Sophia of Jesus Christ", S),
   (5, "救い主の対話", "The Dialogue of the Savior", S),
 ]),
 ("IV", 4, [
   (1, "ヨハネのアポクリュフォン", "The Apocryphon of John", S),
   (2, "エジプト人の福音書", "The Gospel of the Egyptians", S),
 ]),
 ("V", 5, [
   (1, "祝福されたエウグノストス", "Eugnostos the Blessed", A),
   (2, "パウロの黙示録", "The Apocalypse of Paul", S),
   (3, "ヤコブの黙示録(第一)", "The (First) Apocalypse of James", S),
   (4, "ヤコブの黙示録(第二)", "The (Second) Apocalypse of James", S),
   (5, "アダムの黙示録", "The Apocalypse of Adam", S),
 ]),
 ("VI", 6, [
   (1, "ペテロと十二使徒の行伝", "The Acts of Peter and the Twelve Apostles", S),
   (2, "雷・全きヌース(完全なる心)", "The Thunder, Perfect Mind", S),
   (3, "権威ある教え", "Authoritative Teaching", S),
   (4, "われらの大いなる力の概念", "The Concept of Our Great Power", S),
   (5, "プラトン『国家』588A–589B", "Plato, Republic 588a–589b", S),
   (6, "第八と第九についての講話", "The Discourse on the Eighth and Ninth", S),
   (7, "感謝の祈り", "The Prayer of Thanksgiving", S),
   (8, "書記による覚書", "Scribal Note", S),
   (9, "アスクレピオス 21–29", "Asclepius 21–29", S),
 ]),
 ("VII", 7, [
   (1, "セームの釈義(パラフレイズ)", "The Paraphrase of Shem", S),
   (2, "大セツの第二の教え", "The Second Treatise of the Great Seth", S),
   (3, "ペテロの黙示録", "The Apocalypse of Peter", S),
   (4, "シルワノスの教え", "The Teachings of Silvanus", S),
   (5, "セツの三つの碑", "The Three Steles of Seth", S),
 ]),
 ("VIII", 8, [
   (1, "ゾストリアノス", "Zostrianos", S),
   (2, "ペテロからフィリポへの手紙", "The Letter of Peter to Philip", S),
 ]),
 ("IX", 9, [
   (1, "メルキゼデク", "Melchizedek", S),
   (2, "ノレアの思想", "The Thought of Norea", S),
   (3, "真理の証言", "The Testimony of Truth", S),
 ]),
 ("X", 10, [
   (1, "マルサネス", "Marsanes", S),
 ]),
 ("XI", 11, [
   (1, "認識の解明", "The Interpretation of Knowledge", S),
   (2, "ヴァレンティノス派の講解", "A Valentinian Exposition", S),
   (3, "アロゲネス", "Allogenes", S),
   (4, "ヒュプシフロネ", "Hypsiphrone", S),
 ]),
 ("XII", 12, [
   (1, "セクストスの金言", "The Sentences of Sextus", S),
   (2, "真理の福音(断片)", "The Gospel of Truth (fragments)", S),
   (3, "断片", "Fragments", S),
 ]),
 ("XIII", 13, [
   (1, "三形態の原初思想(トリモルフォス・プロテンノイア)", "Trimorphic Protennoia", S),
   (2, "世界の起源について(冒頭部)", "On the Origin of the World (excerpt)", S),
 ]),
]

def esc(s): return html.escape(str(s), quote=True)
def tid(roman, num): return f"{roman}-{num}"
def locus(roman, num): return f"NHC&nbsp;{roman},{num}"
def href_for(roman, num, status):
    return "eugnostos.html" if status == A else f"tractate.html?id={tid(roman,num)}"

TOTAL = sum(len(t) for _,_,t in CODICES)
AVAIL = sum(1 for _,_,t in CODICES for x in t if x[3]==A)
TODAY = datetime.date.today().isoformat()

# --- shared head / theme ----------------------------------------------------
FONTS = ('<link rel="icon" type="image/svg+xml" href="image/icon.svg">'
 '<link rel="preconnect" href="https://fonts.googleapis.com">'
 '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
 '<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;1,400&'
 'family=Inter:wght@400;500;600&family=Noto+Sans+JP:wght@400;500;700&'
 'family=Noto+Serif+JP:wght@500;600&family=Noto+Sans+Coptic&display=swap" rel="stylesheet">')

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
html[data-mode="dark"]{
 --bg:#131228; --panel:#1b1937; --panel-2:#201e40;
 --ink:#ece9f7; --ink-soft:#c3bfe0; --ink-faint:#8a85ad;
 --chrome:#100f24; --chrome-ink:#ece9f7; --chrome-faint:#9a95bd;
 --gold:#d6ad55; --gold-soft:#caa44e; --lapis:#7d97df; --rose:#d68aa0;
 --line:#2d2a52; --line-2:rgba(255,255,255,.10); --hi:#24224a;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg); color:var(--ink); font-family:var(--ui);
 -webkit-font-smoothing:antialiased; line-height:1.6;
 background-image:radial-gradient(120% 80% at 50% -10%, var(--hi), transparent 60%);
 animation:fade .5s ease both}
@keyframes fade{from{opacity:0; transform:translateY(4px)} to{opacity:1; transform:none}}
@media (prefers-reduced-motion:reduce){ body{animation:none} }
@view-transition{ navigation:auto; }
a{color:inherit}
.cop{font-family:var(--cop)}
/* header */
header{position:sticky; top:0; z-index:5; background:var(--chrome); color:var(--chrome-ink);
 border-bottom:1px solid var(--line-2); display:flex; align-items:center; gap:14px;
 padding:11px clamp(14px,4vw,40px)}
.brand{display:flex; flex-direction:row; align-items:center; gap:9px; text-decoration:none; color:inherit}
.brand .brandlogo{flex:none; border-radius:6px}
.brand .bt{display:flex; flex-direction:column; line-height:1.15}
.brand b{font-family:var(--disp); font-weight:600; font-size:1.04rem; letter-spacing:.01em}
.brand small{color:var(--chrome-faint); font-size:.72rem; letter-spacing:.06em}
.brand .cop{color:var(--gold-soft); margin-right:.3em}
.spacer{flex:1}
.chip{appearance:none; cursor:pointer; font-family:var(--ui); font-size:.76rem;
 color:var(--chrome-ink); background:rgba(255,255,255,.07); border:1px solid var(--line-2);
 padding:7px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:6px;
 text-decoration:none; white-space:nowrap}
.chip:hover{background:rgba(255,255,255,.14)}
.search{display:flex; align-items:center; gap:7px; background:rgba(255,255,255,.08);
 border:1px solid var(--line-2); border-radius:999px; padding:6px 12px; min-width:0}
.search svg{width:15px; height:15px; color:var(--chrome-faint); flex:none}
.search input{background:none; border:0; outline:0; color:var(--chrome-ink); font-family:var(--ui);
 font-size:.82rem; width:min(34vw,230px)}
.search input::placeholder{color:var(--chrome-faint)}
.wrap{max-width:1120px; margin:0 auto; padding:0 clamp(16px,4vw,40px)}
"""

# --- index.html -------------------------------------------------------------
def codex_block(roman, no, tracts):
    rows=[]
    for num, ja, en, status in tracts:
        cls = "trow" + (" on" if status==A else "")
        pill = ('<span class="pill on">公開</span>' if status==A
                else '<span class="pill">準備中</span>')
        search = esc((ja+" "+en).lower())
        rows.append(
          f'<a class="{cls}" href="{href_for(roman,num,status)}" data-s="{search}">'
          f'<span class="tn">{num}</span>'
          f'<span class="tt"><span class="ja">{esc(ja)}</span>'
          f'<span class="en">{esc(en)}</span></span>'
          f'<span class="loc">{locus(roman,num)}</span>{pill}'
          f'<span class="arr">→</span></a>')
    return (f'<section class="codex" data-codex="{roman}">'
            f'<div class="chead"><span class="rn">{roman}</span>'
            f'<div class="ct"><b>Codex {roman}</b><small>NHC&nbsp;{roman} · {len(tracts)} tractates</small></div></div>'
            f'<div class="tlist">{"".join(rows)}</div></section>')

def build_index():
    blocks = "\n".join(codex_block(r,n,t) for r,n,t in CODICES)
    css = THEME + """
.hero{padding:clamp(34px,7vw,72px) 0 22px}
.eyebrow{font-family:var(--ui); font-size:.74rem; letter-spacing:.22em; text-transform:uppercase;
 color:var(--gold)}
.hero h1{font-family:var(--disp); font-weight:600; line-height:1.08; margin:.32em 0 .1em;
 font-size:clamp(2.1rem,5.4vw,3.4rem)}
.hero h1 .cop{display:block; font-size:.5em; color:var(--gold-soft); letter-spacing:.04em; margin-bottom:.18em}
.hero .lead{max-width:62ch; color:var(--ink-soft); font-size:1.02rem}
.hero .lead b{color:var(--ink)}
.callout{display:flex; flex-wrap:wrap; align-items:center; gap:14px; margin-top:22px;
 background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--gold);
 border-radius:14px; padding:16px 18px}
.callout .k{font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--gold)}
.callout .ttl{font-family:var(--disp); font-size:1.12rem}
.callout .ttl .cop{color:var(--gold-soft); margin-right:.35em}
.callout a.go{margin-left:auto; background:var(--lapis); color:#fff; border:0; border-radius:999px;
 padding:10px 18px; font-size:.86rem; text-decoration:none; display:inline-flex; gap:8px; align-items:center}
.callout a.go:hover{filter:brightness(1.08)}
.rule{height:1px; background:linear-gradient(90deg,transparent,var(--line),transparent); margin:30px 0 8px}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:20px; padding-bottom:60px}
.codex{background:var(--panel); border:1px solid var(--line); border-radius:16px; overflow:hidden;
 display:flex; flex-direction:column}
.chead{display:flex; align-items:center; gap:12px; padding:14px 16px 10px; position:relative}
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
.trow .tt .ja{display:block; font-family:var(--jp); font-size:.92rem; font-weight:500; color:var(--ink)}
.trow .tt .en{display:block; font-family:var(--disp); font-style:italic; font-size:.78rem; color:var(--ink-faint)}
.trow .loc{font-size:.7rem; color:var(--ink-faint); white-space:nowrap; font-variant-numeric:tabular-nums}
.pill{font-size:.66rem; letter-spacing:.06em; padding:3px 9px; border-radius:999px;
 background:var(--hi); color:var(--ink-faint); border:1px solid var(--line); white-space:nowrap}
.pill.on{background:var(--gold); color:#1a140a; border-color:var(--gold); font-weight:600}
.trow .arr{color:var(--ink-faint); opacity:0; transition:opacity .12s, transform .12s; transform:translateX(-3px)}
.trow:hover .arr{opacity:1; transform:none}
.trow.on{outline:1px solid rgba(154,114,32,.28)}
.trow.on:hover{background:var(--hi)}
.empty{grid-column:1/-1; text-align:center; color:var(--ink-faint); padding:40px}
footer{border-top:1px solid var(--line); color:var(--ink-faint); font-size:.78rem;
 padding:22px 0 50px}
footer .wrap{display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center}
footer b{color:var(--ink-soft)}
@media(max-width:520px){ .trow{grid-template-columns:auto 1fr auto; } .trow .loc,.trow .arr{display:none} }
"""
    body = f"""
<header>
  <a class="brand" href="index.html"><img class="brandlogo" src="image/icon.svg" alt="" width="30" height="30" onerror="this.style.display='none'"><span class="bt"><b><span class="cop">ⲛⲁⲅ ϩⲁⲙⲙⲁⲇⲓ</span>ナグ・ハマディ写本コーパス</b>
   <small>The Nag Hammadi Library · digital TEI edition</small></span></a>
  <span class="spacer"></span>
  <div class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
   <input id="q" type="search" placeholder="文書名で絞り込み（日・英）" autocomplete="off" aria-label="文書名で検索"></div>
  <button class="chip" id="modeBtn" title="表示モード">☀ アイオーン</button>
</header>

<div class="wrap">
 <section class="hero">
   <div class="eyebrow">Nag Hammadi Codices I–XIII</div>
   <h1><span class="cop">ⲛⲁⲅ ϩⲁⲙⲙⲁⲇⲓ</span>ナグ・ハマディ写本コーパス</h1>
   <p class="lead">ナグ・ハマディ写本(全13冊・約{TOTAL}文書)を、<b>形態素グロス・コプト語辞書・神学注釈・日英仏訳</b>を備えた
   TEI&nbsp;P5 デジタル版として整備するプロジェクトです。各文書は本文(コプト語)・辞書・注釈の3ファイルに分離し、
   共通のビュワーで読めるようにします。</p>
   <div class="callout">
     <div>
       <div class="k">現在公開中</div>
       <div class="ttl"><span class="cop">ⲉⲩⲅⲛⲱⲥⲧⲟⲥ</span>祝福されたエウグノストス <span style="color:var(--ink-faint);font-size:.85rem">— NHC III,3 / V,1</span></div>
     </div>
     <a class="go" href="eugnostos.html">読む <span aria-hidden="true">→</span></a>
   </div>
 </section>

 <div class="rule"></div>
 <div class="grid" id="grid">
{blocks}
   <p class="empty" id="empty" hidden>該当する文書がありません。</p>
 </div>
</div>

<footer><div class="wrap">
  <b>{AVAIL}</b>&nbsp;文書を公開 / 全&nbsp;<b>{TOTAL}</b>&nbsp;文書(13写本)　·　
  本文はパブリックドメイン、注釈・辞書・対訳は CC&nbsp;BY&nbsp;4.0(原文オリジナルのシード)　·　
  生成 {TODAY}
</div></footer>

<script>
const q=document.getElementById('q'), grid=document.getElementById('grid'), empty=document.getElementById('empty');
function filter(){{
  const v=(q.value||'').trim().toLowerCase();
  let shown=0;
  grid.querySelectorAll('.codex').forEach(cx=>{{
    let any=0;
    cx.querySelectorAll('.trow').forEach(r=>{{
      const hit = !v || (r.dataset.s||'').includes(v);
      r.style.display = hit?'':'none'; if(hit) any++;
    }});
    cx.style.display = any?'':'none'; shown+=any;
  }});
  empty.hidden = shown>0;
}}
q.addEventListener('input', filter);
const H=document.documentElement, mb=document.getElementById('modeBtn');
if(matchMedia&&matchMedia('(prefers-color-scheme:dark)').matches) H.setAttribute('data-mode','dark');
mb.textContent = H.getAttribute('data-mode')==='dark' ? '☾ アルコーン' : '☀ アイオーン';
mb.onclick=()=>{{ const d=H.getAttribute('data-mode')==='dark';
  H.setAttribute('data-mode', d?'light':'dark'); mb.textContent = d?'☀ アイオーン':'☾ アルコーン'; }};
</script>
"""
    return ("<!doctype html><html lang=\"ja\" data-mode=\"light\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>ナグ・ハマディ写本コーパス — Nag Hammadi Library</title>"
            f"{FONTS}<style>{css}</style></head><body>{body}</body></html>")

# --- tractate.html (placeholder) -------------------------------------------
def build_tractate():
    # inline lookup table id -> {ja,en,codex,num,status}
    items=[]
    for roman,no,tracts in CODICES:
        for num,ja,en,status in tracts:
            items.append('"%s":{ja:"%s",en:"%s",roman:"%s",num:%d,avail:%s}'
                         % (tid(roman,num), ja.replace('"','\\"'), en.replace('"','\\"'),
                            roman, num, "true" if status==A else "false"))
    cat = "{" + ",".join(items) + "}"
    css = THEME + """
.shell{max-width:780px; margin:0 auto; padding:clamp(28px,6vw,64px) clamp(16px,4vw,40px) 80px}
.eyebrow{font-family:var(--ui); font-size:.74rem; letter-spacing:.2em; text-transform:uppercase; color:var(--gold)}
h1{font-family:var(--disp); font-weight:600; line-height:1.12; font-size:clamp(2rem,5.2vw,3rem); margin:.3em 0 .12em}
.en{font-family:var(--disp); font-style:italic; color:var(--ink-faint); font-size:1.12rem}
.soon{display:inline-flex; align-items:center; gap:8px; margin-top:20px; background:var(--hi);
 border:1px solid var(--line); color:var(--ink-soft); border-radius:999px; padding:7px 15px; font-size:.82rem}
.soon .dot{width:8px; height:8px; border-radius:50%; background:var(--gold)}
.card{margin-top:26px; background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px 24px}
.card h2{font-family:var(--disp); font-weight:600; font-size:1.12rem; margin:0 0 12px}
.card p{color:var(--ink-soft); margin:0 0 14px; max-width:62ch}
.layers{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-top:6px}
.layer{background:var(--panel-2); border:1px solid var(--line); border-radius:11px; padding:12px 14px}
.layer b{display:block; font-family:var(--jp); font-size:.9rem}
.layer small{color:var(--ink-faint); font-size:.74rem}
.actions{display:flex; flex-wrap:wrap; gap:12px; margin-top:26px}
.btn{display:inline-flex; align-items:center; gap:8px; text-decoration:none; border-radius:999px;
 padding:11px 18px; font-size:.88rem; border:1px solid var(--line); color:var(--ink); background:var(--panel)}
.btn:hover{background:var(--panel-2)}
.btn.primary{background:var(--lapis); color:#fff; border-color:transparent}
.btn.primary:hover{filter:brightness(1.08)}
.rail{display:flex; gap:6px; margin:22px 0 0; opacity:.5}
.rail i{height:5px; flex:1; border-radius:3px; background:linear-gradient(90deg,var(--gold-soft),var(--lapis))}
.notfound{color:var(--ink-faint)}
"""
    body = """
<header>
  <a class="brand" href="index.html"><img class="brandlogo" src="image/icon.svg" alt="" width="30" height="30" onerror="this.style.display='none'"><span class="bt"><b><span class="cop">ⲛⲁⲅ ϩⲁⲙⲙⲁⲇⲓ</span>ナグ・ハマディ写本コーパス</b>
   <small>The Nag Hammadi Library · digital TEI edition</small></span></a>
  <span class="spacer"></span>
  <a class="chip" href="index.html">← 文書一覧</a>
  <button class="chip" id="modeBtn" title="表示モード">☀ アイオーン</button>
</header>
<main class="shell" id="shell"><p class="notfound">読み込み中…</p></main>
<script>
const CAT=__CATALOG__;
const H=document.documentElement, mb=document.getElementById('modeBtn');
if(matchMedia&&matchMedia('(prefers-color-scheme:dark)').matches) H.setAttribute('data-mode','dark');
mb.textContent = H.getAttribute('data-mode')==='dark' ? '☾ アルコーン' : '☀ アイオーン';
mb.onclick=()=>{ const d=H.getAttribute('data-mode')==='dark';
  H.setAttribute('data-mode', d?'light':'dark'); mb.textContent = d?'☀ アイオーン':'☾ アルコーン'; };
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const id=new URLSearchParams(location.search).get('id');
const t=CAT[id];
const shell=document.getElementById('shell');
if(!t){
  shell.innerHTML=`<div class="eyebrow">Nag Hammadi Codices</div>
   <h1>文書が見つかりません</h1>
   <p class="notfound">指定の文書 ID <code>${esc(id||'(なし)')}</code> は見つかりませんでした。</p>
   <div class="actions"><a class="btn primary" href="index.html">← 文書一覧へ戻る</a></div>`;
} else if(t.avail){
  location.replace('eugnostos.html');
} else {
  document.title = t.ja + ' — 準備中 · NHC '+t.roman+','+t.num;
  shell.innerHTML=`
   <div class="eyebrow">Codex ${t.roman} · NHC&nbsp;${t.roman},${t.num}</div>
   <h1>${esc(t.ja)}</h1>
   <div class="en">${esc(t.en)}</div>
   <div class="soon"><span class="dot"></span> このテキストは整備予定です（準備中）</div>
   <div class="rail"><i></i><i></i><i></i><i></i><i></i></div>
   <div class="card">
     <h2>完成時に備わる構成</h2>
     <p>本文書は本コーパスの拡張対象です。完成時には<b>エウグノストスと同一の構成</b>で公開され、
        同じビュワーで形態素クリック・三言語切替・注釈の併読ができるようになります。</p>
     <div class="layers">
       <div class="layer"><b>本文(TEI)</b><small>コプト語・形態素グロス・二証本対照</small></div>
       <div class="layer"><b>コプト語辞書</b><small>レンマ→品詞・日英仏</small></div>
       <div class="layer"><b>注釈</b><small>神学的解釈・主題分類</small></div>
       <div class="layer"><b>対訳</b><small>日本語・英語・フランス語</small></div>
     </div>
   </div>
   <div class="actions">
     <a class="btn primary" href="eugnostos.html">完成版の例：エウグノストスを見る →</a>
     <a class="btn" href="index.html">← 文書一覧へ</a>
   </div>`;
}
</script>
"""
    body = body.replace("__CATALOG__", cat)
    return ("<!doctype html><html lang=\"ja\" data-mode=\"light\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>準備中 — ナグ・ハマディ写本コーパス</title>"
            f"{FONTS}<style>{css}</style></head><body>{body}</body></html>")

# --- write ------------------------------------------------------------------
open(os.path.join(OUTDIR,"index.html"),"w",encoding="utf-8").write(build_index())
open(os.path.join(OUTDIR,"tractate.html"),"w",encoding="utf-8").write(build_tractate())
print("wrote index.html (landing) and tractate.html (placeholder)")
print("codices:", len(CODICES), "| tractates:", TOTAL, "| available:", AVAIL)
