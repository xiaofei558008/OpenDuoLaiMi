#!/usr/bin/env python3
"""一步上线英文歌：python3 publish_en.py  （需要 /workspace/portraits/sienna_varlow.png 与 callen_ashgrove.png）
1) 肖像 -> site/singers/<slug>.webp + -96.webp  2) tpl.html 注册头像  3) out_en/* 复制进 out/（歌手名按 EN_SINGERS）
4) publish.py oracle aliyun  5) 打印阿里云拉取命令（经 Tom 电脑 ssh 执行 ~/alipull.sh）"""
import os,sys,json,shutil,subprocess,glob,re
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from en_batch import EN_SINGERS
from PIL import Image
for k,v in EN_SINGERS.items():
    p=f"/workspace/portraits/{v['slug']}.png"
    if not os.path.exists(p): sys.exit("missing portrait "+p)
    im=Image.open(p).convert("RGB"); w,h=im.size; s=min(w,h); im=im.crop(((w-s)//2,(h-s)//2,(w+s)//2,(h+s)//2))
    im.resize((512,512)).save(f"site/singers/{v['slug']}.webp",quality=85); im.resize((96,96)).save(f"site/singers/{v['slug']}-96.webp",quality=85)
t=open("site/tpl.html",encoding="utf-8").read()
for v in EN_SINGERS.values():
    if f"'{v['display']}':'{v['slug']}'" not in t: t=t.replace("const AVK={",f"const AVK={{'{v['display']}':'{v['slug']}',",1)
t=t.replace(r"/抒情|情歌|慢歌|流行/.test(g)",r"/抒情|情歌|慢歌|流行|pop|ballad|country|folk|rock|r&b/i.test(g)") if "pop|ballad" not in t else t
open("site/tpl.html","w",encoding="utf-8").write(t)
n=0
for m in glob.glob("out_en/*/meta.json"):
    d=json.load(open(m)); sk=d.get("singer_id") or d["singer"]
    if sk in EN_SINGERS: d["singer_id"]=sk; d["singer"]=EN_SINGERS[sk]["display"]
    json.dump(d,open(m,"w"),indent=2,ensure_ascii=False)
    if not os.path.exists(os.path.join(os.path.dirname(m),"cover.jpg")): print("skip no cover",m); continue
    shutil.copytree(os.path.dirname(m),"out/"+os.path.basename(os.path.dirname(m)),dirs_exist_ok=True); n+=1
print("EN songs copied",n)
subprocess.run([sys.executable,"publish.py","oracle","aliyun"],check=True)
print("NEXT (Aliyun): CopyFromBox /workspace/alipush/* to Tom PC, scp to ~/alipush/, sudo bash ~/alipush/apply.sh (see alipush.py)")
