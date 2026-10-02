#!/usr/bin/env python3
"""0001 专属一图流脚本（F14 v2 · 总分总金字塔）。

结构决策（本篇单独设计，不套模板）：
    ┌ 总 ──这支视频到底在讲什么（核心结论）
    │  ↓
    │  4 个「分」用箭头串成递进：搭库 → 喂料立规 → 四个自动化开关 → 最终产出
    │  每个「分」下方竖排该组的章节卡片（标题逐字 + 时间码 + 一句话描述）
    ↓
    └ 总 ──产出落地，形成闭环

为什么是总分总而不是横向流水线：0001 章节标题偏长（最长 32 字），
横向排 4 段每段要塞 1–5 章会挤到看不清；竖排 + 箭头递进既保住了可读性，
又用「总—分—总」把「记住你 → 能干活 → 产出」的闭环讲出来。

规范硬约束（详见 docs/设计文档.md 第 6 节 / 第 8 节红线 9）：
  - 叶子节点标题**逐字等于** content.json 的 summary.chapters[i].title，
    时间码取 time_range，另带 chapters[i].phrase（8–20 字）。
    本脚本不硬编码任何标题清单，一律现取。
  - 标题**只折行、不截断**，绝不出现「…」。
  - 启动即断言分组下标并集 == range(len(chapters))，漏章/重章当场退出。
  - 画布宽 ≤1600px、标题 ≥28px、描述 ≥22px（可读性下限：图要缩到 800px 仍能读）。

用法：
    python scripts/draw_onepager_0001.py --dir "data/0001.…"
    python scripts/draw_onepager_0001.py --dir "data/0001.…" --no-preview
"""
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

# ---- 可读性下限（红线 9④；图在飞书/docx 里会缩到 800px 宽显示）----
W = 1600
F_ROOT = 34# 顶部/底部「总」
F_ROOT_SUB = 23
F_GROUP = 28# 分支名
F_GROUP_SUB = 21
F_TITLE = 28# 叶子标题
F_PHRASE = 22# 叶子描述
F_TIME = 21        # 时间码
F_HEAD = 38# 大标题
F_SUB = 22         # 副标题

PAD = 24
CARD_GAP = 14
BRANCH_GAP = 56
ROW_PAD = 30
LABEL_W = 286
CARD_MAX_W = W - LABEL_W - 90
CARD_X = 60 + LABEL_W + 34

INK = "#1F2329"
SUB_INK = "#4A5158"
LINE = "#DFE3E8"

# ---- 本篇的「总」：核心结论（AI 读完总结版后拟定，不在任何脚本里预先写死）----
ROOT_THESIS = "让豆包从「每次从头交代」变成「记住你、能干活」"
ROOT_CLOSING = "产出直接落进飞书，从一个文件夹到全自动产出"

# ---- 本篇结构决策：分支名 + 覆盖的章节下标（叶子数据一律现取 chapters[]）----
# 注意第③ 支含下标 5（旧 summary.phases漏掉了这一章「多线程并行」，此处已修）
GROUPS = [
    {"name": "① 搭库", "color": "#4C7DD8", "chapters": [0, 1, 2, 3]},
    {"name": "② 喂料立规", "color": "#D89A4C", "chapters": [4]},
    {"name": "③ 四个自动化开关", "color": "#4CA86B", "chapters": [5, 6, 7, 8, 9]},
    {"name": "④ 最终产出", "color": "#8A5FC8", "chapters": [10, 11]},
]
LAYOUT_NAME = "thesis-branch-thesis"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def text_size(d, text, fnt):
    b = d.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def wrap_by_width(d, text, fnt, max_w):
    """按像素宽度折行（中文友好）。只折行，不截断、不加省略号。"""
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if cur and text_size(d, trial, fnt)[0] > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


def tint(hex_color: str, ratio: float = 0.9) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (f"#{int(255-(255-r)*ratio):02x}"
            f"{int(255-(255-g)*ratio):02x}"
            f"{int(255-(255-b)*ratio):02x}")


def dark(hex_color: str, f: float = 0.72) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"


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


