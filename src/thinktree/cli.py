"""thinktree — 把思考 Tree（Markdown 嵌套列表）变成可交互的思维导图。

Tree.md 是唯一来源。格式：复选框 = 节点，普通列表行 = 节点的说明（详见 README）：
  - `## 标题`                           主枝
  - `- [ ] 问题？ => 一句话结论`          节点：[ ] 进行中 · [x] 已定 · [-] 否决 · [>] 搁置
  - `    - why: ……`                     节点下面的普通列表行是说明，why: 开头的是 why

用法：
  thinktree                             启动查看器，打开首页（最近打开 + vault 里发现的 tree）
  thinktree <Tree.md>                   直接打开某个 tree；已在运行就只开浏览器
  thinktree init [文件夹]               新建一个 tree（示例 Tree.md + 给 AI 的 CLAUDE.md），顺便设置好 vault
  thinktree build <Tree.md> [-o X]      导出单文件 HTML（默认 Tree.md 旁边的 Tree.html）
  thinktree check <Tree.md>             检查重复编号、找不到的链接、悬空的 [编号] 引用
  thinktree json  <Tree.md>             输出解析后的 JSON（给别的脚本 / AI 用）
  thinktree prompt                      输出给 AI 的格式说明（贴给 ChatGPT / Claude）
  thinktree recent                      列出最近打开的 tree
  thinktree stop                        停掉后台在跑的查看器

只依赖 Python 3.9+ 标准库；前端从 CDN 加载 d3 和 markmap-view。
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from . import __version__

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
TEMPLATES = HERE / "templates"
WINDOWS = os.name == "nt"


def _posix(rel: str) -> str:
    """vault 内相对路径统一用 /（Obsidian 的链接和 [[wikilink]] 都是 /；Windows 上 relpath 给的是 \\）。"""
    return rel.replace(os.sep, "/")


def write_text_atomic(path: Path, text: str):
    """写临时文件再原子替换；保留原文件的换行风格（Windows 上不把整个文件改成 CRLF）。"""
    try:
        crlf = b"\r\n" in path.read_bytes()
    except OSError:
        crlf = False
    tmp = path.with_name(path.name + ".thinktree-tmp")
    with open(tmp, "w", encoding="utf-8", newline="\r\n" if crlf else "\n") as f:
        f.write(text)
    for i in range(5):  # Windows：Obsidian 正好打开着文件时替换会失败，稍等重试
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if i == 4:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.1)

# ---------------------------------------------------------------- parsing

STATUS = {"❓": "open", "✅": "done", "❌": "rejected", "🅿️": "parked", "🅿": "parked"}
STATUS_RE = "|".join(sorted(map(re.escape, STATUS), key=len, reverse=True))
NODE_RE = re.compile(rf"^(?:(?P<st>{STATUS_RE})\s*)?\*\*\[(?P<id>[0-9][0-9a-z]*)\]\s*(?P<title>.*?)\*\*(?P<rest>.*)$")
SECTION_RE = re.compile(r"^##\s+(?:\[(?P<id>[0-9][0-9a-z]*)\]\s*)?(?P<title>.+?)\s*$")
LIST_RE = re.compile(r"^(?P<ws>[ \t]*)[-*+]\s+(?P<text>.*)$")
COMMENT_RE = re.compile(r"\s*<!--.*?-->\s*")
WIKILINK_RE = re.compile(r"\[\[((?:[^\[\]]|\[[^\[\]]*\])+)\]\]")
WHY_RE = re.compile(r"^why\s*[:：]\s*", re.I)
REF_RE = re.compile(r"(?<!\[)\[([0-9][0-9a-z]*)\](?!\]|\()")
# 新写法：复选框就是节点。[ ] 进行中 · [x] 已定 · [-] 否决 · [>] 搁置
TASK_RE = re.compile(r"^\[(?P<ch>.)\](?:\s+(?P<rest>.*))?$")
TASK_STATUS = {" ": "open", "?": "open", "/": "open", "x": "done", "X": "done", "-": "rejected", ">": "parked"}
EXPLICIT_ID_RE = re.compile(r"^\[(?P<id>[0-9][0-9a-z]*)\]\s*")
# 节点标记：节点文字里（结论之前）出现这些符号。⭐ = 重要，🚩 = 待办（打算明天 / 接下来几天做）
MARKS = {"star": ("⭐", re.compile(r"\s*⭐\ufe0f?\s*")), "todo": ("🚩", re.compile(r"\s*🚩\ufe0f?\s*"))}
TASK_LINE_RE = re.compile(r"^(?P<pre>[ \t]*[-*+]\s+\[.\]\s?)(?P<body>.*)$")
# 节点类型：标题开头写 "实验：" / "思考："（中英文冒号都行）。解析时去掉前缀，记在 type 里；没写 = ""（未分类）
NODE_TYPES = {"实验": "exp", "思考": "think"}
TYPE_RE = re.compile(r"^(?P<k>" + "|".join(map(re.escape, NODE_TYPES)) + r")\s*[:：]\s*")
TAIL_RE = re.compile(r"\s*((?:[（(][^（）()]*[）)]|↔\s*\[[0-9a-z]+\])\s*)+$")  # 末尾的括号 / ↔ 引用 = 附加说明


def _split_concl(t: str) -> Tuple[str, str]:
    """"标题 => 结论" → ("标题 ", "=> 结论")：只在结论之前找 ⭐，结论里的不算。"""
    for sep in ("=>", "→"):
        if sep in t:
            i = t.index(sep)
            return t[:i], t[i:]
    return t, ""


def pop_mark(t: str, mark: str) -> Tuple[str, bool]:
    """去掉节点文字里的某个标记（只看结论之前），返回 (去掉后的文字, 原来有没有)。"""
    rx = MARKS[mark][1]
    head, tail = _split_concl(t)
    if not rx.search(head):
        return t, False
    return (rx.sub(" ", head).strip() + (" " + tail if tail else "")).strip(), True


def pop_type(title: str) -> Tuple[str, str]:
    """"实验：xxx" → ("xxx", "exp")；没有类型前缀 → (原文, "")。"""
    m = TYPE_RE.match(title)
    return (title[m.end():], NODE_TYPES[m.group("k")]) if m else (title, "")


def split_node_text(t: str) -> Tuple[Optional[str], str, str, str]:
    """"[id] 标题 (10-02) => 结论" → (id 或 None, 标题, 附加, 结论)。结论用 => 分隔（旧的 → 也认）。"""
    head, concl = t, ""
    for sep in ("=>", "→"):
        if sep in t:
            head, concl = (x.strip() for x in t.split(sep, 1))
            break
    nid = None
    m = EXPLICIT_ID_RE.match(head)
    if m:
        nid, head = m.group("id"), head[m.end():]
    m = re.match(r"^\*\*(.+?)\*\*(.*)$", head)  # 允许整句加粗
    if m:
        head = m.group(1) + m.group(2)
    extra = ""
    m = TAIL_RE.search(head)
    if m and m.start() > 0:
        head, extra = head[: m.start()], m.group(0).strip()
    return nid, head.strip(), extra, concl


def _letters(k: int) -> str:
    s = ""
    while k:
        k, r = divmod(k - 1, 26)
        s = chr(97 + r) + s
    return s


def auto_id(parent_id: str, parent_kind: str, k: int) -> str:
    """按位置编号：2 → 2a → 2a1 → 2a1a（数字字母交替）；根下直接的节点用 1, 2, 3。"""
    if parent_kind == "root":
        return str(k)
    return parent_id + (_letters(k) if parent_id[-1].isdigit() else str(k))


def _clean(text: str) -> str:
    return COMMENT_RE.sub(" ", text).strip()


def _indent_unit(lines: List[str]) -> int:
    """空格缩进时自动判断一级是几个空格（tab 永远算一级）。"""
    widths = []
    for ln in lines:
        m = LIST_RE.match(ln)
        if m and m.group("ws") and "\t" not in m.group("ws"):
            widths.append(len(m.group("ws")))
    return min(widths) if widths else 4


def _level(ws: str, unit: int) -> int:
    return ws.count("\t") + len(ws.replace("\t", "")) // unit


def parse(text: str) -> dict:
    lines = text.splitlines()
    i0 = 0
    if lines and lines[0].strip() == "---":  # frontmatter
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                i0 = j + 1
                break
    unit = _indent_unit(lines[i0:])

    nodes: Dict[str, dict] = {}
    order: List[str] = []
    issues: List[dict] = []

    def new_node(nid, kind, title, parent, line, status="none", conclusion="", extra=""):
        if nid in nodes:
            issues.append({"level": "error", "line": line, "msg": f"编号重复：[{nid}]（第一次出现在第 {nodes[nid]['line']} 行）"})
            nid = f"{nid}~{line}"
        nodes[nid] = {
            "id": nid, "kind": kind, "status": status, "title": title,
            "conclusion": conclusion, "extra": extra, "details": [], "why": "", "why_items": [],
            "parent": parent, "children": [], "refs": [], "backrefs": [], "line": line,
            "legacy_details": False, "has_note": False, "syntax": "", "star": False, "todo": False, "type": "",
        }
        if parent:
            nodes[parent]["children"].append(nid)
        order.append(nid)
        return nid

    root = new_node("root", "root", "思考 Tree", None, 0)
    legend: List[Tuple[int, str]] = []
    section = root
    sec_count = 0
    # stack 元素：(level, kind, owner, base)；kind ∈ node / note（📝 容器）/ detail / legend
    # base = 容器内第一层详情的缩进偏移（旧格式的属性子项要往里缩一层）
    stack: List[Tuple[int, str, str, int]] = []

    for ln_no, raw in enumerate(lines[i0:], start=i0 + 1):
        if not raw.strip():
            continue
        if raw.startswith("# ") and not raw.startswith("## "):
            nodes[root]["title"] = _clean(raw[2:])
            continue
        m = SECTION_RE.match(raw)
        if m:
            sec_count += 1
            sid = m.group("id") or str(sec_count)
            section = new_node(sid, "section", _clean(m.group("title")), root, ln_no)
            stack = []
            continue
        m = LIST_RE.match(raw)
        if not m:
            # 列表项的续行：挂到当前详情或忽略
            if stack and stack[-1][1] in ("note", "detail", "legend"):
                owner = stack[-1][2]
                target = legend if owner == "__legend__" else nodes[owner]["details"]
                target.append((max(0, stack[-1][0]), _clean(raw)))
            continue

        lvl = _level(m.group("ws"), unit)
        txt = _clean(m.group("text"))
        while stack and stack[-1][0] >= lvl:
            stack.pop()

        container = next((s for s in reversed(stack) if s[1] in ("note", "legend")), None)
        if container:
            rel = lvl - container[0] - 1 + container[3]
            if container[1] == "legend":
                legend.append((rel, txt))
            else:
                nodes[container[2]]["details"].append((rel, txt))
            stack.append((lvl, "detail", container[2], 0))
            continue

        owner = next((s[2] for s in reversed(stack) if s[1] == "node"), section)

        if txt.startswith("📖"):
            stack.append((lvl, "legend", "__legend__", 0))
            continue
        if txt.startswith("📝"):
            nodes[owner]["has_note"] = True
            rest = txt[1:].strip()
            if rest:
                nodes[owner]["details"].append((0, rest))
            stack.append((lvl, "note", owner, 0))
            continue

        tm = TASK_RE.match(txt)
        if tm:
            body, star = pop_mark(tm.group("rest") or "", "star")
            body, todo = pop_mark(body, "todo")
            nid, title, extra, conclusion = split_node_text(body)
            title, ntype = pop_type(title)
            title = title or "（未命名）"
            k = sum(1 for c in nodes[owner]["children"] if nodes[c]["kind"] == "node") + 1
            nid = nid or auto_id(owner, nodes[owner]["kind"], k)
            nid = new_node(nid, "node", title, owner, ln_no, TASK_STATUS.get(tm.group("ch"), "open"), conclusion, extra)
            nodes[nid]["syntax"] = "task"
            nodes[nid]["star"], nodes[nid]["todo"], nodes[nid]["type"] = star, todo, ntype
            stack.append((lvl, "node", nid, 0))
            continue

        nm = NODE_RE.match(txt)
        if nm:
            rest = nm.group("rest").strip()
            extra, conclusion = rest, ""
            for sep in ("=>", "→"):
                if sep in rest:
                    extra, conclusion = (x.strip() for x in rest.split(sep, 1))
                    break
            nid = new_node(nm.group("id"), "node", nm.group("title").strip(), owner, ln_no,
                           STATUS.get(nm.group("st") or "", "none"), conclusion, extra)
            if not nm.group("st"):
                issues.append({"level": "warn", "line": ln_no, "msg": f"[{nid}] 没有状态符号"})
            nodes[nid]["syntax"] = "legacy"
            stack.append((lvl, "node", nid, 0))
            continue

        # 节点下面的普通列表行 = 说明。（旧的加粗写法要求放进 📝，check 会提醒）
        owner_lvl = next((s[0] for s in reversed(stack) if s[1] == "node"), lvl - 1)
        rel = max(0, lvl - owner_lvl - 1)
        nodes[owner]["details"].append((rel, txt))
        if nodes[owner]["syntax"] == "legacy":
            nodes[owner]["legacy_details"] = True
        stack.append((lvl, "note", owner, rel + 1))  # 子项也算详情

    # why（可以多行：`why:` 那行 + 它下面缩进的子条目）/ 引用 / 反向引用
    for n in nodes.values():
        items: List[list] = []
        inside, shift = False, 0
        for rel, t in n["details"]:
            if rel == 0:
                inside = bool(WHY_RE.match(t))
                if inside:
                    head = WHY_RE.sub("", t).strip()
                    shift = 0 if head else 1  # 只写了 "why:"，内容全在子条目里
                    if head:
                        items.append([0, head])
            elif inside:
                items.append([rel - shift, t])
        n["why_items"] = items
        n["why"] = " ".join(t for r, t in items if r == 0)
        blob = " ".join([n["extra"], n["conclusion"]] + [t for _, t in n["details"]])
        blob = WIKILINK_RE.sub(" ", blob)
        refs = []
        for r in REF_RE.findall(blob):
            if r != n["id"] and r not in refs:
                refs.append(r)
        n["refs"] = refs
    for n in nodes.values():
        for r in n["refs"]:
            if r in nodes:
                nodes[r]["backrefs"].append(n["id"])
            else:
                issues.append({"level": "error", "line": n["line"], "msg": f"[{n['id']}] 引用了不存在的编号 [{r}]"})
        if n["kind"] == "node":
            if n["legacy_details"]:
                issues.append({"level": "warn", "line": n["line"], "msg": f"[{n['id']}] 有属性没放进 📝（旧格式，导图里会和子问题混在一起）"})
            if not n["why_items"]:
                issues.append({"level": "info", "line": n["line"], "msg": f"[{n['id']}] 没写 why（为什么 branch 到这里）"})

    for n in nodes.values():
        n["details"] = [list(d) for d in n["details"]]
    return {"root": root, "nodes": nodes, "order": order,
            "legend": [list(x) for x in legend], "issues": issues}


# ---------------------------------------------------------------- vault / links

def find_vault(start: Path) -> Optional[Path]:
    for p in [start] + list(start.parents):
        if (p / ".obsidian").is_dir():
            return p
    return None


class VaultIndex:
    """basename / 相对路径 → 文件，用来解析 [[wikilink]] 并生成 obsidian:// 链接。"""

    def __init__(self, vault: Optional[Path]):
        self.vault = vault
        self.name = vault.name if vault else ""
        self.by_key: Dict[str, List[str]] = {}
        if not vault:
            return
        for root, dirs, files in os.walk(vault):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if not f.endswith(".md"):
                    continue
                rel = _posix(os.path.relpath(os.path.join(root, f), vault)[:-3])
                self.by_key.setdefault(f[:-3], []).append(rel)
                self.by_key.setdefault(rel, []).append(rel)

    def url(self, rel: str) -> str:
        return f"obsidian://open?vault={quote(self.name)}&file={quote(rel)}"

    def resolve(self, target: str) -> Optional[dict]:
        name = target.split("|", 1)[0].split("#", 1)[0].strip()
        hits = self.by_key.get(name)
        if not hits:
            return None
        return {"path": hits[0], "url": self.url(hits[0]), "ambiguous": len(hits) > 1}


