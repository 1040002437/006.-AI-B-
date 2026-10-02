#!/usr/bin/env python3
"""S13：按 content.json 的截图清单精确抽帧。

用法:
    python scripts/extract_frames.py --dir "data/0001.《标题》"

要点:
- `-ss` 必须放在 `-i` 前面（先定位再解码），放后面会逐帧解码慢一个数量级
- 文件名即时间码：00-05-12.jpg
- ffmpeg 用 imageio-ffmpeg 自带二进制
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description="按 time code 抽帧")
    ap.add_argument("--dir", required=True, help="视频文件夹 data/0001.《标题》")
    ap.add_argument("--force", action="store_true", help="已存在也重新抽")
    a = ap.parse_args()

    video_dir = (ROOT / a.dir).resolve() if not Path(a.dir).is_absolute() else Path(a.dir)
    content = json.loads((video_dir / "content.json").read_text(encoding="utf-8"))
    video = video_dir / "video.mp4"
    if not video.exists():
        sys.exit(f"找不到视频：{video}")

    frames_dir = video_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    for im in content["images"]:
        out = video_dir / im["file"]
        if out.exists() and not a.force:
            print(f"  已存在 {im['file']}")
            continue
        cmd = [ffmpeg, "-y", "-ss", str(im["t"]), "-i", str(video),
               "-frames:v", "1", "-q:v", "2", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0 or not out.exists():
            print((r.stderr or "")[-800:], file=sys.stderr)
            sys.exit(f"抽帧失败：{im['time']}")
        print(f"  {im['time']} → {im['file']}（{out.stat().st_size//1024} KB）")

    print(f"抽帧完成：{frames_dir}")


if __name__ == "__main__":
    main()
