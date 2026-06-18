# 智能炒股

基于 Python 的 A 股智能分析工具，通过多因子技术指标模型，为个股生成买入、观望、卖出等交易信号。

> **风险提示**：本项目仅供学习与研究，不构成任何投资建议。股市有风险，投资需谨慎。

## 功能特性

- **实时行情**：通过 [AKShare](https://github.com/akfamily/akshare) 获取 A 股日线数据
- **技术指标**：MA、RSI、MACD、布林带、OBV、ATR、VMA、KDJ、CCI、WR、MFI、ADX
- **盯盘预警**：趋势打分、多指标共振、动量共振(RSI+KDJ/CCI/WR)、ADX震荡过滤、布林/ATR预警
- **筹码/资金/估值**：筹码成本与获利盘、主力资金流、PE/PB估值、北向资金（沪深港通标的）
- **策略回测**：模拟多因子信号买卖，统计收益、回撤、胜率、夏普比率
- **AI 解读**：结合技术面与新闻生成投研摘要（支持 OpenAI 兼容 API）
- **批量分析**：支持同时分析多只股票并排序
- **股票搜索**：按代码或名称快速检索
- **一体化盯盘面板**：顶部实时看板 + 下方 K 线/分时同屏，自动刷新自选股信号与告警
- **第三期指标**：AMA 自适应均线、VIX 波动恐慌指数、板块情绪、分时 RSI/VWAP、自定义策略编辑器
- **Web 面板**：K 线蜡烛图、缩放平移、布林带叠加、十字光标联动、自选股 SQLite 持久化、监控告警、多股对比

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 分析单只股票

```bash
# 实时行情（需网络可访问 A 股数据源）
python main.py analyze 600519

# 演示模式（本地模拟数据，无需网络）
python main.py --demo analyze 600519
```

示例输出包含：最新价、综合评分、交易信号、分析依据与关键指标。

### 3. 搜索股票

```bash
python main.py search 茅台
python main.py search 600519
```

### 4. 批量分析

```bash
python main.py batch 600519 000001 300750 --days 120
```

### 5. 启动 Web 可视化面板

```bash
# 演示模式（推荐）
python web_main.py --demo --port 8000

# 实时行情模式
python web_main.py --port 8000

# 指定数据库路径（默认 data/smart_stock.db）
python web_main.py --port 8000 --db E:/zhinengchaogu/data/smart_stock.db
```

浏览器访问 `http://127.0.0.1:8000`，即可使用：

- **实时盯盘看板**（页面顶部）：自选股现价、信号、趋势分、共振、ADX、动量、VIX、板块、AMA 一览
- **自定义策略编辑器**（左侧栏）：买卖阈值、ADX 过滤、因子权重、AMA 开关，保存到 SQLite
- **分时图**（主图区）：5/15/30/60 分钟 K 线 + RSI + VWAP
- 股票搜索与单股分析
- K 线蜡烛图 + 均线/AMA，支持滚轮缩放、拖拽平移、← → 逐根切换
- MACD / RSI / 布林带 / 成交量 / OBV / KDJ 副图切换
- 信号评分卡、自选股管理（60 秒自动监控）
- 多股归一化收益对比图、策略回测、AI 投研解读

### 一体化 Web 面板操作步骤（Windows 示例）

#### 第一步：拉取代码并安装依赖

```powershell
cd E:\zhinengchaogu
git pull origin cursor/phase3-unified-dfac
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

#### 第二步：启动 Web 服务

```powershell
# 演示模式（无网络也能用，推荐先体验）
python web_main.py --demo --port 8000

# 实盘模式（需能访问东方财富行情）
python web_main.py --port 8000

# 指定数据库路径
python web_main.py --port 8000 --db E:\zhinengchaogu\data\smart_stock.db
```

若提示端口占用：

```powershell
netstat -ano | findstr :8000
# 结束占用进程，或换端口：
python web_main.py --port 8001
```

#### 第三步：打开浏览器

1. 访问 `http://127.0.0.1:8000`（若换了端口则对应修改）
2. 按 **Ctrl+F5** 强制刷新，避免旧版 JS/CSS 缓存

#### 第四步：分析单只股票

1. 顶部输入框输入代码（如 `600519`）或名称（如 `茅台`）
2. 点击 **搜索**，在左侧结果中点选股票
3. 点击 **分析**，等待 K 线、副图、评分卡加载完成
4. 主图可勾选 **AMA均线**、**买卖点**、**叠加布林带**

#### 第五步：配置自选股与实时盯盘

1. 左侧 **自选股** 区域输入代码，点 **添加**
2. 顶部 **实时盯盘看板** 自动显示所有自选股摘要
3. 左侧可设置 **自动监控** 间隔（30 秒 / 60 秒 / 5 分钟）
4. 点 **立即刷新看板** 可手动更新；勾选 **监控时同步刷新当前股 K 线** 可在盯盘时同步重绘图表
5. 点击看板某一行可快速切换当前分析股票

#### 第六步：使用第三期功能

| 功能 | 操作 |
|------|------|
| **AMA 自适应均线** | 主图勾选「AMA均线」；评分卡显示 AMA 信号 |
| **VIX 恐慌指数** | 评分卡「VIX 恐慌」；看板 VIX 列；高恐慌时触发预警 |
| **板块情绪** | 评分卡「板块情绪」；看板板块列显示行业涨跌 |
| **分时指标** | 主图区「分时走势与指标」选择 5/15/30/60 分钟，点 **刷新分时** |
| **策略编辑器** | 左侧调整买入/卖出阈值、因子权重 → **保存策略** → 重新点 **分析** 生效 |

#### 第七步：回测与 AI 解读（可选）

1. 左侧点 **策略回测** → **运行回测** 查看历史收益
2. 点 **AI 解读** → **生成解读**（无 API Key 时为演示摘要）

#### 常见问题

| 现象 | 处理 |
|------|------|
| 浏览器 `ERR_CONNECTION_REFUSED` | 确认终端里 `web_main.py` 正在运行且无报错 |
| K 线显示折线或样式旧 | Ctrl+F5 强刷；确认拉取了最新分支 |
| 实盘拉取失败 | 先用 `--demo`；或稍后重试 **分析** |
| 策略改了没变化 | 保存后需重新点击 **分析** 或 **立即刷新看板** |

#### 本地数据库

Web 服务启动时会自动创建 SQLite 数据库（默认 `data/smart_stock.db`），用于保存：

| 数据 | 说明 |
|------|------|
| 自选股 | 股票代码列表 |
| 监控设置 | 自动监控间隔、通知开关 |
| 信号快照 | 每只股票最新信号与评分 |
| 信号告警 | 信号变化历史记录 |
| 分析历史 | 每次「分析」的完整结果 JSON |

也可通过环境变量指定路径：

```bash
export SMART_STOCK_DB=/path/to/smart_stock.db
python web_main.py --port 8000
```

### 6. 策略回测

```bash
python main.py --demo backtest 600519 --days 180 --capital 100000
```

输出策略收益、基准收益、最大回撤、胜率、夏普比率等指标。

### 7. AI 解读（财报/新闻）

```bash
# 演示模式（无需 API Key）
python main.py --demo insight 600519

# 配置大模型后使用真实 AI 解读
export OPENAI_API_KEY=your_key
export OPENAI_BASE_URL=https://api.openai.com/v1
python main.py insight 600519
```

可复制 `.env.example` 为 `.env` 并填入密钥。

## 评分逻辑

系统从四个维度综合评分（范围约 -2 ~ +2）：

| 维度 | 说明 |
|------|------|
| 趋势 | 均线多空排列、价格与均线关系 |
| 动量 | RSI 超买超卖、MACD 金叉死叉 |
| 波动 | 布林带位置 |
| 成交量 | 放量上涨/下跌、量能萎缩 |

| 综合评分 | 信号 |
|----------|------|
| ≥ 1.0 | 强烈买入 |
| ≥ 0.6 | 买入 |
| -0.6 ~ 0.6 | 观望 |
| ≤ -0.6 | 卖出 |
| ≤ -1.0 | 强烈卖出 |

## 项目结构

```
smart_stock/
├── analyzer.py    # 分析编排
├── chip.py        # 筹码分布
├── cli.py         # 命令行界面
├── config.py      # 配置参数
├── data.py        # 行情数据获取
├── fundamentals.py # 估值与北向
├── indicators.py  # 技术指标计算
├── intraday.py    # 分时指标
├── sector.py      # 板块情绪
├── vix.py         # 波动恐慌指数
├── strategy_profile.py # 可持久化策略配置
├── models.py      # 数据模型
├── serializers.py # API 序列化
├── service.py     # Web 服务层
├── strategy.py    # 交易策略与信号
├── backtest.py    # 策略回测
├── news.py        # 新闻资讯
├── llm_insight.py # 大模型解读
└── web/           # Web 面板
    ├── app.py
    └── static/
main.py            # CLI 入口
web_main.py        # Web 入口
```

## 自定义参数

可在 `smart_stock/config.py` 中调整：

- 均线周期（默认 5/10/20/60）
- RSI、MACD、布林带参数
- 买入/卖出阈值

## 后续可扩展方向

- 策略参数优化与多策略组合回测
- 接入更多实时资讯源与公告 PDF 解析
- 板块映射自动同步、沪深 300 真实 iVIX 数据源

## License

MIT
