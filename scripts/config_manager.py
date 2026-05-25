# -*- coding: utf-8 -*-
"""
配置管理模块
负责读取、解析、验证配置文件

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import os
import yaml
from pathlib import Path


SECURE_CONFIG_MAP = {
    'notification.wechat.webhook_url': 'WECHAT_WEBHOOK',
    'notification.email.sender_email': 'EMAIL_SENDER',
    'notification.email.sender_password': 'EMAIL_PASSWORD',
    'notification.email.receiver_email': 'EMAIL_RECEIVER',
}


class ConfigManager:
    """配置管理类"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'funds': [],
        'alert': {
            'daily_drop_threshold': -3,
            'weekly_drop_threshold': -8,
            'overbought_threshold': 5,
            'oversold_threshold': -5
        },
        'notification': {
            'enabled': False,
            'method': 'console',
            'wechat': {'webhook_url': ''},
            'email': {
                'smtp_server': 'smtp.qq.com',
                'smtp_port': 587,
                'sender_email': '',
                'sender_password': '',
                'receiver_email': ''
            }
        },
        'database': {
            'path': 'fund_data.db',
            'backup_enabled': True,
            'backup_retention_days': 30
        },
        'data_source': {
            'primary': 'eastmoney',
            'fallback_enabled': True,
            'request_timeout': 15,
            'max_retries': 3,
            'request_interval': 1
        },
        'analysis': {
            'default_days': 365,
            'ma_periods': [5, 10, 20, 60],
            'rsi_period': 14,
            'bollinger_period': 20,
            'risk_free_rate': 0.03
        },
        'backtest': {
            'initial_capital': 10000,
            'short_ma': 5,
            'long_ma': 20,
            'plot_enabled': True
        },
        'output': {
            'chart_dir': '.',
            'chart_dpi': 300,
            'show_chart': False,
            'report_dir': '.'
        }
    }
    
    def __init__(self, config_path=None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 scripts/config.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            script_dir = Path(__file__).parent
            config_path = script_dir / 'config.yaml'
        
        self.config_path = Path(config_path)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"配置文件不存在: {self.config_path}")
            print("使用默认配置")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
            
            if user_config:
                self._merge_config(self.config, user_config)
                print(f"配置文件加载成功: {self.config_path}")
            else:
                print("配置文件为空，使用默认配置")
                
        except yaml.YAMLError as e:
            print(f"配置文件格式错误: {e}")
            print("使用默认配置")
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            print("使用默认配置")
    
    def reload(self):
        """重新加载配置文件"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
        print("配置已重新加载")
    
    def _merge_config(self, default, user):
        """
        合并用户配置和默认配置
        
        Args:
            default: 默认配置字典
            user: 用户配置字典
        """
        for key, value in user.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value
    
    def get(self, key_path, default=None):
        """
        获取配置值
        
        Args:
            key_path: 配置路径，如 'funds' 或 'alert.daily_drop_threshold'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_secure(self, key_path, env_var=None, default=None):
        """
        安全获取配置值，优先使用环境变量
        
        Args:
            key_path: 配置路径
            env_var: 环境变量名称
            default: 默认值
        
        Returns:
            配置值
        """
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value
        
        mapped_env = SECURE_CONFIG_MAP.get(key_path)
        if mapped_env:
            env_value = os.environ.get(mapped_env)
            if env_value:
                return env_value
        
        return self.get(key_path, default)
    
    def set(self, key_path, value):
        """
        设置配置值
        
        Args:
            key_path: 配置路径
            value: 配置值
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save_config(self, output_path=None):
        """
        保存配置到文件
        
        Args:
            output_path: 输出路径，默认覆盖原文件
        """
        if output_path is None:
            output_path = self.config_path
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            print(f"配置已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get_fund_codes(self):
        """获取启用的基金代码列表"""
        funds = self.get('funds', [])
        return [f['code'] for f in funds if f.get('enabled', True)]
    
    def get_fund_info(self, fund_code):
        """获取指定基金的配置信息"""
        funds = self.get('funds', [])
        for fund in funds:
            if fund.get('code') == fund_code:
                return fund
        return None
    
    def add_fund(self, fund_code, fund_name='', monthly_invest=0):
        """
        添加基金到配置
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            monthly_invest: 每月定投金额
        """
        funds = self.get('funds', [])
        
        # 检查是否已存在
        for fund in funds:
            if fund.get('code') == fund_code:
                print(f"基金 {fund_code} 已存在")
                return False
        
        funds.append({
            'code': fund_code,
            'name': fund_name,
            'monthly_invest': monthly_invest,
            'enabled': True
        })
        
        self.set('funds', funds)
        print(f"基金 {fund_code} 已添加")
        return True
    
    def remove_fund(self, fund_code):
        """
        从配置中移除基金
        
        Args:
            fund_code: 基金代码
        """
        funds = self.get('funds', [])
        funds = [f for f in funds if f.get('code') != fund_code]
        self.set('funds', funds)
        print(f"基金 {fund_code} 已移除")
    
    def validate(self):
        """
        验证配置有效性
        
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        
        # 验证基金列表
        funds = self.get('funds', [])
        if not funds:
            errors.append("未配置任何基金")
        
        # 验证预警阈值
        daily_threshold = self.get('alert.daily_drop_threshold')
        if daily_threshold and daily_threshold > 0:
            errors.append("日跌幅预警阈值应为负数")
        
        # 验证数据源
        valid_sources = ['eastmoney', 'sina', 'tencent']
        primary_source = self.get('data_source.primary')
        if primary_source and primary_source not in valid_sources:
            errors.append(f"无效的数据源: {primary_source}")
        
        # 验证通知配置
        notification_method = self.get('notification.method')
        if notification_method and notification_method not in ['wechat', 'email', 'console']:
            errors.append(f"无效的通知方式: {notification_method}")
        
        return len(errors) == 0, errors
    
    def print_config(self):
        """打印当前配置"""
        print("\n" + "="*50)
        print("当前配置")
        print("="*50)
        
        # 基金列表
        funds = self.get('funds', [])
        print(f"\n基金列表 ({len(funds)} 只):")
        for fund in funds:
            status = "启用" if fund.get('enabled', True) else "禁用"
            print(f"  - {fund.get('code')}: {fund.get('name', 'N/A')} "
                  f"(定投: {fund.get('monthly_invest', 0)}元, {status})")
        
        # 预警配置
        print(f"\n预警配置:")
        print(f"  日跌幅阈值: {self.get('alert.daily_drop_threshold')}%")
        print(f"  周跌幅阈值: {self.get('alert.weekly_drop_threshold')}%")
        
        # 数据源
        print(f"\n数据源配置:")
        print(f"  主数据源: {self.get('data_source.primary')}")
        print(f"  备用数据源: {'启用' if self.get('data_source.fallback_enabled') else '禁用'}")
        
        # 数据库
        print(f"\n数据库配置:")
        print(f"  路径: {self.get('database.path')}")
        
        print("="*50)


# 命令行接口
def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='配置管理工具')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--show', action='store_true', help='显示当前配置')
    parser.add_argument('--validate', action='store_true', help='验证配置')
    parser.add_argument('--add-fund', nargs=3, metavar=('CODE', 'NAME', 'INVEST'),
                       help='添加基金: CODE NAME MONTHLY_INVEST')
    parser.add_argument('--remove-fund', metavar='CODE', help='移除基金')
    
    args = parser.parse_args()
    
    # 加载配置
    config = ConfigManager(args.config)
    
    if args.show:
        config.print_config()
    
    if args.validate:
        is_valid, errors = config.validate()
        if is_valid:
            print("配置验证通过")
        else:
            print("配置验证失败:")
            for error in errors:
                print(f"  - {error}")
    
    if args.add_fund:
        code, name, invest = args.add_fund
        config.add_fund(code, name, int(invest))
        config.save_config()
    
    if args.remove_fund:
        config.remove_fund(args.remove_fund)
        config.save_config()


if __name__ == "__main__":
    main()