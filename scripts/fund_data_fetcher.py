# -*- coding: utf-8 -*-
"""
基金数据获取模块

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import re

class FundDataFetcher:
    """基金数据获取类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_fund_nav(self, fund_code, start_date=None, end_date=None, max_retries=3, per_page=40):
        """
        获取基金净值数据
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期，默认为1年前
            end_date: 结束日期，默认为今天
            max_retries: 最大重试次数
            per_page: 每页数据量
        
        Returns:
            DataFrame: 基金净值数据
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        for attempt in range(max_retries):
            try:
                url = f"https://fund.eastmoney.com/f10/F10DataApi.aspx"
                params = {
                    'type': 'lsjz',
                    'code': fund_code,
                    'page': 1,
                    'sdate': start_date,
                    'edate': end_date,
                    'per': per_page
                }
                
                timeout = 15 + attempt * 5
                response = self.session.get(url, params=params, timeout=timeout)
                response.encoding = 'utf-8'
                
                data = response.text
                
                records = []
                
                pattern = r'<td[^>]*>(.*?)</td>'
                matches = re.findall(pattern, data)
                
                if len(matches) >= 4:
                    for i in range(0, len(matches), 7):
                        if i + 3 < len(matches):
                            try:
                                date_str = matches[i].strip()
                                if not re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                                    continue
                                unit_nav = float(matches[i+1].strip())
                                total_nav = float(matches[i+2].strip())
                                daily_return_str = matches[i+3].strip().replace('%', '')
                                daily_return = float(daily_return_str) if daily_return_str else 0
                                
                                records.append({
                                    '日期': date_str,
                                    '单位净值': unit_nav,
                                    '累计净值': total_nav,
                                    '日增长率': daily_return
                                })
                            except (ValueError, IndexError):
                                continue
                
                if records:
                    df = pd.DataFrame(records)
                    df['日期'] = pd.to_datetime(df['日期'])
                    df = df.set_index('日期')
                    df = df.sort_index()
                    return df
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return self._get_fund_nav_backup(fund_code, start_date, end_date)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                print(f"获取基金 {fund_code} 数据失败: {e}")
                return self._get_fund_nav_backup(fund_code, start_date, end_date)
    
    def _get_fund_nav_backup(self, fund_code, start_date, end_date):
        """备用数据获取方案"""
        try:
            # 使用基金净值查询接口
            url = f"https://api.fund.eastmoney.com/f10/lsjz"
            params = {
                'fundCode': fund_code,
                'pageIndex': 1,
                'pageSize': 1000,
                'startDate': start_date,
                'endDate': end_date,
                '_': int(time.time() * 1000)
            }
            
            headers = {
                **self.headers,
                'Referer': f'https://fundf10.eastmoney.com/jjjz_{fund_code}.html'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('Data') and data['Data'].get('LSJZList'):
                        records = []
                        for item in data['Data']['LSJZList']:
                            records.append({
                                '日期': item['FSRQ'],
                                '单位净值': float(item['DWJZ']),
                                '累计净值': float(item['LJJZ']),
                                '日增长率': float(item['JZZZL']) if item['JZZZL'] else 0
                            })
                        
                        if records:
                            df = pd.DataFrame(records)
                            df['日期'] = pd.to_datetime(df['日期'])
                            df = df.set_index('日期')
                            df = df.sort_index()
                            return df
                except json.JSONDecodeError:
                    pass
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"备用接口也失败: {e}")
            return pd.DataFrame()
    
    def get_fund_info(self, fund_code):
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
        
        Returns:
            dict: 基金信息
        """
        try:
            url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            text = response.text.strip()
            
            json_match = re.search(r'jsonpgz\((.*)\)', text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1).strip()
                if json_str.endswith(';'):
                    json_str = json_str[:-1]
                
                data = json.loads(json_str)
                
                return {
                    '基金代码': data.get('fundcode', ''),
                    '基金名称': data.get('name', ''),
                    '净值日期': data.get('jzrq', ''),
                    '单位净值': float(data.get('dwjz', 0)),
                    '估算净值': float(data.get('gsz', 0)),
                    '估算涨跌幅': float(data.get('gszzl', 0))
                }
            
            return {}
            
        except Exception as e:
            print(f"获取基金 {fund_code} 信息失败: {e}")
            return {}
    
    def get_fund_holding(self, fund_code):
        """
        获取基金重仓股信息
        
        Args:
            fund_code: 基金代码
        
        Returns:
            list: 重仓股列表
        """
        try:
            url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
            params = {
                'type': 'jjcc',
                'code': fund_code,
                'topline': 10,
                'year': '',
                'month': '',
                'rt': str(time.time())
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.encoding = 'utf-8'
            
            # 解析重仓股数据
            data = response.text
            
            # 提取股票信息
            stocks = []
            pattern = r'<td><a[^>]*>(.*?)</a></td>'
            matches = re.findall(pattern, data)
            
            # 每6个元素为一行：序号、股票代码、股票名称、占净值比例、持仓股数、持仓市值
            for i in range(0, len(matches), 6):
                if i + 5 < len(matches):
                    try:
                        stock = {
                            '序号': matches[i].strip(),
                            '股票代码': matches[i+1].strip(),
                            '股票名称': matches[i+2].strip(),
                            '占净值比例': matches[i+3].strip(),
                            '持仓股数': matches[i+4].strip(),
                            '持仓市值': matches[i+5].strip()
                        }
                        stocks.append(stock)
                    except IndexError:
                        continue
            
            return stocks[:10]  # 返回前10大重仓股
            
        except Exception as e:
            print(f"获取基金 {fund_code} 重仓股失败: {e}")
            return []
    
    def get_multiple_funds(self, fund_codes, start_date=None, end_date=None):
        """
        批量获取多只基金数据
        
        Args:
            fund_codes: 基金代码列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            dict: 基金数据字典
        """
        funds_data = {}
        for code in fund_codes:
            print(f"正在获取基金 {code} 数据...")
            funds_data[code] = self.get_fund_nav(code, start_date, end_date)
            time.sleep(1)  # 避免请求过快
        
        return funds_data


# 使用示例
if __name__ == "__main__":
    fetcher = FundDataFetcher()
    
    # 获取单只基金数据
    fund_code = "110011"
    print(f"获取基金 {fund_code} 数据...")
    
    fund_data = fetcher.get_fund_nav(fund_code)
    if not fund_data.empty:
        print(f"成功获取 {len(fund_data)} 条记录")
        print(f"最新日期: {fund_data.index[-1]}")
        print(f"最新净值: {fund_data['单位净值'].iloc[-1]}")
        print(f"数据范围: {fund_data.index[0]} 到 {fund_data.index[-1]}")
        
        # 显示前5条数据
        print("\n前5条数据:")
        print(fund_data.head())
    else:
        print("获取数据失败")
    
    # 获取基金实时信息
    print(f"\n获取基金 {fund_code} 实时信息...")
    fund_info = fetcher.get_fund_info(fund_code)
    if fund_info:
        print(f"基金名称: {fund_info.get('基金名称', '')}")
        print(f"估算净值: {fund_info.get('估算净值', 0)}")
        print(f"估算涨跌幅: {fund_info.get('估算涨跌幅', 0)}%")