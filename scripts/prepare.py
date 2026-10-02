#!/usr/bin/env python3
"""S08：素材阶段一键串联（F1–F4）。

用法:
    python scripts/prepare.py "https://www.bilibili.com/video/BV1FGeG6pENE/"
    python scripts/prepare.py "<url>" --force        # 已存在则覆盖重跑
    python scripts/prepare.py "<url>" --no-download  # 只解析+抓字幕

流程:
    [1/3] 解析链接 → 建 000N.《标题》 → 写 视频信息.md
    [2/3] 下载 720P → video.mp4
    [3/3] 抓字幕（CC 优先，AI 兜底）→ subtitle.json / subtitle.srt
    [4/4] 回写 视频信息.md 的字幕与产物状态

无字幕时直接中止（质量红线 1），不产出残缺素材。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}", flush=True)


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        print(out)
        print((r.stderr or "").strip(), file=sys.stderr)
        sys.exit(f"步骤失败（退出码 {r.returncode}）：{' '.join(cmd)}")
    print(out)
    return out


def update_info(info_md: Path, sub_json: Path, source: str) -> None:
    """把字幕统计与产物状态回写到 视频信息.md。"""
    body = json.loads(sub_json.read_text(encoding="utf-8")).get("body", [])
    n = len(body)
    cover = body[-1]["to"] if body else 0
    txt = info_md.read_text(encoding="utf-8")
    txt = re.sub(r"\| 来源 \| .*? \|", f"| 来源 | {source} |", txt)
    txt = re.sub(r"\| 段数 \| .*? \|", f"| 段数 | {n} 段 |", txt)
    txt = re.sub(r"\| 覆盖 \| .*? \|", f"| 覆盖 | {cover/60:.1f} 分钟 |", txt)
    txt = txt.replace("| `video.mp4` | ⬜ 待生成 |", "| `video.mp4` | ✅ 已下载 |")
    txt = txt.replace("| `subtitle.json` / `subtitle.srt` | ⬜ 待生成 |",
                      "| `subtitle.json` / `subtitle.srt` | ✅ 已抓取 |")
    txt = txt.replace("_待抓取_", "已抓取")
    info_md.write_text(txt, encoding="utf-8")


def detect_source(url: str, bvid: str) -> str:
    """回查一次 player 接口，确认这批字幕是人工 CC 还是 AI 字幕。"""
    try:
        from fetch_subtitle import get_json, load_sessdata, make_session, pick_subtitle, wbi_key, wbi_sign
        sess = make_session(load_sessdata(), referer=url)
        view = get_json(sess, "https://api.bilibili.com/x/web-interface/view",
                        params={"bvid": bvid})
        d = view["data"]
        p = wbi_sign({"aid": d["aid"], "cid": d["cid"], "bvid": bvid}, wbi_key(sess))
        player = get_json(sess, "https://api.bilibili.com/x/player/wbi/v2", params=p)
        subs = (player.get("data") or {}).get("subtitle", {}).get("subtitles", [])
        pick = pick_subtitle(subs)
        lan = str(pick.get("lan", ""))
        return "B站 AI 字幕（ai-zh）" if lan.startswith("ai-") else "人工 CC 字幕"
    except SystemExit:
        raise
    except Exception as e:                       # 回查失败不影响主流程
        return f"B站字幕（来源回查失败：{e}）"


def main() -> None:
    ap = argparse.ArgumentParser(description="素材阶段一键串联：解析→下载→抓字幕")
    ap.add_argument("url", help="B站视频链接")
    ap.add_argument("--force", action="store_true", help="已存在时覆盖重跑")
    ap.add_argument("--no-download", action="store_true", help="跳过视频下载")
    a = ap.parse_args()

    total = 3 if not a.no_download else 2
    step(1, total, "解析链接 / 建目录 / 写视频信息")
    out = run([sys.executable, str(SCRIPTS / "init_video.py"), a.url]
              + (["--force"] if a.force else []))
    m = re.search(r"OUT_DIR=(.+)$", out, re.M)
    if not m:
        sys.exit("未能从 init_video.py 拿到输出目录")
    out_dir = Path(m.group(1).strip())

    i = 2
    if not a.no_download:
        step(i, total, "下载 720P 视频")
        sys.path.insert(0, str(SCRIPTS))
        import download_video
        download_video.download(a.url, out_dir, a.force)
        i += 1

    step(i, total, "抓取字幕（CC 优先，AI 兜底）")
    run([sys.executable, str(SCRIPTS / "fetch_subtitle.py"), a.url,
         "--out-dir", str(out_dir)])

    bvid = re.search(r"(BV[0-9A-Za-z]{10})", a.url).group(1)
    update_info(out_dir / "视频信息.md", out_dir / "subtitle.json",
                detect_source(a.url, bvid))

    print(f"\n素材就绪：{out_dir}")
    print("下一步：由 WorkBuddy 读字幕做分段与总结（P2）")


if __name__ == "__main__":
    main()
