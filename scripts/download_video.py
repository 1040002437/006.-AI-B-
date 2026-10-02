#!/usr/bin/env python3
"""F3：下载 720P 视频到 000N.《标题》/video.mp4。

用法:
    python scripts/download_video.py "<url>" --out-dir "data/0001.《标题》"
    python scripts/download_video.py "<url>" --out-dir <dir> --force   # 已存在也重下

要点:
- 优先 H.264（avc1）编码的 720P，避开 AV1 —— 后续抽帧解码快一个数量级
- ffmpeg 用 imageio-ffmpeg 自带的二进制，换机不用装系统 ffmpeg
- 已存在 video.mp4 时默认跳过（不重复下载）
"""
import argparse
import sys
from pathlib import Path

import imageio_ffmpeg
import yt_dlp

# 720P 优先 avc1；拿不到再退回任意编码的 720P
FORMAT = ("bestvideo[height<=720][vcodec^=avc1]+bestaudio[ext=m4a]/"
          "bestvideo[height<=720]+bestaudio/"
          "best[height<=720]/best")


def download(url: str, out_dir: Path, force: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "video.mp4"
    if target.exists() and not force:
        print(f"已存在，跳过下载：{target}（{target.stat().st_size/1024/1024:.1f} MB）")
        return target

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    opts = {
        "format": FORMAT,
        "outtmpl": str(out_dir / "video.%(ext)s"),
        "merge_output_format": "mp4",
        "ffmpeg_location": str(Path(ffmpeg_exe).parent),
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 5,
        "noprogress": False,
        "quiet": False,
        "no_warnings": False,
        "logger": _Logger(),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    if not target.exists():
        alt = sorted(out_dir.glob("video.*"))
        if not alt:
            sys.exit("下载失败：目录内没有 video.* 文件")
        alt[0].rename(target)
    print(f"下载完成：{target}（{target.stat().st_size/1024/1024:.1f} MB）")
    return target


class _Logger:
    """把 yt-dlp 的日志压成单行进度，避免刷屏。"""

    def debug(self, msg):
        if msg.startswith("[download]") and "%" in msg:
            print(f"\r{msg.strip()}", end="", flush=True)

    def info(self, msg):
        print(f"  {msg}")

    def warning(self, msg):
        print(f"  [warn] {msg}")

    def error(self, msg):
        print(f"  [error] {msg}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="下载 B站 720P 视频")
    ap.add_argument("url", help="B站视频链接")
    ap.add_argument("--out-dir", required=True, help="输出目录（data/0001.《标题》/）")
    ap.add_argument("--force", action="store_true", help="已存在也重新下载")
    a = ap.parse_args()
    download(a.url, Path(a.out_dir), a.force)


if __name__ == "__main__":
    main()
