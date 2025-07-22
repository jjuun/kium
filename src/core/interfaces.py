"""
A-ki 프로젝트 인터페이스 정의
컴포넌트 간 결합도를 낮추고 테스트 가능성을 높이기 위한 프로토콜 정의
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class TradingSignal:
    """거래 신호 데이터 클래스"""
    symbol: str
    signal_type: str  # 'buy' or 'sell'
    price: float
    quantity: int
    confidence: float
    timestamp: datetime
    condition_id: Optional[int] = None
    condition_value: Optional[str] = None
    reason: Optional[List[str]] = None


@dataclass
class MarketData:
    """시장 데이터 클래스"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    change: Optional[float] = None
    change_rate: Optional[float] = None


@dataclass
class OrderRequest:
    """주문 요청 데이터 클래스"""
    symbol: str
    order_type: str  # 'buy' or 'sell'
    quantity: int
    price: float
    order_method: str = "market"  # 'market' or 'limit'
    timestamp: Optional[datetime] = None


@dataclass
class OrderResult:
    """주문 결과 데이터 클래스"""
    order_id: str
    symbol: str
    order_type: str
    quantity: int
    executed_price: float
    status: str  # 'pending', 'executed', 'cancelled', 'failed'
    timestamp: datetime
    message: Optional[str] = None


class DataCollectorProtocol(Protocol):
    """데이터 수집기 프로토콜"""
    
    def get_historical_data(self, symbol: str, days: int) -> List[MarketData]:
        """과거 데이터 수집"""
        ...
    
    def get_real_time_price(self, symbol: str) -> Optional[float]:
        """실시간 가격 조회"""
        ...
    
    def calculate_technical_indicators(self, data: List[MarketData]) -> Dict[str, Any]:
        """기술적 지표 계산"""
        ...
    
    def validate_symbol(self, symbol: str) -> bool:
        """종목코드 유효성 검증"""
        ...


class TradingStrategyProtocol(Protocol):
    """거래 전략 프로토콜"""
    
    def generate_signal(self, market_data: MarketData, indicators: Dict[str, Any]) -> Optional[TradingSignal]:
        """거래 신호 생성"""
        ...
    
    def get_strategy_name(self) -> str:
        """전략 이름 반환"""
        ...
    
    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        ...
    
    def update_parameters(self, params: Dict[str, Any]) -> bool:
        """전략 파라미터 업데이트"""
        ...


class RiskManagerProtocol(Protocol):
    """리스크 관리 프로토콜"""
    
    def check_position_size_limit(self, order: OrderRequest, current_positions: List[Dict[str, Any]]) -> bool:
        """포지션 크기 제한 확인"""
        ...
    
    def check_daily_loss_limit(self, daily_pnl: float) -> bool:
        """일일 손실 제한 확인"""
        ...
    
    def check_stop_loss(self, position: Dict[str, Any], current_price: float) -> bool:
        """손절 확인"""
        ...
    
    def check_take_profit(self, position: Dict[str, Any], current_price: float) -> bool:
        """익절 확인"""
        ...
    
    def calculate_position_size(self, available_capital: float, risk_per_trade: float) -> int:
        """포지션 크기 계산"""
        ...


class OrderExecutorProtocol(Protocol):
    """주문 실행 프로토콜"""
    
    def execute_order(self, order: OrderRequest) -> OrderResult:
        """주문 실행"""
        ...
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        ...
    
    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """주문 상태 조회"""
        ...
    
    def get_account_balance(self) -> Dict[str, Any]:
        """계좌 잔고 조회"""
        ...


class WatchlistManagerProtocol(Protocol):
    """감시종목 관리 프로토콜"""
    
    def add_symbol(self, symbol: str) -> bool:
        """감시종목 추가"""
        ...
    
    def remove_symbol(self, symbol: str) -> bool:
        """감시종목 제거"""
        ...
    
    def get_active_symbols(self) -> List[str]:
        """활성 감시종목 목록 조회"""
        ...
    
    def is_symbol_watched(self, symbol: str) -> bool:
        """종목 감시 여부 확인"""
        ...


