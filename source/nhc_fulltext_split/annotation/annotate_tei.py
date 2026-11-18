#!/usr/bin/env python3
"""Provisional linguistic annotation of Sheneset bound-group TEI documents.
Source lexicon: eugnostos_tei.xml and republic_tei.xml. Additionally a small
manually authored set of high-frequency Coptic morphemes is used. This is NOT
an automatic published edition, and low-confidence assignments need checking.
No source characters or segmentation IDs are changed.
"""
import re, csv, hashlib, sys
from collections import Counter, defaultdict
from pathlib import Path
from lxml import etree as E

NS='http://www.tei-c.org/ns/1.0'; XML='http://www.w3.org/XML/1998/namespace'
q=lambda a:'{'+NS+'}'+a
ns={'t':NS}
source_dir=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/tei_annotation_work')
out_dir=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/mnt/data/tei_annotated_draft/xml')
root_dir=Path(sys.argv[3]) if len(sys.argv)>3 else Path('/mnt/data')
out_dir.mkdir(parents=True,exist_ok=True)

def txt(w): return ''.join(w.itertext()).strip()
def clip(s): return re.sub(r'\s+','',s or '')
def hashid(s): return hashlib.sha1(s.encode()).hexdigest()[:12]

# Manually controlled high-frequency lexical list: FORM | POS | LEMMA | EN gloss | JA gloss
# Entries are provisional and should be compared to specialized grammatical reference works.
LEXICON='''
ⲁⲩⲱ|CONJ|ⲁⲩⲱ|and|そして
ϫⲉ|CONJ|ϫⲉ|that / saying|〜と／ということ
ⲇⲉ|PTC|ⲇⲉ|but / and|しかし／そして
ⲅⲁⲣ|PTC|ⲅⲁⲣ|for / because|なぜなら
ⲁⲗⲗⲁ|CONJ|ⲁⲗⲗⲁ|but / rather|しかし／むしろ
ⲏ|CONJ|ⲏ|or|または
ⲙⲉⲛ|PTC|ⲙⲉⲛ|on the one hand|一方では
ⲟⲩⲇⲉ|CONJ|ⲟⲩⲇⲉ|nor|〜もまたない
ⲕⲁⲓ|CONJ|ⲕⲁⲓ|and / even|そして／〜さえ
ⲟⲛ|ADV|ⲟⲛ|again / also|再び／また
ⲧⲟⲧⲉ|ADV|ⲧⲟⲧⲉ|then|そのとき
ϭⲉ|PTC|ϭⲉ|then / therefore|それでは／ゆえに
ⲉⲃⲟⲗ|ADV|ⲉⲃⲟⲗ|out / outward|外へ／外に
ⲉϩⲣⲁⲓ|ADV|ⲉϩⲣⲁⲓ|upward / forth|上方へ／外へ
ⲉϩⲟⲩⲛ|ADV|ⲉϩⲟⲩⲛ|inward|内へ
ⲉⲛⲉϩ|ADV|ⲉⲛⲉϩ|forever|永遠に
ⲙⲙⲁⲩ|ADV|ⲙⲙⲁⲩ|there|そこに
ⲙⲙⲉⲩ|ADV|ⲙⲙⲁⲩ|there|そこに
ⲉⲛⲧ|CREL|ⲉⲛⲧ|which / that|〜したところの
ⲉⲧ|REL|ⲉⲧ|who / which|〜であるところの
ⲉⲧⲉ|REL|ⲉⲧⲉ|that is / which|すなわち／〜であるところの
ⲛⲧ|REL|ⲛⲧ|which / that|〜したところの
ⲛⲧⲁ|CFOC|ⲛⲧⲁ|who / which (past)|〜したところの（過去）
ⲛϭⲓ|PTC|ⲛϭⲓ|subject marker|主語標識
ⲉⲧⲃⲉ|PREP|ⲉⲧⲃⲉ|because of / concerning|〜のために／〜について
ⲉϫⲛ|PREP|ⲉϫⲛ|upon|〜の上に
ⲛϩⲏⲧ|PREP|ⲛϩⲏⲧ|in / within|〜の中に
ϩⲓ|PREP|ϩⲓ|on / at|〜の上に／〜に
ϩⲛ|PREP|ϩⲛ|in|〜の中に
ϩⲙ|PREP|ϩⲛ|in|〜の中に
ϩⲁ|PREP|ϩⲁ|under / before|〜の下に／前に
ϩⲓⲧⲛ|PREP|ϩⲓⲧⲛ|by / through|〜によって／通して
ⲙⲙⲟ|PREP|ⲙⲙⲟ|of / object marker|〜を（目的語標識）
ⲉⲣⲟ|PREP|ⲉⲣⲟ|to / toward|〜へ／〜に
ⲛⲥⲱ|PREP|ⲛⲥⲁ|after|〜の後に
ⲕⲁⲧⲁ|PREP|ⲕⲁⲧⲁ|according to|〜に従って
ϩⲱⲥ|CONJ|ϩⲱⲥ|as / like|〜として
ⲛⲧⲉ|PREP|ⲛⲧⲉ|of / belonging to|〜の
ⲡ|ART|ⲡ|the (masculine)|定冠詞（男性単数）
ⲧ|ART|ⲧ|the (feminine)|定冠詞（女性単数）
ⲟⲩ|ART|ⲟⲩ|a / an|不定冠詞
ⲡⲓ|ART|ⲡ|the (masculine)|定冠詞（男性）
ⲧⲓ|ART|ⲧ|the (feminine)|定冠詞（女性）
ⲛⲓ|ART|ⲛ|the (plural)|定冠詞（複数）
ϩⲉⲛ|ART|ϩⲉⲛ|some / plural indefinite|不定冠詞（複数）
ⲛⲁⲓ|PDEM|ⲛⲁⲓ|these|これら
ⲡⲁⲓ|PDEM|ⲡⲁⲓ|this (masculine)|このもの（男性）
ⲧⲁⲓ|PDEM|ⲧⲁⲓ|this (feminine)|このもの（女性）
ⲛⲏ|PDEM|ⲛⲏ|those|それら
ⲡⲏ|PDEM|ⲡⲏ|that (masculine)|あのもの（男性）
ⲡⲉϥ|PPOS|ⲡⲉϥ|his|彼の
ⲧⲉϥ|PPOS|ⲧⲉϥ|his (feminine noun)|彼の（女性名詞）
ⲛⲉϥ|PPOS|ⲛⲉϥ|his (plural noun)|彼の（複数名詞）
ⲡⲉⲥ|PPOS|ⲡⲉⲥ|her|彼女の
ⲛⲉⲩ|PPOS|ⲛⲉⲩ|their|彼らの
ⲡⲟⲩ|PPOS|ⲡⲟⲩ|their|彼らの
ⲧⲟⲩ|PPOS|ⲧⲟⲩ|their|彼らの
ⲧⲉⲧⲛ|PPER|ⲧⲉⲧⲛ|you (plural)|あなたがた
ⲁⲛⲟⲕ|PPER|ⲁⲛⲟⲕ|I|私
ⲁⲛⲟⲛ|PPER|ⲁⲛⲟⲛ|we|私たち
ⲛⲧⲟϥ|PPER|ⲛⲧⲟϥ|he|彼
ⲛⲧⲟⲥ|PPER|ⲛⲧⲟⲥ|she|彼女
ⲛⲧⲟⲟⲩ|PPER|ⲛⲧⲟⲟⲩ|they|彼ら
ⲥⲉ|PPER|ⲥⲉ|they|彼らは
ⲧⲛ|PPER|ⲧⲛ|we / us|私たち
ϥ|PPER|ϥ|he / him|彼／彼を
ⲥ|PPER|ⲥ|she / her|彼女／彼女を
ⲩ|PPER|ⲩ|they / them|彼ら／彼らを
ⲕ|PPER|ⲕ|you (masc.)|あなた
ⲓ|PPER|ⲓ|I / me|私
ⲟⲩⲛ|EXIST|ⲟⲩⲛ|there is|〜がある
ⲙⲛ|NEG|ⲙⲛ|there is not / without|〜がない／〜なしに
ⲁⲛ|NEG|ⲁⲛ|not|〜ない
ⲧⲙ|NEG|ⲧⲙ|not / lest|〜しない／〜しないように
ⲙⲡⲣ|NEG|ⲙⲡⲣ|do not (prohibition)|〜するな
ⲁ|APST|ⲁ|perfect / past tense marker|完了・過去標識
ⲛⲁ|FUT|ⲛⲁ|future marker|未来標識
ⲛⲉ|PRET|ⲛⲉ|past reference marker|過去時制標識
ϣⲁ|AAOR|ϣⲁ|aorist / habitual|アオリスト／習慣
ⲙⲡⲉ|ANEGPST|ⲙⲡⲉ|negative past|過去否定標識
ⲛⲧⲉ|PREP|ⲛⲧⲉ|of|〜の
ⲧⲣⲉ|ACAUS|ⲧⲣⲉ|causative infinitive marker|使役不定詞標識
ⲙⲛⲧ|PFX|ⲙⲛⲧ|abstract noun formative|抽象名詞形成要素
ⲣⲉϥ|PFX|ⲣⲉϥ|agent noun formative|動作主名詞形成要素
ⲁⲧ|PFX|ⲁⲧ|without / privative|否定的派生接頭辞
ⲕⲉ|ADJ|ⲕⲉ|another / other|他の
ⲛⲓⲙ|ADJ|ⲛⲓⲙ|every / all|あらゆる
ⲛⲟϭ|ADJ|ⲛⲟϭ|great / big|大きい／偉大な
ⲟⲩⲁ|NUM|ⲟⲩⲁ|one|一つ
ⲥⲛⲁⲩ|NUM|ⲥⲛⲁⲩ|two|二
ⲧⲏⲣ|ADJ|ⲧⲏⲣ|all / entire|全体の
ϣⲟⲣⲡ|ADJ|ϣⲟⲣⲡ|first|最初の
ⲛⲁⲩ|N|ⲛⲁⲩ|time / hour|時／時間
ⲙⲁ|N|ⲙⲁ|place|場所
ⲣⲱⲙⲉ|N|ⲣⲱⲙⲉ|person / human|人間
ⲥϩⲓⲙⲉ|N|ⲥϩⲓⲙⲉ|woman|女性
ⲛⲟⲩⲧⲉ|N|ⲛⲟⲩⲧⲉ|god|神
ϣⲏⲣⲉ|N|ϣⲏⲣⲉ|child / son|子／息子
ⲉⲓⲱⲧ|N|ⲉⲓⲱⲧ|father|父
ⲙⲁⲁⲩ|N|ⲙⲁⲁⲩ|mother|母
ⲃⲁⲗ|N|ⲃⲁⲗ|eye|目
ϩⲏⲧ|N|ϩⲏⲧ|heart / interior|心／内部
ⲣⲁⲛ|N|ⲣⲁⲛ|name|名
ⲙⲟⲩ|N|ⲙⲟⲩ|death|死
ⲱⲛϩ|N|ⲱⲛϩ|life|生命
ϭⲟⲙ|N|ϭⲟⲙ|power|力
ⲟⲩⲟⲉⲓⲛ|N|ⲟⲩⲟⲉⲓⲛ|light|光
ⲕⲁⲕⲉ|N|ⲕⲁⲕⲉ|darkness|闇
ⲕⲁϩ|N|ⲕⲁϩ|earth|地／大地
ⲙⲁⲩ|N|ⲙⲁⲩ|mother / place|母／場所
ⲕⲟⲥⲙⲟⲥ|N|ⲕⲟⲥⲙⲟⲥ|world / cosmos|世界／宇宙
ⲁⲓⲱⲛ|N|ⲁⲓⲱⲛ|aeon|アイオーン
ⲉⲱⲛ|N|ⲁⲓⲱⲛ|aeon|アイオーン
ⲗⲟⲅⲟⲥ|N|ⲗⲟⲅⲟⲥ|word / Logos|言葉／ロゴス
ⲥⲟⲫⲓⲁ|N|ⲥⲟⲫⲓⲁ|wisdom / Sophia|知恵／ソフィア
ⲅⲛⲱⲥⲓⲥ|N|ⲅⲛⲱⲥⲓⲥ|knowledge / gnosis|認識／グノーシス
ⲇⲩⲛⲁⲙⲓⲥ|N|ⲇⲩⲛⲁⲙⲓⲥ|power|力
ⲁⲣⲭⲱⲛ|N|ⲁⲣⲭⲱⲛ|ruler / archon|支配者／アルコーン
ⲁⲅⲅⲉⲗⲟⲥ|N|ⲁⲅⲅⲉⲗⲟⲥ|angel / messenger|天使／使者
ⲥⲱⲙⲁ|N|ⲥⲱⲙⲁ|body|身体
ⲟⲩⲥⲓⲁ|N|ⲟⲩⲥⲓⲁ|essence / being|本質／存在
ⲛⲟⲩⲥ|N|ⲛⲟⲩⲥ|mind / intellect|ヌース／知性
ⲡⲛⲉⲩⲙⲁ|N|ⲡⲛⲉⲩⲙⲁ|spirit|霊
ⲯⲩⲭⲏ|N|ⲯⲩⲭⲏ|soul|魂
ⲁⲇⲁⲙ|NPROP|ⲁⲇⲁⲙ|Adam|アダム
ⲓⲥ|NPROP|ⲓⲏⲥⲟⲩⲥ|Jesus|イエス
ⲓⲟⲩⲇⲁⲥ|NPROP|ⲓⲟⲩⲇⲁⲥ|Judas|ユダ
ⲡⲓⲱⲧ|N|ⲉⲓⲱⲧ|father|父
ⲟⲩⲱϣ|V|ⲟⲩⲱϣ|wish / desire|望む
ⲣ|V|ⲣ|do / make|行う／作る
ⲉⲓⲣⲉ|V|ⲉⲓⲣⲉ|do / make|行う／作る
ⲁⲣ|V|ⲣ|do / make|行う／作る
ⲟⲩⲱⲛϩ|V|ⲟⲩⲱⲛϩ|reveal / appear|現れる／明らかにする
ϣⲱⲡⲉ|V|ϣⲱⲡⲉ|become / happen|なる／生じる
ϣⲟⲟⲡ|VSTAT|ϣⲱⲡⲉ|exist / be|存在する／ある
ⲉⲓ|V|ⲉⲓ|come|来る
ⲃⲱⲕ|V|ⲃⲱⲕ|go|行く
ⲧⲁⲙⲓⲟ|V|ⲧⲁⲙⲓⲟ|create|創造する
ϫⲡⲟ|V|ϫⲡⲟ|beget / acquire|生む／得る
ϫⲓ|V|ϫⲓ|take / receive|取る／受け取る
ϯ|V|ϯ|give|与える
ϫⲱ|V|ϫⲱ|say / speak|語る／言う
ϫⲟⲟ|V|ϫⲱ|say / speak|語る／言う
ϣⲁϫⲉ|V|ϣⲁϫⲉ|speak|話す
ⲡⲉϫⲁ|VBD|ϫⲱ|said|言った
ⲡⲉϫⲉ|VBD|ϫⲱ|said|言った
ⲥⲱⲧⲙ|V|ⲥⲱⲧⲙ|hear|聞く
ⲉⲓⲙⲉ|V|ⲉⲓⲙⲉ|know / understand|知る／理解する
ⲥⲟⲟⲩⲛ|V|ⲥⲟⲟⲩⲛ|know|知る
ⲙⲉ|V|ⲙⲉ|love|愛する
ⲙⲟⲩⲧⲉ|V|ⲙⲟⲩⲧⲉ|call / name|呼ぶ／名づける
ⲕⲱ|V|ⲕⲱ|put / leave|置く／残す
ⲕⲁ|V|ⲕⲱ|put / leave|置く／残す
ⲣⲁϣⲉ|V|ⲣⲁϣⲉ|rejoice|喜ぶ
ⲧⲛⲧⲱⲛ|V|ⲧⲛⲧⲱⲛ|resemble|似る
ⲉⲓⲛⲉ|V|ⲉⲓⲛⲉ|bring / resemble|持ってくる／似る
ⲙⲉⲉⲩⲉ|N|ⲙⲉⲉⲩⲉ|thought|思想／思考
ϩⲱⲃ|N|ϩⲱⲃ|matter / work|事柄／仕事
ⲣⲟ|N|ⲣⲟ|mouth|口
ⲣⲱ|N|ⲣⲟ|mouth|口
ⲣⲉⲥ|N|ⲣⲉⲥ|dream|夢
ϩⲉ|N|ϩⲉ|manner|仕方／方法
ⲙⲡⲉ|ANEGPST|ⲙⲡⲉ|not (past)|〜しなかった
ⲛⲛ|PREP|ⲛ|to / of|〜の／〜に
ⲙⲡ|PREP|ⲛ|of the|〜の
ⲛⲟⲩ|PPOS|ⲛⲟⲩ|of their|彼らの／〜の
'''
manual={}
for ln in LEXICON.strip().splitlines():
 f,t,l,en,ja=ln.split('|');manual[f]=(t,l,en,ja)

