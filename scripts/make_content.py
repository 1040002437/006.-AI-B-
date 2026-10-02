#!/usr/bin/env python3
"""S09：把各部分素材组装成「中间内容结构」content.json。

用法:
    python scripts/make_content.py --dir "data/0001.《标题》"
        [--blocks .tmp/full_blocks.txt] [--chapters .tmp/chapters.json]
        [--images .tmp/images.json] [--figure "figures/x.png|说明文字"]

结构（与排版无关，两个渲染器都消费它）:
    meta     编号 / 标题 / UP / 时长 / BV号 / 原链接 / 字幕来源
    figures  自绘结构图（总结版开头）
    images   截图清单（时间码 + caption + 文件名），同一份文件全量版与总结版复用
    summary  章节列表：起止秒 / 概述 / 要点 / 归属到本章的截图
    full     段落块列表：起始秒 / 正文 / 归属到本块的截图

截图归属由脚本按时间区间自动分配，不手写。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mmss(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def read_meta(video_dir: Path) -> dict:
    """从 视频信息.md 里读元信息（格式由 init_video.py 生成）。"""
    txt = (video_dir / "视频信息.md").read_text(encoding="utf-8")

    def row(key: str) -> str:
        m = re.search(rf"\|\s*{key}\s*\|\s*(.*?)\s*\|", txt)
        return m.group(1) if m else ""

    url_m = re.search(r"## 原视频链接\s*\n+\s*(\S+)", txt)
    dur_m = re.search(r"（(\d+)\s*秒）", row("时长"))
    return {
        "num": row("编号"),
        "title": row("标题"),
        "up": row("UP主"),
        "duration": int(dur_m.group(1)) if dur_m else 0,
        "bvid": row("BV号"),
        "url": url_m.group(1) if url_m else "",
        "subtitle_source": row("来源"),
        "dir": str(video_dir),
    }


def parse_blocks(path: Path) -> list[dict]:
    """每行 `MM:SS<TAB>正文`，MM:SS 为该块起始时间。"""
    blocks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        m = re.match(r"^(\d{1,2}):(\d{2})\t(.*)$", line)
        if not m:
            sys.exit(f"分块文件格式不对（应为 MM:SS<TAB>正文）：{line[:40]}")
        start = int(m.group(1)) * 60 + int(m.group(2))
        blocks.append({"start": start, "time": mmss(start), "text": m.group(3).strip()})
    return blocks


def main() -> None:
    ap = argparse.ArgumentParser(description="组装中间内容结构 content.json")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0001.《标题》")
    ap.add_argument("--blocks", default=".tmp/full_blocks.txt", help="全量文字分块（MM:SS<TAB>正文）")
    ap.add_argument("--chapters", default=".tmp/chapters.json", help="章节总结 JSON")
    ap.add_argument("--images", default=".tmp/images.json", help="截图点 JSON")
    ap.add_argument("--figure", action="append", default=[],
                    help="自绘结构图，格式 相对路径|说明文字，可多次传")
    a = ap.parse_args()

    video_dir = (ROOT / a.dir).resolve() if not Path(a.dir).is_absolute() else Path(a.dir)
    meta = read_meta(video_dir)

    images = []
    for i, item in enumerate(json.loads((ROOT / a.images).read_text(encoding="utf-8")), 1):
        t = int(item["t"])
        images.append({
            "id": f"img{i:02d}",
            "t": t,
            "time": mmss(t),
            "file": f"frames/{mmss(t).replace(':', '-')}.jpg",
            "caption": item["caption"],
        })

    blocks = parse_blocks(ROOT / a.blocks)
    # 每块的结束时间 = 下一块的起点，最后一块到视频结束
    ends = [b["start"] for b in blocks[1:]] + [meta["duration"] or blocks[-1]["start"] + 60]

    chapters = json.loads((ROOT / a.chapters).read_text(encoding="utf-8"))
    for ch in chapters:
        ch["time_range"] = f"{mmss(ch['start'])} - {mmss(ch['end'])}"

    def in_range(t: int, lo: int, hi: int) -> bool:
        return lo <= t < hi

    for ch in chapters:
        ch["images"] = [im for im in images if in_range(im["t"], ch["start"], ch["end"])]
    for b, end in zip(blocks, ends):
        b["images"] = [im for im in images if in_range(im["t"], b["start"], end)]

    figures = []
    for f in a.figure:
        path, _, cap = f.partition("|")
        figures.append({"file": path.strip(), "caption": cap.strip()})

    content = {
        "meta": meta,
        "figures": figures,
        "images": images,
        "summary": {"heading": "视频总结版本", "chapters": chapters},
        "full": {"heading": "视频全量文字版", "blocks": blocks},
    }
    out = video_dir / "content.json"
    out.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

    unplaced = [im["id"] for im in images
                if not any(im in ch["images"] for ch in chapters)]
    print(f"章节　: {len(chapters)} 个")
    print(f"段落块: {len(blocks)} 个")
    print(f"截图　: {len(images)} 张" + (f"（未落入任何章节：{unplaced}）" if unplaced else ""))
    print(f"自绘图: {len(figures)} 张")
    print(f"输出　: {out}")


if __name__ == "__main__":
    main()