def load(video_dir: Path):
    cpath = video_dir / "content.json"
    if not cpath.exists():
        raise SystemExit(f"找不到 {cpath}\n请先跑 make_content.py 生成中间结构")
    return cpath, json.loads(cpath.read_text(encoding="utf-8"))


def assert_coverage(chapters: list[dict]) -> None:
    """红线 9 的机制保障：分支必须不重不漏地覆盖全部章节，否则当场失败不出图。"""
    idxs = [i for g in GROUPS for i in g["chapters"]]
    n = len(chapters)
    dup = sorted({i for i in idxs if idxs.count(i) > 1})
    missing = sorted(set(range(n)) - set(idxs))
    extra = sorted(set(idxs) - set(range(n)))
    if dup or missing or extra:
        raise SystemExit(
            "分支覆盖不合法，拒绝出图（红线 9）：\n"
            f"  章节总数: {n}\n"
            f"  重复归入: {dup or '无'}\n"
            f"  漏掉的章: {missing or '无'}\n"
            f"  越界的章: {extra or '无'}"
        )


def group_span(g, chapters) -> str:
    idxs = g["chapters"]
    return f"{time_range_of(chapters[idxs[0]]).split(' - ')[0]} – " \
           f"{time_range_of(chapters[idxs[-1]]).split(' - ')[-1]}"


