/* Wordstep cloud sync: optional Supabase, always-available JSON backup.
   The web page never uses an elevated/service-role credential.
   Supabase row-level security enforces per-user access. */
(() => {
  'use strict';
  const PROGRESS = 'wordstep.progress.v1';
  const PREFS = 'wordstep.preferences.v1';
  const PENDING = 'wordstep.cloud.pending.v1';
  const PREF_DIRTY = 'wordstep.cloud.prefs-dirty.v1';
  const SYNC_OWNER = 'wordstep.cloud.user.v1';
  const $ = sel => document.querySelector(sel);
  const read = (key, fallback = {}) => {
    try { const value = JSON.parse(localStorage.getItem(key) || 'null');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : fallback;
    } catch { return fallback; }
  };
  const write = (key, value) => localStorage.setItem(key, JSON.stringify(value));
  const wordData = JSON.parse($('#word-data').textContent);
  const validWords = new Set(wordData.map(x => x.id));
  const validScopes = new Set(['priority', 'base', 'tsl-new', 'all', 'tsl-all']);
  const sanitizeKnown = obj => Object.fromEntries(Object.entries(obj || {})
    .filter(([k,v]) => validWords.has(k) && v === true));
  const cleanPrefs = prefs => {
    const result = {};
    if (validWords.has(prefs.selected)) result.selected = prefs.selected;
    if (validScopes.has(prefs.scope)) result.scope = prefs.scope;
    if ([0.7,0.9,1,1.15].includes(Number(prefs.rate))) result.rate = Number(prefs.rate);
    if (typeof prefs.hidden === 'boolean') result.hidden = prefs.hidden;
    if (typeof prefs.voice === 'string' && prefs.voice.length <= 200) result.voice = prefs.voice;
    return result;
  };
  let lastKnown = sanitizeKnown(read(PROGRESS));
  let client = null, user = null, ready = false, working = false, prefsTimer = null, progressTimer = null;
  let dirty = read(PENDING);
  let switching = false;
  const style = document.createElement('style');
  style.textContent = `
    .cloud-top{display:flex;align-items:center;gap:11px;flex-wrap:wrap;justify-content:flex-end}
    #cloud-open{background:#fff;border:1px solid #dce3de;border-radius:7px;padding:7px 10px;font-size:12px;color:#235c48;cursor:pointer;min-height:38px}
    #cloud-open:focus-visible,#cloud-dialog button:focus-visible,#cloud-dialog input:focus-visible{outline:3px solid #76a18c;outline-offset:2px}
    #cloud-dialog{border:1px solid #dce3de;box-shadow:0 20px 70px #17251c2e;border-radius:12px;padding:24px;width:min(430px,calc(100% - 28px));max-height:85dvh;overflow-y:auto;color:#222b27;background:#fff}
    #cloud-dialog::backdrop{background:#12251a75}
    #cloud-dialog h2{font-size:21px;font-weight:650;margin:0 0 9px}
    #cloud-dialog p{font-size:14px;line-height:1.7;color:#56665b}
    #cloud-dialog .cloud-head{display:flex;justify-content:space-between;align-items:center;gap:8px}
    #cloud-dialog .cloud-close{background:transparent;border:0;min-height:40px;padding:4px 8px;font-size:23px;cursor:pointer}
    #cloud-dialog label{display:block;font-size:13px;color:#506056;margin:12px 0 5px}
    #cloud-dialog input[type=email],#cloud-dialog input[type=password]{width:100%;min-height:42px;font-size:16px;border:1px solid #dce3de;border-radius:7px;padding:9px}
    #cloud-dialog .cloud-primary{background:#235c48;border:1px solid #235c48;border-radius:7px;color:#fff;padding:9px 14px;min-height:43px;cursor:pointer}
    #cloud-dialog .cloud-light{border:1px solid #dce3de;border-radius:7px;background:#fff;color:#235c48;padding:9px 14px;min-height:43px;cursor:pointer}
    #cloud-dialog button:disabled{opacity:.45;cursor:default}
    #cloud-dialog .cloud-row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
    #cloud-status{color:#235c48;font-size:13px;line-height:1.7;min-height:24px;overflow-wrap:anywhere}
    #cloud-dialog hr{border:0;border-top:1px solid #e5ece6;margin:18px 0}
    #cloud-dialog .cloud-small{font-size:12px;color:#66756b}
    #cloud-dialog .cloud-danger{color:#a43e36}
  `;
  document.head.append(style);
  const header = $('.top');
  const right = document.createElement('span');
  right.className = 'cloud-top';
  const count = $('#total');
  count.replaceWith(right);
  right.append(count);
  const trigger = document.createElement('button');
  trigger.id = 'cloud-open'; trigger.type = 'button'; trigger.textContent = '學習紀錄 / 登入';
  right.append(trigger);
  const modal = document.createElement('dialog');
  modal.id = 'cloud-dialog';
  modal.setAttribute('aria-labelledby', 'cloud-title');
  modal.innerHTML = `<div class="cloud-head"><h2 id="cloud-title">學習紀錄</h2><button class="cloud-close" id="cloud-close" type="button" aria-label="關閉">×</button></div>
    <p id="cloud-status" role="status" aria-live="polite">檢查雲端同步設定中…</p>
    <div id="cloud-auth" hidden><form id="cloud-login-form"><label for="cloud-email">電子郵件</label>
      <input id="cloud-email" type="email" required autocomplete="email" placeholder="輸入你的電子郵件" maxlength="254">
      <label for="cloud-password">密碼</label>
      <input id="cloud-password" type="password" required autocomplete="current-password" placeholder="至少 8 個字元" minlength="8" maxlength="72">
      <div class="cloud-row"><button class="cloud-primary" id="cloud-login" type="submit">登入</button>
      <button class="cloud-light" id="cloud-signup" type="button">建立帳號</button></div>
    </form><p class="cloud-small">第一次使用請建立帳號，依收到的電子郵件完成驗證後再登入。帳號與進度會在電腦、手機共用。</p></div>
    <div id="cloud-logged-in" hidden><p id="cloud-user"></p><div class="cloud-row">
    <button class="cloud-light" id="cloud-sync-now" type="button">立即同步</button>
    <button class="cloud-light" id="cloud-logout" type="button">登出</button></div></div>
    <hr><p><strong>備份與還原</strong></p>
    <p class="cloud-small">即使雲端暫時無法使用，也能下載備份。匯入時會保留目前已熟悉的單字，再加入備份中的紀錄。</p>
    <div class="cloud-row"><button class="cloud-light" id="cloud-export" type="button">下載備份 JSON</button>
    <button class="cloud-light" id="cloud-import" type="button">匯入備份</button></div>
    <input id="cloud-import-file" type="file" accept=".json,application/json" hidden>
    <p class="cloud-small">雲端同步只會上傳學習狀態與偏好，不會上傳單字表或電子郵件內容。</p>`;
  document.body.append(modal);
  const status = (message, error=false) => {
    $('#cloud-status').textContent = message;
    $('#cloud-status').classList.toggle('cloud-danger', error);
    trigger.textContent = user ? '雲端已登入' : ready ? '登入同步' : '學習紀錄 / 備份';
  };
  trigger.onclick = () => modal.showModal();
  $('#cloud-close').onclick = () => modal.close();
  modal.addEventListener('click', e => {if (e.target === modal) modal.close();});
  function backup() {
    const payload = {app:'Wordstep',version:1,exportedAt:new Date().toISOString(),
      known:sanitizeKnown(read(PROGRESS)),preferences:cleanPrefs(read(PREFS))};
    const blob = new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `wordstep-backup-${new Date().toISOString().slice(0,10)}.json`;
    link.click();
    setTimeout(()=>URL.revokeObjectURL(link.href),1000);
    status(user ? '備份已下載；雲端同步仍可使用。' : '備份已下載。');
  }
  $('#cloud-export').onclick=backup;
  $('#cloud-import').onclick=()=>$('#cloud-import-file').click();
  $('#cloud-import-file').addEventListener('change', async e => {
    const file = e.target.files?.[0];
    if(!file)return;
    try {
      if(file.size>3_000_000)throw new Error('備份檔案過大');
      const payload=JSON.parse(await file.text());
      if(payload.app!=='Wordstep'||payload.version!==1||!payload.known||Array.isArray(payload.known))throw new Error('不是 Wordstep 備份');
      const incoming=sanitizeKnown(payload.known),previous=sanitizeKnown(read(PROGRESS));
      const merged={...previous,...incoming};
      write(PROGRESS,merged);
      const prefs={...cleanPrefs(read(PREFS)),...cleanPrefs(payload.preferences||{})};
      write(PREFS,prefs);
      const changes={...read(PENDING)};
      for(const id of Object.keys(incoming)) if(!previous[id]) changes[id]=true;
      write(PENDING,changes);dirty=changes;
      localStorage.setItem(PREF_DIRTY,'1');
      status(`已匯入 ${Object.keys(incoming).length} 個熟悉標記，重新整理頁面中…`);
      location.reload();
    } catch(error) {status('匯入失敗：'+(error.message||'無法讀取檔案'),true);}
    finally{e.target.value='';}
  });
  window.addEventListener('wordstep:change', event => {
    const {key,value}=event.detail||{};
    if(switching)return;
    if(key===PROGRESS){
      const next=sanitizeKnown(value);
      const changed={...dirty};
      const keys=new Set([...Object.keys(next),...Object.keys(lastKnown)]);
      for(const id of keys){if(Boolean(next[id])!==Boolean(lastKnown[id]))changed[id]=Boolean(next[id]);}
      dirty=changed;write(PENDING,dirty);lastKnown=next;
      if(user){clearTimeout(progressTimer);progressTimer=setTimeout(flushChanges,300);}
    }else if(key===PREFS){
      localStorage.setItem(PREF_DIRTY,'1');
      if(user){clearTimeout(prefsTimer);prefsTimer=setTimeout(flushChanges,1100);}
    }
  });
  async function getRows(owner){
    const all=[];
    for(let offset=0;offset<2500;offset+=1000){
      const {data,error}=await client.from('wordstep_progress')
        .select('word_id,known,updated_at').eq('user_id',owner).order('word_id').range(offset,offset+999);
      if(error)throw error;
      all.push(...(data||[]));
      if((data||[]).length<1000)break;
    }
    return all;
  }
  async function syncRemote(){
    if(!user||working)return;
    working=true;
    status('正在下載與合併雲端進度…');
    try {
      let ownerChanged=false;
      const oldOwner=localStorage.getItem(SYNC_OWNER);
      if(oldOwner&&oldOwner!==user.id){
        ownerChanged=true;
        // Never merge one signed-in account's local state into another's account.
        write(PROGRESS,{});write(PREFS,{});write(PENDING,{});
        localStorage.removeItem(PREF_DIRTY);dirty={};lastKnown={};
      }
      const [rows,prefsReply]=await Promise.all([
        getRows(user.id),client.from('wordstep_preferences').select('payload').eq('user_id',user.id).maybeSingle()
      ]);
      if(prefsReply.error)throw prefsReply.error;
      const local=sanitizeKnown(read(PROGRESS));
      const pending=read(PENDING);
      const remote=Object.fromEntries(rows.filter(r=>validWords.has(r.word_id)).map(r=>[r.word_id,r.known]));
      const upload={};
      // Explicit pending changes win; existing cloud rows win over stale local state.
      const merged={};
      for(const [id,known] of Object.entries(remote))if(known===true)merged[id]=true;
      for(const [id,known] of Object.entries(local))if(known&&!(id in remote)){
        merged[id]=true;upload[id]=true;
      }
      for(const [id,known] of Object.entries(pending))if(validWords.has(id)&&typeof known==='boolean'){
        if(known)merged[id]=true;else delete merged[id];
        upload[id]=known;
      }
      if(Object.keys(upload).length){
        const entries=Object.entries(upload).map(([word_id,known])=>({user_id:user.id,word_id,known,updated_at:new Date().toISOString()}));
        for(let i=0;i<entries.length;i+=300){
          const {error}=await client.from('wordstep_progress').upsert(entries.slice(i,i+300),{onConflict:'user_id,word_id'});
          if(error)throw error;
        }
      }
      let pref=cleanPrefs(read(PREFS));
      const dirtyPref=localStorage.getItem(PREF_DIRTY)==='1';
      if(prefsReply.data&&!dirtyPref)pref=cleanPrefs(prefsReply.data.payload||{});
      else{
        const {error}=await client.from('wordstep_preferences').upsert({user_id:user.id,payload:pref,updated_at:new Date().toISOString()},{onConflict:'user_id'});
        if(error)throw error;
      }
      const changed=ownerChanged||JSON.stringify(local)!==JSON.stringify(merged)||JSON.stringify(cleanPrefs(read(PREFS)))!==JSON.stringify(pref);
      switching=true;
      write(PROGRESS,merged);write(PREFS,pref);write(PENDING,{});
      localStorage.setItem(SYNC_OWNER,user.id);
      localStorage.removeItem(PREF_DIRTY);
      dirty={};lastKnown=merged;
      switching=false;
      status(`雲端同步成功：${Object.keys(merged).length} 個已熟悉單字。`);
      if(changed){modal.close();location.reload();}
    }catch(e){status('雲端同步失敗，變更仍保留在本機：'+(e.message||'網路錯誤'),true);}
    finally{switching=false;working=false;}
  }
  async function flushChanges(){
    if(!user||working)return;
    const changes=read(PENDING);const prefDirty=localStorage.getItem(PREF_DIRTY)==='1';
    if(!Object.keys(changes).length&&!prefDirty)return;
    working=true;
    status('正在儲存雲端學習紀錄…');
    try {
      const entries=Object.entries(changes).filter(([id,v])=>validWords.has(id)&&typeof v==='boolean')
        .map(([word_id,known])=>({user_id:user.id,word_id,known,updated_at:new Date().toISOString()}));
      for(let i=0;i<entries.length;i+=300){
        const {error}=await client.from('wordstep_progress').upsert(entries.slice(i,i+300),{onConflict:'user_id,word_id'});
        if(error)throw error;
      }
      const prefSnapshot=JSON.stringify(cleanPrefs(read(PREFS)));
      if(prefDirty){
        const {error}=await client.from('wordstep_preferences').upsert({user_id:user.id,payload:JSON.parse(prefSnapshot),updated_at:new Date().toISOString()},{onConflict:'user_id'});
        if(error)throw error;
      }
      // Remove only the changes just uploaded, retaining edits made during the request.
      const fresh=read(PENDING);
      for(const [id,v] of Object.entries(changes))if(fresh[id]===v)delete fresh[id];
      write(PENDING,fresh);dirty=fresh;
      if(prefDirty&&JSON.stringify(cleanPrefs(read(PREFS)))===prefSnapshot)localStorage.removeItem(PREF_DIRTY);
      status('已同步到雲端。');
    }catch(e){status('儲存失敗，資料已暫存於本機：'+(e.message||'網路錯誤'),true);}
    finally{working=false;if(user&&(Object.keys(read(PENDING)).length||localStorage.getItem(PREF_DIRTY)==='1'))setTimeout(flushChanges,5000);}
  }
  window.addEventListener('online',()=>{if(user)syncRemote();});
  window.addEventListener('focus',()=>{if(user&&!working)syncRemote();});
  $('#cloud-sync-now').onclick=syncRemote;
  $('#cloud-logout').onclick=async()=>{
    if(!client)return;
    const {error}=await client.auth.signOut();
    if(error)status('登出失敗：'+error.message,true);
  };
  async function passwordAction(action){
    if(!client)return;
    const email=$('#cloud-email').value.trim();
    const password=$('#cloud-password').value;
    if(!$('#cloud-login-form').reportValidity()||!email||!password)return;
    const loginButton=$('#cloud-login'),signupButton=$('#cloud-signup');
    loginButton.disabled=true;signupButton.disabled=true;
    try {
      if(action==='register'){
        const {data,error}=await client.auth.signUp({email,password,options:{emailRedirectTo:location.origin+location.pathname}});
        if(error)throw error;
        if(data.session)status('帳號建立成功，正在同步學習紀錄。');
        else status('已提交註冊。請點電子郵件中的驗證連結，再回到此網站登入。如果沒有收到信件，請檢查垃圾郵件。');
      }else{
        const {error}=await client.auth.signInWithPassword({email,password});
        if(error)throw error;
        status('已登入，正在載入雲端進度…');
      }
    }catch(e){
      const message=e.message||'請稍後再試';
      status((action==='register'?'註冊':'登入')+'失敗：'+message,true);
    }finally{loginButton.disabled=false;signupButton.disabled=false;$('#cloud-password').value='';}
  }
  $('#cloud-login-form').onsubmit=e=>{e.preventDefault();passwordAction('login');};
  $('#cloud-signup').onclick=()=>passwordAction('register');
  async function init(){
    try {
      const response=await fetch(new URL('./cloud-config.json',import.meta.url),{cache:'no-store'});
      if(!response.ok)throw new Error('設定檔不存在');
      const config=await response.json();
      if(!config.supabaseUrl||!config.supabaseAnonKey){
        status('目前可在這台裝置保存紀錄與下載備份；雲端資料庫尚未完成設定。');
        return;
      }
      if(!/^https:\/\/[a-z0-9-]+\.supabase\.co\/?$/.test(config.supabaseUrl))throw Error('資料庫網址無效');
      const {createClient}=await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.49.10/+esm');
      client=createClient(config.supabaseUrl,config.supabaseAnonKey,{
        auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}
      });
      ready=true;
      $('#cloud-auth').hidden=false;
      status('尚未登入。請使用電子郵件與密碼登入或建立帳號。');
      client.auth.onAuthStateChange((_event,session)=>{
        // Do not await Supabase methods inside onAuthStateChange: schedule them outside.
        setTimeout(()=>handleSession(session),0);
      });
      const {data:{session},error}=await client.auth.getSession();
      if(error)throw error;
      await handleSession(session);
    }catch(e){status('目前僅能使用本機儲存及備份：'+(e.message||'無法連線'),true);}
  }
  let lastSessionId=null;
  async function handleSession(session){
    const current=session?.user||null;
    if(current){
      user=current;
      $('#cloud-auth').hidden=true;
      $('#cloud-logged-in').hidden=false;
      $('#cloud-user').textContent='已登入：'+(user.email||'已驗證帳號');
      if(lastSessionId!==user.id){lastSessionId=user.id;await syncRemote();}
      else {if(!working)status('已登入。');await flushChanges();}
    }else{
      user=null;lastSessionId=null;
      $('#cloud-auth').hidden=!ready;
      $('#cloud-logged-in').hidden=true;
      status(ready?'已登出，仍可本機學習及備份。':'雲端尚未設定，進度暫存本機。');
    }
  }
  init();
})();
