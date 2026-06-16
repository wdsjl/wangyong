const state = {
  demo: true,
  currentCode: "600519",
  chartData: null,
  activeIndicator: "macd",
  showBollinger: false,
  showTradeMarkers: true,
  hoverIndex: null,
  zoomRange: null,
  keyboardNavEnabled: true,
  watchlistCodes: [],
  monitorEnabled: true,
  monitorIntervalSec: 60,
  notifyEnabled: false,
  monitorTimer: null,
  priceChart: null,
  indicatorChart: null,
  compareChart: null,
  backtestChart: null,
  analyzeRequestId: 0,
  chartRenderToken: 0,
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
  addWatchBtn: document.getElementById("addWatchBtn"),
  clearWatchBtn: document.getElementById("clearWatchBtn"),
  batchBtn: document.getElementById("batchBtn"),
  watchlist: document.getElementById("watchlist"),
  watchlistChips: document.getElementById("watchlistChips"),
  watchlistCount: document.getElementById("watchlistCount"),
  monitorToggle: document.getElementById("monitorToggle"),
  monitorInterval: document.getElementById("monitorInterval"),
  monitorNowBtn: document.getElementById("monitorNowBtn"),
  notifyToggle: document.getElementById("notifyToggle"),
  alertPanel: document.getElementById("alertPanel"),
  compareBtn: document.getElementById("compareBtn"),
  backtestBtn: document.getElementById("backtestBtn"),
  insightBtn: document.getElementById("insightBtn"),
  runBacktestBtn: document.getElementById("runBacktestBtn"),
  runInsightBtn: document.getElementById("runInsightBtn"),
  backtestStats: document.getElementById("backtestStats"),
  backtestPanel: document.getElementById("backtestPanel"),
  insightContent: document.getElementById("insightContent"),
  insightPanel: document.getElementById("insightPanel"),
  showBollToggle: document.getElementById("showBollToggle"),
  keepOnlyCurrentBtn: document.getElementById("keepOnlyCurrentBtn"),
  showTradeMarkersToggle: document.getElementById("showTradeMarkersToggle"),
  resetZoomBtn: document.getElementById("resetZoomBtn"),
  crosshairInfo: document.getElementById("crosshairInfo"),
  priceChartEmpty: document.getElementById("priceChartEmpty"),
  indicatorChartEmpty: document.getElementById("indicatorChartEmpty"),
};

const signalClassMap = {
  STRONG_BUY: "strong-buy",
  BUY: "buy",
  HOLD: "hold",
  SELL: "sell",
  STRONG_SELL: "strong-sell",
};

const WATCHLIST_STORAGE_KEY = "smart_stock_watchlist";
const SIGNAL_SNAPSHOT_KEY = "smart_stock_signal_snapshot";
const MONITOR_SETTINGS_KEY = "smart_stock_monitor_settings";
const DEFAULT_WATCHLIST = ["000815"];

const COMPARE_COLORS = ["#38bdf8", "#f472b6", "#fbbf24", "#34d399", "#c084fc", "#fb7185", "#22d3ee", "#f97316"];

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

const tradeMarkerPlugin = {
  id: "tradeMarkers",
  afterDatasetsDraw(chart) {
    if (!state.showTradeMarkers || !state.chartData || chart.canvas.id !== "priceChart") {
      return;
    }
    const buyMarkers = state.chartData.buy_markers || [];
    const sellMarkers = state.chartData.sell_markers || [];
    if (!buyMarkers.length && !sellMarkers.length) return;

    const xScale = chart.scales.x;
    const yScale = chart.scales.y;
    if (!xScale || !yScale) return;

    const ctx = chart.ctx;
    const dateIndex = new Map(state.chartData.dates.map((date, index) => [date, index]));

    const drawMarker = (marker, color, direction) => {
      const index = dateIndex.get(marker.date);
      if (index == null) return;
      const x = xScale.getPixelForValue(index);
      const y = yScale.getPixelForValue(marker.price);
      const size = 7;
      const offset = direction === "buy" ? size + 4 : -(size + 4);
      const tipY = y + offset;
      const baseY = tipY + (direction === "buy" ? -size * 1.6 : size * 1.6);

      ctx.save();
      ctx.fillStyle = color;
      ctx.beginPath();
      if (direction === "buy") {
        ctx.moveTo(x, tipY);
        ctx.lineTo(x - size, baseY);
        ctx.lineTo(x + size, baseY);
      } else {
        ctx.moveTo(x, tipY);
        ctx.lineTo(x - size, baseY);
        ctx.lineTo(x + size, baseY);
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    };

    buyMarkers.forEach((marker) => drawMarker(marker, "#22c55e", "buy"));
    sellMarkers.forEach((marker) => drawMarker(marker, "#ef4444", "sell"));
  },
};

const candlestickPlugin = {
  id: "customCandlestick",
  beforeDatasetsDraw(chart) {
    if (chart.canvas.id !== "priceChart" || !state.chartData) return;

    const chartData = state.chartData;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;
    if (!xScale || !yScale) return;

    const ctx = chart.ctx;
    const count = chartData.dates.length;
    let barWidth = 8;
    if (count > 1) {
      const step = Math.abs(xScale.getPixelForValue(1) - xScale.getPixelForValue(0));
      barWidth = Math.max(3, step * 0.55);
    }

    for (let index = 0; index < count; index += 1) {
      const open = Number(chartData.open[index]);
      const high = Number(chartData.high[index]);
      const low = Number(chartData.low[index]);
      const close = Number(chartData.close[index]);
      if (![open, high, low, close].every(Number.isFinite)) continue;

      const x = xScale.getPixelForValue(index);
      const yHigh = yScale.getPixelForValue(high);
      const yLow = yScale.getPixelForValue(low);
      const yOpen = yScale.getPixelForValue(open);
      const yClose = yScale.getPixelForValue(close);
      const isUp = close >= open;
      const fill = isUp ? chartColors.candleUp : chartColors.candleDown;
      const stroke = isUp ? chartColors.candleBorderUp : chartColors.candleBorderDown;
      const bodyTop = Math.min(yOpen, yClose);
      const bodyBottom = Math.max(yOpen, yClose);
      const bodyHeight = Math.max(1, bodyBottom - bodyTop);

      ctx.save();
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, yHigh);
      ctx.lineTo(x, yLow);
      ctx.stroke();
      ctx.fillStyle = fill;
      ctx.fillRect(x - barWidth / 2, bodyTop, barWidth, bodyHeight);
      ctx.restore();
    }
  },
};

