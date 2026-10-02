#!/usr/bin/env python3
"""0002 专属一图流（F14）—— 横向阶段流 + 动作盒。

版式沿用 draw_onepager_0001.py 已验证的横向扁宽布局（不发明新版式），
只重做一件事：按本片内容重新划分阶段与动作盒。

本片（15:00，评测类）脉络与 0001 不同：不是「搭建 → 自动化」的递进建设线，
而是「先立评测标准 → 再拿标准跑遍工具 → 最后给选型与成本」的一条评测线。
故分六段：

    ① 立界       概念三档区分（Search / Deep Search / Deep Research）
    ② 三级实操   同一个火箭问题走三遍，看三者差别
    ③ 立评测框架 六类探针测局部 + 三道大题测整机 + 四问十一项一票否决
    ④ 九工具实测 商业 4 家 / 开源 3 家 / 公开 Skill 2 家
    ⑤ 成本与选型 349 次调用 2.8 元 → 按诉求分四类推荐
    ⑥ 尾声       根因缺护栏，作者自研 Skill

用法：
    python scripts/draw_onepager_0002.py --dir "data/0002.…"
    python scripts/draw_onepager_0002.py --dir "data/0002.…" --no-preview
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

# ---- 版式参数（沿用 0001 已验证的横向扁宽布局）----
W = 2000
STAGE_BAR_X0 = 50
BOX_X = 470          # 左侧标签条按本篇最长标签实测放宽
BOX_AREA = W - BOX_X - 50
INK = "#2B2F36"
SUB_INK = "#5A6068"
GRAY = "#8A9098"
ARROW = "#98A0AA"

F_TITLE = 40
F_SUBTITLE = 22
F_STAGE = 21
F_MAIN = 25
F_SUB = 20

# ---- 本篇结构决策：阶段 + 动作盒。chapters[] 为该盒对应的总结版章节下标 ----
STAGES = [
    {
        "name": "① 立界",
        "span": "0:00-0:58",
        "color": "#4C7DD8",
        "fill": "#E8F1FF",
        "nodes": [
            {"main": "同一个火箭问题，三档问法",
             "sub": "哪天发射 → 查一点\n还有谁回收 → 对齐事实\n为何不同 → 解释差异",
             "chapters": [0]},
        ],
    },
    {
        "name": "② 三级实操",
        "span": "0:58-3:54",
        "color": "#4CA86B",
        "fill": "#EAF7EC",
        "nodes": [
            {"main": "Search",
             "sub": "Google 查发射日期\n两个权威源互相印证\n确认事实即收尾",
             "chapters": [1]},
            {"main": "Deep Search",
             "sub": "秘塔只给一个问题\n自己决定续查什么\n产出可回查的汇总表",
             "chapters": [2]},
            {"main": "Deep Research",
             "sub": "DeerFlow 拆子任务并行\n交付证据表 + 来源\n再解释为何不同",
             "chapters": [3]},
        ],
    },
    {
        "name": "③ 立评测框架",
        "span": "3:54-6:57",
        "color": "#D89A4C",
        "fill": "#FFF4E5",
        "nodes": [
            {"main": "六类探针测局部",
             "sub": "引用数字对齐\n跨表统一年份币种\n官方源不许用软文替代",
             "chapters": [4]},
            {"main": "三道大题测整机",
             "sub": "学术进展 / 主权基金 / 家庭买车\n资料判断计算同时考",
             "chapters": [5]},
            {"main": "四问十一项 + 一票否决",
             "sub": "不做平均分，「完成」≠ 通过\n核心数据冲突 → 整份不过",
             "chapters": [6]},
        ],
    },
    {
        "name": "④ 九工具实测",
        "span": "6:57-10:23",
        "color": "#C05C8E",
        "fill": "#FBEAF2",
        "nodes": [
            {"main": "商业 4 家",
             "sub": "ChatGPT 下载后 34/54 编号无网址\nGemini 用超期材料\nKimi 缺安全评估 · 阶跃连二手页",
             "chapters": [7]},
            {"main": "开源 3 家",
             "sub": "可换模型可拆步骤，代价自担\nDeerFlow 总成本表格与正文冲突\nLDP 段落重复 · 阿里来源连错",
             "chapters": [8]},
            {"main": "公开 Skill 2 家",
             "sub": "靠宿主工具的搜索与文件能力\nSTORM 换题即废 · Weizhena 篇幅不足\n27 次无一全过 11 项",
             "chapters": [9]},
        ],
    },
    {
        "name": "⑤ 成本与选型",
        "span": "10:23-14:13",
        "color": "#3E8FA8",
        "fill": "#E6F4F8",
        "nodes": [
            {"main": "真实成本远不止 token",
             "sub": "349 次调用共 2.8 元\n不含搜索 / 服务器 / 排障\n也没给人工核验返工定价",
             "chapters": [10]},
            {"main": "按诉求分四类",
             "sub": "要初稿 → Kimi\n愿自建 → Alibaba\n要可控 → DeerFlow\n只缺规矩 → Weizhena",
             "chapters": [11]},
        ],
    },
    {
        "name": "⑥ 尾声",
        "span": "14:13-15:00",
        "color": "#8A5FC8",
        "fill": "#F3EAFB",
        "full_width": True,
        "nodes": [
            {"main": "根因是缺一套能拦住错误的护栏 ｜ 作者用 Harness Engineering 自研 Deep Research Skill，三天内开源",
             "sub": "交稿前三查：重要资料漏没漏 · 关键数字能否重算 · 引用能否回到原网页",
             "chapters": [12]},
        ],
    },
]

TITLE = "视频脉络：Deep Research 工具怎么选（15:00）"
SUBTITLE = "自绘图 · 按「立界 → 三级实操 → 立评测框架 → 九工具实测 → 成本与选型 → 尾声」重排"
LAYOUT_NAME = "horizontal-stage-flow"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def text_size(d, text, fnt):
    b = d.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def check_coverage(chapters: list) -> None:
    """动作盒的 chapters 索引必须不重不漏地覆盖全部章节（红线 9）。"""
    idxs = [i for st in STAGES for n in st["nodes"] for i in n["chapters"]]
    n = len(chapters)
    dup = sorted({i for i in idxs if idxs.count(i) > 1})
    missing = sorted(set(range(n)) - set(idxs))
    extra = sorted(set(idxs) - set(range(n)))
    if dup or missing or extra:
        raise SystemExit(
            "动作盒与总结版章节对应不合法，拒绝出图（红线 9）：\n"
            f"  章节总数: {n}\n  重复归入: {dup or '无'}\n"
            f"  漏掉的章: {missing or '无'}\n  越界的章: {extra or '无'}"
        )


def arrow(d, x1, y1, x2, y2, color=ARROW, width=4):
    d.line([x1, y1, x2, y2], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        d.line([x2, y2, x2 + 16 * math.cos(ang + da), y2 + 16 * math.sin(ang + da)],
               fill=color, width=width)


def wrap(d, text, fnt, max_w):
    """按像素宽度折行（中英混排安全），返回行列表。"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        t = cur + ch
        if text_size(d, t, fnt)[0] > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def draw_box(d, x, y, w, h, node, fill, border):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill,
                        outline=border, width=3)
    f_main, f_sub = font(F_MAIN, True), font(F_SUB)
    cx = x + w / 2
    sub_lines = []
    for para in node.get("sub", "").split("\n"):
        sub_lines += wrap(d, para, f_sub, w - 28)
    main_lines = wrap(d, node["main"], f_main, w - 28)

    total = (len(main_lines) * (F_MAIN + 10) + 14
             + len(sub_lines) * (F_SUB + 8))
    yy = y + max(16, (h - total) / 2)
    for ln in main_lines:
        d.text((cx, yy), ln, font=f_main, fill=INK, anchor="ma")
        yy += F_MAIN + 10
    yy += 14
    for ln in sub_lines:
        d.text((cx, yy), ln, font=f_sub, fill=SUB_INK, anchor="ma")
        yy += F_SUB + 8


