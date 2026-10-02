"""Verify the published static release without credentials or model requests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import socket
import ssl
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://murderbench.com'

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.paths = set()
    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key in ('href','src') and value and value.startswith('/'):
                self.paths.add(value.split('#')[0].split('?')[0])

def fetch(path):
    with urllib.request.urlopen(ORIGIN+path, timeout=20) as response:
        body = response.read()
        local = ROOT/'site'/path.lstrip('/')
        return {'path':path,'status':response.status,
                'local_bytes_match':body==local.read_bytes() if local.is_file() else None,
                'sha256':hashlib.sha256(body).hexdigest()}

def main():
    parser = Links()
    pages = list((ROOT/'site').glob('*.html'))
    for page in pages:
        parser.feed(page.read_text(encoding='utf-8'))
        parser.paths.add('/'+page.name)
    paths = sorted(parser.paths | {'/sitemap.xml','/robots.txt'})
    with ThreadPoolExecutor(max_workers=8) as executor:
        checks = list(executor.map(fetch,paths))
    redirects = []
    for url in ['http://murderbench.com/','https://www.murderbench.com/']:
        with urllib.request.urlopen(url,timeout=20) as response:
            redirects.append({'requested':url,'final':response.url,'status':response.status})
    with urllib.request.urlopen(ORIGIN,timeout=20) as response:
        headers = {name:response.headers.get(name) for name in ['Content-Security-Policy','Strict-Transport-Security','X-Content-Type-Options','X-Frame-Options']}
    with socket.create_connection(('murderbench.com',443),timeout=20) as connection:
        with ssl.create_default_context().wrap_socket(connection,server_hostname='murderbench.com') as secure:
            certificate = secure.getpeercert()
    request = urllib.request.Request('https://cloudflare-dns.com/dns-query?name=murderbench.com&type=NS',headers={'Accept':'application/dns-json'})
    with urllib.request.urlopen(request,timeout=20) as response:
        dns = json.load(response)
    report = {'verified_utc':datetime.now(timezone.utc).isoformat(),'page_count':len(pages),
              'checks':checks,'redirects':redirects,'headers':headers,
              'certificate_expiry':certificate['notAfter'],'certificate_names':certificate['subjectAltName'],
              'nameservers':dns.get('Answer',[])}
    (ROOT/'reviews/final-public-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    assert all(check['status']==200 and check['local_bytes_match'] is not False for check in checks)
    assert all(check['final']=='https://murderbench.com/' for check in redirects)
    assert all(headers.values())
    names = {answer['data'].rstrip('.') for answer in dns.get('Answer',[]) if answer['type']==2}
    assert names == {'ns1.xenocom.com','ns2.xenocom.com'}, names
    print(f'Verified {len(pages)} pages, {len(checks)} local resources, redirects, TLS, headers and nameserver delegation.')

if __name__ == '__main__':
    main()
