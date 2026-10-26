"""Wordstep safe studying-flow upgrade. Keep original vocabulary and progress IDs unchanged."""
from pathlib import Path
import json, re
ROOT=Path(__file__).parent
FILE=ROOT/'index.html'
s=FILE.read_text(encoding='utf-8')
def change(before,after):
    global s
    n=s.count(before)
    assert n==1,(n,before[:130])
    s=s.replace(before,after)

change('.tools{border-bottom:1px solid #e6ebe7;margin-top:3px}', '''.study-toolbar{display:flex;justify-content:space-between;gap:10px;align-items:center;margin:10px 0 2px;min-height:42px}.study-toolbar label{display:flex;align-items:center;gap:9px;font-size:14px;color:#374d40;cursor:pointer}.study-toolbar input{width:18px;height:18px;accent-color:#235c48}.study-toolbar .muted{font-size:12px;white-space:nowrap}.mark-feedback{display:flex;gap:10px;align-items:center;justify-content:space-between;margin:12px 0 0;padding:10px 12px;background:#eef5f0;color:#235c48;font-size:13px;border-radius:7px}.mark-feedback button{border:0;background:transparent;padding:8px;color:#235c48;font-weight:700;cursor:pointer;min-height:35px;white-space:nowrap}.tools{border-bottom:1px solid #e6ebe7;margin-top:3px}''')
change('<details class="tools" id="tools">','''<div class="study-toolbar"><label for="show-known"><input type="checkbox" id="show-known">顯示已熟單字</label><span id="study-count" class="muted" aria-live="polite"></span></div>
<details class="tools" id="tools">''')
change('''<div id="empty" class="empty" hidden><p>沒有符合條件的單字。</p><button type="button" id="empty-clear">顯示全部單字</button></div>''','''<div id="empty" class="empty" hidden><p id="empty-message">沒有符合條件的單字。</p><button type="button" id="empty-clear">清除搜尋與分類</button></div>''')
change('''</nav></div>
<p id="audio-message"''','''</nav></div>
<p id="mark-feedback" class="mark-feedback" role="status" aria-live="polite" hidden><span id="mark-feedback-text"></span><button type="button" id="undo-last">撤銷</button></p>
<p id="audio-message"''')
change('''let prefs=load(PREFS),known=load(PROGRESS),selected=prefs.selected,active=null,matches=[],voices=[];''','''let prefs=load(PREFS),known=load(PROGRESS),selected=prefs.selected,active=null,matches=[],voices=[];
// Keep a read-only snapshot of the original local learning record before this UX upgrade.
try{const old=localStorage.getItem(PROGRESS);if(old&&!localStorage.getItem('wordstep.progress.before-ux.v1'))localStorage.setItem('wordstep.progress.before-ux.v1',old);}catch{}
$('#show-known').checked=prefs.showKnown===true;
$('#filter').value=$('#show-known').checked?'all':'new';
let lastMarked=null;''')
change('''scope:$('#scope').value,selected,hidden,rate''','''scope:$('#scope').value,showKnown:$('#show-known').checked,selected,hidden,rate''')
change('''function render(){
 player.stop();''','''function render(){
 player.stop();''')
change('''const w=current(),index=matches.findIndex(w=>w.id===selected),scopeWords=words.filter(inScope),count=scopeWords.filter(w=>known[w.id]===true).length;''','''const w=current(),index=matches.findIndex(w=>w.id===selected),scopeWords=words.filter(inScope),count=scopeWords.filter(w=>known[w.id]===true).length;
 $('#study-count').textContent=`待學 ${scopeWords.length-count} 字`;
 if(!w){
   const candidates=scopeWords.filter(item=>(cat==='all'||(item.categories||[item.category]).includes(cat))&&(!q||normalize(item.word+' '+item.meaning).includes(q)));
   const finished=candidates.length>0&&candidates.every(item=>known[item.id]===true)&&!$('#show-known').checked;
   $('#empty-message').textContent=finished?'這個範圍的單字都已學完！可勾選「顯示已熟單字」複習。':'沒有符合條件的單字，請調整搜尋或主題分類。';
 }''')
