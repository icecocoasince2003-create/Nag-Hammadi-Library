#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coptic_nlp_tei.py — Coptic SCRIPTORIUM の NLP で、TEI の本文に語群・形態素・品詞・レンマを付け直す

本文を Coptic SCRIPTORIUM の NLP（https://tools.copticscriptorium.org/coptic-nlp/）に送り、返ってきた
語群（norm_group）・形態素（norm）・品詞（pos）・レンマ（lemma）・借用語（xml:lang）を、このリポジトリの
TEI の書き方（<phr> と <w type lemma>）に戻します。構文（UD の依存関係）は TEI に入れず、--conllu を付けたときに
CoNLL-U に出します（仕様書 §5）。

変えないもの（書き出す前に確かめ、1 つでも違えば書き出さずに止まります）:
  - 各 <s> の文字（空白を除く）、<s> の xml:id と @n、<s> の外のすべて
  - <s> の中の <gap>・<supplied>・<lb>・<pb>・<cb> の数と、<supplied> の中の文字
変わるもの:
  - <s> の中の <phr>・<w> の区切りと、<w> の属性（type, lemma, xml:lang="grc", resp="#coptic-nlp", cert）
  - 語群の中に来た <lb>・<pb>・<cb> には break="no" を付ける（すでに break があればそのまま）
  - 区切りとレンマが前と同じ <w> だけ、前の @ana（語義・語釈へのポインタ）を引き継ぐ
  - ヘッダー: <titleStmt> に <respStmt xml:id="coptic-nlp">、<revisionDesc> の末尾に <change> を 1 つ足す

使い方（リポジトリのルートで）:
  python3 scripts/coptic_nlp_tei.py source/nhc_fulltext_split/tei/06-5_plato-republic.xml
      NLP にかけて build/coptic_nlp/06-5_plato-republic.xml に書き出す（元のファイルは変えない）
  python3 scripts/coptic_nlp_tei.py FILE --conllu build/coptic_nlp/FILE.conllu
      構文解析もして、CoNLL-U に出す
  python3 scripts/coptic_nlp_tei.py FILE --save-sgml build/coptic_nlp/FILE.tt
      NLP の出力（SGML）を保存する。--sgml でその出力から作り直せる（ネットにつながない）
  python3 scripts/coptic_nlp_tei.py FILE --export-request build/coptic_nlp/FILE.txt
      NLP に送る文字列だけを書き出して終わる（Web の画面に貼ったり、手元の coptic-nlp に渡したりするとき）

主な指定:
  --groups auto|keep   auto（既定）: いまの <w> を空白で区切って送り、語群は NLP が決める（laytonize=smart）。
                       keep: いまの <phr> を語群として送り、語群の区切りは変えない（人の手で語群を付けた本文向け）
  --style site|cs      site（既定）: サイトの約束に合わせる（PPERS・PPERO・PPERI → PPER、UNKNOWN → X、
                       NOUN → N、ACOND_PPERS のような融合タグ → X。人称代名詞と冠詞のレンマは語形）。
                       cs: Coptic SCRIPTORIUM の品詞とレンマのまま
  --out PATH           書き出す先（既定 build/coptic_nlp/<ファイル名>）。--in-place で元のファイルに書く
  --keep-resp ID       @resp="#ID" の <w> がある <s> は付け直さずに残す（人の注釈を写した所など）
  --cache-dir DIR      1 回ごとの NLP の出力を DIR に保存する。止まってからもう一度動かすと、送り終えた分は
                       送り直さずに使う（失敗したときのやり直しは --retries、待つ秒数は --timeout）

NLP は公開のサービスです。1 回に送るのは既定で 15,000 字まで、送るたびに 3 秒待ちます。多くの文書を
まとめて処理するときは、Coptic SCRIPTORIUM の coptic-nlp（https://github.com/CopticScriptorium/coptic-nlp）を
手元で動かし、同じ形式の SGML を --sgml で読ませてください。

