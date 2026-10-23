# thinktree 开发说明

给想改代码、加功能的人看。用法见 [README](../README.md)。

## 从源码运行 / 开发

```bash
git clone https://github.com/Jiangnan0522/thinktree && cd thinktree
python3 thinktree.py            # 不用安装，直接从源码跑（等同于 thinktree 命令）
# 或者装成可编辑模式，改了代码立刻生效：
uv tool install -e .            # 或 pip install -e .
```

- 改了 `src/thinktree/cli.py`（Python）要重启服务：`thinktree stop && thinktree`（再敲 `thinktree` 只会复用在跑的进程；
  只有版本号不同时才会自动替换）。`web/` 下的文件不用重启，刷新页面即可。
- 旧进程没有某个接口时，页面会报 `Unexpected token '<'`（拿到的是 Python 默认的 HTML 错误页），重启服务就好。
- **发版**：改 `src/thinktree/__init__.py` 里的 `__version__`。版本号变了，同学升级后再运行 `thinktree` 会自动停掉旧服务换成新的
  （`/api/ping` 返回版本，`/api/stop` 只接受命令行发来的、没有 Origin 且带 `X-Thinktree: stop` 头的请求）。
- 状态目录 `~/.thinktree/`（环境变量 `THINKTREE_HOME` 可改），测试时指到临时目录就不会弄乱自己的记录；端口用 `THINKTREE_PORT` 或 `--port`。

## 结构（加功能时看这里）

```
thinktree.py                 从源码运行的入口（插入 src/ 到 sys.path 再调 cli.main）
pyproject.toml               打包配置；命令 thinktree = thinktree.cli:main；web/ 和 templates/ 作为 package data
src/thinktree/
  __init__.py                __version__
  cli.py                     全部后端：
                               parse() → 数据；VaultIndex 解析 [[wikilink]] → obsidian:// 链接；
                               build_data() 组装（含 track_edits() 写每个节点的编辑时间）；render_html() 拼页面；
                               obsidian_vaults() 读 Obsidian 的 obsidian.json 找 vault；discover() 在 vault 里找 tree；
                               insert_node() / mark_node() 写文件；Handler 是 HTTP 服务；cmd_*() 是各个子命令
  web/index.html             页面骨架；<!--CSS--> <!--BOOT--> <!--JS--> 三个占位符由 render_html() 替换
  web/style.css              样式（颜色都是 :root 变量，自动适配深色模式）
  web/app.js                 前端：build() 把数据转成 markmap 节点；renderPanel() 画侧边栏；poll() 自动刷新；renderHome() 首页
  templates/                 thinktree init 用的模板：Tree.md（示例）、CLAUDE.md（给 AI 的说明，也是 thinktree prompt 的输出）、
                             thinktree.css（装进 <vault>/.obsidian/snippets/ 的高亮片段）
```

服务端接口：`/api/tree?path=`（每次重新解析；带 `open=1` 时记入最近）、`/api/version?path=`（mtime，前端每 1.5 秒轮询）、`/api/home`（最近 + 发现 + Obsidian vault 列表）、`/api/forget?path=`、`/api/ping`（返回版本）；
POST：`/api/insert`、`/api/mark`（页面发）、`/api/stop`（命令行发）。
前端按网址判断模式：有 `window.__TREE__` = build 出来的静态页；有 `?tree=` = 看某个 tree；都没有 = 首页（`renderHome()`）。

数据格式（`json` 子命令输出）：

```
{ root: "root", order: [id...], legend: [[缩进, 文本]...], issues: [{level, line, msg}...],
  links: { "[[里的原文]]": {path, url, ambiguous} | null },
  meta:  { source, source_url, vault, mtime, generated, history_since },
  nodes: { id: { id, kind: root|section|node, status, title, extra, conclusion,
                 details: [[缩进, 文本]...], why, parent, children: [id...],
                 type: exp|think|"", refs: [id...], backrefs: [id...], line, uid: "u12"（编辑历史里的稳定编号，插入节点后不变）, edited: 秒 | null, created: 秒 | null, days: ["YYYY-MM-DD"...] } } }
```

### 想加的功能可以从这些地方下手

- 新的节点属性（例如 `date:`、`owner:`）：在 parse() 末尾"why / 引用"那段里，像 `why` 一样从 details 中抽出来；前端在 renderPanel() 里显示。
- 新的检查规则：parse() 或 build_data() 里往 `issues` 追加；页面 `?` 面板和 `check` 命令会自动显示。
- 新视图（时间线、只看开放问题的列表等）：在 app.js 里基于 `st.data.nodes` 另写渲染函数，工具栏加按钮切换。
- 更多写操作（例如在页面上直接改状态）：仿照 `insert_node()` + `do_POST` 的 `/api/insert`，按 `line` 定位修改，改前比对 mtime。

