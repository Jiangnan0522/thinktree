/* thinktree 前端：markmap 画树，点节点开侧边栏。数据来自 window.__TREE__（build）或 /api/tree（serve）。 */
(() => {
  "use strict";
  const { Markmap } = window.markmap;
  const STATUS = { open: "进行中", done: "已定", rejected: "否决", parked: "搁置" };
  const KIND = { exp: "实验", think: "思考" };  // 节点类型：Tree.md 里标题开头写 "实验：" / "思考："
  const PALETTE = ["#6366f1", "#0d9488", "#e07a1f", "#db2777", "#7c3aed", "#0284c7"];
  // 自绘状态图标（Tree.md 里仍然写 emoji，显示时替换）
  const ICON = {
    open: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.1" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M8 3.7a4.3 4.3 0 0 1 0 8.6z" fill="currentColor"/></svg>',
    done: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7.2" fill="currentColor"/><path d="M4.9 8.3l2.1 2.1 4.2-4.6" fill="none" stroke="var(--ic-fg)" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    rejected: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7.2" fill="currentColor"/><path d="M5.7 5.7l4.6 4.6M10.3 5.7l-4.6 4.6" fill="none" stroke="var(--ic-fg)" stroke-width="1.9" stroke-linecap="round"/></svg>',
    parked: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7.2" fill="currentColor"/><path d="M6.4 5.4v5.2M9.6 5.4v5.2" fill="none" stroke="var(--ic-fg)" stroke-width="1.9" stroke-linecap="round"/></svg>',
    warn: '<svg viewBox="0 0 16 16"><path d="M8 1.9l6.5 11.5H1.5z" fill="currentColor" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M8 6.1v3.5" fill="none" stroke="var(--ic-fg)" stroke-width="1.7" stroke-linecap="round"/><circle cx="8" cy="11.6" r="0.95" fill="var(--ic-fg)"/></svg>',
    home: '<svg viewBox="0 0 16 16"><path d="M2.4 7.3L8 2.4l5.6 4.9v6.3H9.9V9.9H6.1v3.7H2.4z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    clock: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.3" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 4.6V8l2.4 1.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    cal: '<svg viewBox="0 0 16 16"><rect x="2.2" y="3.2" width="11.6" height="10.6" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2.2 6.6h11.6M5.4 1.8v2.6M10.6 1.8v2.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    star: '<svg viewBox="0 0 16 16"><path d="M8 1.6l1.95 4.1 4.45.55-3.27 3.08.85 4.42L8 11.55l-3.98 2.2.85-4.42L1.6 6.25l4.45-.55z" fill="currentColor" stroke="currentColor" stroke-width="1" stroke-linejoin="round"/></svg>',
    flag: '<svg viewBox="0 0 16 16"><path d="M3.6 14.6V1.9" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M4.2 2.5h8.3l-2 3.3 2 3.3H4.2z" fill="currentColor" stroke="currentColor" stroke-width="1" stroke-linejoin="round"/></svg>',
    exp: '<svg viewBox="0 0 16 16"><path d="M6.2 1.9h3.6M6.7 2v4.3L2.9 12.7a1.1 1.1 0 0 0 .95 1.6h8.3a1.1 1.1 0 0 0 .95-1.6L9.3 6.3V2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M4.6 10.2h6.8l1.1 2.4a.6.6 0 0 1-.55.85H4.05a.6.6 0 0 1-.55-.85z" fill="currentColor"/></svg>',
    think: '<svg viewBox="0 0 16 16"><path d="M8 2.2c-3.3 0-5.8 2-5.8 4.6 0 1.6 1 3 2.6 3.8l-.5 2.3 2.6-1.6c.36.05.73.08 1.1.08 3.3 0 5.8-2 5.8-4.6S11.3 2.2 8 2.2z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><circle cx="5.6" cy="6.8" r=".9" fill="currentColor"/><circle cx="8" cy="6.8" r=".9" fill="currentColor"/><circle cx="10.4" cy="6.8" r=".9" fill="currentColor"/></svg>',
    doc: '<svg viewBox="0 0 16 16"><path d="M4 1.8h5.1L12.4 5v9.2H4z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M9 1.9v3.3h3.3M6.1 8.3h4.3M6.1 10.8h4.3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
  };
  const ico = (k) => `<span class="ic ic-${k}">${ICON[k]}</span>`;
  const EMOJI = [["🅿️", "parked"], ["🅿", "parked"], ["⚠️", "warn"], ["⚠", "warn"], ["❓", "open"], ["✅", "done"], ["❌", "rejected"], ["📄", "doc"]];
  const secColor = (i) => PALETTE[(i || 0) % PALETTE.length];
  const WIKI = /\[\[((?:[^\[\]]|\[[^\[\]]*\])+)\]\]/g;
  const $ = (s) => document.querySelector(s);
  const TREE_PATH = new URLSearchParams(location.search).get("tree");
  const api = (what, extra) => `api/${what}?path=${encodeURIComponent(TREE_PATH)}${extra || ""}`;
  const setHash = (h) => { try { history.replaceState(null, "", h); } catch {} };  // file:// 下浏览器不让改

  const st = {
    data: null, mm: null, sel: null, items: new Map(), saved: {},
    statuses: new Set(Object.keys(STATUS)), q: "", level: 3, concl: true, mtime: 0,
  };

  // ------------------------------------------------------------ 偏好（只存本机，读不到就用默认）
  const pref = {
    get(k, d) { try { const v = localStorage.getItem("thinktree:" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("thinktree:" + k, JSON.stringify(v)); } catch {} },
  };
  st.level = pref.get("level", 3);
  st.concl = pref.get("concl", true);
  st.whyMap = pref.get("whyMap", false);
  st.statuses = new Set(pref.get("statuses", Object.keys(STATUS)));
  st.recent = pref.get("recent", false);
  st.kind = pref.get("kind", "");  // 类型透镜："" 全部 / "exp" / "think"
  st.lensMode = pref.get("lensMode", pref.get("recentDays", 7));  // 3 / 7 / 14 / "custom"
  st.lensRange = pref.get("lensRange", null);  // 自定义范围 { from, to }（"YYYY-MM-DD"）
  st.calAnchor = null;  // 日历上点了起点、还没点终点

  // ------------------------------------------------------------ 文本渲染
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function wikilink(tgt) {
    const [target, alias] = tgt.split("|");
    const label = alias || target.split("/").pop();
    const r = st.data.links[tgt];
    return r
      ? `<a href="${esc(r.url)}" title="在 Obsidian 打开：${esc(r.path)}">${esc(label)}</a>`
      : `<span class="wl-broken" title="找不到文件">${esc(label)}</span>`;
  }

  /** 行内 markdown：`code`、**bold**、[[wikilink]]、[2a2] 节点引用 */
  function inline(text) {
    return String(text).split(/(`[^`]+`)/).map((part) => {
      if (/^`[^`]+`$/.test(part)) return `<code>${esc(part.slice(1, -1))}</code>`;
      const ph = [];
      let h = esc(part.replace(WIKI, (_, t) => { ph.push(wikilink(t)); return `\u0000${ph.length - 1}\u0000`; }));
      h = h.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/=&gt;/g, "→");  // 写 =>，显示成 →
      h = h.replace(/(^|[^\[])\[([0-9][0-9a-z]*)\](?![\](])/g, (m, pre, id) =>
        st.data.nodes[id] ? `${pre}<a class="ref" data-ref="${id}">[${id}]</a>` : m);
      for (const [e, k] of EMOJI) h = h.split(e).join(ico(k));
      return h.replace(/\u0000(\d+)\u0000/g, (_, i) => ph[+i]);
    }).join("");
  }

  /** [[缩进, 文本], ...] → 嵌套 <ul> */
  function list(items) {
    let out = "", depth = -1;
    for (const [rel, t] of items) {
      const d = Math.min(Math.max(0, rel), depth + 1);
      if (d > depth) { out += "<ul>"; depth = d; }
      else { out += "</li>"; while (depth > d) { out += "</ul></li>"; depth--; } }
      out += `<li${/^why\s*[:：]/i.test(t) ? ' class="why-line"' : ""}>${inline(t)}`;
    }
    while (depth >= 0) { out += "</li></ul>"; depth--; }
    return out;
  }

  /** why 可以是多行（why: 那行 + 子条目）；单行就渲染成一段话 */
  const whyItems = (n) => n.why_items || (n.why ? [[0, n.why]] : []);
  function whyHTML(n) {
    const it = whyItems(n);
    return it.length === 1 ? `<p>${inline(it[0][1])}</p>` : list(it);
  }
  const plain = (t) => String(t).replace(WIKI, (_, x) => x.split("|").pop()).replace(/\*\*|`/g, "");
  const whyText = (n) => whyItems(n).map(([r, t]) => (r ? "  · " : "") + plain(t)).join("\n");

  // ------------------------------------------------------------ 树 → markmap 数据
  const N = () => st.data.nodes;
  const matches = (n) => !st.q || [n.id, KIND[n.type] || "", n.title, n.conclusion, n.extra, ...n.details.map((d) => d[1])]
    .join(" ").toLowerCase().includes(st.q.toLowerCase());
  const filtering = () => !!st.q || st.statuses.size < Object.keys(STATUS).length;

  // ------------------------------------------------------------ 折叠状态：每个 tree、每种筛选组合（状态 × 类型 × 最近编辑）各记一份，存本机
  // 按节点的 uid（编辑历史里的稳定编号）记，插入节点、编号整体后移也还对得上；没折叠 / 展开过的节点用默认值
  const FOLD_KEY = "folds:" + (TREE_PATH || "static");
  const uidOf = (id) => (N()[id] && N()[id].uid) || id;
  function viewKey() {
    const allSt = st.statuses.size === Object.keys(STATUS).length;
    return [allSt ? "" : [...st.statuses].sort().join(","), st.kind, st.recent ? st.lensMode : ""].join("|");
  }
  const savedFolds = () => pref.get(FOLD_KEY, {})[viewKey()] || {};
  function saveFolds() {
    if (!st.mm || !st.mm.state.data || st.q) return;  // 搜索时的临时展开不记
    const f = {};
    walk(st.mm.state.data, (it) => { if (it.children && it.children.length) f[uidOf(it.payload.tid)] = it.payload.fold ? 1 : 0; });
    const all = pref.get(FOLD_KEY, {}); all[viewKey()] = f; pref.set(FOLD_KEY, all);
  }
  function resetFolds() { const all = pref.get(FOLD_KEY, {}); delete all[viewKey()]; pref.set(FOLD_KEY, all); }

  // ------------------------------------------------------------ 「最近编辑」透镜：选定日期范围内编辑过的节点高亮，它们的祖先正常，其余变暗（不隐藏）
  const RECENT_DAYS = [3, 7, 14];
  const CAL_DAYS = 14;  // 日历显示过去多少天
  const dayStr = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const daysAgo = (k) => { const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() - k); return d; };
  const md = (ds) => ds.slice(5);  // "2026-10-05" → "10-05"
  /** 当前模式对应的日期范围；"近 N 天" = 今天和之前 N-1 天 */
  function lensRange(mode = st.lensMode) {
    if (mode === "todo") return { todo: true };
    if (mode === "custom" && st.lensRange) return st.lensRange;
    const n = typeof mode === "number" ? mode : 7;
    return { from: dayStr(daysAgo(n - 1)), to: dayStr(daysAgo(0)) };
  }
  let lensCache = null;
  /** 透镜开着：最近编辑 / 待办（st.recent）或类型（st.kind），两者可以叠加 */
  const lensOn = () => st.recent || !!st.kind;
  /** 符合条件的节点 = hot，和它们的上级 = path。条件 = 范围内编辑过（todo 模式：标了 🚩；r 为 null：不限）且类型对得上 */
  function lens(r = st.recent ? lensRange() : null, kind = st.kind) {
    const key = (!r ? "all" : r.todo ? "todo" : `${r.from}|${r.to}`) + "|" + kind;
    if (lensCache && lensCache.data === st.data && lensCache.key === key) return lensCache;
    const hot = new Set(), path = new Set();
    for (const n of Object.values(N())) {
      if (n.kind !== "node" || (kind && n.type !== kind)) continue;
      if (r && !(r.todo ? n.todo : (n.days || []).some((d) => d >= r.from && d <= r.to))) continue;
      hot.add(n.id);
      for (let p = n.parent; p; p = N()[p].parent) path.add(p);
    }
    return (lensCache = { data: st.data, key, hot, path });
  }
  /** 透镜样式：只开类型透镜时命中的节点不加"最近编辑"的高亮，淡化其余节点就够了 */
  const lensCls = (id) => { const l = lensOf(id); return !l || l === "path" || (l === "hot" && !st.recent) ? "" : " r-" + l; };
  const mmdd = (ts) => { const d = new Date(ts * 1000); return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
  /** 节点在透镜下的档位：hot / path / dim；透镜关着返回 "" */
  const lensOf = (id) => !lensOn() || id === "root" ? "" : lens().hot.has(id) ? "hot" : lens().path.has(id) ? "path" : "dim";

  /** "标题（09-20 ~ 10-02）" → ["标题", "09-20 ~ 10-02"]：括号里含数字才当日期 */
  function splitDate(t) {
    const m = t.match(/^(.*?)\s*[（(]([^（）()]*\d[^（）()]*)[）)]\s*$/);
    return m ? [m[1], m[2]] : [t, ""];
  }

  function content(n, sec) {
    if (n.kind === "root") {
      const qs = Object.values(N()).filter((x) => x.kind === "node");
      const open = qs.filter((x) => x.status === "open").length;
      return `<div class="tn root" data-tid="root"><div class="root-t">${inline(n.title)}</div>` +
        `<div class="root-s">${qs.length} 个问题 · ${open} 个进行中</div></div>`;
    }
    if (n.kind === "section") {
      const [t, date] = splitDate(n.title);
      return `<div class="tn sec${lensCls(n.id)}" data-tid="${n.id}" style="--c:${secColor(sec)}">` +
        `${/^s\d+$/.test(n.id) ? "" : `<span class="sec-id">${esc(n.id)}</span>`}<span class="sec-t">${inline(t)}</span>` +
        `${date ? `<span class="date">${esc(date)}</span>` : ""}</div>`;
    }
    const hit = st.q && matches(n) ? " hit" : "";
    const s = STATUS[n.status] ? n.status : "none";
    const tip = n.why ? ` title="why: ${esc(whyText(n))}"` : "";
    const r = lensCls(n.id);
    const k = KIND[n.type] ? ` k-${n.type}` : "";
    const box = `<div class="tn node st-${s}${hit}${r}${k}" data-tid="${n.id}"${tip}>` +
      `<span class="tag" title="${STATUS[s] || ""}">${STATUS[s] ? ico(s) : ""}<span>${esc(n.id)}</span></span>` +
      `${n.type === "exp" ? `<span class="kd" title="实验">${ico("exp")}</span>` : ""}` +
      `<span class="tt">${inline(n.title)}</span>${n.extra ? `<span class="ex">${inline(n.extra)}</span>` : ""}` +
      `${st.whyMap && n.why ? `<div class="wy"><span class="wy-l">why</span>${inline(n.why)}</div>` : ""}` +
      `${st.concl && n.conclusion ? `<div class="cc">${inline(n.conclusion)}</div>` : ""}</div>`;
    // 加星：星放在节点框外面的前方（连线上），--★[ 节点 ]
    const marks = (n.todo ? `<span class="mk flag" title="待办">${ICON.flag}</span>` : "") + (n.star ? `<span class="mk star" title="已加星">${ICON.star}</span>` : "");
    return marks ? `<div class="mark-row">${marks}${box}</div>` : box;
  }

  function build(id, depth, sec) {
    const n = N()[id];
    const kids = n.children.map((c, i) => build(c, depth + 1, n.kind === "root" ? i : sec)).filter(Boolean);
    if (n.kind === "node" && !(st.statuses.has(n.status) && matches(n)) && !kids.length) return null;
    if (n.kind === "section" && !kids.length && filtering()) return null;
    let fold = depth >= st.level ? 1 : 0;
    if (filtering() || (lensOn() && lens().path.has(id))) fold = 0;  // 筛选 / 透镜：默认展开到所有匹配的节点
    const saved = st.saved[uidOf(id)];
    if (saved !== undefined && !st.q) fold = saved;  // 在这个筛选下手动折叠 / 展开过就照记下的来；搜索时总是全展开
    return { content: content(n, sec), children: kids, payload: { tid: id, sec, fold: kids.length ? fold : 0 } };
  }

  function walk(item, fn) { fn(item); (item.children || []).forEach((c) => walk(c, fn)); }

  async function render(fit) {
    st.saved = savedFolds();
    const root = build("root", 1, 0) || { content: "（没有匹配的节点）", children: [], payload: { tid: "root" } };
    if (!st.mm) {
      st.mm = Markmap.create("#map", {
        color: (it) => (it.payload && it.payload.tid !== "root"
          ? secColor(it.payload.sec) + (lensOf(it.payload.tid) === "dim" ? "40" : "") : "#9ca3af"),
        lineWidth: (it) => ({ 1: 3, 2: 2.6, 3: 1.8 }[it.state.depth] || 1.3),
        duration: 350, maxWidth: 400, initialExpandLevel: -1, spacingVertical: 9, spacingHorizontal: 64, fitRatio: 0.98, paddingX: 10,
      });
      const toggle = st.mm.toggleNode.bind(st.mm);  // 点小圆点折叠 / 展开后记下来
      st.mm.toggleNode = async (d, recursive) => { await toggle(d, recursive); saveFolds(); };
    }
    await st.mm.setData(root);
    st.items.clear();
    walk(st.mm.state.data, (it) => st.items.set(it.payload.tid, it));
    markSelected();
    if (fit) await st.mm.fit();
  }

  function markSelected() {
    document.querySelectorAll(".tn.sel").forEach((e) => e.classList.remove("sel"));
    if (st.sel) document.querySelectorAll(`.tn[data-tid="${CSS.escape(st.sel)}"]`).forEach((e) => e.classList.add("sel"));
  }

  // ------------------------------------------------------------ 选中 / 侧边栏
  async function select(id, reveal) {
    if (!N()[id]) return;
    st.sel = id;
    if (reveal) {
      if (!st.items.has(id)) {  // 被筛选掉了：清掉筛选再画
        st.q = ""; $("#search").value = "";
        st.statuses = new Set(Object.keys(STATUS)); drawFilters();
        await render(false);
      }
      let changed = false;
      for (let p = N()[id].parent; p; p = N()[p].parent) {
        const it = st.items.get(p);
        if (it && it.payload.fold) { it.payload = { ...it.payload, fold: 0 }; changed = true; }
      }
      if (changed) { await st.mm.renderData(); saveFolds(); }
    }
    renderPanel(id);
    markSelected();
    setHash("#" + encodeURIComponent(id));
    const it = st.items.get(id);
    if (it) setTimeout(() => (reveal ? st.mm.centerNode(it) : st.mm.ensureVisible(it, { left: 40, right: 40, top: 40, bottom: 40 })), 120);
  }

  function nodeLine(n) {
    return `<span class="nl st-${n.status}">${STATUS[n.status] ? ico(n.status) : ""}<a class="ref" data-ref="${n.id}">${esc(n.id)}</a> ` +
      `${KIND[n.type] ? `<span class="nl-kd k-${n.type}" title="${KIND[n.type]}">${ICON[n.type]}</span>` : ""}` +
      `<span class="tt">${inline(n.title)}</span>${n.todo ? `<span class="nl-mk flag">${ICON.flag}</span>` : ""}${n.star ? `<span class="nl-mk star">${ICON.star}</span>` : ""}</span>` +
      (n.conclusion ? `<div class="nl-cc">${inline(n.conclusion)}</div>` : "");
  }

  function renderPanel(id) {
    const n = N()[id];
    const chain = [];
    for (let p = id; p; p = N()[p].parent) chain.unshift(N()[p]);
    let h = `<div class="crumbs">${chain.map((x) => x.kind === "root"
      ? `<a class="ref" data-ref="root">${esc(x.title)}</a>` : `<a class="ref" data-ref="${x.id}">[${x.id}]</a>`).join(" › ")}</div>`;
    // 附加文字如果只是 "（10-02）" 这样的日期，就做成小标签
    const exDate = (n.extra.match(/^[（(]([^（）()]*\d[^（）()]*)[）)]$/) || [])[1];
    const [title, secDate] = n.kind === "section" ? splitDate(n.title) : [n.title, ""];
    const date = exDate || secDate;
    if (n.kind !== "root") h += `<div class="badges">${STATUS[n.status] ? `<span class="badge ${n.status}">${ico(n.status)}${STATUS[n.status]}</span>` : ""}` +
      `${KIND[n.type] ? `<span class="badge kb k-${n.type}">${ico(n.type)}${KIND[n.type]}</span>` : ""}` +
      `<span class="pid">${esc(n.id)}</span>${date ? `<span class="date">${esc(date)}</span>` : ""}` +
      `${n.todo && n.todo_since ? `<span class="todo-since">${ICON.flag}标为待办 ${ago(n.todo_since)}</span>` : ""}` +
      `${n.edited ? `<span class="edited" title="${esc(new Date(n.edited * 1000).toLocaleString())}">${ico("clock")}最后编辑 ${ago(n.edited)} · ${mmdd(n.edited)}</span>` : ""}</div>`;
    if (canEdit()) {
      const acts = n.kind === "root" ? [["edit", "✎ 编辑", "e"]]
        : n.kind === "section" ? [["child", "＋ 子问题", "a"], ["after", "＋ 新主枝", "s"], ["edit", "✎ 编辑", "e"]]
        : [["child", "＋ 子问题", "a"], ["after", "＋ 同级", "s"], ["edit", "✎ 编辑", "e"]];
      const starBtn = n.kind === "node" && n.syntax === "task"
        ? `<button class="act mk-btn star${n.star ? " on" : ""}" data-act="star" title="${n.star ? "取消星标" : "标成重要：在 Tree.md 里加 ⭐"}（快捷键 x）">${ICON.star}${n.star ? "已加星" : "加星"}</button>` +
          `<button class="act mk-btn flag${n.todo ? " on" : ""}" data-act="todo" title="${n.todo ? "取消待办" : "打算明天 / 接下来几天做：在 Tree.md 里加 🚩"}（快捷键 t）">${ICON.flag}${n.todo ? "待办中" : "待办"}</button>` : "";
      h += `<div class="actions">${acts.map(([w, lb, k]) =>
        `<button class="act" data-act="${w}" title="在 Obsidian 里${w === "edit" ? "打开到这一行" : "插入一行并打开"}（快捷键 ${k}）">${lb}</button>`).join("")}${starBtn}</div>`;
    }
    if (n.kind === "node" && (n.days || []).length) h += `<div class="p-hist">${n.created ? `新建 ${mmdd(n.created)} · ` : ""}编辑过 ` +
      `${n.days.slice(-10).map(md).join("、")}${n.days.length > 10 ? ` 等 ${n.days.length} 天` : ""}</div>`;
    h += `<h2>${inline(title)}</h2>`;
    if (n.extra && !exDate) h += `<div class="p-extra">${inline(n.extra)}</div>`;
    if (n.kind === "node") h += whyItems(n).length
      ? `<div class="p-why"><span class="lbl">为什么想这个</span>${whyHTML(n)}</div>`
      : `<div class="p-why empty">还没写 why：为什么会 branch 到这个问题？</div>`;
    if (n.conclusion) h += `<div class="p-concl"><span class="lbl">结论</span>${inline(n.conclusion)}</div>`;

    const path = chain.filter((x) => x.kind !== "root");
    if (path.length > 1) {
      h += `<h3>How we got here</h3><ol class="path">` + path.map((x) =>
        `<li class="${x.id === id ? "cur" : ""}">${x.kind === "section" ? `<b>${inline(splitDate(x.title)[0])}</b>` : nodeLine(x)}` +
        (x.id !== id && whyItems(x).length ? `<div class="why"><span class="why-l">why</span><div class="why-b">${whyHTML(x)}</div></div>` : "") +
        `</li>`).join("") + `</ol>`;
    }
    // 详情里去掉整个 why 块（why: 那行和它的子条目），它已经显示在上面
    let inWhy = false;
    const det = n.details.filter(([rel, t]) => {
      if (rel === 0) inWhy = /^why\s*[:：]/i.test(t);
      return !inWhy;
    });
    if (det.length) h += `<h3>详情</h3><div class="details">${list(det)}</div>`;
    const kids = n.children.map((c) => N()[c]);
    if (kids.length) h += `<h3>${n.kind === "node" ? "子问题" : "节点"}（${kids.length}）</h3><ul class="kids">${kids.map((k) => `<li>${k.kind === "section" ? `<a class="ref" data-ref="${k.id}">${inline(k.title)}</a>` : nodeLine(k)}</li>`).join("")}</ul>`;
    if (n.backrefs.length) h += `<h3>被这些节点引用 ↔</h3><ul class="backs">${n.backrefs.map((b) => `<li>${nodeLine(N()[b])}</li>`).join("")}</ul>`;
    h += `<div class="foot">Tree.md 第 ${n.line} 行${st.data.meta.source_url ? ` · <a href="${esc(st.data.meta.source_url)}">在 Obsidian 打开 Tree</a>` : ""}</div>`;
    $("#panelBody").innerHTML = h;
    $("#panel").hidden = false;
  }

  // ------------------------------------------------------------ 插入节点 / 在 Obsidian 里编辑
  const canEdit = () => !!(window.__LIVE__ && TREE_PATH);

  function openObsidian(url) {
    // 自定义协议：让浏览器交给 Obsidian，不离开当前页
    const a = document.createElement("a"); a.href = url; a.click();
  }

  async function toggleMark(mark) {
    const n = N()[st.sel];
    if (!canEdit() || !n || n.kind !== "node" || n.syntax !== "task") return;
    let res;
    try {
      const r = await fetch("api/mark", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: TREE_PATH, id: st.sel, mark, mtime: st.mtime }),
      });
      res = (r.headers.get("Content-Type") || "").includes("json") ? await r.json()
        : { error: `服务器返回 ${r.status}（不是 JSON）——可能是旧版 thinktree 还在运行，重启一下` };
    } catch (e) { res = { error: String(e) }; }
    if (res.error) { toast(res.error); return; }
    const d = await (await fetch(api("tree"), { cache: "no-store" })).json();  // 不等轮询，马上刷新
    if (d.error) return;
    applyData(d);
    await render(false);
    if (N()[st.sel]) renderPanel(st.sel);
    toast({ star: ["已加星", "已取消星标"], todo: ["已标为待办", "已取消待办"] }[mark][res.on ? 0 : 1]);
  }

  async function act(where) {
    if (where === "star" || where === "todo") return toggleMark(where);
    if (!canEdit() || !st.sel) return;
    let res;
    try {
      const r = await fetch("api/insert", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: TREE_PATH, id: st.sel, where, mtime: st.mtime }),
      });
      res = (r.headers.get("Content-Type") || "").includes("json") ? await r.json()
        : { error: `服务器返回 ${r.status}（不是 JSON）——可能是旧版 thinktree 还在运行，重启一下` };
    } catch (e) { res = { error: String(e) }; }
    if (res.error) { toast(res.error); return; }
    if (res.inserted) st.pendingLine = res.line;  // 刷新后自动选中新节点
    if (res.url) {
      toast((res.inserted ? "已插入新节点，正在打开 Obsidian…" : "正在打开 Obsidian…") +
        (res.at_line ? "" : `（没启用 Advanced URI 插件，跳不到第 ${res.line} 行）`));
      openObsidian(res.url);
    } else toast((res.inserted ? "已插入。" : "") + "这个文件不在 Obsidian vault 里，没法跳转");
  }

  function selectPending() {
    if (!st.pendingLine) return;
    const n = Object.values(N()).find((x) => x.line === st.pendingLine && x.kind !== "root");
    st.pendingLine = null;
    if (n) select(n.id, true);
  }

  function renderHelp() {
    const iss = st.data.issues || [];
    let h = `<h2>说明</h2>`;
    if (st.data.legend.length) h += `<h3>图例（来自 Tree.md）</h3><div class="details">${list(st.data.legend)}</div>`;
    h += `<h3>操作</h3><div class="details"><ul>
      <li>点节点文字：打开详情；双击节点：复制节点名称；点圆点：折叠 / 展开（⌘ 点击：递归）</li>
      <li>点 <code>[编号]</code>：跳到那个节点；网址加 <code>#2a2</code> 可直接定位</li>
      <li>拖动 / 滚轮：平移；⌘ + 滚轮 / 双指：缩放</li>
      <li>键盘：<code>/</code> 搜索 · <code>f</code> 适应窗口 · <code>?</code> 说明 · <code>Esc</code> 关闭</li>
      <li>选中节点后：<code>a</code> 加子问题 · <code>s</code> 加同级 · <code>e</code> 在 Obsidian 里编辑（跳到这一行需要 Obsidian 装 Advanced URI 插件）· <code>x</code> 加星 / 取消（⭐）· <code>t</code> 待办 / 取消（🚩，工具栏「待办」只看这些）</li>
      <li><code>r</code> / 工具栏「最近编辑」下拉（3 / 7 / 14 天），或点旁边的日历选任意一段日期：高亮这段时间编辑过的节点，它们的上级正常显示，其余变暗；侧边栏显示每个节点的最后编辑时间</li>
      <li>节点类型：标题开头写 <code>实验：</code> 或 <code>思考：</code>（中英文冒号都行）。工具栏「全部 / 实验 / 思考」或 <code>k</code>：只看一类，其余变暗、上级照常显示，能看出脉络；可以和「最近编辑」叠加</li></ul></div>`;
    h += `<h3>检查结果（${iss.length}）</h3>` + (iss.length
      ? `<ul class="issues">${iss.map((i) => `<li class="${i.level}">第 ${i.line} 行：${esc(i.msg)}</li>`).join("")}</ul>`
      : `<div>没有问题</div>`);
    h += `<div class="foot">${esc(st.data.meta.source)}<br>生成于 ${esc(st.data.meta.generated)}</div>`;
    $("#panelBody").innerHTML = h;
    $("#panel").hidden = false;
  }

  function closePanel() {
    $("#panel").hidden = true; st.sel = null; markSelected();
    setHash(location.pathname + location.search);
  }

  // ------------------------------------------------------------ 工具栏
  function drawFilters() {
    const count = {};
    Object.values(N()).forEach((n) => { if (n.kind === "node") count[n.status] = (count[n.status] || 0) + 1; });
    $("#filters").innerHTML = Object.entries(STATUS).map(([k, lb]) =>
      `<button class="chip st-${k} ${st.statuses.has(k) ? "" : "off"}" data-st="${k}" title="点击切换显示">${ico(k)}<span class="lb">${lb}</span><span class="n">${count[k] || 0}</span></button>`).join("");
    const todoOn = st.recent && st.lensMode === "todo";
    const nTodo = Object.values(N()).filter((n) => n.kind === "node" && n.todo).length;
    $("#todo").innerHTML = `<button class="chip todo ${todoOn ? "" : "off"}${nTodo ? " has" : ""}" title="只看标了 🚩 的待办节点，其余变暗">${ico("flag")}<span class="lb">待办</span><span class="n">${nTodo}</span></button>`;
    const nk = (k) => Object.values(N()).filter((n) => n.kind === "node" && n.type === k).length;
    $("#kind").innerHTML = `<button class="chip${st.kind ? " off" : ""}" data-k="" title="不按类型筛选">全部</button>` +
      Object.entries(KIND).map(([k, lb]) => `<button class="chip k-${k}${st.kind === k ? " on" : " off"}" data-k="${k}" ` +
        `title="只看${lb}节点：其余变暗，上级保持原样，看得出脉络（k 切换）">${ico(k)}<span class="lb">${lb}</span><span class="n">${nk(k)}</span></button>`).join("");
    const cur = st.recent && !todoOn ? String(st.lensMode) : "0";
    const cr = st.lensRange;
    $("#lens").className = st.recent && !todoOn ? "" : "off";
    $("#lens").innerHTML = `${ico("clock")}<select title="高亮这段时间编辑过的节点，其余变暗（r 开 / 关）">` +
      `<option value="0"${cur === "0" ? " selected" : ""}>最近编辑：关</option>` +
      RECENT_DAYS.map((d) => `<option value="${d}"${cur === String(d) ? " selected" : ""}>近 ${d} 天（${lens(lensRange(d)).hot.size}）</option>`).join("") +
      (cr ? `<option value="custom"${cur === "custom" ? " selected" : ""}>${md(cr.from)}${cr.to !== cr.from ? " → " + md(cr.to) : ""}（${lens(cr).hot.size}）</option>` : "") +
      `</select><button id="calBtn" class="${$("#cal").hidden ? "" : "on"}" title="编辑日历：选一段日期">${ico("cal")}</button>`;
    if (!$("#cal").hidden) drawCal();
    const errs = (st.data.issues || []).filter((i) => i.level === "error").length;
    $("#help").textContent = errs ? `? ${errs}` : "?";
    $("#help").style.color = errs ? "var(--rejected)" : "";
  }

  /** mode = 0 关闭透镜；3 / 7 / 14 = 近 N 天；"custom" = range。r 键在关和上次的模式之间切换 */
  function setLens(mode, range) {
    st.recent = !!mode;
    if (mode) st.lensMode = mode;
    if (range) st.lensRange = range;
    pref.set("recent", st.recent); pref.set("lensMode", st.lensMode); pref.set("lensRange", st.lensRange);
    drawFilters(); render(false);
    if (st.recent && !lens().hot.size && st.lensMode === "todo") toast("还没有待办节点：选中节点后按 t 或点「待办」");
    else if (st.recent && !lens().hot.size) {
      const since = st.data.meta.history_since;
      toast(st.kind ? `这段时间没有编辑过的${KIND[st.kind]}节点`
        : `这段时间没有编辑记录${since ? `（${new Date(since * 1000).toLocaleDateString()} 开始记录）` : ""}`);
    }
  }

  /** 类型透镜："" 关 / "exp" / "think"；和最近编辑 / 待办叠加 */
  function setKind(k) {
    st.kind = k; pref.set("kind", k);
    drawFilters(); render(false);
    if (k && !lens().hot.size) toast(st.recent ? `这个范围里没有${KIND[k]}节点`
      : `还没有${KIND[k]}节点：在 Tree.md 里把节点写成「- [ ] ${KIND[k]}：标题」`);
  }

  // ------------------------------------------------------------ 编辑日历：过去两周每天编辑过几个节点，像订酒店一样点起点、终点选范围
  function drawCal() {
    const cnt = {}, fresh = {};
    for (const n of Object.values(N())) {
      if (n.kind !== "node" || (st.kind && n.type !== st.kind)) continue;
      const c = n.created ? dayStr(new Date(n.created * 1000)) : "";
      for (const d of n.days || []) { cnt[d] = (cnt[d] || 0) + 1; if (d === c) fresh[d] = (fresh[d] || 0) + 1; }
    }
    const first = dayStr(daysAgo(CAL_DAYS - 1)), today = dayStr(daysAgo(0));
    const start = daysAgo(CAL_DAYS - 1); start.setDate(start.getDate() - ((start.getDay() + 6) % 7));  // 对齐到周一
    const end = daysAgo(0); end.setDate(end.getDate() + (7 - end.getDay()) % 7);  // 补到周日
    const max = Math.max(1, ...Object.values(cnt));
    let cells = "";
    for (const d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      const ds = dayStr(d), out = ds < first || ds > today, c = cnt[ds] || 0;
      const label = d.getDate() === 1 || ds === first ? `${d.getMonth() + 1}/${d.getDate()}` : d.getDate();
      cells += out ? `<div class="cd out"><span class="dn">${label}</span></div>`
        : `<button class="cd${ds === today ? " today" : ""}" data-d="${ds}" style="--h:${c / max}" title="${ds}：编辑了 ${c} 个节点${fresh[ds] ? `，其中新建 ${fresh[ds]} 个` : ""}">` +
          `<span class="dn">${label}</span><span class="dc">${c ? `${c} 改` : ""}${fresh[ds] ? `<span class="dnew">+${fresh[ds]}</span>` : ""}</span></button>`;
    }
    const r = st.recent && st.lensMode !== "todo" ? lensRange() : null;
    $("#cal").innerHTML = `<div class="cal-h"><b>编辑日历</b><span class="cal-r">${st.calAnchor ? `从 ${md(st.calAnchor)} 起，再点一天作为终点`
        : r ? `${md(r.from)}${r.to !== r.from ? " → " + md(r.to) : ""} · ${lens().hot.size} 个节点` : "点一天作为起点，再点一天作为终点"}</span></div>` +
      `<div class="cal-w">${["一", "二", "三", "四", "五", "六", "日"].map((w) => `<span>${w}</span>`).join("")}</div>` +
      `<div class="cal-g">${cells}</div>` +
      `<div class="cal-f"><span class="dc">N 改</span> = 当天编辑过的节点数（含新建），<span class="dnew">+N</span> = 其中新建</div>`;
    paintRange(st.calAnchor ? { from: st.calAnchor, to: st.calAnchor } : r);
  }

  /** 给日历格子标上范围（选好的，或点了起点后悬停预览的） */
  function paintRange(r) {
    document.querySelectorAll("#cal .cd[data-d]").forEach((b) => {
      const d = b.dataset.d, inR = !!r && d >= r.from && d <= r.to;
      b.classList.toggle("in", inR);
      b.classList.toggle("rs", inR && d === r.from);
      b.classList.toggle("re", inR && d === r.to);
    });
  }

  function toggleCal(show = $("#cal").hidden) {
    $("#cal").hidden = !show;
    st.calAnchor = null;
    if (show) {
      const b = $("#lens").getBoundingClientRect();
      $("#cal").style.left = `${Math.max(8, Math.min(b.left, innerWidth - 300))}px`;
      $("#cal").style.top = `${b.bottom + 6}px`;
    }
    drawFilters();
  }

  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 1800);
  }

  /** 复制到剪贴板；navigator.clipboard 不可用时退回 execCommand */
  async function copyText(s) {
    try { await navigator.clipboard.writeText(s); return true; } catch {}
    const ta = document.createElement("textarea");
    ta.value = s; ta.style.cssText = "position:fixed;opacity:0";
    document.body.appendChild(ta); ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch {}
    ta.remove();
    return ok;
  }

  /** 双击节点：复制节点名称（纯文本；主枝去掉日期） */
  async function copyName(id) {
    const n = N()[id]; if (!n) return;
    const name = plain(n.kind === "section" ? splitDate(n.title)[0] : n.title).trim();
    toast(await copyText(name) ? `已复制：${name}` : "复制失败");
  }

  function bind() {
    $("#map").addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (a && a.classList.contains("ref")) { e.preventDefault(); select(a.dataset.ref, true); return; }
      if (a) return;  // obsidian:// 链接照常打开
      const el = e.target.closest(".tn");
      if (el) select(el.dataset.tid, false);
    });
    // 捕获阶段拦下：不然 d3-zoom 会把双击当成放大
    $("#map").addEventListener("dblclick", (e) => {
      const el = e.target.closest(".tn");
      if (!el || e.target.closest("a")) return;
      e.stopPropagation(); e.preventDefault();
      getSelection().removeAllRanges();  // 双击会选中一个词，清掉
      copyName(el.dataset.tid);
    }, true);
    $("#panel").addEventListener("click", (e) => {
      const b = e.target.closest("button.act");
      if (b) { act(b.dataset.act); return; }
      const a = e.target.closest("a.ref");
      if (a) { e.preventDefault(); select(a.dataset.ref, true); }
    });
    $("#close").onclick = closePanel;
    $("#help").onclick = renderHelp;
    $("#fit").onclick = () => st.mm.fit();
    $("#filters").addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      const k = b.dataset.st;
      st.statuses.has(k) ? st.statuses.delete(k) : st.statuses.add(k);
      pref.set("statuses", [...st.statuses]); drawFilters(); render(true);
    });
    $("#lens").addEventListener("change", (e) => {
      const v = e.target.value; setLens(v === "custom" ? "custom" : +v); e.target.blur();
    });
    $("#lens").addEventListener("click", (e) => { if (e.target.closest("#calBtn")) toggleCal(); });
    $("#kind").addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      setKind(b.dataset.k === st.kind ? "" : b.dataset.k);
    });
    $("#todo").addEventListener("click", () => setLens(st.recent && st.lensMode === "todo" ? 0 : "todo"));
    $("#cal").addEventListener("click", (e) => {
      const b = e.target.closest(".cd[data-d]"); if (!b) return;
      const d = b.dataset.d;
      if (!st.calAnchor) { st.calAnchor = d; drawCal(); return; }
      const [from, to] = [st.calAnchor, d].sort();
      st.calAnchor = null;
      setLens("custom", { from, to });
    });
    $("#cal").addEventListener("mouseover", (e) => {
      const b = e.target.closest(".cd[data-d]");
      if (b && st.calAnchor) paintRange({ from: [st.calAnchor, b.dataset.d].sort()[0], to: [st.calAnchor, b.dataset.d].sort()[1] });
    });
    document.addEventListener("mousedown", (e) => {
      if (!$("#cal").hidden && !e.target.closest("#cal, #lens")) toggleCal(false);
    });
    const lv = $("#level"); lv.value = String(st.level);
    lv.onchange = () => { st.level = +lv.value; pref.set("level", st.level); resetFolds(); render(true); };
    const sw = $("#showWhy"); sw.checked = st.whyMap;
    sw.onchange = () => { st.whyMap = sw.checked; pref.set("whyMap", st.whyMap); render(false); };
    const sc = $("#showConcl"); sc.checked = st.concl;
    sc.onchange = () => { st.concl = sc.checked; pref.set("concl", st.concl); render(false); };
    let t;
    $("#search").addEventListener("input", (e) => {
      clearTimeout(t); t = setTimeout(() => { st.q = e.target.value.trim(); render(true); }, 150);
    });
    $("#search").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const hit = st.data.order.find((id) => N()[id].kind === "node" && matches(N()[id]) && st.statuses.has(N()[id].status));
        if (hit) select(hit, true);
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.target.matches("input, select, textarea")) {
        if (e.key === "Escape") { e.target.value = ""; st.q = ""; e.target.blur(); render(true); }
        return;
      }
      if (e.key === "/") { e.preventDefault(); $("#search").focus(); }
      else if (e.key === "Escape") { if (!$("#cal").hidden) toggleCal(false); else closePanel(); }
      else if (!st.mm) return;
      else if (e.key === "f") st.mm.fit();
      else if (e.key === "?") renderHelp();
      else if (e.key === "r" && !e.metaKey && !e.ctrlKey) setLens(st.recent ? 0 : st.lensMode);
      else if (e.key === "k" && !e.metaKey && !e.ctrlKey) setKind({ "": "exp", exp: "think", think: "" }[st.kind]);
      else if (st.sel && !$("#panel").hidden && canEdit() && !e.metaKey && !e.ctrlKey) {
        const w = { a: "child", s: "after", e: "edit", x: "star", t: "todo" }[e.key];
        if (w) { e.preventDefault(); act(w); }
      }
    });
  }

  // ------------------------------------------------------------ 数据加载 / 自动刷新
  function applyData(d) {
    st.data = d;
    st.mtime = d.meta.mtime;
    const title = N().root.title;
    $("#title").textContent = title; document.title = title;
    drawFilters();
  }

  async function poll() {
    try {
      const v = await (await fetch(api("version"), { cache: "no-store" })).json();
      if (v.error) throw new Error(v.error);
      if (v.mtime !== st.mtime) {
        const r = await fetch(api("tree"), { cache: "no-store" });
        const d = await r.json();
        if (d.error) throw new Error(d.error);
        applyData(d);
        await render(false);
        if (st.sel && N()[st.sel]) renderPanel(st.sel); else if (st.sel) closePanel();
        selectPending();
        toast("Tree.md 已更新");
      }
      $("#live").textContent = "live"; $("#live").className = "";
    } catch (err) {
      $("#live").textContent = "连接断开 / 解析出错"; $("#live").className = "err";
      $("#live").title = String(err);
    }
    setTimeout(poll, 1500);
  }

  // ------------------------------------------------------------ 首页：最近打开 + vault 里发现的 tree
  const ago = (t) => {
    const s = Date.now() / 1000 - t;
    if (s < 60) return "刚刚";
    if (s < 3600) return `${Math.floor(s / 60)} 分钟前`;
    if (s < 86400) return `${Math.floor(s / 3600)} 小时前`;
    if (s < 86400 * 30) return `${Math.floor(s / 86400)} 天前`;
    return new Date(t * 1000).toLocaleDateString();
  };
  const treeHref = (p) => `?tree=${encodeURIComponent(p)}`;

  function card(it, recent) {
    const stats = recent && !it.missing
      ? `<div class="c-stats">${Object.keys(STATUS).filter((k) => (it.status || {})[k]).map((k) =>
          `<span class="c-st" title="${STATUS[k]}">${ico(k)}${it.status[k]}</span>`).join("")}` +
        `${it.todo ? `<span class="c-todo" title="待办节点">${ico("flag")}${it.todo} 待办</span>` : ""}<span class="c-n">${it.nodes} 个问题</span>${it.errors ? `<span class="c-err">${it.errors} 个错误</span>` : ""}</div>`
      : "";
    return `<a class="card${it.missing ? " missing" : ""}" href="${it.missing ? "#" : treeHref(it.path)}" title="${esc(it.path)}">` +
      `<div class="c-top"><div class="c-title">${esc(it.title || "未命名")}</div>` +
      (recent ? `<button class="forget" data-path="${esc(it.path)}" title="从最近列表移除">×</button>` : "") + `</div>` +
      stats + `<div class="c-path">${esc(it.display || it.path)}</div>` +
      (recent ? `<div class="c-time">${it.missing ? "文件不存在了" : ago(it.opened)}</div>` : "") + `</a>`;
  }

  async function renderHome(errMsg) {
    document.body.classList.add("is-home");
    $("#home").hidden = false;
    $("#title").textContent = "thinktree"; document.title = "thinktree";
    let d = { recent: [], discovered: [], vaults: [] };
    try { d = await (await fetch("api/home", { cache: "no-store" })).json(); } catch (e) { errMsg = errMsg || String(e); }
    const vaults = d.vaults || [];
    // 第一次用：一个 tree 都没有时，告诉怎么建
    const firstRun = !d.recent.length && !d.discovered.length
      ? `<div class="first-run"><b>还没有 tree？</b>在终端运行 <code>thinktree init</code>：选一个 Obsidian vault，自动建好示例 Tree.md 并设置好 vault。` +
        `<br>${vaults.length ? `已找到 ${vaults.length} 个 Obsidian vault：${vaults.map((v) => `<code>${esc(v.split(/[\\/]/).pop())}</code>`).join(" ")}，里面还没有 tree。`
          : "没找到 Obsidian vault：装好 Obsidian 并打开过一个 vault 后，这里会自动列出里面的 tree。"}</div>`
      : "";
    $("#home").innerHTML = `<div class="home-wrap">
      <div class="hero"><h1>thinktree</h1><p>打开一个思考 Tree，看 how we got here。</p></div>
      ${errMsg ? `<div class="h-err">${esc(errMsg)}</div>` : ""}
      ${firstRun}
      <form id="openForm" class="open-form">
        <input id="openPath" placeholder="粘贴 Tree.md 的完整路径，回车打开" autocomplete="off" spellcheck="false">
        <button type="submit">打开</button>
      </form>
      <h3>最近打开</h3>
      ${d.recent.length ? `<div class="cards">${d.recent.map((it) => card(it, true)).join("")}</div>`
        : `<div class="empty">还没有打开过。用上面的输入框，或者点下面发现的 tree。</div>`}
      ${d.discovered.length ? `<h3>在 vault 里发现</h3><div class="cards">${d.discovered.map((it) => card(it, false)).join("")}</div>` : ""}
      <p class="hint">Obsidian 里所有 vault 中命名为 <code>Tree.md</code>、或 frontmatter 里写了 <code>thinktree: true</code> 的文件，会自动出现在“发现”里。
      命令行：<code>thinktree init</code> 新建 · <code>thinktree 路径/Tree.md</code> 直接打开 · <code>thinktree prompt</code> 给 AI 的格式说明。</p></div>`;
    $("#openForm").onsubmit = (e) => {
      e.preventDefault();
      const p = $("#openPath").value.trim().replace(/^['"]|['"]$/g, "");
      if (p) location.href = treeHref(p);
    };
    $("#home").onclick = async (e) => {
      const b = e.target.closest(".forget");
      if (b) {
        e.preventDefault(); e.stopPropagation();
        await fetch(`api/forget?path=${encodeURIComponent(b.dataset.path)}`);
        renderHome();
      } else if (e.target.closest(".card.missing")) e.preventDefault();
    };
  }

  async function main() {
    bind();
    $("#homeBtn .ic").innerHTML = ICON.home;
    if (!window.__TREE__ && !TREE_PATH) return renderHome();
    let d = window.__TREE__;
    if (!d) {
      d = await (await fetch(api("tree", "&open=1"), { cache: "no-store" })).json();
      if (d.error) return renderHome(d.error);
      $("#homeBtn").hidden = false;
    }
    applyData(d);
    await render(true);
    const h = decodeURIComponent(location.hash.slice(1));
    if (h && N()[h]) select(h, true);
    if (window.__LIVE__) poll();
    else $("#live").textContent = "静态 · " + d.meta.generated;
  }

  main().catch((e) => { document.body.insertAdjacentHTML("beforeend", `<pre style="color:red;padding:16px">${esc(e.stack || e)}</pre>`); });
})();
