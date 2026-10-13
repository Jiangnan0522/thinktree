# thinktree

把 Obsidian 里的"思考 Tree"（一个用 Markdown 嵌套列表写的 `Tree.md`）变成可交互的思维导图。

做项目时，想法是一棵树：从一个问题分出几个子问题，有的想通了，有的走不通。笔记虽然都在，过几天就忘了**当初为什么想这个点、想完了没有**。
thinktree 让你随时走一遍 **how we got here**：点任何一个节点，侧边栏显示它的结论、为什么会想到它，以及从根到它的每一层 why。

- 内容全在你自己的 `Tree.md` 里，用 Obsidian 照常写；查看器只在你点「＋」「加星」「待办」时往文件里加一行。
- 只依赖 Python 标准库，Mac / Windows / Linux 都能用；页面在本机浏览器里打开，数据不上传。

---

## 安装（一次）

需要：[Obsidian](https://obsidian.md)、能上网（第一次安装和打开页面时要从网上加载）。

**1. 装 uv**（一个 Python 工具管理器，会顺带装好 Python，不用自己装）

- **Mac**：打开「终端」，粘贴：
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Windows**：打开「PowerShell」，粘贴：
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

装完**关掉终端再重新打开一个**。

**2. 装 thinktree**

```bash
uv tool install https://github.com/Jiangnan0522/thinktree/archive/refs/heads/main.zip
```

验证：`thinktree --version` 能打出版本号就好了。提示找不到命令的话，运行 `uv tool update-shell`，再重开终端。

> 已经有 Python 3.9+ 也可以不装 uv：`pip install https://github.com/Jiangnan0522/thinktree/archive/refs/heads/main.zip`。

**升级**：`uv tool install --force --refresh https://github.com/Jiangnan0522/thinktree/archive/refs/heads/main.zip`
**卸载**：`uv tool uninstall thinktree`（你的 Tree.md 不受影响）

---

## 第一次使用（5 分钟）

**1. 新建一个 tree**

```bash
thinktree init
```

它会列出你电脑上的 Obsidian vault，选一个，再选放在哪个子文件夹（默认 `思考Tree`），然后自动：

- 建一个示例 `Tree.md`（里面写了格式说明，看懂后换成你自己的内容）
- 建一个 `CLAUDE.md`：给 AI 看的格式说明（见下面「让 AI 帮忙」）
- 给这个 vault 装一个 CSS 小片段：从查看器跳到 Obsidian 时，高亮那一行
- 检查 Advanced URI 插件（见第 2 步）

最后问你要不要马上打开查看器。

**2. 在 Obsidian 里装 Advanced URI 插件（推荐，每个 vault 一次）**

设置 → 第三方插件 → 关闭安全模式 → 浏览 → 搜索 **Advanced URI** → 安装 → 启用。

装了它，在查看器里点「✎ 编辑」或「＋」时，Obsidian 会直接跳到 Tree.md 里**那一行**；不装也能用，只是只打开文件。

**3. 打开查看器**

```bash
thinktree
```

浏览器会打开首页，列出所有 vault 里的 tree，点进去就行。
**运行 thinktree 的终端窗口要一直开着**（可以最小化）；关掉窗口查看器就停了，下次再运行 `thinktree` 即可。

---

## 日常用法

一边在 Obsidian 里写 `Tree.md`，一边开着查看器：**保存后页面自动刷新**。

| 操作 | 效果 |
|---|---|
| 点节点 | 侧边栏：结论、why、How we got here、子问题、谁引用了它 |
| 双击节点 | 复制节点名称 |
| 点节点旁边的小圆点 | 折叠 / 展开（Mac ⌘ 点击 / Windows Ctrl 点击：连子节点一起） |
| 点 `[2a1]` 这样的编号 | 跳到那个节点 |
| 拖动 | 平移 |
| 滚轮 / 触控板 | Mac：滚动平移，⌘ + 滚轮或双指捏合缩放；Windows：滚轮缩放 |
| `/` | 搜索 |
| `f` | 整棵树适应窗口 |
| `r` | 「最近编辑」：高亮近几天改过的节点，其余变暗（旁边的 📅 可选任意日期范围） |
| `?` | 说明 + 格式检查结果（比如链接找不到文件、引用了不存在的编号） |
| `Esc` | 关闭侧边栏 |

选中一个节点后：

| 键 | 效果 |
|---|---|
| `a` | 加子问题：在 Tree.md 里插入一行空的 `- [ ]` 并在 Obsidian 里打开到那一行 |
| `s` | 加同级节点 |
| `e` | 在 Obsidian 里打开到这一行 |
| `x` | 加星 / 取消（⭐ 重要） |
| `t` | 待办 / 取消（🚩；工具栏「待办」只看这些） |

工具栏的状态按钮可以筛选（例如只看进行中的问题）。网址可以收藏，末尾加 `#2a1` 直接定位到某个节点。

**分享给没装 thinktree 的人**：`thinktree build Tree.md` 导出一个单独的 `Tree.html`，发给别人双击就能看（只读）。

---

## Tree.md 怎么写

一条规则：**复选框 = 节点，普通列表行 = 这个节点的说明。**

```markdown
---
cssclasses: thinktree
thinktree: true
---
# 我的项目 思考 Tree

## 起点：要解决什么问题（09-20 ~ 10-02）
- [x] 这个项目到底想回答什么？ => 一句话结论
	- why: 为什么会想到这个问题
	- => 详细一点的结论
	- 📄 [[相关笔记]] · ⚠️ 前提或坑
	- [ ] 子问题？
		- why: ……
	- [-] 被否决的方向 => 为什么不行
```

| 写法 | 意思 |
|---|---|
| `# 标题` | 根节点 |
| `## 标题` | 主枝 |
| `- [ ]` / `- [x]` / `- [-]` / `- [>]` | 节点：进行中 / 已定 / 否决 / 搁置 |
| `问题 => 结论` | `=>` 后面是一句话结论（显示成 →） |
| 节点下面的 `- why: ……` | 为什么会想到这个问题（下面再缩进的行也算）。**最重要，尽量每个节点都写** |
| 节点下面的其他普通列表行 | 节点的说明 |
| 缩进在节点下面的复选框 | 子问题 |
| `- [ ] ⭐ 问题` / `- [ ] 🚩 问题` | 重要 / 待办 |
| `[2a1]` | 引用别的节点（编号按位置自动生成：`2 → 2a → 2a1`，不用手写，看查看器里显示的） |
| 标题末尾的 `（10-02）` | 显示成日期小标签 |

- frontmatter 里的 `thinktree: true` 让文件出现在首页（文件名叫 `Tree.md` 的不写也行）；`cssclasses: thinktree` 让跳转时的高亮生效。
- 否决的方向也**留在树上**，写清为什么，免得以后绕回去。
- 节点粒度要粗：一个问题或一个决策一个节点；长的论证写成单独的笔记，tree 里只留结论 + `📄 [[链接]]`。
- 运行 `thinktree check Tree.md` 可以检查格式（重复编号、找不到的链接、引用了不存在的编号）。

---

## 让 AI 帮忙维护 tree

`thinktree init` 在 tree 旁边放了一份 `CLAUDE.md`，写了格式规则和"收到一段新想法时怎么更新 tree"的流程。

- **Claude Code**：在 tree 所在的文件夹里启动，它会自动读 `CLAUDE.md`。然后直接说"今天想了 xxx，帮我加到 tree 里"。
- **Codex / Cursor**：把 `CLAUDE.md` 改名（或复制）成 `AGENTS.md`。
- **ChatGPT / 网页版 Claude**：运行 `thinktree prompt`，把输出和 `Tree.md` 的内容一起贴过去。

可以按自己的项目改 `CLAUDE.md`，比如加上你的笔记放在哪、实验记录怎么写。

---

## 命令一览

```bash
thinktree                     # 打开首页（所有 vault 里的 tree + 最近打开）
thinktree 路径/Tree.md         # 直接打开某个 tree
thinktree init [文件夹]        # 新建 tree + 设置 vault（不给文件夹就一步步问）；已有的文件不会覆盖
thinktree check Tree.md       # 检查格式
thinktree build Tree.md       # 导出单文件 HTML（-o 指定位置）
thinktree prompt              # 输出给 AI 的格式说明
thinktree recent              # 列出最近打开的 tree
thinktree stop                # 停掉在跑的查看器
thinktree --version
```

---

## 常见问题

**首页什么都没有？**
首页会自动扫描 Obsidian 里登记过的所有 vault，找文件名叫 `Tree.md`、或 frontmatter 里有 `thinktree: true` 的文件。都没有的话，运行 `thinktree init` 建一个；
或者在首页的输入框里粘贴 Tree.md 的完整路径。vault 不在 Obsidian 里登记的，可以设环境变量 `THINKTREE_VAULTS` 指定要扫的文件夹（Mac 用 `:` 分隔，Windows 用 `;`）。

**页面一片空白 / 图出不来？**
页面要从 jsdelivr 加载两个画图的库（d3、markmap），需要能上网。网络慢的话多等一会儿再刷新。

**点「编辑」只打开了文件，没跳到那一行？**
没装或没启用 Advanced URI 插件（见上面第 2 步）。装好后再运行一次 `thinktree init <tree 所在文件夹>` 可以检查。

**提示"端口 8765 被别的程序占用了"？**
换个端口：`thinktree --port 9000`；或者设环境变量 `THINKTREE_PORT=9000`。

**升级后页面还是旧的？**
直接再运行 `thinktree`：发现在跑的是旧版本时，会自动停掉换成新的。还不行就 `thinktree stop` 后再运行。

**在 Obsidian 里改了，页面上的"最近编辑"时间对吗？**
Tree.md 里没有时间信息，thinktree 每次发现文件变了就和上一份快照比，记下哪些节点改过。只有 thinktree 开着时才记录，所以平时可以一直开着。
快照存在 `~/.thinktree/`（Windows：`C:\Users\你的用户名\.thinktree\`），删掉只会丢编辑时间记录，不影响 tree。

**会不会改坏我的 Tree.md？**
只有你点「＋ 子问题」「＋ 同级」「加星」「待办」时才写文件，每次只加 / 改一行；如果文件在你看的这段时间被改过，会拒绝写入并提示刷新。
建议 vault 用 Obsidian Sync / iCloud / git 之类做备份（反正平时也应该有）。

---

想改代码或加功能：见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。
