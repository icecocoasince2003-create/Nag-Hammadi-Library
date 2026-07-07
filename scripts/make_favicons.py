#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_favicons.py — image/icon.svg からファビコン一式を再生成する

使い方（リポジトリのルートで）:

    pip3 install cairosvg pillow   # 初回のみ
    python3 scripts/make_favicons.py

生成物:
    image/favicon-32.png        (タブ用フォールバック)
    image/favicon-192.png       (Android / PWA用)
    image/apple-touch-icon.png  (iOSホーム画面用, 180px)
    favicon.ico                 (ルート直下, ブラウザが自動要求)

icon.svg のデザインを差し替えたら、このスクリプトを実行して
上記4ファイルを更新し、まとめてコミットしてください。
"""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "scripts" else _HERE
SRC = os.path.join(ROOT, "image", "icon.svg")

try:
    import cairosvg
    from PIL import Image
except ImportError:
    sys.exit("cairosvg と pillow が必要です:  pip3 install cairosvg pillow")

if not os.path.exists(SRC):
    sys.exit("image/icon.svg が見つかりません: " + SRC)

svg = open(SRC, "rb").read()
targets = [
    (32,  os.path.join(ROOT, "image", "favicon-32.png")),
    (192, os.path.join(ROOT, "image", "favicon-192.png")),
    (180, os.path.join(ROOT, "image", "apple-touch-icon.png")),
]
for size, out in targets:
    cairosvg.svg2png(bytestring=svg, write_to=out, output_width=size, output_height=size)
    print("wrote", os.path.relpath(out, ROOT), f"({size}x{size})")

ico = os.path.join(ROOT, "favicon.ico")
Image.open(targets[0][1]).save(ico, sizes=[(32, 32), (16, 16)])
print("wrote favicon.ico (32/16)")