def build_data(tree_path: Path) -> dict:
    text = tree_path.read_text(encoding="utf-8")
    data = parse(text)
    vault = find_vault(tree_path.parent)
    idx = VaultIndex(vault)
    links = {}
    for m in WIKILINK_RE.finditer(text):
        tgt = m.group(1)
        if tgt in links:
            continue
        r = idx.resolve(tgt)
        links[tgt] = r
        if r is None:
            line = text[: m.start()].count("\n") + 1
            data["issues"].append({"level": "error", "line": line, "msg": f"链接找不到文件：[[{tgt}]]"})
        elif r["ambiguous"]:
            line = text[: m.start()].count("\n") + 1
            data["issues"].append({"level": "warn", "line": line, "msg": f"链接有重名文件，用了 {r['path']}：[[{tgt}]]"})
    rel_tree = _posix(os.path.relpath(tree_path, vault)[:-3]) if vault else tree_path.stem
    mtime = tree_path.stat().st_mtime
    data["links"] = links
    data["meta"] = {
        "source": str(tree_path),
        "source_url": idx.url(rel_tree) if vault else "",
        "vault": idx.name,
        "mtime": mtime,
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "history_since": track_edits(tree_path, data, mtime, seed=lambda n: _seed_date(n, mtime, idx, links)),
    }
    return data


