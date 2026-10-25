set -e
B=/home/xiaofei/bak-lrc-$(date +%Y%m%d%H%M%S); mkdir -p $B
cd /home/xiaofei; rm -rf lrcpkg; mkdir lrcpkg; tar xzf lrcpkg.tgz -C lrcpkg
cp /var/www/music-data/songs/catalog.json $B/; cp /var/www/openduolaimi.com/index.html $B/duo.html; cp /var/www/opendoremi.com/index.html $B/dor.html
for d in lrcpkg/songs/*/; do id=$(basename $d); cp /var/www/music-data/songs/$id/meta.json $B/$id.meta.json; cp $d/* /var/www/music-data/songs/$id/; done
cp lrcpkg/songs/catalog.json /var/www/music-data/songs/catalog.json
cp lrcpkg/duo.html /var/www/openduolaimi.com/index.html; cp lrcpkg/dor.html /var/www/opendoremi.com/index.html
chmod -R a+rX /var/www/music-data /var/www/openduolaimi.com /var/www/opendoremi.com
echo BACKUP=$B; echo LRC_OK
