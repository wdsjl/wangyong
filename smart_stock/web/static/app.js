const state = {
  demo: true,
  currentCode: "600519",
  chartData: null,
  activeIndicator: "macd",
  priceChart: null,
  indicatorChart: null,
};

const elements = {
  modeBadge: document.getElementById("modeBadge"),
  searchInput: document.getElementById("searchInput"),
  daysSelect: document.getElementById("daysSelect"),
  searchBtn: document.getElementById("searchBtn"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  statusText: document.getElementById("statusText"),
  searchResults: document.getElementById("searchResults"),
  stockTitle: document.getElementById("stockTitle"),
  latestPrice: document.getElementById("latestPrice"),
  latestDate: document.getElementById("latestDate"),
  signalPill: document.getElementById("signalPill"),
  scoreText: document.getElementById("scoreText"),
  scoreFill: document.getElementById("scoreFill"),
  reasonList: document.getElementById("reasonList"),
  metricGrid: document.getElementById("metricGrid"),
  riskNote: document.getElementById("riskNote"),
  watchInput: document.getElementById("watchInput"),
  batchBtn: document.getElementById("batchBtn"),
  watchlist: document.getElementById("watchlist"),
};

const signalClassMap = {
  STRONG_BUY: "strong-buy",
  BUY: "buy",
  HOLD: "hold",
  SELL: "sell",
  STRONG_SELL: "strong-sell",
};

const chartColors = {
  close: "#38bdf8",
  ma5: "#f472b6",
  ma10: "#a78bfa",
  ma20: "#fbbf24",
  ma60: "#34d399",
  upper: "#fca5a5",
  middle: "#94a3b8",
  lower: "#86efac",
  macd: "#38bdf8",
  signal: "#f59e0b",
  histPos: "#22c55e",
  histNeg: "#ef4444",
  rsi: "#c084fc",
  volume: "#64748b",
};

async function api(path) {
  const response = await fetch(path);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "请求失败");
  }
  return payload;
}

function setStatus(message, isError = false) {
  elements.statusText.textContent = message;
  elements.statusText.style.color = isError ? "#fca5a5" : "#94a3b8";
}

function formatPrice(value) {
  return Number(value).toFixed(2);
}

function scoreToWidth(score) {
  const normalized = Math.max(-2, Math.min(2, score));
  return `${((normalized + 2) / 4) * 100}%`;
}

function scoreToColor(score) {
  if (score >= 0.6) return chartColors.histPos;
  if (score <= -0.6) return chartColors.histNeg;
  return chartColors.middle;
}

function renderSearchResults(items) {
  if (!items.length) {
    elements.searchResults.innerHTML = '<div class="empty">未找到匹配股票</div>';
    return;
  }

  elements.searchResults.innerHTML = items
    .map(
      (item) => `
        <div class="result-item ${item.code === state.currentCode ? "active" : ""}" data-code="${item.code}">
          <div>
            <strong>${item.name}</strong>
            <div class="meta">${item.code}</div>
          </div>
          <span>查看</span>
        </div>
      `
    )
    .join("");

  elements.searchResults.querySelectorAll(".result-item").forEach((node) => {
    node.addEventListener("click", () => {
      state.currentCode = node.dataset.code;
      elements.searchInput.value = state.currentCode;
      loadAnalysis();
    });
  });
}