Chart.register(crosshairPlugin, candlestickPlugin, tradeMarkerPlugin);

function initChartEnvironment() {
  if (typeof Chart === "undefined") {
    throw new Error("Chart.js 未加载，请确认 /static/vendor 目录下的图表库文件存在");
  }
  if (typeof ChartZoom !== "undefined") {
    Chart.register(ChartZoom);
  }
}

try {
  initChartEnvironment();
} catch (error) {
  console.error(error);
  document.addEventListener("DOMContentLoaded", () => {
    showChartMessage("priceChartEmpty", `${error.message}。请 git pull 更新后重启 web_main.py`);
    showChartMessage("indicatorChartEmpty", "图表库未就绪");
    setCanvasVisible("priceChart", false);
    setCanvasVisible("indicatorChart", false);
  });
}

function showChartMessage(targetId, message) {
  const node = document.getElementById(targetId);
  if (!node) return;
  node.textContent = message;
  node.classList.add("visible");
}

function hideChartMessage(targetId) {
  const node = document.getElementById(targetId);
  if (!node) return;
  node.classList.remove("visible");
  node.textContent = "";
}

function setCanvasVisible(canvasId, visible) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  canvas.classList.toggle("is-hidden", !visible);
}

function normalizeWatchCode(code) {
  return String(code).replace(/\D/g, "");
}

function parseWatchInput(value) {
  return [
    ...new Set(
      String(value)
        .split(/[,，\s]+/)
        .map(normalizeWatchCode)
        .filter(Boolean)
    ),
  ];
}

function loadWatchlistFromStorage() {
  try {
    const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (raw === null) {
      return [...DEFAULT_WATCHLIST];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [...DEFAULT_WATCHLIST];
    }
    return [...new Set(parsed.map(normalizeWatchCode).filter(Boolean))];
  } catch {
    return [...DEFAULT_WATCHLIST];
  }
}

function saveWatchlistToStorage(codes) {
  localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(codes));
}

async function loadWatchlistFromServer() {
  try {
    const payload = await api("/api/watchlist");
    if (Array.isArray(payload.codes)) {
      return [...new Set(payload.codes.map(normalizeWatchCode).filter(Boolean))];
    }
  } catch {
    // 服务端不可用时回退本地
  }
  return null;
}

async function persistWatchlistToServer(codes) {
  try {
    await api("/api/watchlist", {
      method: "PUT",
      body: JSON.stringify({ codes }),
    });
    return true;
  } catch {
    return false;
  }
}

function setWatchlistCodes(codes, { persist = true } = {}) {
  state.watchlistCodes = [...new Set(codes.map(normalizeWatchCode).filter(Boolean))];
  elements.watchInput.value = state.watchlistCodes.join(",");
  if (persist) {
    saveWatchlistToStorage(state.watchlistCodes);
    void persistWatchlistToServer(state.watchlistCodes);
  }
  renderWatchlistChips();
}

function addToWatchlist(code) {
  const normalized = normalizeWatchCode(code);
  if (!normalized) return false;
  if (state.watchlistCodes.includes(normalized)) return false;
  setWatchlistCodes([...state.watchlistCodes, normalized]);
  return true;
}

function removeFromWatchlist(code) {
  const normalized = normalizeWatchCode(code);
  setWatchlistCodes(state.watchlistCodes.filter((item) => item !== normalized));
}

function clearWatchlist() {
  setWatchlistCodes([]);
  elements.watchlist.innerHTML = '<div class="empty">自选股已清空，可添加新股票</div>';
  elements.alertPanel.innerHTML = '<div class="empty">暂无信号变化告警</div>';
  destroyChart(state.compareChart);
  state.compareChart = null;
  setStatus("已清空自选股");
}