# ---------------------------------------------------------------- output

def render_html(data: Optional[dict], live: bool) -> str:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    if live:
        boot = "<script>window.__LIVE__ = true;</script>"
        css = '<link rel="stylesheet" href="style.css">'
        js = '<script src="app.js"></script>'
    else:
        payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        boot = f"<script>window.__TREE__ = {payload};</script>"
        css = "<style>\n" + (WEB / "style.css").read_text(encoding="utf-8") + "\n</style>"
        js = "<script>\n" + (WEB / "app.js").read_text(encoding="utf-8") + "\n</script>"
    return html.replace("<!--BOOT-->", boot).replace("<!--CSS-->", css).replace("<!--JS-->", js)


def cmd_check(tree: Path) -> int:
    data = build_data(tree)
    n_nodes = sum(1 for n in data["nodes"].values() if n["kind"] == "node")
    by_status: Dict[str, int] = {}
    for n in data["nodes"].values():
        if n["kind"] == "node":
            by_status[n["status"]] = by_status.get(n["status"], 0) + 1
    print(f"{tree.name}: {n_nodes} 个节点 {by_status}，{len(data['links'])} 个不同链接")
    icon = {"error": "✗", "warn": "!", "info": "·"}
    for it in sorted(data["issues"], key=lambda x: x["line"]):
        print(f"  {icon[it['level']]} 第 {it['line']} 行：{it['msg']}")
    errors = sum(1 for it in data["issues"] if it["level"] == "error")
    print("没有错误" if not errors else f"{errors} 个错误")
    return 1 if errors else 0


# ---------------------------------------------------------------- recent / discover

STATE_DIR = Path(os.environ.get("THINKTREE_HOME", str(Path.home() / ".thinktree")))
RECENT_FILE = STATE_DIR / "recent.json"
RECENT_MAX = 20
_recent_lock = threading.Lock()


def load_recent() -> List[dict]:
    try:
        items = json.loads(RECENT_FILE.read_text(encoding="utf-8"))
        return [it for it in items if isinstance(it, dict) and it.get("path")]
    except Exception:
        return []


def save_recent(items: List[dict]):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RECENT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items[:RECENT_MAX], ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(RECENT_FILE)


def summarize(data: dict) -> dict:
    qs = [n for n in data["nodes"].values() if n["kind"] == "node"]
    status: Dict[str, int] = {}
    for n in qs:
        status[n["status"]] = status.get(n["status"], 0) + 1
    return {"title": data["nodes"]["root"]["title"], "nodes": len(qs), "status": status,
            "todo": sum(1 for n in qs if n.get("todo")),
            "errors": sum(1 for i in data["issues"] if i["level"] == "error")}