## 跨平台注意

- vault 内相对路径一律转成 `/`（`_posix()`）：Obsidian 链接和 `[[wikilink]]` 都用 `/`，Windows 的 `relpath` 给的是 `\`。
- 写 Tree.md 用 `write_text_atomic()`：临时文件 + 原子替换，保留原文件的换行风格（不然 Windows 上会把整个文件改成 CRLF），
  Obsidian 正好占着文件时重试几次。
- Windows 上 `SO_REUSEADDR` 允许两个进程占同一个端口，所以 `Server` 在 Windows 上关掉 `allow_reuse_address`。
- 终端不是 UTF-8 时（Windows 管道），`main()` 把 stdout / stderr 设成 `errors="replace"`，打不出来的字符换成 `?`。
- Obsidian 的 vault 列表：Mac `~/Library/Application Support/obsidian/obsidian.json`，Windows `%APPDATA%\obsidian\obsidian.json`，
  Linux `~/.config/obsidian/`（以及 Flatpak / Snap 的位置），见 `_obsidian_config_files()`。

## 在图上插入节点 / 跳到 Obsidian 编辑

选中节点后，侧边栏有 **＋ 子问题**（快捷键 `a`）、**＋ 同级**（`s`；主枝上是"新主枝"）、**✎ 编辑**（`e`）：
插入时在 Tree.md 对应位置写入一行空的 `- [ ] `（缩进自动对齐），然后让 Obsidian 打开到那一行；编辑只跳转不写入。
图会自动刷新并选中新节点（空节点显示为"（未命名）"）。

- 写入保护：只接受本页面发来的 JSON POST（检查 Origin）；只能写"在查看器里打开过"（在最近列表里）的 tree；
  文件在你看的这段时间被改过就拒绝（409），刷新后再试。
- **加星 / 待办**：在复选框后面加 / 去掉 `⭐` / `🚩`（`mark_node()`，`/api/mark`，标记定义在 `MARKS`），同样的写入保护。加 / 去标记不算"编辑"。
- **待办提醒**：侧边栏显示"标为待办 N 天前"（🚩 第一次出现的时间记在编辑历史的 `todo_since`）。
- 工具只在这两处写 tree（`insert_node()`、`mark_node()`）；`init` 只新建文件、往 `.obsidian/appearance.json` 的 `enabledCssSnippets` 里加一项。
- 跳转链接：启用了 Advanced URI（`<vault>/.obsidian/community-plugins.json` 里有 `obsidian-advanced-uri`）时用
  `obsidian://adv-uri?vault=…&filepath=…&line=N&column=M`，否则退回 `obsidian://open`，只打开文件，页面会提示跳不到行。
  链接**故意不带 `viewmode=source`**：带了会把那个标签页切成源码模式，之后在该标签页打开的笔记也会一直是源码模式。
- Advanced URI 只放光标、不选中，所以用 CSS snippet（`templates/thinktree.css`）高亮光标所在行；
  只作用于 frontmatter 里有 `cssclasses: thinktree` 的笔记。

## 最近编辑透镜（近 3 / 7 / 14 天 + 编辑日历）

工具栏的 **🕘 最近编辑** 下拉（关 / 近 3 天 / 近 7 天 / 近 14 天，括号里是节点数；`r` 在关和上次选的天数之间切换）：这段时间编辑过的节点高亮，它们的上级（从根到它的路径）正常显示，其余节点变暗但仍可见，
用来看"最近在想什么、哪些还没结论"，同时不丢掉整体脉络。打开时默认展开到这些节点；在这个视图里手动折叠 / 展开过的会记住（见下面「折叠记忆」）。

- **编辑日历**：下拉旁边的 📅 弹出过去两周的日历（按周一对齐），每格是当天编辑过的节点数（含新建，`+N` = 其中新建），颜色越深越多。
  像订酒店一样点起点、再点终点选一段日期（同一天点两次 = 只看那天），选好的范围会作为一项留在下拉里。"近 N 天" = 今天和之前 N-1 天，选了也会在日历上标出来。`Esc` 或点外面关闭。
- 侧边栏显示每个节点的"最后编辑"时间，以及"新建 MM-DD · 编辑过 MM-DD、MM-DD…"。