# Context-sensitive morphological short forms (no semantic context-invariant lemma is forced).
PRON={'ϥ':('he / him','彼／彼を'),'ⲥ':('she / her','彼女／彼女を'),'ⲩ':('they / them','彼ら／彼らを'),
'ⲕ':('you','あなた'),'ⲓ':('I / me','私'),'ⲧⲛ':('we / us','私たち'),'ⲥⲉ':('they','彼ら')}
ARTS={'ⲡ','ⲧ','ⲛ','ⲟⲩ','ⲡⲓ','ⲧⲓ','ⲛⲓ','ϩⲉⲛ','ⲡⲉ','ⲧⲉ','ⲛⲉ','ⲡⲉϥ','ⲧⲉϥ','ⲛⲉϥ','ⲡⲁ','ⲧⲁ','ⲡⲟⲩ','ⲧⲟⲩ','ⲛⲉⲩ'}
PAST={'ⲁ','ⲁⲩ','ⲙⲡⲉ','ⲁϥ','ⲁⲥ','ⲁⲕ','ⲁⲓ','ⲛⲧⲁ','ⲡⲉϫⲁ'}
VERBCUES={'ⲁ','ⲁⲩ','ⲛⲁ','ⲉ','ⲛⲧⲁ','ⲙⲡⲉ','ⲛⲧ','ⲉⲣⲉ','ϣⲁ','ⲧⲣⲉ','ⲛⲥⲉ','ⲉϥ'}
LINKFORMS={'ⲛ','ⲙ','ⲉ','ⲛⲁ','ⲡⲉ','ⲧⲉ','ⲛⲉ','ⲟⲩ','ⲉⲓ','ϯ','ⲙⲛ','ⲛⲧⲉ','ⲉⲧ','ⲛⲧ','ⲙⲡ','ϣⲁ','ⲧⲁ','ⲡⲁ','ⲛⲟⲩ','ⲙⲉ','ⲛⲁⲩ','ⲟ','ⲧⲉⲧⲛ'}

