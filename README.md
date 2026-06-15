# 智能炒股

基于 Python 的 A 股智能分析工具，通过多因子技术指标模型，为个股生成买入、观望、卖出等交易信号。

> **风险提示**：本项目仅供学习与研究，不构成任何投资建议。股市有风险，投资需谨慎。

## 功能特性

- **实时行情**：通过 [AKShare](https://github.com/akfamily/akshare) 获取 A 股日线数据
- **技术指标**：MA、RSI、MACD、布林带
- **智能信号**：多因子评分，输出强烈买入 / 买入 / 观望 / 卖出 / 强烈卖出
- **批量分析**：支持同时分析多只股票并排序
- **股票搜索**：按代码或名称快速检索
- **Web 面板**：K 线蜡烛图、缩放平移、布林带叠加、十字光标联动与信号看板

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
```

浏览器访问 `http://127.0.0.1:8000`，即可使用：

- 股票搜索与单股分析
- K 线蜡烛图 + 均线图，支持滚轮缩放、拖拽平移
- 主图可叠加布林带，十字光标联动副图
- MACD / RSI / 布林带 / 成交量切换
- 信号评分卡与自选股批量看板

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
├── cli.py         # 命令行界面
├── config.py      # 配置参数
├── data.py        # 行情数据获取
├── indicators.py  # 技术指标计算
├── models.py      # 数据模型
├── serializers.py # API 序列化
├── service.py     # Web 服务层
├── strategy.py    # 交易策略与信号
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

- 接入大模型解读财报与新闻情绪
- 策略回测与收益统计
- 自选股监控与告警

## License

MIT
