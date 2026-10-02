---
name: bili-video-note
description: "把一个 B站视频变成一篇带截图和时间码的飞书云文档（同时留一份本地 docx）。自动下载 720P、抓取 B站 CC/AI 字幕、按语义分段、抽关键帧；由 WorkBuddy 在对话中完成「分段 / 摘要 / 选图」这段需要理解力的部分。产出《视频总结版本》+《视频全量文字版》两个一级标题，每个段落块带 [hh:mm:ss] 可跳回原视频。Use when: 用户给一个 bilibili.com/video/BV… 或 b23.tv 链接，并要求『阅读并生成文档』『看这个视频并出文档』『你去看这个B站视频并生成笔记』『总结这个B站视频』『转成飞书文档/笔记』『提取每分每秒的内容』；或提到『视频转文档』『B站笔记』『让 AI 看视频』。用户只要给链接 + 这类意图，就自动触发并执行全流程，不要反过来问用户要不要做。"
description_zh: "B站视频 → 飞书云文档：带时间码的完整文字版 + 分章节总结版 + 关键画面截图"
description_en: "Turn a Bilibili video into a Feishu cloud doc with screenshots and timestamps"
version: "1.4.0"
display_name: "B站视频转飞书文档"
visibility: "private"
agent_created: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
metadata:
  requires:
    bins: ["python", "node"]
---

# B站视频转飞书云文档

输入一个 B站链接，输出一篇能直接在手机上读的飞书云文档（外加一份同名本地 docx 保底）。
本 Skill 把整套工作流固化下来：**你拿到链接后直接执行，不用再问「要不要做」**——除非触发下面的「必须停下」条件。

## 项目定位（代码在哪）

本 Skill 是**知识层 + 流程编排**，真正的脚本在另一个仓库里（已推到 GitHub）。换机或新会话时，先确认仓库已 clone 到本机：

```bash
REPO="C:/D/AI项目/006.让AI学会看B站视频"
```

**路径探测**：若上面的默认路径不存在，用 Glob 找：
`**/让AI学会看B站视频/scripts/run_all.py` 或 `**/006.-AI-B-*/scripts/run_all.py`。
找不到就问用户仓库 clone 在哪，不要凭空猜路径。

所有脚本都用 `ROOT = Path(__file__)` 定位根目录，**从任意 cwd 调用都有效**，产物一律落到 `$REPO/data/000N.《标题》/`。

```bash
PY="$REPO/.venv/Scripts/python.exe"
```

## 自动执行协议（重要）

用户给链接 + 「阅读并生成文档」类意图后，按下面三步一气呵成跑完，**不要中途停下汇报、不要问下一步**。只在以下情况停下并把报错原文给用户：

- 抓不到字幕（红线 1：SESSDATA 失效 / 该视频无 CC 也无 AI 字幕）→ 停下说明
- 依赖缺失或 lark-cli 没装 → 停下，给出 `references/env-setup.md` 的修复命令
- 飞书写入失败（但本地 docx 已落地）→ 停下说明，docx 仍可用
- 多 P 视频但链接没指定 `?p=N` → 停下让用户选哪一 P

其余一律自动推进，最后一条消息给：飞书云文档链接 + 本地 docx 路径 + 视频信息.md 路径。

## 三步流程

