const state = {
  demo: true,
  currentCode: "600519",
  chartData: null,
  activeIndicator: "macd",
  showBollinger: false,
  hoverIndex: null,
  zoomRange: null,
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
  showBollToggle: document.getElementById("showBollToggle"),
  resetZoomBtn: document.getElementById("resetZoomBtn"),
  crosshairInfo: document.getElementById("crosshairInfo"),
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
  candleUp: "#ef4444",
  candleDown: "#22c55e",
  candleBorderUp: "#f87171",
  candleBorderDown: "#34d399",
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
  crosshair: "rgba(148, 163, 184, 0.55)",
};

const crosshairPlugin = {
  id: "crosshair",
  afterDraw(chart) {
    if (state.hoverIndex == null) return;
    const xScale = chart.scales.x;
    if (!xScale) return;

    const x = xScale.getPixelForValue(state.hoverIndex);
    const { top, bottom } = chart.chartArea;
    if (x < chart.chartArea.left || x > chart.chartArea.right) return;

    const ctx = chart.ctx;
    ctx.save();
    ctx.strokeStyle = chartColors.crosshair;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.stroke();
    ctx.restore();
  },
};

Chart.register(crosshairPlugin);

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

function formatVolume(value) {
  if (value == null) return "-";
  if (value >= 100000000) return `${(value / 100000000).toFixed(2)}亿`;
  if (value >= 10000) return `${(value / 10000).toFixed(2)}万`;
  return String(value);
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

function defaultZoomRange(length, windowSize = 60) {
  if (length <= windowSize) return { min: 0, max: length - 1 };
  return { min: length - windowSize, max: length - 1 };
}

function applyZoomRange(options, range) {
  options.scales.x.min = range.min;
  options.scales.x.max = range.max;
}

function syncZoomFrom(sourceChart) {
  const { min, max } = sourceChart.scales.x;
  state.zoomRange = { min, max };
  const target = sourceChart.canvas.id === "priceChart" ? state.indicatorChart : state.priceChart;
  if (!target) return;
  target.options.scales.x.min = min;
  target.options.scales.x.max = max;
  target.update("none");
}

function resetZoom() {
  if (!state.chartData) return;
  state.zoomRange = defaultZoomRange(state.chartData.dates.length);
  [state.priceChart, state.indicatorChart].forEach((chart) => {
    if (!chart) return;
    applyZoomRange(chart.options, state.zoomRange);
    chart.update("none");
  });
}

function buildZoomOptions() {
  return {
    pan: {
      enabled: true,
      mode: "x",
      onPanComplete: ({ chart }) => syncZoomFrom(chart),
    },
    zoom: {
      wheel: { enabled: true, speed: 0.08 },
      pinch: { enabled: true },
      mode: "x",
      onZoomComplete: ({ chart }) => syncZoomFrom(chart),
    },
    limits: {
      x: { min: "original", max: "original" },
    },
  };
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
  state.zoomRange = defaultZoomRange(state.chartData.dates.length);
  state.hoverIndex = null;
  elements.crosshairInfo.textContent = "移动鼠标到图表上查看十字光标数据";

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

function baseChartOptions(extra = {}) {
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        labels: { color: "#cbd5e1" },
      },
      tooltip: {
        callbacks: {
          title(items) {
            const chart = state.chartData;
            if (!chart || !items.length) return "";
            return chart.dates[items[0].dataIndex] || "";
          },
          label(context) {
            if (context.dataset.type === "candlestick") {
              const raw = context.raw;
              return [
                `开: ${formatPrice(raw.o)}`,
                `高: ${formatPrice(raw.h)}`,
                `低: ${formatPrice(raw.l)}`,
                `收: ${formatPrice(raw.c)}`,
              ];
            }
            const value = context.parsed.y;
            if (context.dataset.label === "成交量") {
              return `${context.dataset.label}: ${formatVolume(value)}`;
            }
            return `${context.dataset.label}: ${value == null ? "-" : formatPrice(value)}`;
          },
        },
      },
      zoom: buildZoomOptions(),
      ...extra.plugins,
    },
    scales: {
      x: {
        ticks: { color: "#94a3b8", maxTicksLimit: 10 },
        grid: { color: "rgba(148, 163, 184, 0.08)" },
      },
      y: {
        ticks: { color: "#94a3b8" },
        grid: { color: "rgba(148, 163, 184, 0.08)" },
      },
      ...extra.scales,
    },
  };

  if (state.zoomRange) {
    applyZoomRange(options, state.zoomRange);
  }
  return options;
}

