# 基金投资分析脚本

## 免责声明

**本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。**

**不构成任何投资建议，据此操作风险自担。**

**基金投资有风险，过往业绩不代表未来表现。**

## 利益冲突声明

本工具作者不持有任何基金公司的股份，不接受任何基金公司的赞助。
所有推荐（如果有）仅基于公开数据和算法，不代表任何投资建议。

---

## 项目概述

这是一个为500元投资入门设计的基金分析工具，包含数据获取、分析、可视化、定投模拟、回测、投资日志等功能。

## 文件结构

```
scripts/
├── config.yaml              # 配置文件
├── config_manager.py        # 配置管理模块
├── fund_data_fetcher.py     # 基金数据获取模块（基础版）
├── fund_data_fetcher_v2.py  # 基金数据获取模块（增强版，多数据源+缓存）
├── fund_analyzer.py         # 基金分析模块（基础版）
├── fund_analyzer_v2.py      # 基金分析模块（增强版，技术指标+智能定投）
├── fund_database.py         # SQLite数据库模块（含投资日志）
├── fund_notifier.py         # 通知模块（微信/邮件/控制台）
├── main.py                  # 主程序（基础版）
├── main_cli.py              # 命令行主程序（增强版）
├── trading_system.py        # 模块化交易系统（五模块信号）
├── demo_analysis.py         # 演示脚本（使用模拟数据）
├── test_project.py          # 项目测试
├── test_optimization.py     # 优化功能测试
└── README.md                # 本说明文档
```

## 功能特性

### 1. 数据获取
- 多数据源降级（东方财富 -> 新浪 -> 腾讯）
- 请求重试机制和缓存（1小时过期）
- 数据完整性校验（心跳检测）

### 2. 分析功能
- 收益率计算（总收益率、年化收益率）
- 风险指标（最大回撤、波动率、夏普比率）
- 技术指标（MA、RSI、布林带、MACD）
- 基金 vs 基准对比（超额收益、信息比率）
- 定投模拟（普通定投 + 价值平均定投）

### 3. 回测功能
- 双均线策略回测
- 含交易成本（0.15%佣金 + 0.1%滑点）
- 交易记录输出

### 4. 投资日志
- 记录每次操作的理由、情绪、反思
- 月度复盘功能
- 帮助新手养成好习惯

### 5. 可视化
- 静态图表（matplotlib PNG）
- 交互式图表（plotly HTML）

### 6. 通知预警
- 微信企业机器人
- 邮件通知
- 控制台输出

### 7. 数据存储
- SQLite本地数据库
- 复合索引优化
- 自动清理旧数据（默认保留3年）

### 8. 模块化交易系统
- 五模块独立判断：趋势、买点、波动、风控、止盈
- `--action signal` 命令输出明确交易信号（BUY/SELL/HOLD）
- 基金版优化：回撤控制替代止损、年化波动率替代ATR

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install pandas matplotlib requests pyyaml requests-cache plotly jinja2 watchdog
```

### Docker部署

```bash
# 构建镜像
docker build -t fund-analyzer .

# 运行
docker run fund-analyzer
```

## 使用方法

### 1. 交互式向导（新手推荐）

```bash
python scripts/main_cli.py --wizard
```

### 2. 分析基金

```bash
python scripts/main_cli.py --action analyze --fund 110011 161725
```

### 3. 监控预警

```bash
python scripts/main_cli.py --action monitor --notify
```

### 4. 回测策略（含交易成本）

```bash
python scripts/main_cli.py --action backtest --fund 110011
```

### 5. 定投模拟

```bash
# 普通定投
python scripts/main_cli.py --action simulate --fund 110011 --amount 500

