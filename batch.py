#!/usr/bin/env python3
"""全自动批量：榜单(网易云+酷狗) 1:1 对应题材/曲风/情绪 -> Grok 原创歌词+封面 -> Mureka -> 剪 AI 提示 -> 时间轴歌词.
用法: python batch.py [--max N] [--out out] [--min-balance 200]"""
import os, json, time, argparse, re, datetime, uuid, requests, base64, traceback
import charts, lyrics_align
from aitrim import strip_ai_notice, _dur
from generate import XAI, MUREKA, TEXT_MODEL, IMG_MODEL, MUREKA_MODEL, SINGERS, xh, mh, gen_cover
from pypinyin import lazy_pinyin

def balance():
    return requests.get(MUREKA+"/v1/account/billing",headers=mh(),timeout=30).json()["balance"]

def bad(text, it):
    for w in [it["title"]]+it["artists"]:
        w=re.sub(r"[\s（(].*$","",w.strip()) if w==it["title"] else w.strip()
        if len(w)>=2 and w in text: return w
    return None

SING_DESC="; ".join(f'{k}: {v["age"]}岁{v["gender"]}, {v["desc"]}' for k,v in SINGERS.items())
USED=set()
def write(it, counts, tries=4):
    prompt=(f"参考榜单歌曲：《{it['title']}》 — {'/'.join(it['artists'])}（来源 {it['src']} 第{it['rank']}名）。\n"
      "请判断这首歌的题材、曲风、情绪、速度和原唱性别，然后创作一首题材/曲风/情绪与之一一对应、但完全原创的中文歌曲。"
      "严禁使用原曲歌名、歌词句子、歌手名或任何真实艺人名；旋律只描述风格。"
      f"平台歌手：{SING_DESC}。请从中选最合适的演唱者（女声原唱选夏音禾或何曼伊，男声原唱选陈乐川；沧桑/古风/戏腔/怀旧/DJ情歌/伤感女声优先何曼伊），"
      f"当前已分配次数 {json.dumps(counts,ensure_ascii=False)}，在合适的前提下尽量均衡。"
      f"已有歌名(不可重复): {'、'.join(sorted(USED))}。"
      "歌词用[Verse]/[Pre-Chorus]/[Chorus]/[Bridge]/[Outro]结构, 每行不超过14字, 约2.5-3.5分钟, 不要括号注释。只输出JSON: "
      '{"ref_genre":"原曲曲风","theme":"","theme_en":"","genre":"","genre_en":"","mood":"","mood_en":"","tempo":"英文如 mid-tempo 90 bpm",'
      '"singer":"夏音禾|陈乐川|何曼伊","title":"原创中文歌名","title_en":"英文译名","lyrics":"","music_prompt":"英文曲风/乐器/编曲描述, 不含人名",'
      '"cover_prompt":"抽象艺术封面英文描述,无文字无人物"}')
    for _ in range(tries):
        try:
            import concurrent.futures as cf
            ex=cf.ThreadPoolExecutor(1); fu=ex.submit(requests.post,XAI+"/chat/completions",headers=xh(),json={"model":TEXT_MODEL,"messages":[{"role":"user","content":prompt}],"response_format":{"type":"json_object"}},timeout=(20,180))
            try: r=fu.result(timeout=300)
            finally: ex.shutdown(wait=False)
            r.raise_for_status(); d=json.loads(r.json()["choices"][0]["message"]["content"])
        except Exception as e: print("grok err",e); time.sleep(5); continue
        if d.get("singer") not in SINGERS: d["singer"]="陈乐川"
        b=bad(d["title"]+d["lyrics"],it)
        if d["title"] in USED: print("dup title",d["title"]); continue
        if not b: USED.add(d["title"]); return d
        print("filter reject:",d["title"],"hit:",b)
    raise RuntimeError("lyrics filter")

def balance_singer(d,counts):
    s=d["singer"]; g=SINGERS[s]["gender"]
    if counts[s] > min(counts.values())+3:
        alt=[k for k in SINGERS if k!=s and (SINGERS[k]["gender"]==g or g=="女声")]
        alt=[k for k in alt if SINGERS[k]["gender"]==g] or alt
        if alt: s=min(alt,key=lambda k:counts[k])
    return s

def mureka(lyrics,prompt):
    for k in range(30):
        r=requests.post(MUREKA+"/v1/song/generate",headers=mh(),json={"lyrics":lyrics,"model":MUREKA_MODEL,"prompt":prompt[:1000]},timeout=60)
        if r.status_code==200: break
        print("mureka submit",r.status_code,r.text[:200])
        if r.status_code in (429,503): time.sleep(20); continue
        raise RuntimeError(r.text)
    tid=r.json()["id"]; t0=time.time()
    while True:
        time.sleep(10)
        try: q=requests.get(f"{MUREKA}/v1/song/query/{tid}",headers=mh(),timeout=30).json()
        except Exception as e: print("poll",e); continue
        if q.get("status")=="succeeded": return tid,q
        if q.get("status") in("failed","timeouted","cancelled") or time.time()-t0>1800: raise RuntimeError(json.dumps(q,ensure_ascii=False)[:500])

