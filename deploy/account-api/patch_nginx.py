import sys,re
p='/etc/nginx/sites-available/openduolaimi'
s=open(p).read()
if 'OpenDoremi account API' in s: print('already'); sys.exit()
cat='''    location = /api/v1/catalog.json {
        default_type application/json; types { application/json json; }
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
        add_header Access-Control-Allow-Headers "*" always;
        add_header Cache-Control "no-cache" always;
        if ($request_method = OPTIONS) { return 204; }
        try_files $uri =404;
    }
'''
snip=open('/tmp/odapi/nginx-api.snippet').read()
anchor='    location /api/ {'
assert anchor in s
s=s.replace(anchor, cat+snip+anchor,1)
open(p,'w').write(s); print('patched')