function buildCandlestickData(chart) {
  return chart.dates.map((date, index) => ({
    x: date,
    o: chart.open[index],
    h: chart.high[index],
    l: chart.low[index],
    c: chart.close[index],
  }));
}

function buildVolumeColors(chart) {
  return chart.dates.map((_, index) => {
    const open = chart.open[index];
    const close = chart.close[index];
    if (open == null || close == null) {
      return "rgba(148, 163, 184, 0.35)";
    }
    return close >= open ? "rgba(239, 68, 68, 0.72)" : "rgba(34, 197, 94, 0.72)";
  });
}

function buildLineDataset(label, data, color, dashed = false) {
  return {
    type: "line",
    label,
    data,
    borderColor: color,
    backgroundColor: color,
    borderWidth: dashed ? 1 : 1.5,
    borderDash: dashed ? [5, 4] : [],
    pointRadius: 0,
    tension: 0.2,
    spanGaps: true,
  };
}

function buildPriceDatasets(chart) {
  const datasets = [
    {
      type: "candlestick",
      label: "K线",
      data: buildCandlestickData(chart),
      color: {
        up: chartColors.candleUp,
        down: chartColors.candleDown,
        unchanged: "#94a3b8",
      },
      borderColor: {
        up: chartColors.candleBorderUp,
        down: chartColors.candleBorderDown,
        unchanged: "#94a3b8",
      },
    },
    buildLineDataset("MA5", chart.ma5, chartColors.ma5),
    buildLineDataset("MA10", chart.ma10, chartColors.ma10),
    buildLineDataset("MA20", chart.ma20, chartColors.ma20),
    buildLineDataset("MA60", chart.ma60, chartColors.ma60),
  ];

  if (state.showBollinger) {
    datasets.push(
      buildLineDataset("BOLL 上轨", chart.boll_upper, chartColors.upper, true),
      buildLineDataset("BOLL 中轨", chart.boll_middle, chartColors.middle),
      buildLineDataset("BOLL 下轨", chart.boll_lower, chartColors.lower, true)
    );
  }

  return datasets;
}

function getIndicatorSummary(index) {
  const chart = state.chartData;
  if (!chart || index == null) return [];

  const summaries = {
    macd: [
      ["MACD", chart.macd[index]],
      ["信号", chart.macd_signal[index]],
      ["柱", chart.macd_hist[index]],
    ],
    rsi: [["RSI", chart.rsi[index]]],
    boll: [
      ["上轨", chart.boll_upper[index]],
      ["中轨", chart.boll_middle[index]],
      ["下轨", chart.boll_lower[index]],
    ],
    volume: [["成交量", chart.volume[index], true]],
  };

  return summaries[state.activeIndicator] || [];
}

function updateCrosshairInfo(index) {
  const chart = state.chartData;
  if (!chart || index == null) {
    elements.crosshairInfo.textContent = "移动鼠标到图表上查看十字光标数据";
    return;
  }

  const parts = [
    chart.dates[index],
    `开 ${formatPrice(chart.open[index])}`,
    `高 ${formatPrice(chart.high[index])}`,
    `低 ${formatPrice(chart.low[index])}`,
    `收 ${formatPrice(chart.close[index])}`,
    `MA20 ${formatPrice(chart.ma20[index])}`,
  ];

  getIndicatorSummary(index).forEach(([label, value, isVolume]) => {
    parts.push(`${label} ${isVolume ? formatVolume(value) : formatPrice(value)}`);
  });

  elements.crosshairInfo.textContent = parts.join("  |  ");
}

function setHoverIndex(index) {
  if (state.hoverIndex === index) return;
  state.hoverIndex = index;
  updateCrosshairInfo(index);
  syncActiveElements(index);
  state.priceChart?.update("none");
  state.indicatorChart?.update("none");
}

function clearHoverIndex() {
  state.hoverIndex = null;
  updateCrosshairInfo(null);
  [state.priceChart, state.indicatorChart].forEach((chart) => {
    if (!chart) return;
    chart.setActiveElements([]);
    chart.tooltip?.setActiveElements([], { x: 0, y: 0 });
    chart.update("none");
  });
}

function syncActiveElements(index) {
  [state.priceChart, state.indicatorChart].forEach((chart) => {
    if (!chart || index == null) return;
    const activeElements = chart.data.datasets.map((_, datasetIndex) => ({
      datasetIndex,
      index,
    }));
    chart.setActiveElements(activeElements);
    chart.tooltip?.setActiveElements(activeElements, { x: 0, y: 0 });
  });
}

