#!/usr/bin/env python3
"""打包发布：生成 catalog + 两站 index.html，同步 Oracle(opendoremi，英文界面)，并打包阿里云(openduolaimi)的增量包。"""
import os, json, shutil, subprocess, tarfile, glob, sys, time
from generate import build_catalog
import api
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
    t=render(t)
    for k,v in IDS.items(): open(f"{PUB}/{k}.html","w",encoding="utf-8").write(t.replace("__UMAMI__",UM.format(v)))
    downloads()
    shutil.copy2(f"{PUB}/duo.html",PUB+"/songs/_duo.html")
    api.build(cat)  # /api/v1/catalog.json
    return cat
ICONS=os.environ.get("OD_ICONS","site/icons")
def icon(n):
    p=os.path.join(ICONS,n+".svg")
    if not os.path.exists(p): p=os.path.join("site/icons",n+".svg")
    s=open(p,encoding="utf-8").read().strip()
    s=s[s.index("<svg"):]
    return s.replace("<svg",'<svg aria-hidden="true" focusable="false" class="i-'+n+'"',1)
def render(t):
    import re
    t=re.sub(r"__I_([a-z-]+)__",lambda m:icon(m.group(1)),t)
    return t.replace("__ACCT__",open("site/acct.js",encoding="utf-8").read())
def downloads():
    """/download 页（noindex，暂不挂导航）。包信息在 site/downloads.json，空 = 即将推出。"""
    d=json.load(open("site/downloads.json",encoding="utf-8")); tpl=open("site/download.html",encoding="utf-8").read()
    L={"duo":dict(lang="zh-CN",name="OpenDuolaimi",title="下载 App · OpenDuolaimi",h1="下载 OpenDuolaimi App",sub="不登录也能完整播放；登录后收藏、最近播放和续播可在 App 与网页间同步。",
        soon="即将推出",ready="可下载",dl="下载",ver="版本",size="大小",sha="SHA-256",tbd="待发布",
        android=("Android","适用于 Android 手机和平板",["下载 APK 文件","首次安装时，在系统提示中允许“安装未知来源应用”","打开 APK 完成安装","可在电脑上用 sha256 校验文件完整性"]),
        windows=("Windows","适用于 Windows 10 / 11（64 位）",["下载安装包","双击运行；若出现 SmartScreen 提示，点“更多信息”→“仍要运行”","按向导完成安装","可用 PowerShell：Get-FileHash 文件名 校验 SHA-256"])),
       "dor":dict(lang="en",name="OpenDoremi",title="Download the app · OpenDoremi",h1="Download OpenDoremi",sub="Fully playable without an account; log in to sync favorites, recently played and resume between the app and the web.",
        soon="Coming soon",ready="Available",dl="Download",ver="Version",size="Size",sha="SHA-256",tbd="TBA",
        android=("Android","For Android phones and tablets",["Download the APK file","When prompted, allow installing apps from this source","Open the APK to install","Optionally verify the file with its SHA-256"]),
        windows=("Windows","For Windows 10 / 11 (64-bit)",["Download the installer","Run it; if SmartScreen appears, choose More info → Run anyway","Follow the setup wizard","Optionally verify: Get-FileHash <file> in PowerShell"]))}
    import html as H
    for k,m in L.items():
        cards=""
        for pf in ("android","windows"):
            x=d.get(pf,{}); nm,desc,steps=m[pf]; ok=bool(x.get("file"))
            v=lambda f:H.escape(x.get(f) or m["tbd"])
            cards+=f'<section class="c" id="{pf}"><h2>{nm}</h2><span class="st">{m["ready"] if ok else m["soon"]}</span><div style="opacity:.75;font-size:14px">{desc}</div>'
            cards+=f'<dl><dt>{m["ver"]}</dt><dd>{v("version")}</dd><dt>{m["size"]}</dt><dd>{v("size")}</dd><dt>{m["sha"]}</dt><dd>{v("sha256")}</dd></dl>'
            cards+=(f'<a class="btn" href="{H.escape(x["file"])}" download>{m["dl"]}</a>' if ok else f'<a class="btn dis" aria-disabled="true">{m["soon"]}</a>')
            cards+="<ol>"+"".join(f"<li>{H.escape(s)}</li>" for s in steps)+"</ol></section>"
        o=tpl.replace("__CARDS__",cards)
        for f in ("lang","name","title","h1","sub"): o=o.replace("__"+f.upper()+"__",H.escape(m[f]))
        os.makedirs(f"{PUB}/download",exist_ok=True); open(f"{PUB}/download/{k}.html","w",encoding="utf-8").write(o)
def oracle():
    P="/workspace/oracle/venv/bin/python"; R="/workspace/oracle/rsh.py"
    ts=time.strftime("%Y%m%d%H%M%S")
    subprocess.run([P,R,"run",f"mkdir -p ~/bak-{ts} && cp /var/www/opendoremi.com/index.html ~/bak-{ts}/ && cp /var/www/music-data/songs/catalog.json ~/bak-{ts}/ ; mkdir -p ~/stage/songs"],check=True)
    subprocess.run([P,R,"puttree",PUB+"/songs","/home/ubuntu/stage/songs"],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([P,R,"put",PUB+"/dor.html","/home/ubuntu/stage/index.html"],check=True)
    subprocess.run([P,R,"put",PUB+"/download/dor.html","/home/ubuntu/stage/download.html"],check=True)
    subprocess.run([P,R,"put",PUB+"/api/dor/v1/catalog.json","/home/ubuntu/stage/catalog.json"],check=True)
    subprocess.run([P,R,"run","sudo cp -r /home/ubuntu/stage/songs/. /var/www/music-data/songs/ && sudo cp /home/ubuntu/stage/index.html /var/www/opendoremi.com/index.html && sudo mkdir -p /var/www/opendoremi.com/download && sudo cp /home/ubuntu/stage/download.html /var/www/opendoremi.com/download/index.html && sudo mkdir -p /var/www/opendoremi.com/api/v1 && sudo cp /home/ubuntu/stage/catalog.json /var/www/opendoremi.com/api/v1/catalog.json && sudo chown -R www-data:www-data /var/www/opendoremi.com /var/www/music-data && echo SYNC_OK"],check=True)
def aliyun_pkg(path="/workspace/aimusic/alipkg.tgz"):
    with tarfile.open(path,"w:gz") as t:
        t.add(PUB+"/songs",arcname="songs"); t.add(PUB+"/duo.html",arcname="duo.html")
    return path
if __name__=="__main__":
    c=stage(); print("songs",len(c))
    if "oracle" in sys.argv: oracle()
    if "aliyun" in sys.argv: subprocess.run([sys.executable,"alipush.py"],check=True)  # 默认国内直推，见 alipush.py