function keepOnlyCurrentWatchlist() {
  const code = normalizeWatchCode(state.currentCode || elements.searchInput.value);
  if (!code) {
    setStatus("请先选择要保留的股票", true);
    return;
  }
  setWatchlistCodes([code]);
  elements.watchlist.innerHTML = '<div class="empty">点击批量分析查看结果</div>';
  setStatus(`自选股已仅保留 ${code}`);
}

function initWatchlist() {
  // 由 bootstrap 异步加载
}

async function bootstrapWatchlist() {
  let codes = await loadWatchlistFromServer();
  if (codes === null) {
    codes = loadWatchlistFromStorage();
  }
  if (!codes.length) {
    codes = [...DEFAULT_WATCHLIST];
  }
  setWatchlistCodes(codes, { persist: false });
  if (codes.length) {
    await persistWatchlistToServer(codes);
    saveWatchlistToStorage(codes);
  }
}

function renderWatchlistChips() {
  if (!elements.watchlistChips) return;

  if (!state.watchlistCodes.length) {
    elements.watchlistChips.innerHTML = '<div class="empty">暂无自选股，请添加</div>';
    elements.watchlistCount.textContent = "0 只";
    return;
  }

  elements.watchlistCount.textContent = `${state.watchlistCodes.length} 只`;
  elements.watchlistChips.innerHTML = state.watchlistCodes
    .map(
      (code) => `
        <div class="watch-chip ${code === state.currentCode ? "active" : ""}" data-code="${code}">
          <button type="button" class="chip-main" data-code="${code}">${code}</button>
          <button type="button" class="chip-remove" data-code="${code}" aria-label="移除 ${code}">×</button>
        </div>
      `
    )
    .join("");

  elements.watchlistChips.querySelectorAll(".chip-main").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentCode = button.dataset.code;
      elements.searchInput.value = state.currentCode;
      renderWatchlistChips();
      loadAnalysis();
    });
  });

  elements.watchlistChips.querySelectorAll(".chip-remove").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      removeFromWatchlist(button.dataset.code);
      setStatus(`已移除自选股 ${button.dataset.code}`);
    });
  });
}

function loadMonitorSettings() {
  try {
    const raw = localStorage.getItem(MONITOR_SETTINGS_KEY);
    if (!raw) return;
    const settings = JSON.parse(raw);
    state.monitorEnabled = settings.monitorEnabled ?? true;
    state.monitorIntervalSec = settings.monitorIntervalSec ?? 60;
    state.notifyEnabled = settings.notifyEnabled ?? false;
  } catch {
    // 使用默认值
  }
}

function saveMonitorSettings() {
  const payload = {
    monitorEnabled: state.monitorEnabled,
    monitorIntervalSec: state.monitorIntervalSec,
    notifyEnabled: state.notifyEnabled,
  };
  localStorage.setItem(MONITOR_SETTINGS_KEY, JSON.stringify(payload));
  void persistMonitorSettingsToServer(payload);
}

async function loadMonitorSettingsFromServer() {
  try {
    const payload = await api("/api/monitor-settings");
    return {
      monitorEnabled: payload.monitor_enabled ?? true,
      monitorIntervalSec: payload.interval_sec ?? 60,
      notifyEnabled: payload.notify_enabled ?? false,
    };
  } catch {
    return null;
  }
}

async function persistMonitorSettingsToServer(settings) {
  try {
    await api("/api/monitor-settings", {
      method: "PUT",
      body: JSON.stringify({
        monitor_enabled: settings.monitorEnabled,
        interval_sec: settings.monitorIntervalSec,
        notify_enabled: settings.notifyEnabled,
      }),
    });
    return true;
  } catch {
    return false;
  }
}