def display_path(path: Path) -> str:
    """vault 里的文件显示成 "vault / 相对路径"，否则用 ~ 缩写。"""
    vault = find_vault(path.parent)
    if vault:
        parts = Path(os.path.relpath(path, vault)).parts
        return " / ".join([vault.name] + (["…"] if len(parts) > 2 else []) + list(parts[-2:]))
    home = str(Path.home())
    return "~" + str(path)[len(home):] if str(path).startswith(home) else str(path)


def touch_recent(path: Path, data: dict, bump: bool):
    """bump=True：用户刚打开，移到最前；False：只刷新摘要（自动刷新时）。"""
    with _recent_lock:
        items = load_recent()
        idx = next((i for i, it in enumerate(items) if it["path"] == str(path)), None)
        entry = {"path": str(path), **summarize(data), "opened": time.time()}
        if idx is not None and not bump:
            entry["opened"] = items[idx].get("opened", entry["opened"])
            items[idx] = entry
        else:
            if idx is not None:
                items.pop(idx)
            items.insert(0, entry)
        save_recent(items)


def forget_recent(path: str):
    with _recent_lock:
        save_recent([it for it in load_recent() if it["path"] != path])


def _looks_like_tree(path: Path) -> bool:
    if path.name == "Tree.md":
        return True
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(600)
    except OSError:
        return False
    return head.startswith("---") and re.search(r"^thinktree:\s*true\s*$", head.split("\n---", 1)[0], re.M) is not None


def _obsidian_config_files() -> List[Path]:
    """Obsidian 记录所有 vault 的 obsidian.json 可能在的位置（按系统 / 安装方式）。"""
    home = Path.home()
    if sys.platform == "darwin":
        return [home / "Library" / "Application Support" / "obsidian" / "obsidian.json"]
    if WINDOWS:
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "obsidian" / "obsidian.json"] if appdata else []
    xdg = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return [xdg / "obsidian" / "obsidian.json",
            home / ".var" / "app" / "md.obsidian.Obsidian" / "config" / "obsidian" / "obsidian.json",  # Flatpak
            home / "snap" / "obsidian" / "current" / ".config" / "obsidian" / "obsidian.json"]  # Snap


def obsidian_vaults() -> List[Path]:
    """Obsidian 里打开过的所有 vault（读 Obsidian 自己的 obsidian.json），最近用过的在前。"""
    found: List[Tuple[float, Path]] = []
    for f in _obsidian_config_files():
        try:
            vaults = json.loads(f.read_text(encoding="utf-8")).get("vaults", {})
        except (OSError, ValueError, AttributeError):
            continue
        for v in vaults.values():
            p = Path(v.get("path", "")) if isinstance(v, dict) else None
            if p and p.is_dir() and all(p != q for _, q in found):
                found.append((v.get("ts") or 0, p))
    return [p for _, p in sorted(found, key=lambda x: -x[0])]


def discover(extra_roots: List[Path]) -> List[dict]:
    """在 vault 里找 tree：文件名是 Tree.md，或 frontmatter 有 `thinktree: true`。
    扫哪些目录：环境变量 THINKTREE_VAULTS（多个用 os.pathsep 分隔：Mac 冒号、Windows 分号）
    + 最近打开过的 tree 所在的 vault + Obsidian 里登记的所有 vault。"""
    env_roots = [Path(p).expanduser() for p in os.environ.get("THINKTREE_VAULTS", "").split(os.pathsep) if p.strip()]
    roots = []
    for r in env_roots + extra_roots + obsidian_vaults():
        r = r.resolve()  # 和最近列表里的路径（都 resolve 过）对得上
        if r not in roots:
            roots.append(r)
    found, seen = [], set()
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            for f in files:
                p = Path(d) / f
                if f.endswith(".md") and str(p) not in seen and _looks_like_tree(p):
                    seen.add(str(p))
                    title = ""
                    try:
                        m = re.search(r"^# (.+)$", p.read_text(encoding="utf-8", errors="ignore"), re.M)
                        title = m.group(1).strip() if m else ""
                    except OSError:
                        pass
                    found.append({"path": str(p), "title": title or p.parent.name, "display": display_path(p)})
    return found


# ---------------------------------------------------------------- 编辑历史（每个节点的最后编辑时间）
# Tree.md 里没有时间信息，所以每次文件变了就和上一份快照比，记下哪些节点被改过。
# 编号按位置生成、插入节点后会变，所以快照里用内部 uid，靠 _match() 把新旧节点对上。
# 快照放在 ~/.thinktree/history/<路径哈希>.json，删掉只是丢历史，不影响 tree。

HISTORY_DIR = STATE_DIR / "history"
MINOR_EDIT = 5  # 改动少于这么多字符（修错字之类）不算编辑；改状态总算
KEEP_DAYS = 60  # 每个节点的编辑日期只留最近这么多天
_history_lock = threading.Lock()
MMDD_RE = re.compile(r"(?<!\d)(\d{1,2})-(\d{1,2})(?!\d)")


def _history_file(path: Path) -> Path:
    return HISTORY_DIR / (hashlib.sha1(str(path).encode()).hexdigest()[:16] + ".json")


def _own_text(n: dict) -> str:
    """节点自己的文字（标题、附加、结论、why、详情），不含子节点。"""
    return "\n".join([n["title"], n["extra"], n["conclusion"]] + [t for _, t in n["details"]])


def _changed_chars(a: str, b: str) -> int:
    if a == b:
        return 0
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in ops if op != "equal")


def _match(nodes: Dict[str, dict], old: Dict[str, dict]) -> Dict[str, str]:
    """新节点 id → 旧快照 uid。从根往下：同一父节点下先找标题相同的，再找标题相近的（改了标题）；
    都没有就在全树找标题相同的（挪了位置）。剩下的就是新建的节点。"""
    m, used = {"root": "root"}, {"root"}
    kids_of: Dict[str, List[str]] = {}
    for u, o in old.items():
        kids_of.setdefault(o["parent"], []).append(u)
    queue = ["root"]
    while queue:
        pid = queue.pop(0)
        kids = nodes[pid]["children"]
        queue.extend(kids)
        cands = kids_of.get(m[pid], []) if pid in m else []
        rest = []
        for c in kids:
            u = next((u for u in cands if u not in used and old[u]["title"] == nodes[c]["title"]), None)
            if u:
                m[c] = u
                used.add(u)
            else:
                rest.append(c)
        for c in rest:
            t = nodes[c]["title"]
            best, score = None, 0.6
            for u in cands:
                if u not in used:
                    r = difflib.SequenceMatcher(None, old[u]["title"], t).ratio()
                    if r > score:
                        best, score = u, r
            if best is None and t:
                best = next((u for u, o in old.items() if u not in used and o["title"] == t), None)
            if best:
                m[c] = best
                used.add(best)
    return m


