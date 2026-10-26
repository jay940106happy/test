"""Wordstep integration regression: scoped data, login, persistence, cross-browser sync.

The browser tests use a deterministic Supabase-client mock against a shared test HTTP
server; actual Supabase security/configuration is independently checked via SQL and REST.
"""
import functools
import http.server
import json
import threading
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent
rows = {"wordstep_progress": {}, "wordstep_preferences": {}}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE.parent), **kwargs)
    def log_message(self, *args): pass
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path == '/__fake_backend':
            query = urllib.parse.parse_qs(parts.query)
            owner=query.get('owner',[''])[0]
            table=query.get('table',[''])[0]
            assert table in rows
            data=list(rows[table].get(owner, {}).values()) if table=='wordstep_progress' else rows[table].get(owner)
            body=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        else: super().do_GET()
    def do_POST(self):
        if self.path != '/__fake_backend': return self.send_error(404)
        body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
        owner,table=body['owner'],body['table']
        assert table in rows and owner
        if table=='wordstep_progress':
            for entry in body['records']:
                assert entry['user_id']==owner
                rows[table].setdefault(owner,{})[entry['word_id']]=entry
        else:
            assert body['records']['user_id']==owner
            rows[table][owner]=body['records']
        out=b'{}';self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out)

MOCK_SDK = r'''const callbacks=[];
let email=localStorage.getItem('__ws_test_email')||'';
const user=e=>({id:'test-'+e,email:e});
const session=()=>email?{user:user(email)}:null;
async function fetchDb(type,table,owner,records){
 const opt=type==='write'?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({table,owner,records})}:{};
 const query=type==='read'?('?table='+encodeURIComponent(table)+'&owner='+encodeURIComponent(owner)):'';
 const res=await fetch('/__fake_backend'+query,opt);
 if(!res.ok)return {data:null,error:new Error('mock fetch '+res.status)};
 return {data:await res.json(),error:null};
}
export function createClient(_url,_key,_options){
 const auth={
  onAuthStateChange(cb){callbacks.push(cb);return {data:{subscription:{unsubscribe(){}}}}},
  async getSession(){return {data:{session:session()},error:null}},
  async signUp({email:e,password}){if(password.length<8)return {data:{},error:new Error('short password')};return {data:{user:user(e),session:null},error:null}},
  async signInWithPassword({email:e,password}){if(password.length<8)return {data:{},error:new Error('short password')};email=e;localStorage.setItem('__ws_test_email',e);setTimeout(()=>callbacks.forEach(cb=>cb('SIGNED_IN',session())),0);return {data:{session:session()},error:null}},
  async signOut(){email='';localStorage.removeItem('__ws_test_email');setTimeout(()=>callbacks.forEach(cb=>cb('SIGNED_OUT',null)),0);return {error:null}}
 };
 function from(table){let owner='';return {
  select(){return this},eq(_column, value){owner=value;return this},order(){return this},
  async range(a,b){const res=await fetchDb('read',table,owner);return {...res,data:res.data.slice(a,b+1)}},
  async maybeSingle(){return fetchDb('read',table,owner)},
  async upsert(data){owner=Array.isArray(data)?data[0].user_id:data.user_id;return fetchDb('write',table,owner,data)}
 }}
 return {auth,from};
}'''

checks=[]
def ok(description, condition):
    assert condition, description
    checks.append(description)

