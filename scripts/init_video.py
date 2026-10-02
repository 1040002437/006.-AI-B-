#!/usr/bin/env python3
"""F1+F2：解析 B站链接 → 建 000N.《标题》 目录 → 写 视频信息.md。

用法:
    python scripts/init_video.py "https://www.bilibili.com/video/BV1FGeG6pENE/"
    python scripts/init_video.py "<url>" --force      # 已存在时也重建目录信息

行为:
- 抽 BV 号与分 P（?p=N）；丢弃 spm_id_from 等追踪参数
- 调 view 接口取标题 / UP主 / 时长 / 各 P 的 cid
- 编号 = data/ 下现有最大 4 位编号 + 1（空号不复用）
- 同一 BV 号已存在 → 打印已存在编号并中止（除非 --force）
- 多 P 视频且链接未指定 P → 列出分 P 让你选，不擅自决定

产物:
    data/000N.《标题》/视频信息.md
    并在最后一行打印 OUT_DIR=<绝对路径>，供 prepare.py 串联时捕获
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_subtitle import (  # noqa: E402  复用已跑通的请求/wbi/解析逻辑
    ROOT, get_json, load_sessdata, make_session, parse_bvid, wbi_key, wbi_sign,
)

DATA = ROOT / "data"
ILLEGAL = r'\\/:*?"<>|'


def sanitize(title: str, limit: int = 60) -> str:
    """去掉 Windows 非法字符；超长截断。"""
    t = re.sub(r"[\\/:*?\"<>|]", "", title).strip()
    t = re.sub(r"\s+", " ", t)
    return (t[:limit] + "…") if len(t) > limit else t


def next_number() -> int:
    """扫描 data/ 下已有的 4 位编号目录，返回最大编号 + 1。"""
    nums = []
    for d in DATA.glob("*") if DATA.exists() else []:
        m = re.match(r"^(\d{4})\.", d.name)
        if m and d.is_dir():
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def find_existing(bvid: str) -> Path | None:
    """按 视频信息.md 里记录的 BV号 反查已存在的文件夹。"""
    for d in sorted(DATA.glob("*")) if DATA.exists() else []:
        info = d / "视频信息.md"
        if info.exists() and bvid in info.read_text(encoding="utf-8"):
            return d
    return None


def parse_page(url: str) -> int:
    m = re.search(r"[?&]p=(\d+)", url)
    return int(m.group(1)) if m else 1


def fetch_view(url: str, bvid: str) -> dict:
    sess = make_session(load_sessdata(), referer=url)
    view = get_json(sess, "https://api.bilibili.com/x/web-interface/view",
                    params={"bvid": bvid})
    if view.get("code") != 0:
        sys.exit(f"视频信息获取失败：{view.get('message')}\n"
                 "若提示未登录/风控，可能是 SESSDATA 已失效，请重新获取。")
    return view["data"]


def hms(sec: int) -> str:
    return f"{sec // 60} 分 {sec % 60} 秒（{sec} 秒）"


def write_info_md(path: Path, *, num: int, title: str, up: str, dur: int,
                  bvid: str, cid: int, url: str, page: int, total_page: int) -> None:
    clean = sanitize(title)
    page_note = f"，第 {page}/{total_page} P" if total_page > 1 else ""
    path.write_text(f"""# {num:04d}.《{clean}》

## 基本信息

| 项 | 值 |
|---|---|
| 编号 | {num:04d} |
| 标题 | {clean} |
| UP主 | {up} |
| 时长 | {hms(dur)} |
| BV号 | {bvid} |
| cid | {cid} |
| 分 P | {page} / {total_page}{page_note} |
| 画质 | 720P |
| 抓取时间 | {datetime.date.today().isoformat()} |

## 原视频链接

{url}

## 字幕

| 项 | 值 |
|---|---|
| 来源 | _待抓取_ |
| 段数 | _待抓取_ |
| 覆盖 | _待抓取_ |

## 产物

| 产物 | 状态 |
|---|---|
| `视频信息.md` | ✅ 本文件 |
| `video.mp4` | ⬜ 待生成 |
| `subtitle.json` / `subtitle.srt` | ⬜ 待生成 |
| `frames/` 截图 | ⬜ 待生成 |
| `figures/` 自绘图 | ⬜ 待生成 |
| `{num:04d}.《{clean}》.docx` | ⬜ 待生成 |
| 飞书云文档 | ⬜ 待生成（生成后链接写在此处） |

## 飞书云文档

_待生成_
""", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="解析链接 → 建目录 → 写视频信息")
    ap.add_argument("url", help="B站视频链接（可带 ?p=N）")
    ap.add_argument("--force", action="store_true", help="已存在时仍重建目录信息")
    a = ap.parse_args()

    bvid = parse_bvid(a.url)
    data = fetch_view(a.url, bvid)
    pages = data.get("pages", [])
    total_page = len(pages)
    page = parse_page(a.url)

    if total_page > 1:
        if not re.search(r"[?&]p=\d+", a.url):
            listing = "\n".join(f"  P{p['page']}: {p['part']}" for p in pages)
            sys.exit("这是一个多 P 视频，请在链接里指定要处理的那一 P（例如末尾加 ?p=2）：\n"
                     f"{listing}\n原链接：{a.url}")
        page = min(max(page, 1), total_page)

    cid = pages[page - 1]["cid"] if pages else data["cid"]
    part_title = pages[page - 1].get("part", "") if pages else ""
    title = data["title"] if total_page <= 1 else f"{data['title']} - P{page} {part_title}"
    dur = pages[page - 1].get("duration", data.get("duration", 0)) if pages else data.get("duration", 0)

    exist = find_existing(bvid)
    if exist and not a.force:
        print(f"该 BV 号已存在：{exist.name}（如需覆盖请加 --force）")
        print(f"OUT_DIR={exist.resolve()}")
        return

    num = next_number()
    clean = sanitize(title)
    folder = DATA / f"{num:04d}.《{clean}》"
    folder.mkdir(parents=True, exist_ok=True)
    write_info_md(folder / "视频信息.md", num=num, title=clean, up=data["owner"]["name"],
                  dur=int(dur), bvid=bvid, cid=cid, url=a.url, page=page,
                  total_page=total_page)

    print(f"编号　: {num:04d}")
    print(f"标题　: {clean}")
    print(f"UP主　: {data['owner']['name']}　时长 {hms(int(dur))}")
    print(f"目录　: {folder}")
    print(f"OUT_DIR={folder.resolve()}")


if __name__ == "__main__":
    main()