def _seed_date(n: dict, now: float, idx: "VaultIndex", links: dict) -> Optional[float]:
    """第一次建快照时没有历史，先估一个最后编辑时间（取最晚的）：
    节点上手写的日期（例如 "（10-02）"），以及节点里 [[链接]] 的笔记的修改时间。"""
    cands = []
    ref = datetime.fromtimestamp(now)
    for mo in MMDD_RE.finditer(n["extra"]):
        try:
            d = datetime(ref.year, int(mo.group(1)), int(mo.group(2)), 12)
        except ValueError:
            continue
        cands.append((d.replace(year=ref.year - 1) if d > ref else d).timestamp())
    for m in WIKILINK_RE.finditer(_own_text(n)):
        r = links.get(m.group(1))
        if r and idx.vault:
            try:
                cands.append(min(now, (idx.vault / (r["path"] + ".md")).stat().st_mtime))
            except OSError:
                pass
    return max(cands) if cands else None


def _adopt_moved(path: Path, data: dict) -> Optional[dict]:
    """tree 文件被移动 / 改名后路径变了：找一份原路径已不存在、节点标题大多对得上的历史接着用。"""
    titles = {n["title"] for n in data["nodes"].values() if n["kind"] != "root"}
    best, score = None, 0.5
    for f in HISTORY_DIR.glob("*.json"):
        try:
            h = json.loads(f.read_text(encoding="utf-8"))
            if Path(h["path"]).exists():
                continue
            old = {o["title"] for o in h["nodes"].values()}
            r = len(titles & old) / max(1, len(titles | old))
        except (OSError, ValueError, KeyError):
            continue
        if r > score:
            best, score = (f, h), r
    if not best:
        return None
    f, h = best
    f.unlink()  # 搬到新路径的文件名下，旧的删掉（避免被别的 tree 再领走）
    h["path"] = str(path)
    return h


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def track_edits(path: Path, data: dict, mtime: float, seed=None) -> Optional[float]:
    """和上一份快照比，给每个节点写上
      edited  最后编辑时间（秒；不知道是 None）
      created 第一次出现的时间（建快照之前就有的节点是 None）
      days    编辑过的日期 ["2026-10-05", ...]（新建也算），给日历和范围筛选用
    改动的时间记成文件的 mtime。seed(node)：第一次建快照时估计的时间；不给就不建快照。
    返回开始记录的时间。"""
    nodes = data["nodes"]
    with _history_lock:
        f = _history_file(path)
        try:
            h = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            h = None
        if h is None:
            h = _adopt_moved(path, data)
        fresh = h is None
        if fresh and seed is None:  # 后台盯梢没有链接信息，第一份快照留给 build_data 建
            return None
        old = {} if fresh else h["nodes"]
        m = _match(nodes, old)
        nxt = 1 if fresh else h["next"]
        snap = {}
        for nid in data["order"]:
            n = nodes[nid]
            if nid == "root":
                continue
            text, u = _own_text(n), m.get(nid)
            if u is None:  # 新节点
                u, nxt = f"u{nxt}", nxt + 1
                m[nid] = u
                edited, base = (seed(n) if fresh else mtime), text
                created = None if fresh else mtime
                days = [_day(edited)] if edited else []
            else:
                o = old[u]
                edited, base, created = o["edited"], o["text"], o.get("created")
                days = o.get("days", [_day(edited)] if edited else [])  # 旧格式只有 edited
                if o["status"] != n["status"] or _changed_chars(base, text) >= MINOR_EDIT:
                    edited, base = mtime, text
                    if _day(mtime) not in days:
                        days = days + [_day(mtime)]
            days = [d for d in days if d >= _day(mtime - KEEP_DAYS * 86400)]
            # text 只在算作编辑时更新，这样连续的小改动累积起来也会被记上
            # 🚩 第一次出现的时间（去掉就清空）；只在这里记，不算编辑
            todo_since = (old.get(u, {}).get("todo_since") or mtime) if n["todo"] else None
            snap[u] = {"parent": m[n["parent"]], "title": n["title"], "status": n["status"], "text": base,
                       "edited": edited, "created": created, "days": days, "todo_since": todo_since}
            n.update(uid=u, edited=edited, created=created, days=days, todo_since=todo_since)
        since = mtime if fresh else h["since"]
        if fresh or snap != old or h.get("path") != str(path):
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps({"path": str(path), "since": since, "next": nxt, "nodes": snap},
                                      ensure_ascii=False), encoding="utf-8")
            tmp.replace(f)
    return since


def watch_recent(interval: float = 5.0):
    """服务开着时盯住最近打开过的 tree：没开页面时在 Obsidian 里的修改也按时记下。"""
    seen: Dict[str, float] = {}
    while True:
        for it in load_recent():
            p = Path(it["path"])
            try:
                mt = p.stat().st_mtime
                if seen.get(str(p)) != mt:
                    data = parse(p.read_text(encoding="utf-8"))
                    track_edits(p, data, mt)
                    if str(p) in seen:  # 首页卡片上的统计（含待办数）跟着更新；启动时第一轮不用
                        touch_recent(p, data, bump=False)
                    seen[str(p)] = mt
            except Exception:  # 文件被删 / 正在写一半：下一轮再说
                pass
        time.sleep(interval)


# ---------------------------------------------------------------- edit (插入节点 / 跳到 Obsidian)

def _indent_width(line: str) -> int:
    ws = line[: len(line) - len(line.lstrip(" \t"))]
    return len(ws.expandtabs(4))


def _block_end(lines: List[str], start: int) -> int:
    """节点（第 start 行，0 起）连同它所有缩进子行的最后一个非空行。"""
    base = _indent_width(lines[start])
    end = start
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if not ln.strip():
            continue
        if ln.startswith("#") or _indent_width(ln) <= base:
            break
        end = i
    return end


def _section_end(lines: List[str], start: int) -> int:
    """主枝标题（第 start 行）下面内容的最后一个非空行（到下一个 # 标题为止）。"""
    end = start
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("#"):
            break
        if lines[i].strip():
            end = i
    return end


