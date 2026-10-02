# 项目长期记忆（ curated ）

## 核心约定
- **产物目录**：`data/000N.《视频标题》/`，编号四位递增，由扫 `data/` 最大号 +1 得出
- **三个一级标题顺序固定**：《一图流》→《视频总结版本》→《视频全量文字版》（F14 一图流自 2026-10-02 起每篇必做）
- **无字幕即中止**：不是降级，而是明确报错（红线 1）
- **不做 ASR**：CC 字幕优先，无 CC 用 AI 字幕，都没有就停
- **AI 字幕无标点**：`ai-zh` 源是一整串汉字，每篇必须人工断句 + 听写纠错（固定工作量）

## 关键文件地图
- 规格与红线：`docs/设计文档.md`
- 进度看板：`docs/执行计划.md`
- 新手入口：`《新手刚拿到此项目最先阅读》.md`
- 工作流 Skill：`~/.workbuddy/skills/bili-video-note/`（用户级）+ `.workbuddy/skills/bili-video-note/`（仓库级，随 clone 走）

## 已踩的坑
- `lark-cli` 在 Windows 下是 `.cmd`，Python subprocess 会 WinError 2 → 改走 `node.exe + run.js`
- `media-insert` 只能追加到文档末尾 → 用 `docs +create` 的 DocxXML `<img path="@./x.jpg">` 内联上传
- 下载优先 `avc1` 避开 AV1，否则抽帧极慢
- 抽帧 `-ss` 必须放 `-i` 前面

## 仓库
- GitHub 公开仓库：`git@github.com:1040002437/006.-AI-B-.git`
- 凭据（`.secrets/`）、素材（`data/`）、环境（`.venv/`）均不进 git
