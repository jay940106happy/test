"""Build a self-contained reader from the original 1000 entries and reviewed examples."""
import collections
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
WORK = REPO/'working'
BANK_HASHES = {'01-04.txt':'861aab708a969e9b0ecb0e0f5db8fc939d67d6c0dd030d278f8e89e27bb44104','05-08.txt':'41eeb5e0dca6efa355532a8e1b5c28225593d8792727d88e57e577f808bdd5fc','09-12.txt':'613c9a886e031eda6b7ef0790da4e72b1504353020cefed0fa938f159980a59b','13-16.txt':'400090259263c4c7cd8e6cbef75992cf93fe1e8b49165f6a0d776b638135f04e','17-20.txt':'7ddbeb05d8e954dbf30e311c837439af5d763b7cdef94d694e1ff0713d23252d'}
source_path = ROOT/'source.json' if (ROOT/'source.json').exists() else WORK/'source.json'
base_path = ROOT/'words.json' if (ROOT/'words.json').exists() else WORK/'matched.json'
source = json.loads(source_path.read_text(encoding='utf-8'))
words = json.loads(base_path.read_text(encoding='utf-8'))
overrides = json.loads((ROOT/'overrides.json').read_text(encoding='utf-8'))
basic = []
for filename, expected in BANK_HASHES.items():
    path = ROOT/'examples'/filename
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, filename
    rows = [line.split('|') for line in path.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 200 and all(len(row) == 2 for row in rows), filename
    basic.extend(rows)
assert len(basic) == 1000
legacy = WORK/'legacy.html'
legacy_words = {}
if legacy.exists():
    match = re.search(r'<script id="word-data"[^>]*>(.*?)</script>',legacy.read_text(encoding='utf-8'),re.S)
    old = json.loads(match.group(1)) if match else []
    if isinstance(old,dict): old = old.get('words',[])
    assert len(old) == 16
    legacy_words = {w['word']:w for w in old}
for w, (en, zh) in zip(words,basic):
    assert w['word'].lower() in en.lower(), (w['number'],w['word'],en)
    if len(w['examples']) == 2:
        other = next((e for e in w['examples'] if e['en'] != en),None)
        assert other, w['word']
        w['examples'] = [{'en':en,'zh':zh},other]
        w['exampleSource'] = 'Wordstep basic sentence; kknono668/toeic-vocab-tw context sentence'
    old = legacy_words.get(w['word'])
    if old:
        w['examples'] = old['examples']
        w['tips'] = [old['tip']] if old.get('tip') else w.get('tips',[])
        w['exampleSource'] = 'Wordstep original examples'
    patch = overrides.get(str(w['number']))
    if patch:
        assert len(patch) == 4 and all(isinstance(s,str) and s.strip() for s in patch)
        w['examples'] = [{'en':patch[0],'zh':patch[1]},{'en':patch[2],'zh':patch[3]}]
        w['exampleSource'] = 'Wordstep original examples'
    w['tips'] = w.get('tips',[])[:1]
    w['forms'] = [f for f in w.get('forms',[]) if isinstance(f,str) and len(f)<50]
assert len(words) == len(source['words']) == 1000
assert len({w['id'] for w in words}) == 1000
assert list(collections.Counter(w['category'] for w in words).values()) == [50]*20
for i,(w,original) in enumerate(zip(words,source['words']),1):
    for key in ['word','pos','meaning','phrase','category']:
        assert w[key] == original[key], (i,key)
    assert w['number'] == i
    assert len(w['examples']) == 2, (i,w['word'])
    assert w['examples'][0]['en'] != w['examples'][1]['en'], (i,'duplicate example')
    for e in w['examples']:
        assert len(e['en'].split()) >= 3 and e['zh'].strip(), (i,'empty text')
        assert re.search(r'[\u3400-\u9fff]',e['zh']), (i,'missing translation')
encoded = json.dumps(words,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
template = (ROOT/'index.template.html').read_text(encoding='utf-8')
assert template.count('__WORDSTEP_DATA__') == 1
output = REPO/'docs/index.html'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(template.replace('__WORDSTEP_DATA__',encoded),encoding='utf-8')
(ROOT/'words.json').write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf-8')
metadata_path = WORK/'metadata.json'
meta = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else {}
meta.update({'entries':1000,'uniqueSpellings':999,'examples':2000,'categories':20,'incomplete':0,'originalExampleEntries':sum(w.get('exampleSource')=='Wordstep original examples' for w in words),'changes':'All original entries and order preserved. Basic sentence bank retained. Missing and ambiguous examples completed. Original 16 pairs and tips restored. Promotion has separate career and sales senses.'})
(ROOT/'provenance.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'entries':len(words),'examples':sum(len(w['examples']) for w in words),'categories':20,'missing':0,'htmlBytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