function loadSignalSnapshot() {
  try {
    return JSON.parse(localStorage.getItem(SIGNAL_SNAPSHOT_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveSignalSnapshot(items) {
  const snapshot = {};
  items.forEach((item) => {
    snapshot[item.code] = {
      signal: item.signal.value,
      signalKey: item.signal.key,
      score: item.score,
      updatedAt: new Date().toISOString(),
    };
  });
  localStorage.setItem(SIGNAL_SNAPSHOT_KEY, JSON.stringify(snapshot));
}

function detectSignalChanges(items, previous) {
  return items
    .filter((item) => {
      const prev = previous[item.code];
      return prev && prev.signal !== item.signal.value;
    })
    .map((item) => ({
      code: item.code,
      name: item.name,
      from: previous[item.code].signal,
      to: item.signal.value,
      score: item.score,
    }));
}

function renderAlerts(alerts) {
  if (!alerts.length) {
    elements.alertPanel.innerHTML = '<div class="empty">暂无信号变化告警</div>';
    return;
  }

  elements.alertPanel.innerHTML = alerts
    .map(
      (alert) => `
        <div class="alert-item">
          <strong>${alert.name} (${alert.code})</strong>
          <div class="meta">信号 ${alert.from} → ${alert.to} · 评分 ${alert.score >= 0 ? "+" : ""}${Number(alert.score).toFixed(3)}</div>
        </div>
      `
    )
    .join("");
}

function notifySignalChanges(alerts) {
  if (!state.notifyEnabled || !alerts.length || !("Notification" in window)) return;
  if (Notification.permission !== "granted") return;

  const body = alerts.map((alert) => `${alert.name}: ${alert.from} → ${alert.to}`).join("\n");
  new Notification("自选股信号变化", { body });
}

async function requestNotificationPermission() {
  if (!("Notification" in window)) {
    setStatus("当前浏览器不支持通知", true);
    state.notifyEnabled = false;
    elements.notifyToggle.checked = false;
    return;
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    state.notifyEnabled = false;
    elements.notifyToggle.checked = false;
    setStatus("未授予通知权限", true);
  }
}

function stopMonitorTimer() {
  if (state.monitorTimer) {
    clearInterval(state.monitorTimer);
    state.monitorTimer = null;
  }
}

function startMonitorTimer() {
  stopMonitorTimer();
  if (!state.monitorEnabled) return;
  state.monitorTimer = setInterval(() => {
    refreshWatchlist({ detectChanges: true, silent: true });
  }, state.monitorIntervalSec * 1000);
}

function initMonitorControls() {
  // 由 bootstrap 异步加载
}

async function bootstrapMonitorControls() {
  const serverSettings = await loadMonitorSettingsFromServer();
  if (serverSettings) {
    state.monitorEnabled = serverSettings.monitorEnabled;
    state.monitorIntervalSec = serverSettings.monitorIntervalSec;
    state.notifyEnabled = serverSettings.notifyEnabled;
  } else {
    loadMonitorSettings();
  }
  elements.monitorToggle.checked = state.monitorEnabled;
  elements.monitorInterval.value = String(state.monitorIntervalSec);
  elements.notifyToggle.checked = state.notifyEnabled;
  saveMonitorSettings();
  startMonitorTimer();
}

function renderCompareChart(series) {
  releaseCanvas("compareChart");
  state.compareChart = null;
  if (!series.length) {
    return;
  }

  const ctx = releaseCanvas("compareChart");
  if (!ctx) return;
  state.compareChart = new Chart(ctx, {
    type: "line",
    data: {
      datasets: series.map((item, index) => ({
        label: `${item.name} (${item.return_pct >= 0 ? "+" : ""}${item.return_pct}%)`,
        data: item.dates.map((date, dateIndex) => ({
          x: date,
          y: item.values[dateIndex],
        })),
        borderColor: COMPARE_COLORS[index % COMPARE_COLORS.length],
        backgroundColor: COMPARE_COLORS[index % COMPARE_COLORS.length],
        pointRadius: 0,
        borderWidth: 2,
        tension: 0.2,
      })),
    },
    options: baseChartOptions({
      plugins: {
        zoom: {
          pan: { enabled: true, mode: "x" },
          zoom: {
            wheel: { enabled: true, speed: 0.08 },
            pinch: { enabled: true },
            mode: "x",
          },
        },
      },
    }),
  });
}

async function loadCompareChart() {
  if (state.watchlistCodes.length < 2) {
    destroyChart(state.compareChart);
    setStatus("至少需要 2 只自选股才能对比", true);
    return;
  }

  const days = elements.daysSelect.value;
  setStatus("正在生成多股对比图...");
  try {
    const payload = await api(
      `/api/compare?codes=${encodeURIComponent(state.watchlistCodes.join(","))}&days=${days}`
    );
    renderCompareChart(payload.series);
    setStatus(`多股对比已更新，共 ${payload.series.length} 只股票`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
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
          <div class="result-actions">
            <button type="button" class="icon-btn add-watch-btn" data-code="${item.code}" title="加入自选">+</button>
            <span>查看</span>
          </div>
        </div>
      `
    )
    .join("");

  elements.searchResults.querySelectorAll(".result-item").forEach((node) => {
    node.addEventListener("click", (event) => {
      if (event.target.closest(".add-watch-btn")) return;
      state.currentCode = node.dataset.code;
      elements.searchInput.value = state.currentCode;
      loadAnalysis();
    });
  });

  elements.searchResults.querySelectorAll(".add-watch-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const added = addToWatchlist(button.dataset.code);
      setStatus(added ? `已加入自选：${button.dataset.code}` : `已在自选股中：${button.dataset.code}`);
    });
  });
}

function renderAnalysis(payload) {
  const { analysis } = payload;
  state.chartData = payload.chart;
  state.zoomRange = defaultZoomRange(state.chartData.dates.length);
  state.hoverIndex = null;
  elements.crosshairInfo.textContent = "移动鼠标到图表上查看数据，或使用 ← → 键逐根切换 K 线";

  const sourceLabel =
    payload.data_source === "live"
      ? "实盘"
      : payload.demo_fallback
        ? "模拟回退"
        : "演示";
  const sourceClass = payload.data_source === "live" ? "live" : "warning";
  elements.stockTitle.innerHTML = `${analysis.name} (${analysis.code}) <span class="badge ${sourceClass}">${sourceLabel}</span>`;
  state.currentCode = analysis.code;
  renderWatchlistChips();
  elements.latestPrice.textContent = formatPrice(analysis.latest_price);
  elements.latestDate.textContent = `${analysis.price_label || "收盘价"} · ${analysis.latest_date}`;
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

  requestAnimationFrame(() => renderCharts());
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
          <div class="watch-item-actions">
            <div class="signal-pill ${signalClassMap[item.signal.key] || "hold"}">${item.signal.value}</div>
            <button type="button" class="icon-btn watch-remove-btn" data-code="${item.code}" title="从自选删除">×</button>
          </div>
        </div>
      `
    )
    .join("");

  elements.watchlist.querySelectorAll(".watch-remove-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const code = button.dataset.code;
      removeFromWatchlist(code);
      setStatus(`已从自选移除 ${code}`);
      refreshWatchlist({ silent: true, withCompare: false });
    });
  });

  elements.watchlist.querySelectorAll(".watch-item").forEach((node) => {
    node.addEventListener("click", () => {
      state.currentCode = node.dataset.code;
      elements.searchInput.value = state.currentCode;
      loadAnalysis();
    });
  });
}

function releaseCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const existing = typeof Chart.getChart === "function" ? Chart.getChart(canvas) : null;
  if (existing) {
    existing.destroy();
  }
  return canvas;
}

function destroyChart(chart) {
  if (!chart) return;
  try {
    chart.destroy();
  } catch (error) {
    console.warn("destroy chart failed", error);
  }
}

function destroyCanvasChart(canvasId) {
  releaseCanvas(canvasId);
  if (canvasId === "priceChart") {
    state.priceChart = null;
  }
  if (canvasId === "indicatorChart") {
    state.indicatorChart = null;
  }
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
            const chartData = state.chartData;
            if (
              chartData &&
              context.dataIndex != null &&
              context.chart.canvas.id === "priceChart" &&
              context.dataset.label === "K线"
            ) {
              const index = context.dataIndex;
              return [
                `开: ${formatPrice(chartData.open[index])}`,
                `高: ${formatPrice(chartData.high[index])}`,
                `低: ${formatPrice(chartData.low[index])}`,
                `收: ${formatPrice(chartData.close[index])}`,
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

function buildPriceChartDatasets(chart) {
  return [
    {
      label: "K线",
      data: chart.close,
      borderColor: "transparent",
      backgroundColor: "transparent",
      pointRadius: 0,
      borderWidth: 0,
      order: 10,
    },
    { ...buildLineDataset("MA5", chart.ma5, chartColors.ma5), order: 1 },
    { ...buildLineDataset("MA10", chart.ma10, chartColors.ma10), order: 2 },
    { ...buildLineDataset("MA20", chart.ma20, chartColors.ma20), order: 3 },
    { ...buildLineDataset("MA60", chart.ma60, chartColors.ma60), order: 4 },
  ];
}

function createPriceChart(ctx, chart) {
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: chart.dates,
      datasets: buildPriceChartDatasets(chart),
    },
    options: buildPriceChartOptions(),
  });
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
  const series = Array.isArray(data) ? data.map((value) => (value == null ? null : Number(value))) : [];
  return {
    type: "line",
    label,
    data: series,
    borderColor: color,
    backgroundColor: color,
    borderWidth: dashed ? 1 : 1.5,
    borderDash: dashed ? [5, 4] : [],
    pointRadius: 0,
    tension: 0.2,
    spanGaps: true,
    yAxisID: "y",
  };
}

function buildPriceChartOptions(extra = {}) {
  return baseChartOptions({
    ...extra,
    scales: {
      x: {
        type: "category",
        ticks: { color: "#94a3b8", maxTicksLimit: 10 },
        grid: { color: "rgba(148, 163, 184, 0.08)" },
      },
      y: {
        ticks: { color: "#94a3b8" },
        grid: { color: "rgba(148, 163, 184, 0.08)" },
      },
      ...(extra.scales || {}),
    },
  });
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
    elements.crosshairInfo.textContent = "移动鼠标到图表上查看数据，或使用 ← → 键逐根切换 K 线";
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

function setHoverIndex(index, { force = false } = {}) {
  if (!force && state.hoverIndex === index) return;
  state.hoverIndex = index;
  updateCrosshairInfo(index);
  syncActiveElements(index);
  state.priceChart?.update("none");
  state.indicatorChart?.update("none");
}

function getDefaultHoverIndex() {
  if (!state.chartData) return 0;
  if (state.zoomRange) return state.zoomRange.max;
  return state.chartData.dates.length - 1;
}

function ensureIndexVisible(index) {
  if (!state.zoomRange || !state.chartData) return;

  const { min, max } = state.zoomRange;
  if (index >= min && index <= max) return;

  const windowSize = max - min;
  const lastIndex = state.chartData.dates.length - 1;
  let newMin;
  let newMax;

  if (index < min) {
    newMin = index;
    newMax = index + windowSize;
  } else {
    newMax = index;
    newMin = index - windowSize;
  }

  if (newMin < 0) {
    newMin = 0;
    newMax = Math.min(windowSize, lastIndex);
  }
  if (newMax > lastIndex) {
    newMax = lastIndex;
    newMin = Math.max(0, lastIndex - windowSize);
  }

  state.zoomRange = { min: newMin, max: newMax };
  [state.priceChart, state.indicatorChart].forEach((chart) => {
    if (!chart) return;
    applyZoomRange(chart.options, state.zoomRange);
    chart.update("none");
  });
}

function moveHoverIndex(delta) {
  if (!state.chartData) return;

  const lastIndex = state.chartData.dates.length - 1;
  const currentIndex = state.hoverIndex == null ? getDefaultHoverIndex() : state.hoverIndex;
  const nextIndex = Math.max(0, Math.min(lastIndex, currentIndex + delta));

  ensureIndexVisible(nextIndex);
  setHoverIndex(nextIndex, { force: true });
}

function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

function handleChartKeydown(event) {
  if (!state.keyboardNavEnabled || !state.chartData || isTypingTarget(event.target)) return;

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveHoverIndex(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    moveHoverIndex(1);
  }
}

function focusInitialHover() {
  if (!state.chartData) return;
  const index = getDefaultHoverIndex();
  setHoverIndex(index, { force: true });
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
  const renderToken = ++state.chartRenderToken;

  if (!chart || !chart.dates?.length) {
    destroyCanvasChart("priceChart");
    destroyCanvasChart("indicatorChart");
    showChartMessage("priceChartEmpty", "暂无 K 线数据，请先点击「分析」加载股票");
    showChartMessage("indicatorChartEmpty", "暂无副图数据");
    setCanvasVisible("priceChart", false);
    setCanvasVisible("indicatorChart", false);
    return;
  }

  hideChartMessage("priceChartEmpty");
  hideChartMessage("indicatorChartEmpty");
  setCanvasVisible("priceChart", true);
  setCanvasVisible("indicatorChart", true);

  destroyCanvasChart("priceChart");
  destroyCanvasChart("indicatorChart");
  if (renderToken !== state.chartRenderToken) return;

  const priceCtx = releaseCanvas("priceChart");
  if (!priceCtx || renderToken !== state.chartRenderToken) return;

  state.priceChart = createPriceChart(priceCtx, chart);

  const indicatorCtx = releaseCanvas("indicatorChart");
  if (!indicatorCtx || renderToken !== state.chartRenderToken) {
    destroyChart(state.priceChart);
    state.priceChart = null;
    return;
  }

  state.indicatorChart = new Chart(indicatorCtx, buildIndicatorConfig(chart, state.activeIndicator));

  attachChartInteractions(state.priceChart);
  attachChartInteractions(state.indicatorChart);
  focusInitialHover();
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
  destroyCanvasChart("indicatorChart");
  const indicatorCtx = releaseCanvas("indicatorChart");
  if (!indicatorCtx) return;
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
  const renderToken = ++state.chartRenderToken;
  destroyCanvasChart("priceChart");
  const priceCtx = releaseCanvas("priceChart");
  if (!priceCtx || renderToken !== state.chartRenderToken) return;
  state.priceChart = createPriceChart(priceCtx, state.chartData);
  attachChartInteractions(state.priceChart);
  hideChartMessage("priceChartEmpty");
  setCanvasVisible("priceChart", true);
  if (state.hoverIndex != null) {
    syncActiveElements(state.hoverIndex);
    state.priceChart?.update("none");
  }
  if (state.zoomRange && state.priceChart) {
    applyZoomRange(state.priceChart.options, state.zoomRange);
    state.priceChart.update("none");
  }
}

async function loadBacktest() {
  const code = state.currentCode || elements.searchInput.value.trim();
  if (!code) {
    setStatus("请先选择股票", true);
    return;
  }

  const days = elements.daysSelect.value;
  setStatus(`正在回测 ${code}...`);
  try {
    const payload = await api(`/api/backtest/${encodeURIComponent(code)}?days=${days}&capital=100000`);
    renderBacktest(payload);
    elements.backtestPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setStatus(`回测完成：策略收益 ${payload.total_return_pct >= 0 ? "+" : ""}${payload.total_return_pct}%`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

function renderBacktest(payload) {
  const stats = [
    ["策略收益", `${payload.total_return_pct >= 0 ? "+" : ""}${payload.total_return_pct}%`],
    ["基准收益", `${payload.benchmark_return_pct >= 0 ? "+" : ""}${payload.benchmark_return_pct}%`],
    ["超额收益", `${payload.excess_return_pct >= 0 ? "+" : ""}${payload.excess_return_pct}%`],
    ["最大回撤", `${payload.max_drawdown_pct}%`],
    ["胜率", `${payload.win_rate_pct}%`],
    ["交易次数", String(payload.trade_count)],
    ["夏普比率", payload.sharpe_ratio == null ? "-" : Number(payload.sharpe_ratio).toFixed(2)],
    ["期末权益", formatPrice(payload.final_equity)],
  ];

  elements.backtestStats.innerHTML = stats
    .map(
      ([label, value]) => `
        <div class="metric">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `
    )
    .join("");

  destroyChart(state.backtestChart);
  const ctx = document.getElementById("backtestChart");
  const dates = payload.equity_curve.map((item) => item.date);
  state.backtestChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "策略权益",
          data: payload.equity_curve.map((item) => item.equity),
          borderColor: "#38bdf8",
          backgroundColor: "#38bdf8",
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "买入持有",
          data: payload.equity_curve.map((item) => item.benchmark),
          borderColor: "#94a3b8",
          backgroundColor: "#94a3b8",
          pointRadius: 0,
          borderDash: [6, 4],
          tension: 0.2,
        },
      ],
    },
    options: baseChartOptions(),
  });
}

