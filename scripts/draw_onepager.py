#!/usr/bin/env python3
"""S23：绘制「一图流」开篇脉络图（F14，每篇必做）。

入参：视频文件夹里的 content.json（由 make_content.py / 对话阶段产出）。
输出：该文件夹 figures/一图流.png —— 一张视频脉络导航图。

设计依据：docs/设计文档.md 第 6 节「一图流」。
特性：
  - 优先按 summary.phases 绘制「阶段纵向堆叠 + 阶段内横向流转」的层级图
    phases 结构：[
      {
        "name": "搭库",
        "time_range": "0:00 - 8:37",
        "color": "#4C7DD8",
        "nodes": [
          {"label": "新建「个人知识库」文件夹", "sub": "素材先攒进一个目录", "chapters": [0]},
          ...
        ]
      }
    ]
  - 无 phases 时回退到旧的纵向时间轴（保持兼容）
  - 节点文字自动折行、自动算卡片宽度；超宽时自动换行到下一行
  - 节点间用箭头连接，阶段间也用箭头连接；箭头绘制在卡片底层，不遮挡文字
  - 画完自动把 {file, role:"overview"} 写回 content.json 的 figures[0]
字体：微软雅黑（C:/Windows/Fonts/msyh*.ttc）。
"""
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

# 阶段默认配色（蓝、橙、绿、紫、红、青、棕、靛）
PHASE_PALETTE = [
    "#4C7DD8", "#D89A4C", "#4CA86B", "#8A5FC8",
    "#C0506B", "#2E9CA4", "#B5792B", "#5B6CC4",
]

# 旧平铺模式配色
FLAT_PALETTE = [
    ("#4C7DD8", "#E8F1FF"), ("#D89A4C", "#FFF4E5"), ("#4CA86B", "#EAF7EC"),
    ("#8A5FC8", "#F3EAFB"), ("#C0506B", "#FBE9EE"), ("#2E9CA4", "#E3F4F5"),
    ("#B5792B", "#FBF1E0"), ("#5B6CC4", "#ECEEFB"),
]

CIRCLE_NUMS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def mmss(sec) -> str:
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "--:--"
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def wrap_text(text: str, max_chars: int) -> list[str]:
    """按字符数折行（中文友好）。"""
    text = (text or "").strip()
    if not text:
        return [""]
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= max_chars:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines


def text_size(d: ImageDraw.Draw, text: str, fnt) -> tuple[int, int]:
    bbox = d.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_arrow(d: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int,
               color: str = "#6A737D", width: int = 4):
    """带箭头的折线/直线。"""
    d.line([(x1, y1), (x2, y2)], fill=color, width=width)
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return
    length = (dx ** 2 + dy ** 2) ** 0.5
    ux, uy = dx / length, dy / length
    vx, vy = -uy, ux
    ah = 14
    aw = 9
    tip = (x2, y2)
    base = (x2 - ah * ux, y2 - ah * uy)
    left = (base[0] + aw * vx, base[1] + aw * vy)
    right = (base[0] - aw * vx, base[1] - aw * vy)
    d.polygon([tip, left, right], fill=color)


def _tint_color(hex_color: str) -> str:
    """把阶段主色变淡，用于卡片底色。"""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"#{int(255-(255-r)*0.88):02x}{int(255-(255-g)*0.88):02x}{int(255-(255-b)*0.88):02x}"
    except Exception:
        return "#F2F4F7"


def _dark_color(hex_color: str, factor: float = 0.65) -> str:
    """把阶段主色变深，用于箭头。"""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
    except Exception:
        return "#6A737D"


# ============================================================
# 层级模式
# ============================================================

class MeasuredNode:
    def __init__(self, node, label_lines, sub_lines, w, h):
        self.node = node
        self.label_lines = label_lines
        self.sub_lines = sub_lines
        self.w = w
        self.h = h


def build_rows(nodes: list[dict], content_w: int, d: ImageDraw.Draw,
               card_h: int, hgap: int, vgap: int,
               min_w: int, max_w: int, pad_x: int) -> list[list[MeasuredNode]]:
    """把节点按横向空间打包成行，每节点附带计算好的尺寸。"""
    f_label = font(22, True)
    f_sub = font(17, True)

    measured = []
    for n in nodes:
        label = n.get("label", "").strip()
        sub = n.get("sub", "").strip()
        label_lines = wrap_text(label, 22)
        if len(label_lines) > 2:
            label_lines = label_lines[:1] + [label_lines[1][:20] + "…"]
        sub_lines = wrap_text(sub, 26)
        if len(sub_lines) > 2:
            sub_lines = sub_lines[:1] + [sub_lines[1][:24] + "…"]

        lw = max((text_size(d, ln, f_label)[0] for ln in label_lines), default=0)
        sw = max((text_size(d, ln, f_sub)[0] for ln in sub_lines), default=0)
        text_w = max(lw, sw)
        w = max(min_w, min(max_w, text_w + pad_x * 2))
        measured.append(MeasuredNode(node=n, label_lines=label_lines,
                                     sub_lines=sub_lines, w=w, h=card_h))

    rows: list[list[MeasuredNode]] = []
    cur_row, cur_w = [], 0
    for m in measured:
        need = m.w + (hgap if cur_row else 0)
        if cur_row and cur_w + need > content_w:
            rows.append(cur_row)
            cur_row, cur_w = [m], m.w
        else:
            cur_row.append(m)
            cur_w += need
    if cur_row:
        rows.append(cur_row)
    return rows


