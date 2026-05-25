# -*- coding: utf-8 -*-
"""
基金数据获取模块（增强版）
支持多数据源备份，提高稳定性

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。

数据来源致谢：
- 天天基金网 (fund.eastmoney.com)
- 新浪财经 (finance.sina.com.cn)
- 腾讯财经 (stockapp.finance.qq.com)

本工具仅供个人学习使用，请勿大规模抓取，尊重数据源权益。
"""

import requests
import requests_cache
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import re
from functools import wraps

requests_cache.install_cache(
    'fund_api_cache',
    expire_after=3600,
    backend='sqlite'
)


def retry_on_failure(max_retries=3, delay=1):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


class FundDataFetcherV2:
    """基金数据获取类（增强版）"""
    
    # 支持的数据源
    SOURCES = ['eastmoney', 'sina', 'tencent', 'akshare']
    
    def __init__(self, primary_source='eastmoney', fallback_enabled=True,
                 request_timeout=15, max_retries=3, request_interval=1):
        """
        初始化数据获取器
        
        Args:
            primary_source: 主数据源
            fallback_enabled: 是否启用备用数据源
            request_timeout: 请求超时时间
            max_retries: 最大重试次数
            request_interval: 请求间隔
        """
        self.primary_source = primary_source
        self.fallback_enabled = fallback_enabled
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.request_interval = request_interval
        
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
    
    def get_fund_nav(self, fund_code, start_date=None, end_date=None):
        """
        获取基金净值数据（带降级策略）
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 基金净值数据
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 尝试主数据源
        try:
            result = self._get_from_source(self.primary_source, fund_code, start_date, end_date)
            if result is not None and not result.empty and self._validate_nav_data(result):
                return result
        except Exception as e:
            print(f"主数据源 {self.primary_source} 失败: {e}")
        
        # 如果启用备用数据源，依次尝试
        if self.fallback_enabled:
            for source in self.SOURCES:
                if source == self.primary_source:
                    continue
                try:
                    print(f"尝试备用数据源: {source}")
                    result = self._get_from_source(source, fund_code, start_date, end_date)
                    if result is not None and not result.empty and self._validate_nav_data(result):
                        print(f"备用数据源 {source} 成功")
                        return result
                except Exception as e:
                    print(f"备用数据源 {source} 失败: {e}")
                    continue
        
        print(f"所有数据源均失败")
        return pd.DataFrame()
    
    def _validate_nav_data(self, df):
        """校验净值数据是否有效"""
        if df.empty:
            return False
        latest_date = df.index[-1]
        if (pd.Timestamp.now() - latest_date).days > 5:
            return False
        if (df['单位净值'] <= 0).any():
            return False
        return True
    
    def _get_from_source(self, source, fund_code, start_date, end_date):
        """
        从指定数据源获取数据
        
        Args:
            source: 数据源名称
            fund_code: 基金代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 基金净值数据
        """
        if source == 'eastmoney':
            return self._get_from_eastmoney(fund_code, start_date, end_date)
        elif source == 'sina':
            return self._get_from_sina(fund_code, start_date, end_date)
        elif source == 'tencent':
            return self._get_from_tencent(fund_code, start_date, end_date)
        elif source == 'akshare':
            return self._get_from_akshare(fund_code, start_date, end_date)
        else:
            raise ValueError(f"不支持的数据源: {source}")
    
    def _get_from_akshare(self, fund_code, start_date, end_date):
        """
        从AKShare获取数据（需要Python 3.9+）
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 基金净值数据
        """
        try:
            import akshare as ak
        except ImportError:
            print("AKShare未安装，请运行: pip install akshare")
            print("注意：AKShare需要Python 3.9+")
            return pd.DataFrame()
        
        try:
            df = ak.fund_em_open_fund_daily(fund=fund_code)
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={
                '净值日期': '日期',
                '单位净值': '单位净值',
                '累计净值': '累计净值',
                '日增长率': '日增长率'
            })
            
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            df = df.sort_index()
            
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]
            
            return df
        except Exception as e:
            print(f"AKShare获取数据失败: {e}")
            return pd.DataFrame()
    
    @retry_on_failure(max_retries=3, delay=1)
    def _get_from_eastmoney(self, fund_code, start_date, end_date):
        """从天天基金获取数据"""
        url = "https://fund.eastmoney.com/f10/F10DataApi.aspx"
        all_records = []
        page = 1
        
        while True:
            params = {
                'type': 'lsjz',
                'code': fund_code,
                'page': page,
                'sdate': start_date,
                'edate': end_date,
                'per': 40
            }
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.encoding = 'utf-8'
            
            data = response.text
            records = []
            
            row_pattern = r'<tr>(.*?)</tr>'
            rows = re.findall(row_pattern, data, re.DOTALL)
            
            for row in rows:
                td_pattern = r'<td[^>]*>(.*?)</td>'
                cells = re.findall(td_pattern, row)
                if len(cells) >= 4:
                    try:
                        date_str = cells[0].strip()
                        unit_nav = float(cells[1].strip())
                        total_nav = float(cells[2].strip())
                        daily_return_str = cells[3].strip().replace('%', '')
                        daily_return = float(daily_return_str) if daily_return_str else 0
                        
                        records.append({
                            '日期': date_str,
                            '单位净值': unit_nav,
                            '累计净值': total_nav,
                            '日增长率': daily_return
                        })
                    except (ValueError, IndexError):
                        continue
            
            if not records:
                break
            
            all_records.extend(records)
            
            if '下一页' not in data or len(records) < 40:
                break
            
            page += 1
            if page > 10:
                break
        
        if all_records:
            df = pd.DataFrame(all_records)
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            df = df.sort_index()
            df = df[~df.index.duplicated(keep='first')]
            return df
        
        return pd.DataFrame()
    
    @retry_on_failure(max_retries=3, delay=1)
    def _get_from_sina(self, fund_code, start_date, end_date):
        """从新浪财经获取数据"""
        # 新浪基金净值接口
        url = f"https://hq.sinajs.cn/list=f_{fund_code}"
        
        headers = {
            **self.headers,
            'Referer': 'https://finance.sina.com.cn'
        }
        
        response = self.session.get(url, headers=headers, timeout=self.request_timeout)
        response.encoding = 'gbk'
        
        # 解析新浪格式数据
        # 格式: var hq_str_f_基金代码="基金名称,净值日期,单位净值,累计净值,前日单位净值,前日累计净值,..."
        text = response.text
        
        match = re.search(r'"(.*?)"', text)
        if match:
            parts = match.group(1).split(',')
            if len(parts) >= 4:
                fund_name = parts[0]
                nav_date = parts[1]
                unit_nav = float(parts[2])
                total_nav = float(parts[3])
                
                # 创建单条记录的DataFrame
                df = pd.DataFrame({
                    '日期': [nav_date],
                    '单位净值': [unit_nav],
                    '累计净值': [total_nav],
                    '日增长率': [0]
                })
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.set_index('日期')
                return df
        
        return pd.DataFrame()
    
    @retry_on_failure(max_retries=3, delay=1)
    def _get_from_tencent(self, fund_code, start_date, end_date):
        """从腾讯财经获取数据"""
        # 腾讯基金接口
        url = f"https://qt.gtimg.cn/q=f_{fund_code}"
        
        headers = {
            **self.headers,
            'Referer': 'https://gu.qq.com'
        }
        
        response = self.session.get(url, headers=headers, timeout=self.request_timeout)
        response.encoding = 'gbk'
        
        # 解析腾讯格式数据
        text = response.text
        
        match = re.search(r'"(.*?)"', text)
        if match:
            parts = match.group(1).split('~')
            if len(parts) >= 10:
                fund_name = parts[1]
                nav_date = parts[6]
                unit_nav = float(parts[4])
                total_nav = float(parts[5])
                daily_return = float(parts[8]) if parts[8] else 0
                
                df = pd.DataFrame({
                    '日期': [nav_date],
                    '单位净值': [unit_nav],
                    '累计净值': [total_nav],
                    '日增长率': [daily_return]
                })
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.set_index('日期')
                return df
        
        return pd.DataFrame()
    
    def get_fund_info(self, fund_code):
        """
        获取基金实时信息
        
        Args:
            fund_code: 基金代码
        
        Returns:
            dict: 基金信息
        """
        try:
            url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = self.session.get(url, timeout=self.request_timeout)
            
            text = response.text
            json_match = re.search(r'jsonpgz\((.*?)\)', text)
            
            if json_match:
                json_str = json_match.group(1)
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
            time.sleep(self.request_interval)
        
        return funds_data


# 使用示例
if __name__ == "__main__":
    fetcher = FundDataFetcherV2(primary_source='eastmoney', fallback_enabled=True)
    
    # 获取单只基金数据
    fund_code = "110011"
    print(f"获取基金 {fund_code} 数据...")
    
    fund_data = fetcher.get_fund_nav(fund_code)
    if not fund_data.empty:
        print(f"成功获取 {len(fund_data)} 条记录")
        print(f"最新日期: {fund_data.index[-1]}")
        print(f"最新净值: {fund_data['单位净值'].iloc[-1]}")
    else:
        print("获取数据失败")
    
    # 获取基金实时信息
    print(f"\n获取基金 {fund_code} 实时信息...")
    fund_info = fetcher.get_fund_info(fund_code)
    if fund_info:
        print(f"基金名称: {fund_info.get('基金名称', '')}")
        print(f"估算净值: {fund_info.get('估算净值', 0)}")
        print(f"估算涨跌幅: {fund_info.get('估算涨跌幅', 0)}%")