function markdownToHtml(text) {
  return text
    .replace(/^## (.*$)/gim, "<h3>$1</h3>")
    .replace(/^\- (.*$)/gim, "<li>$1</li>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n{2,}/g, "<br><br>");
}

async function loadInsight() {
  const code = state.currentCode || elements.searchInput.value.trim();
  if (!code) {
    setStatus("请先选择股票", true);
    return;
  }

  const days = elements.daysSelect.value;
  setStatus(`正在生成 AI 解读：${code}...`);
  elements.insightContent.innerHTML = '<div class="empty">正在分析技术面与新闻...</div>';
  try {
    const payload = await api(`/api/insight/${encodeURIComponent(code)}?days=${days}`);
    renderInsight(payload);
    elements.insightPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    const modeLabel = payload.mode === "llm" ? "大模型" : "演示模式";
    setStatus(`AI 解读完成（${modeLabel}）`);
  } catch (error) {
    elements.insightContent.innerHTML = `<div class="empty">${error.message}</div>`;
    setStatus(error.message, true);
  }
}

function renderInsight(payload) {
  const newsHtml = (payload.news || [])
    .map((item) => `<li>[${item.published_at}] ${item.title}（${item.source}）</li>`)
    .join("");
  elements.insightContent.innerHTML = `
    <div>${markdownToHtml(payload.content)}</div>
    ${newsHtml ? `<h3>参考新闻</h3><ul>${newsHtml}</ul>` : ""}
    <p class="watch-note">${payload.disclaimer}</p>
  `;
}

async function loadConfig() {
  const config = await api("/api/config");
  state.demo = config.demo;
  if (config.demo) {
    elements.modeBadge.textContent = "演示模式";
    elements.modeBadge.className = "badge warning";
  } else if (!config.live_data_ok) {
    elements.modeBadge.textContent = "实盘暂不可用";
    elements.modeBadge.className = "badge warning";
  } else {
    elements.modeBadge.textContent = "实时行情模式";
    elements.modeBadge.className = "badge live";
  }
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

async function loadAnalysis(retryCount = 0) {
  const code = elements.searchInput.value.trim() || state.currentCode;
  const days = elements.daysSelect.value;
  state.currentCode = code;
  const requestId = ++state.analyzeRequestId;

  setStatus(`正在分析 ${code}...`);
  showChartMessage("priceChartEmpty", `正在加载 ${code} 的 K 线...`);
  try {
    const payload = await api(`/api/analyze/${encodeURIComponent(code)}?days=${days}`);
    if (requestId !== state.analyzeRequestId) return;
    renderAnalysis(payload);
    const sourceHint = payload.demo_fallback
      ? "（网络波动，已临时使用模拟 K 线，可点分析重试）"
      : payload.data_source === "live"
        ? "（实盘数据）"
        : "（演示数据）";
    setStatus(`分析完成：${payload.analysis.name}${sourceHint}`);
  } catch (error) {
    if (requestId !== state.analyzeRequestId) return;
    if (retryCount < 2) {
      setStatus(`行情拉取失败，正在重试 (${retryCount + 1}/2)...`);
      await new Promise((resolve) => setTimeout(resolve, 1200));
      return loadAnalysis(retryCount + 1);
    }
    showChartMessage("priceChartEmpty", `分析失败，无法加载 K 线：${error.message}`);
    showChartMessage("indicatorChartEmpty", "副图暂无数据");
    setCanvasVisible("priceChart", false);
    setCanvasVisible("indicatorChart", false);
    setStatus(`${error.message}（可再次点击「分析」重试）`, true);
  }
}

async function refreshWatchlist({ detectChanges = false, silent = false, withCompare = false } = {}) {
  if (!state.watchlistCodes.length) {
    if (!silent) setStatus("请先添加自选股", true);
    return;
  }

  const codes = state.watchlistCodes.join(",");
  const days = elements.daysSelect.value;
  if (!silent) setStatus(detectChanges ? "正在监控刷新..." : "正在批量分析...");

  try {
    const payload = await api(
      `/api/batch?codes=${encodeURIComponent(codes)}&days=${days}&detect_changes=${detectChanges}`
    );
    const alerts = detectChanges ? payload.alerts || detectSignalChanges(payload.items, loadSignalSnapshot()) : [];
    saveSignalSnapshot(payload.items);
    renderWatchlist(payload.items);
    if (detectChanges) {
      renderAlerts(alerts);
      notifySignalChanges(alerts);
      if (!silent) {
        setStatus(alerts.length ? `检测到 ${alerts.length} 条信号变化` : "监控刷新完成，信号无变化");
      }
    } else if (!silent) {
      setStatus(`批量分析完成，共 ${payload.items.length} 只股票（已保存到数据库）`);
    }
    if (withCompare || state.watchlistCodes.length >= 2) {
      await loadCompareChart();
    }
  } catch (error) {
    if (!silent) setStatus(error.message, true);
  }
}

async function loadBatch() {
  await refreshWatchlist({ detectChanges: false, withCompare: true });
}

function addWatchFromInput() {
  const codes = parseWatchInput(elements.watchInput.value);
  if (!codes.length) {
    setStatus("请输入有效股票代码", true);
    return;
  }
  const merged = [...new Set([...state.watchlistCodes, ...codes])];
  const addedCount = merged.length - state.watchlistCodes.length;
  setWatchlistCodes(merged);
  elements.watchInput.value = "";
  setStatus(addedCount > 0 ? `已添加 ${addedCount} 只自选股` : "这些股票已在自选股中");
}

function addCurrentToWatchlist() {
  const code = state.currentCode || elements.searchInput.value.trim();
  const added = addToWatchlist(code);
  setStatus(added ? `已加入自选：${normalizeWatchCode(code)}` : `已在自选股中：${normalizeWatchCode(code)}`);
}

function bindEvents() {
  elements.searchBtn.addEventListener("click", searchStocks);
  elements.analyzeBtn.addEventListener("click", loadAnalysis);
  elements.batchBtn.addEventListener("click", loadBatch);
  elements.addWatchBtn.addEventListener("click", addWatchFromInput);
  document.querySelectorAll(".add-current-watch-btn").forEach((button) => {
    button.addEventListener("click", addCurrentToWatchlist);
  });
  elements.clearWatchBtn.addEventListener("click", () => {
    clearWatchlist();
  });
  elements.keepOnlyCurrentBtn.addEventListener("click", keepOnlyCurrentWatchlist);
  elements.monitorNowBtn.addEventListener("click", () => {
    refreshWatchlist({ detectChanges: true, withCompare: true });
  });
  elements.compareBtn.addEventListener("click", loadCompareChart);
  elements.backtestBtn.addEventListener("click", loadBacktest);
  elements.insightBtn.addEventListener("click", loadInsight);
  elements.runBacktestBtn.addEventListener("click", loadBacktest);
  elements.runInsightBtn.addEventListener("click", loadInsight);
  elements.monitorToggle.addEventListener("change", (event) => {
    state.monitorEnabled = event.target.checked;
    saveMonitorSettings();
    startMonitorTimer();
    setStatus(state.monitorEnabled ? "已开启自动监控" : "已关闭自动监控");
  });
  elements.monitorInterval.addEventListener("change", (event) => {
    state.monitorIntervalSec = Number(event.target.value);
    saveMonitorSettings();
    startMonitorTimer();
  });
  elements.notifyToggle.addEventListener("change", async (event) => {
    state.notifyEnabled = event.target.checked;
    saveMonitorSettings();
    if (state.notifyEnabled) {
      await requestNotificationPermission();
      saveMonitorSettings();
    }
  });
  elements.watchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") addWatchFromInput();
  });
  elements.resetZoomBtn.addEventListener("click", resetZoom);
  elements.showBollToggle.addEventListener("change", (event) => {
    state.showBollinger = event.target.checked;
    state.activeIndicator = state.showBollinger ? "boll" : state.activeIndicator;
    if (state.showBollinger) {
      document.querySelectorAll(".chart-tabs button").forEach((node) => {
        node.classList.toggle("active", node.dataset.chart === "boll");
      });
      rerenderIndicatorChart();
      setStatus("布林带已切换到下方副图显示");
      return;
    }
    rerenderPriceChart();
  });
  if (elements.showTradeMarkersToggle) {
    elements.showTradeMarkersToggle.addEventListener("change", (event) => {
      state.showTradeMarkers = event.target.checked;
      state.priceChart?.update("none");
      setStatus(state.showTradeMarkers ? "已显示策略买卖点" : "已隐藏买卖点");
    });
  }
  elements.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchStocks();
  });
  document.addEventListener("keydown", handleChartKeydown);

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
  await bootstrapWatchlist();
  await bootstrapMonitorControls();
  await loadConfig();
  elements.searchInput.value = state.currentCode;
  await searchStocks();
  await loadAnalysis();
  if (state.watchlistCodes.length) {
    // 启动时只刷新自选股列表，避免与分析接口并发打满行情源
    await refreshWatchlist({ detectChanges: false, silent: true, withCompare: false });
  }
}

bootstrap();
