"""生成带时间戳的歌词 lyrics.json：[{start,end,text,sec,words:[{start,end,text}]}]（秒）。
优先用 Mureka 返回的 lyrics_sections；否则用 faster-whisper 字级时间戳对齐 lyrics.txt。"""
import json, re, subprocess, difflib

def from_mureka(sections, max_end=None):
    out = []
    for s in sections or []:
        for l in s.get("lines") or []:
            st, en = l["start"]/1000, l["end"]/1000
            if max_end and st >= max_end: continue
            w = [{"start": x["start"]/1000, "end": x["end"]/1000, "text": x["text"]} for x in (l.get("words") or [])]
            out.append({"start": st, "end": min(en, max_end or en), "text": l["text"], "sec": s.get("section_type", ""), "words": w})
    return out

def _load(p):
    import numpy as np
    b = subprocess.run(["ffmpeg","-v","error","-i",p,"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout
    return np.frombuffer(b, np.float32)

_M = None
def align(mp3, lyrics_txt):
    global _M
    from faster_whisper import WhisperModel
    try:
        import opencc; cc = opencc.OpenCC("t2s").convert
    except Exception: cc = lambda x: x
    if _M is None: _M = WhisperModel("medium", compute_type="int8")  # small 版在歌声上系统性偏早 0.4s、最多 1.5s
    lines, sec = [], ""
    for l in lyrics_txt.splitlines():
        t = l.strip()
        if not t: continue
        m = re.fullmatch(r"\[(.*)\]", t)
        if m: sec = m.group(1); continue
        lines.append({"text": t, "sec": sec})
    segs, _ = _M.transcribe(_load(mp3), language="zh", word_timestamps=True, initial_prompt="，".join(x["text"] for x in lines[:8]))
    hc, ht = [], []   # 识别出的每个字及其时间
    for s in segs:
        if re.search(r"[A-Za-z]{4,}", s.text) and s.end - s.start > 6: continue  # 前奏幻觉
        for w in s.words or []:
            chars = [c for c in cc(w.word) if not c.isspace() and c not in "，。、！？,.!?"]
            n = len(chars)
            for k, c in enumerate(chars):
                hc.append(c); ht.append((w.start + (w.end-w.start)*k/max(n,1), w.start + (w.end-w.start)*(k+1)/max(n,1)))
    lc, owner = [], []
    for i, l in enumerate(lines):
        for c in l["text"]:
            if not c.isspace() and c not in "，。、！？,.!?": lc.append(c); owner.append(i)
    tm = [None]*len(lc)
    for a, b, n in difflib.SequenceMatcher(None, lc, hc, autojunk=False).get_matching_blocks():
        for k in range(n): tm[a+k] = ht[b+k]
    # 插值未匹配的字
    known = [i for i, t in enumerate(tm) if t]
    if not known: return []
    for i in range(len(tm)):
        if tm[i]: continue
        p = max([k for k in known if k < i], default=None); q = min([k for k in known if k > i], default=None)
        if p is None: tm[i] = (max(0, tm[q][0]-0.3*(q-i)),)*2
        elif q is None: tm[i] = (tm[p][1]+0.3*(i-p),)*2
        else:
            r = (i-p)/(q-p); x = tm[p][1] + (tm[q][0]-tm[p][1])*r; tm[i] = (x, x+0.25)
    out = []
    for i, l in enumerate(lines):
        idx = [k for k, o in enumerate(owner) if o == i]
        if not idx: continue
        words = [{"start": round(tm[k][0],2), "end": round(max(tm[k][1], tm[k][0]+0.1),2), "text": lc[k]} for k in idx]
        # 保持单调
        for j in range(1, len(words)):
            if words[j]["start"] < words[j-1]["start"]: words[j]["start"] = words[j-1]["start"]
        out.append({"start": words[0]["start"], "end": words[-1]["end"], "text": l["text"], "sec": l["sec"], "words": words})
    for j in range(1, len(out)):
        if out[j]["start"] < out[j-1]["start"]: out[j]["start"] = out[j-1]["end"]
    return out

def finalize(L, max_end=None):
    """统一修正：行按时间排序、行尾不越过下一行开头、字的结束时间延伸到下一个字开头（卡拉OK平滑填色）。"""
    L = sorted([l for l in L if l.get("text")], key=lambda l: l["start"])
    for j, l in enumerate(L):
        nxt = L[j+1]["start"] if j+1 < len(L) else (max_end or l["end"])
        l["end"] = round(max(l["start"]+0.3, min(l["end"], nxt)), 3)
        w = l.get("words") or []
        for k, x in enumerate(w):
            ne = w[k+1]["start"] if k+1 < len(w) else l["end"]
            x["end"] = round(max(x["start"]+0.05, min(max(x["end"], ne), l["end"])), 3)
    return L

def write_lrc(lines, path):
    f = lambda t: f"[{int(t//60):02d}:{t%60:05.2f}]"
    open(path, "w", encoding="utf-8").write("\n".join(f(l["start"]) + l["text"] for l in lines) + "\n")

if __name__ == "__main__":
    import sys, os
    for d in sys.argv[1:]:
        L = align(os.path.join(d,"song.mp3"), open(os.path.join(d,"lyrics.txt"),encoding="utf-8").read())
        json.dump(L, open(os.path.join(d,"lyrics.json"),"w",encoding="utf-8"), ensure_ascii=False)
        write_lrc(L, os.path.join(d,"lyrics.lrc"))
        print(d, len(L)); print(open(os.path.join(d,"lyrics.lrc"),encoding="utf-8").read()[:900])
