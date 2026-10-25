set -e
cd /home/xiaofei; rm -rf mp && mkdir mp && tar xzf music.tgz -C mp
mkdir -p /var/www/music-data && rm -rf /var/www/music-data/songs && cp -r mp/songs /var/www/music-data/ && chmod -R a+rX /var/www/music-data
for s in openduolaimi opendoremi; do r=/var/www/$s.com; [ -f $r/index.html.bak ] || cp $r/index.html $r/index.html.bak; done
cp mp/duo/index.html /var/www/openduolaimi.com/index.html; cp mp/dor/index.html /var/www/opendoremi.com/index.html
for s in openduolaimi opendoremi; do f=/etc/nginx/sites-available/$s
 grep -q music-data $f || { cp $f /root/$s.nginx.bak; sed -i '0,/location \/ {/s||location /songs/ { alias /var/www/music-data/songs/; location ~ \\.mp3$ { add_header Cache-Control "public, max-age=2592000"; } location ~ \\.json$ { add_header Cache-Control "no-cache"; } }\n    location / {|' $f; }
done
nginx -t && systemctl reload nginx && echo DEPLOY_OK
