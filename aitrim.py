"""检测并剪掉 Mureka 音频末尾的语音提示「当前内容由AI生成」。检测不到则保持原样。"""
import subprocess, re, os, shutil, json

def _dur(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],capture_output=True,text=True).stdout)

def _silences(p, noise="-35dB", d=0.4):
    err = subprocess.run(["ffmpeg","-i",p,"-af",f"silencedetect=n={noise}:d={d}","-f","null","-"],capture_output=True,text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(st, en + [None]*(len(st)-len(en))))

def _asr_has_notice(p, start):
    """可选：用 faster-whisper 确认片段内容；没装就返回 None。"""
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    b = subprocess.run(["ffmpeg","-v","error","-ss",str(start),"-i",p,"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout
    m = WhisperModel("small", compute_type="int8")
    txt = "".join(s.text for s in m.transcribe(np.frombuffer(b, np.float32), language="zh")[0])
    return bool(re.search(r"AI|生成|生成", txt)), txt

def find_notice(p):
    """返回 (切点秒, 提示开始秒) 或 None。特征：结尾 ≥2s 静音 + 0.8~4s 语音 + 结尾。"""
    D = _dur(p); sil = _silences(p)
    for i in range(len(sil)-1, -1, -1):
        s, e = sil[i]
        if e is None or e < D - 8: continue
        if e - s < 2.0: continue
        nxt = sil[i+1][0] if i+1 < len(sil) else D
        if 0.8 <= nxt - e <= 4.0 and D - e <= 6.0:
            return s, e
    return None

def strip_ai_notice(p, keep_orig=True, fade=0.3, bitrate="192k"):
    f = find_notice(p)
    if not f: return None
    cut, nstart = f
    chk = _asr_has_notice(p, nstart - 0.3)
    if chk is not None and not chk[0]: return None
    end = cut + fade
    orig = p[:-4] + ".orig.mp3"
    if keep_orig and not os.path.exists(orig): shutil.copy2(p, orig)
    src = orig if os.path.exists(orig) else p
    tmp = p + ".tmp.mp3"
    subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-t",f"{end:.3f}","-af",f"afade=t=out:st={end-fade:.3f}:d={fade}",
                    "-c:a","libmp3lame","-b:a",bitrate,"-map_metadata","0",tmp], check=True)
    os.replace(tmp, p)
    return {"cut_from": round(end,3), "notice_start": round(nstart,3), "new_duration": round(_dur(p),3)}

if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]: print(p, strip_ai_notice(p))
