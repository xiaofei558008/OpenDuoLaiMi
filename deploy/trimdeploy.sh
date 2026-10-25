set -e
B=/home/xiaofei/bak-trim-$(date +%Y%m%d%H%M%S); mkdir -p $B
cd /home/xiaofei; rm -rf trimpkg; mkdir trimpkg; tar xzf trimpkg.tgz -C trimpkg
cp -a /var/www/music-data/songs $B/songs
cp /var/www/openduolaimi.com/index.html $B/duo.html; cp /var/www/opendoremi.com/index.html $B/dor.html
for d in trimpkg/songs/*/; do id=$(basename $d); cp $d/song.mp3 $d/meta.json /var/www/music-data/songs/$id/; done
cp trimpkg/songs/catalog.json /var/www/music-data/songs/catalog.json
cp trimpkg/duo.html /var/www/openduolaimi.com/index.html; cp trimpkg/dor.html /var/www/opendoremi.com/index.html
chmod -R a+rX /var/www/music-data /var/www/openduolaimi.com /var/www/opendoremi.com
echo BACKUP=$B; echo TRIM_OK
