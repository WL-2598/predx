/* =============================================================================
   PredX · 单页交易终端（零依赖原生 JS）v2
   路由：#/markets  #/market/:id  #/portfolio  #/leaderboard  #/admin  #/auth
   ========================================================================== */

/* ---------------------------------------------------------------- 图标 */
const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/>',
  wallet: '<rect x="3" y="6" width="18" height="13" rx="3"/><path d="M3 10h18M16 14h2"/>',
  user: '<circle cx="12" cy="8" r="3.6"/><path d="M5 20c1.2-3.6 3.8-5.2 7-5.2s5.8 1.6 7 5.2"/>',
  logout: '<path d="M15 5h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-3"/><path d="M10 8l-4 4 4 4M6 12h9"/>',
  chart: '<path d="M4 19V5M4 19h16"/><path d="m7 14 3.5-4 3 2.6L19 7"/>',
  trophy: '<path d="M8 4h8v4a4 4 0 0 1-8 0V4Z"/><path d="M8 6H5v2a3 3 0 0 0 3 3M16 6h3v2a3 3 0 0 1-3 3"/><path d="M12 12v5M9 20h6"/>',
  layers: '<path d="m12 3 8 4.5-8 4.5L4 7.5 12 3Z"/><path d="m4 12 8 4.5 8-4.5M4 16.5 12 21l8-4.5"/>',
  star: '<path d="m12 4 2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.6-4.8 2.6.9-5.4L4.2 9.7l5.4-.8L12 4Z"/>',
  up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 19c.9-3.3 3.2-4.8 6-4.8s5.1 1.5 6 4.8"/><path d="M16 5.6a3.2 3.2 0 0 1 0 6.2M17.5 14.6c1.7.6 2.8 2 3.3 4"/>',
  flame: '<path d="M12 3c3.2 4 5.4 5.9 5.4 9a5.4 5.4 0 0 1-10.8 0c0-1.6.6-2.7 1.6-4 .6 1 1.3 1.6 2.2 2 .9-2.3.4-4.2 1.6-7Z"/>',
  sparkles: '<path d="M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6L12 4Z"/><path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
  alert: '<path d="M12 4.5 21 19H3l9-14.5Z"/><path d="M12 10v4M12 17h.01"/>',
  calendar: '<rect x="4" y="5.5" width="16" height="14" rx="3"/><path d="M8 3.5v3M16 3.5v3M4 10h16"/>',
  shield: '<path d="M12 3.5 19 6v6c0 4-3 7-7 8.5C8 19 5 16 5 12V6l7-2.5Z"/><path d="m9 12 2 2 4-4"/>',
  coins: '<ellipse cx="12" cy="7" rx="7" ry="3"/><path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7"/><path d="M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5"/>',
  cpu: '<rect x="6.5" y="6.5" width="11" height="11" rx="2.5"/><path d="M10 10h4v4h-4z"/><path d="M9.5 3.5v3M14.5 3.5v3M9.5 17.5v3M14.5 17.5v3M3.5 9.5h3M3.5 14.5h3M17.5 9.5h3M17.5 14.5h3"/>',
  landmark: '<path d="M3.5 9.5 12 4l8.5 5.5"/><path d="M6 10v7M10 10v7M14 10v7M18 10v7M3.5 20h17"/>',
  film: '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M8 5v14M16 5v14M3.5 12h17"/>',
  globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.6 2.4 4 5.4 4 8.5s-1.4 6.1-4 8.5c-2.6-2.4-4-5.4-4-8.5s1.4-6.1 4-8.5Z"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/>',
  bitcoin: '<circle cx="12" cy="12" r="8.5"/><path d="M10 8.5h3.2a2.2 2.2 0 0 1 0 4.4H10Zm0 4.4h3.6a2.2 2.2 0 0 1 0 4.4H10Z"/><path d="M10 8.5V7M12.4 8.5V7M10 17.3v1.5M12.4 17.3v1.5"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".6"/>',
  bolt: '<path d="M13 3 6 13h5l-1 8 7-10h-5l1-8Z"/>',
  filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
  refresh: '<path d="M20 11a8 8 0 1 1-2.5-5.8M20 4v4h-4"/>',
  book: '<path d="M5 4h9a4 4 0 0 1 4 4v12H9a4 4 0 0 1-4-4V4Z"/><path d="M9 8h6M9 12h6"/>',
  back: '<path d="M14 6l-6 6 6 6"/>',
  moon: '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
};

