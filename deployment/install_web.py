"""Install the isolated FastAPI site and Apache configuration."""
from pathlib import Path
import shutil
import subprocess
import sys
import time

source = Path(sys.argv[1]).resolve(strict=True)
root = Path('/var/www/murderbench')
root.mkdir(exist_ok=True)
shutil.copytree(source / 'site', root, dirs_exist_ok=True)
subprocess.run(['chmod', '-R', 'a+rX', str(root)], check=True)
service = Path('/etc/systemd/system/murderbench.service')
shutil.copy2(source / 'deployment/murderbench.service', service)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'murderbench'], check=True)
subprocess.run(['systemctl', 'restart', 'murderbench'], check=True)
config = Path('/etc/apache2/sites-available/murderbench.com.conf')
old = config.read_text() if config.exists() else None
if old:
    shutil.copy2(config, str(config) + f'.backup-{int(time.time())}')
http = '''<VirtualHost *:80>
 ServerName murderbench.com
 ServerAlias www.murderbench.com
 Alias /.well-known/acme-challenge/ /var/www/murderbench/.well-known/acme-challenge/
 <Directory /var/www/murderbench/.well-known/acme-challenge>
  Require all granted
 </Directory>
 ProxyPass /.well-known/acme-challenge/ !
 ProxyPreserveHost On
 ProxyPass / http://127.0.0.1:8014/
 ProxyPassReverse / http://127.0.0.1:8014/
</VirtualHost>
'''
cert = Path('/etc/letsencrypt/live/murderbench.com/fullchain.pem')
if cert.exists():
    http = http.replace(' ProxyPass / http://127.0.0.1:8014/', ' RewriteEngine On\n RewriteCond %{REQUEST_URI} !^/\\.well-known/acme-challenge/\n RewriteRule ^ https://murderbench.com%{REQUEST_URI} [R=301,L]\n ProxyPass / http://127.0.0.1:8014/')
    http += '''<VirtualHost *:443>
 ServerName murderbench.com
 ServerAlias www.murderbench.com
 SSLEngine On
 Include /etc/letsencrypt/options-ssl-apache.conf
 SSLCertificateFile /etc/letsencrypt/live/murderbench.com/fullchain.pem
 SSLCertificateKeyFile /etc/letsencrypt/live/murderbench.com/privkey.pem
 RewriteEngine On
 RewriteCond %{HTTP_HOST} ^www\\.murderbench\\.com$ [NC]
 RewriteRule ^ https://murderbench.com%{REQUEST_URI} [R=301,L]
 ProxyPreserveHost On
 RequestHeader set X-Forwarded-Proto "https"
 ProxyPass / http://127.0.0.1:8014/
 ProxyPassReverse / http://127.0.0.1:8014/
 Header always set X-Content-Type-Options "nosniff"
 Header always set Referrer-Policy "strict-origin-when-cross-origin"
 Header always set X-Frame-Options "DENY"
 Header always set Strict-Transport-Security "max-age=31536000"
 Header always set Content-Security-Policy "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
 ErrorLog ${APACHE_LOG_DIR}/murderbench-error.log
 CustomLog ${APACHE_LOG_DIR}/murderbench-access.log combined
</VirtualHost>
'''
config.write_text(http)
try:
    subprocess.run(['a2ensite', 'murderbench.com.conf'], check=True)
    subprocess.run(['apache2ctl', 'configtest'], check=True)
except subprocess.CalledProcessError:
    if old is not None:
        config.write_text(old)
    else:
        subprocess.run(['a2dissite', 'murderbench.com.conf'], check=True)
    raise
subprocess.run(['systemctl', 'reload', 'apache2'], check=True)
print('HTTPS enabled' if cert.exists() else 'HTTP ready. Issue certificate after public DNS resolves.')
