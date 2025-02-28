"""
메트릭 수집 모듈

이 모듈은 애플리케이션의 다양한 메트릭을 수집하고 보고하는 기능을 제공합니다.
Prometheus, StatsD 또는 사용자 정의 메트릭 시스템과 통합할 수 있습니다.
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import json
import os

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """단일 메트릭 포인트를 나타내는 데이터 클래스"""
    name: str
    value: float
    tags: Dict[str, str]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """메트릭 포인트를 딕셔너리로 변환"""
        return {
            "name": self.name,
            "value": self.value,
            "tags": self.tags,
            "timestamp": self.timestamp
        }


class MetricRegistry:
    """
    메트릭 레지스트리
    
    모든 메트릭을 등록하고 관리합니다.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricRegistry, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """싱글톤 인스턴스 초기화"""
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
        self.meters = {}
        self.callbacks = []
        self.lock = threading.RLock()
    
    def register_callback(self, callback: Callable):
        """메트릭 데이터가 업데이트될 때마다 호출될 콜백 등록"""
        with self.lock:
            self.callbacks.append(callback)
    
    def _notify_callbacks(self, metric: MetricPoint):
        """등록된 모든 콜백에 메트릭 업데이트 알림"""
        for callback in self.callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"메트릭 콜백 실행 중 오류 발생: {e}")
    
    def counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> 'Counter':
        """카운터 메트릭 생성 또는 검색"""
        tags = tags or {}
        key = (name, frozenset(tags.items()))
        
        with self.lock:
            if key not in self.counters:
                self.counters[key] = Counter(name, tags, self)
            return self.counters[key]
    
    def gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> 'Gauge':
        """게이지 메트릭 생성 또는 검색"""
        tags = tags or {}
        key = (name, frozenset(tags.items()))
        
        with self.lock:
            if key not in self.gauges:
                self.gauges[key] = Gauge(name, tags, self)
            return self.gauges[key]
    
    def histogram(self, name: str, tags: Optional[Dict[str, str]] = None) -> 'Histogram':
        """히스토그램 메트릭 생성 또는 검색"""
        tags = tags or {}
        key = (name, frozenset(tags.items()))
        
        with self.lock:
            if key not in self.histograms:
                self.histograms[key] = Histogram(name, tags, self)
            return self.histograms[key]
    
    def meter(self, name: str, tags: Optional[Dict[str, str]] = None) -> 'Meter':
        """미터 메트릭 생성 또는 검색"""
        tags = tags or {}
        key = (name, frozenset(tags.items()))
        
        with self.lock:
            if key not in self.meters:
                self.meters[key] = Meter(name, tags, self)
            return self.meters[key]


class Metric:
    """모든 메트릭 타입의 기본 클래스"""
    
    def __init__(self, name: str, tags: Dict[str, str], registry: MetricRegistry):
        self.name = name
        self.tags = tags
        self.registry = registry
    
    def _record(self, value: float):
        """메트릭 값을 기록하고 콜백에 알림"""
        point = MetricPoint(name=self.name, value=value, tags=self.tags)
        self.registry._notify_callbacks(point)
        return point


class Counter(Metric):
    """
    증가만 가능한 카운터 메트릭
    
    이벤트 발생 횟수, 요청 수 등을 추적하는 데 사용됩니다.
    """
    
    def __init__(self, name: str, tags: Dict[str, str], registry: MetricRegistry):
        super().__init__(name, tags, registry)
        self.value = 0
        self.lock = threading.RLock()
    
    def inc(self, amount: float = 1.0) -> MetricPoint:
        """카운터 값을 지정된 양만큼 증가"""
        with self.lock:
            self.value += amount
            return self._record(self.value)
    
    def get_value(self) -> float:
        """현재 카운터 값 반환"""
        with self.lock:
            return self.value


