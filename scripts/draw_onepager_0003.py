#!/usr/bin/env python3
"""0003 专属一图流（F14）—— 横向阶段流 + 动作盒。

版式沿用 draw_onepager_0001/0002.py 已验证的横向扁宽布局（不发明新版式），
只重做一件事：按本片内容重新划分阶段与动作盒。

本片（7:43，概念科普类）脉络是一条「提出困惑 → 讲清 API → 暴露痛点 →
引出 SDK → 划清边界与选型」的单线递进，不分叉、不并行。故分五段：

    ① 场景设问外卖 App 要怎么拿到定位与路线能力
    ② 什么是 API  通信 / 抽象 / 标准化 三大特性
    ③ 一次调用    请求三要素 + 响应 JSON + 裸写代码的代价
    ④ SDK 登场    现成工具箱 → 一行queryRoute 拿到 RouteResponse
    ⑤ 关系与选型  API 是契约、SDK 是代码包，按需求二选一

用法：
    python scripts/draw_onepager_0003.py --dir "data/0003.…"
    python scripts/draw_onepager_0003.py --dir "data/0003.…" --no-preview
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
BOX_X = 430          # 左侧标签条按本篇最长标签（347px）实测放宽
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
        "name": "① 场景设问",
        "span": "0:00-1:09",
        "color": "#4C7DD8",
        "fill": "#E8F1FF",
        "nodes": [
            {"main": "外卖 App 要怎么拿到地图能力",
             "sub": "需求：自动定位 + 查路线 + 距离与预估时长\n现实：地图库与路径规划算法都不自研\n问题：客户端怎样和远端地图云服务交互",
             "chapters": [0]},
        ],
    },
    {
        "name": "② 什么是 API",
        "span": "1:09-2:53",
        "color": "#4CA86B",
        "fill": "#EAF7EC",
        "nodes": [
            {"main": "一套通信协议，三个关键特性",
             "sub": "Application Programming Interface，像一座桥\n通信：App 发需求，服务回传结果\n抽象：实现全藏进黑盒，只约定输入输出\n标准化：SOAP / gRPC / REST，本片用 REST",
             "chapters": [1]},
        ],
    },
    {
        "name": "③ 一次调用怎么发",
        "span": "2:53-5:05",
        "color": "#D89A4C",
        "fill": "#FFF4E5",
        "nodes": [
            {"main": "请求 = 方法 + 参数 + 端点",
             "sub": "方法 GET：取数据用 GET\n参数：起点与终点的经纬度\n端点 endpoint：服务端开放的 URL",
             "chapters": [2]},
            {"main": "响应多为 JSON，裸写很麻烦",
             "sub": "返回路线总距离、预估时长、路径点位\n纯手写：拼请求、处理异常、解析 JSON 全自理\n重复劳动多且易错 → 于是有了工具包",
             "chapters": [3]},
        ],
    },
    {
        "name": "④ SDK 登场",
        "span": "5:05-6:27",
        "color": "#C05C8E",
        "fill": "#FBEAF2",
        "nodes": [
            {"main": "SDK = 写好代码的工具箱",
             "sub": "Software Development Kit\n按语言提供：Java / Kotlin / Python / Go\n用什么技术栈就选对应语言的 SDK",
             "chapters": [4]},
            {"main": "只调一行，剩下交给底层",
             "sub": "queryRoute(起点, 终点) 即可\n底层自动拼参数、打端点、收 JSON 并转对象\n拿到 RouteResponse，点属性直接取数绘制",
             "chapters": [5]},
        ],
    },
    {
        "name": "⑤ 关系与选型",
        "span": "6:27-7:43",
        "color": "#3E8FA8",
        "fill": "#E6F4F8",
        "nodes": [
            {"main": "契约与工具包，各管一层",
             "sub": "API 是接口契约，不是可编译的代码包\n遵守约定，任意语言都能直接调\nSDK 底层几乎都在调 API，绑定语言与平台",
             "chapters": [6]},
            {"main": "两个结论 + 按需求二选一",
             "sub": "可以不用 SDK 手写网络代码调 API\nSDK 也不可能脱离服务 API 凭空干活\n高度定制 → 直接对接 API；快速出业务 → 官方 SDK",
             "chapters": [7]},
        ],
    },
]

TITLE = "视频脉络：别再混淆 API 与 SDK（7:43）"
SUBTITLE = "自绘图 · 按「场景设问 → 什么是 API → 一次调用怎么发 → SDK 登场 → 关系与选型」重排"
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
    bh = {1: 190, 2: 190}.get(n, 200)
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
    ap = argparse.ArgumentParser(description="0003 专属一图流（横向阶段流 + 动作盒）")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0003.《标题》")
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