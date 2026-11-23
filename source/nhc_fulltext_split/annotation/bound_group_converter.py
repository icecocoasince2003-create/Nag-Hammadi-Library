#!/usr/bin/env python3
"""A reproducible *provisional* Coptic TEI bound-group conversion.

Usage: python tei_boundgroup_convert.py --input-dir /path/to/xml --output-dir /path/to/output
The training references must be present in input-dir: eugnostos_tei.xml, republic_tei.xml.
The source XML files are selected by filenames beginning with NN-N_.

--ref PATH (repeatable; added 2026-11-23 for the evaluation in ../evaluation/):
use only the given annotated TEI file(s) as references, in the order given,
instead of input-dir/eugnostos_tei.xml and input-dir/republic_tei.xml. They are
the training data of the bound-group model and the source of the attested
morpheme splits; the <phr>/<w> of III,3 are copied only from a reference named
eugnostos_tei.xml, so none are copied when it is not among them. Example (held-out
check of VI,5): --ref data/eugnostos_tei.xml, so that republic_tei.xml is not seen.
Without --ref the behaviour and the output are byte for byte the same as before.
The model is deterministic: LogisticRegression with the lbfgs solver (the
scikit-learn default, now named explicitly) does not use random numbers;
random_state=12 is kept from the original.

No dictionary, lemma, POS or morphological correctness is claimed for inferred spans.
Original <w> nodes and attributes are left intact outside the exact-reference matches.
"""
import argparse, csv, copy, re, json, statistics
from collections import defaultdict, Counter
from pathlib import Path
from lxml import etree as ET
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

NS = 'http://www.tei-c.org/ns/1.0'
XML = 'http://www.w3.org/XML/1998/namespace'
N = {'tei': NS}
q=lambda tag: f'{{{NS}}}{tag}'
def s_id(s): return s.get(f'{{{XML}}}id', s.get('n',''))
def surface(w): return ''.join(w.itertext()).strip()
def plain_s(s):return ''.join(surface(w) for w in s.xpath('.//tei:w', namespaces=N))

STOP = {'ⲁⲩⲱ','ϫⲉ','ⲇⲉ','ⲅⲁⲣ','ⲁⲗⲗⲁ','ⲏ','ⲙⲉⲛ','ⲟⲩⲛ','ⲕⲁⲓ','ⲟⲩⲇⲉ','ⲧⲟⲧⲉ','ⲉⲡⲉⲓⲇⲏ','ⲉⲡⲓⲇⲏ','ϭⲉ'}
SHORT = {'ⲁ','ⲉ','ⲛ','ⲙ','ⲡ','ⲧ','ⲟⲩ','ⲥ','ϥ','ⲩ','ⲕ','ⲛⲉ','ⲧⲉ','ⲙⲡ','ⲛⲧ','ⲛⲁ','ⲛϭⲓ','ⲉⲧ','ⲛⲧⲁ','ⲁⲩⲱ','ⲧⲛ','ⲉⲣⲟ','ⲙⲙⲟ','ⲙⲙⲉ'}

DEFAULT_REFS = ('eugnostos_tei.xml','republic_tei.xml')

def ref_files(folder,ref_paths=None):
    """The reference files: those given with --ref, else the two defaults in folder."""
    return [Path(p) for p in ref_paths] if ref_paths else [folder/f for f in DEFAULT_REFS]

def train_refs(folder,ref_paths=None):
    refs=[]; counts=defaultdict(Counter); groups=Counter()
    for path in ref_files(folder,ref_paths):
        f=path.name
        root=ET.parse(str(path))
        for s in root.xpath('//tei:body//tei:s', namespaces=N):
            if not s.xpath('./tei:phr', namespaces=N): continue
            words=[];ends=[]
            for phr in s.xpath('./tei:phr', namespaces=N):
                local=phr.xpath('./tei:w', namespaces=N)
                if not local: continue
                group=tuple(surface(w) for w in local)
                groups[group]+=1
                for w in local:
                    words.append(surface(w));ends.append(False)
                    if w.get('type'):counts[surface(w)][w.get('type')]+=1
                ends[-1]=True
            if len(words)>1:refs.append((f,s_id(s),words,ends))
    return refs, counts, groups

