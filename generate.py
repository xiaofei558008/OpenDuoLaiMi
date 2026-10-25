#!/usr/bin/env python3
"""AI 音乐生成流水线: 网易云热歌榜(仅标题/歌手) -> Grok 原创歌词 -> Mureka 作曲演唱 -> Grok 封面.
用法: python generate.py --count 3 [--out out]
环境变量: XAI_API_KEY, MUREKA_API_KEY, 可选 XAI_TEXT_MODEL, XAI_IMAGE_MODEL, MUREKA_MODEL, MUREKA_BASE"""
from aitrim import strip_ai_notice
import lyrics_align
def make_timed_lyrics(od,c,lyrics,max_end=None):
    """歌词时间轴（基于剪完后的音频）：优先 Mureka lyrics_sections，否则 whisper 对齐。"""
    L=lyrics_align.from_mureka(c.get("lyrics_sections"),max_end) if c.get("lyrics_sections") else []
    if not L:
        try: L=lyrics_align.align(os.path.join(od,"song.mp3"),lyrics)
        except Exception as e: print("align failed",e); L=[]
    if L:
        json.dump(L,open(os.path.join(od,"lyrics.json"),"w",encoding="utf-8"),ensure_ascii=False)
        lyrics_align.write_lrc(L,os.path.join(od,"lyrics.lrc"))
import os, json, time, argparse, re, datetime, uuid, glob, requests
XAI="https://api.x.ai/v1"
MUREKA=os.environ.get("MUREKA_BASE","https://api.mureka.cn")
TEXT_MODEL=os.environ.get("XAI_TEXT_MODEL","grok-4.7")
IMG_MODEL=os.environ.get("XAI_IMAGE_MODEL","grok-imagine-image-2.0")
MUREKA_MODEL=os.environ.get("MUREKA_MODEL","auto")
STYLES=["抒情慢歌 ballad","轻快流行 upbeat pop","古风 中国风","民谣 folk","电子流行 synth-pop"]

def xh(): return {"Authorization":"Bearer "+os.environ["XAI_API_KEY"]}
def mh(): return {"Authorization":"Bearer "+os.environ["MUREKA_API_KEY"],"Content-Type":"application/json"}

def chart(n=20):
    r=requests.get("https://music.163.com/api/playlist/detail?id=3778678",headers={"Referer":"https://music.163.com/","User-Agent":"Mozilla/5.0"},timeout=20)
    tr=r.json()["result"]["tracks"][:n]
    return [{"title":t["name"],"artists":[a["name"] for a in t["artists"]]} for t in tr]

def bad(text,ch):
    for c in ch:
        for w in [c["title"]]+c["artists"]:
            w=w.strip()
            if len(w)>=2 and w in text: return w
        t=re.sub(r"\s","",c["title"])
        for i in range(len(t)-5):
            if t[i:i+6] in text: return t[i:i+6]
    return None

def gen_lyrics(ch,style,tries=4):
    names="; ".join(c["title"] for c in ch)
    prompt=(f"以下是热歌榜歌名(仅用于提炼抽象主题,严禁引用): {names}\n"
      f"请提炼一个抽象主题,创作一首完全原创的中文歌曲,风格: {style}。禁止出现任何榜单歌名、歌手名(包括真实歌手的名字)或已知歌词。"
      "歌词用[Verse]/[Pre-Chorus]/[Chorus]/[Bridge]结构,约2-3分钟。只输出JSON: "
      '{"theme":"","genre":"","mood":"","tempo":"","vocal":"男声或女声","title":"","lyrics":"","cover_prompt":"抽象艺术封面英文描述,无文字无人物"}')
    for _ in range(tries):
        r=requests.post(XAI+"/chat/completions",headers=xh(),json={"model":TEXT_MODEL,"messages":[{"role":"user","content":prompt}],"response_format":{"type":"json_object"}},timeout=180)
        r.raise_for_status()
        d=json.loads(r.json()["choices"][0]["message"]["content"])
        b=bad(d["title"]+d["lyrics"],ch)
        if not b: return d
        print("filter reject:",d["title"],"hit:",b)
    raise RuntimeError("歌词多次未通过版权过滤")

# 平台虚拟歌手（原创艺名）。voice 为写进 Mureka prompt 的英文音色描述，不含任何真实歌手名
SINGERS={
  "夏音禾":{"gender":"女声","age":26,"desc":"清亮音色","voice":"bright clear young female vocal, airy and sweet"},
  "陈乐川":{"gender":"男声","age":23,"desc":"清爽少年感","voice":"warm youthful male vocal, clean and gentle"},
  "何曼伊":{"gender":"女声","age":38,"desc":"低沉沧桑、有故事感","voice":"mature husky low female vocal, weathered and storytelling"},
}
OLD_KEYS=("古风","中国风","抒情","怀旧","民谣","ballad","retro","chinese style","folk")
def pick_singer(style,i=0):
    """先选歌手：古风/抒情/怀旧类优先何曼伊，其余在夏音禾、陈乐川间轮换。"""
    if any(k in str(style).lower() for k in OLD_KEYS): return "何曼伊"
    return ("夏音禾","陈乐川")[i%2]
