set -e
cd ~; T=$(mktemp -d); tar xzf ~/odweb.tgz -C $T
R=/var/www/openduolaimi.com; B=~/bak-web-$(date +%Y%m%d%H%M%S); mkdir -p $B; cp $R/index.html $B/duo.html; cp /var/www/music-data/songs/_duo.html $B/_duo.html 2>/dev/null || true
cp $T/duo.html $R/index.html; mkdir -p $R/download; cp $T/download/duo.html $R/download/index.html; cp $T/songs/_duo.html /var/www/music-data/songs/_duo.html
chmod -R a+rX $R/index.html $R/download; rm -rf $T ~/odweb.tgz; echo BACKUP=$B; echo WEB_OK
