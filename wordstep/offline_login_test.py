"""UI regression: a paused/unreachable cloud must not show raw 'Failed to fetch' or erase study progress."""
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

SDK = r"""
export function createClient() {
 return {
  auth:{
   onAuthStateChange(){ return {data:{subscription:{unsubscribe(){}}}} },
   async getSession(){return {data:{session:null},error:null}},
   async signInWithPassword(){return {data:{session:null},error:{code:'invalid_credentials',message:'Invalid login credentials'}}},
   async setSession(){return {error:null}},
  },
  from(){throw Error('unexpected cloud call')}
 };
}
"""

server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/index.html'
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(viewport={'width':390,'height':844})
    context.route('https://cdn.jsdelivr.net/**',lambda r:r.fulfill(status=200,body=SDK,content_type='application/javascript',headers={'Access-Control-Allow-Origin':'*'}))
    context.route('**/functions/v1/wordstep-account',lambda r:r.abort('failed'))
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.goto(url)
    page.evaluate("""localStorage.setItem('wordstep.progress.v1', JSON.stringify({w0001:true}));""")
    page.reload()
    page.locator('#cloud-open').click()
    page.locator('#cloud-account').fill('a-new-student')
    page.locator('#cloud-password').fill('a-password-123')
    page.locator('#cloud-login').click()
    page.wait_for_function("""() => {
      const s=document.querySelector('#cloud-status').textContent;
      return s.includes('Failed to fetch') || s.includes('連線') && s.includes('本機');
    }""",timeout=14000)
    msg=page.locator('#cloud-status').inner_text()
    assert 'Failed to fetch' not in msg, ('Raw network failure shown to learner',msg)
    assert '連線' in msg and '本機' in msg, ('Need friendly offline message',msg)
    assert page.evaluate("JSON.parse(localStorage.getItem('wordstep.progress.v1')).w0001===true"),'Previous data cleared'
    assert 'wordstep.cloud.pending.v1' in page.evaluate("Object.keys(localStorage).join(',')") or page.evaluate("localStorage.getItem('wordstep.progress.v1')") is not None
    page.locator('#cloud-close').click()
    assert page.locator('#word').inner_text(), 'Reading screen inaccessible'
    assert not errors,errors
    browser.close()
server.shutdown()
print('PASS: offline login error localization and local learning progress retention')
