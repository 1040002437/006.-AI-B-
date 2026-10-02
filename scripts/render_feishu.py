#!/usr/bin/env python3
"""S16+S17+S18：content.json → 飞书云文档（一次建文档、图文穿插、链接写回）。

用法:
    python scripts/render_feishu.py --dir "data/0001.《标题》"

实现:
- DocxXML：`<img path="@frames/xx.jpg" caption="📍 hh:mm:ss …" width="800"/>`
  内联上传本地图片（cwd 相对路径，脚本把 cwd 切到视频文件夹）
- 用户身份（--as user）创建到 .secrets/feishu_folder.txt 指定的云盘文件夹
- lark-cli 是 .cmd，必须用 node.exe + run.js 直调（Windows 已知坑）
- 成功后把云文档链接写回 视频信息.md

红线:
- 创建或插图失败必须报错退出（红线 8），本地 docx 在此之前已生成
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parent.parent
NODE = next(iter(sorted(glob.glob(str(Path.home() / ".workbuddy/binaries/node/versions/*/node.exe")))), None)
RUNJS = str(Path.home() / ".workbuddy/binaries/node/cli-connector-packages/node_modules/@larksuite/cli/scripts/run.js")


def e(text: str) -> str:
    return escape(str(text))


def img_tag(rel: str, cap: str) -> str:
    if not (video_dir / rel).exists():
        print(f"[warn] 缺图，跳过：{rel}", file=sys.stderr)
        return ""
    return f'<img path="@./{rel}" caption={quoteattr(cap)} width="800"/>'


def build_xml(c: dict) -> str:
    meta = c["meta"]
    dur = f"{meta['duration'] // 60} 分 {meta['duration'] % 60} 秒"
    x = [f"<title>{e(meta['num'])}.《{e(meta['title'])}》</title>"]
    x.append(f'<p><b>原视频：</b><a type="url-preview" href="{e(meta["url"])}">{e(meta["url"])}</a></p>')
    x.append(f"<p><b>UP主：</b>{e(meta['up'])}　<b>时长：</b>{e(dur)}　"
             f"<b>BV号：</b>{e(meta['bvid'])}　<b>字幕来源：</b>{e(meta['subtitle_source'])}</p>")

    # ---- 一图流（F14） ----
    overview = next((f for f in c.get("figures", []) if f.get("role") == "overview"), None)
    other_figures = [f for f in c.get("figures", []) if f.get("role") != "overview"]
    if overview:
        x.append("<h1>一图流</h1>")
        x.append(img_tag(overview["file"], f"一图流　{overview['caption']}"))

    # ---- 总结版 ----
    x.append(f"<h1>{e(c['summary']['heading'])}</h1>")
    for f in other_figures:
        x.append(img_tag(f["file"], f"自绘图　{f['caption']}"))
    for i, ch in enumerate(c["summary"]["chapters"], 1):
        x.append(f"<h2>{i:02d} {e(ch['title'])}（{e(ch['time_range'])}）</h2>")
        x.append(f"<p>{e(ch['summary'])}</p>")
        if ch["bullets"]:
            x.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in ch["bullets"]) + "</ul>")
        for im in ch["images"]:
            x.append(img_tag(im["file"], f"📍 {im['time']}　{im['caption']}"))

    # ---- 全量版 ----
    x.append(f"<h1>{e(c['full']['heading'])}</h1>")
    x.append(f"<p>来源：{e(meta['subtitle_source'])}（B站导出），已做断句与明显听写纠错；"
             "时间码为段落起点，可跳回原视频定位。</p>")
    for b in c["full"]["blocks"]:
        x.append(f"<p><b>【{e(b['time'])}】</b>　{e(b['text'])}</p>")
        for im in b["images"]:
            x.append(img_tag(im["file"], f"📍 {im['time']}　{im['caption']}"))
    return "\n".join(x)


def lark(args: list[str], cwd: Path) -> dict:
    cmd = [NODE, RUNJS] + args + ["--as", "user", "--format", "json"]
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=570)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        print(out)
        print((r.stderr or "")[-2000:], file=sys.stderr)
        sys.exit(f"lark-cli 失败（退出码 {r.returncode}）：{' '.join(args[:3])}…")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"lark-cli 返回不是 JSON：{out[:600]}")


def find_keys(obj, wanted: dict) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in wanted and not wanted[k]:
                wanted[k] = v
            find_keys(v, wanted)
    elif isinstance(obj, list):
        for v in obj:
            find_keys(v, wanted)


def write_back(info_md: Path, url: str) -> None:
    txt = info_md.read_text(encoding="utf-8")
    txt = re.sub(r"## 飞书云文档\s*\n+_待生成_",
                 f"## 飞书云文档\n\n{url}", txt)
    txt = txt.replace("| 飞书云文档 | ⬜ 待生成（生成后链接写在此处） |",
                      "| 飞书云文档 | ✅ 已生成（链接见文末） |")
    txt = txt.replace("| `frames/` 截图 | ⬜ 待生成 |", "| `frames/` 截图 | ✅ 已生成 |")
    txt = txt.replace("| `figures/` 自绘图 | ⬜ 待生成 |", "| `figures/` 自绘图 | ✅ 已生成 |")
    m = re.search(r"\| `(\d{4}\.《.*?》\.docx)` \| ⬜ 待生成 \|", txt)
    if m:
        txt = txt.replace(m.group(0), f"| `{m.group(1)}` | ✅ 已生成 |")
    info_md.write_text(txt, encoding="utf-8")


video_dir = None


def main() -> None:
    global video_dir
    ap = argparse.ArgumentParser(description="content.json → 飞书云文档")
    ap.add_argument("--dir", required=True, help="视频文件夹")
    ap.add_argument("--dry-run", action="store_true", help="只生成 XML 不创建")
    a = ap.parse_args()
    video_dir = (ROOT / a.dir).resolve() if not Path(a.dir).is_absolute() else Path(a.dir)
    c = json.loads((video_dir / "content.json").read_text(encoding="utf-8"))

    xml = build_xml(c)
    xml_path = video_dir / "feishu_doc.xml"
    xml_path.write_text(xml, encoding="utf-8")
    print(f"XML 就绪：{xml_path}（{len(xml) // 1024} KB）")
    if a.dry_run:
        return

    folder = (ROOT / ".secrets" / "feishu_folder.txt").read_text().strip()
    print("创建飞书云文档（含 13 张图上传，约需 1-2 分钟）…")
    res = lark(["docs", "+create", "--parent-token", folder,
                "--content", f"@{xml_path.name}"], cwd=video_dir)

    wanted = {"document_id": "", "url": ""}
    find_keys(res, wanted)
    if not wanted["document_id"] or not wanted["url"]:
        print(json.dumps(res, ensure_ascii=False)[:1500])
        sys.exit("未能从返回中解析 document_id / url")
    print(f"云文档：{wanted['url']}")
    print(f"doc_id：{wanted['document_id']}")

    write_back(video_dir / "视频信息.md", wanted["url"])
    print("已写回 视频信息.md")


if __name__ == "__main__":
    main()