function renderAnalysis(payload) {
  const { analysis } = payload;
  state.chartData = payload.chart;

  elements.stockTitle.textContent = `${analysis.name} (${analysis.code})`;
  elements.latestPrice.textContent = formatPrice(analysis.latest_price);
  elements.latestDate.textContent = `最新交易日 ${analysis.latest_date}`;
  elements.signalPill.textContent = analysis.signal.value;
  elements.signalPill.className = `signal-pill ${signalClassMap[analysis.signal.key] || "hold"}`;
  elements.scoreText.textContent = `${analysis.score >= 0 ? "+" : ""}${analysis.score.toFixed(3)}`;
  elements.scoreFill.style.width = scoreToWidth(analysis.score);
  elements.scoreFill.style.background = scoreToColor(analysis.score);
  elements.reasonList.innerHTML = analysis.reasons.map((item) => `<li>${item}</li>`).join("");
  elements.riskNote.textContent = analysis.risk_note;

  const indicators = analysis.indicators || {};
  const metricItems = [
    ["MA5", indicators.ma5],
    ["MA10", indicators.ma10],
    ["MA20", indicators.ma20],
    ["MA60", indicators.ma60],
    ["RSI", indicators.rsi],
    ["MACD", indicators.macd],
    ["MACD 信号", indicators.macd_signal],
    ["MACD 柱", indicators.macd_hist],
  ];

  elements.metricGrid.innerHTML = metricItems
    .map(
      ([label, value]) => `
        <div class="metric">
          <span>${label}</span>
          <strong>${value == null ? "-" : formatPrice(value)}</strong>
        </div>
      `
    )
    .join("");

  renderCharts();
}

function renderWatchlist(items) {
  if (!items.length) {
    elements.watchlist.innerHTML = '<div class="empty">暂无结果</div>';
    return;
  }

  elements.watchlist.innerHTML = items
    .map(
      (item) => `
        <div class="watch-item" data-code="${item.code}">
          <div>
            <strong>${item.name}</strong>
            <div class="meta">${item.code} · ${formatPrice(item.latest_price)}</div>
          </div>
          <div class="signal-pill ${signalClassMap[item.signal.key] || "hold"}">${item.signal.value}</div>
        </div>
      `
    )
    .join("");

  elements.watchlist.querySelectorAll(".watch-item").forEach((node) => {
    node.addEventListener("click", () => {
      state.currentCode = node.dataset.code;
      elements.searchInput.value = state.currentCode;
      loadAnalysis();
    });
  });
}

function destroyChart(chart) {
  if (chart) chart.destroy();
}

function baseChartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        labels: { color: "#cbd5e1" },
      },
    },
    scales: {
      x: {
        ticks: { color: "#94a3b8", maxTicksLimit: 8 },
        grid: { color: "rgba(148, 163, 184, 0.08)" },
      },
      y: {
        ticks: { color: "#94a3b8" },
        grid: { color: "rgba(148, 163, 184, 0.08)" },
      },
    },
  };
}

function renderCharts() {
  const chart = state.chartData;
  if (!chart) return;

  destroyChart(state.priceChart);
  destroyChart(state.indicatorChart);

  const priceCtx = document.getElementById("priceChart");
  state.priceChart = new Chart(priceCtx, {
    type: "line",
    data: {
      labels: chart.dates,
      datasets: [
        { label: "收盘价", data: chart.close, borderColor: chartColors.close, tension: 0.2 },
        { label: "MA5", data: chart.ma5, borderColor: chartColors.ma5, tension: 0.2 },
        { label: "MA10", data: chart.ma10, borderColor: chartColors.ma10, tension: 0.2 },
        { label: "MA20", data: chart.ma20, borderColor: chartColors.ma20, tension: 0.2 },
        { label: "MA60", data: chart.ma60, borderColor: chartColors.ma60, tension: 0.2 },
      ],
    },
    options: baseChartOptions(),
  });

  const indicatorCtx = document.getElementById("indicatorChart");
  state.indicatorChart = new Chart(indicatorCtx, buildIndicatorConfig(chart, state.activeIndicator));
}