class Gauge(Metric):
    """
    임의의 값을 가질 수 있는 게이지 메트릭
    
    현재 활성 연결, 메모리 사용량 등을 추적하는 데 사용됩니다.
    """
    
    def __init__(self, name: str, tags: Dict[str, str], registry: MetricRegistry):
        super().__init__(name, tags, registry)
        self.value = 0
        self.lock = threading.RLock()
    
    def set(self, value: float) -> MetricPoint:
        """게이지 값을 설정"""
        with self.lock:
            self.value = value
            return self._record(self.value)
    
    def inc(self, amount: float = 1.0) -> MetricPoint:
        """게이지 값을 증가"""
        with self.lock:
            self.value += amount
            return self._record(self.value)
    
    def dec(self, amount: float = 1.0) -> MetricPoint:
        """게이지 값을 감소"""
        with self.lock:
            self.value -= amount
            return self._record(self.value)
    
    def get_value(self) -> float:
        """현재 게이지 값 반환"""
        with self.lock:
            return self.value


class Histogram(Metric):
    """
    값의 분포를 추적하는 히스토그램 메트릭
    
    응답 시간, 요청 크기 등의 분포를 추적하는 데 사용됩니다.
    """
    
    def __init__(self, name: str, tags: Dict[str, str], registry: MetricRegistry):
        super().__init__(name, tags, registry)
        self.values = []
        self.count = 0
        self.sum = 0
        self.min = float('inf')
        self.max = float('-inf')
        self.lock = threading.RLock()
    
    def update(self, value: float) -> List[MetricPoint]:
        """히스토그램에 새 값 추가"""
        with self.lock:
            self.values.append(value)
            self.count += 1
            self.sum += value
            self.min = min(self.min, value)
            self.max = max(self.max, value)
            
            # 각 통계에 대한 메트릭 포인트 생성
            points = []
            
            # 카운트 메트릭
            count_tags = dict(self.tags)
            count_tags['type'] = 'count'
            points.append(MetricPoint(name=f"{self.name}.count", value=self.count, tags=count_tags))
            
            # 합계 메트릭
            sum_tags = dict(self.tags)
            sum_tags['type'] = 'sum'
            points.append(MetricPoint(name=f"{self.name}.sum", value=self.sum, tags=sum_tags))
            
            # 평균 메트릭
            avg_tags = dict(self.tags)
            avg_tags['type'] = 'avg'
            points.append(MetricPoint(name=f"{self.name}.avg", value=self.sum / self.count, tags=avg_tags))
            
            # 최소값 메트릭
            min_tags = dict(self.tags)
            min_tags['type'] = 'min'
            points.append(MetricPoint(name=f"{self.name}.min", value=self.min, tags=min_tags))
            
            # 최대값 메트릭
            max_tags = dict(self.tags)
            max_tags['type'] = 'max'
            points.append(MetricPoint(name=f"{self.name}.max", value=self.max, tags=max_tags))
            
            # 콜백에 모든 메트릭 포인트 알림
            for point in points:
                self.registry._notify_callbacks(point)
            
            return points
    
    def get_snapshot(self) -> Dict[str, float]:
        """현재 히스토그램 통계의 스냅샷 반환"""
        with self.lock:
            return {
                "count": self.count,
                "sum": self.sum,
                "avg": self.sum / self.count if self.count > 0 else 0,
                "min": self.min if self.min != float('inf') else 0,
                "max": self.max if self.max != float('-inf') else 0
            }


