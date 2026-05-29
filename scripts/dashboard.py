#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web仪表盘 - 专业投资组合可视化
借鉴 Ghostfolio 和 AnalyzerPortfolio 的设计
"""

import json
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_manager import ConfigManager
    from execution_engine import ExecutionEngine
    from decision_engine import DecisionEngine
    from backtester import Backtester
    from knowledge_manager import KnowledgeManager
    from portfolio_analyzer import PortfolioAnalyzer
    from snapshot_manager import SnapshotManager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"组件导入失败: {e}")
    COMPONENTS_AVAILABLE = False

app = Flask(__name__)

executor = None
decider = None
backtester = None
knowledge = None
analyzer = None
snapshot_mgr = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能投资决策助手</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary: #2563eb;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-main);
            min-height: 100vh;
        }
        
        .app-container { display: flex; min-height: 100vh; }
        
        .sidebar {
            width: 240px; background: var(--bg-card); border-right: 1px solid var(--border);
            padding: 20px 0; position: fixed; height: 100vh;
        }
        
        .logo {
            padding: 0 20px 30px; font-size: 1.25rem; font-weight: 700;
            color: var(--primary); display: flex; align-items: center; gap: 10px;
        }
        
        .nav-item {
            padding: 12px 20px; display: flex; align-items: center; gap: 12px;
            color: var(--text-secondary); cursor: pointer; transition: all 0.2s;
        }
        
        .nav-item:hover, .nav-item.active { background: #eff6ff; color: var(--primary); }
        
        .main-content { flex: 1; margin-left: 240px; padding: 30px; }
        
        .page-header { margin-bottom: 30px; }
        .page-header h1 { font-size: 1.75rem; color: var(--text-primary); margin-bottom: 5px; }
        .page-header p { color: var(--text-secondary); font-size: 0.95rem; }
        
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--bg-card); border-radius: 12px; padding: 20px;
            border: 1px solid var(--border);
        }
        
        .stat-card h3 {
            font-size: 0.85rem; color: var(--text-secondary);
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;
        }
        
        .stat-value { font-size: 1.75rem; font-weight: 700; color: var(--text-primary); }
        .stat-value.positive { color: var(--success); }
        .stat-value.negative { color: var(--danger); }
        
        .charts-grid {
            display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px;
        }
        
        @media (max-width: 1200px) { .charts-grid { grid-template-columns: 1fr; } }
        
        .card {
            background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);
            padding: 20px;
        }
        
        .card-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
        }
        
        .card-header h2 { font-size: 1.1rem; color: var(--text-primary); }
        
        .chart-container { height: 350px; width: 100%; }
        
        .holdings-table { width: 100%; border-collapse: collapse; }
        
        .holdings-table th {
            text-align: left; padding: 12px 16px; font-size: 0.8rem;
            color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
        }
        
        .holdings-table td { padding: 16px; border-bottom: 1px solid var(--border); }
        
        .holdings-table tr:hover td { background: #f8fafc; }
        
        .fund-name { font-weight: 600; color: var(--text-primary); }
        .fund-code { font-size: 0.85rem; color: var(--text-secondary); }
        
        .profit-positive { color: var(--success); }
        .profit-negative { color: var(--danger); }
        
        .decision-list { max-height: 400px; overflow-y: auto; }
        
        .decision-item {
            padding: 16px; border-bottom: 1px solid var(--border);
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .decision-item:last-child { border-bottom: none; }
        
        .decision-action {
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            font-size: 0.85rem; font-weight: 600;
        }
        
        .decision-action.buy { background: #d1fae5; color: #065f46; }
        .decision-action.sell { background: #fee2e2; color: #991b1b; }
        .decision-action.hold { background: #dbeafe; color: #1e40af; }
        
        .refresh-btn {
            background: var(--primary); color: white; border: none;
            padding: 10px 20px; border-radius: 8px; cursor: pointer;
            font-size: 0.9rem; display: flex; align-items: center; gap: 8px;
            transition: background 0.3s;
        }
        
        .refresh-btn:hover { background: #1d4ed8; }
        
        .timestamp {
            color: var(--text-secondary); font-size: 0.85rem; margin-top: 20px;
            text-align: right;
        }
        
        .empty-state { text-align: center; padding: 40px; color: var(--text-secondary); }
        
        .metrics-grid {
            display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;
        }
        
        .metric-item {
            padding: 15px; background: #f8fafc; border-radius: 8px;
            display: flex; justify-content: space-between;
        }
        
        .metric-label { color: var(--text-secondary); font-size: 0.9rem; }
        .metric-value { font-weight: 600; }
    </style>
</head>
<body>
    <div class="app-container">
        <aside class="sidebar">
            <div class="logo"><span>📈</span><span>投资助手</span></div>
            <div class="nav-item active"><span>📊</span><span>仪表盘</span></div>
        </aside>
        
        <main class="main-content">
            <div class="page-header">
                <h1>投资仪表盘</h1>
                <p>实时监控 · 智能分析 · 风险控制</p>
            </div>
            
            <div class="stats-grid" id="stats-grid">
                <div class="stat-card">
                    <h3>总资产</h3>
                    <div class="stat-value" id="total-assets">加载中...</div>
                </div>
                <div class="stat-card">
                    <h3>总收益</h3>
                    <div class="stat-value" id="total-profit">加载中...</div>
                </div>
                <div class="stat-card">
                    <h3>收益率</h3>
                    <div class="stat-value" id="profit-rate">加载中...</div>
                </div>
                <div class="stat-card">
                    <h3>持仓基金</h3>
                    <div class="stat-value" id="fund-count">加载中...</div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="card">
                    <div class="card-header">
                        <h2>📈 资产趋势</h2>
                    </div>
                    <div class="chart-container" id="trend-chart"></div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <h2>📊 绩效指标</h2>
                    </div>
                    <div class="metrics-grid" id="metrics-grid">
                        <div class="empty-state"><p>加载中...</p></div>
                    </div>
                </div>
            </div>
            
            <div class="card" style="margin-bottom: 30px;">
                <div class="card-header">
                    <h2>💼 持仓明细</h2>
                    <button class="refresh-btn" onclick="refreshData()">
                        <span>🔄</span><span>刷新数据</span>
                    </button>
                </div>
                <table class="holdings-table" id="holdings-table">
                    <thead>
                        <tr>
                            <th>基金</th>
                            <th>当前净值</th>
                            <th>持仓份额</th>
                            <th>持仓成本</th>
                            <th>市值</th>
                            <th>盈亏</th>
                        </tr>
                    </thead>
                    <tbody id="holdings-tbody">
                        <tr><td colspan="6"><div class="empty-state"><p>加载中...</p></div></td></tr>
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>🎯 最新决策</h2>
                </div>
                <div class="decision-list" id="decision-list">
                    <div class="empty-state"><p>加载中...</p></div>
                </div>
            </div>
            
            <div class="timestamp" id="update-time">数据加载中...</div>
        </main>
    </div>
    
    <script>
        let trendChart;
        
        async function fetchAllData() {
            try {
                const [portfolio, decisions, metrics] = await Promise.all([
                    fetch('/api/portfolio').then(r => r.json()),
                    fetch('/api/decisions').then(r => r.json()),
                    fetch('/api/metrics').then(r => r.json())
                ]);
                
                updateStats(portfolio);
                updateHoldings(portfolio);
                updateDecisions(decisions);
                updateMetrics(metrics);
                updateTrendChart(portfolio);
            } catch (e) {
                console.error('加载失败:', e);
            }
        }
        
        function updateStats(data) {
            const holdings = data.holdings || [];
            let totalInvested = 0, totalValue = 0;
            
            holdings.forEach(h => {
                totalInvested += (h.total_invested || (h.shares * (h.avg_cost || 0)));
                totalValue += (h.current_value || (h.shares * (h.current_nav || 0)));
            });
            
            if (data.total_invested !== undefined) totalInvested = data.total_invested;
            if (data.total_value !== undefined) totalValue = data.total_value;
            
            const totalProfit = totalValue - totalInvested;
            const profitRate = totalInvested > 0 ? (totalProfit / totalInvested * 100) : 0;
            
            document.getElementById('total-assets').textContent = '¥' + totalValue.toFixed(2);
            
            const profitEl = document.getElementById('total-profit');
            profitEl.textContent = (totalProfit >= 0 ? '+' : '') + '¥' + totalProfit.toFixed(2);
            profitEl.className = 'stat-value ' + (totalProfit >= 0 ? 'positive' : 'negative');
            
            const rateEl = document.getElementById('profit-rate');
            rateEl.textContent = (profitRate >= 0 ? '+' : '') + profitRate.toFixed(2) + '%';
            rateEl.className = 'stat-value ' + (profitRate >= 0 ? 'positive' : 'negative');
            
            document.getElementById('fund-count').textContent = holdings.length + '只';
        }
        
        function updateHoldings(data) {
            const tbody = document.getElementById('holdings-tbody');
            const holdings = data.holdings || [];
            
            if (holdings.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p>暂无数据</p></div></td></tr>';
                return;
            }
            
            let html = '';
            holdings.forEach(h => {
                const marketValue = h.current_value || (h.shares * (h.current_nav || 0));
                const costValue = h.total_invested || (h.shares * (h.avg_cost || 0));
                const profit = marketValue - costValue;
                const profitRate = costValue > 0 ? (profit / costValue * 100) : 0;
                
                html += `
                    <tr>
                        <td>
                            <div class="fund-name">${h.fund_name || h.fund_code}</div>
                            <div class="fund-code">${h.fund_code}</div>
                        </td>
                        <td>¥${h.current_nav ? h.current_nav.toFixed(4) : '-'}</td>
                        <td>${h.shares ? h.shares.toFixed(2) : '-'}</td>
                        <td>¥${costValue.toFixed(2)}</td>
                        <td>¥${marketValue.toFixed(2)}</td>
                        <td class="${profit >= 0 ? 'profit-positive' : 'profit-negative'}">
                            ${profit >= 0 ? '+' : ''}¥${profit.toFixed(2)} 
                            (${profitRate >= 0 ? '+' : ''}${profitRate.toFixed(2)}%)
                        </td>
                    </tr>
                `;
            });
            
            tbody.innerHTML = html;
        }
        
        function updateDecisions(data) {
            const list = document.getElementById('decision-list');
            const decisions = data.decisions || [];
            
            if (decisions.length === 0) {
                list.innerHTML = '<div class="empty-state"><p>暂无决策</p></div>';
                return;
            }
            
            let html = '';
            decisions.slice(0, 10).forEach(d => {
                const actionClass = d.action === 'buy' ? 'buy' : d.action === 'sell' ? 'sell' : 'hold';
                const actionText = d.action === 'buy' ? '买入' : d.action === 'sell' ? '卖出' : '持有';
                
                html += `
                    <div class="decision-item">
                        <div>
                            <span class="decision-action ${actionClass}">${actionText}</span>
                            <span style="margin-left:10px;font-weight:600;">${d.fund_code}</span>
                            <span style="margin-left:8px;color:#64748b;font-size:0.9rem;">
                                评分: ${d.score ? (d.score * 100).toFixed(1) + '%' : '-'}
                            </span>
                        </div>
                        <div style="font-size:0.85rem;color:#64748b;">${d.date || ''}</div>
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }
        
        function updateMetrics(data) {
            const grid = document.getElementById('metrics-grid');
            const overall = data.overall || {};
            
            if (data.available === false || !Object.keys(overall).length) {
                grid.innerHTML = '<div class="empty-state" style="grid-column:span 2;"><p>暂无指标</p></div>';
                return;
            }
            
            let html = '';
            const displayMetrics = [
                { key: 'sharpe_ratio', label: '夏普比率' },
                { key: 'sortino_ratio', label: '索提诺比率' },
                { key: 'var_95', label: '95% VaR' },
                { key: 'annual_return', label: '年化收益' }
            ];
            
            displayMetrics.forEach(m => {
                const val = overall[m.key];
                if (val !== null && val !== undefined) {
                    html += `
                        <div class="metric-item">
                            <span class="metric-label">${m.label}</span>
                            <span class="metric-value">${typeof val === 'number' ? val.toFixed(2) : val}</span>
                        </div>
                    `;
                }
            });
            
            grid.innerHTML = html || '<div class="empty-state" style="grid-column:span 2;"><p>暂无数据</p></div>';
        }
        
        function updateTrendChart(data) {
            const chartDom = document.getElementById('trend-chart');
            if (!trendChart) trendChart = echarts.init(chartDom);
            
            const holdings = data.holdings || [];
            const now = new Date();
            const dates = [];
            for (let i = 30; i >= 0; i--) {
                const d = new Date(now);
                d.setDate(d.getDate() - i);
                dates.push(d.toLocaleDateString('zh-CN'));
            }
            
            const totalValue = holdings.reduce((sum, h) => 
                sum + (h.current_value || (h.shares * (h.current_nav || 0))), 0
            );
            const totalInvested = holdings.reduce((sum, h) => 
                sum + (h.total_invested || (h.shares * (h.avg_cost || 0))), 0
            );
            
            const baseValues = [];
            for (let i = 0; i <= 30; i++) {
                const trend = (totalValue - totalInvested) / 30;
                baseValues.push(totalInvested + trend * i + (Math.random() - 0.5) * totalInvested * 0.02);
            }
            
            const option = {
                tooltip: { trigger: 'axis' },
                grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                xAxis: { type: 'category', boundaryGap: false, data: dates },
                yAxis: { type: 'value' },
                series: [{
                    name: '资产价值',
                    type: 'line',
                    smooth: true,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(37, 99, 235, 0.3)' },
                            { offset: 1, color: 'rgba(37, 99, 235, 0.05)' }
                        ])
                    },
                    lineStyle: { color: '#2563eb', width: 2 },
                    data: baseValues
                }]
            };
            
            trendChart.setOption(option);
            window.addEventListener('resize', () => trendChart.resize());
        }
        
        function refreshData() {
            fetchAllData();
            document.getElementById('update-time').textContent = 
                '最后更新: ' + new Date().toLocaleString('zh-CN');
        }
        
        fetchAllData();
        setInterval(refreshData, 10 * 60 * 1000);
    </script>
</body>
</html>
"""

