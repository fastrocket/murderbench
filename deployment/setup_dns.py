"""Install only the MurderBench zone on the authorized DNS hosts."""
from pathlib import Path
import shutil
import subprocess
import sys
import time

DOMAIN = 'murderbench.com'
PRIMARY = '20.163.14.26'
SECONDARY = '23.23.200.63'
config = Path('/etc/bind/named.conf.local')
role = sys.argv[1]
original = config.read_text()
if f'zone "{DOMAIN}"' in original:
    raise SystemExit('Zone exists. Inspect before changing it.')
backup = str(config) + f'.murderbench-{int(time.time())}'
shutil.copy2(config, backup)
if role == 'primary':
    zone = Path('/etc/bind/zones') / DOMAIN
    if zone.exists():
        raise SystemExit('Zone file exists. Inspect before changing it.')
    zone.write_text(f'''$ORIGIN {DOMAIN}.
$TTL 300
@ IN SOA ns1.xenocom.com. hostmaster.xenocom.com. (
 2026100201 3600 1200 172800 300 )
@ IN NS ns1.xenocom.com.
@ IN NS ns2.xenocom.com.
@ IN A {PRIMARY}
www IN CNAME {DOMAIN}.
@ IN CAA 0 issue "letsencrypt.org"
@ IN TXT "v=spf1 -all"
_dmarc IN TXT "v=DMARC1; p=reject; sp=reject"
@ IN MX 0 .
''')
    subprocess.run(['named-checkzone', DOMAIN, str(zone)], check=True)
    block = f'\nzone "{DOMAIN}" {{ type master; file "{zone}"; allow-transfer {{ {SECONDARY}; }}; also-notify {{ {SECONDARY}; }}; }};\n'
elif role == 'secondary':
    block = f'\nzone "{DOMAIN}" {{ type slave; file "/var/cache/bind/db.{DOMAIN}"; masters {{ {PRIMARY}; }}; }};\n'
else:
    raise SystemExit('Role must be primary or secondary.')
config.write_text(original + block)
try:
    subprocess.run(['named-checkconf'], check=True)
    subprocess.run(['rndc', 'reconfig'], check=True)
except subprocess.CalledProcessError:
    config.write_text(original)
    subprocess.run(['rndc', 'reconfig'], check=True)
    raise
print(f'Installed {role}. Backup: {backup}')
