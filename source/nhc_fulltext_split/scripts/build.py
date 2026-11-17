#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NHC 全文ファイルを文書（トラクテート）単位に分割し、サイト掲載用の下処理を行う。

    python3 build.py <Nag_Hammadi.txt> <出力フォルダ>

入力 : 「ID<TAB>コプト語<TAB>(空)」形式の行が並ぶテキスト（CRLF, UTF-8）。
       手で挿入された見出し行・空行・行の途中分割があってもよい（読み込み時に元へ戻す）。
出力 : tsv/ txt/ nhc_all.tsv catalog.tsv changes.tsv restored_letters.tsv unresolved_letters.tsv

行う処理は次の 6 つだけ（訳・グロス・語の再分割はしない）:
  1. 文書境界での分割（境界は「行ID＋アンカー文字列」で指定。行の途中でも切る）
  2. 表題 / 奥書表題 / コロフォン（と写本Xの未配置断片）を別行にして kind を付ける
     kind = title | text | subscript | colophon | fragment
  3. ⲯ → ⲝ（変換表の誤りで ⲝ がすべて ⲯ になっているのを戻す。ソースに ⲝ があれば何もしない）
  4. 英語の編集注記の残骸（"lines missing" 等）を欠損マーカー [...] に置換
  5. 重複ブロック（闘技者トマスの書 末尾）の除去
  6. 落ちている ⲍ・ⲯ の復元（規則は restore.py。語形から確実に言える箇所だけ。ソースに ⲍ があれば何もしない）