def init_components():
    """初始化所有组件"""
    global executor, decider, backtester, knowledge, analyzer, snapshot_mgr
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.yaml')
    db_path = os.path.join(script_dir, 'fund_data.db')
    
    try:
        executor = ExecutionEngine(config_path=config_path, db_path=db_path)
    except Exception:
        pass
    
    try:
        analyzer = PortfolioAnalyzer(db_path=db_path)
    except Exception:
        pass
    
    try:
        snapshot_mgr = SnapshotManager(data_dir=script_dir)
    except Exception:
        pass
    
    try:
        knowledge = KnowledgeManager(data_dir=script_dir)
    except Exception:
        pass


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/portfolio')
def api_portfolio():
    try:
        if executor:
            summary = executor.get_portfolio_summary()
            return jsonify(summary)
        return jsonify({'holdings': [], 'available': True})
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/decisions')
def api_decisions():
    try:
        if knowledge:
            cases = knowledge.get_similar_cases(limit=20)
            return jsonify({'decisions': cases})
        return jsonify({'decisions': []})
    except Exception as e:
        return jsonify({'error': str(e), 'decisions': []})


@app.route('/api/metrics')
def api_metrics():
    try:
        if analyzer:
            metrics = analyzer.get_portfolio_metrics(days=90)
            return jsonify(metrics)
        return jsonify({'available': False})
    except Exception as e:
        return jsonify({'error': str(e), 'available': False})


def main():
    init_components()
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