def build(video_dir: Path, cpath: Path, content: dict) -> Path:
    meta = content.get("meta", {})
    chapters = content.get("summary", {}).get("chapters", [])
    if not chapters:
        raise SystemExit("content.json 里没有 summary.chapters，无法画一图流")
    assert_coverage(chapters)

    oneliner = str(meta.get("oneliner") or "").strip()
    title = str(meta.get("title") or "未命名视频")
    duration = meta.get("duration") or 0

    # ---------- 预布局 ----------
    probe = Image.new("RGB", (W, 100), "#FFFFFF")
    dp = ImageDraw.Draw(probe)

    #顶部「总」
    root_lines = wrap_by_width(dp, ROOT_THESIS, font(F_ROOT, True), W - 200)
    head_h = 96+ len(root_lines) * 46 + 58
    # 底部「总」
    close_lines = wrap_by_width(dp, ROOT_CLOSING, font(F_ROOT, True), W - 260)
    foot_h = 44 + len(close_lines) * 46 + 40

    # 各分支
    branch_blocks = []
    for g in GROUPS:
        cards = []
        for idx in g["chapters"]:
            ch = chapters[idx]
            t_lines = wrap_by_width(dp, ch["title"], font(F_TITLE, True), CARD_MAX_W - PAD * 2)
            p_lines = wrap_by_width(dp, str(ch.get("phrase") or ""), font(F_PHRASE),
                                    CARD_MAX_W - PAD * 2)
            tw = max(text_size(dp, ln, font(F_TITLE, True))[0] for ln in t_lines)
            pw = max(text_size(dp, ln, font(F_PHRASE))[0] for ln in p_lines)
            ts = time_range_of(ch)
            sw = text_size(dp, ts, font(F_TIME, True))[0]
            cw = min(CARD_MAX_W, max(tw, pw, sw) + PAD * 2)
            ch_h = PAD + len(t_lines) * 38 + 4 + len(p_lines) * 29 + 34
            cards.append({"idx": idx, "ch": ch, "t_lines": t_lines, "p_lines": p_lines,
                          "w": cw, "h": ch_h, "ts": ts})
        cards_h = sum(c["h"] for c in cards) + (len(cards) - 1) * CARD_GAP
        # 分支标签是左侧竖块：高度按「名称+副文本折行后」的实际占位算，下方留呼吸
        n_gl = len(wrap_by_width(dp, g["name"], font(F_GROUP, True), LABEL_W - 30))
        n_gs = len(wrap_by_width(dp, f"{len(cards)} 章　{group_span(g, chapters)}",
                                 font(F_GROUP_SUB), LABEL_W - 30))
        label_h = max(84, n_gl * 34 + n_gs * 26 + 18)
        branch_blocks.append({
            "g": g, "cards": cards,
            "h": max(cards_h + label_h, 150),
            "label_h": label_h,
        })

    body_h = sum(b["h"] + BRANCH_GAP for b in branch_blocks)
    H = head_h + body_h + 30 + foot_h

    # ---------- 绘制 ----------
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)

    # ===== 页眉=====
    d.text((W / 2, 46), f"一图流 · {title}", font=font(F_HEAD, True), fill=INK, anchor="mm")
    sub = f"{oneliner}· 时长 {mmss(duration)}" if oneliner else f"时长 {mmss(duration)}"
    d.text((W / 2, 86), sub, font=font(F_SUB), fill=SUB_INK, anchor="mm")
    d.line([(60, 118), (W - 60, 118)], fill=LINE, width=2)

    # ===== 顶部「总」=====
    y = head_h
    th_w = W - 200
    th_h = len(root_lines) * 46 + 44
    d.rounded_rectangle([100, y, 100 + th_w, y + th_h], radius=16,
                        fill="#F4F5F7", outline="#C9CDD3", width=2)
    ty = y + 22
    d.text((W / 2, ty), "总", font=font(24, True), fill="#7A828A", anchor="mm")
    ty += 22
    for ln in root_lines:
        d.text((W / 2, ty + 23), ln, font=font(F_ROOT, True), fill=INK, anchor="mm")
        ty += 46
    y += th_h + 24

    # ===== 四个「分」=====
    for bi, blk in enumerate(branch_blocks):
        g = blk["g"]
        color = g["color"]
        bh = blk["h"]
        cards = blk["cards"]

        # 左侧分支标签（竖块）
        d.rounded_rectangle([60, y, 60 + LABEL_W, y + blk["label_h"]],
                            radius=14, fill=color)
        # 分支名：按块内可用宽度折行（不截断，红线保护的是章节标题，分组名不在此列）
        inner_w = LABEL_W - 30
        gl = wrap_by_width(dp, g["name"], font(F_GROUP, True), inner_w)
        # 副文本（章数 + 时间范围）：折行到块内即可，仍不截断
        gs = f"{len(cards)} 章　{group_span(g, chapters)}"
        gs_lines = wrap_by_width(dp, gs, font(F_GROUP_SUB), inner_w)
        gh = len(gl) * 34 + len(gs_lines) * 26 + 10
        gy = y + max(8, (blk["label_h"] - gh) / 2)
        cx = 60 + LABEL_W / 2
        for ln in gl:
            d.text((cx, gy + 17), ln, font=font(F_GROUP, True), fill="#FFFFFF", anchor="mm")
            gy += 34
        for ln in gs_lines:
            d.text((cx, gy + 13), ln, font=font(F_GROUP_SUB), fill="#EDF1F5", anchor="mm")
            gy += 26

        # 右侧章节卡（竖排）
        cy = y
        for card in cards:
            d.rounded_rectangle([CARD_X, cy, CARD_X + card["w"], cy + card["h"]],
                                radius=14, fill=tint(color), outline="#DCDFE4", width=2)
            d.ellipse([CARD_X + PAD, cy + PAD, CARD_X + PAD + 34, cy + PAD + 34], fill=color)
            d.text((CARD_X + PAD + 17, cy + PAD + 17), str(card["idx"] + 1),
                   font=font(20, True), fill="#FFFFFF", anchor="mm")
            ty2 = cy + PAD + 8
            for ln in card["t_lines"]:
                d.text((CARD_X + PAD + 46, ty2), ln, font=font(F_TITLE, True),
                       fill=INK, anchor="lm")
                ty2 += 38
            ty2 += 4
            for ln in card["p_lines"]:
                d.text((CARD_X + PAD + 46, ty2), ln, font=font(F_PHRASE),
                       fill=SUB_INK, anchor="lm")
                ty2 += 29
            d.text((CARD_X + card["w"] - PAD, cy + card["h"] - 17), f"[ {card['ts']} ]",
                   font=font(F_TIME, True), fill=dark(color, 0.85), anchor="rm")
            cy += card["h"] + CARD_GAP

        y += bh

        # 分支之间的递进箭头：画在左侧标签列的空隙里（不与卡片重叠）
        if bi < len(branch_blocks) - 1:
            ax = 60 + LABEL_W / 2
            ay1 = y + 4
            ay2 = y + BRANCH_GAP - 10
            d.line([(ax, ay1), (ax, ay2 - 10)], fill="#8A9098", width=4)
            d.polygon([(ax, ay2), (ax - 10, ay2 - 14), (ax + 10, ay2 - 14)],
                      fill="#8A9098")
            d.text((ax + 16, (ay1 + ay2) / 2), "递进", font=font(19),
                   fill="#9AA1A8", anchor="lm")

    y += 10

    # ===== 底部「总」=====
    cl_w = W - 260
    cl_h = len(close_lines) * 46 + 44
    d.rounded_rectangle([130, y, 130 + cl_w, y + cl_h], radius=16,
                        fill="#EEF3F8", outline="#B9C4D0", width=2)
    cty = y + 22
    d.text((W / 2, cty), "总", font=font(24, True), fill="#7A828A", anchor="mm")
    cty += 22
    for ln in close_lines:
        d.text((W / 2, cty + 23), ln, font=font(F_ROOT, True), fill=INK, anchor="mm")
        cty += 46

    out = video_dir / "figures" / "一图流.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")

    # 写回 content.json：figures[0] + summary.onepager，pop 掉旧 phases
    cap = ("一图流 · 总分总："
           + re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", ROOT_THESIS)
           + " → " + " → ".join(re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", g["name"])
                                 for g in GROUPS))
    figs = [f for f in (content.get("figures") or []) if f.get("role") != "overview"]
    content["figures"] = [{"file": "figures/一图流.png", "role": "overview",
                          "caption": cap}] + figs
    content["summary"]["onepager"] = {
        "layout": LAYOUT_NAME,
        "thesis": ROOT_THESIS,
        "closing": ROOT_CLOSING,
        "groups": [{"name": g["name"], "color": g["color"], "chapters": g["chapters"]}
                   for g in GROUPS],
    }
    content["summary"].pop("phases", None)   # 旧受控版式产物，且 0001 数据本身漏章
    cpath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def make_preview(png: Path) -> Path:
    """按 800px 宽缩放另存——这就是飞书/docx 里的真实观感，必须看一眼。"""
    im = Image.open(png)
    nw = 800
    nh = int(im.height * nw / im.width)
    prev = png.parent / "_preview_一图流.png"
    im.resize((nw, nh), Image.LANCZOS).save(prev, "PNG")
    return prev