def box_layout(stage):
    """盒宽按可用宽度自适应分配，绝不溢出。"""
    nodes = stage["nodes"]
    n = len(nodes)
    if stage.get("full_width"):
        return [BOX_AREA], 150
    gap = 40 if n <= 3 else 24
    bw = (BOX_AREA - gap * (n - 1)) // n
    bh = {1: 150, 2: 190}.get(n, 200)
    return [bw] * n, bh


def build(video_dir: Path, cpath: Path, content: dict) -> Path:
    chapters = content.get("summary", {}).get("chapters", [])
    if not chapters:
        raise SystemExit("content.json 里没有 summary.chapters，无法画一图流")
    check_coverage(chapters)

    y_layout = 130
    for si, st in enumerate(STAGES):
        _, bh = box_layout(st)
        y_layout += bh
        if si < len(STAGES) - 1:
            y_layout += 52
    H = y_layout + 40

    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 44), TITLE, font=font(F_TITLE, True), fill=INK, anchor="mm")
    d.text((W / 2, 92), SUBTITLE, font=font(F_SUBTITLE), fill=GRAY, anchor="mm")

    y = 130
    for si, st in enumerate(STAGES):
        color, fill = st["color"], st["fill"]
        label = f"{st['name']}（{st['span']}）"
        lw = text_size(d, label, font(F_STAGE, True))[0] + 32
        d.rounded_rectangle([50, y, 50 + lw, y + 46], radius=10, fill=color)
        d.text((50 + lw / 2, y + 23), label, font=font(F_STAGE, True),
               fill="#FFFFFF", anchor="mm")

        widths, bh = box_layout(st)
        gap = 40 if len(widths) <= 3 else 24
        x = BOX_X
        for i, (node, bw) in enumerate(zip(st["nodes"], widths)):
            draw_box(d, x, y, bw, bh, node, fill, color)
            if i < len(st["nodes"]) - 1:
                arrow(d, x + bw + 6, y + bh / 2, x + bw + gap - 6, y + bh / 2)
            x += bw + gap

        if si < len(STAGES) - 1:
            y += bh
            arrow(d, W / 2, y + 8, W / 2, y + 52 - 8)
            y += 52

    out = video_dir / "figures" / "一图流.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")

    others = [f for f in (content.get("figures") or [])
              if f.get("role") != "overview"]
    content["figures"] = [{"file": "figures/一图流.png", "role": "overview",
                          "caption": "一图流 · " + SUBTITLE}] + others
    content["summary"]["onepager"] = {
        "layout": LAYOUT_NAME,
        "stages": [{"name": s["name"], "span": s["span"], "color": s["color"],
                    "nodes": [{"main": n["main"], "sub": n.get("sub", ""),
                               "chapters": n["chapters"]} for n in s["nodes"]]}
                   for s in STAGES],
    }
    cpath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def make_preview(png: Path) -> Path:
    im = Image.open(png)
    nw = 1000
    nh = int(im.height * nw / im.width)
    prev = png.parent / "_preview_一图流.png"
    im.resize((nw, nh), Image.LANCZOS).save(prev, "PNG")
    return prev


