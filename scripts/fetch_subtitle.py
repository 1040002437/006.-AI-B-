#!/usr/bin/env python3
"""抓取 B站字幕（需登录态 SESSDATA）。

用法:
    python scripts/fetch_subtitle.py "https://www.bilibili.com/video/BVxxxx/"
    python scripts/fetch_subtitle.py "<url>" --out-dir "data/0001.《标题》"

产物（写入 --out-dir，默认 data/ 根目录）:
    subtitle.json   原始字幕 JSON（含 from/to/content）
    subtitle.srt    SRT 字幕（后续全量文字版与截图定位的基础）

字幕选择: **人工 CC 字幕优先，无则 B站 AI 字幕（ai-zh）**。
无字幕时直接报错中止（质量红线 1），不做 ASR 降级。

依赖: requests
SESSDATA 从 .secrets/sessdata.txt 读取，或用环境变量 BILI_SESSDATA 传入。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import uuid
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
API = "https://api.bilibili.com"
ROOT = Path(__file__).resolve().parent.parent


def load_sessdata() -> str:
    """读取 SESSDATA：环境变量优先，其次 .secrets/sessdata.txt。"""
    s = os.environ.get("BILI_SESSDATA")
    if s:
        return s.strip()
    f = ROOT / ".secrets" / "sessdata.txt"
    if not f.exists():
        sys.exit(f"缺少登录凭证：请把 SESSDATA 写入 {f} 或设置环境变量 BILI_SESSDATA")
    return f.read_text().strip()


def make_session(sessdata: str, referer: str = "https://www.bilibili.com/") -> requests.Session:
    """构造会话。B站风控（412）要求带设备指纹 cookie：buvid3 + b_nut。"""
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://www.bilibili.com",
    })
    s.cookies.set("SESSDATA", sessdata, domain=".bilibili.com")
    s.cookies.set("buvid3", f"{uuid.uuid4()}infoc", domain=".bilibili.com")
    s.cookies.set("b_nut", str(int(time.time())), domain=".bilibili.com")
    return s


def get_json(sess: requests.Session, url: str, **kw) -> dict:
    """带重试的 GET：B站偶发 412 风控，退避重试即可。"""
    r = None
    for i in range(3):
        r = sess.get(url, timeout=30, **kw)
        if r.status_code == 200 and r.text.lstrip().startswith("{"):
            return r.json()
        time.sleep(1.5 * (i + 1))
    sys.exit(f"请求失败或被风控拦截（HTTP {getattr(r,'status_code','?')}）：{url}\n"
             "若持续失败，可能是 SESSDATA 已失效，请重新获取。")


def wbi_key(sess: requests.Session) -> str:
    """取 wbi 签名密钥：nav 接口的 img_url / sub_url 文件名拼接。"""
    nav = get_json(sess, f"{API}/x/web-interface/nav")["data"]["wbi_img"]
    stem = lambda u: os.path.splitext(os.path.basename(u))[0]
    return stem(nav["img_url"]) + stem(nav["sub_url"])


def wbi_sign(params: dict, key: str) -> dict:
    params["wts"] = int(time.time())
    qs = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((qs + key).encode()).hexdigest()
    return params


def parse_bvid(url: str) -> str:
    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    if not m:
        sys.exit(f"无法从链接中解析 BV 号：{url}")
    return m.group(1)


def pick_subtitle(subs: list) -> dict:
    """人工 CC 字幕优先，AI 字幕（ai-zh）兜底。

    只带 SESSDATA 不加 wbi 签名时 subtitle_url 会是空串，所以这里
    必须挑一个「真的有 URL」的候选，否则后面下载必然失败。
    """
    if not subs:
        sys.exit("该视频没有可用字幕（CC 与 AI 字幕都没有）。\n"
                 "按质量红线 1：直接中止，不做 ASR 降级、不产出残缺文档。")

    has_url = lambda s: bool(s.get("subtitle_url"))
    lan = lambda s: str(s.get("lan", ""))
    human = [s for s in subs if not lan(s).startswith("ai-") and has_url(s)]
    ai = [s for s in subs if lan(s) == "ai-zh" and has_url(s)]

    for group in (human, ai, [s for s in subs if has_url(s)]):
        if group:
            return group[0]
    sys.exit("字幕列表中没有可下载的 subtitle_url（可能是签名失效或登录态过期）")


def fetch_subtitle(bvid: str, sess: requests.Session, key: str) -> tuple[dict, str, dict]:
    """返回 (字幕 JSON, 视频标题, 选中的字幕元信息)。"""
    view = get_json(sess, f"{API}/x/web-interface/view", params={"bvid": bvid})
    if view.get("code") != 0:
        sys.exit(f"视频信息获取失败：{view.get('message')}")
    aid, cid, title = view["data"]["aid"], view["data"]["cid"], view["data"]["title"]

    # 必须 wbi 签名，否则 subtitle_url 为空
    p = wbi_sign({"aid": aid, "cid": cid, "bvid": bvid}, key)
    player = get_json(sess, f"{API}/x/player/wbi/v2", params=p)
    subs = (player.get("data") or {}).get("subtitle", {}).get("subtitles", [])

    pick = pick_subtitle(subs)
    url = pick["subtitle_url"]
    if url.startswith("//"):
        url = "https:" + url

    body = sess.get(url, timeout=30).json()
    return body, title, pick


def to_srt(body: dict) -> str:
    """把 B站字幕 JSON 转成 SRT 文本。"""
    def fmt(t: float) -> str:
        h = int(t // 3600)
        m = int(t % 3600 // 60)
        s = t % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"

    out = []
    for i, item in enumerate(body.get("body", []), 1):
        out.append(f"{i}\n{fmt(item['from'])} --> {fmt(item['to'])}\n{item['content']}\n")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="抓取 B站字幕（CC 优先，AI 兜底）")
    ap.add_argument("url", help="B站视频链接或 BV 号")
    ap.add_argument("--out-dir", default=None,
                    help="输出目录（通常是 data/0001.《标题》/），默认 data/ 根目录")
    a = ap.parse_args()

    bvid = parse_bvid(a.url)
    sess = make_session(load_sessdata(), referer=a.url)
    body, title, pick = fetch_subtitle(bvid, sess, wbi_key(sess))

    out = Path(a.out_dir) if a.out_dir else ROOT / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "subtitle.json").write_text(
        json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "subtitle.srt").write_text(to_srt(body), encoding="utf-8")

    n = len(body.get("body", []))
    dur = body["body"][-1]["to"] if body.get("body") else 0
    kind = "人工 CC" if not str(pick.get("lan", "")).startswith("ai-") else "B站 AI"
    print(f"标题　: {title}")
    print(f"字幕　: {kind} 字幕（lan={pick.get('lan')}），{n} 条，覆盖到 {dur/60:.1f} 分钟")
    print(f"输出　: {out / 'subtitle.srt'}")


if __name__ == "__main__":
    main()
