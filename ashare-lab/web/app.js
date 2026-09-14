const $ = (sel) => document.querySelector(sel);
const pages = {
  market: $("#page-market"),
  stock: $("#page-stock"),
  screener: $("#page-screener"),
  watch: $("#page-watch"),
};

const WATCH_KEY = "ashare-lab-watch";

function signed(n, digits = 2) {
  if (n == null || Number.isNaN(n)) return "—";
  const v = Number(n);
  const t = v.toFixed(digits);
  return v > 0 ? "+" + t : t;
}

function fmt(n, digits = 2) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toFixed(digits);
}

function yi(n) {
  if (n == null) return "—";
  const v = Number(n);
  if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(2) + " 万亿";
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + " 亿";
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + " 万";
  return String(v);
}

function clsPct(n) {
  if (n == null) return "";
  return Number(n) >= 0 ? "up" : "down";
}

async function api(path) {
  const res = await fetch(path);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "请求失败");
  return data;
}

function showPage(name) {
  Object.entries(pages).forEach(([k, el]) => {
    el.hidden = k !== name;
  });
  document.querySelectorAll(".nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.page === name);
  });
}

function loadWatch() {
  try {
    return JSON.parse(localStorage.getItem(WATCH_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveWatch(items) {
  localStorage.setItem(WATCH_KEY, JSON.stringify(items));
}

function toggleWatch(item) {
  const items = loadWatch();
  const i = items.findIndex((x) => x.code === item.code);
  if (i >= 0) items.splice(i, 1);
  else items.unshift({ code: item.code, name: item.name });
  saveWatch(items.slice(0, 30));
  return items;
}

function isWatched(code) {
  return loadWatch().some((x) => x.code === code);
}

function drawFlow(canvas, days) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  const rows = (days || []).slice(0, 12).reverse();
  if (!rows.length) return;
  const vals = rows.map((d) => Number(d.main_net) || 0);
  const max = Math.max(...vals.map((v) => Math.abs(v)), 1);
  const mid = h / 2;
  const slot = w / rows.length;
  rows.forEach((d, i) => {
    const v = Number(d.main_net) || 0;
    const bh = (Math.abs(v) / max) * (mid - 10);
    const x = i * slot + slot * 0.2;
    ctx.fillStyle = v >= 0 ? "#f04343" : "#27c281";
    if (v >= 0) ctx.fillRect(x, mid - bh, slot * 0.6, bh);
    else ctx.fillRect(x, mid, slot * 0.6, bh);
  });
  ctx.strokeStyle = "#1d3646";
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(w, mid);
  ctx.stroke();
}

function flowTable(list) {
  return (list || [])
    .map(
      (r) => `<tr data-code="${r.code || ""}">
        <td>${r.name} ${r.code ? `<span class="muted">${r.code}</span>` : ""}</td>
        <td class="${clsPct(r.pct)}">${signed(r.pct)}%</td>
        <td class="${clsPct(r.main_net_inflow)}">${yi(r.main_net_inflow)}</td>
        <td class="${clsPct(r.main_net_pct)}">${r.main_net_pct == null ? "—" : signed(r.main_net_pct, 2) + "%"}</td>
      </tr>`
    )
    .join("");
}

function drawKline(canvas, bars) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  if (!bars || bars.length < 2) return;
  const pad = 12;
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);
  const max = Math.max(...highs);
  const min = Math.min(...lows);
  const span = max - min || 1;
  const slot = (w - pad * 2) / bars.length;
  bars.forEach((b, i) => {
    const x = pad + i * slot + slot / 2;
    const yHigh = pad + ((max - b.high) / span) * (h - pad * 2);
    const yLow = pad + ((max - b.low) / span) * (h - pad * 2);
    const yOpen = pad + ((max - b.open) / span) * (h - pad * 2);
    const yClose = pad + ((max - b.close) / span) * (h - pad * 2);
    const up = b.close >= b.open;
    ctx.strokeStyle = up ? "#f04343" : "#27c281";
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.moveTo(x, yHigh);
    ctx.lineTo(x, yLow);
    ctx.stroke();
    const top = Math.min(yOpen, yClose);
    const bh = Math.max(Math.abs(yClose - yOpen), 1.2);
    ctx.fillRect(x - Math.max(slot * 0.3, 1.5), top, Math.max(slot * 0.6, 2), bh);
  });
}

function scoreCard(score) {
  const parts = (score.parts || [])
    .map((p) => {
      const pct = (p.score / p.max_score) * 100;
      const reasons = (p.reasons || []).map((r) => `<div class="reason">· ${r}</div>`).join("");
      return `<div>
        <div style="display:flex;justify-content:space-between"><strong>${p.name}</strong><span>${p.score}/${p.max_score}</span></div>
        <div class="bar"><span style="width:${pct}%"></span></div>
        ${reasons}
      </div>`;
    })
    .join("");
  const risks = (score.risks || []).map((r) => `<div class="risk">⚠ ${r}</div>`).join("");
  return `<div class="card">
    <div class="score-head">
      <div>
        <div class="muted">研究评分</div>
        <div class="score-num">${score.total}</div>
      </div>
      <div>
        <span class="verdict">${score.verdict}</span>
        <p class="muted">${score.verdict_note}</p>
      </div>
    </div>
    <div class="bars">${parts}</div>
    ${risks}
  </div>`;
}

async function renderMarket() {
  pages.market.innerHTML = `<div class="card muted">正在拉取延迟行情…</div>`;
  try {
    const data = await api("/api/market");
    const idxs = (data.indices || [])
      .map(
        (x) => `<div class="card idx">
        <div class="name">${x.name}</div>
        <div class="price ${clsPct(x.pct)}">${fmt(x.price)}</div>
        <div class="${clsPct(x.pct)}">${signed(x.pct)}%</div>
      </div>`
      )
      .join("");
    const b = data.breadth || {};
    const sectors = (data.sectors || [])
      .map(
        (s) => `<tr data-code="">
        <td>${s.name}</td>
        <td class="${clsPct(s.pct)}">${signed(s.pct)}%</td>
        <td class="${clsPct(s.main_net_inflow)}">${yi(s.main_net_inflow)}</td>
      </tr>`
      )
      .join("");
    const hot = (data.hot || [])
      .map(
        (r) => `<tr data-code="${r.code}">
        <td>${r.name} <span class="muted">${r.code}</span></td>
        <td>${fmt(r.price)}</td>
        <td class="${clsPct(r.pct)}">${signed(r.pct)}%</td>
        <td class="${clsPct(r.main_net_inflow)}">${yi(r.main_net_inflow)}</td>
        <td>${fmt(r.pe_ttm || r.pe, 1)}</td>
        <td>${fmt(r.roe, 1)}%</td>
        <td>${r.score ? r.score.total : "—"}</td>
      </tr>`
      )
      .join("");
    const sectorFlow = flowTable(data.sectors_flow || []).replace(/data-code="[^"]*"/g, 'data-code=""');
    pages.market.innerHTML = `
      <div class="grid indices">${idxs}</div>
      <div class="grid two" style="margin-top:14px">
        <div class="card">
          <h3>市场宽度（A股）</h3>
          <div class="metrics">
            <div><div class="muted">上涨</div><div class="up">${b.up ?? "—"}</div></div>
            <div><div class="muted">下跌</div><div class="down">${b.down ?? "—"}</div></div>
            <div><div class="muted">涨停</div><div class="up">${b.limit_up ?? "—"}</div></div>
            <div><div class="muted">跌停</div><div class="down">${b.limit_down ?? "—"}</div></div>
          </div>
        <p class="muted">平均涨跌 ${signed(b.avg_pct)}% · ${data.as_of}${data.partial_errors && data.partial_errors.length ? " · 部分数据源暂不可用" : ""}</p>
        </div>
        <div class="card">
          <h3>行业涨幅榜</h3>
          <table class="table"><thead><tr><th>行业</th><th>涨跌</th><th>主力净流入</th></tr></thead><tbody>${sectors}</tbody></table>
        </div>
      </div>
      <div class="grid two" style="margin-top:14px">
        <div class="card">
          <h3>个股主力净流入榜</h3>
          <table class="table"><thead><tr><th>名称</th><th>涨跌</th><th>主力净流入</th><th>占成交</th></tr></thead>
          <tbody>${flowTable(data.money_in)}</tbody></table>
        </div>
        <div class="card">
          <h3>个股主力净流出榜</h3>
          <table class="table"><thead><tr><th>名称</th><th>涨跌</th><th>主力净流入</th><th>占成交</th></tr></thead>
          <tbody>${flowTable(data.money_out)}</tbody></table>
        </div>
      </div>
      <div class="card" style="margin-top:14px">
        <h3>行业主力净流入</h3>
        <table class="table"><thead><tr><th>行业</th><th>涨跌</th><th>主力净流入</th><th>占成交</th></tr></thead>
        <tbody>${sectorFlow}</tbody></table>
      </div>
      <div class="card" style="margin-top:14px">
        <h3>成交额靠前个股（附轻量评分）</h3>
        <table class="table">
          <thead><tr><th>名称</th><th>价格</th><th>涨跌</th><th>主力净流入</th><th>PE</th><th>ROE</th><th>评分</th></tr></thead>
          <tbody>${hot}</tbody>
        </table>
        <p class="muted">${data.disclaimer}</p>
      </div>`;
    pages.market.querySelectorAll("tr[data-code]").forEach((tr) => {
      tr.addEventListener("click", () => {
        if (tr.dataset.code) openStock(tr.dataset.code);
      });
    });
  } catch (e) {
    pages.market.innerHTML = `<div class="card error">${e.message}</div>`;
  }
}

async function openStock(code) {
  showPage("stock");
  pages.stock.innerHTML = `<div class="card muted">正在研究 ${code}… 日 K、财报与评分大约需要几秒。</div>`;
  history.replaceState(null, "", `#/stock/${code}`);
  try {
    const data = await api("/api/stock/" + code);
    const q = data.quote || {};
    const f = (data.finance || {}).latest || {};
    const t = data.trend || {};
    const watched = isWatched(q.code);
    const ff = data.fund_flow || {};
    const consec = ff.consecutive || 0;
    const consecText = !consec ? "无连续方向" : consec > 0 ? `连续净流入 ${consec} 日` : `连续净流出 ${Math.abs(consec)} 日`;
    const flowDays = (ff.days || [])
      .slice(0, 10)
      .map(
        (d) => `<tr>
          <td>${d.date || ""}</td>
          <td class="${clsPct(d.main_net)}">${yi(d.main_net)}</td>
          <td class="${clsPct(d.extra_large_net)}">${yi(d.extra_large_net)}</td>
          <td class="${clsPct(d.large_net)}">${yi(d.large_net)}</td>
          <td class="${clsPct(d.medium_net)}">${yi(d.medium_net)}</td>
          <td class="${clsPct(d.small_net)}">${yi(d.small_net)}</td>
        </tr>`
      )
      .join("");
    const metrics = [
      ["PE(TTM)", fmt(q.pe_ttm, 1)],
      ["市净率", fmt(q.pb, 2)],
      ["总市值", yi(q.mkt_cap)],
      ["换手率", fmt(q.turnover, 2) + "%"],
      ["ROE", fmt(f.roe, 1) + "%"],
      ["营收同比", signed(f.revenue_yoy) + "%"],
      ["净利同比", signed(f.profit_yoy) + "%"],
      ["毛利率", fmt(f.gross_margin, 1) + "%"],
      ["负债率", fmt(f.debt_ratio, 1) + "%"],
      ["主力净流入", yi(ff.today_main)],
      ["近5日主力", yi(ff.sum_5)],
      ["MA20", fmt(t.ma20, 2)],
    ]
      .map(([k, v]) => `<div class="card"><div class="muted">${k}</div><div>${v}</div></div>`)
      .join("");
    const quarters = ((data.finance || {}).quarters || [])
      .map(
        (r) => `<tr>
        <td>${r.report_date || ""}</td>
        <td>${fmt(r.revenue / 1e8, 1)}</td>
        <td class="${clsPct(r.revenue_yoy)}">${signed(r.revenue_yoy)}</td>
        <td>${fmt(r.profit / 1e8, 1)}</td>
        <td class="${clsPct(r.profit_yoy)}">${signed(r.profit_yoy)}</td>
        <td>${fmt(r.roe, 1)}</td>
      </tr>`
      )
      .join("");
    pages.stock.innerHTML = `
      <div class="card">
        <div class="score-head">
          <div>
            <h2 class="quote-name">${q.name || ""} <span class="${clsPct(q.pct)}">${fmt(q.price)} ${signed(q.pct)}%</span></h2>
            <p class="sub">${q.ts_code} · ${q.industry || "行业未知"} · 日K来源 ${data.kline_source || "—"}</p>
          </div>
          <button class="ghost" id="watch-btn">${watched ? "移出自选" : "加入自选"}</button>
        </div>
        <canvas class="kline" id="kline"></canvas>
        <p class="muted">均线 ${t.alignment || "—"} · 近20日 ${signed(t.ret20)}% · 量比 ${fmt(t.vol_ratio, 2)}</p>
      </div>
      <div class="grid two" style="margin-top:14px">
        ${scoreCard(data.score)}
        <div class="card">
          <h3>主力资金净流入</h3>
          <div class="metrics">
            <div><div class="muted">当日主力</div><div class="${clsPct(ff.today_main)}">${yi(ff.today_main)}</div></div>
            <div><div class="muted">近5日</div><div class="${clsPct(ff.sum_5)}">${yi(ff.sum_5)}</div></div>
            <div><div class="muted">近10日</div><div class="${clsPct(ff.sum_10)}">${yi(ff.sum_10)}</div></div>
            <div><div class="muted">近5日流入天数</div><div>${ff.inflow_days_5 ?? "—"} / 5</div></div>
          </div>
          <p class="reason">超大单 ${yi(ff.today_extra_large)} · 大单 ${yi(ff.today_large)} · 中单 ${yi(ff.today_medium)} · 小单 ${yi(ff.today_small)}</p>
          <p class="reason">${consecText} · 主力=超大单+大单 · 当日东财延迟快照，历史新浪日频</p>
          <canvas class="flow-chart" id="flow-chart"></canvas>
          <table class="table">
            <thead><tr><th>日期</th><th>主力</th><th>超大单</th><th>大单</th><th>中单</th><th>小单</th></tr></thead>
            <tbody>${flowDays || `<tr><td colspan="6" class="muted">暂无历史资金数据</td></tr>`}</tbody>
          </table>
        </div>
      </div>
      <div class="card" style="margin-top:14px">
          <h3>财务快照 ${f.report_date || ""}</h3>
          <p class="reason">营收 ${yi(f.revenue)} · 净利润 ${yi(f.profit)} · EPS ${fmt(f.eps, 2)}</p>
          <p class="reason">近3年 PE 分位：30% = ${fmt(data.valuation && data.valuation.p30, 1)}，中位 ${fmt(data.valuation && data.valuation.p50, 1)}，70% = ${fmt(data.valuation && data.valuation.p70, 1)}</p>
          <table class="table">
            <thead><tr><th>报告期</th><th>营收(亿)</th><th>同比%</th><th>净利(亿)</th><th>同比%</th><th>ROE</th></tr></thead>
            <tbody>${quarters}</tbody>
          </table>
        </div>
      <div class="metrics" style="margin-top:14px">${metrics}</div>
      <p class="muted">${data.disclaimer}</p>`;
    const canvas = $("#kline");
    drawKline(canvas, data.kline || []);
    const flowCanvas = $("#flow-chart");
    if (flowCanvas) drawFlow(flowCanvas, ff.days || []);
    $("#watch-btn").addEventListener("click", () => {
      toggleWatch({ code: q.code, name: q.name });
      openStock(q.code);
    });
  } catch (e) {
    pages.stock.innerHTML = `<div class="card error">${e.message}</div>`;
  }
}

async function renderScreener() {
  showPage("screener");
  pages.screener.innerHTML = `
    <div class="card">
      <h3>条件选股</h3>
      <p class="muted">从当日成交额靠前的 A 股里筛，不穷尽全市场。适合找“值得继续看”的候选。</p>
      <div class="filters">
        <input id="pe_max" type="number" placeholder="PE上限 如 30" />
        <input id="pb_max" type="number" placeholder="PB上限 如 5" />
        <input id="roe_min" type="number" placeholder="ROE下限 如 10" />
        <input id="cap_min" type="number" placeholder="市值下限(亿) 如 50" />
        <input id="industry" placeholder="行业包含 如 半导体" />
        <select id="sort">
          <option value="amount">按成交额</option>
          <option value="flow">按主力净流入</option>
          <option value="pct">按涨跌幅</option>
          <option value="mktcap">按市值</option>
          <option value="turnover">按换手</option>
        </select>
        <label class="muted"><input id="exclude_st" type="checkbox" checked /> 排除 ST</label>
        <label class="muted"><input id="inflow_only" type="checkbox" /> 仅主力净流入</label>
        <button id="run-screen">筛选</button>
      </div>
      <div id="screen-result" class="muted">设置条件后点筛选。</div>
    </div>`;
  $("#run-screen").addEventListener("click", runScreener);
}

async function runScreener() {
  const box = $("#screen-result");
  box.innerHTML = "筛选中…";
  const qs = new URLSearchParams({
    pe_max: $("#pe_max").value,
    pb_max: $("#pb_max").value,
    roe_min: $("#roe_min").value,
    cap_min: $("#cap_min").value,
    industry: $("#industry").value,
    sort: $("#sort").value,
    exclude_st: $("#exclude_st").checked ? "1" : "0",
    inflow_only: $("#inflow_only").checked ? "1" : "0",
  });
  try {
    const data = await api("/api/screener?" + qs.toString());
    if (!data.items.length) {
      box.innerHTML = `<div class="empty">没有命中。尝试放宽 PE / ROE / 市值。</div>`;
      return;
    }
    const rows = data.items
      .map(
        (r) => `<tr data-code="${r.code}">
        <td>${r.name} <span class="muted">${r.code}</span></td>
        <td>${r.industry || ""}</td>
        <td>${fmt(r.price)}</td>
        <td class="${clsPct(r.pct)}">${signed(r.pct)}%</td>
        <td>${fmt(r.pe_ttm || r.pe, 1)}</td>
        <td>${fmt(r.pb, 2)}</td>
        <td class="${clsPct(r.main_net_inflow)}">${yi(r.main_net_inflow)}</td>
        <td>${fmt(r.roe, 1)}</td>
        <td>${r.score.total} · ${r.score.verdict}</td>
      </tr>`
      )
      .join("");
    box.innerHTML = `<p class="muted">${data.note} 命中 ${data.total} 只，展示前 ${data.items.length} 只。初筛分不含日 K，点进去才是完整研究评分。</p>
      <table class="table">
          <thead><tr><th>名称</th><th>行业</th><th>价格</th><th>涨跌</th><th>PE</th><th>PB</th><th>主力净流入</th><th>ROE</th><th>初筛分</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    box.querySelectorAll("tr[data-code]").forEach((tr) => tr.addEventListener("click", () => openStock(tr.dataset.code)));
  } catch (e) {
    box.innerHTML = `<div class="error">${e.message}</div>`;
  }
}

async function renderWatch() {
  showPage("watch");
  const items = loadWatch();
  if (!items.length) {
    pages.watch.innerHTML = `<div class="card empty">自选为空。在个股页点「加入自选」，数据只存在本机浏览器。</div>`;
    return;
  }
  pages.watch.innerHTML = `<div class="card muted">正在刷新自选…</div>`;
  const rows = [];
  for (const it of items) {
    try {
      const data = await api("/api/stock/" + it.code);
      rows.push({ ...it, data });
    } catch (e) {
      rows.push({ ...it, error: e.message });
    }
  }
  const html = rows
    .map((r) => {
      if (r.error) return `<tr><td>${r.name}</td><td colspan="4" class="error">${r.error}</td></tr>`;
      const q = r.data.quote;
      return `<tr data-code="${r.code}">
        <td>${q.name} <span class="muted">${q.code}</span></td>
        <td>${fmt(q.price)}</td>
        <td class="${clsPct(q.pct)}">${signed(q.pct)}%</td>
        <td>${r.data.score.total}</td>
        <td>${r.data.score.verdict}</td>
      </tr>`;
    })
    .join("");
  pages.watch.innerHTML = `<div class="card"><h3>自选观察</h3>
    <table class="table"><thead><tr><th>名称</th><th>价格</th><th>涨跌</th><th>评分</th><th>结论</th></tr></thead><tbody>${html}</tbody></table>
  </div>`;
  pages.watch.querySelectorAll("tr[data-code]").forEach((tr) => tr.addEventListener("click", () => openStock(tr.dataset.code)));
}

let suggestTimer = 0;
const searchInput = $("#search-input");
const suggestBox = $("#suggest");

searchInput.addEventListener("input", () => {
  clearTimeout(suggestTimer);
  const q = searchInput.value.trim();
  if (!q) {
    suggestBox.hidden = true;
    return;
  }
  suggestTimer = setTimeout(async () => {
    try {
      const data = await api("/api/search?q=" + encodeURIComponent(q));
      if (!data.items.length) {
        suggestBox.hidden = true;
        return;
      }
      suggestBox.innerHTML = data.items
        .map((it) => `<div data-code="${it.code}"><span>${it.name}</span><span class="muted">${it.ts_code} ${it.type}</span></div>`)
        .join("");
      suggestBox.hidden = false;
      suggestBox.querySelectorAll("div").forEach((el) =>
        el.addEventListener("click", () => {
          suggestBox.hidden = true;
          searchInput.value = el.dataset.code;
          openStock(el.dataset.code);
        })
      );
    } catch {
      suggestBox.hidden = true;
    }
  }, 200);
});

$("#search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = searchInput.value.trim();
  if (!q) return;
  if (/^\d{6}/.test(q)) openStock(q.slice(0, 6));
  else {
    api("/api/search?q=" + encodeURIComponent(q)).then((data) => {
      if (data.items[0]) openStock(data.items[0].code);
    });
  }
});

document.querySelectorAll(".nav button").forEach((btn) => {
  btn.addEventListener("click", () => {
    const page = btn.dataset.page;
    history.replaceState(null, "", "#/" + page);
    if (page === "market") {
      showPage("market");
      renderMarket();
    } else if (page === "screener") renderScreener();
    else renderWatch();
  });
});

function boot() {
  const hash = location.hash || "#/market";
  const m = hash.match(/#\/stock\/(\d{6})/);
  if (m) {
    openStock(m[1]);
    return;
  }
  if (hash.includes("screener")) renderScreener();
  else if (hash.includes("watch")) renderWatch();
  else {
    showPage("market");
    renderMarket();
  }
}

boot();
