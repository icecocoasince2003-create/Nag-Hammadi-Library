#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_og_image.py — リンクを共有したときのプレビュー画像 image/og-image.png（1200×630）を作る

  python3 scripts/make_og_image.py            image/og-image.png を書き出す
  python3 scripts/make_og_image.py --svg      もとの SVG も image/og-image.svg に書き出す（確認用。サイトでは使わない）

各ページの <head> の og:image（Facebook・X などのプレビュー）が指す画像です。og:image に SVG は使えないので PNG にします。
ダークテーマの背景（assets/cosmos.css の配色。2026-11-27 からデザイン B の紺の夜に 80px の淡い方眼）に、サイトのアイコン image/icon.svg と、マスコットのゲンゲン
image/web/gengen_guide.svg（左向き。アイコンのほうを向く）を置きます。題名は og:title で出るので、文字は入れません
（文字を入れると、作る環境にあるフォントで仕上がりが変わるため）。星の位置は乱数の種を固定しているので、毎回同じ画像になります。

PNG にするのに rsvg-convert（librsvg）を使います。macOS では `brew install librsvg` で入ります。
アイコンかゲンゲンを描き直したら、このスクリプトを実行し直してください。
"""
import base64
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630


def data_uri(path):
    with open(os.path.join(ROOT, path), "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode("ascii")


def stars(n=150, seed=1945):
    rnd = random.Random(seed)            # 種を固定（毎回同じ星空）
    out = []
    for _ in range(n):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice((0.6, 0.8, 0.9, 1.1, 1.3, 1.7))
        o = rnd.uniform(0.25, 0.85)
        c = rnd.choice(("#ffffff", "#ffffff", "#ece6da", "#dcc08a", "#cbd7ec"))
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" fill-opacity="%.2f"/>' % (x, y, r, c, o))
    return "".join(out)


def svg():
    icon_cx, icon_cy, icon = 335, 315, 330          # アイコン（中心と大きさ）
    gg_x, gg_y, gg = 640, 85, 470                   # ゲンゲン（左上と大きさ）
    rings = "".join('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="#efe4c6" stroke-opacity="%.2f" stroke-width="%.1f"%s/>'
                    % (icon_cx, icon_cy, r, o, w, d) for r, o, w, d in (
                        (205, .16, 1.4, ""), (250, .10, 1.2, ' stroke-dasharray="2 9"'), (300, .07, 1.0, ""), (365, .05, 1.0, "")))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
 <radialGradient id="og-sky" cx="42%" cy="46%" r="75%">
  <stop offset="0" stop-color="#2a3768"/><stop offset=".5" stop-color="#18213f"/><stop offset="1" stop-color="#0f1730"/>
 </radialGradient>
 <radialGradient id="og-glow-l"><stop offset="0" stop-color="#a9bbdb" stop-opacity=".22"/><stop offset="1" stop-color="#a9bbdb" stop-opacity="0"/></radialGradient>
 <radialGradient id="og-glow-r"><stop offset="0" stop-color="#c8a870" stop-opacity=".16"/><stop offset="1" stop-color="#c8a870" stop-opacity="0"/></radialGradient>
 <pattern id="og-grid" width="80" height="80" patternUnits="userSpaceOnUse">
  <path d="M 80 0 H 0 V 80" fill="none" stroke="#e2dcd0" stroke-opacity=".05" stroke-width="1"/>
 </pattern>
</defs>
<rect width="{W}" height="{H}" fill="url(#og-sky)"/>
<rect width="{W}" height="{H}" fill="url(#og-grid)"/>
{stars()}
<circle cx="{icon_cx}" cy="{icon_cy}" r="290" fill="url(#og-glow-l)"/>
<circle cx="{gg_x + gg // 2}" cy="{gg_y + gg // 2 + 20}" r="250" fill="url(#og-glow-r)"/>
{rings}
<image x="{icon_cx - icon // 2}" y="{icon_cy - icon // 2}" width="{icon}" height="{icon}" xlink:href="{data_uri('image/icon.svg')}"/>
<image x="{gg_x}" y="{gg_y}" width="{gg}" height="{gg}" xlink:href="{data_uri('image/web/gengen_guide.svg')}"/>
</svg>
"""


def main():
    src = svg()
    if "--svg" in sys.argv:
        with open(os.path.join(ROOT, "image", "og-image.svg"), "w", encoding="utf-8") as f:
            f.write(src)
    exe = shutil.which("rsvg-convert")
    if not exe:
        sys.exit("rsvg-convert が見つかりません（macOS: brew install librsvg）")
    out = os.path.join(ROOT, "image", "og-image.png")
    subprocess.run([exe, "--width", str(W), "--height", str(H), "--format", "png", "--output", out, "-"],
                   input=src.encode("utf-8"), check=True)
    print("wrote image/og-image.png (%d×%d, %d KB)" % (W, H, os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
