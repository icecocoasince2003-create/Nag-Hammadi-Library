#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transfer_annotation.py — エウグノストス III,3 の人の手の注釈を、『イエス・キリストの知恵』III,4 の同じ文言の語群に写す案（C-9）

data/parallels.xml の par-eug-SJC（エウグノストス III,3 と III,4 のセグメントの対応。自動の照合）で結ばれたセグメントの組ごとに、
両方の本文の文字（scripts/build_parallels.py と同じそろえ方: 語の区切り・上線などの合成記号・コプト文字以外を除き、小文字）を
difflib.SequenceMatcher で比べ、MIN_BLOCK 文字以上続けて一致する範囲（文言が一致する範囲）を探す。その範囲にすっぽり入る
エウグノストスの語群（<phr>。語群の外の <w> は 1 語の語群とみなす）ごとに、III,4 の同じ文字の範囲を求め、エウグノストスの
形態素の区切り・品詞（@type）・レンマ（@lemma）・借用語の印（xml:lang="grc"）・文脈上の語釈の参照（@ana）を写す案を 1 行にする。
今の III,4 の注釈（2026-11-24 からは Coptic SCRIPTORIUM の NLP によるもの）と区切り・品詞・レンマ・借用語の印がすべて同じ語群は、
表に入れず数だけを示す。III,4 の同じ範囲が 2 つのエウグノストスのセグメントから見つかったときは、一致の長いほうの 1 行にする。

■ 案の表（source/nhc_fulltext_split/proposals/transfer_III-4.tsv。UTF-8・LF・タブ区切り）
  番号 / エウグノストス（seg_id と語群の番号）/ seg_id（III,4）/ w（III,4 の範囲の最初の <w>。その <s> の中で何番目か）/
  phr（その <w> の語群の番号）/ 語群（III,4 の文字）/ 今の注釈（III,4）/ 写す注釈（エウグノストス）/ 違い / 当てはめ /
  一致の長さ（その範囲を含む一致の文字数）/ 状態 / 確認者
  注釈は「形/品詞/レンマ」を「 · 」で並べる（借用語は (grc)、文脈上の語釈は [語釈: …]）。当てはめは「可」（III,4 の 1 つの語群と
  ちょうど同じ範囲で、復元した字〔<supplied>〕を含まない）か「不可: 理由」。状態は初め「案（生田目の確認待ち）」で、確認作業の
  画面（review.html）のキュー ⑧ で承認・却下などにする。同じ入力からは、いつも同じバイト列の表ができる。
  写す注釈はエウグノストスの今の品詞のまま（REL・PRET など、品詞をそろえる判断表 pos_harmonization.tsv で直す案のあるものを含む）。
  その判断表を当てはめたら、表を作り直してから確かめるとよい（判断の入った表は上書きしない）。

■ 当てはめ（python3 scripts/transfer_annotation.py apply）
  状態が「承認」で、当てはめが「可」の行だけ。III,4 のその <phr> の中の <w> を、エウグノストスの形態素の区切りで作り直す
  （文字は III,4 のものをそのまま使い、区切る位置だけを写す）。新しい <w> には @type・@lemma・xml:lang をエウグノストスから写し、
  resp="#transfer" を付ける。@cert は付けない（人が承認した行だけを写すので、docs/ANNOTATION_SPEC.md の「人が確かめた語からは
  @cert を削除する」に合わせる）。@ana は、形とレンマが同じ元の <w> にあればそれを残し、エウグノストスに文脈上の語釈
  （#gl-…）があれば、その <interp> を III,4 の英語の語釈表に写して指す。ヘッダーに <respStmt xml:id="transfer"> を、
  <revisionDesc> に 1 行を足す。表の「語群」と「今の注釈」が今の III,4 と違う行（注釈が変わった・もう当てはめた）は飛ばして
  報告する。何も付けなければ表示だけで、--write で書き込む。書き込む前に、本文の文字と、ほかの <w> が変わらないことを確かめる。

使い方（リポジトリのルートで）:
  python3 scripts/transfer_annotation.py                       案の表を書き、要約を表示する
  python3 scripts/transfer_annotation.py apply                 承認した行で変わる所を表示するだけ
  python3 scripts/transfer_annotation.py apply --write         III,4 の TEI に書き込む
  （試すときは --file で III,4 の TEI の場所を、--out（案のみ）・--tsv（当てはめ）で表の場所を変えられる）
