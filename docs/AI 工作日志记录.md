# AI 工作日志记录

> 每个 session 结束前追加一条：**做了什么 / 关键结论 / 下次从哪继续**。
> 只记有长期价值的事，不记临时报错与搜索过程。

---

## 2026-10-02 · Session 1 · 项目治理初始化

**做了什么**

- `git init -b master`，设 `core.quotepath false`（中文文件名正常显示）
- 建 `AGENTS.md`（项目说明书原文 + 文档地图一节）
- 建 `docs/` 四份固定文档；补 `.gitignore`（Python/Node/密钥）
- 首个 commit `45046c0`

**关键结论**

- 用户随后要求四份 md **清空为 0 字节空模板**，内容由他后续逐条给 → commit `27735ea`
- **重要偏好**：此项目不要替用户预判文档内容批量填充，等给内容再写

**下次从哪继续**

- 等用户给设计文档与执行计划的内容

---

## 2026-10-02 · Session 2 · 需求调研 + 现成工具评估 + 下载验证

**做了什么**

- 逐条确认需求：输入 B站链接 → 输出飞书云文档（全量文字版 + 章节总结 + 截图时间码）
- 评估现成工具：通义听悟、飞书妙记、Ai好记、BibiGPT
- 实测下载：BV1FGeG6pENE（35:35 / 720P / 87MB）约 15 秒下完
- 验证抽帧：`ffmpeg -ss 00:05:00` 精确取帧成功

**关键结论**

- **通义听悟、飞书妙记都不支持直接贴 B站链接**（合规），必须下载后上传 —— 这是所有大厂工具共同的缺口，也正是本项目的立足点
- 飞书妙记免费档只有「语音转文字 300 分钟/月」，**「智能纪要」0 篇需付费**
- 免费额度和"带截图"能力是**反着来的**：最免费的没有截图，有截图的最不免费
- 用户画像修正：**只看长视频、一次 4-5 个、不批量** → 现成工具额度不够，自建更划算
- 环境全程纯 pip（yt-dlp + imageio-ffmpeg），**没装任何系统软件**，验证了换机可跑

**下次从哪继续**

- 解决文字来源：先试抓 B站官方 AI 字幕，抓不到再谈 ASR

---

## 2026-10-02 · Session 3 · 打通 AI 字幕抓取（ASR 环节省掉）

**做了什么**

- 用户指出播放器里有「中文(AI)」字幕，要求直接抓
- 沉淀脚本 `scripts/fetch_subtitle.py`，产出 `.srt` + `.subtitle.json`
- commit `d064a15`

**关键结论（踩坑，务必记住）**

1. **AI 字幕必须「wbi 签名 + SESSDATA 登录态」双满足**
   - 只带 cookie 调 `x/player/v2` → 列表有 `ai-zh` 但 `subtitle_url` 是**空字符串**
   - 带 cookie 调 `x/player/wbi/v2`（wbi 签名）→ 才返回真实地址 `aisubtitle.hdslb.com/...?auth_key=...`
2. **HTTP 412 风控**：`x/web-interface/view` 曾返回 HTML 拦截页。解决 = 会话补设备指纹 cookie `buvid3`(uuid+infoc) + `b_nut`(时间戳)，加 `Referer`/`Origin`/`Accept-Language` 头；脚本内 `get_json` 三次退避重试
3. **wbi 签名算法**：nav 接口取 `wbi_img.img_url`/`sub_url` → 取文件名（去扩展名）拼接为 key → 参数加 `wts` 后按 key 排序 urlencode → `w_rid = md5(qs + key)`
4. 结果：**833 段字幕、覆盖 35.6 分钟**，成本 0、耗时秒级
5. 凭证存 `.secrets/sessdata.txt`，`.gitignore` 已加 `.secrets/ cookies.txt *.cookie` 与 `data/ *.mp4`，绝不入库

**下次从哪继续**

- 实现 F1–F3（链接解析、建目录、下载），把「给链接 → 素材文件夹」串成一条命令

---

## 2026-10-02 · Session 4 · 需求对齐 + 设计文档

**做了什么**

- 对齐目录规范：`data/0001.《视频标题》/` 自包含（视频 + 字幕 + 原链接 + 报告 + 截图）
- 写入 `docs/设计文档.md`（10 节：目标、为什么自造、流程、目录规范、功能清单 F1–F10、技术选型、明确不做、质量红线 5 条、里程碑、待定）
- commit `77e6c72`

**关键结论（用户拍板）**

- 编号 **4 位 `0001`**（候选 3/4/6 位里选的）
- 产物（docx + frames/）**放该视频文件夹内**，不另建 outputs/
- **无 AI 字幕 → 直接报错中止**，不自动降级 ASR
- 画质**固定 720P**
- 视频名清洗非法字符 + 60 字截断；重复 BV 号提示已存在不新建；分 P 只处理指定 P、多 P 先提示
- 旧文件（`data/` 根目录散着的 mp4/srt/json）**暂缓处理，用户说"等会"再定**

**下次从哪继续**

- 用户点头后实现 F1–F3：`scripts/add_video.py` 一条命令完成「解析 → 建 0001 目录 → 下载 720P → 抓字幕 → 写视频信息.md」
- 旧文件归档方案待用户定

