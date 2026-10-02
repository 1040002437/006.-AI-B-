# 内容阶段怎么做（第 ② 步，没有命令可替代）

这一步占整个流程的时间最多，也决定成品质量。产物是三个文本文件，喂给 `make_content.py` 组装成 `content.json`。

## 拿到素材后先通读

```bash
python - << 'EOF'
import json, pathlib
b = json.loads(pathlib.Path("<视频文件夹>/subtitle.json").read_text(encoding="utf-8"))["body"]
def mmss(s): return f"{int(s)//60:02d}:{int(s)%60:02d}"
out, buf, t0 = [], "", b[0]["from"]
for x in b:
    buf += x["content"]
    if len(buf) >= 38 or x is b[-1]:
        out.append(f"[{mmss(t0)}] {buf}"); buf = ""; t0 = x["to"]
pathlib.Path(".tmp/transcript_raw.txt").write_text("\n".join(out), encoding="utf-8")
EOF
```

**AI 字幕（`ai-zh`）完全没有标点**，一整串汉字。通读时同步做两件事：**断句**和**听写纠错**（实测踩过的：飞书≠非洲、豆包≠豆吧、Seedance≠CDance、AGENTS.md≠AMD）。这一步省不掉。

## 产出三个文件（都放 `.tmp/`）

### 1. `full_blocks.txt` —— 全量文字版

每行一块，**制表符**分隔，冒号前是该块起点：

```
00:00<TAB>开场，今天要讲的是…
01:02<TAB>先说知识库这部分…
```

- 目标 **60 秒左右一块**，但**跟着语义走**，不要机械切：一句话讲到一半宁可让这块长一点
- 参考量：35 分钟 ≈ 40–45 块
- 每块用完整句子写，保留原意，不要压缩成摘要——这是"全量"版

### 2. `chapters.json` —— 总结版章节

```json
[
  {"start": 0,     "end": 104,  "title": "为什么要用知识库",
   "summary": "……", "bullets": ["要点一", "要点二"]},
  {"start": 104,   "end": 312,  "title": "怎么搭 Skills",
   "summary": "……", "bullets": []}
]
```

- `start` / `end` 单位是**秒**，必须首尾相接覆盖全片
- 参考量：35 分钟 ≈ 10–14 章
- `summary` 讲这章到底讲了什么、结论是什么；`bullets` 留操作步骤或要点，**没有就给空数组**，别硬凑

### 3. `images.json` —— 截图点

```json
[
  {"t": 30,  "caption": "本地知识库文件夹结构"},
  {"t": 385, "caption": "8 个模块的可视化面板"}
]
```

**选图判据（红线 5）：只截"文字说不出来的信息"**——界面长什么样、代码怎么写的、图表数据多少、成品 PPT 长什么样。**纯口播对着镜头讲的段落不配图。** 所以时间点是疏密不均的，不是每隔几分钟一张。

参考密度：35 分钟 ≈ 6–12 张。

caption 写画面里那个**信息点**（"豆包的 Skills 创建界面"），不要写"视频截图"。

## 一图流（F14，每篇必做）

在《视频总结版本》**之前**单开一级标题「一图流」，节内只放一张「视频脉络图」，不配说明文字（文字都画在图里）。这是导航索引图，让人先看清全片结构、再按图跳正文。

- 图上节点 = `chapters[]` 的每个章节：节点标题直接用 `chapters[i].title`、时间码用 `time_range`，**逐字 1:1 对齐**（红线 9 的机制保障，别手画节点名）
- 节点数 5 / 12 两种规模都要能自动排版（≤8 平铺、>8 分组）；沿用 `draw_figure_0001.py` 的 PIL + `msyh.ttc` 路线
- 脚本 `scripts/draw_onepager.py` 规划中（S23，入参 content.json 参数化直绘）；落地前先用 PIL 按上面规则现画一张 `figures/一图流.png`
- 组装时把它作为**第一个** `--figure` 传入 `make_content.py`（role=overview）

## 文中补充图 / 自绘图（F12，可选 0–1 张）

只有当你判断正文某处结构讲不清（如局部对比、步骤流程）时才画，**每篇 0–1 张**；全片脉络已由 F14 一图流承担，这里**不重复画总脉络**。

- `scripts/draw_figure_0001.py` 是可抄的模板：PIL + `C:/Windows/Fonts/msyh.ttc`（中文），输出 PNG 到视频文件夹的 `figures/`
- 画完**必须生成缩略图给自己看一眼**（常见问题是文字被框挤出去）

## 组装

```bash
"$PY" "$REPO/scripts/make_content.py" --dir "data/000N.《标题》" \
    --blocks .tmp/full_blocks.txt --chapters .tmp/chapters.json --images .tmp/images.json \
    --figure "figures/xxx.png|图说明"
```

脚本会按时间区间**自动把截图分配给章节和段落块**——同一张图文件在总结版和全量版都出现，这是刻意的：两个版本都该能看见画面。输出末尾若提示"未落入任何章节"，说明那张图的时间点落在了 chapters 覆盖范围外，检查一下起止秒。

然后到第 ③ 步 `--full`：抽帧 → docx → 云文档。

## 交付前自查

- 抽完帧**逐张用缩略图核对**，确认确实拍到了想要的信息；时刻偏了就改 `images.json` 重抽，别将就
- 收尾：本地 docx 存在、云文档生成成功、链接已写回 `视频信息.md`