# Unambiguous forms witnessed as a complete <phr> with multiple <w> in the references.
# Homographs such as ⲛⲁⲓ and ⲛⲟⲩ are deliberately excluded.
SAFE_SPLITS = {
    'ⲁϥ','ⲙⲙⲟⲥ','ⲙⲙⲟϥ','ⲙⲙⲟⲟⲩ','ⲡⲉϫⲁϥ','ⲡⲉϫⲁⲓ','ⲛϩⲏⲧϥ','ⲛϩⲏⲧⲟⲩ',
    'ⲛϩⲉ','ⲟⲩⲁⲁϥ','ⲟⲩϭⲟⲙ','ⲟⲩⲉⲓⲛⲉ','ϫⲱϥ','ⲧⲏⲣϥ','ⲧⲏⲣⲟⲩ','ⲉϥⲟ','ⲉϥϣⲟⲟⲡ',
    'ⲛⲧⲁⲉⲓⲣ','ⲡⲣⲱⲙⲉ','ⲡⲗⲟⲅⲟⲥ','ⲙⲡⲣⲱⲙⲉ','ⲛⲣⲱⲙⲉ','ⲙⲡϣⲁ','ⲛⲧⲯⲩⲭⲏ',
    'ⲛⲧⲙⲏⲧⲉ','ⲛϣⲟⲣⲡ','ϩⲓⲧⲟⲟⲧϥ','ⲙⲡⲓⲛⲉ','ⲉⲣⲟϥ','ⲛϫⲟⲟⲩ','ⲥⲟⲩⲱⲛϥ',
    'ⲁϥϫⲟⲟⲥ','ⲙⲡⲉⲡⲧⲁⲛⲧⲛ','ϣⲁϥⲁⲁϥ'
}

def exact_splits(groups):
    found=defaultdict(set)
    for words, n in groups.items():
        if len(words)>1 and ''.join(words) in SAFE_SPLITS:
            found[''.join(words)].add(words)
    return {a:next(iter(v)) for a,v in found.items() if len(v)==1}

def split_attested_w(s,mapping):
    count=0
    for w in list(s.xpath('./tei:w',namespaces=N)):
        parts=mapping.get(surface(w))
        if not parts or w.attrib or len(parts)<2: continue
        parent=w.getparent();idx=parent.index(w)
        for j,chunk in enumerate(parts):
            node=ET.Element(q('w'));node.text=chunk
            parent.insert(idx+j,node)
        parent.remove(w);count+=1
    return count

def features(toks,i,cats,group_counts):
    a,b=toks[i],toks[i+1]
    before=toks[i-1] if i>0 else '#'
    after=toks[i+2] if i+2<len(toks) else '#'
    def cat(z):return cats[z].most_common(1)[0][0] if cats.get(z) else '?'
    return {
        'a':a, 'b':b, 'pair':a+'|'+b, 'before':before, 'after':after,
        'cat_a':cat(a),'cat_b':cat(b),'cat_pair':cat(a)+'|'+cat(b),
        'cat_prev':cat(before),'cat_next':cat(after),
        'alen':len(a),'blen':len(b),'asmall':len(a)<=2,'bsmall':len(b)<=2,
        'apref':a[:2], 'bpref':b[:2], 'asuff':a[-2:], 'bsuff':b[-2:],
        'apref3':a[:3], 'bpref3':b[:3], 'asuff3':a[-3:], 'bsuff3':b[-3:],
        'as':a in SHORT,'bs':b in SHORT,'astop':a in STOP,'bstop':b in STOP,
        'knownpair':group_counts[(a,b)]>0,
    }

def make_model(refs,cats,groups):
    xx=[];yy=[]
    for _,_,words,ends in refs:
        for i in range(len(words)-1):
            xx.append(features(words,i,cats,groups)); yy.append(int(ends[i]))
    dv=DictVectorizer(sparse=True)
    mdl=LogisticRegression(max_iter=400,C=0.75, random_state=12, solver='lbfgs')
    mdl.fit(dv.fit_transform(xx),yy)
    return dv,mdl

def predict_words(words,vec,mdl,cats,groups):
    if len(words)<2: return []
    ff=[features(words,i,cats,groups) for i in range(len(words)-1)]
    return list(mdl.predict_proba(vec.transform(ff))[:,1])

def reference_map(folder,ref_paths=None):
    eug=[p for p in ref_files(folder,ref_paths) if p.name=='eugnostos_tei.xml']
    if not eug:return {}
    root=ET.parse(str(eug[0]))
    ss=root.xpath('//tei:body//tei:s',namespaces=N)
    return {s_id(s):s for s in ss if s.xpath('./tei:phr',namespaces=N)}