def singer_of(vocal):  # 兼容旧数据
    v=str(vocal).lower()
    return "夏音禾" if ("女" in v or "female" in v) else "陈乐川"

def gen_song(d,singer):
    # 提示词只描述曲风与原创歌手音色,不出现任何真实歌手名
    style=f'{d["genre"]}, {d["mood"]}, {d["tempo"]}, {SINGERS[singer]["voice"]}'
    r=requests.post(MUREKA+"/v1/song/generate",headers=mh(),json={"lyrics":d["lyrics"],"model":MUREKA_MODEL,"prompt":style},timeout=60)
    if r.status_code!=200: raise SystemExit(f"Mureka error {r.status_code}: {r.text}")
    tid=r.json()["id"]
    while True:
        time.sleep(10)
        q=requests.get(f"{MUREKA}/v1/song/query/{tid}",headers=mh(),timeout=30).json()
        if q["status"]=="succeeded": return style,q
        if q["status"] in("failed","timeouted","cancelled"): raise RuntimeError(json.dumps(q,ensure_ascii=False))

def gen_cover(p,path):
    r=requests.post(XAI+"/images/generations",headers=xh(),json={"model":IMG_MODEL,"prompt":p+", abstract art, square album cover, no text","n":1,"response_format":"b64_json"},timeout=180)
    r.raise_for_status()
    import base64; open(path,"wb").write(base64.b64decode(r.json()["data"][0]["b64_json"]))

def main():
    a=argparse.ArgumentParser(); a.add_argument("--count",type=int,default=3); a.add_argument("--out",default="out"); a=a.parse_args()
    ch=chart()
    for i in range(a.count):
        st=STYLES[i%len(STYLES)]; singer=pick_singer(st,i); sg=SINGERS[singer]
        d=gen_lyrics(ch,f'{st}; 演唱者为{sg["age"]}岁{sg["gender"]}，{sg["desc"]}，请按其年龄与音色写词')
        d["vocal"]=sg["gender"]
        sid=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:4]
        od=os.path.join(a.out,sid); os.makedirs(od)
        open(os.path.join(od,"lyrics.txt"),"w",encoding="utf-8").write(d["lyrics"])
        style,q=gen_song(d,singer); c=q["choices"][0]
        open(os.path.join(od,"song.mp3"),"wb").write(requests.get(c["url"],timeout=120).content)
        tr=strip_ai_notice(os.path.join(od,"song.mp3"))
        if tr: c["duration"]=int(tr["new_duration"]*1000); print("trimmed AI notice",tr)
        make_timed_lyrics(od,c,d["lyrics"],(c.get("duration") or 0)/1000 or None)
        gen_cover(d.get("cover_prompt",d["theme"]),os.path.join(od,"cover.jpg"))
        meta={k:d[k] for k in("title","theme","genre","mood","tempo","vocal")}
        meta.update(singer=singer,style_prompt=style,duration_ms=c.get("duration"),models={"lyrics":TEXT_MODEL,"cover":IMG_MODEL,"music":q.get("model",MUREKA_MODEL)},
            created=datetime.datetime.now().isoformat(),label="AI生成",license="CC BY 4.0（以平台条款为准）")
        json.dump(meta,open(os.path.join(od,"meta.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        print("done",sid,meta["title"])
    return a.out
def build_catalog(out):
    cat=[]
    for od in sorted(glob.glob(os.path.join(out,"*","meta.json"))):
        d=os.path.dirname(od); sid=os.path.basename(d); m=json.load(open(od,encoding="utf-8"))
        m.setdefault("singer",singer_of(m.get("vocal","")))
        cat.append(dict(id=sid,title=m["title"],singer=m["singer"],theme=m["theme"],genre=m["genre"],mood=m["mood"],vocal=m["vocal"],
            duration=round((m.get("duration_ms") or 0)/1000),cover=f"/songs/{sid}/cover.jpg",mp3=f"/songs/{sid}/song.mp3",
            lyrics=open(os.path.join(d,"lyrics.txt"),encoding="utf-8").read()))
        if os.path.exists(os.path.join(d,"lyrics.json")): cat[-1]["timed"]=f"/songs/{sid}/lyrics.json"
        if m.get("video"): cat[-1]["video"]=m["video"]  # 预留：MV/演唱会视频 URL
    json.dump(cat,open(os.path.join(out,"catalog.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return cat

if __name__=="__main__":
    build_catalog(main())
