# 阿里云 openduolaimi.com：从 Oracle(opendoremi.com) 拉取歌曲增量 + 中文版首页。先备份。
set -e
S=https://opendoremi.com/songs; W=/var/www/music-data/songs; T=/home/xiaofei/pull; rm -rf $T; mkdir -p $T
B=/home/xiaofei/bak-batch-$(date +%Y%m%d%H%M%S); mkdir -p $B
cp $W/catalog.json $B/; cp /var/www/openduolaimi.com/index.html $B/duo.html
for d in $W/*/; do [ -f $d/lyrics.json ] && cp $d/lyrics.json $B/$(basename $d).lyrics.json; done
curl -sfL --retry 3 $S/catalog.json -o $T/catalog.json; curl -sfL --retry 3 $S/_duo.html -o $T/duo.html
grep -q 93cf5b4d-137e-4fe9-b791-7fd667756b00 $T/duo.html
n=0
for id in $(python3 -c "import json;[print(x['id']) for x in json.load(open('$T/catalog.json'))]"); do
  mkdir -p $W/$id
  for f in song.mp3 cover.jpg lyrics.txt lyrics.json lyrics.lrc meta.json; do
    case $f in song.mp3|cover.jpg) [ -s $W/$id/$f ] && [ "$id" != "${FORCE:-x}" ] && continue;; esac
    curl -sfL --retry 3 $S/$id/$f -o $W/$id/$f.tmp && mv $W/$id/$f.tmp $W/$id/$f || echo "MISS $id/$f"
  done; n=$((n+1))
done
cp $T/catalog.json $W/catalog.json; cp $T/duo.html /var/www/openduolaimi.com/index.html
chmod -R a+rX $W /var/www/openduolaimi.com
echo BACKUP=$B SONGS=$n; echo ALI_OK