def copy_ref_phr(src_s,ref_s):
    """Use only if *entire* reconstructed Coptic sequence matches the source.

    Unresolved stand-off gloss ids are removed; source s attributes/ids preserved.
    """
    if plain_s(src_s) != plain_s(ref_s):return False
    if ref_s.xpath('./tei:w',namespaces=N):return False  # partially annotated reference
    if src_s.xpath('./tei:w[@cert or @resp or @ana or @xml:id]',namespaces=N):return False
    for ch in list(src_s):src_s.remove(ch)
    src_s.text=None
    for original in ref_s:
        if original.tag != q('phr'):continue
        phr=copy.deepcopy(original)
        for elem in phr.iter():
            if 'ana' in elem.attrib: del elem.attrib['ana']
            if elem.tag == q('w') and 'resp' in elem.attrib: del elem.attrib['resp']
        src_s.append(phr)
    return True

def flush_groups(s,group,groups_data,probabilities,review,batch_tag,group_conf):
    if not group:return
    phr=ET.SubElement(s,q('phr'))
    for w in group:
        w.tail=None
        phr.append(w)
    groups_data.append(group[:])
    group.clear()

def group_s(s,vec,mdl,cats,groups,review,doc,threshold=0.5):
    children=list(s)
    # For this dataset these are <w> interspersed with occasional <gap>.
    splits=[];chunk=[]
    for ch in children:
        if ch.tag==q('w'):
            chunk.append(ch)
        else:
            if chunk: splits.append(('words',chunk));chunk=[]
            splits.append(('other',[ch]))
    if chunk:splits.append(('words',chunk))
    for ch in children:s.remove(ch)
    s.text=None
    n_groups=0; uncertain=0; groupsizes=[]
    for kind,els in splits:
        if kind!='words':
            for el in els: el.tail=None;s.append(el)
            continue
        texts=[surface(w) for w in els]
        probs=predict_words(texts,vec,mdl,cats,groups)
        start=0
        for i,prob in enumerate(probs):
            # model-only grouping. Each originally tokenized <w> is preserved.
            # If huge groups arise from bad OCR / unusual dialect, force a boundary.
            must_close=(i-start+1 >= 10)
            # A stem-like unit followed by another stem-like unit normally
            # begins a new bound group, unless that exact pair is attested
            # as one orthographic word in the reference exemplars.
            long_pair=(len(texts[i])>=3 and len(texts[i+1])>=3
                       and (texts[i],texts[i+1]) not in groups
                       and not (cats.get(texts[i]) and cats[texts[i]].most_common(1)[0][0]
                                in {'ART','PPOS','REL','CREL','CFOS','CFOC','PREP','PDEM'}))
            close=prob >= threshold or must_close or long_pair
            if 0.35 <= prob <= 0.65 or must_close or long_pair:
                uncertain+=1
                if len(review)<90000:
                    review.append({'file':doc,'s_id':s_id(s),'after_w_no':str(i+1),
                         'left':texts[i], 'right':texts[i+1],
                         'boundary_probability':f'{prob:.3f}',
                         'chosen_boundary':'yes' if close else 'no',
                         'reason':'max_group_length' if must_close else ('long_lexical_pair' if long_pair else 'model_near_threshold')})
            if close:
                chunk=els[start:i+1]
                phr=ET.SubElement(s,q('phr'))
                for w in chunk: w.tail=None;phr.append(w)
                n_groups+=1;groupsizes.append(len(chunk));start=i+1
        if start<len(els):
            phr=ET.SubElement(s,q('phr'))
            for w in els[start:]:w.tail=None;phr.append(w)
            n_groups+=1;groupsizes.append(len(els)-start)
    return n_groups,uncertain,max(groupsizes or [0])

