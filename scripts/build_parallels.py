#!/usr/bin/env python3
"""build_parallels.py — 並行箇所の一覧（data/parallels.xml）を作る。

エウグノストス III,3（data/eugnostos_tei.xml の証本 wit-III）の各セグメントについて、同じ文言が残っている
箇所を次の文書から探し、TEI の <link> で結ぶ。

  * エウグノストス V,1   source/nhc_fulltext_split/tei/05-1_eugnostos.xml          （同じ文書のもう一つの写本）
  * イエス・キリストの知恵 III,4  source/nhc_fulltext_split/tei/03-4_sophia-of-jesus-christ.xml

ほかの 53 文書（『世界の起源について』II,5 / XIII,2 を含む）とは、定型句（「すべてのアイオーンとその世界」
「世界の基が置かれた時から」など、20 文字台）より長い一致が無いので、箇所どうしは結ばない。

方法（data/parallels.xml のヘッダーにも同じ説明を書く）:
  1. 両方の本文を、語の区切り（空白）・上線などの合成記号・コプト文字以外の記号を除き、小文字にそろえた
     1 本の文字列にする。
  2. difflib.SequenceMatcher（autojunk=False）で、順序を保ったまま一致する部分を探し、4 文字以上の一致だけを使う。
  3. セグメントの組ごとに一致した文字数を数え、8 文字以上（短いセグメントでは 5 文字以上で、どちらかの半分以上）
     を「対応あり」とする。
  4. 1 つのセグメントの対応先が離れて何か所にもあるとき（あいだに 4 セグメント以上）は、一致した文字数の
     いちばん多いまとまりだけを残す（ほかのまとまりも 20 文字以上一致していれば残す）。まとまりの中で一致の
     無いセグメントも、あいだを埋めて対応に含める。
  5. @cert は、セグメントの文字のうち一致した文字の割合（c）と、いちばん長い一致（L 文字）から決める:
     high = c が 0.5 以上か L が 20 以上、medium = c が 0.25 以上か L が 10 以上、low = それ以外。

自動の照合なので、言い換えられた箇所（V,1 は III,3 と訳の違う箇所が多い）は結ばれない。ビュワーは、
結ばれていないセグメントについて、前後の対応箇所のあいだにある本文を「対応は未確認」として示す。

手で確かめて足した <link>（resp="#align" の無いもの）がファイルにあるときは、書き込まずに止まる
（自動の結果で上書きして失わないため）。ただし、コーパスの外のテキストと結ぶ <linkGrp subtype="external">
（data/parallels/README.md）は手で書くもので、このスクリプトは作らない。書き直すときも、いまのファイルにある
その <linkGrp> を、そのまま（字下げも含めて）新しいファイルの末尾に残す。

使い方:  python3 scripts/build_parallels.py           # 要約と、いまの data/parallels.xml との違いを表示するだけ
         python3 scripts/build_parallels.py --write   # data/parallels.xml に書き込む
"""
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from bisect import bisect_right
from collections import defaultdict
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "parallels.xml")
TEI = "{http://www.tei-c.org/ns/1.0}"
XML = "{http://www.w3.org/XML/1998/namespace}"

SOURCE = {"path": "data/eugnostos_tei.xml", "pointer": "eugnostos_tei.xml", "witness": "wit-III"}
# (xml:id, 対応先のファイル, 対応先の文書（catalog.xml の xml:id）, @subtype, 説明 ja / en)
TARGETS = [
    ("par-eug-V1", "source/nhc_fulltext_split/tei/05-1_eugnostos.xml", "doc-V-1", "witness",
     "エウグノストスのもう一つの写本（NHC V,1）。同じ文書だが、III,3 と文言の一致しない箇所が多い。",
     "The other manuscript of Eugnostos (NHC V,1): the same text, but often worded differently from III,3."),
    ("par-eug-SJC", "source/nhc_fulltext_split/tei/03-4_sophia-of-jesus-christ.xml", "doc-III-4", "rewriting",
     "『イエス・キリストの知恵』（NHC III,4。写本 III でエウグノストスのすぐ後に書かれている）。エウグノストスと同じ文言が、"
     "救い主と弟子たちの問答の形で長く続く。BG 8502,3 にも残る（本コーパスには未収録）。",
     "The Sophia of Jesus Christ (NHC III,4, copied right after Eugnostos in Codex III): long stretches of the "
     "same wording, set as a dialogue between the Saviour and his disciples. Also extant in BG 8502,3 (not in this corpus)."),
]

