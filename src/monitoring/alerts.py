# src/monitoring/alerts.py
"""
알림 설정 모듈

이 모듈은 시스템 이벤트 및 메트릭에 기반한 알림을 생성하고 전송하는 기능을 제공합니다.
이메일, Slack, 웹훅 등 다양한 알림 채널을 지원합니다.
"""

import logging
import threading
import time
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import os

from .metrics import MetricPoint

# 로깅 설정
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """알림 심각도 수준"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    """알림 데이터 클래스"""
    name: str
    description: str
    severity: AlertSeverity
    tags: Dict[str, str]
    timestamp: float = None
    resolved: bool = False
    resolved_timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """알림을 딕셔너리로 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolved_timestamp": self.resolved_timestamp
        }
    
    def resolve(self):
        """알림을 해결됨으로 표시"""
        self.resolved = True
        self.resolved_timestamp = time.time()

class AlertRule:
    """
    알림 규칙 기본 클래스
    
    특정 조건이 충족될 때 알림을 생성하는 규칙을 정의합니다.
    """
    def __init__(self, name: str, description: str, severity: AlertSeverity, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.severity = severity
        self.tags = tags or {}
        self.last_triggered = 0
        self.cooldown_period = 300  # 기본 쿨다운 5분
        self.lock = threading.RLock()
    
    def set_cooldown(self, seconds: int):
        """알림 쿨다운 기간 설정"""
        self.cooldown_period = seconds
        return self
    
    def evaluate(self, *args, **kwargs) -> Optional[Alert]:
        """
        알림 조건 평가
        
        실제 규칙 로직은 하위 클래스에서 구현해야 합니다.
        """
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")
    
    def can_trigger(self) -> bool:
        """알림이 쿨다운 상태인지 확인"""
        with self.lock:
            now = time.time()
            return now - self.last_triggered > self.cooldown_period
    
    def _trigger(self, description: Optional[str] = None) -> Optional[Alert]:
        """알림 트리거"""
        with self.lock:
            if not self.can_trigger():
                return None
            self.last_triggered = time.time()
            alert_description = description or self.description
            return Alert(
                name=self.name,
                description=alert_description,
                severity=self.severity,
                tags=self.tags,
                timestamp=self.last_triggered
            )

class ThresholdAlertRule(AlertRule):
    """
    임계값 기반 알림 규칙
    
    메트릭 값이 지정된 임계값을 초과하면 알림을 생성합니다.
    """
    def __init__(self, name: str, metric_name: str, threshold: float, 
                 description: str, severity: AlertSeverity, 
                 comparator: str = ">", tags: Optional[Dict[str, str]] = None):
        super().__init__(name, description, severity, tags)
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparator = comparator
        
        # 비교 함수 매핑
        self.compare_funcs = {
            ">": lambda x, y: x > y,
            ">=": lambda x, y: x >= y,
            "<": lambda x, y: x < y,
            "<=": lambda x, y: x <= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y
        }
        
        if self.comparator not in self.compare_funcs:
            raise ValueError(f"유효하지 않은 비교자: {comparator}. 사용 가능한 값: {list(self.compare_funcs.keys())}")
    
    def evaluate(self, metric: MetricPoint) -> Optional[Alert]:
        """메트릭이 임계값 조건을 충족하는지 평가"""
        if metric.name != self.metric_name:
            return None
            
        compare_func = self.compare_funcs[self.comparator]
        if compare_func(metric.value, self.threshold):
            description = (f"{self.description}: {metric.name}의 값 {metric.value}이(가) " 
                           f"임계값 {self.threshold}을(를) {self.comparator} 만족합니다.")
            return self._trigger(description)
        
        return None

class ChangeAlertRule(AlertRule):
    """
    변화율 기반 알림 규칙
    
    메트릭 값의 변화율이 지정된 임계값을 초과하면 알림을 생성합니다.
    """
    def __init__(self, name: str, metric_name: str, change_threshold: float, 
                 description: str, severity: AlertSeverity, 
                 is_percent: bool = True, tags: Optional[Dict[str, str]] = None):
        super().__init__(name, description, severity, tags)
        self.metric_name = metric_name
        self.change_threshold = change_threshold
        self.is_percent = is_percent
        self.last_value = None
        self.value_lock = threading.RLock()
    
    def evaluate(self, metric: MetricPoint) -> Optional[Alert]:
        """메트릭의 변화율이 임계값을 초과하는지 평가"""
        if metric.name != self.metric_name:
            return None
        
        with self.value_lock:
            if self.last_value is None:
                self.last_value = metric.value
                return None
            
            # 변화량 또는 변화율 계산
            if self.is_percent:
                if self.last_value == 0:
                    change = float('inf') if metric.value > 0 else 0
                else:
                    change = ((metric.value - self.last_value) / abs(self.last_value)) * 100
            else:
                change = metric.value - self.last_value
            
            if abs(change) >= self.change_threshold:
                description = (f"{self.description}: {metric.name}의 변화량이 "
                               f"{change:.2f}{'%' if self.is_percent else ''}로, "
                               f"임계값 {self.change_threshold}{'%' if self.is_percent else ''}을(를) 초과했습니다.")
                self.last_value = metric.value  # 값 업데이트
                return self._trigger(description)
            
            self.last_value = metric.value  # 값 업데이트
            return None

# -------------------------------
# 추가 알림 채널 핸들러 구현
# -------------------------------

class EmailAlertHandler:
    """
    이메일 알림 핸들러

    SMTP 서버를 통해 이메일로 알림을 전송합니다.
    """
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str,
                 from_addr: str, to_addrs: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
    
    def send_alert(self, alert: Alert):
        subject = f"Alert: {alert.name} - {alert.severity.value.upper()}"
        body = json.dumps(alert.to_dict(), indent=2)
        msg = MIMEMultipart()
        msg['From'] = self.from_addr
        msg['To'] = ", ".join(self.to_addrs)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
                logger.info("이메일 알림 전송 성공")
        except Exception as e:
            logger.error(f"이메일 알림 전송 중 오류: {e}")

class SlackAlertHandler:
    """
    Slack 알림 핸들러

    Slack 웹훅 URL을 사용하여 메시지로 알림을 전송합니다.
    """
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_alert(self, alert: Alert):
        payload = {
            "text": f"Alert: {alert.name}\nSeverity: {alert.severity.value}\nDescription: {alert.description}\nTimestamp: {alert.timestamp}"
        }
        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code != 200:
                logger.error(f"Slack 알림 전송 실패: {response.status_code}, {response.text}")
            else:
                logger.info("Slack 알림 전송 성공")
        except Exception as e:
            logger.error(f"Slack 알림 전송 중 오류: {e}")

class WebhookAlertHandler:
    """
    웹훅 알림 핸들러

    지정된 URL로 HTTP POST 요청을 보내어 알림을 전송합니다.
    """
    def __init__(self, url: str):
        self.url = url
    
    def send_alert(self, alert: Alert):
        payload = alert.to_dict()
        try:
            response = requests.post(self.url, json=payload)
            if response.status_code != 200:
                logger.error(f"Webhook 알림 전송 실패: {response.status_code}, {response.text}")
            else:
                logger.info("Webhook 알림 전송 성공")
        except Exception as e:
            logger.error(f"Webhook 알림 전송 중 오류: {e}")

# -------------------------------
# 알림 디스패처 구현
# -------------------------------

class AlertDispatcher:
    """
    알림 디스패처

    등록된 모든 알림 핸들러에 알림을 전송합니다.
    """
    def __init__(self):
        self.handlers: List[Callable[[Alert], None]] = []
        self.lock = threading.RLock()
    
    def register_handler(self, handler: Callable[[Alert], None]):
        """알림 핸들러 등록"""
        with self.lock:
            self.handlers.append(handler)
    
    def dispatch(self, alert: Alert):
        """등록된 모든 핸들러에 알림 전송"""
        with self.lock:
            for handler in self.handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"알림 핸들러 실행 중 오류: {e}")

# -------------------------------
# 예시 사용법
# -------------------------------
# dispatcher = AlertDispatcher()
#
# # 이메일 알림 핸들러 등록
# email_handler = EmailAlertHandler(
#     smtp_server="smtp.example.com",
#     smtp_port=587,
#     username="your_username",
#     password="your_password",
#     from_addr="from@example.com",
#     to_addrs=["to@example.com"]
# )
# dispatcher.register_handler(email_handler.send_alert)
#
# # Slack 알림 핸들러 등록
# slack_handler = SlackAlertHandler(webhook_url="https://hooks.slack.com/services/...")
# dispatcher.register_handler(slack_handler.send_alert)
#
# # 웹훅 알림 핸들러 등록
# webhook_handler = WebhookAlertHandler(url="https://example.com/webhook")
# dispatcher.register_handler(webhook_handler.send_alert)
#
# # 이후, 생성된 Alert 인스턴스를 dispatcher.dispatch(alert)로 전송하면 됩니다.
