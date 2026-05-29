# -*- coding: utf-8 -*-
"""
新闻情绪接收 API 服务
接收 TrendRadar 推送的新闻数据，分析情绪并存储

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sentiment_analyzer import SentimentAnalyzer
from fund_database import FundDatabase
from config_manager import ConfigManager


analyzer = SentimentAnalyzer()
db = None
config = None
API_KEY = None


class NewsHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/news-sentiment':
            self._handle_news_sentiment()
        elif parsed.path == '/api/news-sentiment/manual':
            self._handle_manual_input()
        else:
            self._send_json(404, {'error': 'Not Found'})

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == '/api/health':
            self._send_json(200, {'status': 'ok', 'timestamp': datetime.now().isoformat()})

        elif parsed.path == '/api/sentiment/latest':
            self._handle_latest_sentiment(params)

        elif parsed.path == '/api/sentiment/trend':
            self._handle_sentiment_trend(params)

        elif parsed.path == '/api/sentiment/summary':
            self._handle_sentiment_summary(params)

        elif parsed.path == '/api/portfolio':
            self._handle_portfolio(params)

        elif parsed.path == '/api/decisions':
            self._handle_decisions(params)

        elif parsed.path == '/api/stats':
            self._handle_stats(params)

        elif parsed.path == '/':
            self._handle_dashboard()

        else:
            self._send_json(404, {'error': 'Not Found'})

    def _handle_news_sentiment(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_json(400, {'error': 'Empty request body'})
            return

        raw_data = self.rfile.read(content_length)
        try:
            data = json.loads(raw_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json(400, {'error': 'Invalid JSON'})
            return

        api_key = self.headers.get('X-API-Key', '')
        if API_KEY and api_key != API_KEY:
            self._send_json(401, {'error': 'Invalid API key'})
            return

        result = self._process_news(data)
        self._send_json(200, result)

    def _handle_manual_input(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_json(400, {'error': 'Empty request body'})
            return

        raw_data = self.rfile.read(content_length)
        try:
            data = json.loads(raw_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json(400, {'error': 'Invalid JSON'})
            return

        news_items = data.get('news_items', [])
        if not news_items:
            self._send_json(400, {'error': 'No news items provided'})
            return

        result = self._process_news({
            'source': 'manual',
            'report_type': 'manual',
            'news_items': news_items,
            'timestamp': datetime.now().isoformat(),
        })
        self._send_json(200, result)

    def _process_news(self, data):
        news_items = data.get('news_items', [])
        source = data.get('source', 'unknown')
        report_type = data.get('report_type', 'unknown')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        ai_summary = data.get('ai_summary')

        analysis = analyzer.analyze_news(news_items)

        funds = config.get('funds', [])
        fund_codes = [f['code'] for f in funds if f.get('enabled', True)]

        for fund_code in fund_codes:
            db.save_news_sentiment(
                fund_code=fund_code,
                date=timestamp[:10],
                sentiment_score=analysis['sentiment_score'],
                finance_score=analysis['finance_score'],
                positive_count=analysis['positive_count'],
                negative_count=analysis['negative_count'],
                neutral_count=analysis['neutral_count'],
                total_count=analysis['total_count'],
                top_keywords=','.join(analysis['top_keywords']),
                source=source,
                ai_summary=ai_summary,
            )

        if not fund_codes:
            db.save_news_sentiment(
                fund_code='general',
                date=timestamp[:10],
                sentiment_score=analysis['sentiment_score'],
                finance_score=analysis['finance_score'],
                positive_count=analysis['positive_count'],
                negative_count=analysis['negative_count'],
                neutral_count=analysis['neutral_count'],
                total_count=analysis['total_count'],
                top_keywords=','.join(analysis['top_keywords']),
                source=source,
                ai_summary=ai_summary,
            )

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"收到 {analysis['total_count']} 条新闻 "
              f"(财经: {analysis['finance_count']}, "
              f"正面: {analysis['positive_count']}, "
              f"负面: {analysis['negative_count']}, "
              f"情绪分: {analysis['sentiment_score']:.4f})")

        return {
            'status': 'ok',
            'processed': analysis['total_count'],
            'finance_count': analysis['finance_count'],
            'sentiment_score': analysis['sentiment_score'],
            'finance_score': analysis['finance_score'],
            'saved_to_funds': fund_codes or ['general'],
        }

    def _handle_latest_sentiment(self, params):
        fund_code = params.get('fund_code', [None])[0]

        if fund_code:
            result = db.get_latest_sentiment(fund_code)
        else:
            result = db.get_latest_sentiment()

        if result:
            self._send_json(200, result)
        else:
            self._send_json(200, {'message': 'No sentiment data available'})

    def _handle_sentiment_trend(self, params):
        fund_code = params.get('fund_code', [None])[0]
        days = int(params.get('days', [7])[0])

        trend = analyzer.get_sentiment_trend(db.conn, fund_code, days)
        self._send_json(200, {'trend': trend, 'days': days})

    def _handle_sentiment_summary(self, params):
        days = int(params.get('days', [7])[0])
        summary = db.get_sentiment_summary(days)
        self._send_json(200, summary)

    def _handle_portfolio(self, params):
        try:
            from execution_engine import ExecutionEngine
            executor = ExecutionEngine(config)
            portfolio = executor.get_portfolio_summary()
            self._send_json(200, portfolio)
        except Exception as e:
            self._send_json(200, {'holdings': [], 'error': str(e)})

    def _handle_decisions(self, params):
        try:
            from knowledge_manager import KnowledgeManager
            knowledge = KnowledgeManager(config)
            limit = int(params.get('limit', [20])[0])
            decisions = knowledge.get_recent_decisions(limit=limit)
            self._send_json(200, {'decisions': decisions})
        except Exception as e:
            self._send_json(200, {'decisions': [], 'error': str(e)})

    def _handle_stats(self, params):
        try:
            stats = {
                'total_funds': 0,
                'total_assets': 0,
                'total_profit': 0,
                'profit_rate': 0,
                'last_update': datetime.now().isoformat()
            }
            try:
                from execution_engine import ExecutionEngine
                executor = ExecutionEngine(config)
                portfolio = executor.get_portfolio_summary()
                holdings = portfolio.get('holdings', [])
                stats['total_funds'] = len(holdings)
                for h in holdings:
                    market_value = h.get('shares', 0) * h.get('current_nav', 0)
                    cost_value = h.get('shares', 0) * h.get('avg_cost', 0)
                    stats['total_assets'] += market_value
                    stats['total_profit'] += (market_value - cost_value)
                if stats['total_assets'] > 0:
                    stats['profit_rate'] = stats['total_profit'] / (stats['total_assets'] - stats['total_profit']) * 100
            except Exception:
                pass
            self._send_json(200, stats)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_dashboard(self):
        try:
            dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')
            if os.path.exists(dashboard_path):
                with open(dashboard_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self._send_json(404, {'error': 'Dashboard not found'})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")


def run_server(host='0.0.0.0', port=5000, config_path=None):
    global db, config, API_KEY

    config = ConfigManager(config_path)
    db_path = config.get('database.path', 'fund_data.db')
    db = FundDatabase(db_path)
    API_KEY = config.get('news_api.api_key', '')

    server = HTTPServer((host, port), NewsHandler)
    print(f"新闻情绪 API 服务已启动: http://{host}:{port}")
    print(f"API 端点:")
    print(f"  POST /api/news-sentiment        - 接收 TrendRadar 新闻数据")
    print(f"  POST /api/news-sentiment/manual  - 手动输入新闻")
    print(f"  GET  /api/health                 - 健康检查")
    print(f"  GET  /api/sentiment/latest       - 最新情绪数据")
    print(f"  GET  /api/sentiment/trend        - 情绪趋势")
    print(f"  GET  /api/sentiment/summary      - 情绪摘要")
    print(f"按 Ctrl+C 停止服务")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='新闻情绪接收 API 服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--config', help='配置文件路径')

    args = parser.parse_args()
    run_server(args.host, args.port, args.config)