- **时间从哪来**：Tree.md 里没有时间信息，所以文件每次变化都和上一份快照比，记下哪些节点变了（`track_edits()`）。
  快照在 `~/.thinktree/history/<路径哈希>.json`，删掉只会丢历史，不影响 tree。服务开着时后台每 5 秒检查一次最近打开过的 tree（`watch_recent()`），没开页面也照样记录。
- **记了什么**：每个节点 `edited`（最后编辑时间）、`created`（第一次出现的时间；开始记录前就有的节点为空）、`days`（编辑过的日期列表，按天去重，只留最近 60 天 `KEEP_DAYS`）。
- **什么算编辑**：节点自己的标题 / 附加 / 结论 / why / 详情累计改动 ≥ 5 个字符（`MINOR_EDIT`，修错字不算），或者状态变了。子节点变了不算父节点。
- **节点对应**：编号按位置生成、插入节点后会变，所以快照用内部 uid，靠 `_match()` 对上新旧节点：同一父节点下标题相同 → 标题相近（改了标题）→ 全树标题相同（挪了位置）。都对不上就算新建。
- **移动 / 改名**：快照按文件路径存。路径变了且没有对应快照时，会接手一份原路径已不存在、节点标题大多（Jaccard > 0.5）对得上的快照（`_adopt_moved()`），历史不会断。
- **冷启动**：第一次建快照时没有历史，用节点上手写的日期（如 `（10-02）`）和节点里 `[[链接]]` 笔记的修改时间估一个，取最晚的。

页面操作：点节点文字开详情，双击节点复制节点名称，点圆点折叠；点 `[编号]` 跳转；网址加 `#2a2` 直接定位；`/` 搜索、`f` 适应窗口、`r` 最近编辑透镜、`x` 加星、`t` 待办、`?` 说明（含 check 结果）、`Esc` 关闭。
工具栏的状态按钮可筛选（例如只看 ❓），筛选和搜索会自动展开到匹配节点。展开层级、结论开关、筛选会记在浏览器本地。

**折叠记忆**：每个 tree、每种筛选组合（状态筛选 × 类型 × 最近编辑模式，`viewKey()`）各记一份折叠状态，存在 localStorage 的 `thinktree:folds:<路径>`。
点圆点折叠 / 展开（包了一层 `mm.toggleNode`）或跳转时展开上级后整份记下（`saveFolds()`）；没记过的视图、新出现的节点用默认值（展开层级；筛选 / 透镜下展开到匹配节点）。按节点 `uid` 记，插入节点、编号后移也对得上。搜索时总是全展开、不记；改「展开层级」会清掉当前视图的记录。

## Tree.md 格式细节（补充 README）

| 写法 | 解析成 |
|---|---|
| `# 标题` | 根节点 |
| `## [n] 标题` | 主枝（编号可省，自动 1, 2, 3） |
| `- [ ]` / `[x]` / `[-]` / `[>]` | 节点：进行中 / 已定 / 否决 / 搁置（`[?]` `[/]` 也算进行中） |
| 结论（`=>`）之前出现 `⭐` / `🚩` | `star` / `todo`；结论里的不算 |
| 标题开头 `实验：` / `思考：`（中英文冒号） | `type` = `exp` / `think`，前缀从 `title` 里去掉（`NODE_TYPES` / `pop_type()`；前端 `KIND`）；没写 = `""` |
| 节点文字 `标题 (附加) => 结论` | `title` / `extra`（末尾括号、`↔ [id]`）/ `conclusion` |
| 编号 | 按位置自动：`2 → 2a → 2a1 → 2a1a`；也可手写 `- [ ] [7z] 标题` |
| 节点下的普通列表行 | `details`（保留相对缩进） |
| `why:` 行 + 它下面缩进的子条目 | `why_items`；`why` = 第一层文字 |
| `- 📖` 下面的行 | 图例，显示在 `?` 面板 |

图上 🚩 / ⭐ 显示在节点框外面的前方（`--🚩★[ 节点 ]`）。
兼容旧写法：`- ✅ **[2a2] 标题** → 结论` + `- 📝` 详情容器仍能解析（`check` 会提醒没放进 📝 的属性）。
显示时 `=>` 变成 →，❓ ✅ ❌ 🅿️ ⚠️ 📄 换成自绘 SVG 图标（app.js 里的 `ICON` / `EMOJI`）。
文本里出现的 `[编号]`（编号存在时）记为引用，自动算出反向引用。