```bash
# ① 素材（确定性，秒级）：解析建目录 → 下载 720P → 抓字幕。
#    脚本会打印 "素材就绪：<绝对路径>"，记住这个 data/000N.《标题》 文件夹
"$PY" "$REPO/scripts/run_all.py" "<B站链接>"

#② 内容（这一步是你做的，没有命令可替代）：
#    读 subtitle.json → 写 .tmp/full_blocks.txt / chapters.json / images.json
#    （做法见 references/content-guide.md；AI 字幕无标点，必须断句+听写纠错）
#    ⚠ chapters.json 的每一章都要带 phrase（8-20 字），否则 make_content.py 会警告
#    ⚠ .tmp/ 是仓库根公共区，多视频共用 —— 写之前先清掉上一条视频的残留
#    组装成中间结构 content.json（figures 里可顺带传入 F12 文中补充图）：
"$PY" "$REPO/scripts/make_content.py" --dir "data/000N.《标题》" \
    [--figure "figures/xxx.png|图说明文字"]
#    必做：一图流 = 一张横向扁宽的「阶段流 + 动作盒」图，不是目录、不是竖版长图。
#    先看 data/000N.《标题》/figures/ 里有没有历史产物可复用版式，别从零发明。
#    再为当前视频设计专属结构（分几段、每段哪几个动作由你判断，不问用户），
#    写该篇专属脚本（复制 draw_onepager_0002.py 再改，它带像素级自动折行），产出 figures/一图流.png。
#    版式：顶部标题+副标题 / 左侧阶段标签含时间码 / 右侧动作盒横排+横向箭头 /
#          阶段间竖向箭头递进 / 末段可通栏；约 2000x900~1200 扁宽。
#    动作盒= 主文字（你提炼的动作短句）+ 副文字；并记录它对应哪几章 chapters[]，
#    启动即断言并集==range(len(chapters))，漏章或重复归入就拒绝出图。
#    盒宽按可用宽度自适应、标签宽按像素自适应（不溢出不裁切）；--preview 出 1000px 缩略图自检。
"$PY" "$REPO/scripts/draw_onepager_0001.py" --dir "data/000N.《标题》"   # 建设类视频（4阶段）的版式样例
"$PY" "$REPO/scripts/draw_onepager_0002.py" --dir "data/000N.《标题》"   # 评测类视频（6阶段）的版式样例
"$PY" "$REPO/scripts/draw_onepager_0003.py" --dir "data/000N.《标题》"   # 概念科普类视频（5阶段单线递进）的版式样例
#    专属脚本命名沿用 draw_onepager_<三位编号>.py。0002 版已加按像素自动折行（wrap），
#    主副文字都不会溢出盒宽，长句可放心写——**新写脚本直接复制 0002 那份**
#    ⚠ 单节点阶段的盒高偏小时，5 行副文字会溢出盒底（0003 踩过）→ 要么压缩到 4 行，
#      要么把 box_layout() 里 {1: 150} 改成 190
#    可选：再画 F12 文中补充图（参考 draw_onepager_0001.py 的 PIL 画法），需再跑 make_content.py 把它追加进 figures

# ③ 渲染（确定性）：抽帧 → 本地 docx → 飞书云文档 → 链接写回 视频信息.md
#    缺一图流会直接报错并中止（不再自动跑通用绘图）——请先跑②里的该篇专属脚本。
"$PY" "$REPO/scripts/run_all.py" --dir "data/000N.《标题》" --full
```

变体：`--force`（同一链接重跑覆盖）、`--no-download`（只要字幕省时间）。

**衔接要点**：② 结束**必须**先跑 `make_content.py` 生成 `content.json`，③ 的 `--full` 才不会因缺 `content.json` 而中止。

## 开工前体检（第一次或换机后跑一次）

```bash
[ ] ls "$REPO/.secrets/sessdata.txt"      # B站登录态，过期会报错（红线 1）
[ ] ls "$REPO/.secrets/feishu_folder.txt"  # 飞书目标文件夹 token
[ ] "$PY" -c "import yt_dlp, PIL, docx, requests; print('依赖 OK')"
[ ] ls ~/.workbuddy/binaries/node/cli-connector-packages/node_modules/@larksuite/cli/scripts/run.js
[ ] ls "$REPO/.venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg.exe"  # 见下方 ffmpeg 坑
```

四项任一缺失就先去 `references/env-setup.md` 补齐，**不要硬跑**。

**ffmpeg 不在 PATH**（Windows 常见）：venv 里 `imageio_ffmpeg` 自带了二进制，`prepare.py` 与 `extract_frames.py` 用 `imageio_ffmpeg.get_ffmpeg_exe()` 直调不受影响，但 **`download_video.py` 合并音视频流走的是 yt-dlp 自己的 PATH 查找**，找不到就报 `You have requested merging of multiple formats but ffmpeg is not installed`。修法：把 `ffmpeg-win-x86_64-v7.1.exe` 复制一份成 `ffmpeg.exe`，然后**在所有调 `run_all.py` 的命令前临时注入 PATH**：

```bash
FFDIR="$REPO/.venv/Lib/site-packages/imageio_ffmpeg/binaries"
PATH="$FFDIR:$PATH" "$PY" "$REPO/scripts/run_all.py" "..."
```

## 产物规范（硬约束）

- **命名**：`data/0001.《视频标题》/`，编号四位递增，由扫 `data/` 最大编号 +1 得出
- **三个一级标题，顺序固定**：《一图流》（最前）→《视频总结版本》→《视频全量文字版》；《一图流》必须是「一级标题『一图流』+ **一张横向扁宽的阶段流图**」，节内无文字（F14，每篇必做；分几段、每段哪几个动作由我按内容自行判断）
- **开头第一行**必须是可点击的原视频链接
- **每张图**的 caption 必须以 `📍 hh:mm:ss` 开头。**一图流除外**——它不是某时刻的截图，图注不加 `📍`
- 云文档固定落在飞书「009.AI生成文档」文件夹，链接成功后写回 `视频信息.md`；**同一视频重跑会整篇覆盖更新同一篇（首次 `+create` 新建，之后 `+update --command overwrite`），不会生成多篇同名文档**；飞书自带版本历史可回滚

## 质量红线（含一图流）

