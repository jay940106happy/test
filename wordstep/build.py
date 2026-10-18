"""Build the standalone learning page from the original table and bilingual examples."""
import hashlib
import json
import re
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CATEGORIES = ['辦公室與工作','人事與招募','會議與商務溝通','公司與管理','行銷與廣告','銷售與客戶','金融與銀行','會計與付款','採購與訂單','物流與配送','製造與生產','房地產與設施','科技與設備','商務旅行','交通','飯店與住宿','餐飲與服務','活動與娛樂','健康與日常服務','跨情境高頻字彙']
SOURCE_URL = 'https://www.david.com.tw/toeic/vocabulary/must-know-words/1000-words/'
EXPECTED_SOURCE = 'f69f3e4dbaea84fbc8a9d0e1d7e8ae79a923466283e203b5ee47bb44f279cb07'
BANK_HASHES = {'01-04.txt':'861aab708a969e9b0ecb0e0f5db8fc939d67d6c0dd030d278f8e89e27bb44104','05-08.txt':'41eeb5e0dca6efa355532a8e1b5c28225593d8792727d88e57e577f808bdd5fc','09-12.txt':'613c9a886e031eda6b7ef0790da4e72b1504353020cefed0fa938f159980a59b','13-16.txt':'400090259263c4c7cd8e6cbef75992cf93fe1e8b49165f6a0d776b638135f04e','17-20.txt':'7ddbeb05d8e954dbf30e311c837439af5d763b7cdef94d694e1ff0713d23252d'}
def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
def read_source():
    path = ROOT / 'source.json'
    if path.exists():
        result = json.loads(path.read_text(encoding='utf-8'))
    else:
        req = urllib.request.Request(SOURCE_URL, headers={'User-Agent':'Mozilla/5.0 (compatible; Wordstep vocabulary import)'})
        with urllib.request.urlopen(req, timeout=60) as response:
            soup = BeautifulSoup(response.read().decode('utf-8'), 'html.parser')
        groups = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [' '.join(td.stripped_strings) for td in tr.find_all(['td','th'], recursive=False)]
                if len(cells) == 4 and cells[0] and re.search(r'(?:n|v|adj|adv|prep|conj)\.', cells[1]):
                    rows.append(cells)
            if rows:
                groups.append(rows)
        assert [len(g) for g in groups] == [50] * 20, 'Source is incomplete; refusing to publish.'
        entries = []
        for category, rows in zip(CATEGORIES, groups):
            for word, pos, meaning, phrase in rows:
                entries.append(dict(word=word, pos=pos, meaning=meaning, phrase=phrase, category=category))
        result = dict(source=SOURCE_URL, count=len(entries), categories=CATEGORIES, words=entries)
    digest = hashlib.sha256(compact(result['words']).encode()).hexdigest()
    assert digest == EXPECTED_SOURCE, f'Source changed: {digest}; review it before publishing.'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
LEXICAL = {'includes':'include','meets':'meet','owe':'owe','caused':'cause','needs':'need','contains':'contain','offers':'offer','leave':'leave','connects':'connect','shows':'show','closes':'close','requires':'require','serves':'serve','specialize':'specialize','prefer':'prefer'}
LEXICAL_HAS = {752,756,767,777}
def lower_subject(text):
    proper = {'I','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'}
    return text if text in proper else text[:1].lower() + text[1:]
def to_question(sentence, number):
    text = sentence.rstrip('.')
    match = re.search(r'\b(is|are|am|was|were|can|will|should|must|may|could|would|has|have)\b', text)
    if match and number not in LEXICAL_HAS:
        subject = text[:match.start()].strip()
        rest = text[match.end():].strip()
        assert subject and rest, sentence
        question = f'{match[0].capitalize()} {lower_subject(subject)} {rest}?'
        tip = f'把 {match[0]} 移到主詞前，就能把陳述句改成問句。比較兩句的字序，再各聽一次。'
        return question, tip
    match = re.search(r'\b(' + '|'.join(list(LEXICAL) + ['has']) + r')\b', text)
    assert match, (number, sentence)
    verb = match[0]
    subject = text[:match.start()].strip()
    helper = 'Did' if verb == 'caused' else ('Do' if verb in ['owe','leave','specialize','prefer'] else 'Does')
    base = 'have' if verb == 'has' else LEXICAL[verb]
    question = f'{helper} {lower_subject(subject)} {base} {text[match.end():].strip()}?'
    tip = f'用 {helper} 開頭提問，後面的動詞用原形 {base}。比較兩句的動詞形式，再各聽一次。'
    return question, tip