"""
import re, sys, os, bisect, collections, importlib.util

GAP = '[...]'

# restore.py は同じフォルダから読み込む（python3 -I で実行しても動くように sys.path に頼らない）
_spec = importlib.util.spec_from_file_location('restore', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'restore.py'))
restore = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(restore)
assert restore.GAP == GAP

# ----------------------------------------------------------------------------
# 1. 読み込み
# ----------------------------------------------------------------------------
class Row:
    __slots__ = ('id', 'toks', 'line', 'joins', 'offs', 'joined')
    def __init__(self, rid, toks, line):
        self.id, self.toks, self.line, self.joins = rid, toks, line, []
    def index(self):
        self.offs, s = [], 0
        for t in self.toks:
            self.offs.append(s); s += len(t)
        self.offs.append(s)
        self.joined = ''.join(self.toks)
    def span(self, regex, occ=1, need_end=True):
        """空白を無視して regex を探し、トークン範囲 (a, b) を返す。トークン境界に揃わなければエラー。
        need_end=False のときは開始位置だけがトークン境界に揃っていればよい（文書の開始位置用）。"""
        ms = list(re.finditer(regex, self.joined))
        if len(ms) < occ:
            raise ValueError(f'row {self.id}: /{regex}/ occurrence {occ} not found')
        m = ms[occ - 1]
        a = bisect.bisect_left(self.offs, m.start()); b = bisect.bisect_left(self.offs, m.end())
        if self.offs[a] != m.start() or (need_end and self.offs[b] != m.end()):
            raise ValueError(f'row {self.id}: /{regex}/ does not fall on token boundaries')
        return a, b

def load_rows(path):
    raw = open(path, 'rb').read().decode('utf-8')
    if raw.startswith('\ufeff'):
        raw = raw[1:]
    rows, headers = [], []
    for ln, l in enumerate(raw.replace('\r\n', '\n').replace('\r', '\n').split('\n'), 1):
        if not l.strip():
            continue
        m = re.match(r'^(\d+)\t(.*)$', l)
        if m:
            parts = m.group(2).split('\t')
            if any(p.strip() for p in parts[1:]):
                raise ValueError(f'line {ln}: unexpected content in 3rd column')
            rows.append(Row(m.group(1), parts[0].split(), ln))
        elif re.search(r'[A-Za-z]', l):
            headers.append((ln, l.strip()))            # 手で入れた見出し → 捨てる
        else:
            r = rows[-1]                                   # 手で分割された行の後半 → 前の行に戻す
            r.joins.append((ln, len(r.toks)))
            r.toks += l.split('\t')[0].split()
    for a, b in zip(rows, rows[1:]):
        if int(b.id) != int(a.id) + 1:
            raise ValueError(f'row id gap between {a.id} and {b.id}')
    for r in rows:
        r.index()
    return rows, headers

# ----------------------------------------------------------------------------
# 2. 文書の定義
#    (uid, file-slug, 英題, 略号, 標準ページ範囲, 開始行ID, 開始アンカー, occurrence, 備考)
#    アンカー None = その行の先頭から。正規表現は空白を除いた行テキストに対して照合する。
#    [ⲯⲝ] / ⲯ? / ⲍ? は、ⲍ・ⲯ・ⲝ を直したソースでも同じ定義で動くようにするための許容。
#    ただし一部のアンカーは注記残骸（ϯϯϭ, ⲗϣϧϭ など）を目印にしているので、
#    注記の入り方が違うソースに使うときはそこだけ直す必要がある。
# ----------------------------------------------------------------------------
UNITS = [
 ('I,2',   'apocryphon-of-james',        'The Apocryphon of James',                  'Ap. Jas.',        '1,1–16,30',     '7500001', None, 1, ''),
 ('I,3',   'gospel-of-truth',            'The Gospel of Truth',                      'Gos. Truth',      '16,31–43,24',   '7500381', r'ⲡⲉⲩⲁⲅⲅⲉⲗⲓⲟⲛⲛⲧⲙⲏⲉ', 1, ''),
 ('I,4',   'treatise-on-the-resurrection','The Treatise on the Resurrection',        'Treat. Res.',     '43,25–50,18',   '7501113', r'ⲟⲩⲛϩⲁⲉⲓⲛⲉⲡⲁϣⲏⲣⲉⲣⲏⲅⲓⲛⲟⲥ', 1, ''),
 ('I,5',   'tripartite-tractate',        'The Tripartite Tractate',                  'Tri. Trac.',      '51,1–138,27',   '7501123', r'ϫⲉⲡⲉⲧⲁⲛⲛⲁϣϫⲟⲟϥϩⲁⲛⲉⲧϫⲁⲥⲓ', 1, ''),
 ('II,1',  'apocryphon-of-john',         'The Apocryphon of John',                   'Ap. John',        '1,1–32,9',      '7503827', r'ⲧⲉⲥⲃⲱⲛⲧⲉⲡⲥⲱⲧⲏⲣ', 1, ''),
 ('II,2',  'gospel-of-thomas',           'The Gospel of Thomas',                     'Gos. Thom.',      '32,10–51,28',   '7503903', r'ⲛⲁⲉⲓⲛⲉⲛϣⲁϫⲉⲉⲑⲏⲡⲉⲛⲧⲁⲓⲥⲉⲧⲟⲛϩϫⲟⲟⲩ', 1, ''),
 ('II,3',  'gospel-of-philip',           'The Gospel of Philip',                     'Gos. Phil.',      '51,29–86,19',   '7503919', r'ⲟⲩϩⲉⲃⲣⲁⲓⲟⲥⲣⲣⲱⲙⲉ', 1, ''),
 ('II,4',  'hypostasis-of-the-archons',  'The Hypostasis of the Archons',            'Hyp. Arch.',      '86,20–97,23',   '7504148', r'ⲉⲧⲃⲉⲑⲩⲡⲟⲥⲧⲁⲥⲓⲥⲛⲛⲉ[ⲯⲝ]ⲟⲩⲥⲓⲁ', 1, ''),
 ('II,5',  'on-the-origin-of-the-world', 'On the Origin of the World',               'Orig. World',     '97,24–127,17',  '7504277', r'ⲉⲡⲉⲓⲇⲏⲟⲩⲟⲛⲛⲓⲙⲛⲛⲟⲩⲧⲉ', 1, ''),
 ('II,6',  'exegesis-on-the-soul',       'The Exegesis on the Soul',                 'Exeg. Soul',      '127,18–137,27', '7504565', r'ⲧⲉ[ⲯⲝ]ⲏⲅⲏⲥⲓⲥⲉⲧⲃⲉⲧⲯ?ⲩⲭⲏ', 1, ''),
 ('II,7',  'book-of-thomas-the-contender','The Book of Thomas the Contender',        'Thom. Cont.',     '138,1–145,19 (+ colophon 145,20–23)', '7504667', r'ⲛϣⲁϫⲉⲉⲑⲏⲡⲛⲁⲓⲉⲛⲧⲁϥϣⲁϫⲉ', 1,
            '奥書表題のあとに写本IIのコロフォン。ソースではその後ろに本文の一部（143頁後半相当）が重複して入っていたので除去した。'),
 ('III,1', 'apocryphon-of-john',         'The Apocryphon of John',                   'Ap. John',        '1,1–40,11',     '7504797', r'ϯϯϭⲡⲁⲡⲟⲕⲣⲩⲫⲟⲛ', 1,
            '冒頭の表題は扉頁のもの（ソースの注記 "title page" の残骸は除去）。19–20頁は欠（[...]）。'),
 ('III,2', 'gospel-of-the-egyptians',    'The Gospel of the Egyptians',              'Gos. Eg.',        '40,12–69,20',   '7505035', r'ⲡϫⲱⲱⲙⲉⲛⲧϩⲓⲉⲣⲁⲛⲧⲉⲛⲣⲙⲛⲕⲏⲙⲉ', 1, '末尾にコロフォンと奥書表題。'),
 ('III,3', 'eugnostos',                  'Eugnostos the Blessed',                    'Eugnostos',       '70,1–90,13',    '7505190', r'ⲉⲩⲅⲛⲱⲥⲧⲟⲥⲡⲙⲁⲕⲁⲣⲓⲟⲥⲛⲛⲉⲧⲉⲛⲟⲩϥⲛⲉ', 1, ''),
 ('III,4', 'sophia-of-jesus-christ',     'The Sophia of Jesus Christ',               'Soph. Jes. Chr.', '90,14–119,18',  '7505330', r'ⲧⲥⲟⲫⲓⲁⲛⲓⲏⲥⲡⲉⲭⲣⲥ', 1, ''),
 ('III,5', 'dialogue-of-the-savior',     'The Dialogue of the Savior',               'Dial. Sav.',      '120,1–147,23',  '7505517', r'ⲡⲇⲓⲁⲗⲟⲅⲟⲥⲙⲡⲥⲱⲧⲏⲣ', 1, ''),
 ('IV,1',  'apocryphon-of-john',         'The Apocryphon of John',                   'Ap. John',        '1,1–49,28',     '7505655', None, 1,
            '元ファイルの見出しでは「2,1」とされていたが、内容・前後関係から IV,1。'),
 ('IV,2',  'gospel-of-the-egyptians',    'The Gospel of the Egyptians',              'Gos. Eg.',        '50,1–81,2',     '7506040', r'ⲡϫⲱⲱⲙⲉⲉⲧⲟⲩⲁⲁⲃⲛⲧⲉⲛⲓⲣⲙⲛⲕⲏⲙⲉ', 1, ''),
 ('V,1',   'eugnostos',                  'Eugnostos the Blessed',                    'Eugnostos',       '1,1–17,18',     '7506196', r'ⲉⲩⲅⲛⲟⲥⲧⲟⲥⲛⲛⲓϣⲏⲣⲉ', 1, ''),
 ('V,2',   'apocalypse-of-paul',         'The Apocalypse of Paul',                   'Apoc. Paul',      '17,19–24,9',    '7506464', r'ⲧⲁⲡⲟⲕⲁⲗⲩⲯ?ⲓⲥⲙⲡⲁⲩⲗⲟⲥ', 1, ''),
 ('V,3',   'first-apocalypse-of-james',  'The (First) Apocalypse of James',          '1 Apoc. Jas.',    '24,10–44,10',   '7506532', r'ⲧⲁⲡⲟⲕⲁⲗⲩⲯ?ⲓⲥⲛⲓⲁⲕⲱⲃⲟⲥ', 1, ''),
 ('V,4',   'second-apocalypse-of-james', 'The (Second) Apocalypse of James',         '2 Apoc. Jas.',    '44,11–63,32',   '7506752', r'ⲧⲁⲡⲟⲕⲁⲗⲩⲯ?ⲓⲥⲛⲓⲁⲕⲱⲃⲟⲥ', 2, ''),
 ('V,5',   'apocalypse-of-adam',         'The Apocalypse of Adam',                   'Apoc. Adam',      '64,1–85,32',    '7506943', r'ⲧⲁⲡⲟⲕⲁⲗⲩ?ⲯ?ⲓⲥⲛⲁⲇⲁⲙ', 1, ''),
 ('VI,1',  'acts-of-peter-and-the-twelve-apostles','The Acts of Peter and the Twelve Apostles','Acts Pet. 12 Apost.','1,1–12,22','7507156', r'ϫⲉⲉⲧⲡⲣⲟⲫⲁⲥⲓⲥ', 1, ''),
 ('VI,2',  'thunder-perfect-mind',       'The Thunder: Perfect Mind',                'Thund.',          '13,1–21,32',    '7507325', r'ⲧⲉⲃⲣⲟⲛⲧⲏ', 1, ''),
 ('VI,3',  'authoritative-teaching',     'Authoritative Teaching',                   'Auth. Teach.',    '22,1–35,24',    '7507543', None, 1, ''),
 ('VI,4',  'concept-of-our-great-power', 'The Concept of Our Great Power',           'Great Pow.',      '36,1–48,15',    '7507791', None, 1, ''),
 ('VI,5',  'plato-republic',             'Plato, Republic 588b–589b',                'Plato Rep.',      '48,16–51,23',   '7508048', None, 1, ''),
 ('VI,6',  'discourse-on-the-eighth-and-ninth','The Discourse on the Eighth and Ninth','Disc. 8–9',     '52,1–63,32',    '7508103', None, 1, ''),
 ('VI,7',  'prayer-of-thanksgiving',     'The Prayer of Thanksgiving',               'Pr. Thanks.',     '63,33–65,7 (+ scribal note 65,8–14)', '7508284', None, 1,
            '末尾に写字生の覚え書き（VI,7a）を kind=colophon で含む。'),
 ('VI,8',  'asclepius',                  'Asclepius 21–29',                          'Asclepius',       '65,15–78,43',   '7508310', r'ⲉϣϫⲉⲕⲟⲩⲱϣⲇⲉⲉⲛⲁⲩ', 1, ''),
 ('VII,1', 'paraphrase-of-shem',         'The Paraphrase of Shem',                   'Paraph. Shem',    '1,1–49,9',      '7508559', r'ⲧⲡⲁⲣⲁⲫⲣⲁⲥⲓⲥⲛⲥⲏⲉⲙ', 1, ''),
 ('VII,2', 'second-treatise-of-the-great-seth','The Second Treatise of the Great Seth','Treat. Seth',   '49,10–70,12',   '7509504', r'ⲉϥⲙⲟⲧⲛⲇⲉⲙⲙⲟϥⲛϭⲓⲡⲙⲉⲅⲉⲑⲟⲥ', 1, ''),
 ('VII,3', 'apocalypse-of-peter',        'The Apocalypse of Peter',                  'Apoc. Pet.',      '70,13–84,14',   '7509890', r'ⲁⲡⲟⲕⲁⲗⲩⲯ?ⲓⲥⲡⲉⲧⲣⲟⲩ', 1, ''),
 ('VII,4', 'teachings-of-silvanus',      'The Teachings of Silvanus',                'Teach. Silv.',    '84,15–118,7 (+ colophon 118,8–9)', '7510105', r'ⲛⲥⲃⲟⲩⲛⲥⲓⲗⲟⲩⲁⲛⲟⲥ', 1,
            '末尾のコロフォンに由来不明の「ⲏⲏⲏ」「ⲧ ⲩ」を含む（装飾か注記の残骸の可能性。未変更）。VII,5 との境目は「ⲡ ⲟⲩⲱⲛϩ ⲉⲃⲟⲗ」の直前に置いた。'),
 ('VII,5', 'three-steles-of-seth',       'The Three Steles of Seth',                 'Steles Seth',     '118,10–127,27 (+ colophon 127,28–32)', '7510721', r'ⲡⲟⲩⲱⲛϩⲉⲃⲟⲗⲛⲧⲉⲇⲱⲥⲓⲑⲉⲟⲥ', 1, ''),
 ('VIII,1','zostrianos',                 'Zostrianos',                               'Zost.',           '1,1–132,9',     '7510939', r'ⲉⲛⲧⲉⲡⲉⲛⲛⲓϣⲁϫⲉⲟⲛϩ', 1, '奥書表題のあとの暗号文（132,7–9）は kind=colophon。'),
 ('VIII,2','letter-of-peter-to-philip',  'The Letter of Peter to Philip',            'Ep. Pet. Phil.',  '132,10–140,27', '7511688', r'ⲧⲉⲡⲓⲥⲧⲟⲗⲏⲙⲡⲉⲧⲣⲟⲥ', 1, ''),
 ('IX,1',  'melchizedek',                'Melchizedek',                              'Melch.',          '1,1–27,10',     '7511769', None, 1, ''),
 ('IX,2',  'thought-of-norea',           'The Thought of Norea',                     'Norea',           '27,11–29,5',    '7511863', None, 1, ''),
 ('IX,3',  'testimony-of-truth',         'The Testimony of Truth',                   'Testim. Truth',   '29,6–74,30',    '7511877', None, 1,
            '末尾（ID 7512181 以降）は数文字ずつの断片が続く。写本IXの未同定断片が含まれている可能性があるが、ソースの並びのままここに置いた。'),
 ('X,1',   'marsanes',                   'Marsanes',                                 'Marsanes',        '1,1–68,18',     '7512228', None, 1,
            '奥書表題 ⲙⲁⲣⲥⲁⲛⲏⲥ のあとに続く 3 レコードは写本Xの未配置断片とみられるので kind=fragment とした。'),
 ('XI,1',  'interpretation-of-knowledge','The Interpretation of Knowledge',          'Interp. Know.',   '1,1–21,35',     '7512519', r'ⲃⲑⲉⲣⲙⲏⲛⲓⲁⲃⲛⲧⲅⲛⲱⲥⲓⲥ', 1,
            'ソースでは冒頭表題の各行の前に「ⲃ」があった（ⲃ ⲑ ⲉⲣⲙⲏⲛⲓⲁ ⲃ ⲛ ⲧ ⲅⲛⲱⲥⲓⲥ）。頁ラベル "B" の残骸とみて削除した（changes.tsv に記録）。'),
 ('XI,2',  'valentinian-exposition',     'A Valentinian Exposition',                 'Val. Exp.',       '22,1–39,39',    '7512542', r'ⲟⲩⲧⲉϩⲛⲉⲓⲁϩⲟⲩⲛⲧⲭⲟⲣⲏⲅⲓⲁ', 1, ''),
 ('XI,2a', 'on-the-anointing',           'On the Anointing',                         'On Anoint.',      '40,1–29',       '7512572', r'ⲗϣϧϭⲣⲉϩⲕⲁⲧⲁⲡⲧⲩⲡⲟⲥ', 1, ''),
 ('XI,2b', 'on-baptism-a',               'On Baptism A',                             'On Bap. A',       '40,30–41,38',   '7512572', r'ⲡⲉⲉⲓⲡⲉⲡⲡⲗⲏⲣⲱⲙⲁⲙⲡⲕⲉⲫⲁⲗⲁⲓⲟⲛⲛⲧⲅⲛⲱⲥⲓⲥ', 1, ''),
 ('XI,2c', 'on-baptism-b',               'On Baptism B',                             'On Bap. B',       '42,1–43,19',    '7512572', r'ⲗϣϧϭⲁⲃⲁⲗϩⲙⲡⲕⲟⲥⲙⲟⲥⲁϩⲟⲩⲛⲁⲡⲓⲟⲣⲇⲁⲛⲏⲥ', 1, ''),
 ('XI,2d', 'on-the-eucharist-a',         'On the Eucharist A',                       'On Euch. A',      '43,20–38',      '7512572', r'ⲧⲛϣⲱⲡϩⲙⲁⲧⲛⲧⲟⲟⲧⲕⲛⲧⲛⲣⲉⲩⲭⲁⲣⲓⲥⲧⲉⲓ', 1, ''),
 ('XI,2e', 'on-the-eucharist-b',         'On the Eucharist B',                       'On Euch. B',      '44,1–37',       '7512572', r'ⲗϣϧϭϩⲛⲧⲧⲙⲙⲉⲉⲩⲉ', 1, ''),
 ('XI,3',  'allogenes',                  'Allogenes',                                'Allogenes',       '45,1–69,20',    '7512572', r'ⲗϣϧϭⲉⲩⲉⲛⲕⲁⲧⲁⲟⲩⲁⲛⲧⲉⲗⲓⲟⲥ', 1, ''),
 ('XI,4',  'hypsiphrone',                'Hypsiphrone',                              'Hypsiph.',        '69,21–72,33',   '7512937', r'ϩ?ⲩⲯ?ⲓⲫⲣⲟⲛⲏⲡϫⲱⲱⲙⲉ', 1, '最終行（ID 7512953）は数文字ずつの断片の連続。'),
 ('XII,1', 'sentences-of-sextus',        'The Sentences of Sextus',                  'Sent. Sextus',    '15,1–16,28; 27,1–34,28', '7512954', None, 1, ''),
 ('XII,2', 'gospel-of-truth-fragments',  'The Gospel of Truth (fragments)',          'Gos. Truth',      '53,19–60,30',   '7513084', r'ⲁⲩⲱⲛⲉⲧⲥⲱⲧⲙⲉⲣⲟϥⲛⲉϥϯⲛⲁⲩ', 1, ''),
 ('XII,3', 'fragments',                  'Fragments',                                'Frm.',            '',              '7513098', r'(?<=ⲉⲩⲇⲟⲕⲉⲓ)ⲁⲁⲉⲩⲁⲙⲁⲛⲏⲣⲉ', 1,
            'XII,2 との境目は断片的で確定しにくい。「ⲡⲉⲧϥⲉⲩⲇⲟⲕⲉⲓ」の直後に置いた。'),
 ('XIII,1','trimorphic-protennoia',      'Trimorphic Protennoia',                    'Trim. Prot.',     '35,1–50,24',    '7513101', r'ⲁⲛⲟⲕⲧⲉⲧⲡⲣⲱⲧⲉⲛⲛⲟⲓⲁ', 1,
            '末尾は第三部の小見出し＋全体の表題（subscript）と奥書（colophon）。本文中の小見出し（ⲡⲁ ⲧϩⲓⲙⲁⲣⲙⲉⲛⲏ ⲃ など）は text のまま。'),
 ('XIII,2','on-the-origin-of-the-world-fragment','On the Origin of the World (fragment)','Orig. World', '50,25–34',      '7513227', None, 1, ''),
]
ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10,'XI':11,'XII':12,'XIII':13}

# ----------------------------------------------------------------------------
# 3. 表題などのラベル  (行ID, 正規表現 or None=行全体, occurrence, kind)
# ----------------------------------------------------------------------------
PS = r'ⲁⲡⲟⲕⲁⲗⲩ?ⲯ?ⲓⲥ'
LABELS = [
 # --- 冒頭表題 (title)
 ('7504565', r'ⲧⲉ[ⲯⲝ]ⲏⲅⲏⲥⲓⲥⲉⲧⲃⲉⲧⲯ?ⲩⲭⲏ', 1, 'title'),            # II,6
 ('7504797', r'ϯϯϭⲡⲁⲡⲟⲕⲣⲩⲫⲟⲛϯϯϭⲛⲓⲱϩⲁⲛⲛⲏⲥ', 1, 'title'),                # III,1（ϯϯϭ は削除されるラベル残骸）
 ('7505330', r'ⲧⲥⲟⲫⲓⲁⲛⲓⲏⲥⲡⲉⲭⲣⲥ', 1, 'title'),                   # III,4
 ('7505517', r'ⲡⲇⲓⲁⲗⲟⲅⲟⲥⲙⲡⲥⲱⲧⲏⲣ', 1, 'title'),                 # III,5
 ('7506464', r'ⲧ' + PS + r'ⲙⲡⲁⲩⲗⲟⲥ', 1, 'title'),                  # V,2
 ('7506532', r'ⲧ' + PS + r'ⲛⲓⲁⲕⲱⲃⲟⲥ', 1, 'title'),                 # V,3
 ('7506752', r'ⲧ' + PS + r'ⲛⲓⲁⲕⲱⲃⲟⲥ', 2, 'title'),                 # V,4
 ('7506943', r'ⲧ' + PS + r'ⲛⲁⲇⲁⲙ', 1, 'title'),                    # V,5
 ('7507325', r'ⲧⲉⲃⲣⲟⲛⲧⲏ', 1, 'title'), ('7507326', r'^ⲛⲟⲩⲥⲛⲧⲉⲗⲉⲓⲟⲥ', 1, 'title'),   # VI,2
 ('7507791', None, 1, 'title'), ('7507792', None, 1, 'title'),       # VI,4
 ('7508559', r'ⲧⲡⲁⲣⲁⲫⲣⲁⲥⲓⲥⲛⲥⲏⲉⲙ', 1, 'title'),                 # VII,1
 ('7509890', PS + r'ⲡⲉⲧⲣⲟⲩ', 1, 'title'),                          # VII,3
 ('7510105', r'ⲛⲥⲃⲟⲩⲛⲥⲓⲗⲟⲩⲁⲛⲟⲥ', 1, 'title'),                   # VII,4
 ('7511688', r'ⲧⲉⲡⲓⲥⲧⲟⲗⲏⲙⲡⲉⲧⲣⲟⲥⲉⲧⲁϥϫⲟⲟⲩⲥⲙⲫⲓⲗⲓⲡⲡⲟⲥ', 1, 'title'),  # VIII,2
 ('7511769', r'^ⲙⲉⲗ[ϫⲭ]ⲓⲥⲉⲇⲉⲕ', 1, 'title'),                     # IX,1
 ('7512519', r'ⲃⲑⲉⲣⲙⲏⲛⲓⲁⲃⲛⲧⲅⲛⲱⲥⲓⲥ', 1, 'title'),              # XI,1
 ('7512937', r'ϩ?ⲩⲯ?ⲓⲫⲣⲟⲛⲏ(?=ⲡϫⲱⲱⲙⲉ)', 1, 'title'),            # XI,4
 # --- 奥書表題 (subscript)
 ('7501123', r'ⲡⲗⲟⲅⲟⲥⲉⲧⲃⲉⲧⲁⲛⲁⲥⲧⲁⲥⲓⲥ', 1, 'subscript'),        # I,4
 ('7503903', r'ⲕⲁⲧⲁⲓⲱϩⲁⲛⲛⲏⲛⲛⲁⲡⲟⲕⲣⲩⲫⲟⲛ', 1, 'subscript'),      # II,1
 ('7503919', r'ⲡⲉⲩⲁⲅⲅⲉⲗⲓⲟⲛⲡⲕⲁⲧⲁⲑⲱⲙⲁⲥ', 1, 'subscript'),       # II,2
 ('7504148', r'ⲡⲉⲩⲁⲅⲅⲉⲗⲓⲟⲛⲡⲕⲁⲧⲁⲫⲓⲗⲓⲡⲡⲟⲥ', 1, 'subscript'),    # II,3
 ('7504277', r'ⲧⲑⲩⲡⲟⲥⲧⲁⲥⲓⲥⲛⲛⲁⲣⲭⲱⲛ', 1, 'subscript'),          # II,4
 ('7504667', r'ⲧⲉ[ⲯⲝ]ⲏⲅⲏⲥⲓⲥⲉⲧⲃⲉⲧⲯ?ⲩⲭⲏ', 1, 'subscript'),        # II,6
 ('7504793', r'ⲡϫⲱⲙⲉⲛⲑⲱⲙⲁⲥⲡⲁⲑⲗⲏⲧⲏⲥⲉϥⲥϩⲁⲓⲛⲛⲧⲉⲗⲉⲓⲟⲥ', 1, 'subscript'),   # II,7
 ('7504793', r'ⲁⲣⲓⲡⲁⲙⲉⲉⲩⲉϩⲱⲛⲁⲥⲛⲏⲩϩⲛⲛⲉⲧⲛⲡⲣⲟⲥⲉⲩⲭⲏⲉⲓⲣⲏⲛⲏⲧⲟⲓⲥⲁⲅⲓⲟⲓⲥⲙⲛⲛⲓⲡⲛⲉⲩⲙⲁⲧⲓⲕⲟⲥ', 1, 'colophon'),
 ('7505035', r'ⲡⲁⲡⲟⲕⲣⲩⲫⲟⲛⲛⲓⲱϩⲁⲛⲛⲏⲥ', 1, 'subscript'),          # III,1
 ('7505187', r'ⲡⲉⲩⲁⲅⲅⲉⲗⲓⲟⲛⲛⲛⲣⲙⲛⲕⲏⲙⲉ.*$', 1, 'colophon'),         # III,2
 ('7505188', None, 1, 'colophon'), ('7505189', None, 1, 'colophon'),
 ('7505190', r'^ⲓⲭⲑⲩⲥⲑⲉⲟⲅⲣⲁⲫⲟⲥⲧⲃⲓⲃⲗⲟⲥⲧϩⲓⲉⲣⲁⲙⲡⲛⲟϭⲛⲁϩⲟⲣⲁⲧⲟⲛⲙⲡⲛⲁϩⲁⲙⲏⲛ', 1, 'colophon'),
 ('7505190', r'ⲧⲃⲓⲃⲗⲟⲥⲧϩⲓⲉⲣⲁⲙⲡⲛⲟϭⲛⲁϩⲟⲣⲁⲧⲟⲛⲙⲡⲛⲉⲩⲙⲁϩⲁⲙⲏⲛ', 1, 'subscript'),
 ('7505330', r'ⲉⲩⲅⲛⲱⲥⲧⲟⲥⲡⲙⲁⲕⲁⲣⲓⲟⲥ(?=ⲧⲥⲟⲫⲓⲁ)', 1, 'subscript'),   # III,3
 ('7505517', r'^ⲧⲥⲟⲫⲓⲁⲛⲓⲏⲥ', 1, 'subscript'),                    # III,4
 ('7505654', r'ⲡⲇⲓⲁⲗⲟⲅⲟⲥⲙⲡⲥⲱⲧⲏⲣ$', 1, 'subscript'),             # III,5
 ('7506040', r'ⲕⲁⲧⲁⲓⲱ(ϩⲁⲛⲛ)?ⲏⲛⲛⲁⲡⲟⲕⲣⲩⲫⲟⲛ', 1, 'subscript'),     # IV,1
 ('7506464', r'^ⲉⲩⲅⲛ?[ⲟⲱ]?ⲥⲧⲟⲥ', 1, 'subscript'),                 # V,1
 ('7506532', r'^ⲧ' + PS + r'ⲙⲡⲁⲩⲗⲟⲥ', 1, 'subscript'),              # V,2
 ('7506752', r'^ⲧ' + PS + r'ⲛⲓⲁⲕⲱⲃⲟⲥ', 1, 'subscript'),             # V,3
 ('7507156', r'ⲧ' + PS + r'ⲛⲁⲇⲁⲙ', 1, 'subscript'),                 # V,5
 ('7507325', r'ⲛⲓⲡⲣⲁ[ⲯⲝ]ⲓⲥⲛⲧⲉⲡⲉⲧⲣⲟⲥⲙⲛⲡⲓⲙⲛⲧⲥⲛⲟⲟⲩⲥⲛⲁⲡⲟⲥⲧⲟⲗⲟⲥ', 1, 'subscript'),   # VI,1
 ('7507790', None, 1, 'subscript'),                                   # VI,3
 ('7508047', None, 1, 'subscript'),                                   # VI,4
 ('7508309', None, 1, 'colophon'),                                    # VI,7a scribal note
 ('7508310', r'^ⲉⲡⲓⲛⲁϣⲱⲟⲩⲅⲁⲣⲛϭⲓⲛⲗⲟⲅⲟⲥⲉⲧⲁⲩⲉⲓⲉⲧⲟⲟⲧⲛⲧⲉⲡⲏ', 1, 'colophon'),
 ('7509890', r'^ⲇⲉⲩⲧⲉⲣⲟⲥⲗⲟⲅⲟⲥⲧⲟⲩⲙⲉⲅⲁⲗⲟⲩⲥⲏⲑ', 1, 'subscript'),   # VII,2
 ('7510105', r'^' + PS + r'ⲡⲉⲧⲣⲟⲩ', 1, 'subscript'),                 # VII,3
 ('7510721', r'^ⲓⲭⲑⲩⲥⲑⲁⲩⲙⲁⲏⲏⲏⲁⲙⲏⲭⲁⲛⲟⲛⲧⲩ', 1, 'colophon'),        # VII,4
 ('7510937', None, 1, 'subscript'),                                   # VII,5
 ('7510938', None, 1, 'colophon'),
 ('7510939', r'^ⲥⲙⲟⲩⲉⲣⲟⲓⲡⲓⲱⲧϯⲥⲙⲟⲩⲉⲣⲟⲕⲡⲓⲱⲧϩⲛⲟⲩⲉⲓⲣⲏⲛⲏϩⲁⲙⲏⲛ', 1, 'colophon'),
 ('7511687', r'^ⲍ?ⲱⲥⲧⲣⲓⲁⲛⲟⲥ', 1, 'subscript'),                    # VIII,1
 ('7511687', r'(?<=ⲱⲥⲧⲣⲓⲁⲛⲟⲥ).+$', 1, 'colophon'),                 # cryptogram
 ('7511688', r'^.+?(?=ⲧⲉⲡⲓⲥⲧⲟⲗⲏⲙⲡⲉⲧⲣⲟⲥ)', 1, 'colophon'),
 ('7512517', r'ⲙⲁⲣⲥⲁⲛⲏⲥ', 1, 'subscript'),                         # X
 ('7512517', r'(?<=ⲙⲁⲣⲥⲁⲛⲏⲥ).+$', 1, 'fragment'),                  # 奥書表題より後ろ = 未配置断片
 ('7512518', None, 1, 'fragment'),
 ('7512519', r'^.+?(?=ⲃⲑⲉⲣⲙⲏⲛⲓⲁⲃⲛⲧⲅⲛⲱⲥⲓⲥ)', 1, 'fragment'),
 ('7512542', r'ⲑⲉⲣⲙⲏⲛⲓⲁⲛⲧⲅⲛⲱⲥⲓⲥ', 1, 'subscript'),               # XI,1
 ('7512937', r'(?<=ⲛⲧⲉⲡⲁⲗⲗⲟⲅⲉⲛⲏⲥ)ⲡⲁⲗⲗⲟⲅⲉⲛⲏⲥ', 1, 'subscript'),   # XI,3
 ('7513226', r'^ⲡⲗⲟⲅⲟⲥⲛⲧⲉⲡⲓⲫⲁⲛⲓⲁⲅⲡⲣⲱⲧⲉⲛⲛⲟⲓⲁⲧⲣⲓⲙⲟⲣⲫⲟⲥⲅ', 1, 'subscript'),      # XIII,1
 ('7513226', r'ⲁⲅⲓⲁⲅⲣⲁⲫⲏⲡⲁⲧⲣⲟⲅⲣⲁⲫⲟⲥⲉⲛⲅⲛⲱⲥⲉⲓⲧⲉⲗⲉⲓⲁ$', 1, 'colophon'),
]

# ----------------------------------------------------------------------------
# 4. 編集注記の残骸
#    ソースは大文字=ギリシア系文字／小文字 s f k h j g t = ϣ ϥ ϧ ϩ ϫ ϭ ϯ の翻字で、
#    英語の注記（"Lines missing", "lines lacking", "fragments", "Pages ..." など）が
#    そのまま変換されて ϣ ϣϣϭ / ⲗϣ ϧϭ / ϥϭ ϯ ϣ / ⲡϭ … のような残骸になっている。
# ----------------------------------------------------------------------------
NOTE_PATTERNS = sorted([
 ('ⲗϣ', 'ϯ', 'ϯϩ', 'ϣϣϭ'), ('ϣ', 'ϥϭ', 'ϣϣϭ'), ('ϭϣ', 'ϣϣϭ'), ('ⲗ', 'ϣ', 'ϣϣϭ'), ('ⲗϣ', 'ϣϣϭ'),
 ('ϣ', 'ϣϣϭ'), ('ⲙϣϣϭ', 'ϣ'), ('ⲙϣϣϭ',), ('ϣϣϭ',),                          # … missing
 ('ⲗϣ', 'ⲗϧϭ'), ('ⲗϣ', 'ϧϭ'), ('ϣ', 'ϧϭ'), ('ⲗϧϭ',), ('ϧϭ',),               # … lacking
 ('ⲗϣ', 'ϥϭ', 'ϯ', 'ϣ'), ('ϥϭ', 'ϯ', 'ϣ'), ('ⲡϭ', 'ϣ', 'ϯ', 'ϣ'),            # fragments / Pages …
], key=len, reverse=True)

# 個別指定 (行ID, 正規表現, occurrence, 'gap' | 'drop', 説明)
NOTE_SPECIALS = [
 ('7505654', r'ⲁⲡⲡⲣⲟⲭⲓⲙⲁⲧⲉⲗⲯ?ⲗⲓⲛⲉⲥⲁⲣⲉⲙⲓⲥⲥⲓⲛⲅ', 1, 'gap', '注記 "APPROXIMATEL(Y) n LINES ARE MISSING" がコプト文字に化けたもの'),
 ('7506196', r'ϣϥϭϣϣϭϧϯϥϭϯϥⲓϣϣ', 1, 'gap', 'IV,2 末尾の注記残骸（"… following missing … fragment …"）'),
 ('7511404', r'(ⲡϭϣϯϣⲓϯϣϧϯϣϯϯϩϭϭ){2}(ⲡϭϣϧϯϩϩϭϯ){2}', 1, 'gap', 'ゾストゥリアノス: "Pages …" で始まる注記残骸×4（頁の欠損）'),
 ('7504797', r'ϯϯϭ(?=ⲡⲁⲡⲟⲕⲣⲩⲫⲟⲛ)', 1, 'drop', '注記 "title page" の残骸（欠損ではないので削除）'),
 ('7504797', r'(?<=ⲡⲁⲡⲟⲕⲣⲩⲫⲟⲛ)ϯϯϭ', 1, 'drop', '注記 "title page" の残骸（欠損ではないので削除）'),
 ('7504797', r'ⲡϭϣϯϥϭϯ', 1, 'gap', '"Pages … fragment" とみられる注記残骸'),
 ('7512519', r'ⲃ(?=ⲑⲉⲣⲙⲏⲛⲓⲁⲃⲛⲧⲅⲛⲱⲥⲓⲥ)', 1, 'drop', '表題の各行の前に付いた頁ラベル "B"（見返し B）の残骸とみられる（欠損ではないので削除）'),
 ('7512519', r'(?<=ⲃⲑⲉⲣⲙⲏⲛⲓⲁ)ⲃ(?=ⲛⲧⲅⲛⲱⲥⲓⲥ)', 1, 'drop', '表題の各行の前に付いた頁ラベル "B"（見返し B）の残骸とみられる（欠損ではないので削除）'),
 ('7504911', r'ⲡϭϯϣϯⲡϭϯϯϣϯ', 1, 'gap', 'III,1: "Page … Page …"（19–20頁の欠）'),
 ('7506987', r'ϭϧϧϭ', 1, 'gap', '注記残骸（"… lacking" を含む。先頭の ϭ も注記の一部とみなした）'),
 ('7512102', r'ⲃϧϥϭϯ', 1, 'gap', '注記残骸（"B…k fragment"。意味未確定）'),
 ('7512197', r'^ⲃϧ$', 1, 'gap', '注記残骸のみの行（"Blank" か。意味未確定）'),
 ('7503832', r'(?<=ⲛϩⲏⲧϥ)ϧ(?=ⲟⲩⲁⲁⲧϥ)', 1, 'gap', '単独の ϧ（注記残骸。意味未確定）'),
 ('7512553', r'(?<=ⲟⲩⲛⲧⲉⲟ)ϧ(?=ⲧⲟⲩⲧⲉⲧ)', 1, 'gap', '単独の ϧ（注記残骸。意味未確定）'),
]
RESIDUE_TOKENS = {'ϣϣϭ', 'ϧϭ', 'ϧ', 'ϥϭ', 'ϥϭϯ', 'ϭϭ', 'ϭϯ', 'ϣϣ', 'ϭϣ', 'ⲗϣ', 'ⲡϭ', 'ⲡϭϣ', 'ⲃϧ', 'ⲗϧϭ', 'ⲙϣϣϭ'}

# 重複ブロック: (行ID, 開始アンカー) 〜 次の文書(III,1)の開始まで
DUP_START = ('7504793', r'(?<=ⲡⲛⲉⲩⲙⲁⲧⲓⲕⲟⲥ)ⲟⲩⲟⲉⲓⲛⲏⲧⲛⲉⲃⲟⲗϩⲓⲧⲟⲟⲧϥⲙⲡⲕⲁⲧ')
DUP_END_UNIT = 'III,1'

# ----------------------------------------------------------------------------
def main(src, out):
    rows, headers = load_rows(src)
    byid = {r.id: k for k, r in enumerate(rows)}
    R = lambda rid: rows[byid[rid]]
    n_src_tokens = sum(len(r.toks) for r in rows)
    log = []                                    # changes.tsv の行
    # ⲯ→ⲝ は「ソースに ⲝ が 1 つもない」（＝変換表の誤りの特徴）ときだけ行う。
    # ⲝ を含む（＝直された）ソースでは本物の ⲯ を壊さないよう何もしない。
    fix_psi = not any('ⲝ' in t for r in rows for t in r.toks)
    if not fix_psi:
        print('note: source already contains ⲝ -> the ⲯ→ⲝ step is skipped')
    # ⲍ・ⲯ の復元も「ソースに ⲍ が 1 つもなく、ⲝ もない」（＝同じ変換の誤りの特徴）ときだけ行う。
    do_restore = fix_psi and not any('ⲍ' in t for r in rows for t in r.toks)
    if not do_restore:
        print('note: source already contains ⲍ or ⲝ -> lost letters are not restored')

    for ln, h in headers:
        log.append(('header_removed', '', f'line {ln}', '', h, '', '手で挿入された見出し行を除去'))
    for r in rows:
        for ln, at in r.joins:
            log.append(('row_rejoined', '', r.id, f'{at}-{len(r.toks)}', ' '.join(r.toks[at:]), '',
                        f'見出し挿入のため途中で分割されていた行（{ln}行目）を元の行に結合'))

    # ---- 文書境界 → 各トークンに unit を割り当てる
    starts = []
    for (uid, slug, en, ab, pp, rid, rx, occ, note) in UNITS:
        a = 0 if rx is None else R(rid).span(rx, occ, need_end=False)[0]
        starts.append((byid[rid], a, uid))
    assert starts == sorted(starts), 'unit starts are not in order'
    unit_of = [[None] * len(r.toks) for r in rows]
    si, cur = 0, None
    for k, r in enumerate(rows):
        for i in range(len(r.toks)):
            while si < len(starts) and (starts[si][0], starts[si][1]) <= (k, i):
                cur = starts[si][2]; si += 1
            unit_of[k][i] = cur
    assert si == len(starts) and all(u is not None for us in unit_of for u in us)

    # ---- kind
    kind_of = [['text'] * len(r.toks) for r in rows]
    for rid, rx, occ, kind in LABELS:
        r = R(rid); a, b = (0, len(r.toks)) if rx is None else r.span(rx, occ)
        us = {unit_of[byid[rid]][i] for i in range(a, b)}
        if len(us) != 1:
            raise ValueError(f'label {kind} in row {rid} straddles units {us}')
        for i in range(a, b):
            kind_of[byid[rid]][i] = kind

    # ---- act: None=そのまま / ('gap', n) / ('drop',)
    act = [[None] * len(r.toks) for r in rows]
    gap_id = [0]
    def mark(k, a, b, what, why):
        r = rows[k]
        assert all(act[k][i] is None for i in range(a, b)), f'overlapping edit in {r.id}'
        us = {unit_of[k][i] for i in range(a, b)}
        assert len(us) == 1, f'edit straddles units in {r.id}: {us}'
        if what == 'gap':
            gap_id[0] += 1
            for i in range(a, b): act[k][i] = ('gap', gap_id[0])
        else:
            for i in range(a, b): act[k][i] = ('drop',)
        log.append(('note_to_gap' if what == 'gap' else 'removed', us.pop(), r.id, f'{a}-{b}',
                    ' '.join(r.toks[a:b]), GAP if what == 'gap' else '', why))

    # 重複ブロック
    k0 = byid[DUP_START[0]]; a0 = rows[k0].span(DUP_START[1], need_end=False)[0]
    k1, a1, _ = next(s for s in starts if s[2] == DUP_END_UNIT)
    dup = [(k, i) for k in range(k0, k1 + 1) for i in range(len(rows[k].toks))
           if (k, i) >= (k0, a0) and (k, i) < (k1, a1)]
    dup_txt = ''.join(rows[k].toks[i] for k, i in dup)
    before = ''.join(''.join(rows[k].toks) for k in range(max(0, k0 - 40), k0)) + ''.join(rows[k0].toks[:a0])
    if dup_txt and dup_txt in before:
        for k in range(k0, k1 + 1):
            idx = [i for (kk, i) in dup if kk == k]
            if idx:
                for i in idx: act[k][i] = ('drop',)
                log.append(('duplicate_removed', unit_of[k][idx[0]], rows[k].id, f'{idx[0]}-{idx[-1] + 1}',
                            ' '.join(rows[k].toks[idx[0]:idx[-1] + 1]), '',
                            'コロフォンの後ろに本文（ID 7504771–7504775 相当）がそのまま繰り返されている重複ブロック'))
        print(f'duplicate block removed: {len(dup)} tokens / {len(dup_txt)} chars')
    else:
        print('WARNING: expected duplicate block not found verbatim earlier in the text; nothing removed')

    # 注記残骸（個別 → 一般パターン）
    for rid, rx, occ, what, why in NOTE_SPECIALS:
        a, b = R(rid).span(rx, occ); mark(byid[rid], a, b, what, why)
    for k, r in enumerate(rows):
        i = 0
        while i < len(r.toks):
            hit = None
            if act[k][i] is None:
                for p in NOTE_PATTERNS:
                    if tuple(r.toks[i:i + len(p)]) == p and all(act[k][j] is None for j in range(i, i + len(p))) \
                       and len({unit_of[k][j] for j in range(i, i + len(p))}) == 1:
                        hit = p; break
            if hit:
                mark(k, i, i + len(hit), 'gap', '英語の編集注記の残骸（lines missing / lacking / fragments / Pages … の類）')
                i += len(hit)
            else:
                i += 1
    left = [(r.id, i, t) for k, r in enumerate(rows) for i, t in enumerate(r.toks)
            if act[k][i] is None and (t in RESIDUE_TOKENS or 'ϧ' in t)]
    if left:
        print('WARNING: residue-looking tokens left untouched:', left[:20])

    # ---- 出力行を組み立てる
    units = collections.OrderedDict((u[0], []) for u in UNITS)
    stats = collections.defaultdict(lambda: collections.Counter())
    accounted = 0
    for k, r in enumerate(rows):
        i = 0
        while i < len(r.toks):
            u, kd = unit_of[k][i], kind_of[k][i]
            j = i
            while j < len(r.toks) and unit_of[k][j] == u and kind_of[k][j] == kd:
                j += 1
            out_toks, src_ix, n_xi = [], [], 0          # src_ix: 出力トークン → 元の行でのトークン番号（[...] と削除印は None）
            for q, (t, a_) in enumerate(zip(r.toks[i:j], act[k][i:j]), i):
                if a_ is None:
                    if fix_psi and 'ⲯ' in t:
                        n_xi += t.count('ⲯ'); t = t.replace('ⲯ', 'ⲝ')
                    out_toks.append(t); src_ix.append(q)
                elif a_[0] == 'gap':
                    last = next((x for x in reversed(out_toks) if x != restore.DROP), None)
                    if last != GAP:                                  # 連続する注記は 1 つにまとめる
                        out_toks.append(GAP); src_ix.append(None)
                elif out_toks and out_toks[-1] != restore.DROP:      # ('drop',): 出力しないが、復元の照合がここをまたがないよう印を置く
                    out_toks.append(restore.DROP); src_ix.append(None)
            events = []
            if do_restore:
                new_toks, evs = restore.apply(out_toks, r.id, u)
                for i0, i1, tok, hs, letters in evs:
                    a, b = src_ix[i0], src_ix[i1] + 1
                    assert None not in src_ix[i0:i1 + 1] and b - a == i1 - i0 + 1
                    conf = 'B' if any(h[1] == 'B' for h in hs) else 'A'
                    word = '+'.join(h[0] for h in hs)
                    note = ' / '.join(dict.fromkeys(h[2] for h in hs))
                    joined = '。語の途中で切れていた ' + str(b - a) + ' トークンを連結' if b - a > 1 else ''
                    log.append(('letter_restored', u, r.id, f'{a}-{b}', ' '.join(r.toks[a:b]), tok,
                                f'ⲍ・ⲯ の復元（確度 {conf}）: {word}（{note}）{joined}'))
                    events.append([a, b, ' '.join(r.toks[a:b]), tok, word, letters, conf, note])
                shift = 0                                            # 連結後のトークン列での位置（文脈の表示用）
                for (i0, i1, tok, hs, letters), ev in zip(evs, events):
                    ev.append(i0 - shift); shift += i1 - i0
                out_toks = new_toks
            keep = [x for x in out_toks if x != restore.DROP]
            for ev in events:                                        # 文脈: 前後 5 トークン
                q = ev.pop()                                         # out_toks（削除印を含む）での位置
                p = sum(1 for x in out_toks[:q] if x != restore.DROP)
                assert keep[p] == ev[3]
                ev.append(' '.join(keep[max(0, p - 5):p]) + ' «' + keep[p] + '» ' + ' '.join(keep[p + 1:p + 6]))
            out_toks = keep
            n_tok = sum(1 for x in out_toks if x != GAP)
            accounted += j - i
            if out_toks:
                span = 'all' if (i == 0 and j == len(r.toks)) else f'{i}-{j}'
                units[u].append([kd, r.id, span, ' '.join(out_toks), events])
                st = stats[u]; st['rows'] += 1; st['tokens'] += n_tok; st['gaps'] += out_toks.count(GAP); st['xi'] += n_xi
                st['restored'] += len(events); st['joined'] += sum(e[1] - e[0] - 1 for e in events)
                st['zeta'] += sum(e[5].count('ⲍ') for e in events); st['psi'] += sum(e[5].count('ⲯ') for e in events)
            else:
                assert not events
            i = j
    assert accounted == n_src_tokens

    # ---- 書き出し
    os.makedirs(os.path.join(out, 'tsv'), exist_ok=True); os.makedirs(os.path.join(out, 'txt'), exist_ok=True)
    def fname(uid, slug):
        cx, tr = uid.split(','); return f'{ROMAN[cx]:02d}-{tr}_{slug}'
    cat, allrows, rest_rows = [], [], []
    for (uid, slug, en, ab, pp, rid, rx, occ, note) in UNITS:
        recs = units[uid]; fn = fname(uid, slug)
        if not recs:
            raise ValueError(f'unit {uid} is empty')
        with open(os.path.join(out, 'tsv', fn + '.tsv'), 'w', encoding='utf-8', newline='') as f:
            f.write('seq\tkind\tsrc_id\tsrc_tok\ttext\n')
            for n, (kd, sid, span, txt, events) in enumerate(recs, 1):
                assert '\t' not in txt and '\n' not in txt and '  ' not in txt
                f.write(f'{n}\t{kd}\t{sid}\t{span}\t{txt}\n')
                allrows.append((uid, n, kd, sid, span, txt))
                for a, b, orig, tok, word, letters, conf, why, ctx in events:
                    rest_rows.append((uid, n, kd, sid, f'{a}-{b}', orig, tok, word, letters, conf, why, ctx))
        with open(os.path.join(out, 'txt', fn + '.txt'), 'w', encoding='utf-8', newline='') as f:
            for kd, sid, span, txt, events in recs:
                f.write(txt + '\n')
        st = stats[uid]; cx, tr = uid.split(',')
        cat.append([uid, cx, tr, fn, en, ab, pp, recs[0][1], recs[-1][1], st['rows'], st['tokens'], st['gaps'], st['xi'], st['restored'], note])
    with open(os.path.join(out, 'nhc_all.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('unit\tseq\tkind\tsrc_id\tsrc_tok\ttext\n')
        for rec in allrows:
            f.write('\t'.join(str(x) for x in rec) + '\n')
    with open(os.path.join(out, 'catalog.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('\t'.join(['unit', 'codex', 'tractate', 'file', 'title_en', 'abbrev', 'pages_standard', 'src_id_first', 'src_id_last',
                           'rows', 'tokens', 'gap_markers', 'psi_to_xi', 'restored', 'note_ja']) + '\n')
        for c in cat:
            assert not any('\t' in str(x) or '\n' in str(x) for x in c)
            f.write('\t'.join(str(x) for x in c) + '\n')
    with open(os.path.join(out, 'changes.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('type\tunit\tsrc_id\tsrc_tok\tremoved_or_original\treplacement\treason\n')
        for rec in log:
            f.write('\t'.join(rec) + '\n')
    with open(os.path.join(out, 'restored_letters.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('unit\tseq\tkind\tsrc_id\tsrc_tok\tsource\trestored\tword\tletters\tconfidence\tnote\tcontext\n')
        for rec in rest_rows:
            assert not any('\t' in str(x) or '\n' in str(x) for x in rec)
            f.write('\t'.join(str(x) for x in rec) + '\n')
    with open(os.path.join(out, 'unresolved_letters.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('unit\tseq\tkind\tsrc_id\tsource\tpossibly\tnote\n')
        for sid, key, found, maybe, why in restore.UNRESOLVED:
            hit = [(uid, n, kd) for uid, n, kd, sid_, span, txt in allrows if sid_ == sid and key in txt.replace(' ', '')]
            if do_restore and len(hit) != 1:
                raise ValueError(f'unresolved entry {sid} {key}: found {len(hit)} records')
            for uid, n, kd in hit:
                f.write('\t'.join([uid, str(n), kd, sid, found, maybe, why]) + '\n')
    for fn_old in ('lost_letter_candidates.tsv',):                   # 旧版の出力が残っていれば消す
        if os.path.exists(os.path.join(out, fn_old)):
            os.remove(os.path.join(out, fn_old))

    c = collections.Counter(l[0] for l in log)
    print('rows', len(rows), 'tokens', n_src_tokens, 'units', len(UNITS), 'output rows', len(allrows))
    print('log', dict(c)); print('psi->xi', sum(s['xi'] for s in stats.values()), 'gap markers', sum(s['gaps'] for s in stats.values()))
    print('restored tokens', len(rest_rows), 'zeta', sum(st['zeta'] for st in stats.values()), 'psi', sum(st['psi'] for st in stats.values()),
          'tokens joined away', sum(st['joined'] for st in stats.values()),
          'A', sum(1 for x in rest_rows if x[9] == 'A'), 'B', sum(1 for x in rest_rows if x[9] == 'B'))
    return cat

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
