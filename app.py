"""Local single-user web demo. Run python app.py; never expose to a public network."""
import json
import os
import secrets
import datetime
from http.server import HTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from aegis.core import InputError
from aegis.service import Advisor

HTML=Path(__file__).with_name('ui.html').read_text(encoding='utf-8')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,body,ctype='application/json'):
        raw=body.encode() if isinstance(body,str) else json.dumps(body,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype+'; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'nonce-"+self.server.csrf+"'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(raw)
    def valid_host(self):
        return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
    def do_GET(self):
        if not self.valid_host(): return self.send(403,{'status':'DENIED'})
        if self.path=='/': return self.send(200,HTML.replace('__TOKEN__',self.server.csrf),'text/html')
        if self.path=='/health': return self.send(200,{'status':'ok','mode':'synthetic_local'})
        self.send(404,{'status':'NOT_FOUND'})
    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-AEGIS-Token')!=self.server.csrf or self.headers.get('Origin')!=f'http://127.0.0.1:{self.server.server_port}':
            return self.send(403,{'status':'DENIED'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>16384: return self.send(413,{'status':'INVALID_INPUT'})
            if self.headers.get('Content-Type')!='application/json': return self.send(415,{'status':'INVALID_INPUT'})
            d=json.loads(self.rfile.read(length))
            if not isinstance(d,dict): raise InputError('JSON object required')
            a=self.server.advisor
            if self.path=='/api/parse':
                result=a.parse(d.get('text'),d.get('llm') is True,d.get('consent') is True)
            elif self.path=='/api/propose':
                if d.get('confirmed') is not True: raise InputError('Confirm the interpreted constraints first')
                result=a.propose(d.get('profile'),d.get('constraints'),role='PROPOSE',gamma=.02,epsilon=.00002,cost_bps=1)
            elif self.path=='/api/approve':
                result=a.approve(d.get('proposal_id'),d.get('confirmed') is True,role='APPROVE_SIM')
            elif self.path=='/api/execute':
                result=a.execute(d.get('proposal_id'),d.get('approval_token'),role='APPROVE_SIM')
            elif self.path=='/api/products': result=a.products()
            else: return self.send(404,{'status':'NOT_FOUND'})
            self.send(200,result)
        except (InputError,ValueError,TypeError,KeyError) as e:
            self.send(400,{'status':'INVALID_INPUT','message':str(e)[:300]})
        except Exception:
            self.send(503,{'status':'UNAVAILABLE','message':'Operation stopped safely. Check the local environment.'})

def make_server(port=8765,advisor=None):
    server=HTTPServer(('127.0.0.1',port),Handler)
    server.timeout=15
    server.csrf=secrets.token_hex(24)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    server.advisor=advisor or Advisor(log=Path('runs')/f'{stamp}.jsonl')
    return server

if __name__=='__main__':
    server=make_server(int(os.environ.get('AEGIS_PORT','8765')))
    print(f'AEGIS synthetic demo: http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
