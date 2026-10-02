# 环境搭建与换机清单

## 一次性依赖

```bash
REPO="C:/D/AI项目/006.让AI学会看B站视频"
cd "$REPO"
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
# yt-dlp / imageio-ffmpeg / requests / python-docx / pillow
```

不需要装 ffmpeg（`imageio-ffmpeg` 自带预编译二进制）、不需要显卡。

## 凭据一：B站 SESSDATA（拿字幕用）

**B站字幕只对登录用户下发**，所以必须带 Cookie。

1. 浏览器登录 bilibili.com → F12 → Application → Cookies → 复制 `SESSDATA` 的值
2. 写入 `$REPO/.secrets/sessdata.txt`（整行，不要换行）
3. 几个月会失效一次，脚本会明确报错而不是返回空字幕

只有 CC 字幕也没有 AI 字幕时，脚本直接中止（红线 1）——这时候要么换个视频，要么人工给字幕。

## 凭据二：飞书授权（写文档用）

写飞书靠 `lark-cli`，它不在项目里，也不是 pip 包——**由 WorkBuddy 的 lark 套件安装**（lark-unified skill），装完在：

```
C:/Users/<用户>/.workbuddy/binaries/node/cli-connector-packages/node_modules/@larksuite/cli/scripts/run.js
```

调用必须用 `node.exe + run.js`，**不能直接调 `.cmd`**（Windows 下 Python subprocess 会 WinError 2）：

```bash
NODE="C:/Users/<用户>/.workbuddy/binaries/node/versions/<版本>/node.exe"
"$NODE" .../@larksuite/cli/scripts/run.js docs +create --as user --parent-token <folder> --content @doc.xml --format json
```

授权用**用户身份**（bot 身份会因为权限范围不够报 `app_scope_not_applied`）：

```bash
auth login --scope ... --device-code     # 必须在同一进程里轮询，不能拆成两步
```

目标文件夹 token 写进 `$REPO/.secrets/feishu_folder.txt`（飞书云盘打开目标文件夹，URL 最后一段就是）。当前用的是「009.AI生成文档」。

## 换到新电脑的完整清单

git 只能带走代码和文档，这四样带不走：

| 缺失 | 表现 | 怎么补 |
|---|---|---|
| `.secrets/` 两个文件 | 抓不到字幕 / 写不了云文档 | 重取 SESSDATA + 重做飞书授权 |
| `.venv/` | `import` 报错 | `pip install -r requirements.txt` |
| `data/`（90MB+） | 没有历史素材和 docx | 整盘拷（编号才连续）；不拷则从 0001 重新开始，旧文档去飞书云盘看 |
| `lark-cli` | 渲染阶段报找不到它 | 让 WorkBuddy 重装 lark 套件并重新授权 |

新机器上 Python 版本不同没关系——按上面「一次性依赖」重建一个 `.venv` 即可，脚本靠 `__file__` 定位根目录，跟着 `$REPO` 走。

## 体检一条命令

```bash
ls "$REPO/.secrets/" && "$PY" -c "import yt_dlp, PIL, docx, requests; print('依赖 OK')" \
  && ls ~/.workbuddy/binaries/node/cli-connector-packages/node_modules/@larksuite/cli/scripts/run.js
```