class ConditionManagerProtocol(Protocol):
    """거래 조건 관리 프로토콜"""
    
    def add_condition(self, symbol: str, condition_type: str, category: str, value: str) -> bool:
        """거래 조건 추가"""
        ...
    
    def remove_condition(self, condition_id: int) -> bool:
        """거래 조건 제거"""
        ...
    
    def get_conditions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """거래 조건 목록 조회"""
        ...
    
    def get_conditions_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """특정 종목의 거래 조건 조회"""
        ...


class SignalMonitorProtocol(Protocol):
    """신호 모니터링 프로토콜"""
    
    def add_signal(self, signal: TradingSignal) -> int:
        """신호 추가"""
        ...
    
    def get_signals(self, symbol: Optional[str] = None, status: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        """신호 목록 조회"""
        ...
    
    def update_signal_status(self, signal_id: int, status: str, executed_price: Optional[float] = None) -> bool:
        """신호 상태 업데이트"""
        ...
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 신호 조회"""
        ...


class LoggerProtocol(Protocol):
    """로거 프로토콜"""
    
    def info(self, message: str) -> None:
        """정보 로그"""
        ...
    
    def warning(self, message: str) -> None:
        """경고 로그"""
        ...
    
    def error(self, message: str) -> None:
        """에러 로그"""
        ...
    
    def debug(self, message: str) -> None:
        """디버그 로그"""
        ...


class ConfigProtocol(Protocol):
    """설정 관리 프로토콜"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        ...
    
    def set(self, key: str, value: Any) -> None:
        """설정값 설정"""
        ...
    
    def load(self) -> None:
        """설정 로드"""
        ...
    
    def save(self) -> None:
        """설정 저장"""
        ...


class DatabaseProtocol(Protocol):
    """데이터베이스 프로토콜"""
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """쿼리 실행"""
        ...
    
    def fetchall(self) -> List[tuple]:
        """모든 결과 조회"""
        ...
    
    def fetchone(self) -> Optional[tuple]:
        """단일 결과 조회"""
        ...
    
    def commit(self) -> None:
        """트랜잭션 커밋"""
        ...
    
    def rollback(self) -> None:
        """트랜잭션 롤백"""
        ...
    
    def close(self) -> None:
        """연결 종료"""
        ...


class EventBusProtocol(Protocol):
    """이벤트 버스 프로토콜"""
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """이벤트 구독"""
        ...
    
    def unsubscribe(self, event_type: str, handler: callable) -> None:
        """이벤트 구독 해제"""
        ...
    
    def publish(self, event_type: str, data: Any) -> None:
        """이벤트 발행"""
        ...


class CacheProtocol(Protocol):
    """캐시 프로토콜"""
    
    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시 설정"""
        ...
    
    def delete(self, key: str) -> None:
        """캐시 삭제"""
        ...
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        ...


class AutoTraderProtocol(Protocol):
    """자동매매 엔진 프로토콜"""
    
    def start(self, quantity: int = 1) -> bool:
        """자동매매 시작"""
        ...
    
    def stop(self) -> bool:
        """자동매매 중지"""
        ...
    
    def is_running(self) -> bool:
        """실행 상태 확인"""
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 조회"""
        ...
    
    def set_order_cooldown(self, minutes: int) -> Dict[str, Any]:
        """주문 쿨다운 설정"""
        ...
    
    def get_order_cooldown_minutes(self) -> int:
        """주문 쿨다운 조회"""
        ...
    
    @property
    def trade_quantity(self) -> int:
        """매매 수량"""
        ...
    
    @trade_quantity.setter
    def trade_quantity(self, value: int) -> None:
        """매매 수량 설정"""
        ... 