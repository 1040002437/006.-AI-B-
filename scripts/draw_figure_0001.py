#!/usr/bin/env python3
"""S14：为 0001 绘制「视频脉络」结构图（PIL，中文字体用微软雅黑）。

这张图的信息增量：视频是边演示边讲的，时间线是乱的；
本图把全片线性化成「搭库 → 喂料立规 → 四个自动化开关 → 产出」四段，
让读者 10 秒看懂整条链路，替代反复回看。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VIDEO_DIR = Path(__file__).resolve().parent.parent / \
    "data/0001.《【豆包实操】从个人知识库到自动化：Skills、飞书、定时任务一次讲清》"

W, H = 2000, 1120
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

INK = "#2B2F36"
STAGES = [
    # (标题, 底色, 边框, 盒子列表[(主文字, 副文字)])
    ("① 搭库（0:00-8:37）", "#E8F1FF", "#4C7DD8", [
        ("新建「个人知识库」文件夹", "素材先攒进一个目录"),
        ("豆包新建项目绑定该文件夹", "读写范围被限制在这个目录"),
        ("丢入「架构师提示词」自动搭骨架", "8 模块 + 主地图 + 规则 + 首设清单"),
    ]),
    ("② 喂料与立规（8:37-12:03）", "#FFF4E5", "#D89A4C", [
        ("喂料：口喷个人信息 / 分享历史对话 / 朋友圈长图", "让它记住你是谁、怎么说话"),
        ("立规矩：记住的必须同步写入本地知识库", "版本号 V1.0 → V1.1 自动迭代"),
    ]),
    ("③ 四个自动化开关（12:03-28:36）", "#EAF7EC", "#4CA86B", [
        ("定时任务", "每周五 12:00\n自动出周报 PPT"),
        ("连接器", "飞书 / 企微 / 钉钉\n百度网盘 / 淘宝"),
        ("Skill 技能", "跑通的工作流打包\n一句话整套复用"),
        ("手机遥控电脑", "扫码绑定\n产出写进飞书随时看"),
    ]),
    ("④ 产出（全片）", "#F3EAFB", "#8A5FC8", [
        ("周报 PPT ｜ 商品主图·详情页·视频 ｜ 飞书文档 ｜ 多维表格竞品库", "人只负责派活与验收"),
    ]),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def draw_box(d: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int,
             main: str, sub: str, fill: str, border: str,
             f_main: ImageFont.FreeTypeFont, f_sub: ImageFont.FreeTypeFont) -> None:
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill,
                        outline=border, width=3)
    cx = x + w / 2
    if "\n" in sub:                       # 竖排小卡：主标题 + 多行副文字
        d.text((cx, y + 18), main, font=f_main, fill=INK, anchor="ma")
        yy = y + 18 + f_main.size + 14
        for line in sub.split("\n"):
            d.text((cx, yy), line, font=f_sub, fill="#5A6068", anchor="ma")
            yy += f_sub.size + 8
    else:
        d.text((cx, y + h / 2 - (f_main.size + f_sub.size) / 2 - 4), main,
               font=f_main, fill=INK, anchor="ma")
        d.text((cx, y + h / 2 + f_main.size / 2 + 2), sub,
               font=f_sub, fill="#5A6068", anchor="ma")


def arrow(d: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int,
          color: str = "#98A0AA") -> None:
    d.line([x1, y1, x2, y2], fill=color, width=4)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        d.line([x2, y2, x2 + 16 * math.cos(ang + da), y2 + 16 * math.sin(ang + da)],
               fill=color, width=4)


def main() -> None:
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 44), "视频脉络：从一个文件夹到全自动产出（35:35）",
           font=font(40, True), fill=INK, anchor="mm")
    d.text((W / 2, 92), "自绘图 · 按「搭库 → 喂料立规 → 自动化 → 产出」重排，原视频为穿插演示",
           font=font(22), fill="#8A9098", anchor="mm")

    y = 130
    for si, (stage, fill, border, boxes) in enumerate(STAGES):
        # 阶段标题条
        d.rounded_rectangle([60, y, 380, y + 44], radius=10, fill=border)
        d.text((220, y + 22), stage, font=font(20, True), fill="#FFFFFF", anchor="mm")

        if si == 0:                        # 三个盒子横排
            bw, bh, gap = 480, 110, 40
            x = 400
            for i, (m, s) in enumerate(boxes):
                draw_box(d, x, y, bw, bh, m, s, fill, border,
                         font(24, True), font(19))
                if i < len(boxes) - 1:
                    arrow(d, x + bw + 6, y + bh / 2, x + bw + gap - 6, y + bh / 2)
                x += bw + gap
            y_next = y + bh
        elif si == 1:                      # 两个盒子横排
            bw, bh, gap = 740, 110, 60
            x = 400
            for i, (m, s) in enumerate(boxes):
                draw_box(d, x, y, bw, bh, m, s, fill, border,
                         font(24, True), font(19))
                if i < len(boxes) - 1:
                    arrow(d, x + bw + 6, y + bh / 2, x + bw + gap - 6, y + bh / 2)
                x += bw + gap
            y_next = y + bh
        elif si == 2:                      # 四个开关横排
            bw, bh, gap = 352, 180, 32
            x = 400
            for i, (m, s) in enumerate(boxes):
                draw_box(d, x, y, bw, bh, m, s, fill, border,
                         font(25, True), font(20))
                if i < len(boxes) - 1:
                    arrow(d, x + bw + 4, y + bh / 2, x + bw + gap - 4, y + bh / 2)
                x += bw + gap
            y_next = y + bh
        else:                              # 产出：一条通栏
            bw, bh = 1480, 110
            draw_box(d, 400, y, bw, bh, boxes[0][0], boxes[0][1], fill, border,
                     font(26, True), font(20))
            y_next = y + bh

        if si < len(STAGES) - 1:
            y += (y_next - y)
            gap_y = 56 if si != 1 else 64
            arrow(d, W / 2, y + 8, W / 2, y + gap_y - 8)
            y += gap_y

    out_dir = VIDEO_DIR / "figures"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "视频脉络-从一个文件夹到全自动产出.png"
    img.save(out)
    print(f"已生成：{out}")


if __name__ == "__main__":
    main()
