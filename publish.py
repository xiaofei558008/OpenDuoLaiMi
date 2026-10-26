#!/usr/bin/env python3
"""打包发布：生成 catalog + 两站 index.html，同步 Oracle(opendoremi，英文界面)，并打包阿里云(openduolaimi)的增量包。"""
import os, json, shutil, subprocess, tarfile, glob, sys, time
from generate import build_catalog
OUT="out"; PUB="pub"
UM='<script defer src="https://stats.opendebugger.com/script.js" data-website-id="{}" class="umami-tracker"></script>'
IDS={"duo":"93cf5b4d-137e-4fe9-b791-7fd667756b00","dor":"7899420c-45e5-4de7-ab65-5a656cdf7d65"}
FILES=("song.mp3","cover.jpg","lyrics.txt","lyrics.json","lyrics.lrc","meta.json","mv_small.mp4","song.opus")
def stage():
    cat=[c for c in build_catalog(OUT) if os.path.exists(os.path.join(OUT,c["id"],"cover.jpg"))]
    json.dump(cat,open(os.path.join(OUT,"catalog.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    os.makedirs(PUB+"/songs",exist_ok=True)
    for c in cat:
        d=os.path.join(PUB,"songs",c["id"]); os.makedirs(d,exist_ok=True)
        for f in FILES:
            s=os.path.join(OUT,c["id"],f)
            if os.path.exists(s): shutil.copy2(s,d)
        h=os.path.join(OUT,c["id"],"hls")
        if os.path.isdir(h): shutil.copytree(h,os.path.join(d,"hls"),dirs_exist_ok=True)
        mp=os.path.join(d,"meta.json")
        if os.path.exists(mp):
            m=json.load(open(mp,encoding="utf-8"))
            if m.pop("label",None) is not None: json.dump(m,open(mp,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    shutil.copy2(os.path.join(OUT,"catalog.json"),PUB+"/songs/catalog.json")
    shutil.copy2("site/hls.min.js",PUB+"/songs/hls.min.js")
    shutil.copytree("site/singers",PUB+"/songs/singers",dirs_exist_ok=True)
    t=open("site/tpl.html",encoding="utf-8").read()
    for k,v in IDS.items(): open(f"{PUB}/{k}.html","w",encoding="utf-8").write(t.replace("__UMAMI__",UM.format(v)))
    shutil.copy2(f"{PUB}/duo.html",PUB+"/songs/_duo.html")
    return cat
def oracle():
    P="/workspace/oracle/venv/bin/python"; R="/workspace/oracle/rsh.py"
    ts=time.strftime("%Y%m%d%H%M%S")
    subprocess.run([P,R,"run",f"mkdir -p ~/bak-{ts} && cp /var/www/opendoremi.com/index.html ~/bak-{ts}/ && cp /var/www/music-data/songs/catalog.json ~/bak-{ts}/ ; mkdir -p ~/stage/songs"],check=True)
    subprocess.run([P,R,"puttree",PUB+"/songs","/home/ubuntu/stage/songs"],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([P,R,"put",PUB+"/dor.html","/home/ubuntu/stage/index.html"],check=True)
    subprocess.run([P,R,"run","sudo cp -r /home/ubuntu/stage/songs/. /var/www/music-data/songs/ && sudo cp /home/ubuntu/stage/index.html /var/www/opendoremi.com/index.html && sudo chown -R www-data:www-data /var/www/opendoremi.com /var/www/music-data && echo SYNC_OK"],check=True)
def aliyun_pkg(path="/workspace/aimusic/alipkg.tgz"):
    with tarfile.open(path,"w:gz") as t:
        t.add(PUB+"/songs",arcname="songs"); t.add(PUB+"/duo.html",arcname="duo.html")
    return path
if __name__=="__main__":
    c=stage(); print("songs",len(c))
    if "oracle" in sys.argv: oracle()
    if "aliyun" in sys.argv: subprocess.run([sys.executable,"alipush.py"],check=True)  # 默认国内直推，见 alipush.py