source = read_source()
lines = []
for filename, expected in BANK_HASHES.items():
    path = ROOT / 'examples' / filename
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f'Example transfer mismatch in {filename}: {actual}'
    bank = [line.split('|') for line in path.read_text(encoding='utf-8').splitlines()]
    assert len(bank) == 200 and all(len(line) == 2 for line in bank)
    lines.extend(bank)
assert len(lines) == len(source['words']) == 1000
# Preserve existing authored examples, not a reconstruction from memory.
old_html = subprocess.check_output(['git','show','834021502c40809b3afd7958aff4672f828153b5:docs/index.html'], cwd=REPO, text=True)
old_data = json.loads(BeautifulSoup(old_html, 'html.parser').find('script', id='word-data').string)
old = {word['word']: word for word in old_data['words']}
assert len(old) == 16
words, ids = [], Counter()
for number, (word, (en, zh)) in enumerate(zip(source['words'], lines), 1):
    assert word['word'].lower() in en.lower(), (number, word['word'], en)
    base_id = word['word'].lower()
    ids[base_id] += 1
    uid = base_id if ids[base_id] == 1 else f'{base_id}-{ids[base_id]}'
    question, tip = to_question(en, number)
    item = dict(word, id=uid, number=number, tip=tip, exampleLabels=['基本句','改成問句'], examples=[{'en':en,'zh':zh},{'en':question,'zh':zh.rstrip('。！？?!')+'嗎？'}])
    if word['word'] in old:
        item['examples'] = old[word['word']]['examples']
        item['tip'] = old[word['word']]['tip']
        item['exampleLabels'] = ['例句 1','例句 2']
    words.append(item)
assert len({w['id'] for w in words}) == 1000
assert Counter(w['category'] for w in words) == Counter({c:50 for c in CATEGORIES})
assert len({w['word'] for w in words}) == 999
for word in words:
    assert len(word['examples']) == 2
    assert word['examples'][0]['en'] != word['examples'][1]['en']
    for example in word['examples']:
        assert len(example['en'].split()) >= 3 and re.search(r'[\u4e00-\u9fff]', example['zh'])
assert next(w for w in words if w['word']=='holiday')['examples'][1]['en'].startswith('Is Monday ')
data = {'meta':{'sourceTitle':'戴維美語｜多益必考單字 1000','sourceUrl':SOURCE_URL,'count':1000,'distinctSpellings':999,'exampleCount':2000,'categories':CATEGORIES,'version':'2026-10-18-full','note':'保留原表 20 類各 50 筆；promotion 分別表示升遷與促銷，因此共 1,000 詞條、999 種拼寫。例句與句型提示為本練習站編寫。'},'words':words}
html = (ROOT / 'template.html').read_text(encoding='utf-8').replace('__WORD_DATA__', compact(data).replace('</','<\\/'))
soup = BeautifulSoup(html, 'html.parser')
for element_id in ['search','category','status','word-list','known-toggle','voice','rate','play-all','tip']:
    assert soup.find(id=element_id), f'Missing restored feature: {element_id}'
assert soup.find('details', id='tools') and not soup.find(id='tools').has_attr('open')
(REPO / 'docs' / 'index.html').write_text(html, encoding='utf-8')
print('Verified: 1000 original entries, 20 categories x 50, 2000 bilingual examples, all 16 original example pairs preserved.')
print('HTML SHA256:', hashlib.sha256(html.encode()).hexdigest())