MIN_BLOCK = 4        # これより短い一致は数えない
MIN_PAIR = 8         # セグメントの組で、これだけ一致すれば対応あり
MIN_PAIR_SHORT = 5   # 短いセグメント: これ以上で、どちらかの半分以上なら対応あり
GAP = 4              # 対応先のあいだがこれより離れていたら、別のまとまり
KEEP_SECOND = 20     # 2 つ目以降のまとまりを残す一致文字数
EXTERNAL = re.compile(r'\n[ \t]*<linkGrp\b[^>]*\bsubtype="external"[^>]*>.*?</linkGrp>', re.S)   # 手で書く外のテキストとの組


def norm(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^Ⲁ-⳿Ϣ-ϯ]", "", s)       # コプト文字（ギリシア文字由来＋デモティック由来）だけ


def segments(path, witness=None):
    """[(xml:id, @n, 本文)]。witness を渡すと、その証本の <text> の中だけ。"""
    root = ET.parse(os.path.join(ROOT, path)).getroot()
    texts = [t for t in root.iter(TEI + "text") if t.get("type") == "witness"]
    if witness:
        texts = [t for t in texts if t.get(XML + "id") == witness]
    out = []
    for t in texts:
        for s in t.iter(TEI + "s"):
            words = ["".join(w.itertext()) for w in s.iter(TEI + "w")]   # 戻した字の <supplied> の中も読む
            out.append((s.get(XML + "id"), s.get("n") or "", " ".join(words)))
    return out


def stream(segs):
    parts, starts, pos = [], [], 0
    for _, _, text in segs:
        n = norm(text)
        starts.append(pos)
        parts.append(n)
        pos += len(n)
    return "".join(parts), starts


def align(src, tgt):
    """{source の番号: [(target の番号の並び, 一致文字数, 最長の一致)]} と、各 source セグメントの文字数。"""
    A, As = stream(src)
    B, Bs = stream(tgt)
    lenA = [(As[i + 1] if i + 1 < len(As) else len(A)) - As[i] for i in range(len(As))]
    lenB = [(Bs[j + 1] if j + 1 < len(Bs) else len(B)) - Bs[j] for j in range(len(Bs))]
    matched = defaultdict(lambda: defaultdict(int))       # matched[i][j] = 一致した文字数
    longest = defaultdict(lambda: defaultdict(int))       # longest[i][j] = いちばん長い一致（i と j の中に収まる部分）
    for b in SequenceMatcher(None, A, B, autojunk=False).get_matching_blocks():
        if b.size < MIN_BLOCK:
            continue
        run = None
        for t in range(b.size):
            i, j = bisect_right(As, b.a + t) - 1, bisect_right(Bs, b.b + t) - 1
            matched[i][j] += 1
            run = (i, j, run[2] + 1) if run and run[:2] == (i, j) else (i, j, 1)
            longest[i][j] = max(longest[i][j], run[2])
    result = {}
    for i, row in matched.items():
        sig = sorted(j for j, m in row.items()
                     if m >= MIN_PAIR or (m >= MIN_PAIR_SHORT and (m * 2 >= lenA[i] or m * 2 >= lenB[j])))
        if not sig:
            continue
        clusters, cur = [], [sig[0]]
        for j in sig[1:]:
            if j - cur[-1] > GAP:
                clusters.append(cur)
                cur = [j]
            else:
                cur.append(j)
        clusters.append(cur)
        scored = [(sum(row[j] for j in c), c) for c in clusters]
        best = max(s for s, _ in scored)
        kept = []
        for s, c in scored:
            if s == best or s >= KEEP_SECOND:
                kept.append((list(range(c[0], c[-1] + 1)), s, max(longest[i][j] for j in c)))
        result[i] = kept
    return result, lenA


