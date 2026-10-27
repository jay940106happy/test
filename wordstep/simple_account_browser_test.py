"""Regression: one-button Wordstep username+password login without email verification."""
import http.server, json, pathlib, threading, urllib.parse
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
class Server(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args): pass

sdk=r"""
const callbacks=[];
let signedIn=null;
function current(){
  const state=localStorage.getItem('__test_wordstep_account');
  return state?{user:{id:'account-'+state,email:'uXXXXX@users.wordstep.invalid',user_metadata:{wordstep_name:state}}}:null;
}
export function createClient(){
 const auth={
   onAuthStateChange(cb){callbacks.push(cb);return {data:{subscription:{unsubscribe(){}}}};},
   async getSession(){return {data:{session:current()},error:null};},
   async setSession(tokens){
     if(!tokens.access_token||!tokens.refresh_token)return {data:{session:null},error:{message:'tokens missing'}};
     const account=tokens.access_token.replace('token-','');
     localStorage.setItem('__test_wordstep_account',account);
     setTimeout(()=>callbacks.forEach(c=>c('SIGNED_IN',current())),0);
     return {data:{session:current()},error:null};
   },
   async signOut(){
     localStorage.removeItem('__test_wordstep_account');
     setTimeout(()=>callbacks.forEach(c=>c('SIGNED_OUT',null)),0);
     return {error:null};
   }
 };
 function from(name){let owner='';return {
   select(){return this;},eq(_field,value){owner=value;return this;},order(){return this;},
   async range(){return {data:[],error:null};},
   async maybeSingle(){return {data:null,error:null};},
   async upsert(items){return {data:items,error:null};}
 }}
 return {auth,from};
}
"""
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Server)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/wordstep/index.html"
checks=[]
def check(label,pred):
    assert pred,label
    checks.append(label)
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(viewport={'width':390,'height':844})
    context.route("https://cdn.jsdelivr.net/**",lambda r:r.fulfill(status=200,body=sdk,content_type="application/javascript",headers={"Access-Control-Allow-Origin":"*"}))
    calls=[]
    def edge(route):
        data=json.loads(route.request.post_data)
        calls.append(data)
        if data['password']=='wrong-password-000':
            route.fulfill(status=401,content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'error':'wrong_password'}))
        else:
            acc=data['account']
            route.fulfill(status=200,content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'account':acc,'created':len([x for x in calls if x['account']==acc])==1,'access_token':'token-'+acc,'refresh_token':'ref-'+acc}))
    context.route("**/functions/v1/wordstep-account",edge)
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base)
    page.evaluate("""localStorage.setItem('wordstep.progress.v1', JSON.stringify({w0001:true}));""")
    page.reload()
    page.locator('#cloud-open').click()
    check('single login button',page.locator('#cloud-login').count()==1 and page.locator('#cloud-signup').count()==0)
    check('account not email input',page.locator('#cloud-account').is_visible() and page.locator('#cloud-account').get_attribute('type')=='text')
    check('no verification UI',not page.get_by_text('電子郵件中的驗證連結').count())
    check('existing local progress',page.evaluate("JSON.parse(localStorage.getItem('wordstep.progress.v1')).w0001===true"))
    page.locator('#cloud-account').fill('studyuser')
    page.locator('#cloud-password').fill('valid-password-2026')
    page.locator('#cloud-login').click()
    page.wait_for_function("() => document.querySelector('#cloud-open').textContent.includes('雲端已登入')",timeout=16000)
    check('first login calls Edge',calls and calls[0]['account']=='studyuser')
    check('login closes dialog for learning',not page.locator('#cloud-dialog').is_visible())
    check('previous word data retained',page.evaluate("JSON.parse(localStorage.getItem('wordstep.progress.v1')).w0001===true"))
    page.locator('#cloud-open').click()
    check('account is displayed',page.locator('#cloud-user').inner_text().find('studyuser')!=-1)
    page.locator('#cloud-logout').click()
    page.wait_for_function("() => document.querySelector('#cloud-auth')?.hidden===false")
    page.locator('#cloud-account').fill('studyuser')
    page.locator('#cloud-password').fill('wrong-password-000')
    page.locator('#cloud-login').click()
    page.wait_for_function("() => document.querySelector('#cloud-status').textContent.includes('密碼')")
    check('wrong password has friendly feedback','密碼' in page.locator('#cloud-status').inner_text())
    check('progress retained even after wrong password',page.evaluate("JSON.parse(localStorage.getItem('wordstep.progress.v1')).w0001===true"))
    check('no browser JavaScript errors',not errors)
    browser.close()
server.shutdown()
print('PASS',len(checks),'Wordstep simple-login browser checks')
