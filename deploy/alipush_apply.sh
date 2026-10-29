set -e
cd /home/xiaofei/alipush
for p in $(ls *.part00 2>/dev/null); do b=${p%.part00}; cat $b.part* > $b.tar; done
md5sum -c --quiet md5.txt; echo MD5_OK
W=/var/www/music-data/songs; B=/home/xiaofei/bak-push-$(date +%Y%m%d%H%M%S); mkdir -p $B
cp $W/catalog.json $B/; cp /var/www/openduolaimi.com/index.html $B/duo.html; [ -f /var/www/openduolaimi.com/download/index.html ] && cp /var/www/openduolaimi.com/download/index.html $B/download.html || true
P=$(pgrep -f 'bash /home/xiaofei/alipull.sh' || true); [ -n "$P" ] && kill $P && echo KILLED_PULL $P
rm -rf st; mkdir st; for t in q*.tar ; do tar xf $t -C st; done
cp -r st/songs/. $W/; cp st/duo.html /var/www/openduolaimi.com/index.html; mkdir -p /var/www/openduolaimi.com/download; cp st/download/duo.html /var/www/openduolaimi.com/download/index.html; mkdir -p /var/www/openduolaimi.com/api/v1; cp st/api/duo/v1/catalog.json /var/www/openduolaimi.com/api/v1/catalog.json
find $W -name '*.tmp' -delete
for d in $W/*/; do [ -f $d/hls/master.m3u8 ] && date > $d/hls/.ok; done
chown -R xiaofei:xiaofei $W /var/www/openduolaimi.com; chmod -R a+rX $W /var/www/openduolaimi.com
python3 -c "import json;c=json.load(open('$W/catalog.json'));import os;print('CAT',len(c),'missing',[x['id'] for x in c if not os.path.exists('$W/'+x['id']+'/song.opus') or not os.path.exists('$W/'+x['id']+'/cover.jpg')])"
rm -rf st q*.tar q*.part* part*.tar; echo BACKUP=$B; echo PUSH_OK