def cert(chars, length, run):
    c = chars / max(1, length)
    if c >= 0.5 or run >= 20:
        return "high"
    if c >= 0.25 or run >= 10:
        return "medium"
    return "low"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build():
    src = segments(SOURCE["path"], SOURCE["witness"])
    groups, summary = [], []
    for gid, path, doc, subtype, ja, en in TARGETS:
        tgt = segments(path)
        result, lenA = align(src, tgt)
        rel = os.path.relpath(os.path.join(ROOT, path), os.path.join(ROOT, "data"))
        links, linked_src, linked_tgt, certs = [], 0, set(), defaultdict(int)
        for i in sorted(result):
            chars = sum(s for _, s, _ in result[i])
            run = max(r for _, _, r in result[i])
            c = cert(chars, lenA[i], run)
            certs[c] += 1
            linked_src += 1
            for js, _, _ in result[i]:
                for j in js:
                    linked_tgt.add(j)
                    links.append(f'      <link target="{SOURCE["pointer"]}#{src[i][0]} {rel}#{tgt[j][0]}" cert="{c}" resp="#align"/>')
        summary.append((gid, os.path.basename(path), linked_src, len(src), len(linked_tgt), len(tgt), len(links), dict(certs)))
        groups.append("\n".join([
            f'    <linkGrp type="parallel" subtype="{subtype}" xml:id="{gid}" corresp="catalog.xml#doc-eugnostos catalog.xml#{doc}">',
            f'      <desc xml:lang="ja">{esc(ja)}</desc>',
            f'      <desc xml:lang="en">{esc(en)}</desc>',
            *links,
            "    </linkGrp>"]))
    return HEADER + "\n".join(groups) + FOOTER, summary


HEADER = "".join([
    '<?xml version="1.0" encoding="UTF-8"?>\n',
    '<!-- 並行箇所の一覧。scripts/build_parallels.py が書き出す（方法は下の encodingDesc）。\n',
    '     resp="#align" の <link> は自動の照合の結果で、スクリプトを実行し直すと作り直される。\n',
    '     手で確かめた対応を足すときは resp を付けずに書く（そのときスクリプトは上書きせずに止まる）。 -->\n',
    '<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="ja">\n',
    '  <teiHeader>\n',
    '    <fileDesc>\n',
    '      <titleStmt>\n',
    '        <title xml:lang="ja">並行箇所 — エウグノストスと同じ文言を持つ箇所</title>\n',
    '        <title xml:lang="en">Parallel passages — places that share the wording of Eugnostos</title>\n',
    '        <respStmt xml:id="align">\n',
    '          <resp>automatic alignment (scripts/build_parallels.py)</resp>\n',
    '          <name>Sheneset project</name>\n',
    '        </respStmt>\n',
    '      </titleStmt>\n',
    '      <publicationStmt>\n',
    '        <authority>Sheneset — TEI corpus of the Nag Hammadi Codices</authority>\n',
    '        <availability status="free">\n',
    '          <licence target="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</licence>\n',
    '        </availability>\n',
    '        <date when="2026-11-18">2026-11-18</date>\n',
    '      </publicationStmt>\n',
    '      <sourceDesc>\n',
    '        <p xml:lang="ja">エウグノストス III,3 の本文は <ref target="eugnostos_tei.xml">eugnostos_tei.xml</ref>（証本 wit-III）。',
    '対応先の本文は、ナグ・ハマディ写本 全文テキスト（未注釈・校訂本と未照合の作業用テキスト。',
    '<ref target="../source/nhc_fulltext_split/README_ja.md">source/nhc_fulltext_split/README_ja.md</ref>）。',
    '文書の題名と略号は <ref target="catalog.xml">catalog.xml</ref>。</p>\n',
    '        <p xml:lang="en">The text of Eugnostos III,3 is eugnostos_tei.xml (witness wit-III). ',
    'The other texts come from the unannotated full text of the Nag Hammadi Codices (a working text not yet collated with the critical editions; ',
    'source/nhc_fulltext_split/README_ja.md). Titles and sigla are in catalog.xml.</p>\n',
    '      </sourceDesc>\n',
    '    </fileDesc>\n',
    '    <encodingDesc>\n',
    '      <editorialDecl>\n',
    '        <p xml:lang="ja">各 &lt;link&gt; は、エウグノストス III,3 のセグメント（&lt;s&gt;）',
    'と、同じ文言を持つ他の文書のセグメントを結ぶ。自動の照合による: ',
    '両方の本文から語の区切り・合成記号（上線など）',
    '・記号を除いて 1 本の文字列にし、順序を保ったまま一致する 4 文字以上の部分を探した（Python の difflib.SequenceMatcher）',
    '。セグメントの組で 8 文字以上（短いセグメントでは 5 文字以上で、どちらかの半分以上）一致すれば結ぶ。',
    '1 つのセグメントの対応先が離れた何か所にもあるときは、一致のいちばん多いまとまりを残し、まとまりの中の一致の無いセグメントも含める。',
    '@cert は一致の強さ: high は、そのセグメントの文字の半分以上が一致するか、20 文字以上続けて一致するもの。',
    'medium は 4 分の 1 以上か 10 文字以上。low はそれ以外。言い換えられた箇所は結ばれていない。',
    'ほかの文書（『世界の起源について』を含む）とは、定型句より長い一致が無いので結んでいない。',
    '頁・行番号は対応先の本文に無いので、セグメントの番号（@n）で示す。</p>\n',
    '        <p xml:lang="en">Each &lt;link&gt; joins a segment (&lt;s&gt;) of Eugnostos III,3 to a segment of another text with the same wording. ',
    'The links come from an automatic comparison: ',
    'both texts were reduced to a single string without word division, combining marks (supralinear strokes etc.) or punctuation, and shared runs of four or more letters were found in order (Python difflib.SequenceMatcher). ',
    'A pair of segments is linked when at least 8 letters match (for short segments, at least 5 letters making up half of either segment). ',
    'When a segment matches several separate places, the place with the most matching letters is kept, and segments without a match inside that place are included. ',
    '@cert gives the strength of the match: high when half the letters of the segment match or a run of 20 letters matches; ',
    'medium for a quarter or a run of 10; low otherwise. Passages that were reworded are not linked. ',
    'No other text (On the Origin of the World included) shares more than stock phrases with Eugnostos, so none is linked. ',
    'The other texts have no page and line numbers, so segments are cited by number (@n).</p>\n',
    '      </editorialDecl>\n',
    '    </encodingDesc>\n',
    '  </teiHeader>\n',
    '  <standOff>\n',
])


