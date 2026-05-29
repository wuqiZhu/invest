# -*- coding: utf-8 -*-
"""
AI网关 - DeepSeek财务安全系统

三把锁：
1. 日预算锁：每天DeepSeek最多花多少钱
2. 单次调用超限锁：单次prompt太长立刻拦截
3. 连续失败熔断锁：连续报错自动暂停15分钟
"""

import os
import time
import threading
from datetime import date
from collections import defaultdict


class BudgetConfig:
    def __init__(self):
        self.daily_budget_cny = float(os.getenv("DEEPSEEK_DAILY_BUDGET_CNY", "5.0"))
        self.max_input_chars = int(os.getenv("DEEPSEEK_MAX_INPUT_CHARS", "8000"))
        self.failure_circuit_threshold = int(os.getenv("DEEPSEEK_FAILURE_THRESHOLD", "5"))
        self.circuit_recovery_sec = int(os.getenv("DEEPSEEK_CIRCUIT_RECOVERY_SEC", "900"))
        self.fallback_to_mimo = os.getenv("DEEPSEEK_FALLBACK_TO_MIMO", "true").lower() == "true"


budget_config = BudgetConfig()


class DeepSeekCostTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.daily_spend = defaultdict(float)
        self.today = date.today().isoformat()

    def add_cost(self, prompt_tokens, completion_tokens, model="mimo-v2.5-pro"):
        cost = (prompt_tokens / 1_000_000) * 1.0 + (completion_tokens / 1_000_000) * 2.0
        with self.lock:
            self.daily_spend[self.today] += cost
        return cost

    def get_today_spend(self):
        with self.lock:
            return self.daily_spend.get(self.today, 0.0)

    def is_budget_exceeded(self):
        return self.get_today_spend() >= budget_config.daily_budget_cny

    def reset_daily_if_needed(self):
        new_day = date.today().isoformat()
        if new_day != self.today:
            with self.lock:
                self.today = new_day


cost_tracker = DeepSeekCostTracker()


class DeepSeekCircuitBreaker:
    def __init__(self):
        self.fail_count = 0
        self.last_fail_time = 0
        self.open = False
        self.lock = threading.Lock()

    def record_failure(self):
        with self.lock:
            self.fail_count += 1
            self.last_fail_time = time.time()
            if self.fail_count >= budget_config.failure_circuit_threshold:
                self.open = True
                print(f"[DeepSeek] 连续失败{self.fail_count}次，熔断开启！")

    def record_success(self):
        with self.lock:
            self.fail_count = 0
            self.open = False

    def allow_request(self):
        with self.lock:
            if not self.open:
                return True
            if time.time() - self.last_fail_time > budget_config.circuit_recovery_sec:
                self.open = False
                self.fail_count = 0
                print("[DeepSeek] 熔断恢复")
                return True
            return False


circuit_breaker = DeepSeekCircuitBreaker()


def validate_input(prompt):
    if len(prompt) > budget_config.max_input_chars:
        raise ValueError(
            f"DeepSeek输入过长({len(prompt)}字符)，已拦截。"
            f"上限{budget_config.max_input_chars}字符。"
        )


def send_alert(message):
    try:
        import requests
        nc_url = os.getenv("NOTIFICATION_CENTER_URL", "http://notification-center:5050")
        requests.post(
            f"{nc_url}/notify",
            json={
                "priority": "urgent" if "耗尽" in message else "high",
                "channel": "dingtalk",
                "message": f"【DeepSeek预算防护】{message}"
            },
            timeout=5
        )
    except Exception:
        pass
    print(f"[预算告警] {message}")


def get_budget_status():
    return {
        "daily_budget": budget_config.daily_budget_cny,
        "today_spend": cost_tracker.get_today_spend(),
        "budget_remaining": budget_config.daily_budget_cny - cost_tracker.get_today_spend(),
        "circuit_open": circuit_breaker.open,
        "fail_count": circuit_breaker.fail_count,
    }