change('''function move(delta){if(!matches.length)return;''','''function hideFeedback(){lastMarked=null;$('#mark-feedback').hidden=true;}
function markKnown(){
 const w=current();if(!w)return;
 if(known[w.id]){delete known[w.id];hideFeedback();render();return;}
 const i=matches.findIndex(item=>item.id===w.id);
 const later=matches.slice(i+1).concat(matches.slice(0,i));
 const next=later.find(item=>!known[item.id])||($('#show-known').checked?later[0]:null);
 known[w.id]=true;
 selected=next?.id||null;
 render();
 lastMarked={id:w.id,word:w.word};
 $('#mark-feedback-text').textContent=`${w.word} 已標記熟悉`;
 $('#mark-feedback').hidden=false;
}
function move(delta){hideFeedback();if(!matches.length)return;''')
change('''function clearFilters(){$('#search').value='';$('#category').value='all';$('#filter').value='all';render();}''','''function clearFilters(){hideFeedback();$('#search').value='';$('#category').value='all';$('#filter').value=$('#show-known').checked?'all':'new';render();}''')
change('''$('#scope').addEventListener('change',()=>{updateCategories();render();});$('#search').addEventListener('input',render);$('#category').addEventListener('change',render);$('#filter').addEventListener('change',render);''','''$('#scope').addEventListener('change',()=>{hideFeedback();updateCategories();render();});$('#search').addEventListener('input',()=>{hideFeedback();render();});$('#category').addEventListener('change',()=>{hideFeedback();render();});
$('#show-known').addEventListener('change',()=>{hideFeedback();$('#filter').value=$('#show-known').checked?'all':'new';render();});
$('#filter').addEventListener('change',()=>{hideFeedback();$('#show-known').checked=$('#filter').value!=='new';render();});''')
change('''$('#known').onclick=()=>{if(!current())return;if(known[selected])delete known[selected];else known[selected]=true;render();};''','''$('#known').onclick=markKnown;
$('#undo-last').onclick=()=>{if(!lastMarked)return;const item=lastMarked;delete known[item.id];selected=item.id;hideFeedback();if($('#filter').value==='known'){$('#filter').value='all';$('#show-known').checked=true;}render();};''')
# Verify the unique IDs and complete vocabulary are unchanged.
original=FILE.read_text(encoding='utf-8')
pattern=r'<script id="word-data" type="application/json">(.*?)</script>'
a=re.search(pattern,original,re.S).group(1); b=re.search(pattern,s,re.S).group(1)
assert a==b and len(json.loads(b))==1969, 'Original vocabulary or order was modified'
FILE.write_text(s,encoding='utf-8')
print('SAFE PATCH: 1969 original cards and all IDs unchanged')

# Synchronize the show-known preference across devices and protect older
# progress when changing accounts on a shared browser.
cloud_file=ROOT/'cloud-sync.js'
cloud=cloud_file.read_text(encoding='utf-8')
def cloud_change(before,after):
    global cloud
    assert cloud.count(before)==1,(cloud.count(before),before[:120])
    cloud=cloud.replace(before,after)
cloud_change("  const SYNC_OWNER = 'wordstep.cloud.user.v1';",
 "  const SYNC_OWNER = 'wordstep.cloud.user.v1';\n  const ARCHIVE_PREFIX = 'wordstep.cloud.account-archive.v1.';")
cloud_change("    if (typeof prefs.hidden === 'boolean') result.hidden = prefs.hidden;",
 "    if (typeof prefs.hidden === 'boolean') result.hidden = prefs.hidden;\n    if (typeof prefs.showKnown === 'boolean') result.showKnown = prefs.showKnown;")
cloud_change("""      const oldOwner=localStorage.getItem(SYNC_OWNER);
      if(oldOwner&&oldOwner!==user.id){
        ownerChanged=true;
        // Never merge one signed-in account's local state into another's account.
        write(PROGRESS,{});write(PREFS,{});write(PENDING,{});
        localStorage.removeItem(PREF_DIRTY);dirty={};lastKnown={};
      }""", """      const oldOwner=localStorage.getItem(SYNC_OWNER);
      if(oldOwner&&oldOwner!==user.id){
        ownerChanged=true;
        // Archive previous user's unsynced progress, then restore the other account.
        // Never send the previous account's records to the new account.
        const snapshot={progress:read(PROGRESS),preferences:read(PREFS),
          pending:read(PENDING),prefsDirty:localStorage.getItem(PREF_DIRTY)==='1'};
        write(ARCHIVE_PREFIX+oldOwner,snapshot); // Throws before changing data if storage is full.
        const restored=read(ARCHIVE_PREFIX+user.id);
        write(PROGRESS,sanitizeKnown(restored.progress||{}));
        write(PREFS,cleanPrefs(restored.preferences||{}));
        write(PENDING,restored.pending||{});
        if(restored.prefsDirty)localStorage.setItem(PREF_DIRTY,'1');
        else localStorage.removeItem(PREF_DIRTY);
        localStorage.setItem(SYNC_OWNER,user.id);
        dirty=read(PENDING);lastKnown=sanitizeKnown(read(PROGRESS));
      }""")
cloud_file.write_text(cloud,encoding='utf-8')
print('SAFE CLOUD PATCH: preferences sync; previous accounts archived before switching')