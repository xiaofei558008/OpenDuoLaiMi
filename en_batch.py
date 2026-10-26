#!/usr/bin/env python3
"""英文歌批量（仅暂存到 out_en/，不发布）。歌手显示名集中在 EN_SINGERS，改名只改这里。"""
import os,json,datetime,uuid,requests,traceback,time
import lyrics_align
from aitrim import strip_ai_notice,_dur
from generate import XAI,TEXT_MODEL,IMG_MODEL,MUREKA_MODEL,xh,gen_cover
from batch import mureka,tail_check,balance
EN_SINGERS={
 "singer_en_f":{"display":"Sienna Varlow","slug":"sienna_varlow","gender":"female","age":27,"voice":"warm soulful female pop vocal, clear mid-range, breathy verses and powerful belted chorus, American English"},
 "singer_en_m":{"display":"Callen Ashgrove","slug":"callen_ashgrove","gender":"male","age":29,"voice":"smooth raspy male baritone vocal, intimate and warm, light falsetto on hooks, British English"},
}
PLAN=[("singer_en_f","emotional piano pop ballad, slow 70 bpm, heartbreak and self-worth"),
("singer_en_m","upbeat 80s-inspired synth-pop dance track, 118 bpm, late-night city romance"),
("singer_en_f","glossy dance-pop with four-on-the-floor beat, 124 bpm, confident empowerment"),
("singer_en_m","acoustic indie folk, fingerpicked guitar, 96 bpm, nostalgic road trip"),
("singer_en_f","modern country-pop, banjo and electric guitar, 104 bpm, small-town summer love"),
("singer_en_m","slow-jam contemporary R&B, 78 bpm, tender devotion"),
("singer_en_f","alt-pop with moody synths and trap hi-hats, 90 bpm, moving on after a breakup"),
("singer_en_m","anthemic pop-rock with big drums, 128 bpm, chasing dreams together"),
("singer_en_f","lo-fi bedroom pop, soft and dreamy, 85 bpm, quiet rainy-day love")]
USED=set()
def write(sk,spec):
    sg=EN_SINGERS[sk]
    p=(f"Write a completely ORIGINAL English song inspired only by current global pop chart trends. Style: {spec}. Singer: {sg['age']}-year-old {sg['gender']} vocalist. "
       "Do not quote or paraphrase any existing song lyrics or titles; do not mention any real artist, brand or person. "
       f"Avoid these titles: {', '.join(USED)}. Structure with [Verse]/[Pre-Chorus]/[Chorus]/[Bridge]/[Outro], about 3 minutes, lines under 10 words, no parenthetical notes. "
       'Output JSON only: {"title":"","theme_en":"","genre_en":"","mood_en":"","tempo":"","lyrics":"","music_prompt":"English instrumentation/arrangement description, no names","cover_prompt":"abstract album art description, no text no people"}')
    for _ in range(4):
        try:
            r=requests.post(XAI+"/chat/completions",headers=xh(),json={"model":TEXT_MODEL,"messages":[{"role":"user","content":p}],"response_format":{"type":"json_object"}},timeout=(20,240))
            r.raise_for_status(); d=json.loads(r.json()["choices"][0]["message"]["content"])
            if d["title"] not in USED: USED.add(d["title"]); return d
        except Exception as e: print("grok err",e); time.sleep(5)
    raise RuntimeError("grok")
def one(sk,spec,out="out_en"):
    sg=EN_SINGERS[sk]; d=write(sk,spec)
    sid=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:4]; od=os.path.join(out,sid); os.makedirs(od)
    open(os.path.join(od,"lyrics.txt"),"w").write(d["lyrics"])
    style=f'{d.get("music_prompt") or spec}, {d.get("mood_en","")}, {d.get("tempo","")}, {sg["voice"]}'
    tid,q=mureka(d["lyrics"],style); json.dump(q,open(os.path.join(od,"mureka.json"),"w"),indent=1)
    c=q["choices"][0]; mp=os.path.join(od,"song.mp3")
    open(mp,"wb").write(requests.get(c["url"],timeout=180).content)
    tr=strip_ai_notice(mp); ok,tail=tail_check(mp)
    if not ok: tr=strip_ai_notice(mp) or tr; ok,tail=tail_check(mp)
    dur=_dur(mp); L=lyrics_align.from_mureka(c.get("lyrics_sections"),dur) if c.get("lyrics_sections") else []; src="mureka"
    if not L: L=lyrics_align.align(mp,d["lyrics"]); src="whisper"
    if L:
        L=lyrics_align.finalize(L,dur); json.dump(L,open(os.path.join(od,"lyrics.json"),"w")); lyrics_align.write_lrc(L,os.path.join(od,"lyrics.lrc"))
    try: gen_cover(d.get("cover_prompt",d["theme_en"]),os.path.join(od,"cover.jpg"))
    except Exception as e: print("cover fail",e)
    meta=dict(title=d["title"],title_en=d["title"],theme=d.get("theme_en"),theme_en=d.get("theme_en"),genre=d.get("genre_en"),genre_en=d.get("genre_en"),mood=d.get("mood_en"),mood_en=d.get("mood_en"),tempo=d.get("tempo"),
      lang="en",vocal=sg["gender"],singer=sg["display"],singer_id=sk,style_prompt=style,duration_ms=int(dur*1000),mureka_task_id=tid,lyrics_timing=src,ai_trim=tr,tail_ok=ok,tail_asr=tail,
      reference={"note":"inspired by global pop trends only; original lyrics & melody"},models={"lyrics":TEXT_MODEL,"cover":IMG_MODEL,"music":q.get("model",MUREKA_MODEL)},
      created=datetime.datetime.now().isoformat(),license="CC BY 4.0")
    json.dump(meta,open(os.path.join(od,"meta.json"),"w"),indent=2)
    print(f"DONE {sid} {d['title']} {sk} {dur:.0f}s timing={src} tail_ok={ok}",flush=True)
if __name__=="__main__":
    i=0
    while i<len(PLAN) and balance()>=200:
        try: one(*PLAN[i])
        except Exception: traceback.print_exc()
        i+=1; print("balance",balance(),flush=True)
    print("EN END balance",balance())
