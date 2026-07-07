#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_icon.py — image/icon.svg を差し替えたあとにアイコンを全ページへ反映する

使い方（リポジトリのルートで。追加インストール不要・Mac標準機能で動作）:

    python3 scripts/update_icon.py

やること:
  1. image/icon.svg から image/favicon-32.png と image/apple-touch-icon.png を再生成
     （macOS標準の qlmanage + sips を使用。cairosvg が入っていればそちらを優先）
  2. republic.html / eugnostos.html / search.html の <head> に埋め込まれた
     ファビコン(data URI)を新しいデザインに書き換え
  3. scripts/build_site.py を実行して index.html / tractate.html も再生成

実行後は生成物をまとめてコミット・プッシュしてください。
"""
import base64, os, re, shutil, subprocess, sys, tempfile, urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "scripts" else _HERE
SRC = os.path.join(ROOT, "image", "icon.svg")
PNG32 = os.path.join(ROOT, "image", "favicon-32.png")
TOUCH = os.path.join(ROOT, "image", "apple-touch-icon.png")
PAGES = ["republic.html", "eugnostos.html", "search.html"]

if not os.path.exists(SRC):
    sys.exit("image/icon.svg が見つかりません: " + SRC)

# ---- 1) SVG → PNG（cairosvg → macOS qlmanage の順に試す） -------------------
def rasterize():
    try:
        import cairosvg
        svg = open(SRC, "rb").read()
        cairosvg.svg2png(bytestring=svg, write_to=PNG32, output_width=32, output_height=32)
        cairosvg.svg2png(bytestring=svg, write_to=TOUCH, output_width=180, output_height=180)
        return "cairosvg"
    except Exception:
        pass
    if shutil.which("qlmanage") and shutil.which("sips"):
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(["qlmanage", "-t", "-s", "512", "-o", td, SRC],
                               capture_output=True, text=True)
            thumb = os.path.join(td, os.path.basename(SRC) + ".png")
            if r.returncode != 0 or not os.path.exists(thumb):
                sys.exit("qlmanage でのSVG描画に失敗しました:\n" + r.stderr)
            shutil.copy(thumb, PNG32); shutil.copy(thumb, TOUCH)
            subprocess.run(["sips", "-z", "32", "32", PNG32], capture_output=True)
            subprocess.run(["sips", "-z", "180", "180", TOUCH], capture_output=True)
        return "qlmanage+sips"
    sys.exit("SVGをPNG化する手段がありません。macOSで実行するか、pip3 install cairosvg してください。")

engine = rasterize()
print("PNG再生成 (%s): image/favicon-32.png, image/apple-touch-icon.png" % engine)

# ---- 2) data URI を作って手作業管理ページの <head> を書き換え -----------------
svg_min = " ".join(open(SRC, encoding="utf-8").read().split())
svg_uri = "data:image/svg+xml," + urllib.parse.quote(svg_min, safe="=:/ '(),.-").replace('"', "%22")
png_uri = "data:image/png;base64," + base64.b64encode(open(PNG32, "rb").read()).decode()

RE_SVG = re.compile(r'<link rel="icon" type="image/svg\+xml" href="data:image/svg\+xml,[^"]*">')
RE_PNG = re.compile(r'<link rel="alternate icon" type="image/png" sizes="32x32" href="data:image/png;base64,[^"]*">')
NEW_SVG = '<link rel="icon" type="image/svg+xml" href="%s">' % svg_uri
NEW_PNG = '<link rel="alternate icon" type="image/png" sizes="32x32" href="%s">' % png_uri

for page in PAGES:
    path = os.path.join(ROOT, page)
    if not os.path.exists(path):
        print("skip（ファイルなし）:", page); continue
    t = open(path, encoding="utf-8").read()
    t, n1 = RE_SVG.subn(NEW_SVG, t)
    t, n2 = RE_PNG.subn(NEW_PNG, t)
    if n1 == n2 == 1:
        open(path, "w", encoding="utf-8").write(t)
        print("アイコン更新:", page)
    else:
        print("警告: %s のアイコンリンクを置換できませんでした (svg=%d, png=%d)" % (page, n1, n2))

# ---- 3) 生成ページ（index/tractate）の再ビルド --------------------------------
build = os.path.join(_HERE, "build_site.py")
if os.path.exists(build):
    subprocess.run([sys.executable, build], check=True)
print("完了。git add -A → commit → push してください。")
