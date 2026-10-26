"""抓取网易云(热歌/飙升/新歌)与酷狗(TOP500/飙升)榜单：仅取歌名+歌手，用于提炼题材/曲风/情绪。"""
import requests, re, json
UA={"User-Agent":"Mozilla/5.0"}
def netease(pid,name):
    r=requests.get(f"https://music.163.com/api/playlist/detail?id={pid}",headers={**UA,"Referer":"https://music.163.com/"},timeout=20).json()
    return [{"title":t["name"],"artists":[a["name"] for a in t["artists"]],"src":"网易云"+name,"rank":i+1} for i,t in enumerate(r["result"]["tracks"])]
def kugou(rid,name,pages=3):
    out=[]
    for p in range(1,pages+1):
        t=requests.get(f"https://www.kugou.com/yy/rank/home/{p}-{rid}.html?from=rank",headers=UA,timeout=20).content.decode("utf-8","ignore")
        seen=set()
        for x in re.findall(r'title="([^"]+ - [^"]+)"',t):
            if x.endswith("...") or x in seen: continue
            seen.add(x); a,s=x.split(" - ",1)
            out.append({"title":s.strip(),"artists":re.split(r"[、,，&/ ]+",a.strip()),"src":"酷狗"+name,"rank":len(out)+1})
    return out
def norm(t): return re.sub(r"[\s（(].*$","",t).lower()
def all_charts():
    lists=[]
    for f in (lambda:netease(3778678,"热歌榜"),lambda:kugou(8888,"TOP500"),lambda:netease(19723756,"飙升榜"),lambda:kugou(6666,"飙升榜"),lambda:netease(3779629,"新歌榜")):
        try: lists.append(f())
        except Exception as e: print("chart fail",e); lists.append([])
    out,seen=[],set()
    for i in range(max(map(len,lists))):
        for L in lists:
            if i<len(L) and norm(L[i]["title"]) not in seen:
                seen.add(norm(L[i]["title"])); out.append(L[i])
    return out
if __name__=="__main__":
    c=all_charts(); print(len(c)); [print(x) for x in c[:12]]