class Meter(Metric):
    """
    초당 이벤트 발생률을 측정하는 미터 메트릭
    
    요청률, 오류율 등을 추적하는 데 사용됩니다.
    """
    
    def __init__(self, name: str, tags: Dict[str, str], registry: MetricRegistry):
        super().__init__(name, tags, registry)
        self.count = 0
        self.start_time = time.time()
        self.last_tick = self.start_time
        
        # 1분, 5분, 15분 지수 가중 이동 평균 (EWMA)
        self.m1_rate = 0
        self.m5_rate = 0
        self.m15_rate = 0
        
        # M1 알파 값 (1-분 EWMA의 가중치)
        self.m1_alpha = 1 - pow(math.e, -5 / 60.0)
        # M5 알파 값 (5-분 EWMA의 가중치)
        self.m5_alpha = 1 - pow(math.e, -5 / 300.0)
        # M15 알파 값 (15-분 EWMA의 가중치)
        self.m15_alpha = 1 - pow(math.e, -5 / 900.0)
        
        self.lock = threading.RLock()
        
        # 백그라운드 스레드 시작
        self.running = True
        self.tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self.tick_thread.start()
    
    def _tick_loop(self):
        """백그라운드 스레드로 실행되는 틱 루프"""
        while self.running:
            try:
                self._tick()
                time.sleep(5)  # 5초마다 업데이트
            except Exception as e:
                logger.error(f"미터 틱 루프 실행 중 오류 발생: {e}")
    
    def _tick(self):
        """EWMA 값 업데이트"""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_tick
            self.last_tick = current_time
            
            instant_rate = self.count / (current_time - self.start_time) if current_time > self.start_time else 0
            
            # EWMA 업데이트
            if self.m1_rate == 0:
                self.m1_rate = instant_rate
            else:
                self.m1_rate += self.m1_alpha * (instant_rate - self.m1_rate)
            
            if self.m5_rate == 0:
                self.m5_rate = instant_rate
            else:
                self.m5_rate += self.m5_alpha * (instant_rate - self.m5_rate)
            
            if self.m15_rate == 0:
                self.m15_rate = instant_rate
            else:
                self.m15_rate += self.m15_alpha * (instant_rate - self.m15_rate)
            
            # 메트릭 포인트 기록 및 콜백에 알림
            points = []
            
            # 순간 속도 메트릭
            instant_tags = dict(self.tags)
            instant_tags['rate'] = 'instant'
            points.append(MetricPoint(name=f"{self.name}.rate", value=instant_rate, tags=instant_tags))
            
            # 1분 속도 메트릭
            m1_tags = dict(self.tags)
            m1_tags['rate'] = '1m'
            points.append(MetricPoint(name=f"{self.name}.rate", value=self.m1_rate, tags=m1_tags))
            
            # 5분 속도 메트릭
            m5_tags = dict(self.tags)
            m5_tags['rate'] = '5m'
            points.append(MetricPoint(name=f"{self.name}.rate", value=self.m5_rate, tags=m5_tags))
            
            # 15분 속도 메트릭
            m15_tags = dict(self.tags)
            m15_tags['rate'] = '15m'
            points.append(MetricPoint(name=f"{self.name}.rate", value=self.m15_rate, tags=m15_tags))
            
            for point in points:
                self.registry._notify_callbacks(point)
    
    def mark(self, count: int = 1) -> MetricPoint:
        """지정된 수의 이벤트 발생 기록"""
        with self.lock:
            self.count += count
            return self._record(self.count)
    
    def get_rates(self) -> Dict[str, float]:
        """현재 속도 값 반환"""
        with self.lock:
            current_time = time.time()
            return {
                "count": self.count,
                "mean_rate": self.count / (current_time - self.start_time) if current_time > self.start_time else 0,
                "m1_rate": self.m1_rate,
                "m5_rate": self.m5_rate,
                "m15_rate": self.m15_rate
            }
    
    def stop(self):
        """미터 정지 및 백그라운드 스레드 종료"""
        self.running = False
        if self.tick_thread.is_alive():
            self.tick_thread.join(timeout=1.0)


# 메트릭 출력 핸들러
class FileMetricHandler:
    """메트릭을 파일에 기록하는 핸들러"""
    
    def __init__(self, filepath: str, flush_interval: int = 10):
        self.filepath = filepath
        self.flush_interval = flush_interval
        self.buffer = []
        self.lock = threading.RLock()
        self.last_flush = time.time()
        
        # 디렉토리가 존재하지 않으면 생성
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
    
    def handle_metric(self, metric: MetricPoint):
        """메트릭을 버퍼에 추가하고 필요 시 플러시"""
        with self.lock:
            self.buffer.append(metric.to_dict())
            
            # 플러시 간격이 지났거나 버퍼가 충분히 차면 플러시
            current_time = time.time()
            if current_time - self.last_flush >= self.flush_interval or len(self.buffer) >= 1000:
                self.flush()
    
    def flush(self):
        """버퍼의 메트릭을 파일에 기록"""
        with self.lock:
            if not self.buffer:
                return
            
            try:
                with open(self.filepath, 'a', encoding='utf-8') as f:
                    for metric in self.buffer:
                        f.write(json.dumps(metric) + '\n')
                
                self.buffer = []
                self.last_flush = time.time()
            except Exception as e:
                logger.error(f"메트릭 파일 작성 중 오류 발생: {e}")