function buildIndicatorConfig(chart, type) {
  if (type === "rsi") {
    return {
      type: "line",
      data: {
        labels: chart.dates,
        datasets: [{ label: "RSI", data: chart.rsi, borderColor: chartColors.rsi, tension: 0.2 }],
      },
      options: {
        ...baseChartOptions(),
        plugins: {
          ...baseChartOptions().plugins,
          annotation: {},
        },
      },
    };
  }

  if (type === "boll") {
    return {
      type: "line",
      data: {
        labels: chart.dates,
        datasets: [
          { label: "收盘价", data: chart.close, borderColor: chartColors.close, tension: 0.2 },
          { label: "上轨", data: chart.boll_upper, borderColor: chartColors.upper, tension: 0.2 },
          { label: "中轨", data: chart.boll_middle, borderColor: chartColors.middle, tension: 0.2 },
          { label: "下轨", data: chart.boll_lower, borderColor: chartColors.lower, tension: 0.2 },
        ],
      },
      options: baseChartOptions(),
    };
  }

  if (type === "volume") {
    return {
      type: "bar",
      data: {
        labels: chart.dates,
        datasets: [{ label: "成交量", data: chart.volume, backgroundColor: "rgba(100, 116, 139, 0.55)" }],
      },
      options: baseChartOptions(),
    };
  }

  const histColors = chart.macd_hist.map((value) =>
    value == null ? "rgba(148, 163, 184, 0.3)" : value >= 0 ? chartColors.histPos : chartColors.histNeg
  );

  return {
    type: "bar",
    data: {
      labels: chart.dates,
      datasets: [
        {
          type: "bar",
          label: "MACD 柱",
          data: chart.macd_hist,
          backgroundColor: histColors,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "MACD",
          data: chart.macd,
          borderColor: chartColors.macd,
          tension: 0.2,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "信号线",
          data: chart.macd_signal,
          borderColor: chartColors.signal,
          tension: 0.2,
          yAxisID: "y",
        },
      ],
    },
    options: baseChartOptions(),
  };
}

async function loadConfig() {
  const config = await api("/api/config");
  state.demo = config.demo;
  elements.modeBadge.textContent = config.demo ? "演示模式" : "实时行情模式";
}

async function searchStocks() {
  const keyword = elements.searchInput.value.trim();
  if (!keyword) {
    setStatus("请输入搜索关键词", true);
    return;
  }

  setStatus("正在搜索...");
  try {
    const payload = await api(`/api/search?keyword=${encodeURIComponent(keyword)}&limit=12`);
    renderSearchResults(payload.items);
    setStatus(`找到 ${payload.items.length} 条结果`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadAnalysis() {
  const code = elements.searchInput.value.trim() || state.currentCode;
  const days = elements.daysSelect.value;
  state.currentCode = code;

  setStatus(`正在分析 ${code}...`);
  try {
    const payload = await api(`/api/analyze/${encodeURIComponent(code)}?days=${days}`);
    renderAnalysis(payload);
    setStatus(`分析完成：${payload.analysis.name}`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadBatch() {
  const codes = elements.watchInput.value.trim();
  if (!codes) {
    setStatus("请输入自选股代码", true);
    return;
  }

  const days = elements.daysSelect.value;
  setStatus("正在批量分析...");
  try {
    const payload = await api(`/api/batch?codes=${encodeURIComponent(codes)}&days=${days}`);
    renderWatchlist(payload.items);
    setStatus(`批量分析完成，共 ${payload.items.length} 只股票`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

function bindEvents() {
  elements.searchBtn.addEventListener("click", searchStocks);
  elements.analyzeBtn.addEventListener("click", loadAnalysis);
  elements.batchBtn.addEventListener("click", loadBatch);
  elements.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchStocks();
  });

  document.querySelectorAll(".chart-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".chart-tabs button").forEach((node) => node.classList.remove("active"));
      button.classList.add("active");
      state.activeIndicator = button.dataset.chart;
      if (state.chartData) {
        destroyChart(state.indicatorChart);
        const indicatorCtx = document.getElementById("indicatorChart");
        state.indicatorChart = new Chart(
          indicatorCtx,
          buildIndicatorConfig(state.chartData, state.activeIndicator)
        );
      }
    });
  });
}

async function bootstrap() {
  bindEvents();
  await loadConfig();
  elements.searchInput.value = state.currentCode;
  await searchStocks();
  await loadAnalysis();
  await loadBatch();
}

bootstrap();