def main() -> None:
    ap = argparse.ArgumentParser(description="0001 专属一图流（F14 v2 · 总分总）")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0001.《标题》")
    ap.add_argument("--content", default=None)
    ap.add_argument("--no-preview", action="store_true", help="不生成 800px 缩略自检图")
    a = ap.parse_args()

    video_dir = Path(a.dir) if Path(a.dir).is_absolute() else (ROOT / a.dir)
    cpath = Path(a.content) if a.content else video_dir / "content.json"
    _, content = load(video_dir)
    out = build(video_dir, cpath, content)

    chapters = content["summary"]["chapters"]
    im = Image.open(out)
    print(f"已生成一图流：{out}（{W}×{im.height}，"
          f"总分总：1 总 + {len(GROUPS)} 分 + {len(chapters)} 叶子 + 1 总）")
    print("已写回 content.json：figures[0].role=overview + summary.onepager，"
          "并移除旧 summary.phases")
    print("\n叶子节点逐字清单（人工核对用，须与 chapters[i].title 完全一致、无省略号）：")
    for i, ch in enumerate(chapters):
        print(f"  {i + 1:2d}. [{time_range_of(ch)}] {ch['title']}")
        print(f"       {ch.get('phrase', '')}")

    if not a.no_preview:
        prev = make_preview(out)
        print(f"\n自检缩略图（800px 宽 = 飞书/手机观感）：{prev}  ← 请 Read 它确认可读")


if __name__ == "__main__":
    main()