def load_ref():
    catalog=defaultdict(Counter); lang=defaultdict(Counter); gloss=defaultdict(Counter)
    for name in ['eugnostos_tei.xml','republic_tei.xml']:
        r=E.parse(str(root_dir/name))
        glossmap={v.get('{'+XML+'}id'): ''.join(v.itertext()).strip() for v in r.findall('.//t:interpGrp[@type="gloss"]/t:interp',ns)}
        for w in r.findall('.//t:body//t:w',ns):
            f=txt(w); t=w.get('type');lem=w.get('lemma')
            if not t or t in ('X','UNKNOWN','Ⲛ') or not lem:continue
            catalog[f][(t,lem)]+=1
            if w.get('{'+XML+'}lang')=='grc':lang[(f,t,lem)]['grc']+=1
            for a in (w.get('ana') or '').split():
                key=a.lstrip('#')
                if key in glossmap:gloss[(t,lem)][glossmap[key]]+=1
    return catalog,lang,gloss
cat,langs,refgloss=load_ref()

# Gloss map built from reference and controlled core morpheme list.
glosses={}
for form,(pos,lemma,en,ja) in manual.items():
    glosses[(pos,lemma)]=(en,ja)
# supplemental glosses from reference (use only unique clearly attested sense)
for key,ct in refgloss.items():
    if key not in glosses and len(ct)==1:
        glosses[key]=(ct.most_common(1)[0][0],None)


