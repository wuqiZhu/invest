# -*- coding: utf-8 -*-
"""
基金数据库模块

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class FundDatabase:
    """基金数据库类"""
    
    def __init__(self, db_path="fund_data.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_database(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # 创建基金基本信息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fund_info (
            fund_code TEXT PRIMARY KEY,
            fund_name TEXT,
            fund_type TEXT,
            establish_date TEXT,
            manager TEXT,
            company TEXT,
            update_time TEXT
        )
        ''')
        
        # 创建基金净值表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fund_nav (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT,
            nav_date TEXT,
            unit_nav REAL,
            total_nav REAL,
            daily_return REAL,
            update_time TEXT,
            FOREIGN KEY (fund_code) REFERENCES fund_info (fund_code)
        )
        ''')
        
        # 创建定投记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS invest_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT,
            invest_date TEXT,
            amount REAL,
            nav REAL,
            shares REAL,
            total_shares REAL,
            total_invested REAL,
            current_value REAL,
            profit REAL,
            profit_rate REAL,
            update_time TEXT,
            FOREIGN KEY (fund_code) REFERENCES fund_info (fund_code)
        )
        ''')
        
        # 创建分析结果表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fund_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT,
            analysis_date TEXT,
            total_return REAL,
            annualized_return REAL,
            max_drawdown REAL,
            volatility REAL,
            sharpe_ratio REAL,
            monthly_return REAL,
            update_time TEXT,
            FOREIGN KEY (fund_code) REFERENCES fund_info (fund_code)
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nav_fund_code ON fund_nav(fund_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nav_date ON fund_nav(nav_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invest_fund_code ON invest_records(fund_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_fund_code ON fund_analysis(fund_code)')
        
        # 复合索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fund_nav_code_date ON fund_nav(fund_code, nav_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fund_analysis_code_date ON fund_analysis(fund_code, analysis_date)')
        
        # 投资日志表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            fund_code TEXT,
            action TEXT,
            amount REAL,
            nav REAL,
            reason TEXT,
            emotion TEXT,
            reflection TEXT,
            update_time TEXT
        )
        ''')

        # 新闻情绪表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT,
            date TEXT,
            sentiment_score REAL,
            finance_score REAL,
            positive_count INTEGER,
            negative_count INTEGER,
            neutral_count INTEGER,
            total_count INTEGER,
            top_keywords TEXT,
            source TEXT,
            ai_summary TEXT,
            update_time TEXT
        )
        ''')
        
        self.conn.commit()
    
    def save_fund_info(self, fund_info):
        """保存基金基本信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO fund_info 
        (fund_code, fund_name, fund_type, establish_date, manager, company, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            fund_info.get('基金代码', ''),
            fund_info.get('基金名称', ''),
            fund_info.get('基金类型', ''),
            fund_info.get('成立日期', ''),
            fund_info.get('基金经理', ''),
            fund_info.get('基金公司', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
    
    def save_fund_nav(self, fund_code, nav_data):
        """保存基金净值数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for date, row in nav_data.iterrows():
            cursor.execute('''
            INSERT OR REPLACE INTO fund_nav 
            (fund_code, nav_date, unit_nav, total_nav, daily_return, update_time)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                fund_code,
                date.strftime('%Y-%m-%d'),
                row['单位净值'],
                row['累计净值'],
                row.get('日增长率', 0),
                update_time
            ))
        
        conn.commit()
        conn.close()
    
    def save_analysis_result(self, fund_code, analysis):
        """保存分析结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO fund_analysis 
        (fund_code, analysis_date, total_return, annualized_return, max_drawdown, 
         volatility, sharpe_ratio, monthly_return, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fund_code,
            datetime.now().strftime('%Y-%m-%d'),
            analysis.get('总收益率', 0),
            analysis.get('年化收益率', 0),
            analysis.get('最大回撤', 0),
            analysis.get('波动率', 0),
            analysis.get('夏普比率', 0),
            analysis.get('月均收益率', 0),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
    
    def save_invest_record(self, invest_record):
        """保存定投记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO invest_records 
        (fund_code, invest_date, amount, nav, shares, total_shares, 
         total_invested, current_value, profit, profit_rate, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invest_record.get('fund_code', ''),
            invest_record.get('invest_date', ''),
            invest_record.get('amount', 0),
            invest_record.get('nav', 0),
            invest_record.get('shares', 0),
            invest_record.get('total_shares', 0),
            invest_record.get('total_invested', 0),
            invest_record.get('current_value', 0),
            invest_record.get('profit', 0),
            invest_record.get('profit_rate', 0),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
    
    def get_fund_nav(self, fund_code, start_date=None, end_date=None):
        """获取基金净值数据"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT nav_date, unit_nav, total_nav, daily_return FROM fund_nav WHERE fund_code = ?"
        params = [fund_code]
        
        if start_date:
            query += " AND nav_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND nav_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY nav_date"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['nav_date'] = pd.to_datetime(df['nav_date'])
            df = df.set_index('nav_date')
            df = df.rename(columns={
                'unit_nav': '单位净值',
                'total_nav': '累计净值',
                'daily_return': '日增长率'
            })
        
        return df
    
    def get_fund_list(self):
        """获取基金列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT fund_code, fund_name FROM fund_info")
        funds = cursor.fetchall()
        
        conn.close()
        return funds
    
    def get_invest_records(self, fund_code=None):
        """获取定投记录"""
        conn = sqlite3.connect(self.db_path)
        
        if fund_code:
            query = "SELECT * FROM invest_records WHERE fund_code = ? ORDER BY invest_date"
            df = pd.read_sql_query(query, conn, params=[fund_code])
        else:
            query = "SELECT * FROM invest_records ORDER BY invest_date"
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        return df
    
    def get_analysis_history(self, fund_code):
        """获取分析历史"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM fund_analysis WHERE fund_code = ? ORDER BY analysis_date"
        df = pd.read_sql_query(query, conn, params=[fund_code])
        
        conn.close()
        return df
    
    def get_fund_summary(self):
        """获取基金摘要信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            f.fund_code,
            f.fund_name,
            COUNT(n.id) as nav_count,
            MIN(n.nav_date) as start_date,
            MAX(n.nav_date) as end_date,
            MAX(n.unit_nav) as latest_nav,
            a.total_return,
            a.annualized_return,
            a.max_drawdown
        FROM fund_info f
        LEFT JOIN fund_nav n ON f.fund_code = n.fund_code
        LEFT JOIN fund_analysis a ON f.fund_code = a.fund_code
        GROUP BY f.fund_code
        '''
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        columns = ['基金代码', '基金名称', '数据条数', '开始日期', '结束日期', 
                   '最新净值', '总收益率', '年化收益率', '最大回撤']
        
        df = pd.DataFrame(results, columns=columns)
        
        conn.close()
        return df
    
    def export_to_csv(self, fund_code, output_path):
        """导出基金数据到CSV"""
        nav_data = self.get_fund_nav(fund_code)
        if not nav_data.empty:
            nav_data.to_csv(output_path, encoding='utf-8-sig')
            print(f"数据已导出到: {output_path}")
        else:
            print(f"基金 {fund_code} 没有数据")
    
    def cleanup_old_data(self, retention_days=1095):
        """清理旧数据（默认保留3年）"""
        cursor = self.conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime('%Y-%m-%d')
        cursor.execute("DELETE FROM fund_nav WHERE nav_date < ?", (cutoff_date,))
        cursor.execute("DELETE FROM fund_analysis WHERE analysis_date < ?", (cutoff_date,))
        deleted_nav = cursor.rowcount
        self.conn.commit()
        print(f"已清理 {cutoff_date} 之前的数据")
        return deleted_nav
    
    def add_journal_entry(self, fund_code, action, amount, nav, reason, emotion, reflection=""):
        """添加投资日志条目"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO journal (date, fund_code, action, amount, nav, reason, emotion, reflection, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            fund_code, action, amount, nav, reason, emotion, reflection,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        self.conn.commit()
    
    def get_journal_entries(self, fund_code=None, limit=20):
        """获取投资日志条目"""
        cursor = self.conn.cursor()
        if fund_code:
            cursor.execute("SELECT * FROM journal WHERE fund_code=? ORDER BY date DESC LIMIT ?",
                           (fund_code, limit))
        else:
            cursor.execute("SELECT * FROM journal ORDER BY date DESC LIMIT ?", (limit,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def review_month(self, year, month):
        """月度复盘"""
        cursor = self.conn.cursor()
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
        cursor.execute('''
        SELECT action, COUNT(*) as count, SUM(amount) as total_amount
        FROM journal WHERE date BETWEEN ? AND ? GROUP BY action
        ''', (start_date, end_date))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_last_trade(self, fund_code, action=None):
        """获取最近一次交易记录"""
        cursor = self.conn.cursor()
        if action:
            cursor.execute(
                "SELECT * FROM journal WHERE fund_code=? AND action=? ORDER BY date DESC LIMIT 1",
                (fund_code, action))
        else:
            cursor.execute(
                "SELECT * FROM journal WHERE fund_code=? ORDER BY date DESC LIMIT 1",
                (fund_code,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None
    
    def get_monthly_trade_count(self, fund_code=None):
        """获取本月交易次数"""
        cursor = self.conn.cursor()
        now = datetime.now()
        start_date = f"{now.year}-{now.month:02d}-01"
        if fund_code:
            cursor.execute(
                "SELECT COUNT(*) FROM journal WHERE fund_code=? AND date>=?",
                (fund_code, start_date))
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM journal WHERE date>=?", (start_date,))
        return cursor.fetchone()[0]
    
    def get_timeline(self, fund_code=None, days=30):
        """
        获取时间线视图
        
        Args:
            fund_code: 基金代码（可选）
            days: 查询天数
        
        Returns:
            list: 时间线事件列表
        """
        cursor = self.conn.cursor()
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        events = []
        
        # 查询journal表
        if fund_code:
            cursor.execute(
                "SELECT date, fund_code, action, amount, nav, reason, emotion FROM journal WHERE fund_code=? AND date>=? ORDER BY date DESC",
                (fund_code, start_date))
        else:
            cursor.execute(
                "SELECT date, fund_code, action, amount, nav, reason, emotion FROM journal WHERE date>=? ORDER BY date DESC",
                (start_date,))
        
        for row in cursor.fetchall():
            date, code, action, amount, nav, reason, emotion = row
            action_text = {'buy': '买入', 'sell': '卖出', 'hold': '持有'}.get(action, action)
            events.append({
                'date': date,
                'type': '操作',
                'detail': f"{action_text} {code} {amount}元 净值{nav:.4f}",
                'reason': reason,
                'emotion': emotion
            })
        
        # 查询invest_records表
        if fund_code:
            cursor.execute(
                "SELECT invest_date, fund_code, amount, nav, profit_rate FROM invest_records WHERE fund_code=? AND invest_date>=? ORDER BY invest_date DESC",
                (fund_code, start_date))
        else:
            cursor.execute(
                "SELECT invest_date, fund_code, amount, nav, profit_rate FROM invest_records WHERE invest_date>=? ORDER BY invest_date DESC",
                (start_date,))
        
        for row in cursor.fetchall():
            date, code, amount, nav, profit_rate = row
            events.append({
                'date': date,
                'type': '定投',
                'detail': f"定投 {code} {amount}元 净值{nav:.4f} 收益率{profit_rate:.2f}%",
                'reason': '',
                'emotion': ''
            })
        
        # 按日期排序
        events.sort(key=lambda x: x['date'], reverse=True)
        
        return events

    def save_news_sentiment(self, fund_code, date, sentiment_score, finance_score,
                            positive_count, negative_count, neutral_count,
                            total_count, top_keywords='', source='', ai_summary=None):
        """保存新闻情绪数据"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO news_sentiment
        (fund_code, date, sentiment_score, finance_score, positive_count,
         negative_count, neutral_count, total_count, top_keywords, source, ai_summary, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fund_code, date, sentiment_score, finance_score,
            positive_count, negative_count, neutral_count,
            total_count, top_keywords, source, ai_summary,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        self.conn.commit()

    def get_latest_sentiment(self, fund_code=None):
        """获取最新情绪数据"""
        cursor = self.conn.cursor()
        if fund_code:
            cursor.execute(
                "SELECT * FROM news_sentiment WHERE fund_code=? ORDER BY update_time DESC LIMIT 1",
                (fund_code,))
        else:
            cursor.execute(
                "SELECT * FROM news_sentiment ORDER BY update_time DESC LIMIT 1")

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def get_sentiment_summary(self, days=7):
        """获取情绪摘要"""
        cursor = self.conn.cursor()
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT
                AVG(sentiment_score) as avg_sentiment,
                AVG(finance_score) as avg_finance,
                SUM(positive_count) as total_positive,
                SUM(negative_count) as total_negative,
                SUM(neutral_count) as total_neutral,
                SUM(total_count) as total_news,
                COUNT(*) as data_points
            FROM news_sentiment
            WHERE date >= ?
        ''', (start_date,))

        columns = ['avg_sentiment', 'avg_finance', 'total_positive',
                    'total_negative', 'total_neutral', 'total_news', 'data_points']
        row = cursor.fetchone()

        if row and row[0] is not None:
            result = dict(zip(columns, row))
            result['avg_sentiment'] = round(result['avg_sentiment'], 4)
            result['avg_finance'] = round(result['avg_finance'], 4)
            result['days'] = days
            return result

        return {
            'avg_sentiment': 0, 'avg_finance': 0,
            'total_positive': 0, 'total_negative': 0,
            'total_neutral': 0, 'total_news': 0,
            'data_points': 0, 'days': days
        }

    def get_recent_sentiment(self, fund_code=None, days=3):
        """获取最近几天的情绪数据列表"""
        cursor = self.conn.cursor()
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        if fund_code:
            cursor.execute('''
                SELECT date, sentiment_score, finance_score, total_count, top_keywords
                FROM news_sentiment
                WHERE fund_code = ? AND date >= ?
                ORDER BY date DESC
            ''', (fund_code, start_date))
        else:
            cursor.execute('''
                SELECT date, sentiment_score, finance_score, total_count, top_keywords
                FROM news_sentiment
                WHERE date >= ?
                ORDER BY date DESC
            ''', (start_date,))

        columns = ['date', 'sentiment_score', 'finance_score', 'total_count', 'top_keywords']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


# 使用示例
if __name__ == "__main__":
    db = FundDatabase()
    
    # 测试数据库
    print("数据库初始化成功")
    
    # 获取基金列表
    funds = db.get_fund_list()
    print(f"基金数量: {len(funds)}")
    
    # 获取基金摘要
    summary = db.get_fund_summary()
    print("\n基金摘要:")
    print(summary)