def add_doc_notes(root,file,ref_names=DEFAULT_REFS):
    # ref_names: basenames of the references (--ref); the default gives the original wording.
    ref_names=tuple(ref_names)
    copy_ja=('eugnostos_tei.xml の本文が文字単位で一致する既注釈箇所だけ参考の <phr>/<w> を転用した。'
             if 'eugnostos_tei.xml' in ref_names else '')
    learn_ja=('それ以外は ' if copy_ja else '')+'・'.join(ref_names)+' の既注釈例から学習した分類器で、元の <w> 間にグループ境界を推定した。'
    refs_en=('the two references' if ref_names==DEFAULT_REFS else
             ('the references ' if len(ref_names)>1 else 'the reference ')+', '.join(ref_names))
    enc=root.find('./'+q('teiHeader')+'/'+q('encodingDesc'))
    if enc is None:
        header=root.find('./'+q('teiHeader'))
        enc=ET.SubElement(header,q('encodingDesc'))
    decl=enc.find(q('editorialDecl'))
    if decl is None:decl=ET.SubElement(enc,q('editorialDecl'))
    seg=decl.find(q('segmentation'))
    if seg is None:seg=ET.SubElement(decl,q('segmentation'))
    p=ET.SubElement(seg,q('p'));p.set(f'{{{XML}}}lang','ja')
    p.text=('2026-11-18 暫定 bound-group 分析：<phr> はコプト語の正書法上のまとまり、<w> は形態素単位を表す。'
            +copy_ja+learn_ja+
            '元の <w> の切り方は原則維持し、元資料に含まれる誤分割・未分割を全面的に修正したものではない。'
            '人手による校正前の試案であり、分割結果を言語学上の確定事項と解釈しない。')
    # Mark methods as text-only: XML mentions of angle bracket in p.text escaped by serializer.
    rev=root.find('./'+q('teiHeader')+'/'+q('revisionDesc'))
    if rev is None:rev=ET.SubElement(root.find(q('teiHeader')),q('revisionDesc'))
    ch=ET.Element(q('change'));ch.set('when','2026-11-18')
    ch.text='Provisional bound-group segmentation into <phr> containing morpheme <w>, with exact-match reference reuse where available and automatically inferred boundaries elsewhere; original text verified against input.'
    rev.insert(0,ch)
    titles=root.xpath('./tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type="sub"]',namespaces=N)
    for title in titles:
        if title.get(f'{{{XML}}}lang')=='en':
            title.text=re.sub(r' — segmented Coptic text without linguistic annotation \(working file\)$',
               ' — provisional bound-group and morpheme TEI segmentation (for review)',title.text or '')
    p2=ET.SubElement(seg,q('p'));p2.set(f'{{{XML}}}lang','en')
    p2.text=('A small inventory of unambiguous surface forms is further split into morphemes based on '+refs_en+', but most source w segmentation remains unchanged. No broad morphological reanalysis or editorial collation has been performed; grouping is provisional.')
    # No lemmas/POS guessed where unavailable.