def tail_check(mp3):
    """剪后复核：最后 8 秒不得含 AI 提示语音。"""
    import numpy as np, subprocess
    from faster_whisper import WhisperModel
    global _W
    try: _W
    except NameError: _W=WhisperModel("small",compute_type="int8")
    D=_dur(mp3)
    b=subprocess.run(["ffmpeg","-v","error","-ss",str(max(0,D-8)),"-i",mp3,"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout
    txt="".join(s.text for s in _W.transcribe(np.frombuffer(b,np.float32),language="zh",vad_filter=True)[0])
    return not re.search(r"AI|人工智能|由.{0,3}生成|内容由",txt,re.I), txt

def one(it,counts,out):
    d=write(it,counts); s=balance_singer(d,counts); sg=SINGERS[s]
    sid=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:4]; od=os.path.join(out,sid); os.makedirs(od)
    open(os.path.join(od,"lyrics.txt"),"w",encoding="utf-8").write(d["lyrics"])
    style=f'{d.get("music_prompt") or d["genre_en"]}, {d["mood_en"]}, {d["tempo"]}, {sg["voice"]}'
    tid,q=mureka(d["lyrics"],style)
    json.dump(q,open(os.path.join(od,"mureka.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    c=q["choices"][0]
    open(os.path.join(od,"song.mp3"),"wb").write(requests.get(c["url"],timeout=180).content)
    tr=strip_ai_notice(os.path.join(od,"song.mp3"))
    ok,tail=tail_check(os.path.join(od,"song.mp3"))
    if not ok:  # 兜底：再按更宽松条件剪一次
        print("tail still has notice:",tail); tr=strip_ai_notice(os.path.join(od,"song.mp3")) or tr; ok,tail=tail_check(os.path.join(od,"song.mp3"))
    dur=_dur(os.path.join(od,"song.mp3"))
    L=lyrics_align.from_mureka(c.get("lyrics_sections"),dur) if c.get("lyrics_sections") else []
    src="mureka"
    if not L:
        L=lyrics_align.align(os.path.join(od,"song.mp3"),d["lyrics"]); src="whisper"
    if L:
        L=lyrics_align.finalize(L,dur)
        json.dump(L,open(os.path.join(od,"lyrics.json"),"w",encoding="utf-8"),ensure_ascii=False); lyrics_align.write_lrc(L,os.path.join(od,"lyrics.lrc"))
    try: gen_cover(d.get("cover_prompt",d["theme_en"]),os.path.join(od,"cover.jpg"))
    except Exception as e: print("cover fail",e)
    meta={k:d.get(k) for k in("title","title_en","theme","theme_en","genre","genre_en","mood","mood_en","tempo")}
    meta.update(vocal=sg["gender"],singer=s,title_pinyin=" ".join(lazy_pinyin(d["title"])),style_prompt=style,duration_ms=int(dur*1000),
        mureka_task_id=tid,lyrics_timing=src,ai_trim=tr,tail_ok=ok,tail_asr=tail,
        reference={"chart":it["src"],"rank":it["rank"],"note":"仅参考题材/曲风/情绪，歌词旋律均为原创"},
        models={"lyrics":TEXT_MODEL,"cover":IMG_MODEL,"music":q.get("model",MUREKA_MODEL)},
        created=datetime.datetime.now().isoformat(),license="CC BY 4.0（以平台条款为准）")
    json.dump(meta,open(os.path.join(od,"meta.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    counts[s]+=1
    print(f"DONE {sid} 《{d['title']}》 {s} {dur:.0f}s timing={src} tail_ok={ok} ref={it['src']}#{it['rank']}",flush=True)
    return sid

def main():
    a=argparse.ArgumentParser(); a.add_argument("--max",type=int,default=999); a.add_argument("--out",default="out"); a.add_argument("--min-balance",type=int,default=200)
    a=a.parse_args()
    st=os.path.join(a.out,"batch_state.json")
    S=json.load(open(st)) if os.path.exists(st) else {"done":[],"counts":{k:0 for k in SINGERS}}
    import glob
    for f in glob.glob(os.path.join(a.out,"*","meta.json")): USED.add(json.load(open(f,encoding="utf-8"))["title"])
    ch=[x for x in charts.all_charts() if f'{x["src"]}#{x["rank"]}' not in S["done"]]
    n=0
    for it in ch:
        if n>=a.max: break
        b=balance(); print("balance",b,flush=True)
        if b<a.min_balance: print("balance exhausted"); break
        try: one(it,S["counts"],a.out); n+=1
        except Exception as e: traceback.print_exc()
        S["done"].append(f'{it["src"]}#{it["rank"]}'); json.dump(S,open(st,"w"),ensure_ascii=False)
    print("BATCH END",n,"balance",balance())
if __name__=="__main__": main()