def contextual(form,forms,i):
    prev=forms[i-1] if i else ''
    nxt=forms[i+1] if i+1<len(forms) else ''
    isfirst=i==0;islast=i==len(forms)-1
    # All decisions here are conservative and confidence-labeled.
    if form in ('ⲡⲉ','ⲧⲉ','ⲛⲉ'):
        if not islast and (nxt not in PRON):return ('ART',{'ⲡⲉ':'ⲡ','ⲧⲉ':'ⲧ','ⲛⲉ':'ⲛ'}[form], 'medium')
        return ('COP',form,'medium')
    if form=='ⲛ':
        if isfirst and not islast and nxt in ('ⲥⲉ','ⲁ','ⲛⲧⲁ','ⲛⲁ'):
            return ('PREP','ⲛ','low')
        if isfirst and not islast and nxt in ('ⲣⲱⲙⲉ','ⲣⲁⲛ','ⲟⲩⲧⲉ','ϣⲏⲣⲉ'):
            return ('ART','ⲛ','low')
        return ('PREP','ⲛ','medium')
    if form=='ⲙ':return ('PREP','ⲛ','medium')
    if form=='ⲉ':
        if nxt in ('ϥ','ⲥ','ⲩ','ⲕ','ⲛ','ⲧⲛ') and isfirst:
            return ('CCIRC','ⲉ','low')
        return ('PREP','ⲉ','medium')
    if form=='ⲟⲩ':
        if isfirst and not islast:return ('ART','ⲟⲩ','medium')
        if islast and prev in {'ϫⲟⲟ','ⲙⲙⲟ','ⲉⲣⲟ','ⲧⲏⲣ','ⲛϩⲏⲧ','ϫⲱ'}:return ('PPER','ⲩ','medium')
        if islast:return ('ART','ⲟⲩ','low')
        return ('ART','ⲟⲩ','low')
    if form=='ⲛⲁ':
        if i and prev in PRON and not islast:return ('FUT','ⲛⲁ','medium')
        if not islast and nxt in ('ϫⲓ','ϣⲱⲡⲉ','ϫⲱ','ⲃⲱⲕ','ⲟⲩⲱⲛϩ','ⲉⲓⲣⲉ','ⲣ','ⲧⲁⲙⲓⲟ'):
            return ('FUT','ⲛⲁ','medium')
        return ('PREP','ⲛⲁ','medium')
    if form=='ⲙⲛ':
        if isfirst and islast:return ('NEG','ⲙⲛ','low')
        return ('PREP','ⲙⲛ','low')
    if form=='ϯ':
        if (prev in PAST or nxt in {'ϣⲱⲡⲉ','ⲣ','ⲉⲓⲣⲉ','ⲟⲩⲱϣ','ⲧⲁⲙⲓⲟ'}):return ('PPER','ϯ','medium')
        return ('V','ϯ','low')
    if form=='ⲉⲓ':
        if prev in PAST:return ('PPER','ⲁⲛⲟⲕ','medium')
        if i==0 and not islast:return ('PPER','ⲁⲛⲟⲕ','low')
        return ('V','ⲉⲓ','low')
    if form=='ϣⲁ' and not islast:return ('AAOR','ϣⲁ','medium')
    if form in ('ⲡⲁ','ⲧⲁ'):
        if not islast:return ('PPOS',form,'medium')
        return ('PPOS',form,'low')
    if form=='ⲙⲉ':
        if (prev in PRON or prev in {'ⲁ','ⲉ','ϣⲁ'}):return ('V','ⲙⲉ','medium')
        return ('N','ⲙⲉ','low')
    if form=='ⲛⲁⲩ' and prev in {'ⲉ','ⲛ','ⲙⲙⲟ'}:return ('PPER','ⲛⲁⲩ','low')
    return None