# 价值平均定投
python scripts/main_cli.py --action simulate --fund 110011 --amount 500 --strategy value_avg
```

### 6. 基金 vs 基准对比

```bash
python scripts/main_cli.py --action compare --fund 110011 --benchmark 110030
```

### 7. 生成交互式图表

```bash
python scripts/main_cli.py --action chart --fund 110011
```

### 8. 生成分析报告

```bash
python scripts/main_cli.py --action report --fund 110011
```

### 9. 记录投资日志

```bash
python scripts/main_cli.py --action journal --fund 110011 --trade-action buy --amount 100 --nav 1.5 --reason "定投" --emotion calm
```

### 10. 月度复盘

```bash
python scripts/main_cli.py --action review --year 2026 --month 5
```

### 11. 魔鬼代言人（反面观点）

```bash
python scripts/main_cli.py --action devils-advocate --fund 110011
```

### 12. 巴菲特赌局

```bash
python scripts/main_cli.py --action buffet-bet --fund 110011
```

### 13. 每日简报

```bash
python scripts/main_cli.py --action daily-report
```

### 14. 随机复盘

```bash
python scripts/main_cli.py --action random-review
```

### 16. 模块化交易信号

```bash
python scripts/main_cli.py --action signal --fund 110011
```

输出五个模块的判断结果和综合交易信号（BUY/SELL/HOLD）。

### 17. 其他命令

```bash
# 列出基金
python scripts/main_cli.py --action list

# 显示配置
python scripts/main_cli.py --action config

# 演示脚本（模拟数据）
python scripts/demo_analysis.py
```

## 环境变量配置

敏感信息建议使用环境变量：

```bash
# Windows
set WECHAT_WEBHOOK=your_webhook_url
set EMAIL_PASSWORD=your_email_password

# Linux/Mac
export WECHAT_WEBHOOK=your_webhook_url
export EMAIL_PASSWORD=your_email_password
```

## 基金代码示例

| 基金代码 | 基金名称 | 类型 |
|---------|----------|------|
| 110011 | 易方达中小盘混合 | 混合型 |
| 110020 | 易方达沪深300ETF联接 | 指数型 |
| 001632 | 天弘创新驱动混合 | 混合型 |
| 161725 | 招商中证白酒指数 | 指数型 |
| 110030 | 易方达沪深300量化增强 | 指数型 |

## 分析指标说明

### 收益指标
- **总收益率**：投资期间的总收益百分比
- **年化收益率**：将总收益换算成年度收益率

### 风险指标
- **最大回撤**：从最高点到最低点的最大跌幅
- **波动率**：收益率的标准差
- **夏普比率**：风险调整后收益（>1良好，>2优秀）

### 技术指标（仅供学习参考）
- **RSI**：相对强弱指标（>70超买，<30超卖）
- **布林带**：价格波动通道
- **MACD**：趋势跟踪指标
- **均线偏离**：当前价格与均线的偏离程度

## 注意事项

1. **数据来源**：使用东方财富等公开接口，接口稳定性可能受影响
2. **网络要求**：获取真实数据需要网络连接正常
3. **数据延迟**：基金净值数据通常有1-2天延迟
4. **技术指标**：RSI、MACD等指标在基金日频净值上会严重滞后，仅供学习参考
5. **回测结果**：历史数据不代表未来表现，实盘会有交易成本和滑点

## 技术栈

- Python 3.8+
- pandas / numpy：数据处理
- matplotlib：静态图表
- plotly：交互式图表
- requests / requests-cache：网络请求和缓存
- sqlite3：本地数据库
- pyyaml：配置文件
- jinja2：HTML报表模板
- watchdog：配置文件热加载

## 更新日志

- 2026-05-25：优化4 - 模块化交易系统
  - 新增trading_system.py模块（五模块架构）
  - 新增ATR和SAR技术指标
  - 新增signal命令输出交易信号
  - config.yaml添加trading_system配置
- 2026-05-24：优化3 - 投资心理保护
- 2026-05-24：优化版本
  - 多数据源降级和请求缓存
  - 技术指标（RSI、布林带、MACD）
  - 通知模块（微信/邮件）
  - 命令行工具增强
  - 免责声明
  - 凭证安全（环境变量）
  - 数据完整性校验
  - 数据库复合索引和自动清理
  - 回测含交易成本
  - 基金 vs 基准对比
  - 投资日志和月度复盘
  - 交互式向导模式
  - 价值平均定投策略
  - 交互式HTML图表
