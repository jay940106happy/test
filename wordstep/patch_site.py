"""Safely add the cloud/backup controls to the existing Wordstep page.

Keeps all 1969 words and all old learning UI, changing only the storage notifier,
local-only explanatory copy and loading the separate cloud-sync.js module.
"""
from pathlib import Path
import re, json
root=Path(__file__).resolve().parent
path=root/'index.html'
html=path.read_text(encoding='utf-8')
if '<script src="./cloud-sync.js" type="module"></script>' in html:
    print('Wordstep cloud module already installed')
else:
    before="function store(key,value){try{localStorage.setItem(key,JSON.stringify(value));}catch{$('#save-message').hidden=false;}}"
    after="function store(key,value){try{const before=localStorage.getItem(key),after=JSON.stringify(value);localStorage.setItem(key,after);if(before!==after)window.dispatchEvent(new CustomEvent('wordstep:change',{detail:{key,value}}));}catch{$('#save-message').hidden=false;}}"
    assert html.count(before)==1,'Cannot safely patch existing storage notifier'
    html=html.replace(before,after)
    assert html.count('；進度儲存在目前瀏覽器。')==1
    html=html.replace('；進度儲存在目前瀏覽器。','；登入後可同步雲端，未登入時僅儲存於本機。')
    assert html.count('</body>')==1
    html=html.replace('</body>','<script src="./cloud-sync.js" type="module"></script>\n</body>')
    html=html.replace('content="完整1000筆多益字詞、每筆兩句中英例句，點擊朗讀。"','content="多益 1969 個字卡、3938 句中英對照例句與點讀，支援備份還原及帳號雲端進度同步。"')
    html=html.replace('的20類、1,000筆詞條。promotion 的「升遷」與「促銷」分列兩筆，共999種拼寫。','的20類、1,000筆詞條，並與 TSL 1.2 合併去重；promotion 的兩個意思合為一張字卡，共 1,969 張不重複字卡。')
    path.write_text(html,encoding='utf-8')
m=re.search(r'<script id="word-data"[^>]*>(.*?)</script>',html,re.S)
assert m,'Missing complete Wordstep vocabulary'
words=json.loads(m.group(1))
assert len(words)==1969 and sum(len(w['examples']) for w in words)==3938
assert 'wordstep:change' in html and './cloud-sync.js' in html
print('Wordstep preserved:',len(words),'cards',3938,'examples')