---

## 2026-10-02 · Session 5 · 飞书写入打通（从"手动建应用"到实测成功）

**做了什么**

- 讨论技术栈细节并拍板：段落块时间戳（约 60s/块）、总结版与全量版都配图、CC 字幕优先、长视频自动分块
- 定稿输出架构：**中间内容结构 + 双渲染**（飞书云文档为主 + 本地 docx 兜底），取消 `笔记.md`
- 新增 F13 自绘结构图（`figures/`，思维导图/流程图/对比表/时间轴，实用导向）
- 排查 WorkBuddy 飞书连接器"点了转圈"：日志显示连接调用 27ms 空转，连接器未安装（`enabled: []`）
- 安装市场套件 `lark-unified`（飞书/Lark 全能套件），拿到官方 `lark-cli` v1.0.97
- 完成设备码授权 + 用户身份 OAuth，成功创建云文档并插入带时间码的图片

**关键结论**

- 飞书写入**走用户身份（user）而非 bot**：文档直接落在个人云空间，省掉"应用建文档再授权给个人"那一步。bot 身份会报 `app_scope_not_applied`（99991672）
- 实测验证文档：https://my.feishu.cn/docx/ScJydJ36TozW60xBBRzc9ExKnef （H1/H2 层级、正文、图片 + `📍 00:05:00` caption 全部正常）
- 用户账号：张秩伟；应用 App ID：`cli_aa358d94c978dbc1`

**踩坑（重要，别重踩）**

1. **WinError 2**：`lark-cli` 在 Windows 是 `.cmd`，Python `subprocess` 无法执行。修法：用 `node.exe` + `node_modules/@larksuite/cli/scripts/run.js` 调用。**已修进 skill**（`~/.workbuddy/skills/lark-unified/scripts/lark_setup.py` 新增 `lark_cli_base_cmd()`）
2. **授权必须同流程轮询**：只 `--print-url-only` 拿 URL 而不发起 `--device-code` 轮询，用户点了也拿不到凭证（浪费了两次授权）
3. **`--file` / `--content @file` 只认 cwd 相对路径**，绝对路径被拒
4. WorkBuddy 市场里的"飞书连接器"卡片在未安装时点「连接」会空转转圈，不是用户操作问题

**下次从哪继续**

- F10 渲染器实现：把中间内容结构渲染成飞书 XML（`<title>/<h1>/<h2>/<p>/<img>`）并调用 `lark-cli docs +create` / `+media-insert`
- 先把 M1 的本地链路跑通：读字幕 → 分段总结 → 选截图点 → 抽帧 → 出 docx（用已抓好的豆包视频 833 段字幕）
- 旧文件归档方案仍待用户定

---

## Session 6（2026-10-02）· 全流程完工，首篇端到端交付

**做了什么（S05–S21 全部完成）**

- P1 素材链路脚本化：`init_video.py`（解析/编号/建目录/写信息，含重复 BV 识别与多 P 提示）、`download_video.py`（720P 优先 avc1 避 AV1）、`prepare.py`（一条命令 F1–F4，字幕统计回写 `视频信息.md`）
- P2 内容生成（0001 首篇）：833 段 AI 字幕**无标点** → 全文断句+听写纠错（飞书/豆包/Seedance/AGENTS.md 等错词修正）→ 42 个 60 秒段落块 + 12 章总结 + 12 张截图选点（逐张看图核对，8 模块可视化帧从 06:12 修正到 06:25）+ 1 张 PIL 自绘「视频脉络」图
- P3/P4 渲染：`render_docx.py`（真 Heading×14、图内嵌×13、eastasia 字体、可点原链接）、`render_feishu.py`（**关键突破：DocxXML `<img path="@./xx.jpg" caption="…"/>` 建文档时内联上传本地图**，绕开 media-insert 只能追加末尾的限制）、链接写回 `视频信息.md`
- P5：`run_all.py` 一键串联（素材一条命令；内容阶段有意停在对话；`--full` 渲染一条命令）、`docs/测试文档.md` 8 条红线验收

**成果物**

- 飞书云文档：https://my.feishu.cn/docx/Zh3XdGcOjoXHoyxkmh0c8oD6nzb（13 图带 📍 时间码、42 块时间戳、开头原链接）
- 本地 docx：`data/0001.《…》/0001.《…》.docx`（结构与云文档同源）

**踩坑（新）**

1. `media-insert` 只能追加到文档**末尾**，无法穿插图文 → 用 `+create` 的 XML `<img path="@./x.jpg">` 一次成型
2. python-docx 的 `_NumberingStyle` 没有 `.font` 属性，遍历样式要 `getattr(s, "font", None)` + try/except
3. AI 字幕（ai-zh）**完全没有标点**，全量文字版必须人工断句纠错——这是每篇的固定工作量，已计入口径
4. Pillow 画图中文用 `C:/Windows/Fonts/msyh.ttc`，可正常嵌入 docx/飞书

**下次从哪继续**

- 日常使用：新链接 → `run_all.py "<链接>"` → 对话生成分段/选图 → `run_all.py --dir … --full`
- 遗留验证：第一个无字幕视频实测红线 1 的报错路径
- 可选：把「分段方案确认」环节加回来（当前经授权跳过用户确认）
