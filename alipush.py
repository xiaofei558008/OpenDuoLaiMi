#!/usr/bin/env python3
"""阿里云默认发布路线（国内直推，替代跨境 alipull）：
1) Tom 电脑: ssh xiaofei@8.133.18.102 'bash list.sh' 生成 ~/alilist.txt，scp 回电脑，CopyToBox 到 /workspace/alipush/alilist.txt
2) python3 alipush.py   -> /workspace/alipush/q*.tar（每块<=15MB, CopyFromBox 上限实测约 18MB）+ md5.txt + apply.sh
3) CopyFromBox 各块到 C:\\Users\\Administrator\\，scp 到 ~/alipush/，sudo bash ~/alipush/apply.sh
alipull.sh 仅作兜底（跨境很慢，约 15KB/s）。"""
import os,tarfile,glob,hashlib,shutil,subprocess
PUB="/workspace/aimusic/pub"; O="/workspace/alipush"; LIM=15e6
for f in glob.glob(O+"/q*")+glob.glob(O+"/part*"): os.remove(f)
have={}
if os.path.exists(O+"/alilist.txt"):
    for l in open(O+"/alilist.txt"):
        s,p=l.rstrip("\n").split(" ",1); have[p[2:]]=int(s)
os.chdir(PUB); need=[]
for r,d,f in os.walk("songs"):
    for x in f:
        lp=os.path.join(r,x); rp=lp[6:]
        if x=="mv.mp4": continue
        if rp in have and have[rp]==os.path.getsize(lp) and not x.endswith((".json",".html",".m3u8",".js")): continue
        need.append(lp)
need.append("duo.html"); need.append("download/duo.html"); need.append("api/duo/v1/catalog.json"); ch=[];cur=[];sz=0
for p in need:
    s=os.path.getsize(p)
    if sz+s>LIM and cur: ch.append(cur);cur=[];sz=0
    cur.append(p);sz+=s
ch.append(cur)
for i,c in enumerate(ch):
    t=f"{O}/q{i:03d}.tar"
    with tarfile.open(t,"w") as tf:
        for p in c: tf.add(p)
    if os.path.getsize(t)>LIM*1.2: subprocess.run(["split","-b","15M","-d",t,t[:-4]+".part"],check=True); 
subprocess.run(f"cd {O} && md5sum q*.tar > md5.txt && for t in q*.tar; do [ -f ${{t%.tar}}.part00 ] && rm $t; done; true",shell=True)
shutil.copy2("/workspace/aimusic/alipush_apply.sh",O+"/apply.sh")
print(len(need),"files",len(ch),"chunks ->",O)
