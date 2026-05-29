#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web仪表盘 - 投资组合可视化
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
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"组件导入失败: {e}")
    COMPONENTS_AVAILABLE = False

app = Flask(__name__)

executor = None
decider = None
backtester = None
knowledge = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>投资决策助手 - 仪表盘</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card h3 {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        
        .stat-value.positive {
            color: #10b981;
        }
        
        .stat-value.negative {
            color: #ef4444;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 1200px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .fund-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        
        .fund-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }
        
        .fund-card.warning {
            border-left-color: #f59e0b;
        }
        
        .fund-card.danger {
            border-left-color: #ef4444;
        }
        
        .fund-card h4 {
            color: #333;
            margin-bottom: 10px;
            font-size: 1em;
        }
        
        .fund-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 0.9em;
        }
        
        .fund-info .label {
            color: #666;
        }
        
        .fund-info .value {
            text-align: right;
            font-weight: 600;
        }
        
        .profit-positive {
            color: #10b981;
        }
        
        .profit-negative {
            color: #ef4444;
        }
        
        .decision-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .decision-item {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .decision-item:last-child {
            border-bottom: none;
        }
        
        .decision-action {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .decision-action.buy {
            background: #d1fae5;
            color: #065f46;
        }
        
        .decision-action.sell {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .decision-action.hold {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .decision-meta {
            text-align: right;
            font-size: 0.85em;
            color: #666;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.3s ease;
        }
        
        .refresh-btn:hover {
            background: #5a6fd6;
        }
        
        .timestamp {
            text-align: center;
            color: rgba(255,255,255,0.7);
            margin-top: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 智能投资决策助手</h1>
            <p>实时监控 · 智能决策 · 风险控制</p>
            <button class="refresh-btn" onclick="refreshData()" style="margin-top: 15px;">
                🔄 刷新数据
            </button>
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
        
        <div class="main-content">
            <div class="left-column">
                <div class="card">
                    <h2>📊 持仓详情</h2>
                    <div class="fund-grid" id="fund-grid">
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>加载基金数据...</p>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>📈 回测结果</h2>
                    <div id="backtest-results">
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>加载回测数据...</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="right-column">
                <div class="card">
                    <h2>🎯 最新决策</h2>
                    <div class="decision-list" id="decision-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>加载决策数据...</p>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>⚡ 快速操作</h2>
                    <div style="display: grid; gap: 10px;">
                        <button onclick="generateReport()" style="
                            background: #10b981;
                            color: white;
                            border: none;
                            padding: 12px;
                            border-radius: 8px;
                            cursor: pointer;
                        ">📄 生成日报</button>
                        
                        <button onclick="runBacktest()" style="
                            background: #f59e0b;
                            color: white;
                            border: none;
                            padding: 12px;
                            border-radius: 8px;
                            cursor: pointer;
                        ">🔬 运行回测</button>
                        
                        <button onclick="checkRisk()" style="
                            background: #ef4444;
                            color: white;
                            border: none;
                            padding: 12px;
                            border-radius: 8px;
                            cursor: pointer;
                        ">⚠️ 风险检查</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="timestamp" id="update-time">
            数据加载中...
        </div>
    </div>
    
    <script>
        let portfolioData = null;
        
        async function fetchPortfolio() {
            try {
                const response = await fetch('/api/portfolio');
                const data = await response.json();
                portfolioData = data;
                updateStats(data);
                updateFundGrid(data);
            } catch (error) {
                console.error('获取投资组合失败:', error);
            }
        }
        
        async function fetchDecisions() {
            try {
                const response = await fetch('/api/decisions');
                const data = await response.json();
                updateDecisions(data);
            } catch (error) {
                console.error('获取决策失败:', error);
            }
        }
        
        async function fetchBacktest() {
            try {
                const response = await fetch('/api/backtest');
                const data = await response.json();
                updateBacktest(data);
            } catch (error) {
                console.error('获取回测失败:', error);
            }
        }
        
        function updateStats(data) {
            if (data.error) {
                document.getElementById('total-assets').textContent = '错误';
                return;
            }
            
            const holdings = data.holdings || [];
            let totalAssets = 0;
            let totalProfit = 0;
            
            holdings.forEach(h => {
                const marketValue = h.shares * h.current_nav;
                const costValue = h.shares * h.avg_cost;
                totalAssets += marketValue;
                totalProfit += (marketValue - costValue);
            });
            
            const profitRate = totalAssets > 0 ? (totalProfit / (totalAssets - totalProfit) * 100) : 0;
            
            document.getElementById('total-assets').textContent = 
                '¥' + totalAssets.toFixed(2);
            
            const profitEl = document.getElementById('total-profit');
            profitEl.textContent = (totalProfit >= 0 ? '+' : '') + '¥' + totalProfit.toFixed(2);
            profitEl.className = 'stat-value ' + (totalProfit >= 0 ? 'positive' : 'negative');
            
            const rateEl = document.getElementById('profit-rate');
            rateEl.textContent = (profitRate >= 0 ? '+' : '') + profitRate.toFixed(2) + '%';
            rateEl.className = 'stat-value ' + (profitRate >= 0 ? 'positive' : 'negative');
            
            document.getElementById('fund-count').textContent = holdings.length + '只';
        }
        
        function updateFundGrid(data) {
            const grid = document.getElementById('fund-grid');
            const holdings = data.holdings || [];
            
            if (holdings.length === 0) {
                grid.innerHTML = '<p style="text-align:center;color:#666;">暂无持仓数据</p>';
                return;
            }
            
            let html = '';
            holdings.forEach(h => {
                const marketValue = h.shares * h.current_nav;
                const profit = marketValue - (h.shares * h.avg_cost);
                const profitRate = (profit / (h.shares * h.avg_cost) * 100);
                
                let cardClass = 'fund-card';
                if (profitRate <= -10) cardClass += ' danger';
                else if (profitRate <= -5) cardClass += ' warning';
                
                html += `
                    <div class="${cardClass}">
                        <h4>${h.fund_code} ${h.fund_name || ''}</h4>
                        <div class="fund-info">
                            <span class="label">当前净值:</span>
                            <span class="value">${h.current_nav ? h.current_nav.toFixed(4) : '-'}</span>
                            
                            <span class="label">持仓份额:</span>
                            <span class="value">${h.shares.toFixed(2)}</span>
                            
                            <span class="label">持仓成本:</span>
                            <span class="value">¥${(h.shares * h.avg_cost).toFixed(2)}</span>
                            
                            <span class="label">市值:</span>
                            <span class="value">¥${marketValue.toFixed(2)}</span>
                            
                            <span class="label">盈亏:</span>
                            <span class="value ${profit >= 0 ? 'profit-positive' : 'profit-negative'}">
                                ${profit >= 0 ? '+' : ''}¥${profit.toFixed(2)} (${profitRate >= 0 ? '+' : ''}${profitRate.toFixed(2)}%)
                            </span>
                        </div>
                    </div>
                `;
            });
            
            grid.innerHTML = html;
        }
        
        function updateDecisions(data) {
            const list = document.getElementById('decision-list');
            const decisions = data.decisions || [];
            
            if (decisions.length === 0) {
                list.innerHTML = '<p style="text-align:center;color:#666;">暂无决策记录</p>';
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
                            <span style="margin-left: 10px; font-weight: 600;">${d.fund_code}</span>
                            <span style="margin-left: 8px; color: #666; font-size: 0.9em;">
                                评分: ${(d.score * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div class="decision-meta">
                            ${d.date || ''}
                        </div>
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }
        
        function updateBacktest(data) {
            const container = document.getElementById('backtest-results');
            
            if (data.error) {
                container.innerHTML = `<p style="text-align:center;color:#666;">${data.error}</p>`;
                return;
            }
            
            const results = data.results || [];
            if (results.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#666;">暂无回测数据</p>';
                return;
            }
            
            let html = '<table style="width:100%;border-collapse:collapse;">';
            html += '<tr style="background:#f8f9fa;"><th style="padding:10px;text-align:left;">基金</th>';
            html += '<th style="padding:10px;text-align:right;">策略收益</th>';
            html += '<th style="padding:10px;text-align:right;">持有收益</th>';
            html += '<th style="padding:10px;text-align:right;">超额</th></tr>';
            
            results.forEach(r => {
                const excess = r.strategy_return - r.hold_return;
                html += `<tr style="border-bottom:1px solid #eee;">
                    <td style="padding:10px;">${r.fund_code}</td>
                    <td style="padding:10px;text-align:right;color:${r.strategy_return >= 0 ? '#10b981' : '#ef4444'}">
                        ${(r.strategy_return * 100).toFixed(2)}%
                    </td>
                    <td style="padding:10px;text-align:right;color:${r.hold_return >= 0 ? '#10b981' : '#ef4444'}">
                        ${(r.hold_return * 100).toFixed(2)}%
                    </td>
                    <td style="padding:10px;text-align:right;color:${excess >= 0 ? '#10b981' : '#ef4444'}">
                        ${excess >= 0 ? '+' : ''}${(excess * 100).toFixed(2)}%
                    </td>
                </tr>`;
            });
            
            html += '</table>';
            container.innerHTML = html;
        }
        
        async function refreshData() {
            await Promise.all([fetchPortfolio(), fetchDecisions(), fetchBacktest()]);
            document.getElementById('update-time').textContent = 
                '最后更新: ' + new Date().toLocaleString('zh-CN');
        }
        
        function generateReport() {
            fetch('/api/generate-report')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('日报已生成并发送到钉钉');
                    } else {
                        alert('生成失败: ' + (data.error || '未知错误'));
                    }
                });
        }
        
        function runBacktest() {
            alert('回测功能正在运行，请稍后刷新查看结果');
            fetch('/api/run-backtest')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        refreshData();
                    }
                });
        }
        
        function checkRisk() {
            fetch('/api/check-risk')
                .then(r => r.json())
                .then(data => {
                    if (data.alerts && data.alerts.length > 0) {
                        alert('风险警告:\n' + data.alerts.join('\n'));
                    } else {
                        alert('当前无风险警告');
                    }
                });
        }
        
        refreshData();
        setInterval(refreshData, 5 * 60 * 1000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/portfolio')
def api_portfolio():
    try:
        if executor:
            portfolio = executor.get_portfolio_summary()
            return jsonify(portfolio)
        return jsonify({'error': '服务未初始化'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/decisions')
def api_decisions():
    try:
        if knowledge:
            decisions = knowledge.get_recent_decisions(limit=20)
            return jsonify({'decisions': decisions})
        return jsonify({'decisions': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/backtest')
def api_backtest():
    try:
        if backtester:
            results = backtester.get_latest_results()
            return jsonify({'results': results})
        return jsonify({'error': '回测模块未加载'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-report')
def api_generate_report():
    try:
        from daily_report import generate_daily_report
        report = generate_daily_report()
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/run-backtest')
def api_run_backtest():
    try:
        from daily_backtest import run_daily_backtest
        run_daily_backtest()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/check-risk')
def api_check_risk():
    try:
        alerts = []
        if executor:
            portfolio = executor.get_portfolio_summary()
            holdings = portfolio.get('holdings', [])
            
            for h in holdings:
                if h.get('profit_rate', 0) <= -15:
                    alerts.append(f"{h['fund_code']}: 亏损 {h['profit_rate']:.2f}%，触发止损警告")
                elif h.get('profit_rate', 0) >= 20:
                    alerts.append(f"{h['fund_code']}: 盈利 {h['profit_rate']:.2f}%，触发止盈提醒")
        
        return jsonify({'alerts': alerts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def init_components():
    global executor, decider, backtester, knowledge
    
    if not COMPONENTS_AVAILABLE:
        print("组件不可用，仪表盘将以只读模式运行")
        return
    
    try:
        config = ConfigManager()
        executor = ExecutionEngine(config)
        decider = DecisionEngine(config)
        backtester = Backtester(config)
        knowledge = KnowledgeManager(config)
        print("组件初始化成功")
    except Exception as e:
        print(f"组件初始化失败: {e}")


if __name__ == '__main__':
    init_components()
    
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    print(f"仪表盘启动在端口 {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