"""
import argparse
import datetime
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_parallels as bp  # noqa: E402  文字のそろえ方（norm）
import insert_breaks as ib    # noqa: E402  バイト位置つきの読み込み（当てはめ）

TEI = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
XLANG = "{http://www.w3.org/XML/1998/namespace}lang"
EUG, EUG_WIT = "data/eugnostos_tei.xml", "wit-III"
SJC = "source/nhc_fulltext_split/tei/03-4_sophia-of-jesus-christ.xml"
PARALLELS, GROUP = "data/parallels.xml", "par-eug-SJC"
OUT = "source/nhc_fulltext_split/proposals/transfer_III-4.tsv"
MIN_BLOCK = 8
COLUMNS = ["番号", "エウグノストス", "seg_id", "w", "phr", "語群", "今の注釈", "写す注釈", "違い", "当てはめ", "一致の長さ", "状態", "確認者"]
STATE_DRAFT, STATE_OK = "案（生田目の確認待ち）", "承認"
SEP = " · "


def norm(s):
    return bp.norm(s)


# ---------------------------------------------------------------------------------------------- 読み込み

def eug_segments():
    """{seg_id: [(語群の番号, [<w>…])]}（語群の外の <w> は番号 0 の 1 語の語群）。glosses: {gl-…: 文字列}"""
    root = ET.parse(os.path.join(ROOT, EUG)).getroot()
    wit = next(t for t in root.iter(TEI + "text") if t.get(XID) == EUG_WIT)
    segs = {}
    for s in wit.iter(TEI + "s"):
        groups, k = [], 0

        def walk(el):
            nonlocal k
            for c in el:
                if c.tag == TEI + "phr":
                    k += 1
                    ws = list(c.iter(TEI + "w"))
                    if ws:
                        groups.append((k, ws))
                elif c.tag == TEI + "w":
                    groups.append((0, [c]))
                else:
                    walk(c)
        walk(s)
        segs[s.get(XID)] = groups
    glosses = {i.get(XID): " ".join("".join(i.itertext()).split()) for i in root.iter(TEI + "interp") if i.get(XID)}
    return segs, glosses


def sjc_segments(path):
    """{seg_id: Seg}。Seg.ws = [(<w>, 語群の番号)]（1 から）。"""
    root = ET.parse(path).getroot()
    out = {}
    for s in root.iter(TEI + "s"):
        ws, k = [], 0

        def walk(el, cur):
            nonlocal k
            for c in el:
                if c.tag == TEI + "phr":
                    k += 1
                    walk(c, k)
                elif c.tag == TEI + "w":
                    ws.append((c, cur))
                else:
                    walk(c, cur)
        walk(s, 0)
        out[s.get(XID)] = ws
    return out


def links():
    """[(エウグノストスの seg_id, III,4 の seg_id)]（ファイルの順）"""
    root = ET.parse(os.path.join(ROOT, PARALLELS)).getroot()
    grp = next(g for g in root.iter(TEI + "linkGrp") if g.get(XID) == GROUP)
    out = []
    for ln in grp.iter(TEI + "link"):
        a, b = ln.get("target").split()
        out.append((a.split("#")[1], b.split("#")[1]))
    return out


def text_of(w):
    return "".join(w.itertext())


def letter_start(where, k):
    """文字の位置 k を含む <w> の最初の文字の位置"""
    while k > 0 and where[k - 1] == where[k]:
        k -= 1
    return k


def span_text(ws, skip, count):
    """<w> の並びの文字（空白を除く）のうち、先頭の skip 文字を飛ばした count 文字（合成記号は前の字に付ける）"""
    out, n = "", 0
    for ch in "".join("".join(text_of(w).split()) for w in ws):
        if norm(ch):
            n += 1
            if n > skip + count:
                break
        if n > skip:
            out += ch
    return out


def morph(w, glosses=None):
    """「形/品詞/レンマ」（(grc)・[語釈: …] つき）"""
    f = "".join(text_of(w).split())
    s = "%s/%s/%s" % (f, w.get("type") or "", w.get("lemma") or "")
    if w.get(XLANG) == "grc":
        s += "(grc)"
    if glosses is not None:
        for p in (w.get("ana") or "").split():
            if p.startswith("#gl-"):
                s += "[語釈: %s]" % glosses.get(p[1:], p[1:])
    return s


# ---------------------------------------------------------------------------------------------- 案

def propose(sjc_path):
    eug, glosses = eug_segments()
    sjc = sjc_segments(sjc_path)
    sjc_order = {sid: i for i, sid in enumerate(sjc)}
    by_eug = {}
    for e, t in links():
        by_eug.setdefault(e, [])
        if t not in by_eug[e]:
            by_eug[e].append(t)
    found = {}            # (seg_id, 最初の w, 最後の w の次) → 行
    stats = {"groups": 0, "in_match": 0, "same": 0}
    for e, targets in by_eug.items():
        groups = eug.get(e)
        if not groups:
            continue
        targets = sorted(targets, key=lambda t: sjc_order.get(t, 10 ** 9))
        # III,4 の文字の並び: 文字ごとに (seg_id, <w> の番号〔0 から〕)
        b_chars, b_where = [], []
        for t in targets:
            for wi, (w, _k) in enumerate(sjc.get(t, [])):
                for ch in norm(text_of(w)):
                    b_chars.append(ch)
                    b_where.append((t, wi))
        a_chars, spans = [], []
        for k, ws in groups:
            start = len(a_chars)
            a_chars.extend(norm("".join(text_of(w) for w in ws)))
            spans.append((k, ws, start, len(a_chars)))
        stats["groups"] += len(spans)
        blocks = [b for b in SequenceMatcher(None, "".join(a_chars), "".join(b_chars), autojunk=False).get_matching_blocks()
                  if b.size >= MIN_BLOCK]
        for k, ws, ga, gb in spans:
            if gb == ga:
                continue
            blk = next((b for b in blocks if b.a <= ga and gb <= b.a + b.size), None)
            if blk is None:
                continue
            stats["in_match"] += 1
            ja, jb = blk.b + (ga - blk.a), blk.b + (gb - blk.a)
            where = b_where[ja:jb]
            t = where[0][0]
            row_key = None
            reason = None
            if any(x[0] != t for x in where):
                reason = "セグメントをまたぐ"
                wis = sorted({x[1] for x in where if x[0] == t})
            else:
                wis = sorted({x[1] for x in where})
            seg_ws = sjc[t]
            first, last = wis[0], wis[-1]
            # 範囲の両端が <w> の境目か
            starts = ja == 0 or b_where[ja - 1] != where[0]
            ends = jb == len(b_where) or b_where[jb] != where[-1]
            cur = [seg_ws[i][0] for i in range(first, last + 1)]
            phrs = {seg_ws[i][1] for i in range(first, last + 1)}
            if reason is None:
                if not (starts and ends):
                    reason = "語（<w>）の途中から・までの範囲"
                elif len(phrs) != 1 or 0 in phrs:
                    reason = "III,4 では語群が %d つに分かれている" % len(phrs) if 0 not in phrs else "III,4 では語群に入っていない語がある"
                else:
                    p = phrs.pop()
                    whole = [i for i, (_w, kk) in enumerate(seg_ws) if kk == p]
                    if whole != list(range(first, last + 1)):
                        reason = "III,4 の語群の一部だけ"
                    elif any(w.find(TEI + "supplied") is not None for w in cur):
                        reason = "復元した字（<supplied>）を含む"
            new = [morph(w, glosses) for w in ws]
            old = [morph(w) for w in cur]
            same_cut = [len(norm(text_of(w))) for w in ws] == [len(norm(text_of(w))) for w in cur] and starts and ends
            diffs = []
            if not same_cut:
                diffs.append("区切り")
            else:
                if any((a.get("type") or "") != (b.get("type") or "") for a, b in zip(ws, cur)):
                    diffs.append("品詞")
                if any((a.get("lemma") or "") != (b.get("lemma") or "") for a, b in zip(ws, cur)):
                    diffs.append("レンマ")
                if any((a.get(XLANG) == "grc") != (b.get(XLANG) == "grc") for a, b in zip(ws, cur)):
                    diffs.append("借用語の印")
            if any((w.get("ana") or "").find("#gl-") >= 0 for w in ws):
                diffs.append("語釈")
            if not diffs:
                stats["same"] += 1
                continue
            row_key = (t, first, ja - letter_start(b_where, ja), jb - ja)     # III,4 の同じ文字の範囲は 1 行
            row = {"エウグノストス": "%s 語群 %s" % (e, k) if k else "%s（語群の外）" % e,
                   "seg_id": t, "w": str(first + 1), "phr": str(seg_ws[first][1] or ""),
                   "語群": "".join(b_chars[ja:jb]) if reason == "セグメントをまたぐ" else span_text(cur, ja - letter_start(b_where, ja), jb - ja),
                   "今の注釈": SEP.join(old), "写す注釈": SEP.join(new), "違い": "・".join(diffs),
                   "当てはめ": "可" if reason is None else "不可: " + reason, "一致の長さ": str(blk.size),
                   "状態": STATE_DRAFT, "確認者": ""}
            prev = found.get(row_key)
            if prev is None or int(prev["一致の長さ"]) < blk.size:
                found[row_key] = row
    rows = [found[k] for k in sorted(found, key=lambda k: (sjc_order[k[0]], k[1], k[2]))]
    for i, r in enumerate(rows, 1):
        r["番号"] = str(i)
    return rows, stats


def tsv_text(rows):
    def clean(v):
        return " ".join(str(v).split())
    return "\n".join(["\t".join(COLUMNS)] + ["\t".join(clean(r[c]) for c in COLUMNS) for r in rows]) + "\n"


def cmd_propose(argv):
    ap = argparse.ArgumentParser(prog="transfer_annotation.py", description="エウグノストスの注釈を III,4 に写す案の表を作る")
    ap.add_argument("--file", default=os.path.join(ROOT, SJC), help="III,4 の TEI（既定: %s）" % SJC)
    ap.add_argument("--out", default=os.path.join(ROOT, OUT), help="表の書き先（既定: %s）" % OUT)
    a = ap.parse_args(argv)
    rows, st = propose(a.file)
    text = tsv_text(rows)
    if os.path.exists(a.out):
        with open(a.out, encoding="utf-8", newline="") as f:
            old = f.read()
        if any(r.split("\t")[COLUMNS.index("状態")] not in ("", STATE_DRAFT) for r in old.split("\n")[1:] if r):
            raise SystemExit("!! %s にはもう判断の入った行があります。作り直すと消えるので、書き込みません（別の --out に書いて比べてください）" % a.out)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    can = sum(1 for r in rows if r["当てはめ"] == "可")
    print("エウグノストスの語群 %d のうち、III,4 と %d 文字以上続けて一致する範囲に入るもの %d" % (st["groups"], MIN_BLOCK, st["in_match"]))
    print("  今の III,4 の注釈と同じ（表に入れない）%d・違う（表の行）%d（当てはめ 可 %d・不可 %d）" % (st["same"], len(rows), can, len(rows) - can))
    kinds = {}
    for r in rows:
        for d in r["違い"].split("・"):
            kinds[d] = kinds.get(d, 0) + 1
    print("  違い: " + "・".join("%s %d" % kv for kv in sorted(kinds.items(), key=lambda kv: -kv[1])))
    reasons = {}
    for r in rows:
        if r["当てはめ"] != "可":
            reasons[r["当てはめ"]] = reasons.get(r["当てはめ"], 0) + 1
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("  %s: %d" % (k, v))
    print("→ %s（%d 行）" % (os.path.relpath(a.out), len(rows)))
    return 0


# ---------------------------------------------------------------------------------------------- 当てはめ

RESP_STMT = ('<respStmt xml:id="transfer">\n'
             '{i}  <resp>annotation (bound groups, morphemes, part of speech, lemmas, contextual glosses) transferred from the hand-annotated '
             'Eugnostos III,3 where the wording is the same (scripts/transfer_annotation.py; rows approved in review.html)</resp>\n'
             '{i}  <name>Sheneset project</name>\n'
             '{i}</respStmt>')


def split_raw(raw, counts):
    """raw（<w> の文字列）を、そろえた文字の数 counts で切る（合成記号は前の字に付ける）"""
    out, cur, n, k = [], "", 0, 0
    for ch in raw:
        if norm(ch) and counts[k] == n and cur:
            out.append(cur)
            cur, n, k = "", 0, k + 1
        cur += ch
        if norm(ch):
            n += 1
    out.append(cur)
    return out


def cmd_apply(argv):
    ap = argparse.ArgumentParser(prog="transfer_annotation.py apply", description="承認した行の注釈を III,4 に当てはめる")
    ap.add_argument("--tsv", default=os.path.join(ROOT, OUT))
    ap.add_argument("--file", default=os.path.join(ROOT, SJC))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    with open(a.tsv, encoding="utf-8", newline="") as f:
        lines = [l for l in f.read().split("\n") if l]
    head = lines[0].split("\t")
    rows = [dict(zip(head, l.split("\t"))) for l in lines[1:]]
    approved = [r for r in rows if r.get("状態") == STATE_OK]
    eug, glosses = eug_segments()
    eug_ws = {}
    for sid, groups in eug.items():
        for k, ws in groups:
            eug_ws[(sid, k, morph_key(ws))] = ws
    data = open(a.file, "rb").read()
    segs, _ = ib.segments(ib.parse(data))
    edits, skipped, used_gl = [], [], set()
    for r in approved:
        why = None
        if r.get("当てはめ") != "可":
            why = "当てはめが「%s」" % r.get("当てはめ")
        seg = segs.get(r["seg_id"])
        if why is None and seg is None:
            why = "セグメントが無い"
        if why is None:
            p = int(r["phr"] or 0)
            if not 1 <= p <= len(seg.phrs):
                why = "語群 %s が無い" % r["phr"]
        if why is None:
            phr = seg.phrs[p - 1]
            wis = [i for i, k in enumerate(seg.wphr) if k == p]
            cur = [seg.ws[i] for i in wis]
            cur_txt = [ib.w_text(data, w) for w in cur]
            attrs = [w.attrs for w in cur]
            now = SEP.join("%s/%s/%s%s" % ("".join(t.split()), at.get("type", ""), at.get("lemma", ""), "(grc)" if at.get("xml:lang") == "grc" else "")
                           for t, at in zip(cur_txt, attrs))
            if "".join("".join(t.split()) for t in cur_txt) != r["語群"] or now != r["今の注釈"] or str(wis[0] + 1) != r["w"]:
                why = "今の III,4 が表と違う（注釈が変わったか、もう当てはめた）"
        if why is None:
            new = parse_morphs(r["写す注釈"])
            counts = [len(norm(m["form"])) for m in new]
            raw = "".join(cur_txt)
            if sum(counts) != len(norm(raw)) or norm(raw) != norm("".join(m["form"] for m in new)):
                why = "文字が合わない"
        if why:
            skipped.append((r["番号"], r["seg_id"], why))
            continue
        pieces = split_raw(raw, counts)
        old_ana = {("".join(t.split()), at.get("lemma", "")): at.get("ana") for t, at in zip(cur_txt, attrs) if at.get("ana")}
        indent = line_indent(data, cur[0].start)
        close_indent = line_indent(data, phr.end)
        out = []
        for m, piece in zip(new, pieces):
            ana = old_ana.get(("".join(piece.split()), m["lemma"]))
            if m["gloss"]:
                gid = gloss_id(m["gloss"], glosses)
                if gid:
                    used_gl.add(gid)
                    ana = ("#" + gid) if not ana else ana + " #" + gid
            att = ['type="%s"' % escape(m["type"])]
            if m["lemma"]:
                att.append('lemma="%s"' % escape(m["lemma"]))
            if m["grc"]:
                att.append('xml:lang="grc"')
            if ana:
                att.append('ana="%s"' % escape(ana))
            att.append('resp="#transfer"')
            out.append("\n%s<w %s>%s</w>" % (indent, " ".join(att), escape(piece, {'"': "&quot;"})))
        edits.append((phr.start_end, phr.end, "".join(out) + "\n" + close_indent, r))
    print("承認した行 %d: 当てはめる %d・飛ばした %d" % (len(approved), len(edits), len(skipped)))
    for e in edits:
        r = e[3]
        print("  + %s %s w=%s: %s → %s" % (r["番号"], r["seg_id"], r["w"], r["今の注釈"], r["写す注釈"]))
    for n, sid, why in skipped:
        print("  ? %s %s: %s" % (n, sid, why))
    if not edits:
        print("変更なし — %s は書き換えません。" % os.path.relpath(a.file))
        return 0
    text = data.decode("utf-8")
    bdata = data
    for start, end, new_text, _r in sorted(edits, key=lambda e: -e[0]):
        bdata = bdata[:start] + new_text.encode("utf-8") + bdata[end:]
    text = bdata.decode("utf-8")
    if 'xml:id="transfer"' not in text:
        m = re.search(r'\n( *)<respStmt xml:id="coptic-nlp">.*?</respStmt>', text, re.S)
        if not m:
            raise SystemExit("!! III,4 のヘッダーに <respStmt xml:id=\"coptic-nlp\"> が無いので、#transfer の説明を足す場所がありません")
        text = text[:m.end()] + "\n" + m.group(1) + RESP_STMT.format(i=m.group(1)) + text[m.end():]
    for gid in sorted(used_gl):
        if 'xml:id="%s"' % gid not in text:
            m = re.search(r'(\n( *)<interpGrp type="gloss" xml:lang="en">)', text)
            if not m:
                raise SystemExit("!! III,4 に英語の語釈表がありません")
            text = text[:m.end()] + "\n%s  <interp xml:id=\"%s\">%s</interp>" % (m.group(2), gid, escape(glosses[gid])) + text[m.end():]
    change = ('<change when="%s">Annotation of %d bound groups transferred from the hand-annotated Eugnostos III,3 where the wording is the same '
              '(rows approved in source/nhc_fulltext_split/proposals/transfer_III-4.tsv; scripts/transfer_annotation.py): morpheme boundaries, '
              '<att>type</att>, <att>lemma</att>, xml:lang and contextual glosses; <att>resp</att>="#transfer". The letters are unchanged.</change>'
              % (a.date, len(edits)))
    m = re.search(r"\n( *)</revisionDesc>", text)
    text = text[:m.start()] + "\n" + m.group(1) + "  " + change + text[m.start():]
    out = text.encode("utf-8")
    verify(data, out, edits)
    if a.write:
        with open(a.file, "wb") as f:
            f.write(out)
        print("→ %s に書き込みました（python3 scripts/check_tei.py で確かめてください）" % os.path.relpath(a.file))
    else:
        print("(dry-run: 書き込むには --write を付けてください)")
    return 0


def morph_key(ws):
    return SEP.join(morph(w) for w in ws)


def parse_morphs(s):
    out = []
    for part in s.split(SEP):
        gloss = re.findall(r"\[語釈: ([^\]]*)\]", part)
        core = re.sub(r"\[語釈: [^\]]*\]", "", part)
        grc = core.endswith("(grc)")
        core = core[:-5] if grc else core
        form, typ, lemma = (core.split("/") + ["", ""])[:3]
        out.append({"form": form, "type": typ, "lemma": lemma, "grc": grc, "gloss": gloss[0] if gloss else ""})
    return out


def gloss_id(text, glosses):
    return next((k for k, v in sorted(glosses.items()) if v == text), None)


def line_indent(data, pos):
    line_start = data.rfind(b"\n", 0, pos) + 1
    m = re.match(rb"[ \t]*", data[line_start:pos])
    return m.group(0).decode("ascii")


def verify(old, new, edits):
    """本文の文字が変わらないこと、当てはめた語群のほかの <w> が変わらないこと"""
    def words(data):
        segs, _ = ib.segments(ib.parse(data))
        letters = "".join(ib.w_text(data, w) for s in segs.values() for w in s.ws)
        return segs, letters
    so, lo = words(old)
    sn, ln = words(new)
    if norm(lo) != norm(ln):
        raise SystemExit("!! 書き換えると本文の文字が変わります — 中止")
    touched = {(e[3]["seg_id"], int(e[3]["phr"])) for e in edits}
    for sid, seg in so.items():
        a = [(ib.w_text(old, w), w.attrs) for w, k in zip(seg.ws, seg.wphr) if (sid, k) not in touched]
        nseg = sn[sid]
        b = [(ib.w_text(new, w), w.attrs) for w, k in zip(nseg.ws, nseg.wphr) if (sid, k) not in touched]
        if a != b:
            raise SystemExit("!! 書き換えると、当てはめない <w> も変わります（%s）— 中止" % sid)


def main(argv):
    if argv and argv[0] == "apply":
        return cmd_apply(argv[1:])
    return cmd_propose(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
