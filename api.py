#!/usr/bin/env python3
"""生成 App/小程序用 /api/v1/catalog.json（两站各一份）-> pub/api/{duo,dor}/v1/catalog.json"""
import json, os, datetime, hashlib
PUB="pub"
SITES={"duo":("openduolaimi.com","zh"),"dor":("opendoremi.com","en")}
AVK={'Callen Ashgrove':'callen_ashgrove','Sienna Varlow':'sienna_varlow','夏音禾':'xiayinhe','陈乐川':'chenlechuan','何曼伊':'hemanyi'}
PY={'夏音禾':'Xia Yinhe','陈乐川':'Chen Lechuan','何曼伊':'He Manyi'}
def build(cat):
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(microsecond=0).isoformat()
    ver=hashlib.sha1(json.dumps(cat,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]
    for k,(dom,lang) in SITES.items():
        B=f"https://{dom}"; songs=[]
        for c in cat:
            i=c["id"]; d=f"{PUB}/songs/{i}"; S=f"{B}/songs/{i}"
            meta=json.load(open(f"{d}/meta.json",encoding="utf-8")) if os.path.exists(f"{d}/meta.json") else {}
            en=lang=="en"
            s=c["singer"]
            lj=f"{d}/lyrics.json"
            if os.path.exists(lj):
                L=json.load(open(lj,encoding="utf-8"))
                json.dump({"lines":[{"t":round(x["start"],2),"text":x["text"]} for x in L if x.get("text")]},open(f"{d}/lyrics_v1.json","w",encoding="utf-8"),ensure_ascii=False)
            songs.append({"id":i,
             "title":(c.get("title_en") or c["title"]) if en else c["title"],
             "title_original":c["title"],
             "singer":PY.get(s,s) if en else s,
             "singer_id":AVK.get(s),
             "album":None,
             "singer_avatar":f"{B}/songs/singers/{AVK[s]}.webp" if s in AVK else None,
             "singer_avatar_small":f"{B}/songs/singers/{AVK[s]}-96.webp" if s in AVK else None,
             "cover":f"{S}/cover.jpg",
             "opus_url":f"{S}/song.opus" if os.path.exists(f"{d}/song.opus") else None,
             "mp3_url":f"{S}/song.mp3",
             "duration_sec":c.get("duration"),
             "lyrics_url":f"{S}/lyrics_v1.json" if os.path.exists(f"{d}/lyrics.json") else None,
             "lyrics_lrc_url":f"{S}/lyrics.lrc" if os.path.exists(f"{d}/lyrics.lrc") else None,
             "mv_hls_url":f"{S}/hls/master.m3u8" if os.path.exists(f"{d}/hls/master.m3u8") else None,
             "genre":(c.get("genre_en") or c.get("genre")) if en else c.get("genre"),
             "published_at":(c.get("created") or "")[:19]+"+08:00" if c.get("created") else None})
        o=f"{PUB}/api/{k}/v1"; os.makedirs(o,exist_ok=True)
        json.dump({"version":datetime.date.today().isoformat()+"."+ver,"updated_at":now,"site":dom,"lang":lang,"count":len(songs),"songs":songs},
                  open(f"{o}/catalog.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
if __name__=="__main__":
    build(json.load(open(f"{PUB}/songs/catalog.json",encoding="utf-8")))