def convert(rootfile,outfile,ref_map,vec,mdl,cats,groups,review,morph_splits,ref_names=DEFAULT_REFS):
    parser=ET.XMLParser(remove_blank_text=True,resolve_entities=False,no_network=True)
    root=ET.parse(str(rootfile),parser)
    all_s=root.xpath('//tei:body//tei:s',namespaces=N)
    snapshot=[(s_id(s),plain_s(s)) for s in all_s]
    src_token_count=sum(len(s.xpath('./tei:w',namespaces=N)) for s in all_s)
    match=0;guess=0;uncertain=0;maxlen=0;attested_splits=0
    for s in all_s:
        if rootfile.name=='03-3_eugnostos.xml':
            # All prior annotated source segments after the incipit have unchanged IDs.
            ref=ref_map.get(s_id(s))
            if ref is None and s.get('n')=='1':ref=ref_map.get('III-INCIPIT')
            if ref is not None and copy_ref_phr(s,ref):
                match+=1;continue
        attested_splits+=split_attested_w(s,morph_splits)
        a,b,c=group_s(s,vec,mdl,cats,groups,review,rootfile.name)
        guess+=a;uncertain+=b;maxlen=max(maxlen,c)
    add_doc_notes(root.getroot(),rootfile.name,ref_names)
    # Account for the reference tokens whose morphological division differs from source input.
    measures=root.xpath('./tei:teiHeader/tei:fileDesc/tei:extent/tei:measure[@unit="token"]',namespaces=N)
    if not measures:measures=root.xpath('./teiHeader/fileDesc/extent/measure[@unit="token"]')
    new_w=len(root.xpath('//tei:body//tei:w',namespaces=N))
    for m in measures:
        m.set('quantity',str(new_w));m.text=f'{new_w} morpheme tokens (provisional)'
    # Cross-check every segment by reconstructing its full Coptic characters, ignoring group boundaries.
    for s,(orig_id,orig_chars) in zip(all_s,snapshot):
        if s_id(s)!=orig_id or plain_s(s)!=orig_chars:
            raise ValueError(f'Text or ID changed: {rootfile.name} :: {orig_id}')
    for s in all_s:
        assert not s.xpath('./tei:w',namespaces=N),f'Unwrapped <w> in {rootfile.name} {s_id(s)}'
    outfile.parent.mkdir(parents=True,exist_ok=True)
    root.write(str(outfile),encoding='utf-8',xml_declaration=True,pretty_print=True)
    check=ET.parse(str(outfile))
    assert len(check.xpath('//tei:body//tei:s',namespaces=N))==len(all_s)
    return {'file':rootfile.name,'segments':len(all_s),'input_w':src_token_count,
            'output_w':new_w,'bound_groups':len(root.xpath('//tei:body//tei:phr',namespaces=N)),
            'reference_matched_segments':match,'attested_w_splits':attested_splits,'model_groups':guess,
            'review_flagged_boundaries':uncertain,'max_group_length_model':maxlen,
            'text_and_IDs_preserved':'yes','xml_well_formed':'yes'}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input-dir',type=Path,default=Path('/mnt/data'))
    ap.add_argument('--output-dir',type=Path,default=Path('/mnt/data/tei_boundgroups_draft'))
    ap.add_argument('--ref',action='append',type=Path,metavar='PATH',
                    help='reference TEI file (repeatable); default: eugnostos_tei.xml and republic_tei.xml in --input-dir')
    args=ap.parse_args()
    for p in args.ref or []:
        if not p.is_file():ap.error(f'--ref: no such file: {p}')
    ref_names=tuple(p.name for p in ref_files(args.input_dir,args.ref))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    refs,cats,groups=train_refs(args.input_dir,args.ref)
    vec,mdl=make_model(refs,cats,groups)
    refmap=reference_map(args.input_dir,args.ref)
    morph_splits=exact_splits(groups)
    reviews=[]; rows=[]
    sources=sorted(f for f in args.input_dir.glob('*.xml') if re.match(r'^\d\d-\d[a-z]?_',f.name))
    for fn in sources:
        outf=args.output_dir/fn.name
        info=convert(fn,outf,refmap,vec,mdl,cats,groups,reviews,morph_splits,ref_names)
        print(json.dumps(info,ensure_ascii=False))
        rows.append(info)
    with (args.output_dir/'conversion_report.tsv').open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=rows[0].keys(),delimiter='\t');wr.writeheader();wr.writerows(rows)
    with (args.output_dir/'review_boundaries.tsv').open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=['file','s_id','after_w_no','left','right','boundary_probability','chosen_boundary','reason'],delimiter='\t');wr.writeheader();wr.writerows(reviews)
    (args.output_dir/'README_ja.txt').write_text('''暫定版：ナグ・ハマディTEI文書のbound group分割（2026-11-18）

・対象：アップロードされた 01-2 ～ 04-1 の文書17件。参照用eugnostos_tei.xmlとrepublic_tei.xmlは変換対象から除外。
・<s>、そのxml:id / n、<ab>、<gap>等の本文構造を保持。
・各<s>内の正書法上のbound groupを<phr>に、各形態素を<w>に配置。
・03-3エウグノストスのうち参考資料と文字列が一致する既注釈セグメントは、参考の<phr>/<w>を複写し、未定義のstand-offグロス参照(@ana)を削除。
・その他はeugnostos_tei.xmlとrepublic_tei.xmlの既<phr>箇所を教師例として学習した推定。元の<w>区切りは原則変更なしだが、参考資料に確認できる曖昧性の低い形態素複合形は一部だけ再分割。
・推定の際のグループ長の上限は10形態素。校訂本文・写本との照合や原文の修正は行っていない。
・正書法上のグループの検出は暫定的で、特に方言（リュコポリス系）、長文、大きな複合形、未知語、語中の不自然な<w>分割、写本の損傷箇所は要確認。
・未確認の品詞とlemmaは推測で補わず、元ファイルにないまま残してある。参考からの転用部には参考のtype/lemmaが入る。
・本文のコプト文字を<s>ごとに連結した結果とxml:idは原本と完全一致することを検証済み。XMLはすべて構文解析済み。
・conversion_report.tsv：文書ごとの件数と検証結果。
・review_boundaries.tsv：境界の推定確率が0.35～0.65で曖昧な位置、長い形態素連続のため境界を優先した位置など。確率は校正済みの信頼度ではない。

使い方：本フォルダにあるXMLを必要に応じて修正・校訂してください。元ファイルは上書きしていません。
再生成：tei_boundgroup_convert.py を入力 XML ファイル群と参考2件のあるディレクトリで実行してください。
  python tei_boundgroup_convert.py --input-dir ./input --output-dir ./output
'''+('' if not args.ref else
     '\n参考（--ref）：この出力の学習に使った参考は '+'、'.join(str(p) for p in args.ref)+' だけです。'
     '上の説明の参考2件（eugnostos_tei.xml、republic_tei.xml）は、この出力ではこれに置き換えて読んでください。\n'),encoding='utf-8')
    print('TOTAL',len(rows),'documents',sum(int(z['segments']) for z in rows),'segments',sum(int(z['output_w']) for z in rows),'w',sum(int(z['bound_groups']) for z in rows),'phr',len(reviews),'review flagged')

if __name__=='__main__':main()