def draw_hierarchical(content: dict, out_path: Path) -> None:
    meta = content.get("meta", {})
    phases = content.get("summary", {}).get("phases") or []
    if not phases:
        raise ValueError("无 phases，不应走层级绘制")

    title = meta.get("oneliner") or meta.get("title", "未命名视频")
    duration = meta.get("duration") or 0

    W = 2200
    MARGIN_X = 70
    HEAD = 150
    MARGIN_BOTTOM = 70
    PHASE_LABEL_W = 200
    PHASE_GAP_X = 30
    CONTENT_X = MARGIN_X + PHASE_LABEL_W + PHASE_GAP_X
    CONTENT_W = W - MARGIN_X - CONTENT_X
    CARD_H = 118
    CARD_HGAP = 32
    CARD_VGAP = 32
    PHASE_VGAP = 52
    PHASE_PAD_TOP = 36
    PHASE_PAD_BOTTOM = 36
    CARD_PAD_X = 24
    LABEL_FONT = font(22, True)
    SUB_FONT = font(17, True)
    SUB_INK = "#333333"
    INK = "#2B2F36"

    # ---------- 预布局：计算每个阶段尺寸和每张卡片位置 ----------
    dummy = Image.new("RGB", (W, 1000), "#FFFFFF")
    d_dummy = ImageDraw.Draw(dummy)

    phase_layouts = []
    all_card_boxes = []   # (x, y, w, h)
    for pidx, ph in enumerate(phases):
        nodes = ph.get("nodes") or []
        rows = build_rows(nodes, CONTENT_W, d_dummy, CARD_H, CARD_HGAP, CARD_VGAP,
                          300, 760, CARD_PAD_X)
        rows_h = sum(r[0].h for r in rows) + (len(rows) - 1) * CARD_VGAP if rows else 0
        ph_h = max(rows_h + PHASE_PAD_TOP + PHASE_PAD_BOTTOM, 110)
        phase_layouts.append({
            "phase": ph,
            "rows": rows,
            "height": ph_h,
            "rows_h": rows_h,
            "color": ph.get("color") or PHASE_PALETTE[pidx % len(PHASE_PALETTE)],
        })

    H = HEAD + sum(p["height"] for p in phase_layouts) + \
        (len(phase_layouts) - 1) * PHASE_VGAP + MARGIN_BOTTOM

    # ---------- 绘制：白底 → 阶段背景 → 箭头 → 阶段标签 → 卡片 → 文字 ----------
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)

    # 标题
    main_title = f"视频脉络：{title}"
    if duration:
        main_title += f"（{mmss(duration)}）"
    d.text((W / 2, 48), main_title, font=font(38, True), fill=INK, anchor="mm")
    phase_names = " → ".join(p["phase"].get("name", "") for p in phase_layouts)
    subtitle = f"自绘图 · 按「{phase_names}」重排，原视频为穿插演示"
    d.text((W / 2, 94), subtitle, font=font(21), fill="#8A9098", anchor="mm")
    d.line([MARGIN_X, HEAD - 24, W - MARGIN_X, HEAD - 24], fill="#E3E6EA", width=2)

    # 计算每张卡片的最终坐标
    y = HEAD
    for layout in phase_layouts:
        ph_h = layout["height"]
        content_y_start = y + PHASE_PAD_TOP
        content_usable_h = ph_h - PHASE_PAD_TOP - PHASE_PAD_BOTTOM
        rows_total_h = layout["rows_h"]
        y_offset = (content_usable_h - rows_total_h) // 2
        row_y = content_y_start + y_offset

        phase_card_centers = []
        for row in layout["rows"]:
            row_w = sum(c.w for c in row) + (len(row) - 1) * CARD_HGAP
            x_start = CONTENT_X + (CONTENT_W - row_w) // 2
            x = x_start
            row_centers = []
            for card in row:
                row_centers.append((x + card.w // 2, row_y + card.h // 2, card.w, card.h))
                all_card_boxes.append((x, row_y, card.w, card.h))
                x += card.w + CARD_HGAP
            phase_card_centers.append(row_centers)
            row_y += CARD_H + CARD_VGAP

        layout["centers"] = phase_card_centers
        y += ph_h + PHASE_VGAP

    # 画所有箭头（在卡片和标签之下）
    for layout in phase_layouts:
        color = layout["color"]
        arrow_color = _dark_color(color, 0.75)
        for ridx, row in enumerate(layout["centers"]):
            for i in range(len(row) - 1):
                x1 = row[i][0] + row[i][2] // 2
                y1 = row[i][1]
                x2 = row[i + 1][0] - row[i + 1][2] // 2
                y2 = row[i + 1][1]
                draw_arrow(d, x1 + 10, y1, x2 - 8, y2, arrow_color, 4)
            # 行末 → 下一行首
            if ridx < len(layout["centers"]) - 1:
                last = row[-1]
                first = layout["centers"][ridx + 1][0]
                x1, y1 = last[0], last[1] + last[3] // 2
                x2, y2 = first[0], first[1] - first[3] // 2
                draw_arrow(d, x1, y1 + 12, x2, y2 - 8, arrow_color, 4)

    # 阶段间箭头
    for i in range(len(phase_layouts) - 1):
        a_last = phase_layouts[i]["centers"][-1][-1]
        b_first = phase_layouts[i + 1]["centers"][0][0]
        x1, y1 = a_last[0], a_last[1] + a_last[3] // 2
        x2, y2 = b_first[0], b_first[1] - b_first[3] // 2
        draw_arrow(d, x1, y1 + 8, x2, y2 - 8, "#5A626A", 5)

    # 画阶段标签和卡片文字
    y = HEAD
    for layout in phase_layouts:
        ph = layout["phase"]
        ph_h = layout["height"]
        color = layout["color"]
        name = ph.get("name", f"阶段")
        time_range = ph.get("time_range", "")

        # 阶段标签：左侧圆角竖块
        label_x = MARGIN_X
        d.rounded_rectangle([label_x, y, label_x + PHASE_LABEL_W, y + ph_h],
                            radius=14, fill=color)
        pidx = phase_layouts.index(layout)
        num = CIRCLE_NUMS[pidx] if pidx < len(CIRCLE_NUMS) else f"({pidx + 1})"
        d.text((label_x + PHASE_LABEL_W / 2, y + ph_h / 2 - 14),
               f"{num} {name}", font=font(22, True), fill="#FFFFFF", anchor="mm")
        if time_range:
            d.text((label_x + PHASE_LABEL_W / 2, y + ph_h / 2 + 18),
                     f"（{time_range}）", font=font(16), fill="#FFFFFF", anchor="mm")

        # 卡片与文字
        for ridx, row in enumerate(layout["centers"]):
            cards = layout["rows"][ridx]
            for (cx, cy, w, h), card in zip(row, cards):
                x = cx - w // 2
                y_card = cy - h // 2
                light = _tint_color(color)
                d.rounded_rectangle([x, y_card, x + w, y_card + h],
                                    radius=14, fill=light, outline="#D9DEE4", width=2)
                line_h = 28
                sub_h = 22
                total_text_h = len(card.label_lines) * line_h + len(card.sub_lines) * sub_h
                ly = y_card + (h - total_text_h) // 2
                for ln in card.label_lines:
                    d.text((x + w // 2, ly), ln, font=LABEL_FONT,
                           fill=INK, anchor="mm")
                    ly += line_h
                for ln in card.sub_lines:
                    d.text((x + w // 2, ly), ln, font=SUB_FONT,
                           fill=SUB_INK, anchor="mm")
                    ly += sub_h

        y += ph_h + PHASE_VGAP

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    n_nodes = sum(len(p.get("nodes", [])) for p in phases)
    print(f"已生成一图流：{out_path}（{W}×{H}，{len(phases)} 阶段 {n_nodes} 节点）")


# ============================================================
# 旧平铺模式（兼容）
# ============================================================

def draw_flat(content: dict, out_path: Path) -> None:
    """保留原纵向时间轴逻辑，无 phases 时回退。"""
    meta = content.get("meta", {})
    chapters = content.get("summary", {}).get("chapters", [])
    if not chapters:
        raise SystemExit("content.json 里没有 summary.chapters，无法画一图流")

    title = meta.get("oneliner") or meta.get("title", "未命名视频")
    duration = meta.get("duration") or 0

    HEAD = 150
    CARD_H = 92
    GAP = 26
    MARGIN_X = 80
    MARGIN_BOTTOM = 60
    W = 2000
    per_card = CARD_H + GAP
    H = HEAD + len(chapters) * per_card + MARGIN_BOTTOM

    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    INK = "#2B2F36"
    spine_x = MARGIN_X + 70

    d.text((W / 2, 46), f"一图流 · 《{title}》",
           font=font(38, True), fill=INK, anchor="mm")
    sub = f"共 {len(chapters)} 章" + (f" · 时长 {mmss(duration)}" if duration else "")
    sub += " · 节点与总结版章节 1:1 对应"
    d.text((W / 2, 94), sub, font=font(22), fill="#8A9098", anchor="mm")
    d.line([MARGIN_X, HEAD - 18, W - MARGIN_X, HEAD - 18], fill="#E3E6EA", width=2)

    y = HEAD
    for idx, ch in enumerate(chapters, 1):
        color, light = FLAT_PALETTE[(idx - 1) % len(FLAT_PALETTE)]
        top = y
        d.rounded_rectangle([MARGIN_X, top, W - MARGIN_X, top + CARD_H],
                            radius=16, fill=light, outline="#D9DEE4", width=2)
        cy = top + CARD_H / 2
        d.ellipse([spine_x - 26, cy - 26, spine_x + 26, cy + 26], fill=color)
        d.text((spine_x, cy), f"{idx:02d}", font=font(24, True),
               fill="#FFFFFF", anchor="mm")
        d.text((spine_x + 56, top + 22), _time_range(ch),
               font=font(20, True), fill=color, anchor="lm")

        lines = wrap_text(ch.get("title", ""), 22)
        ty = top + (CARD_H - len(lines) * 30) / 2
        for ln in lines:
            d.text((spine_x + 200, ty), ln, font=font(27, True), fill=INK, anchor="lm")
            ty += 30

        ph_text = _get_phrase(ch)
        pw = 30 + len(ph_text) * 19
        px = W - MARGIN_X - pw - 14
        d.rounded_rectangle([px, cy - 20, px + pw, cy + 20], radius=14, fill=color)
        d.text((px + pw / 2, cy), ph_text, font=font(19, True),
               fill="#FFFFFF", anchor="mm")

        if idx < len(chapters):
            ny = top + CARD_H + GAP / 2
            d.line([spine_x, top + CARD_H, spine_x, ny], fill="#C4CAD2", width=4)
        y = top + per_card

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    print(f"已生成一图流：{out_path}（{W}×{H}，{len(chapters)} 节点）")


def _time_range(ch: dict) -> str:
    if ch.get("time_range"):
        return ch["time_range"]
    return f"{mmss(ch.get('start'))} - {mmss(ch.get('end'))}"


def _get_phrase(ch: dict) -> str:
    p = ch.get("phrase")
    if isinstance(p, str) and p.strip():
        return p.strip()
    bl = ch.get("bullets") or []
    s = bl[0] if bl else (ch.get("summary") or ch.get("title") or "")
    s = re.sub(r"^[\-\*•\s]+", "", str(s)).strip()
    if len(s) > 14:
        s = s[:13] + "…"
    return s or "（略）"


# ============================================================
# 主流程
# ============================================================

def draw(content: dict, out_path: Path) -> None:
    phases = content.get("summary", {}).get("phases")
    if phases:
        draw_hierarchical(content, out_path)
    else:
        draw_flat(content, out_path)


def register(content: dict, out_rel: str) -> dict:
    figs = content.get("figures", []) or []
    overview = {"file": out_rel, "role": "overview",
                "caption": "一图流 · 视频脉络导航图"}
    others = [f for f in figs if f.get("role") != "overview"]
    content["figures"] = [overview] + others
    return content


def main() -> None:
    ap = argparse.ArgumentParser(description="绘制一图流开篇脉络图 (F14)")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0001.《标题》")
    ap.add_argument("--content", default=None, help="content.json 路径（默认 <dir>/content.json）")
    ap.add_argument("--out", default=None, help="输出 PNG（默认 <dir>/figures/一图流.png）")
    a = ap.parse_args()

    video_dir = (ROOT / a.dir).resolve() if not Path(a.dir).is_absolute() else Path(a.dir)
    cpath = Path(a.content) if a.content else video_dir / "content.json"
    opath = Path(a.out) if a.out else video_dir / "figures" / "一图流.png"
    if not cpath.exists():
        raise SystemExit(f"找不到 content.json：{cpath}\n请先跑 make_content.py 生成中间结构")

    content = json.loads(cpath.read_text(encoding="utf-8"))
    draw(content, opath)
    rel = str(opath.relative_to(video_dir)).replace("\\", "/")
    content = register(content, rel)
    cpath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已登记 overview 图到 content.json：{rel}")


if __name__ == "__main__":
    main()