# Small number of lexical forms that have variant forms/orthography but are not
# fully analyzed in the user-provided witnesses.
def lexical_guess(form,forms,i, assigned):
    if len(form)<3 or not re.search('[\u2c80-\u2cff\u03e2-\u03ef]',form):
        return ('X',None,'low')
    prev=forms[i-1] if i else ''
    prevtag=assigned[-1] if assigned else ''
    if i>0 and (prev in ARTS or prevtag in ('ART','PPOS','PDEM')):
        return ('N',form,'low')
    if i>0 and (prev in PRON or prevtag in ('PPER','APST','AAOR','FUT','ACAUS')):
        return ('V',form,'low')
    if i>0 and prev in ('ⲛ','ⲙ','ⲉ','ϩⲛ','ϩⲙ','ⲧⲟⲩ'):
        return ('N',form,'low')
    # standalone long loanword endings, frequently nouns, not all are reliable
    if i==0 and len(forms)==1 and (form.endswith('ⲟⲥ') or form.endswith('ⲓⲁ') or form.endswith('ⲏⲥ')):
        return ('N',form,'low')
    return ('X',None,'low')

def classify(form,forms,i,assigned,existing):
    if existing and existing[0] and existing[1]:return (*existing, 'high', 'copied_reference')
    if form in LINKFORMS:
        ctx=contextual(form,forms,i)
        if ctx:return (*ctx,'context_rule')
    if form in manual:
        pos,lemma,_,_=manual[form]
        return pos,lemma,'medium','core_lexicon'
    if form in cat:
        vals=cat[form]
        (t,l),n=vals.most_common(1)[0];total=sum(vals.values())
        if total>=2 and n/total>=.8:
            return t,l,'high' if total>=3 and n/total>=.95 else 'medium','reference_lexicon'
        if n/total>=.55:
            return t,l,'low','ambiguous_reference'
    t,l,cert=lexical_guess(form,forms,i,assigned)
    return t,l,cert,'context_heuristic' if t!='X' else 'unresolved'