1. 抓不到字幕 → **直接报错中止**，不许降级给残缺成品
2. 文档开头必须有可点原链接，docx 和云文档都不能少
3. 总结每章必须有 `hh:mm:ss - hh:mm:ss` 时间区间
4. 每张图必须有时间码标注
5. 截图只取「文字给不出信息」的画面（界面、代码、图表），不均匀分布；口播头像帧不算
6. **一图流（F14）每篇必做**：文档最前必须有 H1「一图流」+ **恰好一张横向扁宽的阶段流图**（顶部标题+副标题 / 左侧阶段标签含时间码 / 右侧动作盒横排+横向箭头 / 阶段间竖向箭头递进）。结构由我按该视频内容**自行决策，不套模板、不向用户确认**。硬要求：① 每个动作盒的 `chapters[]` 并集**不重不漏覆盖全部章节**，同一章的多个动作合并进一个盒内多行；② 盒内 = 主文字（提炼的动作短句）+ 副文字；③ 盒宽按可用宽度自适应、标签宽按像素自适应，**不得溢出或裁切**；④ **不要画竖版长图**；⑤ 缩到 1000px 宽后仍可读。**画之前先扫一眼 `figures/` 有无可复用版式**——0001 的三次返工就是重画时忽略了已存在的图
7. F12 自绘图（文中补充图）**可选 0–1 张**，必须有信息增量、宁缺毋滥；全片脉络已移交 F14，这里不重复画总脉络
8. docx 必须用真 Heading 样式 + 图片内嵌，不能是一堆加粗段落
9. 飞书写入失败必须明确报错；执行顺序保证 docx 先落地，飞书挂了用户手里也已有成品

## 踩过的坑（别再踩）

- **AI 字幕完全没有标点**：`ai-zh` 源是一整串汉字，全量文字版必须做断句 + 听写纠错（飞书≠非洲、豆包≠豆吧、Seedance≠CDance、AGENTS.md≠AMD）。这是每篇固定工作量
- **`media-insert` 只能追加到文档末尾**，图文穿插必须靠 `docs +create` 的 DocxXML：`<img path="@./frames/xx.jpg" caption="📍 …" width="800"/>`，路径相对视频文件夹
- **lark-cli 是 Windows 的 `.cmd`**，Python `subprocess` 调不了（WinError 2），必须 `node.exe + run.js` 直调（render_feishu.py 已封装好）
- 下载优先 `avc1`，避开 AV1——AV1 抽帧极慢
- 抽帧时 `-ss` 必须放在 `-i` 前面
- **ffmpeg 抽出的 JPEG 不能直接喂给 python-docx**：ffmpeg 写的文件头带 `avc1` 私有 APP1 标记（`ff d8 ff e0 ... avc1`）而非标准 Exif，PIL 能读但 `add_picture` 的嗅探器认不出，报 `UnrecognizedImageError`。已在 `extract_frames.py` 里加 `normalize()` 用 PIL 重存一遍解决；若换机器后旧帧报错，重跑 `extract_frames.py --force` 即可。**下游三个脚本（抽帧/渲染 docx/渲染飞书）都走 PATH 里的 ffmpeg，缺 ffmpeg 时三个都会失败**
- **`make_content.py` 会重建 `figures/`**，抽帧也在其后——所以别在 `make_content.py` 之前手工往 `frames/` 放图
- **`.tmp/` 是仓库根的公共临时区，不是 per-video**：不同视频的 `full_blocks.txt` / `chapters.json` / `images.json` 会互相覆盖。处理下一条视频前先清空（或确保本次写入时机正确）
- **`phrase` 字段必填**：8–20 字的汉字长度校验，斜杠和空格都算字符，超了就退回重写。缺这个字段 `make_content.py` 会警告，一图流节点无从生成
- **AI 字幕的 PPT 切页比口播晚**（0003 踩过）：按口播时间点抽帧会抽到上一页的重复画面。**PPT 教学类视频必须先抽 1 帧/10~20 秒拼成缩略图核对**，发现重复就把时间点往后挪几秒再抽
- **`render_docx.py` 报 `PermissionError` = docx 被占用**：上一次生成的文件还开着（Word / 预览面板 / 资源管理器缩略图）。关掉后重跑 `--full` 即可，**已生成的帧不用重抽**（extract_frames 会跳过已存在的文件）
- **反复重渲染会踩瞬时文件锁**：Windows 上 antivirus / 索引服务可能短暂占用 docx。遇到就等几秒重跑一次，别改脚本

## 换台电脑怎么办

git 只带得走代码和文档，带不走：`.secrets/` 凭据、`data/` 素材与成品、`.venv/`、`lark-cli`。新机上要重装依赖 + 重做两个授权（重跑 `references/env-setup.md` 的清单），lark-cli 由 WorkBuddy 重装 lark 套件补齐。仓库地址：`git@github.com:1040002437/006.-AI-B-.git`。

## 完整背景

- `references/content-guide.md` —— 第 ② 步的详细做法与 content.json 字段契约
- `references/env-setup.md` —— 环境搭建、凭据获取、换机清单
- 项目本体（含设计文档、执行计划、测试文档、新手文档）：`$REPO/docs/`