def main() -> None:
    ap = argparse.ArgumentParser(description="0002 专属一图流（横向阶段流 + 动作盒）")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0002.《标题》")
    ap.add_argument("--content", default=None)
    ap.add_argument("--no-preview", action="store_true")
    a = ap.parse_args()

    video_dir = Path(a.dir) if Path(a.dir).is_absolute() else (ROOT / a.dir)
    cpath = Path(a.content) if a.content else video_dir / "content.json"
    if not cpath.exists():
        raise SystemExit(f"找不到 {cpath}\n请先跑 make_content.py 生成中间结构")
    content = json.loads(cpath.read_text(encoding="utf-8"))

    out = build(video_dir, cpath, content)
    chapters = content["summary"]["chapters"]
    im = Image.open(out)
    print(f"已生成一图流：{out}（{W}×{im.height}，{len(STAGES)} 阶段，覆盖 {len(chapters)} 章）")

    print("\n动作盒 → 总结版章节对应（供人工核对）：")
    for st in STAGES:
        for n in st["nodes"]:
            marks = "、".join(f"第{c + 1}章「{chapters[c]['title'][:12]}…」"
                              for c in n["chapters"])
            print(f"  [{st['name']}] {n['main'][:22]:<24} ← {marks}")

    if not a.no_preview:
        prev = make_preview(out)
        print(f"\n自检缩略图（1000px 宽）：{prev}  ← 请 Read 它确认可读")


if __name__ == "__main__":
    main()