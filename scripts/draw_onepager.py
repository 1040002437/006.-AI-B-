#!/usr/bin/env python3
"""S23：绘制「一图流」开篇脉络图（F14，每篇必做）。

入参：视频文件夹里的 content.json（由 make_content.py 产出）。
输出：该文件夹 figures/一图流.png —— 一张视频脉络导航图，节点与
      《视频总结版本》的章节 1:1 对应（标题、时间码、短语均由脚本
      直读 content.json，从机制上杜绝图上与正文对不上的问题）。

设计依据：docs/设计文档.md 第 6 节「一图流」。
特性：
  - 节点数量可变：纵向时间轴自动算高，不写死
  - 每节点：序号圆 + 时间码 + 章节标题（超长自动换行）+ 短语小标签
  - 可选 phases[] 分组：若 content.json 的 summary.phases 存在
    （[{name,start,end}]），按阶段插入分隔色带；不存在则平铺
  - 短语容错：chapters[i].phrase 缺失时，从 bullets[0]/summary 派生
  - 画完自动把 {file, role:"overview"} 写回 content.json 的 figures[0]，
    使后续渲染器无需特判即可消费
字体：微软雅黑（C:/Windows/Fonts/msyh*.ttc），沿用 draw_figure_0001.py。
"""
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

# 序号圆 + 标题文字的配色（循环取，章数再多也够）
PALETTE = [
    ("#4C7DD8", "#E8F1FF"), ("#D89A4C", "#FFF4E5"), ("#4CA86B", "#EAF7EC"),
    ("#8A5FC8", "#F3EAFB"), ("#C0506B", "#FBE9EE"), ("#2E9CA4", "#E3F4F5"),
    ("#B5792B", "#FBF1E0"), ("#5B6CC4", "#ECEEFB"),
]


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


def wrap(text: str, max_chars: int) -> list[str]:
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


def get_phrase(ch: dict) -> str:
    p = ch.get("phrase")
    if isinstance(p, str) and p.strip():
        return p.strip()
    bl = ch.get("bullets") or []
    s = bl[0] if bl else (ch.get("summary") or ch.get("title") or "")
    s = re.sub(r"^[\-\*•\s]+", "", str(s)).strip()
    if len(s) > 14:
        s = s[:13] + "…"
    return s or "（略）"


def get_time_range(ch: dict) -> str:
    if ch.get("time_range"):
        return ch["time_range"]
    return f"{mmss(ch.get('start'))} - {mmss(ch.get('end'))}"


def draw(content: dict, out_path: Path) -> None:
    meta = content.get("meta", {})
    chapters = content.get("summary", {}).get("chapters", [])
    if not chapters:
        raise SystemExit("content.json 里没有 summary.chapters，无法画一图流")

    phases = content.get("summary", {}).get("phases") or []
    title = meta.get("title", "未命名视频")
    duration = meta.get("duration") or 0

    # ---------- 尺寸预算 ----------
    HEAD = 150
    CARD_H = 92
    GAP = 26
    PHASE_H = 56
    MARGIN_X = 80
    MARGIN_BOTTOM = 60
    W = 2000
    per_card = CARD_H + GAP
    n_phases = 0
    if phases:
        # 统计实际会落地的阶段数（至少含一章者）
        for ph in phases:
            st, en = ph.get("start", 0), ph.get("end", 10**9)
            if any(st <= c.get("start", 0) < en for c in chapters):
                n_phases += 1
    H = HEAD + len(chapters) * per_card + n_phases * (PHASE_H + GAP) + MARGIN_BOTTOM

    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    INK = "#2B2F36"
    SUB = "#5A6068"
    spine_x = MARGIN_X + 70

    # ---------- 头部 ----------
    d.text((W / 2, 46), f"一图流 · 《{title}》",
           font=font(38, True), fill=INK, anchor="mm")
    sub = f"共 {len(chapters)} 章" + (f" · 时长 {mmss(duration)}" if duration else "")
    sub += " · 节点与总结版章节 1:1 对应"
    d.text((W / 2, 94), sub, font=font(22), fill="#8A9098", anchor="mm")
    d.line([MARGIN_X, HEAD - 18, W - MARGIN_X, HEAD - 18], fill="#E3E6EA", width=2)

    y = HEAD
    cur_phase = None

    for idx, ch in enumerate(chapters, 1):
        # 阶段分隔带（可选）
        if phases:
            for ph in phases:
                st, en = ph.get("start", 0), ph.get("end", 10**9)
                if st <= ch.get("start", 0) < en and cur_phase is not ph:
                    cur_phase = ph
                    d.rounded_rectangle([MARGIN_X, y, W - MARGIN_X, y + PHASE_H],
                                        radius=10, fill="#F2F4F7")
                    d.text((MARGIN_X + 24, y + PHASE_H / 2),
                           ph.get("name", f"阶段 {idx}"),
                           font=font(22, True), fill="#3A3F47", anchor="lm")
                    y += PHASE_H + GAP
                    break

        color, light = PALETTE[(idx - 1) % len(PALETTE)]
        top = y
        # 卡片底
        d.rounded_rectangle([MARGIN_X, top, W - MARGIN_X, top + CARD_H],
                            radius=16, fill=light, outline="#D9DEE4", width=2)
        # 序号圆 + 时间码
        cy = top + CARD_H / 2
        d.ellipse([spine_x - 26, cy - 26, spine_x + 26, cy + 26], fill=color)
        d.text((spine_x, cy), f"{idx:02d}", font=font(24, True),
               fill="#FFFFFF", anchor="mm")
        d.text((spine_x + 56, top + 22), get_time_range(ch),
               font=font(20, True), fill=color, anchor="lm")

        # 标题（自动换行）
        lines = wrap(ch.get("title", ""), 22)
        ty = top + (CARD_H - len(lines) * 30) / 2
        for ln in lines:
            d.text((spine_x + 200, ty), ln, font=font(27, True), fill=INK, anchor="lm")
            ty += 30

        # 短语小标签（右侧）
        ph_text = get_phrase(ch)
        pw = 30 + len(ph_text) * 19
        px = W - MARGIN_X - pw - 14
        d.rounded_rectangle([px, cy - 20, px + pw, cy + 20], radius=14, fill=color)
        d.text((px + pw / 2, cy), ph_text, font=font(19, True),
               fill="#FFFFFF", anchor="mm")

        # 连接线（非末节点）
        if idx < len(chapters):
            ny = top + CARD_H + GAP / 2
            d.line([spine_x, top + CARD_H, spine_x, ny], fill="#C4CAD2", width=4)
        y = top + per_card

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    print(f"已生成一图流：{out_path}（{W}×{H}，{len(chapters)} 节点）")


def register(content: dict, out_rel: str) -> dict:
    """把 overview 图写回 content.json 的 figures[0]，供渲染器消费。"""
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
    # 写回 overview 到 figures[0]
    rel = str(opath.relative_to(video_dir)).replace("\\", "/")
    content = register(content, rel)
    cpath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已登记 overview 图到 content.json：{rel}")


if __name__ == "__main__":
    main()
