#!/usr/bin/env python3
"""S20：全流程一键串联。

用法:
    python scripts/run_all.py "<B站链接>"            # 从零：素材 →（无内容时停）提示进入内容阶段
    python scripts/run_all.py "<B站链接>" --full     # 内容就绪时一路到云文档
    python scripts/run_all.py --dir "data/0001.《…》" --full   # 对已有素材续跑渲染

阶段:
    [素材] 解析建目录 → 下载 720P → 抓字幕              （确定性，脚本完成）
    [内容] 分段 / 摘要 / 选截图点 / 一图流 → content.json   （需要 WorkBuddy 在对话中完成）
    [渲染] 抽帧 → 本地 docx → 飞书云文档 → 链接写回       （确定性，脚本完成）

没有 content.json 时会停在素材阶段——内容生成由 WorkBuddy 读字幕完成，
这是有意设计（总结质量靠理解力，不靠模板）。

一图流必须由该篇专属脚本产出（每篇结构不同、AI 自行判断版式），
缺图时 --full 直接报错中止，不自动跑通用绘图。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PY = sys.executable


def run(cmd: list[str], cwd: Path | None = None) -> str:
    """流式执行子进程：进度实时可见，同时收集 stdout 供解析。"""
    print(f"\n$ {' '.join(cmd)}\n", flush=True)
    p = subprocess.Popen(cmd, cwd=str(cwd or ROOT),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    collected = []
    for line in p.stdout:
        sys.stdout.write(line)
        collected.append(line)
    code = p.wait()
    if code != 0:
        sys.exit(f"步骤失败（退出码 {code}），已停止。")
    return "".join(collected)


def main() -> None:
    ap = argparse.ArgumentParser(description="全流程串联")
    ap.add_argument("url", nargs="?", help="B站视频链接")
    ap.add_argument("--dir", help="已有视频文件夹（续跑渲染阶段）")
    ap.add_argument("--full", action="store_true", help="素材之后继续：抽帧→docx→飞书")
    ap.add_argument("--force", action="store_true", help="已存在时覆盖重跑")
    ap.add_argument("--no-download", action="store_true")
    a = ap.parse_args()

    if not a.url and not a.dir:
        sys.exit("需要提供 B站链接或 --dir")

    if a.dir:
        out_dir = (ROOT / a.dir).resolve() if not Path(a.dir).is_absolute() else Path(a.dir)
    else:
        out = run([PY, str(SCRIPTS / "prepare.py"), a.url]
                  + (["--force"] if a.force else [])
                  + (["--no-download"] if a.no_download else []))
        marker = None
        for line in out.splitlines():
            if line.startswith("素材就绪："):
                marker = line[len("素材就绪："):].strip()
        if not marker:
            sys.exit("未能从 prepare.py 输出中解析素材文件夹")
        out_dir = Path(marker)
        print(f"\n素材文件夹：{out_dir.name}")

    content = out_dir / "content.json"
    if not a.full:
        print(f"\n素材阶段结束：{out_dir}")
        if not content.exists():
            print("下一步：由 WorkBuddy 读字幕生成分段/摘要/选图/一图流"
                  "（.tmp/full_blocks.txt、chapters.json、images.json）\n"
                  "        → make_content.py → 该篇专属一图流脚本"
                  "（参考 scripts/draw_onepager_0001.py，版式自行设计）\n"
                  "        → 然后用 --full 续跑。")
        return

    if not content.exists():
        sys.exit(f"缺少 {content}。内容阶段（分段/摘要/选图/一图流）需先在对话中完成。")

    c = json.loads(content.read_text(encoding="utf-8"))
    has_overview = any(f.get("role") == "overview" for f in c.get("figures", []))
    one_pager = out_dir / "figures" / "一图流.png"
    if not has_overview or not one_pager.exists():
        sys.exit(
            "缺少一图流：figures/一图流.png 未生成，或未登记到 content.json 的 "
            "figures[0]（role=overview）。\n"
            "F14 规范要求「每篇单独设计结构 + 专属脚本」，不再自动跑通用绘图"
            "（其产出不满足红线 9）。请先：\n"
            "  1) 为该视频设计阶段划分与动作盒（版式参考 scripts/draw_onepager_0001.py）\n"
            "  2) 写 scripts/draw_onepager_<编号>.py，直读 content.json 的 "
            "summary.chapters[]\n"
            "  3) 脚本须启动即断言动作盒 chapters[] 并集 == range(len(chapters))，"
            "并写回 summary.onepager 与 figures[0]"
        )

    run([PY, str(SCRIPTS / "extract_frames.py"), "--dir", str(out_dir)])
    run([PY, str(SCRIPTS / "render_docx.py"), "--dir", str(out_dir)])
    run([PY, str(SCRIPTS / "render_feishu.py"), "--dir", str(out_dir)])
    print("\n全部完成：本地 docx + 飞书云文档已生成，链接已写回 视频信息.md")


if __name__ == "__main__":
    main()
