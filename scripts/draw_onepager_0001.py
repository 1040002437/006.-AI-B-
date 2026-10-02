#!/usr/bin/env python3
"""0001 专属一图流（F14 v2）—— 横向阶段流 + 动作盒。

版式沿用 `draw_figure_0001.py`（2000×1120 扁宽）已验证的样式，本脚本只做一件事：
**把硬编码的节点数据改为直读 content.json 的 summary.chapters[]**，
并加一条覆盖校验（动作盒的 chapters 索引并集必须等于全部章节，漏章/重章拒绝出图）。

结构（AI 读完《视频总结版本》后自行拟定，不向用户确认）：
    顶部：标题 + 副标题（点明全片按哪几段重排）
    左侧：阶段标签条「① 搭库（0:00-8:37）」，含时间码
    右侧：该阶段的动作盒横排，盒间横向箭头串联；阶段间竖向箭头递进
    末段：通栏收尾

每个动作盒 = 主文字（提炼的动作短句）+ 副文字（补充说明），
并记录它对应总结版的哪几章（chapters[]），供读者回查。

用法：
    python scripts/draw_onepager_0001.py --dir "data/0001.…"
    python scripts/draw_onepager_0001.py --dir "data/0001.…" --no-preview
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

# ---- 版式参数（沿用 draw_figure_0001.py 已验证的横向扁宽布局）----
W = 2000
# 左侧阶段条要放得下最长标签「③ 四个自动化开关（12:03-28:36）」，按实测宽度放宽
STAGE_BAR_X0, STAGE_BAR_X1 = 50, 430
BOX_X = 450
# BOX_X 右侧可用宽度 = W - BOX_X - 50（右边距）
BOX_AREA = W - BOX_X - 50
INK = "#2B2F36"
SUB_INK = "#5A6068"
GRAY = "#8A9098"
ARROW = "#98A0AA"

# 字号：例图是 24/19，2000px 宽在飞书缩到 800px 后偏小（24→9.6px），
# 这里提到 28/22（缩后 11.2 / 8.8px），只调字号不改版式。
F_TITLE = 40
F_SUBTITLE = 22
F_STAGE = 22
F_MAIN = 28
F_SUB = 22

# ---- 本篇结构决策：阶段 + 动作盒。chapters[] 为该动作盒对应的总结版章节下标 ----
STAGES = [
    {
        "name": "① 搭库",
        "span": "0:00-8:37",
        "color": "#4C7DD8",
        "fill": "#E8F1FF",
        "nodes": [
            {"main": "新建「个人知识库」文件夹 → 豆包新建项目绑定",
             "sub": "素材先攒进一个目录；读写范围被限制在这个目录",
             "chapters": [0]},
            {"main": "丢入「架构师提示词」自动搭骨架",
             "sub": "8 模块 + 主地图 + 规则 + 首设清单",
             "chapters": [1, 2, 3]},
        ],
    },
    {
        "name": "② 喂料与立规",
        "span": "8:37-12:03",
        "color": "#D89A4C",
        "fill": "#FFF4E5",
        "nodes": [
            {"main": "喂料：口喷个人信息 / 分享历史对话 / 朋友圈长图",
             "sub": "让它记住你是谁、怎么说话；记住的必须同步写入本地知识库，\n"
                    "版本号 V1.0 → V1.1 自动迭代",
             "chapters": [4]},
        ],
    },
    {
        "name": "③ 四个自动化开关",
        "span": "12:03-28:36",
        "color": "#4CA86B",
        "fill": "#EAF7EC",
        "nodes": [
            {"main": "多线程并行", "sub": "一次跑四五个任务\n并给它「标准」",
             "chapters": [5]},
            {"main": "定时任务", "sub": "每周五 12:00\n自动出周报 PPT",
             "chapters": [6]},
            {"main": "连接器", "sub": "飞书 / 企微 / 钉钉\n百度网盘 / 淘宝",
             "chapters": [7]},
            {"main": "Skill 技能", "sub": "跑通的工作流打包\n一句话整套复用",
             "chapters": [8]},
            {"main": "手机遥控电脑", "sub": "扫码绑定\n产出写进飞书随时看",
             "chapters": [9]},
        ],
    },
    {
        "name": "④ 产出（全片）",
        "span": "28:36-35:35",
        "color": "#8A5FC8",
        "fill": "#F3EAFB",
        "full_width": True,
        "nodes": [
            {"main": "周报 PPT ｜ 商品主图·详情页·视频 ｜ 飞书文档 ｜ 多维表格竞品库",
             "sub": "人只负责派活与验收", "chapters": [10, 11]},
        ],
    },
]

TITLE = "视频脉络：从一个文件夹到全自动产出（35:35）"
SUBTITLE = "自绘图 · 按「搭库 → 喂料立规 → 自动化 → 产出」重排，原视频为穿插演示"
LAYOUT_NAME = "horizontal-stage-flow"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def text_size(d, text, fnt):
    b = d.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def mmss(sec) -> str:
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "--:--"
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def time_range_of(ch: dict) -> str:
    """时间码直读 chapters，优先原样印 time_range。"""
    tr = str(ch.get("time_range") or "").strip()
    if tr:
        return tr
    return f"{mmss(ch.get('start'))} - {mmss(ch.get('end'))}"


def check_coverage(chapters: list[dict]) -> None:
    """动作盒的 chapters 索引必须不重不漏地覆盖全部章节（红线 9 的机制保障）。"""
    idxs = [i for st in STAGES for n in st["nodes"] for i in n["chapters"]]
    n = len(chapters)
    dup = sorted({i for i in idxs if idxs.count(i) > 1})
    missing = sorted(set(range(n)) - set(idxs))
    extra = sorted(set(idxs) - set(range(n)))
    if dup or missing or extra:
        raise SystemExit(
            "动作盒与总结版章节对应不合法，拒绝出图（红线 9）：\n"
            f"  章节总数: {n}\n"
            f"  重复归入: {dup or '无'}\n"
            f"  漏掉的章: {missing or '无'}\n"
            f"  越界的章: {extra or '无'}"
        )


def arrow(d, x1, y1, x2, y2, color=ARROW, width=4):
    d.line([x1, y1, x2, y2], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        d.line([x2, y2, x2 + 16 * math.cos(ang + da), y2 + 16 * math.sin(ang + da)],
               fill=color, width=width)


def draw_box(d, x, y, w, h, node, fill, border, f_main, f_sub):
    """动作盒：主文字 + 副文字。"""
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill,
                        outline=border, width=3)
    main = node["main"]
    sub = node.get("sub", "")
    if "\n" in sub:
        # 竖排小卡：主标题在上，多行副文字在下
        cx = x + w / 2
        d.text((cx, y + 20), main, font=f_main, fill=INK, anchor="ma")
        yy = y + 20 + f_main.size + 12
        for line in sub.split("\n"):
            d.text((cx, yy), line, font=f_sub, fill=SUB_INK, anchor="ma")
            yy += f_sub.size + 8
    else:
        cx = x + w / 2
        cy = y + h / 2
        d.text((cx, cy - (f_main.size + f_sub.size) / 2 - 4), main,
               font=f_main, fill=INK, anchor="ma")
        d.text((cx, cy + f_main.size / 2 + 2), sub, font=f_sub,
               fill=SUB_INK, anchor="ma")


def box_layout(stage) -> tuple[list, int]:
    """盒宽按可用宽度自动分配，保证不溢出画布；返回(盒宽列表, 盒高)。"""
    nodes = stage["nodes"]
    n = len(nodes)
    if stage.get("full_width"):
        return [BOX_AREA], 120

    # 盒间距：盒子越多间距越小
    gap = 44 if n <= 3 else 26
    # 单盒宽度 = (可用宽度 - 总间距) / 盒数
    bw = (BOX_AREA - gap * (n - 1)) // n
    # 高度按盒子宽度与主文字长度自适应
    if n <= 2:
        bh = 135
    elif n == 3:
        bh = 145
    else:
        bh = 175
    return [bw] * n, bh


def build(video_dir: Path, cpath: Path, content: dict) -> Path:
    chapters = content.get("summary", {}).get("chapters", [])
    if not chapters:
        raise SystemExit("content.json 里没有 summary.chapters，无法画一图流")
    check_coverage(chapters)

    # ---------- 预布局：算总高 ----------
    y_layout = 130
    for si, st in enumerate(STAGES):
        _, bh = box_layout(st)
        y_layout += bh
        if si < len(STAGES) - 1:
            y_layout += 56
    H = y_layout + 40

    # ---------- 绘制 ----------
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 44), TITLE, font=font(F_TITLE, True), fill=INK, anchor="mm")
    d.text((W / 2, 92), SUBTITLE, font=font(F_SUBTITLE), fill=GRAY, anchor="mm")

    y = 130
    for si, st in enumerate(STAGES):
        color, fill = st["color"], st["fill"]
        # 左侧阶段标签条（含时间码），宽度按文字自适应，绝不裁切
        label = f"{st['name']}（{st['span']}）"
        lw = text_size(d, label, font(F_STAGE, True))[0] + 36
        lw = min(max(lw, 200), BOX_X - 60)
        d.rounded_rectangle([50, y, 50 + lw, y + 50], radius=10, fill=color)
        d.text((50 + lw / 2, y + 25), label, font=font(F_STAGE, True),
               fill="#FFFFFF", anchor="mm")

        widths, bh = box_layout(st)
        gap = 44 if len(widths) <= 3 else 26
        x = BOX_X
        for i, (node, bw) in enumerate(zip(st["nodes"], widths)):
            draw_box(d, x, y, bw, bh, node, fill, color, font(F_MAIN, True), font(F_SUB))
            if i < len(st["nodes"]) - 1:
                arrow(d, x + bw + 6, y + bh / 2, x + bw + gap - 6, y + bh / 2)
            x += bw + gap
        y_next = y + bh

        if si < len(STAGES) - 1:
            y = y_next
            arrow(d, W / 2, y + 8, W / 2, y + 56 - 8)
            y += 56

    out = video_dir / "figures" / "一图流.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")

    # 写回 content.json：figures[0] + summary.onepager，pop 旧 phases
    others = [f for f in (content.get("figures") or [])
              if f.get("role") != "overview" and "视频脉络" not in f.get("file", "")]
    cap = "一图流 · " + SUBTITLE
    content["figures"] = [{"file": "figures/一图流.png", "role": "overview",
                          "caption": cap}] + others
    content["summary"]["onepager"] = {
        "layout": LAYOUT_NAME,
        "stages": [{"name": s["name"], "span": s["span"], "color": s["color"],
                    "nodes": [{"main": n["main"], "sub": n.get("sub", ""),
                               "chapters": n["chapters"]} for n in s["nodes"]]}
                   for s in STAGES],
    }
    content["summary"].pop("phases", None)
    cpath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def make_preview(png: Path) -> Path:
    """缩到 1000px 宽另存——飞书里这张图会被缩放，这里看的是接近真实观感的尺寸。"""
    im = Image.open(png)
    nw = 1000
    nh = int(im.height * nw / im.width)
    prev = png.parent / "_preview_一图流.png"
    im.resize((nw, nh), Image.LANCZOS).save(prev, "PNG")
    return prev


def main() -> None:
    ap = argparse.ArgumentParser(description="0001 专属一图流（横向阶段流 + 动作盒）")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0001.《标题》")
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
    print(f"已生成一图流：{out}（{W}×{im.height}，{len(STAGES)} 阶段，"
          f"覆盖 {len(chapters)} 章）")
    print("已写回 content.json：figures[0].role=overview + summary.onepager，"
          "移除旧 phases 与旧视频脉络图")
    print("\n动作盒 → 总结版章节对应（供人工核对）：")
    for st in STAGES:
        for n in st["nodes"]:
            marks = "、".join(f"第{c + 1}章「{chapters[c]['title'][:14]}…」"
                              for c in n["chapters"])
            print(f"  [{st['name']}] {n['main'][:20]:<22} ← {marks}")

    if not a.no_preview:
        prev = make_preview(out)
        print(f"\n自检缩略图（1000px 宽）：{prev}  ← 请 Read 它确认可读")


if __name__ == "__main__":
    main()