function icon(name, extra = "") {
  const body = ICONS[name] || ICONS.grid;
  return `<svg class="icon ${extra}" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

const CAT_META = {
  政治: { icon: "landmark", color: "#5b8cff" },
  加密: { icon: "bitcoin", color: "#f5a524" },
  宏观: { icon: "chart", color: "#22c55e" },
  科技: { icon: "cpu", color: "#a06bff" },
  体育: { icon: "trophy", color: "#f97316" },
  娱乐: { icon: "film", color: "#ec4899" },
  社会: { icon: "users", color: "#06b6d4" },
  综合: { icon: "grid", color: "#8b94a7" },
};
const CATS = ["政治", "加密", "宏观", "科技", "体育", "娱乐", "社会", "综合"];

/* ---------------------------------------------------------------- 工具 */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const money = (c) => "$" + (Number(c || 0) / 100).toLocaleString("en-US",
  { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const money0 = (c) => "$" + Math.round(Number(c || 0) / 100).toLocaleString("en-US");
const moneyShort = (c) => {
  const v = Math.abs(Number(c || 0)) / 100;
  let s;
  if (v >= 1e6) s = (v / 1e6).toFixed(v >= 1e7 ? 0 : 1) + "M";
  else if (v >= 1e4) s = (v / 1e3).toFixed(v >= 1e5 ? 0 : 1) + "k";
  else s = v >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 0 })
                     : v.toFixed(v < 10 ? 2 : 0);
  return (c < 0 ? "-$" : "$") + s;
};
const num = (n) => Number(n || 0).toLocaleString("en-US");
const signed = (c) => (c > 0 ? "+" : c < 0 ? "-" : "") + money(Math.abs(c));
const cls = (c) => (c > 0 ? "pos" : c < 0 ? "neg" : "dim");

function when(ts) {
  if (!ts) return "—";
  const s = String(ts).replace("T", " ");
  return s.length >= 16 ? s.slice(5, 16) : s;
}
function relTime(ts) {
  if (!ts) return "";
  const t = new Date(String(ts).replace(" ", "T")).getTime();
  if (isNaN(t)) return when(ts);
  const d = Math.floor((Date.now() - t) / 1000);
  if (d < 60) return "刚刚";
  if (d < 3600) return `${Math.floor(d / 60)} 分钟前`;
  if (d < 86400) return `${Math.floor(d / 3600)} 小时前`;
  if (d < 86400 * 30) return `${Math.floor(d / 86400)} 天前`;
  return when(ts);
}
function dayLeft(ts) {
  if (!ts) return "长期";
  const t = new Date(String(ts).replace(" ", "T")).getTime();
  if (isNaN(t)) return "—";
  const d = Math.ceil((t - Date.now()) / 86400000);
  if (d < 0) return "已到期";
  if (d === 0) return "今日截止";
  if (d === 1) return "明天截止";
  return `${d} 天后截止`;
}
const tile = (category, size = "") => {
  const m = CAT_META[category] || CAT_META["综合"];
  return `<span class="tile ${size}" style="background:${m.color}1f;color:${m.color}">${icon(m.icon)}</span>`;
};
const avatarColor = (name) => {
  const palette = ["#8bb3ff", "#c7a4ff", "#7ee0b5", "#ffc98b", "#ff9fae", "#93e1f0", "#d7c2ff"];
  let h = 0;
  for (const ch of String(name || "?")) h = (h * 31 + ch.charCodeAt(0)) % 9973;
  return palette[h % palette.length];
};
const avatar = (name, size = 30) => `<span class="av" style="width:${size}px;height:${size}px;
  background:${avatarColor(name)}">${esc(String(name || "?").trim().slice(0, 1).toUpperCase())}</span>`;

/* ---------------------------------------------------------------- 状态 */
const S = {
  token: localStorage.getItem("px_token") || "",
  user: null, me: null,
  watch: new Set(),
  cats: [], stats: null,
  q: { cat: "all", sort: "hot", text: "", status: "open" },
};

/* ---------------------------------------------------------------- API */
async function api(path, opt = {}) {
  const headers = { "Content-Type": "application/json" };
  if (S.token) headers["Authorization"] = "Bearer " + S.token;
  const res = await fetch(path, {
    method: opt.method || "GET", headers,
    body: opt.body ? JSON.stringify(opt.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { data = null; }
  if (!res.ok) {
    const msg = (data && data.error && data.error.message) || `请求失败 (${res.status})`;
    if (res.status === 401 && S.token) logout(true);
    const err = new Error(msg);
    err.status = res.status;
    err.code = data && data.error && data.error.code;
    throw err;
  }
  return data;
}

async function loadMe() {
  if (!S.token) { S.user = null; S.watch.clear(); return; }
  try {
    const d = await api("/api/auth/me");
    S.user = d.user; S.me = d.stats;
    const w = await api("/api/watchlist").catch(() => ({ items: [] }));
    S.watch = new Set((w.items || []).map((m) => m.id));
  } catch (_) { S.user = null; }
}

function logout(silent) {
  S.token = ""; S.user = null; S.me = null; S.watch.clear();
  localStorage.removeItem("px_token");
  paintHeader();
  if (!silent) { location.hash = "#/markets"; render(); }
  else toast("登录已失效，请重新登录", "err");
}

/* ---------------------------------------------------------------- 提示 */
function toast(msg, kind = "") {
  const box = $("#toast");
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.innerHTML = `${icon(kind === "ok" ? "check" : kind === "err" ? "alert" : "info")}<span>${esc(msg)}</span>`;
  box.appendChild(el);
  setTimeout(() => { el.style.opacity = 0; el.style.transform = "translateY(8px)"; }, 2800);
  setTimeout(() => el.remove(), 3200);
}

/* ---------------------------------------------------------------- 顶栏 */
function paintHeader() {
  const right = $("#topRight");
  if (S.user) {
    right.innerHTML = `
      <div class="balance" title="可用余额">${icon("wallet")}<span>余额</span>${money(S.user.balance_cents)}</div>
      <button class="avatar" data-act="menu" title="${esc(S.user.handle)}">${esc(S.user.handle.trim().slice(0, 1).toUpperCase())}</button>`;
  } else {
    right.innerHTML = `<button class="btn primary" data-act="login">登录 / 注册</button>`;
  }
  const admin = $("#navAdmin");
  if (admin) admin.hidden = !(S.user && ["admin", "creator"].includes(S.user.role));
  const hash = location.hash || "#/markets";
  $$("#nav a, #mobileNav a").forEach((a) => {
    const key = a.dataset.nav;
    const on = key === "markets" ? /^#\/(markets|market\/)/.test(hash) : hash.startsWith("#/" + key);
    a.classList.toggle("on", on);
  });
}

function accountMenu() {
  const box = $("#menuRoot");
  box.innerHTML = `<div class="pop">
    <div class="who"><b>${esc(S.user.handle)}</b><small>${esc(S.user.email)}</small></div>
    <button data-act="portfolio">${icon("layers")}我的持仓</button>
    <button data-act="ledger">${icon("coins")}资金流水</button>
    <button data-act="deposit">${icon("plus")}充值体验金</button>
    ${["admin", "creator"].includes(S.user.role) ? `<button data-act="admin">${icon("shield")}管理端</button>` : ""}
    <button data-act="logout">${icon("logout")}退出登录</button>
  </div>`;
  setTimeout(() => document.addEventListener("click", closeMenuOnce, { once: true }), 0);
}
function closeMenuOnce(e) {
  if (e.target.closest(".pop") || e.target.closest("[data-act=menu]")) return;
  const box = $("#menuRoot");
  if (box) box.innerHTML = "";
}
const closeMenu = () => { const b = $("#menuRoot"); if (b) b.innerHTML = ""; };

/* ---------------------------------------------------------------- 图形 */
/** Catmull-Rom → 三次贝塞尔：把折线变成平滑曲线（行情图观感的关键） */
function smoothPath(pts) {
  if (pts.length < 3) return pts.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ` +
         `${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

function sparkline(vals, w = 240, h = 38, forceColor) {
  if (!vals || vals.length < 2) {
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"
      style="width:100%;height:100%;display:block">
      <line x1="0" y1="${h / 2}" x2="${w}" y2="${h / 2}" stroke="rgba(255,255,255,.08)" stroke-width="1"/></svg>`;
  }
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = 3;
  const X = (i) => (w * i) / (vals.length - 1);
  const Y = (v) => h - pad - ((v - lo) / (hi - lo || 1)) * (h - pad * 2);
  const up = vals[vals.length - 1] >= vals[0];
  const color = forceColor || (up ? "#22c55e" : "#f43f5e");
  const d = smoothPath(vals.map((v, i) => [X(i), Y(v)]));
  const id = "sg" + Math.random().toString(36).slice(2, 8);
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"
    style="width:100%;height:100%;display:block">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${color}" stop-opacity=".3"/>
      <stop offset="100%" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
    <path d="${d} L ${w} ${h} L 0 ${h} Z" fill="url(#${id})"/>
    <path d="${d}" fill="none" stroke="${color}" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

/**
 * 主行情图：折线 + 面积 + 网格 + 十字光标 + 悬浮提示。
 * 返回 { html, mount(el) }，mount 负责绑定鼠标交互（重渲染后需要重新 mount）。
 */
function priceChart(points, opts = {}) {
  const w = 780, h = opts.height || 260;
  const pad = { l: 42, r: 12, t: 14, b: 22 };
  if (!points || points.length < 2) {
    return {
      html: `<div class="empty">${icon("chart")}<b>暂无价格数据</b><span>市场开盘后成交会生成价格点</span></div>`,
      mount() {},
    };
  }
  const color = opts.color || "#5b8cff";
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const ys = points.map((p) => p.price_cents);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  const span = Math.max(hi - lo, 6);
  lo = Math.max(0, Math.floor(lo - span * 0.35));
  hi = Math.min(100, Math.ceil(hi + span * 0.35));
  const X = (i) => pad.l + (points.length === 1 ? iw / 2 : (iw * i) / (points.length - 1));
  const Y = (v) => pad.t + ih * (1 - (v - lo) / (hi - lo || 1));
  const line = smoothPath(points.map((p, i) => [X(i), Y(p.price_cents)]));
  const gid = "cg" + Math.random().toString(36).slice(2, 8);

  let grid = "";
  for (let g = 0; g <= 4; g++) {
    const v = lo + ((hi - lo) * g) / 4, y = Y(v);
    grid += `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${w - pad.r}" y2="${y.toFixed(1)}"
      stroke="rgba(255,255,255,.05)" stroke-width="1"/>
      <text x="${pad.l - 8}" y="${(y + 3.5).toFixed(1)}" fill="#5b6478" font-size="10.5"
        text-anchor="end" font-family="ui-monospace,monospace">${Math.round(v)}¢</text>`;
  }
  const last = points[points.length - 1];
  const html = `<div class="chartbox" data-chart>
    <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto;display:block">
      <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity=".26"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
      ${grid}
      <path d="${line} L ${X(points.length - 1)} ${pad.t + ih} L ${pad.l} ${pad.t + ih} Z" fill="url(#${gid})"/>
      <path d="${line}" fill="none" stroke="${color}" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${X(points.length - 1)}" cy="${Y(last.price_cents)}" r="3.6" fill="${color}"
        stroke="#0b0e14" stroke-width="2"/>
      <g data-cursor style="opacity:0">
        <line data-cline x1="0" y1="${pad.t}" x2="0" y2="${pad.t + ih}" stroke="rgba(255,255,255,.28)"
          stroke-width="1" stroke-dasharray="3 3"/>
        <circle data-cdot r="4" fill="${color}" stroke="#0b0e14" stroke-width="2"/>
      </g>
      <text x="${pad.l}" y="${h - 6}" fill="#5b6478" font-size="10.5">${when(points[0].ts).slice(0, 11)}</text>
      <text x="${w - pad.r}" y="${h - 6}" fill="#5b6478" font-size="10.5" text-anchor="end">${when(last.ts).slice(0, 11)}</text>
    </svg>
    <div class="tip" data-tip></div>
  </div>`;

  const mount = (root) => {
    const box = root.querySelector("[data-chart]");
    if (!box) return;
    const svg = box.querySelector("svg");
    const cursor = box.querySelector("[data-cursor]");
    const line = box.querySelector("[data-cline]");
    const dot = box.querySelector("[data-cdot]");
    const tip = box.querySelector("[data-tip]");
    const move = (ev) => {
      const rect = svg.getBoundingClientRect();
      const xv = ((ev.clientX - rect.left) / rect.width) * w;
      let idx = 0, best = Infinity;
      for (let i = 0; i < points.length; i++) {
        const d = Math.abs(X(i) - xv);
        if (d < best) { best = d; idx = i; }
      }
      const px = X(idx), py = Y(points[idx].price_cents);
      cursor.style.opacity = 1;
      line.setAttribute("x1", px); line.setAttribute("x2", px);
      dot.setAttribute("cx", px); dot.setAttribute("cy", py);
      tip.classList.add("on");
      tip.style.left = (px / w) * 100 + "%";
      tip.style.top = (py / h) * 100 + "%";
      tip.innerHTML = `<b>${points[idx].price_cents}¢</b><span class="t">${when(points[idx].ts)}</span>`;
    };
    svg.addEventListener("mousemove", move);
    svg.addEventListener("mouseleave", () => {
      cursor.style.opacity = 0;
      tip.classList.remove("on");
    });
  };
  return { html, mount };
}

/* ---------------------------------------------------------------- 卡片 */
function marketCard(m, opts = {}) {
  const first = m.outcomes[0] || { price_cents: 50, name: "会" };
  const second = m.outcomes[1];
  const delta = m.trend ? m.trend.delta_cents : 0;
  const starred = S.watch.has(m.id);
  const isOpen = m.status === "open";
  const yesPct = first.price_cents;
  const multi = m.outcomes.length > 2;
  return `<article class="card" data-mid="${m.id}">
    ${m.featured ? `<span class="badge">精选</span>` : ""}
    <div class="hd">
      ${tile(m.category)}
      <div class="cat">${esc(m.category)}<b>${isOpen ? dayLeft(m.closes_at) : m.status === "resolved" ? "已结算" : "已停盘"}</b></div>
      <div class="grow"></div>
      <button class="iconbtn ${starred ? "starred" : ""}" data-act="watch" data-mid="${m.id}"
        title="${starred ? "取消关注" : "关注"}">${icon("star")}</button>
    </div>
    <a href="#/market/${m.id}"><h3>${esc(m.question)}</h3></a>
    <div class="prob">
      <div>
        <div class="num">${yesPct}<small>¢</small></div>
        <div class="chip-delta ${delta > 0 ? "up" : delta < 0 ? "down" : "flat"}" style="margin-top:5px">
          ${delta > 0 ? "▲" : delta < 0 ? "▼" : "—"} ${Math.abs(delta)}¢ 24h
        </div>
      </div>
      <div class="spark">${sparkline(m.spark, 240, 38)}</div>
    </div>
    <div class="split" title="${esc(first.name)} ${yesPct}% / ${esc((second || {}).name || "")} ${second ? second.price_cents : 0}%">
      <i class="y" style="width:${yesPct}%"></i><i class="n" style="width:${100 - yesPct}%"></i>
    </div>
    <div class="buyrow ${multi ? "multi" : ""}">
      ${multi
        ? `<button class="bbtn all" data-act="go" data-mid="${m.id}">${m.outcomes.length} 个结果 ·
             ${esc(first.name)} ${first.price_cents}¢ 起</button>`
        : `<button class="bbtn yes" data-act="go" data-mid="${m.id}" data-oid="${first.id}">
             <span class="nm">买入「${esc(first.name)}」</span><span class="p">${first.price_cents}¢</span></button>
           <button class="bbtn no" data-act="go" data-mid="${m.id}" data-oid="${second.id}">
             <span class="nm">买入「${esc(second.name)}」</span><span class="p">${second.price_cents}¢</span></button>`}
    </div>
    <div class="ft">
      <span>${icon("chart")} ${moneyShort(m.volume_cents)}</span>
      <span class="dot"></span>
      <span>${icon("users")} ${num(m.traders_count || 0)} 人参与</span>
      <div class="grow"></div>
      <span>${num(m.trades_count)} 笔</span>
    </div>
  </article>`;
}

const skeletonCards = (n = 6) =>
  Array.from({ length: n }, () => `<div class="sk sk-card"></div>`).join("");

/* ---------------------------------------------------------------- 首页 */
async function renderMarkets() {
  const app = $("#app");
  if (app.dataset.shell !== "markets") {
    app.dataset.shell = "markets";
    app.innerHTML = `<div class="catbar"><div class="inner" id="catbar"></div></div>
      <div class="wrap">
        <section class="hero" id="hero">
          <div class="sk sk-card" style="height:300px;grid-column:1/-1"></div>
        </section>
        <div class="section-head">
          <h2>全部市场</h2><span class="sub" id="listSub"></span>
          <div class="grow"></div>
          <span class="sub" id="listCount"></span>
        </div>
        <div class="grid" id="grid">${skeletonCards(6)}</div>
        <section style="margin-top:34px">
          <div class="section-head"><h2>PredX 怎么运作</h2>
            <span class="sub">三步把判断变成头寸</span></div>
          <div class="grid" style="grid-template-columns:repeat(3,1fr)">
            ${[["target", "1 · 选择事件", "浏览按分类整理的事件市场，价格 1–99 分就是市场当前给出的概率。"],
               ["bolt", "2 · 买入你的判断", "认为概率被低估就买入；市价即时成交，限价单挂在盘口等对手方。"],
               ["check", "3 · 到期结算兑付", "事件发生则每份合约兑付 $1.00，否则归零；盈亏实时结算到账户。"]]
              .map(([ic, t, d]) => `<div style="background:var(--surface);border:1px solid var(--line);
                border-radius:var(--r-lg);padding:18px">
                <div style="width:34px;height:34px;border-radius:10px;display:grid;place-items:center;
                  background:var(--brand-soft);color:var(--brand)">${icon(ic)}</div>
                <div style="font-weight:750;margin:11px 0 6px;font-size:13.5px">${t}</div>
                <div style="color:var(--muted);font-size:12.5px;line-height:1.75">${d}</div></div>`).join("")}
          </div>
        </section>
        <div class="footer">
          <span>${icon("shield")} 演示环境：全部资金为虚拟体验金</span>
          <span>不接入真实支付</span><span>不发行任何代币</span>
          <div class="grow"></div>
          <span>PredX v1.1 · 事件合约交易终端</span>
        </div>
      </div>`;
  }

  // 分类条
  const cats = S.cats.length ? S.cats : CATS.map((c) => ({ category: c, n: "" }));
  $("#catbar").innerHTML = `
    <button class="catpill ${S.q.cat === "all" ? "on" : ""}" data-act="cat" data-v="all">
      ${icon("grid")}全部<span class="n">${cats.some((c) => c.n) ? num(cats.reduce((a, c) => a + Number(c.n || 0), 0)) : ""}</span></button>
    ${cats.map((c) => `<button class="catpill ${S.q.cat === c.category ? "on" : ""}"
        data-act="cat" data-v="${esc(c.category)}">
        ${icon((CAT_META[c.category] || CAT_META["综合"]).icon)}${esc(c.category)}
        <span class="n">${c.n || ""}</span></button>`).join("")}
    <button class="catpill ${S.q.cat === "starred" ? "on" : ""}" data-act="cat" data-v="starred">
      ${icon("star")}关注<span class="n">${S.watch.size || ""}</span></button>
    <span class="sep"></span>
    <div class="selwrap">
      <select class="sel" id="sortSel" data-act="sortsel">
        ${[["hot", "精选优先"], ["new", "最新上架"], ["closing", "即将截止"], ["trending", "最活跃"]]
          .map(([k, t]) => `<option value="${k}" ${S.q.sort === k ? "selected" : ""}>${t}</option>`).join("")}
      </select>${icon("down")}
    </div>
  `;

  const params = new URLSearchParams({ status: S.q.status, sort: S.q.sort, limit: "60" });
  const starredOnly = S.q.cat === "starred";
  if (S.q.cat !== "all" && !starredOnly) params.set("category", S.q.cat);
  if (S.q.text) params.set("q", S.q.text);

  try {
    const [stats, list] = await Promise.all([
      api("/api/markets/stats").catch(() => null),
      api("/api/markets?" + params.toString()),
      api("/api/markets/categories").then((d) => (S.cats = d.items)).catch(() => null),
    ]);
    S.stats = stats;
    let items = list.items || [];
    if (starredOnly) {
      if (!S.user) {
        $("#grid").innerHTML = `<div class="empty" style="grid-column:1/-1">${icon("star")}
          <b>登录后可查看关注的市场</b>
          <button class="btn primary sm" data-act="login" style="margin-top:6px">去登录</button></div>`;
        $("#listCount").textContent = "";
        return;
      }
      items = items.filter((m) => S.watch.has(m.id));
    }

    // hero：精选市场 + 平台数据
    const spot = items.find((m) => m.featured) || items[0];
    const top = await api("/api/leaderboard?limit=3").catch(() => ({ items: [] }));
    if (spot) {
      const first = spot.outcomes[0];
      const chart = priceChart((spot.spark || []).map((p, i) => ({ price_cents: p, ts: "" })), { height: 120 });
      $("#hero").innerHTML = `
        <div class="spot">
          <span class="tagline">${icon("flame")} 精选市场</span>
          <h2><a href="#/market/${spot.id}">${esc(spot.question)}</a></h2>
          <div class="row">
            <div class="big">${first.price_cents}<small>¢</small></div>
            <div style="padding-bottom:6px">
              <div class="chip-delta ${(spot.trend?.delta_cents || 0) >= 0 ? "up" : "down"}">
                ${(spot.trend?.delta_cents || 0) >= 0 ? "▲" : "▼"} ${Math.abs(spot.trend?.delta_cents || 0)}¢ 24h
              </div>
              <div style="color:var(--muted);font-size:12px;margin-top:6px">
                「${esc(first.name)}」隐含概率 ${first.price_cents}% · ${dayLeft(spot.closes_at)}
              </div>
            </div>
          </div>
          <div style="display:flex;gap:14px;margin-top:10px;color:var(--faint);font-size:11.5px;font-weight:650">
            <span>${icon("chart")} ${moneyShort(spot.volume_cents)} 成交</span>
            <span>${icon("users")} ${num(spot.traders_count)} 人参与</span>
            <span>${icon("layers")} ${num(spot.trades_count)} 笔</span>
          </div>
          <div class="chart" style="height:132px">${sparkline(spot.spark, 620, 132,
            (spot.trend?.delta_cents || 0) >= 0 ? "#22c55e" : "#f43f5e")}</div>
          <div class="cta">
            <a class="btn yes" href="#/market/${spot.id}">买入「${esc(first.name)}」 ${first.price_cents}¢</a>
            <a class="btn no" href="#/market/${spot.id}">买入「${esc(spot.outcomes[1].name)}」 ${spot.outcomes[1].price_cents}¢</a>
          </div>
        </div>
        <div class="sidestats">
          <div class="kpi">
            <div class="box"><div class="k">${icon("chart")}累计成交额</div>
              <div class="v">${money0(stats ? stats.volume_cents : 0)}</div>
              <div class="d">24h ${money0(stats ? stats.volume_24h_cents : 0)}</div></div>
            <div class="box"><div class="k">${icon("layers")}进行中市场</div>
              <div class="v">${num(stats ? stats.open_markets : 0)}</div>
              <div class="d">共 ${num(stats ? stats.markets : 0)} 个事件</div></div>
            <div class="box"><div class="k">${icon("users")}活跃交易者</div>
              <div class="v">${num(stats ? stats.active_traders_24h : 0)}</div>
              <div class="d">近 24 小时</div></div>
            <div class="box"><div class="k">${icon("bolt")}成交笔数</div>
              <div class="v">${num(stats ? stats.trades : 0)}</div>
              <div class="d">24h ${num(stats ? stats.trades_24h : 0)} 笔</div></div>
          </div>
          <div class="traders">
            <div class="hd"><b>${icon("trophy")} 领先交易员</b><a href="#/leaderboard">全部 →</a></div>
            ${(top.items || []).map((u, i) => `
              <div class="trow">
                <span class="rank">${i + 1}</span>
                ${avatar(u.handle, 26)}
                <span class="nm">${esc(u.handle)}</span>
                <span class="pnl ${cls(u.pnl_cents)}">${signed(u.pnl_cents)}</span>
              </div>`).join("") || `<div class="empty" style="padding:14px">暂无排名</div>`}
          </div>
        </div>`;
    }

    $("#listSub").textContent = S.q.text ? `“${S.q.text}” 的搜索结果`
      : starredOnly ? "我关注的市场" : (S.q.cat === "all" ? "按成交额排序" : S.q.cat);
    $("#listCount").textContent = `${items.length} 个市场`;
    $("#grid").innerHTML = items.length
      ? items.map((m) => marketCard(m)).join("")
      : `<div class="empty" style="grid-column:1/-1">${icon("search")}
           <b>没有匹配的市场</b><span>换个分类，或清空搜索关键词试试</span></div>`;
  } catch (e) {
    $("#grid").innerHTML = `<div class="empty" style="grid-column:1/-1">${icon("alert")}
      <b>加载失败</b><span>${esc(e.message)}</span></div>`;
  }
}

/* ---------------------------------------------------------------- 详情页 */
const DS = { tab: "overview", oid: null, range: "all", data: null, hist: null, pos: null };

async function renderMarket(id) {
  const app = $("#app");
  app.dataset.shell = "market";
  if (!DS.data || Number(DS.data.id) !== Number(id)) {
    app.innerHTML = `<div class="wrap"><div class="sk sk-line" style="width:40%;height:26px"></div>
      <div class="sk sk-line" style="width:70%"></div>
      <div class="grid" style="margin-top:18px">${skeletonCards(2)}</div></div>`;
  }
  let m;
  try { m = await api(`/api/markets/${id}`); }
  catch (e) {
    app.innerHTML = `<div class="wrap"><div class="empty">${icon("alert")}<b>${esc(e.message)}</b>
      <a class="btn" href="#/markets" style="margin-top:8px">返回市场</a></div></div>`;
    return;
  }
  DS.data = m;
  if (!DS.oid || !m.outcomes.some((o) => o.id === DS.oid)) DS.oid = m.outcomes[0].id;
  const sel = m.outcomes.find((o) => o.id === DS.oid) || m.outcomes[0];

  let hist = { series: {}, stats: {} };
  try { hist = await api(`/api/markets/${id}/history?outcome_id=${DS.oid}&range=${DS.range}&limit=400`); }
  catch (_) {}
  DS.hist = hist;

  let pos = null;
  if (S.user) { try { pos = await api("/api/portfolio"); } catch (_) {} }
  DS.pos = pos;
  const myPos = pos ? pos.positions.find((p) => p.market_id == m.id && p.outcome_id == DS.oid) : null;

  const series = (hist.series && hist.series[DS.oid]) || [];
  const st = (hist.stats && hist.stats[DS.oid]) || {};
  const delta = st.delta_cents ?? (m.trend ? m.trend.delta_cents : 0);
  const chart = priceChart(series, { color: sel.price_cents >= 50 ? "#22c55e" : "#5b8cff", height: 250 });
  const starred = S.watch.has(m.id);
  const isOpen = m.status === "open";

  app.innerHTML = `<div class="wrap">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:14px;color:var(--faint);font-size:12.5px">
      <a href="#/markets" style="display:flex;align-items:center;gap:4px">${icon("back")}市场</a>
      <span>/</span><a href="#/markets" data-act="cat" data-v="${esc(m.category)}">${esc(m.category)}</a>
      <span>/</span><span style="color:var(--text-2)">#${m.id}</span>
    </div>

    <div class="detail-grid">
      <div class="stack">
        <section class="panel"><div class="pb">
          <div class="dtop">
            ${tile(m.category, "")}
            <div style="flex:1;min-width:0">
              <h1>${esc(m.question)}</h1>
              <div class="chips">
                <span class="chip">${esc(m.category)}</span>
                <span class="chip">${m.outcomes.length === 2 ? "二元合约" : m.outcomes.length + " 结果合约"}</span>
                <span class="chip ${isOpen ? "live" : "done"}">${isOpen ? "交易中" : m.status === "resolved" ? "已结算" : "已停盘"}</span>
                <span class="chip">${icon("clock")}${dayLeft(m.closes_at)}</span>
                <span class="chip">${icon("users")}${num(m.traders_count)} 人参与</span>
                <span class="chip">${icon("chart")}${moneyShort(m.volume_cents)} 成交</span>
              </div>
            </div>
            <button class="iconbtn ${starred ? "starred" : ""}" data-act="watch" data-mid="${m.id}"
              title="${starred ? "取消关注" : "关注"}">${icon("star")}</button>
          </div>

          <div class="price-head">
            <div>
              <div class="name">${esc(sel.name)} · 当前价格</div>
              <div class="val">${sel.price_cents}<small>¢</small></div>
            </div>
            <div style="padding-bottom:6px;display:flex;gap:8px;align-items:center">
              <span class="chip-delta ${delta > 0 ? "up" : delta < 0 ? "down" : "flat"}">
                ${delta > 0 ? "▲" : delta < 0 ? "▼" : "—"} ${Math.abs(delta)}¢
                ${({ "1h": "1H", "6h": "6H", "1d": "1D", "1w": "1W", "1m": "1M", all: "全部" })[DS.range]}</span>
              <span style="color:var(--faint);font-size:12px">高 ${st.high_cents ?? sel.price_cents}¢ · 低 ${st.low_cents ?? sel.price_cents}¢</span>
            </div>
            <div class="grow" style="flex:1"></div>
            <div class="rangetabs">
              ${[["1h", "1H"], ["6h", "6H"], ["1d", "1D"], ["1w", "1W"], ["1m", "1M"], ["all", "全部"]]
                .map(([k, t]) => `<button class="${DS.range === k ? "on" : ""}" data-act="range" data-v="${k}">${t}</button>`).join("")}
            </div>
          </div>

          <div class="ochips" style="margin-bottom:8px">
            ${m.outcomes.map((o) => `<button class="ochip ${o.id === DS.oid ? "on" : ""}" data-act="pick" data-oid="${o.id}">
              ${esc(o.name)} <span class="p">${o.price_cents}¢</span></button>`).join("")}
          </div>
          ${chart.html}
        </div></section>

        <section class="panel">
          <div class="tabs">
            ${[["overview", "概览", ""], ["book", "订单簿", ""], ["trades", "成交", m.recent_trades.length],
               ["holders", "持仓榜", m.top_holders.length], ["comments", "评论", m.comments_count]]
              .map(([k, label, n]) => `<button class="${DS.tab === k ? "on" : ""}" data-act="tab" data-v="${k}">
                ${label}${n ? `<span class="count">${n}</span>` : ""}</button>`).join("")}
          </div>
          <div class="pb" id="tabBody">${tabBody(m, DS.oid)}</div>
        </section>

        ${(m.related && m.related.length) ? `<section>
          <div class="section-head"><h2>同类市场</h2><span class="sub">${esc(m.category)}</span></div>
          <div class="grid">${m.related.map((r) => marketCard(r)).join("")}</div>
        </section>` : ""}
      </div>

      <aside class="stack">
        <div class="panel trade" id="tradePanel">${tradePanelHTML(m, DS.oid, myPos)}</div>
        <div class="panel"><div class="pb" style="padding:14px 16px">
          <div style="font-size:12px;font-weight:800;color:var(--text-2);margin-bottom:8px">${icon("info")} 结算规则</div>
          <div style="color:var(--muted);font-size:12.5px;line-height:1.7">
            ${esc((m.rules || "以官方公布结果为最终依据。").slice(0, 160))}
          </div>
          ${m.source_url ? `<a href="${esc(m.source_url)}" target="_blank" rel="noopener"
            style="color:var(--brand);font-size:12px;font-weight:700;display:inline-block;margin-top:8px">
            查看数据来源 →</a>` : ""}
        </div></div>
      </aside>
    </div>
  </div>`;

  chart.mount(app);
  drawTab(m, DS.oid);
  wireTrade(m, DS.oid, myPos);
}

function tabBody(m, oid) {
  if (DS.tab === "overview") {
    return `<div style="color:var(--text-2);font-size:13px;line-height:1.8">
        ${esc(m.description || "该市场暂无补充说明。").replace(/\n/g, "<br>")}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px">
        <div style="background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:13px">
          <div style="font-size:11.5px;font-weight:800;color:var(--muted);letter-spacing:.4px">结算规则</div>
          <div style="margin-top:6px;font-size:12.5px;color:var(--text-2);line-height:1.75">
            ${esc(m.rules || "以市场截止后的官方结果为准；答对的结果每份兑付 $1.00，其余归零。")}</div>
        </div>
        <div style="background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:13px">
          <div style="font-size:11.5px;font-weight:800;color:var(--muted);letter-spacing:.4px">交易机制</div>
          <div style="margin-top:6px;font-size:12.5px;color:var(--text-2);line-height:1.75">
            1 分 = 1% 隐含概率，1 份合约结算价 $1.00。<br>
            撮合：对手限价单 → LMSR 做市商 → 残余挂单。<br>
            吃单手续费 ${(m.fee_bps / 100).toFixed(2)}%，挂单免费。流动性深度 b=${m.liquidity_b}。
          </div>
        </div>
      </div>`;
  }
  if (DS.tab === "book") {
    const books = m.books || {};
    return m.outcomes.map((o) => {
      const b = books[o.id] || books[String(o.id)] ||
        { asks: [], bids: [], best_ask_cents: o.price_cents, best_bid_cents: o.price_cents, spread_cents: 0 };
      const maxQ = Math.max(1, ...b.asks.map((x) => Number(x.qty) || 0), ...b.bids.map((x) => Number(x.qty) || 0));
      const row = (x, kind) => `<div class="lrow ${kind} ${x.src !== "amm" ? "user" : ""}">
          <div class="bar" style="width:${Math.min(100, ((Number(x.qty) || 0) / maxQ) * 100)}%"></div>
          <span class="p">${Number(x.price_cents).toFixed(1)}¢</span>
          <span class="q">${num(x.qty)} 份${x.src === "amm" ? "" : " · 用户"}</span>
        </div>`;
      return `<div style="margin-bottom:20px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:9px">
          <b style="font-size:13.5px">${esc(o.name)}</b>
          <span style="color:var(--muted);font-size:12px">
            卖一 <b style="color:#fb7185">${Number(b.best_ask_cents).toFixed(1)}¢</b> ·
            买一 <b style="color:#4ade80">${Number(b.best_bid_cents).toFixed(1)}¢</b></span>
        </div>
        <div class="ladder">
          <div class="col">
            <div class="cap"><span>卖盘 ASK · 你买入</span><span>价格 / 数量</span></div>
            ${(b.asks || []).slice(0, 5).map((x) => row(x, "ask")).join("") ||
              `<div class="lrow"><span class="q">暂无挂单</span></div>`}
          </div>
          <div class="col">
            <div class="cap"><span>买盘 BID · 你卖出</span><span>价格 / 数量</span></div>
            ${(b.bids || []).slice(0, 5).map((x) => row(x, "bid")).join("") ||
              `<div class="lrow"><span class="q">暂无挂单</span></div>`}
          </div>
        </div>
        <div class="spread">价差 <b>${Number(b.spread_cents || 0).toFixed(1)}¢</b>
          <span style="color:var(--faint)">· 做市商最大敞口 ${moneyShort(b.amm_max_loss_cents || 0)}</span></div>
      </div>`;
    }).join("");
  }
  if (DS.tab === "trades") {
    const rows = m.recent_trades || [];
    if (!rows.length) return `<div class="empty">${icon("chart")}<b>还没有成交</b></div>`;
    return `<div class="tape">
      <div class="taprow" style="color:var(--muted);font-size:10.5px;font-weight:800;letter-spacing:.4px">
        <span>时间</span><span>结果</span><span style="text-align:right">价格</span>
        <span style="text-align:right">份数</span><span class="cparty" style="text-align:right">买方 / 卖方</span></div>
      ${rows.map((t) => `<div class="taprow">
        <span class="dim mono">${when(t.created_at).slice(0, 11)}</span>
        <span>${esc(t.outcome_name)}</span>
        <span style="text-align:right;font-weight:800">${t.price_cents}¢</span>
        <span style="text-align:right" class="dim">${num(t.qty)}</span>
        <span class="cparty" style="text-align:right;color:var(--muted);font-size:11px">
          ${esc(t.buyer_handle || "做市商")} / ${esc(t.seller_handle || "做市商")}</span>
      </div>`).join("")}</div>`;
  }
  if (DS.tab === "holders") {
    const hs = m.top_holders || [];
    if (!hs.length) return `<div class="empty">${icon("users")}<b>暂无持仓大户</b></div>`;
    const max = Math.max(...hs.map((h) => h.shares));
    return `<div style="display:flex;flex-direction:column;gap:8px">
      ${hs.map((h, i) => {
        const price = (m.outcomes.find((o) => o.id === h.outcome_id) || {}).price_cents || 0;
        return `<div style="display:flex;align-items:center;gap:10px">
          <span style="width:14px;color:var(--faint);font-weight:800;font-size:12px">${i + 1}</span>
          ${avatar(h.handle, 26)}
          <span style="width:96px;font-size:12.5px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(h.handle)}</span>
          <span class="chip" style="flex:none">${esc(h.outcome_name)}</span>
          <div class="bar-cell" style="flex:1"><div class="track"><div class="fill" style="width:${(h.shares / max) * 100}%"></div></div></div>
          <span style="width:78px;text-align:right;font-size:12.5px;font-weight:700">${num(h.shares)} 份</span>
          <span style="width:86px;text-align:right;font-size:12px;color:var(--muted)">${money(h.shares * price)}</span>
        </div>`;
      }).join("")}</div>`;
  }
  return `<div id="cmtList"><div class="sk sk-line" style="width:60%"></div><div class="sk sk-line" style="width:80%"></div></div>
    ${S.user ? `<div class="cmtbox">
        <input id="cmtInput" placeholder="说说你的判断…（Enter 发布）" maxlength="500">
        <button class="btn primary" data-act="comment">发布</button>
      </div>` : `<div class="note" style="margin-top:0">${icon("info")}
        登录后即可参与讨论。</div>`}`;
}

async function drawTab(m, oid) {
  if (DS.tab !== "comments") return;
  const box = $("#cmtList");
  try {
    const d = await api(`/api/markets/${m.id}/comments`);
    if (!$("#cmtList")) return;
    $("#cmtList").innerHTML = (d.items || []).length
      ? d.items.map((c) => `<div class="cmt">${avatar(c.handle, 30)}
          <div style="flex:1;min-width:0">
            <div><span class="who">${esc(c.handle)}</span><span class="when">${relTime(c.created_at)}</span></div>
            <p>${esc(c.body)}</p></div></div>`).join("")
      : `<div class="empty">${icon("users")}<b>还没有评论</b><span>来做第一个发言的人</span></div>`;
  } catch (e) {
    if (box) box.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

/* ---------------------------------------------------------------- 交易面板 */
function tradePanelHTML(m, oid, myPos) {
  const sel = m.outcomes.find((o) => o.id === oid) || m.outcomes[0];
  if (m.status !== "open") {
    return `<div class="ph">${m.status === "resolved" ? "已结算" : "已停盘"}</div>
      <div class="pb"><div class="empty">${icon("check")}
        <b>${m.status === "resolved" ? "该市场已结算" : "该市场已停止交易"}</b>
        <span>${m.status === "resolved" ? "赢家结果已按每份 $1.00 兑付" : "等待管理员复牌或结算"}</span></div></div>`;
  }
  return `<div class="ph"><span>${icon("bolt")} 下单</span><div class="grow"></div>
      <span class="hint">${esc(sel.name)} · ${sel.price_cents}¢</span></div>
    <div class="pb">
      <div class="side">
        <button data-act="side" data-v="buy" class="on buy">买入</button>
        <button data-act="side" data-v="sell" class="sell">卖出</button>
      </div>

      <div class="field">
        <label>选择结果</label>
        <div class="opts">
          ${m.outcomes.map((o) => `<button class="opt ${o.id === oid ? "on" : ""}" data-act="pick" data-oid="${o.id}">
            <span>${esc(o.name)}</span>
            <span class="p">${o.price_cents}¢ <small>${o.price_cents}%</small></span></button>`).join("")}
        </div>
      </div>

      <div class="field" style="display:flex;align-items:center;justify-content:space-between">
        <label style="margin:0">订单类型</label>
        <div class="rangetabs" id="modeSeg">
          <button data-act="mode" data-v="market" class="on">市价</button>
          <button data-act="mode" data-v="limit">限价</button>
        </div>
      </div>

      <div class="field">
        <label><span id="amtLabel">金额</span><span id="amtHint"></span></label>
        <div class="inputbox">
          <span class="pre" id="amtPre">$</span>
          <input id="amtInput" inputmode="decimal" placeholder="100.00" autocomplete="off">
          <span class="suf" id="amtSuf"></span>
        </div>
        <div class="quick" id="quickRow">
          <button data-act="quick" data-v="0.25">25%</button>
          <button data-act="quick" data-v="0.5">50%</button>
          <button data-act="quick" data-v="0.75">75%</button>
          <button data-act="quick" data-v="1">最大</button>
          <button data-act="quick" data-v="100">$100</button>
        </div>
      </div>

      <div class="field" id="pxField" style="display:none">
        <label><span>限价</span><span>1–99 分</span></label>
        <div class="inputbox">
          <button class="iconbtn" data-act="pxstep" data-v="-1" style="width:26px;height:26px">−</button>
          <input id="pxInput" inputmode="numeric" value="${sel.price_cents}" style="text-align:center">
          <button class="iconbtn" data-act="pxstep" data-v="1" style="width:26px;height:26px">+</button>
        </div>
      </div>

      <div class="quote" id="quoteBox">
        <div class="l"><span>预估成交份额</span><b id="qQty">—</b></div>
        <div class="l"><span>成交均价</span><b id="qAvg">—</b></div>
        <div class="l"><span>手续费</span><b id="qFee">—</b></div>
        <div class="l total"><span id="qTotalLabel">合计支付</span><b id="qTotal">—</b></div>
        <div class="l win"><span id="qWinLabel">若猜对可兑付</span><b id="qWin">—</b></div>
      </div>

      <button class="btn yes block lg" id="submitBtn" style="margin-top:12px" data-act="submit">
        买入「${esc(sel.name)}」</button>
      <div class="hintline" id="tradeWarn"></div>

      <div style="display:flex;justify-content:space-between;margin-top:8px;padding-top:10px;
        border-top:1px solid var(--line);color:var(--faint);font-size:11.5px;font-weight:600">
        <span>可用 ${S.user ? money(S.user.balance_cents) : "登录后可用"}</span>
        <span>${myPos ? `持仓 ${num(myPos.shares)} 份 · 可卖 ${num(myPos.shares - myPos.locked_shares)}` : "当前未持有"}</span>
      </div>
    </div>`;
}

function wireTrade(m, oid, myPos) {
  const st = { side: "buy", mode: "market" };
  const el = {
    amt: $("#amtInput"), px: $("#pxInput"), pxField: $("#pxField"),
    label: $("#amtLabel"), pre: $("#amtPre"), suf: $("#amtSuf"), hint: $("#amtHint"),
    warn: $("#tradeWarn"), submit: $("#submitBtn"),
  };
  if (!el.amt) return;
  const cur = () => m.outcomes.find((o) => o.id === DS.oid) || m.outcomes[0];

  function sync() {
    const sell = st.side === "sell";
    $$("#tradePanel [data-act=side]").forEach((b, i) => {
      b.classList.toggle("on", (i === 0) === !sell);
      b.classList.toggle("buy", i === 0); b.classList.toggle("sell", i === 1);
    });
    $$("#modeSeg button").forEach((b) => b.classList.toggle("on", b.dataset.v === st.mode));
    el.pxField.style.display = st.mode === "limit" ? "block" : "none";
    const isQty = sell || st.mode === "limit";
    el.label.textContent = isQty ? (sell ? "卖出份额" : "买入份额") : "金额";
    el.hint.textContent = isQty ? "单位：份" : `可用 ${S.user ? money(S.user.balance_cents) : "—"}`;
    el.pre.textContent = isQty ? "" : "$";
    el.suf.textContent = isQty ? "份" : "";
    el.amt.placeholder = isQty ? "100" : "100.00";
    el.submit.className = "btn block lg " + (sell ? "no" : "yes");
    el.submit.style.marginTop = "12px";
    el.submit.textContent = `${sell ? "卖出" : "买入"}「${cur().name}」`;
    $("#qTotalLabel").textContent = sell ? "预计到手" : "合计支付";
    $("#qWinLabel").textContent = sell ? "持仓全对可兑付" : "若猜对可兑付";
  }

  let timer = null;
  function body() {
    const raw = (el.amt.value || "").trim();
    const isQty = st.side === "sell" || st.mode === "limit";
    const n = parseFloat(raw);
    const out = { outcome_id: DS.oid, side: st.side };
    if (!isNaN(n) && n > 0) {
      if (isQty) out.qty = Math.floor(n);
      else out.amount_cents = Math.round(n * 100);
    }
    if (st.mode === "limit") {
      const p = parseInt(el.px.value, 10);
      if (!isNaN(p)) out.price_cents = Math.min(99, Math.max(1, p));
    }
    out.max_slippage_bps = 500;          // 与下单一致：最多接受 5% 价格保护
    return out;
  }

  function reset() {
    ["#qQty", "#qAvg", "#qFee", "#qTotal", "#qWin"].forEach((s) => { const n = $(s); if (n) n.textContent = "—"; });
    el.warn.textContent = ""; el.warn.className = "hintline";
  }

  function refresh() {
    const b = body();
    if (!b.qty && !b.amount_cents) { reset(); return; }
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const q = await api(`/api/markets/${m.id}/quote`, { method: "POST", body: b });
        $("#qQty").textContent = num(q.qty) + " 份";
        $("#qAvg").textContent = Number(q.avg_cents).toFixed(1) + "¢";
        $("#qFee").textContent = money(q.fee_cents);
        $("#qTotal").textContent = money(q.total_cents);
        $("#qWin").textContent = st.side === "sell"
          ? money((myPos ? myPos.shares : 0) * 100)
          : `${money(q.payout_if_win_cents)} (+${money(q.payout_if_win_cents - q.total_cents)})`;
        if (!q.qty) {
          el.warn.className = "hintline err";
          el.warn.innerHTML = `${icon("alert")}该价位没有可成交的流动性，请调价或减小数量`;
        } else if (b.amount_cents && q.total_cents < b.amount_cents * 0.97 && st.side === "buy") {
          el.warn.className = "hintline warn";
          el.warn.innerHTML = `${icon("info")}当前深度下最多成交 ${num(q.qty)} 份（${money(q.total_cents)}）；
            剩余金额可提高限价后继续买入`;
        } else if (q.price_after_cents !== q.mid_cents) {
          el.warn.className = "hintline warn";
          const slip = (q.avg_cents - q.mid_cents).toFixed(1);
          el.warn.innerHTML = `${icon("info")}成交后价格预计 ${q.price_after_cents}¢（滑点 ${slip}¢）`;
        } else { el.warn.textContent = ""; el.warn.className = "hintline"; }
      } catch (e) {
        el.warn.className = "hintline err";
        el.warn.innerHTML = `${icon("alert")}${esc(e.message)}`;
        $("#qQty").textContent = "—"; $("#qTotal").textContent = "—";
      }
    }, 250);
  }

  el.amt.addEventListener("input", refresh);
  el.px.addEventListener("input", refresh);

  const panel = $("#tradePanel");
  panel.addEventListener("click", async (ev) => {
    const b = ev.target.closest("[data-act]");
    if (!b) return;
    const act = b.dataset.act;
    if (act === "side") { st.side = b.dataset.v; sync(); refresh(); }
    if (act === "mode") { st.mode = b.dataset.v; sync(); refresh(); }
    if (act === "pxstep") {
      el.px.value = Math.min(99, Math.max(1, (parseInt(el.px.value, 10) || 50) + Number(b.dataset.v)));
      refresh();
    }
    if (act === "pick") {
      DS.oid = Number(b.dataset.oid);
      ev.stopPropagation();
      renderMarket(m.id);
      return;
    }
    if (act === "quick") {
      const v = b.dataset.v;
      if (st.side === "sell" || st.mode === "limit") {
        const avail = st.side === "sell"
          ? (myPos ? Math.max(0, myPos.shares - myPos.locked_shares) : 0)
          : Math.floor((S.user ? S.user.balance_cents : 0) / Math.max(1, cur().price_cents));
        const n = v === "100" ? Math.floor(10000 / Math.max(1, cur().price_cents)) : Math.floor(avail * parseFloat(v));
        el.amt.value = String(n || "");
      } else {
        const bal = S.user ? S.user.balance_cents : 0;
        el.amt.value = v === "100" ? "100.00" : (bal * parseFloat(v) / 100).toFixed(2);
      }
      refresh();
    }
    if (act === "submit") {
      if (!S.user) { location.hash = "#/auth"; render(); return; }
      const payload = body();
      if (!payload.qty && !payload.amount_cents) {
        el.warn.className = "hintline err";
        el.warn.innerHTML = `${icon("alert")}请先填写数量或金额`;
        return;
      }
      payload.order_type = st.mode;
      el.submit.disabled = true;
      try {
        const r = await api(`/api/markets/${m.id}/orders`, { method: "POST", body: payload });
        const rest = r.resting_qty || 0;
        toast(`成交 ${num(r.filled_qty)} 份 @ ${Number(r.avg_price_cents).toFixed(1)}¢` +
          (rest ? `，另有 ${num(rest)} 份挂单中` : ""), "ok");
        await loadMe(); paintHeader();
        renderMarket(m.id);
      } catch (e) {
        el.warn.className = "hintline err";
        el.warn.innerHTML = `${icon("alert")}${esc(e.message)}`;
        el.submit.disabled = false;
      }
    }
  });
  sync();
}

/* ---------------------------------------------------------------- 资金曲线 */
function moneyChart(points, w = 420, h = 132) {
  if (!points || points.length < 2) {
    return `<div class="empty" style="padding:22px">${icon("chart")}<b>暂无流水</b></div>`;
  }
  const pad = { l: 46, r: 10, t: 10, b: 18 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const vs = points.map((p) => p.v);
  let lo = Math.min(...vs), hi = Math.max(...vs);
  if (hi === lo) { hi += 100; lo -= 100; }
  const X = (i) => pad.l + (iw * i) / (points.length - 1);
  const Y = (v) => pad.t + ih * (1 - (v - lo) / (hi - lo));
  const d = smoothPath(points.map((p, i) => [X(i), Y(p.v)]));
  const up = vs[vs.length - 1] >= vs[0];
  const color = up ? "#22c55e" : "#f43f5e";
  const gid = "mg" + Math.random().toString(36).slice(2, 8);
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto;display:block">
    <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${color}" stop-opacity=".26"/>
      <stop offset="100%" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
    <line x1="${pad.l}" y1="${pad.t}" x2="${w - pad.r}" y2="${pad.t}" stroke="rgba(255,255,255,.05)"/>
    <line x1="${pad.l}" y1="${pad.t + ih}" x2="${w - pad.r}" y2="${pad.t + ih}" stroke="rgba(255,255,255,.05)"/>
    <text x="${pad.l - 6}" y="${pad.t + 4}" fill="#5b6478" font-size="9.5" text-anchor="end"
      font-family="ui-monospace,monospace">${moneyShort(hi)}</text>
    <text x="${pad.l - 6}" y="${pad.t + ih}" fill="#5b6478" font-size="9.5" text-anchor="end"
      font-family="ui-monospace,monospace">${moneyShort(lo)}</text>
    <path d="${d} L ${X(points.length - 1)} ${pad.t + ih} L ${pad.l} ${pad.t + ih} Z" fill="url(#${gid})"/>
    <path d="${d}" fill="none" stroke="${color}" stroke-width="1.9" stroke-linejoin="round"/>
    <circle cx="${X(points.length - 1)}" cy="${Y(vs[vs.length - 1])}" r="3.2" fill="${color}"/>
    <text x="${pad.l}" y="${h - 4}" fill="#5b6478" font-size="9.5">${when(points[0].ts).slice(0, 11)}</text>
    <text x="${w - pad.r}" y="${h - 4}" fill="#5b6478" font-size="9.5" text-anchor="end">
      ${when(points[points.length - 1].ts).slice(0, 11)}</text>
  </svg>`;
}

/* ---------------------------------------------------------------- 持仓页 */
const PS = { tab: "positions" };

async function renderPortfolio() {
  const app = $("#app");
  app.dataset.shell = "portfolio";
  if (!S.user) {
    app.innerHTML = `<div class="wrap"><div class="panel" style="max-width:480px;margin:8vh auto">
      <div class="pb" style="text-align:center;padding:38px 26px">
        ${icon("wallet", "icon")}
        <h2 style="font-size:18px;margin:10px 0 6px">登录后查看持仓</h2>
        <p style="color:var(--muted);font-size:13px;line-height:1.7">
          注册即送 <b style="color:var(--text)">$10,000</b> 虚拟体验金<br>可立即买入事件合约</p>
        <button class="btn primary block lg" data-act="login" style="margin-top:16px">登录 / 注册</button>
      </div></div></div>`;
    return;
  }
  app.innerHTML = `<div class="wrap">
    <div class="kpis">${Array.from({ length: 4 }, () => `<div class="sk sk-card" style="height:96px"></div>`).join("")}</div>
    <div class="sk sk-card" style="height:260px"></div></div>`;

  let d, ledger;
  try {
    [d, ledger] = await Promise.all([
      api("/api/portfolio"),
      api("/api/wallet/ledger?limit=200").catch(() => ({ items: [] })),
    ]);
  } catch (e) {
    app.innerHTML = `<div class="wrap"><div class="empty">${icon("alert")}<b>${esc(e.message)}</b></div></div>`;
    return;
  }
  const s = d.summary;
  const pts = (ledger.items || []).slice().reverse()
    .map((r) => ({ v: r.balance_after_cents, ts: r.created_at }));
  const totalValue = Math.max(1, s.positions_value_cents);

  app.innerHTML = `<div class="wrap">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <h1 style="font-size:20px;font-weight:800">我的持仓</h1>
      <div class="grow"></div>
      <button class="btn sm" data-act="deposit">${icon("plus")}充值体验金</button>
      <button class="btn sm ghost" data-act="ledger">${icon("coins")}资金流水</button>
    </div>

    <div class="kpis">
      <div class="box"><div class="k">${icon("wallet")}账户权益</div>
        <div class="v">${money(s.equity_cents)}</div>
        <div class="s">余额 + 持仓市值</div></div>
      <div class="box"><div class="k">${icon("coins")}可用余额</div>
        <div class="v">${money(s.balance_cents)}</div>
        <div class="s">虚拟体验金</div></div>
      <div class="box"><div class="k">${icon("layers")}持仓市值</div>
        <div class="v">${money(s.positions_value_cents)}</div>
        <div class="s">成本 ${money(s.cost_basis_cents)}</div></div>
      <div class="box"><div class="k">${icon("chart")}未实现盈亏</div>
        <div class="v ${cls(s.unrealized_cents)}">${signed(s.unrealized_cents)}</div>
        <div class="s">已实现 ${signed(s.realized_cents)}</div></div>
    </div>

    <div style="display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px;align-items:start">
      <section class="panel">
        <div class="tabs">
          ${[["positions", "持仓", d.positions.length], ["orders", "未成交委托", d.open_orders.length],
             ["trades", "成交记录", d.recent_trades.length]]
            .map(([k, t, n]) => `<button class="${PS.tab === k ? "on" : ""}" data-act="ptab" data-v="${k}">
              ${t}${n ? `<span class="count">${n}</span>` : ""}</button>`).join("")}
        </div>
        <div id="pbody">${portfolioBody(d, totalValue)}</div>
      </section>

      <aside class="stack">
        <div class="panel"><div class="ph">${icon("chart")}现金余额变化</div>
          <div class="pb" style="padding:12px 10px">${moneyChart(pts)}</div></div>
        <div class="panel"><div class="ph">${icon("layers")}持仓分布</div>
          <div class="pb"><div class="alloc">
            ${d.positions.slice().sort((a, b) => b.value_cents - a.value_cents).slice(0, 6).map((p, i) => `
              <div class="row">
                <span class="nm" title="${esc(p.question)}">${esc(p.category || "综合")} · ${esc(p.outcome_name.slice(0, 4))}</span>
                <div class="track"><div class="fill" style="width:${(p.value_cents / totalValue) * 100}%;
                  background:${["#5b8cff", "#a06bff", "#22c55e", "#f5a524", "#06b6d4", "#ec4899"][i % 6]}"></div></div>
                <span class="v">${money(p.value_cents)}</span>
              </div>`).join("") || `<div class="empty" style="padding:12px">暂无持仓</div>`}
          </div></div></div>
      </aside>
    </div>
  </div>`;
}

function portfolioBody(d, totalValue) {
  if (PS.tab === "orders") {
    if (!d.open_orders.length) {
      return `<div class="empty">${icon("clock")}<b>没有未成交的委托</b><span>限价单未成交的部分会挂在这里</span></div>`;
    }
    return `<table><thead><tr><th>事件</th><th>方向</th><th>价格</th><th>数量</th><th>已成交</th><th></th></tr></thead>
      <tbody>${d.open_orders.map((o) => `<tr>
        <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(o.question)}</td>
        <td><span class="chip" style="color:${o.side === "buy" ? "#4ade80" : "#fb7185"}">
          ${o.side === "buy" ? "买" : "卖"} ${esc(o.outcome_name)}</span></td>
        <td class="mono">${o.price_cents}¢</td>
        <td class="mono">${num(o.qty)}</td>
        <td class="mono dim">${num(o.filled_qty)}</td>
        <td style="text-align:right"><button class="btn sm" data-act="cancel" data-oid="${o.id}">撤单</button></td>
      </tr>`).join("")}</tbody></table>`;
  }
  if (PS.tab === "trades") {
    if (!d.recent_trades.length) return `<div class="empty">${icon("chart")}<b>还没有成交记录</b></div>`;
    return `<table><thead><tr><th>时间</th><th>方向</th><th>价格</th><th>数量</th><th>金额</th><th>手续费</th></tr></thead>
      <tbody>${d.recent_trades.slice(0, 30).map((t) => {
        const buy = t.buyer_id === S.user.id;
        return `<tr>
          <td class="dim mono">${when(t.created_at)}</td>
          <td><span class="chip" style="color:${buy ? "#4ade80" : "#fb7185"}">${buy ? "买入" : "卖出"}</span></td>
          <td class="mono">${t.price_cents}¢</td>
          <td class="mono">${num(t.qty)}</td>
          <td class="mono">${money(t.notional_cents)}</td>
          <td class="mono dim">${money(t.fee_cents)}</td></tr>`;
      }).join("")}</tbody></table>`;
  }
  if (!d.positions.length) {
    return `<div class="empty">${icon("layers")}<b>还没有持仓</b>
      <a class="btn primary sm" href="#/markets" style="margin-top:6px">去挑一个事件 →</a></div>`;
  }
  return `<table><thead><tr><th>事件</th><th>结果</th><th>份数</th><th>均价</th><th>现价</th><th>市值</th>
      <th>浮动盈亏</th><th>操作</th></tr></thead>
    <tbody>${d.positions.map((p) => `<tr class="posrow" data-act="go-mid" data-mid="${p.market_id}">
      <td style="max-width:300px"><div style="display:flex;align-items:center;gap:8px">
        ${tile(p.category || "", "")}${""}
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(p.question)}</span></div></td>
      <td><span class="chip">${esc(p.outcome_name)}</span></td>
      <td class="mono">${num(p.shares)}${p.locked_shares ? `<span class="mini"> +${num(p.locked_shares)}</span>` : ""}</td>
      <td class="mono dim">${Number(p.avg_cents).toFixed(1)}¢</td>
      <td class="mono">${p.price_cents}¢</td>
      <td class="mono">${money(p.value_cents)}</td>
      <td class="mono ${cls(p.pnl_cents)}">${signed(p.pnl_cents)}
        <div class="mini">${((p.pnl_cents / Math.max(1, p.value_cents - p.pnl_cents)) * 100).toFixed(1)}%</div></td>
      <td style="text-align:right">${p.market_status === "open"
        ? `<button class="btn sm" data-act="go" data-mid="${p.market_id}">交易</button>`
        : `<span class="chip done">${p.market_status === "resolved" ? "已结算" : "已停盘"}</span>`}</td>
    </tr>`).join("")}</tbody></table>`;
}

/* ---------------------------------------------------------------- 排行榜 */
async function renderLeaderboard() {
  const app = $("#app");
  app.dataset.shell = "leaderboard";
  app.innerHTML = `<div class="wrap"><div class="sk sk-card" style="height:150px"></div></div>`;
  try {
    const d = await api("/api/leaderboard?limit=30");
    const items = d.items || [];
    const top3 = items.slice(0, 3);
    const order = [top3[1], top3[0], top3[2]].filter(Boolean);
    app.innerHTML = `<div class="wrap">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
        <h1 style="font-size:20px;font-weight:800">排行榜</h1>
        <span class="chip">${icon("trophy")}按盈亏排序</span>
      </div>
      <p style="color:var(--muted);font-size:12.5px;margin:0 0 16px">
        盈亏 = 当前权益 − 初始体验金；权益 = 可用余额 + 持仓按现价估值。</p>

      <div class="podium">
        ${order.map((u) => {
          const rank = items.indexOf(u) + 1;
          return `<div class="pod ${rank === 1 ? "first" : ""}">
            ${rank === 1 ? `<span class="crown">${icon("trophy")}</span>` : ""}
            <span class="medal">#${rank}</span>
            ${avatar(u.handle, rank === 1 ? 52 : 44)}
            <div class="nm">${esc(u.handle)}</div>
            <div class="pnl ${cls(u.pnl_cents)}">${signed(u.pnl_cents)}</div>
            <div class="roi">收益率 ${(u.roi * 100).toFixed(2)}% · ${u.positions} 个持仓</div>
          </div>`;
        }).join("")}
      </div>

      <section class="panel">
        <table><thead><tr><th>#</th><th>交易员</th><th>账户权益</th><th>盈亏</th><th>收益率</th>
          <th>未实现</th><th>持仓</th><th>余额</th></tr></thead>
        <tbody>${items.map((u, i) => `<tr>
          <td style="color:${i < 3 ? "#f5c451" : "var(--faint)"};font-weight:850">${i + 1}</td>
          <td><div style="display:flex;align-items:center;gap:8px">${avatar(u.handle, 24)}
            <b>${esc(u.handle)}</b></div></td>
          <td class="mono">${money(u.equity_cents)}</td>
          <td class="mono ${cls(u.pnl_cents)}">${signed(u.pnl_cents)}</td>
          <td><div class="bar-cell"><div class="track"><div class="fill"
              style="width:${Math.min(100, Math.abs(u.roi) * 400)}%;
              background:${u.roi >= 0 ? "#22c55e" : "#f43f5e"}"></div></div>
            <span class="${cls(u.pnl_cents)}" style="width:56px;text-align:right">
              ${(u.roi * 100).toFixed(2)}%</span></div></td>
          <td class="mono ${cls(u.unrealized_cents)}">${signed(u.unrealized_cents)}</td>
          <td class="mono dim">${u.positions}</td>
          <td class="mono dim">${money(u.balance_cents)}</td>
        </tr>`).join("")}</tbody></table>
      </section>
    </div>`;
  } catch (e) {
    app.innerHTML = `<div class="wrap"><div class="empty">${icon("alert")}<b>${esc(e.message)}</b></div></div>`;
  }
}

/* ---------------------------------------------------------------- 管理端 */
const AS = { tab: "markets" };

async function renderAdmin() {
  const app = $("#app");
  app.dataset.shell = "admin";
  if (!S.user || !["admin", "creator"].includes(S.user.role)) {
    app.innerHTML = `<div class="wrap"><div class="empty">${icon("shield")}
      <b>需要管理员权限</b><span>演示账号 admin@predx.io / admin1234</span>
      <button class="btn primary sm" data-act="login" style="margin-top:8px">去登录</button></div></div>`;
    return;
  }
  app.innerHTML = `<div class="wrap"><div class="sk sk-card" style="height:220px"></div></div>`;
  const [st, list, users, audit] = await Promise.all([
    api("/api/admin/stats").catch(() => null),
    api("/api/markets?status=all&limit=100").catch(() => ({ items: [] })),
    api("/api/admin/users").catch(() => ({ items: [] })),
    api("/api/admin/audit?limit=40").catch(() => ({ items: [] })),
  ]);
  const items = list.items || [];
  const open = items.filter((m) => m.status === "open");
  const done = items.filter((m) => m.status !== "open");
  const daily = (st && st.daily) || [];
  const maxV = Math.max(1, ...daily.map((x) => x.v || 0));
  const byCat = (st && st.by_category) || [];
  const maxCat = Math.max(1, ...byCat.map((x) => x.v || 0));

  app.innerHTML = `<div class="wrap">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <h1 style="font-size:20px;font-weight:800">管理端</h1>
      <span class="chip">${icon("shield")}${esc(S.user.role === "admin" ? "管理员" : "市场创建者")}</span>
      <div class="grow"></div>
      <button class="btn primary" data-act="newMarket">${icon("plus")}上架新市场</button>
    </div>

    <div class="kpis">
      <div class="box"><div class="k">${icon("layers")}市场</div>
        <div class="v">${num(st ? st.open_markets : 0)}<span style="font-size:13px;color:var(--muted)"> / ${num(st ? st.markets : 0)}</span></div>
        <div class="s">进行中 / 总数</div></div>
      <div class="box"><div class="k">${icon("chart")}累计成交额</div>
        <div class="v">${money0(st ? st.volume_cents : 0)}</div>
        <div class="s">${num(st ? st.trades : 0)} 笔成交</div></div>
      <div class="box"><div class="k">${icon("users")}用户</div>
        <div class="v">${num(st ? st.users : 0)}</div>
        <div class="s">体验金余额 ${money0(st ? st.balance_cents : 0)}</div></div>
      <div class="box"><div class="k">${icon("coins")}手续费收入</div>
        <div class="v">${money(st ? st.fees_cents : 0)}</div>
        <div class="s">吃单 0.20%</div></div>
    </div>

    <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:14px;margin-bottom:14px">
      <section class="panel"><div class="ph">${icon("chart")}近 14 日成交额
          <div class="grow"></div><span class="hint">单位：美元</span></div>
        <div class="pb"><div class="bars">
          ${daily.map((x) => `<div class="b" title="${x.d} · ${money0(x.v)}">
            <div class="track"><i style="height:${Math.max(3, ((x.v || 0) / maxV) * 100)}%"></i></div>
            <span>${(x.d || "").slice(5)}</span></div>`).join("") ||
            `<div class="empty" style="padding:20px">暂无数据</div>`}
        </div></div></section>
      <section class="panel"><div class="ph">${icon("filter")}分类分布</div>
        <div class="pb"><div class="alloc">
          ${byCat.map((c, i) => `<div class="row">
            <span class="nm">${esc(c.category)}</span>
            <div class="track"><div class="fill" style="width:${((c.v || 0) / maxCat) * 100}%;
              background:${["#5b8cff", "#a06bff", "#22c55e", "#f5a524", "#06b6d4", "#ec4899", "#f97316", "#8b94a7"][i % 8]}"></div></div>
            <span class="v">${moneyShort(c.v || 0)}</span></div>`).join("")}
        </div></div></section>
    </div>

    <section class="panel">
      <div class="tabs">
        ${[["markets", "市场管理", items.length], ["users", "用户", users.items.length], ["audit", "审计日志", audit.items.length]]
          .map(([k, t, n]) => `<button class="${AS.tab === k ? "on" : ""}" data-act="atab" data-v="${k}">
            ${t}<span class="count">${n}</span></button>`).join("")}
      </div>
      <div id="abody">${adminBody({ open, done, users, audit })}</div>
    </section>
  </div>`;
}

function adminBody({ open, done, users, audit }) {
  if (AS.tab === "users") {
    return `<table><thead><tr><th>ID</th><th>邮箱</th><th>昵称</th><th>角色</th><th>余额</th>
        <th>体验金</th><th>状态</th><th></th></tr></thead><tbody>
      ${users.items.map((u) => `<tr>
        <td class="dim mono">${u.id}</td>
        <td style="font-size:12px">${esc(u.email)}</td>
        <td><div style="display:flex;align-items:center;gap:7px">${avatar(u.handle, 22)}${esc(u.handle)}</div></td>
        <td><span class="chip">${esc(u.role)}</span></td>
        <td class="mono">${money(u.balance_cents)}</td>
        <td class="mono dim">${money(u.equity_seed)}</td>
        <td><span class="chip" style="color:${u.status === "active" ? "#4ade80" : "#fb7185"}">
          ${u.status === "active" ? "正常" : "冻结"}</span></td>
        <td style="text-align:right"><button class="btn sm" data-act="freeze" data-uid="${u.id}"
          data-status="${u.status === "active" ? "frozen" : "active"}">
          ${u.status === "active" ? "冻结" : "解冻"}</button></td></tr>`).join("")}
    </tbody></table>`;
  }
  if (AS.tab === "audit") {
    if (!audit.items.length) return `<div class="empty">${icon("shield")}<b>暂无审计记录</b></div>`;
    return `<table><thead><tr><th>时间</th><th>用户</th><th>动作</th><th>对象</th><th>详情</th><th>IP</th></tr></thead>
      <tbody>${audit.items.map((a) => `<tr>
        <td class="dim mono">${when(a.created_at)}</td>
        <td class="dim">${a.user_id || "—"}</td>
        <td><span class="chip">${esc(a.action)}</span></td>
        <td class="dim">${esc(a.target || "—")}</td>
        <td class="dim" style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
          font-size:11.5px">${esc(a.meta || "")}</td>
        <td class="dim mono" style="font-size:11px">${esc(a.ip || "—")}</td></tr>`).join("")}
      </tbody></table>`;
  }
  const row = (m) => `<tr>
      <td class="dim mono">${m.id}</td>
      <td style="max-width:330px">
        <div style="display:flex;align-items:center;gap:8px">
          ${tile(m.category)}
          <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(m.question)}</span></div>
        <div class="mini" style="margin-left:42px">${esc(m.category)} · ${esc(m.outcomes.map((o) => `${o.name} ${o.price_cents}¢`).join(" / "))}</div>
      </td>
      <td class="mono">${money0(m.volume_cents)}</td>
      <td class="mono dim">${num(m.trades_count)}</td>
      <td><span class="chip" style="color:${m.status === "open" ? "#4ade80" : m.status === "resolved" ? "#9db9ff" : "#f5a524"}">
        ${m.status === "open" ? "进行中" : m.status === "resolved" ? "已结算" : "已停盘"}</span></td>
      <td style="white-space:nowrap;text-align:right">
        ${m.status === "open" ? `<button class="btn sm" data-act="closeMarket" data-mid="${m.id}">停盘</button>` : ""}
        ${m.status === "closed" ? `<button class="btn sm" data-act="reopen" data-mid="${m.id}">复牌</button>` : ""}
        ${m.status !== "resolved" ? `<button class="btn sm primary" data-act="resolve" data-mid="${m.id}">结算</button>` : ""}
        <a class="btn sm ghost" href="#/market/${m.id}">查看</a>
      </td></tr>`;
  return `<div class="subhead"><span>进行中（${open.length}）</span><div class="grow"></div>
      <span class="hint">停盘 / 结算会立即影响持仓兑付</span></div>
    <table><thead><tr><th>ID</th><th>事件</th><th>成交额</th><th>笔数</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>${open.map(row).join("")}</tbody></table>
    <div class="subhead" style="border-top:1px solid var(--line)">已结束（${done.length}）</div>
    <table><thead><tr><th>ID</th><th>事件</th><th>成交额</th><th>笔数</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>${done.map(row).join("")}</tbody></table>`;
}

/* ---------------------------------------------------------------- 登录页 */
const AU = { mode: "login" };

function renderAuth() {
  const app = $("#app");
  app.dataset.shell = "auth";
  app.innerHTML = `<div class="wrap">
    <div class="auth-wrap">
      <div class="auth-hero">
        <span class="tagline" style="display:inline-flex;align-items:center;gap:6px;font-size:11.5px;
          font-weight:800;letter-spacing:.6px;color:#9db9ff;background:var(--brand-soft);
          border:1px solid rgba(91,140,255,.3);border-radius:999px;padding:3px 9px">
          ${icon("sparkles")}PREDX · 事件合约</span>
        <h1 style="margin-top:14px">把你的判断<br>变成可交易的价格</h1>
        <p>买入你认为会发生的事件。若事件发生，每份合约兑付 <b style="color:var(--text)">$1.00</b>；
          否则归零。价格 1–99 分，就是市场给出的概率。</p>
        <ul>
          <li>${icon("check")}注册即送 $10,000 虚拟体验金</li>
          <li>${icon("check")}LMSR 做市商：新市场开盘即可交易，价差仅 1–2 分</li>
          <li>${icon("check")}市价 / 限价、买入 / 卖出，下单前实时报价</li>
          <li>${icon("check")}结算自动兑付，持仓与盈亏实时更新</li>
        </ul>
      </div>
      <div class="auth-card">
        <div class="tabs">
          <button class="${AU.mode === "login" ? "on" : ""}" data-act="authTab" data-v="login">登录</button>
          <button class="${AU.mode === "register" ? "on" : ""}" data-act="authTab" data-v="register">注册</button>
        </div>
        <div id="authForm"></div>
        <div class="note">${icon("info")}
          演示账号 <b>demo@predx.io / demo1234</b>（交易员）、<b>admin@predx.io / admin1234</b>（管理员）。
          本站为技术演示，不接入真实支付、不发行代币。</div>
      </div>
    </div>
  </div>`;
  authForm(AU.mode);
}

function authForm(mode) {
  AU.mode = mode;
  $$("[data-act=authTab]").forEach((b) => b.classList.toggle("on", b.dataset.v === mode));
  const box = $("#authForm");
  box.innerHTML = `
    <div class="field" style="margin-top:0">
      <label>邮箱</label>
      <div class="inputbox" style="height:42px"><input id="auEmail" type="email"
        placeholder="you@example.com" style="font-size:14px;font-weight:600"></div>
    </div>
    <div class="field">
      <label>密码<span>${mode === "register" ? "至少 8 位" : ""}</span></label>
      <div class="inputbox" style="height:42px"><input id="auPwd" type="password"
        placeholder="••••••••" style="font-size:14px;font-weight:600"></div>
    </div>
    ${mode === "register" ? `<div class="field"><label>昵称<span>可选</span></label>
      <div class="inputbox" style="height:42px"><input id="auHandle" placeholder="交易员小明"
        style="font-size:14px;font-weight:600"></div></div>` : ""}
    <button class="btn primary block lg" style="margin-top:16px" data-act="doAuth" data-v="${mode}">
      ${mode === "register" ? "注册并领取 $10,000" : "登录"}</button>
    <div class="hintline err" id="auWarn"></div>`;
  const onEnter = (e) => { if (e.key === "Enter") $("[data-act=doAuth]").click(); };
  $("#auEmail").addEventListener("keydown", onEnter);
  $("#auPwd").addEventListener("keydown", onEnter);
  setTimeout(() => $("#auEmail") && $("#auEmail").focus(), 60);
}

async function doAuth(mode) {
  const email = ($("#auEmail").value || "").trim();
  const password = $("#auPwd").value || "";
  const handle = $("#auHandle") ? $("#auHandle").value.trim() : "";
  const warn = $("#auWarn");
  try {
    const body = mode === "register" ? { email, password, handle } : { email, password };
    const d = await api("/api/auth/" + mode, { method: "POST", body });
    S.token = d.token; S.user = d.user;
    localStorage.setItem("px_token", d.token);
    await loadMe();
    paintHeader();
    toast(mode === "register" ? "注册成功，已发放 $10,000 体验金" : `欢迎回来，${d.user.handle}`, "ok");
    location.hash = "#/markets";
    render();
  } catch (e) {
    if (warn) warn.innerHTML = `${icon("alert")}${esc(e.message)}`;
  }
}

/* ---------------------------------------------------------------- 弹层 */
function modal(html) {
  $("#modalRoot").innerHTML = `<div class="mask">${html}</div>`;
  const mask = $("#modalRoot .mask");
  if (mask) mask.addEventListener("click", (e) => { if (e.target === mask) closeModal(); });
}
const closeModal = () => { $("#modalRoot").innerHTML = ""; };

function newMarketModal() {
  modal(`<div class="modal">
    <div class="mh">${icon("plus")}<b>上架新市场</b><div class="grow"></div>
      <button class="iconbtn" data-act="closeModal">${icon("close")}</button></div>
    <div class="mb">
      <label>问题（一句话说清，至少 6 个字）</label>
      <input id="nmQ" placeholder="例：2026 年底前，美联储会降息至 3% 以下吗？">
      <label>结果（逗号分隔，2–8 个；二元市场填「会,不会」）</label>
      <input id="nmO" value="会,不会">
      <div class="two">
        <div><label>分类</label><select id="nmCat">${CATS.map((c) => `<option>${c}</option>`).join("")}</select></div>
        <div><label>初始流动性 b</label><input id="nmB" value="1200"></div>
      </div>
      <label>初始概率（逗号分隔，0–1；留空为等分）</label>
      <input id="nmP" placeholder="0.65,0.35">
      <label>截止时间（YYYY-MM-DD HH:MM，可留空）</label>
      <input id="nmCloses" placeholder="2026-12-31 23:59">
      <label>说明</label>
      <textarea id="nmDesc" rows="3" placeholder="背景、为什么值得交易…"></textarea>
      <label>结算规则</label>
      <textarea id="nmRules" rows="2" placeholder="以哪个官方数据源为准…"></textarea>
      <label>结果来源 URL</label>
      <input id="nmSrc" placeholder="https://">
      <div class="hintline err" id="nmWarn"></div>
    </div>
    <div class="mf"><button class="btn ghost" data-act="closeModal">取消</button>
      <button class="btn primary" data-act="createMarket">创建并上架</button></div>
  </div>`);
}

async function resolveModal(mid) {
  let data;
  try { data = (DS.data && Number(DS.data.id) === Number(mid)) ? DS.data : await api(`/api/markets/${mid}`); }
  catch (e) { toast(e.message, "err"); return; }
  modal(`<div class="modal">
    <div class="mh">${icon("check")}<b>结算市场 #${mid}</b><div class="grow"></div>
      <button class="iconbtn" data-act="closeModal">${icon("close")}</button></div>
    <div class="mb">
      <p style="margin:0 0 12px;font-weight:750;font-size:14px">${esc(data.question)}</p>
      <label>选择胜出结果（每份兑付 $1.00，其余归零）</label>
      <div class="opts">
        ${data.outcomes.map((o) => `<button class="opt" data-act="pickWinner" data-mid="${mid}" data-oid="${o.id}">
          <span>${esc(o.name)}</span><span class="p">${o.price_cents}¢</span></button>`).join("")}
      </div>
      <label>结算备注（写入审计日志）</label>
      <input id="rsNote" placeholder="依据官方公告 …">
      <div class="note">${icon("alert")}结算不可撤销：会撤销全部挂单、向赢家持仓兑付、其余归零。</div>
    </div>
    <div class="mf"><button class="btn ghost" data-act="closeModal">取消</button></div>
  </div>`);
}

async function createMarket() {
  const q = $("#nmQ").value.trim();
  const outs = $("#nmO").value.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
  const pRaw = $("#nmP").value.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
  const body = {
    question: q, outcomes: outs, category: $("#nmCat").value,
    emoji: "🎯", description: $("#nmDesc").value, rules: $("#nmRules").value,
    source_url: $("#nmSrc").value || null, closes_at: $("#nmCloses").value || null,
    liquidity_b: parseFloat($("#nmB").value) || null,
  };
  if (pRaw.length) body.probs = pRaw.map(Number);
  try {
    const r = await api("/api/admin/markets", { method: "POST", body });
    closeModal();
    toast("市场已上架 #" + r.id, "ok");
    location.hash = `#/market/${r.id}`;
  } catch (e) {
    const w = $("#nmWarn");
    if (w) w.innerHTML = `${icon("alert")}${esc(e.message)}`;
  }
}

/* ---------------------------------------------------------------- 路由 */
async function render() {
  const hash = location.hash || "#/markets";
  paintHeader();
  closeMenu();
  let mo;
  if ((mo = hash.match(/^#\/market\/(\d+)/))) return renderMarket(Number(mo[1]));
  if (hash.startsWith("#/portfolio")) return renderPortfolio();
  if (hash.startsWith("#/leaderboard")) return renderLeaderboard();
  if (hash.startsWith("#/admin")) return renderAdmin();
  if (hash.startsWith("#/auth")) return renderAuth();
  return renderMarkets();
}

/* ---------------------------------------------------------------- 全局事件 */
document.addEventListener("click", async (ev) => {
  const el = ev.target.closest("[data-act]");
  if (!el) return;
  const act = el.dataset.act;

  switch (act) {
    case "closeModal": closeModal(); return;
    case "menu": accountMenu(); return;
    case "login": closeMenu(); location.hash = "#/auth"; render(); return;
    case "logout": closeMenu(); logout(); return;
    case "portfolio": closeMenu(); location.hash = "#/portfolio"; render(); return;
    case "admin": closeMenu(); location.hash = "#/admin"; render(); return;
    case "cat": S.q.cat = el.dataset.v; if (location.hash.startsWith("#/market/")) {
        location.hash = "#/markets"; } render(); return;
    case "go": {
      const mid = el.dataset.mid;
      if (el.dataset.oid) DS.oid = Number(el.dataset.oid);
      if (location.hash === `#/market/${mid}`) renderMarket(Number(mid));
      else location.hash = `#/market/${mid}`;
      return;
    }
    case "go-mid": location.hash = `#/market/${el.dataset.mid}`; return;
    case "watch": {
      if (!S.user) { location.hash = "#/auth"; render(); return; }
      try {
        const r = await api(`/api/markets/${el.dataset.mid}/watch`, { method: "POST", body: {} });
        if (r.watching) S.watch.add(Number(el.dataset.mid));
        else S.watch.delete(Number(el.dataset.mid));
        toast(r.watching ? "已加入关注" : "已取消关注", "ok");
        const onDetail = location.hash.startsWith("#/market/");
        if (onDetail && DS.data) renderMarket(DS.data.id); else renderMarkets();
      } catch (e) { toast(e.message, "err"); }
      return;
    }
    case "tab": DS.tab = el.dataset.v; await renderMarket(DS.data.id); return;
    case "range": DS.range = el.dataset.v; await renderMarket(DS.data.id); return;
    case "pick": DS.oid = Number(el.dataset.oid); await renderMarket(DS.data.id); return;
    case "ptab": PS.tab = el.dataset.v; {
      const d = await api("/api/portfolio");
      const total = Math.max(1, d.summary.positions_value_cents);
      $$("[data-act=ptab]").forEach((b) => b.classList.toggle("on", b.dataset.v === PS.tab));
      const body = $("#pbody");
      if (body) body.innerHTML = portfolioBody(d, total);
      return;
    }
    case "atab": AS.tab = el.dataset.v; {
      const [list, users, audit] = await Promise.all([
        api("/api/markets?status=all&limit=100").catch(() => ({ items: [] })),
        api("/api/admin/users").catch(() => ({ items: [] })),
        api("/api/admin/audit?limit=40").catch(() => ({ items: [] })),
      ]);
      const items = list.items || [];
      $$("[data-act=atab]").forEach((b) => b.classList.toggle("on", b.dataset.v === AS.tab));
      const body = $("#abody");
      if (body) body.innerHTML = adminBody({
        open: items.filter((m) => m.status === "open"),
        done: items.filter((m) => m.status !== "open"), users, audit,
      });
      return;
    }
    case "comment": {
      const box = $("#cmtInput");
      const text = (box && box.value || "").trim();
      if (text.length < 2) { toast("评论至少 2 个字", "err"); return; }
      try {
        await api(`/api/markets/${DS.data.id}/comments`, { method: "POST", body: { body: text } });
        toast("评论已发布", "ok");
        DS.tab = "comments";
        await renderMarket(DS.data.id);
      } catch (e) { toast(e.message, "err"); }
      return;
    }
    case "cancel": {
      try {
        await api(`/api/orders/${el.dataset.oid}`, { method: "DELETE" });
        toast("已撤单，资金/份额已解冻", "ok");
        await loadMe(); paintHeader(); render();
      } catch (e) { toast(e.message, "err"); }
      return;
    }
    case "deposit": {
      closeMenu();
      modal(`<div class="modal">
        <div class="mh">${icon("coins")}<b>充值体验金</b><div class="grow"></div>
          <button class="iconbtn" data-act="closeModal">${icon("close")}</button></div>
        <div class="mb">
          <div class="note" style="margin-top:0">${icon("info")}
            演示环境：这是虚拟资金，用于体验交易流程，不具备任何货币价值，也无法提现。</div>
          <label>金额（美元）</label>
          <input id="dpAmt" value="1000">
          <div class="quick" style="grid-template-columns:repeat(4,1fr);margin-top:8px">
            ${[100, 500, 1000, 5000].map((v) => `<button data-act="dpval" data-v="${v}">$${v}</button>`).join("")}
          </div>
          <div class="hintline err" id="dpWarn"></div>
        </div>
        <div class="mf"><button class="btn ghost" data-act="closeModal">取消</button>
          <button class="btn primary" data-act="doDeposit">确认充值</button></div>
      </div>`);
      return;
    }
    case "dpval": { const i = $("#dpAmt"); if (i) i.value = el.dataset.v; return; }
    case "doDeposit": {
      const amt = Math.round(parseFloat($("#dpAmt").value || "0") * 100);
      try {
        await api("/api/wallet/deposit", { method: "POST", body: { amount_cents: amt } });
        closeModal(); toast("充值成功（虚拟资金）", "ok");
        await loadMe(); paintHeader(); render();
      } catch (e) {
        const w = $("#dpWarn"); if (w) w.innerHTML = `${icon("alert")}${esc(e.message)}`;
      }
      return;
    }
    case "ledger": {
      closeMenu();
      const d = await api("/api/wallet/ledger?limit=40");
      const kind = { signup: "体验金", deposit: "充值", trade_buy: "买入", trade_sell: "卖出",
        settlement: "结算兑付", fee: "手续费", refund: "退款" };
      modal(`<div class="modal" style="width:min(680px,100%)">
        <div class="mh">${icon("coins")}<b>资金流水</b><div class="grow"></div>
          <span class="hint" style="color:var(--muted);font-size:12px">余额 ${money(d.balance_cents)}</span>
          <button class="iconbtn" data-act="closeModal" style="margin-left:8px">${icon("close")}</button></div>
        <div style="max-height:60vh;overflow:auto">
          <table><thead><tr><th>时间</th><th>类型</th><th>变动</th><th>余额</th><th>备注</th></tr></thead>
            <tbody>${d.items.map((r) => `<tr>
              <td class="dim mono">${when(r.created_at)}</td>
              <td><span class="chip">${kind[r.kind] || esc(r.kind)}</span></td>
              <td class="mono ${cls(r.delta_cents)}">${signed(r.delta_cents)}</td>
              <td class="mono">${money(r.balance_after_cents)}</td>
              <td class="dim" style="font-size:11.5px">${esc(r.note || "")}</td></tr>`).join("")}
          </tbody></table>
        </div>
        <div class="mf"><button class="btn ghost" data-act="closeModal">关闭</button></div>
      </div>`);
      return;
    }
    case "authTab": authForm(el.dataset.v); return;
    case "doAuth": await doAuth(el.dataset.v || AU.mode); return;
    case "newMarket": newMarketModal(); return;
    case "createMarket": await createMarket(); return;
    case "resolve": await resolveModal(Number(el.dataset.mid)); return;
    case "pickWinner": {
      const mid = el.dataset.mid, oid = el.dataset.oid;
      const note = ($("#rsNote") || {}).value || "";
      if (!confirm("确认结算？此操作不可撤销，会立即向赢家兑付。")) return;
      try {
        const r = await api(`/api/admin/markets/${mid}/resolve`, { method: "POST", body: { outcome_id: Number(oid), note } });
        closeModal();
        toast(`已结算，兑付 ${money(r.paid_cents || 0)}`, "ok");
        await loadMe(); paintHeader(); render();
      } catch (e) { toast(e.message, "err"); }
      return;
    }
    case "closeMarket": {
      try {
        await api(`/api/admin/markets/${el.dataset.mid}/close`, { method: "POST", body: {} });
        toast("已停盘", "ok"); render();
      } catch (e) { toast(e.message, "err"); }
      return;
    }
    case "reopen": {
      try {
        await api(`/api/admin/markets/${el.dataset.mid}/reopen`, { method: "POST", body: {} });
        toast("已复牌", "ok"); render();
      } catch (e) { toast(e.message, "err"); }
      return;
    }
    case "freeze": {
      try {
        await api(`/api/admin/users/${el.dataset.uid}/status`, { method: "POST",
          body: { status: el.dataset.status } });
        toast("用户状态已更新", "ok"); render();
      } catch (e) { toast(e.message, "err"); }
      return;
    }
  }
});

document.addEventListener("change", (ev) => {
  const el = ev.target.closest("[data-act=sortsel]");
  if (el) { S.q.sort = el.value; renderMarkets(); }
});

/* 搜索：防抖 + 快捷键 */
let searchTimer = null;
function bindSearch() {
  const box = $("#searchBox");
  if (!box) return;
  box.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      S.q.text = box.value.trim();
      if (!location.hash.startsWith("#/markets")) location.hash = "#/markets";
      render();
      const b2 = $("#searchBox");
      if (b2) { b2.value = S.q.text; b2.focus(); }
    }, 320);
  });
  document.addEventListener("keydown", (ev) => {
    if ((ev.key === "k" && (ev.metaKey || ev.ctrlKey)) || (ev.key === "/" && ev.target.tagName !== "INPUT")) {
      ev.preventDefault();
      $("#searchBox").focus();
    }
    if (ev.key === "Escape") { closeModal(); closeMenu(); }
  });
}

window.addEventListener("hashchange", () => { DS.tab = "overview"; render(); });

/* 启动 */
(async function boot() {
  await loadMe();
  paintHeader();
  bindSearch();
  render();
})();