class PrometheusMetricHandler:
    """Prometheus 형식으로 메트릭을 노출하는 핸들러"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.RLock()
    
    def handle_metric(self, metric: MetricPoint):
        """메트릭 저장"""
        with self.lock:
            key = (metric.name, frozenset(metric.tags.items()))
            self.metrics[key] = metric
    
    def get_prometheus_metrics(self) -> str:
        """Prometheus 형식의 메트릭 반환"""
        with self.lock:
            lines = []
            
            # 메트릭별로 그룹화
            metrics_by_name = {}
            for (name, _), metric in self.metrics.items():
                if name not in metrics_by_name:
                    metrics_by_name[name] = []
                metrics_by_name[name].append(metric)
            
            # 각 메트릭에 대한 HELP 및 TYPE 라인 생성
            for name, metrics in metrics_by_name.items():
                # 메트릭 이름에서 점을 언더스코어로 대체 (Prometheus 네이밍 규칙)
                prom_name = name.replace('.', '_')
                
                # HELP 라인
                lines.append(f"# HELP {prom_name} {name} metric")
                
                # 메트릭 타입 추론
                metric_type = "gauge"  # 기본값
                if name.endswith(".count"):
                    metric_type = "counter"
                elif name.endswith(".rate"):
                    metric_type = "gauge"
                
                # TYPE 라인
                lines.append(f"# TYPE {prom_name} {metric_type}")
                
                # 각 메트릭 포인트에 대한 라인 생성
                for metric in metrics:
                    # 태그를 Prometheus 레이블로 변환
                    labels = ','.join([f'{k}="{v}"' for k, v in metric.tags.items()])
                    label_str = f"{{{labels}}}" if labels else ""
                    
                    # 메트릭 라인
                    lines.append(f"{prom_name}{label_str} {metric.value}")
                
                # 메트릭 간 간격 추가
                lines.append("")
            
            return '\n'.join(lines)


# 편의 함수
def create_metric_registry() -> MetricRegistry:
    """메트릭 레지스트리 생성"""
    return MetricRegistry()

def setup_file_metrics(registry: MetricRegistry, filepath: str):
    """파일 기반 메트릭 핸들러 설정"""
    handler = FileMetricHandler(filepath)
    registry.register_callback(handler.handle_metric)
    return handler

def setup_prometheus_metrics(registry: MetricRegistry):
    """Prometheus 메트릭 핸들러 설정"""
    handler = PrometheusMetricHandler()
    registry.register_callback(handler.handle_metric)
    return handler

# 기본 메트릭 레지스트리 인스턴스
default_registry = MetricRegistry()

# 편의 함수
def counter(name: str, tags: Optional[Dict[str, str]] = None) -> Counter:
    """기본 레지스트리에서 카운터 메트릭 생성 또는 검색"""
    return default_registry.counter(name, tags)

def gauge(name: str, tags: Optional[Dict[str, str]] = None) -> Gauge:
    """기본 레지스트리에서 게이지 메트릭 생성 또는 검색"""
    return default_registry.gauge(name, tags)

def histogram(name: str, tags: Optional[Dict[str, str]] = None) -> Histogram:
    """기본 레지스트리에서 히스토그램 메트릭 생성 또는 검색"""
    return default_registry.histogram(name, tags)

def meter(name: str, tags: Optional[Dict[str, str]] = None) -> Meter:
    """기본 레지스트리에서 미터 메트릭 생성 또는 검색"""
    return default_registry.meter(name, tags)