標準ライブラリだけで動きます（Python 3.9 以上）。問題が無ければ終了コード 0、書き出せなかったときは 1。
"""
import argparse
import datetime
import difflib
import hashlib
import html
import http.client
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
T = "{%s}" % TEI_NS
XID = "{%s}id" % XML_NS

SERVICE = "https://tools.copticscriptorium.org/coptic-nlp/"
RESP_ID = "coptic-nlp"
USER_AGENT = "Sheneset coptic_nlp_tei.py (https://github.com/icecocoasince2003-create/Nag-Hammadi-Library)"

MILESTONES = ("lb", "pb", "cb")
# <w> の中で文字を包む要素（このまま引き継ぐ。<w> の区切りで分かれることがある）。<choice> などはまだ扱わない
WRAPPERS = ("supplied", "unclear", "del", "add", "surplus", "hi", "expan", "abbr", "ex", "am")

# Coptic SCRIPTORIUM の品詞 → UD の UPOS（https://universaldependencies.org/cop/morphology.html）
UPOS = {}
for _upos, _tags in (
        ("AUX", "AAOR ACAUS ACONJ AFUTCONJ AJUS ANEGAOR ANEGJUS ANEGOPT ANEGPST ANY AOPT APST CPRET FUT"),
        ("SCONJ", "ACOND ALIM APREC CCIRC CCOND CREL"),
        ("VERB", "EXIST V VBD VIMP VSTAT"),
        ("PRON", "COP PINT PPERI PPERO PPERS"),
        ("ADV", "ADV IMOD NEG"),
        ("DET", "ART PDEM PPOS"),
        ("PART", "CFOC PTC"),
        ("NOUN", "N NOUN"),
        ("X", "FM UNKNOWN"),
        ("CCONJ", "CONJ"),
        ("PROPN", "NPROP"),
        ("NUM", "NUM"),
        ("ADP", "PREP"),
        ("PUNCT", "PUNCT")):
    for _t in _tags.split():
        UPOS[_t] = _upos

# --style site: サイトの品詞コードへの読み替え（ほかのコードはそのまま）
SITE_POS = {"PPERS": "PPER", "PPERO": "PPER", "PPERI": "PPER", "UNKNOWN": "X", "NOUN": "N"}
# --style site: レンマを語形（NLP の norm）にする品詞（サイトの人手の注釈の書き方）
SITE_SURFACE_LEMMA = ("PPER", "ART")


class Unsupported(Exception):
    """この <s> の中身は、このスクリプトでは安全に書き換えられない。"""


class ServiceError(SystemExit):
    """NLP のサービスから結果を受け取れなかった（--retries の回数だけやり直す。やり直しても駄目なら終わる）。"""


def local(tag):
    return tag.split("}")[-1] if isinstance(tag, str) else ""


def esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(s):
    return esc_text(s).replace('"', "&quot;")


def attr_items(el):
    """要素の属性を、文書に書かれた順に (名前, 値) で返す（xml: の属性は xml:… の名前で）。"""
    out = []
    for k, v in el.attrib.items():
        if k.startswith("{%s}" % XML_NS):
            k = "xml:" + k.split("}")[1]
        elif k.startswith("{"):
            raise Unsupported("名前空間つきの属性 %s" % k)
        out.append((k, v))
    return out


def empty_element(el, extra=None):
    """子を持たない要素（<lb/> など）を、元の属性の順のまま書く。extra は (名前, 値) を末尾に足す。"""
    if len(el) or (el.text and el.text.strip()):
        raise Unsupported("<%s> に中身がある" % local(el.tag))
    items = attr_items(el)
    if extra:
        names = {k for k, _ in items}
        items += [(k, v) for k, v in extra if k not in names]
    return "<%s%s/>" % (local(el.tag), "".join(' %s="%s"' % (k, esc_attr(v)) for k, v in items))


def site_pos_names():
    """scripts/build_site.py の POS_NAMES にあるコード（報告に使う。読めなければ空）。"""
    path = os.path.join(ROOT, "scripts", "build_site.py")
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return set()
    i = src.find("POS_NAMES = {")
    j = src.find("\n}", i)
    if i < 0 or j < 0:
        return set()
    return set(re.findall(r'"([A-Z]+)"\s*:', src[i:j]))


# ---------------------------------------------------------------- TEI の <s> を読む

class Seg:
    """1 つの <s> の中身。文字の列と、そのあいだにある <lb>・<gap> など。"""

    def __init__(self, sid):
        self.sid = sid
        self.chars = []        # [(文字, 包む要素の列 ((名前, 属性), ...))]
        self.events = []       # [(位置, 順番, 種類 'm'|'gap', 要素, 包む要素の列)]  位置 = その前にある文字の数
        self.old_tokens = []   # [(始め, 終わり, 属性)]  いまの <w> の範囲
        self.old_groups = []   # [(始め, 終わり)]        いまの <phr> の範囲（<phr> の外の <w> は 1 語ずつ）
        self._seq = 0

    def add_event(self, kind, el, wrap=()):
        self.events.append((len(self.chars), self._seq, kind, el, wrap))
        self._seq += 1

    def text(self, a=0, b=None):
        return "".join(c for c, _ in self.chars[a:b])


def read_segment(s):
    seg = Seg(s.get(XID) or "")
    counter = [0]
    if s.text and s.text.strip():
        raise Unsupported("<s> の直下に文字がある")

    def add_text(text, wrap):
        for ch in text or "":
            if not ch.isspace():
                seg.chars.append((ch, wrap))

    def walk_w(el, wrap):
        add_text(el.text, wrap)
        for ch in el:
            tag = local(ch.tag)
            if tag in MILESTONES:
                seg.add_event("m", ch, wrap)
            elif tag in WRAPPERS:
                counter[0] += 1   # 同じ属性の要素が隣り合っても 1 つにまとめない
                walk_w(ch, wrap + ((tag, tuple(attr_items(ch)), counter[0]),))
            elif tag == "gap":
                raise Unsupported("<w> の中の <gap>")
            else:
                raise Unsupported("<w> の中の <%s>" % tag)
            add_text(ch.tail, wrap)

    def walk(el, in_phr):
        for ch in el:
            tag = local(ch.tag)
            if tag == "phr":
                if in_phr:
                    raise Unsupported("入れ子の <phr>")
                start = len(seg.chars)
                walk(ch, True)
                if len(seg.chars) > start:
                    seg.old_groups.append((start, len(seg.chars)))
            elif tag == "w":
                start = len(seg.chars)
                walk_w(ch, ())
                seg.old_tokens.append((start, len(seg.chars), dict(attr_items(ch))))
                if not in_phr and len(seg.chars) > start:
                    seg.old_groups.append((start, len(seg.chars)))
            elif tag == "gap":
                seg.add_event("gap", ch)
            elif tag in MILESTONES:
                seg.add_event("m", ch)
            else:
                raise Unsupported("<s> の中の <%s>" % tag)
            if ch.tail and ch.tail.strip():
                raise Unsupported("<w> の外に文字がある")

    walk(s, False)
    return seg


def chunks_of(seg):
    """<gap> で区切った文字の範囲 [(始め, 終わり)]。空の範囲は除く。"""
    cuts = sorted({ev[0] for ev in seg.events if ev[2] == "gap"})
    bounds = [0] + cuts + [len(seg.chars)]
    return [(a, b) for a, b in zip(bounds, bounds[1:]) if b > a]


def request_units(seg, a, b, groups):
    """NLP に送る単位（空白で区切る）の文字の範囲。groups='keep' なら <phr>、'auto' なら <w>。"""
    spans = seg.old_groups if groups == "keep" else [(x, y) for x, y, _ in seg.old_tokens]
    units = []
    for x, y in spans:
        x, y = max(x, a), min(y, b)
        if y > x:
            units.append((x, y))
    covered = sum(y - x for x, y in units)
    if covered != b - a:   # 範囲の外の文字があれば 1 単位として足す（ふつうは起きない）
        units = [(a, b)] if not units else units
    return units


# ---------------------------------------------------------------- NLP に送る・受け取る

def build_request(segs, groups):
    """[(chunk の ID, 送る文字列)]。chunk の ID は「<s> の xml:id~番号」。"""
    out = []
    for seg in segs:
        for k, (a, b) in enumerate(chunks_of(seg)):
            text = " ".join(seg.text(x, y) for x, y in request_units(seg, a, b, groups))
            if re.search(r"[<>&]", text):
                raise SystemExit("%s: 本文に < > & がある" % seg.sid)
            out.append(("%s~%d" % (seg.sid, k), text))
    return out


def batches(request, limit):
    """chunk を 1 回に送る分（limit 字まで）にまとめ、SGML 風の文字列にする。"""
    out, cur, size = [], [], 0
    for cid, text in request:
        piece = '<seg n="%s"> %s </seg>\n' % (esc_attr(cid), text)
        if cur and size + len(piece) > limit:
            out.append("".join(cur))
            cur, size = [], 0
        cur.append(piece)
        size += len(piece)
    if cur:
        out.append("".join(cur))
    return out


def call_service(data, service, url, detok, parse, timeout=180):
    if service == "api":
        target = urllib.parse.urljoin(url, "api")
        fields = {"data": data, "lb": "noline", "format": "sgml_entities" if parse else "sgml_no_parse"}
    else:
        target = url
        fields = {"data": data, "lb": "noline", "dialect": "auto", "sgml_mode": "sgml", "tok_mode": "auto",
                  "tok": "on", "norm": "on", "tag": "on", "lemma": "on", "lang": "on"}
        if detok != "none":
            fields["laytonize"] = detok
        if parse:
            fields["parse"] = "on"
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(target, data=body, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as e:   # URLError・HTTPError・時間切れ・接続の切断
        raise ServiceError("NLP のサービスにつながりません（%s）: %s" % (target, e))
    if service == "form":
        m = re.search(r'<textarea[^>]*id="result"[^>]*>(.*?)</textarea>', text, re.S)
        if not m:
            raise ServiceError("NLP の画面から結果を読めません（%s）。--service api を試すか、--export-request で送る文字列を"
                               "書き出して Web の画面で処理し、結果を --sgml で読ませてください。" % target)
        text = html.unescape(m.group(1))
    if "Internal Server Error" in text or "Input was too long" in text:
        raise ServiceError("NLP のサービスが処理できませんでした: %s" % text.strip()[:300])
    return text


def call_with_retries(data, a, detok, parse):
    """call_service を、失敗したら少し待って --retries 回までやり直す。"""
    for attempt in range(a.retries + 1):
        try:
            return call_service(data, a.service, a.url, detok, parse, timeout=a.timeout)
        except ServiceError as e:
            if attempt >= a.retries:
                raise
            wait = max(a.delay, 1.0) * 10 * (attempt + 1)
            print("  失敗しました（%s）。%d 秒後にやり直します" % (str(e)[:200], wait), file=sys.stderr)
            time.sleep(wait)


def cache_key(service, url, detok, parse, data):
    """--cache-dir に保存する出力の鍵（送り先・指定・送る文字列が同じなら同じ鍵）。"""
    return hashlib.sha1("\n".join((service, url, detok, str(bool(parse)), data)).encode("utf-8")).hexdigest()[:16]


TAG_RE = re.compile(r"<(/?)([A-Za-z_][\w:.\-]*)([^<>]*?)(/?)>")
ATTR_RE = re.compile(r'([\w:.\-]+)="([^"]*)"')


class Token:
    __slots__ = ("attrs", "group", "pieces", "text", "chunk", "start", "end", "split", "align")

    def __init__(self, attrs, group):
        self.attrs = attrs
        self.group = group
        self.pieces = []      # [(chunk の ID, 文字)]
        self.text = ""
        self.chunk = None
        self.start = self.end = 0
        self.split = False    # 2 つの chunk にまたがっていたので分けた
        self.align = False    # 文字の対応がずれていた


def parse_sgml(sgml):
    """NLP の出力（Coptic SCRIPTORIUM の TT SGML）から Token の列を作る。要素の入れ子が崩れていてもよい
    （<seg> は <norm> の中で開閉することがある）。返り値: (tokens, 警告の Counter)"""
    tokens, warn = [], Counter()
    cur_chunk, group, norm = None, 0, None

    def text_piece(piece):
        piece = "".join(piece.split())
        if not piece:
            return
        if norm is None:
            warn["形態素の外の文字"] += 1
            return
        norm.pieces.append((cur_chunk, html.unescape(piece)))

    pos = 0
    for m in TAG_RE.finditer(sgml):
        text_piece(sgml[pos:m.start()])
        pos = m.end()
        closing, name, rest, _self = m.groups()
        attrs = {k: html.unescape(v) for k, v in ATTR_RE.findall(rest)}
        if name == "seg":
            cur_chunk = None if closing else attrs.get("n")
        elif name == "norm_group" and not closing:
            group += 1
        elif name == "norm":
            if closing:
                norm = None
            else:
                norm = Token(attrs, group)
                tokens.append(norm)
    text_piece(sgml[pos:])

    out = []
    for t in tokens:
        chunks = []
        for c, p in t.pieces:
            if c is None:
                c = chunks[-1][0] if chunks else None
                warn["<seg> の外の文字"] += 1
            if chunks and chunks[-1][0] == c:
                chunks[-1][1].append(p)
            else:
                chunks.append((c, [p]))
        if not chunks:
            warn["文字のない形態素"] += 1
            continue
        for k, (c, ps) in enumerate(chunks):
            u = Token(t.attrs, t.group) if k else t
            u.chunk, u.text = c, unicodedata.normalize("NFC", "".join(ps))
            u.split = len(chunks) > 1
            out.append(u)
            if k:
                warn["2 つの <s> にまたがる形態素を分けた"] += 1
    return out, warn


# ---------------------------------------------------------------- 文字の位置を合わせる

def align_chunk(expected, toks, a, warn):
    """chunk の文字列 expected（全体の位置 a から）に、NLP の Token を対応させ、各 Token の start・end を決める。
    すべての文字がどれか 1 つの Token に入り、Token の順は変えない。対応しない Token は捨てる。"""
    got = "".join(t.text for t in toks)
    exp_n = unicodedata.normalize("NFC", expected)
    if got == exp_n and len(exp_n) == len(expected):
        pos = a
        for t in toks:
            t.start, t.end = pos, pos + len(t.text)
            pos = t.end
        return toks
    sm = difflib.SequenceMatcher(None, expected, got, autojunk=False)
    g2e = [-1] * len(got)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                g2e[j1 + d] = i1 + d
    kept, starts, gpos, last = [], [], 0, -1
    for t in toks:
        idx = [g2e[j] for j in range(gpos, gpos + len(t.text)) if g2e[j] >= 0]
        gpos += len(t.text)
        if not idx or idx[0] <= last:
            warn["文字が対応しない形態素を捨てた"] += 1
            continue
        kept.append(t)
        starts.append(idx[0])
        last = idx[0]
    if not kept:
        return []
    starts[0] = 0
    for i, t in enumerate(kept):
        s0, s1 = starts[i], (starts[i + 1] if i + 1 < len(kept) else len(expected))
        t.start, t.end = a + s0, a + s1
        if expected[s0:s1] != t.text:
            t.align = True
            warn["文字の対応がずれた形態素"] += 1
    return kept


# ---------------------------------------------------------------- <s> の中身を書く

def token_attrs(t, style, old_by_span, keep_ana, stats):
    pos = t.attrs.get("pos") or "UNKNOWN"
    lemma = t.attrs.get("lemma") or ""
    norm = t.attrs.get("norm") or t.text
    lang = t.attrs.get("xml:lang") or ""
    fused = "_" in pos           # ACOND_PPERS など、分けられなかった語（Coptic SCRIPTORIUM の融合タグ）
    if style == "site":
        if fused:
            stats["融合タグを X にした: " + pos] += 1
            pos = "X"
        pos = SITE_POS.get(pos, pos)
        if pos in SITE_SURFACE_LEMMA:
            lemma = norm
    items = [("type", pos)]
    if lemma and pos != "X":
        items.append(("lemma", lemma))
    if lang == "Greek":
        items.append(("xml:lang", "grc"))
    elif lang:
        stats["借用語の印を付けなかった言語: " + lang] += 1
    old = old_by_span.get((t.start, t.end))
    if keep_ana and old and old.get("ana") and old.get("lemma") == lemma:
        items.append(("ana", old["ana"]))
        stats["@ana を引き継いだ <w>"] += 1
    elif old and old.get("ana"):
        stats["@ana を引き継げなかった <w>"] += 1
    low = t.align or t.split or fused or pos in ("X", "UNKNOWN")
    items += [("resp", "#" + RESP_ID), ("cert", "low" if low else "medium")]
    stats["品詞 " + pos] += 1
    return items


def render_segment(seg, toks, style, keep_ana, indent, unit, stats):
    """<s> の新しい中身（改行と字下げつき）。toks は位置の順に並んだ Token（すべての文字を覆う）。"""
    tok_of = [None] * len(seg.chars)
    for i, t in enumerate(toks):
        for p in range(t.start, t.end):
            tok_of[p] = i
    if any(x is None for x in tok_of):
        raise Unsupported("NLP の結果が覆わない文字がある")
    group_of = [toks[i].group for i in tok_of]
    chunk_of = [toks[i].chunk for i in tok_of]
    old_by_span = {(x, y): at for x, y, at in seg.old_tokens}

    events_at = {}
    for pos, seq, kind, el, wrap in sorted(seg.events, key=lambda e: (e[0], e[1])):
        events_at.setdefault(pos, []).append((kind, el, wrap))

    blocks = []          # ('phr', [part...]) | ('line', xml)
    cur_phr = None       # その語群の部分: ('w', 属性, 中身) | ('line', xml)
    cur_w = None         # [属性, 中身の文字列]
    cur_key = None       # (chunk, group)
    cur_tok = None
    open_wrap = ()

    def set_wrappers(target):
        nonlocal open_wrap
        k = 0
        while k < len(open_wrap) and k < len(target) and open_wrap[k] == target[k]:
            k += 1
        while len(open_wrap) > k:
            cur_w[1] += "</%s>" % open_wrap[-1][0]
            open_wrap = open_wrap[:-1]
        for item in target[k:]:
            name, at = item[0], item[1]
            cur_w[1] += "<%s%s>" % (name, "".join(' %s="%s"' % (n, esc_attr(v)) for n, v in at))
            open_wrap = open_wrap + (item,)

    def close_w():
        nonlocal cur_w, cur_tok
        if cur_w is not None:
            set_wrappers(())
            cur_phr.append(("w", cur_w[0], cur_w[1]))
            cur_w, cur_tok = None, None

    def close_phr():
        nonlocal cur_phr, cur_key
        close_w()
        if cur_phr is not None:
            blocks.append(("phr", cur_phr))
            cur_phr, cur_key = None, None

    def milestone_xml(el, inside_group):
        extra = [("break", "no")] if inside_group and local(el.tag) in MILESTONES else None
        if extra and el.get("break") is None:
            stats["語群の中の改行に break=\"no\" を付けた"] += 1
        if not inside_group and el.get("break") == "no":
            stats["語群のあいだに来た break=\"no\" の改行（要確認）"] += 1
        return empty_element(el, extra)

    n = len(seg.chars)
    for p in range(n + 1):
        for kind, el, ev_wrap in events_at.get(p, []):
            prev_t = tok_of[p - 1] if p > 0 else None
            next_t = tok_of[p] if p < n else None
            same_tok = prev_t is not None and prev_t == next_t
            same_grp = (prev_t is not None and next_t is not None and kind == "m"
                        and (chunk_of[p - 1], group_of[p - 1]) == (chunk_of[p], group_of[p]))
            if kind == "m" and same_tok:
                set_wrappers(ev_wrap)
                cur_w[1] += milestone_xml(el, True)
            elif kind == "m" and same_grp:
                close_w()
                cur_phr.append(("line", milestone_xml(el, True)))
            else:
                close_phr()
                blocks.append(("line", milestone_xml(el, False) if kind == "m" else empty_element(el)))
        if p == n:
            break
        i = tok_of[p]
        key = (chunk_of[p], group_of[p])
        if key != cur_key:
            close_phr()
            cur_phr, cur_key = [], key
        if i != cur_tok:
            close_w()
            cur_w = [token_attrs(toks[i], style, old_by_span, keep_ana, stats), ""]
            cur_tok = i
            open_wrap = ()
        ch, wrap = seg.chars[p]
        set_wrappers(wrap)
        cur_w[1] += esc_text(ch)
    close_phr()

    lines = []
    for kind, body in blocks:
        if kind == "line":
            lines.append(indent + unit + body)
            continue
        lines.append(indent + unit + "<phr>")
        for part in body:
            if part[0] == "line":
                lines.append(indent + unit * 2 + part[1])
            else:
                _, at, content = part
                lines.append(indent + unit * 2 + "<w%s>%s</w>" % (
                    "".join(' %s="%s"' % (k, esc_attr(v)) for k, v in at), content))
        lines.append(indent + unit + "</phr>")
        stats["<phr>"] += 1
    stats["<w>"] += sum(1 for k, b in blocks if k == "phr" for part in b if part[0] == "w")
    return "\n" + "\n".join(lines) + "\n" + indent


# ---------------------------------------------------------------- ヘッダー

def add_header(src, n_segs, opts, today):
    note = []
    resp = ('<respStmt xml:id="%s">\n{i}  <resp>automatic segmentation into bound groups and morphemes, '
            'part-of-speech tagging and lemmatization with the Coptic SCRIPTORIUM NLP service '
            '(https://tools.copticscriptorium.org/coptic-nlp/); not checked by hand</resp>\n'
            '{i}  <name>Coptic SCRIPTORIUM</name>\n{i}</respStmt>' % RESP_ID)
    if ('xml:id="%s"' % RESP_ID) not in src:
        m = re.search(r"\n([ \t]*)</titleStmt>", src)
        if m:
            i = m.group(1) + "  "
            src = src[:m.start()] + "\n" + i + resp.format(i=i) + src[m.start():]
        else:
            note.append("<titleStmt> が無いので <respStmt> を足さなかった")
    change = ('<change when="%s">Bound groups (<gi>phr</gi>), morphemes (<gi>w</gi>), part of speech '
              '(<att>type</att>) and lemmas of %d segments re-annotated automatically with the Coptic SCRIPTORIUM '
              'NLP service by scripts/coptic_nlp_tei.py (%s); <att>resp</att>="#%s", not checked by hand. '
              'The letters of the text, the gaps, the supplied letters and the page and line breaks are unchanged.'
              '</change>' % (today, n_segs, opts, RESP_ID))
    m = re.search(r"\n([ \t]*)</revisionDesc>", src)
    if m:
        src = src[:m.start()] + "\n" + m.group(1) + "  " + change + src[m.start():]
    else:
        note.append("<revisionDesc> が無いので <change> を足さなかった")
    return src, note


# ---------------------------------------------------------------- CoNLL-U

def write_conllu(path, docname, toks_in_order, seg_of_chunk):
    """構文解析の結果（norm の func・head）を CoNLL-U に書く。文の区切りは NLP の new_sent に従う。"""
    if not any(t.attrs.get("func") for t in toks_in_order):
        return False
    sents, cur = [], []
    for t in toks_in_order:
        if cur and t.attrs.get("new_sent") == "true":
            sents.append(cur)
            cur = []
        cur.append(t)
    if cur:
        sents.append(cur)
    out = ["# newdoc id = %s" % docname]
    for n, sent in enumerate(sents, 1):
        index = {}
        for k, t in enumerate(sent, 1):
            if t.attrs.get("xml:id") and t.attrs["xml:id"] not in index:
                index[t.attrs["xml:id"]] = k
        groups = []
        for k, t in enumerate(sent, 1):
            key = (t.chunk, t.group)
            if groups and groups[-1][0] == key:
                groups[-1][2] = k
            else:
                groups.append([key, k, k])
        s_ids = []
        for t in sent:
            sid = seg_of_chunk.get(t.chunk, "")
            if sid and sid not in s_ids:
                s_ids.append(sid)
        text = " ".join("".join(sent[i - 1].text for i in range(g[1], g[2] + 1)) for g in groups)
        out += ["", "# sent_id = %s-%d" % (docname, n), "# tei_s = %s" % " ".join(s_ids), "# text = %s" % text]
        starts = {g[1]: g for g in groups}
        for k, t in enumerate(sent, 1):
            g = starts.get(k)
            if g and g[2] > g[1]:
                form = "".join(sent[i - 1].text for i in range(g[1], g[2] + 1))
                out.append("%d-%d\t%s\t_\t_\t_\t_\t_\t_\t_\t_" % (g[1], g[2], form))
            xpos = t.attrs.get("pos") or "UNKNOWN"
            head_ref = (t.attrs.get("head") or "").lstrip("#")
            func = t.attrs.get("func") or "dep"
            head = 0 if func == "root" else index.get(head_ref, 0)
            if func != "root" and head == 0:
                func = "dep"
            misc = ["TEI=%s" % seg_of_chunk.get(t.chunk, "")]
            if t.attrs.get("xml:lang") == "Greek":
                misc.append("Lang=grc")
            if t.attrs.get("norm") and t.attrs["norm"] != t.text:
                misc.append("Norm=%s" % t.attrs["norm"])
            out.append("\t".join([str(k), t.text, t.attrs.get("lemma") or "_", UPOS.get(xpos, "X"), xpos, "_",
                                  str(head), func, "_", "|".join(misc)]))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n\n")
    return True


# ---------------------------------------------------------------- 確かめる

def fingerprint(s_el):
    """<s> の中で、書き換えの前後で同じでなければならないもの: 文字の並びと、各文字を包む要素
    （<supplied> などの名前と属性。<w> の区切りで分かれてもよい）、欠損と改行の数と順。"""
    chars, marks = [], []

    def walk(el, wrap):
        tag = local(el.tag)
        if tag in WRAPPERS:
            wrap = wrap + ((tag, tuple(sorted(el.attrib.items()))),)
        if tag == "gap" or tag in MILESTONES:
            marks.append((tag, len(chars), tuple(sorted(el.attrib.items()))))
        for ch in el.text or "":
            if not ch.isspace():
                chars.append((ch, wrap))
        for c in el:
            walk(c, wrap)
            for ch in c.tail or "":
                if not ch.isspace():
                    chars.append((ch, wrap))

    walk(s_el, ())
    # break="no" は付け足すことがあるので比べない
    marks = [(t, p, tuple(kv for kv in at if kv[0] != "break")) for t, p, at in marks]
    return (s_el.get(XID), s_el.get("n"), tuple(chars), tuple(marks))


def is_subsequence(old_lines, new_lines):
    it = iter(new_lines)
    return all(any(o == n for n in it) for o in old_lines)


def main():
    ap = argparse.ArgumentParser(description="Coptic SCRIPTORIUM の NLP で TEI に語群・形態素・品詞・レンマを付け直す")
    ap.add_argument("file", help="TEI ファイル（data/*.xml や source/nhc_fulltext_split/tei/*.xml）")
    ap.add_argument("--out", help="書き出す先（既定: build/coptic_nlp/<ファイル名>）")
    ap.add_argument("--in-place", action="store_true", help="元のファイルに書き戻す")
    ap.add_argument("--groups", choices=("auto", "keep"), default="auto",
                    help="auto: 語群は NLP が決める（既定）。keep: いまの <phr> を変えない")
    ap.add_argument("--style", choices=("site", "cs"), default="site",
                    help="site: サイトの品詞コード・レンマの約束に合わせる（既定）。cs: Coptic SCRIPTORIUM のまま")
    ap.add_argument("--service", choices=("form", "api"), default="form",
                    help="form: Web の画面と同じ入口（語群の推定と構文解析ができる。既定）。api: API の入口")
    ap.add_argument("--url", default=SERVICE, help="NLP のサービスの URL（既定: %(default)s）")
    ap.add_argument("--detok", choices=("none", "conservative", "smart", "aggressive"),
                    help="語群の推定（laytonize）。既定は --groups auto なら smart、keep なら none")
    ap.add_argument("--conllu", help="構文解析もして、この場所に CoNLL-U で書き出す")
    ap.add_argument("--sgml", action="append", help="NLP に送らず、保存した出力（SGML）を読む（複数可。送った順に）")
    ap.add_argument("--save-sgml", help="NLP の出力（SGML）をこの場所に保存する")
    ap.add_argument("--export-request", help="NLP に送る文字列をこの場所に書き出して終わる")
    ap.add_argument("--max-chars", type=int, default=15000, help="1 回に送る字数の上限（既定 %(default)s）")
    ap.add_argument("--delay", type=float, default=3.0, help="送るたびに待つ秒数（既定 %(default)s）")
    ap.add_argument("--no-keep-ana", action="store_true", help="前の @ana を引き継がない")
    ap.add_argument("--keep-resp", action="append", default=[], metavar="ID",
                    help="@resp にこの xml:id（#ID）を持つ <w> がある <s> は、付け直さずにそのまま残す"
                         "（人の注釈を写した所など。複数可）")
    ap.add_argument("--timeout", type=float, default=180, help="1 回の送信で結果を待つ秒数（既定 %(default)s）")
    ap.add_argument("--retries", type=int, default=2, help="送信に失敗したとき、やり直す回数（既定 %(default)s）")
    ap.add_argument("--cache-dir", help="1 回ごとの NLP の出力をここに保存し、同じ送信はそれで代える"
                                        "（長い処理が途中で止まったとき、送り直さずに続けられる）")
    ap.add_argument("--today", default=datetime.date.today().isoformat(), help=argparse.SUPPRESS)
    a = ap.parse_args()

    detok = a.detok or ("smart" if a.groups == "auto" else "none")
    if a.service == "api" and detok != "none":
        print("注意: API の入口は語群の推定（laytonize）をしません。--groups keep か --service form を使ってください。",
              file=sys.stderr)
    src_path = os.path.abspath(a.file)
    src = open(src_path, encoding="utf-8").read()
    root = ET.fromstring(src.encode("utf-8"))
    s_elems = list(root.iter(T + "s"))
    s_spans = list(re.finditer(r"<s\b([^>]*)>(.*?)</s>", src, re.S))
    if len(s_elems) != len(s_spans):
        raise SystemExit("%s: <s> の数が合いません（入れ子か空の <s> がある）" % a.file)

    segs, skipped = [], Counter()
    keep = {"#" + r.lstrip("#") for r in a.keep_resp}
    for s_el, m in zip(s_elems, s_spans):
        sid = s_el.get(XID) or ""
        if m.group(1).rstrip().endswith("/") or ('xml:id="%s"' % sid) not in m.group(1):
            raise SystemExit("%s: <s> の対応がとれません（%s）" % (a.file, sid))
        if keep and any(keep & set((w.get("resp") or "").split()) for w in s_el.iter(T + "w")):
            skipped["@resp が %s の語があるので、そのまま残した" % "・".join(sorted(keep))] += 1
            segs.append(None)
            continue
        try:
            seg = read_segment(s_el)
        except Unsupported as e:
            skipped[str(e)] += 1
            segs.append(None)
            continue
        segs.append(seg)
    work = [s for s in segs if s is not None and s.chars]
    request = build_request(work, a.groups)
    docname = os.path.splitext(os.path.basename(src_path))[0]

    if a.export_request:
        with open(a.export_request, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(batches(request, 10 ** 9)))
        print("%s に NLP へ送る文字列を書き出しました（%d chunk、%d 字）" % (
            a.export_request, len(request), sum(len(t) for _, t in request)))
        return 0

    parse = bool(a.conllu)
    if a.sgml:
        sgml = "\n".join(open(p, encoding="utf-8").read() for p in a.sgml)
    else:
        parts = batches(request, a.max_chars)
        outs, sent = [], 0
        for k, data in enumerate(parts, 1):
            cpath = None
            if a.cache_dir:
                cpath = os.path.join(a.cache_dir, "%s.%s.tt" % (docname, cache_key(a.service, a.url, detok, parse, data)))
                if os.path.exists(cpath):
                    print("保存した出力を使います %d/%d（%s）" % (k, len(parts), os.path.basename(cpath)), file=sys.stderr)
                    with open(cpath, encoding="utf-8") as f:
                        outs.append(f.read())
                    continue
            if sent:
                time.sleep(a.delay)
            print("NLP に送っています %d/%d（%d 字）" % (k, len(parts), len(data)), file=sys.stderr)
            out_k = call_with_retries(data, a, detok, parse)
            sent += 1
            if cpath:
                os.makedirs(a.cache_dir, exist_ok=True)
                with open(cpath + ".part", "w", encoding="utf-8", newline="\n") as f:
                    f.write(out_k)
                os.replace(cpath + ".part", cpath)
            outs.append(out_k)
        sgml = "\n".join(outs)
        if a.save_sgml:
            os.makedirs(os.path.dirname(os.path.abspath(a.save_sgml)), exist_ok=True)
            with open(a.save_sgml, "w", encoding="utf-8", newline="\n") as f:
                f.write(sgml)

    toks, warn = parse_sgml(sgml)
    by_chunk = {}
    for t in toks:
        by_chunk.setdefault(t.chunk, []).append(t)
    unknown = set(by_chunk) - {cid for cid, _ in request}
    if unknown:
        warn["送っていない chunk の ID"] += len(unknown)

    stats = Counter()
    pieces, cursor, done = [], 0, 0
    ordered = []
    seg_of_chunk = {}
    for seg, m in zip(segs, s_spans):
        if seg is None or not seg.chars:
            continue
        seg_toks = []
        missing = False
        for k, (x, y) in enumerate(chunks_of(seg)):
            cid = "%s~%d" % (seg.sid, k)
            seg_of_chunk[cid] = seg.sid
            got = by_chunk.get(cid)
            if not got:
                missing = True
                break
            seg_toks += align_chunk(seg.text(x, y), got, x, warn)
        if missing:
            skipped["NLP の結果に無いセグメント"] += 1
            continue
        line_start = src.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", src[line_start:m.start()]).group(0)
        try:
            inner = render_segment(seg, seg_toks, a.style, not a.no_keep_ana, indent, "  ", stats)
        except Unsupported as e:
            skipped[str(e)] += 1
            continue
        pieces.append(src[cursor:m.start(2)])
        pieces.append(inner)
        cursor = m.end(2)
        ordered += seg_toks
        done += 1
    pieces.append(src[cursor:])
    out = "".join(pieces)
    opts = "groups=%s, laytonize=%s, style=%s" % (a.groups, detok, a.style)
    out, notes = add_header(out, done, opts, a.today)

    # 確かめる
    problems = []
    try:
        new_root = ET.fromstring(out.encode("utf-8"))
    except ET.ParseError as e:
        problems.append("書き出す XML が整形式でない: %s" % e)
        new_root = None
    if new_root is not None:
        old_fp = [fingerprint(s) for s in s_elems]
        new_fp = [fingerprint(s) for s in new_root.iter(T + "s")]
        if len(old_fp) != len(new_fp):
            problems.append("<s> の数が変わった")
        else:
            for o, n in zip(old_fp, new_fp):
                if o != n:
                    problems.append("%s: 文字・欠損・補い・改行のどれかが変わった" % o[0])
        outside_old = re.sub(r"<s\b[^>]*>.*?</s>", "<s/>", src, flags=re.S).splitlines()
        outside_new = re.sub(r"<s\b[^>]*>.*?</s>", "<s/>", out, flags=re.S).splitlines()
        if not is_subsequence(outside_old, outside_new):
            problems.append("<s> の外の行が変わった")

    print("%s: %d セグメントを付け直しました（%s）" % (a.file, done, opts))
    names = site_pos_names()
    for k, v in sorted(stats.items(), key=lambda kv: (not kv[0].startswith("<"), kv[0])):
        if k.startswith("品詞 "):
            continue
        print("  %s: %d" % (k, v))
    pos_counts = {k[3:]: v for k, v in stats.items() if k.startswith("品詞 ")}
    print("  品詞: " + ", ".join("%s %d" % kv for kv in sorted(pos_counts.items(), key=lambda kv: -kv[1])))
    if names and a.style == "site":
        extra = sorted(set(pos_counts) - names)
        if extra:
            print("  サイトの品詞表（build_site.py の POS_NAMES）に無いコード: " + ", ".join(extra))
    for k, v in sorted(warn.items()):
        print("  注意 %s: %d" % (k, v))
    for k, v in sorted(skipped.items()):
        print("  付け直さなかったセグメント（%s）: %d" % (k, v))
    for n in notes:
        print("  注意: " + n)
    if problems:
        for p in problems[:20]:
            print("  問題: " + p, file=sys.stderr)
        print("問題があったので書き出しませんでした。", file=sys.stderr)
        return 1

    dest = src_path if a.in_place else os.path.abspath(
        a.out or os.path.join(ROOT, "build", "coptic_nlp", os.path.basename(src_path)))
    if dest == src_path and not a.in_place:
        raise SystemExit("元のファイルに書くときは --in-place を付けてください")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print("書き出しました: %s" % os.path.relpath(dest, os.getcwd()))
    if a.conllu:
        if write_conllu(a.conllu, docname, ordered, seg_of_chunk):
            print("CoNLL-U: %s" % a.conllu)
        else:
            print("注意: NLP の出力に構文解析の結果（func・head）が無いので、CoNLL-U は書きませんでした。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
