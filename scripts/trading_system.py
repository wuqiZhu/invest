# -*- coding: utf-8 -*-
"""
模块化交易系统
将交易决策拆分为五个独立模块：趋势、买点、波动、风控、止盈

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import pandas as pd
import numpy as np


class TradingSystem:
    """模块化交易系统"""
    
    def __init__(self, config, analyzer):
        """
        初始化交易系统
        
        Args:
            config: 配置管理器实例
            analyzer: 分析器实例
        """
        self.config = config
        self.analyzer = analyzer
        self.ts_config = config.get('trading_system', {})
    
    def get_signal(self, fund_data, fund_code=""):
        """
        获取交易信号
        
        Args:
            fund_data: 基金净值数据
            fund_code: 基金代码
        
        Returns:
            dict: 包含signal（BUY/SELL/HOLD）和各模块判断结果
        """
        if fund_data.empty or len(fund_data) < 30:
            return {'signal': 'HOLD', 'reason': '数据不足', 'modules': {
                'trend': {'status': 'unknown', 'pass': False, 'detail': '数据不足，无法判断'},
                'volatility': {'status': 'unknown', 'pass': False, 'detail': '数据不足，无法判断'},
                'entry': {'status': 'unknown', 'pass': False, 'detail': '数据不足，无法判断'},
                'risk': {'status': 'unknown', 'pass': True, 'detail': '数据不足，默认通过'},
                'profit': {'status': 'unknown', 'pass': False, 'detail': '数据不足，无法判断'}
            }}
        
        nav_series = fund_data['单位净值']
        latest_nav = nav_series.iloc[-1]
        
        result = {
            'fund_code': fund_code,
            'latest_nav': latest_nav,
            'modules': {}
        }
        
        # 1. 趋势模块
        trend_result = self._check_trend(nav_series)
        result['modules']['trend'] = trend_result
        
        # 2. 波动模块
        volatility_result = self._check_volatility(nav_series)
        result['modules']['volatility'] = volatility_result
        
        # 3. 买点模块
        entry_result = self._check_entry(nav_series)
        result['modules']['entry'] = entry_result
        
        # 4. 风控模块
        risk_result = self._check_risk(nav_series)
        result['modules']['risk'] = risk_result
        
        # 5. 止盈模块
        profit_result = self._check_profit(nav_series)
        result['modules']['profit'] = profit_result

        # 6. 情绪模块（可选，需要新闻数据）
        sentiment_result = self._check_sentiment(fund_code)
        result['modules']['sentiment'] = sentiment_result

        # 综合决策
        result['signal'] = self._make_decision(result)
        
        return result
    
    def _check_trend(self, nav_series):
        """
        趋势模块：判断趋势方向
        
        规则：
        - 上升趋势：净值 > EMA20 > EMA60
        - 下降趋势：净值 < EMA20 < EMA60
        - 中性：其他情况
        """
        ema_short = self.ts_config.get('trend', {}).get('ema_short', 20)
        ema_long = self.ts_config.get('trend', {}).get('ema_long', 60)
        
        ema20 = nav_series.ewm(span=ema_short).mean().iloc[-1]
        ema60 = nav_series.ewm(span=ema_long).mean().iloc[-1]
        latest = nav_series.iloc[-1]
        
        trend_up = (latest > ema20) and (ema20 > ema60)
        trend_down = (latest < ema20) and (ema20 < ema60)
        
        if trend_up:
            return {
                'status': 'up',
                'pass': True,
                'detail': f'净值{latest:.3f} > EMA20({ema20:.3f}) > EMA60({ema60:.3f})'
            }
        elif trend_down:
            return {
                'status': 'down',
                'pass': False,
                'detail': f'净值{latest:.3f} < EMA20({ema20:.3f}) < EMA60({ema60:.3f})'
            }
        else:
            return {
                'status': 'neutral',
                'pass': True,
                'detail': f'趋势中性，净值{latest:.3f}'
            }
    
    def _check_volatility(self, nav_series):
        """
        波动模块：判断波动是否适合交易
        
        规则：
        - 波动太低（<min_volatility）：不适合交易
        - 波动太高（>max_volatility）：需谨慎
        - 适中：适合交易
        """
        period = self.ts_config.get('volatility', {}).get('volatility_period', 60)
        min_vol = self.ts_config.get('volatility', {}).get('min_volatility', 10)
        max_vol = self.ts_config.get('volatility', {}).get('max_volatility', 30)
        
        returns = nav_series.pct_change().dropna()
        if len(returns) < period:
            return {'status': 'unknown', 'pass': True, 'detail': '数据不足'}
        
        volatility = returns.iloc[-period:].std() * np.sqrt(252) * 100
        
        if volatility < min_vol:
            return {
                'status': 'low',
                'pass': False,
                'detail': f'波动率{volatility:.1f}% < {min_vol}%，波动太低'
            }
        elif volatility > max_vol:
            return {
                'status': 'high',
                'pass': True,
                'detail': f'波动率{volatility:.1f}% > {max_vol}%，高波动需谨慎'
            }
        else:
            return {
                'status': 'normal',
                'pass': True,
                'detail': f'波动率{volatility:.1f}%，适合交易'
            }
    
    def _check_entry(self, nav_series):
        """
        买点模块：判断是否出现买点
        
        规则（基金版）：
        - 均线偏离：净值低于EMA20超过阈值
        - MACD金叉：DIF > DEA
        """
        ema20 = nav_series.ewm(span=20).mean().iloc[-1]
        latest = nav_series.iloc[-1]
        deviation = (latest - ema20) / ema20 * 100
        
        threshold = self.ts_config.get('entry', {}).get('deviation_threshold', -5)
        use_macd = self.ts_config.get('entry', {}).get('use_macd_golden_cross', True)
        
        # 均线偏离信号
        deviation_signal = deviation < threshold
        
        # MACD金叉信号
        macd_signal = False
        if use_macd and len(nav_series) >= 26:
            macd_result = self.analyzer._calculate_macd(nav_series)
            dif = macd_result.get('MACD_DIF', 0)
            dea = macd_result.get('MACD_DEA', 0)
            macd_signal = dif > dea
        
        if deviation_signal:
            return {
                'status': 'deviation_buy',
                'pass': True,
                'detail': f'均线偏离{deviation:.1f}% < {threshold}%，超卖买点'
            }
        elif macd_signal:
            return {
                'status': 'macd_buy',
                'pass': True,
                'detail': f'MACD金叉确认'
            }
        else:
            return {
                'status': 'no_signal',
                'pass': False,
                'detail': f'均线偏离{deviation:.1f}%，无明显买点'
            }
    
    def _check_risk(self, nav_series):
        """
        风控模块：检查风险状态
        
        规则（基金版）：
        - 当前回撤超过阈值：暂停定投
        - 否则：风险可控
        """
        max_dd_threshold = self.ts_config.get('risk', {}).get('max_drawdown_pause', 15)
        
        peak = nav_series.expanding(min_periods=1).max()
        drawdown = (nav_series - peak) / peak * 100
        current_drawdown = drawdown.iloc[-1]
        
        if abs(current_drawdown) > max_dd_threshold:
            return {
                'status': 'pause',
                'pass': False,
                'detail': f'当前回撤{current_drawdown:.1f}% > {max_dd_threshold}%，建议暂停定投'
            }
        else:
            return {
                'status': 'normal',
                'pass': True,
                'detail': f'当前回撤{current_drawdown:.1f}%，风险可控'
            }
    
    def _check_profit(self, nav_series):
        """
        止盈模块：检查是否需要止盈
        
        规则：
        - 移动回撤止盈：收益率超过目标且回撤超过阈值
        - 半仓止盈：收益率超过触发阈值
        - 否则：继续持有
        """
        target_return = self.ts_config.get('profit', {}).get('target_return', 20)
        trailing_stop = self.ts_config.get('profit', {}).get('trailing_stop_drawdown', 8)
        half_trigger = self.ts_config.get('profit', {}).get('half_profit_trigger', 15)
        
        # 计算从第一日到现在的收益率
        total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100
        
        # 计算从最高点的回撤
        peak = nav_series.expanding(min_periods=1).max()
        drawdown_from_peak = (nav_series.iloc[-1] - peak.iloc[-1]) / peak.iloc[-1] * 100
        
        if total_return > target_return and drawdown_from_peak < -trailing_stop:
            return {
                'status': 'trailing_stop',
                'pass': True,
                'detail': f'收益率{total_return:.1f}%，从高点回撤{abs(drawdown_from_peak):.1f}%，建议止盈'
            }
        elif total_return > half_trigger:
            return {
                'status': 'half_profit',
                'pass': True,
                'detail': f'收益率{total_return:.1f}% > {half_trigger}%，可考虑赎回一半'
            }
        else:
            return {
                'status': 'hold',
                'pass': False,
                'detail': f'收益率{total_return:.1f}%，继续持有'
            }

    def _check_sentiment(self, fund_code):
        """
        情绪模块：检查市场新闻情绪

        规则：
        - 极度乐观（sentiment > 0.5）：警惕追高风险
        - 极度悲观（sentiment < -0.5）：可能是机会
        - 正常区间：情绪平稳
        """
        try:
            from fund_database import FundDatabase
            db_path = self.config.get('database.path', 'fund_data.db')
            db = FundDatabase(db_path)
            recent = db.get_recent_sentiment(fund_code, days=3)
            db.close()

            if not recent:
                return {
                    'status': 'no_data',
                    'pass': True,
                    'detail': '暂无新闻情绪数据，不影响信号判断'
                }

            latest = recent[0]
            score = latest.get('sentiment_score', 0)
            total = latest.get('total_count', 0)
            keywords = latest.get('top_keywords', '')

            if score > 0.5:
                return {
                    'status': 'euphoria',
                    'pass': False,
                    'detail': f'市场情绪极度乐观({score:.2f})，共{total}条新闻，需警惕追高'
                }
            elif score < -0.5:
                return {
                    'status': 'panic',
                    'pass': True,
                    'detail': f'市场情绪极度悲观({score:.2f})，共{total}条新闻，可能是机会'
                }
            elif score > 0.2:
                return {
                    'status': 'optimistic',
                    'pass': True,
                    'detail': f'市场情绪偏乐观({score:.2f})，共{total}条新闻'
                }
            elif score < -0.2:
                return {
                    'status': 'pessimistic',
                    'pass': True,
                    'detail': f'市场情绪偏悲观({score:.2f})，共{total}条新闻'
                }
            else:
                return {
                    'status': 'neutral',
                    'pass': True,
                    'detail': f'市场情绪平稳({score:.2f})，共{total}条新闻'
                }
        except Exception:
            return {
                'status': 'error',
                'pass': True,
                'detail': '情绪数据获取失败，不影响信号判断'
            }

    def _make_decision(self, result):
        """
        综合决策
        
        优先级：
        1. 止盈信号优先
        2. 风控暂停
        3. 趋势+买点确认
        """
        trend = result['modules']['trend']
        volatility = result['modules']['volatility']
        entry = result['modules']['entry']
        risk = result['modules']['risk']
        profit = result['modules']['profit']
        
        # 止盈优先
        if profit['status'] in ['trailing_stop', 'half_profit']:
            return 'SELL'
        
        # 风控暂停
        if not risk['pass']:
            return 'HOLD'
        
        # 趋势+买点确认
        if trend['pass'] and volatility['pass'] and entry['pass']:
            return 'BUY'
        
        return 'HOLD'
    
    def get_advice(self, result):
        """
        生成操作建议

        Args:
            result: get_signal返回的结果

        Returns:
            str: 操作建议
        """
        signal = result.get('signal', 'HOLD')
        modules = result.get('modules', {})

        trend = modules.get('trend', {})
        volatility = modules.get('volatility', {})
        entry = modules.get('entry', {})
        risk = modules.get('risk', {})
        profit = modules.get('profit', {})
        sentiment = modules.get('sentiment', {})

        sentiment_advice = ''
        if sentiment.get('status') == 'euphoria':
            sentiment_advice = '（市场情绪过热，需谨慎）'
        elif sentiment.get('status') == 'panic':
            sentiment_advice = '（市场恐慌，可能是机会）'

        if signal == 'BUY':
            if entry.get('status') == 'oversold':
                return f"建议将下月定投额提高30%{sentiment_advice}"
            else:
                return f"建议维持当前定投金额{sentiment_advice}"
        elif signal == 'SELL':
            if profit.get('status') == 'trailing_stop':
                return f"建议赎回全部，锁定收益{sentiment_advice}"
            elif profit.get('status') == 'half_profit':
                return f"建议赎回一半，保留一半{sentiment_advice}"
            else:
                return f"建议暂停定投，等待信号{sentiment_advice}"
        else:
            if not risk.get('pass', True):
                return f"建议暂停定投，风险较高{sentiment_advice}"
            elif trend.get('status') == 'down':
                return f"建议维持当前定投金额，等待趋势反转{sentiment_advice}"
            else:
                return f"建议维持当前定投金额{sentiment_advice}"
