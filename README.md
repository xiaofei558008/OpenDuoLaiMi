# OpenDuoLaiMi · 开源 AI 音乐平台

所有歌曲由 AI 生成（歌词、封面、演唱），无版权负担、开放免费。站点：openduolaimi.com / opendoremi.com。

## 流程

1. **本地生成**（在本地电脑运行，服务器暂不联网）：`python generate.py --count 3 --out out`
   - 用 **Grok API**（`grok-4.7`）根据抽象主题写歌词；生成的文本经过 n-gram 过滤，避免与已有歌词雷同；不向模型提供任何原曲歌词、音频或真实歌手名。
   - 用 **Grok API**（`grok-imagine-image-2.0`）生成封面。
   - 用 **Mureka API**（`https://api.mureka.cn`，`/v1/song/generate` + `/v1/song/query/{id}`）生成演唱歌曲。
2. **剪掉结尾 AI 提示音**：`aitrim.py` 用 faster-whisper 识别结尾的“当前内容由AI生成”提示，用 ffmpeg 剪掉并淡出（generate.py 自动调用）。
3. **对齐歌词**：`lyrics_align.py` 优先使用 Mureka 返回的时间轴，否则用语音识别把歌词与音频对齐，供播放器逐句变色。
4. **上传服务器**：把 `out/` 中的歌曲目录和 `catalog.json` 打包，scp 到服务器，运行 `deploy/` 下的脚本放到 `/var/www/music-data/songs/`；播放器模板为 `site/tpl.html`。

## 环境

- Python 3.10+，`pip install -r requirements.txt`，系统需安装 `ffmpeg`
- 环境变量（见 `.env.example`）：`XAI_API_KEY`、`MUREKA_API_KEY`
- 可选：`XAI_TEXT_MODEL`、`XAI_IMAGE_MODEL`、`MUREKA_MODEL`、`MUREKA_BASE`

## 虚拟歌手（原创艺名）

| 艺名 | 声部 | 年龄 | 音色 |
|---|---|---|---|
| 夏音禾 | 女声 | 26 | 清亮、甜美 |
| 陈乐川 | 男声 | 23 | 清爽少年感 |
| 何曼伊 | 女声 | 38 | 低沉沧桑、有故事感（古风/抒情/怀旧优先） |

配置在 `generate.py` 的 `SINGERS` 中，提示词只写音色描述，不含任何真实歌手名。

## 许可

每首歌标注“AI 生成”，以 CC BY 4.0（以平台条款为准）发布。密钥、密码与生成的媒体文件不入库。

## 流媒体与发布（2026-10）
- 音频：每首歌同时发布 `song.opus`（libopus 96k VBR，约比 mp3 小 44%）与 `song.mp3`，播放器按 `canPlayType` 优先 Opus。
- MV：HLS（720p ~1.5Mbps / 480p ~0.75Mbps，2s 关键帧，4s 分片）+ `mv_small.mp4` faststart 兜底；播放器 Safari 原生 HLS，其他浏览器用本地 `site/hls.min.js`。
- opendoremi.com 对疑似中国大陆访客（时区/语言判断，无 IP 定位）显示可关闭横幅，指向 openduolaimi.com 同一首歌。
- 阿里云默认发布路线：`alipush.py`（国内直推，分块 tar + md5 + `deploy/alipush_apply.sh`），`alipull.sh` 仅作兜底。
