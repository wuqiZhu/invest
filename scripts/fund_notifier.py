# -*- coding: utf-8 -*-
"""
基金通知模块
支持微信企业机器人、钉钉机器人、邮件通知

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import os
import requests
import json
import hmac
import hashlib
import base64
import urllib.parse
import time
from datetime import datetime


class FundNotifier:
    """基金通知类"""
    
    def __init__(self, config=None):
        """
        初始化通知器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
    
    def send_wechat(self, content, webhook_url=None):
        """
        通过企业微信机器人发送通知
        
        Args:
            content: 通知内容
            webhook_url: webhook地址
        
        Returns:
            bool: 是否发送成功
        """
        if webhook_url is None:
            webhook_url = os.environ.get('WECHAT_WEBHOOK') or \
                          self.config.get('wechat', {}).get('webhook_url')
        
        if not webhook_url:
            print("未配置微信webhook")
            return False
        
        data = {
            "msgtype": "text",
            "text": {"content": content}
        }
        
        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print("微信通知发送成功")
                    return True
                else:
                    print(f"微信通知失败: {result.get('errmsg')}")
                    return False
            else:
                print(f"微信通知请求失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"微信通知异常: {e}")
            return False
    
    def send_dingtalk(self, content, webhook_url=None, secret=None):
        """
        通过钉钉机器人发送通知
        
        Args:
            content: 通知内容
            webhook_url: webhook地址
            secret: 加签密钥
        
        Returns:
            bool: 是否发送成功
        """
        if webhook_url is None:
            webhook_url = os.environ.get('DINGTALK_WEBHOOK') or \
                          self.config.get('dingtalk', {}).get('webhook_url')
        
        if secret is None:
            secret = os.environ.get('DINGTALK_SECRET') or \
                     self.config.get('dingtalk', {}).get('secret')
        
        if not webhook_url:
            print("未配置钉钉webhook")
            return False
        
        # 确保消息包含关键词"通知"（钉钉机器人安全设置要求）
        if "通知" not in content:
            content = f"通知：{content}"
        
        if secret:
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f'{timestamp}\n{secret}'
            hmac_code = hmac.new(
                secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        data = {
            "msgtype": "text",
            "text": {"content": content}
        }
        
        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print("钉钉通知发送成功")
                    return True
                else:
                    print(f"钉钉通知失败: {result.get('errmsg')}")
                    return False
            else:
                print(f"钉钉通知请求失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"钉钉通知异常: {e}")
            return False
    
    def send_email(self, subject, body, to_email=None):
        """
        通过邮件发送通知
        
        Args:
            subject: 邮件主题
            body: 邮件内容
            to_email: 收件人邮箱
        
        Returns:
            bool: 是否发送成功
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        if to_email is None:
            to_email = self.config.get('email', {}).get('receiver_email')
        
        if not to_email:
            print("未配置收件人邮箱")
            return False
        
        smtp_server = self.config.get('email', {}).get('smtp_server', 'smtp.qq.com')
        smtp_port = self.config.get('email', {}).get('smtp_port', 587)
        sender_email = os.environ.get('EMAIL_SENDER') or \
                       self.config.get('email', {}).get('sender_email')
        sender_password = os.environ.get('EMAIL_PASSWORD') or \
                          self.config.get('email', {}).get('sender_password')
        
        if not sender_email or not sender_password:
            print("未配置发件人邮箱信息")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            print("邮件通知发送成功")
            return True
        except Exception as e:
            print(f"邮件通知失败: {e}")
            return False
    
    def send_console(self, content):
        """
        控制台输出通知
        
        Args:
            content: 通知内容
        """
        print("\n" + "="*50)
        print("基金预警通知")
        print("="*50)
        print(content)
        print("="*50)
    
    def send(self, content, method='console', **kwargs):
        """
        发送通知
        
        Args:
            content: 通知内容
            method: 通知方式 (console, wechat, dingtalk, email)
            **kwargs: 其他参数
        
        Returns:
            bool: 是否发送成功
        """
        if method == 'console':
            self.send_console(content)
            return True
        elif method == 'wechat':
            return self.send_wechat(content, **kwargs)
        elif method == 'dingtalk':
            return self.send_dingtalk(content, **kwargs)
        elif method == 'email':
            subject = kwargs.get('subject', '基金预警通知')
            return self.send_email(subject, content, **kwargs)
        else:
            print(f"不支持的通知方式: {method}")
            return False
    
    def check_and_notify(self, fund_code, fund_info, threshold=-5, method='console'):
        """
        检查基金涨跌幅并发送通知
        
        Args:
            fund_code: 基金代码
            fund_info: 基金信息字典
            threshold: 预警阈值（百分比）
            method: 通知方式
        
        Returns:
            bool: 是否触发预警
        """
        if not fund_info:
            return False
        
        change_pct = fund_info.get('估算涨跌幅', 0)
        fund_name = fund_info.get('基金名称', fund_code)
        
        if change_pct <= threshold:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = f"""基金预警通知
时间: {timestamp}
基金: {fund_code} - {fund_name}
估算涨跌幅: {change_pct}%
预警阈值: {threshold}%
建议: 关注市场动态，理性分析"""
            
            self.send(message, method=method)
            return True
        
        return False
    
    def batch_check_and_notify(self, funds_info, threshold=-5, method='console'):
        """
        批量检查基金涨跌幅并发送通知
        
        Args:
            funds_info: 基金信息字典 {code: info}
            threshold: 预警阈值
            method: 通知方式
        
        Returns:
            list: 触发预警的基金列表
        """
        alerts = []
        
        for fund_code, fund_info in funds_info.items():
            if self.check_and_notify(fund_code, fund_info, threshold, method='console'):
                alerts.append(fund_code)
        
        # 如果有预警，汇总发送
        if alerts and method != 'console':
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            summary = f"""基金批量预警通知
时间: {timestamp}
触发预警基金数量: {len(alerts)}
触发预警基金: {', '.join(alerts)}
预警阈值: {threshold}%"""
            
            self.send(summary, method=method)
        
        return alerts


# 命令行接口
def main():
    """命令行入口"""
    import argparse
    from fund_data_fetcher import FundDataFetcher
    
    parser = argparse.ArgumentParser(description='基金通知工具')
    parser.add_argument('--fund', '-f', nargs='+', help='基金代码')
    parser.add_argument('--threshold', '-t', type=float, default=-5, help='预警阈值')
    parser.add_argument('--method', '-m', choices=['console', 'wechat', 'email'],
                       default='console', help='通知方式')
    parser.add_argument('--webhook', '-w', help='微信webhook地址')
    parser.add_argument('--email', '-e', help='收件人邮箱')
    
    args = parser.parse_args()
    
    # 配置
    config = {}
    if args.webhook:
        config['wechat'] = {'webhook_url': args.webhook}
    if args.email:
        config['email'] = {'receiver_email': args.email}
    
    # 初始化
    fetcher = FundDataFetcher()
    notifier = FundNotifier(config)
    
    # 获取基金信息
    funds_info = {}
    fund_codes = args.fund or ['110011']
    
    for code in fund_codes:
        print(f"获取基金 {code} 信息...")
        info = fetcher.get_fund_info(code)
        if info:
            funds_info[code] = info
            print(f"  基金名称: {info.get('基金名称', 'N/A')}")
            print(f"  估算涨跌幅: {info.get('估算涨跌幅', 0)}%")
    
    # 检查预警
    alerts = notifier.batch_check_and_notify(
        funds_info,
        threshold=args.threshold,
        method=args.method
    )
    
    if alerts:
        print(f"\n触发预警的基金: {', '.join(alerts)}")
    else:
        print("\n未触发预警")


if __name__ == "__main__":
    main()