def has_adv_uri(vault: Path) -> bool:
    """vault 里是否启用了 Advanced URI 插件（启用的插件 id 记在 community-plugins.json）。"""
    try:
        enabled = json.loads((vault / ".obsidian" / "community-plugins.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return "obsidian-advanced-uri" in enabled


def obsidian_line_url(path: Path, line: int, column: int) -> Tuple[Optional[str], bool]:
    """(链接, 能否定位到行)。有 Advanced URI 插件就打开到指定行列（1 起），否则只打开文件。"""
    vault = find_vault(path.parent)
    if not vault:
        return None, False
    rel = _posix(os.path.relpath(path, vault)[:-3])
    if not has_adv_uri(vault):
        return f"obsidian://open?vault={quote(vault.name)}&file={quote(rel)}", False
    return (f"obsidian://adv-uri?vault={quote(vault.name)}&filepath={quote(rel)}"
            f"&line={line}&column={column}"), True


def insert_node(path: Path, node_id: str, where: str, client_mtime: float) -> dict:
    """where: child（作为最后一个子节点）/ after（下面插同级）/ edit（不写，只定位到这一行）。"""
    if abs(path.stat().st_mtime - client_mtime) > 1e-3:
        raise Conflict("Tree.md 在你看的时候被改过了，页面刷新后再试")
    text = path.read_text(encoding="utf-8")
    data = parse(text)
    n = data["nodes"].get(node_id)
    if not n:
        raise BadRequest(f"找不到节点 [{node_id}]")
    lines = text.split("\n")
    if n["kind"] == "root":
        idx = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), 0)
    else:
        idx = n["line"] - 1
    if where == "edit":
        return {"line": idx + 1, "column": len(lines[idx]) + 1, "inserted": False}

    uses_tab = "\t" in text or not re.search(r"^ +[-*+] ", text, re.M)
    unit = "\t" if uses_tab else " " * _indent_unit(lines)
    if n["kind"] == "node":
        ws = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip(" \t"))]
        new = (ws + unit if where == "child" else ws) + "- [ ] "
        at = _block_end(lines, idx) + 1
    elif n["kind"] == "section" and where == "child":
        new = "- [ ] "
        at = _section_end(lines, idx) + 1
    elif where == "after" and n["kind"] == "section":
        new = "## "
        at = _section_end(lines, idx) + 1
        lines.insert(at, "")  # 主枝之间空一行
        at += 1
    else:
        raise BadRequest("根节点只能编辑，不能插入")
    lines.insert(at, new)
    write_text_atomic(path, "\n".join(lines))
    return {"line": at + 1, "column": len(new) + 1, "inserted": True}


def mark_node(path: Path, node_id: str, mark: str, client_mtime: float) -> dict:
    """切换节点标记（star ⭐ / todo 🚩）：在复选框后面加 / 去掉符号。写进 Tree.md，Obsidian 里手写也一样。"""
    if mark not in MARKS:
        raise BadRequest(f"mark 不对：{mark}")
    if abs(path.stat().st_mtime - client_mtime) > 1e-3:
        raise Conflict("Tree.md 在你看的时候被改过了，页面刷新后再试")
    text = path.read_text(encoding="utf-8")
    n = parse(text)["nodes"].get(node_id)
    if not n or n["kind"] != "node" or n["syntax"] != "task":
        raise BadRequest(f"只能给复选框节点加标记：[{node_id}]")
    lines = text.split("\n")
    m = TASK_LINE_RE.match(lines[n["line"] - 1])
    if not m:
        raise BadRequest(f"第 {n['line']} 行不是复选框节点")
    pre = m.group("pre") if m.group("pre").endswith(" ") else m.group("pre") + " "
    body, had = pop_mark(m.group("body"), mark)
    lines[n["line"] - 1] = pre + (body if had else MARKS[mark][0] + " " + body).rstrip()
    write_text_atomic(path, "\n".join(lines))
    return {"mark": mark, "on": not had, "mtime": path.stat().st_mtime}


# ---------------------------------------------------------------- server

class BadRequest(Exception):
    pass


class Conflict(Exception):
    pass


def tree_from_query(qs: dict) -> Path:
    raw = (qs.get("path") or [""])[0].strip().strip("'\"")
    if not raw:
        raise BadRequest("缺少 path 参数")
    p = Path(raw).expanduser()
    if not p.is_absolute():
        raise BadRequest(f"需要完整路径：{raw}")
    p = p.resolve()
    if p.suffix.lower() != ".md":
        raise BadRequest(f"只能打开 .md 文件：{p}")
    if not p.is_file():
        raise BadRequest(f"找不到文件：{p}")
    return p


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 安静
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8", code)

    def do_GET(self):
        # 只接受本机地址访问（防 DNS rebinding 让别的网页读本地文件）
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return self._send(b"forbidden", "text/plain", 403)
        url = urlparse(self.path)
        path, qs = url.path, parse_qs(url.query)
        try:
            if path in ("/", "/index.html"):
                self._send(render_html(None, live=True).encode(), "text/html; charset=utf-8")
            elif path in ("/app.js", "/style.css"):
                ctype = "text/javascript" if path.endswith(".js") else "text/css"
                self._send((WEB / path[1:]).read_bytes(), ctype + "; charset=utf-8")
            elif path == "/api/ping":
                self._json({"thinktree": True, "version": __version__})
            elif path == "/api/tree":
                tree = tree_from_query(qs)
                data = build_data(tree)
                data["meta"]["display"] = display_path(tree)
                touch_recent(tree, data, bump=qs.get("open") == ["1"])
                self._json(data)
            elif path == "/api/version":
                self._json({"mtime": tree_from_query(qs).stat().st_mtime})
            elif path == "/api/home":
                recent = load_recent()
                for it in recent:
                    p = Path(it["path"])
                    it["missing"] = not p.is_file()
                    it["display"] = display_path(p)
                vaults = [find_vault(Path(it["path"]).parent) for it in recent]
                seen = {it["path"] for it in recent}
                found = [f for f in discover([v for v in vaults if v]) if f["path"] not in seen]
                self._json({"recent": recent, "discovered": found, "vaults": [str(v) for v in obsidian_vaults()]})
            elif path == "/api/forget":
                forget_recent((qs.get("path") or [""])[0])
                self._json({"ok": True})
            else:
                self._send(b"not found", "text/plain", 404)
        except BadRequest as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:  # 解析出错时把错误显示在页面上，而不是让服务挂掉
            self._json({"error": repr(e)}, 500)

    def do_POST(self):
        """写操作：只接受本页面发来的 JSON（别的网站发不了：Origin 不对，JSON 也会触发预检）。"""
        host = (self.headers.get("Host") or "").split(":")[0]
        origin = self.headers.get("Origin") or ""
        port = self.server.server_address[1]
        # `thinktree stop` / 升级后自动重启：命令行发的，没有 Origin；网页发不了（自定义头会触发预检，这里不回应预检）
        if urlparse(self.path).path == "/api/stop" and host in ("127.0.0.1", "localhost") \
                and not origin and self.headers.get("X-Thinktree") == "stop":
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if host not in ("127.0.0.1", "localhost") or origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            return self._send(b"forbidden", "text/plain", 403)
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._send(b"need json", "text/plain", 415)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            route = urlparse(self.path).path
            if route not in ("/api/insert", "/api/mark"):
                return self._send(b"not found", "text/plain", 404)
            tree = tree_from_query({"path": [body.get("path", "")]})
            if str(tree) not in {it["path"] for it in load_recent()}:
                raise BadRequest("只能修改在查看器里打开过的 tree")
            if route == "/api/mark":
                return self._json(mark_node(tree, str(body.get("id", "")), str(body.get("mark", "")), float(body.get("mtime", 0))))
            where = body.get("where")
            if where not in ("child", "after", "edit"):
                raise BadRequest(f"where 不对：{where}")
            res = insert_node(tree, str(body.get("id", "")), where, float(body.get("mtime", 0)))
            res["url"], res["at_line"] = obsidian_line_url(tree, res["line"], res["column"])
            res["mtime"] = tree.stat().st_mtime
            self._json(res)
        except BadRequest as e:
            self._json({"error": str(e)}, 400)
        except Conflict as e:
            self._json({"error": str(e)}, 409)
        except Exception as e:
            self._json({"error": repr(e)}, 500)