# Note: original <w> texts & s ids, and the original <phr> grouping, are frozen.
records=[]; detailed=[]; uncertain=Counter(); overall=Counter(); gloss_ids={}
for file in sorted(source_dir.glob('*.xml')):
    if not re.match(r'^\d\d-\d[a-z]?_', file.name):continue
    root=E.parse(str(file),E.XMLParser(remove_blank_text=False,resolve_entities=False,no_network=True))
    before=[(s.get('{'+XML+'}id'),''.join(txt(w) for w in s.findall('.//t:w',ns))) for s in root.findall('.//t:body//t:s',ns)]
    total=Counter(); formsmap=defaultdict(Counter); exmap=defaultdict(list)
    for seg in root.findall('.//t:body//t:s',ns):
        sid=seg.get('{'+XML+'}id') or seg.get('n') or '?'
        for phr in seg.findall('t:phr',ns):
            ww=phr.findall('t:w',ns); forms=[txt(w) for w in ww]; done=[]
            for i,w in enumerate(ww):
                f=forms[i]; orig=(w.get('type'),w.get('lemma'))
                t,lemma,cert,src=classify(f,forms,i,done,orig)
                w.set('type',t);w.set('cert',cert);w.set('resp','#morph-auto' if src!='copied_reference' else '#morph-reference')
                if lemma:w.set('lemma',lemma)
                elif 'lemma' in w.attrib:del w.attrib['lemma']
                if (f,t,lemma) in langs and langs[(f,t,lemma)]['grc']:
                    w.set('{'+XML+'}lang','grc')
                g=glosses.get((t,lemma))
                if g:
                    refs=[]
                    for lang,gl in [('en',g[0]),('ja',g[1])]:
                        if not gl:continue
                        glkey=(lang,gl);gid='g-'+lang+'-'+hashid(gl)
                        gloss_ids[glkey]=gid
                        refs.append('#'+gid)
                    if refs:
                        other=[an for an in (w.get('ana') or '').split() if not an.startswith('#g-')]
                        w.set('ana',' '.join(other+refs))
                done.append(t)
                total[(cert,src)]+=1;formsmap[f][(t,lemma or '',cert,src)]+=1
                if cert=='low' and len(exmap[f])<3:exmap[f].append(sid)
    # Add grouped stand-off glossary and metadata, without altering source text.
    tei=root.getroot();head=tei.find(q('teiHeader'))
    title=tei.find('./t:teiHeader/t:fileDesc/t:titleStmt',ns)
    if title is not None:
        rsp=E.SubElement(title,q('respStmt'));rsp.set('{'+XML+'}id','morph-auto')
        E.SubElement(rsp,q('resp')).text='Provisional morphosyntactic analysis from reference witnesses, a controlled core list, and explicitly flagged heuristics'
        E.SubElement(rsp,q('name')).text='Automated draft, for human review'
        rsp2=E.SubElement(title,q('respStmt'));rsp2.set('{'+XML+'}id','morph-reference')
        E.SubElement(rsp2,q('resp')).text='Morphological assignments copied from the supplied annotated reference text'
        E.SubElement(rsp2,q('name')).text='Eugnostos Digital Corpus project'
    edit=tei.find('./t:teiHeader/t:encodingDesc/t:editorialDecl',ns)
    if edit is not None:
        interpretation=edit.find(q('interpretation'))
        if interpretation is None:interpretation=E.SubElement(edit,q('interpretation'))
        paragraph=E.SubElement(interpretation,q('p'));paragraph.set('{'+XML+'}lang','ja')
        paragraph.text='本版の形態素注釈は自動生成された暫定案。w/@type は仮の品詞、w/@lemma は推定できた場合の見出し語、w/@ana は standOff の英日語釈を参照する。w/@cert は high（参考本文との一致など）、medium（参照辞書・規則）、low（未確定の形態素解析）を表す。未知語は type="X" とし、検証のない lemma や語釈を補わない。全体は校訂版・辞書との照合を要する。'
    rev=tei.find('./t:teiHeader/t:revisionDesc',ns)
    if rev is not None:
        ch=E.SubElement(rev,q('change'));ch.set('when','2026-11-18');ch.text='Provisional POS/lemma, stand-off English/Japanese glosses, and explicit confidence markers added; original Coptic text and segmentation preserved.'
    st=tei.find(q('standOff'))
    if st is None:st=E.SubElement(tei,q('standOff'))
    for lang in ('en','ja'):
        grp=E.SubElement(st,q('interpGrp'));grp.set('type','gloss');grp.set('{'+XML+'}lang',lang)
        for (glang,textg),idg in sorted(gloss_ids.items(),key=lambda a:a[1]):
            if glang!=lang:continue
            inter=E.SubElement(grp,q('interp'));inter.set('{'+XML+'}id',idg);inter.text=textg
    after=[(s.get('{'+XML+'}id'),''.join(txt(w) for w in s.findall('.//t:w',ns))) for s in root.findall('.//t:body//t:s',ns)]
    assert before==after, f'Text or segment ID mismatch {file}'
    assert not root.findall('.//t:body//t:s/t:w',ns),f'unwrapped w in {file}'
    outf=out_dir/file.name;root.write(str(outf),xml_declaration=True,encoding='utf-8',pretty_print=False)
    rr=E.parse(str(outf));assert len(rr.findall('.//t:body//t:s',ns))==len(before)
    for f,cts in formsmap.items():
        for (t,lem,cert,src),n in cts.items():
            if cert=='low':uncertain[(file.name,f,t,lem,src)]+=n
            overall[(cert,src)]+=n
    records.append({'file':file.name,'segments':len(before),'morphemes':sum(total.values()),
                    'high':sum(v for (conf,src),v in total.items() if conf=='high'),
                    'medium':sum(v for (conf,src),v in total.items() if conf=='medium'),
                    'low':sum(v for (conf,src),v in total.items() if conf=='low'),
                    'unknown_X':sum(v for (conf,src),v in total.items() if src=='unresolved'),
                    'source_text_unchanged':'yes','XML_parsed':'yes'})
    print(file.name, records[-1]['morphemes'], 'unknown',records[-1]['unknown_X'])

with (out_dir.parent/'annotation_report.tsv').open('w',encoding='utf-8',newline='') as fh:
 wr=csv.DictWriter(fh,fieldnames=records[0].keys(),delimiter='\t');wr.writeheader();wr.writerows(records)
with (out_dir.parent/'review_morphology.tsv').open('w',encoding='utf-8',newline='') as fh:
 wr=csv.writer(fh,delimiter='\t');wr.writerow(['file','surface','suggested_type','suggested_lemma','source','occurrences'])
 for (f,s,t,l,src),n in sorted(uncertain.items(),key=lambda it:(it[0][0],-it[1],it[0][1])):
    wr.writerow([f,s,t,l,src,n])
with (out_dir.parent/'core_glosses.tsv').open('w',encoding='utf-8',newline='') as fh:
 wr=csv.writer(fh,delimiter='\t');wr.writerow(['surface','type','lemma','English','日本語'])
 for form,(t,l,en,ja) in sorted(manual.items()):wr.writerow([form,t,l,en,ja])
print('TOTAL:',len(records),'documents',sum(x['morphemes'] for x in records),'morphemes',dict(overall))
