# -*- coding: utf-8 -*-
"""
闭环调度器

协调各组件的运行，实现完整的闭环流程：
信息采集 → 分析 → 决策 → 执行 → 反馈 → 学习

使用方式：
    python pipeline_scheduler.py --full    # 运行完整闭环
    python pipeline_scheduler.py --status  # 查看状态
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_manager import ConfigManager
    from decision_engine import DecisionEngine
    from execution_engine import ExecutionEngine
    from knowledge_manager import KnowledgeManager
    LOCAL_IMPORTS = True
except ImportError:
    LOCAL_IMPORTS = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PipelineScheduler:
    """闭环调度器"""

    def __init__(self, config_path: str = None):
        if LOCAL_IMPORTS:
            self.config = ConfigManager(config_path)
            self.decision_engine = DecisionEngine(config_path)
            self.execution_engine = ExecutionEngine(config_path)
            try:
                self.knowledge_manager = KnowledgeManager()
            except Exception:
                self.knowledge_manager = None

        self.notification_url = os.environ.get(
            'NOTIFICATION_CENTER_URL',
            'http://notification-center:5050'
        )

        self.pipeline_status = {
            'last_run': None,
            'last_step': None,
            'errors': [],
            'success_count': 0,
            'failure_count': 0
        }

    def run_full_pipeline(self) -> Dict[str, Any]:
        """运行完整闭环流程"""
        logger.info("=" * 50)
        logger.info("开始运行完整闭环流程")
        logger.info("=" * 50)

        start_time = time.time()
        results = {
            'pipeline_id': f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'start_time': datetime.now().isoformat(),
            'steps': [],
            'status': 'running'
        }

        self.risk_alerts = []

        try:
            # 步骤0: 更新净值
            logger.info("步骤0: 更新基金净值")
            step0_result = self._run_step('净值更新', self._step_update_nav)
            results['steps'].append(step0_result)

            # 步骤1: 信息采集
            logger.info("步骤1: 信息采集")
            step1_result = self._run_step('采集', self._step_collect)
            results['steps'].append(step1_result)

            # 步骤2: 信息分析
            logger.info("步骤2: 信息分析")
            step2_result = self._run_step('分析', self._step_analyze)
            results['steps'].append(step2_result)

            # 步骤3: 止盈止损检查
            logger.info("步骤3: 止盈止损检查")
            step3_result = self._run_step('止盈止损', self._step_check_risk)
            results['steps'].append(step3_result)
            if step3_result.get('data', {}).get('alerts'):
                self.risk_alerts = step3_result['data']['alerts']

            # 步骤4: 决策生成
            logger.info("步骤4: 决策生成")
            step4_result = self._run_step('决策', self._step_decide)
            results['steps'].append(step4_result)

            # 步骤5: 执行交易
            logger.info("步骤5: 执行交易")
            step5_result = self._run_step('执行', self._step_execute)
            results['steps'].append(step5_result)

            # 步骤6: 发送通知
            logger.info("步骤6: 发送通知")
            step6_result = self._run_step('通知', self._step_notify)
            results['steps'].append(step6_result)

            # 步骤7: 回测验证
            logger.info("步骤7: 回测验证")
            step7_result = self._run_step('回测', self._step_backtest)
            results['steps'].append(step7_result)

            results['status'] = 'success'
            self.pipeline_status['success_count'] += 1

        except Exception as e:
            logger.error(f"闭环流程异常: {e}")
            results['status'] = 'error'
            results['error'] = str(e)
            self.pipeline_status['failure_count'] += 1

        finally:
            end_time = time.time()
            results['end_time'] = datetime.now().isoformat()
            results['duration_seconds'] = round(end_time - start_time, 2)
            self.pipeline_status['last_run'] = results['end_time']
            self._save_result(results)
            self._send_completion_notification(results)

        logger.info("=" * 50)
        logger.info(f"闭环流程完成: {results['status']}")
        logger.info("=" * 50)

        return results

    def _run_step(self, step_name: str, step_func) -> Dict[str, Any]:
        """运行单个步骤"""
        start_time = time.time()
        result = {
            'step': step_name,
            'start_time': datetime.now().isoformat(),
            'status': 'running'
        }

        try:
            step_result = step_func()
            result['status'] = 'success'
            result['data'] = step_result
            self.pipeline_status['last_step'] = step_name
            logger.info(f"步骤 {step_name} 完成")
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            self.pipeline_status['errors'].append({
                'step': step_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"步骤 {step_name} 失败: {e}")
        finally:
            end_time = time.time()
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = round(end_time - start_time, 2)

        return result

    def _step_update_nav(self) -> Dict[str, Any]:
        """步骤0: 更新基金净值"""
        logger.info("更新基金净值...")

        try:
            from update_nav import update_fund_nav
            success_count = update_fund_nav()
            return {
                'status': 'success',
                'updated_count': success_count
            }
        except Exception as e:
            logger.error(f"净值更新失败: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def _step_collect(self) -> Dict[str, Any]:
        """步骤1: 信息采集"""
        logger.info("TrendRadar 作为独立服务运行")
        return {
            'status': 'triggered',
            'message': 'TrendRadar 作为独立服务运行'
        }

    def _step_analyze(self) -> Dict[str, Any]:
        """步骤2: 信息分析"""
        logger.info("analyser 作为独立服务运行")
        return {
            'status': 'triggered',
            'message': 'analyser 作为独立服务运行'
        }

    def _step_check_risk(self) -> Dict[str, Any]:
        """步骤3: 止盈止损检查"""
        logger.info("检查止盈止损...")

        if not LOCAL_IMPORTS:
            return {'status': 'skipped', 'message': '依赖不可用'}

        try:
            alerts = self.execution_engine.check_take_profit_stop_loss(
                take_profit=20,
                stop_loss=-10
            )
            
            if alerts:
                logger.info(f"发现 {len(alerts)} 个止盈止损信号")
                for alert in alerts:
                    action = "止盈" if alert['action'] == 'take_profit' else "止损"
                    logger.warning(
                        f"{action}信号: {alert['fund_code']}, "
                        f"盈亏比例: {alert['profit_rate']:.2f}%"
                    )
                return {
                    'status': 'alerts',
                    'alerts': alerts,
                    'count': len(alerts)
                }
            else:
                logger.info("未发现止盈止损信号")
                return {
                    'status': 'safe',
                    'message': '所有基金在安全范围内'
                }
        except Exception as e:
            logger.error(f"止盈止损检查失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _step_decide(self) -> Dict[str, Any]:
        """步骤4: 决策生成"""
        logger.info("生成投资决策...")

        if not LOCAL_IMPORTS:
            return {'status': 'skipped', 'message': '依赖不可用'}

        try:
            analysis_report = {
                'sentiment_score': 0.72,
                'keywords': ['央行降准', '半导体上涨', '消费回暖'],
                'source': 'pipeline_scheduler',
                'timestamp': datetime.now().isoformat()
            }

            risk_alerts = getattr(self, 'risk_alerts', [])
            if risk_alerts:
                logger.info(f"传递 {len(risk_alerts)} 个止盈止损信号到决策引擎")

            decision = self.decision_engine.make_decision(analysis_report, risk_alerts=risk_alerts)
            logger.info(f"决策结果: {decision}")

            if self.knowledge_manager and 'decisions' in decision:
                for d in decision['decisions']:
                    try:
                        self.knowledge_manager.save_decision(d)
                    except Exception as e:
                        logger.warning(f"保存决策到知识库失败: {e}")

            return decision
        except Exception as e:
            logger.error(f"决策生成失败: {e}")
            raise

    def _step_execute(self) -> Dict[str, Any]:
        """步骤5: 执行交易"""
        logger.info("执行交易...")

        if not LOCAL_IMPORTS:
            return {'status': 'skipped', 'message': '依赖不可用'}

        try:
            result = self.execution_engine.process_next_batch()
            if result:
                logger.info(f"执行完成: {result}")
                return result
            else:
                logger.info("没有待执行的批次")
                return {'status': 'no_pending', 'message': '没有待执行的批次'}
        except Exception as e:
            logger.error(f"执行失败: {e}")
            raise

    def _step_notify(self) -> Dict[str, Any]:
        """步骤6: 发送通知"""
        logger.info("发送通知...")

        if not REQUESTS_AVAILABLE:
            return {'status': 'skipped', 'message': 'requests不可用'}

        try:
            if LOCAL_IMPORTS:
                portfolio = self.execution_engine.get_portfolio_summary()
                notification_text = self._build_notification_text(portfolio)
            else:
                notification_text = f"## 📊 闭环流程完成\n**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            response = requests.post(
                f"{self.notification_url}/notify",
                json={
                    'text': notification_text,
                    'title': '投资决策报告',
                    'priority': 'medium',
                    'source': 'pipeline_scheduler',
                    'tags': ['report']
                },
                timeout=10
            )

            if response.status_code == 200:
                logger.info("通知发送成功")
                return {'status': 'sent', 'response': response.json()}
            else:
                logger.warning(f"通知发送失败: {response.status_code}")
                return {'status': 'failed', 'status_code': response.status_code}

        except Exception as e:
            logger.error(f"通知发送失败: {e}")
            return {'status': 'error', 'error': str(e)}

    def _build_notification_text(self, portfolio: Dict[str, Any]) -> str:
        """构建通知内容"""
        lines = [
            "� 投资决策通知",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 30,
        ]

        risk_alerts = getattr(self, 'risk_alerts', [])
        if risk_alerts:
            lines.append("")
            lines.append("🚨 止盈止损预警")
            lines.append("-" * 30)
            for alert in risk_alerts:
                action = "止盈" if alert['action'] == 'take_profit' else "止损"
                lines.append(f"⚠️ {alert['fund_code']}: {action}信号 (盈亏: {alert['profit_rate']:.2f}%)")

        lines.append("")
        lines.append("💰 持仓概况")
        lines.append("-" * 30)

        if portfolio.get('available'):
            holdings = portfolio.get('holdings', [])
            if holdings:
                total_invested = portfolio.get('total_invested', 0)
                total_value = portfolio.get('total_value', 0)
                total_profit = portfolio.get('total_profit', 0)
                profit_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0

                lines.append(f"总资产: ¥{total_value:,.2f}")
                lines.append(f"总收益: ¥{total_profit:,.2f} ({profit_rate:+.2f}%)")
                lines.append("")

                for h in holdings:
                    fund_code = h.get('fund_code', '')
                    profit_emoji = "📈" if h.get('profit', 0) >= 0 else "📉"
                    pnl_rate = h.get('profit_rate', 0)

                    lines.append(f"┌─────────────────────────────────────┐")
                    lines.append(f"│ {fund_code}")
                    lines.append(f"│ 份额: {h.get('total_shares', 0):.2f} | 市值: ¥{h.get('current_value', 0):,.2f}")
                    lines.append(f"│ {profit_emoji} 盈亏: {pnl_rate:+.2f}%")

                    if pnl_rate >= 15:
                        lines.append(f"│ 🔴 接近止盈线(+20%)")
                    elif pnl_rate <= -8:
                        lines.append(f"│ ⚠️ 接近止损线(-10%)")

                    lines.append(f"└─────────────────────────────────────┘")
            else:
                lines.append("暂无持仓")
        else:
            lines.append("暂无持仓数据")

        lines.append("")
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def _step_backtest(self) -> Dict[str, Any]:
        """步骤7: 回测验证"""
        logger.info("运行每日回测...")

        try:
            from daily_backtest import run_daily_backtest
            report = run_daily_backtest()
            logger.info(f"回测完成:\n{report}")
            return {
                'status': 'success',
                'report': report
            }
        except Exception as e:
            logger.error(f"回测失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _save_result(self, results: Dict[str, Any]):
        """保存执行结果"""
        try:
            result_dir = Path(__file__).parent.parent / 'data' / 'pipeline'
            result_dir.mkdir(parents=True, exist_ok=True)

            result_file = result_dir / f"{results['pipeline_id']}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            logger.info(f"结果已保存: {result_file}")
        except Exception as e:
            logger.error(f"保存结果失败: {e}")

    def _send_completion_notification(self, results: Dict[str, Any]):
        """发送完成通知"""
        if not REQUESTS_AVAILABLE:
            return

        try:
            status_emoji = "✅" if results['status'] == 'success' else "❌"
            steps_summary = []
            for step in results.get('steps', []):
                step_emoji = "✅" if step['status'] == 'success' else "❌"
                steps_summary.append(f"{step_emoji} {step['step']}")

            notification_text = f"""## {status_emoji} 闭环流程完成

**状态**: {results['status']}
**耗时**: {results.get('duration_seconds', 0)}秒

### 步骤详情
{chr(10).join(steps_summary)}

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            requests.post(
                f"{self.notification_url}/notify",
                json={
                    'text': notification_text,
                    'title': '闭环流程报告',
                    'priority': 'high' if results['status'] != 'success' else 'medium',
                    'source': 'pipeline_scheduler',
                    'tags': ['pipeline', 'report']
                },
                timeout=10
            )
        except Exception as e:
            logger.error(f"发送完成通知失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            'status': 'running',
            'pipeline_status': self.pipeline_status,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='闭环调度器')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--full', action='store_true', help='运行完整闭环')
    parser.add_argument('--status', action='store_true', help='查看状态')

    args = parser.parse_args()

    scheduler = PipelineScheduler(args.config)

    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.full:
        result = scheduler.run_full_pipeline()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