def page_url(port: int, tree: Optional[Path]) -> str:
    return f"http://127.0.0.1:{port}/" + (f"?tree={quote(str(tree), safe='/')}" if tree else "")


def running_version(port: int) -> Optional[str]:
    """端口上在跑的 thinktree 的版本；没在跑是 None，太旧（不报版本）是 ""。"""
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=0.6) as r:
            d = json.loads(r.read())
    except Exception:
        return None
    return str(d.get("version", "")) if d.get("thinktree") is True else None


def stop_server(port: int) -> bool:
    """让在跑的服务退出，等端口空出来。旧版本没有 /api/stop，返回 False。"""
    req = Request(f"http://127.0.0.1:{port}/api/stop", data=b"{}", method="POST",
                  headers={"X-Thinktree": "stop", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=2) as r:
            if not json.loads(r.read()).get("ok"):
                return False
    except Exception:
        return False
    for _ in range(30):
        if running_version(port) is None:
            return True
        time.sleep(0.1)
    return False


class Server(ThreadingHTTPServer):
    # Windows 上 SO_REUSEADDR 允许两个进程占同一个端口，关掉才能发现"已经有一个在跑"
    allow_reuse_address = not WINDOWS


def cmd_open(tree: Optional[Path], port: int, open_browser: bool) -> int:
    url = page_url(port, tree)
    ver = running_version(port)
    if ver == __version__:  # 已经开着：只打开浏览器，不再起第二个
        print(f"thinktree 已在运行 → {url}")
        if open_browser:
            webbrowser.open(url)
        return 0
    if ver is not None:  # 在跑的是另一个版本（通常是刚升级）：停掉旧的，换成现在这个
        if stop_server(port):
            print(f"已停掉旧版本的 thinktree（{ver or '很旧的版本'}），换成 {__version__}", flush=True)
        else:
            print(f"端口 {port} 上有一个旧版本的 thinktree 在跑，没法自动停掉。\n"
                  "关掉运行它的终端窗口（或 Mac：pkill -f thinktree；Windows：任务管理器结束 python）后再试。",
                  file=sys.stderr)
            return 1
    try:
        srv = Server(("127.0.0.1", port), Handler)
    except OSError:
        print(f"端口 {port} 被别的程序占用了，用 --port 换一个", file=sys.stderr)
        return 1
    threading.Thread(target=watch_recent, daemon=True).start()
    print(f"thinktree {__version__} → {url}\n"
          "这个窗口要一直开着；关掉窗口或按 Ctrl+C 就停止。", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
        print("thinktree 已停止（被 thinktree stop 或新版本替换）")
    except KeyboardInterrupt:
        print()
    finally:
        srv.server_close()
    return 0


def cmd_stop(port: int) -> int:
    ver = running_version(port)
    if ver is None:
        print(f"端口 {port} 上没有在跑的 thinktree")
        return 0
    if stop_server(port):
        print("已停止")
        return 0
    print("停不掉（可能是旧版本）：关掉运行它的终端窗口即可", file=sys.stderr)
    return 1


def cmd_recent() -> int:
    items = load_recent()
    if not items:
        print("还没有打开过任何 tree")
    for it in items:
        when = time.strftime("%m-%d %H:%M", time.localtime(it.get("opened", 0)))
        print(f"{when}  {it.get('title', '')}  ({it.get('nodes', 0)} 个问题)\n           {it['path']}")
    return 0


def resolve_tree(p: Path) -> Optional[Path]:
    tree = p.expanduser().resolve()
    if not tree.is_file() or tree.suffix.lower() != ".md":
        print(f"找不到 .md 文件：{tree}", file=sys.stderr)
        return None
    return tree


# ---------------------------------------------------------------- init：新建 tree + 设置 vault

ADV_URI_ID = "obsidian-advanced-uri"
DEFAULT_FOLDER = "思考Tree"


def _ask(prompt: str, default: str = "") -> str:
    try:
        ans = input(prompt).strip().strip("'\"")
    except EOFError:
        ans = ""
    return ans or default


def _yes(prompt: str) -> bool:
    return _ask(prompt + " [Y/n] ", "y").lower() in ("y", "yes", "是")


def _pick_folder() -> Optional[Path]:
    """没给文件夹时问用户：选一个 Obsidian vault，再给子文件夹名。"""
    if not sys.stdin.isatty():
        print("请给出文件夹：thinktree init <文件夹>", file=sys.stderr)
        return None
    here = find_vault(Path.cwd())
    vaults = ([here] if here else []) + [v for v in obsidian_vaults() if v.resolve() != (here.resolve() if here else None)]
    if vaults:
        print("找到这些 Obsidian vault：")
        for i, v in enumerate(vaults, 1):
            print(f"  {i}) {v.name}    {v}")
        ans = _ask("选一个（输入编号），或者粘贴别的文件夹路径 [1]：", "1")
        base = vaults[int(ans) - 1] if ans.isdigit() and 1 <= int(ans) <= len(vaults) else Path(ans).expanduser()
    else:
        print("没找到 Obsidian vault（Obsidian 没装，或者还没打开过任何 vault）。")
        ans = _ask("粘贴一个文件夹路径（建议放在 vault 里）：")
        if not ans:
            return None
        base = Path(ans).expanduser()
    sub = _ask(f"在 {base.name} 里的哪个子文件夹建 tree？（回车 = {DEFAULT_FOLDER}，输入 . = 直接放在这里）：", DEFAULT_FOLDER)
    return base if sub == "." else base / sub


def setup_vault(vault: Path, interactive: bool):
    """给 vault 装上高亮跳转行的 CSS snippet，并检查 Advanced URI 插件。可以重复运行。"""
    obs = vault / ".obsidian"
    snippet = obs / "snippets" / "thinktree.css"
    if snippet.exists():
        print(f"  ✓ CSS snippet 已存在：{snippet}")
    else:
        snippet.parent.mkdir(parents=True, exist_ok=True)
        snippet.write_text((TEMPLATES / "thinktree.css").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  ✓ 装好 CSS snippet：{snippet}")
    appearance = obs / "appearance.json"
    try:
        conf = json.loads(appearance.read_text(encoding="utf-8")) if appearance.exists() else {}
    except ValueError:
        conf = None  # 文件坏了就别碰
    if isinstance(conf, dict) and "thinktree" not in conf.get("enabledCssSnippets", []):
        conf["enabledCssSnippets"] = conf.get("enabledCssSnippets", []) + ["thinktree"]
        appearance.write_text(json.dumps(conf, ensure_ascii=False, indent=2), encoding="utf-8")
        print("  ✓ 已启用 snippet（Obsidian 开着的话：设置 → 外观 → CSS 代码片段，确认 thinktree 是打开的）")

    installed = (obs / "plugins" / ADV_URI_ID).is_dir()
    if has_adv_uri(vault):
        print("  ✓ Advanced URI 插件已启用（点「编辑」能跳到 Tree.md 的那一行）")
        return
    print("  ! " + ("Advanced URI 插件装了但没启用" if installed else "还没装 Advanced URI 插件") +
          "：不装也能用，只是点「编辑」时只能打开文件、跳不到那一行。\n"
          "    装法：Obsidian → 设置 → 第三方插件 → 关闭安全模式 → 浏览 → 搜 Advanced URI → 安装 → 启用")
    if interactive and _yes("    现在在 Obsidian 里打开这个插件的页面？"):
        webbrowser.open(f"obsidian://show-plugin?id={ADV_URI_ID}")


def cmd_init(target: Optional[Path], title: Optional[str], open_after: bool) -> int:
    interactive = sys.stdin.isatty()
    if target is None:
        target = _pick_folder()
        if target is None:
            return 1
    target = target.expanduser().resolve()
    tree = target if target.suffix.lower() == ".md" else target / "Tree.md"
    folder = tree.parent
    folder.mkdir(parents=True, exist_ok=True)
    print()
    if tree.exists():
        print(f"  · 已经有 {tree}，不覆盖")
    else:
        text = (TEMPLATES / "Tree.md").read_text(encoding="utf-8")
        text = text.replace("{{title}}", title or f"{folder.name} 思考 Tree").replace("{{today}}", time.strftime("%m-%d"))
        tree.write_text(text, encoding="utf-8")
        print(f"  ✓ 新建 {tree}（里面是示例，看懂格式后换成你自己的内容）")
    guide = folder / "CLAUDE.md"
    if guide.exists():
        print(f"  · 已经有 {guide}，不覆盖")
    else:
        guide.write_text((TEMPLATES / "CLAUDE.md").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  ✓ 新建 {guide}（给 AI 看的格式说明；用 Codex / Cursor 的话改名成 AGENTS.md）")
    vault = find_vault(folder)
    if vault:
        print(f"\nvault「{vault.name}」的设置：")
        setup_vault(vault, interactive)
    else:
        print("\n  ! 这个文件夹不在 Obsidian vault 里：查看器照样能用，但 [[链接]] 和「在 Obsidian 里编辑」不行。\n"
              "    在 Obsidian 里「打开文件夹作为仓库」选它（或它的上级），再运行一次 thinktree init 就会自动设置。")
    print(f"\n之后打开：thinktree \"{tree}\"（或者直接运行 thinktree，在首页点它）")
    if open_after and interactive and _yes("\n现在就打开查看器？"):
        return cmd_open(tree, int(os.environ.get("THINKTREE_PORT", 8765)), True)
    return 0


def cmd_prompt() -> int:
    print((TEMPLATES / "CLAUDE.md").read_text(encoding="utf-8"))
    return 0


COMMANDS = ("open", "serve", "init", "build", "check", "json", "prompt", "recent", "stop")


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows 终端 / 管道不是 UTF-8 时，打不出来的字符换成 ? 而不是报错
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    # `thinktree` / `thinktree X.md` / `thinktree --port 9000` 都等于 open
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help", "-V", "--version")):
        argv = ["open"] + argv
    ap = argparse.ArgumentParser(prog="thinktree", description=__doc__.split("\n")[0],
                                 epilog="不写子命令 = open。例：thinktree / thinktree Tree.md / thinktree init")
    ap.add_argument("-V", "--version", action="version", version=f"thinktree {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("open", "serve"):
        s = sub.add_parser(name, help="启动查看器（已在运行就只开浏览器）；不给文件就打开首页")
        s.add_argument("tree", type=Path, nargs="?")
        s.add_argument("--port", type=int, default=int(os.environ.get("THINKTREE_PORT", 8765)))
        s.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    b = sub.add_parser("build", help="导出单文件 HTML")
    b.add_argument("tree", type=Path)
    b.add_argument("-o", "--out", type=Path)
    c = sub.add_parser("check", help="检查格式和链接")
    c.add_argument("tree", type=Path)
    j = sub.add_parser("json", help="输出解析结果")
    j.add_argument("tree", type=Path)
    i = sub.add_parser("init", help="新建一个 tree（示例 Tree.md + CLAUDE.md），并设置好所在的 Obsidian vault")
    i.add_argument("tree", type=Path, nargs="?", help="放 tree 的文件夹（或 .md 文件路径）；不给就一步步问")
    i.add_argument("--title", help="tree 的标题（默认用文件夹名）")
    i.add_argument("--no-open", action="store_true", help="建好后不问要不要打开")
    sub.add_parser("prompt", help="输出给 AI 的格式说明（复制给 ChatGPT / Claude）")
    sub.add_parser("recent", help="列出最近打开的 tree")
    st = sub.add_parser("stop", help="停掉在跑的查看器")
    st.add_argument("--port", type=int, default=int(os.environ.get("THINKTREE_PORT", 8765)))
    a = ap.parse_args(argv)

    if a.cmd == "recent":
        return cmd_recent()
    if a.cmd == "prompt":
        return cmd_prompt()
    if a.cmd == "stop":
        return cmd_stop(a.port)
    if a.cmd == "init":
        return cmd_init(a.tree, a.title, not a.no_open)
    tree = resolve_tree(a.tree) if a.tree else None
    if a.tree and not tree:
        return 2
    if a.cmd in ("open", "serve"):
        return cmd_open(tree, a.port, not a.no_open)
    if a.cmd == "build":
        out = (a.out or tree.with_suffix(".html")).expanduser().resolve()
        out.write_text(render_html(build_data(tree), live=False), encoding="utf-8")
        print(f"写入 {out}")
    elif a.cmd == "check":
        return cmd_check(tree)
    elif a.cmd == "json":
        print(json.dumps(build_data(tree), ensure_ascii=False, indent=1))
    return 0


