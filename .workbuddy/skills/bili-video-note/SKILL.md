---
name: bili-video-note
description: "把一个 B站视频变成一篇带截图和时间码的飞书云文档（同时留一份本地 docx）。自动下载 720P、抓取 B站 CC/AI 字幕、按语义分段、抽关键帧；由 WorkBuddy 在对话中完成「分段 / 摘要 / 选图」这段需要理解力的部分。产出《视频总结版本》+《视频全量文字版》两个一级标题，每个段落块带 [hh:mm:ss] 可跳回原视频。Use when: 用户给一个 bilibili.com/video/BV… 或 b23.tv 链接，并要求『阅读并生成文档』『看这个视频并出文档』『你去看这个B站视频并生成笔记』『总结这个B站视频』『转成飞书文档/笔记』『提取每分每秒的内容』；或提到『视频转文档』『B站笔记』『让 AI 看视频』。用户只要给链接 + 这类意图，就自动触发并执行全流程，不要反过来问用户要不要做。"
description_zh: "B站视频 → 飞书云文档：带时间码的完整文字版 + 分章节总结版 + 关键画面截图"
description_en: "Turn a Bilibili video into a Feishu cloud doc with screenshots and timestamps"
version: "1.1.0"
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

# ② 内容（这一步是你做的，没有命令可替代）：
#    读 subtitle.json → 写 .tmp/full_blocks.txt / chapters.json / images.json
#    （做法见 references/content-guide.md；AI 字幕无标点，必须断句+听写纠错）
#    可选：跑 scripts/draw_figure_0001.py 画一张结构图 → figures/
#    然后把三份文件组装成中间结构 content.json：
"$PY" "$REPO/scripts/make_content.py" --dir "data/000N.《标题》" \
    [--figure "figures/xxx.png|图说明文字"]

# ③ 渲染（确定性）：抽帧 → 本地 docx → 飞书云文档 → 链接写回 视频信息.md
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
```

四项任一缺失就先去 `references/env-setup.md` 补齐，**不要硬跑**。

## 产物规范（硬约束）

- **命名**：`data/0001.《视频标题》/`，编号四位递增，由扫 `data/` 最大编号 +1 得出
- **两个一级标题**：《视频总结版本》在前、《视频全量文字版》在后，两个都要配图
- **开头第一行**必须是可点击的原视频链接
- **每张图**的 caption 必须以 `📍 hh:mm:ss` 开头
- 云文档固定落在飞书「009.AI生成文档」文件夹，链接成功后写回 `视频信息.md`

## 八条质量红线

1. 抓不到字幕 → **直接报错中止**，不许降级给残缺成品
2. 文档开头必须有可点原链接，docx 和云文档都不能少
3. 总结每章必须有 `hh:mm:ss - hh:mm:ss` 时间区间
4. 每张图必须有时间码标注
5. 截图只取「文字给不出信息」的画面（界面、代码、图表），不均匀分布；口播头像帧不算
6. 自绘图必须有信息增量，宁缺毋滥（每篇 0–1 张）
7. docx 必须用真 Heading 样式 + 图片内嵌，不能是一堆加粗段落
8. 飞书写入失败必须明确报错；执行顺序保证 docx 先落地，飞书挂了用户手里也已有成品

## 踩过的坑（别再踩）

- **AI 字幕完全没有标点**：`ai-zh` 源是一整串汉字，全量文字版必须做断句 + 听写纠错（飞书≠非洲、豆包≠豆吧、Seedance≠CDance、AGENTS.md≠AMD）。这是每篇固定工作量
- **`media-insert` 只能追加到文档末尾**，图文穿插必须靠 `docs +create` 的 DocxXML：`<img path="@./frames/xx.jpg" caption="📍 …" width="800"/>`，路径相对视频文件夹
- **lark-cli 是 Windows 的 `.cmd`**，Python `subprocess` 调不了（WinError 2），必须 `node.exe + run.js` 直调（render_feishu.py 已封装好）
- 下载优先 `avc1`，避开 AV1——AV1 抽帧极慢
- 抽帧时 `-ss` 必须放在 `-i` 前面

## 换台电脑怎么办

git 只带得走代码和文档，带不走：`.secrets/` 凭据、`data/` 素材与成品、`.venv/`、`lark-cli`。新机上要重装依赖 + 重做两个授权（重跑 `references/env-setup.md` 的清单），lark-cli 由 WorkBuddy 重装 lark 套件补齐。仓库地址：`git@github.com:1040002437/006.-AI-B-.git`。

## 完整背景

- `references/content-guide.md` —— 第 ② 步的详细做法与 content.json 字段契约
- `references/env-setup.md` —— 环境搭建、凭据获取、换机清单
- 项目本体（含设计文档、执行计划、测试文档、新手文档）：`$REPO/docs/`
