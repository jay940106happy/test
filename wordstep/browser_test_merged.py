"""Browser regression checks for merged Wordstep study modes and retained functionality."""
import functools
import http.server
import json
import pathlib
import re
import threading
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parent.parent
qa=ROOT/'qa'
qa.mkdir(exist_ok=True)
html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
match=re.search(r'<script id="word-data"[^>]*>(.*?)</script>',html,re.S)
assert match
words=json.loads(match.group(1))
assert len(words)==1969
assert len({w['word'].casefold() for w in words})==1969
assert sum(bool(w['base']) for w in words)==999
assert sum(bool(w['tslRank']) for w in words)==1250
assert sum(not w['base'] and w['tslRank']<=500 for w in words)==300
assert all(len(w['examples'])==2 for w in words)
assert next(w for w in words if w['word']=='violin')['category']=='活動與娛樂'
assert next(w for w in words if w['word']=='cloudy')['category']=='天氣與自然'
assert next(w for w in words if w['word']=='promotion')['aliases']==['w0206']
assert next(w for w in words if w['word']=='promotion')['meaning'].startswith('升遷；')
mock="""window.__spoken=[];window.__cancelled=0;Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>[{name:'English',lang:'en-US',voiceURI:'en-US'}],addEventListener:()=>{},cancel:()=>{window.__cancelled++;},speak:u=>{window.__spoken.push({text:u.text,rate:u.rate,lang:u.lang});if(u.onstart)u.onstart();}}});window.SpeechSynthesisUtterance=function(text){this.text=text;};"""
handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'docs'))
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/index.html'
checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':390,'height':844})
    page.add_init_script(mock)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url)
    check('priority contains 1299 cards',page.locator('#word-jump option').count()==1299)
    check('shows first original word',page.locator('#word').inner_text()=='office')
    check('both examples present',page.locator('.example').count()==2)
    page.screenshot(path=str(qa/'integrated-mobile.png'),full_page=True)
    for mode,total in [('base',999),('tsl-new',300),('all',1969),('tsl-all',1250),('priority',1299)]:
        page.select_option('#scope',mode)
        check(mode+' total',page.locator('#word-jump option').count()==total)
    page.select_option('#scope','all')
    page.locator('#search').fill('violin')
    check('TSL violin visible',page.locator('#word').inner_text()=='violin')
    check('violin correct category',page.locator('#category-label').inner_text().startswith('活動與娛樂'))
    page.locator('#search').fill('cloudy')
    check('weather category',page.locator('#category-label').inner_text().startswith('天氣與自然'))
    page.locator('#search').fill('便宜')
    check('Chinese search works',0<page.locator('#word-jump option').count()<1969)
    page.locator('#search').fill('résumé')
    check('accents searchable',page.locator('#word').inner_text()=='résumé')
    page.locator('#search').fill('resume')
    check('ASCII accent searchable',page.locator('#word').inner_text()=='résumé')
    page.locator('#search').fill('')
    page.locator('#tools').evaluate('(e)=>e.open=true')
    page.select_option('#category','科技與設備')
    check('topic filtering nonempty',0<page.locator('#word-jump option').count()<1969)
    page.locator('#search').fill('headphone')
    check('headphone classified',page.locator('#word').inner_text()=='headphone')
    page.locator('#search').fill('')
    page.locator('#clear-filters').click()
    check('clear filters retains scope',page.locator('#scope').input_value()=='all')
    page.select_option('#scope','tsl-new')
    check('first TSL new word',page.locator('#word').inner_text()=='mister')
    page.locator('[data-play="word"]').click()
    check('word speech',page.evaluate('window.__spoken.at(-1).text')=='mister')
    page.locator('[data-play="example0"]').click()
    check('sentence 1 speech',page.evaluate('window.__spoken.at(-1).text')==page.locator('.example .en').nth(0).inner_text())
    page.locator('[data-play="example1"]').click()
    check('sentence 2 speech',page.evaluate('window.__spoken.at(-1).text')==page.locator('.example .en').nth(1).inner_text())
    page.evaluate('window.__spoken=[]')
    page.locator('#play-all').click()
    check('group spoken three times',len(page.evaluate('window.__spoken'))==3)
    page.locator('#known').click()
    check('mark learned TSL',page.locator('#known').get_attribute('aria-pressed')=='true')
    page.reload()
    check('persist scope',page.locator('#scope').input_value()=='tsl-new')
    check('persist TSL known',page.locator('#known').get_attribute('aria-pressed')=='true')
    page.locator('#hide-chinese').click()
    check('hide Chinese',page.locator('#meaning').evaluate('(e)=>getComputedStyle(e).visibility')=='hidden')
    page.locator('#hide-chinese').click()
    check('show Chinese',page.locator('#meaning').evaluate('(e)=>getComputedStyle(e).visibility')=='visible')
    page.locator('#tools').evaluate('(e)=>e.open=true')
    page.select_option('#filter','known')
    check('known only',page.locator('#word-jump option').count()==1)
    page.select_option('#filter','new')
    check('unknown only',page.locator('#word-jump option').count()==299)
    page.select_option('#filter','all')
    page.locator('#search').fill('xxxxxxxxxxx')
    check('empty state',page.locator('#empty').is_visible())
    page.locator('#empty-clear').click()
    check('recover empty state',page.locator('#word-jump option').count()==300)
    for width in (320,390,1280):
        page.set_viewport_size({'width':width,'height':850})
        check('no overflow '+str(width),page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        if width==1280:page.screenshot(path=str(qa/'integrated-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#tools').evaluate('(e)=>e.open=true')
    page.screenshot(path=str(qa/'integrated-tools-mobile.png'),full_page=True)
    check('no JS errors',not errors)
    old=browser.new_context()
    tab=old.new_page()
    tab.goto(url)
    tab.evaluate("""localStorage.setItem('wordstep.preferences.v1',JSON.stringify({selected:'w0206',scope:'priority'}));localStorage.setItem('wordstep.progress.v1',JSON.stringify({w0206:true}));""")
    tab.reload()
    check('legacy duplicate selection migrates',tab.locator('#word').inner_text()=='promotion')
    check('legacy duplicate progress migrates',tab.locator('#known').get_attribute('aria-pressed')=='true')
    old.close()
    browser.close()
server.shutdown()
(qa/'integration-report.json').write_text(json.dumps({'checks':len(checks),'passed':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS',len(checks),'checks')
