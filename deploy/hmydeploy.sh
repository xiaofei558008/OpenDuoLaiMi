set -e
B=/home/xiaofei/bak-hmy-$(date +%Y%m%d%H%M%S); mkdir -p $B
cd /home/xiaofei; rm -rf hmypkg; mkdir hmypkg; tar xzf hmypkg.tgz -C hmypkg
cp /var/www/music-data/songs/catalog.json /var/www/music-data/songs/20261025-225553-5828/meta.json $B/
cp hmypkg/songs/catalog.json /var/www/music-data/songs/catalog.json
cp hmypkg/songs/20261025-225553-5828/meta.json /var/www/music-data/songs/20261025-225553-5828/meta.json
chmod -R a+rX /var/www/music-data
echo BACKUP=$B; echo HMY_OK
