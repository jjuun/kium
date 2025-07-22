"""
A-ki 프로젝트 의존성 주입 컨테이너
컴포넌트 간 의존성을 관리하고 테스트 가능성을 높이기 위한 DI 컨테이너
"""
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .interfaces import (
    DataCollectorProtocol,
    TradingStrategyProtocol,
    RiskManagerProtocol,
    OrderExecutorProtocol,
    WatchlistManagerProtocol,
    ConditionManagerProtocol,
    SignalMonitorProtocol,
    LoggerProtocol,
    ConfigProtocol,
    DatabaseProtocol,
    EventBusProtocol,
    CacheProtocol,
    AutoTraderProtocol,
)
from .logger import logger
from .config import Config


@dataclass
class ContainerConfig:
    """컨테이너 설정"""
    db_path: str = "auto_trading.db"
    log_level: str = "INFO"
    test_mode: bool = False
    cache_enabled: bool = True
    event_bus_enabled: bool = True


class SimpleCache:
    """간단한 인메모리 캐시 구현"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        if key in self._cache:
            # TTL 체크 (간단한 구현)
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시 설정"""
        self._cache[key] = value
        if ttl:
            import time
            self._ttl[key] = time.time() + ttl
    
    def delete(self, key: str) -> None:
        """캐시 삭제"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        self._cache.clear()
        self._ttl.clear()


class SimpleEventBus:
    """간단한 이벤트 버스 구현"""
    
    def __init__(self):
        self._handlers: Dict[str, list] = {}
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """이벤트 구독"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: callable) -> None:
        """이벤트 구독 해제"""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
    
    def publish(self, event_type: str, data: Any) -> None:
        """이벤트 발행"""
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"이벤트 핸들러 실행 실패: {e}")


class DatabaseConnection:
    """데이터베이스 연결 래퍼"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """쿼리 실행"""
        conn = self._get_connection()
        cursor = conn.cursor()
        if params:
            return cursor.execute(query, params)
        return cursor.execute(query)
    
    def fetchall(self) -> list:
        """모든 결과 조회"""
        conn = self._get_connection()
        cursor = conn.cursor()
        return cursor.fetchall()
    
    def fetchone(self) -> Optional[tuple]:
        """단일 결과 조회"""
        conn = self._get_connection()
        cursor = conn.cursor()
        return cursor.fetchone()
    
    def commit(self) -> None:
        """트랜잭션 커밋"""
        if self._connection:
            self._connection.commit()
    
    def rollback(self) -> None:
        """트랜잭션 롤백"""
        if self._connection:
            self._connection.rollback()
    
    def close(self) -> None:
        """연결 종료"""
        if self._connection:
            self._connection.close()
            self._connection = None


class DependencyContainer:
    """의존성 주입 컨테이너"""
    
    def __init__(self, config: ContainerConfig):
        self.config = config
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register_singleton(self, interface: Type, implementation: Type) -> None:
        """싱글톤 등록"""
        self._factories[interface.__name__] = lambda: implementation()
    
    def register_factory(self, interface: Type, factory: callable) -> None:
        """팩토리 등록"""
        self._factories[interface.__name__] = factory
    
    def register_instance(self, interface: Type, instance: Any) -> None:
        """인스턴스 등록"""
        self._instances[interface.__name__] = instance
    
    def resolve(self, interface: Type) -> Any:
        """의존성 해결"""
        interface_name = interface.__name__
        
        # 이미 생성된 인스턴스가 있으면 반환
        if interface_name in self._instances:
            return self._instances[interface_name]
        
        # 싱글톤 인스턴스가 있으면 반환
        if interface_name in self._singletons:
            return self._singletons[interface_name]
        
        # 팩토리가 있으면 인스턴스 생성
        if interface_name in self._factories:
            instance = self._factories[interface_name]()
            if interface_name in ['LoggerProtocol', 'ConfigProtocol', 'DatabaseProtocol', 'CacheProtocol', 'EventBusProtocol']:
                self._singletons[interface_name] = instance
            return instance
        
        raise ValueError(f"등록되지 않은 인터페이스: {interface_name}")
    
    def configure_defaults(self) -> None:
        """기본 의존성 설정"""
        # 로거 설정
        self.register_instance(LoggerProtocol, logger)
        
        # 설정 관리자 설정
        config_instance = Config()
        self.register_instance(ConfigProtocol, config_instance)
        
        # 데이터베이스 설정
        db_connection = DatabaseConnection(self.config.db_path)
        self.register_instance(DatabaseProtocol, db_connection)
        
        # 캐시 설정
        if self.config.cache_enabled:
            cache = SimpleCache()
            self.register_instance(CacheProtocol, cache)
        
        # 이벤트 버스 설정
        if self.config.event_bus_enabled:
            event_bus = SimpleEventBus()
            self.register_instance(EventBusProtocol, event_bus)
    
    def cleanup(self) -> None:
        """리소스 정리"""
        # 데이터베이스 연결 종료
        if 'DatabaseProtocol' in self._singletons:
            db = self._singletons['DatabaseProtocol']
            if hasattr(db, 'close'):
                db.close()
        
        # 캐시 정리
        if 'CacheProtocol' in self._singletons:
            cache = self._singletons['CacheProtocol']
            if hasattr(cache, 'clear'):
                cache.clear()


# 전역 컨테이너 인스턴스
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """전역 컨테이너 인스턴스 반환"""
    global _container
    if _container is None:
        config = ContainerConfig()
        _container = DependencyContainer(config)
        _container.configure_defaults()
    return _container


def set_container(container: DependencyContainer) -> None:
    """전역 컨테이너 설정 (테스트용)"""
    global _container
    _container = container


def resolve_dependency(interface: Type) -> Any:
    """의존성 해결 헬퍼 함수"""
    return get_container().resolve(interface)


def cleanup_container() -> None:
    """컨테이너 정리"""
    global _container
    if _container:
        _container.cleanup()
        _container = None


# 타입 힌트를 위한 별칭
Container = DependencyContainer 