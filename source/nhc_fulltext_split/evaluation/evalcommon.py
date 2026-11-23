"""Shared helpers for the scripts in this folder (standard library only).

- letters(): the letters of a form, used to line up two versions of a text whose
  morphemes are cut differently.
- wilson(): 95% Wilson score interval of a proportion.
- strip_marks(): a string without combining marks (for the "normalised" lemma match).
- segments(): the <s> of a TEI file with their <w>, <phr> and <gap>, in document order,
  numbered the same way in every script (語の位置・語群の位置).
"""
import math
import re
import unicodedata
import xml.etree.ElementTree as ET

TEI = '{http://www.tei-c.org/ns/1.0}'
XML = '{http://www.w3.org/XML/1998/namespace}'
Z95 = 1.959963984540054          # two-sided 95% normal quantile

_BRACKETED = re.compile(r'\[[^\]]*\]')


def w_text(w):
    """The text of a <w>, including <supplied> and the text around <lb/> inside it."""
    return ''.join(w.itertext()).strip()


def letters(text):
    """The letters of a form, for alignment.

    Unicode NFD; square-bracketed parts removed together with their content (in
    data/republic_tei.xml they occur only in ⲑ[ⲧ] and [ϩ]ⲉ / [ϩ]ⲓⲕⲱⲛ, and the bracketed
    letters are not in the text of tei/06-5); then only characters of Unicode category
    L* are kept, lowercased.
    This drops whitespace, punctuation, combining marks (U+0304, U+0305, U+0308 ...),
    brackets and lacuna signs.
    """
    text = _BRACKETED.sub('', unicodedata.normalize('NFD', text or ''))
    return ''.join(ch for ch in text if unicodedata.category(ch).startswith('L')).lower()


def strip_marks(s):
    """NFD, combining marks (categories Mn, Me) removed, NFC, outer whitespace removed."""
    d = unicodedata.normalize('NFD', s or '')
    kept = ''.join(ch for ch in d if unicodedata.category(ch) not in ('Mn', 'Me'))
    return unicodedata.normalize('NFC', kept).strip()


def wilson(k, n, z=Z95):
    """95% Wilson score interval (low, high) for k successes in n trials; (nan, nan) if n == 0."""
    if not n:
        return (float('nan'), float('nan'))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def body_of(path):
    root = ET.parse(str(path)).getroot()
    body = root.find('.//' + TEI + 'body')
    if body is None:
        raise SystemExit(f'{path}: no <body>')
    return root, body


def segments(body):
    """[(s, ws, phr_of, items)] for every <s> under <body>, in document order.

    ws      all <w> descendants of the <s> in document order; the 1-based index in this
            list is 語の位置 (w_pos).
    phr_of  {w: k}: k is the 1-based index of the <phr> containing w among all <phr>
            descendants of the <s> (語群の位置); w outside any <phr> are missing.
    items   the reading order of the segment for showing context: ('phr', k, [w...]) for
            each <phr>, ('gap', None, []) for a <gap> outside any <phr>, ('w', None, [w])
            for a <w> outside any <phr>.
    """
    out = []
    for s in body.iter(TEI + 's'):
        ws = list(s.iter(TEI + 'w'))
        phr_index = {phr: k for k, phr in enumerate(s.iter(TEI + 'phr'), 1)}
        phr_of = {}
        for phr, k in phr_index.items():
            for w in phr.iter(TEI + 'w'):
                phr_of[w] = k
        items = []
        _walk(s, items, phr_index)
        out.append((s, ws, phr_of, items))
    return out


def _walk(el, items, phr_index):
    for ch in el:
        if ch.tag == TEI + 'phr':
            items.append(('phr', phr_index[ch], list(ch.iter(TEI + 'w'))))
        elif ch.tag == TEI + 'w':
            items.append(('w', None, [ch]))
        elif ch.tag == TEI + 'gap':
            items.append(('gap', None, []))
        else:
            _walk(ch, items, phr_index)