FOOTER = """
  </standOff>
</TEI>
"""


def main():
    write = "--write" in sys.argv
    new, summary = build()
    ET.fromstring(new.encode("utf-8"))                     # 整形式であることを確かめる
    for gid, base, ns, nsrc, nt, ntgt, nl, certs in summary:
        print(f"{gid}: {base} — III,3 の {ns}/{nsrc} セグメント ↔ {nt}/{ntgt} セグメント（<link> {nl} 本、"
              + "・".join(f"{k} {certs.get(k, 0)}" for k in ("high", "medium", "low")) + "）")
    old = None
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = f.read()
        try:
            links = list(ET.fromstring(old.encode("utf-8")).iter(TEI + "link"))
        except ET.ParseError as e:
            print(f"!! 中止: いまの data/parallels.xml を XML として読めません（{e}）。書き込みません")
            return 1
        external = EXTERNAL.findall(old)
        if external:                                        # 手で書いた外のテキストとの組は、そのまま残す
            new = new.replace("\n  </standOff>", "".join(external) + "\n  </standOff>", 1)
            print("コーパスの外のテキストとの組 %d（<linkGrp subtype=\"external\">）はそのまま残します" % len(external))
        auto = [l for g in ET.fromstring(old.encode("utf-8")).iter(TEI + "linkGrp") if g.get("subtype") != "external"
                for l in g.iter(TEI + "link")]
        hand = [l for l in auto if l.get("resp") != "#align"]
        if hand:
            print(f"!! 中止: data/parallels.xml に手で足した <link> が {len(hand)} 本あります（resp=\"#align\" が無い）。"
                  "自動の結果で上書きすると失われるので、書き込みません")
            for l in hand[:5]:
                print("   ", l.get("target"))
            return 1
    if new == old:
        print("data/parallels.xml は最新です（変更なし）")
        return 0
    if not write:
        print("data/parallels.xml に" + ("差分があります" if old else "まだありません") + "。書き込むには --write を付けて実行してください")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    print("data/parallels.xml を書き出しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