def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/{SITE.name}/index.html'
    with sync_playwright() as p:
        browser=p.chromium.launch()
        ctx1=browser.new_context(viewport={'width':390,'height':844},accept_downloads=True)
        page=ctx1.new_page()
        failures=[]
        page.on('pageerror',lambda e:failures.append(str(e)))
        def mock_sdk(route):
            route.fulfill(status=200,body=MOCK_SDK,content_type='application/javascript',headers={'Access-Control-Allow-Origin':'*'})
        ctx1.route('https://cdn.jsdelivr.net/**',mock_sdk)
        page.goto(base,wait_until='load')
        ok('1969 library loads',page.locator('#word').inner_text()=='office')
        ok('1299 priority scope',page.locator('#word-jump option').count()==1299)
        page.locator('#known').click()
        ok('offline progress stored and automatically advances',page.evaluate("JSON.parse(localStorage.getItem('wordstep.progress.v1')).w0001===true") and page.locator('#word').inner_text()=='workplace')
        page.locator('#cloud-open').click()
        ok('cloud account controls visible',page.locator('#cloud-auth').is_visible())
        ok('cloud login and signup present',page.locator('#cloud-signup').is_visible() and page.locator('#cloud-login').is_visible())
        page.locator('#cloud-email').fill('student@example.com')
        page.locator('#cloud-password').fill('pass-123456')
        page.locator('#cloud-login').click()
        page.wait_for_function("() => document.querySelector('#cloud-status').textContent.includes('雲端同步成功')",timeout=25000)
        ok('cloud login displayed',page.locator('#cloud-logged-in').is_visible())
        ok('prelogin progress transferred to account',rows['wordstep_progress'].get('test-student@example.com',{}).get('w0001',{}).get('known') is True)
        # Another independent browser and localStorage profile accesses the same test backend.
        ctx2=browser.new_context(viewport={'width':390,'height':844})
        ctx2.route('https://cdn.jsdelivr.net/**',mock_sdk)
        other=ctx2.new_page();other.on('pageerror',lambda e:failures.append(str(e)))
        other.goto(base,wait_until='load')
        other.locator('#cloud-open').click()
        other.locator('#cloud-email').fill('student@example.com')
        other.locator('#cloud-password').fill('pass-123456')
        other.locator('#cloud-login').click()
        other.wait_for_function("() => JSON.parse(localStorage.getItem('wordstep.progress.v1')||'{}').w0001===true",timeout=25000)
        ok('same account downloads progress on second device',other.evaluate("JSON.parse(localStorage.getItem('wordstep.progress.v1')).w0001===true") and other.locator('#word').inner_text()=='workplace')
        # Simulate learning a TSL word on device 2 and remote retrieval on device 1.
        if other.locator('#cloud-dialog').evaluate('(e)=>e.open'):
            other.locator('#cloud-close').click()
        other.select_option('#scope','tsl-new')
        other.locator('#known').click()
        other.wait_for_function("() => document.querySelector('#cloud-open').textContent.includes('雲端已登入')")
        other.wait_for_timeout(900)
        ok('new TSL mark persisted remotely',rows['wordstep_progress'].get('test-student@example.com',{}).get('tsl0001',{}).get('known') is True)
        page.locator('#cloud-sync-now').click()
        page.wait_for_function("() => JSON.parse(localStorage.getItem('wordstep.progress.v1')||'{}').tsl0001===true",timeout=25000)
        ok('manual refresh receives second device progress',True)  # wait_for_function above asserts the value.
        # Verify second account never inherits the first account's local state.
        page.locator('#cloud-open').click()
        page.locator('#cloud-logout').click()
        page.wait_for_function("() => document.querySelector('#cloud-login-form')?.offsetParent !== null")
        page.locator('#cloud-email').fill('other@example.com')
        page.locator('#cloud-password').fill('other-123456')
        with page.expect_navigation(wait_until='domcontentloaded',timeout=25000):
            page.locator('#cloud-login').click()
        page.wait_for_function("() => document.querySelector('#cloud-user')?.textContent.includes('other@example.com')",timeout=25000)
        page.wait_for_function("() => localStorage.getItem('wordstep.cloud.user.v1')==='test-other@example.com' && !JSON.parse(localStorage.getItem('wordstep.progress.v1')||'{}').w0001",timeout=25000)
        ok('different account isolated',True)
        page.wait_for_function("() => JSON.parse(localStorage.getItem('wordstep.cloud.account-archive.v1.test-student@example.com')||'{}').progress?.w0001===true",timeout=25000)
        ok('previous account local archive preserved',True)
        # The app reloads automatically when a different account is restored.
        # An explicit navigation settles auth callbacks before interacting with the dialog.
        page.reload(wait_until='domcontentloaded',timeout=15000)
        page.locator('#cloud-open').wait_for(state='visible',timeout=15000)
        page.locator('#cloud-open').click()
        page.locator('#cloud-logout').click()
        page.wait_for_function("() => document.querySelector('#cloud-login-form')?.offsetParent !== null",timeout=25000)
        page.locator('#cloud-email').fill('student@example.com')
        page.locator('#cloud-password').fill('pass-123456')
        with page.expect_navigation(wait_until='domcontentloaded',timeout=25000):
            page.locator('#cloud-login').click()
        page.wait_for_function("() => JSON.parse(localStorage.getItem('wordstep.progress.v1')||'{}').w0001===true",timeout=25000)
        page.wait_for_function("() => localStorage.getItem('wordstep.cloud.user.v1')==='test-student@example.com'",timeout=25000)
        ok('first account progress restored after switching back',True)
        # Original standalone learning functions are preserved.
        page.reload(wait_until='domcontentloaded',timeout=15000)
        page.locator('#cloud-open').wait_for(state='visible',timeout=15000)
        page.select_option('#scope','all')
        page.locator('#search').fill('violin')
        ok('topic grouping still correct',page.locator('#category-label').inner_text().startswith('活動與娛樂'))
        page.locator('#search').fill('')
        for width in [320,390,1280]:
            page.set_viewport_size({'width':width,'height':860})
            ok(f'no horizontal overflow at {width}px',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        ok('no browser errors',not failures)
        browser.close()
    server.shutdown()
    print('PASS',len(checks),'cloud preservation and sync checks')
    (SITE/'browser-test-results.json').write_text(json.dumps({'checks':checks,'passed':len(checks)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()