function attachChartInteractions(chart) {
  if (!chart) return;

  chart.canvas.onmousemove = (event) => {
    const elementsAtEvent = chart.getElementsAtEventForMode(
      event,
      "index",
      { intersect: false },
      false
    );
    if (!elementsAtEvent.length) return;
    setHoverIndex(elementsAtEvent[0].index);
  };

  chart.canvas.onmouseleave = () => {
    clearHoverIndex();
  };
}

function renderCharts() {
  const chart = state.chartData;
  if (!chart) return;

  destroyChart(state.priceChart);
  destroyChart(state.indicatorChart);

  const priceCtx = document.getElementById("priceChart");
  state.priceChart = new Chart(priceCtx, {
    type: "candlestick",
    data: {
      labels: chart.dates,
      datasets: buildPriceDatasets(chart),
    },
    options: baseChartOptions(),
  });

  const indicatorCtx = document.getElementById("indicatorChart");
  state.indicatorChart = new Chart(indicatorCtx, buildIndicatorConfig(chart, state.activeIndicator));

  attachChartInteractions(state.priceChart);
  attachChartInteractions(state.indicatorChart);
}

function buildIndicatorConfig(chart, type) {
  if (type === "rsi") {
    return {
      type: "line",
      data: {
        labels: chart.dates,
        datasets: [buildLineDataset("RSI", chart.rsi, chartColors.rsi)],
      },
      options: baseChartOptions({
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { color: "#94a3b8", stepSize: 20 },
            grid: { color: "rgba(148, 163, 184, 0.08)" },
          },
        },
      }),
    };
  }

  if (type === "boll") {
    return {
      type: "line",
      data: {
        labels: chart.dates,
        datasets: [
          buildLineDataset("收盘价", chart.close, chartColors.close),
          buildLineDataset("上轨", chart.boll_upper, chartColors.upper, true),
          buildLineDataset("中轨", chart.boll_middle, chartColors.middle),
          buildLineDataset("下轨", chart.boll_lower, chartColors.lower, true),
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
        datasets: [
          {
            label: "成交量",
            data: chart.volume,
            backgroundColor: buildVolumeColors(chart),
          },
        ],
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
        },
        buildLineDataset("MACD", chart.macd, chartColors.macd),
        buildLineDataset("信号线", chart.macd_signal, chartColors.signal),
      ],
    },
    options: baseChartOptions(),
  };
}

function rerenderIndicatorChart() {
  if (!state.chartData) return;
  destroyChart(state.indicatorChart);
  const indicatorCtx = document.getElementById("indicatorChart");
  state.indicatorChart = new Chart(
    indicatorCtx,
    buildIndicatorConfig(state.chartData, state.activeIndicator)
  );
  if (state.zoomRange) {
    applyZoomRange(state.indicatorChart.options, state.zoomRange);
    state.indicatorChart.update("none");
  }
  attachChartInteractions(state.indicatorChart);
  if (state.hoverIndex != null) {
    syncActiveElements(state.hoverIndex);
    updateCrosshairInfo(state.hoverIndex);
    state.indicatorChart.update("none");
  }
}

function rerenderPriceChart() {
  if (!state.chartData) return;
  destroyChart(state.priceChart);
  const priceCtx = document.getElementById("priceChart");
  state.priceChart = new Chart(priceCtx, {
    type: "candlestick",
    data: {
      labels: state.chartData.dates,
      datasets: buildPriceDatasets(state.chartData),
    },
    options: baseChartOptions(),
  });
  attachChartInteractions(state.priceChart);
  if (state.hoverIndex != null) {
    syncActiveElements(state.hoverIndex);
    state.priceChart.update("none");
  }
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
  elements.resetZoomBtn.addEventListener("click", resetZoom);
  elements.showBollToggle.addEventListener("change", (event) => {
    state.showBollinger = event.target.checked;
    rerenderPriceChart();
  });
  elements.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchStocks();
  });

  document.querySelectorAll(".chart-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".chart-tabs button").forEach((node) => node.classList.remove("active"));
      button.classList.add("active");
      state.activeIndicator = button.dataset.chart;
      rerenderIndicatorChart();
      if (state.hoverIndex != null) {
        updateCrosshairInfo(state.hoverIndex);
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
